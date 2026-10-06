# -*- coding: utf8 -*-
"""
child_growth.py —— 儿童成长结算桩 child_growth_pass (x86 32 位, keystone 装配 + capstone 回读自检)

两件事:
  1) **每月**给每个在场孩子按年龄档位攒"自然保底"分数, 攒满 100 就给"最落后的一维"+1。
     培养指令(CMD_RING)的消费在 M3b-3, 在本桩的尾段。
  2) **M4 元服**: 虚岁 >= AGE_PUKU 的孩子当场转成人 —— 摘儿童态 → 归属挂载 → 记归属码 + 人次埋点。
     元服瞬间**不改五维** (培养成果 = 元服值 = 之后 AI 眼中的他), 此后 nibble=0xf, 本桩不再碰他。

调用点: 只有 month_hook (child_stub.py) 里 child_pass 之后的第二段 call。
        保存侧钩(历史名 load_hook) **不调** ⇒ 读档不白涨 (§6.3 决策)。

月守卫: 用日历月 `byte[0x5205F1]` +1 存进 `KID_TAB+9` (0 = 本进程从未结算)。
        +1 是为了让"存过 0 月"和"没存过"可分 —— 月基 0/1 都成立, 不依赖游戏的月编号起点。

引擎侧原语 (逐条反汇编实测, 见 PLAN_CHILD_RAISING.md §6.3/§6.9 + probe_genpuku*.txt):
  0x49A5C0  ecx = 实体 → eax = 年龄;  把 ecx 当工作寄存器用掉了(调用后要重取指针), 纯 ret
  0x4A2F80  字段写手(统率): ecx = 字段指针, push delta, `ret 4`; 内部 sat_add 上限 0x64;
            保存 esi, 毁 eax/ecx/edx。 每维 +0x20 ⇒ 武力 0x4A2FA0 / 内政 0x4A2FC0 / 外交 0x4A2FE0 / 魅力 0x4A3000
  0x524A20  BSDATA 运行时镜像, 59B/条 (INST 里 `mov ecx,0x524a20` + `oid*59`, 已被 C7e 断言未搬动)
  ── M4 归属簇 (全部 cdecl/thiscall 实测, 都 push/pop 自己的 ebx/esi/edi ⇒ 但桩里仍显式保护) ──
  0x49A6B0  ecx=实体, push val, `ret 4` ⇒ word[+0x2c] 低 nibble := val & 0xf   (成人 = 0xf: ents_dump 369/370)
  0x49A6D0  ecx=实体, push v,   `ret 4` ⇒ bit4 = (v != 0)  (v=0 = 解除排除 ⇒ 下月起进名单)
  0x4A5100  cdecl(本人, 主人) → eax=1/0: **真正的挂载原语**。校验主人(bit15=0 / 身分码!=0 / 城<0xc8 / 国<0x31)
            后: 本人.国:=主人.国, 本人.城:=主人.城, 0x4A0540 进主人城链表(节点=实体+4, 已在链上则不动 ⇒ 幂等),
            +0x16=0, +0x12=0xff, +0x13=城-0x38, 本人身分码==0 时置 1(家臣)。 **不写主君 +0x2a**。
  0x49A800  ecx=实体, push 1, `ret 4` ⇒ bit11 (大名一族) —— 0x4A5220 尾部对"父=大名"的同一手
  0x4A5290  cdecl(本人) → eax=1/0: 本国国主挂载(查 0x5179b8+国*18 的国主槽), 查不到/不合格则**浪人化**
            (城=0x49F940(所属), 身分码=0, 国=0xff, +0x16 清 0x3f 位, +0x12=0xff, +0x13=城-0x38)
  0x4A4FC0  cdecl(本人): 三级派发 随主君(0x4A5010)→随父(0x4A5220)→国主/浪人(0x4A5290),
            ★但入口门是 `test byte[+0x2d],7`(=身分码), 我们的孩子身分码==0 ⇒ **只走短路径, 不挂载**
            ⇒ M4 不能用它做归属, 只能自己按 随父→国主/浪人 的顺序调底层 (本节即为此)。

KID_TAB 条目 (KID_ESZ=12, 按**槽**索引; 唯一真源就是下面的 KID 常量):
  +0 word 亲密度   +2 word 已投入点   +4 byte 五维增量位图(bit d = 第 d 维被养过)
  +5 byte 自然保底累加器(0..99)   +6 byte 活动码   +7 byte 剩余天数
  +8 byte 教席     +9 byte 上次结算月+1(0=从未)   +10 word 元服归属记录(0=尚未元服 1随父 2挂国主 3浪人)
     ★归属码是**读数**, 不是门: 重复元服由入口的 `nibble==0xb` 天然挡住(元服后 nibble=0xf)。
"""

AGE_GET = 0x49A5C0          # ecx=实体 -> eax=年龄 (clobbers ecx)
STAT_W0 = 0x4A2F80          # 五维写手表首项 (统率), 每维 +0x20
STAT_STRIDE = 0x20
SAT_ADD = 0x4EBCA0          # (cur, delta, cap) -> min(cur+delta, cap)  由 STAT_W0 内部调用
BSD_BASE = 0x524A20         # BSDATA 运行时镜像基址
BSD_REC_SZ = 59
BSD_DIM0 = 0x16             # 记录里的成年五维首字节
DATE_M = 0x5205F1           # 当前月 (byte)
DATE_Y, DATE_D = 0x5205F0, 0x5205F2   # 当前年 / 当前日 (byte) —— M5 门禁用
ENT_DIM0 = 0x0A             # 实体里的五维首字节
ENT_OID = 0x02
ENT_STATUS = 0x2C

# ---- M4 元服: 归属簇原语 (文件头逐条列了语义与调用约定) ----
NIB_SET = 0x49A6B0          # ecx=实体, push val -> word[+0x2c] 低 nibble := val&0xf
EXCL_SET = 0x49A6D0         # ecx=实体, push v -> bit4 (v=0 解除排除)
DAIMYO_SET = 0x49A800       # ecx=实体, push 1 -> bit11 (大名一族)
MOUNT = 0x4A5100            # cdecl(本人, 主人) -> eax=1 挂进主人家 / 0 主人不合格
LORD_OR_RONIN = 0x4A5290    # cdecl(本人) -> eax=1 挂本国国主 / 0 浪人化
NIBBLE_ADULT = 0xf          # 原生成人态 (实测 369/370 个原生实体 = 0xf)
# ---- M3d 教席三通道: 教席实体取数原语 ----
PLAYER_ENT = 0x49f5e0       # 主角实体 getter (无参, eax = 玩家对象)
QUALIFY = 0x4b5620          # 资格判定 (学习者, 师父): 技能/外交/魅力达标 => eax=0 (教到顶就教不动, 直接复用)
T_LORD_CAP, T_FATH_CAP = 0x1e, 0x1c   # 主角 T 上限 30 / 父 T 上限 28
T_LORD_MUL, T_FATH_MUL = 0x19, 0x16   # 主角 主维*25/100 / 父 最高维*22/100
ID_MASK = 0x700             # 身分码位域 (word[+0x2c] 的 bits8..10); 7=大名+10 / 6=重臣+5
ID_DAIMYO, ID_KARO = 7, 6
PUKU = {'none': 0, 'follow': 1, 'lord': 2, 'ronin': 3}   # KID_TAB+10 归属码
DAIMYO_MASK = 0x700         # 身分码 == 7 = 大名

