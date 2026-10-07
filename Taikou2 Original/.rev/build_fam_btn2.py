"""
家族族谱 MOD v3 —— 在 TAIK2W95_zoom.exe 基础上打补丁, 生成 TAIK2W95_family.exe

相对 v2(build_familybtn.py) 的修正 (2026-10-04):
  * **命中框对齐修正**: 绘制原点从 (160,83) 改为 **(152,58)**。
    实测依据(用户截图 1282x847, 客户区原点 (1,47), 2x 放大 -> 逻辑 = (img-origin)/2):
      - 「家族族谱」墨迹  逻辑 x 397..461 / y 116.5..132.5
      - 「统御力」行墨迹  逻辑 x 176..      (SetRect 局部 24,122)
      - 由 局部x + OX = 逻辑x 得 OX = 152 (两个独立锚点一致)
      - 由 局部y + OY + 墨迹内偏移 = 逻辑y, 且墨迹内偏移≈0 得 OY = 58
    旧值 (160,83) 使命中框落在文字**下方** 24px、右侧 8px —— 正是用户
    "点文字没用、要靠下一点才能点到" 的原因。
  * **悬停变色 / 按下变色**: 复用游戏自己的文字调色机制
    (widget+0x60 = 前景色号, +0x62 = 背景色号, 经 0x4b12b0 设置)。
    游戏自带页签用的配色就是 (fg=1,bg=7) / (fg=2,bg=7) —— 见 0x46226F / 0x4622DF。
      普通 = (0, -1) 透明底黑字 (与面板其余文字一致)
      悬停 = (1,  7) 高亮
      按下 = (2,  7)
  * HIT_PAD 3 -> 4 (命中框略放宽, 上下都有余量)

相对 ft3 的变化:
  * **不再靠 F9** —— 在「武将詳細(调查人物信息)面板」里直接画一个按钮,
    鼠标左键点它就打开族谱。F9 保留为备用触发。
  * 按钮画在面板绘制函数 0x474f20 的收尾处(0x47515e) -> 代码洞。
  * 命中判定复用游戏自己的鼠标读取 0x4F1FCB + 鼠标状态全局 0x529af0(bit0=左键),
    在调查卡消息循环 0x46e31f 的挂钩里做。

必须的前提(ft3 已确立, 本脚本沿用):
  * 族谱渲染复用游戏自带「属下武将列表」框架 0x462d40(自包含列表模态)
  * family_entry(0x535000) 复刻 0x462d40 的栈帧: sub esp,0x14 / push esi / push edi
  * family_builder 遍历 0x519868 处 370 个实体(步长47) 现算族谱根
  * 根 = [0x514ee8] 当前信息卡武将实体指针

按钮几何(面板局部坐标, 可调):
  python build_fam_btn2.py --btn X,Y,W,H --orig LX,LY
  默认 按钮 (245,57,72,18) = 面板「柴田胜家 40岁」同行右侧; 原点 (152,58)
"""
import sys, struct, argparse

SRC = r'F:\Games\Taikou 2\Taikou2 Original\TAIK2W95_zoom.exe'
DST = r'F:\Games\Taikou 2\Taikou2 Original\TAIK2W95_family.exe'
DELTA = 0xC00                      # file offset = RVA - 0xC00
off_of = lambda rva: rva - DELTA

# ---------- 按钮几何(面板局部坐标, 命令行走 --btn X,Y,W,H 覆盖) ----------
_ap = argparse.ArgumentParser()
_ap.add_argument('--btn', default='245,57,72,18', help='按钮 面板局部 X,Y,W,H (默认 245,57,72,18)')
_ap.add_argument('--out', default=None, help='输出 exe 路径')
_ap.add_argument('--src', default=None, help='输入 zoom.exe 路径')
_ap.add_argument('--orig', default='152,58', help='信息卡绘制原点 逻辑坐标 LX,LY (默认 152,58)')
# 自测开关: 关掉「调查卡循环头 0x46E31F」这条老触发路径, 只留 ★v6 的通用探测
# (卡片绘制收尾 + 另外两个卡片等待循环), 用来证明新挂钩自己能独立工作。
_ap.add_argument('--no-nav', action='store_true', help='自测: 不挂钩 0x46E31F(只留通用探测)')
_args = _ap.parse_args()
_BX, _BY, _BW, _BH = (int(v) for v in _args.btn.split(','))
ORIGIN_LX, ORIGIN_LY = (int(v) for v in _args.orig.split(','))
if _args.src: SRC = _args.src
if _args.out: DST = _args.out

# ---------- 常量 ----------
IMAGE_BASE = 0x400000                # PE ImageBase —— RVA 转 VA 的基准
CAVE_RVA = 0x135000
CAVE_VA  = IMAGE_BASE + CAVE_RVA     # 0x535000
GET_SUBJECT   = 0x49f5e0            # -> eax = 当前查看对象实体指针
RESUME        = 0x462d4c            # 属下武将页签 0x462d40 内 test si,si 起 (esi=计数)
THUNK_CALL    = 0x462559            # idx2 thunk: e8 12010000 call 0x462670
THUNK_RET_ADDR = THUNK_CALL + 5     # 0x46255e
ORIG_TARGET   = 0x462670

EBASE, ESTRIDE, ECOUNT = 0x519868, 47, 0x172   # 实体数组 / 步长 / 槽数(370)
O_SELFID, O_FATHERID, O_STATUS = 0x00, 0x1d, 0x2c
LISTBUF = 0x51e9c0                  # 全局: dword* -> 列表 UI 读取的实体指针数组
G_ROOT   = 0x5352B0                 # 洞内 dword: 预设根实体指针, 0=builder 现算

# ---------- 关系标注 ----------
FT_PAINT_VA    = 0x535400           # 洞内 painter
# v3: 0x535480 -> 0x5354A0, 给变长后的 ft_paint(多了 override 分支)让出空间
VASSAL_THUNK_VA= 0x5354B0           # 普通属下一页: 清 G_FAMILY 后 jmp 0x462d40
G_FAMILY       = 0x5354C0           # dword: 1=族谱绘制
STR_FMT3       = 0x5354D0           # "%s %s %s\0"
R_SELF   = 0x5354E0                 # "本人"
R_CHILD  = 0x5354F0                 # "子女"
R_FATHER = 0x535500                 # "父亲"
R35      = 0x535510                 # 柴田胜丰: "养子"
R38      = 0x535520                 # 佐久间盛政: "甥"
R42      = 0x535530                 # 佐久间安政: "姻戚"
R45      = R38                      # 佐久间正胜: "甥"
# ★v4: RELSTR 由 370 条缩到 64 条 —— 族谱最多 8 行/家族, 通用路径亦限 64 行。
#      腾出的 0x535700..0x535C3F (1344B) 用作族谱数据表区。
RELSTR   = 0x535600                 # dword[32]: builder 按行写入关系串地址
RELSTR_N = 32
G_FAMSEL = 0x5355D8                 # dword: 命中的 FAM_DIR 项 (start<<8)|nrow

# ---------- ★v4: 多家族族谱 (表驱动, 通用) ----------
# 背景: 运行时姓名表 0x520660(名)/0x521aa8(姓) 是按 **SNDATA S1 槽位** 填的, 实测只有 436 槽
#       有效, 且 **柴田胜丰/佐久间盛政/安政/正胜 等未登场成员完全不在其中**
#       (probe_names.py 实机取证)。故族谱数据改为 **洞内内置表**, 不再依赖姓名表。
# 触发: 当前实体 +0x00 (= S1 槽位) 查姓名表 -> (名dword, 姓dword) 命中 FAM_DIR 即展开该家族。
SUR_BASE, GIV_BASE, NAME_STRIDE, NAME_RANGE = 0x520660, 0x521aa8, 7, 0x3e8
EBASE_END = EBASE + ECOUNT * ESTRIDE
# (注意: SUR_BASE 实际是**名**表, GIV_BASE 实际是**姓**表 —— 变量名与语义相反, 沿用勿改)

# --- 洞内布局 (RELSTR 由 370 条缩到 64 条, 腾出 0x535700 起的 1344B 主空闲块) ---
FAM_DIR_VA = 0x535680                 # 每项 12B: [+0]=名dword [+4]=姓dword [+8]=(start<<8)|nrow  (仍在代码洞)
FAM_ENTRY  = 12                       # 每行 12B: [+0]=姓串ptr [+4]=名串ptr [+8]=关系串ptr
DIR_ENTRY  = 12
# ★ 族谱"串池"改放 .fdata 新节, 不再挤在代码洞 —— 柴田史实条目扩到 11 人后,
#   洞内 0x535C40 上限溢出 31B; FAM_DIR/FAM_ROWS 仍留在洞内(汇编按绝对值引用),
#   只有最大头的字符串池搬到 .fdata 的 FAM_POOL_VA. SEC_SZ 已扩到 0x5400 容纳。
#   (v8: 树形族谱 21 家 141 节点, 节内数据区重排 -> 代码区推到 0x2800,
#    旧列表串池尾随其后, 搬至 0x53AE00; 节末 0x53B400。)
FAM_POOL_VA = 0x53BC00               # .fdata 内旧列表串池基址 (= 0x536000 + 0x5C00; v13 动态族谱
                                     #   又加了通用「本人+子嗣」块(+8 节点/+1 目录)与更长的代码
                                     #   (实测末 0x5A9A) -> 旧列表串池(576B)再尾随到 0x5C00,
                                     #   池尾 0x53BE40 仍在节内)
FAM_LIMIT  = 0x53C000                # .fdata 节末 (0x536000 + 0x6000) 串池上界
                                     #   ★ 0x53C000 正是 .edata(实体池) 的起点, 再抬就撞 MOD

# ===== 家族树数据 =====
# 格式: (触发者姓, 触发者名, [ (缩进级, 姓, 名, 关系) ... ])
#   · 缩进级 0=根 1=子/同级分支 2=孙 —— 每级渲染为 2 个 ASCII 空格(游戏 ASCII 字体必含)
#   · 缩进并入"姓串", 使 painter 完全无需改动即可显示层次
#   · "·未" 后缀 = 该成员在 1560 剧本**未登场**(SNDATA @0x14 登场标志=0), 游戏内无实体
# 数据依据: BSDATA1.TR2 明文主表 (700×59B, father_id @0x29 u16 / 生年 @0x27 = 年-1490)
#            + SNDATA1.TR2 登场标志; 史实姻亲(养子/甥/妹夫)按史料补全, 库内无 father 链接者补上。
FAMILIES = (
    # 史实: 严格按血缘代际排列 —— 父在上, 兄弟姐妹与正室平级, 养子在子女辈。
    # 柴田胜音(父) -> 胜久/胜家/胜政(兄弟) + 阿市(正室, 平级) -> 胜丰(养子)。
    # 浅井茶茶/初/江是阿市与前夫浅井长政之女, 与柴田家无血缘, 不纳入本树。
    # 注: 阿市/胜政/胜音/胜久/胜丰 在 1560 剧本未登场(休眠),
    #   但为省字库串池空间省略 "·未" 后缀(历史关系已足够说明)。
    ('柴田', '胜家', (
        (0, '柴田', '胜家', '本人'),
        (1, '柴田', '胜音', '父'),
        (1, '柴田', '胜久', '兄'),
        (1, '柴田', '胜政', '弟'),
        (1, '',     '阿市', '正室'),
        (2, '柴田', '胜丰', '养子'),
    )),
    ('织田', '信长', (
        (0, '织田', '信长', '本人'),
        (1, '织田', '信忠', '长子·未'),
        (1, '织田', '信雄', '次子·未'),
        (1, '织田', '信孝', '三子·未'),
    )),
    ('毛利', '元就', (
        (0, '毛利',   '元就', '本人'),
        (1, '毛利',   '隆元', '长子'),
        (1, '吉川',   '元春', '次子'),
        (1, '小早川', '隆景', '三子'),
        (1, '穗井田', '元清', '四子·未'),
    )),
    ('北条', '氏康', (
        (0, '北条', '氏康', '本人'),
        (1, '北条', '氏政', '长子'),
        (1, '北条', '氏照', '次子·未'),
        (1, '北条', '氏邦', '三子·未'),
        (1, '北条', '氏规', '四子·未'),
        (1, '北条', '氏尧', '五子·未'),
    )),
    ('岛津', '贵久', (
        (0, '岛津', '贵久', '本人'),
        (1, '岛津', '义久', '长子'),
        (1, '岛津', '义弘', '次子'),
        (1, '岛津', '岁久', '三子'),
        (1, '岛津', '家久', '四子·未'),
    )),
    ('武田', '信玄', (
        (0, '武田', '信玄', '本人'),
        (1, '武田', '义信', '长子'),
        (1, '武田', '胜赖', '次子·未'),
        (1, '仁科', '盛信', '三子·未'),
    )),
    ('德川', '家康', (
        (0, '德川', '家康', '本人'),
        (1, '德川', '信康', '长子·未'),
        (1, '德川', '秀康', '次子·未'),
        (1, '德川', '秀忠', '三子·未'),
    )),
    ('真田', '幸隆', (
        (0, '真田', '幸隆', '本人'),
        (1, '真田', '信纲', '长子'),
        (1, '真田', '昌辉', '次子'),
        (1, '真田', '昌幸', '三子·未'),
    )),
    ('伊达', '晴宗', (
        (0, '伊达', '晴宗', '本人'),
        (1, '伊达', '辉宗', '长子'),
        (1, '留守', '政景', '次子·未'),
        (1, '石川', '昭光', '三子·未'),
    )),
    ('大友', '宗麟', (
        (0, '大友', '宗麟', '本人'),
        (1, '大友', '义统', '长子·未'),
        (1, '大友', '亲家', '次子·未'),
        (1, '大友', '亲盛', '三子·未'),
    )),
    ('森', '可成', (
        (0, '森', '可成', '本人'),
        (1, '森', '长可', '长子·未'),
        (1, '森', '兰丸', '次子·未'),
    )),
    ('最上', '义守', (
        (0, '最上', '义守', '本人'),
        (1, '最上', '义光', '长子'),
        (1, '中野', '义时', '次子·未'),
    )),
    ('吉川', '元春', (
        (0, '吉川', '元春', '本人'),
        (1, '吉川', '元长', '长子·未'),
        (1, '繁泽', '元氏', '次子·未'),
        (1, '吉川', '广家', '三子·未'),
    )),
)

