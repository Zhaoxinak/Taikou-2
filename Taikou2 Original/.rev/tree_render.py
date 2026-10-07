"""tree_render.py — 「树形家族树」的 GDI 自绘渲染层(手写 x86, 字节级)

被 build_fam_btn2.py import; 生成的机器码写入新节 .fdata 的 O_CODE 起。

整体结构(每段自带 ret, 便于单独反汇编校验)
    log_init      建崩溃诊断日志(进程死了日志仍在盘上)
    resolve_api   惰性解析 26 个 API 地址 -> GDI_TAB
    make_res      建刷/笔/字体 + 取 NULL_BRUSH / NULL_PEN
    free_res      退出时 DeleteObject 掉上述对象
    wait_rel      进入模态前等左键松开(否则"打开"的那次点击会立刻被当成"关闭")
    clamp         平移量钳制(内容比视口大就卡边, 小就居中)
    pump          排空消息 + ESC/单击关闭 + 方向键平移 + 鼠标拖拽 + Sleep
    draw_frame    面板底 + 边框 + 标题 + 底部提示 + 设视口裁剪
    draw_edges    父子折线(先画, 让头像框盖住接缝)
    draw_nodes    头像框(状态配色 + 头肩剪影 + 本人高亮) + 姓名 + 关系
    tree_show     模态循环: frame -> edges -> nodes -> pump
    tree_entry    入口: 由当前信息卡武将的 (名,姓) 在 FAM_DIR 里查家族 -> tree_show

坐标系: 物理像素。面板 700x520 居中于客户区, 树画在**内容坐标系**里,
        运行时统一加 PANX/PANY 得到屏幕坐标 —— 平移只是两个加数,
        画点代码不必知道视口在哪。

★ 五个用血换来的坑:
  1) TextOutA 的 cchString 传 -1(让系统自己找 NUL)在本机返回 0,
     GetLastError=87(ERROR_INVALID_PARAMETER) —— 一个字都不画, 不报错不崩溃。
     必须传**显式字符数**, 所以串池里每个串都带 u8 长度前缀。
  2) GetDC / ReleaseDC / GetAsyncKeyState 导出在 **user32** 而不是 gdi32/kernel32。
  3) 所有超过 imm8 正数上限(127)的立即数必须 push imm32, 否则符号扩展出负数。
  4) 立即数算术必须按范围选宽度(见 _addi): `add eax, 699` 若走 83 /0 ib 会被
     截成 -69, 面板矩形算成 left>right 的倒置矩形 —— 整棵树静默不画。
  5) 节点文字的 x 必须取节点自己的 CX; 取面板中心会把同一代所有姓名叠在一起。

关闭方式: ESC / 单击(未拖拽时)。
平移方式: ← → ↑ ↓ 方向键, 或按住左键拖拽。
"""
import struct

# ---------- 几何(与 tree_data.py 必须一致) ----------
AV_HX, AV_HY = 13, 15    # 头像框半宽/半高(与 tree_data.AV_W/AV_H 同步)
NODE_SZ = 10             # NODE_TAB 单条字节数
DIR_SZ = 24              # FAM_DIR 单条字节数
# ★v12 动态族谱: FAM_DIR+8 存的是 **start/2**(族块长被 tree_data 凑偶保证), 所以任何
#   "起始节点指针 = start*NODE_SZ + NODES_VA" 的地方都要乘 2*NODE_SZ(=20)。
#   count(+9) 由 build_big 的动态点亮桩在开树时从 static_n(+21) 抬到 static_n+点亮数,
#   渲染层照旧读 count —— 它不知道也不关心哪些是动态槽。
START_MUL = 2 * NODE_SZ  # 乘 start(+8) 得到族基址的系数

OFS_NAME = AV_HY + 7     # 姓名基线相对 cy (与 tree_data.OFS_NAME 同步)
OFS_REL = OFS_NAME + 12  # 关系基线相对 cy
REL_H = 12               # 关系字号(必须与 make_res 里 FTRL 的字高一致, 与 tree_data.REL_H 同步)

CHARSET_GB = 134         # GB2312_CHARSET

# 面板几何
# 原 700x520 在部分逻辑分辨率(如 640x480 缩放)下右侧/底边被裁;
# 改小到 640x460, 仍给树内容留足够空间, 且能在较小窗口居中显示。
PW, PH = 640, 460
TITLE_H, HINT_H = 32, 26
INSET = 4                # 视口相对面板的内缩
TITLE_OFS = 10           # 标题基线相对面板上沿
HINT_OFS = 19            # 提示基线相对面板下沿
INNER = 6                # 内衬线内缩
STEP = 14                # 方向键每帧平移像素

# 点选详情框(浮在面板底部, 覆盖提示带并上探一点进视口): 两行 + 金边
DET_H, DET_PAD, DET_LINEH = 44, 8, 16

# 父子折线的两个纵向锚点(都是相对量, 见 draw_edges 注释)
EDGE_TOP = OFS_REL + REL_H + 6   # 竖线起点: 父节点标签下方(留 6px 间隙)
EDGE_BAR = AV_HY + 10            # 横杠: 子节点框顶再往上 10px

TA_CENTER_TOP = 6        # TA_CENTER|TA_TOP
NULL_BRUSH, NULL_PEN = 5, 8

HEAD = (-6, -12, 6, 0)   # 头部椭圆 l,t,r,b (相对框中心) — 12px 圆
BODY = (-11, 2, 11, 14)  # 肩部椭圆(半身剪影), 必须留在框内(框 ±13/±15)


# ======================================================================
class Asm:
    """两段式汇编器: 先收集 rel8/rel32 待定项, resolve 时回填"""

    def __init__(self, va):
        self.va = va
        self.code = bytearray()
        self.labels = {}
        self.f8 = []
        self.f32 = []

    def pos(self):
        return self.va + len(self.code)

    def label(self, n):
        assert n not in self.labels, '标签重复: %s' % n
        self.labels[n] = self.pos()

    def b(self, *xs):
        self.code.extend(bytes(xs))

    def dw(self, v):
        self.code.extend(struct.pack('<I', v & 0xFFFFFFFF))

    def jr8(self, op, name):
        self.code.append(op)
        self.code.append(0)
        self.f8.append((len(self.code) - 1, name))

    def jr32(self, op, name):
        """0F op rel32 近跳转 —— op 必须是 Jcc(0x80..0x8F)。

        无条件跳转没有 0F 形式; 去远处请用 jmpabs()。
        曾写成 jr32(0xE9,...) 结果发出 "0F E9 rel32" —— x86 里 0F E9 不是跳转,
        CPU 解成 MMX 指令 psubsw mm1,[ebx], 直接访问非法地址崩溃。
        """
        assert 0x80 <= op <= 0x8F, 'jr32 只接受 Jcc 操作码, 收到 0x%02X' % op
        self.code.append(0x0F)
        self.code.append(op)
        self.code.extend(b'\0\0\0\0')
        self.f32.append((len(self.code) - 4, name))

    def callabs(self, va):
        self.code.append(0xE8)
        self.code.extend(b'\0\0\0\0')
        self.f32.append((len(self.code) - 4, va))

    def jmpabs(self, va):
        self.code.append(0xE9)
        self.code.extend(b'\0\0\0\0')
        self.f32.append((len(self.code) - 4, va))

    def resolve(self):
        for off, name in self.f8:
            rel = self.labels[name] - (self.va + off + 1)
            assert -128 <= rel <= 127, \
                'rel8 越界 %s %d (段起始 VA 0x%06X) —— 改用 jr32/jmpabs' % (name, rel, self.va)
            self.code[off] = rel & 0xFF
        for off, tgt in self.f32:
            tgt = self.labels[tgt] if isinstance(tgt, str) else tgt
            self.code[off:off + 4] = struct.pack('<i', tgt - (self.va + off + 4))
        return bytes(self.code)


# ---------- 常用指令小工具 ----------
def _ld(a, va):
    a.b(0xA1); a.dw(va)                                   # mov eax,[va]


def _ldc(a, va):
    a.b(0x8B, 0x0D); a.dw(va)                             # mov ecx,[va]


def _ldd(a, va):
    a.b(0x8B, 0x15); a.dw(va)                             # mov edx,[va]


def _st(a, va):
    a.b(0xA3); a.dw(va)                                   # mov [va],eax


def _stc(a, va):
    a.b(0x89, 0x0D); a.dw(va)                             # mov [va],ecx


def _std(a, va):
    a.b(0x89, 0x15); a.dw(va)                             # mov [va],edx


def _set(a, va, v):
    a.b(0xC7, 0x05); a.dw(va); a.dw(v)                    # mov dword[va],v


def _p32(a, v):
    a.b(0x68); a.dw(v)                                    # push imm32


def _p8(a, v):
    a.b(0x6A, v & 0xFF)                                   # push imm8


