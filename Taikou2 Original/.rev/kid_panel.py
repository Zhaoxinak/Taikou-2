# -*- coding: utf8 -*-
"""
kid_panel.py —— M3c-2 「培养详情」GDI 面板 (五维条 / 成功率 P / 亲密度)

为什么自己画而不用原生对话框: 原生 0x47BED0 只能给「一串文字 + 选一项」,
画不了五维条; 而计划(PLAN §6.7 尾)定死了一条约束 ——
    **面板展示的 P 必须与成长桩 0x54CA00 段 cg_t_* 的推导逐式同构**,
否则"看着能中、实际没中"会被当成 bug。所以这里不是"再算一遍近似值",
而是把桩里 cg_teach/cg_t_lord/cg_t_father/cg_t_add 四条路径原样搬过来
(连 `imul 0x67 / shr 0xa` 这个 bond/10 近似和 clamp(5,85) 的次序都不改)。

复用而不是重写: 族谱面板(tree_render.py)已经落在 .fdata(0x536000) 里,
下面这些段是**已构建、已跑通**的, 本模块只 call 它们, 一个字节都不重新生成:
    resolve_api 0x53933A   惰性解析 27 个 API -> GDI_TAB (未解析时全 0, 必须守卫)
    make_res    0x539414   建刷/笔/字体 -> RSTATE
    free_res    0x53965A   DeleteObject 掉上述对象
    wait_rel    0x5397A7   进模态前等左键松开(否则打开那次点击立刻被当关闭)
    pump        0x539953   排空消息 + ESC/单击关闭 + 方向键/拖拽 + Sleep
  ★ 地址来自 tree_blobs.json (build_fam_btn2.py 导出), 构建时逐个 assert 复核,
    族谱那侧重排段序时这里会当场炸, 不会静默指到错地方。

模态结构照抄 tree_show(0x53A838) 的 proven 顺序:
    resolve -> GetActiveWindow -> GetDC -> GetClientRect(居中) -> make_res
    -> wait_rel -> loop{ 画 -> pump -> QUIT? } -> free_res -> ReleaseDC
  全部包在 pushad/popad 里: cm_foster 的 esi/ebp/栈帧进来什么样出去什么样。

★ 与族谱那段共用的坑(照抄 tree_render.py 头注, 别再踩一遍):
  1) TextOutA 的 cchString 必须传**显式字符数** (传 -1 本机返回 0, 一个字都不画),
     所以串池每条都是 [u8 长度][GBK 字节][NUL]。
  2) 立即数一律 0x 前缀 (keystone 会把裸十进制当十六进制吃)。
  3) SRC 必须纯 ASCII (中文注释会让 keystone UnicodeEncodeError)。
"""

import json
import os

import child_growth as CG
from child_menu import lint_src

# ================= 复用的族谱段 VA (真源: tree_blobs.json) =================
_BLOBS = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                     'tree_blobs.json')))
_BV = {b['name']: b['va'] for b in _BLOBS['blobs']}
RESOLVE_VA = _BV['resolve_api']
MAKE_RES_VA = _BV['make_res']
FREE_RES_VA = _BV['free_res']
WAIT_REL_VA = _BV['wait_rel']
PUMP_VA = _BV['pump']
assert (RESOLVE_VA, MAKE_RES_VA, FREE_RES_VA, WAIT_REL_VA, PUMP_VA) == \
    (0x53933A, 0x539414, 0x53965A, 0x5397A7, 0x539953), _BV

# ---- .fdata 运行时布局 (与 build_fam_btn2.py 必须一致) ----
SEC_VA = 0x536000
O_GDITAB, O_RSTATE, O_SCRATCH = 0x0000, 0x03C0, 0x04C0
GDI_TAB_VA = SEC_VA + O_GDITAB
RSTATE_VA = SEC_VA + O_RSTATE
GDIOK_VA = RSTATE_VA + 0x0D8          # dword: API 已解析标志 (tree_show 也读这个)
RC_VA = SEC_VA + O_SCRATCH            # RECT 暂存(与族谱共用; 两边不会同时模态)

# RSTATE 字段偏移 (与 tree_render.RS 必须一致)
RS = dict(HWND=0x00, HDC=0x04, QUIT=0x0C, PANX=0x68, PANY=0x6C, DRAG=0x78,
          MOVED=0x7C, WX0=0x80, WY0=0x84, WX1=0x88, WY1=0x8C,
          VX0=0x90, VY0=0x94, VX1=0x98, VY1=0x9C, CW=0xA0, CH=0xA4,
          BRBG=0x14, BRN0=0x18, BRSH=0x24, PENAC=0x38, PENIN=0x3C,
          PENFR=0x40, FTTI=0x44, FTRL=0x4C)
# GDI_TAB 槽位 (与 build_fam_btn2.API_LIST 必须一致)
A_GAW, A_GETDC, A_RELDC, A_SELOBJ, A_RECT = 1, 3, 4, 7, 9
A_SETTC, A_SETBK, A_SETA, A_TEXTOUT, A_GCRECT = 13, 14, 15, 16, 22
T = lambda i: GDI_TAB_VA + i * 4
assert T(A_TEXTOUT) == 0x536040 and RC_VA == 0x5364C0

# ---- 配色 (与 tree_render.C 同源, 挑对比度够的) ----
C_TXT = 0x00E8F0F0        # 标签: 近白
C_TITLE = 0x0080E0FF      # 标题: 淡金
C_HINT = 0x0090A080       # 底部提示: 暗黄
C_VAL = 0x00FFE060        # 数值: 亮青(强调)

# ---- 面板几何 ----
PW, PH = 420, 380
TITLE_Y = 28              # 标题基线相对面板顶
HINT_Y = 362              # 提示基线相对面板顶
ROW_H = 26
ROW_Y0 = 52               # 第 0 行(统率)相对面板顶
P_ROW, BOND_ROW = 186, 212
INFO_Y0, INFO_H = 248, 26 # M5: 进度表四行 (累计培养 / 已养维度 / 距元服 / 本月剩余)
LAB_X, BAR_X, BAR_W, BAR_H, VAL_X = 16, 72, 240, 12, 324

# ---- M5 反馈小框几何 ----
MW, MH = 460, 150
M_NAME_Y = 36             # 孩子名基线(相对框顶)
M_LINE_Y = 78             # 台词基线
M_HINT_Y = 128            # 底部提示基线
# ★ 反馈小框里孩子槽的上界 = 姓名表**有效行数** (4578B / 7B = 654)。
#   名字表是"按槽直索引"(oid == 槽), 所以上界就该是表行数。
#   千万别写小: 本批孩子实体落在槽 463..476 (CHILD_PRELOAD 批次 fam13),
#   若守卫写成 0x40 之类, kd_msg 会直接 return —— 反馈框根本不弹, 而且看起来像"功能没做"。
NAME_TAB_ROWS = 654
SLOT_MAX_MSG = NAME_TAB_ROWS