# --- 自动布局: FAM_DIR -> FAM_ROWS -> 串池 ---
def _ind_sur(ind, sur):
    return '  ' * ind + sur

def _build_family_layout():
    pool, order = {}, []
    def intern(t):
        if t not in pool:
            pool[t] = None
            order.append(t)
        return t
    rows, dirs = [], []
    for tsur, tgiv, members in FAMILIES:
        start = len(rows)
        for ind, sur, giv, rel in members:
            intern(_ind_sur(ind, sur)); intern(giv); intern(rel)
            rows.append((_ind_sur(ind, sur), giv, rel))
        assert len(members) < 256 and start < 256
        dirs.append((tgiv, tsur, start, len(members)))
    va_rows = FAM_DIR_VA + len(dirs) * DIR_ENTRY
    va_str = FAM_POOL_VA                      # ★ 串池搬到 .fdata, 不再紧跟 ROWS
    v = va_str
    for t in order:
        pool[t] = v
        v += len(t.encode('gbk')) + 1          # NUL 结尾
    return dirs, rows, pool, va_rows, va_str, v

_DIRS, _ROWS, _STR, FAM_ROWS, _S_BASE, _S_END = _build_family_layout()
FAM_NROW  = len(_ROWS)                 # 总行数(跨所有家族)
FAM_TOTAL = FAM_NROW * FAM_ENTRY
assert _S_END <= FAM_LIMIT, '族谱数据溢出: 0x%06X > 0x%06X (需 %dB)' % (_S_END, FAM_LIMIT, _S_END - FAM_DIR_VA)

_tbl = bytearray()
for _s, _g, _r in _ROWS:
    _tbl += struct.pack('<III', _STR[_s], _STR[_g], _STR[_r])
assert len(_tbl) == FAM_TOTAL

_dir = bytearray()
for _g, _s, _st, _n in _DIRS:                  # [+0]=名dword [+4]=姓dword
    _dir += struct.pack('<II', struct.unpack('<I', (_g.encode('gbk') + b'\0\0\0\0')[:4])[0],
                               struct.unpack('<I', (_s.encode('gbk') + b'\0\0\0\0')[:4])[0])
    _dir += struct.pack('<I', (_st << 8) | _n)
print('  族谱表: %d 家族 / %d 行 | DIR 0x%06X(%dB) ROWS 0x%06X(%dB) 串 0x%06X..0x%06X(%dB) 余 %dB'
      % (len(_DIRS), FAM_NROW, FAM_DIR_VA, len(_dir), FAM_ROWS, FAM_TOTAL,
         _S_BASE, _S_END - 1, _S_END - _S_BASE, FAM_LIMIT - _S_END))

# ---------- 新增: 按钮 ----------
MOUSE_FN   = 0x4F1FCB               # get_mouse(int* x, int* y, int* flag)  cdecl
MOUSESTATE = 0x529AF0               # dword, bit0=左键按下, bit1=右键按下
ORIGIN_X   = 0x526C48               # 绘制原点全局(实测**随地图滚动变化**, 不能用做面板原点)
ORIGIN_Y   = 0x526C4C
# 信息卡的绘制原点(逻辑画面坐标) —— 逐像素比对实测: 局部(x,y) -> 逻辑(x+160, y+83)
#   佐证: 能力块 SetRect(24,122) 对应画面第 1 行「统御力」逻辑 y=205; 信赖度 SetRect(24,250)
#         对应逻辑 y=333 —— 两者都给出 +83, 说明 +83 是该面板绘制管线的固定偏移。
# 卡片是固定位置的模态窗(640x400 画布上), 故取常量。可用 --orig 覆盖。
PANEL_FN   = 0x4754C0               # **真正**的「武将信息卡」面板绘制函数(实测确认)
PANEL_TAIL = 0x475765               # 其收尾前: e8 66 e5 f8 ff = call 0x403cd0 (刷新文字)
SETRECT_FN = 0x4B1190               # SetRect(widget, x, y, w, h) stdcall ret 0x10
TILE_FN    = 0x4B1E60               # 贴 8x8 图案 (图案表 0x508690)
APPEND_TXT = 0x4B16D0               # AppendText(widget, str)  把文字追加进当前 SetRect, 由框架排版
TEXT_FN    = 0x420210               # Text(widget, x, y, fmt, ...) cdecl: 置笔(esi+0x58/5a)后追加
FLUSH_FN   = 0x403CD0               # 收尾刷新(原指令)
PATTERN    = 0x508690               # 面板自身用的底纹图案表
CARD_CUR   = 0x514EE8               # 信息卡当前武将实体指针(卡片循环写入)

CLICK_VA    = 0x535300              # ft_click
NAV_VA      = 0x5352C0              # nav_click 跳板(同 ft3 位置)
BTN_DRAW_VA = 0x535C40              # ft_btn_draw
TILE_TAB    = 0x535D20              # (x,y) 对表
G_BTN_CX    = 0x535E40
G_BTN_CY    = 0x535E44
G_BTN_PREV  = 0x535E48
STR_BTN     = 0x535F00              # "家族族谱"
CNT_HOOK    = 0x535E50              # ft_btn_draw 被调用次数
CNT_A       = 0x535E54              # 0x474f20 进入次数
CNT_B       = 0x535E58              # 0x4754c0 进入次数
CNT_C       = 0x535E5C              # 0x475180 进入次数
CNT_D       = 0x535E60              # 0x4753e0 进入次数
G_OX0       = 0x535E68              # 进入面板绘制时的绘制原点
G_OY0       = 0x535E6C
G_OX        = 0x535E70              # 画按钮时的绘制原点
G_OY        = 0x535E74
CNT_TRAMP   = 0x535E80              # 入口计数跳板区

# --- 诊断: 命中/鼠标/控件矩形 ---
G_RECTX     = 0x535F10              # esi+0x50 = 卡片控件矩形 X (绘制局部坐标原点)
G_RECTY     = 0x535F14              # esi+0x52 = 卡片控件矩形 Y
G_MX        = 0x535F18              # ft_click 每次捕获到的鼠标 x
G_MY        = 0x535F1C              # 鼠标 y
G_CLICK     = 0x535F20              # 捕获到的点击次数
G_HIT       = 0x535F24              # 命中按钮次数
G_RECTW     = 0x535F28              # esi+0x54 (诊断)
G_RECTH     = 0x535F2C              # esi+0x56 (诊断)
STR_FMTS    = 0x535F30              # (已废弃) "%s"
LBL_Y0      = 0x535EE0 + 0x40       # (占位, 未用)
G_WIDGET    = 0x535F38              # 诊断: 信息卡控件指针(esi)
G_IN        = 0x535F3C              # 诊断: 当前鼠标是否落在命中框内(每圈刷新, 无需点击)
# ★v6: ft_probe 重入锁。卡片绘制收尾里要调 ft_click(它会读鼠标并泵 1 条消息),
#      万一那条消息又绕回卡片绘制, 没有这道锁就会无限递归。
G_BUSY      = 0x535F40
G_PCALL     = 0x535F44              # 诊断: ft_probe 累计执行次数(证明新挂钩真的在跑)

# ---------- 两段式汇编器 ----------
class Asm:
    def __init__(self, va):
        self.va = va; self.code = bytearray(); self.labels = {}; self.f8 = []; self.f32 = []
    def pos(self): return self.va + len(self.code)
    def label(self, n): self.labels[n] = self.pos()
    def b(self, *xs): self.code.extend(bytes(xs))
    def dw(self, v): self.code.extend(struct.pack('<I', v))
    def jr8(self, op, name):
        self.code.append(op); self.code.append(0); self.f8.append((len(self.code) - 1, name))
    def callabs(self, va):
        self.code.append(0xE8); self.code.extend(b'\0\0\0\0'); self.f32.append((len(self.code) - 4, va))
    def jmpabs(self, va):
        self.code.append(0xE9); self.code.extend(b'\0\0\0\0'); self.f32.append((len(self.code) - 4, va))
    def resolve(self):
        for off, name in self.f8:
            tgt = self.labels[name]
            rel = (tgt - (self.va + off + 1))
            assert -128 <= rel <= 127, 'rel8 越界 %s %d' % (name, rel)
            self.code[off] = rel & 0xFF
        for off, tgt in self.f32:
            tgt = self.labels[tgt] if isinstance(tgt, str) else tgt
            self.code[off:off + 4] = struct.pack('<i', tgt - (self.va + off + 4))
        return bytes(self.code)


# ======================================================================
# ★v6: 新增 PE 节 .fdata —— 承载「树形家族树」的数据区 + 渲染代码
#
# 为什么新增节: 现有代码洞(0x535000-0x536000, 位于 .idata 尾部空白)只剩 ~333B,
# 而树形界面需要 ~1.8KB 数据(节点表 888B + 家族目录 260B + 串池 653B) + 渲染代码,
# 显然放不下。原 exe 节表后还有 440B 空隙(可容纳 11 个节头), 故追加一个新节,
# 其内存不在任何原有节范围内, 游戏绝不会写到它。
#
# 节参数: RVA 0x136000 (紧接 .idata 之后)  文件偏移 0x135400 (= 原文件末尾),
#         大小 0x3000(12KB), 属性 EXECUTE|READ|WRITE|INITIALIZED_DATA。
#
# !! RVA vs VA 不要混 !!
#    节头里的 VirtualAddress 写的是 **RVA**(0x136000);
#    而 ImageBase=0x400000, 所以运行时真实 **VA = 0x536000**。
#    当初把两者混为一谈, 导致渲染代码被 call 到 0x137864(未映射) -> 一点页签就崩。
#    下面统一: *_RVA 用于 PE 头 / SizeOfImage, SEC_VA 用于一切汇编里的地址引用。
#
# 渲染方式: GDI 自绘 —— 游戏原生 UI 全是 8x8 tile, 没有通用「填充矩形/画线」API
#   (0x47BF40 只是按 16px 步进贴图案, 用于进度条), 画不出圆形节点与父子连线。
#   实测(2026-10-04, gp_a2_*.png): GetDC(游戏窗口) 后 GDI 画框/线/圆/字能正常显示,
#   且 1.2s 后与鼠标移动后画面完全不变(不被游戏重绘擦除)。
#
# 该块必须在 nav_click(下方) 之前求值 —— nav_click 要拿到 TREE_ENTRY_VA。
# ======================================================================
import tree_data as TD
import tree_render as TR

IAT_GETMOD, IAT_GETPROC = 0x4fb138, 0x4fb0e0   # 与 ft_resolve 用同一组 IAT 槽位

_TREEDATA = TD.encode()
SEC_RVA, SEC_PTR, SEC_SZ = 0x136000, 0x135400, 0x6000   # 节头用的 RVA / 文件偏移 / 大小
SEC_VA   = IMAGE_BASE + SEC_RVA                          # 0x536000 运行时虚拟地址
assert SEC_VA == 0x536000 and SEC_RVA == 0x136000
# 旧代码洞 0x535000-0x536000 紧邻新节起点之前, 两者不重叠
assert CAVE_VA + 0x1000 <= SEC_VA

# 新节内偏移布局
O_GDITAB = 0x0000     # N_API × dword (26 × 4 = 104B -> 0x00-0x68)
O_GDINAM = 0x0080     # 函数名 + DLL 名 + 字体名 + 提示串 + 日志绝对路径 池(NUL 分隔, ~430B)
O_GDIOFF = 0x0340     # N_API × u16: 名字在 O_GDINAM 内的偏移
O_GDIMOD = 0x0380     # N_API × u8:  该函数所属模块索引(0=kernel32 1=user32 2=gdi32)
O_RSTATE = 0x03C0     # 运行时状态(256B)
O_SCRATCH= 0x04C0     # 临时区: RECT(16B) + MSG(28B) + POINT(8B)
O_FAMDIR = 0x0500     # FAM_DIR  28×24 = 672B -> 0x7A0  (21 家 + 别名多触发 + 末尾 1 条通用块)
O_DYNCTRL = 0x07C0    # 动态族谱控制块 0x40B: +0 桩入口dword(build_big 写; family.exe 留 0=不点亮)
                      #              +4 本次点亮数 | +8 开树次数 | +0xC 因没有本人实体而跳过
O_NODES  = 0x0800     # NODE_TAB 282×10 = 2820B -> 0x1304  (v12: 21 家 6 动态子嗣槽 + 1 个通用块)
O_OIDTAB = 0x1400     # OIDTAB   282×2 = 564B -> 0x1624 (每节点对应的实体编号 oid, 0xFFFF=无)
O_POOL   = 0x1700     # 树串池(名字/关系/标题/详情, ~9KB -> ~0x3A60); 池首 8×16B 是运行时可变区
O_DETAILTAB = 0x3B00  # 每节点 u16 -> 详情串在 O_POOL 内的偏移 (282×2 = 564B -> 0x3D34)
O_CODE   = 0x3E00     # 渲染代码(实测 7254B + 挂钩桩 -> 需 < FAM_POOL_VA 偏移 0x5C00)

O_RC, O_MSG, O_PT = O_SCRATCH + 0x00, O_SCRATCH + 0x10, O_SCRATCH + 0x30

GDI_TAB_VA   = SEC_VA + O_GDITAB
GDI_NAM_VA   = SEC_VA + O_GDINAM
GDI_OFF_VA   = SEC_VA + O_GDIOFF
GDI_MOD_VA   = SEC_VA + O_GDIMOD
RSTATE_VA    = SEC_VA + O_RSTATE
SCRATCH_VA   = SEC_VA + O_SCRATCH
RC_VA        = SEC_VA + O_RC
MSGBUF_VA    = SEC_VA + O_MSG
PT_VA        = SEC_VA + O_PT
FAMDIR_VA    = SEC_VA + O_FAMDIR
DYNCTRL_VA   = SEC_VA + O_DYNCTRL
NODES_VA     = SEC_VA + O_NODES
OIDTAB_VA    = SEC_VA + O_OIDTAB
POOL_VA      = SEC_VA + O_POOL
DETAILTAB_VA = SEC_VA + O_DETAILTAB
TREE_CODE_VA = SEC_VA + O_CODE
DYN_FN_VA    = DYNCTRL_VA                 # dword: 动态点亮桩入口(build_big 写)
DYN_LIT_VA   = DYNCTRL_VA + 0x04          # dword: 本次开树点亮了几个动态槽
DYN_CALL_VA  = DYNCTRL_VA + 0x08          # dword: 点亮桩被执行次数
DYN_NOSUB_VA = DYNCTRL_VA + 0x0C          # dword: 本人无实体(oid=0xFFFF)而跳过的次数
DYN_SLOT_VA  = DYNCTRL_VA + 0x10          # dword: tree_entry 存下的当前卡人物池槽(通用树要用)