# ---- M3b-3: 原生随机数 ----
# 0x4EBD60(n): cdecl, 调用方清栈。内部 push esi / `mov esi,[esp+8]` 取参, n<2 直接返 0;
#   否则 call 0x4EBD30 (LCG: seed=seed*0x41C64E6D+0x3039, 返 (seed>>16)&0x7fff) -> eax=rand(0..32767)
#   `and eax,0xffff ; cdq ; idiv esi` -> eax = rand % n  (高位已被 and 清掉, 返回值干净)
#   毁 eax/edx, esi 自己 push/pop, ebx/ebp/edi 不动。
# 0x4EBD50(seed) = srand (写 [0x50DE48]); 种子地址 0x50DE48 —— 手测时想反推概率可直接读/写它。
RAND = 0x4EBD60
RAND_SEED = 0x50DE48

NIBBLE_CHILD = 0xb
AGE_FREEZE = 15             # 虚岁 >= 此值 => 自然成长停 (M4: 到龄当场元服, 之后本桩不再碰他)
AGE_PUKU = AGE_FREEZE       # 元服阈值默认与冻结线同值; build 可用 KID_AGE_GENPUKU 抬(99=只长不元服)
RATES = (14, 35, 52)        # 百分定点/月: 0-6 / 7-11 / 12-14  (阶段边界 = RATES 的下标界)
STAGE_EDGES = (7, 12)       # age<7 -> RATES[0]; 7<=age<12 -> RATES[1]; 12<=age<15 -> RATES[2]
NDIM = 5
ACC_FULL = 100
START_FLOOR = 5             # 五维起步 = (成年值+1)//2, 下限 5

KID_ESZ = 12
KID = {'bond': 0, 'points': 2, 'gain': 4, 'acc': 5, 'act': 6,
       'days': 7, 'teacher': 8, 'lastm': 9, 'puku': 10}

# ================= M3b-3: CMD_RING 消费 + 成效公式 (PLAN §2.3) =================
# 队列: 头 8B = dword head / dword tail (自由递增, 取 index 用 and 0x3f), 其后 64 条 x 8B:
#   +0 word 槽   +1 byte 活动码   +2 byte 教席   +3 byte 道具档位 tier   +4 word 金   +6 word 天
# UI(M3c) 写 tail, 月结算消费 head => 「一条指令最多等一个月」。载入钩不调本桩 => 读档不重复消费。
RING_HEAD_OFF, RING_TAIL_OFF, RING_ENTS_OFF = 0x0, 0x4, 0x8
RING_N, RING_ENT_SZ = 64, 8
ENT_F = {'slot': 0x0, 'act': 0x1, 'teacher': 0x2, 'tier': 0x3, 'gold': 0x4, 'days': 0x6}
# 维度序: 0 统率 1 武力 2 内政 3 外交 4 魅力 (实体 +0x0a..0x0e, 写手表 STAT_W0 每维 +0x20 同序)
DIM_NAME = ('统率', '武力', '内政', '外交', '魅力')
# 活动表: 名称, 主加维, 基础加成 B%  (原表"读书 50% 内政否则统率"本轮取单一维度, 简化已记入 PLAN §6.6)
ACTS = (('读书', 2, 5), ('读兵书', 0, 8), ('学剑术', 1, 6), ('习礼法', 4, 5), ('茶道', 4, 8),
        ('学算术', 2, 5), ('马屋打工', 1, 5), ('铁炮见习', 1, 6), ('随父见习', 2, 4),
        ('送寺修行', 4, 7))
TEACHERS = (('自学', 2), ('主角', 20), ('父', 15), ('母', 10), ('师匠', 12))
B_TIER_STEP, B_TIER_MAX, B_TIER_MASK = 5, 15, 3      # B += tier*5, tier 只认 0..3, B 上限 15
P0, P_MIN, P_MAX, P_CAP_RAND = 10, 5, 85, 100
# 亲密 R = bond/10: 整数除法在桩里太贵, 用 (bond*0x67)>>0xa (=103/1024=0.100586)。
# 实测对 bond 0..100 与 floor(bond/10) 逐值相等 (最大偏差项 6*k+103*r < 1024, k<=10,r<=9 => 987)。
BOND_MUL, BOND_SHR = 103, 10
D_SHIFT = 2                     # D = 当前值/4  (= 值*25/100, 0..25)
STAT_CEIL = 100                 # 培养可突破史实成年值(D3), 但硬顶 100 —— 与"自然保底以史实值为顶"不同

# ================= M5 (2026-10-07): 培养节奏 / 花费 —— 用户口径 =================
# 用户实机反馈 (2026-10-07): 「好像可以无限培养, 这个肯定不对啊, 每个月培养是有限制的」。
# 实测根因: cm_foster 写 RING 条目时 word[+4](金)/word[+6](天) **恒写 0**, 而本桩消费端
#   从头到尾没读过这两个字段 ⇒ 既无花费也无月内次数门 ⇒ 一个月内可连点 64 次 (RING 容量),
#   下月初一次性全结算。本轮按用户拍板的口径补上:
#     每月 1 次 + 扣金 (天数*GOLD_PER_DAY, 照 PLAN §0.2 原生修行"每日 2 金") + 推进游戏日期。
#
# ★ 硬约束 DAY_MAX: 0x4A0D50 在「日 >= 31」时会走月进位 (0x4A0DC3 inc ebx -> 0x4A0DED
#   call 0x4A4C60 -> 0x4A4CC0 -> 月钩 0x4A4CC5), 也就是会在菜单模态里递归调本桩!
#   所以门禁要求 DATE_D + 天数 <= DAY_MAX, 限死不跨月就能绕开整条月链 (只走日事件)。
MONTHLY_CAP = 1                 # 主角每月可提交的培养指令数
ACT_DAYS = (3, 4, 4, 3, 4, 3, 5, 5, 3, 6)   # 与 ACTS 同序: 每次活动消耗天数
GOLD_PER_DAY = 2                # 每日花费. ★ 单位是"文" —— word[0x51662E] 就是 UI 上
                                #   "所持金 0贯200文" 里的那个 200 (1 贯 = 1000 文),
                                #   不是"贯". 原生修行同样是 2 (PLAN §0.2), 照抄口径。
DAY_MAX = 30                    # 一个月的天数上界 (到 31 就走月进位)
PAY = 0x44E350                  # cdecl(amt): 主角支付 amt (单位同 GOLD_PTR); 内部 sat_sub 不查余额 => 调用前自查
GOLD_PTR = 0x51662E             # 主角金钱 word = word[0x516610 + 0x1e]
ADVANCE_DAY = 0x4A0D50          # stdcall(hours, 1): 推进时间; 全镜像原生调用一律 (24, 1) 逐日推
ADVANCE_HOURS = 24
assert len(ACT_DAYS) == len(ACTS), (len(ACT_DAYS), len(ACTS))