# ---- 串池条目: [u8 长度][GBK][NUL]; 顺序即下面 S_* 下标 ----
STRINGS = ('培养详情',                             # 0 标题
           '统率', '武力', '内政', '外交', '魅力',         # 1..5 五维
           '成功率(%)',                             # 6
           '亲密',                                  # 7
           'ESC/单击关闭',                          # 8 详情面板底部提示
           '累计培养(次)', '已养维度(维)', '距元服(月)', '本月剩余(次)',   # 9..12 M5 进度表
           '点击关闭')                              # 13 反馈小框底部提示
S_TITLE, S_DIM0, S_P, S_BOND, S_HINT = 0, 1, 6, 7, 8
S_CNT, S_DIMS, S_PUKU, S_LEFT, S_MSG_HINT = 9, 10, 11, 12, 13
assert len(STRINGS) == 14, len(STRINGS)

# ---- 静态区 (KD_DATA) 内部偏移 ----
KD = dict(ent=0x00, slot=0x04, act=0x08, teach=0x0C, tier=0x10,
          dim=0x14, b=0x18, r=0x1C, p=0x20, bond=0x24, num=0x28,
          lbl=0x30, lbln=0x34, val=0x38, rowy=0x3C, tmpw=0x40,
          strtab=0x44,
          # ---- M5 ----
          bar=0x58,        # dword: 条宽用的 0..100 (与 KD_VAL 分离: 进度表几行要画比例, 显示原始值)
          n1=0x5C, n2=0x60, n3=0x64, n4=0x68,   # 累计培养 / 已养维度 / 距元服月 / 本月剩余
          nm=0x6C,         # 反馈小框: 孩子名 (GCK, 最多 16B)
          nmlen=0x7C)      # 反馈小框: 名字字节数
KD_DATA_SZ = 0x80
assert KD['strtab'] + 5 * 4 <= KD['bar'] and KD['nmlen'] + 4 <= KD_DATA_SZ
assert KD['num'] + 8 <= KD['lbl']


def str_pool_bytes():
    """串池字节 + 每条的 [字节首址, 字符数](字符数 = GBK 字节数)。"""
    out = bytearray()
    for s in STRINGS:
        raw = s.encode('gbk')
        out += bytes([len(raw)]) + raw + b'\x00'
    return bytes(out)