MODS_VA  = RSTATE_VA + 0xC8      # 3 × dword: kernel32/user32/gdi32 句柄
GDIOK_VA = RSTATE_VA + 0xD8      # dword: 已解析标志

# 函数表: (模块索引, 名字)  索引即 GDI_TAB 内的槽位序号
# ★ 模块归属别凭印象写! 实测(2026-10-04, tk_tab.py 导出 GDI_TAB):
#   GetDC / ReleaseDC / GetAsyncKeyState 都导出在 **user32.dll**(不是 gdi32/kernel32)。
#   早前写成 (2,'GetDC')/(0,'GetAsyncKeyState'), GetProcAddress 直接返回 0,
#   槽位留空 -> `call dword[TAB+3*4]` == `call 0` -> 一点页签就闪退。
#   下面 build 结束前有 assert 逐个向同名 DLL 复核, 写错会当场构建失败。
API_LIST = (
    (0, 'Sleep'), (1, 'GetActiveWindow'), (1, 'PeekMessageA'),
    (1, 'GetDC'), (1, 'ReleaseDC'), (2, 'CreatePen'), (2, 'CreateSolidBrush'),
    (2, 'SelectObject'), (2, 'DeleteObject'), (2, 'Rectangle'), (2, 'Ellipse'),
    (2, 'MoveToEx'), (2, 'LineTo'), (2, 'SetTextColor'), (2, 'SetBkMode'),
    (2, 'SetTextAlign'), (2, 'TextOutA'), (2, 'CreateFontA'), (2, 'GetStockObject'),
    (1, 'GetAsyncKeyState'),
    (0, 'CreateFileA'), (0, 'WriteFile'),       # 崩溃诊断日志(写盘, 进程死了日志还在)
    (1, 'GetClientRect'),                       # 客户区尺寸 -> 面板居中
    (1, 'GetCursorPos'),                        # 鼠标拖拽平移
    (1, 'ScreenToClient'),                      # 点击命中: 屏幕光标->客户区(与 PANX/绘制同系)
    (2, 'IntersectClipRect'),                   # 树裁剪在视口内
    (2, 'SelectClipRgn'),                       # 离开时复位 DC 裁剪区 (必须放最后: A_SCLIP==N_API-1)
)
N_API = len(API_LIST)
A_SLEEP, A_GAW, A_PEEK, A_GETDC, A_RELDC = 0, 1, 2, 3, 4
A_CPEN, A_CBRUSH, A_SELOBJ, A_DELOBJ = 5, 6, 7, 8
A_RECT, A_ELLIPSE, A_MOVETO, A_LINETO = 9, 10, 11, 12
A_SETTC, A_SETBK, A_SETA, A_TEXTOUT, A_CFONT, A_GETSTK = 13, 14, 15, 16, 17, 18
A_GAKS, A_CFILE, A_WFILE = 19, 20, 21
A_GCRECT, A_GCUR = 22, 23
A_S2C, A_ICLIP, A_SCLIP = 24, 25, 26     # ScreenToClient 插在 GCUR 与 ICLIP 之间, SCLIP 必须仍为末位
assert A_SCLIP == N_API - 1 and N_API * 4 <= O_GDINAM
A = dict(SLEEP=A_SLEEP, GAW=A_GAW, PEEK=A_PEEK, GETDC=A_GETDC, RELDC=A_RELDC,
         CPEN=A_CPEN, CBRUSH=A_CBRUSH, SELOBJ=A_SELOBJ, DELOBJ=A_DELOBJ,
         RECT=A_RECT, ELLIPSE=A_ELLIPSE, MOVETO=A_MOVETO, LINETO=A_LINETO,
         SETTC=A_SETTC, SETBK=A_SETBK, SETA=A_SETA, TEXTOUT=A_TEXTOUT,
         CFONT=A_CFONT, GETSTK=A_GETSTK, GAKS=A_GAKS,
         CFILE=A_CFILE, WFILE=A_WFILE,
         GCRECT=A_GCRECT, GCUR=A_GCUR, ICLIP=A_ICLIP, SCLIP=A_SCLIP,
         S2C=A_S2C)
T = lambda i: GDI_TAB_VA + i * 4

# ---- 模块归属校验: 逐个向"声明所属的那个 DLL"要这个导出, 拿不到就构建失败 ----
#   没有这道防线时, 写错模块的后果是 GetProcAddress 静默返回 0, 槽位留空,
#   运行时 `call dword[TAB+idx*4]` == `call 0` -> 进程当场死, 且极难定位。
import ctypes as _ct
_DLLFILE = ('kernel32.dll', 'user32.dll', 'gdi32.dll')
for _mi, _fn in API_LIST:
    assert hasattr(_ct.WinDLL(_DLLFILE[_mi]), _fn), \
        'API_LIST 模块写错: %s 里没有导出 %s' % (_DLLFILE[_mi], _fn)

# RSTATE 字段偏移(每项 4B; 全部必须 4 字节对齐, 下面有重叠断言)
#   ★ 越界检查: 最大偏移 + 4 <= 0x100(O_RSTATE 的区域大小)
RS = dict(
    HWND=0x00, HDC=0x04, FAMP=0x08, QUIT=0x0C, STAGE=0x10,
    BRBG=0x14, BRN0=0x18, BRN1=0x1C, BRN2=0x20, BRSH=0x24,
    PENLN=0x28, PENF0=0x2C, PENF1=0x30, PENF2=0x34, PENAC=0x38,
    PENIN=0x3C, PENFR=0x40, FTTI=0x44, FTNM=0x48, FTRL=0x4C,
    NB=0x50, NP=0x54,
    CX=0x58, CY=0x5C, PX=0x60, PY=0x64,
    PANX=0x68, PANY=0x6C, MX0=0x70, MY0=0x74, DRAG=0x78, MOVED=0x7C,
    WX0=0x80, WY0=0x84, WX1=0x88, WY1=0x8C,
    VX0=0x90, VY0=0x94, VX1=0x98, VY1=0x9C,
    CW=0xA0, CH=0xA4, MX1=0xA8, MY1=0xAC,
    LOGB=0xB8, LOGW=0xBC, LOGH=0xC0,
    MODS=0xC8, GDIOK=0xD4,
    LASTX=0xD8, LASTY=0xDC,
    SUBJX=0xE0, SUBJY=0xE4,   # 配偶连线对端(本人)的内容坐标 cx,cy
    SPOUSEX=0xE8, SPOUSEY=0xEC, # 配偶节点本身的内容坐标（用于父折线绕开配偶）
    SPOUSEL=0xF0, SPOUSER=0xF4, # 配偶左右边界(屏幕坐标), 父折线在此断开
    SELDETOFF=0xF8,            # 点选节点详情串在 POOL 内的偏移; 0xFFFFFFFF=未选
)
# MODS(0xC8-0xD3) 紧接 GDIOK(0xD4)
assert RS['MODS'] + 12 == RS['GDIOK']
assert max(RS.values()) + 4 <= 0x100, 'RSTATE 溢出 (O_SCRATCH 在 +0x100)'

# 配色 (COLORREF = 0x00BBGGRR)
C = dict(
    BG     = 0x00281E14,   # 面板底:   深墨蓝  RGB(0x14,0x1E,0x28)
    FRAME  = 0x0060B0D8,   # 外框:     金      RGB(0xD8,0xB0,0x60)
    INNER  = 0x00887050,   # 内衬线:   暗青    RGB(0x50,0x70,0x88)
    LINE   = 0x00807868,   # 父子线:   灰蓝    RGB(0x68,0x78,0x80)
    FILL0  = 0x00103850,   # 在世填充: 暗金    RGB(0x50,0x38,0x10)
    FILL1  = 0x00444040,   # 已故填充: 暗灰    RGB(0x40,0x40,0x44)
    FILL2  = 0x00242C30,   # 未出生:   暗青灰  RGB(0x30,0x2C,0x24)
    SILH   = 0x00B0C0C8,   # 头像剪影: 浅米    RGB(0xC8,0xC0,0xB0)
    EDGE0  = 0x0020A0E0,   # 在世框线: 金橙    RGB(0xE0,0xA0,0x20)
    EDGE1  = 0x00989090,   # 已故框线: 灰      RGB(0x90,0x90,0x98)
    EDGE2  = 0x0090A8B0,   # 未出生框: 淡青    RGB(0xB0,0xA8,0x90)
    ACCENT = 0x00FFE060,   # 本人高亮: 亮青    RGB(0x60,0xE0,0xFF)
    TXT    = 0x00E8F0F0,   # 姓名:     近白    RGB(0xF0,0xF0,0xE8)
    REL    = 0x00C8B8A8,   # 关系:     浅灰蓝  RGB(0xA8,0xB8,0xC8)
    TITLE  = 0x0080E0FF,   # 标题:     淡金    RGB(0xFF,0xE0,0x80)
    HINT   = 0x0090A080,   # 底部提示: 暗黄    RGB(0x80,0xA0,0x90)
)
for _k1, _v1 in sorted(RS.items(), key=lambda kv: (kv[1], kv[0])):
    for _k0, _v0 in RS.items():
        if _v0 < _v1:
            assert _v0 + 4 <= _v1, 'RSTATE 字段重叠: %s(0x%02X)/%s(0x%02X)' % (_k0, _v0, _k1, _v1)

_sec_blob = bytearray(SEC_SZ)
_sec_blob[O_FAMDIR:O_FAMDIR + len(_TREEDATA['dir'])] = _TREEDATA['dir']
_sec_blob[O_NODES:O_NODES + len(_TREEDATA['nodes'])] = _TREEDATA['nodes']
_sec_blob[O_OIDTAB:O_OIDTAB + len(_TREEDATA['oids'])] = _TREEDATA['oids']
_sec_blob[O_POOL:O_POOL + len(_TREEDATA['pool'])] = _TREEDATA['pool']
_sec_blob[O_DETAILTAB:O_DETAILTAB + len(_TREEDATA['detail'])] = _TREEDATA['detail']
assert O_FAMDIR + len(_TREEDATA['dir']) <= O_DYNCTRL, 'FAM_DIR 溢出'
assert O_NODES + len(_TREEDATA['nodes']) <= O_OIDTAB, 'NODE_TAB 溢出'
assert O_OIDTAB + len(_TREEDATA['oids']) <= O_POOL, 'OIDTAB 溢出'
assert O_POOL + len(_TREEDATA['pool']) <= O_DETAILTAB, '树串池溢出到详情表'
assert O_DETAILTAB + len(_TREEDATA['detail']) <= O_CODE, '详情表溢出到代码区'
assert len(_TREEDATA['detail']) == _TREEDATA['nnode'] * 2, '详情表与节点数不齐'
assert len(_TREEDATA['oids']) == _TREEDATA['nnode'] * 2, 'OIDTAB 与节点数不齐'
# 动态可变区: 池首 8 条 16B 记录(6 子嗣槽 + 通用树本人 + 通用树标题)由运行时桩填姓名,
# 构建期必须全是 0(长度=0 => 一个字都不画)
assert _TREEDATA['dyn_str_base'] == 0 and \
    bytes(_TREEDATA['pool'][:_TREEDATA['gen_recs'] * _TREEDATA['dyn_str_sz']]) == \
    b'\x00' * (_TREEDATA['gen_recs'] * _TREEDATA['dyn_str_sz']), '动态姓名区没钉在池首或非零'

# 函数名串池 + 偏移表 + 模块索引表 + DLL 名
_np = bytearray()
_noff = []
for _mi, _n in API_LIST:
    _noff.append(len(_np))
    _np.extend(_n.encode('ascii') + b'\x00')
_STR_K32 = O_GDINAM + len(_np); _np.extend(b'kernel32.dll\x00')
_STR_U32 = O_GDINAM + len(_np); _np.extend(b'user32.dll\x00')
_STR_G32 = O_GDINAM + len(_np); _np.extend(b'gdi32.dll\x00')
STR_K32_VA, STR_U32_VA, STR_G32_VA = (SEC_VA + _STR_K32, SEC_VA + _STR_U32, SEC_VA + _STR_G32)
_STR_FONT = O_GDINAM + len(_np); _np.extend('宋体\x00'.encode('gbk'))
STR_FONT_VA = SEC_VA + _STR_FONT
# 注意: 池里每个串都必须带 NUL —— TextOutA 传 cchString=-1 会一直读到 NUL 为止。
# 之前这条漏了 \0, 结果把紧随其后的 "tk_tree.log" 也当成提示文字画了出来。
_STR_HINT = O_GDINAM + len(_np)
_HINT_TXT = '点人物=详情      方向键/拖拽=移动      ESC/点空白=关闭'
_np.extend(_HINT_TXT.encode('gbk') + b'\x00')
HINT_LEN = len(_HINT_TXT.encode('gbk'))
STR_HINT_VA = SEC_VA + _STR_HINT
_STR_LOG = O_GDINAM + len(_np)
_np.extend(('F:\\Games\\Taikou 2\\Taikou2 Original\\.rev\\tk_tree.log\x00').encode('gbk'))
# 用**绝对路径**: 相对路径会被游戏自己 SetCurrentDirectory 带偏, 曾有日志"凭空消失"。
STR_LOG_VA = SEC_VA + _STR_LOG
LOGBUF_VA = RSTATE_VA + RS['LOGB']
assert O_GDINAM + len(_np) <= O_GDIOFF, '函数名串池溢出 (0x%X > 0x%X)' % (O_GDINAM + len(_np), O_GDIOFF)
_sec_blob[O_GDINAM:O_GDINAM + len(_np)] = _np
for _i, ((_mi, _n), _v) in enumerate(zip(API_LIST, _noff)):
    struct.pack_into('<H', _sec_blob, O_GDIOFF + _i * 2, _v)
    struct.pack_into('<B', _sec_blob, O_GDIMOD + _i, _mi)

