# -*- coding: utf-8 -*-
"""
build_big.py —— P1「实体池搬家」: 从 TAIK2W95_family.exe 派生 TAIK2W95_big.exe
  * 新增 RW 节 .edata @RVA 0x13C000 (VA 0x53C000): 实体池新家 (容量 = 顶部 CAP, 布局全自动推导)
  * 把代码/静态表中所有指向旧池 [0x519868,0x51DC56) 的 4 字节 LE 字段(imm32/disp32)
    重定位到 0x53C000+同偏移; 0x51DC56(池尾界) → 0x53C000+47*370
  * 370 边界常数(0x172)一律不动 —— 本步纯搬家, 行为应逐位相同
  * 防误伤: 只改「白名单访存指令的完整 4 字节操作数字段」; j*/call 的 rel32 自动排除
  验证: 重建后全节复扫, 旧池区间字段引用应为 0; 逐点清单 -> _big_reloc.json

★ 2026-10-07 事故簿 (四条都已回填本文件, 产物不再需要任何事后 byte patch):
  1) P2 曾把 .text 里 **所有** 0x172 放大到 CAP —— 但 0x49C5E5/0x49CD3D 是**栈局部数组**的
     memset 长度, 栈帧只有 370B, 放大到 1024 会踩穿返回地址 => 进大地图后 EIP=0。
     => 现由 STACK_MEMSET_SITES 黑名单保留。
  2) child_growth 里 debug_log 是 stdcall(ret 4), 4 个调用点中 3 个在 call 后还 add esp,4,
     每次多清 4B => ESP 逐次漂移 => 月边界必崩。=> 源码已删那 3 条 add esp,4。
  3) 5 个纯诊断 trampoline (D/E/F/G/H) 默认关闭 (TKID_DBG_TRAMP=1 才装), 它们占掉
     0x4A0D50/0x4F44B0 等的头 5 字节, 实测就是"进大地图必崩"的直接来源。
  4) 它们的**本体**原本堆在 KD_CODE_VA + 0x500, 而培养面板 kd_* 五段实际要 1626B(0x65A)
     —— 尾部被覆盖 => 点「培养」执行到 kd_row 半截指令必 AV。
     => KD_CODE 配额 0x500 -> KD_CODE_SZ=0x700, tramp 本体跟着搬出去。
  回归: python .rev/verify_final.py TAIK2W95_big.exe   (11 项 / 期望 0 FAIL)
"""
import struct, json, os, sys, time
import pefile
from capstone import Cs, CS_ARCH_X86, CS_MODE_32
from capstone.x86 import X86_OP_IMM, X86_OP_MEM
import child_save as SV            # M6: 只用它的 SC_CTRS(埋点表) + 桩装配/格式常量
import child_growth as CG
import child_menu as CM            # M3c/M5: 回家菜单 + 门禁/花费/反馈 (串池尺寸由它定义)

# 控制台默认 GBK, 打印里的 ✓/中文会触发 UnicodeEncodeError -> 在写盘前崩, big.exe 不更新。
try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

SRC = r'F:\Games\Taikou 2\Taikou2 Original\TAIK2W95_family.exe'
# TKID_DST: 构建产物改名(分页试演档 = ..\TAIK2W95_big_p2.exe), 相对路径按 .rev 的上一级解析;
#   不设就是正式档 TAIK2W95_big.exe。注意 _big_layout.json 永远只有一份, 谁最后构建谁说话
#   —— 试演档验收要紧接着它的构建跑(见 mk_page2.bat), 最后一步必须重建正式档。
DST = os.environ.get('TKID_DST') or r'F:\Games\Taikou 2\Taikou2 Original\TAIK2W95_big.exe'
if not os.path.isabs(DST):
    DST = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), DST))

IMAGE_BASE = 0x400000
LO, STRIDE, N0 = 0x519868, 47, 370
HI = LO + STRIDE * N0                 # 0x51DC56 = 旧池尾/旧界
NEW = 0x53C000                        # 新池基址 (RVA 0x13C000)
NEW_RVA, NEW_PTR = 0x13C000, None

# ---------- 容量档 (改这一行就是换容量; 全部 .edata 布局由它推导, 无手写地址) ----------
#   代价表: 每槽 47B 实体 + 7B 姓 + 7B 名 = 61B, .edata 还要留 1KB MOD 私有区。
#     CAP  512 -> .edata 0x08000 (32KB)   CAP 1024 -> 0x12000 (72KB)
#     CAP 2048 -> .edata 0x22000 (136KB)  CAP 4096 -> 0x42000 (264KB)
#   槽号在引擎里全程走 word(原版 370>255 已证), 上限 65535; 真正的天花板是
#   BSDATA 的 700 条档案 oid(要突破须做 VBSD 镜像, 见 PLAN_CHILD_PRELOAD.md 的 L2 层)。
CAP = 1024                            # 在场槽总数 (0..CAP-1); 0..369 = 原生存档区, 370+ = MOD 区
assert N0 < CAP <= 0xFFFF, '容量必须是 (370, 65535] 且能塞进 imm16 界检'


def _align(v, a):
    return (v + a - 1) // a * a


POOL_SZ = STRIDE * CAP                      # 实体池字节
# 姓名表极性(实测, 别信变量名): 原 0x520660 = **名表**, 原 0x521AA8 = **姓表**。
#   证据: INST 0x47F7B0 先 lea ebx,[slot*7+0x521aa8] 再 lea esi,[slot*7+0x520660],
#         而游标指向 BSDATA 记录首字节 = 姓(rec[0:7]), 故第一张(0x521AA8)收姓;
#         fam_sim.py / build_familytree.py 早已按此写 (SUR_BASE 放 giv, GIV_BASE 放 sur)。
#   本节 SUR_OFF/GIV_OFF 沿用老脚本的**反**命名(0x520660->SUR_*, 0x521AA8->GIV_*),
#   以保持既有地址口径不变; 真正放姓的是 GIV_*, 写姓名时必须按此配对。
SUR_OFF = _align(POOL_SZ, 0x100)            # = 原 0x520660 -> 实为 **名表** (CAP×7)
GIV_OFF = _align(SUR_OFF + 7 * CAP, 0x100)  # = 原 0x521AA8 -> 实为 **姓表** (CAP×7)
MOD_OFF = _align(GIV_OFF + 7 * CAP + 0x200, 0x100)   # MOD 私有区(桩/钩子/埋点/位图/排程表/预载桩)
MOD_SZ = 0xA000                   # 私有区配额 (v13 动态族谱起 40KB): 埋点 0xC0 | 儿童位图 0x100(CAP bit)
                                  #   | 排程表 0x180..0x1200(8B/条, <=527) | 预载桩 0x1200..
                                  #   | 成长桩 0x1400.. | 成长埋点 0x2000.. | KID_TAB 0x2100(CAP*12)
                                  #   | CMD_RING 其后 544B | 回家菜单数组 再其后
                                  #   | M6 影子存档桩 0x6100.. | 影子存档数据区 0x6700..0x6840
                                  # 注: `.edata` 是本 PE **最后一节**且 Raw==Virt==整节零填充,
                                  #     抬 MOD_SZ = 纯加长文件尾, 所有 M() 地址自动重推 (R8)。
NEW_SZ = _align(MOD_OFF + MOD_SZ, 0x1000)    # 节大小 (换 CAP 自动长)

# MOD 私有区内偏移(相对 NEW+MOD_OFF) —— 与 CAP=512 时的手写地址逐位相同(0x543C00 起),
#   这样换容量档只平移整块, 老脚本/老存档判读口径不变。唯一真源, 落地写 _big_layout.json。
M = lambda o: NEW + MOD_OFF + o
MOD_SLOT_VA, MOD_STUB_VA = M(0x00), M(0x10)   # MCI 私有指针槽 + mciSendCommandA 桩
BGM_CNT_VA = M(0x40)
APPEAR_CNT_VA, VACANT_CNT_VA = M(0x48), M(0x4C)    # 登场人次 / 空槽遭遇
MONTH_CNT_VA, ARMED_CNT_VA = M(0x50), M(0x54)      # 例程执行次数(=月) / 武装槽次数
APPEAR_STUB_VA, EQ_STUB_VA = M(0x60), M(0x80)
# 儿童预载 (M2): 埋点 -> 位图 -> 排程表 -> 桩代码, 全在 MOD 私有区内, 换 CAP 自动重算
CHILD_PRELOAD_VA, CHILD_REARM_VA = M(0xC0), M(0xC4)      # 实例化人次 / 复臂人次
CHILD_GENPUKU_VA, CHILD_SCAN_VA = M(0xC8), M(0xCC)       # 元服人次(M4) / 主循环趟数
CHILD_SKIP_VA = M(0xD0)                                  # 撞到别人占的槽 (应为 0)
CHILD_PLACE_VA = M(0xD4)                                 # 随父居住写城人次 (M3a; 动态/静态两条路都计)
CHILD_INIT5_VA = M(0xD8)                                 # init_stats 次数 (M3b-2; 应恒等于 CHILD_PRELOAD)
CHILD_BM_VA = M(0x100)                                   # CAP bit 儿童位图: 孩子身份的唯一真相源
CHILD_SCHED_VA = M(0x180)                                # 排程表 8B/条: oid,slot,fslot,国,城 + 哨兵
CHILD_PASS_VA = M(0x1200)                                # 预载桩代码入口 child_pass
# ---- M3b: 成长结算 (桩 + 数据区)。全部相对 M() 且随 CAP 自动长, 换容量档不用改这里 ----
CHILD_GROWTH_VA = M(0x1420)                              # 成长桩 child_growth_pass 入口 (月钩第二段)
KID_ESZ = 12                                             # KID_TAB 条目字节数 (见 child_growth.py 的布局注释)
GROWTH_CNT_VA = M(0x2000)                                # 埋点表 4B/槽 (0x2000..0x2100 = 64 槽; 现用 33)
KID_TAB_VA = M(0x2100)                                   # 孩子培养记录, 按槽, CAP*12 B
CMD_RING_VA = KID_TAB_VA + CAP * KID_ESZ                 # 环形指令队列 头8B + 64*8B
MENU_PTR_VA = CMD_RING_VA + 0x220                        # 回家菜单: 串指针数组 (16*4B)
MENU_CODE_VA = MENU_PTR_VA + 0x40                        # 回家菜单: 指令码表 (16*2B)
PANEL_VA = MENU_CODE_VA + 0x20                           # 培养面板命中/状态 (32B)
# ---- M3b-3: 成效公式的两张常数表 (桩按 [act*4]/[teach] 直接读, 落在原"余量"头部) ----
ACT_TAB_VA = PANEL_VA + 0x20                             # 10 条 x 4B = (主加维, B 基础%, 0, 0)
TEACH_TAB_VA = ACT_TAB_VA + 0x28                         # 5 条 x 1B = T (教席加成; M3d 换成能力驱动)
# ---- M3c: 回家菜单「培养孩子」(PLAN §8.1 方案 E)。偏移全部接在 TEACH_TAB 之后(原余量头部), ----
#      区域表在下面 4j2 统一圈地/清零, 越界由那里的 assert 炸出来 (换 CAP 时 CMD_RING 会搬, 这里跟着搬)。
MENU_STR_VA = M(0x53D0)                                  # 24 项 x 24B GBK 菜单串(培养孩子/活动/教席/档次/暂不培养/岁/上一页/下一页)
DEC100_VA = M(0x5610)                                    # "00".."99" 两位十进制表, 桩里拼年龄免除法
NAME_BUF_VA = M(0x56E0)                                  # 孩子姓名行 12 x 24B (姓+名+  NN岁; 每页 10 行 + 2 行导航 = 12)
SLOT_ARR_VA = M(0x5800)                                  # 行 -> 槽 (12 x 2B)
SUB_PTR_VA = M(0x5820)                                   # 运行时子菜单指针数组 (12 x 4B)
ACT_PTR_VA = M(0x5860)                                   # 活动子菜单 11 x 4B (静态, 含"暂不培养")
TEACH_PTR_VA = M(0x5890)                                 # 教席子菜单 6 x 4B
TIER_PTR_VA = M(0x58B0)                                  # 档次子菜单 5 x 4B
MENU_SCR_VA = M(0x58D0)                                  # 钩子暂存 ebx/flag/cnt/ptrs/cnt1 (5 x 4B)
MENU_STUB_VA = M(0x5900)                                 # 桩代码: cm_hook 在前, cm_foster 16B 对齐在后
# ---- M6: sidecar 影子存档桩 + 它的数据区 (child_save.py) ----
SC_CODE_VA = M(0x6100)                                   # 两个 trampoline + sc_save/sc_load/sc_reset..
SC_DATA_VA = M(0x6700)                                   # 路径/头部缓冲/六段表/句柄/槽号/摘要/游标/模板/OFSTRUCT
# ---- M3c-2: 培养详情 GDI 面板 (kid_panel.py)。串池 -> 参数静态区 -> 桩代码 ----
KD_STR_VA = M(0x6900)                                    # [u8 长度][GBK][NUL] (标题/五维/成功率/亲密/提示 + M5 进度表四行/小框提示)
KD_DATA_VA = M(0x6A00)                                   # 参数静态区 (ent/slot/act/teach/tier/dim/B/R/P/bond/.. + M5 的 bar/n1..n4/nm/nmlen)
KD_CODE_VA = M(0x6B00)                                   # kd_show / kd_frame / kd_bars / kd_row / kd_itoa / kd_msg / kd_m_frame
KD_CODE_SZ = 0xC00                                       # ★ 五段实测 1626B; 2026-10-07 加 kd_msg+kd_m_frame 与进度表四行 => 抬到 0xC00
                                                         #   (旧配额 0x500/0x700 都装不下, 溢出会被后续占用者覆盖)
# ---- M5 (2026-10-07): 每月 1 次 / 花费 / 反馈 的两块数据区 ----
MSG_STR_VA = M(0x7700)                                   # 门禁拒绝 + 确认 + 反馈台词 + 费用提示 串池
MSG_STR_SZ = CM.MS_STR_ROW * len(CM.MSG_STRINGS)         # 26 项 x 24B = 0x270 -> 0x280
FOSTER_VA = M(0x7A00)                                    # 月计数(ym/cnt) + 本次天数/金 + 活动天数表 + 对话框指针数组
FOSTER_SZ = 0x40
assert MSG_STR_VA + MSG_STR_SZ <= FOSTER_VA, (MSG_STR_SZ, FOSTER_VA - MSG_STR_VA)
FO = dict(ym=0x00, cnt=0x04, days=0x08, gold=0x0C,        # dword: 上次培养的 (年<<8|月)+1 / 本月次数 / 本次天数 / 本次金
          msg_act=0x10, msg_slot=0x14,                    # dword: 反馈小框用 (活动码 / 孩子槽)
          act_days=0x18,                                  # byte[10]: 与 child_growth.ACTS 同序的天数表
          confirm=0x24,                                   # dword[2]: 确认框 "就这么办 / 再想想" (构建期填, 兼容旧口径)
          cost_arr=0x28,                                  # dword[3]: 运行时拼的确认框指针 (费用行/就这么办/再想想)
          deny_month=0x34, deny_time=0x38, deny_gold=0x3C)  # dword[1] x3: 三种拒绝的单按钮提示框
assert FO['deny_gold'] + 4 <= FOSTER_SZ, FO
assert FO['deny_gold'] + 4 <= FOSTER_SZ, FO
# ---- 生孩子: 「本次可选表」(v1 的 20 个名字池原来住这儿) ----
#   v2 (2026-10-08): 名字池扩到 500 个真名并搬到 MOD 尾 (BIRTH_POOL, 见下), 这里只留
#   bn_avail 每次开框收进来的「本次可选 20 个」= 20 x 2B 池内下标 + 1 个 dword 计数。
#   ★ 这块的尺寸**保持 0x8C 不变**: BIRTH_LABEL 及它后面的每个地址都不动 (verify/补丁站点
#     按布局表读, 但 4x 跳转表补丁与桩自检锁的是地址, 一挪就得全链重跑)。
BIRTH_AVAIL_VA = FOSTER_VA + FOSTER_SZ
BIRTH_AVAIL_SZ = 0x8C
BIRTH_AVAILN_VA = BIRTH_AVAIL_VA + 2 * CM.BIRTH_NAME_OFFER
assert 2 * CM.BIRTH_NAME_OFFER + 4 <= BIRTH_AVAIL_SZ, (CM.BIRTH_NAME_OFFER, BIRTH_AVAIL_SZ)
#   菜单标签「生孩子」另起一行: MENU_STR 那 24 行已把 0x240 用满, 且 DEC100 起的下游各区紧排无余量,
#   塞进去要把九个区整体顺移 (verify 侧有多处硬编码) => 标签放自己区尾, 不动任何既有地址。
BIRTH_LABEL_VA = BIRTH_AVAIL_VA + BIRTH_AVAIL_SZ
BIRTH_LABEL_SZ = CM.STR_ROW
assert BIRTH_LABEL_VA + BIRTH_LABEL_SZ <= NEW + MOD_OFF + MOD_SZ, \
    '生孩子名字池+标签越出 MOD_SZ (%06X + %02X > %06X)' % (
        BIRTH_LABEL_VA, BIRTH_LABEL_SZ, NEW + MOD_OFF + MOD_SZ)
# ---- 生孩子处理程序: 代码窗口 (v2 搬进 MOD 尾的新空地, 见下面 BIRTH_POOL 一段) ----
#   为什么搬: v1 窗口 M(0x7C00)+0x300 只剩 25B 余量, 而 v2 要在开框前筛「选过没有 / 本剧本
#   有活人叫这个名没有」, 处理长到近 1KB; 就地加长会压掉紧跟其后的 BIRTH_PICK/出生提示。
#   旧窗口 M(0x7C00)..M(0x7F00) 从此留白, BIRTH_PICK/PROMPT/NAME_TMP 三个地址一个都不动。
BIRTH_PICK_VA = M(0x7F00)                             # dword: 码 7 的分流标记 0=培养孩子 / 1=生孩子
assert BIRTH_PICK_VA >= BIRTH_LABEL_VA + BIRTH_LABEL_SZ, \
    '生孩分流标记压到可选表/标签 (%06X < %06X)' % (
        BIRTH_PICK_VA, BIRTH_LABEL_VA + BIRTH_LABEL_SZ)