# ================= 桩源码 (纯 ASCII 注释! keystone 会炸) =================
# kd_show   : 模态入口 —— 取窗口/DC/居中, 算 P 与亲密, 然后循环画
# kd_frame  : 面板底 + 金边 + 标题 + 底部提示
# kd_bars   : 五维循环 —— 每维装好 kd_row 的参数再 call kd_row
# kd_row    : 画一行 (标签 + 数值 + 进度条), 参数全走静态区
# kd_itoa   : 0..255 -> 十进制串 (esi=串首, eax=长度)
#
# ★ 跨段传值一律走静态区(不靠寄存器): 一来"桩怎么算 P"与"面板怎么算 P"能逐条对照,
#   二来 pushad/popad 洗不掉, 三来 stdcall 会破坏 eax/ecx/edx(宽度必须存内存)。
# ★ 两套串池格式不同, 别混:
#     kid_panel.STRINGS  -> [u8 长度][GBK][NUL], 紧凑无 pad; 配套解码 = movzx ecx,[eax]; inc eax
#     child_menu.MSG_STRINGS -> [GBK][NUL][pad 到 MS_STR_ROW], 无长度前缀;
#        配套解码 = **自己数字节数** (kd_line_len / kd_hint_len 两个循环), 见下面第 1 条。
#   后者兼顾原生对话框 (0x47BED0 要的是 C 字符串), 所以不能塞长度字节进串首。
# ★ 所有居中一律 (wx0 + wx1) / 2, 不许 (wx0 + 框宽)/2 —— 后者只在 wx0 恰好为 0 时才对。
SRC_ALL = """
kd_show:
  pushad
  mov eax, dword ptr [%(kd_act)s]
  cmp eax, 0xa
  jae kd_exit
  mov eax, dword ptr [%(kd_teach)s]
  cmp eax, 0x5
  jae kd_exit
  call %(resolve)s
  mov eax, dword ptr [%(gdio)s]
  test eax, eax
  je kd_exit
  call dword ptr [%(t_gaw)s]
  test eax, eax
  je kd_exit
  mov dword ptr [%(r_hwnd)s], eax
  push eax
  call dword ptr [%(t_getdc)s]
  test eax, eax
  je kd_exit
  mov dword ptr [%(r_hdc)s], eax
  push %(r_rc)s
  push dword ptr [%(r_hwnd)s]
  call dword ptr [%(t_gcrect)s]
  mov eax, dword ptr [%(r_rc)s + 0x8]
  mov dword ptr [%(r_cw)s], eax
  mov eax, dword ptr [%(r_rc)s + 0xc]
  mov dword ptr [%(r_ch)s], eax
  mov eax, dword ptr [%(r_cw)s]
  sub eax, %(pw)s
  sar eax, 1
  mov dword ptr [%(r_wx0)s], eax
  mov eax, dword ptr [%(r_ch)s]
  sub eax, %(ph)s
  sar eax, 1
  mov dword ptr [%(r_wy0)s], eax
  mov eax, dword ptr [%(r_wx0)s]
  add eax, %(pw)s
  dec eax
  mov dword ptr [%(r_wx1)s], eax
  mov eax, dword ptr [%(r_wy0)s]
  add eax, %(ph)s
  dec eax
  mov dword ptr [%(r_wy1)s], eax
  mov eax, dword ptr [%(r_wx0)s]
  mov dword ptr [%(r_vx0)s], eax
  mov eax, dword ptr [%(r_wy0)s]
  mov dword ptr [%(r_vy0)s], eax
  mov eax, dword ptr [%(r_wx1)s]
  mov dword ptr [%(r_vx1)s], eax
  mov eax, dword ptr [%(r_wy1)s]
  mov dword ptr [%(r_vy1)s], eax
  mov dword ptr [%(r_quit)s], 0
  mov dword ptr [%(r_drag)s], 0
  mov dword ptr [%(r_moved)s], 0
  mov dword ptr [%(r_panx)s], 0
  mov dword ptr [%(r_pany)s], 0
  # ---- dim / B (same as stub cg_cmd: ACT_TAB[act*4] / [act*4+1] + (tier&0x3)*B_STEP, cap B_MAX) ----
  mov eax, dword ptr [%(kd_act)s]
  imul eax, eax, 0x4
  add eax, %(act_tab)s
  movzx ecx, byte ptr [eax]
  mov dword ptr [%(kd_dim)s], ecx
  movzx edx, byte ptr [eax + 0x1]
  mov ecx, dword ptr [%(kd_tier)s]
  and ecx, 0x3
  imul ecx, ecx, 0x5
  add edx, ecx
  cmp edx, 0xf
  jbe kd_b_ok
  mov edx, 0xf
kd_b_ok:
  mov dword ptr [%(kd_b)s], edx
  # ---- R = min(bond,BOND_CAP)*BOND_MUL >> BOND_SHR (same as stub cg_bond, no div) ----
  mov eax, dword ptr [%(kd_slot)s]
  imul eax, eax, 0xc
  add eax, %(kid)s
  mov esi, eax
  movzx eax, word ptr [esi]
  cmp eax, 0x64
  jbe kd_bond_ok
  mov eax, 0x64
kd_bond_ok:
  mov dword ptr [%(kd_bond)s], eax
  imul ecx, eax, 0x67
  shr ecx, 0xa
  mov dword ptr [%(kd_r)s], ecx
  # ---- T: teacher bonus (same branches as stub cg_teach / cg_t_lord / cg_t_father / cg_t_const) ----
  mov eax, dword ptr [%(kd_teach)s]
  cmp eax, 0x1
  je kd_t_lord
  cmp eax, 0x2
  je kd_t_father
  movzx ecx, byte ptr [eax + %(teach_tab)s]
  jmp kd_t_add
kd_t_lord:
  # T = min(T_LORD_CAP, byte[lord + dim + 0x0a]*T_LORD_MUL/PCT + rank bonus); rank = (word[+0x2c]&ID_MASK)>>8
  push esi
  push edi
  push ebx
  call %(player_ent)s
  mov ebx, eax
  mov edx, dword ptr [%(kd_dim)s]
  movzx eax, byte ptr [ebx + edx + 0x0a]
  imul eax, eax, %(t_lord_mul)s
  xor edx, edx
  mov ecx, 0x64
  div ecx
  movzx edx, word ptr [ebx + 0x2c]
  and edx, %(id_mask)s
  shr edx, 0x8
  xor ecx, ecx
  cmp dl, %(id_daimyo)s
  jne kd_l2
  mov ecx, 0xa
  jmp kd_l3
kd_l2:
  cmp dl, %(id_karo)s
  jne kd_l3
  mov ecx, 0x5
kd_l3:
  add eax, ecx
  cmp eax, %(t_lord_cap)s
  jbe kd_l4
  mov eax, %(t_lord_cap)s
kd_l4:
  pop ebx
  pop edi
  pop esi
  mov ecx, eax
  jmp kd_t_add
kd_t_father:
  # fslot = word[sched + slot*ESZ + 0x4]; 0xffff -> const T_CONST; else T = min(T_FATH_CAP, father maxdim*T_FATH_MUL/PCT)
  mov eax, dword ptr [%(kd_slot)s]
  imul eax, eax, %(esz)s
  add eax, %(sched)s
  movzx ecx, word ptr [eax + 0x4]
  cmp cx, 0xffff
  je kd_t_const
  lea eax, [ecx + ecx * 2]
  shl eax, 0x4
  sub eax, ecx
  add eax, %(pool)s
  movzx edx, byte ptr [eax + 0x0a]
  movzx ebx, byte ptr [eax + 0x0b]
  cmp bl, dl
  jb kd_f1
  mov edx, ebx
kd_f1:
  movzx ebx, byte ptr [eax + 0x0c]
  cmp bl, dl
  jb kd_f2
  mov edx, ebx
kd_f2:
  movzx ebx, byte ptr [eax + 0x0d]
  cmp bl, dl
  jb kd_f3
  mov edx, ebx
kd_f3:
  movzx ebx, byte ptr [eax + 0x0e]
  cmp bl, dl
  jb kd_f4
  mov edx, ebx
kd_f4:
  imul edx, edx, %(t_fath_mul)s
  mov eax, edx
  xor edx, edx
  mov ecx, 0x64
  div ecx
  cmp eax, %(t_fath_cap)s
  jbe kd_f5
  mov eax, %(t_fath_cap)s
kd_f5:
  mov ecx, eax
  jmp kd_t_add
kd_t_const:
  mov ecx, 0xf
  jmp kd_t_add
kd_t_add:
  # P = clamp(P0 + T + B + R - cur/D_SH, P_MIN, P_MAX)  (step order identical to stub cg_t_add..cg_p_done)
  mov edx, dword ptr [%(kd_b)s]
  add edx, ecx
  add edx, 0xa
  mov ecx, dword ptr [%(kd_r)s]
  add edx, ecx
  mov ecx, dword ptr [%(kd_dim)s]
  mov eax, dword ptr [%(kd_ent)s]
  movzx ecx, byte ptr [eax + ecx + 0x0a]
  shr ecx, 0x2
  sub edx, ecx
  cmp edx, 0x5
  jge kd_p_hi
  mov edx, 0x5
kd_p_hi:
  cmp edx, 0x55
  jle kd_p_done
  mov edx, 0x55
kd_p_done:
  mov dword ptr [%(kd_p)s], edx
  # ---- M5 progress rows: invested points / popcount(dim bitmap) / months to genpuku / left this month ----
  mov eax, dword ptr [%(kd_slot)s]
  imul eax, eax, 0xc
  add eax, %(kid)s
  movzx ecx, word ptr [eax + 0x2]
  mov dword ptr [%(kd_n1)s], ecx
  movzx ecx, byte ptr [eax + 0x4]
  xor edx, edx
kd_pc:
  test ecx, ecx
  je kd_pc_done
  mov ebx, ecx
  and ebx, 0x1
  add edx, ebx
  shr ecx, 0x1
  jmp kd_pc
kd_pc_done:
  mov dword ptr [%(kd_n2)s], edx
  mov eax, %(mcap)s
  sub eax, dword ptr [%(f_cnt)s]
  jns kd_left
  xor eax, eax
kd_left:
  mov dword ptr [%(kd_n4)s], eax
  mov ecx, dword ptr [%(kd_ent)s]
  call %(age_get)s
  movzx eax, ax
  cmp eax, %(age_puku)s
  jb kd_pk
  xor eax, eax
  jmp kd_pk_done
kd_pk:
  mov ecx, %(age_puku)s
  sub ecx, eax
  imul eax, ecx, 0xc
kd_pk_done:
  mov dword ptr [%(kd_n3)s], eax
  # ---- modal loop ----
  call %(make_res)s
  call %(wait_rel)s
kd_loop:
  call kd_frame
  call kd_bars
  mov dword ptr [%(kd_lbl)s], %(str_p)s
  mov dword ptr [%(kd_lbln)s], %(len_p)s
  mov eax, dword ptr [%(kd_p)s]
  mov dword ptr [%(kd_val)s], eax
  mov dword ptr [%(kd_bar)s], eax
  mov eax, dword ptr [%(r_wy0)s]
  add eax, %(p_row)s
  mov dword ptr [%(kd_rowy)s], eax
  call kd_row
  mov dword ptr [%(kd_lbl)s], %(str_bond)s
  mov dword ptr [%(kd_lbln)s], %(len_bond)s
  mov eax, dword ptr [%(kd_bond)s]
  mov dword ptr [%(kd_val)s], eax
  mov dword ptr [%(kd_bar)s], eax
  mov eax, dword ptr [%(r_wy0)s]
  add eax, %(bond_row)s
  mov dword ptr [%(kd_rowy)s], eax
  call kd_row
  # ---- M5 four rows (KD_BAR separate from KD_VAL: value shown raw, bar drawn as ratio) ----
  mov dword ptr [%(kd_lbl)s], %(str_cnt)s
  mov dword ptr [%(kd_lbln)s], %(len_cnt)s
  mov eax, dword ptr [%(kd_n1)s]
  mov dword ptr [%(kd_val)s], eax
  imul eax, eax, 0xa
  cmp eax, 0x64
  jbe kd_q0
  mov eax, 0x64
kd_q0:
  mov dword ptr [%(kd_bar)s], eax
  mov eax, dword ptr [%(r_wy0)s]
  add eax, %(info_y0)s
  mov dword ptr [%(kd_rowy)s], eax
  call kd_row
  mov dword ptr [%(kd_lbl)s], %(str_dims)s
  mov dword ptr [%(kd_lbln)s], %(len_dims)s
  mov eax, dword ptr [%(kd_n2)s]
  mov dword ptr [%(kd_val)s], eax
  imul eax, eax, 0x14
  cmp eax, 0x64
  jbe kd_q1
  mov eax, 0x64
kd_q1:
  mov dword ptr [%(kd_bar)s], eax
  mov eax, dword ptr [%(r_wy0)s]
  add eax, %(info_y1)s
  mov dword ptr [%(kd_rowy)s], eax
  call kd_row
  mov dword ptr [%(kd_lbl)s], %(str_puku)s
  mov dword ptr [%(kd_lbln)s], %(len_puku)s
  mov eax, dword ptr [%(kd_n3)s]
  mov dword ptr [%(kd_val)s], eax
  mov eax, 0xb4
  sub eax, dword ptr [%(kd_n3)s]
  imul eax, eax, 0x5
  xor edx, edx
  mov ecx, 0x9
  div ecx
  mov dword ptr [%(kd_bar)s], eax
  mov eax, dword ptr [%(r_wy0)s]
  add eax, %(info_y2)s
  mov dword ptr [%(kd_rowy)s], eax
  call kd_row
  mov dword ptr [%(kd_lbl)s], %(str_left)s
  mov dword ptr [%(kd_lbln)s], %(len_left)s
  mov eax, dword ptr [%(kd_n4)s]
  mov dword ptr [%(kd_val)s], eax
  imul eax, eax, 0x64
  xor edx, edx
  mov ecx, %(mcap)s
  div ecx
  mov dword ptr [%(kd_bar)s], eax
  mov eax, dword ptr [%(r_wy0)s]
  add eax, %(info_y3)s
  mov dword ptr [%(kd_rowy)s], eax
  call kd_row
  call %(pump)s
  mov eax, dword ptr [%(r_quit)s]
  test eax, eax
  je kd_loop
  call %(free_res)s
  push dword ptr [%(r_hdc)s]
  push dword ptr [%(r_hwnd)s]
  call dword ptr [%(t_reldc)s]
kd_exit:
  popad
  ret

kd_frame:
  pushad
  push dword ptr [%(r_brbg)s]
  push dword ptr [%(r_hdc)s]
  call dword ptr [%(t_selobj)s]
  push dword ptr [%(r_penfr)s]
  push dword ptr [%(r_hdc)s]
  call dword ptr [%(t_selobj)s]
  push dword ptr [%(r_wy1)s]
  push dword ptr [%(r_wx1)s]
  push dword ptr [%(r_wy0)s]
  push dword ptr [%(r_wx0)s]
  push dword ptr [%(r_hdc)s]
  call dword ptr [%(t_rect)s]
  push dword ptr [%(r_penin)s]
  push dword ptr [%(r_hdc)s]
  call dword ptr [%(t_selobj)s]
  mov eax, dword ptr [%(r_wy1)s]
  sub eax, 0x6
  push eax
  mov eax, dword ptr [%(r_wx1)s]
  sub eax, 0x6
  push eax
  mov eax, dword ptr [%(r_wy0)s]
  add eax, 0x6
  push eax
  mov eax, dword ptr [%(r_wx0)s]
  add eax, 0x6
  push eax
  push dword ptr [%(r_hdc)s]
  call dword ptr [%(t_rect)s]
  push 0x1
  push dword ptr [%(r_hdc)s]
  call dword ptr [%(t_setbk)s]
  push dword ptr [%(r_ftti)s]
  push dword ptr [%(r_hdc)s]
  call dword ptr [%(t_selobj)s]
  push %(c_title)s
  push dword ptr [%(r_hdc)s]
  call dword ptr [%(t_settc)s]
  push 0x6
  push dword ptr [%(r_hdc)s]
  call dword ptr [%(t_seta)s]
  push %(len_title)s
  push %(str_title)s
  mov eax, dword ptr [%(r_wy0)s]
  add eax, %(title_y)s
  push eax
  mov eax, dword ptr [%(r_wx0)s]
  add eax, dword ptr [%(r_wx1)s]
  sar eax, 1
  push eax
  push dword ptr [%(r_hdc)s]
  call dword ptr [%(t_textout)s]
  push dword ptr [%(r_ftrl)s]
  push dword ptr [%(r_hdc)s]
  call dword ptr [%(t_selobj)s]
  push %(c_hint)s
  push dword ptr [%(r_hdc)s]
  call dword ptr [%(t_settc)s]
  push %(len_hint)s
  push %(str_hint)s
  mov eax, dword ptr [%(r_wy0)s]
  add eax, %(hint_y)s
  push eax
  mov eax, dword ptr [%(r_wx0)s]
  add eax, dword ptr [%(r_wx1)s]
  sar eax, 1
  push eax
  push dword ptr [%(r_hdc)s]
  call dword ptr [%(t_textout)s]
  popad
  ret

kd_bars:
  pushad
  xor ebx, ebx
kd_bar_l:
  cmp ebx, 0x5
  jae kd_bar_done
  mov eax, dword ptr [%(kd_strtab)s + ebx * 4]
  movzx ecx, byte ptr [eax]
  inc eax
  mov dword ptr [%(kd_lbl)s], eax
  mov dword ptr [%(kd_lbln)s], ecx
  mov eax, dword ptr [%(kd_ent)s]
  movzx eax, byte ptr [eax + ebx + 0x0a]
  mov dword ptr [%(kd_val)s], eax
  mov dword ptr [%(kd_bar)s], eax
  mov eax, ebx
  imul eax, eax, %(row_h)s
  add eax, %(row_y0)s
  add eax, dword ptr [%(r_wy0)s]
  mov dword ptr [%(kd_rowy)s], eax
  call kd_row
  inc ebx
  jmp kd_bar_l
kd_bar_done:
  popad
  ret

kd_row:
  # one row: label(KD_LBL/KD_LBLN) + value(KD_VAL) + bar (width = val*BAR_W/PCT)
  pushad
  push 0x0
  push dword ptr [%(r_hdc)s]
  call dword ptr [%(t_seta)s]
  push dword ptr [%(r_ftrl)s]
  push dword ptr [%(r_hdc)s]
  call dword ptr [%(t_selobj)s]
  push %(c_txt)s
  push dword ptr [%(r_hdc)s]
  call dword ptr [%(t_settc)s]
  push dword ptr [%(kd_lbln)s]
  push dword ptr [%(kd_lbl)s]
  push dword ptr [%(kd_rowy)s]
  mov eax, dword ptr [%(r_wx0)s]
  add eax, %(lab_x)s
  push eax
  push dword ptr [%(r_hdc)s]
  call dword ptr [%(t_textout)s]
  push %(c_val)s
  push dword ptr [%(r_hdc)s]
  call dword ptr [%(t_settc)s]
  mov eax, dword ptr [%(kd_val)s]
  call kd_itoa
  push eax
  push esi
  push dword ptr [%(kd_rowy)s]
  mov eax, dword ptr [%(r_wx0)s]
  add eax, %(val_x)s
  push eax
  push dword ptr [%(r_hdc)s]
  call dword ptr [%(t_textout)s]
  # bar width = BAR(0..100) * BAR_W / PCT  (kept in static: stdcall clobbers eax/ecx/edx)
  # KD_BAR is separate from KD_VAL: progress rows show raw value but draw a ratio bar
  mov eax, dword ptr [%(kd_bar)s]
  imul eax, eax, %(bar_w)s
  xor edx, edx
  mov ecx, 0x64
  div ecx
  mov dword ptr [%(kd_tmpw)s], eax
  # track
  push dword ptr [%(r_brbg)s]
  push dword ptr [%(r_hdc)s]
  call dword ptr [%(t_selobj)s]
  push dword ptr [%(r_penin)s]
  push dword ptr [%(r_hdc)s]
  call dword ptr [%(t_selobj)s]
  mov eax, dword ptr [%(kd_rowy)s]
  add eax, %(bar_h)s
  push eax
  mov eax, dword ptr [%(r_wx0)s]
  add eax, %(bar_x)s
  add eax, %(bar_w)s
  push eax
  push dword ptr [%(kd_rowy)s]
  mov eax, dword ptr [%(r_wx0)s]
  add eax, %(bar_x)s
  push eax
  push dword ptr [%(r_hdc)s]
  call dword ptr [%(t_rect)s]
  # fill
  push dword ptr [%(r_brsh)s]
  push dword ptr [%(r_hdc)s]
  call dword ptr [%(t_selobj)s]
  push dword ptr [%(r_penac)s]
  push dword ptr [%(r_hdc)s]
  call dword ptr [%(t_selobj)s]
  mov eax, dword ptr [%(kd_rowy)s]
  add eax, %(bar_h)s
  push eax
  mov eax, dword ptr [%(r_wx0)s]
  add eax, %(bar_x)s
  add eax, dword ptr [%(kd_tmpw)s]
  push eax
  push dword ptr [%(kd_rowy)s]
  mov eax, dword ptr [%(r_wx0)s]
  add eax, %(bar_x)s
  push eax
  push dword ptr [%(r_hdc)s]
  call dword ptr [%(t_rect)s]
  popad
  ret

kd_itoa:
  # in: eax = 0..0xff ; out: esi = string start, eax = length (buffer KD_NUM, three digits + NUL)
  push ebx
  push ecx
  push edx
  mov ebx, %(kd_num)s
  lea esi, [ebx + 0x4]
  mov byte ptr [esi], 0x0
  mov ecx, 0xa
kd_itoa_l:
  xor edx, edx
  div ecx
  dec esi
  add dl, 0x30
  mov byte ptr [esi], dl
  test eax, eax
  jnz kd_itoa_l
  mov eax, ebx
  add eax, 0x4
  sub eax, esi
  pop edx
  pop ecx
  pop ebx
  ret

kd_msg:
  # M5 feedback box: child name + line picked by activity code + "click to close".
  #   Same modal skeleton as kd_show (reuses resolve/make_res/free_res/wait_rel/pump),
  #   only three text lines, no bars; the name is read from given/surname tables (two 7B copies).
  pushad
  # Bounds first: a garbage act/slot would send the line cursor off the pool and make
  # TextOut walk arbitrary memory (that is exactly how the "spew" bug looked on screen).
  mov eax, dword ptr [%(msg_act)s]
  cmp eax, %(act_n)s
  jae kd_m_exit
  mov eax, dword ptr [%(msg_slot)s]
  cmp eax, %(slot_max)s
  jae kd_m_exit
  call %(resolve)s
  mov eax, dword ptr [%(gdio)s]
  test eax, eax
  je kd_m_exit
  call dword ptr [%(t_gaw)s]
  test eax, eax
  je kd_m_exit
  mov dword ptr [%(r_hwnd)s], eax
  push eax
  call dword ptr [%(t_getdc)s]
  test eax, eax
  je kd_m_exit
  mov dword ptr [%(r_hdc)s], eax
  push %(r_rc)s
  push dword ptr [%(r_hwnd)s]
  call dword ptr [%(t_gcrect)s]
  mov eax, dword ptr [%(r_rc)s + 0x8]
  mov dword ptr [%(r_cw)s], eax
  mov eax, dword ptr [%(r_rc)s + 0xc]
  mov dword ptr [%(r_ch)s], eax
  mov eax, dword ptr [%(r_cw)s]
  sub eax, %(mw)s
  sar eax, 1
  mov dword ptr [%(r_wx0)s], eax
  mov eax, dword ptr [%(r_ch)s]
  sub eax, %(mh)s
  sar eax, 1
  mov dword ptr [%(r_wy0)s], eax
  mov eax, dword ptr [%(r_wx0)s]
  add eax, %(mw)s
  dec eax
  mov dword ptr [%(r_wx1)s], eax
  mov eax, dword ptr [%(r_wy0)s]
  add eax, %(mh)s
  dec eax
  mov dword ptr [%(r_wy1)s], eax
  mov dword ptr [%(r_quit)s], 0
  # ---- build child name: given table 7B then surname table 7B ----
  mov eax, dword ptr [%(msg_slot)s]
  mov esi, eax
  shl esi, 0x3
  sub esi, eax
  add esi, %(giv)s
  mov edi, %(kd_nm)s
  mov ecx, 0x7
kd_m_n1:
  mov al, byte ptr [esi]
  test al, al
  je kd_m_n1e
  mov byte ptr [edi], al
  inc esi
  inc edi
  dec ecx
  jne kd_m_n1
kd_m_n1e:
  mov eax, dword ptr [%(msg_slot)s]
  mov esi, eax
  shl esi, 0x3
  sub esi, eax
  add esi, %(sur)s
  mov ecx, 0x7
kd_m_n2:
  mov al, byte ptr [esi]
  test al, al
  je kd_m_n2e
  mov byte ptr [edi], al
  inc esi
  inc edi
  dec ecx
  jne kd_m_n2
kd_m_n2e:
  mov byte ptr [edi], 0x0
  mov eax, edi
  sub eax, %(kd_nm)s
  mov dword ptr [%(kd_nmlen)s], eax
  call %(make_res)s
  call %(wait_rel)s
kd_m_loop:
  call kd_m_frame
  call %(pump)s
  mov eax, dword ptr [%(r_quit)s]
  test eax, eax
  je kd_m_loop
  call %(free_res)s
  push dword ptr [%(r_hdc)s]
  push dword ptr [%(r_hwnd)s]
  call dword ptr [%(t_reldc)s]
kd_m_exit:
  popad
  ret

kd_m_frame:
  pushad
  push dword ptr [%(r_brbg)s]
  push dword ptr [%(r_hdc)s]
  call dword ptr [%(t_selobj)s]
  push dword ptr [%(r_penfr)s]
  push dword ptr [%(r_hdc)s]
  call dword ptr [%(t_selobj)s]
  push dword ptr [%(r_wy1)s]
  push dword ptr [%(r_wx1)s]
  push dword ptr [%(r_wy0)s]
  push dword ptr [%(r_wx0)s]
  push dword ptr [%(r_hdc)s]
  call dword ptr [%(t_rect)s]
  push dword ptr [%(r_penin)s]
  push dword ptr [%(r_hdc)s]
  call dword ptr [%(t_selobj)s]
  mov eax, dword ptr [%(r_wy1)s]
  sub eax, 0x5
  push eax
  mov eax, dword ptr [%(r_wx1)s]
  sub eax, 0x5
  push eax
  mov eax, dword ptr [%(r_wy0)s]
  add eax, 0x5
  push eax
  mov eax, dword ptr [%(r_wx0)s]
  add eax, 0x5
  push eax
  push dword ptr [%(r_hdc)s]
  call dword ptr [%(t_rect)s]
  push 0x1
  push dword ptr [%(r_hdc)s]
  call dword ptr [%(t_setbk)s]
  # ---- name (title font, TA_CENTER) ----
  push dword ptr [%(r_ftti)s]
  push dword ptr [%(r_hdc)s]
  call dword ptr [%(t_selobj)s]
  push %(c_title)s
  push dword ptr [%(r_hdc)s]
  call dword ptr [%(t_settc)s]
  push 0x6
  push dword ptr [%(r_hdc)s]
  call dword ptr [%(t_seta)s]
  push dword ptr [%(kd_nmlen)s]
  push %(kd_nm)s
  mov eax, dword ptr [%(r_wy0)s]
  add eax, %(m_name_y)s
  push eax
  mov eax, dword ptr [%(r_wx0)s]
  add eax, dword ptr [%(r_wx1)s]      # CENTER X = (wx0 + wx1) / 2. NOT (wx0 + MW)/2 !
  sar eax, 1
  push eax
  push dword ptr [%(r_hdc)s]
  call dword ptr [%(t_textout)s]
  # ---- line (regular font) ----
  push dword ptr [%(r_ftrl)s]
  push dword ptr [%(r_hdc)s]
  call dword ptr [%(t_selobj)s]
  push %(c_txt)s
  push dword ptr [%(r_hdc)s]
  call dword ptr [%(t_settc)s]
  push 0x6
  push dword ptr [%(r_hdc)s]
  call dword ptr [%(t_seta)s]
  mov eax, dword ptr [%(msg_act)s]
  add eax, %(ms_line0)s
  imul eax, eax, %(ms_row)s
  add eax, %(msg_str)s
  # This pool is child_menu's MSG_STR: rows are [GBK][NUL][pad to the row width] with NO
  # length prefix, because the same pointers are fed to the native dialog 0x47BED0 (it wants
  # C strings). => we must count the bytes ourselves: TextOutA with cbString = -1 draws
  # NOTHING here (module head note 1), and reading row[0] as a length paints a GBK lead byte
  # worth of bytes = eight rows of the pool across the screen. Scan bounded by the row width.
  mov edi, eax
  xor ecx, ecx
kd_line_len:
  cmp byte ptr [edi + ecx], 0
  je kd_line_len_end
  inc ecx
  cmp ecx, %(ms_row)s
  jb kd_line_len
kd_line_len_end:
  push ecx
  push edi
  mov eax, dword ptr [%(r_wy0)s]
  add eax, %(m_line_y)s
  push eax
  mov eax, dword ptr [%(r_wx0)s]
  add eax, dword ptr [%(r_wx1)s]
  sar eax, 1
  push eax
  push dword ptr [%(r_hdc)s]
  call dword ptr [%(t_textout)s]
  # ---- bottom hint ----
  push %(c_hint)s
  push dword ptr [%(r_hdc)s]
  call dword ptr [%(t_settc)s]
  push 0x0
  push dword ptr [%(r_hdc)s]
  call dword ptr [%(t_seta)s]
  mov eax, %(msg_str)s
  add eax, %(ms_hint_off)s
  # Same shape as the line row above: count to the NUL by hand, never pass -1.
  mov edi, eax
  xor ecx, ecx
kd_hint_len:
  cmp byte ptr [edi + ecx], 0
  je kd_hint_len_end
  inc ecx
  cmp ecx, %(ms_row)s
  jb kd_hint_len
kd_hint_len_end:
  push ecx
  push edi
  mov eax, dword ptr [%(r_wy0)s]
  add eax, %(m_hint_y)s
  push eax
  mov eax, dword ptr [%(r_wx0)s]
  add eax, dword ptr [%(r_wx1)s]
  sar eax, 1
  push eax
  push dword ptr [%(r_hdc)s]
  call dword ptr [%(t_textout)s]
  popad
  ret
"""