# 渲染代码
_rblobs, TREE_ENTRY_VA = TR.build(dict(
    CODE_VA=TREE_CODE_VA, RSTATE_VA=RSTATE_VA, GDI_TAB_VA=GDI_TAB_VA,
    GDIOK_VA=GDIOK_VA, MODS_VA=MODS_VA, MODTAB_VA=GDI_MOD_VA,
    OFFTAB_VA=GDI_OFF_VA, NAM_VA=GDI_NAM_VA, NODES_VA=NODES_VA,
    POOL_VA=POOL_VA, DETAILTAB_VA=DETAILTAB_VA, OIDTAB_VA=OIDTAB_VA,
    DYN_FN_VA=DYN_FN_VA, DYN_LIT_VA=DYN_LIT_VA, DYN_SLOT_VA=DYN_SLOT_VA,
    MSGBUF_VA=MSGBUF_VA, RC_VA=RC_VA, PT_VA=PT_VA,
    FAMDIR_VA=FAMDIR_VA,
    STR_FONT_VA=STR_FONT_VA, STR_HINT_VA=STR_HINT_VA, HINT_LEN=HINT_LEN,
    STR_LOG_VA=STR_LOG_VA, LOGBUF_VA=LOGBUF_VA,
    DLLS=(STR_K32_VA, STR_U32_VA, STR_G32_VA),
    IAT_GETMOD=IAT_GETMOD, IAT_GETPROC=IAT_GETPROC,
    CARD_CUR=CARD_CUR, N_API=N_API, NDIR=_TREEDATA['scan_ndir'],
    # 关闭时消费点击用的洞内变量(定义在下方 ft_click 段, 此处按值写死并断言)
    LBDOWN_VA=0x535EE0, LBSEEN_VA=0x535EE4, LBPREV_VA=0x535EE8,
    FAMILY_VA=G_FAMILY,
    # 动态桩在(=big.exe): 未命中史实家族的人开「本人+子嗣」通用树;
    # 动态桩不在(=family.exe, 没有 .edata): 回落柴田树(调试期兜底, 至少能验收渲染)。
    GENERIC_DIR_VA=FAMDIR_VA + _TREEDATA['generic_dir'],
    FALLBACK_VA=FAMDIR_VA + 0 * 24,
    RS=RS, T=T, A=A, C=C))
_o = O_CODE
_bloblist = []
for _nm, _bl in _rblobs:
    assert _o + len(_bl) <= SEC_SZ, '渲染代码溢出: %s' % _nm
    _sec_blob[_o:_o + len(_bl)] = _bl
    _bloblist.append((_nm, SEC_VA + _o, len(_bl)))
    print('  code  %-12s %5d B  @VA 0x%06X' % (_nm, len(_bl), SEC_VA + _o))
    _o += len(_bl)

# ---------- ★v6: 通用点击探测 ft_probe ----------
# 背景(实测 2026-10-04): 「角色详情」这张卡能从**多条路径**打开, 每条路径各有一个
#       "模态等待循环", 循环头互不相同。原先只把点击判定挂在 0x46E31F 一个循环头上,
#       所以从别的界面进去时, 根本没人调用 ft_click -> 点「家族族谱」零反应。
# 对策: 探测挂到三个**覆盖面递增**的点上, 三处共用同一段 ft_probe ——
#   ① 0x4eefa0 入口(见下方 univ_thunk): 全库 66 个调用点, 是所有"等一个事件"的
#      模态循环的公共必经之路(0x46E31F / 0x4989E3 / 0x4BA0DD 全都调它)。
#      挂这里等于一次覆盖所有界面 —— 这是本次修复的关键。
#   ② 卡片绘制收尾(ft_btn_draw): 不依赖"循环里有泵"的兜底。
#   ③ 原 0x46E31F 循环头(nav_click): 验证过的老路径, 保留。
# ft_probe 先做**零开销预检**(只看左键锁存计数 + F9), 真有点击才走
# ft_click(它会读鼠标并泵 1 条消息), 把对游戏的额外干扰压到最低。
PROBE_VA = SEC_VA + _o
_p = Asm(PROBE_VA)
_p.b(0x60)                                   # pushad
_p.b(0xFF, 0x05); _p.dw(G_PCALL)             # inc dword[G_PCALL]  (诊断: 证明在跑)
_p.b(0x83, 0x3D); _p.dw(G_BUSY); _p.b(0x00)
_p.jr8(0x75, 'out')                          # cmp [G_BUSY],0 / jnz out  (防重入)
_p.b(0xC7, 0x05); _p.dw(G_BUSY); _p.dw(1)
_p.b(0xA1); _p.dw(0x535EE0)                  # mov eax,[G_LBDOWN]
_p.b(0x3B, 0x05); _p.dw(0x535EE4)            # cmp eax,[G_LBSEEN]
_p.jr8(0x75, 'hit')                          # 有未消费的左键按下 -> 进判定
_p.callabs(0x535200)                         # 否则查 F9 备用触发(ft_kbd, 末尾有 assert)
_p.b(0x85, 0xC0); _p.jr8(0x74, 'clr')
_p.jmpabs('go')
_p.label('hit')
# 门: 只有「信息卡确实在显示」才认这次点击。
#   [0x514e0c] bit1 就是各卡片等待循环自己用的"卡片在屏"判据
#   (0x46E43C / 0x4989F2 / 0x4BA0EC 全是 test byte[0x514e0c],2 后继续等)。
_p.b(0xF6, 0x05); _p.dw(0x514E0C); _p.b(0x02)
_p.jr8(0x74, 'clr')                          # jz clr
_p.label('go')
_p.callabs(CLICK_VA)                         # eax = ft_click()
_p.b(0x85, 0xC0); _p.jr8(0x74, 'clr')
_p.callabs(TREE_ENTRY_VA)                    # 命中 -> 开族谱
_p.label('clr')
_p.b(0xC7, 0x05); _p.dw(G_BUSY); _p.dw(0)    # mov dword[G_BUSY],0
_p.label('out')
_p.b(0x61)                                   # popad
_p.b(0xC3)                                   # ret
_probe = _p.resolve()
assert _o + len(_probe) <= SEC_SZ, 'ft_probe 溢出'
_sec_blob[_o:_o + len(_probe)] = _probe
_bloblist.append(('ft_probe', SEC_VA + _o, len(_probe)))
print('  code  %-12s %5d B  @VA 0x%06X' % ('ft_probe', len(_probe), SEC_VA + _o))
_o += len(_probe)

# 0x4eefa0 入口跳板: 探测 -> 执行原前 5 字节 -> 跳回原函数 +5。
# 原前 5 字节 = 53 56 57 8B F1 (push ebx / push esi / push edi / mov esi,ecx)，
# 其中 ecx 是队列 this —— ft_probe 用 pushad/popad 包住, 不会破坏它。
UNIV_SITE = 0x4EEFA0
UNIV_THUNK_VA = SEC_VA + _o
_u = Asm(UNIV_THUNK_VA)
_u.callabs(PROBE_VA)
_u.b(0x53, 0x56, 0x57, 0x8B, 0xF1)           # 原指令
_u.jmpabs(UNIV_SITE + 5)
_univ = _u.resolve()
assert _o + len(_univ) <= SEC_SZ, 'univ_thunk 溢出'
_sec_blob[_o:_o + len(_univ)] = _univ
_bloblist.append(('univ_thunk', UNIV_THUNK_VA, len(_univ)))
print('  code  %-12s %5d B  @VA 0x%06X   [随后挂钩 0x%06X 入口(全库 66 个调用点)]'
      % ('univ_thunk', len(_univ), UNIV_THUNK_VA, UNIV_SITE))
_o += len(_univ)

# 0x4ee0d0 入口跳板 —— 另一种等待循环(0x47AE40 那一族)用的是"事件队列查询"
# 0x4ee0a0/0x4ee0d0, 而不是 0x4eefa0。补挂 0x4ee0d0 把这一族也覆盖上,
# 这样两类等待循环(共 40+ 个调用点)都能跑到点击判定。
# 原前 7 字节 = 83 EC 10 / 8D 44 24 00 = sub esp,0x10 ; lea eax,[esp]
# 跳板里复刻这 7 字节 —— pushad/popad 成对, 所以 esp 与直接进原函数完全一致。
UNIV2_SITE = 0x4EE0D0
UNIV2_THUNK_VA = SEC_VA + _o
_u2 = Asm(UNIV2_THUNK_VA)
_u2.callabs(PROBE_VA)
_u2.b(0x83, 0xEC, 0x10)                      # sub esp,0x10   (原指令 1/2)
_u2.b(0x8D, 0x44, 0x24, 0x00)                # lea eax,[esp]  (原指令 2/2)
_u2.jmpabs(UNIV2_SITE + 7)
_univ2 = _u2.resolve()
assert _o + len(_univ2) <= SEC_SZ, 'univ2_thunk 溢出'
_sec_blob[_o:_o + len(_univ2)] = _univ2
_bloblist.append(('univ2_thunk', UNIV2_THUNK_VA, len(_univ2)))
print('  code  %-12s %5d B  @VA 0x%06X   [随后挂钩 0x%06X 入口(29 个调用点)]'
      % ('univ2_thunk', len(_univ2), UNIV2_THUNK_VA, UNIV2_SITE))
_o += len(_univ2)
assert _o <= FAM_POOL_VA - SEC_VA, \
    '渲染代码溢出到旧列表串池: 代码末 0x%04X > 串池起 0x%04X' % (_o, FAM_POOL_VA - SEC_VA)
import json as _json
_json.dump(dict(sec_va=SEC_VA, sec_ptr=SEC_PTR, sec_sz=SEC_SZ, o_code=O_CODE,
                n_api=N_API, gdi_tab=GDI_TAB_VA, rstate=RSTATE_VA,
                famdir=FAMDIR_VA, nodes=NODES_VA, pool=POOL_VA,
                famp=RSTATE_VA + RS['FAMP'],
                oidtab=OIDTAB_VA, detailtab=DETAILTAB_VA,
                dyn_fn=DYN_FN_VA, dyn_lit=DYN_LIT_VA, dyn_call=DYN_CALL_VA,
                dyn_nosub=DYN_NOSUB_VA, dyn_slot=DYN_SLOT_VA,
                dyn_pool=POOL_VA + _TREEDATA['dyn_str_base'],
                dyn_str_sz=_TREEDATA['dyn_str_sz'], dyn_slots=_TREEDATA['dyn_slots'],
                generic_dir=FAMDIR_VA + _TREEDATA['generic_dir'],
                gen_nodes_va=NODES_VA + _TREEDATA['gen_start'] * 10,
                gen_static_n=_TREEDATA['gen_static_n'],
                gen_name_idx=_TREEDATA['gen_name_idx'],
                gen_title_idx=_TREEDATA['gen_title_idx'],
                gen_flag=_TREEDATA['gen_flag'],
                gen_title_suffix=_TREEDATA['gen_title_suffix'],
                gen_recs=_TREEDATA['gen_recs'],
                scan_ndir=_TREEDATA['scan_ndir'],
                ndir=_TREEDATA['ndir'], nnode=_TREEDATA['nnode'],
                nstatic=sum(m['static_n'] for m in _TREEDATA['meta']),
                entry_va=TREE_ENTRY_VA, fallback_va=FAMDIR_VA,
                blobs=[dict(name=n, va=v, size=z, off=v - SEC_VA - O_CODE)
                       for n, v, z in _bloblist]),
           open('tree_blobs.json', 'w'), indent=1)
assert TREE_ENTRY_VA == SEC_VA + O_CODE + sum(z for _, _, z in _bloblist[:len(_rblobs) - 1])
print('OK  .fdata 布局: FAM_DIR %dB @0x%06X | NODE %dB @0x%06X | POOL %dB @0x%06X | CODE %dB @0x%06X'
      % (len(_TREEDATA['dir']), FAMDIR_VA, len(_TREEDATA['nodes']), NODES_VA,
         len(_TREEDATA['pool']), POOL_VA, _o - O_CODE, TREE_CODE_VA))
print('OK  树入口 tree_entry @VA 0x%06X' % TREE_ENTRY_VA)
for _e in _TREEDATA['meta']:
    print('  树: %-6s 触发%-24s %2d人 start=%-3d 内容框%s 本人#%d'
          % (_e['title'], '/'.join(s + g for s, g in _e['triggers']),
             _e['n'], _e['start'], _e['bbox'], _e['subject']))

# ---------- family_entry ----------
ENTRY_LEN = 27
builder_va = CAVE_VA + ENTRY_LEN