SRC = """
child_growth_pass:
  push ebx
  push ebp
  push esi
  push edi
  sub esp, 0x10
  inc dword ptr [%(c_pass)s]
  ; 埋点: child_growth_pass 开始 (0x43 = 'C')
  push 0x43
  call %(debug_log)s
  mov ebx, %(sched)s
cg_next:
  movzx eax, word ptr [ebx]
  cmp ax, 0xffff
  je cg_done
  movzx edx, word ptr [ebx + 2]
  lea esi, [edx + edx * 2]
  shl esi, 4
  sub esi, edx
  add esi, %(pool)s
  lea eax, [edx + edx * 2]
  shl eax, 2
  add eax, %(kid)s
  mov edi, eax
  movzx eax, byte ptr [esi + 0x2c]
  and al, 0x0f
  cmp al, 0xb
  jne cg_advance
  movzx eax, byte ptr [esi + 0x2d]
  test al, 0x80
  jnz cg_advance
  movzx eax, byte ptr [%(date_m)s]
  inc eax
  cmp al, byte ptr [edi + 9]
  je cg_dupm
  mov byte ptr [edi + 9], al
  inc dword ptr [%(c_settled)s]
  ; 埋点: 即将取年龄 (0x44 = 'D')
  push 0x44
  call %(debug_log)s
  ; ★ 无 add esp,4: debug_log 是 stdcall(ret 4), 自己清参数 (见 2026-10-07 的 ESP 漂移事故)
  mov ecx, esi
  call %(age_get)s
  cmp eax, %(puku_age)s
  jae cg_freeze
  mov dword ptr [esp + 0xc], 0xe
  cmp eax, 7
  jb cg_rate_ok
  mov dword ptr [esp + 0xc], 0x23
  cmp eax, 0xc
  jb cg_rate_ok
  mov dword ptr [esp + 0xc], 0x34
cg_rate_ok:
  movzx eax, byte ptr [edi + 5]
  add eax, dword ptr [esp + 0xc]
  cmp eax, 0x64
  jb cg_acc_low
  sub eax, 0x64
  mov byte ptr [edi + 5], al
  jmp cg_grow
cg_acc_low:
  mov byte ptr [edi + 5], al
  jmp cg_autoteach
cg_grow:
  movzx eax, word ptr [esi + 2]
  imul eax, eax, 0x3b
  add eax, %(bsd_dim0)s
  mov dword ptr [esp + 8], eax
  mov dword ptr [esp], 0
  mov dword ptr [esp + 4], 0
  mov dword ptr [esp + 0xc], 0
cg_scan:
  mov ecx, dword ptr [esp]
  movzx eax, byte ptr [esi + ecx + 0x0a]
  mov edx, dword ptr [esp + 8]
  movzx edx, byte ptr [edx + ecx]
  sub edx, eax
  cmp edx, dword ptr [esp + 0xc]
  jle cg_scan_next
  mov dword ptr [esp + 0xc], edx
  mov dword ptr [esp + 4], ecx
cg_scan_next:
  inc dword ptr [esp]
  cmp dword ptr [esp], 5
  jb cg_scan
  cmp dword ptr [esp + 0xc], 0
  jle cg_full
  mov ecx, dword ptr [esp + 4]
  mov edx, 1
  shl edx, cl
  or byte ptr [edi + 4], dl
  inc dword ptr [%(c_natural)s]
  mov eax, %(stat_w0)s
  imul ecx, ecx, 0x20
  add eax, ecx
  mov ecx, dword ptr [esp + 4]
  lea ecx, [esi + ecx + 0x0a]
  push 1
  call eax
  jmp cg_autoteach
cg_full:
  inc dword ptr [%(c_full)s]
  jmp cg_autoteach
cg_autoteach:
  # ---- M3d elder auto-teach channel (father monthly auto 1x / player same-city in-person) ----
  # in: esi=child ent, edi=KID_TAB entry, ebx=sched cursor ([ebx+4]=fslot)
  # pick most-lagging dim (same scan as cg_grow); on success +1 that dim, mark bitmap/points, inc marker
  # reuse: qualify 0x4b5620(learner, teacher) / player ent 0x49f5e0 / rand 0x4EBD60
  movzx ecx, word ptr [esi + 2]
  imul ecx, ecx, 0x3b
  add ecx, %(bsd_dim0)s
  mov dword ptr [esp + 8], ecx
  mov dword ptr [esp], 0
  mov dword ptr [esp + 4], 0
  mov dword ptr [esp + 0xc], 0
cg_at_scan:
  mov ecx, dword ptr [esp]
  movzx eax, byte ptr [esi + ecx + 0x0a]
  mov edx, dword ptr [esp + 8]
  movzx edx, byte ptr [edx + ecx]
  sub edx, eax
  cmp edx, dword ptr [esp + 0xc]
  jle cg_at_scan_next
  mov dword ptr [esp + 0xc], edx
  mov dword ptr [esp + 4], ecx
cg_at_scan_next:
  inc dword ptr [esp]
  cmp dword ptr [esp], 5
  jb cg_at_scan
  # ---- father auto-teach (cg_at_father) ----
  movzx ecx, word ptr [ebx + 4]
  cmp cx, 0xffff
  je cg_at_player
  lea eax, [ecx + ecx * 2]
  shl eax, 4
  sub eax, ecx
  add eax, %(pool)s
  mov ebp, eax
  movzx edx, byte ptr [esi + 0x25]
  cmp dl, byte ptr [ebp + 0x25]
  jne cg_at_player
  push ebp
  push esi
  call %(qualify)s
  add esp, 8
  test eax, eax
  jz cg_at_player
  movzx edx, byte ptr [ebp + 0x0a]
  movzx ecx, byte ptr [ebp + 0x0b]
  cmp cl, dl
  jb cg_at_fm1
  mov edx, ecx
cg_at_fm1:
  movzx ecx, byte ptr [ebp + 0x0c]
  cmp cl, dl
  jb cg_at_fm2
  mov edx, ecx
cg_at_fm2:
  movzx ecx, byte ptr [ebp + 0x0d]
  cmp cl, dl
  jb cg_at_fm3
  mov edx, ecx
cg_at_fm3:
  movzx ecx, byte ptr [ebp + 0x0e]
  cmp cl, dl
  jb cg_at_fm4
  mov edx, ecx
cg_at_fm4:
  imul edx, edx, %(t_fath_mul)s
  mov eax, edx
  xor edx, edx
  mov ecx, 0x64
  div ecx
  cmp eax, %(t_fath_cap)s
  jbe cg_at_fm5
  mov eax, %(t_fath_cap)s
cg_at_fm5:
  # P = clamp(10 + T + 0(bond/10) - cur/4, 5, 85); B=0 (auto-teach has no activity)
  mov edx, eax
  add edx, 0xa
  movzx ecx, word ptr [edi]
  cmp ecx, 0x64
  jbe cg_at_bp1
  mov ecx, 0x64
cg_at_bp1:
  imul ecx, ecx, 0x67
  shr ecx, 0xa
  add edx, ecx
  mov ecx, dword ptr [esp + 4]
  movzx ecx, byte ptr [esi + ecx + 0x0a]
  shr ecx, 2
  sub edx, ecx
  cmp edx, 5
  jge cg_at_ph_hi
  mov edx, 5
cg_at_ph_hi:
  cmp edx, 0x55
  jle cg_at_ph_done
  mov edx, 0x55
cg_at_ph_done:
  cmp dword ptr [esp + 0xc], 0
  jle cg_at_fire
  push 0x64
  call %(rand)s
  add esp, 4
  cmp eax, edx
  jae cg_at_fire
  mov ecx, dword ptr [esp + 4]
  mov eax, %(stat_w0)s
  imul ecx, ecx, 0x20
  add eax, ecx
  mov ecx, dword ptr [esp + 4]
  lea ecx, [esi + ecx + 0x0a]
  push 1
  call eax
  mov ecx, dword ptr [esp + 4]
  mov edx, 1
  shl edx, cl
  or byte ptr [edi + 4], dl
  inc word ptr [edi + 2]
cg_at_fire:
  inc dword ptr [%(teach_parent)s]
  jmp cg_at_player
  # ---- player same-city in-person teach (cg_at_player) ----
cg_at_player:
  call %(player_ent)s
  mov ebp, eax
  movzx edx, byte ptr [esi + 0x25]
  cmp dl, byte ptr [ebp + 0x25]
  jne cg_at_done
  inc dword ptr [%(teach_lord)s]
  mov ecx, dword ptr [esp + 4]
  movzx eax, byte ptr [ebp + ecx + 0x0a]
  imul eax, eax, %(t_lord_mul)s
  xor edx, edx
  mov ecx, 0x64
  div ecx
  movzx edx, word ptr [ebp + 0x2c]
  and edx, %(id_mask)s
  shr edx, 8
  xor ecx, ecx
  cmp dl, %(id_daimyo)s
  jne cg_at_pb2
  mov ecx, 0xa
  jmp cg_at_pb3
cg_at_pb2:
  cmp dl, %(id_karo)s
  jne cg_at_pb3
  mov ecx, 5
cg_at_pb3:
  add eax, ecx
  cmp eax, %(t_lord_cap)s
  jbe cg_at_pb4
  mov eax, %(t_lord_cap)s
cg_at_pb4:
  mov edx, eax
  add edx, 0xa
  movzx ecx, word ptr [edi]
  cmp ecx, 0x64
  jbe cg_at_bp2
  mov ecx, 0x64
cg_at_bp2:
  imul ecx, ecx, 0x67
  shr ecx, 0xa
  add edx, ecx
  mov ecx, dword ptr [esp + 4]
  movzx ecx, byte ptr [esi + ecx + 0x0a]
  shr ecx, 2
  sub edx, ecx
  cmp edx, 5
  jge cg_at_p2_hi
  mov edx, 5
cg_at_p2_hi:
  cmp edx, 0x55
  jle cg_at_p2_done
  mov edx, 0x55
cg_at_p2_done:
  push 0x64
  call %(rand)s
  add esp, 4
  cmp eax, edx
  jae cg_at_done
  mov ecx, dword ptr [esp + 4]
  mov eax, %(stat_w0)s
  imul ecx, ecx, 0x20
  add eax, ecx
  mov ecx, dword ptr [esp + 4]
  lea ecx, [esi + ecx + 0x0a]
  push 1
  call eax
  mov ecx, dword ptr [esp + 4]
  mov edx, 1
  shl edx, cl
  or byte ptr [edi + 4], dl
  inc word ptr [edi + 2]
cg_at_done:
  jmp cg_advance

cg_freeze:
  inc dword ptr [%(c_freeze)s]
  ; 埋点: 即将元服 (0x45 = 'E')
  push 0x45
  call %(debug_log)s
  ; ★ 无 add esp,4: debug_log 是 stdcall(ret 4), 自己清参数
  # ---- M4 genpuku (D2: follow father first, engine's lord/ronin channel as fallback) ----
  #   one-shot gate = the low nibble at this stub's entry: after we set 0xf the `cmp al,0xb`
  #   below never hits again. PUKU code (KID_TAB+10) is a *reading* for the panel, NOT a gate:
  #   gating on it would strand a re-instantiated kid (fresh scenario / sidecar MISS puts the
  #   nibble back to 0xb) forever at 15+ in child state, and FREEZE != GENPUKU.
  #   Order: clear child state first (else the mount writes are re-treated as a kid next month),
  #   then mount, finally record puku code + person-count.
  #   Stack: 3 pushes guard ebx(cursor)/esi(self)/edi(kid entry); this branch's only local is
  #   [esp+0x10] (father ptr) - free slot of sub esp,0x10; engine callees only write below
  #   their own frame, so they cannot reach it.
  push ebx
  push esi
  push edi
  mov ecx, esi
  push 0xff
  call %(nib_set)s
  mov ecx, esi
  push 0
  call %(excl_set)s
  movzx ecx, word ptr [ebx + 4]
  cmp cx, 0xffff
  je cg_puku_native
  lea eax, [ecx + ecx * 2]
  shl eax, 4
  sub eax, ecx
  add eax, %(pool)s
  mov dword ptr [esp + 0x10], eax
  push eax
  push esi
  call %(mount)s
  add esp, 8
  test eax, eax
  je cg_puku_native
  mov edx, dword ptr [esp + 0x10]
  movzx eax, word ptr [edx + 0x2c]
  and eax, 0x700
  cmp eax, 0x700
  jne cg_puku_follow
  mov ecx, esi
  push 1
  call %(daimyo_set)s
cg_puku_follow:
  mov word ptr [edi + 0xa], 1
  inc dword ptr [%(c_mount)s]
  jmp cg_puku_done
cg_puku_native:
  push esi
  call %(lord_ronin)s
  add esp, 4
  test eax, eax
  je cg_puku_ronin
  mov word ptr [edi + 0xa], 2
  inc dword ptr [%(c_mount)s]
  jmp cg_puku_done
cg_puku_ronin:
  mov word ptr [edi + 0xa], 3
  inc dword ptr [%(c_ronin)s]
cg_puku_done:
  inc dword ptr [%(genpuku)s]
  pop edi
  pop esi
  pop ebx
  jmp cg_advance
cg_dupm:
  inc dword ptr [%(c_dupm)s]
cg_advance:
  add ebx, %(esz)s
  jmp cg_next
  # ---- M3b-3: CMD_RING consumption (after the whole pool has been scanned) ----
  # locals: [esp]=head  [esp+4]=activity code  [esp+8]=success probability P (percent)
cg_done:
  ; 埋点: 排程表扫描完成, 即将进 CMD_RING 消费 (0x46 = 'F')
  push 0x46
  call %(debug_log)s
  ; ★ 无 add esp,4: debug_log 是 stdcall(ret 4), 自己清参数
  mov eax, dword ptr [%(ring)s]
  mov dword ptr [esp], eax
  cmp eax, dword ptr [%(ring)s + 4]
  je cg_ret
cg_cmd_next:
  inc dword ptr [%(c_cmd)s]
  mov eax, dword ptr [esp]
  and eax, 0x3f
  lea ebx, [eax * 8 + %(ring_ents)s]
  movzx eax, word ptr [ebx]
  lea esi, [eax + eax * 2]
  shl esi, 2
  add esi, %(kid)s
  lea ebp, [eax + eax * 2]
  shl ebp, 4
  sub ebp, eax
  add ebp, %(pool)s
  movzx ecx, byte ptr [ebp + 0x2c]
  and cl, 0x0f
  cmp cl, 0xb
  jne cg_cmd_reject
  test byte ptr [ebp + 0x2d], 0x80
  jnz cg_cmd_reject
  bt dword ptr [%(bm)s], eax
  jnc cg_cmd_reject
  movzx eax, byte ptr [ebx + 1]
  cmp eax, 0xa
  jae cg_cmd_reject
  mov dword ptr [esp + 4], eax
  movzx edi, byte ptr [eax * 4 + %(act_tab)s]
  movzx edx, byte ptr [eax * 4 + %(act_tab)s + 1]
  movzx ecx, byte ptr [ebx + 3]
  and ecx, 3
  imul ecx, ecx, 5
  add edx, ecx
  cmp edx, 0xf
  jbe cg_teach
  mov edx, 0xf
cg_teach:
  movzx ecx, byte ptr [ebx + 2]
  cmp ecx, 5
  jae cg_cmd_reject
  cmp ecx, 1
  je cg_t_lord
  cmp ecx, 2
  je cg_t_father
  movzx ecx, byte ptr [ecx + %(teach_tab)s]
  jmp cg_t_add
cg_t_lord:
  # M3d lord T = min(30, maindim*25/100 + id bonus); idcode = word[+0x2c]&0x700 >> 8
  push esi
  push edi
  push ebp
  push edx
  call %(player_ent)s
  mov ebx, eax
  movzx eax, byte ptr [ebx + edi + 0x0a]
  imul eax, eax, %(t_lord_mul)s
  xor edx, edx
  mov ecx, 0x64
  div ecx
  movzx edx, word ptr [ebx + 0x2c]
  and edx, %(id_mask)s
  shr edx, 8
  xor ecx, ecx
  cmp dl, %(id_daimyo)s
  jne cg_t_lord_b2
  mov ecx, 0xa
  jmp cg_t_lord_b3
cg_t_lord_b2:
  cmp dl, %(id_karo)s
  jne cg_t_lord_b3
  mov ecx, 5
cg_t_lord_b3:
  add eax, ecx
  cmp eax, %(t_lord_cap)s
  jbe cg_t_lord_b4
  mov eax, %(t_lord_cap)s
cg_t_lord_b4:
  pop edx
  pop ebp
  pop edi
  pop esi
  inc dword ptr [%(teach_lord)s]
  mov ecx, eax
  jmp cg_t_add
cg_t_father:
  # M3d father T = min(28, maxdim*22/100); fslot->father ent
  push edx
  movzx eax, word ptr [ebx]
  imul eax, eax, %(esz)s
  lea edx, [%(sched)s + eax + 4]
  movzx ecx, word ptr [edx]
  cmp cx, 0xffff
  je cg_t_const_parent
  lea eax, [ecx + ecx * 2]
  shl eax, 4
  sub eax, ecx
  add eax, %(pool)s
  movzx edx, byte ptr [eax + 0x0a]
  movzx ecx, byte ptr [eax + 0x0b]
  cmp cl, dl
  jb cg_t_fa1
  mov edx, ecx
cg_t_fa1:
  movzx ecx, byte ptr [eax + 0x0c]
  cmp cl, dl
  jb cg_t_fa2
  mov edx, ecx
cg_t_fa2:
  movzx ecx, byte ptr [eax + 0x0d]
  cmp cl, dl
  jb cg_t_fa3
  mov edx, ecx
cg_t_fa3:
  movzx ecx, byte ptr [eax + 0x0e]
  cmp cl, dl
  jb cg_t_fa4
  mov edx, ecx
cg_t_fa4:
  imul edx, edx, %(t_fath_mul)s
  mov eax, edx
  xor edx, edx
  mov ecx, 0x64
  div ecx
  cmp eax, %(t_fath_cap)s
  jbe cg_t_fa5
  mov eax, %(t_fath_cap)s
cg_t_fa5:
  pop edx
  inc dword ptr [%(teach_parent)s]
  mov ecx, eax
  jmp cg_t_add
cg_t_const_parent:
  # no father (not in native pool): fallback const 15, count parent teach once
  pop edx
  mov ecx, 0xf
  jmp cg_t_add
cg_t_add:
  add edx, ecx
  add edx, 0xa
  movzx ecx, word ptr [esi]
  cmp ecx, 0x64
  jbe cg_bond
  mov ecx, 0x64
cg_bond:
  imul ecx, ecx, 0x67
  shr ecx, 0xa
  add edx, ecx
  movzx ecx, byte ptr [ebp + edi + 0x0a]
  shr ecx, 2
  sub edx, ecx
  cmp edx, 5
  jge cg_p_hi
  mov edx, 5
cg_p_hi:
  cmp edx, 0x55
  jle cg_p_done
  mov edx, 0x55
cg_p_done:
  mov dword ptr [esp + 8], edx
  inc dword ptr [%(c_roll)s]
  push 0x64
  call %(rand)s
  add esp, 4
  cmp eax, dword ptr [esp + 8]
  jae cg_cmd_fail
  movzx ecx, byte ptr [ebp + edi + 0x0a]
  cmp ecx, 0x64
  jae cg_cmd_reject
  inc dword ptr [%(c_ok)s]
  mov eax, %(stat_w0)s
  imul ecx, edi, 0x20
  add eax, ecx
  mov ecx, edi
  add ecx, ebp
  add ecx, 0x0a
  push 1
  call eax
  mov ecx, edi
  mov edx, 1
  shl edx, cl
  or byte ptr [esi + 4], dl
  inc word ptr [esi + 2]
  mov eax, dword ptr [esp + 4]
  mov byte ptr [esi + 6], al
  jmp cg_cmd_step
cg_cmd_fail:
  inc dword ptr [%(c_fail)s]
  jmp cg_cmd_step
cg_cmd_reject:
  inc dword ptr [%(c_reject)s]
cg_cmd_step:
  mov eax, dword ptr [esp]
  inc eax
  mov dword ptr [esp], eax
  mov dword ptr [%(ring)s], eax
  cmp eax, dword ptr [%(ring)s + 4]
  jne cg_cmd_next
cg_ret:
  add esp, 0x10
  pop edi
  pop esi
  pop ebp
  pop ebx
  ret
"""