def _addi(a, d):
    """add eax, d —— 按范围自动选宽度。

    ★ 血的教训: 曾经写成无条件 `83 /0 ib`, 于是
        `add eax, -700` 被截成 `add eax, +68`(0x44)
        `add eax,  699` 被截成 `add eax, -69`(0xBB)
      结果面板右边界 = 左边界 - 69, 得到一个 left>right 的**倒置矩形**,
      Rectangle 什么都不画, 而且由它推出来的视口裁剪区也是空的
      —— 整棵家族树一个像素都没上屏, 却全程不报错、不崩溃。
    """
    d = int(d)
    if d == 0:
        return
    if -128 <= d <= 127:
        if d > 0:
            a.b(0x83, 0xC0, d & 0xFF)                     # add eax, imm8
        else:
            a.b(0x83, 0xE8, (-d) & 0xFF)                  # sub eax, imm8
    else:
        if d > 0:
            a.b(0x05); a.dw(d & 0xFFFFFFFF)               # add eax, imm32
        else:
            a.b(0x2D); a.dw((-d) & 0xFFFFFFFF)            # sub eax, imm32


def _add8(a, d):
    """严格的 imm8 版本 —— 只允许 ±127, 超了直接炸, 不给静默截断的机会。"""
    assert -128 <= d <= 127, \
        'imm8 装不下 %d (段 VA 0x%06X) —— 请改用 _addi()' % (d, a.pos())
    _addi(a, d)