fb = Asm(builder_va)
fb.b(0x53, 0x55, 0x56, 0x57)                       # push ebx,ebp,esi,edi
fb.b(0x8B, 0x1D); fb.dw(G_ROOT)                    # mov ebx,[G_ROOT]
fb.b(0x85, 0xDB)                                   # test ebx,ebx
fb.jr8(0x75, 'okroot')                             # jne okroot
fb.b(0xA1); fb.dw(0x514EE8)                        # mov eax,[0x514ee8] 当前信息卡武将实体指针
fb.b(0x3D); fb.dw(EBASE)                           # cmp eax,EBASE
fb.jr8(0x72, 'bail')                               # jb bail
fb.b(0x3D); fb.dw(EBASE_END)                       # cmp eax,EBASE_END
fb.jr8(0x73, 'bail')                               # jae bail
fb.jr8(0xEB, 'havee')                              # jmp havee
fb.label('bail')
fb.b(0x33, 0xC0)                                   # xor eax,eax
fb.b(0x5F, 0x5E, 0x5D, 0x5B)                       # pop edi,esi,ebp,ebx
fb.b(0xC3)                                         # ret
fb.label('havee')
fb.b(0x8B, 0xD8)                                   # mov ebx,eax
fb.label('okroot')
fb.b(0x0F, 0xB7, 0x2B)                             # movzx ebp,[ebx+0] 自我 oid
fb.b(0x0F, 0xB7, 0x7B, 0x1D)                       # movzx edi,[ebx+0x1d] 父id
fb.b(0x33, 0xF6)                                   # xor esi,esi
fb.b(0xBA); fb.dw(EBASE)                            # mov edx,EBASE
fb.b(0xB9); fb.dw(ECOUNT)                           # mov ecx,ECOUNT
fb.b(0x81, 0xFD); fb.dw(NAME_RANGE)                 # cmp ebp,0x3e8
fb.jr8(0x73, 'nloop0')                              # jae nloop0
# ★触发段必须保住 esi(行计数=0) 与 edi(父id) —— 通用路径依赖它们, 故先入栈。
#   两条出口都出栈, 保持栈平衡。ecx/edx 被本段占用, 由 nloop0 重置。
fb.b(0x56)                                          # push esi
fb.b(0x57)                                          # push edi
fb.b(0x6B, 0xC5, NAME_STRIDE)                       # imul eax,ebp,7
fb.b(0x05); fb.dw(SUR_BASE)                         # add eax,SUR_BASE   (名表)
fb.b(0x8B, 0x08)                                    # mov ecx,[eax]      ecx = 名dword
fb.b(0x05); fb.dw(GIV_BASE - SUR_BASE)              # add eax,(姓表-名表)
fb.b(0x8B, 0x10)                                    # mov edx,[eax]      edx = 姓dword
# ★v4: 遍历 FAM_DIR 匹配 (名,姓) -> 命中取 (start<<8)|nrow
fb.b(0xBE); fb.dw(FAM_DIR_VA)                       # mov esi,FAM_DIR_VA
fb.b(0xBF); fb.dw(len(_DIRS))                       # mov edi,NDIR
fb.label('dloop')
fb.b(0x39, 0x0E)                                    # cmp [esi],ecx      名
fb.jr8(0x75, 'dnext')
fb.b(0x39, 0x56, 0x04)                              # cmp [esi+4],edx    姓
fb.jr8(0x75, 'dnext')
fb.b(0x8B, 0x46, 0x08)                              # mov eax,[esi+8]  (start<<8)|nrow
fb.b(0xA3); fb.dw(G_FAMSEL)                         # mov [G_FAMSEL],eax
fb.b(0x5F)                                          # pop edi
fb.b(0x5E)                                          # pop esi
fb.jmpabs('shib')
fb.label('dnext')
fb.b(0x83, 0xC6, DIR_ENTRY)                         # add esi,12
fb.b(0x4F)                                          # dec edi
fb.jr8(0x75, 'dloop')
fb.b(0x5F)                                          # pop edi
fb.b(0x5E)                                          # pop esi
# 未命中 -> 走通用路径(在场亲属)。
# ★必须重置 edx/ecx: 目录循环已把 edx 推到表尾, 不重置会导致实体遍历越界。
fb.label('nloop0')
fb.b(0xBA); fb.dw(EBASE)                            # mov edx,EBASE
fb.b(0xB9); fb.dw(ECOUNT)                           # mov ecx,ECOUNT

fb.label('nloop')
fb.b(0x66, 0x8B, 0x42, 0x2C)                        # mov ax,[edx+2c]
fb.b(0xF6, 0xC4, 0x80)                             # test ah,80
fb.jr8(0x75, 'nskip')
fb.b(0xF6, 0xC4, 0x07)                             # test ah,7
fb.jr8(0x74, 'nskip')
fb.b(0x66, 0x3B, 0x6A, 0x00)                       # cmp bp,[edx+0]
fb.jr8(0x74, 'ntake')
fb.b(0x66, 0x3B, 0x6A, 0x1D)                       # cmp bp,[edx+0x1d]
fb.jr8(0x74, 'ntake')
fb.b(0x66, 0x3B, 0x7A, 0x00)                       # cmp di,[edx+0]
fb.jr8(0x75, 'nskip')
fb.label('ntake')
fb.b(0x0F, 0xB7, 0x42, 0x00)                        # movzx eax,[edx+0]
fb.b(0x66, 0x3B, 0xC5)                             # cmp ax,bp
fb.jr8(0x74, 'r_self')
fb.b(0x66, 0x3B, 0x6A, 0x1D)                       # cmp bp,[edx+0x1d]
fb.jr8(0x74, 'r_child')
fb.b(0xB8); fb.dw(R_FATHER)
fb.jr8(0xEB, 'gstore')
fb.label('r_self')
fb.b(0xB8); fb.dw(R_SELF)
fb.jr8(0xEB, 'gstore')
fb.label('r_child')
fb.b(0xB8); fb.dw(R_CHILD)
fb.label('gstore')
fb.b(0x8B, 0x1D); fb.dw(LISTBUF)
fb.b(0x89, 0x14, 0xB3)                             # mov [ebx+esi*4],edx
fb.b(0xBB); fb.dw(RELSTR)
fb.b(0x89, 0x04, 0xB3)                             # mov [ebx+esi*4],eax
fb.b(0x46)                                         # inc esi
fb.b(0x83, 0xFE, RELSTR_N)                         # cmp esi,RELSTR_N  (★v4 防RELSTR越界)
fb.jr8(0x73, 'ndone')
fb.label('nskip')
fb.b(0x83, 0xC2, 0x2F)                             # add edx,47
fb.b(0x49)                                         # dec ecx
fb.jr8(0x75, 'nloop')
fb.label('ndone')
fb.b(0x8B, 0xC6)                                   # mov eax,esi
fb.jmpabs('end')

fb.label('shib')
# ★v4: 按 G_FAMSEL=(start<<8)|nrow 展开内置家族表。
#   不在场成员(id36/39/43/46 等)压根不在 370 实体池里, 遍历必然漏 —— 必须查内置表。
#   eax = nrow, ebx = &FAM_ROWS[start], ecx = LISTBUF, esi = 行号
fb.b(0x8B, 0x0D); fb.dw(LISTBUF)                # mov ecx,[LISTBUF]   列表指针数组
fb.b(0x8B, 0x15); fb.dw(G_FAMSEL)               # mov edx,[G_FAMSEL]
fb.b(0x0F, 0xB6, 0xC2)                          # movzx eax,dl        nrow
fb.b(0x0F, 0xB6, 0xF6)                          # movzx esi,dh        start
fb.b(0x6B, 0xF6, FAM_ENTRY)                     # imul esi,esi,12
fb.b(0x81, 0xC6); fb.dw(FAM_ROWS)               # add esi,FAM_ROWS    esi = &FAM_ROWS[start]
fb.b(0x33, 0xDB)                                # xor ebx,ebx         行号
fb.label('sloop')
fb.b(0x8B, 0x16)                                # mov edx,[esi]       (姓串, 未用)
fb.b(0x89, 0x34, 0x99)                          # mov [ecx+ebx*4],esi LISTBUF[i] = 表项地址(哨兵)
fb.b(0x8B, 0x56, 0x08)                          # mov edx,[esi+8]     关系串 ptr
fb.b(0x89, 0x14, 0x9D); fb.dw(RELSTR)           # mov [RELSTR+ebx*4],edx
fb.b(0x83, 0xC6, FAM_ENTRY)                     # add esi,12
fb.b(0x43)                                      # inc ebx
fb.b(0x39, 0xC3)                                # cmp ebx,eax
fb.jr8(0x72, 'sloop')                           # jb sloop
fb.b(0x8B, 0xC3)                                # mov eax,ebx        返回行数
fb.b(0x5F, 0x5E, 0x5D, 0x5B)                    # pop edi,esi,ebp,ebx
fb.b(0xC3)                                      # ret
fb.label('end')
fb.b(0x5F, 0x5E, 0x5D, 0x5B)
fb.b(0xC3)
body = fb.resolve()
assert (builder_va - CAVE_VA) + len(body) <= (0x535200 - CAVE_VA), 'builder 与 kbd 区冲突'

# ---------- ft_resolve: 惰性解析 GetAsyncKeyState (ft_kbd / ft_click 共用) ----------
RESOLVE_VA = 0x535560
IAT_GETMOD   = 0x4fb138
IAT_GETPROC  = 0x4fb0e0
KBD_VA   = 0x535200
STR_U32  = 0x535270
STR_GAKS = 0x535280
G_GS     = 0x5352A0
G_PREV   = 0x5352A8
VK_F9    = 0x78
VK_LBUTTON = 0x01
CARD_LOOP_HEAD   = 0x46e31f
CARD_LOOP_RESUME = 0x46e324

r = Asm(RESOLVE_VA)
r.b(0xA1); r.dw(G_GS)                        # mov eax,[G_GS]
r.b(0x85, 0xC0)                              # test eax,eax
r.jr8(0x75, 'done')                          # jnz done
r.b(0x60)                                    # pushad
r.b(0x68); r.dw(STR_U32)                     # push "user32"
r.b(0xFF, 0x15); r.dw(IAT_GETMOD)            # call [GetModuleHandleA]
r.b(0x68); r.dw(STR_GAKS)                    # push "GetAsyncKeyState"
r.b(0x50)                                    # push eax
r.b(0xFF, 0x15); r.dw(IAT_GETPROC)           # call [GetProcAddress]
r.b(0x85, 0xC0)                              # test eax,eax
r.jr8(0x74, 'z')                             # jz z
r.b(0xA3); r.dw(G_GS)                        # mov [G_GS],eax
r.label('z')
r.b(0x61)                                    # popad
r.b(0xA1); r.dw(G_GS)                        # mov eax,[G_GS]
r.label('done')
r.b(0xC3)                                    # ret
resolve = r.resolve()

a = Asm(KBD_VA)
a.b(0x51)                                    # push ecx
a.callabs(RESOLVE_VA)                        # eax = GetAsyncKeyState 指针
a.b(0x85, 0xC0)                              # test eax,eax
a.jr8(0x74, 'zero')                          # jz zero
a.b(0x8B, 0xC8)                              # mov ecx,eax
a.b(0x6A, VK_F9)                             # push VK_F9
a.b(0xFF, 0xD1)                              # call ecx (stdcall 自清4)
a.b(0x0F, 0xB7, 0xC0)                        # movzx eax,ax
a.b(0x25); a.dw(0x8000)                      # and eax,0x8000
a.jr8(0x74, 'up')                            # jz up
a.b(0x80, 0x3D); a.dw(G_PREV); a.b(0x00)     # cmp byte[G_PREV],0
a.jr8(0x75, 'zero')                          # jne zero
a.b(0xC6, 0x05); a.dw(G_PREV); a.b(0x01)     # mov byte[G_PREV],1
a.b(0xB8); a.dw(1)                           # mov eax,1
a.jr8(0xEB, 'done')                          # jmp done
a.label('up')
a.b(0xC6, 0x05); a.dw(G_PREV); a.b(0x00)     # mov byte[G_PREV],0
a.label('zero')
a.b(0x31, 0xC0)                              # xor eax,eax
a.label('done')
a.b(0x59)                                    # pop ecx
a.b(0xC3)                                    # ret
kbd = a.resolve()
assert (KBD_VA - CAVE_VA) + len(kbd) <= (STR_U32 - CAVE_VA), 'ft_kbd 撞 STR_U32'
assert (0x535200, 0x535300) == (KBD_VA, CLICK_VA), 'ft_probe 里写死的 ft_kbd/ft_click 地址已过期'

# ---------- family_entry 代码 ----------
e = bytearray()
def ee(d): e.extend(d)
ee(b'\xc7\x05' + struct.pack('<I', G_FAMILY) + b'\x01\x00\x00\x00')  # mov dword[G_FAMILY],1
ee(b'\x83\xec\x14')                                         # sub esp,0x14
ee(b'\x56')                                                 # push esi
ee(b'\x57')                                                 # push edi
ee(b'\xe8' + struct.pack('<i', builder_va - (CAVE_VA + len(e) + 5)))
ee(b'\x8b\xf0')                                             # mov esi,eax
ee(b'\xe9' + struct.pack('<i', RESUME - (CAVE_VA + len(e) + 5)))
assert len(e) == ENTRY_LEN, len(e)

# ---------- ft_click (两路触发: WM_LBUTTONDOWN 锁存 + 轮询边沿) ----------
BTN_X, BTN_Y, BTN_W, BTN_H = _BX, _BY, _BW, _BH  # 面板局部坐标, 可被 --btn 覆盖
HIT_PAD = 4                                        # 命中框比文字框各向外扩 4px(容错)
HIT_W, HIT_H = BTN_W + 2 * HIT_PAD, BTN_H + 2 * HIT_PAD
# 局部坐标系实测锚点: 能力块 SetRect(0x18,0x7a,0x58,0x78) = (24,122,88,120),
#                     信赖度 SetRect(0x18,0xfa,0x118,0x18) = (24,250,280,24)
# 按钮放在「部将」正下方 (局部 245,57)
G_LBDOWN  = 0x535EE0    # dword: WM_LBUTTONDOWN 累计次数(游戏 WndProc 里 inc)
G_LBSEEN  = 0x535EE4    # dword: ft_click 已消费到哪一次
G_LBPREV  = 0x535EE8    # dword: 轮询式边沿检测的上一状态
G_LOOPCNT = 0x535EEC    # dword: 诊断——信息卡消息循环转了多少圈
assert (G_LBDOWN, G_LBSEEN, G_LBPREV) == (0x535EE0, 0x535EE4, 0x535EE8), \
    '树渲染层(v6 段)里写死的 LB* 地址与此处不一致'

