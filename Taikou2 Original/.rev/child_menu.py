# -*- coding: utf8 -*-
"""
child_menu.py —— M3c 回家菜单「培养孩子」(x86 32 位, keystone 装配 + capstone 回读自检)

两块桩 + 一份只读数据, 全部落在 MOD 私有区:
  A) cm_hook   : 断点 0x4CD563 (回家菜单构建器 0x4CD480 弹菜单前) —— 把原生的
                 "码表 + 串指针数组"两份都拷进 MOD 区, 尾追第 7 项"培养孩子", 再按原生
                 约定 call 0x47BED0, 自己把返回的"序号"翻译成"指令码"(原生 0..6 / MOD 7 / 取消 -1),
                 最后逐条复刻原生收尾 pop edi/esi/ebp + add esp,0x24 + ret。
  B) cm_foster : 码 7 的处理程序, 挂在跳转表第 8 槽 (0x4CD47C 原为对齐 NOP)。
                 流程 = 选孩子(运行时拼姓名, **分页**: 一页 PAGE_KIDS 个 + 下一页/上一页) -> 选活动 -> 选教席
                 -> 选书籍档次 -> 写 CMD_RING 条目 + tail++。
                 两个分页埋点: PAGE_ROWS = 最近一次弹窗的行数(取最大值, >PAGE_KIDS 即导航行已出现),
                               PAGE_NAV  = 下一页/上一页被点的次数 (默认档 fam13 恒 0 => 没翻页发生过)。

为什么必须拷表: 原生栈上串指针数组 base=E-0x18 只有 E-0x18..E 这 24B (6 个指针), **第 7 个指针正好覆写返回地址**;
码表 base=E-0x24 的第 7 个 word 又落在 E-0x18 = ptr[0] 上 —— 两处都装不下第 7 项
(PLAN §8.1 栈容量硬约束) ⇒ 两份都搬出到 MOD 区, 且绕开 0x4CD583 的原生翻译。

引擎侧原语 (逐条实测, 见 PLAN_CHILD_RAISING.md §8.1):
  0x47BED0(count, dword* 串指针数组, flag, 0, 0) cdecl / 5 push / add esp,0x14
         -> ax = 选中序号, 0xffff = 取消。**内部 0x47BE00 限 count 为 1..12** (0x47BE0E `cmp di,0xc/jg`)
            —— 40 只是 0x47BED0 的拷贝钳位, 真正一屏最多 12 项。独立子菜单实测用 flag=4 (见 0x445758/0x412E64)。
  0x49A5C0(ecx=实体) -> eax=虚岁 (只吃 ecx; eax 被当成 16 位累加用, 高 16 位不可信 => 一律 movzx eax,ax)
  回家菜单循环头 0x4CD339 / 退出 0x4CD455; 构建器帧 E: 码表=E-0x24, 串指针数组=E-0x18, 计数在 edi。
  钩站点 0x4CD563 上的活寄存器 (从 exe 字节读出): ecx=flag(2|4) edx=串表基址 edi=项数 ebx=探病 gate 值。
  构建器返回后调用方先做两判断 (0x4CD36F `cmp ax,0xffff` / 0x4CD381 `cmp ax,4` -> 0x4CD41D),
  才 `movsx eax,ax; cmp eax,6; ja 0x4CD455; jmp [eax*4+0x4CD460]` —— 所以我们只有码 7 一条新路径,
  取消仍交回 -1 (走 ax==0xffff), 原生码 0..6 逐字不变 (码 4 压根到不了表)。

串/表极性提醒: 运行时 0x547C00=**名**表(sur_va), 0x549800=**姓**表(giv_va), 每条 7B (oid==槽 索引)。

★ 已修 bug (2026-10-07, fix3): cm_same 块里 edi 曾一身兼两职 ——
  273/275 行把 edi 当**行索引 row**(0..page_max-1) 写 sub_ptr/slot_arr 两张表,
  而 283/300 行的 `mov byte ptr [edi], al` 又把 edi 当**写指针**往里拷姓名。
  row==0 时 edi==0 ⇒ 往地址 0 写 ⇒ 点「培养孩子」必崩 (AV @ MOD+0x5ACE, EDI=0)。
  edx 在 271 行已经算好 `name_buf + row*24` 却没人拿它当游标。
  修法: 在 275 行之后、进姓名拷贝循环之前补一条 `mov edi, edx`, 让 edi 转为本行缓冲写游标
  (后面 291/300/308/322 那些 mov byte ptr [edi] 跟着一起变正确)。
"""

import os

import child_growth as CG

# ================= 补丁站点 (VA 与原始字节, 构建与验收共用) =================
HOOK_MENU_SITE = 0x4CD563        # 回家菜单构建器 0x4CD480 内, push ecx / push edx / push edi + call 前 2 字节
HOOK_MENU_ORIG = bytes.fromhex('515257E865')
CODE_LIMIT_SITE = 0x4CD390       # `cmp eax, 6` 的立即数 -> 7 (让码 7 不再是"越界即退出")
CODE_LIMIT_ORIG = b'\x06'
TABLE8_SITE = 0x4CD47C           # 跳转表第 8 槽 (表尾后的 4 字节对齐 NOP, 全镜像 0 引用)
TABLE8_ORIG = b'\x90\x90\x90\x90'
MENU_TOP = 0x4CD339              # 回家菜单循环头 (处理程序完事跳这里 = 重弹菜单)
MENU_EXIT = 0x4CD455             # 回家菜单退出 (leave)
MENU_CALL = 0x4CD367             # 循环里 call 构建器 0x4CD480 的位置
MENU_PRE_EXIT = 0x4CD41D         # 调用方预判: ax==0xffff(取消) 或 ax==4(离开) 直去这里, 不查表
DIALOG = 0x47BED0
AGE_GET = 0x49A5C0
CODE_STR_TAB = 0x50CAE8          # 原生菜单串表: 标签地址 = CODE_STR_TAB + 码*CODE_STR_STRIDE
CODE_STR_STRIDE = 11
# 构建器 0x4CD480 实际会写的指令码 (逐条从 exe 字节读出):
#   码 0 休息(恒有, 0x4CD49B 立即数) / 码 1 金库(0x4CD4A9 `mov word[esp+0xe], di`, 寄存器形式;
#     门 `test cl,4` = byte[0x516638]&4 **置位则整条消失且 edi 停在 1**) /
#   码 2 与宁宁交谈 或 码 6 与阿桢谈话((word[0x520604]>>12)&3 = 0/1; =2/3 时连 edi 都不加) /
#   码 3 武将休息室(gate=[E+4]) / 码 5 探病(gate=[E+8]) / 码 4 离开(恒有)
#   ⚠ 只按"store 立即数"扫会漏掉码 1 (它是 di 寄存器搬过去的) —— 这条已踩过一次。
#   => 项数 1..6, 我们追加 1 项 => 弹窗最多 7 项, 仍低于 12 硬门。
HOME_ITEM_MAX = 6                # 原生回家菜单本构建器最多 6 项 (0/1/2|6/3/5/4)
MENU_ITEM_MAX = 12               # 0x47BE00 的 count 上限: `test di,di/jle` + `cmp di,0xc/jg` 都直跳
                                 #   0x47BE8A `or ax,0xffff` —— **count>12 连窗口都不建, 等于没反应**
                                 #   (全镜像 107 个调用点自己就压在 2..11, 没有一处超)