# ======================================================================
def build(ctx):
    """ctx 需要的键:
        CODE_VA, RSTATE_VA, GDI_TAB_VA, GDIOK_VA, MODS_VA, MODTAB_VA, OFFTAB_VA,
        NAM_VA, NODES_VA, POOL_VA, MSGBUF_VA, RC_VA, PT_VA, FAMDIR_VA,
        OIDTAB_VA, DYN_FN_VA, DYN_SLOT_VA, GENERIC_DIR_VA,
        STR_FONT_VA, STR_HINT_VA, STR_LOG_VA, HINT_LEN, LOGBUF_VA,
        DLLS, IAT_GETMOD, IAT_GETPROC, CARD_CUR, N_API, NDIR,
        LBDOWN_VA, LBSEEN_VA, LBPREV_VA, FAMILY_VA, FALLBACK_VA,
        RS, T, A, C
       -> (blobs, entry_va)  blobs: [(name, bytes)]
    """
    RS = ctx['RS']
    T = ctx['T']
    A = ctx['A']
    C = ctx['C']
    RV = ctx['RSTATE_VA']
    NODES_VA = ctx['NODES_VA']
    POOL_VA = ctx['POOL_VA']
    DETAILTAB_VA = ctx['DETAILTAB_VA']

    cur = [ctx['CODE_VA']]

    def new():
        return Asm(cur[0])

    def commit(a):
        bl = a.resolve()
        cur[0] += len(bl)
        return bl

    blobs = []

    # ---------- 寻址小工具 ----------
    def ld(a, off):
        _ld(a, RV + off)

    def ldc(a, off):
        _ldc(a, RV + off)

    def st(a, off):
        _st(a, RV + off)

    def stc(a, off):
        _stc(a, RV + off)

    def std(a, off):
        _std(a, RV + off)

    def push_r(a, off, delta=0):
        """push dword[RSTATE+off] (+delta)"""
        ld(a, off)
        if delta:
            _add8(a, delta)
        a.b(0x50)

    def push_hdc(a):
        push_r(a, RS['HDC'])

    def sel(a, off):
        """SelectObject(hdc, [RSTATE+off])"""
        push_r(a, off); push_hdc(a)
        a.b(0xFF, 0x15); a.dw(T(A['SELOBJ']))

    def setcolor(a, col):
        _p32(a, col); push_hdc(a)
        a.b(0xFF, 0x15); a.dw(T(A['SETTC']))

    def align_center(a):
        _p8(a, TA_CENTER_TOP); push_hdc(a)
        a.b(0xFF, 0x15); a.dw(T(A['SETA']))

    def cx_center(a):
        """push (WX0+WX1)/2"""
        ld(a, RS['WX0']); ldc(a, RS['WX1'])
        a.b(0x03, 0xC1); a.b(0xD1, 0xF8)
        a.b(0x50)

    def pool_str(a, disp):
        """按 [ebx+disp] 取长度前缀串, 压入 cchString 与 lpString"""
        a.b(0x0F, 0xB7, 0x4B, disp)                       # movzx ecx,word[ebx+disp]
        a.b(0x0F, 0xB6, 0x91); a.dw(POOL_VA)              # movzx edx,byte[ecx+POOL]
        a.b(0x83, 0xC1, 1)                                # inc ecx
        a.b(0x52)                                         # push cchString
        a.b(0x89, 0xCA)                                   # mov edx,ecx
        a.b(0x81, 0xC2); a.dw(POOL_VA)                    # add edx,POOL
        a.b(0x52)                                         # push lpString

    def textout(a, y_off, y_delta):
        """面板居中文本: 尾参 y / x=(WX0+WX1)/2 / hdc, 然后 call TextOutA"""
        push_r(a, y_off, y_delta)
        cx_center(a)
        push_hdc(a)
        a.b(0xFF, 0x15); a.dw(T(A['TEXTOUT']))

    def textout_node(a, y_off, y_delta):
        """节点文本: 尾参 y / x=[CX](该节点自己的中心) / hdc

        ★ 曾经复用面板版 textout, x 取的是 (WX0+WX1)/2 —— 于是同一代里
          所有节点的姓名都叠在面板正中, 多列行看起来像只有一行标签。
        """
        push_r(a, y_off, y_delta)
        push_r(a, RS['CX'])
        push_hdc(a)
        a.b(0xFF, 0x15); a.dw(T(A['TEXTOUT']))

    # ---------- 日志(崩溃现场) ----------
    LOGB = ctx['LOGBUF_VA']
    LOGW = RV + RS['LOGW']
    LOGH = RV + RS['LOGH']
    _lbn = [0]

    def logb(a, n):
        """把 1 字节阶段标记写进 tk_tree.log。

        为什么不用内存变量: 游戏一崩进程就没了, 内存里的诊断值全丢。
        WriteFile 写完数据就在系统缓存里, 进程死后文件仍在, 最后那个字节
        就是崩溃点 —— 这是唯一能拿到「死后现场」的手段。
        ★ 必须带 NULL 守卫: GDI_TAB 是惰性解析的, 在 resolve_api 跑完之前
          里面全是 0, `call dword[TAB+n]` == `call 0` -> EIP 跳到 0, 当场死亡。
        """
        _lbn[0] += 1
        lz = 'lz%d' % _lbn[0]
        _ld(a, T(A['WFILE']))
        a.b(0x85, 0xC0); a.jr8(0x74, lz)                  # 未解析 -> 静默跳过
        a.b(0xC6, 0x05); a.dw(LOGB); a.b(n & 0xFF)        # mov byte[LOGB],n
        _p32(a, 0)                                        # lpOverlapped
        _p32(a, LOGW)                                     # lpNumberOfBytesWritten
        _p8(a, 1)                                         # nNumberOfBytesToWrite
        _p32(a, LOGB)                                     # lpBuffer
        # hFile 必须从内存取: 此刻 eax 装的是 WriteFile 的函数地址
        a.b(0xFF, 0x35); a.dw(LOGH)                       # push dword[LOGH]
        a.b(0xFF, 0x15); a.dw(T(A['WFILE']))
        a.label(lz)

    def stage(a, n):
        _set(a, RV + RS['STAGE'], n)
        logb(a, n)

    # ==================================================================
    # 0) log_init
    # ==================================================================
    log_va = cur[0]
    a = new()
    a.b(0x60)
    _ld(a, T(A['CFILE']))
    a.b(0x85, 0xC0); a.jr8(0x74, 'lok')                   # 未解析 -> 放弃(否则 call 0 必崩)
    _ld(a, LOGH)
    a.b(0x85, 0xC0); a.jr8(0x75, 'lok')                   # 已打开 -> 跳过
    _p32(a, 0)                                            # hTemplateFile
    _p32(a, 0x80)                                         # FILE_ATTRIBUTE_NORMAL(必须 imm32!)
    _p8(a, 2)                                             # CREATE_ALWAYS
    _p8(a, 0)                                             # lpSecurityAttributes
    _p8(a, 1)                                             # FILE_SHARE_READ
    _p32(a, 0x40000000)                                   # GENERIC_WRITE
    _p32(a, ctx['STR_LOG_VA'])
    a.b(0xFF, 0x15); a.dw(T(A['CFILE']))
    _st(a, LOGH)
    a.label('lok')
    a.b(0x61); a.b(0xC3)
    blobs.append(('log_init', commit(a)))

    # ==================================================================
    # 1) resolve_api
    # ==================================================================
    resolve_va = cur[0]
    a = new()
    _ld(a, ctx['GDIOK_VA']); a.b(0x85, 0xC0); a.jr32(0x85, 'done')
    a.b(0x60)
    logb(a, 0x20)
    for i in range(3):
        _p32(a, ctx['DLLS'][i])
        a.b(0xFF, 0x15); a.dw(ctx['IAT_GETMOD'])
        _st(a, ctx['MODS_VA'] + i * 4)
    a.b(0x31, 0xDB)                                       # xor ebx,ebx
    a.label('loop')
    a.b(0x0F, 0xB6, 0x83); a.dw(ctx['MODTAB_VA'])         # movzx eax,byte[MODTAB+ebx]
    a.b(0x8B, 0x3C, 0x85); a.dw(ctx['MODS_VA'])           # mov edi,[eax*4+MODS]
    a.b(0x0F, 0xB7, 0x04, 0x5D); a.dw(ctx['OFFTAB_VA'])   # movzx eax,word[ebx*2+OFFTAB]
    a.b(0x05); a.dw(ctx['NAM_VA'])                        # add eax,NAM
    a.b(0x50); a.b(0x57)                                  # push lpProcName; push hModule
    a.b(0xFF, 0x15); a.dw(ctx['IAT_GETPROC'])
    a.b(0x85, 0xC0); a.jr8(0x74, 'nx')
    a.b(0x89, 0x04, 0x9D); a.dw(ctx['GDI_TAB_VA'])        # mov [ebx*4+TAB],eax
    a.label('nx')
    a.b(0x43)                                             # inc ebx
    a.b(0x83, 0xFB, ctx['N_API']); a.jr8(0x72, 'loop')
    _set(a, ctx['GDIOK_VA'], 1)
    logb(a, 0x2F)
    a.b(0x61)
    a.label('done')
    a.b(0xC3)
    blobs.append(('resolve_api', commit(a)))

    # ==================================================================
    # 2) make_res
    # ==================================================================
    make_va = cur[0]
    a = new()
    a.b(0x60)
    logb(a, 0x30)

    def stock(dst, oid):
        _p8(a, oid)
        a.b(0xFF, 0x15); a.dw(T(A['GETSTK']))
        st(a, dst)

    stock(RS['NB'], NULL_BRUSH)
    stock(RS['NP'], NULL_PEN)

    def brush(dst, color):
        _p32(a, color); a.b(0xFF, 0x15); a.dw(T(A['CBRUSH']))
        st(a, dst)

    def pen(dst, style, width, color):
        _p32(a, color); _p8(a, width); _p8(a, style)
        a.b(0xFF, 0x15); a.dw(T(A['CPEN']))
        st(a, dst)

    def font(dst, h, weight):
        # 所有数值参数一律 push imm32: CHARSET_GB=134 / weight=700 都超过 imm8 正数上限,
        # push imm8 会符号扩展 -> iCharSet 变成 -122 / 字重变成 188。
        _p32(a, ctx['STR_FONT_VA'])
        _p32(a, 0); _p32(a, 0); _p32(a, 0); _p32(a, 0)    # pitch/quality/clip/outprec
        _p32(a, CHARSET_GB)
        _p32(a, 0); _p32(a, 0); _p32(a, 0)                # strike/underline/italic
        _p32(a, weight)
        _p32(a, 0); _p32(a, 0); _p32(a, 0)                # orientation/escapement/width
        _p32(a, (-h) & 0xFFFFFFFF)                        # cHeight(负 = 字符高度)
        a.b(0xFF, 0x15); a.dw(T(A['CFONT']))
        st(a, dst)

    brush(RS['BRBG'], C['BG'])
    brush(RS['BRN0'], C['FILL0'])
    brush(RS['BRN1'], C['FILL1'])
    brush(RS['BRN2'], C['FILL2'])
    brush(RS['BRSH'], C['SILH'])
    pen(RS['PENLN'], 0, 1, C['LINE'])
    pen(RS['PENF0'], 0, 1, C['EDGE0'])
    pen(RS['PENF1'], 0, 1, C['EDGE1'])
    pen(RS['PENF2'], 0, 1, C['EDGE2'])
    pen(RS['PENAC'], 0, 2, C['ACCENT'])
    pen(RS['PENIN'], 0, 1, C['INNER'])
    pen(RS['PENFR'], 0, 2, C['FRAME'])
    font(RS['FTTI'], 22, 700)
    font(RS['FTNM'], 13, 600)
    font(RS['FTRL'], REL_H, 400)
    logb(a, 0x3F)
    a.b(0x61); a.b(0xC3)
    blobs.append(('make_res', commit(a)))

    # ==================================================================
    # 3) free_res
    # ==================================================================
    free_va = cur[0]
    a = new()
    a.b(0x60)
    logb(a, 0x40)
    for i, key in enumerate(('BRBG', 'BRN0', 'BRN1', 'BRN2', 'BRSH',
                             'PENLN', 'PENF0', 'PENF1', 'PENF2', 'PENAC',
                             'PENIN', 'PENFR', 'FTTI', 'FTNM', 'FTRL')):
        ld(a, RS[key])
        a.b(0x85, 0xC0); a.jr8(0x74, 'k%d' % i)
        a.b(0x50); a.b(0xFF, 0x15); a.dw(T(A['DELOBJ']))
        a.label('k%d' % i)
    logb(a, 0x4F)
    a.b(0x61); a.b(0xC3)
    blobs.append(('free_res', commit(a)))

    # ==================================================================
    # 4) wait_rel
    # ==================================================================
    wait_va = cur[0]
    a = new()
    a.b(0x60)
    logb(a, 0x50)
    a.b(0xBF); a.dw(300)                                  # edi = 300 × 5ms ≈ 1.5s
    a.label('wl')
    _p8(a, 0x01)
    a.b(0xFF, 0x15); a.dw(T(A['GAKS']))
    a.b(0x0F, 0xB7, 0xC0); a.b(0x25); a.dw(0x8000)
    a.jr8(0x74, 'wd')
    _p8(a, 5); a.b(0xFF, 0x15); a.dw(T(A['SLEEP']))
    a.b(0x4F); a.jr8(0x75, 'wl')
    a.label('wd')
    logb(a, 0x5F)
    a.b(0x61); a.b(0xC3)
    blobs.append(('wait_rel', commit(a)))

    # ==================================================================
    # 5) clamp —— 平移量钳制
    #    内容比视口大: 卡住边 ; 内容比视口小: 居中
    #    化简: 若 C0+PAN > V0 则 PAN = V0-C0 ; 若 C1+PAN < V1 则 PAN = V1-C1
    #    (content>=view 时两个条件互斥, 所以顺序无所谓)
    # ==================================================================
    def clamp_axis(a, pan_off, c0_disp, c1_disp, v0_off, v1_off, tag):
        pv, v0, v1 = RV + pan_off, RV + v0_off, RV + v1_off
        # esi = 视口宽/高 ; edi = 内容宽/高
        _ld(a, v1); _ldc(a, v0)
        a.b(0x29, 0xC8)                                   # sub eax,ecx
        a.b(0x89, 0xC6)                                   # mov esi,eax
        a.b(0x0F, 0xBF, 0x4B, c0_disp)                    # movsx ecx,word[ebx+C0]
        a.b(0x0F, 0xBF, 0x43, c1_disp)                    # movsx eax,word[ebx+C1]
        a.b(0x29, 0xC8)
        a.b(0x89, 0xC7)                                   # mov edi,eax
        a.b(0x39, 0xF7)                                   # cmp edi,esi
        a.jr32(0x83, tag + 'big')                         # jae big
        # --- 内容比视口小: 居中 ---
        _ld(a, v0)
        a.b(0x0F, 0xBF, 0x4B, c0_disp)
        a.b(0x29, 0xC8)                                   # eax = V0 - C0
        a.b(0x89, 0xF1)                                   # mov ecx,esi
        a.b(0x29, 0xF9)                                   # sub ecx,edi
        a.b(0xD1, 0xE9)                                   # shr ecx,1
        a.b(0x01, 0xC8)                                   # add eax,ecx
        _st(a, pv)
        a.jmpabs(tag + 'done')
        a.label(tag + 'big')
        _ld(a, pv)
        a.b(0x0F, 0xBF, 0x4B, c0_disp)
        a.b(0x01, 0xC1)                                   # ecx = C0 + pan
        a.b(0x3B, 0x0D); a.dw(v0)
        a.jr32(0x8E, tag + 'c2')                          # jle c2
        _ld(a, v0)
        a.b(0x0F, 0xBF, 0x4B, c0_disp)
        a.b(0x29, 0xC8)
        _st(a, pv)
        a.label(tag + 'c2')
        _ld(a, pv)
        a.b(0x0F, 0xBF, 0x4B, c1_disp)
        a.b(0x01, 0xC1)
        a.b(0x3B, 0x0D); a.dw(v1)
        a.jr32(0x8D, tag + 'done')                        # jge done
        _ld(a, v1)
        a.b(0x0F, 0xBF, 0x4B, c1_disp)
        a.b(0x29, 0xC8)
        _st(a, pv)
        a.label(tag + 'done')

    clamp_va = cur[0]
    a = new()
    a.b(0x60)
    a.b(0x8B, 0x1D); a.dw(RV + RS['FAMP'])                # mov ebx,[FAMP]
    a.b(0x85, 0xDB); a.jr32(0x84, 'cout')                 # 没有家族 -> 不求值
    # bbox 在 FAM_DIR +12..+18 (i16), 顺序 cx0,cy0,cx1,cy1
    clamp_axis(a, RS['PANX'], 12, 16, RS['VX0'], RS['VX1'], 'cx')
    clamp_axis(a, RS['PANY'], 14, 18, RS['VY0'], RS['VY1'], 'cy')
    a.label('cout')
    a.b(0x61); a.b(0xC3)
    blobs.append(('clamp', commit(a)))

    # ==================================================================
    # 6) pump
    # ==================================================================
    pump_va = cur[0]
    a = new()
    a.b(0x60)
    logb(a, 0x60)
    # --- 复位 DC 裁剪区(游戏自己也用这个 DC, 不能把裁剪留给它) ---
    ld(a, RS['HDC'])
    a.b(0x85, 0xC0); a.jr8(0x74, 'noclip')
    _p8(a, 0); push_hdc(a)
    a.b(0xFF, 0x15); a.dw(T(A['SCLIP']))
    a.label('noclip')
    # --- 排空消息队列 ---
    a.label('pl')
    _p8(a, 0x01)                                          # PM_REMOVE
    _p8(a, 0x00); _p8(a, 0x00)                            # filter min/max
    _p8(a, 0x00)                                          # hwnd = 0
    _p32(a, ctx['MSGBUF_VA'])
    a.b(0xFF, 0x15); a.dw(T(A['PEEK']))
    a.b(0x85, 0xC0); a.jr8(0x74, 'pdone')
    _ld(a, ctx['MSGBUF_VA'] + 4)                          # msg.message
    a.b(0x3D); a.dw(0x0012)                               # WM_QUIT
    a.jr32(0x84, 'quit')
    a.b(0x3D); a.dw(0x0100)                               # WM_KEYDOWN
    a.jr8(0x75, 'pl')
    _ld(a, ctx['MSGBUF_VA'] + 8)                          # msg.wParam
    a.b(0x3D); a.dw(0x1B)                                 # VK_ESCAPE
    a.jr8(0x75, 'pl')
    a.jmpabs('quit')
    # --- ESC 轮询(消息被游戏吃掉时的兜底) ---
    a.label('pdone')
    _p8(a, 0x1B)
    a.b(0xFF, 0x15); a.dw(T(A['GAKS']))
    a.b(0x0F, 0xB7, 0xC0); a.b(0x25); a.dw(0x8000)
    a.jr32(0x85, 'quit')

    # --- 方向键平移 ---
    def arrow(vk, off, d, tag):
        _p8(a, vk)
        a.b(0xFF, 0x15); a.dw(T(A['GAKS']))
        a.b(0x0F, 0xB7, 0xC0)                             # movzx eax,ax
        a.b(0x25); a.dw(0x8000)                           # and eax,0x8000(同时置 ZF)
        a.jr8(0x74, tag)
        ld(a, off); _add8(a, d); st(a, off)
        a.label(tag)
    arrow(0x25, RS['PANX'], -STEP, 'kL')                  # VK_LEFT
    arrow(0x27, RS['PANX'], +STEP, 'kR')                  # VK_RIGHT
    arrow(0x26, RS['PANY'], -STEP, 'kU')                  # VK_UP
    arrow(0x28, RS['PANY'], +STEP, 'kD')                  # VK_DOWN

    # --- 鼠标: 按下拖动平移, 未拖动则单击关闭 ---
    _p8(a, 0x01)                                          # VK_LBUTTON
    a.b(0xFF, 0x15); a.dw(T(A['GAKS']))
    a.b(0x0F, 0xB7, 0xC0); a.b(0x25); a.dw(0x8000)
    a.jr32(0x84, 'mouseup')
    _p32(a, ctx['PT_VA'])
    a.b(0xFF, 0x15); a.dw(T(A['GCUR']))
    # GetCursorPos 给的是**屏幕**坐标, 而节点/PANX 绘制用的是**客户区**坐标。
    # 就地转成客户坐标, 于是拖拽增量(与平移同系)和单击命中(与 cx+PANX 同系)都对得上。
    _p32(a, ctx['PT_VA'])                                  # push &pt (lpPoint)
    push_r(a, RS['HWND'])                                  # push hwnd
    a.b(0xFF, 0x15); a.dw(T(A['S2C']))                     # ScreenToClient(hwnd, &pt)
    _ld(a, ctx['PT_VA']); st(a, RS['MX1'])
    _ld(a, ctx['PT_VA'] + 4); st(a, RS['MY1'])
    ld(a, RS['DRAG'])
    a.b(0x85, 0xC0); a.jr32(0x85, 'dragging')
    # 刚按下
    _set(a, RV + RS['DRAG'], 1)
    _set(a, RV + RS['MOVED'], 0)
    ld(a, RS['MX1']); st(a, RS['MX0'])
    ld(a, RS['MY1']); st(a, RS['MY0'])
    a.jmpabs('mousedone')
    a.label('dragging')
    # esi = dx ; edi = dy
    ld(a, RS['MX1']); ldc(a, RS['MX0'])
    a.b(0x29, 0xC8); a.b(0x89, 0xC6)                      # sub eax,ecx ; mov esi,eax
    ld(a, RS['MY1']); ldc(a, RS['MY0'])
    a.b(0x29, 0xC8); a.b(0x89, 0xC7)
    # 阈值 3px: 小于阈值不算拖拽(容手抖, 保证单击仍能关闭)
    a.b(0x83, 0xFE, 0x03); a.jr32(0x8D, 'moved')          # cmp esi,3  ; jge
    a.b(0x83, 0xFE, 0xFD); a.jr32(0x8E, 'moved')          # cmp esi,-3 ; jle
    a.b(0x83, 0xFF, 0x03); a.jr32(0x8D, 'moved')
    a.b(0x83, 0xFF, 0xFD); a.jr32(0x8E, 'moved')
    a.jmpabs('nomoved')
    a.label('moved')
    _set(a, RV + RS['MOVED'], 1)
    a.label('nomoved')
    ld(a, RS['PANX']); a.b(0x01, 0xF0); st(a, RS['PANX'])  # add eax,esi
    ld(a, RS['PANY']); a.b(0x01, 0xF8); st(a, RS['PANY'])  # add eax,edi
    ld(a, RS['MX1']); st(a, RS['MX0'])
    ld(a, RS['MY1']); st(a, RS['MY0'])
    a.jmpabs('mousedone')
    a.label('mouseup')
    ld(a, RS['DRAG'])
    a.b(0x85, 0xC0); a.jr32(0x84, 'mousedone')            # 没按过 -> 无事
    _set(a, RV + RS['DRAG'], 0)
    ld(a, RS['MOVED'])
    a.b(0x85, 0xC0); a.jr32(0x85, 'mousedone')            # 拖过 -> 不关
    # --- 单击(未拖拽): 命中节点=弹详情并留在树里; 空白处=关闭 ---
    logb(a, 0xA0)
    a.b(0x8B, 0x1D); a.dw(RV + RS['FAMP'])                # mov ebx,[FAMP]
    a.b(0x85, 0xDB); a.jr32(0x84, 'quit')                 # 无家族 -> 关
    a.b(0x0F, 0xB6, 0x43, 0x08)                           # movzx eax,byte[ebx+8] start/2
    a.b(0x0F, 0xB6, 0x4B, 0x09)                           # movzx ecx,byte[ebx+9] count
    a.b(0x6B, 0xC0, START_MUL)                            # imul eax,eax,2*NODE_SZ
    a.b(0x05); a.dw(NODES_VA)                             # add eax,NODES_VA
    a.b(0x89, 0xC6)                                       # mov esi,eax
    a.b(0x31, 0xFF)                                       # xor edi,edi (i)
    a.label('ht0')
    a.b(0x0F, 0xBF, 0x16)                                 # movsx edx,word[esi+0] node.cx
    a.b(0x03, 0x15); a.dw(RV + RS['PANX'])                # add edx,[PANX] (sx)
    _ld(a, RV + RS['MX1'])                                # mov eax,[MX1]
    a.b(0x29, 0xD0)                                       # sub eax,edx
    a.jr8(0x7D, 'hx1')                                    # jge hx1
    a.b(0xF7, 0xD8)                                       # neg eax
    a.label('hx1')
    a.b(0x83, 0xF8, AV_HX); a.jr8(0x77, 'htn')            # cmp eax,13 ; ja next
    a.b(0x0F, 0xBF, 0x56, 0x02)                           # movsx edx,word[esi+2] node.cy
    a.b(0x03, 0x15); a.dw(RV + RS['PANY'])                # add edx,[PANY] (sy)
    _ld(a, RV + RS['MY1'])                                # mov eax,[MY1]
    a.b(0x29, 0xD0)                                       # sub eax,edx
    a.jr8(0x7D, 'hy1')                                    # jge hy1
    a.b(0xF7, 0xD8)                                       # neg eax
    a.label('hy1')
    a.b(0x83, 0xF8, AV_HY); a.jr8(0x77, 'htn')            # cmp eax,15 ; ja next
    # 命中: 全局索引 = 2*(start/2) + i -> DETAILTAB[gi] -> SELDETOFF
    a.b(0x0F, 0xB6, 0x43, 0x08)                           # movzx eax,byte[ebx+8] start/2
    a.b(0x6B, 0xC0, 0x02)                                 # imul eax,eax,2
    a.b(0x01, 0xF8)                                       # add eax,edi
    a.b(0x0F, 0xB7, 0x04, 0x45); a.dw(DETAILTAB_VA)       # movzx eax,word[eax*2+DTLTAB]
    a.b(0xA3); a.dw(RV + RS['SELDETOFF'])                 # mov [SELDETOFF],eax
    _set(a, RV + RS['LASTX'], 0x7FFFFFFF)                 # 强制下一帧重绘(画详情)
    a.jmpabs('mousedone')                                 # 留在树里
    a.label('htn')
    a.b(0x83, 0xC6, NODE_SZ)                              # add esi,10
    a.b(0x47)                                             # inc edi
    a.b(0x3B, 0xF9); a.jr32(0x8C, 'ht0')                  # cmp edi,ecx ; jl ht0 (索引在 edi, 勿用 0xC1=eax)
    a.jmpabs('quit')                                      # 遍历无命中 -> 关
    a.label('mousedone')
    a.callabs(clamp_va)
    _p8(a, 15)
    a.b(0xFF, 0x15); a.dw(T(A['SLEEP']))
    a.label('out')
    logb(a, 0x6F)
    a.b(0x61); a.b(0xC3)
    a.label('quit')
    # 关窗瞬间消费掉模态期间累积的点击, 否则回到信息卡循环后 ft_click 会立刻重开树
    _ld(a, ctx['LBDOWN_VA'])
    _st(a, ctx['LBSEEN_VA'])
    _set(a, ctx['LBPREV_VA'], 1)
    _set(a, ctx['FAMILY_VA'], 0)
    _set(a, RV + RS['QUIT'], 1)
    logb(a, 0x6E)
    a.jmpabs('out')
    blobs.append(('pump', commit(a)))

    # ==================================================================
    # 7) draw_frame
    # ==================================================================
    frame_va = cur[0]
    a = new()
    a.b(0x60)
    logb(a, 0x70)
    a.b(0x8B, 0x1D); a.dw(RV + RS['FAMP'])                # mov ebx,[FAMP]
    # 面板底
    sel(a, RS['BRBG']); sel(a, RS['PENFR'])
    for off in (RS['WY1'], RS['WX1'], RS['WY0'], RS['WX0']):
        push_r(a, off)
    push_hdc(a)
    a.b(0xFF, 0x15); a.dw(T(A['RECT']))
    # 内衬线
    sel(a, RS['PENIN'])
    for off, d in ((RS['WY1'], -INNER), (RS['WX1'], -INNER),
                   (RS['WY0'], INNER), (RS['WX0'], INNER)):
        push_r(a, off, d)
    push_hdc(a)
    a.b(0xFF, 0x15); a.dw(T(A['RECT']))
    _p8(a, 0x01); push_hdc(a)
    a.b(0xFF, 0x15); a.dw(T(A['SETBK']))                  # TRANSPARENT
    # 标题(家族名)
    sel(a, RS['FTTI']); setcolor(a, C['TITLE']); align_center(a)
    pool_str(a, 10)                                       # word[fam+10] = title_off
    textout(a, RS['WY0'], TITLE_OFS)
    # 底部操作提示
    sel(a, RS['FTRL']); setcolor(a, C['HINT']); align_center(a)
    _p32(a, ctx['HINT_LEN'])
    _p32(a, ctx['STR_HINT_VA'])
    textout(a, RS['WY1'], -HINT_OFS)
    # 设视口裁剪 —— 树本体不许越出中间区域
    for off in (RS['VY1'], RS['VX1'], RS['VY0'], RS['VX0']):
        push_r(a, off)
    push_hdc(a)
    a.b(0xFF, 0x15); a.dw(T(A['ICLIP']))
    logb(a, 0x7F)
    a.b(0x61); a.b(0xC3)
    blobs.append(('draw_frame', commit(a)))

    # ==================================================================
    # 8) draw_edges
    # ==================================================================
    edges_va = cur[0]
    a = new()
    a.b(0x60)
    logb(a, 0x80)
    a.b(0x8B, 0x1D); a.dw(RV + RS['FAMP'])
    # --- 前置 1: 找「本人」, 存内容坐标 cx,cy 到 SUBJX/SUBJY ---
    a.b(0x0F, 0xB6, 0x6B, 8)                              # ebp = start/2
    a.b(0x6B, 0xED, START_MUL); a.b(0x81, 0xC5); a.dw(NODES_VA)   # ebp = start*NSZ+NODES_VA
    a.b(0x89, 0xEE)                                       # mov esi,ebp (扫描指针)
    a.b(0x0F, 0xB6, 0x4B, 9)                              # ecx = count
    a.b(0x31, 0xC0)                                       # xor eax,eax (i)
    a.label('fnd')
    a.b(0x0F, 0xB6, 0x56, 9)                              # movzx edx,byte[esi+9] flags
    a.b(0xF6, 0xC2, 0x04); a.jr8(0x75, 'fsubj')           # test dl,4(F_SUBJECT) ; jnz
    a.b(0x83, 0xC6, NODE_SZ); a.b(0x40)                   # esi += NSZ ; inc eax
    # !! 39 /r 是 "cmp r/m32, r32" —— 写 39 C1 会编成 cmp ecx,eax(方向反了),
    #    于是 "count < i" 第一圈就为假 -> 直接落进"未找到"分支, SUBJX 留 -1。
    a.b(0x3B, 0xC1); a.jr8(0x7C, 'fnd')                   # cmp eax,ecx ; jl
    a.b(0xC7, 0x05); a.dw(RV + RS['SUBJX']); a.dw(0xFFFFFFFF)   # 未找到 -> -1
    a.b(0xC7, 0x05); a.dw(RV + RS['SUBJY']); a.dw(0xFFFFFFFF)
    a.jmpabs('fdone')
    a.label('fsubj')
    a.b(0x0F, 0xBF, 0x46, 0); a.b(0xA3); a.dw(RV + RS['SUBJX'])   # movsx eax,word[esi+0]; mov[SUBJX],eax
    a.b(0x0F, 0xBF, 0x46, 2); a.b(0xA3); a.dw(RV + RS['SUBJY'])   # movsx eax,word[esi+2]; mov[SUBJY],eax
    a.label('fdone')
    # --- 前置 2: 找**首个**「配偶」, 预计算其框左右缘 SPOUSEL/SPOUSER ---
    #    只用于亲子横杠遇配偶断开; v9 多对夫妻时按首对(本人辈)断开。
    a.b(0x89, 0xEE)                                       # mov esi,ebp 重置扫描
    a.b(0x0F, 0xB6, 0x4B, 9)                              # ecx = count
    a.b(0x31, 0xC0)                                       # xor eax,eax
    a.label('fsp')
    a.b(0x0F, 0xB6, 0x56, 9)                              # movzx edx,byte[esi+9]
    a.b(0xF6, 0xC2, 0x08); a.jr8(0x75, 'fsp_found')       # test dl,8(F_SPOUSE) ; jnz
    a.b(0x83, 0xC6, NODE_SZ); a.b(0x40)                   # esi += NSZ ; inc eax
    a.b(0x3B, 0xC1); a.jr8(0x7C, 'fsp')                   # cmp eax,ecx ; jl (同上, 勿用 39 C1)
    a.b(0xC7, 0x05); a.dw(RV + RS['SPOUSEX']); a.dw(0xFFFFFFFF)
    a.b(0xC7, 0x05); a.dw(RV + RS['SPOUSEY']); a.dw(0xFFFFFFFF)
    a.b(0xC7, 0x05); a.dw(RV + RS['SPOUSEL']); a.dw(0xFFFFFFFF)
    a.jmpabs('fsp_done')
    a.label('fsp_found')
    a.b(0x0F, 0xBF, 0x46, 0); a.b(0xA3); a.dw(RV + RS['SPOUSEX'])
    a.b(0x0F, 0xBF, 0x46, 2); a.b(0xA3); a.dw(RV + RS['SPOUSEY'])
    # SPL = SPOUSEX - AV_HX + PANX,  SPR = SPOUSEX + AV_HX + PANX
    ld(a, RS['SPOUSEX']); _add8(a, -AV_HX); a.b(0x03, 0x05); a.dw(RV + RS['PANX']); a.b(0xA3); a.dw(RV + RS['SPOUSEL'])
    ld(a, RS['SPOUSEX']); _add8(a, AV_HX); a.b(0x03, 0x05); a.dw(RV + RS['PANX']); a.b(0xA3); a.dw(RV + RS['SPOUSER'])
    a.label('fsp_done')
    # --- 主循环准备 ---
    a.b(0x0F, 0xB6, 0x7B, 9)                              # edi = count
    a.b(0x0F, 0xB6, 0x6B, 8)                              # ebp = start/2
    a.b(0x6B, 0xED, START_MUL); a.b(0x81, 0xC5); a.dw(NODES_VA)
    a.b(0x8B, 0xDD)                                       # mov ebx,ebp
    a.b(0x85, 0xFF); a.jr32(0x84, 'done')
    sel(a, RS['PENLN'])
    a.label('loop')
    # 节点屏幕坐标(所有节点都先算, 配偶/亲子共用)
    a.b(0x0F, 0xBF, 0x03); a.b(0x03, 0x05); a.dw(RV + RS['PANX']); st(a, RS['CX'])
    a.b(0x0F, 0xBF, 0x4B, 2); _ldd(a, RV + RS['PANY']); a.b(0x01, 0xCA); std(a, RS['CY'])
    # --- 配偶判定: F_SPOUSE(bit3) ---
    a.b(0x0F, 0xB6, 0x43, 9)                              # movzx eax,byte[ebx+9] flags
    a.b(0xF6, 0xC0, 0x08); a.jr32(0x84, 'not_spouse')     # test al,8 ; jz (括号分支变长, 需 rel32)
    # === 配偶括号(U形) v9: 对每个 F_SPOUSE 节点画 丈夫↔妻 括号 ===
    #    约定: 配偶节点的 parent = 丈夫索引(布局同排, 妻在夫右半格)。
    #    青色 PENAC。三笔: 夫框底短竖 ↓ / 横线(夫中心x→妻中心x) / ↑ 妻框底短竖。
    #    横线落在两人姓名文字**上方**(cy+AV_HY+4 < cy+OFS_NAME), 不穿字。
    #    括号纯属婚姻标记, **子女线不从括号中心挂**(养子未必是配偶所生) ——
    #    子女按各自 parent 从父/母节点本人下方垂线。
    sel(a, RS['PENAC'])
    # 丈夫节点指针 = 族基址ebp + parent×NODE_SZ (parent 是**族内**索引!)
    a.b(0x0F, 0xB6, 0x43, 8)                              # movzx eax,byte[ebx+8]
    a.b(0x6B, 0xC0, NODE_SZ); a.b(0x01, 0xE8)             # imul eax,NSZ; add eax,ebp
    a.b(0x89, 0xC6)                                       # mov esi,eax
    a.b(0x0F, 0xBF, 0x06); a.b(0x03, 0x05); a.dw(RV + RS['PANX']); st(a, RS['PX'])   # 夫屏幕x
    a.b(0x0F, 0xBF, 0x4E, 2); _ldd(a, RV + RS['PANY']); a.b(0x01, 0xCA); std(a, RS['PY'])  # 夫屏幕y
    _p8(a, 0x00)                                          # lppt = NULL
    push_r(a, RS['PY'], AV_HY)                            # 左竖起点: 夫框底
    ld(a, RS['PX']); a.b(0x50)
    push_hdc(a)
    a.b(0xFF, 0x15); a.dw(T(A['MOVETO']))
    push_r(a, RS['PY'], AV_HY + 4)                        # 左竖终点: 括号横线高
    ld(a, RS['PX']); a.b(0x50)
    push_hdc(a)
    a.b(0xFF, 0x15); a.dw(T(A['LINETO']))
    _p8(a, 0x00)
    push_r(a, RS['PY'], AV_HY + 4)                        # 横线起点: 夫中心x
    ld(a, RS['PX']); a.b(0x50)
    push_hdc(a)
    a.b(0xFF, 0x15); a.dw(T(A['MOVETO']))
    push_r(a, RS['CY'], AV_HY + 4)                        # 横线终点: 妻中心x
    push_r(a, RS['CX'])
    push_hdc(a)
    a.b(0xFF, 0x15); a.dw(T(A['LINETO']))
    _p8(a, 0x00)
    push_r(a, RS['CY'], AV_HY + 4)                        # 右竖起点: 括号横线高
    push_r(a, RS['CX'])
    push_hdc(a)
    a.b(0xFF, 0x15); a.dw(T(A['MOVETO']))
    push_r(a, RS['CY'], AV_HY)                            # 右竖终点: 妻框底
    push_r(a, RS['CX'])
    push_hdc(a)
    a.b(0xFF, 0x15); a.dw(T(A['LINETO']))
    a.jmpabs('skip')
    a.label('not_spouse')
    sel(a, RS['PENLN'])
    # --- 原亲子折线 (parent==0xFF 跳过) ---
    a.b(0x0F, 0xB6, 0x43, 8)                              # movzx eax,byte[ebx+8] parent
    a.b(0x3C, 0xFF); a.jr32(0x84, 'skip')
    a.b(0x6B, 0xC0, NODE_SZ); a.b(0x01, 0xE8)             # imul eax,NSZ; add eax,ebp (parent=族内索引)
    a.b(0x89, 0xC6)                                       # mov esi,eax
    # 父节点屏幕坐标
    a.b(0x0F, 0xBF, 0x06); a.b(0x03, 0x05); a.dw(RV + RS['PANX']); st(a, RS['PX'])
    a.b(0x0F, 0xBF, 0x4E, 2); _ldd(a, RV + RS['PANY']); a.b(0x01, 0xCA); std(a, RS['PY'])
    # 子节点屏幕坐标(已算入 CX/CY, 这里重算保持原逻辑)
    a.b(0x0F, 0xBF, 0x03); a.b(0x03, 0x05); a.dw(RV + RS['PANX']); st(a, RS['CX'])
    a.b(0x0F, 0xBF, 0x4B, 2); _ldd(a, RV + RS['PANY']); a.b(0x01, 0xCA); std(a, RS['CY'])
    # 折线: (px, py+EDGE_TOP) -> (px, BAR) -> (cx, BAR) -> (cx, cy-AV_HY)
    # EDGE_TOP 必须落在**父节点自己的标签下方** —— 否则那条竖线会把
    # 父节点的姓名/关系从中间划开(实测看起来就是"字被劈成两半")。
    # BAR 落在子节点框上方一点, 同一代兄弟共用同一条横杠(组织图样式)。
    _p8(a, 0x00)
    push_r(a, RS['PY'], EDGE_TOP)
    push_r(a, RS['PX']); push_hdc(a)
    a.b(0xFF, 0x15); a.dw(T(A['MOVETO']))
    # 横杠：从父节点 px 到子节点 cx。若中间有配偶节点，
    # 在配偶头像两侧断开，避免父线横穿配偶、使其看起来像子女。
    ld(a, RS['SPOUSEX']); a.b(0x83, 0xF8, 0xFF); a.jr32(0x84, 'hbar_single')  # 无配偶 -> 单段
    ld(a, RS['CX']); ldc(a, RS['SPOUSEL']); a.b(0x3B, 0xC1); a.jr32(0x8E, 'hbar_single')  # cx <= 配偶左 -> 单段
    ld(a, RS['PX']); a.b(0x3B, 0x05); a.dw(RV + RS['SPOUSER']); a.jr32(0x8D, 'hbar_single')  # px >= 配偶右 -> 单段
    # ---- 分段横杠：px↓ -> SPL | 跳过配偶 | SPR -> cx ----
    #      ★ 之前漏了 px->SPL 这一段, 父竖线与 SPR 右侧的线段之间空了
    #        整整一个配偶框宽 —— 看起来就是"胜政那根线断了"。
    push_r(a, RS['CY'], -EDGE_BAR); push_r(a, RS['PX']); push_hdc(a)
    a.b(0xFF, 0x15); a.dw(T(A['LINETO']))                 # 竖线下探到横杠高
    push_r(a, RS['CY'], -EDGE_BAR); push_r(a, RS['SPOUSEL']); push_hdc(a)
    a.b(0xFF, 0x15); a.dw(T(A['LINETO']))                 # 横杠: px -> 配偶左缘
    _p8(a, 0x00)
    push_r(a, RS['CY'], -EDGE_BAR); push_r(a, RS['SPOUSER']); push_hdc(a)
    a.b(0xFF, 0x15); a.dw(T(A['MOVETO']))
    push_r(a, RS['CY'], -EDGE_BAR); push_r(a, RS['CX']); push_hdc(a)
    a.b(0xFF, 0x15); a.dw(T(A['LINETO']))                 # 横杠: 配偶右缘 -> cx
    a.jmpabs('hbar_done')
    a.label('hbar_single')
    for xo in (RS['PX'], RS['CX']):
        ld(a, RS['CY']); _addi(a, -EDGE_BAR); a.b(0x50)   # push BAR
        push_r(a, xo); push_hdc(a)
        a.b(0xFF, 0x15); a.dw(T(A['LINETO']))
    a.label('hbar_done')
    push_r(a, RS['CY'], -AV_HY); push_r(a, RS['CX']); push_hdc(a)
    a.b(0xFF, 0x15); a.dw(T(A['LINETO']))
    a.label('skip')
    a.b(0x83, 0xC3, NODE_SZ)
    a.b(0x4F); a.jr32(0x85, 'loop')
    a.label('done')
    logb(a, 0x8F)
    a.b(0x61); a.b(0xC3)
    blobs.append(('draw_edges', commit(a)))

    # ==================================================================
    # 9) draw_nodes
    # ==================================================================
    def pick3(a, base, tag):
        """按 eax(状态 0/1/2) 选 [RSTATE+base+eax*4] 并 SelectObject"""
        a.b(0x83, 0xE0, 0x03)                             # and eax,3 (状态位)
        a.b(0x85, 0xC0); a.jr8(0x74, tag + '0')
        a.b(0x83, 0xF8, 0x01); a.jr8(0x74, tag + '1')
        sel(a, base + 8); a.jmpabs(tag + 'e')
        a.label(tag + '1'); sel(a, base + 4); a.jmpabs(tag + 'e')
        a.label(tag + '0'); sel(a, base)
        a.label(tag + 'e')

    def ell(a, box):
        for off, d in ((RS['CY'], box[3]), (RS['CX'], box[2]),
                       (RS['CY'], box[1]), (RS['CX'], box[0])):
            push_r(a, off, d)
        push_hdc(a)
        a.b(0xFF, 0x15); a.dw(T(A['ELLIPSE']))

    def box(a, hx, hy):
        for off, d in ((RS['CY'], hy), (RS['CX'], hx),
                       (RS['CY'], -hy), (RS['CX'], -hx)):
            push_r(a, off, d)
        push_hdc(a)
        a.b(0xFF, 0x15); a.dw(T(A['RECT']))

    nodes_va = cur[0]
    a = new()
    a.b(0x60)
    logb(a, 0x90)
    a.b(0x8B, 0x1D); a.dw(RV + RS['FAMP'])
    a.b(0x0F, 0xB6, 0x7B, 9)
    a.b(0x0F, 0xB6, 0x6B, 8)
    a.b(0x6B, 0xED, START_MUL); a.b(0x81, 0xC5); a.dw(NODES_VA)
    a.b(0x8B, 0xDD)
    a.b(0x85, 0xFF); a.jr32(0x84, 'done')
    _p8(a, 0x01); push_hdc(a)
    a.b(0xFF, 0x15); a.dw(T(A['SETBK']))                  # TRANSPARENT
    align_center(a)
    a.label('loop')
    # --- 屏幕坐标 ---
    a.b(0x0F, 0xBF, 0x03); a.b(0x03, 0x05); a.dw(RV + RS['PANX']); st(a, RS['CX'])
    a.b(0x0F, 0xBF, 0x4B, 2); _ldd(a, RV + RS['PANY']); a.b(0x01, 0xCA); std(a, RS['CY'])
    # --- 头像框: 按状态选填刷/描边 ---
    a.b(0x0F, 0xB6, 0x43, 9)
    pick3(a, RS['BRN0'], 'nb')
    a.b(0x0F, 0xB6, 0x43, 9)
    pick3(a, RS['PENF0'], 'np')
    box(a, AV_HX, AV_HY)
    # --- 头肩剪影 ---
    sel(a, RS['NP']); sel(a, RS['BRSH'])
    ell(a, HEAD)
    ell(a, BODY)
    # --- 本人: 外圈高亮 ---
    a.b(0x8A, 0x43, 9); a.b(0xA8, 0x04)                   # mov al,[ebx+9] ; test al,4
    a.jr8(0x74, 'nosub')
    sel(a, RS['PENAC']); sel(a, RS['NB'])
    box(a, AV_HX + 3, AV_HY + 3)
    a.label('nosub')
    # --- 姓名 ---
    sel(a, RS['FTNM']); setcolor(a, C['TXT']); align_center(a)
    pool_str(a, 4)
    textout_node(a, RS['CY'], OFS_NAME)
    # --- 关系 ---
    sel(a, RS['FTRL']); setcolor(a, C['REL']); align_center(a)
    pool_str(a, 6)
    textout_node(a, RS['CY'], OFS_REL)
    a.b(0x83, 0xC3, NODE_SZ)
    a.b(0x4F); a.jr32(0x85, 'loop')
    a.label('done')
    logb(a, 0x9F)
    a.b(0x61); a.b(0xC3)
    blobs.append(('draw_nodes', commit(a)))

    # ==================================================================
    # 9b) draw_detail —— 点选节点的详情框(浮在面板底部)
    #     纯 MOD 自绘: 内容 = 烘进 POOL 的详情记录 [u8 len1][主行][u8 len2][档案行]。
    #     主行(FTNM)=姓名/关系/状态/家族; 档案行(FTRL)=生年/职级/五维(仅 exact/alias)。
    #     ★ 曾用 SetTextAlign(0x01)=TA_UPDATECP -> TextOut 忽略 x,y 全叠在光标位
    #       ("文字挤成一堆"), 现改 TA_LEFT|TA_TOP(0x00) 显式定位每行。
    # ==================================================================
    detail_va = cur[0]
    a = new()
    a.b(0x60)                                           # pushad
    ld(a, RS['SELDETOFF'])                              # mov eax,[SELDETOFF]
    a.b(0x3D); a.dw(0xFFFFFFFF)                         # cmp eax,-1
    a.jr32(0x84, 'ddone')                               # je 未选 -> 什么都不做
    logb(a, 0xA1)
    _p8(a, 0); push_hdc(a)                              # SelectClipRgn(hdc, NULL) 复位裁剪
    a.b(0xFF, 0x15); a.dw(T(A['SCLIP']))
    logb(a, 0xA2)                                       # 埋点: SelectClipRgn 已返回
    # ★ 修正寄存器污染崩溃: 上面 push_hdc 把 hdc 塞进 eax, SelectClipRgn 又用返回值
    #   (区域码 0/2/3)毁掉 eax —— 旧代码 `mov ebx,eax` 于是拿到的是**区域码**, 详情
    #   指针变成 POOL+0..3(串池开头的乱码), 长度是随机 GBK 字节 -> TextOut 画出乱码
    #   后崩(实测 big.exe 0x53A639)。详情偏移 SELDETOFF 是内存全局, stdcall 不动它,
    #   直接从内存取进 ebx(stdcall 保 ebx), 之后 add POOL 得 &记录。
    a.b(0x8B, 0x1D); a.dw(RV + RS['SELDETOFF'])         # mov ebx,[SELDETOFF]
    a.b(0x81, 0xC3); a.dw(POOL_VA)                      # add ebx,POOL_VA  -> ebx=&记录
    # --- 底(墨蓝填充, 无笔) ---
    sel(a, RS['BRBG']); sel(a, RS['NP'])
    push_r(a, RS['WY1'], -2)                            # bottom
    push_r(a, RS['WX1'], -INNER)                        # right
    push_r(a, RS['WY1'], -(DET_H + 2))                  # top
    push_r(a, RS['WX0'], INNER)                         # left
    push_hdc(a)
    a.b(0xFF, 0x15); a.dw(T(A['RECT']))
    # --- 金边(空刷 + PENAC) ---
    sel(a, RS['NB']); sel(a, RS['PENAC'])
    push_r(a, RS['WY1'], -2)
    push_r(a, RS['WX1'], -INNER)
    push_r(a, RS['WY1'], -(DET_H + 2))
    push_r(a, RS['WX0'], INNER)
    push_hdc(a)
    a.b(0xFF, 0x15); a.dw(T(A['RECT']))
    _p8(a, 0x01); push_hdc(a)                           # SetBkMode TRANSPARENT
    a.b(0xFF, 0x15); a.dw(T(A['SETBK']))
    _p8(a, 0x00); push_hdc(a)                           # SetTextAlign TA_LEFT|TA_TOP
    a.b(0xFF, 0x15); a.dw(T(A['SETA']))
    # --- 主行: 姓名/关系/状态/家族 (FTNM) ---
    sel(a, RS['FTNM']); setcolor(a, C['TXT'])
    a.b(0x0F, 0xB6, 0x0B)                               # movzx ecx,byte[ebx]      len1
    a.b(0x8D, 0x53, 0x01)                               # lea edx,[ebx+1]          主行
    a.b(0x51); a.b(0x52)                                # push cch; push lpString
    push_r(a, RS['WY1'], -(DET_H + 2) + DET_PAD)        # y1
    push_r(a, RS['WX0'], INNER + DET_PAD)               # x
    push_hdc(a)
    a.b(0xFF, 0x15); a.dw(T(A['TEXTOUT']))
    logb(a, 0xA3)                                       # 埋点: 主行 TextOut 已返回
    # --- 档案行: 生年/职级/五维 (FTRL); len2=0 则无 ---
    #   ★ 崩溃根因(实测 log 停在 A3、dump 为 KERNELBASE 读未映射堆地址 AV):
    #     SelectObject/SetTextColor 都是 stdcall, 会毁掉 volatile 的 EAX/ECX/EDX。
    #     旧代码先把 len2 放进 ecx、档案串指针放进 edx, 再 sel/setcolor, 于是随后
    #     `push ecx; push edx` 推的是被污染的值 -> TextOutA 拿到乱指针读到未映射页崩。
    #     主行不受影响是因为它 load 完立刻 push(值已上栈)。修法: 用 callee-saved 的
    #     esi 暂存 &len2, 先设好字体/颜色, 再从 esi 现取长度与指针后才 push。
    a.b(0x0F, 0xB6, 0x03)                               # movzx eax,byte[ebx]      len1
    a.b(0x8D, 0x74, 0x03, 0x01)                         # lea esi,[ebx+eax+1]      &len2 (esi 不被 stdcall 毁)
    a.b(0x0F, 0xB6, 0x4E, 0x00)                         # movzx ecx,byte[esi]      len2  (仅判空)
    a.b(0x85, 0xC9); a.jr32(0x84, 'ddone')              # test ecx,ecx ; jz 无档案行
    sel(a, RS['FTRL']); setcolor(a, C['REL'])           # 先选字体/颜色(此处毁 eax/ecx/edx)
    a.b(0x0F, 0xB6, 0x4E, 0x00)                         # movzx ecx,byte[esi]      len2  (污染后重取)
    a.b(0x8D, 0x56, 0x01)                               # lea edx,[esi+1]          档案串指针
    a.b(0x51); a.b(0x52)                                # push cch; push lpString
    push_r(a, RS['WY1'], -(DET_H + 2) + DET_PAD + DET_LINEH)   # y2
    push_r(a, RS['WX0'], INNER + DET_PAD)               # x
    push_hdc(a)
    a.b(0xFF, 0x15); a.dw(T(A['TEXTOUT']))
    logb(a, 0xA4)                                       # 埋点: 档案行 TextOut 已返回
    a.label('ddone')
    a.b(0x61); a.b(0xC3)
    blobs.append(('draw_detail', commit(a)))

    # ==================================================================
    # 10) tree_show
    # ==================================================================
    show_va = cur[0]
    a = new()
    a.b(0x60)
    a.callabs(resolve_va)                                 # ★ 一切都要先有 GDI_TAB
    _ld(a, ctx['GDIOK_VA'])
    a.b(0x85, 0xC0); a.jr32(0x84, 'out')
    a.callabs(log_va)
    logb(a, 0x00)
    stage(a, 1)
    a.b(0xFF, 0x15); a.dw(T(A['GAW']))
    a.b(0x85, 0xC0); a.jr32(0x84, 'out')
    _st(a, RV + RS['HWND'])
    push_r(a, RS['HWND'])
    a.b(0xFF, 0x15); a.dw(T(A['GETDC']))
    a.b(0x85, 0xC0); a.jr32(0x84, 'out')
    _st(a, RV + RS['HDC'])
    stage(a, 2)
    # --- 客户区尺寸 -> 面板居中 ---
    _p32(a, ctx['RC_VA']); push_r(a, RS['HWND'])
    a.b(0xFF, 0x15); a.dw(T(A['GCRECT']))
    _ld(a, ctx['RC_VA'] + 8); st(a, RS['CW'])
    _ld(a, ctx['RC_VA'] + 12); st(a, RS['CH'])
    ld(a, RS['CW']); _addi(a, -PW); a.b(0xD1, 0xF8); st(a, RS['WX0'])
    ld(a, RS['CH']); _addi(a, -PH); a.b(0xD1, 0xF8); st(a, RS['WY0'])
    ld(a, RS['WX0']); _addi(a, PW - 1); st(a, RS['WX1'])
    ld(a, RS['WY0']); _addi(a, PH - 1); st(a, RS['WY1'])
    ld(a, RS['WX0']); _addi(a, INSET); st(a, RS['VX0'])
    ld(a, RS['WY0']); _addi(a, TITLE_H); st(a, RS['VY0'])
    ld(a, RS['WX1']); _addi(a, -INSET); st(a, RS['VX1'])
    ld(a, RS['WY1']); _addi(a, -HINT_H); st(a, RS['VY1'])
    stage(a, 3)
    # --- 初始平移: 把「本人」放到视口正中 ---
    a.b(0x8B, 0x1D); a.dw(RV + RS['FAMP'])
    a.b(0x0F, 0xB6, 0x43, 20)                             # movzx eax,byte[fam+20] subject(族内索引)
    a.b(0x6B, 0xC0, NODE_SZ)
    a.b(0x0F, 0xB6, 0x4B, 8)                              # movzx ecx,byte[fam+8] start/2
    a.b(0x6B, 0xC9, START_MUL)                            # imul ecx,ecx,2*NODE_SZ
    a.b(0x03, 0xC8)                                       # add eax,ecx
    # ★旧代码只乘了 subject, 把 start 当 0 —— 于是第 2 个以后的族开树时"居中"对准的是
    #   柴田家的人(坐标读到的是别的节点), 表现为"一开树本人不在中间/画面歪一半"。
    a.b(0x0F, 0xBF, 0x88); a.dw(NODES_VA); st(a, RS['CX'])
    a.b(0x0F, 0xBF, 0x90); a.dw(NODES_VA + 2); std(a, RS['CY'])
    ld(a, RS['VX0']); ldc(a, RS['VX1'])
    a.b(0x03, 0xC1); a.b(0xD1, 0xF8); ldc(a, RS['CX'])
    a.b(0x29, 0xC8); st(a, RS['PANX'])
    ld(a, RS['VY0']); ldc(a, RS['VY1'])
    a.b(0x03, 0xC1); a.b(0xD1, 0xF8); ldc(a, RS['CY'])
    a.b(0x29, 0xC8); st(a, RS['PANY'])
    _set(a, RV + RS['QUIT'], 0)
    _set(a, RV + RS['DRAG'], 0)
    _set(a, RV + RS['MOVED'], 0)
    _set(a, RV + RS['SELDETOFF'], 0xFFFFFFFF)           # 每次开树: 无选中
    # LASTX/LASTY 用「不可能相等」的哨兵值 -> 第一帧必定重画
    _set(a, RV + RS['LASTX'], 0x7FFFFFFF)
    _set(a, RV + RS['LASTY'], 0x7FFFFFFF)
    a.callabs(clamp_va)
    stage(a, 4)
    a.callabs(make_va)
    stage(a, 5)
    a.callabs(wait_va)
    a.label('loop')
    stage(a, 6)
    # --- 脏检查: 平移量没变就不重画 ---
    # 每帧整块重绘(先铺底再画线画节点)在屏幕上是"闪"的, 而且截图很容易
    # 抓到"边框连画好了、节点还没画"的半成品帧。静止时干脆一次都不画。
    ld(a, RS['PANX']); ldc(a, RS['LASTX'])
    a.b(0x39, 0xC8); a.jr32(0x85, 'draw')                 # cmp eax,ecx ; jne draw
    ld(a, RS['PANY']); ldc(a, RS['LASTY'])
    a.b(0x39, 0xC8); a.jr32(0x85, 'draw')
    a.jmpabs('nodraw')
    a.label('draw')
    a.callabs(frame_va)
    stage(a, 7)
    a.callabs(edges_va)
    stage(a, 8)
    a.callabs(nodes_va)
    stage(a, 9)
    a.callabs(detail_va)
    stage(a, 13)
    ld(a, RS['PANX']); st(a, RS['LASTX'])
    ld(a, RS['PANY']); st(a, RS['LASTY'])
    a.label('nodraw')
    a.callabs(pump_va)
    stage(a, 10)
    _ld(a, RV + RS['QUIT'])
    a.b(0x85, 0xC0); a.jr32(0x84, 'loop')
    stage(a, 11)
    a.callabs(free_va)
    push_hdc(a); push_r(a, RS['HWND'])
    a.b(0xFF, 0x15); a.dw(T(A['RELDC']))
    stage(a, 12)
    a.label('out')
    a.b(0x61); a.b(0xC3)
    blobs.append(('tree_show', commit(a)))

    # ==================================================================
    # 11) tree_entry
    # ==================================================================
    entry_va = cur[0]
    a = new()
    a.b(0x60)
    a.callabs(resolve_va)
    a.callabs(log_va)
    logb(a, 0xE0)
    _ld(a, ctx['CARD_CUR'])
    a.b(0x85, 0xC0); a.jr32(0x84, 'noc')
    a.b(0x0F, 0xB7, 0x28)                                 # movzx ebp,word[eax] (S1 槽位)
    a.b(0x81, 0xFD); a.dw(1000)
    a.jr32(0x83, 'oob')
    _set(a, ctx['DYN_SLOT_VA'], 0)                          # 先清: 通用树只有在真拿到人才会填
    a.b(0x89, 0x2D); a.dw(ctx['DYN_SLOT_VA'])               # mov [dyn_slot],ebp (通用桩要这张卡的人)
    a.b(0x6B, 0xC5, 0x07)                                 # imul eax,ebp,7
    a.b(0x8B, 0x88); a.dw(0x520660)                       # mov ecx,[eax+名表]
    a.b(0x8B, 0x90); a.dw(0x521aa8)                       # mov edx,[eax+姓表]
    a.b(0xBE); a.dw(ctx['FAMDIR_VA'])
    a.b(0xBF); a.dw(ctx['NDIR'])
    a.label('dl')
    a.b(0x39, 0x0E); a.jr8(0x75, 'dn')                    # cmp [esi],ecx
    a.b(0x39, 0x56, 0x04); a.jr8(0x75, 'dn')              # cmp [esi+4],edx
    logb(a, 0xE3)
    a.jmpabs('found')
    a.label('dn')
    a.b(0x83, 0xC6, DIR_SZ); a.b(0x4F); a.jr8(0x75, 'dl')
    fb = ctx.get('FALLBACK_VA')
    gen = ctx.get('GENERIC_DIR_VA')
    if gen is not None:
        # 未命中 27 个史实家族: 有动态桩(.edata 在) -> 走运行时自建的「本人+子嗣」通用树;
        # 没桩(family.exe, 只到 .fdata) -> 仍回落柴田, 否则通用块是一片空白框。
        logb(a, 0xE6)
        _ld(a, ctx['DYN_FN_VA'])
        a.b(0x85, 0xC0); a.jr32(0x85, 'gen')              # 桩在 -> 通用树
    if fb is None:
        logb(a, 0xE5)
        a.jmpabs('out')
    else:
        logb(a, 0xE4)                                     # 未命中 -> 兜底(调试期=柴田)
        a.b(0xBE); a.dw(fb)
        a.jmpabs('found')
    if gen is not None:
        a.label('gen')
        a.b(0xBE); a.dw(gen)
        a.jmpabs('found')
    a.label('noc')
    logb(a, 0xE1)
    a.jmpabs('out')
    a.label('oob')
    logb(a, 0xE2)
    a.label('out')
    a.b(0x61); a.b(0xC3)
    a.label('found')
    a.b(0x89, 0x35); a.dw(RV + RS['FAMP'])                # mov [FAMP],esi
    # 动态点亮桩(build_big 写在 .edata 里): 复位 count=static_n -> 扫实体池 ->
    #   把「父亲=本人 且 儿童位图点亮」的人名写进池首可变姓名区, 并抬 count。
    #   ★ 必须先判空再 call: GDI 桩没落地时该 dword 是 0, call 0 = 当场 AV。
    _ld(a, ctx['DYN_FN_VA'])
    a.b(0x85, 0xC0); a.jr32(0x84, 'dyned')                # je 没桩 -> 直接开树(纯静态)
    a.b(0xFF, 0xD0)                                       # call eax
    a.label('dyned')
    logb(a, 0xE7)
    a.b(0x61)
    a.jmpabs(show_va)
    blobs.append(('tree_entry', commit(a)))
    return blobs, entry_va