c = Asm(CLICK_VA)
c.b(0x53, 0x56, 0x57)                        # push ebx,esi,edi
c.b(0x83, 0xEC, 0x10)                        # sub esp,0x10  [esp]=x [esp+4]=y [esp+8]=flag
# --- 门: 只有「武将信息卡正在显示」时才响应 ([0x514ee8] 非0) ---
c.b(0xA1); c.dw(CARD_CUR)                    # mov eax,[0x514ee8]
c.b(0x85, 0xC0)                              # test eax,eax
c.jr8(0x75, 'cardok')                        # jnz cardok
c.jmpabs('miss')                             # jz miss (远跳, 函数变长后 rel8 不够用)
c.label('cardok')
c.b(0x8D, 0x44, 0x24, 0x08); c.b(0x50)       # lea eax,[esp+8]; push eax   -> &flag
c.b(0x8D, 0x44, 0x24, 0x08); c.b(0x50)       # lea eax,[esp+8]; push eax   -> &y
c.b(0x8D, 0x44, 0x24, 0x08); c.b(0x50)       # lea eax,[esp+8]; push eax   -> &x
c.callabs(MOUSE_FN)                          # 取鼠标逻辑坐标(内部泵消息, 顺带推进锁存计数)
c.b(0x83, 0xC4, 0x0C)                        # add esp,0xc (cdecl)
# --- 诊断: 每圈刷新「鼠标是否落在命中框内」(不需要点击, 用于标定) ---
c.b(0x31, 0xD2)                              # xor edx,edx
c.b(0x8B, 0x04, 0x24)                        # mov eax,[esp]     鼠标 x
c.b(0x2B, 0x05); c.dw(G_BTN_CX)              # sub eax,[G_BTN_CX]
c.b(0x3D); c.dw(HIT_W)                       # cmp eax,HIT_W
c.jr8(0x73, 'in0')                           # jae in0
c.b(0x8B, 0x44, 0x24, 0x04)                  # mov eax,[esp+4]   鼠标 y
c.b(0x2B, 0x05); c.dw(G_BTN_CY)              # sub eax,[G_BTN_CY]
c.b(0x3D); c.dw(HIT_H)                       # cmp eax,HIT_H
c.jr8(0x73, 'in0')                           # jae in0
c.b(0x42)                                    # inc edx
c.label('in0')
c.b(0x89, 0x15); c.dw(G_IN)                  # mov [G_IN],edx
# --- A) 事件锁存: 游戏自己处理过 WM_LBUTTONDOWN, 就说明有一次真实左键按下 ---
c.b(0xA1); c.dw(G_LBDOWN)                    # mov eax,[G_LBDOWN]
c.b(0x3B, 0x05); c.dw(G_LBSEEN)              # cmp eax,[G_LBSEEN]
c.jr8(0x75, 'haveclick')                     # jne haveclick
# --- B) 兜底: 当前左键按下 + 上升沿 ---
c.callabs(RESOLVE_VA)                        # eax = GetAsyncKeyState 指针
c.b(0x85, 0xC0)                              # test eax,eax
c.jr8(0x74, 'miss')                          # jz miss
c.b(0x6A, VK_LBUTTON)                        # push VK_LBUTTON(1)
c.b(0xFF, 0xD0)                              # call eax  (stdcall 自清4)
c.b(0x0F, 0xB7, 0xC0)                        # movzx eax,ax
c.b(0x25); c.dw(0x8000)                      # and eax,0x8000  高位置位=当前按下
c.jr8(0x74, 'up')                            # jz up
c.b(0x83, 0x3D); c.dw(G_LBPREV); c.b(0x00)   # cmp dword[G_LBPREV],0
c.jr8(0x75, 'miss')                          # jne miss (已计过)
c.b(0xC7, 0x05); c.dw(G_LBPREV); c.dw(1)     # mov dword[G_LBPREV],1
c.jr8(0xEB, 'haveclick')                     # jmp haveclick
c.label('up')
c.b(0xC7, 0x05); c.dw(G_LBPREV); c.dw(0)     # mov dword[G_LBPREV],0
c.label('miss')
c.b(0x31, 0xC0)                              # xor eax,eax
c.jr8(0xEB, 'done')                          # jmp done
# --- 命中判定(面板局部坐标, 与鼠标同空间) ---
c.label('haveclick')
c.b(0xFF, 0x05); c.dw(G_CLICK)               # inc dword[G_CLICK]
c.b(0x8B, 0x04, 0x24); c.b(0xA3); c.dw(G_MX) # mov [G_MX],eax   ([esp]=x)
c.b(0x8B, 0x44, 0x24, 0x04); c.b(0xA3); c.dw(G_MY)  # mov [G_MY],eax ([esp+4]=y)
c.b(0xA1); c.dw(G_LBDOWN)                    # mov eax,[G_LBDOWN]
c.b(0xA3); c.dw(G_LBSEEN)                    # mov [G_LBSEEN],eax  (消费掉这次按下)
c.b(0x8B, 0x04, 0x24)                        # mov eax,[esp]   (鼠标 逻辑x)
c.b(0x2B, 0x05); c.dw(G_BTN_CX)              # sub eax,[G_BTN_CX]
c.b(0x3D); c.dw(HIT_W)                       # cmp eax,HIT_W
c.jr8(0x73, 'miss2')                         # jae miss2
c.b(0x8B, 0x44, 0x24, 0x04)                  # mov eax,[esp+4] (鼠标 逻辑y)
c.b(0x2B, 0x05); c.dw(G_BTN_CY)              # sub eax,[G_BTN_CY]
c.b(0x3D); c.dw(HIT_H)                       # cmp eax,HIT_H
c.jr8(0x73, 'miss2')                         # jae miss2
c.b(0xFF, 0x05); c.dw(G_HIT)                 # inc dword[G_HIT]
c.b(0xB8); c.dw(1)                           # mov eax,1
c.jr8(0xEB, 'done')                          # jmp done
c.label('miss2')
c.b(0x31, 0xC0)                              # xor eax,eax
c.label('done')
c.b(0x83, 0xC4, 0x10)                        # add esp,0x10
c.b(0x5F, 0x5E, 0x5B)                        # pop edi,esi,ebx
c.b(0xC3)
click = c.resolve()
assert (CLICK_VA - CAVE_VA) + len(click) <= (FT_PAINT_VA - CAVE_VA), 'ft_click 越界 %d' % len(click)

# ---------- ft_latch: 挂钩游戏 WndProc 的 WM_LBUTTONDOWN 分支 ----------
#   0x4F1F84: 83 0D F0 9A 52 00 01 = or dword[0x529af0],1   (7 字节)
#   替换前 5 字节为 jmp 洞; 洞内 计数 + 原指令 + 跳回 0x4F1F8B
#   实测: 真正生效的是 0x4F26AF (WndProc 里那份), 0x4F1F84 是另一份泵里的副本 —— 两处都挂.
LATCH_SITES = ((0x4F1F84, 0x5355A0), (0x4F26AF, 0x5355C0))
latches = []
for _site, _tva in LATCH_SITES:
    l = Asm(_tva)
    l.b(0xFF, 0x05); l.dw(G_LBDOWN)              # inc dword[G_LBDOWN]
    l.b(0x83, 0x0D); l.dw(0x529AF0); l.b(0x01)   # or dword[0x529af0],1  (原指令)
    l.jmpabs(_site + 7)                          # jmp 到原指令之后
    _blob = l.resolve()
    latches.append((_site, _tva, _blob))
    assert (_tva - CAVE_VA) + len(_blob) <= (RELSTR - CAVE_VA), 'ft_latch 撞 RELSTR'


# ---------- ft_btn_draw (画按钮文字, 挂在信息卡绘制函数 0x4754c0 的收尾 0x475765) ----------
d = Asm(BTN_DRAW_VA)
d.b(0x50, 0x51, 0x52, 0x53, 0x55, 0x57)      # push eax,ecx,edx,ebx,ebp,edi
d.b(0xFF, 0x05); d.dw(CNT_HOOK)              # inc dword[CNT_HOOK]  (诊断)
# --- 门: 仅当「信息卡正在显示本武将」才画 ([0x514ee8] 非0 且 == [esi+0x100]) ---
d.b(0xA1); d.dw(CARD_CUR)                    # mov eax,[0x514ee8]
d.b(0x85, 0xC0)                              # test eax,eax
d.jr8(0x74, 'gofail')                        # jz gofail
d.b(0x3B, 0x86); d.dw(0x100)                 # cmp eax,[esi+0x100]
d.jr8(0x75, 'gofail')                        # jne gofail
d.jr8(0xEB, 'draw')                          # jmp draw
d.label('gofail')
d.jmpabs('skip')                             # 远跳(绝对)
d.label('draw')
# --- 留档诊断: 卡片控件指针 + 它当前的 (x,y,w,h) ---
d.b(0x89, 0x35); d.dw(G_WIDGET)              # mov [G_WIDGET],esi
d.b(0x0F, 0xB7, 0x86); d.dw(0x50); d.b(0xA3); d.dw(G_RECTX)
d.b(0x0F, 0xB7, 0x8E); d.dw(0x52); d.b(0x89, 0x0D); d.dw(G_RECTY)
d.b(0x0F, 0xB7, 0x86); d.dw(0x54); d.b(0xA3); d.dw(G_RECTW)
d.b(0x0F, 0xB7, 0x86); d.dw(0x56); d.b(0xA3); d.dw(G_RECTH)
d.b(0xA1); d.dw(ORIGIN_X); d.b(0xA3); d.dw(G_OX)   # 全局绘制原点(随地图滚动, 仅留档)
d.b(0xA1); d.dw(ORIGIN_Y); d.b(0xA3); d.dw(G_OY)
# --- 命中矩形: 面板局部坐标 -> 逻辑画面坐标 (固定模态窗, 原点常量) ---
d.b(0xB8); d.dw(ORIGIN_LX + BTN_X - HIT_PAD); d.b(0xA3); d.dw(G_BTN_CX)
d.b(0xB8); d.dw(ORIGIN_LY + BTN_Y - HIT_PAD); d.b(0xA3); d.dw(G_BTN_CY)
# --- 交互配色: 依据 G_IN(鼠标在框内) 与 左键当前是否按下, 选 fg/bg 色号 ---
#     0x4b12b0(widget, fg, bg);  push bg 后再 push fg (stdcall 从右往左)
SETCOL_FN = 0x4B12B0
d.b(0x31, 0xD2)                              # xor edx,edx   edx: 0=普通
d.b(0xA1); d.dw(G_IN)                        # mov eax,[G_IN]
d.b(0x85, 0xC0)                              # test eax,eax
d.jr8(0x74, 'colsel')                        # jz colsel     不在框内 -> 普通
d.b(0x42)                                    # inc edx        悬停
d.callabs(RESOLVE_VA)                        # eax = GetAsyncKeyState
d.b(0x85, 0xC0)                              # test eax,eax
d.jr8(0x74, 'colsel')                        # jz colsel
d.b(0x6A, VK_LBUTTON)                        # push VK_LBUTTON
d.b(0xFF, 0xD0)                              # call eax
d.b(0x0F, 0xB7, 0xC0)                        # movzx eax,ax
d.b(0x25); d.dw(0x8000)                      # and eax,0x8000
d.jr8(0x74, 'colsel')                        # jz colsel     左键未按
d.b(0x42)                                    # inc edx        按下
d.label('colsel')
d.b(0x83, 0xFA, 0x02)                        # cmp edx,2
d.jr8(0x74, 'colpress')                      # je colpress
d.b(0x85, 0xD2)                              # test edx,edx
d.jr8(0x74, 'colnorm')                       # jz colnorm
d.b(0x6A, 0x07); d.b(0x6A, 0x01)             # push 7; push 1  悬停 (fg=1,bg=7)
d.b(0x8B, 0xCE)                              # mov ecx,esi
d.callabs(SETCOL_FN)
d.jr8(0xEB, 'coldone')                       # jmp coldone
d.label('colpress')
d.b(0x6A, 0x07); d.b(0x6A, 0x02)             # push 7; push 2  按下 (fg=2,bg=7)
d.b(0x8B, 0xCE)                              # mov ecx,esi
d.callabs(SETCOL_FN)
d.jr8(0xEB, 'coldone')
d.label('colnorm')
d.b(0x6A, 0xFF); d.b(0x6A, 0x00)             # push -1; push 0 普通 (fg=0,bg=透明)
d.b(0x8B, 0xCE)                              # mov ecx,esi
d.callabs(SETCOL_FN)
d.label('coldone')
# --- 字: SetRect(widget, BTN_X, BTN_Y, BTN_W, BTN_H) + AppendText ---
d.b(0x8B, 0xCE)                              # mov ecx,esi
d.b(0x68); d.dw(BTN_H)
d.b(0x68); d.dw(BTN_W)
d.b(0x68); d.dw(BTN_Y)
d.b(0x68); d.dw(BTN_X)
d.callabs(SETRECT_FN)                        # SetRect(widget,x,y,w,h)
d.b(0x68); d.dw(STR_BTN)                     # push "家族族谱"
d.b(0x8B, 0xCE)                              # mov ecx,esi
d.callabs(APPEND_TXT)                        # AppendText(widget, str)
# 恢复面板默认配色, 避免影响后续绘制
d.b(0x6A, 0xFF); d.b(0x6A, 0x00)             # push -1; push 0
d.b(0x8B, 0xCE)                              # mov ecx,esi
d.callabs(SETCOL_FN)
# --- ★v6: 通用点击探测 ---
#   挂在「卡片绘制收尾」而不是某个模态循环头: 0x4754c0 是信息卡**本体**的绘制函数,
#   不管从哪条路径进入角色详情, 这一帧都要画它 -> 任何入口都必然经过这里。
#   放在 flush 之前, 且只在 draw 分支(命中卡片)才探测 —— gofail 分支
#   (别的卡片/控件在画)会跳过, 避免拿过期的 CARD_CUR 误判。
d.b(0x8B, 0xCE)                              # mov ecx,esi
d.callabs(FLUSH_FN)                          # 先把卡片上屏, 族谱再叠在上面
d.callabs(PROBE_VA)
d.jmpabs('end')
d.label('skip')
d.b(0x8B, 0xCE)                              # mov ecx,esi
d.callabs(FLUSH_FN)                          # 原指令: call 0x403cd0
d.label('end')
d.b(0x5F, 0x5D, 0x5B, 0x5A, 0x59, 0x58)      # pop edi,ebp,ebx,edx,ecx,eax
d.b(0x5F, 0x5E, 0x5B)                        # 原收尾: pop edi,esi,ebx
d.b(0x83, 0xC4, 0x5C)                        # add esp,0x5c
d.b(0xC3)                                    # ret
btn_draw = d.resolve()
assert (BTN_DRAW_VA - CAVE_VA) + len(btn_draw) <= (G_BTN_CX - CAVE_VA), 'ft_btn_draw 溢出到全局区 %d' % len(btn_draw)