PAGE_KIDS = int(os.environ.get('TKID_PAGE_KIDS', '10'))   # 一级"选孩子"每页孩子数; 尾追 下一页/上一页 ⇒ +2 = 12 正好顶门
                                                          # 构建时可用 TKID_PAGE_KIDS=2 造"分页试演档"(fam13 一城最多 6 个孩子,
                                                          # 默认 10 永远不生成导航行 => 没法手测翻页); 默认档行为逐字节不变
assert 1 <= PAGE_KIDS and PAGE_KIDS + 2 <= MENU_ITEM_MAX, '分页后一项都不能超 12 硬门'


def cap_imm(v):
    """capstone 把 <10 的立即数渲染成**十进制**(>=10 才 0x), 回读断言必须按同一套渲染比"""
    return '%d' % v if v < 10 else '0x%x' % v
NAME_ROW = 24                    # 孩子姓名行字节
STR_ROW = 24                     # 串池每项字节

AGE_GET_MASK = 0x63              # 标签里年龄钳到 99

# 串池槽位 (每项 STR_ROW 字节, GBK + NUL)
S_HOME = 0                       # 培养孩子 (回家菜单第 7 项)
S_ACT0 = 1                       # 1..10 活动
S_TEACH0 = 11                    # 11..15 教席
S_TIER0 = 16                     # 16..19 书籍档次
S_BACK = 20                      # 暂不培养 (子菜单尾项 = 退出)
S_AGE_SUFFIX = 21                # "岁"
S_PREV = 22                      # 上一页 (一级选孩子的分页导航, 只有需要时才挂)
S_NEXT = 23                      # 下一页
STR_N = 24

TIER_NAMES = ('不用书籍', '普通书籍', '良好书籍', '名品书籍')

# ================= M5 (2026-10-07): 门禁 / 确认 / 反馈 串池 =================
#   为什么另开一池: MENU_STR 的 24 项已经把 0x240 用满, 扩容会顺移后面九个数据区的地址
#   (DEC100/NAME_BUF/SLOT_ARR/... /KD_CODE), 风险与收益不成比例; 独立池落在 MOD 区尾部。
#   ★ 每条 = MS_STR_ROW 字节, 布局 [GBK][NUL][pad] —— **没有长度前缀**:
#     ① 原生对话框 0x47BED0 收的是 C 字符串指针, 串首塞长度字节会把它显示成乱码;
#     ② 反馈小框 kd_m_frame **自己数到 NUL** 再传显式 cbString (本机 TextOutA 传 -1 一个字都不画)。
#     (kid_panel 自己那套池是 [len][GBK][NUL] 紧凑排列, 两边格式不同, 别照抄解码方式。)
MS_STR_ROW = 24
_COST_LINES = tuple(u'%s：%d天/%d文' % (nm, CG.ACT_DAYS[i], CG.ACT_DAYS[i] * CG.GOLD_PER_DAY)
                    for i, (nm, _d, _b) in enumerate(CG.ACTS))
MSG_STRINGS = (
    # 0..2 门禁拒绝 (单按钮提示框)
    u'这个月已经培养过了', u'所持金不足', u'本月时日无多',
    # 3..4 确认框
    u'就这么办', u'再想想',
    # 5..14 反馈台词: **与 child_growth.ACTS 同序** (反馈小框 = 孩子名 + 这一句)
    u'书本上的道理，我记住了', u'兵书真有意思', u'剑术练得手都酸了',
    u'礼数我会好好学的', u'茶道很雅致呢', u'算术好难啊',
    u'打工挣到钱了', u'铁炮的声音真响', u'跟着父亲学到好多', u'寺里修行很清苦',
    # 15 反馈小框底部提示
    u'点击关闭',
) + _COST_LINES                      # 16..25: 每条活动的天数/花费, 确认框第一行显示它
# ★ 26: 一个孩子都扫不到时的明说。原来是静默 return —— 玩家只看到"点了没反应",
#   连"是没孩子"还是"门禁拦了"都分不出来 (2026-10-07 那两轮实机反馈都卡在这个歧义上)。
MS_DENY_MONTH, MS_DENY_GOLD, MS_DENY_TIME = 0, 1, 2
MS_OK, MS_CANCEL = 3, 4
MS_LINE0, MS_MSG_HINT = 5, 15
MS_COST0 = 16                        # 费用提示首条下标; 与 ACTS 同序, 行地址 = 池首 + (MS_COST0+act)*24
MS_NONE = MS_COST0 + len(CG.ACTS)    # 26: "此城还没有可培养的孩子" (首屏为空时才弹)
MSG_STRINGS = MSG_STRINGS + (u'此城还没有可培养的孩子',)
assert len(MSG_STRINGS) == MS_NONE + 1, (len(MSG_STRINGS), MS_NONE)
assert MS_COST0 == MS_MSG_HINT + 1, (MS_COST0, MS_MSG_HINT)


def msg_str_pool_bytes():
    out = bytearray()
    for s in MSG_STRINGS:
        b = s.encode('gbk')
        assert len(b) + 1 <= MS_STR_ROW, ('反馈串超行', s, len(b))
        out += b + b'\x00' * (MS_STR_ROW - len(b))
    return bytes(out)


def msg_str_va(str_va, i):
    return str_va + i * MS_STR_ROW


def str_items():
    """串池内容 (顺序即槽位)。活动/教席名一律从 child_growth 的表来, 不另立一份。"""
    it = [u'培养孩子']
    it += [u'%s·%s+%d%%' % (nm, CG.DIM_NAME[d], b) for nm, d, b in CG.ACTS]
    it += [u'%s+%d%%' % (nm, t) for nm, t in CG.TEACHERS]
    it += [u'%s+%d%%' % (nm, i * CG.B_TIER_STEP) for i, nm in enumerate(TIER_NAMES)]
    it += [u'暂不培养', u'岁', u'上一页', u'下一页']
    assert len(it) == STR_N, len(it)
    return it


def str_pool_bytes():
    out = bytearray()
    for s in str_items():
        b = s.encode('gbk')
        assert len(b) + 1 <= STR_ROW, ('菜单串超行', s, len(b))
        out += b + b'\x00' * (STR_ROW - len(b))     # 补齐整行 (含结束 NUL)
    return bytes(out)


def dec100_bytes():
    """DEC100[i*2] = 两位十进制 '00'..'99' —— 桩里按 age*2 直接取 2 字节, 免去除法。"""
    return ''.join('%02d' % i for i in range(100)).encode('ascii')


def submenu_ptr_bytes(str_va, first_slot, n_items):
    """静态子菜单指针数组: n_items 个选项串 + 1 个"暂不培养"。"""
    import struct
    v = [str_va + (first_slot + i) * STR_ROW for i in range(n_items)]
    v.append(str_va + S_BACK * STR_ROW)
    return struct.pack('<%dI' % len(v), *v)