def _hexsubs(L):
    return {k: ('0x%X' % v if isinstance(v, int) else v) for k, v in L.items()}


def build_panel(panel_va, L):
    """装配七段 (kd_show / kd_frame / kd_bars / kd_row / kd_itoa / kd_msg / kd_m_frame)。
    返回 (code, src, entries); entries = 各段入口 VA (pushad 出现顺序, 见 entry_vas)。

    L 需含: pool, sched, kid, act_tab, teach_tab, esz, player_ent,
            kd_* 静态区绝对地址 (含 M5 的 bar/n1..n4/nm/nmlen)、
            str_title/str_p/str_bond/str_hint/str_cnt/str_dims/str_puku/str_left + 各自 *_len、
            msg_str/msg_row/msg_line0/msg_hint_off/msg_act/msg_slot/f_cnt (M5 门禁计数与反馈小框)。
    """
    from keystone import Ks, KS_ARCH_X86, KS_MODE_32, KS_OPT_SYNTAX_INTEL
    subs = _hexsubs(L)
    subs.update({
        'resolve': '0x%X' % RESOLVE_VA, 'make_res': '0x%X' % MAKE_RES_VA,
        'free_res': '0x%X' % FREE_RES_VA, 'wait_rel': '0x%X' % WAIT_REL_VA,
        'pump': '0x%X' % PUMP_VA,
        'gdio': '0x%X' % GDIOK_VA, 'r_rc': '0x%X' % RC_VA,
        't_gaw': '0x%X' % T(A_GAW), 't_getdc': '0x%X' % T(A_GETDC),
        't_reldc': '0x%X' % T(A_RELDC), 't_selobj': '0x%X' % T(A_SELOBJ),
        't_rect': '0x%X' % T(A_RECT), 't_settc': '0x%X' % T(A_SETTC),
        't_setbk': '0x%X' % T(A_SETBK), 't_seta': '0x%X' % T(A_SETA),
        't_textout': '0x%X' % T(A_TEXTOUT), 't_gcrect': '0x%X' % T(A_GCRECT),
        'c_txt': '0x%X' % C_TXT, 'c_title': '0x%X' % C_TITLE,
        'c_hint': '0x%X' % C_HINT, 'c_val': '0x%X' % C_VAL,
        'pw': '0x%X' % PW, 'ph': '0x%X' % PH,
        'title_y': '0x%X' % TITLE_Y, 'hint_y': '0x%X' % HINT_Y,
        'row_h': '0x%X' % ROW_H, 'row_y0': '0x%X' % ROW_Y0,
        'p_row': '0x%X' % P_ROW, 'bond_row': '0x%X' % BOND_ROW,
        'lab_x': '0x%X' % LAB_X, 'bar_x': '0x%X' % BAR_X,
        'bar_w': '0x%X' % BAR_W, 'bar_h': '0x%X' % BAR_H,
        'val_x': '0x%X' % VAL_X,
        'info_y0': '0x%X' % INFO_Y0,
        'info_y1': '0x%X' % (INFO_Y0 + INFO_H),
        'info_y2': '0x%X' % (INFO_Y0 + 2 * INFO_H),
        'info_y3': '0x%X' % (INFO_Y0 + 3 * INFO_H),
        'mw': '0x%X' % MW, 'mh': '0x%X' % MH,
        'm_name_y': '0x%X' % M_NAME_Y, 'm_line_y': '0x%X' % M_LINE_Y,
        'm_hint_y': '0x%X' % M_HINT_Y,
        'mcap': '0x%X' % CG.MONTHLY_CAP, 'age_get': '0x%X' % CG.AGE_GET,
        'act_n': '0x%X' % len(CG.ACTS), 'slot_max': '0x%X' % SLOT_MAX_MSG,
        'ms_row': '0x%X' % L['msg_row'], 'ms_line0': '0x%X' % L['msg_line0'],
        'ms_hint_off': '0x%X' % L['msg_hint_off'],
        't_lord_mul': '0x%X' % CG.T_LORD_MUL, 't_fath_mul': '0x%X' % CG.T_FATH_MUL,
        't_lord_cap': '0x%X' % CG.T_LORD_CAP, 't_fath_cap': '0x%X' % CG.T_FATH_CAP,
        'id_mask': '0x%X' % CG.ID_MASK,
        'id_daimyo': '0x%X' % CG.ID_DAIMYO, 'id_karo': '0x%X' % CG.ID_KARO})
    for k in ('hwnd', 'hdc', 'quit', 'drag', 'moved', 'panx', 'pany',
              'wx0', 'wy0', 'wx1', 'wy1', 'vx0', 'vy0', 'vx1', 'vy1',
              'cw', 'ch', 'brbg', 'brn0', 'brsh', 'penac', 'penin', 'penfr',
              'ftti', 'ftrl'):
        subs['r_' + k] = '0x%X' % (RSTATE_VA + RS[k.upper()])
    src = SRC_ALL % subs
    lint_src(src)
    ks = Ks(KS_ARCH_X86, KS_MODE_32)
    ks.syntax = KS_OPT_SYNTAX_INTEL
    code = bytes(ks.asm(src, panel_va)[0])
    return code, src, entry_vas(code, panel_va)