CTR_KEYS = ('c_pass', 'c_settled', 'c_dupm', 'c_freeze', 'c_full', 'c_natural',
            'c_cmd', 'c_roll', 'c_fail', 'c_ok', 'c_reject', 'c_mount', 'c_ronin')
# 元服支有两条"挂上了人"的路(随父 / 挂本国国主), 故 c_mount 自增两处; 其余埋点各一处。
CTR_TWICE = ('c_mount',)


def _subs(growth_va, L):
    d = {'sched': '0x%X' % L['sched'], 'pool': '0x%X' % L['pool'], 'kid': '0x%X' % L['kid_tab'],
         'date_m': '0x%X' % DATE_M, 'age_get': '0x%X' % AGE_GET, 'stat_w0': '0x%X' % STAT_W0,
         'bsd_dim0': '0x%X' % (BSD_BASE + BSD_DIM0), 'esz': '0x%X' % L['esz'],
         'ring': '0x%X' % L['ring'], 'ring_ents': '0x%X' % (L['ring'] + RING_ENTS_OFF),
         'bm': '0x%X' % L['bm'], 'rand': '0x%X' % RAND,
         'act_tab': '0x%X' % L['act_tab'], 'teach_tab': '0x%X' % L['teach_tab'],
         'debug_log': '0x%X' % L['debug_log'],
         # ---- M4 元服支 ----
         'puku_age': '0x%X' % L['puku_age'], 'nib_set': '0x%X' % NIB_SET,
         'excl_set': '0x%X' % EXCL_SET, 'mount': '0x%X' % MOUNT,
         'daimyo_set': '0x%X' % DAIMYO_SET, 'lord_ronin': '0x%X' % LORD_OR_RONIN,
         'genpuku': '0x%X' % L['genpuku'],
         # ---- M3d: 教席实体取数 + 三通道埋点 ----
         'player_ent': '0x%X' % PLAYER_ENT, 'qualify': '0x%X' % QUALIFY,
         'teach_lord': '0x%X' % L['teach_lord'], 'teach_parent': '0x%X' % L['teach_parent'],
         'teach_shope': '0x%X' % L['teach_shope'],
         't_lord_mul': '0x%X' % T_LORD_MUL, 't_fath_mul': '0x%X' % T_FATH_MUL,
         't_lord_cap': '0x%X' % T_LORD_CAP, 't_fath_cap': '0x%X' % T_FATH_CAP,
         'id_mask': '0x%X' % ID_MASK, 'id_daimyo': '0x%X' % ID_DAIMYO, 'id_karo': '0x%X' % ID_KARO}
    for k in CTR_KEYS:
        d[k] = '0x%X' % L[k]
    return d