def scratch_layout(scr_va):
    return {'s_ebx': scr_va, 's_flag': scr_va + 4, 's_cnt': scr_va + 8,
            's_ptrs': scr_va + 0x0C, 's_cnt1': scr_va + 0x10}


# ================= A) 回家菜单钩子 (断点 0x4CD563) =================
SRC_HOOK = """
cm_hook:
  mov dword ptr [%(s_ebx)s], ebx
  mov dword ptr [%(s_flag)s], ecx
  mov dword ptr [%(s_cnt)s], edi
  mov dword ptr [%(s_ptrs)s], edx
  inc dword ptr [%(c_menu)s]
  lea esi, [esp + 0x14]
  mov edi, %(menu_code)s
  mov ecx, dword ptr [%(s_cnt)s]
  test ecx, ecx
  je cm_ptr
cm_code_loop:
  mov ax, word ptr [esi]
  mov word ptr [edi], ax
  add esi, 2
  add edi, 2
  dec ecx
  jne cm_code_loop
cm_ptr:
  mov esi, dword ptr [%(s_ptrs)s]
  mov edi, %(menu_ptr)s
  mov ecx, dword ptr [%(s_cnt)s]
  test ecx, ecx
  je cm_append
cm_ptr_loop:
  mov eax, dword ptr [esi]
  mov dword ptr [edi], eax
  add esi, 4
  add edi, 4
  dec ecx
  jne cm_ptr_loop
cm_append:
  # 0x47BED0 arg1 = item count (edx=count, cmp ax,dx as copy bound), arg2 = string ptr array, arg3 = style
  # => last push = arg1 must be ecx(=cnt+1); pushing s_flag(style 2/4) last drew only 2 items, wrong style
  mov eax, dword ptr [%(s_cnt)s]
  lea ecx, [eax + 1]
  mov dword ptr [%(s_cnt1)s], ecx
  shl eax, 2
  mov edx, %(menu_ptr)s
  mov dword ptr [edx + eax], %(str_foster)s
  push dword ptr [%(s_flag)s]
  push edx
  push ecx
  call %(dialog)s
  add esp, 0x14
  cmp ax, -1
  je cm_cancel
  movzx ecx, ax
  cmp cx, word ptr [%(s_cnt)s]
  je cm_foster
  movzx eax, word ptr [ecx * 2 + %(menu_code)s]
  jmp cm_out
cm_foster:
  mov eax, 7
  jmp cm_out
cm_cancel:
  mov eax, -1
cm_out:
  mov ebx, dword ptr [%(s_ebx)s]
  pop edi
  pop esi
  pop ebp
  add esp, 0x24
  ret
"""