# ---------- 诊断: 入口计数跳板 (判明究竟哪个函数在画这张卡) ----------
DIAG = [
    (0x474F20, bytes([0x83, 0xEC, 0x10, 0x53, 0x55]), CNT_A, '面板绘制A(旧假设)', False),
    (0x4754C0, bytes([0x83, 0xEC, 0x5C, 0x53, 0x56]), CNT_B, '面板绘制B(**实测真身**)', True),
    (0x475180, bytes([0x8B, 0x44, 0x24, 0x08, 0x56]), CNT_C, '能力条绘制', False),
    (0x4753E0, bytes([0x53, 0x8B, 0x5C, 0x24, 0x0C]), CNT_D, '信赖度绘制', False),
]
tramps = []
_tva = CNT_TRAMP
for _va, _orig, _cnt, _nm, _cap in DIAG:
    t = Asm(_tva)
    t.b(0xFF, 0x05); t.dw(_cnt)              # inc dword[CNT]
    if _cap:                                  # 记录进入时的绘制原点
        t.b(0x50)                             # push eax
        t.b(0xA1); t.dw(ORIGIN_X); t.b(0xA3); t.dw(G_OX0)
        t.b(0xA1); t.dw(ORIGIN_Y); t.b(0xA3); t.dw(G_OY0)
        t.b(0x58)                             # pop eax
    t.b(*_orig)                              # 原前 5 字节
    t.jmpabs(_va + 5)                        # 回到原函数 +5
    _blob = t.resolve()
    tramps.append((_va, _orig, _nm, _tva, _blob))
    _tva += len(_blob)
assert (_tva - CAVE_VA) <= (STR_BTN - CAVE_VA), '诊断跳板撞 STR_BTN'

# ---------- nav_click ----------
n = Asm(NAV_VA)
n.b(0xFF, 0x05); n.dw(G_LOOPCNT)             # inc dword[G_LOOPCNT] (诊断: 循环转速)
n.callabs(CLICK_VA)                          # call ft_click
n.b(0x85, 0xC0)                              # test eax,eax
n.jr8(0x74, 'tryf9')                         # je tryf9
n.b(0x60)                                    # pushad
n.callabs(TREE_ENTRY_VA)                     # call tree_entry (树形族谱, .fdata 节)
n.b(0x61)                                    # popad
n.jr8(0xEB, 'skip')                          # jmp skip
n.label('tryf9')
n.callabs(KBD_VA)                            # F9 备用
n.b(0x85, 0xC0)
n.jr8(0x74, 'skip')
n.b(0x60)
n.callabs(TREE_ENTRY_VA)
n.b(0x61)
n.label('skip')
n.b(0xA1); n.dw(0x520630)                    # 原指令 mov eax,[0x520630]
n.jmpabs(CARD_LOOP_RESUME)
nav = n.resolve()
assert (NAV_VA - CAVE_VA) + len(nav) <= (CLICK_VA - CAVE_VA), 'nav_click 撞 ft_click'

# ---------- ft_paint ----------
p = Asm(FT_PAINT_VA)
p.b(0x53, 0x56, 0x57)
p.b(0x0F, 0xBF, 0x44, 0x24, 0x10)
p.b(0x8B, 0x0D); p.dw(0x514014)
p.b(0x81, 0xE1); p.b(0xFF, 0x00, 0x00, 0x00)
p.b(0x03, 0xC1)
p.b(0x8B, 0xF8)
p.b(0x8B, 0x15); p.dw(LISTBUF)
p.b(0x8B, 0x34, 0x82)
p.b(0x8B, 0x0D); p.dw(G_FAMILY)
p.b(0x85, 0xC9)
p.jr8(0x75, 'fam')
p.b(0x8B, 0xCE)
p.callabs(0x49c310)
p.b(0x50)
p.b(0x8B, 0xCE)
p.callabs(0x49c2b0)
p.b(0x50)
p.b(0x68); p.dw(0x504a90)
p.b(0x68); p.dw(0x5196a8)
p.callabs(0x4ec870)
p.b(0x83, 0xC4, 0x10)
p.jr8(0xEB, 'done')
p.label('fam')
# ★v3: esi = LISTBUF[idx]。若落在内置表 FAM_ROWS 区间内 -> 该行是"不在场成员",
#      姓名/关系串直接从表项取 (它们不在运行时姓名表里, 无法走 getter)。
# 注: 上一版此处误用 fb.b(...) 写入 builder 缓冲而 p.dw(...) 写入 painter 缓冲,
#     导致 cmp 指令缺少 81 FE 操作码 —— override 判定失效。已修正为同一实例。
p.b(0x81, 0xFE); p.dw(FAM_ROWS)                 # cmp esi,FAM_ROWS
p.jr8(0x72, 'real')                             # jb real
p.b(0x81, 0xFE); p.dw(FAM_ROWS + FAM_TOTAL - FAM_ENTRY)   # cmp esi, 末项
p.jr8(0x77, 'real')                             # ja real
# ---- override: [esi+0]=姓 [esi+4]=名 [esi+8]=关系 ----
p.b(0xFF, 0x76, 0x08)                           # push dword[esi+8]  关系串
p.b(0xFF, 0x76, 0x04)                           # push dword[esi+4]  名
p.b(0xFF, 0x36)                                 # push dword[esi]    姓
p.b(0x68); p.dw(STR_FMT3)
p.b(0x68); p.dw(0x5196a8)
p.callabs(0x4ec870)
p.b(0x83, 0xC4, 0x14)
p.jr8(0xEB, 'done')
p.label('real')
p.b(0x8B, 0x14, 0xBD); p.dw(RELSTR)
p.b(0x52)
p.b(0x8B, 0xCE)
p.callabs(0x49c310)
p.b(0x50)
p.b(0x8B, 0xCE)
p.callabs(0x49c2b0)
p.b(0x50)
p.b(0x68); p.dw(STR_FMT3)
p.b(0x68); p.dw(0x5196a8)
p.callabs(0x4ec870)
p.b(0x83, 0xC4, 0x14)
p.label('done')
p.b(0x5F, 0x5E, 0x5B)
p.b(0xC3)
paint = p.resolve()
assert (FT_PAINT_VA - CAVE_VA) + len(paint) <= (VASSAL_THUNK_VA - CAVE_VA), 'ft_paint 撞 vassal_thunk'

# ---------- vassal_thunk ----------
t = Asm(VASSAL_THUNK_VA)
t.b(0xC7, 0x05); t.dw(G_FAMILY); t.b(0x00, 0x00, 0x00, 0x00)
t.jmpabs(0x462d40)
thunk = t.resolve()
assert (VASSAL_THUNK_VA - CAVE_VA) + len(thunk) <= (G_FAMILY - CAVE_VA), 'vassal_thunk 撞 G_FAMILY'

# ================= ★v5 修复: 族谱"一闪即被覆盖" =================
# 症状: 点「家族族谱」→ 族谱闪一下 → 立刻变成一张数值错乱的属性卡。
# 反汇编 0x462D40(通用列表模态) 后确认两条独立缺陷:
#
#  [缺陷1] 触发族谱的那次左键**尚未释放**就进了模态。
#     列表模态 0x47B590/0x47B430 读的是实时键态, 于是把"仍按着"当成
#     "选中第 0 行" 立即消费 → 族谱瞬间被关掉。
#     修复: 在模态入口 0x462D4C(test si,si) 处先等左键释放(带忙等上限)。
#
#  [缺陷2] 选中处理 0x462D93 之后会执行
#         `mov edx,[LISTBUF+sel*4]` / `mov [0x514ee8],edx`
#     —— 把"当前查看武将(CARD_CUR)"换成被选中那一行。
#     族谱行的 LISTBUF 是洞内表项地址(哨兵 &FAM_ROWS[i]), 不是实体指针,
#     写进 CARD_CUR 后信息卡会用洞内数据当武将属性渲染 → 错乱属性卡。
#     修复: 族谱模式下不走"选中切换", 直接退出(族谱是只读视图)。
#
#  [缺陷3] 任何退出路径(ESC 取消 / 选中退出)都必须清 G_FAMILY,
#          否则下次打开「属下武将」等页会误显示族谱行; 同时要消费掉
#          模态期间产生的点击, 否则主循环的 ft_click 会立刻重开族谱。
# ★v6: 三个跳板从 0x535D60 区搬到洞尾 0x535F80 —— ft_btn_draw 长到 300B 后
#      (0x535C40..0x535D6C) 把原来的 0x535D60 踩了。搬完两者不再相邻,
#      下面每条 assert 都改成"不得越过下一个活地址"。
THUNK_WAIT_VA   = 0x535F80    # A: 模态入口, 等左键释放
THUNK_SELCHK_VA = 0x535FB8    # B: 选中处理前, 族谱模式短路
THUNK_EXIT_VA   = 0x535FD8    # C: 模态所有退出口, 清标志+消费点击
assert (BTN_DRAW_VA - CAVE_VA) + len(btn_draw) <= (THUNK_WAIT_VA - CAVE_VA), \
    'ft_btn_draw 撞修复跳板区 (%d B, 末端 0x%X)' % (len(btn_draw), BTN_DRAW_VA + len(btn_draw))

w = Asm(THUNK_WAIT_VA)
w.b(0x60)                                     # pushad
w.b(0xBF); w.dw(0x400000)                     # mov edi,0x400000  忙等上限(~1.6s)
w.label('wloop')
w.callabs(RESOLVE_VA)                         # eax = GetAsyncKeyState 指针(惰性解析)
w.b(0x85, 0xC0)                               # test eax,eax
w.jr8(0x74, 'wdone')                          # jz wdone
w.b(0x6A, VK_LBUTTON)                         # push VK_LBUTTON
w.b(0xFF, 0xD0)                               # call eax  (stdcall 自清4)
w.b(0xF6, 0xC4, 0x80)                         # test ah,0x80   0x8000 位=当前按下
w.jr8(0x74, 'wdone')                          # jz wdone  已松开
w.b(0x4F)                                     # dec edi
w.jr8(0x75, 'wloop')                          # jnz wloop
w.label('wdone')
w.b(0x61)                                     # popad      还原 esi(=行数)/edi
w.b(0x66, 0x85, 0xF6)                         # test si,si   (原指令)
w.jr8(0x74, 'w51')                            # jz w51  -> 0 行分支
w.jmpabs(0x462D64)                            # 原 jne 0x462D64
w.label('w51')
w.b(0xC7, 0x05); w.dw(G_FAMILY); w.dw(0)      # mov dword[G_FAMILY],0  (0 行也必须清)
w.jmpabs(0x462D51)                            # 原 fall-through
wait_blob = w.resolve()
assert (THUNK_WAIT_VA - CAVE_VA) + len(wait_blob) <= (THUNK_SELCHK_VA - CAVE_VA), 'thunk A 撞 B'

s = Asm(THUNK_SELCHK_VA)
s.b(0x83, 0x3D); s.dw(G_FAMILY); s.b(0x00)    # cmp dword[G_FAMILY],0
s.jr8(0x75, 'fam')                            # jne fam
s.b(0xBF); s.dw(0x7FB)                        # mov edi,0x7fb   (原指令)
s.jmpabs(0x462D98)                            # 回原流程(普通列表, 选中可切武将)
s.label('fam')
s.jmpabs(0x462E03)                            # 族谱只读: 直接走函数退出
selchk_blob = s.resolve()
assert (THUNK_SELCHK_VA - CAVE_VA) + len(selchk_blob) <= (THUNK_EXIT_VA - CAVE_VA), 'thunk B 撞 C'

x = Asm(THUNK_EXIT_VA)
x.b(0xA1); x.dw(G_LBDOWN)                     # mov eax,[G_LBDOWN]
x.b(0xA3); x.dw(G_LBSEEN)                     # mov [G_LBSEEN],eax   消费模态内点击
x.b(0xC7, 0x05); x.dw(G_LBPREV); x.dw(1)      # mov dword[G_LBPREV],1 挡住仍在按下的边沿
x.b(0xC7, 0x05); x.dw(G_FAMILY); x.dw(0)      # mov dword[G_FAMILY],0
x.b(0x5F, 0x5E)                               # pop edi / pop esi     (原 0x462E03)
x.b(0x83, 0xC4, 0x14)                         # add esp,0x14
x.b(0xC3)                                     # ret
exit_blob = x.resolve()
assert (THUNK_EXIT_VA - CAVE_VA) + len(exit_blob) <= 0x1000, 'thunk C 溢出代码洞(洞尾 0x536000)'

# ---------- 写洞 ----------
CAVE_SIZE = 0x1000
cave = bytearray(CAVE_SIZE)
def put(va, data):
    o = va - CAVE_VA
    assert 0 <= o and o + len(data) <= CAVE_SIZE, '洞越界: %06X' % va
    cave[o:o + len(data)] = data
def putstr(va, text):
    put(va, text.encode('gbk') + b'\x00')

put(CAVE_VA, e)
put(builder_va, body)
put(KBD_VA, kbd)
put(STR_U32, b'user32\x00')
put(STR_GAKS, b'GetAsyncKeyState\x00')
put(NAV_VA, nav)
put(RESOLVE_VA, resolve)
for _site, _tva, _blob in latches:
    put(_tva, _blob)
put(CLICK_VA, click)
put(BTN_DRAW_VA, btn_draw)
put(FT_PAINT_VA, paint)
put(VASSAL_THUNK_VA, thunk)
put(THUNK_WAIT_VA, wait_blob)
put(THUNK_SELCHK_VA, selchk_blob)
put(THUNK_EXIT_VA, exit_blob)
putstr(STR_FMT3, '%s %s %s')
putstr(R_SELF,   '本人')
putstr(R_CHILD,  '子女')
putstr(R_FATHER, '父亲')
putstr(R35,      '养子')
putstr(R38,      '甥')
putstr(R42,      '姻戚')
putstr(STR_BTN,  '家族族谱')
for _va, _orig, _nm, _tva, _blob in tramps:
    put(_tva, _blob)