assert BIRTH_PICK_VA + 4 <= NEW + MOD_OFF + MOD_SZ, \
    '生孩标记越出 MOD_SZ (%06X > %06X)' % (BIRTH_PICK_VA + 4, NEW + MOD_OFF + MOD_SZ)
# ---- 出生提示 (实机「生了孩子没有任何提示」): 四行指针数组 + 运行时拼的姓名串 ----
#   姓行/名行各 7B 且 NUL 补位, 不能直接当 C 串连着显示 (中间 NUL 会截断), 所以要一块 16B 缓冲
#   把两行拼成 "姓+名" (最长 6+6+1 = 13B)。指针数组 4 x 4B = 标题 / 姓名 / 随父居住 / 元服才进列表。
BIRTH_PROMPT_VA = M(0x7F10)
BIRTH_PROMPT_SZ = 16
BIRTH_NAME_TMP_VA = M(0x7F20)
BIRTH_NAME_TMP_SZ = 16
assert BIRTH_PROMPT_VA >= BIRTH_PICK_VA + 4, '出生提示指针数组压到分流标记'
assert BIRTH_NAME_TMP_VA >= BIRTH_PROMPT_VA + BIRTH_PROMPT_SZ, '姓名缓冲压到指针数组'
assert BIRTH_NAME_TMP_VA + BIRTH_NAME_TMP_SZ <= NEW + MOD_OFF + MOD_SZ, \
    '出生提示区越出 MOD_SZ (%06X > %06X)' % (BIRTH_NAME_TMP_VA + BIRTH_NAME_TMP_SZ,
                                             NEW + MOD_OFF + MOD_SZ)
# ---- v13 动态族谱: 运行时点亮桩 (tree_dyn.py), 落在 MOD 区新开的尾段 ----
#   前面所有区都排到 0x7F30, 余量只有 0xD0 —— 抬 MOD_SZ 到 0xA000 是**纯加长文件尾**
#   (.edata 是最后一节, Raw==Virt==整节零填充), 既有 M() 地址一个都不动 (同 R8 的口径)。
TREE_DYN_VA = M(0x8000)
TREE_DYN_SZ = 0x400
assert TREE_DYN_VA >= BIRTH_NAME_TMP_VA + BIRTH_NAME_TMP_SZ, '动态族谱桩压到出生提示区'
assert TREE_DYN_VA + TREE_DYN_SZ <= NEW + MOD_OFF + MOD_SZ, \
    '动态族谱桩越出 MOD_SZ (%06X > %06X)' % (TREE_DYN_VA + TREE_DYN_SZ,
                                             NEW + MOD_OFF + MOD_SZ)
# ---- 生孩子 v2: 500 个真名 + 已选标记 + 处理代码, 全落在树桩之后的 MOD 尾空地 ----
#   为什么放这儿: MOD_SZ 抬到 0xA000 时 M(0x8400) 起就是纯余量, 而名字池从 20 涨到 500 要 3.5KB,
#   原区(FOSTER 后面那 0x8C)装不下; 既有地址一个都不动, 只是把新东西往后接。
#   ★ 名字行 7B: bn_live 用 dword@+0 与 dword@+3 两段比完整行, 最后一行只读到 +6, 不越界。
BIRTH_POOL_VA = M(0x8400)
BIRTH_POOL_SZ = 7 * CM.BIRTH_NAME_COUNT               # 3500
BIRTH_USED_VA = _align(BIRTH_POOL_VA + BIRTH_POOL_SZ, 0x10)   # 1B/名: 玩家选过 = 永不重发
BIRTH_USED_SZ = CM.BIRTH_NAME_COUNT                   # 500
BIRTH_CODE_VA = M(0x9400)                             # 生孩处理 (含 bn_avail/bn_live)
BIRTH_CODE_SZ = 0x600
assert BIRTH_POOL_VA >= TREE_DYN_VA + TREE_DYN_SZ, '名字池压到动态族谱桩'
assert BIRTH_USED_VA + BIRTH_USED_SZ <= BIRTH_CODE_VA, '已选标记压到生孩代码窗口'
assert BIRTH_CODE_VA + BIRTH_CODE_SZ <= NEW + MOD_OFF + MOD_SZ, \
    '生孩代码越出 MOD_SZ (%06X > %06X)' % (BIRTH_CODE_VA + BIRTH_CODE_SZ,
                                           NEW + MOD_OFF + MOD_SZ)
# .fdata 那边的清单(由 build_fam_btn2 落地): 桩要引用的全在那儿, 不重复算一遍
TB = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                 'tree_blobs.json'), encoding='utf-8'))
# 成长埋点表 (M3b): 顺序即 0x2000 起的 4B 槽位, 加一项就 append, 别插中间 (tkwatch/verify 按下标取)。
GROWTH_CTRS = ['GROWTH_NATURAL',    # 自然保底 +1 成功次数 (桩: cg_grow 落点)
               'GROWTH_ROLL',       # 掷骰次数 (M3b-3 培养成效门才用; 自然保底不用 rand)
               'GROWTH_SETTLED',    # 本孩本月被结算的次数 (重复结算 = 月守卫失效)
               'GROWTH_DUPM',       # 因"本月已结算"被跳过 (一个月钩内多次触发时应当看到它)
               'GROWTH_FAIL',       # 概率门失败 (M3b-3)
               'GROWTH_FULL',       # 五维全部已到史实成年值 => 自然保底不再加点
               'GROWTH_FREEZE',     # 年龄到达元服线 => 自然成长停 (M4 后应恒等于 CHILD_GENPUKU)
               'GROWTH_CMD',        # 消费掉的指令条数 (与 CMD_PUSH 对照 = 有无丢指令, M3b-3)
               'TEACH_LORD', 'TEACH_PARENT', 'TEACH_SHOPE',
               'KID_NOTSAME_CITY', 'KID_LAST_SLOT', 'KID_LAST_ACT',
               'PANEL_OPEN', 'CMD_PUSH', 'MENU_COUNT',
               'GROWTH_PASS',       # child_growth_pass 被调用趟数 (M3b-2; 应 = 本进程走过的月数)
               'GROWTH_OK',         # M3b-3 培养成功加点数  => 恒等式 OK = ROLL - FAIL
               'GROWTH_REJECT',     # M3b-3 前置不合格(槽不是孩子/码越界/硬顶满) => CMD - ROLL = REJECT
               'GROWTH_PUKU_MOUNT', # M4 元服且**挂上了人**(归属码 1 随父 / 2 本国国主) 人次
               'GROWTH_PUKU_RONIN', # M4 元服但浪人化(归属码 3, 无父可跟且本国查不到国主) 人次
               'PAGE_ROWS',         # M3c 分页: 一级"选孩子"弹窗**见过的最大行数** (>PAGE_KIDS 即导航行已出现)
               'PAGE_NAV',          # M3c 分页: 下一页/上一页被点的次数 (默认档 fam13 应恒 0 = 从没翻过页)
               'BIRTH_COUNT']       # 生孩子次数 (M7; 每次点"生孩子"并成功创建 +1)
GROWTH_CTRS += SV.SC_CTRS                           # M6 影子存档 9 个 (append 在尾, 别插中间)
assert len(GROWTH_CTRS) <= 0x100 // 4, '埋点表只有 0x100 字节 = 64 槽, 现在 %d 个' % len(GROWTH_CTRS)
GC_IDX = {n: GROWTH_CNT_VA + i * 4 for i, n in enumerate(GROWTH_CTRS)}
NEW_HI = NEW + STRIDE * N0            # 新池尾(P1 期等效旧 HI)

MEM_MNEMS = {
    'mov', 'lea', 'cmp', 'push', 'add', 'sub', 'and', 'or', 'xor', 'test',
    'xchg', 'adc', 'sbb', 'movzx', 'movsx', 'inc', 'dec', 'neg', 'not',
    'cmpxchg', 'movbe', 'xadd', 'bt',
}

def reloc_val(v):
    """旧池地址(含池尾界) -> 新地址; 不命中返回 None"""
    if LO <= v < HI:
        return NEW + (v - LO)
    if v == HI:
        return NEW_HI
    return None

def sweep(data, va):
    """线性反汇编+失步重同步, 返回 {addr: Insn}"""
    md = Cs(CS_ARCH_X86, CS_MODE_32)
    md.detail = True
    out = {}
    pos, end = 0, len(data)
    while pos < end:
        prog = False
        for ins in md.disasm(data[pos:end], va + pos):
            prog = True
            pos = ins.address - va + len(ins.bytes)
            out[ins.address] = ins
        if not prog:
            pos += 1
    return out

def sweep_iter(data, va):
    """同 sweep, 但按序 yield(省内存)"""
    md = Cs(CS_ARCH_X86, CS_MODE_32)
    md.detail = True
    pos, end = 0, len(data)
    while pos < end:
        prog = False
        for ins in md.disasm(data[pos:end], va + pos):
            prog = True
            pos = ins.address - va + len(ins.bytes)
            yield ins
        if not prog:
            pos += 1