# ================= B) 码 7 处理程序: 培养孩子流程 =================
# 帧: push ebx/ebp/esi/edi (收尾原样 pop, 回 0x4CD339 时循环状态与进来时一致) + sub esp,0x38
#   +0x00 L_LORD  主角实体指针 (= 进来的 esi)
#   +0x04 L_CITY  主角 国|城 (实体 +0x24 的 word)
#   +0x08 L_CUR   槽游标 0..CAP
#   +0x0C L_ROWS  本页已收的孩子行数 (< PAGE_KIDS)
#   +0x10 L_ENT   选中孩子实体指针
#   +0x14 L_SLOT  选中孩子槽
#   +0x18 L_ACT / +0x1C L_TEACH / +0x20 L_TIER
#   +0x24 L_CURS  姓名行写指针   +0x28 L_TMP
#   +0x2C L_START 本页起点 = 已跳过多少个同城孩子 (0 基, 每页加 PAGE_KIDS; 不用乘法所以也没有除法)
#   +0x30 L_MATCH 本次扫描累计的同城孩子数 (整池, 不限页) => 有没有下一页就看它
#   +0x34 备用 (导航不靠行号判定: 行号在"只有上一页/只有下一页"时会撞车, 所以把哨兵写进行表)
SRC_FOSTER = """
cm_foster:
  push ebx
  push ebp
  push esi
  push edi
  sub esp, 0x38
  inc dword ptr [%(c_panel)s]
  mov dword ptr [esp + 0x00], esi
  movzx eax, word ptr [esi + 0x24]
  mov dword ptr [esp + 0x04], eax
  # M5b (real-machine report: "after entering a castle and going home the child list is
  #   empty, and it only comes back the next month"): the same-city filter below compares the child's word[+0x24] with the player's, but child_stub.place_child
  #   (live-with-father) only runs from make_child and the MONTHLY rearm -- so right after the player
  #   moves the children still carry the OLD city and the list comes up empty until the next
  #   month hook. child_pass is a fully self-contained, idempotent table loop (it pushes/pops
  #   ebx/esi/edi/ebp itself) whose rearm path ends in place_child, so calling it here makes the
  #   roster always reflect where the fathers are right now.
  call %(child_pass)s
  xor eax, eax
  mov dword ptr [esp + 0x08], eax
  mov dword ptr [esp + 0x0C], eax
  mov dword ptr [esp + 0x2C], eax
  mov dword ptr [esp + 0x30], eax
cm_page:
  mov dword ptr [esp + 0x08], 0
  mov dword ptr [esp + 0x0C], 0
  mov dword ptr [esp + 0x30], 0
cm_scan:
  mov eax, dword ptr [esp + 0x08]
  cmp eax, %(cap)s
  jae cm_scan_end
  inc dword ptr [esp + 0x08]
  mov ecx, eax
  shr ecx, 3
  movzx edx, byte ptr [ecx + %(bm)s]
  and ecx, 7
  bt edx, ecx
  jnc cm_scan
  lea ecx, [eax + eax * 2]
  shl ecx, 4
  sub ecx, eax
  add ecx, %(pool)s
  movzx edx, byte ptr [ecx + 0x2C]
  and dl, 0x0F
  cmp dl, 0xb
  jne cm_scan
  test byte ptr [ecx + 0x2D], 0x80
  jnz cm_scan
  movzx edx, word ptr [ecx + 0x24]
  cmp dx, word ptr [esp + 0x04]
  je cm_same
  inc dword ptr [%(c_notcity)s]
  jmp cm_scan
cm_same:
  mov eax, dword ptr [esp + 0x30]
  cmp eax, dword ptr [esp + 0x2C]
  jb cm_count
  cmp dword ptr [esp + 0x0C], %(page_max)s
  jae cm_count
  mov eax, dword ptr [esp + 0x08]
  dec eax
  mov dword ptr [esp + 0x10], ecx
  mov dword ptr [esp + 0x14], eax
  mov edi, dword ptr [esp + 0x0C]
  lea edx, [edi + edi * 2]
  shl edx, 3
  add edx, %(name_buf)s
  mov dword ptr [esp + 0x24], edx
  mov dword ptr [edi * 4 + %(sub_ptr)s], edx
  movzx eax, word ptr [esp + 0x14]
  mov word ptr [edi * 2 + %(slot_arr)s], ax
  mov edi, edx
  mov esi, eax
  shl esi, 3
  sub esi, eax
  add esi, %(giv)s
  mov ecx, 7
cm_cp_surname:
  mov al, byte ptr [esi]
  mov byte ptr [edi], al
  test al, al
  je cm_cp_surname_end
  inc esi
  inc edi
  dec ecx
  jne cm_cp_surname
cm_cp_surname_end:
  mov byte ptr [edi], 0
  mov eax, dword ptr [esp + 0x14]
  mov esi, eax
  shl esi, 3
  sub esi, eax
  add esi, %(sur)s
  mov ecx, 7
cm_cp_given:
  mov al, byte ptr [esi]
  mov byte ptr [edi], al
  test al, al
  je cm_cp_given_end
  inc esi
  inc edi
  dec ecx
  jne cm_cp_given
cm_cp_given_end:
  mov byte ptr [edi], 0
  mov dword ptr [esp + 0x28], edi
  mov ecx, dword ptr [esp + 0x10]
  call %(age)s
  movzx eax, ax
  cmp eax, %(age_mask)s
  jbe cm_age_ok
  mov eax, %(age_mask)s
cm_age_ok:
  mov esi, %(dec100)s
  add esi, eax
  add esi, eax
  mov edi, dword ptr [esp + 0x28]
  mov al, byte ptr [esi]
  mov byte ptr [edi], 0x20
  mov byte ptr [edi + 1], al
  mov al, byte ptr [esi + 1]
  mov byte ptr [edi + 2], al
  mov esi, %(str_age_suffix)s
  mov ax, word ptr [esi]
  mov word ptr [edi + 3], ax
  mov byte ptr [edi + 5], 0
  inc dword ptr [esp + 0x0C]
cm_count:
  inc dword ptr [esp + 0x30]
  jmp cm_scan
cm_scan_end:
  mov eax, dword ptr [esp + 0x0C]
  test eax, eax
  jne cm_have_rows
  # Nothing scanned at all: this used to return silently, so the player just saw "clicking
  #   does nothing" and could not tell "no child here" from "a gate refused". Paging past the
  #   end (start > 0) stays silent; an empty FIRST page gets an explicit notice.
  cmp dword ptr [esp + 0x2C], 0
  jne cm_exit
  push 0
  push 0
  push 4
  push %(str_none)s
  push 1
  call %(dialog)s
  add esp, 0x14
  jmp cm_exit
cm_have_rows:
  add eax, dword ptr [esp + 0x2C]
  cmp dword ptr [esp + 0x30], eax
  jbe cm_nav_prev
  mov eax, dword ptr [esp + 0x0C]
  mov dword ptr [eax * 4 + %(sub_ptr)s], %(str_next)s
  mov word ptr [eax * 2 + %(slot_arr)s], 0xFFFE
  inc dword ptr [esp + 0x0C]
cm_nav_prev:
  cmp dword ptr [esp + 0x2C], 0
  je cm_show
  mov eax, dword ptr [esp + 0x0C]
  mov dword ptr [eax * 4 + %(sub_ptr)s], %(str_prev)s
  mov word ptr [eax * 2 + %(slot_arr)s], 0xFFFD
  inc dword ptr [esp + 0x0C]
cm_show:
  mov eax, dword ptr [esp + 0x0C]
  mov dword ptr [%(c_rows)s], eax
  mov ecx, %(sub_ptr)s
  push 0
  push 0
  push 4
  push ecx
  push eax
  call %(dialog)s
  add esp, 0x14
  cmp ax, -1
  je cm_exit
  movzx eax, ax
  movzx edx, word ptr [eax * 2 + %(slot_arr)s]
  cmp edx, 0xFFFE
  jne cm_not_next
  inc dword ptr [%(c_nav)s]
  add dword ptr [esp + 0x2C], %(page_max)s
  jmp cm_page
cm_not_next:
  cmp edx, 0xFFFD
  jne cm_kid
  inc dword ptr [%(c_nav)s]
  sub dword ptr [esp + 0x2C], %(page_max)s
  jmp cm_page
cm_kid:
  mov dword ptr [esp + 0x14], edx
  lea ecx, [edx + edx * 2]
  shl ecx, 4
  sub ecx, edx
  add ecx, %(pool)s
  mov dword ptr [esp + 0x10], ecx
  push 0
  push 0
  push 4
  push %(act_ptr)s
  push %(act_n)s
  call %(dialog)s
  add esp, 0x14
  cmp ax, -1
  je cm_exit
  movzx eax, ax
  cmp ax, %(act_last)s
  jae cm_exit
  mov dword ptr [esp + 0x18], eax
  push 0
  push 0
  push 4
  push %(teach_ptr)s
  push %(teach_n)s
  call %(dialog)s
  add esp, 0x14
  cmp ax, -1
  je cm_exit
  movzx eax, ax
  cmp ax, %(teach_last)s
  jae cm_exit
  mov dword ptr [esp + 0x1C], eax
  push 0
  push 0
  push 4
  push %(tier_ptr)s
  push %(tier_n)s
  call %(dialog)s
  add esp, 0x14
  cmp ax, -1
  je cm_exit
  movzx eax, ax
  cmp ax, %(tier_last)s
  jae cm_exit
  mov dword ptr [esp + 0x20], eax
  # ---- M3c-2 kid detail panel: args -> static area, then call (pushad/popad safe) ----
  mov ecx, dword ptr [esp + 0x10]
  mov dword ptr [%(kd_ent)s], ecx
  mov ecx, dword ptr [esp + 0x14]
  mov dword ptr [%(kd_slot)s], ecx
  mov ecx, dword ptr [esp + 0x18]
  mov dword ptr [%(kd_act)s], ecx
  mov ecx, dword ptr [esp + 0x1C]
  mov dword ptr [%(kd_teach)s], ecx
  mov ecx, dword ptr [esp + 0x20]
  mov dword ptr [%(kd_tier)s], ecx
  call %(kd_show)s
  # ====== M5: one per month + gold cost + advance days ======
  # gate 1: already raised this month? ym = (year << 8 | month) + 1; 0 means never
  movzx eax, byte ptr [%(date_y)s]
  shl eax, 0x8
  movzx ecx, byte ptr [%(date_m)s]
  or eax, ecx
  inc eax
  mov ecx, dword ptr [%(f_ym)s]
  cmp eax, ecx
  je cm_g1
  mov dword ptr [%(f_ym)s], eax
  mov dword ptr [%(f_cnt)s], 0
cm_g1:
  cmp dword ptr [%(f_cnt)s], %(mcap)s
  jae cm_deny_month
  # gate 2: days = ACT_DAYS[act]; need DATE_D + days <= 0x1e (0x1f rolls month -> month hook)
  mov ecx, dword ptr [%(kd_act)s]
  movzx edx, byte ptr [ecx + %(act_days)s]
  mov dword ptr [%(f_days)s], edx
  movzx eax, byte ptr [%(date_d)s]
  add eax, edx
  cmp eax, %(day_max)s
  ja cm_deny_time
  # gate 3: gold = days * GOLD_PER_DAY (pay uses sat_sub, no balance check -> compare first)
  imul edx, edx, %(gold_per_day)s
  mov dword ptr [%(f_gold)s], edx
  movzx eax, word ptr [%(gold_ptr)s]
  cmp eax, edx
  jb cm_deny_gold
  # confirm dialog: 3 rows -- [0] cost line (days/gold for this activity),
  #   [1] "go ahead", [2] "think again".  Only picking row 1 really commits;
  #   row 0 (the cost line), row 2 and cancel (0xffff) all mean "give up".
  #   The pointer array is assembled here into a 3-slot scratch in the FOSTER area.
  mov ecx, dword ptr [%(kd_act)s]
  imul eax, ecx, %(ms_row)s
  add eax, %(cost0)s
  mov dword ptr [%(cost_arr)s], eax
  mov dword ptr [%(cost_arr)s + 4], %(ok_str)s
  mov dword ptr [%(cost_arr)s + 8], %(cancel_str)s
  push 0
  push 0
  push 4
  push %(cost_arr)s
  push 3
  call %(dialog)s
  add esp, 0x14
  cmp ax, 1
  jne cm_exit
  # pay
  push dword ptr [%(f_gold)s]
  call %(pay)s
  add esp, 4
  # ---- M5b: book this month + show the child's line NOW, before the clock moves ----
  #   Order matters to the player: 0x4A0D50 fires the game's own daily events, so when the
  #   day advance came first the user saw a daimyo's messenger dialog and only THEN the
  #   child's line. Speak first, then let time pass.
  inc dword ptr [%(f_cnt)s]
  mov eax, dword ptr [%(kd_act)s]
  mov dword ptr [%(msg_act)s], eax
  mov eax, dword ptr [%(kd_slot)s]
  mov dword ptr [%(msg_slot)s], eax
  call %(kd_msg)s
  # advance days: 0x4A0D50 is **cdecl** -- the caller must pop the 2 args;
  #   (native sites all do `push 1; push 0x18; call 0x4A0D50; add esp,8`).
  #   Forgetting the add esp,8 here made `pop ecx` reload the stray arg 0x18
  #   every pass => the loop never ended and the date ran away forever.
  mov ecx, dword ptr [%(f_days)s]
  test ecx, ecx
  je cm_day_done                     # never enter the loop with 0 days (dec would wrap to 4G)
cm_day_l:
  push ecx                           # the callee does not preserve ecx
  push 1
  push %(adv_hours)s
  call %(adv_day)s
  add esp, 0x8
  pop ecx
  dec ecx
  jne cm_day_l
cm_day_done:
  mov eax, dword ptr [%(ring_tail)s]
  and eax, 0x3F
  shl eax, 3
  add eax, %(ring_ents)s
  movzx ecx, word ptr [esp + 0x14]
  mov word ptr [eax], cx
  mov ecx, dword ptr [esp + 0x18]
  mov byte ptr [eax + 1], cl
  mov ecx, dword ptr [esp + 0x1C]
  mov byte ptr [eax + 2], cl
  mov ecx, dword ptr [esp + 0x20]
  mov byte ptr [eax + 3], cl
  mov word ptr [eax + 4], 0
  mov word ptr [eax + 6], 0
  mov ecx, dword ptr [%(ring_tail)s]
  inc ecx
  mov dword ptr [%(ring_tail)s], ecx
  inc dword ptr [%(c_push)s]
  movzx ecx, word ptr [esp + 0x14]
  mov dword ptr [%(last_slot)s], ecx
  mov ecx, dword ptr [esp + 0x18]
  mov dword ptr [%(last_act)s], ecx
  jmp cm_exit
  # ---- M5 deny: single button notice box (same 0x47BED0 convention) ----
cm_deny_month:
  push 0
  push 0
  push 4
  push %(deny_month_ptr)s
  push 1
  call %(dialog)s
  add esp, 0x14
  jmp cm_exit
cm_deny_time:
  push 0
  push 0
  push 4
  push %(deny_time_ptr)s
  push 1
  call %(dialog)s
  add esp, 0x14
  jmp cm_exit
cm_deny_gold:
  push 0
  push 0
  push 4
  push %(deny_gold_ptr)s
  push 1
  call %(dialog)s
  add esp, 0x14
cm_exit:
  add esp, 0x38
  pop edi
  pop esi
  pop ebp
  pop ebx
  jmp %(menu_top)s
"""