def act_tab_bytes():
    """活动表落盘字节: 每条 4B = (主加维, B 基础%, 0, 0)。桩按 [act*4] / [act*4+1] 读。"""
    out = bytearray()
    for _nm, dim, b in ACTS:
        assert 0 <= dim < NDIM and 0 <= b <= B_TIER_MAX, (_nm, dim, b)
        out += bytes([dim, b, 0, 0])
    return bytes(out)


def teach_tab_bytes():
    """教席表落盘字节: 每条 1B = T (百分点)。M3d 会把常数换成"能力驱动"的算法, 表位不变。"""
    return bytes(t for _nm, t in TEACHERS)


def prob(act, teacher, tier, bond, cur):
    """Python 参考实现 = 桩里那段公式的逐条翻译 (给验收脚本出对照表)。返回 (P%, 各分项)。"""
    dim, b = ACTS[act][1], ACTS[act][2]
    B = min(b + (tier & B_TIER_MASK) * B_TIER_STEP, B_TIER_MAX)
    T = TEACHERS[teacher][1]
    R = bond / 10 if bond <= 100 else 10            # 桩里先夹到 100 再 (bond*103)>>10
    D = cur >> D_SHIFT
    P = max(P_MIN, min(P_MAX, P0 + T + B + R - D))
    return P, {'dim': dim, 'P0': P0, 'T': T, 'B': B, 'R': R, 'D': D, 'P': P}