# ★v4: 多家族族谱数据表 (FAM_DIR + FAM_ROWS 留洞内; 串池搬到 .fdata)
put(FAM_DIR_VA, bytes(_dir))
put(FAM_ROWS, bytes(_tbl))
# 串池: 写入 .fdata 节 (_sec_blob), 偏移 = VA - 0x536000
for _t, _va in _STR.items():
    _so = _va - 0x536000
    _sb = _t.encode('gbk') + b'\x00'
    assert _so + len(_sb) <= len(_sec_blob), 'FAM 串池越界 .fdata: 0x%X' % _so
    _sec_blob[_so:_so + len(_sb)] = _sb
assert FAM_DIR_VA + len(_dir) <= FAM_ROWS, 'FAM_DIR 越界 ROWS'
assert _S_END <= FAM_LIMIT, '族谱串池溢出: 0x%06X > 0x%06X' % (_S_END, FAM_LIMIT)

for chk_va, chk_sz in ((G_GS, 5), (G_FAMILY, 4), (G_BTN_CX, 0x38), (G_LBDOWN, 0x10), (0x535F10, 0x70)):
    assert bytes(cave[chk_va - CAVE_VA:chk_va - CAVE_VA + chk_sz]) == b'\0' * chk_sz, 'globals 区非零 %06X' % chk_va
fo = off_of(CAVE_RVA)
b = bytearray(open(SRC, 'rb').read())
assert b[fo:fo + CAVE_SIZE] == bytes(CAVE_SIZE), '洞区非全零(已被占用): off=%X' % fo
b[fo:fo + CAVE_SIZE] = cave
print('OK  洞 @RVA %06X entry=%06X builder=%06X kbd=%06X nav=%06X click=%06X btndraw=%06X (%dB)'
      % (CAVE_RVA, CAVE_VA, builder_va, KBD_VA, NAV_VA, CLICK_VA, BTN_DRAW_VA, len(btn_draw)))
print('OK  按钮文字 面板局部(%d,%d) %dx%d  "家族族谱"  命中框 逻辑(%d,%d) %dx%d' % (BTN_X, BTN_Y, BTN_W, BTN_H, ORIGIN_LX+BTN_X-HIT_PAD, ORIGIN_LY+BTN_Y-HIT_PAD, HIT_W, HIT_H))

# ---------- ★v6: 全库共用的「等一个事件」泵 0x4eefa0 挂通用探测 ----------
# 这是本次修复的核心: 所有卡片模态循环(0x46E31F / 0x4989E3 / 0x4BA0DD / …)
# 都要经过它, 所以不管从哪个界面进入角色详情, 点击判定都会被跑到。
_uo = off_of(UNIV_SITE - 0x400000)
_ucur = bytes(b[_uo:_uo + 5])
assert _ucur == b'\x53\x56\x57\x8b\xf1', '0x%06X 入口字节不符: %s' % (UNIV_SITE, _ucur.hex(' '))
b[_uo:_uo + 5] = b'\xe9' + struct.pack('<i', UNIV_THUNK_VA - (UNIV_SITE + 5))
print('OK  通用探测泵 0x%06X 入口 -> univ_thunk(0x%X)   [覆盖全部模态循环]'
      % (UNIV_SITE, UNIV_THUNK_VA))

_uo2 = off_of(UNIV2_SITE - 0x400000)
_ucur2 = bytes(b[_uo2:_uo2 + 7])
assert _ucur2 == b'\x83\xec\x10\x8d\x44\x24\x00', '0x%06X 入口字节不符: %s' % (UNIV2_SITE, _ucur2.hex(' '))
b[_uo2:_uo2 + 7] = b'\xe9' + struct.pack('<i', UNIV2_THUNK_VA - (UNIV2_SITE + 5)) + b'\x90\x90'
print('OK  通用探测泵 0x%06X 入口 -> univ2_thunk(0x%X)  [补覆盖另一族等待循环]'
      % (UNIV2_SITE, UNIV2_THUNK_VA))

# ---------- capstone 回环校验 ----------
try:
    import capstone
    mdv = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)
    def roundtrip(name, va, blob):
        got = bytearray(); ok = 0
        for ins in mdv.disasm(blob, va):
            got.extend(ins.bytes); ok += 1
        assert bytes(got) == blob, '%s 解码不匹配: got %d/%d B' % (name, len(got), len(blob))
        print('  OK %s: %d 指令, %d 字节' % (name, ok, len(blob)))
    roundtrip('ft_kbd', KBD_VA, kbd)
    roundtrip('ft_resolve', RESOLVE_VA, resolve)
    for _s_, _t_, _b_ in latches:
        roundtrip('ft_latch@%06X' % _s_, _t_, _b_)
    roundtrip('nav_click', NAV_VA, nav)
    roundtrip('ft_probe', PROBE_VA, _probe)
    roundtrip('univ_thunk', UNIV_THUNK_VA, _univ)
    roundtrip('univ2_thunk', UNIV2_THUNK_VA, _univ2)
    roundtrip('ft_click', CLICK_VA, click)
    roundtrip('ft_btn_draw', BTN_DRAW_VA, btn_draw)
    roundtrip('family_builder', builder_va, body)
    roundtrip('ft_paint', FT_PAINT_VA, paint)
    roundtrip('vassal_thunk', VASSAL_THUNK_VA, thunk)
    roundtrip('fix_wait', THUNK_WAIT_VA, wait_blob)
    roundtrip('fix_selchk', THUNK_SELCHK_VA, selchk_blob)
    roundtrip('fix_exit', THUNK_EXIT_VA, exit_blob)
except ImportError:
    print('  (跳过 capstone 校验: 未安装)')

# ---------- 劫持 idx2 thunk (家族族谱页签, 保留) ----------
chk = off_of(THUNK_CALL - 0x400000)
cur = bytes(b[chk:chk + 5])
assert cur[:1] == b'\xe8', 'thunk 不是 call: %s' % cur.hex(' ')
old_rel, = struct.unpack('<i', cur[1:5])
assert THUNK_RET_ADDR + old_rel == ORIG_TARGET, 'thunk 目标异常 0x%08X' % (THUNK_RET_ADDR + old_rel)
b[chk + 1:chk + 5] = struct.pack('<i', CAVE_VA - THUNK_RET_ADDR)
print('OK  劫持 RVA 0x%06X  家中排行(0x%X) -> family_entry(0x%X)' % (THUNK_CALL, ORIG_TARGET, CAVE_VA))

# ---------- 关系标注: painter ----------
PK_PUSH = 0x462d7f
po = off_of(PK_PUSH - 0x400000)
assert bytes(b[po:po + 5]) == b'\x68\x30\x2a\x46\x00', '0x462d7f 不是 push 0x462a30'
b[po + 1:po + 5] = struct.pack('<I', FT_PAINT_VA)
print('OK  painter RVA 0x%06X push 0x462a30 -> ft_paint(0x%X)' % (PK_PUSH, FT_PAINT_VA))

# ---------- 普通属下一页清 G_FAMILY ----------
VASSAL_CALL = 0x46256e
vo = off_of(VASSAL_CALL - 0x400000)
vcur = bytes(b[vo:vo + 5])
assert vcur[:1] == b'\xe8', '0x46256e 不是 call'
vret = VASSAL_CALL + 5
old_vrel, = struct.unpack('<i', vcur[1:5])
assert vret + old_vrel == 0x462d40, '0x46256e 目标异常'
b[vo + 1:vo + 5] = struct.pack('<i', VASSAL_THUNK_VA - vret)
print('OK  属下一页 RVA 0x%06X -> vassal_thunk(0x%X)' % (VASSAL_CALL, VASSAL_THUNK_VA))

# ---------- ★v5 修复: 族谱模态的输入残留 / 当前对象污染 / 标志残留 ----------
FIX_SITES = (
    (0x462D4C, b'\x66\x85\xf6\x75\x13',     THUNK_WAIT_VA,   'test si,si -> 等左键释放(缺陷1)'),
    (0x462D93, b'\xbf\xfb\x07\x00\x00',     THUNK_SELCHK_VA, 'mov edi,0x7fb -> 族谱模式短路选中(缺陷2)'),
    (0x462E03, b'\x5f\x5e\x83\xc4\x14\xc3', THUNK_EXIT_VA,   'pop edi -> 退出清标志+消费点击(缺陷3)'),
)
for _va, _exp, _tva, _nm in FIX_SITES:
    _o = off_of(_va - 0x400000)
    _cur = bytes(b[_o:_o + len(_exp)])
    assert _cur == _exp, '0x%06X 字节不符: %s (期望 %s)' % (_va, _cur.hex(' '), _exp.hex(' '))
    b[_o:_o + 5] = b'\xe9' + struct.pack('<i', _tva - (_va + 5))
    print('OK  族谱修复 RVA 0x%06X -> 0x%X   [%s]' % (_va, _tva, _nm))

# ---------- 挂钩调查卡循环头 ----------
if _args.no_nav:
    print('-- 自测模式: 跳过 0x%06X 循环头挂钩(只留 ft_probe 通用探测)' % CARD_LOOP_HEAD)
else:
  hk = off_of(CARD_LOOP_HEAD - 0x400000)
  hcur = bytes(b[hk:hk + 5])
  assert hcur == b'\xa1\x30\x06\x52\x00', '小弹窗循环头字节不符: %s' % hcur.hex(' ')
  b[hk:hk + 5] = b'\xe9' + struct.pack('<i', NAV_VA - (CARD_LOOP_HEAD + 5))
  print('OK  调查卡挂钩 RVA 0x%06X jmp -> nav_click(0x%X)' % (CARD_LOOP_HEAD, NAV_VA))

# ---------- 挂钩: 按钮绘制 (0x4754c0 收尾 call 0x403cd0 处, 保证文字在本次刷新前追加) ----------
epo = off_of(PANEL_TAIL - 0x400000)
epcur = bytes(b[epo:epo + 5])
assert epcur == b'\xe8\x66\xe5\xf8\xff', '面板收尾 call 字节不符: %s' % epcur.hex(' ')
b[epo:epo + 5] = b'\xe9' + struct.pack('<i', BTN_DRAW_VA - (PANEL_TAIL + 5))
print('OK  信息卡绘制收尾 RVA 0x%06X call 0x403cd0 -> ft_btn_draw(0x%X)   [画按钮]' % (PANEL_TAIL, BTN_DRAW_VA))

# ---------- 挂钩 WndProc 的 WM_LBUTTONDOWN 分支 (锁存左键按下) ----------
for _site, _tva, _blob in latches:
    _o = off_of(_site - 0x400000)
    _cur = bytes(b[_o:_o + 7])
    assert _cur == b'\x83\x0d\xf0\x9a\x52\x00\x01', '0x%06X 字节不符: %s' % (_site, _cur.hex(' '))
    b[_o:_o + 5] = b'\xe9' + struct.pack('<i', _tva - (_site + 5))
    print('OK  左键按下锁存 RVA 0x%06X -> ft_latch(0x%X)   [WM_LBUTTONDOWN 计数]' % (_site, _tva))

# ---------- 诊断: 给候选绘制函数挂入口计数器 ----------
for _va, _orig, _nm, _tva, _blob in tramps:
    _o = off_of(_va - 0x400000)
    _cur = bytes(b[_o:_o + 5])
    assert _cur == _orig, '0x%06X 入口字节不符: %s (期望 %s)' % (_va, _cur.hex(' '), _orig.hex(' '))
    b[_o:_o + 5] = b'\xe9' + struct.pack('<i', _tva - (_va + 5))
    print('OK  计数挂钩 0x%06X -> tramp(0x%X)  [%s]' % (_va, _tva, _nm))

# ---------- 页签名 家中排行 -> 家族族谱 ----------
LBL_VA = 0x50494A
old_lbl = '家中排行'.encode('gbk'); new_lbl = '家族族谱'.encode('gbk')
lo = off_of(LBL_VA - 0x400000)
assert bytes(b[lo:lo + len(old_lbl)]) == old_lbl, '页签标签字节不符'
assert len(new_lbl) == len(old_lbl)
b[lo:lo + len(new_lbl)] = new_lbl
print('OK  页签名 家中排行 -> 家族族谱 @VA 0x%06X' % LBL_VA)

_pe = struct.unpack_from('<I', b, 0x3c)[0]
_ns = struct.unpack_from('<H', b, _pe + 6)[0]
_oh = struct.unpack_from('<H', b, _pe + 20)[0]
_sh = _pe + 24 + _oh + _ns * 40
assert _ns == 4 and _sh == 0x248, '节表位置异常 nsec=%d sh=0x%X' % (_ns, _sh)
assert len(b) == SEC_PTR, '原文件末尾 0x%X != 新节 raw 0x%X' % (len(b), SEC_PTR)
# 注意: 节头的 VirtualAddress / SizeOfImage 都是 **RVA**, 这里必须用 SEC_RVA(0x136000)。
# 汇编里引用的绝对地址才用 SEC_VA(0x536000)。
struct.pack_into('<8sIIIIIIHHI', b, _sh,
                 b'.fdata\x00\x00', SEC_SZ, SEC_RVA, SEC_SZ, SEC_PTR,
                 0, 0, 0, 0, 0xE0000040)          # X|R|W|INITIALIZED_DATA
struct.pack_into('<H', b, _pe + 6, _ns + 1)      # NumberOfSections
struct.pack_into('<I', b, _pe + 24 + 56, SEC_RVA + SEC_SZ)   # SizeOfImage (=0x139000)
b.extend(_sec_blob)
print('OK  新增节 .fdata  RVA 0x%06X -> VA 0x%06X   file 0x%X  %dB  SizeOfImage -> 0x%06X'
      % (SEC_RVA, SEC_VA, SEC_PTR, SEC_SZ, SEC_RVA + SEC_SZ))

try:
    open(DST, 'wb').write(bytes(b))
    out = DST
except PermissionError:
    out = DST[:-4] + 'b.exe'
    open(out, 'wb').write(bytes(b))
    print('!! 警告: %s 被占用(游戏在跑?), 本次写到了 %s —— 关游戏后需重跑构建' % (DST, out))
print('\n已生成:', out, len(b), '字节')