def lint_src(src):
    """keystone 陷阱: 源里裸写的多位十进制立即数会按十六进制吃进去 => 一律 0x 前缀。
    另外 keystore 源必须 ASCII (中文注释会 UnicodeEncodeError)。"""
    import re
    bad = [(m.group(0), src[:m.start()].count('\n') + 1)
           for m in re.finditer(r'(?<![0-9a-fA-Fx,.])\d{2,}(?![0-9a-fA-F])', src)]
    assert not bad, 'SRC 有未加 0x 的立即数(会被当十六进制): %s' % bad[:8]
    nonascii = [c for c in src if ord(c) > 0x7F]
    assert not nonascii, 'SRC 含非 ASCII 字符(keystone 会炸): %r' % nonascii[:8]


def _hexsubs(L):
    """L 的值给成 0x 字符串 (int 直接 %s 会变成十进制, 十进制又会被 keystone 当十六进制吃)"""
    return {k: ('0x%X' % v if isinstance(v, int) else v) for k, v in L.items()}


def build_hook(hook_va, L):
    """A) 回家菜单钩子。L 需含 menu_ptr/menu_code/str_va/s_*/c_menu。返回 (code, ins)。"""
    from keystone import Ks, KS_ARCH_X86, KS_MODE_32, KS_OPT_SYNTAX_INTEL
    subs = _hexsubs(L)
    subs['dialog'] = '0x%X' % DIALOG
    subs['str_foster'] = '0x%X' % (L['str_va'] + S_HOME * STR_ROW)
    src = SRC_HOOK % subs
    lint_src(src)
    ks = Ks(KS_ARCH_X86, KS_MODE_32)
    ks.syntax = KS_OPT_SYNTAX_INTEL
    code = bytes(ks.asm(src, hook_va)[0])
    return code, src