def T_of(teacher, player=None, father=None, idcode=0):
    """M3d 教席加成 T 的 Python 参考 (与桩逐位同语义):
      teacher==1 主角: min(30, 主维*25//100 + 身分加成); 身分码 7=大名+10 / 6=重臣+5
      teacher==2 父:   min(28, 最高维*22//100)
      其余(0 自学 /3 母 /4 师匠): 仍吃 TEACH_TAB 常数表
      player/father 给不出实体(None)时退常数表值, 与桩无父分支一致。"""
    if teacher == 1:
        if player is None:
            return TEACHERS[1][1]
        pstat = max(0, min(STAT_CEIL, int(player)))
        bonus = (0xa if idcode == ID_DAIMYO else 5 if idcode == ID_KARO else 0)
        return min(T_LORD_CAP, pstat * T_LORD_MUL // 0x64 + bonus)
    if teacher == 2:
        if father is None:
            return TEACHERS[2][1]
        maxdim = max(max(0, min(STAT_CEIL, int(d))) for d in father)
        return min(T_FATH_CAP, maxdim * T_FATH_MUL // 0x64)
    return TEACHERS[teacher][1]



def lint_src(src):
    """keystone 陷阱(实测): 源里裸写的多位十进制立即数会按**十六进制**吃进去 ——
    `sub esp, 16` 编成 `83 EC 16`(=22), `imul eax, eax, 59` 编成 0x59(=89)。
    ⇒ 桩源码里的立即数一律写 0x 前缀, 这里把漏网的钉死。"""
    import re
    code_only = re.sub(r'#.*', '', src)        # 注释里的 KID_TAB+10 / 15+ 不是立即数
    code_only = re.sub(r';.*', '', code_only)   # 汇编注释也用分号 (Win95/13 bytes/156 都在 ; 注释里)
    code_only = re.sub(r'0x[0-9a-fA-F]+', '', code_only)   # 先剥全部 0x 常量, 防 0x13/0x156 误报
    bad = [(m.group(0), code_only[:m.start()].count('\n') + 1)
           for m in re.finditer(r'(?<![0-9a-fA-Fx,.])\d{2,}(?![0-9a-fA-F])', code_only)]
    assert not bad, 'SRC 有未加 0x 的立即数(会被当十六进制): %s' % bad[:8]


def build(growth_va, L):
    """装配成长桩。L 需含 sched/pool/kid_tab/esz/ring/bm/act_tab/teach_tab/puku_age/genpuku
    + CTR_KEYS 全部埋点 VA。返回 (code, va, src, ins) —— va 只有 child_growth_pass 一个入口。"""
    from keystone import Ks, KS_ARCH_X86, KS_MODE_32, KS_OPT_SYNTAX_INTEL
    ks = Ks(KS_ARCH_X86, KS_MODE_32)
    ks.syntax = KS_OPT_SYNTAX_INTEL
    src = SRC % _subs(growth_va, L)
    lint_src(src)
    # keystone 不支持 ; 注释(尤其含非 ASCII), 装配前剥掉
    import re as _re
    src_clean = _re.sub(r';[^\n]*', '', src)
    code = bytes(ks.asm(src_clean, growth_va)[0])
    va = {'child_growth_pass': growth_va, 'size': len(code)}
    ins = selfcheck(code, growth_va, va, L)
    return code, va, src, ins


def entry_vas(code, origin):
    from capstone import Cs, CS_ARCH_X86, CS_MODE_32
    ins = list(Cs(CS_ARCH_X86, CS_MODE_32).disasm(code, origin))
    assert ins and ins[0].mnemonic == 'push' and ins[0].op_str == 'ebx', ins[:1]
    rets = [i for i in ins if i.mnemonic == 'ret']
    assert len(rets) == 1, ('成长桩只应有一个 ret', [hex(r.address) for r in rets])
    return {'child_growth_pass': origin}


def selfcheck(code, origin, va, L):
    """回读核对: 帧平衡、月守卫、档位常量、五维循环、埋点齐、游标前进且回边唯一。"""
    from capstone import Cs, CS_ARCH_X86, CS_MODE_32
    md = Cs(CS_ARCH_X86, CS_MODE_32)
    ins = list(md.disasm(code, origin))
    assert ins and sum(len(i.bytes) for i in ins) == len(code), '反汇编未覆盖全部字节'

    def one(mn, *pats):
        got = [i for i in ins if i.mnemonic == mn and all(p in i.op_str for p in pats)]
        assert len(got) == 1, ('应恰 1 条: %s %s (命中 %d)' % (mn, pats, len(got)))
        return got[0]

    def cnt(mn, *pats):
        return len([i for i in ins if i.mnemonic == mn and all(p in i.op_str for p in pats)])

    one('sub', 'esp, 0x10')                      # 帧: 4 个 push + 16B 局部 (capstone 打十六进制)
    one('add', 'esp, 0x10')
    one('call', '0x%x' % AGE_GET)               # 年龄走原生 getter
    assert cnt('call', '0x%x' % RAND) == 3, '原生 rand: 培养成效 + 父自动教席 + 主角自动教席 (M3d)'
    assert cnt('call', 'eax') == 4, '五维 +1 有四处(自然保底 + 培养成功 + 父自动 + 主角自动), 都走原生写手'
    assert cnt('imul', 'ecx, ecx, 0x20') == 3, '按维取写手表地址(自然 + 父自动 + 主角自动)'
    assert cnt('lea', 'esi + ecx + 0xa') == 3, 'ecx = 实体五维字段指针(自然 + 父自动 + 主角自动)'
    one('mov', 'byte ptr [edi + 9], al')        # 月守卫: 记下本月
    one('cmp', 'al, byte ptr [edi + 9]')
    assert cnt('mov', 'byte ptr [edi + 5], al') == 2, '累加器写回两条(满/不满)'
    assert cnt('or', 'byte ptr [edi + 4], dl') == 3, '自然段/父自动/主角自动 三路增量位图(KID_TAB+4)'
    assert cnt('or', 'byte ptr [esi + 4], dl') == 1, '培养段增量位图(KID_TAB+4, 指令圈共用同一字节)'
    one('cmp', 'ax, -1')                        # 哨兵
    assert cnt('push', '1') == 5, '五处 push 1 (自然段 / 培养段 / 元服大名位 / 父自动 +1 / 主角自动 +1)'
    for k in CTR_KEYS:
        want = 2 if k in CTR_TWICE else 1
        got = cnt('inc', 'dword ptr [0x%x]' % L[k])
        assert got == want, ('埋点 %s 应自增 %d 次, 实得 %d' % (k, want, got))

    # ---------------- M4 元服支形态 ----------------
    assert cnt('cmp', 'word ptr [edi + 0xa], 0') == 0, \
        '归属码不得当门用: 换剧本/影子档 MISS 后重新实例化的孩子会因残留旧码永不元服 (门=nibble, 见 SRC)'
    one('call', '0x%x' % NIB_SET)                   # 摘儿童态: 低 nibble := 0xf
    one('call', '0x%x' % EXCL_SET)                  # 解除排除位 bit4
    one('call', '0x%x' % MOUNT)                     # 随父挂载 (本人, 父)
    one('call', '0x%x' % DAIMYO_SET)                # 父=大名 => bit11 (与 0x4A5220 尾部同手)
    one('call', '0x%x' % LORD_OR_RONIN)             # 兜底: 本国国主挂载 / 浪人化
    assert cnt('movzx', 'ecx, word ptr [ebx + 4]') == 2, 'fslot 读两处(元服随父挂载 + M3d 父自动教席父实体取数)'
    one('movzx', 'eax, word ptr [edx + 0x2c]')      # 取父亲状态字查大名
    one('mov', 'dword ptr [esp + 0x10], eax')       # 父实体指针存本支专用局部
    assert cnt('add', 'esp, 8') == 2, 'cdecl 双参清栈两处(mount 随父挂载 + M3d qualify 资格判定)'
    for pc in (PUKU['follow'], PUKU['lord'], PUKU['ronin']):
        one('mov', 'word ptr [edi + 0xa], %d' % pc)   # 归属码: 1 随父 / 2 挂国主 / 3 浪人
    assert cnt('cmp', 'cx, -1') == 3, 'fslot==0xffff 判无父三处 (元服随父挂载 + 教席父实体取数指令圈 + 父自动教席)'
    assert cnt('cmp', 'eax, 0x700') == 1 and cnt('and', 'eax, 0x700') == 1, '大名判据只一处(元服支; M3d 身分掩码用 edx)'
    # 归属三分支汇合后人次只加一次, 且必须把三 push 全 pop 回去
    assert cnt('inc', 'dword ptr [0x%x]' % L['genpuku']) == 1, 'CHILD_GENPUKU 一处 (只在该月)'
    assert cnt('push', 'ebx') == 2 and cnt('push', 'esi') == 6 and cnt('push', 'edi') == 3, \
        '寄存器保护 push: 帧(ebx/esi/edi) + 元服(ebx/esi/edi) + M3d cg_t_lord(esi/edi) + cg_autoteach(esi); 其余 push 为 cdecl 实参由 add esp 清'
    assert cnt('pop', 'ebx') == 2 and cnt('pop', 'esi') == 3 and cnt('pop', 'edi') == 3, \
        '三条汇合路径 + cg_t_lord 都要 pop 回各自保存的寄存器 (esi/edi 各含 cg_t_lord 一路)'

    # ---------------- M3b-3 段形态 ----------------
    one('and', 'eax, 0x3f')                     # 64 条圈: index = head & 63
    one('lea', 'ebx, [eax*8 + 0x%x]' % (L['ring'] + RING_ENTS_OFF))
    one('bt', '0x%x' % L['bm'])                 # 只吃"儿童位图认领过的槽"
    one('movzx', 'edi, byte ptr [eax*4 + 0x%x]' % L['act_tab'])        # 活动 -> 主加维
    one('movzx', 'edx, byte ptr [eax*4 + 0x%x]' % (L['act_tab'] + 1))  # 活动 -> B 基础
    one('movzx', 'ecx, byte ptr [ecx + 0x%x]' % L['teach_tab'])          # 教席 -> T
    assert cnt('imul', 'ecx, ecx, 0x67') == 3, '亲密*103>>10 (培养 + 父自动 + 主角自动)'
    assert cnt('shr', 'ecx, 0xa') == 3, '亲密/10 的乘法近似 (培养 + 父自动 + 主角自动)'
    assert cnt('shr', 'ecx, 2') == 3, 'D = 当前值/4 (培养 + 父自动 + 主角自动)'
    assert cnt('imul', 'ecx, edi, 0x20') == 1, '培养段按维取写手表地址'
    one('inc', 'word ptr [esi + 2]')            # KID_TAB+2 已投入点
    one('mov', 'byte ptr [esi + 6], al')        # KID_TAB+6 活动码 (给面板显示"上次活动")
    one('mov', 'dword ptr [0x%x], eax' % L['ring'])        # head 写回 (tail 由 UI 维护)
    assert cnt('cmp', 'eax, dword ptr [0x%x]' % (L['ring'] + RING_TAIL_OFF)) == 2, \
        '队列判空两处: 进段前 + 每条消费后'

    # ---------------- M3d 教席三通道形态 ----------------
    assert cnt('call', '0x%x' % PLAYER_ENT) == 2, '主角实体取数两处(cg_t_lord 指令圈 + cg_at_player 自动)'
    assert cnt('call', '0x%x' % QUALIFY) == 1, '资格判定一处(cg_at_father 父同城)'
    assert cnt('inc', 'dword ptr [0x%x]' % L['teach_lord']) == 2, \
        'TEACH_LORD 自增 2 (指令圈主角教 + 自动主角教)'
    assert cnt('inc', 'dword ptr [0x%x]' % L['teach_parent']) == 2, \
        'TEACH_PARENT 自增 2 (指令圈父教 + 自动父教)'
    assert cnt('inc', 'dword ptr [0x%x]' % L['teach_shope']) == 0, \
        'TEACH_SHOPE 仍为 0 (送设施待 M3c UI 选店, 本轮回常数表)'
    assert cnt('cmp', 'ecx, 1') == 1 and cnt('cmp', 'ecx, 2') == 1, \
        '教席分发: 主角(1)/父(2) 走能力驱动, 其余(0/3/4)走常数表'
    assert cnt('cmp', 'eax, 0x1c') == 2 and cnt('mov', 'eax, 0x1c') == 2, \
        '父 T 上限 28 = min(28, 最高维*22/100) (指令圈 + 自动)'
    assert cnt('cmp', 'eax, 0x1e') == 2 and cnt('mov', 'eax, 0x1e') == 2, \
        '主角 T 上限 30 = min(30, 主维*25/100 + 身分) (指令圈 + 自动)'
    assert cnt('and', 'edx, 0x700') == 2, '身分码位域掩码两处(主角 T 的大名/重臣 加成)'
    assert cnt('cmp', 'dl, 7') == 2 and cnt('cmp', 'dl, 6') == 2, '身分码判据 大名7 / 重臣6 两处'
    assert cnt('imul', 'edx, edx, 0x16') == 2, '父 最高维*22/100 (指令圈 + 自动)'
    assert cnt('imul', 'eax, eax, 0x19') == 2, '主角 主维*25/100 (指令圈 + 自动)'
    # 夹顶/夹底常数 (P0=10 / T+B+R-D 后夹 [5,85] / B 上限 15 / rand 门 100 / 硬顶 100)
    txt = ' | '.join('%s %s' % (i.mnemonic, i.op_str) for i in ins)
    for pat in ('cmp eax, 7', 'cmp eax, 0xc', 'cmp eax, 0xf', 'mov dword ptr [esp + 0xc], 0xe',
                'mov dword ptr [esp + 0xc], 0x23', 'mov dword ptr [esp + 0xc], 0x34',
                'cmp eax, 0x64', 'sub eax, 0x64', 'cmp dword ptr [esp], 5',
                'cmp eax, 0xa', 'cmp edx, 0xf', 'mov edx, 0xf', 'add edx, 0xa',
                'cmp ecx, 0x64', 'mov ecx, 0x64', 'cmp edx, 5', 'mov edx, 5',
                'cmp edx, 0x55', 'mov edx, 0x55', 'push 0x64', 'add esp, 4',
                'mov dword ptr [esp + 8], edx', 'cmp eax, dword ptr [esp + 8]',
                'movzx ecx, byte ptr [ebp + edi + 0xa]'):
        assert pat in txt, '缺指令形态: %s' % pat
    for i in ins:
        if i.mnemonic.startswith('j') and i.op_str.startswith('0x'):
            t = int(i.op_str, 16)
            assert origin <= t < origin + len(code), '跳转越界 %08X -> %08X' % (i.address, t)
    adv = one('add', 'ebx, %d' % L['esz'])
    # 自然段循环头 = 紧跟在哨兵 cmp 之前的那条 movzx [ebx] (培养段也有一条, 别认错)
    sen = one('cmp', 'ax, -1')
    # 循环头 = movzx [ebx], 且下一句不是 `imul eax, eax, <esz>` (M3d 的 cg_t_father 是 movzx[ebx]+imul 的
    # 一次性父实体取数, 非循环; 两个真循环头分别接 `cmp ax,-1` 与 `lea`)
    heads = [i for i in ins if i.mnemonic == 'movzx' and i.op_str.endswith('[ebx]')
             and not (ins[ins.index(i) + 1].mnemonic == 'imul'
                      and ins[ins.index(i) + 1].op_str.startswith('eax, eax'))]
    assert len(heads) == 2, '两个循环头: 排程表 / 指令圈 (命中 %d)' % len(heads)
    sched_head = [h for h in heads if ins[ins.index(h) + 1] is sen]
    assert len(sched_head) == 1, '找不到排程表循环头'
    back = [i for i in ins if i.mnemonic == 'jmp' and i.op_str == '0x%x' % sched_head[0].address]
    assert len(back) == 1 and back[0].address == adv.address + adv.size, \
        '回边必须紧跟游标前进 (漏了就是死循环)'
    # 指令圈: 游标前进 = head+1 写回, 回边必须紧跟其后的 cmp/jne
    step = one('mov', 'dword ptr [0x%x], eax' % L['ring'])
    head_cmd = one('inc', 'dword ptr [0x%x]' % L['c_cmd'])   # 圈循环头 = 消费埋点自增那条
    tail_cmp = [i for i in ins if i.mnemonic == 'cmp'
                and i.op_str == 'eax, dword ptr [0x%x]' % (L['ring'] + RING_TAIL_OFF)][-1]
    jne = ins[ins.index(tail_cmp) + 1]
    assert jne.mnemonic == 'jne' and jne.op_str == '0x%x' % head_cmd.address, \
        '指令圈回边必须紧跟 head/tail 比较并跳回消费埋点处 (否则要么死循环要么漏消费)'
    assert ins.index(step) < ins.index(tail_cmp), 'head 写回应在读 tail 比较之前'
    return ins



# ---------------- Python 参考实现 (给验收脚本出"逐月预期表"用, 与桩逐位同语义) ----------------
def rate_of(age):
    return RATES[0] if age < STAGE_EDGES[0] else (RATES[1] if age < STAGE_EDGES[1] else RATES[2])


def start_stats(adult):
    """make_child 里的 50% 起步: (成年值+1)//2, 下限 5 (round-half-up)"""
    return [max(START_FLOOR, (a + 1) // 2) for a in adult]


def puku_month(age, start_month=1, ceiling=None):
    """M4: 这个孩子在第几个**结算月**元服 (1 = 开局当月)。

    与 simulate() 同源的一条换算: 虚岁每逢新年(月 12 -> 1)才 +1,
    所以第 k 个结算月的龄 = age + (start_month - 1 + k - 1) // 12。
    age 必须用引擎口径 (0x49A5C0 = 当前年 - 生年 + 1)。
    """
    ceiling = AGE_PUKU if ceiling is None else ceiling
    if age >= ceiling:
        return 1
    return 12 * (ceiling - age) + 2 - start_month


def simulate(age, adult, start_month=1, ndim=NDIM, ceiling=None):
    """从当前结算月跑到元服前, 返回 (元服前自然增长点数, 最终五维, 每点落在哪一维, 逐月轨迹)。

    age 必须用引擎口径 (0x49A5C0: 当前年 - 生年 + 1, 虚岁)。
    ceiling = 元服阈值 (虚岁), 默认 AGE_PUKU; 抬它就等于"只长不元服"(调试开关 KID_AGE_GENPUKU)。
    start_month = 开局那个月的日历月 (1..12): 虚岁在**新年**才 +1, 所以第 k 个结算月的龄是
    age + (start_month - 1 + k - 1) // 12, 不是简单每 12 个月 +1 —— 默认 1 月时两者等价。

    与桩一致的另外两条规则: 累加器跨月进位; 每次满 100 给"与史实成年值差距最大"的一维 +1
    (并列取序号最小), 全维已达天花板记 full。
    """
    ceiling = AGE_PUKU if ceiling is None else ceiling
    cur = start_stats(list(adult)[:ndim])
    ceil = [int(a) for a in adult[:ndim]]
    acc, gain, hit, full = 0, [0] * ndim, [], 0
    traj = []
    for k in range(1, 12 * (ceiling - age) + 2):
        a = age + (start_month - 1 + k - 1) // 12
        if a >= ceiling:
            break
        r = rate_of(a)
        acc += r
        fired = 0
        while acc >= ACC_FULL:
            acc -= ACC_FULL
            defs = [ceil[d] - (cur[d] + gain[d]) for d in range(ndim)]
            best = max(range(ndim), key=lambda d: (defs[d], -d))
            if defs[best] <= 0:
                full += 1
                break
            gain[best] += 1
            hit.append((k, a, best))
            fired += 1
        traj.append((k, a, r, acc, fired))
    return {'months': len(traj), 'points': sum(gain), 'by_dim': gain, 'final': [cur[d] + gain[d]
            for d in range(ndim)], 'full': full, 'hits': hit, 'acc_end': acc, 'traj': traj}


if __name__ == '__main__':
    import json, os, sys
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass
    REV = os.path.dirname(os.path.abspath(__file__))
    lay = json.load(open(os.path.join(REV, '_big_layout.json'), encoding='utf-8'))
    import child_stub as CS
    M = lambda o: lay['mod_base'] + o
    GC = lay['growth_ctrs']
    _CL = {'pool': lay['pool_va'], 'sched': lay['v']['CHILD_SCHED'], 'bm': lay['v']['CHILD_BM'],
           'preload': lay['v']['CHILD_PRELOAD'], 'rearm': lay['v']['CHILD_REARM'],
           'scan': lay['v']['CHILD_SCAN'], 'skip': lay['v']['CHILD_SKIP'],
           'place': lay['v']['CHILD_PLACE'], 'init5': lay['v']['CHILD_INIT5'],
           'growth': lay['v']['CHILD_GROWTH']}
    _, _cva, _, _ = CS.build(lay['v']['CHILD_PASS'], _CL)
    L = {'pool': lay['pool_va'], 'sched': lay['v']['CHILD_SCHED'], 'kid_tab': lay['v']['KID_TAB'],
         'esz': CS.ESZ, 'debug_log': _cva['debug_log'],
         'ring': lay['v']['CMD_RING'], 'bm': lay['v']['CHILD_BM'],
         'act_tab': lay['v']['ACT_TAB'], 'teach_tab': lay['v']['TEACH_TAB'],
         'c_pass': GC['GROWTH_PASS'], 'c_settled': GC['GROWTH_SETTLED'],
         'c_dupm': GC['GROWTH_DUPM'], 'c_freeze': GC['GROWTH_FREEZE'],
         'c_full': GC['GROWTH_FULL'], 'c_natural': GC['GROWTH_NATURAL'],
         'c_cmd': GC['GROWTH_CMD'], 'c_roll': GC['GROWTH_ROLL'], 'c_fail': GC['GROWTH_FAIL'],
         'c_ok': GC['GROWTH_OK'], 'c_reject': GC['GROWTH_REJECT'],
         'puku_age': lay.get('genpuku_age', AGE_PUKU), 'genpuku': lay['v']['CHILD_GENPUKU'],
         'c_mount': GC['GROWTH_PUKU_MOUNT'], 'c_ronin': GC['GROWTH_PUKU_RONIN'],
         # ---- M3d 三通道埋点 (TEACH_LORD/PARENT 自动教席会 >0; SHOPE 待 M3c UI 仍 0) ----
         'teach_lord': GC['TEACH_LORD'], 'teach_parent': GC['TEACH_PARENT'],
         'teach_shope': GC['TEACH_SHOPE']}
    code, va, src, ins = build(M(0x1400), L)
    print('child_growth_pass %dB  @0x%06X..0x%06X (预留 0x1400..0x2000 = %d B)'
          % (len(code), va['child_growth_pass'], va['child_growth_pass'] + len(code), 0xC00))
    for i in ins:
        print('  %08X  %-22s %s %s' % (i.address, i.bytes.hex(), i.mnemonic, i.op_str))