def main():
    b = bytearray(open(SRC, 'rb').read())
    pe = pefile.PE(data=bytes(b))
    assert pe.OPTIONAL_HEADER.ImageBase == IMAGE_BASE
    secs = {}
    for s in pe.sections:
        secs[s.Name.rstrip(b'\0').decode()] = s
    assert len(secs) == 5, '族谱版应恰有 5 节'

    # ---------- 1) 新节 .edata ----------
    first_raw = min(s.PointerToRawData for s in pe.sections)
    e_lfanew = struct.unpack_from('<I', b, 0x3C)[0]
    coff = e_lfanew + 4
    nsec = struct.unpack_from('<H', b, coff + 2)[0]
    size_opt = struct.unpack_from('<H', b, coff + 16)[0]
    table = coff + 20 + size_opt
    assert nsec == 5
    assert table + 40 * 6 <= first_raw, '节表空隙不足'
    # .fdata 尾 = 其 ptr+size
    fd = secs['.fdata']
    want_ptr = fd.PointerToRawData + fd.SizeOfRawData
    assert want_ptr % 0x200 == 0
    NEW_PTR = want_ptr
    fsize = os.path.getsize(SRC)
    assert fsize == NEW_PTR, '族谱版文件尾应恰在 .fdata 后'
    # 追加节头
    name = b'.edata\x00\x00'
    hdr = struct.pack('<8sIIIIIIHHI', name, NEW_SZ, NEW_RVA, NEW_SZ, NEW_PTR,
                      0, 0, 0, 0, 0xE0000040)
    b[table + 40 * 5: table + 40 * 5 + 40] = hdr
    struct.pack_into('<H', b, coff + 2, 6)                    # NumberOfSections
    struct.pack_into('<I', b, e_lfanew + 24 + 56, NEW_RVA + NEW_SZ)  # SizeOfImage
    # 补零到新文件尾
    b.extend(b'\x00' * (NEW_PTR + NEW_SZ - len(b)))
    print('节 .edata: RVA 0x%06X VA 0x%06X raw 0x%X size 0x%X SizeOfImage=0x%X' %
          (NEW_RVA, NEW, NEW_PTR, NEW_SZ, NEW_RVA + NEW_SZ))

    # ---------- 2) 重定位所有旧池字段引用 ----------
    manifest, skipped = [], []
    for s in pe.sections:
        nm = s.Name.rstrip(b'\0').decode()
        if nm == '.rsrc':
            continue
        data = bytes(b[s.PointerToRawData:s.PointerToRawData + s.SizeOfRawData])
        s_va = IMAGE_BASE + s.VirtualAddress
        ins_map = sweep(data, s_va)
        for p in range(len(data) - 3):
            v = struct.unpack_from('<I', data, p)[0]
            nv = reloc_val(v)
            if nv is None:
                continue
            # 必须完整落在某条白名单指令的操作数字段上
            host = None
            for back in range(0, 14):
                it = ins_map.get(s_va + p - back)
                if it and it.address - s_va + len(it.bytes) >= p + 4:
                    host = it
                    break
            if host is None or host.mnemonic not in MEM_MNEMS:
                skipped.append((nm, p, v, host.mnemonic if host else 'no-insn'))
                continue
            # 字段匹配: 指令字节内 p-host.off 处须 == pack(v), 且是 imm/disp 值
            off = p - (host.address - s_va)
            if host.bytes[off:off + 4] != struct.pack('<I', v):
                skipped.append((nm, p, v, 'field-mismatch:' + host.mnemonic))
                continue
            ok_operand = False
            for op in host.operands:
                if op.type == X86_OP_IMM and (op.imm & 0xFFFFFFFF) == v:
                    ok_operand = True
                if op.type == X86_OP_MEM and (op.mem.disp & 0xFFFFFFFF) == v:
                    ok_operand = True
            if not ok_operand:
                skipped.append((nm, p, v, 'operand-mismatch'))
                continue
            abs_i = s.PointerToRawData + p
            struct.pack_into('<I', b, abs_i, nv)
            manifest.append({'sec': nm, 'off': p, 'va': s_va + p, 'old': v,
                             'new': nv, 'ins': '%s %s' % (host.mnemonic, host.op_str)})
    n_by_sec = {}
    for m in manifest:
        n_by_sec[m['sec']] = n_by_sec.get(m['sec'], 0) + 1
    print('重定位 %d 处: %s' % (len(manifest), n_by_sec))
    print('跳过(应为 j*/call/garbage 命中): %d' % len(skipped))
    for sk in skipped[:40]:
        print('   skip [%s+0x%X] 0x%08X  %s' % sk)

    # ---------- 3) 复扫验证: 旧池字段引用清零 ----------
    pe2 = pefile.PE(data=bytes(b))
    left = 0
    for s in pe2.sections:
        nm = s.Name.rstrip(b'\0').decode()
        if nm == '.rsrc':
            continue
        data = bytes(b[s.PointerToRawData:s.PointerToRawData + s.SizeOfRawData])
        s_va = IMAGE_BASE + s.VirtualAddress
        ins_map = sweep(data, s_va)
        for p in range(len(data) - 3):
            v = struct.unpack_from('<I', data, p)[0]
            if reloc_val(v) is not None:
                host = None
                for back in range(0, 14):
                    it = ins_map.get(s_va + p - back)
                    if it and it.address - s_va + len(it.bytes) >= p + 4:
                        host = it
                        break
                if not (host and host.mnemonic in MEM_MNEMS):
                    continue
                # 与打点通道同判据: 字段字节匹配 + 操作数值匹配
                off = p - (host.address - s_va)
                if host.bytes[off:off + 4] != struct.pack('<I', v):
                    continue
                if not any((op.type == X86_OP_IMM and (op.imm & 0xFFFFFFFF) == v) or
                           (op.type == X86_OP_MEM and (op.mem.disp & 0xFFFFFFFF) == v)
                           for op in host.operands):
                    continue
                left += 1
                print('   !! 残留 [%s+0x%X] 0x%08X `%s %s`' % (
                    nm, p, v, host.mnemonic, host.op_str))
    assert left == 0, '残留 %d 处' % left
    print('复扫: 白名单字段引用残留 0 ✓ (j*/call/数据噪声命中不算)')

    # ---------- 4) 关键锚点抽查 ----------
    def find4(v):
        return bytes(struct.pack('<I', v))
    assert bytes(b).count(find4(NEW)) >= 300, '新基址 imm 数量异常'
    json.dump(manifest, open('_big_reloc.json', 'w', encoding='utf-8'),
              ensure_ascii=False, indent=1)

    # ---------- 4b) P2-STAGE: 0x172(370) -> CAP ----------
    #   判据: 解码指令的 imm 操作数 == 0x172 且白名单指令(cmp/mov/push...)。
    #   23 处 "cmp 后置 mov 再 jcc" 的延迟界检同属 BOUND(cmp/mov 均不破坏标志) —— 一起改。
    #   序列化器 VA 区间 [0x47DA00,0x47F200) 的 4 处循环保留 370(文件格式锚)。
    #   清点应与 _sites_172.json 的 510 处一致: patched=506, kept=4。
    SER_LO_VA, SER_HI_VA = 0x47DA00, 0x47F200
    OLD_N, NEW_N = 0x172, CAP
    # ★ 黑名单: 这两处是 **栈上局部数组** 的 memset 长度参数 (`lea eax,[esp+0xC]` -> push 0x172),
    #   栈数组本身只有 370B(编译器定的, 不随 CAP 长), 跟着放大到 1024 会踩穿返回地址 => EIP=0 大地图崩。
    #   (2026-10-07 fix1 事故现场: mk_fix1.py 的两处 push 0x400 -> 0x172 就是这两个地址)
    STACK_MEMSET_SITES = (0x49C5E5, 0x49CD3D)
    tsec = secs['.text']
    patched172, kept_ser = [], []
    data = bytes(b[tsec.PointerToRawData:tsec.PointerToRawData + tsec.SizeOfRawData])
    s_va = IMAGE_BASE + tsec.VirtualAddress
    for ins in sweep_iter(data, s_va):
        hit = None
        for o in ins.operands:
            if o.type == X86_OP_IMM and (o.imm & 0xFFFFFFFF) == OLD_N and o.size in (2, 4):
                hit = o
                break
        if hit is None or ins.mnemonic not in MEM_MNEMS:
            continue
        if SER_LO_VA <= ins.address < SER_HI_VA:
            kept_ser.append((ins.address - s_va, '%s %s' % (ins.mnemonic, ins.op_str)))
            continue
        if ins.address in STACK_MEMSET_SITES:
            kept_ser.append((ins.address - s_va,
                             'STACK-MEMSET(栈局部数组,不放大): %s %s'
                             % (ins.mnemonic, ins.op_str)))
            continue
        w = hit.size
        off = len(ins.bytes) - w          # 立即数在指令尾部
        if ins.bytes[off:off + 2] != struct.pack('<H', OLD_N) or \
           (w == 4 and ins.bytes[off + 2:off + 4] != b'\x00\x00'):
            kept_ser.append((ins.address - s_va, 'NOTAIL:' + ins.mnemonic))
            continue
        abs_i = tsec.PointerToRawData + (ins.address - s_va) + off
        struct.pack_into('<H', b, abs_i, NEW_N)
        if w == 4:
            struct.pack_into('<H', b, abs_i + 2, 0)
        patched172.append({'off': ins.address - s_va, 'va': ins.address, 'w': w,
                           'ins': '%s %s' % (ins.mnemonic, ins.op_str)})
    print('P2: 改界 %d 处 (0x172->0x%X=%d), 保留 %d 处' % (len(patched172), NEW_N, NEW_N, len(kept_ser)))
    for o, txt in kept_ser:
        print('   keep +%06X %s' % (o, txt))
    assert len(patched172) == 502 and len(kept_ser) == 8, \
        'P2 点数与清点清单不符(6 序列化器锚 + 2 栈 memset, patched=%d kept=%d)' \
        % (len(patched172), len(kept_ser))

    # ---------- 4c) P2-STAGE: .edata 扩展槽静态初始化 (370..CAP-1) ----------
    #   模板 = 运行时池尾空槽 354 的 47B 原文(ents_dump.json), 仅 id word=槽号。
    #   槽 370 保 0x808F 兼作哨兵假人(吸收 0x172 语义)。
    #   ★ 扩展槽(>=370)一律保持 0x808F 空槽态, 不写待登场标记: 存档序列化器(0x47DCE0/0x47DF00)
    #     只循环 0..369 (4 处 0x172 界保留不动 = 文件格式锚), 落进扩展槽的人在 SAVEDATA 里没有记录,
    #     读档即消失(而登场标志已置 1, 永不再生) —— 所以「待登场槽」必须取自 354..369 这 16 个
    #     池内原生空槽, 见 4i 的 ensure_queue。
    #   ★ 354..369 在运行池里是 0x808F 无名dummy(尾空槽), 4i 每月把它们武装成 0x800B
    #     (bit15 置=不在场, bit7 清=已元服可占, 低4位=0xb 倒数位) —— 引擎自己给
    #     「已故/除籍武将的空缺槽」打的正是这个组合(0x4A4872 赋 nib=6..11), 属原生合法态。
    import json as _json
    dump = _json.load(open(r'F:\Games\Taikou 2\Taikou2 Original\.rev\ents_dump.json', encoding='utf-8'))
    tmpl = None
    for e in dump:
        if e['slot'] == 354:
            tmpl = bytes.fromhex(e['raw'])
    assert tmpl and len(tmpl) == 47, '槽354模板缺失'
    assert struct.unpack_from('<H', tmpl, 0x2c)[0] == 0x808F, '模板状态字异常'
    ed = [s for s in pe2.sections if s.Name.rstrip(b'\0') == b'.edata'][0]
    RESERVE_LO, RESERVE_N = 354, 16      # 待登场槽 = 池内尾空槽 354..369 (存档范围内, 可持久)
    for i in range(N0, CAP):             # 370..CAP-1 全打 0x808F 空槽态
        rec = bytearray(tmpl)
        rec[0:2] = struct.pack('<H', i)  # id word = 槽号 (尾槽惯例)
        off = ed.PointerToRawData + i * STRIDE
        b[off:off + STRIDE] = rec
    # 池内 0..369 的静态值来自 .data 搬家(P1), 尾空槽 354..369 原样 0x808F; 不在此改写 ——
    # 存档/剧本载入会整体覆写 0..369, 静态改写无意义, 由 4i ensure_queue 运行期武装。
    print('扩展槽 %d..%d 静态初始化完成 (模板=尾空槽354, 全 0x808F) ; 待登场槽 = 池 %d..%d 共 %d 个(4i 运行期武装)'
          % (N0, CAP - 1, RESERVE_LO, RESERVE_LO + RESERVE_N - 1, RESERVE_N))

    # ---------- 4d) P2 复核: .text 内白名单操作数 0x172 应只剩序列化器 4 处 ----------
    data = bytes(b[tsec.PointerToRawData:tsec.PointerToRawData + tsec.SizeOfRawData])
    left172 = 0
    for ins in sweep_iter(data, s_va):
        if ins.mnemonic in MEM_MNEMS and any(
                o.type == X86_OP_IMM and (o.imm & 0xFFFFFFFF) == OLD_N
                for o in ins.operands):
            left172 += 1
            print('   余 %06X %s %s' % (ins.address - s_va, ins.mnemonic, ins.op_str))
    assert left172 == 8, 'P2 后残留 %d 处' % left172
    print('P2 复核: 0x172 保留 8 点 = 序列化器 6 (4 mov + 2 cmp) + 栈局部数组 memset 2 ✓')

    # ---------- 4e) P3a-STAGE: 姓名两表搬家到 .edata, 容量 370->CAP ----------
    #   原 0x520660 (370×7, 止 0x521076) = **名表**; 原 0x521AA8 (370×7, 止 0x5224C2) = **姓表**。
    #   全部引用只有 4 个常量: base 与 base+6 (记录尾字节清零)。
    #   新家: SUR=NEW+SUR_OFF(=名表), GIV=NEW+GIV_OFF(=姓表), 均随 CAP 推导;
    #   序列化器逐槽 370 条写文件 —— 搬家透明, 格式不变。
    SUR_NEW = NEW + SUR_OFF          # 名表 (原 0x520660)
    GIV_NEW = NEW + GIV_OFF          # 姓表 (原 0x521AA8)
    assert SUR_NEW + 7 * CAP == GIV_NEW and GIV_NEW + 7 * CAP <= NEW + MOD_OFF, \
        '姓名两表越进 MOD 私有区'
    TAB_MAP = {0x520660: SUR_NEW, 0x520666: SUR_NEW + 6,
               0x521AA8: GIV_NEW,  0x521AAE: GIV_NEW + 6}

    def tab_reloc(v):
        return TAB_MAP.get(v)

    def field_pass(relocate, collect=None, verbose_tag=''):
        """全节(除 .rsrc)窗口扫描: 白名单指令操作数字段命中 relocate(v) 则改写."""
        n_hit = n_skip = 0
        for s in pe2.sections:
            nm = s.Name.rstrip(b'\0').decode()
            if nm == '.rsrc':
                continue
            data = bytes(b[s.PointerToRawData:s.PointerToRawData + s.SizeOfRawData])
            s_va = IMAGE_BASE + s.VirtualAddress
            ins_map = sweep(data, s_va)
            for p in range(len(data) - 3):
                v = struct.unpack_from('<I', data, p)[0]
                nv = relocate(v)
                if nv is None:
                    continue
                host = None
                for back in range(0, 14):
                    it = ins_map.get(s_va + p - back)
                    if it and it.address - s_va + len(it.bytes) >= p + 4:
                        host = it
                        break
                if host is None or host.mnemonic not in MEM_MNEMS:
                    n_skip += 1
                    print('   %sskip [%s+0x%X] 0x%08X %s' % (
                        verbose_tag, nm, p, v, host.mnemonic if host else 'no-insn'))
                    continue
                off = p - (host.address - s_va)
                if host.bytes[off:off + 4] != struct.pack('<I', v):
                    n_skip += 1
                    print('   %sskip [%s+0x%X] field-mismatch' % (verbose_tag, nm, p))
                    continue
                if not any((op.type == X86_OP_IMM and (op.imm & 0xFFFFFFFF) == v) or
                           (op.type == X86_OP_MEM and (op.mem.disp & 0xFFFFFFFF) == v)
                           for op in host.operands):
                    n_skip += 1
                    print('   %sskip [%s+0x%X] 0x%08X operand-mismatch' % (
                        verbose_tag, nm, p, v))
                    continue
                if collect is not None:
                    abs_i = s.PointerToRawData + p
                    struct.pack_into('<I', b, abs_i, nv)
                    collect.append({'sec': nm, 'off': p, 'old': v, 'new': nv,
                                    'ins': '%s %s' % (host.mnemonic, host.op_str)})
                n_hit += 1
        return n_hit, n_skip

    tab_manifest = []
    n_hit, n_skip = field_pass(tab_reloc, tab_manifest, 'P3a ')
    print('P3a: 姓/名表引用重定位 %d 处, 噪声跳过 %d' % (n_hit, n_skip))
    for m in tab_manifest:
        print('   [%s+0x%X] 0x%08X -> 0x%08X  %s' % (m['sec'], m['off'], m['old'], m['new'], m['ins']))
    assert n_skip == 0 and len(tab_manifest) >= 26, 'P3a 站点异常, 需人工核对'

    # 复扫: 旧表常量残留应为 0 (噪声除外, 用同判据)
    left_tab, _ = field_pass(tab_reloc, None, 'P3a-rescan ')
    assert left_tab == 0, 'P3a 残留 %d 处' % left_tab
    print('P3a 复核: 旧姓/名表字段引用 0 ✓ (表容量 %d, 序列化器条数仍 370)' % CAP)

    # ---------- 4f) P3b-STAGE: 休眠人物姓名预填 (姓/名表槽 371..462) ----------
    #   数据源 _dormants.json (gen_dormants.py 从 tree_data 生成, 独名字已拆姓/名)。
    #   序列化器逐槽只写 0..369, 扩展条目在运行期永不被加载流程覆盖 -> 文件字节即终值。
    dorm = json.load(open(r'F:\Games\Taikou 2\Taikou2 Original\.rev\_dormants.json', encoding='utf-8'))
    ed2 = [s for s in pe2.sections if s.Name.rstrip(b'\0') == b'.edata'][0]
    for d in dorm:
        sl = d['slot']
        assert 371 <= sl < CAP, ('休眠名槽越界', sl)
        # 姓 -> GIV_NEW(原 0x521AA8 = 姓表) / 名 -> SUR_NEW(原 0x520660 = 名表)  (见文件头极性说明)
        for key, tbl in (('sur_hex', GIV_NEW), ('giv_hex', SUR_NEW)):
            nb = bytes.fromhex(d[key])
            assert len(nb) <= 6, (d, key)
            off = ed2.PointerToRawData + (tbl - NEW) + sl * 7
            b[off:off + len(nb)] = nb
            b[off + len(nb)] = 0
    print('P3b: 休眠人物 %d 名已预填 (槽 %d..%d)' % (
        len(dorm), dorm[0]['slot'], dorm[-1]['slot']))

    # ---------- 4g) MCI-STUB: 屏蔽 mciSendCommandA 的设备打开, 躲 Win11 24H2 msmpeg2ac3dec fastfail ----------
    #   根因(minidump 实证): 进大地图时游戏经 WINMM!mciSendCommandA 建 DirectShow 图播放 开场动画/BGM(=MP3),
    #   系统旧解码器 msmpeg2ac3dec.dll 自毁(0xC0000602 __fastfail)。属环境回归, 与族谱/池代码无关(family/big/zoom 同崩)。
    #   做法(不依赖被加载器覆写的 IAT): .text 里全部 `call/mov dword,[0x4FB1E8]`(__imp_mciSendCommandA) 的
    #   disp32 改指到 .edata 内私有槽 NEW_SLOT; 该槽存 stub VA, stub 对 MCI_OPEN(0x800) 返回错误码(令调用方跳过媒体),
    #   其余命令返回 0(空操作)。加载器不碰 .edata, 故改写持久; 设备永不打开 -> 解码器不加载 -> 不崩。
    #   代价: 开场/结局动画与背景音乐全静音(用户已确认接受)。还原=用未打此步的 big 或删节。
    IAT_MCI_VA = 0x4FB1E8                       # .data 内 __imp_mciSendCommandA 槽
    NEW_SLOT_VA, STUB_VA = MOD_SLOT_VA, MOD_STUB_VA   # .edata 私有槽/桩 (地址由 CAP 推导)
    ed3 = [s for s in pe2.sections if s.Name.rstrip(b'\0') == b'.edata'][0]
    def ed_off(va):
        assert NEW <= va < NEW + NEW_SZ, ('.edata 越界', hex(va))
        return ed3.PointerToRawData + (va - NEW)
    stub = bytearray()
    stub += b'\x8B\x44\x24\x08'              # mov eax,[esp+8]      msg
    stub += b'\x3D\x00\x08\x00\x00'          # cmp eax,0x800        MCI_OPEN
    stub += b'\x74\x05'                      # je  short .open      (-> 0x10)
    stub += b'\x33\xC0'                      # xor eax,eax          返回 0 (其它命令空操作)
    stub += b'\xC2\x10\x00'                  # ret 16               stdcall 清 4 参
    # .open:
    stub += b'\xB8\x00\x01\x00\x00'          # mov eax,0x100        MCIERR_BASE -> 调用方判失败, 跳过媒体
    stub += b'\xC2\x10\x00'                  # ret 16
    assert len(stub) <= 0x80, 'stub 过长'
    b[ed_off(STUB_VA):ed_off(STUB_VA) + len(stub)] = stub
    struct.pack_into('<I', b, ed_off(NEW_SLOT_VA), STUB_VA)   # 私有槽 = stub 代码 VA
    old4 = struct.pack('<I', IAT_MCI_VA)
    new4 = struct.pack('<I', NEW_SLOT_VA)
    n_ref = b.count(old4)
    b = bytearray(bytes(b).replace(old4, new4))
    assert n_ref == 18, 'mciSendCommandA 引用点数量异常: %d (期望 18)' % n_ref
    assert b.count(old4) == 0 and b.count(new4) == n_ref
    print('MCI-STUB: stub @0x%06X (%dB), 私有槽 0x%06X 存 0x%06X, 改写 [0x4FB1E8] 引用 %d 处 -> 全指私有槽'
          % (STUB_VA, len(stub), NEW_SLOT_VA, STUB_VA, n_ref))

    # ---------- 4h) BGM-STUB: 屏蔽 mp3.dll 背景乐的 DirectShow 图, 才是进大地图仍崩的真凶 ----------
    #   MCI-STUB 只封了引擎内建 mciSendCommandA(开场/结局 AVI); 打完仍崩, minidump 显示 msmpeg2ac3dec 是经
    #   BGM 插件 mp3.dll -> mciSendStringA -> mciqtz32 -> DirectShow 图被加载的。该 DLL 由 .data 内一块保护壳代码驱动:
    #     0x52D100 LoadLibrary("MP3.DLL")+GetProcAddress -> mp3play@[ebp+0x20]/mp3seek@+0x24/mp3stop@+0x28;
    #     0x52D200 play 包装: 拼 ".\\MP3\\??.MP3" 文件名 -> push 文件名 -> 0x52D342 `call [ebp+0x20]`(mp3play, stdcall 1 参, 建图->崩)
    #                            -> 0x52D348 `mov [ebp+0x40],1`(置"正在播放"标志);
    #     0x52D390 stop 包装: 仅当标志!=0 才 `call [ebp+0x28]`(mp3stop) -> 拆图。
    #   全盘: mp3play 只在 0x52D342 调一次, mp3seek 无人调用, mp3stop 被标志门控。故只需断 play:
    #     (a) 三字节 call 换成 `add esp,4` —— 弹出已压入的文件名实参, 栈平衡, 不建图;
    #     (b) 七字节"置标志"换成 `inc dword[BGM_CNT]` + nop —— 标志恒 0 -> stop 亦永不触发 mp3stop; 该计数即埋点。
    #   代价: 背景音乐静音(动画已静音)。还原=删除本步。tkwatch 读 VA BGM_CNT 可确认"命中并抑制 N 次"。
    dsec = [s for s in pe2.sections if s.Name.rstrip(b'\0') == b'.data'][0]
    DVA = IMAGE_BASE + dsec.VirtualAddress
    DSZ = max(dsec.Misc_VirtualSize, dsec.SizeOfRawData)
    def data_off(va):
        assert DVA <= va < DVA + DSZ, ('.data 越界', hex(va))
        return dsec.PointerToRawData + (va - DVA)
    PLAY_CALL_VA, FLAG_SET_VA = 0x52D342, 0x52D348   # BGM_CNT_VA 由顶部布局推导
    # 被替换区 = call[ebp+0x20](3) + 3 nop(3) + mov [ebp+0x40],1(7) = 13 字节, 到 0x52D34F 止
    assert bytes(b[data_off(PLAY_CALL_VA):data_off(PLAY_CALL_VA) + 3]) == b'\xFF\x55\x20', 'play call 站点漂移'
    assert bytes(b[data_off(FLAG_SET_VA):data_off(FLAG_SET_VA) + 7]) == b'\xC7\x45\x40\x01\x00\x00\x00', 'flag set 站点漂移'
    assert bytes(b[data_off(PLAY_CALL_VA):data_off(PLAY_CALL_VA) + 13]) == \
        b'\xFF\x55\x20\x90\x90\x90\xC7\x45\x40\x01\x00\x00\x00', 'play 包装区布局异常'
    # 下一原指令须是 mov word[0x501290],2 (66 c7 05 ..) -> 补丁须恰好填满 13 字节落到它, 不可留残字节(否则错位 AV)
    assert bytes(b[data_off(PLAY_CALL_VA + 13):data_off(PLAY_CALL_VA + 13) + 3]) == b'\x66\xC7\x05', '尾指令边界异常'
    patch = b'\x83\xC4\x04' + b'\xFF\x05' + struct.pack('<I', BGM_CNT_VA) + b'\x90\x90\x90\x90'  # add esp,4 | inc[BGM_CNT] | nop*4 = 13B
    assert len(patch) == 13
    b[data_off(PLAY_CALL_VA):data_off(PLAY_CALL_VA) + 13] = patch
    struct.pack_into('<I', b, ed_off(BGM_CNT_VA), 0)                                   # 埋点计数器初值 0
    assert bytes(b[data_off(PLAY_CALL_VA):data_off(PLAY_CALL_VA) + 13]) == patch
    print('BGM-STUB: 0x%06X call[mp3play]->add esp,4; 0x%06X 置标志->inc dword[0x%06X](埋点,恒不置位) ; stop 因标志恒0 不触发'
          % (PLAY_CALL_VA, FLAG_SET_VA, BGM_CNT_VA))

    # ---------- 4i) APPEAR-STAGE: 解锁引擎原生「元服/登场」通道 ----------
    #   原生例程 0x4A4D10 (唯一调用者 0x4A4CC0 <- 0x4A4C60 <- 0x4A0DED, 在日期推进链 0x4A0D50 内)
    #   每推进 1 个月执行一次 (1/7 月额外先 call 0x4a4f70):
    #     A) 扫池 di=0..0x166: 0x49a610 取状态字低4位倒数位, ==0xff(>=0xc) 或 <=0 跳过, 否则
    #        `push eax; call 0x49a6b0` 把倒数位 -1; 再要求 状态字 bit15=1(不在场) 且 bit7=0
    #        -> 该槽收入空缺槽表 [esp+0x690] (步 2B, 容量 (0x964-0x690)/2 = 362)。
    #     B) 扫 oid si=0..699: 登场标志[0x519288+si]==0 且 BSDATA 记录 +0x27 打包字的 登场年偏移
    #        ((w>>7)&0x3f) <= 当前年偏移 [0x5205f0] -> 收 (oid, 打包字) 到 [esp+0xc8] (步 4B,
    #        容量 0x690-0xc8 = 370), 按 登场年/生年 排序。
    #     C) 两表配对: call 0x47f7b0(oid, slot) 实例化(填姓/名表 + 47B 实体, 状态字取 BSDATA+0x38
    #        => 活人), 置登场标志=1, 然后 `push ent; call 0x4a4fc0` = 元服初始化(按 身分码 挂主君)。
    #   shipped 数据 A 步命中 0 槽(全池倒数位=0xf) => 通道每月空转, 这就是"到年份也没人出现"的根因。
    #   本步四处字节补丁, 与 gen_appear_patch.py 的登场年日程配套:
    #     (a) 0x4A4D61 `push eax; call 0x49a6b0` (6B) -> `inc dword[VACANT_CNT]` (6B 等长):
    #         冻结倒数位(否则空槽 11 个月内没被人填上就永久失效, 通道会自己关掉), 同时兼埋点。
    #         下一条就是 mov ax,[esi+0x2c] / test ah,0x80, 标志不被后续消费; 无 push/pop, 栈不变。
    #     (b) 0x4A4D84 `cmp di,0x167` (5B) -> `cmp di,0x200`: 扫描界抬到 512。当前待登场槽只用到
    #         池内 354..369, 抬界是为把空缺槽容量提到 512 的后续版本(见 4c 存档说明)铺路。
    #         di=511 时 esi=0x53C000+511*47=0x541B4B(+0x2c 读到 0x541B77) < 姓表 0x541E00, 不越界。
    #     (c) 0x4A4F40 `call 0x4a4fc0` (5B) -> `call stub`, stub = inc dword[APPEAR_CNT] + jmp 0x4a4fc0。
    #         trampoline 不 push/pop, 返回地址仍由原 call 压入(0x4A4F45), 栈布局逐位不变。
    #     (d) 0x4A4CC0 `call 0x4a4d10` (5B) -> `call ensure_queue`, 每月扫池前把「仍是原生空槽态
    #         0x808F」的池尾 16 槽(354..369) 武装成待登场槽 0x800B, 然后 jmp 0x4a4d10。
    #         为什么必须在运行期做: 存档/剧本载入器(0x47DCE0/0x47DF00)按 0..369 逐槽覆写池,
    #         .edata 里的静态状态字会被文件值盖掉; 而 354..369 恰在存档范围内 => 登场者能被存下、
    #         读档不丢(落进扩展槽 370+ 的人存档里没有记录, 读档=永久消失)。
    #         已被人填上的槽状态字变成 BSDATA 活人值(≠0x808F) => 不会被再次武装, 幂等;
    #         游戏内死亡/改易腾出的槽引擎自己打 0x800B(0x4A4872), 与本补丁天然合流。
    #         stub 只动 eax/ecx(调用约定下 caller-saved), 不碰 esi/edi/ebp, 不 push/pop。
    #   容量: 常驻待登场槽 16 个(4c RESERVE_N) + 游戏中新腾出的槽; 每月按 登场年/生年 排序择优填补。
    #   还原: 删除本节即可(四处站点回到 clean 原文)。
    # 埋点计数器 / 桩地址: 见顶部 M() 布局(由 CAP 推导), 落地清单写 _big_layout.json
    FREEZE_VA, FREEZE_ORIG = 0x4A4D61, b'\x50\xE8\x49\x59\xFF\xFF'
    BOUND_VA, BOUND_ORIG = 0x4A4D84, b'\x66\x81\xFF\x67\x01'
    CALL_VA, GENSHUKU_VA = 0x4A4F40, 0x4A4FC0
    HOOK_VA, HOOK_ORIG = 0x4A4CC0, b'\xE8\x4B\x00\x00\x00'
    APPEAR_ROUTINE = 0x4A4D10
    EQ_STATUS0 = NEW + RESERVE_LO * STRIDE + 0x2c          # 槽354 状态字 VA
    def text_off(va):
        return tsec.PointerToRawData + (va - s_va)
    assert bytes(b[text_off(FREEZE_VA):text_off(FREEZE_VA) + 6]) == FREEZE_ORIG, '冻结站点漂移'
    assert bytes(b[text_off(BOUND_VA):text_off(BOUND_VA) + 5]) == BOUND_ORIG, '扫描界站点漂移'
    assert bytes(b[text_off(CALL_VA):text_off(CALL_VA) + 5]) == b'\xE8\x7B\x00\x00\x00', '元服 call 站点漂移'
    assert bytes(b[text_off(HOOK_VA):text_off(HOOK_VA) + 5]) == HOOK_ORIG, '月调用站点漂移'
    assert RESERVE_LO + RESERVE_N <= N0, '待登场槽必须全在存档序列化的 0..369 内'
    assert bytes(b[ed_off(APPEAR_CNT_VA):ed_off(EQ_STUB_VA) + 48]) == b'\x00' * 0x68, '登场埋点区非空'
    # (a) 冻结倒数位 + 空槽埋点
    b[text_off(FREEZE_VA):text_off(FREEZE_VA) + 6] = b'\xFF\x05' + struct.pack('<I', VACANT_CNT_VA)
    # (b) 池扫描界 0x167 -> 0x200
    b[text_off(BOUND_VA):text_off(BOUND_VA) + 5] = b'\x66\x81\xFF' + struct.pack('<H', NEW_N)
    # (c) 登场人次埋点 trampoline
    stub = b'\xFF\x05' + struct.pack('<I', APPEAR_CNT_VA)          # 6B: inc dword[APPEAR_CNT]
    stub += b'\xE9' + struct.pack('<i', GENSHUKU_VA - (APPEAR_STUB_VA + 11))  # 5B: jmp 0x4a4fc0 (下条=+11)
    b[ed_off(APPEAR_STUB_VA):ed_off(APPEAR_STUB_VA) + len(stub)] = stub
    b[text_off(CALL_VA):text_off(CALL_VA) + 5] = \
        b'\xE8' + struct.pack('<i', APPEAR_STUB_VA - (CALL_VA + 5))
    # (d) ensure_queue: 武装池尾空槽 -> 0x800B, 再进原登场例程
    eq = bytearray()
    eq += b'\xFF\x05' + struct.pack('<I', MONTH_CNT_VA)            # 6B  inc dword[MONTH_CNT]
    eq += b'\xB8' + struct.pack('<I', EQ_STATUS0)                   # 5B  mov eax, &status[354]
    eq += b'\xB9' + struct.pack('<I', RESERVE_N)                    # 5B  mov ecx, RESERVE_N
    eq += b'\x66\x81\x38' + struct.pack('<H', 0x808F)               # 6B  cmp word[eax],0x808F
    eq += b'\x75\x0B'                                               # 2B  jne .next (= +35 add eax,47)
    eq += b'\xFF\x05' + struct.pack('<I', ARMED_CNT_VA)             # 6B  inc dword[ARMED_CNT]
    eq += b'\x66\xC7\x00' + struct.pack('<H', 0x800B)               # 5B  mov word[eax],0x800B
    eq += b'\x05' + struct.pack('<I', STRIDE)                       # 5B  add eax, 47
    eq += b'\x49'                                                   # 1B  dec ecx
    eq += b'\x75' + struct.pack('<b', 16 - (len(eq) + 2))           # 2B  jne .loop (= +16)
    eq += b'\xE9' + struct.pack('<i', APPEAR_ROUTINE - (EQ_STUB_VA + len(eq) + 5))  # 5B jmp 0x4a4d10
    b[ed_off(EQ_STUB_VA):ed_off(EQ_STUB_VA) + len(eq)] = bytes(eq)
    b[text_off(HOOK_VA):text_off(HOOK_VA) + 5] = \
        b'\xE8' + struct.pack('<i', EQ_STUB_VA - (HOOK_VA + 5))
    for _v, _n in ((APPEAR_CNT_VA, 0), (VACANT_CNT_VA, 0), (MONTH_CNT_VA, 0), (ARMED_CNT_VA, 0)):
        struct.pack_into('<I', b, ed_off(_v), _n)
    # 反汇编复核: 四处站点必须还原成完整指令边界
    chk = sweep(bytes(b[text_off(FREEZE_VA):text_off(BOUND_VA) + 8]), FREEZE_VA)
    assert chk[FREEZE_VA].bytes == b'\xFF\x05' + struct.pack('<I', VACANT_CNT_VA)
    assert BOUND_VA in chk and chk[BOUND_VA].op_str.endswith('0x%x' % NEW_N), \
        '池界补丁未对齐指令/解码异常: %s' % chk.get(BOUND_VA)
    ins_c = sweep(bytes(b[text_off(CALL_VA):text_off(CALL_VA) + 5]), CALL_VA)[CALL_VA]
    assert ins_c.mnemonic == 'call' and ins_c.op_str == '0x%x' % APPEAR_STUB_VA, ins_c.op_str
    st = sweep(bytes(b[ed_off(APPEAR_STUB_VA):ed_off(APPEAR_STUB_VA) + len(stub)]), APPEAR_STUB_VA)
    assert len(st) == 2 and st[APPEAR_STUB_VA + 6].op_str == '0x%x' % GENSHUKU_VA, 'stub 解码异常'
    se = sweep(bytes(b[ed_off(EQ_STUB_VA):ed_off(EQ_STUB_VA) + len(eq)]), EQ_STUB_VA)
    assert max(se) == EQ_STUB_VA + len(eq) - 5, 'ensure_queue 解码越界/长度不符'
    assert se[max(se)].mnemonic == 'jmp' and se[max(se)].op_str == '0x%x' % APPEAR_ROUTINE
    assert se[EQ_STUB_VA + 21].op_str == '0x%x' % (EQ_STUB_VA + 34), 'arm 分支位移错'
    assert se[EQ_STUB_VA + 40].op_str == '0x%x' % (EQ_STUB_VA + 16), '循环回跳位移错'
    assert se[EQ_STUB_VA + 6].op_str.endswith('0x%x' % EQ_STATUS0), '武装基址解码错'
    assert se[EQ_STUB_VA + 16].op_str.endswith('0x808f'), '武装判据解码错'
    ins_h = sweep(bytes(b[text_off(HOOK_VA):text_off(HOOK_VA) + 5]), HOOK_VA)[HOOK_VA]
    assert ins_h.op_str == '0x%x' % EQ_STUB_VA, ins_h.op_str
    print('APPEAR-STAGE: 冻结倒数位+空槽埋点 @0x%06X(->0x%06X) ; 池界 0x167->0x%X @0x%06X ; 元服 call 转 @0x%06X -> stub 0x%06X'
          % (FREEZE_VA, VACANT_CNT_VA, NEW_N, BOUND_VA, CALL_VA, APPEAR_STUB_VA))
    print('  ensure_queue %dB @0x%06X 武装槽 %d..%d 状态字 0x808F->0x800B (基址 0x%06X) ; 月钩 @0x%06X'
          % (len(eq), EQ_STUB_VA, RESERVE_LO, RESERVE_LO + RESERVE_N - 1, EQ_STATUS0, HOOK_VA))
    print('  埋点: APPEAR_CNT(登场人次)0x%06X  VACANT_CNT(空槽遭遇)0x%06X  MONTH_CNT(月数)0x%06X  ARMED_CNT(武装)0x%06X'
          % (APPEAR_CNT_VA, VACANT_CNT_VA, MONTH_CNT_VA, ARMED_CNT_VA))

    # ---------- 4j) CHILD-PRELOAD: 开局把「已出生未登场」的孩子真实放进世界 (M2) ----------
    #   配方唯一来源 = .rev/CHILD_STATE_RECIPE.md §2; 机器码由 child_stub.py 装配并自检。
    #   排程表 = .rev/_child_preload.json (gen_child_preload.py 直读 BSDATA/SNDATA 生成) 的人手,
    #   每人 父槽/兜底城 = .rev/_kin.json (gen_kin.py: S1 槽<->oid + BSDATA 父 u16@+0x29 + 族谱),
    #   两份表在 4j 里逐条 (oid,槽) 对齐后才打包 —— 不同源直接 assert 炸掉。
    #   CHILD_BATCH 分批放量: fam13(13 族谱儿童, 默认) -> kids117 -> all280。
    #   KID_FOLLOW_FATHER=0 可关随父居住(写回孩子自己的城), 便于对照测试。
    #   两个钩子共用一块 child_pass(幂等):
    #     月钩     0x4A4CC5 `call 0x4a5370`  —— 在 4i(d) 的 ensure_queue/登场例程返回之后
    #     保存侧钩 0x47F71F `call 0x47f2a0`  —— ★方向定论(2026-10, 见 child_save 头注/child_stub 头注):
    #            0x47F71F 在 0x47F5C0 里, 而 0x47F5C0 只被**保存**派发器 0x47FC10(调用点 0x47FC40) 调用,
    #            它内部 0x47F6AF 调的是**写**链 0x47DF00(实体->档), 0x47F63E 同样是写登场标志 ——
    #            所以这一发是"整条保存链跑完、原生句柄还没关"的位置, 不是载入后。
    #            历史上把它当载入钩用(理由写成"池读入后重放"), 结论要更正:
    #              * 读档后扩展槽并不会在这里被重放; 重臂仍靠月钩(下一月 tick 到位)。
    #              * 真正的"读档即恢复"由 M6 影子档在载入派发器链尾 0x47FBEE 做(整体回填)。
    #              * 保存时多跑一趟 child_pass 无害(在岗只复臂+随父搬家, 不重跑 init_stats),
    #                且顺序在 M6 写影子档之前 => 影子档拿到的就是这趟之后的状态。
    #   不碰原剧本: 登场日程/BSDATA 一律不改, 孩子只占扩展槽, 状态全部走引擎原语设置。
    import child_stub as CS
    batch = os.environ.get('CHILD_BATCH', 'fam13')
    follow = os.environ.get('KID_FOLLOW_FATHER', '1') != '0'   # M3a 随父居住开关(关掉=写回孩子自己的城)
    # M4 元服阈值(虚岁, 引擎口径 = 0x49A5C0)。默认 15; KID_AGE_GENPUKU=99 => 只长不元服(对照跑法)。
    PUKU_AGE = int(os.environ.get('KID_AGE_GENPUKU', '15'))
    assert 5 <= PUKU_AGE <= 99, '元服阈值要在 5..99: %d' % PUKU_AGE
    pre = json.load(open('_child_preload.json', encoding='utf-8'))
    assert batch in pre['batches'], '无此批次: %s' % batch
    entries = pre['batches'][batch]
    # 亲子索引: gen_kin.py 直读 SNDATA 的 S1 段(原生池 槽<->oid/国/城) + BSDATA 父 u16@+0x29 + 族谱
    kin = json.load(open('_kin.json', encoding='utf-8'))
    assert batch in kin['batches'], 'kin 缺批次 %s (先跑 gen_kin.py)' % batch
    assert kin['batches'][batch] == [[e['oid'], e['slot']] for e in entries], \
        'kin 与 preload 的 (oid,槽) 序列不一致 —— 两份表必须同源'
    for e in entries:
        k = kin['kin'][str(e['oid'])]
        assert k['oid'] == e['oid'] and 0 <= k['pv'] <= 0xFF and 0 <= k['city'] <= 0xFF
        # 父槽只允许两种值: 原生池内(0..369, 且 kin 已保证那格的 oid 就是父亲) 或 0xffff=无父可跟
        assert k['fslot'] == 0xFFFF or 0 <= k['fslot'] < kin['meta']['pool_native'], ('父槽异常', k)
        e['fslot'], e['pv'], e['city'] = ((k['fslot'], k['pv'], k['city']) if follow
                                          else (0xFFFF, k['self_pv'], k['self_city']))
    CL = {'pool': NEW, 'sched': CHILD_SCHED_VA, 'bm': CHILD_BM_VA, 'preload': CHILD_PRELOAD_VA,
          'rearm': CHILD_REARM_VA, 'scan': CHILD_SCAN_VA, 'skip': CHILD_SKIP_VA,
          'place': CHILD_PLACE_VA, 'init5': CHILD_INIT5_VA, 'growth': CHILD_GROWTH_VA}
    ccode, cva, csrc, cins = CS.build(CHILD_PASS_VA, CL)
    sbytes = CS.sched_bytes(entries)
    assert len(entries) < CAP and CHILD_SCHED_VA + len(sbytes) <= CHILD_PASS_VA, '排程表越界'
    assert cva['child_pass'] == CHILD_PASS_VA and cva['stub_end'] <= NEW + NEW_SZ, '桩越出 .edata'
    for e in entries:
        assert N0 <= e['slot'] < CAP, ('孩子只能放扩展槽', e)
        assert not (RESERVE_LO <= e['slot'] < RESERVE_LO + RESERVE_N), ('不得占用 4i 待登场槽', e)
        p = ed_off(NEW + e['slot'] * STRIDE)
        assert struct.unpack_from('<H', bytes(b[p + 0x2c:p + 0x2e]), 0)[0] == 0x808F, ('槽非空', e)
        assert bytes(b[ed_off(SUR_NEW + e['slot'] * 7):ed_off(SUR_NEW + e['slot'] * 7) + 7]) == b'\x00' * 7
        assert bytes(b[ed_off(GIV_NEW + e['slot'] * 7):ed_off(GIV_NEW + e['slot'] * 7) + 7]) == b'\x00' * 7
    b[ed_off(CHILD_BM_VA):ed_off(CHILD_BM_VA) + CAP // 8] = b'\x00' * (CAP // 8)
    b[ed_off(CHILD_SCHED_VA):ed_off(CHILD_SCHED_VA) + len(sbytes)] = sbytes
    b[ed_off(CHILD_PASS_VA):ed_off(CHILD_PASS_VA) + len(ccode)] = ccode
    for _v in (CHILD_PRELOAD_VA, CHILD_REARM_VA, CHILD_GENPUKU_VA, CHILD_SCAN_VA,
               CHILD_SKIP_VA, CHILD_PLACE_VA, CHILD_INIT5_VA):
        struct.pack_into('<I', b, ed_off(_v), 0)

    # ---- 4j-bis) M3b-2 成长结算桩 + M4 元服 child_growth_pass (月钩的第二段 call; 保存侧钩不调) ----
    #   成长: 逐条扫排程表 -> 只处理"儿童态且在岗"的孩子 -> 月守卫(KID_TAB+9) -> 按年龄档位攒分
    #         -> 满 100 就给"与史实成年值差距最大"的一维 +1 (走原生字段写手, 不自加)。
    #   元服(M4): 虚岁 >= PUKU_AGE 的孩子当场转成人 —— nibble:=0xf + 清排除位, 然后
    #         随父 0x4A5100(本人,父) [父=大名再补 bit11] / 无父或挂载失败 0x4A5290(本人) 挂国主或浪人化,
    #         归属码写 KID_TAB+10, 人次写 CHILD_GENPUKU (只在该月一次)。★不改五维, 不动原剧本登场。
    #   桩只用引擎原语: 年龄 0x49A5C0 / 五维写手 0x4A2F80+d*0x20 / 天花板 BSDATA 镜像 0x524A20
    #                  / 归属簇 0x49A6B0,0x49A6D0,0x49A800,0x4A5100,0x4A5290 (probe_genpuku*.txt)。
    import child_growth as CG
    assert cva['stub_end'] <= CHILD_GROWTH_VA, \
        '预载桩(%dB)越出预留位 0x1200..0x1400' % (cva['stub_end'] - CHILD_PASS_VA)
    GL = {'sched': CHILD_SCHED_VA, 'pool': NEW, 'kid_tab': KID_TAB_VA, 'esz': CS.ESZ,
          'ring': CMD_RING_VA, 'bm': CHILD_BM_VA,
          'act_tab': ACT_TAB_VA, 'teach_tab': TEACH_TAB_VA,
          'c_pass': GC_IDX['GROWTH_PASS'], 'c_settled': GC_IDX['GROWTH_SETTLED'],
          'c_dupm': GC_IDX['GROWTH_DUPM'], 'c_freeze': GC_IDX['GROWTH_FREEZE'],
          'c_full': GC_IDX['GROWTH_FULL'], 'c_natural': GC_IDX['GROWTH_NATURAL'],
          'c_cmd': GC_IDX['GROWTH_CMD'], 'c_roll': GC_IDX['GROWTH_ROLL'],
          'c_fail': GC_IDX['GROWTH_FAIL'], 'c_ok': GC_IDX['GROWTH_OK'],
          'c_reject': GC_IDX['GROWTH_REJECT'],
          'puku_age': PUKU_AGE, 'genpuku': CHILD_GENPUKU_VA,
          'c_mount': GC_IDX['GROWTH_PUKU_MOUNT'], 'c_ronin': GC_IDX['GROWTH_PUKU_RONIN'],
          # ---- M3d 三通道埋点 (TEACH_LORD/PARENT 自动教席会 >0; SHOPE 待 M3c UI 仍 0) ----
          'teach_lord': GC_IDX['TEACH_LORD'], 'teach_parent': GC_IDX['TEACH_PARENT'],
          'teach_shope': GC_IDX['TEACH_SHOPE'],
          'debug_log': cva['debug_log']}
    gcode, gva, gsrc, gins = CG.build(CHILD_GROWTH_VA, GL)
    assert gva['child_growth_pass'] == CHILD_GROWTH_VA, gva
    assert CHILD_GROWTH_VA + len(gcode) <= GROWTH_CNT_VA, \
        '成长桩 %dB 越出预留位 0x1400..0x2000' % len(gcode)
    b[ed_off(CHILD_GROWTH_VA):ed_off(CHILD_GROWTH_VA) + len(gcode)] = gcode
    print('  成长桩 %dB @0x%06X..0x%06X (位 0x1400..0x2000, 用 %d%%) ; 档位 %s/月 满 %d 加点'
          % (len(gcode), CHILD_GROWTH_VA, CHILD_GROWTH_VA + len(gcode),
             100 * len(gcode) // (GROWTH_CNT_VA - CHILD_GROWTH_VA), '/'.join(map(str, CG.RATES)),
             CG.ACC_FULL))
    for _site, _orig in CS.SITE_ORIG.items():
        assert bytes(b[text_off(_site):text_off(_site) + 5]) == _orig, '儿童钩子站点漂移 %08X' % _site
    for _site, _ent in ((CS.MONTH_SITE, cva['month_hook']), (CS.LOAD_SITE, cva['load_hook'])):
        b[text_off(_site):text_off(_site) + 5] = b'\xE8' + struct.pack('<i', _ent - (_site + 5))
        _i = sweep(bytes(b[text_off(_site):text_off(_site) + 5]), _site)[_site]
        assert _i.mnemonic == 'call' and _i.op_str == '0x%x' % _ent, \
            ('儿童钩子解码异常 %08X -> %s' % (_site, _i.op_str))
    # R1 回归: 登场例程算实体指针用的槽界(0x4A4F1A `cmp si,0x172`)必须已被 P2 抬到 CAP,
    #   否则扩展槽被武装时 0x4A4FC0 会收到 NULL 实体 (`test byte[0+0x2d],7`) 直接 GPF。
    _rb = bytes(b[text_off(0x4A4F1A):text_off(0x4A4F1A) + 5])
    assert _rb[:3] == b'\x66\x81\xfe' and struct.unpack_from('<H', _rb, 3)[0] == CAP, \
        'R1: 0x4A4F1A 槽界不是 CAP: %s' % _rb.hex()
    _dyn = sum(1 for e in entries if e['fslot'] != 0xFFFF)
    _puku_now = sum(1 for e in entries if e.get('age_engine', e['age']) >= PUKU_AGE)
    print('  元服(M4): 阈值 虚岁>=%d ; 开局即到龄 %d 人 => 首月 CHILD_GENPUKU 应 = %d, '
          '且 GROWTH_FREEZE 与 GROWTH_PUKU_MOUNT+RONIN 同值'
          % (PUKU_AGE, _puku_now, _puku_now))
    print('CHILD-PRELOAD: 批次 %s = %d 人 (槽 %d..%d) ; 桩 %dB child_pass@0x%06X month@0x%06X load@0x%06X'
          % (batch, len(entries), entries[0]['slot'], entries[-1]['slot'],
             len(ccode), cva['child_pass'], cva['month_hook'], cva['load_hook']))
    print('  随父居住 = %s ; 父在原生池 %d/%d 走动态(每月读父亲现城), 其余用静态兜底城%s'
          % ('开' if follow else '关', _dyn, len(entries),
             '  [开关已关: 全部写回孩子自己的 BSDATA 城 = 不搬家]' if not follow else ''))
    print('  钩子 月@0x%06X(%s) 载入@0x%06X(%s) ; 排程表 %dB @0x%06X ; 位图 %dB @0x%06X'
          % (CS.MONTH_SITE, hex(CS.MONTH_JMP), CS.LOAD_SITE, hex(CS.LOAD_JMP),
             len(sbytes), CHILD_SCHED_VA, CAP // 8, CHILD_BM_VA))
    print('  埋点 PRELOAD 0x%06X REARM 0x%06X GENPUKU 0x%06X SCAN 0x%06X SKIP 0x%06X PLACE 0x%06X'
          % (CHILD_PRELOAD_VA, CHILD_REARM_VA, CHILD_GENPUKU_VA, CHILD_SCAN_VA,
             CHILD_SKIP_VA, CHILD_PLACE_VA))

    # ---------- 4j2) M3b 数据区: 成长埋点 / KID_TAB / CMD_RING / 回家菜单数组 ----------
    #   本轮只"圈地 + 清零 + 记账进 json": 桩代码(M3b-2)与 UI(M3c)按同一张表落位, 不再改布局。
    regions = [('GROWTH_CNT', GROWTH_CNT_VA, 0x100), ('KID_TAB', KID_TAB_VA, CAP * KID_ESZ),
               ('CMD_RING', CMD_RING_VA, 0x220), ('MENU_PTR', MENU_PTR_VA, 0x40),
               ('MENU_CODE', MENU_CODE_VA, 0x20), ('PANEL', PANEL_VA, 0x20),
               ('ACT_TAB', ACT_TAB_VA, 0x28), ('TEACH_TAB', TEACH_TAB_VA, 0x8),
               ('MENU_STR', MENU_STR_VA, 0x240), ('DEC100', DEC100_VA, 0xC8),
               ('NAME_BUF', NAME_BUF_VA, 0x120), ('SLOT_ARR', SLOT_ARR_VA, 0x20),
               ('SUB_PTR', SUB_PTR_VA, 0x40), ('ACT_PTR', ACT_PTR_VA, 0x30),
               ('TEACH_PTR', TEACH_PTR_VA, 0x20), ('TIER_PTR', TIER_PTR_VA, 0x20),
               # ★ MENU_STUB 的窗口到 SC_CODE 为止 (0x800B), 不是早年的 0x500:
               #   cm_hook 196B + cm_foster 1189B = 1385B 早就超过 0x500, 旧值只是"圈地口令"失真,
               #   真越界却没人拦 => 这里按真实窗口给你的邻居 SC_CODE 留足。
               ('MENU_SCR', MENU_SCR_VA, 0x20),
               ('MENU_STUB', MENU_STUB_VA, SC_CODE_VA - MENU_STUB_VA),
               ('SC_CODE', SC_CODE_VA, 0x600), ('SC_DATA', SC_DATA_VA, SV.SC_DATA_SZ),
               ('KD_STR', KD_STR_VA, 0x100), ('KD_DATA', KD_DATA_VA, 0x80),
               ('KD_CODE', KD_CODE_VA, KD_CODE_SZ),
               ('MSG_STR', MSG_STR_VA, MSG_STR_SZ), ('FOSTER', FOSTER_VA, FOSTER_SZ),
               ('BIRTH_AVAIL', BIRTH_AVAIL_VA, BIRTH_AVAIL_SZ),
               ('BIRTH_LABEL', BIRTH_LABEL_VA, BIRTH_LABEL_SZ),
               ('BIRTH_PICK', BIRTH_PICK_VA, 4),
               ('BIRTH_PROMPT', BIRTH_PROMPT_VA, BIRTH_PROMPT_SZ),
               ('BIRTH_NAME_TMP', BIRTH_NAME_TMP_VA, BIRTH_NAME_TMP_SZ),
               ('TREE_DYN', TREE_DYN_VA, TREE_DYN_SZ),
               ('BIRTH_POOL', BIRTH_POOL_VA, BIRTH_POOL_SZ),
               ('BIRTH_USED', BIRTH_USED_VA, BIRTH_USED_SZ),
               ('BIRTH_CODE', BIRTH_CODE_VA, BIRTH_CODE_SZ)]
    prev_end = cva['stub_end']                           # 预载桩尾(含两块钩子): 数据区不得与桩代码重叠
    for nm, va, sz in regions:
        assert va >= prev_end, 'M3b 区域 %s 与桩代码重叠 (0x%06X < 0x%06X)' % (nm, va, prev_end)
        assert va + sz <= NEW + MOD_OFF + MOD_SZ, 'M3b 区域 %s 越出 MOD_SZ (抬 MOD_SZ 或挪偏移)' % nm
        assert sz % 4 == 0, nm
        b[ed_off(va):ed_off(va) + sz] = b'\x00' * sz
        prev_end = va + sz
    # M3b-3 常数表落盘 (桩里 `movzx ..., byte [eax*4 + ACT_TAB]` 读的就是这 40B)
    _atab, _ttab = CG.act_tab_bytes(), CG.teach_tab_bytes()
    assert len(_atab) % 4 == 0 and len(_atab) // 4 == len(CG.ACTS), (_atab,)
    assert len(_ttab) == len(CG.TEACHERS), (_ttab,)
    b[ed_off(ACT_TAB_VA):ed_off(ACT_TAB_VA) + len(_atab)] = _atab
    b[ed_off(TEACH_TAB_VA):ed_off(TEACH_TAB_VA) + len(_ttab)] = _ttab

    # ---------- 4j3a) M3c-2/M5: 先装「培养详情 + 反馈小框」面板, 拿到 kd_msg 入口 ----------
    #   为什么提前: cm_foster 提交成功要 call kd_msg, 而 kd_msg 是面板的最后一段,
    #   只能先装配才知道它的 VA。面板只依赖 KD_DATA/KD_STR 的绝对地址, 与菜单桩无关, 提前安全。
    import child_menu as CM
    import kid_panel as KP
    _kdADR = {_k: KD_DATA_VA + _v for _k, _v in KP.KD.items()}
    _kstr = KP.str_pool_bytes()
    assert len(_kstr) <= 0x100, '详情面板串池溢出 (%dB)' % len(_kstr)
    b[ed_off(KD_STR_VA):ed_off(KD_STR_VA) + len(_kstr)] = _kstr
    # 串池每条 [u8 长度][GBK][NUL]: 记下每条的"字节首址"与"字符数"
    _koff, _kent = 0, []
    for _s in KP.STRINGS:
        _n = len(_s.encode('gbk'))
        _kent.append((KD_STR_VA + _koff + 1, _n))
        _koff += 1 + _n + 1
    assert _koff == len(_kstr), (_koff, len(_kstr))
    for _i, _nm in enumerate(('统率', '武力', '内政', '外交', '魅力')):
        assert KP.STRINGS[KP.S_DIM0 + _i] == _nm, (_i, KP.STRINGS[KP.S_DIM0 + _i])
    # 五维标签指针表 (kd_bars 循环按维取)
    for _i in range(5):
        struct.pack_into('<I', b, ed_off(KD_DATA_VA + KP.KD['strtab']) + _i * 4,
                         _kent[KP.S_DIM0 + _i][0] - 1)
    KL = {'pool': NEW, 'sched': CHILD_SCHED_VA, 'kid': KID_TAB_VA,
          'act_tab': ACT_TAB_VA, 'teach_tab': TEACH_TAB_VA, 'esz': CS.ESZ,
          'player_ent': CG.PLAYER_ENT,
          # M5: 进度表读"本月已用次数", 反馈小框读 msg_* 与台词串池
          'f_cnt': FOSTER_VA + FO['cnt'],
          'msg_act': FOSTER_VA + FO['msg_act'], 'msg_slot': FOSTER_VA + FO['msg_slot'],
          'msg_str': MSG_STR_VA, 'msg_row': CM.MS_STR_ROW,
          'msg_line0': CM.MS_LINE0, 'msg_hint_off': CM.MS_MSG_HINT * CM.MS_STR_ROW,
          'age_puku': CG.AGE_PUKU,
          'giv': GIV_NEW, 'sur': SUR_NEW}   # 反馈小框现场拼孩子名 (名表 7B + 姓表 7B)
    for _k, _v in _kdADR.items():
        KL['kd_' + _k] = _v
    for _nm, _i in (('str_title', KP.S_TITLE), ('str_p', KP.S_P), ('str_bond', KP.S_BOND),
                    ('str_hint', KP.S_HINT), ('str_cnt', KP.S_CNT), ('str_dims', KP.S_DIMS),
                    ('str_puku', KP.S_PUKU), ('str_left', KP.S_LEFT)):
        KL[_nm], KL['len_' + _nm[4:]] = _kent[_i][0], _kent[_i][1]
    kcode, ksrc, _kENT = KP.build_panel(KD_CODE_VA, KL)
    KP.selfcheck_panel(kcode, KD_CODE_VA, KL)
    assert KD_CODE_VA + len(kcode) <= MSG_STR_VA, \
        'M3c-2 面板桩越界 (%dB, 会吃掉 MSG_STR)' % len(kcode)
    b[ed_off(KD_CODE_VA):ed_off(KD_CODE_VA) + len(kcode)] = kcode
    KD_MSG_VA = _kENT['msg']
    print('M3C-PANEL: 详情面板 %dB @0x%06X (反馈小框 @0x%06X) ; 串池 %dB @0x%06X ; 参数区 @0x%06X ; '
          '复用族谱段 resolve/make_res/free_res/wait_rel/pump'
          % (len(kcode), KD_CODE_VA, KD_MSG_VA, len(_kstr), KD_STR_VA, KD_DATA_VA))

    # ---------- 4j3b) M5: 门禁/确认/反馈 的串池 + 指针数组 + 活动天数表 ----------
    _msp = CM.msg_str_pool_bytes()
    assert len(_msp) == MSG_STR_SZ, (len(_msp), MSG_STR_SZ)
    b[ed_off(MSG_STR_VA):ed_off(MSG_STR_VA) + len(_msp)] = _msp
    b[ed_off(FOSTER_VA + FO['act_days']):
      ed_off(FOSTER_VA + FO['act_days']) + len(CG.ACT_DAYS)] = bytes(CG.ACT_DAYS)
    _ms = lambda _i: MSG_STR_VA + _i * CM.MS_STR_ROW
    struct.pack_into('<2I', b, ed_off(FOSTER_VA + FO['confirm']),
                     _ms(CM.MS_OK), _ms(CM.MS_CANCEL))
    # 费用确认框的三槽指针数组: 运行时由 cm_foster 按活动码现场改写 (这里填默认值便于静态核对)
    struct.pack_into('<3I', b, ed_off(FOSTER_VA + FO['cost_arr']),
                     _ms(CM.MS_COST0), _ms(CM.MS_OK), _ms(CM.MS_CANCEL))
    for _off, _i in ((FO['deny_month'], CM.MS_DENY_MONTH),
                     (FO['deny_time'], CM.MS_DENY_TIME),
                     (FO['deny_gold'], CM.MS_DENY_GOLD)):
        struct.pack_into('<I', b, ed_off(FOSTER_VA + _off), _ms(_i))
    print('M5-GATE: 月上限 %d 次 / 每日 %d 金 / 天数表 %s ; 串池 %dB @0x%06X ; 计数区 @0x%06X'
          % (CG.MONTHLY_CAP, CG.GOLD_PER_DAY, CG.ACT_DAYS, len(_msp), MSG_STR_VA, FOSTER_VA))

    # ---------- 4j3d) 生孩子: 500 个真名串池 + 已选标记清零 + 菜单标签行 ----------
    _bnp = CM.birth_name_pool_bytes()
    assert len(_bnp) == BIRTH_POOL_SZ, (len(_bnp), BIRTH_POOL_SZ)
    b[ed_off(BIRTH_POOL_VA):ed_off(BIRTH_POOL_VA) + len(_bnp)] = _bnp
    # USED 上面按区域表清过零 (0 = 没被选过); AVAIL 是运行期写的, 静态留零即可。
    assert bytes(b[ed_off(BIRTH_USED_VA):ed_off(BIRTH_USED_VA) + BIRTH_USED_SZ]) == \
        b'\x00' * BIRTH_USED_SZ, '已选标记区必须从全零起步'
    _blb = CM.birth_label_bytes()
    assert len(_blb) == BIRTH_LABEL_SZ, (len(_blb), BIRTH_LABEL_SZ)
    b[ed_off(BIRTH_LABEL_VA):ed_off(BIRTH_LABEL_VA) + len(_blb)] = _blb
    print('BIRTH-NAME: %d 个真名 %dB @0x%06X (每次开框供 %d 个, 已选标记 %dB @0x%06X) ; 菜单标签 %dB @0x%06X'
          % (CM.BIRTH_NAME_COUNT, len(_bnp), BIRTH_POOL_VA, CM.BIRTH_NAME_OFFER,
             BIRTH_USED_SZ, BIRTH_USED_VA, len(_blb), BIRTH_LABEL_VA))

    # ---------- 4j3e) 生孩子: 空槽扫描的下界 (新生孩子从哪一格起找) ----------
    #   扩展槽不是空地: 371..462 = P3b 休眠人物 (姓/名行已在构建期打死), 463..476 = 儿童预载批次。
    #   桩里"状态字 0x808F"这道门只看实体槽, 看不出姓名行有没有人预定 —— 从 N0(370) 起扫的话,
    #   第二个孩子就会盖掉某个还没登场的休眠人物的姓/名行 (他日后登场顶着孩子的名字)。
    #   所以本构建里已有的最大占用槽 +1 才是新生孩子的起点。
    _taken = [e['slot'] for e in entries] + [d['slot'] for d in dorm]
    BIRTH_SLOT_LO = max([N0 - 1] + _taken) + 1
    assert BIRTH_SLOT_LO < CAP, '扩展槽已被占满, 没有生孩子的余量'
    print('BIRTH-SLOT-LO: 新生孩子从槽 %d (0x%X) 起找 (原生 0..%d / 休眠 %d..%d / 预载 %d..%d 之后; 余 %d 格)'
          % (BIRTH_SLOT_LO, BIRTH_SLOT_LO, N0 - 1, min(d['slot'] for d in dorm),
             max(d['slot'] for d in dorm), entries[0]['slot'], entries[-1]['slot'],
             CAP - BIRTH_SLOT_LO))

    # ---------- 4j3c) M3c: 回家菜单「培养孩子」+ M5 门禁/扣费/推天数/反馈 ----------
    #   三处补丁: 0x4CD563(构建器弹菜单前) -> cm_hook 拷表+尾追一项+自译序号;
    #             0x4CD390 `cmp eax,6` -> 7;  0x4CD47C 跳转表第 8 槽(原对齐 NOP) -> cm_foster。
    #   原生 0..6 六个处理逐字节不动; 取消/其余项的行为差别只在"翻译由我们做"。
    ML = {'menu_ptr': MENU_PTR_VA, 'menu_code': MENU_CODE_VA, 'str_va': MENU_STR_VA,
          'pool': NEW, 'bm': CHILD_BM_VA, 'kid': KID_TAB_VA, 'ring': CMD_RING_VA,
          'name_buf': NAME_BUF_VA, 'slot_arr': SLOT_ARR_VA, 'sub_ptr': SUB_PTR_VA,
          'act_ptr': ACT_PTR_VA, 'teach_ptr': TEACH_PTR_VA, 'tier_ptr': TIER_PTR_VA,
          'dec100': DEC100_VA, 'giv': GIV_NEW, 'sur': SUR_NEW, 'cap': CAP,
          'c_menu': GC_IDX['MENU_COUNT'], 'c_panel': GC_IDX['PANEL_OPEN'],
          'c_push': GC_IDX['CMD_PUSH'], 'c_notcity': GC_IDX['KID_NOTSAME_CITY'],
          'c_nav': GC_IDX['PAGE_NAV'], 'c_rows': GC_IDX['PAGE_ROWS'],
          'c_birth': GC_IDX['BIRTH_COUNT'],
          'last_slot': GC_IDX['KID_LAST_SLOT'], 'last_act': GC_IDX['KID_LAST_ACT'],
          # M3c-2 培养详情面板 + M5 反馈小框入口
          'kd_show': KD_CODE_VA, 'kd_msg': KD_MSG_VA,
          # M5: 月计数 / 花费中间量 / 活动天数表 / 三种拒绝 + 确认框
          'f_ym': FOSTER_VA + FO['ym'], 'f_cnt': FOSTER_VA + FO['cnt'],
          'f_days': FOSTER_VA + FO['days'], 'f_gold': FOSTER_VA + FO['gold'],
          'msg_act': FOSTER_VA + FO['msg_act'], 'msg_slot': FOSTER_VA + FO['msg_slot'],
          'act_days': FOSTER_VA + FO['act_days'],
          # M5b: 打开菜单时先把孩子「所在城」同步成父亲当前城 (child_pass 幂等, 内含 place_child)
          'child_pass': cva['child_pass'],
          'confirm_ptr': FOSTER_VA + FO['confirm'],
          'cost_arr': FOSTER_VA + FO['cost_arr'],
          'msg_str': MSG_STR_VA,
          'deny_month_ptr': FOSTER_VA + FO['deny_month'],
          'deny_time_ptr': FOSTER_VA + FO['deny_time'],
          'deny_gold_ptr': FOSTER_VA + FO['deny_gold'],
          # 生孩子: 名字池 / 本次可选表 / 已选标记 / 标志表 / 日期 / 实例化 / 状态原语
          'name_pool': BIRTH_POOL_VA,
          'avail': BIRTH_AVAIL_VA, 'avail_n': BIRTH_AVAILN_VA, 'used': BIRTH_USED_VA,
          'birth_label': BIRTH_LABEL_VA,
          'flagtab': 0x519288,
          'date_y': 0x5205F0,
          'surname_tab': GIV_NEW,
          'child_bm': CHILD_BM_VA,
          # 生孩子: 码 7 只有一格跳转表槽 (0x4CD47C; 下一槽 0x4CD480 = 构建器自己的序言),
          #   所以"生孩子"不发新码: 钩子把选中行记进 BIRTH_PICK, cm_foster 头部按它分流到这里。
          'pick': BIRTH_PICK_VA,
          'birth_handler': BIRTH_CODE_VA,
          'sched': CHILD_SCHED_VA,
          'sched_end': CHILD_PASS_VA,
          'slot_lo': BIRTH_SLOT_LO,
          # 出生提示: 三行指针数组 + 运行时拼的姓名串缓冲
          'msg_arr': BIRTH_PROMPT_VA, 'name_tmp': BIRTH_NAME_TMP_VA}
    for _k, _v in _kdADR.items():
        ML['kd_' + _k] = _v
    ML.update(CM.scratch_layout(MENU_SCR_VA))
    hcode, hsrc = CM.build_hook(MENU_STUB_VA, ML)
    CM.selfcheck_hook(hcode, MENU_STUB_VA, ML)
    MENU_FOSTER_VA = _align(MENU_STUB_VA + len(hcode), 0x10)
    fcode, fsrc = CM.build_foster(MENU_FOSTER_VA, ML)
    CM.selfcheck_foster(fcode, MENU_FOSTER_VA, ML)
    MENU_BIRTH_VA = BIRTH_CODE_VA
    bcode, bsrc = CM.build_birth(MENU_BIRTH_VA, ML)
    CM.selfcheck_birth(bcode, MENU_BIRTH_VA, ML)
    assert MENU_BIRTH_VA + len(bcode) <= NEW + MOD_OFF + MOD_SZ, \
        'M3c 桩越出 MOD_SZ (钩子 %dB + 培养 %dB + 生孩 %dB)' % (len(hcode), len(fcode), len(bcode))
    # ★ 紧邻上一家才是真门禁: 只查 MOD_SZ 的话, 培养处理悄悄长过窗口就会把 sidecar 桩的前半截
    #   吃掉 (症状 = 点培养后 AV, 而只查总边界的旧断言完全看不出来)。
    assert MENU_STUB_VA + len(hcode) <= MENU_FOSTER_VA, \
        'M3c 钩子 %dB 压到培养处理 (%d 处未跳)' % (len(hcode), MENU_STUB_VA + len(hcode) - MENU_FOSTER_VA)
    assert MENU_FOSTER_VA + len(fcode) <= SC_CODE_VA, \
        'M3c 培养处理 %dB 越出 MENU_STUB 窗口 0x%X..0x%X (缺 %dB)' \
        % (len(fcode), MENU_FOSTER_VA, SC_CODE_VA, MENU_FOSTER_VA + len(fcode) - SC_CODE_VA)
    assert MENU_BIRTH_VA + len(bcode) <= MENU_BIRTH_VA + BIRTH_CODE_SZ, \
        'M3c 生孩处理 %dB 越出 BIRTH_CODE 窗口 0x%X+%d (缺 %dB)' \
        % (len(bcode), MENU_BIRTH_VA, BIRTH_CODE_SZ,
           MENU_BIRTH_VA + len(bcode) - MENU_BIRTH_VA - BIRTH_CODE_SZ)
    b[ed_off(MENU_STUB_VA):ed_off(MENU_STUB_VA) + len(hcode)] = hcode
    b[ed_off(MENU_FOSTER_VA):ed_off(MENU_FOSTER_VA) + len(fcode)] = fcode
    b[ed_off(MENU_BIRTH_VA):ed_off(MENU_BIRTH_VA) + len(bcode)] = bcode
    # 菜单数据: 串池 / DEC100 / 三级静态子菜单指针数组
    _sp = CM.str_pool_bytes()
    assert len(_sp) == 0x240 and len(CM.dec100_bytes()) == 0xC8, (len(_sp),)
    b[ed_off(MENU_STR_VA):ed_off(MENU_STR_VA) + len(_sp)] = _sp
    b[ed_off(DEC100_VA):ed_off(DEC100_VA) + 0xC8] = CM.dec100_bytes()
    for _va, _first, _n in ((ACT_PTR_VA, CM.S_ACT0, len(CG.ACTS)),
                            (TEACH_PTR_VA, CM.S_TEACH0, len(CG.TEACHERS)),
                            (TIER_PTR_VA, CM.S_TIER0, len(CM.TIER_NAMES))):
        _pb = CM.submenu_ptr_bytes(MENU_STR_VA, _first, _n)
        assert len(_pb) <= {ACT_PTR_VA: 0x30, TEACH_PTR_VA: 0x20, TIER_PTR_VA: 0x20}[_va], _va
        b[ed_off(_va):ed_off(_va) + len(_pb)] = _pb
    # 站点原字节必须逐字吻合 (防止上游补丁链漂移), 然后落补丁 + 回环解码
    for _site, _orig, _sz in ((CM.HOOK_MENU_SITE, CM.HOOK_MENU_ORIG, 5),
                              (CM.CODE_LIMIT_SITE, CM.CODE_LIMIT_ORIG, 1),
                              (CM.TABLE8_SITE, CM.TABLE8_ORIG, 4)):
        assert bytes(b[text_off(_site):text_off(_site) + _sz]) == _orig, \
            'M3c 站点漂移 %08X: %s' % (_site, bytes(b[text_off(_site):text_off(_site) + _sz]).hex())
    b[text_off(CM.HOOK_MENU_SITE):text_off(CM.HOOK_MENU_SITE) + 5] = \
        CM.jmp_rel(CM.HOOK_MENU_SITE, MENU_STUB_VA)
    b[text_off(CM.CODE_LIMIT_SITE)] = 0x08
    struct.pack_into('<I', b, text_off(CM.TABLE8_SITE), MENU_FOSTER_VA)
    _hi = sweep(bytes(b[text_off(CM.HOOK_MENU_SITE):text_off(CM.HOOK_MENU_SITE) + 5]),
                CM.HOOK_MENU_SITE)[CM.HOOK_MENU_SITE]
    assert _hi.mnemonic == 'jmp' and _hi.op_str == '0x%x' % MENU_STUB_VA, _hi.op_str
    _ci = sweep(bytes(b[text_off(0x4CD38E):text_off(0x4CD38E) + 16]), 0x4CD38E)
    assert _ci[0x4CD38E].op_str == 'eax, 8' and _ci[0x4CD397].mnemonic == 'jmp', \
        [(_x.address, _x.mnemonic, _x.op_str) for _x in sorted(_ci.values())][:4]
    assert struct.unpack_from('<I', bytes(b), text_off(CM.TABLE8_SITE))[0] == MENU_FOSTER_VA
    MOD_USED = prev_end - (NEW + MOD_OFF)
    print('M3C-MENU: 钩子 %dB @0x%06X -> 培养 %dB @0x%06X -> 生孩 %dB @0x%06X ; 串池 %d 项 x %dB @0x%06X ; 分页 每页%d人(TKID_PAGE_KIDS)'
          % (len(hcode), MENU_STUB_VA, len(fcode), MENU_FOSTER_VA, len(bcode), MENU_BIRTH_VA,
             CM.STR_N, CM.STR_ROW, MENU_STR_VA, CM.PAGE_KIDS))
    print('  分页埋点 PAGE_ROWS(最大行数)0x%06X  PAGE_NAV(翻页次数)0x%06X  BIRTH_COUNT(生孩子)0x%06X'
          '  —— fam13 单城最多 6 个孩子: 每页 %d 人 => 6<=%d 不生成导航行(PAGE_NAV 恒 0); 想看翻页就 TKID_PAGE_KIDS=2 构建(6 人翻 3 页)'
          % (GC_IDX['PAGE_ROWS'], GC_IDX['PAGE_NAV'], GC_IDX['BIRTH_COUNT'], CM.PAGE_KIDS, CM.PAGE_KIDS))
    print('M3C-PATCH: 0x%06X 钩 %s | 0x%06X cmp 6->8 | 0x%06X 表槽7=%s'
          % (CM.HOOK_MENU_SITE, CM.jmp_rel(CM.HOOK_MENU_SITE, MENU_STUB_VA).hex(),
             CM.CODE_LIMIT_SITE, CM.TABLE8_SITE, '%08X' % MENU_FOSTER_VA))

    MOD_USED = prev_end - (NEW + MOD_OFF)
    print('M3B-TABS: ACT %dB @0x%06X (%s) ; TEACH %dB @0x%06X (%s)'
          % (len(_atab), ACT_TAB_VA,
             ' '.join('%s=%s+%d%%' % (nm, CG.DIM_NAME[d], bb) for nm, d, bb in CG.ACTS),
             len(_ttab), TEACH_TAB_VA,
             ' '.join('%s+%d%%' % (nm, t) for nm, t in CG.TEACHERS)))
    print('M3B-REGIONS: ' + ' '.join('%s 0x%06X+%dB' % (nm, va, sz) for nm, va, sz in regions))
    print('  吃到 M(0x%X) / MOD_SZ 0x%X (余 %dB) ; 桩预留 0x1200..0x1400 预载 + 0x1400..0x2000 成长'
          % (MOD_USED, MOD_SZ, MOD_SZ - MOD_USED))

    # ---------- 4j4) M6: sidecar 影子存档 (扩展槽人物 + 培养状态跨存档不丢) ----------
    #   原生存档序列化器只循环 0..369 (0x172 = 文件格式锚, 保留不动), 所以扩展槽 370..CAP-1 的人
    #   和 KID_TAB/CMD_RING/儿童位图 在 SAVEDATA.TR2 里没有位置 —— 读档即消失。这里在两个派发器
    #   链尾各顶一发 `call 0x47D850`(每方向恰一次, 且在原生池整体恢复之后), 旁路写一份 TKMODSAVE_<槽>.DAT。
    SDL = {'pool': NEW, 'stride': STRIDE, 'n0': N0, 'cap': CAP, 'giv': GIV_NEW, 'sur': SUR_NEW,
           'bm': CHILD_BM_VA, 'kid_tab': KID_TAB_VA, 'kid_esz': KID_ESZ, 'ring': CMD_RING_VA,
           'sect_va': NEW, 'sect_sz': NEW_SZ, 'data_delta': SC_DATA_VA - SC_CODE_VA,
           'ctr': {nm: GC_IDX[nm] for nm in SV.SC_CTRS}}
    scode, sva, ssrc, sins = SV.build(SC_CODE_VA, SDL)
    assert sva['code_end'] <= SC_DATA_VA, \
        'M6 桩 %dB 吃进 SC_DATA (0x%06X > 0x%06X)' % (len(scode), sva['code_end'], SC_DATA_VA)
    b[ed_off(SC_CODE_VA):ed_off(SC_CODE_VA) + len(scode)] = scode
    # SC_DATA: 路径模板 / 六段描述符表 / 尾空槽模板 —— 句柄·槽号·摘要·游标留着运行期用, 静态清零
    bt, pb = SV.blktab_bytes(SDL), SV.path_bytes()
    assert len(bt) == 0x38 and len(pb) == SV.PATH_SZ, (len(bt), len(pb))
    b[ed_off(SC_DATA_VA + SV.D_PATH):ed_off(SC_DATA_VA + SV.D_PATH) + len(pb)] = pb
    b[ed_off(SC_DATA_VA + SV.D_BLK):ed_off(SC_DATA_VA + SV.D_BLK) + len(bt)] = bt
    b[ed_off(SC_DATA_VA + SV.D_TMPL):ed_off(SC_DATA_VA + SV.D_TMPL) + len(tmpl)] = tmpl
    # 两处站点原字节必须逐字吻合(防上游补丁链漂移), 然后打钩 + 回读解码
    for _site, _orig, _tgt, _back in ((SV.SITE_SAVE, SV.ORIG_SAVE, SC_CODE_VA, SV.BACK_SAVE),
                                      (SV.SITE_LOAD, SV.ORIG_LOAD, sva['tramp_load'], SV.BACK_LOAD)):
        assert bytes(b[text_off(_site):text_off(_site) + 5]) == _orig, \
            'M6 站点漂移 %08X: %s' % (_site, bytes(b[text_off(_site):text_off(_site) + 5]).hex())
        b[text_off(_site):text_off(_site) + 5] = CM.jmp_rel(_site, _tgt)
        _hi = sweep(bytes(b[text_off(_site):text_off(_site) + 5]), _site)[_site]
        assert _hi.mnemonic == 'jmp' and _hi.op_str == '0x%x' % _tgt and _site + 5 == _back, \
            (_site, _hi.mnemonic, _hi.op_str)
    print('M6-SIDECAR: 桩 %dB @0x%06X (save 入口/sc_load 入口 0x%06X) ; 钩 保存@0x%06X 载入@0x%06X'
          % (len(scode), SC_CODE_VA, sva['sc_load'], SV.SITE_SAVE, SV.SITE_LOAD))
    print('  影子档 %dB = 头 0x%X + %s ; 每槽一份 %s'
          % (SV.file_len(SDL), SV.HDR_SZ,
             ' + '.join('%s@0x%06X(%dB)' % (nm, va, sz)
                        for (va, sz), nm in zip(SV.blocks(SDL),
                                                ('实体', '姓行', '名行', '位图', 'KID_TAB', '指令环'))),
             SV.PATH_TMPL))
    print('  SC_DATA 0x%06X+%dB (路径@0x%06X 表@0x%06X 模板@0x%06X OFSTRUCT@0x%06X) ; 埋点 %s'
          % (SC_DATA_VA, SV.SC_DATA_SZ, SC_DATA_VA + SV.D_PATH, SC_DATA_VA + SV.D_BLK,
             SC_DATA_VA + SV.D_TMPL, SC_DATA_VA + SV.D_OFS, ' '.join(SV.SC_CTRS)))

    # ---------- 4j5) v13: 动态族谱点亮桩 (tree_dyn.py) + .fdata 的 DYN_FN 落址 ----------
    #   开树时 tree_entry `call [DYN_FN]`: 复位 count -> 扫实体池点「父链 +0x1d = 本人 oid」的子嗣
    #   -> 姓名写进串池池首可变区 -> count = static_n + 点亮数。
    #   27 个史实家族之外的人走**通用块**(FAM_DIR+22 = GEN_FLAG): 本人姓名 + 「X氏」标题 +
    #   他的游戏内子嗣 —— 这就是「审查所有人的族谱」, 不再回落柴田树。
    import tree_dyn as TDYN
    import tree_data as TDATA
    assert TDYN.GEN_FLAG == TB['gen_flag'] == TDATA.GEN_FLAG, '通用块标记三处不一致'
    assert TB['dyn_str_sz'] == TDATA.DYN_STR_SZ and TB['dyn_slots'] == TDATA.DYN_SLOTS
    assert TB['gen_recs'] == TDATA.GEN_RECS
    assert TB['sec_sz'] == fd.SizeOfRawData, \
        '.fdata 节大小与清单不符 (0x%X vs 0x%X) —— 先跑 build_fam_btn2 再跑本脚本' % (
            TB['sec_sz'], fd.SizeOfRawData)
    gstart = (TB['gen_nodes_va'] - TB['nodes']) // 10
    assert TB['gen_nodes_va'] == TB['nodes'] + gstart * 10 and gstart % 2 == 0, '通用块节点序号异常'
    assert TB['generic_dir'] == TB['famdir'] + TB['scan_ndir'] * 24, '通用目录条位置异常'
    TL = {'famp': TB['famp'], 'oidtab': TB['oidtab'], 'pool': NEW, 'cap': CAP,
          'giv': GIV_NEW, 'sur': SUR_NEW,
          'dynpool': TB['dyn_pool'],
          'gname': TB['dyn_pool'] + TB['gen_name_idx'] * TB['dyn_str_sz'],
          'gtitle': TB['dyn_pool'] + TB['gen_title_idx'] * TB['dyn_str_sz'],
          'gstart': gstart, 'slots': TB['dyn_slots'],
          'suffix': TDYN.title_suffix_word(TB['gen_title_suffix']),
          'slot': TB['dyn_slot'], 'lit': TB['dyn_lit'],
          'calls': TB['dyn_call'], 'nosub': TB['dyn_nosub'],
          'genflag': TB['gen_flag'], 'locals': TDYN.LOCALS}
    tcode, tsrc = TDYN.build(TREE_DYN_VA, TL)
    TDYN.selfcheck(tcode, TREE_DYN_VA, TL)
    assert len(tcode) <= TREE_DYN_SZ, \
        '动态族谱桩 %dB 越出窗口 0x%X' % (len(tcode), TREE_DYN_SZ)
    b[ed_off(TREE_DYN_VA):ed_off(TREE_DYN_VA) + len(tcode)] = tcode
    # 控制块是**可写节内数据**(.fdata 属性 X|R|W, 桩正是往里写姓名), 这里只填桩入口:
    #   family.exe 里这颗 dword 是 0, 渲染层判空后压根不 call => 老产物行为逐位不变。
    _fnoff = fd.PointerToRawData + (TB['dyn_fn'] - TB['sec_va'])
    assert struct.unpack_from('<I', b, _fnoff)[0] == 0, \
        'DYN_FN 已非零 —— 上游不是干净的 family.exe(被重复打过?)'
    struct.pack_into('<I', b, _fnoff, TREE_DYN_VA)
    _i = sweep(bytes(b[ed_off(TREE_DYN_VA):ed_off(TREE_DYN_VA) + 8]), TREE_DYN_VA)[TREE_DYN_VA]
    # ★ capstone 在 32 位默认操作数大小下把 pushad 打成 **pushal**, 两种写法都算通过。
    assert _i.mnemonic in ('pushad', 'pushal'), '%s %s' % (_i.mnemonic, _i.op_str)
    print('TREE-DYN: 桩 %dB @0x%06X (窗口 0x%X) ; DYN_FN 0x%06X[file 0x%X] <- 0x%06X'
          % (len(tcode), TREE_DYN_VA, TREE_DYN_SZ, TB['dyn_fn'], _fnoff, TREE_DYN_VA))
    print('  本人串 0x%06X / 标题串 0x%06X / 子嗣槽串 0x%06X x%d ; 通用块节点基 %d ; 扫槽 0..0x%X'
          % (TL['gname'], TL['gtitle'], TL['dynpool'], TL['slots'], gstart, CAP - 1))

    # ★ 2026-10-07: 这 5 个 diagnostics trampoline 的定位使命已完成, 默认关闭。
    #   三条硬理由:
    #   1) 实测它们本身就会导致「进大地图后必崩 (EIP=0)」——入口 5 字节被 jmp 占掉后
    #      调用方依赖的头几条指令语义被破坏 (mk_nodbg.py/fix1..fix3 一直在事后打还原补丁)。
    #   2) 本体原本落在 KD_CODE_VA + 0x500, 而培养面板 kd_* 实际要 1626B(0x65A),
    #      两者重叠 => kd_row 后半段被覆盖, 点「培养」执行到半截指令必 AV。
    #   3) 真要用时, 本体必须搬出 KD_CODE 实际长度之外 (= KD_CODE_VA + KD_CODE_SZ, 见下面选址)。
    DBG_TRAMP = os.environ.get('TKID_DBG_TRAMP', '0') == '1'
    if not DBG_TRAMP:
        print('DEBUG-TRAMP: 跳过 5 个纯诊断 trampoline (TKID_DBG_TRAMP=1 可临时重开)')
    if DBG_TRAMP:
        # ---------- DEBUG: 日推进链埋点 (临时, 定位 6/4 崩溃) ----------
        #   崩溃在 6月4日(日推进), 不是月结算。月钩/保存侧钩里的 debug_log 不会触发。
        #   正确埋点: 0x4A0E47 `call 0x4a0b00` — 在每日都跑的路径上, 且 eax 后续不用(安全替换)。
        #   trampoline 内联写内存标记到 0x54B670+region (不用文件 API, 不依赖函数调用)
        # ★ 选址 = KD_CODE 圈块之后 (旧值 +0x500 正踩在 kd_row 上, 见 KD_CODE_SZ 注)。
        #   以后谁改了面板代码配额, KD_CODE_SZ 会带着这里一起走, 不会再静默覆盖。
        DBG_DAILY_TRAMP_VA = KD_CODE_VA + KD_CODE_SZ
        _dbg_daily = bytearray()
        _dbg_daily.append(0x60)                                      # pushad
        _dbg_daily += b'\xC6\x05'                                    # mov byte ptr [imm32], imm8
        _dbg_daily += struct.pack('<I', 0x54B674)                    # 0x54B670 + 4 (marker 'D'=0x44, 0x44&0xF=4)
        _dbg_daily.append(0xFF)                                      # marker value
        _dbg_daily.append(0x61)                                      # popad
        _dbg_daily.append(0xE8)                                      # call rel32
        _dbg_daily += struct.pack('<i', 0x4A0B00 - (DBG_DAILY_TRAMP_VA + len(_dbg_daily) + 4))
        _dbg_daily.append(0xE9)                                      # jmp rel32 back
        _dbg_daily += struct.pack('<i', (0x4A0E47 + 5) - (DBG_DAILY_TRAMP_VA + len(_dbg_daily) + 4))
        _dbg_daily_bytes = bytes(_dbg_daily)

        _dbg_daily_orig = bytes(b[text_off(0x4A0E47):text_off(0x4A0E47) + 5])
        assert _dbg_daily_orig == b'\xE8\xB4\xFC\xFF\xFF', 'DEBUG daily 站点漂移: %s' % _dbg_daily_orig.hex()

        b[ed_off(DBG_DAILY_TRAMP_VA):ed_off(DBG_DAILY_TRAMP_VA) + len(_dbg_daily_bytes)] = _dbg_daily_bytes
        b[text_off(0x4A0E47):text_off(0x4A0E47) + 5] = \
            b'\xE8' + struct.pack('<i', DBG_DAILY_TRAMP_VA - (0x4A0E47 + 5))
        _di = sweep(bytes(b[text_off(0x4A0E47):text_off(0x4A0E47) + 5]), 0x4A0E47)[0x4A0E47]
        assert _di.mnemonic == 'call' and _di.op_str == '0x%x' % DBG_DAILY_TRAMP_VA, _di.op_str
        print('DEBUG-TRAMP: D(0x44)@0x%06X->0x%06X(日推进每日路径)'
              % (0x4A0E47, DBG_DAILY_TRAMP_VA))
        print('  tramp D %dB@0x%06X  marker@0x54B674'
              % (len(_dbg_daily_bytes), DBG_DAILY_TRAMP_VA))

        # ★ 再加一个在 0x4A0D50 入口(日推进外层函数), 看这个函数是否被调用
        DBG_ENTRY_TRAMP_VA = DBG_DAILY_TRAMP_VA + 48
        _dbg_entry = bytearray()
        _dbg_entry.append(0x60)                                        # pushad
        _dbg_entry += b'\xC6\x05'                                      # mov byte ptr [imm32], imm8
        _dbg_entry += struct.pack('<I', 0x54B675)                      # 0x54B670 + 5 (marker 'E'=0x45, 0x45&0xF=5)
        _dbg_entry.append(0xFF)                                        # marker value
        _dbg_entry.append(0x61)                                        # popad
        _dbg_entry += b'\x83\xEC\x08\x53\x55'                          # 原5字节: sub esp,8; push ebx; push ebp
        _dbg_entry.append(0xE9)                                        # jmp rel32 back
        _dbg_entry += struct.pack('<i', (0x4A0D50 + 5) - (DBG_ENTRY_TRAMP_VA + len(_dbg_entry) + 4))
        _dbg_entry_bytes = bytes(_dbg_entry)

        _dbg_entry_orig = bytes(b[text_off(0x4A0D50):text_off(0x4A0D50) + 5])
        assert _dbg_entry_orig == b'\x83\xEC\x08\x53\x55', 'DEBUG entry 站点漂移: %s' % _dbg_entry_orig.hex()

        b[ed_off(DBG_ENTRY_TRAMP_VA):ed_off(DBG_ENTRY_TRAMP_VA) + len(_dbg_entry_bytes)] = _dbg_entry_bytes
        b[text_off(0x4A0D50):text_off(0x4A0D50) + 5] = \
            b'\xE9' + struct.pack('<i', DBG_ENTRY_TRAMP_VA - (0x4A0D50 + 5))
        _ei = sweep(bytes(b[text_off(0x4A0D50):text_off(0x4A0D50) + 5]), 0x4A0D50)[0x4A0D50]
        assert _ei.mnemonic == 'jmp' and _ei.op_str == '0x%x' % DBG_ENTRY_TRAMP_VA, _ei.op_str
        print('DEBUG-TRAMP: E(0x45)@0x%06X->0x%06X(日推进外层入口)'
              % (0x4A0D50, DBG_ENTRY_TRAMP_VA))
        print('  tramp E %dB@0x%06X  marker@0x54B675' % (len(_dbg_entry_bytes), DBG_ENTRY_TRAMP_VA))

        # ★ 再加一个在游戏入口(0x4F44B0), 验证埋点能不能工作
        #   如果启动后内存 0x54B676 处有值 → 埋点 OK, 崩溃在启动→日推进之间
        #   如果启动后 0x54B676 仍为 0 → 埋点函数本身有 bug
        DBG_BOOT_TRAMP_VA = DBG_ENTRY_TRAMP_VA + 48
        _dbg_boot = bytearray()
        _dbg_boot.append(0x60)                                         # pushad
        _dbg_boot += b'\xC6\x05'                                       # mov byte ptr [imm32], imm8
        _dbg_boot += struct.pack('<I', 0x54B676)                       # 0x54B670 + 6 (marker 'F'=0x46, 0x46&0xF=6)
        _dbg_boot.append(0xFF)                                         # marker value
        _dbg_boot.append(0x61)                                         # popad
        _dbg_boot += b'\x55\x8B\xEC\x6A\xFF'                           # 原5字节: push ebp; mov ebp,esp; push -1
        _dbg_boot.append(0xE9)                                         # jmp rel32 back
        _dbg_boot += struct.pack('<i', (0x4F44B0 + 5) - (DBG_BOOT_TRAMP_VA + len(_dbg_boot) + 4))
        _dbg_boot_bytes = bytes(_dbg_boot)

        _dbg_boot_orig = bytes(b[text_off(0x4F44B0):text_off(0x4F44B0) + 5])
        assert _dbg_boot_orig == b'\x55\x8B\xEC\x6A\xFF', 'DEBUG boot 站点漂移: %s' % _dbg_boot_orig.hex()

        b[ed_off(DBG_BOOT_TRAMP_VA):ed_off(DBG_BOOT_TRAMP_VA) + len(_dbg_boot_bytes)] = _dbg_boot_bytes
        b[text_off(0x4F44B0):text_off(0x4F44B0) + 5] = \
            b'\xE9' + struct.pack('<i', DBG_BOOT_TRAMP_VA - (0x4F44B0 + 5))
        _bi = sweep(bytes(b[text_off(0x4F44B0):text_off(0x4F44B0) + 5]), 0x4F44B0)[0x4F44B0]
        assert _bi.mnemonic == 'jmp' and _bi.op_str == '0x%x' % DBG_BOOT_TRAMP_VA, _bi.op_str
        print('DEBUG-TRAMP: F(0x46)@0x%06X->0x%06X(游戏入口,验证埋点)'
              % (0x4F44B0, DBG_BOOT_TRAMP_VA))
        print('  tramp F %dB@0x%06X  marker@0x54B676' % (len(_dbg_boot_bytes), DBG_BOOT_TRAMP_VA))

        # ★ 再加两个: 月边界(0x4A0DED) + 每日路径早期(0x4A0E41)
        #   顺序: F(入口) → E(外层) → G(每日早期) → D(每日晚期) → H(月边界,仅月首)
        #   这样崩溃时看哪些 marker 被触发就能精确定位
        # Trampoline G @ 0x4A0E41 (call 0x49a1a0, 每日路径早期)
        DBG_DAILY_EARLY_TRAMP_VA = DBG_BOOT_TRAMP_VA + 48
        _dbg_daily_early = bytearray()
        _dbg_daily_early.append(0x60)                                    # pushad
        _dbg_daily_early += b'\xC6\x05'                                  # mov byte ptr [imm32], imm8
        _dbg_daily_early += struct.pack('<I', 0x54B677)                  # marker 'G'
        _dbg_daily_early.append(0xFF)                                    # marker value
        _dbg_daily_early.append(0x61)                                    # popad
        _dbg_daily_early.append(0xE8)                                    # call rel32
        _dbg_daily_early += struct.pack('<i', 0x49A1A0 - (DBG_DAILY_EARLY_TRAMP_VA + len(_dbg_daily_early) + 4))
        _dbg_daily_early.append(0xE9)                                    # jmp rel32 back
        _dbg_daily_early += struct.pack('<i', (0x4A0E41 + 5) - (DBG_DAILY_EARLY_TRAMP_VA + len(_dbg_daily_early) + 4))
        _dbg_daily_early_bytes = bytes(_dbg_daily_early)

        _dbg_daily_early_orig = bytes(b[text_off(0x4A0E41):text_off(0x4A0E41) + 5])
        assert _dbg_daily_early_orig == b'\xE8\x5A\x93\xFF\xFF', 'DEBUG daily_early 站点漂移: %s' % _dbg_daily_early_orig.hex()

        b[ed_off(DBG_DAILY_EARLY_TRAMP_VA):ed_off(DBG_DAILY_EARLY_TRAMP_VA) + len(_dbg_daily_early_bytes)] = _dbg_daily_early_bytes
        b[text_off(0x4A0E41):text_off(0x4A0E41) + 5] = \
            b'\xE8' + struct.pack('<i', DBG_DAILY_EARLY_TRAMP_VA - (0x4A0E41 + 5))
        _gi = sweep(bytes(b[text_off(0x4A0E41):text_off(0x4A0E41) + 5]), 0x4A0E41)[0x4A0E41]
        assert _gi.mnemonic == 'call' and _gi.op_str == '0x%x' % DBG_DAILY_EARLY_TRAMP_VA, _gi.op_str
        print('DEBUG-TRAMP: G(0x47)@0x%06X->0x%06X(日推进每日早期)'
              % (0x4A0E41, DBG_DAILY_EARLY_TRAMP_VA))
        print('  tramp G %dB@0x%06X  marker@0x54B677' % (len(_dbg_daily_early_bytes), DBG_DAILY_EARLY_TRAMP_VA))

        # Trampoline H @ 0x4A0DED (call 0x4A4C60, 月边界)
        DBG_MONTH_TRAMP_VA = DBG_DAILY_EARLY_TRAMP_VA + 48
        _dbg_month = bytearray()
        _dbg_month.append(0x60)                                      # pushad
        _dbg_month += b'\xC6\x05'                                    # mov byte ptr [imm32], imm8
        _dbg_month += struct.pack('<I', 0x54B678)                    # marker 'H'
        _dbg_month.append(0xFF)                                      # marker value
        _dbg_month.append(0x61)                                      # popad
        _dbg_month.append(0xE8)                                      # call rel32
        _dbg_month += struct.pack('<i', 0x4A4C60 - (DBG_MONTH_TRAMP_VA + len(_dbg_month) + 4))
        _dbg_month.append(0xE9)                                      # jmp rel32 back
        _dbg_month += struct.pack('<i', (0x4A0DED + 5) - (DBG_MONTH_TRAMP_VA + len(_dbg_month) + 4))
        _dbg_month_bytes = bytes(_dbg_month)

        _dbg_month_orig = bytes(b[text_off(0x4A0DED):text_off(0x4A0DED) + 5])
        assert _dbg_month_orig == b'\xE8\x6E\x3E\x00\x00', 'DEBUG month 站点漂移: %s' % _dbg_month_orig.hex()

        b[ed_off(DBG_MONTH_TRAMP_VA):ed_off(DBG_MONTH_TRAMP_VA) + len(_dbg_month_bytes)] = _dbg_month_bytes
        b[text_off(0x4A0DED):text_off(0x4A0DED) + 5] = \
            b'\xE8' + struct.pack('<i', DBG_MONTH_TRAMP_VA - (0x4A0DED + 5))
        _hi = sweep(bytes(b[text_off(0x4A0DED):text_off(0x4A0DED) + 5]), 0x4A0DED)[0x4A0DED]
        assert _hi.mnemonic == 'call' and _hi.op_str == '0x%x' % DBG_MONTH_TRAMP_VA, _hi.op_str
        print('DEBUG-TRAMP: H(0x48)@0x%06X->0x%06X(月边界)'
              % (0x4A0DED, DBG_MONTH_TRAMP_VA))
        print('  tramp H %dB@0x%06X  marker@0x54B678' % (len(_dbg_month_bytes), DBG_MONTH_TRAMP_VA))

    MOD_USED = prev_end - (NEW + MOD_OFF)

    # ---------- 4k) LAYOUT: 把本次容量档与全部派生地址落盘 ----------
    #   verify_appear.py / verify_children.py / tkwatch.py 都读这张表, 不再手写 VA —— 换 CAP 无需改脚本。
    assert cva['stub_end'] + 4 <= NEW + NEW_SZ, 'MOD 私有区溢出'
    layout = {
        'cap': CAP, 'stride': STRIDE, 'n0': N0,
        'pool_va': NEW, 'section_va': NEW, 'section_sz': NEW_SZ, 'section_rva': NEW_RVA,
        'sur_va': SUR_NEW, 'giv_va': GIV_NEW, 'mod_base': NEW + MOD_OFF,
        # 极性注记: SUR_*(原 0x520660)=名表, GIV_*(原 0x521AA8)=姓表 (变量名沿用老工具, 反的)
        'given_tab_va': SUR_NEW, 'surname_tab_va': GIV_NEW,
        'mod_used_upto': MOD_USED,                       # MOD 区已吃字节(数据区已算进去)
        'mod_sz': MOD_SZ, 'kid_esz': KID_ESZ,
        # ---- v13: 动态族谱 (桩在 .edata, 控制块/数据在 .fdata; 验收与 tkwatch 按下表取) ----
        'tree_dyn': {'code_va': TREE_DYN_VA, 'code_sz': len(tcode), 'win_sz': TREE_DYN_SZ,
                     'genpuku_note': 'tree_entry call [dyn_fn]; 通用块由 FAM_DIR+22 分流',
                     'dyn_fn': TB['dyn_fn'], 'dyn_lit': TB['dyn_lit'],
                     'dyn_call': TB['dyn_call'], 'dyn_nosub': TB['dyn_nosub'],
                     'dyn_slot': TB['dyn_slot'], 'dyn_pool': TB['dyn_pool'],
                     'dyn_slots': TB['dyn_slots'], 'dyn_str_sz': TB['dyn_str_sz'],
                     'famp': TB['famp'], 'oidtab': TB['oidtab'], 'famdir': TB['famdir'],
                     'generic_dir': TB['generic_dir'], 'gen_start': gstart,
                     'gen_name_rec': TL['gname'], 'gen_title_rec': TL['gtitle'],
                     'scan_ndir': TB['scan_ndir'], 'ndir': TB['ndir'],
                     'nnode': TB['nnode'], 'nstatic': TB['nstatic'],
                     'entry_va': TB['entry_va'], 'nodes': TB['nodes'], 'pool': TB['pool']},
        'genpuku_age': PUKU_AGE, 'puku_codes': CG.PUKU,   # M4: 阈值(虚岁) + KID_TAB+10 归属码表
        'growth_ctrs': GC_IDX,
        # ---- M6: 影子存档 (verify_children C24 族按这张表核对 exe 内的桩/数据区/钩子/埋点) ----
        'sc': {'code_va': SC_CODE_VA, 'code_sz': len(scode), 'data_va': SC_DATA_VA,
               'data_sz': SV.SC_DATA_SZ, 'site_save': SV.SITE_SAVE, 'site_load': SV.SITE_LOAD,
               'orig_save': SV.ORIG_SAVE.hex(), 'orig_load': SV.ORIG_LOAD.hex(),
               'tramp_load': sva['tramp_load'], 'sc_save': sva['sc_save'], 'sc_load': sva['sc_load'],
               'path': SV.PATH_TMPL, 'path_digit': SV.PATH_DIGIT, 'hdr_sz': SV.HDR_SZ,
               'magic': SV.MAGIC, 'commit': SV.COMMIT, 'ver': SV.VER,
               'file_sz': SV.file_len(SDL), 'payload_sz': SV.payload_len(SDL),
               'blocks': [[va, sz] for va, sz in SV.blocks(SDL)],
               'block_names': ['实体', '姓行', '名行', '位图', 'KID_TAB', '指令环'],
               'open_save': SV.OPEN_SAVE, 'gate': SV.OBJ_GATE, 'recbase': SV.OBJ_RECBASE,
               'rec_hdr': SV.REC_HDR, 'rec_size': SV.REC_SIZE, 'slot_max': SV.SLOT_MAX,
               'deltas': {k: getattr(SV, 'D_' + k) for k in
                          ('PATH', 'HDR', 'BLK', 'HND', 'SLOT', 'DIG', 'CUR', 'TMPL', 'OFS')},
               'hd': {k: getattr(SV, 'HD_' + k) for k in
                      ('MAGIC', 'VER', 'CAP', 'SLOT', 'N0', 'PAYLOAD', 'DIGEST', 'COMMIT', 'RECN')},
               'ctrs': {nm: GC_IDX[nm] for nm in SV.SC_CTRS}},
        'growth_stub_sz': len(gcode),
        'preload_stub_sz': cva['stub_end'] - CHILD_PASS_VA,
        'month_hook_sz': cva['month_hook_sz'], 'load_hook_sz': cva['load_hook_sz'],
        'reserve_lo': RESERVE_LO, 'reserve_n': RESERVE_N,
        'child_batch': batch, 'child_n': len(entries),
        'child_follow_father': follow, 'child_dyn': _dyn,
        'v': {'MCI_SLOT': MOD_SLOT_VA, 'MCI_STUB': MOD_STUB_VA, 'BGM_CNT': BGM_CNT_VA,
              'APPEAR_CNT': APPEAR_CNT_VA, 'VACANT_CNT': VACANT_CNT_VA,
              'MONTH_CNT': MONTH_CNT_VA, 'ARMED_CNT': ARMED_CNT_VA,
              'APPEAR_STUB': APPEAR_STUB_VA, 'EQ_STUB': EQ_STUB_VA,
              'CHILD_PRELOAD': CHILD_PRELOAD_VA, 'CHILD_REARM': CHILD_REARM_VA,
              'CHILD_GENPUKU': CHILD_GENPUKU_VA, 'CHILD_SCAN': CHILD_SCAN_VA,
              'CHILD_SKIP': CHILD_SKIP_VA, 'CHILD_PLACE': CHILD_PLACE_VA, 'CHILD_BM': CHILD_BM_VA,
              'CHILD_INIT5': CHILD_INIT5_VA,
              'CHILD_SCHED': CHILD_SCHED_VA, 'CHILD_PASS': cva['child_pass'],
              'CHILD_MONTH_HOOK': cva['month_hook'], 'CHILD_LOAD_HOOK': cva['load_hook'],
              # 桩内标签/被调方的真实 VA: 桩代码一改, 这些地址就跟着动。
              #   验收脚本一律从这里取, 别再写死 (0x54C9xx 那批硬编码就因为这个漂了一次)。
              'DEBUG_LOG': cva['debug_log'], 'LBL_MAKE_CHILD': cva['make_child'],
              'LBL_PLACE_CHILD': cva['place_child'], 'LBL_INIT_STATS': cva['init_stats'],
              'CHILD_GROWTH': CHILD_GROWTH_VA, 'GROWTH_CNT': GROWTH_CNT_VA,
              'KID_TAB': KID_TAB_VA, 'CMD_RING': CMD_RING_VA,
              'MENU_PTR': MENU_PTR_VA, 'MENU_CODE': MENU_CODE_VA, 'PANEL': PANEL_VA,
              'ACT_TAB': ACT_TAB_VA, 'TEACH_TAB': TEACH_TAB_VA,
              'MENU_STR': MENU_STR_VA, 'DEC100': DEC100_VA, 'NAME_BUF': NAME_BUF_VA,
              'SLOT_ARR': SLOT_ARR_VA, 'SUB_PTR': SUB_PTR_VA, 'ACT_PTR': ACT_PTR_VA,
              'TEACH_PTR': TEACH_PTR_VA, 'TIER_PTR': TIER_PTR_VA, 'MENU_SCR': MENU_SCR_VA},
        # M3c: 回家菜单「培养孩子」的桩与三处补丁 —— verify_children.py 逐字节复核
        'menu': {'hook_va': MENU_STUB_VA, 'foster_va': MENU_FOSTER_VA,
                 'birth_va': MENU_BIRTH_VA,
                 'birth_code_sz': BIRTH_CODE_SZ, 'pick_va': BIRTH_PICK_VA,
                 'birth_slot_lo': BIRTH_SLOT_LO, 'birth_taken_hi': max(_taken),
                 'slot_lo': BIRTH_SLOT_LO,
                 'hook_sz': len(hcode), 'foster_sz': len(fcode), 'birth_sz': len(bcode),
                 'name_pool_va': BIRTH_POOL_VA, 'name_pool_sz': BIRTH_POOL_SZ,
                 'name_count': CM.BIRTH_NAME_COUNT, 'name_offer': CM.BIRTH_NAME_OFFER,
                 'avail_va': BIRTH_AVAIL_VA, 'avail_sz': BIRTH_AVAIL_SZ,
                 'avail_n_va': BIRTH_AVAILN_VA,
                 'used_va': BIRTH_USED_VA, 'used_sz': BIRTH_USED_SZ,
                 'birth_label_va': BIRTH_LABEL_VA, 'birth_label_sz': BIRTH_LABEL_SZ,
                 'flagtab': ML['flagtab'], 'date_y': ML['date_y'],
                 'str_n': CM.STR_N, 'str_row': CM.STR_ROW,
                 'item_max': CM.MENU_ITEM_MAX, 'page_kids': CM.PAGE_KIDS,
                 'cnt_rows': GC_IDX['PAGE_ROWS'], 'cnt_nav': GC_IDX['PAGE_NAV'],
                 'cnt_birth': GC_IDX['BIRTH_COUNT'],
                 'cnt_bytes': 0x100,
                 # 出生提示: 四行指针数组 / 姓名缓冲 / 三行静态串的地址 (verify_children 按这张表复核)
                 'msg_arr_va': BIRTH_PROMPT_VA, 'name_tmp_va': BIRTH_NAME_TMP_VA,
                 'msg_arr_sz': BIRTH_PROMPT_SZ, 'name_tmp_sz': BIRTH_NAME_TMP_SZ,
                 'ms_born': MSG_STR_VA + CM.MS_BORN * CM.MS_STR_ROW,
                 'ms_born_at': MSG_STR_VA + CM.MS_BORN_AT * CM.MS_STR_ROW,
                 'ms_born_gk': MSG_STR_VA + CM.MS_BORN_GK * CM.MS_STR_ROW,
                 'patches': {'hook_site': CM.HOOK_MENU_SITE, 'code_limit': CM.CODE_LIMIT_SITE,
                             'table8': CM.TABLE8_SITE, 'menu_top': CM.MENU_TOP,
                             'menu_exit': CM.MENU_EXIT, 'dialog': CM.DIALOG,
                             'age_get': CM.AGE_GET}},
        # M5: 门禁/花费/反馈 —— 计数区 + 串池 + 三个指针数组 (verify_children.py 按这张表复核)
        'm5': {'foster_va': FOSTER_VA, 'msg_str_va': MSG_STR_VA, 'msg_str_sz': MSG_STR_SZ,
               'fo': {k: FOSTER_VA + v for k, v in FO.items()},
               'monthly_cap': CG.MONTHLY_CAP, 'act_days': list(CG.ACT_DAYS),
               'gold_per_day': CG.GOLD_PER_DAY, 'day_max': CG.DAY_MAX,
               'gold_ptr': CG.GOLD_PTR, 'pay': CG.PAY, 'advance_day': CG.ADVANCE_DAY,
               'msg_row': CM.MS_STR_ROW, 'ms_line0': CM.MS_LINE0, 'ms_hint': CM.MS_MSG_HINT,
               'msg_kd': KD_MSG_VA,
               'ms_ok': MSG_STR_VA + CM.MS_OK * CM.MS_STR_ROW,
               'ms_cancel': MSG_STR_VA + CM.MS_CANCEL * CM.MS_STR_ROW,
               'ms_cost0': MSG_STR_VA + CM.MS_COST0 * CM.MS_STR_ROW,
               'msg_str_n': len(CM.MSG_STRINGS),
               'ms_none': MSG_STR_VA + CM.MS_NONE * CM.MS_STR_ROW,
               'ms_no_slot': MSG_STR_VA + CM.MS_NO_SLOT * CM.MS_STR_ROW,
               'deny_month_str': MSG_STR_VA + CM.MS_DENY_MONTH * CM.MS_STR_ROW,
               'deny_time_str': MSG_STR_VA + CM.MS_DENY_TIME * CM.MS_STR_ROW,
               'deny_gold_str': MSG_STR_VA + CM.MS_DENY_GOLD * CM.MS_STR_ROW,},
        # M3c-2: 培养详情 GDI 面板 (verify_children.py C24 族按这张表复核)
        'panel': {'code_va': KD_CODE_VA, 'code_sz': len(kcode),
                  'str_va': KD_STR_VA, 'str_sz': len(_kstr),
                  'data_va': KD_DATA_VA, 'data_sz': KP.KD_DATA_SZ,
                  'str_n': len(KP.STRINGS), 'pw': KP.PW, 'ph': KP.PH,
                  'kd': {k: KD_DATA_VA + v for k, v in KP.KD.items()},
                  'strings': [{'name': s, 'va': v, 'len': n}
                              for s, (v, n) in zip(KP.STRINGS, _kent)],
                  'strtab': KD_DATA_VA + KP.KD['strtab'],
                  'reuse': {'resolve': KP.RESOLVE_VA, 'make_res': KP.MAKE_RES_VA,
                            'free_res': KP.FREE_RES_VA, 'wait_rel': KP.WAIT_REL_VA,
                            'pump': KP.PUMP_VA},
                  'gdi': {'tab': KP.GDI_TAB_VA, 'rstate': KP.RSTATE_VA,
                          'gdiok': KP.GDIOK_VA, 'rc': KP.RC_VA,
                          'slots': {'gaw': KP.A_GAW, 'getdc': KP.A_GETDC,
                                    'reldc': KP.A_RELDC, 'selobj': KP.A_SELOBJ,
                                    'rect': KP.A_RECT, 'settc': KP.A_SETTC,
                                    'setbk': KP.A_SETBK, 'seta': KP.A_SETA,
                                    'textout': KP.A_TEXTOUT, 'gcrect': KP.A_GCRECT},
                          'rs': KP.RS}},
    }
    # ★ 写在哪里必须以脚本自身位置为准 (以前用相对路径 = 写到"当前目录",
    #   我在 .rev 目录里跑时就更新 .rev/_big_layout.json, 在根目录跑就更新根目录那份 ——
    #   两份同名的 json 互相瞒着对方, verify_children 按 REV/ 读, 于是拿到的永远是旧布局)。
    _LAY = os.path.join(os.path.dirname(os.path.abspath(__file__)), '_big_layout.json')
    json.dump(layout, open(_LAY, 'w', encoding='utf-8'),
              ensure_ascii=False, indent=1)
    print('LAYOUT: CAP=%d .edata 0x%X (池 0x%06X..+%dB, 名表 0x%06X, 姓表 0x%06X, MOD 区 0x%06X 已用 %dB) -> _big_layout.json'
          % (CAP, NEW_SZ, NEW, POOL_SZ, SUR_NEW, GIV_NEW, NEW + MOD_OFF, layout['mod_used_upto']))

    # ---------- 5) 写盘(游戏占用防呆) ----------
    try:
        open(DST, 'wb').write(bytes(b))
        print('OK  %s  %d B  mtime=%s' % (DST, len(b), time.strftime('%H:%M:%S', time.localtime(os.path.getmtime(DST)))))
    except PermissionError:
        out = DST[:-4] + 'b.exe'
        open(out, 'wb').write(bytes(b))
        print('!! 警告: %s 被占用(游戏在跑?), 本次写到了 %s' % (DST, out))

if __name__ == '__main__':
    main()