def build_foster(foster_va, L):
    from keystone import Ks, KS_ARCH_X86, KS_MODE_32, KS_OPT_SYNTAX_INTEL
    subs = _hexsubs(L)
    subs['ring_tail'] = '0x%X' % (L['ring'] + CG.RING_TAIL_OFF)
    subs['ring_ents'] = '0x%X' % (L['ring'] + CG.RING_ENTS_OFF)
    subs.update({'dialog': '0x%X' % DIALOG, 'age': '0x%X' % AGE_GET,
                 'menu_top': '0x%X' % MENU_TOP,
                 'cap': '0x%X' % L['cap'],
                 'page_max': '0x%X' % PAGE_KIDS,
                 'str_next': '0x%X' % (L['str_va'] + S_NEXT * STR_ROW),
                 'str_prev': '0x%X' % (L['str_va'] + S_PREV * STR_ROW),
                 'age_mask': '0x%X' % AGE_GET_MASK,
                 'str_age_suffix': '0x%X' % (L['str_va'] + S_AGE_SUFFIX * STR_ROW),
                 # 活动/教席/档次子菜单: 项数 = 表长 + 1(暂不培养); 选中"暂不培养"的下标 = 表长
                 'act_n': '0x%X' % (len(CG.ACTS) + 1), 'act_last': '0x%X' % len(CG.ACTS),
                 'teach_n': '0x%X' % (len(CG.TEACHERS) + 1), 'teach_last': '0x%X' % len(CG.TEACHERS),
                 'tier_n': '0x%X' % (len(TIER_NAMES) + 1), 'tier_last': '0x%X' % len(TIER_NAMES),
                 # M3c-2 培养详情面板: 参数静态区 + 入口 (面板自己 pushad/popad)
                 'kd_ent': '0x%X' % L['kd_ent'], 'kd_slot': '0x%X' % L['kd_slot'],
                 'kd_act': '0x%X' % L['kd_act'], 'kd_teach': '0x%X' % L['kd_teach'],
                 'kd_tier': '0x%X' % L['kd_tier'], 'kd_show': '0x%X' % L['kd_show'],
                 # ---- M5: 节奏/花费 ----
                 # M5b: 菜单打开时复跑一遍孩子预载桩, 把孩子「所在城」同步成父亲当前城
                 'child_pass': '0x%X' % L['child_pass'],
                 'date_y': '0x%X' % CG.DATE_Y, 'date_m': '0x%X' % CG.DATE_M,
                 'date_d': '0x%X' % CG.DATE_D,
                 'f_ym': '0x%X' % L['f_ym'], 'f_cnt': '0x%X' % L['f_cnt'],
                 'f_days': '0x%X' % L['f_days'], 'f_gold': '0x%X' % L['f_gold'],
                 'msg_act': '0x%X' % L['msg_act'], 'msg_slot': '0x%X' % L['msg_slot'],
                 'act_days': '0x%X' % L['act_days'],
                 'mcap': '0x%X' % CG.MONTHLY_CAP, 'day_max': '0x%X' % CG.DAY_MAX,
                 'gold_per_day': '0x%X' % CG.GOLD_PER_DAY, 'gold_ptr': '0x%X' % CG.GOLD_PTR,
                 'pay': '0x%X' % CG.PAY, 'adv_day': '0x%X' % CG.ADVANCE_DAY,
                 'adv_hours': '0x%X' % CG.ADVANCE_HOURS,
                 # 费用提示: cost0 = 池首 + MS_COST0*行宽, 行地址 = cost0 + act*行宽
                 #          三行指针数组落 FOSTER 区尾部的 12B 暂存 (运行时拼)
                 'ms_row': '0x%X' % MS_STR_ROW,
                 'cost0': '0x%X' % (L['msg_str'] + MS_COST0 * MS_STR_ROW),
                 'cost_arr': '0x%X' % L['cost_arr'],
                 'ok_str': '0x%X' % (L['msg_str'] + MS_OK * MS_STR_ROW),
                 'cancel_str': '0x%X' % (L['msg_str'] + MS_CANCEL * MS_STR_ROW),
                 'confirm_ptr': '0x%X' % L['confirm_ptr'],
                 # 一个孩子都没扫到时的明说 (静默 return 会让"点了没反应"无法诊断)
                 'str_none': '0x%X' % (L['msg_str'] + MS_NONE * MS_STR_ROW),
                 'deny_month_ptr': '0x%X' % L['deny_month_ptr'],
                 'deny_time_ptr': '0x%X' % L['deny_time_ptr'],
                 'deny_gold_ptr': '0x%X' % L['deny_gold_ptr'],
                 'kd_msg': '0x%X' % L['kd_msg']})
    src = SRC_FOSTER % subs
    lint_src(src)
    ks = Ks(KS_ARCH_X86, KS_MODE_32)
    ks.syntax = KS_OPT_SYNTAX_INTEL
    code = bytes(ks.asm(src, foster_va)[0])
    return code, src


def jmp_rel(site, target):
    """5 字节 E9 rel32 补丁 (构建与验收同一算法, 防止两边算歪)"""
    import struct
    return b'\xE9' + struct.pack('<i', target - (site + 5))


# ================= 回读自检 =================
def _dis(code, origin):
    from capstone import Cs, CS_ARCH_X86, CS_MODE_32
    ins = list(Cs(CS_ARCH_X86, CS_MODE_32).disasm(code, origin))
    assert ins and sum(len(i.bytes) for i in ins) == len(code), '反汇编未覆盖全部字节'
    return ins


def _mk(ins):
    def one(mn, *pats):
        got = [i for i in ins if i.mnemonic == mn and all(p in i.op_str for p in pats)]
        assert len(got) == 1, ('应恰 1 条: %s %s (命中 %d)' % (mn, pats, len(got)))
        return got[0]

    def cnt(mn, *pats):
        return len([i for i in ins if i.mnemonic == mn and all(p in i.op_str for p in pats)])

    def cntx(mn, exact):
        return len([i for i in ins if i.mnemonic == mn and i.op_str == exact])
    return one, cnt, cntx


def selfcheck_hook(code, origin, L):
    ins = _dis(code, origin)
    one, cnt, cntx = _mk(ins)
    dl = '0x%x' % DIALOG
    one('call', dl)
    # 0x47BED0 实机约定: arg1 = 条目数 / arg2 = 串指针数组 / arg3 = 样式 (见 0x47BED0 入口
    #   mov edx,[esp+4] + test dx,dx + cmp ax,dx)。末推 = arg1, 必须是 ecx(=cnt+1);
    #   把 s_flag(样式) 推在末位会让菜单只画 2 项且样式参数错 (2026-10-06 实机卡死根因)。
    _ci = [i for i in ins if i.mnemonic == 'call' and i.op_str == dl][0]
    _j = ins.index(_ci)
    _pre = [(x.mnemonic, x.op_str) for x in ins[_j - 3:_j]]
    assert _pre == [('push', 'dword ptr [0x%x]' % L['s_flag']), ('push', 'edx'), ('push', 'ecx')], \
        '对话框实参顺序必须是 (样式, 指针数组, 条目数): 末推=arg1=条目数, 现在是 %s' % (_pre,)
    assert cnt('add', 'esp, 0x14') == 1, '只调一次对话框'
    one('cmp', 'ax, -1')
    one('cmp', 'cx, word ptr [0x%x]' % L['s_cnt'])
    one('movzx', 'eax, word ptr [ecx*2 + 0x%x]' % L['menu_code'])   # 序号 -> 原生指令码
    one('mov', 'eax, 7')
    one('mov', 'eax, 0xffffffff')   # capstone 把 -1 打成 0xffffffff
    one('inc', 'dword ptr [0x%x]' % L['c_menu'])
    assert cnt('dec', 'ecx') == 2, '码表 + 指针数组两份拷贝循环'
    one('mov', 'dword ptr [edx + eax], 0x%x' % (L['str_va'] + S_HOME * STR_ROW))  # 尾追"培养孩子"
    # 收尾必须与原生 0x4CD581..0x4CD58C 同构 (pop edi/esi/ebp + add esp,0x24 + ret), 且不能碰原生翻译那条
    tail = ins[-5:]
    assert [i.mnemonic for i in tail] == ['pop', 'pop', 'pop', 'add', 'ret'], [i.mnemonic for i in tail]
    assert [i.op_str for i in tail[:3]] == ['edi', 'esi', 'ebp'], [i.op_str for i in tail[:3]]
    assert tail[3].op_str == 'esp, 0x24'
    assert cnt('ret') == 1 and cnt('mov', 'ax, word ptr [esp + eax*2 + 4]') == 0, '不得复用原生序号翻译'
    for k in ('s_ebx', 's_flag', 's_cnt', 's_ptrs', 's_cnt1'):
        assert cnt('mov', 'dword ptr [0x%x]' % L[k]) >= 1, k
    one('mov', 'ebx, dword ptr [0x%x]' % L['s_ebx'])
    return ins