# ================= 回读自检 =================
def entry_vas(code, origin):
    """各段入口 VA。按 pushad 出现顺序定位 —— 源码里就是
    kd_show / kd_frame / kd_bars / kd_row / kd_msg / kd_m_frame 这个次序
    (kd_itoa 不用 pushad, 且它不是入口: 只被 kd_row 内部 call)。"""
    ins = _dis(code, origin)
    pa = [i.address for i in ins if i.mnemonic == 'pushal']
    assert len(pa) == 6 and pa[0] == origin, pa
    return {'show': pa[0], 'frame': pa[1], 'bars': pa[2], 'row': pa[3],
            'msg': pa[4], 'msg_frame': pa[5]}


def _dis(code, origin):
    from capstone import Cs, CS_ARCH_X86, CS_MODE_32
    ins = list(Cs(CS_ARCH_X86, CS_MODE_32).disasm(code, origin))
    assert ins and sum(len(i.bytes) for i in ins) == len(code), '反汇编未覆盖全部字节'
    return ins


def selfcheck_panel(code, origin, L):
    """形态断言: P 推导与桩同式 / 五段齐全 / GDI 调用守卫 / DC 配对 / 栈帧平衡。"""
    ins = _dis(code, origin)
    cnt = lambda mn, *p: len([i for i in ins
                              if i.mnemonic == mn and all(q in i.op_str for q in p)])

    # --- 段齐全: 七个入口各一个 ret ---
    assert cnt('ret') == 7, '七段各一个 ret (命中 %d)' % cnt('ret')
    # --- P 推导与桩同式(逐条) ---
    assert cnt('imul', 'ecx, eax, 0x67') == 1, 'R = bond*BOND_MUL'
    assert cnt('shr', 'ecx, 0xa') == 1, 'R >>= BOND_SHR'
    assert cnt('add', 'edx, 0xa') == 1, 'P 基准 +P0'
    assert cnt('shr', 'ecx, 2') == 1, 'cur/4'
    assert cnt('cmp', 'edx, 5') == 1 and cnt('cmp', 'edx, 0x55') == 1, 'clamp(5,85)'
    assert cnt('imul', 'eax, eax, 0x19') == 1, '主角 主维*25/100'
    assert cnt('imul', 'edx, edx, 0x16') == 1, '父 最高维*22/100'
    assert cnt('cmp', 'eax, 0x1e') == 1 and cnt('cmp', 'eax, 0x1c') == 1, 'T 上限 30 / 28'
    assert cnt('and', 'edx, 0x700') == 1 and cnt('shr', 'edx, 8') == 1, '身分码位域'
    # ★ 2 处 = 原"无父退常数 15" + M5 的 AGE_PUKU(15) 立即数 (两个常量都是 0xf)
    assert cnt('mov', 'ecx, 0xf') == 2, '无父退常数 15 / 元服阈值 15'
    assert cnt('and', 'ecx, 3') == 1 and cnt('imul', 'ecx, ecx, 5') == 1, 'B += tier*B_STEP'
    assert cnt('cmp', 'edx, 0xf') == 1, 'B 上限 15'
    assert cnt('cmp', 'cx, -1') == 1, 'fslot 哨兵 0xffff'
    assert cnt('imul', 'eax, eax, 0xc') == 2, 'KID_TAB 12B/条 (R 计算 + M5 进度表)'
    assert cnt('imul', 'eax, eax, 8') == 1, '排程表 8B/条'
    assert cnt('imul', 'eax, eax, 4') == 1, 'ACT_TAB 4B/条'
    assert cnt('div', 'ecx') >= 3, '三处 /100 (主角/父/条宽) + itoa + M5 两条'
    # --- 复用的族谱段: 详情面板与反馈小框各一套 (每段恰 2 次) ---
    for va in (RESOLVE_VA, MAKE_RES_VA, FREE_RES_VA, WAIT_REL_VA, PUMP_VA):
        assert cnt('call', '0x%x' % va) == 2, '复用段 0x%06X 应恰 call 两次' % va
    # --- GDI 守卫: GDIOK/HWND/HDC/QUIT 四处判空 ---
    assert cnt('test', 'eax, eax') >= 4, '判空不足 (命中 %d)' % cnt('test', 'eax, eax')
    _gc = [i for i in ins if i.mnemonic == 'call'
           and i.op_str == 'dword ptr [0x%x]' % T(A_GETDC)]
    assert len(_gc) == 2, 'GetDC 两处 (详情面板 + 反馈小框)'
    for _c in _gc:
        gi = ins.index(_c)
        assert any(i.mnemonic == 'test' for i in ins[gi - 6:gi]), 'GetDC 前必须有判空'
    # --- DC 配对 ---
    assert cnt('call', 'dword ptr [0x%x]' % T(A_RELDC)) == 2
    assert cnt('call', 'dword ptr [0x%x]' % T(A_GCRECT)) == 2
    # --- 画: 五维循环 + 每行两条 Rectangle ---
    assert cnt('cmp', 'ebx, 5') == 1, '五维循环上界'
    assert cnt('call', 'dword ptr [0x%x]' % T(A_RECT)) == 6, '详情(底+内衬+轨道+填充) + 小框(底+内衬)'
    assert cnt('call', 'dword ptr [0x%x]' % T(A_TEXTOUT)) == 7, '详情 4 + 小框 3 (名/台词/提示)'
    assert cnt('call', 'dword ptr [0x%x]' % T(A_SETBK)) == 2
    # TextOutA 必须 5 参且 cchString 显式(不能是 -1): 紧贴 call 前是 push hdc,
    # 再往前一片里至少还有 4 次 push (cchString / lpString / y / x)。
    for t in [i for i in ins if i.mnemonic == 'call'
              and i.op_str == 'dword ptr [0x%x]' % T(A_TEXTOUT)]:
        j = ins.index(t)
        seq = ins[j - 12:j]
        assert ins[j - 1].mnemonic == 'push' and \
            ins[j - 1].op_str == 'dword ptr [0x%x]' % (RSTATE_VA + RS['HDC']), \
            'TextOutA 尾参必须是 hdc: %s' % ins[j - 1].op_str
        assert sum(1 for x in seq if x.mnemonic == 'push') >= 5, \
            'TextOutA 需 5 参: 命中 %d' % sum(1 for x in seq if x.mnemonic == 'push')
    # --- 栈帧: 六段 pushad/popad 成对 (kd_itoa 用 push/pop 三个寄存器) ---
    # capstone 把 0x60/0x61 打成 pushal/popal (AT&T 味的助记名), 别写 pushad/popad
    assert cnt('pushal') == 6 and cnt('popal') == 6, \
        'pushad/popad 各 6 (命中 %d/%d)' % (cnt('pushal'), cnt('popal'))
    # --- 退场: kd_show 的 kd_exit 必须是 popad/ret, 且紧接下一段的 pushad ---
    # (整段最后两条是 kd_itoa 的 pop ebx / ret, 所以只能按段边界找)
    _pa = [j for j, i in enumerate(ins) if i.mnemonic == 'pushal']
    assert len(_pa) == 6, '六段 pushad'
    _end = ins[_pa[1] - 2:_pa[1]]
    assert [i.mnemonic for i in _end] == ['popal', 'ret'], [i.mnemonic for i in _end]
    # --- M5: 进度表 (读培养记录 + 引擎虚岁 + 本月计数) ---
    assert cnt('movzx', 'ecx, word ptr [eax + 2]') == 1, '累计培养 = KID_TAB+2 已投入点'
    assert cnt('movzx', 'ecx, byte ptr [eax + 4]') == 1, '已养维度 = KID_TAB+4 增量位图'
    assert cnt('shr', 'ecx, 1') == 1, '位图 popcount 循环'
    assert cnt('call', '0x%x' % CG.AGE_GET) == 1, '距元服要读引擎虚岁 0x49A5C0'
    assert cnt('sub', 'eax, dword ptr [0x%x]' % L['f_cnt']) == 1, '本月剩余 = CAP - 已用'
    # 只数"写入"形式 (逗号在地址后): kd_row 里那条是 `mov eax, dword ptr [KD_BAR]` (读), 不算
    assert cnt('mov', 'dword ptr [0x%x], ' % L['kd_bar']) == 7, \
        'KD_BAR 与 KD_VAL 分离: 五维循环+P+亲密+进度四行 (命中 %d)' \
        % cnt('mov', 'dword ptr [0x%x], ' % L['kd_bar'])
    _ent = entry_vas(code, origin)
    assert cnt('call', '0x%x' % _ent['row']) == 7, 'kd_row 调用 = 五维循环1 + P/bond 2 + 进度 4'
    # --- M5 反馈小框 ---
    assert cnt('call', '0x%x' % _ent['msg_frame']) == 1
    assert cnt('imul', 'eax, eax, 0x%x' % L['msg_row']) == 1, '台词 = (活动码 + LINE0) * 行宽'
    assert cnt('mov', 'byte ptr [edi], 0') == 1, '名字 NUL 收尾 (写游标在 edi)'
    assert cnt('sub', 'eax, 0x%x' % L['kd_nm']) == 1, '名字长度 = 写指针 - 缓冲首'
    # ★ 反馈小框事故 (2026-10-07 实机): 串池行是 [GBK][NUL][pad], 没有长度前缀。
    #   原来照抄 kid_panel 池的 <movzx ecx,[eax]; inc eax> 解码, 于是把汉字高字节当长度,
    #   TextOut 一次画 180~213 字节 = 糊满 8 行串池, 屏幕上出现几串跨行乱字。
    assert cnt('and', 'ecx, 0xff') == 0, '反馈框不得把首字节当长度 (池无长度前缀)'
    # ★★ 第二次事故 (同日实机, 截图 = 框里只剩名字一行, 台词与提示全不见):
    #   我上一轮把 cbString 改成 -1 想绕开"首字节当长度", 但本机 TextOutA **传 -1 一个字都不画**
    #   (这是本模块头注第 1 条早就记下的坑, 族谱面板当年就踩过)。名字行因为传的是显式长度所以还在。
    #   => 唯一正确的做法: 自己数到 NUL。两条各自带"行宽上界"的扫描循环, 一个 push -1 都不许有。
    assert cnt('push', '-1') == 0, \
        'cbString 绝不能传 -1 (本机 TextOutA 一个字都不画); 必须自己数 (命中 %d)' % cnt('push', '-1')
    assert cnt('cmp', 'byte ptr [edi + ecx], 0') == 2, \
        '台词行 + 提示行各自一个"数到 NUL"循环 (命中 %d)' % cnt('cmp', 'byte ptr [edi + ecx], 0')
    assert cnt('cmp', 'ecx, 0x%x' % L['msg_row']) == 2, \
        '两个长度扫描都要以行宽为界 (防池里出现无 NUL 的行时跑飞)'
    # ★ 居中公式事故 (同一次): (wx0 + MW)/2 把文字甩到框左侧外面, 黑框里空空如也。
    _wx1 = 'dword ptr [0x%x]' % (RSTATE_VA + RS['WX1'])
    assert cnt('add', 'eax, %s' % _wx1) == 5, \
        '居中一律 (wx0+wx1)/2: 详情 2 处 + 小框 3 处 (命中 %d)' % cnt('add', 'eax, %s' % _wx1)
    assert cnt('add', 'eax, 0x%x' % MW) == 1, \
        'MW 只出现在 "wx1 = wx0 + MW - 1" 这一处; 居中一律用 wx1 (命中 %d)' % cnt('add', 'eax, 0x%x' % MW)
    return ins