def selfcheck_foster(code, origin, L):
    ins = _dis(code, origin)
    one, cnt, cntx = _mk(ins)
    dl = '0x%x' % DIALOG
    # 4 次选项 + 1 次确认 + 3 次门禁拒绝 + 1 次「此城没有可培养的孩子」 = 9 次原生对话框 (M5/M5b)
    assert cnt('call', dl) == 9, '四次选项 + 确认 + 三个拒绝 + 空名单 = 9 次原生对话框 (命中 %d)' % cnt('call', dl)
    assert cnt('add', 'esp, 0x14') == 9
    assert cntx('push', '4') == 9, '选项子菜单一律 flag=4 (实测 0x445758/0x412E64)'
    assert cntx('push', '0') == 18, '每次两枚 0 尾参'
    one('call', '0x%x' % AGE_GET)
    assert cnt('sub', 'esp, 0x38') == 1 and cnt('add', 'esp, 0x38') == 1
    head = ins[:4]
    assert [i.op_str for i in head] == ['ebx', 'ebp', 'esi', 'edi'], [i.op_str for i in head]
    tail = ins[-6:]
    assert [i.mnemonic for i in tail] == ['add', 'pop', 'pop', 'pop', 'pop', 'jmp'], [i.mnemonic for i in tail]
    assert [i.op_str for i in tail[1:5]] == ['edi', 'esi', 'ebp', 'ebx']
    assert tail[5].op_str == '0x%x' % MENU_TOP, '完事回菜单头'
    assert cnt('jmp', '0x%x' % MENU_EXIT) == 0, '不直接退出回家菜单'
    # 扫描门: 位图 / 儿童态 nibble / 在场位 / 同城 / 每页上限
    one('bt', 'edx, ecx')
    one('movzx', 'edx, byte ptr [ecx + 0x%x]' % L['bm'])
    one('cmp', 'dl, 0xb')
    one('test', 'byte ptr [ecx + 0x2d], 0x80')
    one('cmp', 'dx, word ptr [esp + 4]')
    one('cmp', 'dword ptr [esp + 0xc], %s' % cap_imm(PAGE_KIDS))
    one('inc', 'dword ptr [0x%x]' % L['c_notcity'])
    one('inc', 'dword ptr [0x%x]' % L['c_panel'])
    one('inc', 'dword ptr [0x%x]' % L['c_push'])
    one('mov', 'dword ptr [0x%x]' % L['last_slot'])
    one('mov', 'dword ptr [0x%x]' % L['last_act'])
    # 姓名拼装: 两段 7B 上限拷贝 + " NN岁"
    assert cnt('mov', 'ecx, 7') == 2, '姓/名各一条有界拷贝'
    assert cnt('dec', 'ecx') == 3, '两条名字拷贝 + M5 推天数循环'
    one('mov', 'byte ptr [edi], 0x20')
    one('mov', 'esi, 0x%x' % L['dec100'])
    one('mov', 'eax, 0x63')
    assert cnt('add', 'esi, eax') == 2, 'DEC100 + age*2'
    # 指令入队 (分工: UI 只写 tail, head 归成长桩)
    one('and', 'eax, 0x3f')
    one('mov', 'word ptr [eax], cx')
    one('mov', 'word ptr [eax + 4], 0')
    one('mov', 'word ptr [eax + 6], 0')
    _ld = one('mov', 'ecx, dword ptr [0x%x]' % (L['ring'] + 4))   # tail 读-改-写 (UI 只碰 tail)
    _i = ins.index(_ld)
    assert [_x.mnemonic for _x in ins[_i + 1:_i + 3]] == ['inc', 'mov'], ins[_i + 1:_i + 3]
    assert ins[_i + 2].op_str == 'dword ptr [0x%x], ecx' % (L['ring'] + 4)
    assert cnt('mov', 'dword ptr [0x%x]' % L['ring']) == 0, 'UI 不得写 head'
    # 三级子菜单的"暂不培养"下标 = 各表长
    for n in (len(CG.ACTS), len(CG.TEACHERS), len(TIER_NAMES)):
        one('cmp', 'ax, %s' % (('%d' % n) if n < 10 else ('0x%x' % n)))   # capstone: <10 打十进制
    # 分页导航: 哨兵写进行表 + 靠哨兵(不是行号)分派 => "只有上一页/只有下一页"也不会走歪
    sa = 'word ptr [eax*2 + 0x%x]' % L['slot_arr']
    one('mov', sa, '0xfffe')
    one('mov', sa, '0xfffd')
    one('movzx', 'edx, ' + sa)
    one('cmp', 'edx, 0xfffe')
    one('cmp', 'edx, 0xfffd')
    one('add', 'dword ptr [esp + 0x2c], %s' % cap_imm(PAGE_KIDS))
    one('sub', 'dword ptr [esp + 0x2c], %s' % cap_imm(PAGE_KIDS))
    # 两个导航分支都跳回"重开一页"(cm_page: 把行表/计数清零的那条), 且只跳这两次
    pg = [i for i in ins if i.mnemonic == 'mov' and i.op_str == 'dword ptr [esp + 8], 0']
    assert len(pg) == 1, 'cm_page 复位点应唯一 (命中 %d)' % len(pg)
    assert cnt('jmp', '0x%x' % pg[0].address) == 2, '下一页/上一页各回一次页首'
    for mn in ('add', 'sub'):
        k = [j for j, i in enumerate(ins) if i.mnemonic == mn and 'esp + 0x2c], ' + cap_imm(PAGE_KIDS) in i.op_str][0]
        assert ins[k + 1].mnemonic == 'jmp' and ins[k + 1].op_str == '0x%x' % pg[0].address
    assert cnt('mov', 'dword ptr [esp + 0x34]') == 0, '导航不写行号 (行号在单侧导航时会撞车)'
    # M3c-2: 选完四级的参数落静态区 + call 详情面板 (写参必须在 call 之前, 且一次)
    one('call', '0x%x' % L['kd_show'])
    for nm, k in (('ent', 'kd_ent'), ('slot', 'kd_slot'), ('act', 'kd_act'),
                  ('teach', 'kd_teach'), ('tier', 'kd_tier')):
        # ★ 模式里必须带 ", ecx": M5 之后的反馈小框参数搬运也读同一批地址
        #   (`mov eax, dword ptr [kd_slot]`), 只用 "dword ptr [addr]" 会命中两条。
        st = one('mov', 'dword ptr [0x%x], ecx' % L[k])
        assert st.op_str == 'dword ptr [0x%x], ecx' % L[k], (nm, st.op_str)
    _kc = ins.index(one('call', '0x%x' % L['kd_show']))
    for k in ('kd_ent', 'kd_slot', 'kd_act', 'kd_teach', 'kd_tier'):
        assert any(i.op_str == 'dword ptr [0x%x], ecx' % L[k] for i in ins[:_kc]), \
            '面板参数 %s 必须在 call 之前写好' % k
    # 分页扫到的"槽"必须是真槽: 游标在 cm_scan 里已 inc, 取回要 dec。
    # ★ 这里踩过坑: cm_same 开头一句 `mov eax,[esp+0x30]`(累计匹配数)把 eax 冲掉了,
    #   于是 slot_arr 存的是"第几个匹配"而不是槽 => 姓名表按它取会取到别人的名字,
    #   选中的实体也算错。现在在写 [esp+0x14] 之前补 `mov eax,[esp+8]; dec eax` 取回真槽。
    assert cnt('mov', 'eax, dword ptr [esp + 8]') == 2, '扫描头一处 + 取回真槽一处'
    assert cnt('dec', 'eax') == 1, '取回真槽的 dec'
    # 分页埋点: 翻页计数在两条分支各一次; 行数读数落在弹窗口令之前 (取最大值, 不是求和)
    assert cnt('inc', 'dword ptr [0x%x]' % L['c_nav']) == 2, '下一页/上一页各计一次 PAGE_NAV'
    _rw = one('mov', 'dword ptr [0x%x], eax' % L['c_rows'])
    assert ins[ins.index(_rw) + 1].op_str == 'ecx, 0x%x' % L['sub_ptr'], 'PAGE_ROWS 必须写在 push 行数之前'
    # ---- M5: 每月 1 次门 / 天数门 / 金门 / 扣金 / 推天数 / 反馈 ----
    # ym = (年<<8|月)+1: 换月才把计数归零, 0 专门留给"本进程从未培养"
    one('shl', 'eax, 8')
    one('or', 'eax, ecx')
    one('inc', 'eax')
    one('mov', 'ecx, dword ptr [0x%x]' % L['f_ym'])
    one('mov', 'dword ptr [0x%x], 0' % L['f_cnt'])
    one('cmp', 'dword ptr [0x%x], 1' % L['f_cnt'])
    one('movzx', 'edx, byte ptr [ecx + 0x%x]' % L['act_days'])
    one('mov', 'dword ptr [0x%x], edx' % L['f_days'])
    one('movzx', 'eax, byte ptr [0x5205f2]')
    one('imul', 'edx, edx, %d' % CG.GOLD_PER_DAY)
    one('mov', 'dword ptr [0x%x], edx' % L['f_gold'])
    one('movzx', 'eax, word ptr [0x%x]' % CG.GOLD_PTR)
    one('add', 'eax, edx')
    one('call', '0x%x' % CG.PAY)
    one('call', '0x%x' % CG.ADVANCE_DAY)
    one('call', '0x%x' % L['kd_msg'])
    # ★★ M5b 事故 (2026-10-07 实机): "每次进城回家, 点培养孩子就不行了, 非要等下一个月"。
    #   根因: 名单按「孩子所在城 == 主角所在城」筛, 而孩子的城只在 child_pass 里随父亲
    #   同步 (make_child / 月钩 rearm) => 主角一移动, 孩子还挂在上一个城, 名单空到下次月钩。
    #   child_pass 自包含且幂等 (自己 push/pop ebx/esi/edi/ebp, 无实参), 所以在扫名单前补跑一次。
    _cp = one('call', '0x%x' % L['child_pass'])
    assert ins.index(_cp) < ins.index(one('call', '0x%x' % L['kd_show'])), \
        'child_pass 必须在扫名单/弹菜单之前跑 (它负责把孩子搬到父亲当前城)'
    # ★★ M5b 顺序: 反馈框必须在推天数之前 —— 0x4A0D50 会触发原生每日事件 (使者/访问),
    #   原来是"先推天数再弹台词", 玩家看到的是"大名的对话后, 孩子才出现"。
    assert ins.index(one('call', '0x%x' % L['kd_msg'])) \
        < ins.index(one('call', '0x%x' % CG.ADVANCE_DAY)), \
        '孩子台词必须在日期推进之前弹出 (否则会被原生每日事件的对话挤到后面)'
    assert cntx('push', '1') == 5, '推天数 1 + 三个拒绝框 + 空名单 1 (命中 %d)' % cntx('push', '1')
    assert cnt('inc', 'dword ptr [0x%x]' % L['f_cnt']) == 1, '只在这一个月+1 处落账'
    _g0 = cntx('test', 'ecx, ecx')
    assert _g0 == 1, '天数 0 的守卫应恰 1 处 (命中 %d)' % _g0
    # ★★ 0x4A0D50 是 cdecl: 调用方必须紧跟 add esp,8 清两枚实参。
    #    漏掉它 => `pop ecx` 每次捡回残留实参 0x18, 循环永不结束, 日期一路狂奔 (2026-10-07 实机症状)。
    _adv = ins.index(one('call', '0x%x' % CG.ADVANCE_DAY))
    assert ins[_adv + 1].mnemonic == 'add' and ins[_adv + 1].op_str == 'esp, 8', \
        '推天数必须紧跟 add esp,8 (实得 %s %s)' % (ins[_adv + 1].mnemonic, ins[_adv + 1].op_str)
    assert cntx('add', 'esp, 8') == 1, '只这一处 cdecl 调用'
    _pp = ins.index(one('pop', 'ecx'))
    assert _adv < _pp, '先清参数再 pop 计数'
    # 费用提示: [cost0 + act*行宽] 落三槽指针数组 -> 3 项确认框, 只有 ax==1 才真办
    _rw24 = ('%d' % MS_STR_ROW) if MS_STR_ROW < 10 else ('0x%x' % MS_STR_ROW)
    one('imul', 'eax, ecx, %s' % _rw24)
    one('add', 'eax, 0x%x' % (L['msg_str'] + MS_COST0 * MS_STR_ROW))
    # ★ keystone 会把 [base + 4] 折进绝对地址 => 回读是三条相邻地址, `[0x... + 4]` 这种写法对不上
    one('mov', 'dword ptr [0x%x], eax' % L['cost_arr'])
    one('mov', 'dword ptr [0x%x], 0x%x' % (L['cost_arr'] + 4,
                                           L['msg_str'] + MS_OK * MS_STR_ROW))
    one('mov', 'dword ptr [0x%x], 0x%x' % (L['cost_arr'] + 8,
                                           L['msg_str'] + MS_CANCEL * MS_STR_ROW))
    assert cntx('push', '3') == 1, '确认框是 3 项 (费用行 + 就这么办 + 再想想)'
    one('cmp', 'ax, 1')
    assert ins[ins.index(one('cmp', 'ax, 1')) + 1].mnemonic == 'jne', '只有选 1 才继续'
    # 反馈: 活动码/槽号先落静态区, 再 call kd_msg (面板与反馈框共用静态区约定)
    one('mov', 'dword ptr [0x%x], eax' % L['msg_act'])
    for k in ('f_ym', 'f_cnt', 'f_days', 'f_gold', 'msg_act', 'msg_slot'):
        assert L[k] > 0, k
    return ins

