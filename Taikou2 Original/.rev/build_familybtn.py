"""
家族族谱 MOD v2 —— 在 TAIK2W95_zoom.exe 基础上打补丁, 生成 TAIK2W95_ft4.exe
(绝不改动原版 TAIK2W95.exe / TAIK2W95_zoom.exe / TAIK2W95_ft3.exe, 只读入并写出新文件)

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
  python build_familybtn.py --btn X,Y,W,H        (默认 24,234,88,16 = 面板左下角)
"""
import sys, struct, argparse

SRC = r'F:\Games\Taikou 2\Taikou2 Original\TAIK2W95_zoom.exe'
DST = r'F:\Games\Taikou 2\Taikou2 Original\TAIK2W95_ft4.exe'
DELTA = 0xC00                      # file offset = RVA - 0xC00
off_of = lambda rva: rva - DELTA

# ---------- 按钮几何(面板局部坐标, 命令行走 --btn X,Y,W,H 覆盖) ----------
_ap = argparse.ArgumentParser()
_ap.add_argument('--btn', default='24,98,96,24', help='按钮 面板局部 X,Y,W,H (默认 24,98,96,24)')
_ap.add_argument('--out', default=None, help='输出 exe 路径')
_ap.add_argument('--src', default=None, help='输入 zoom.exe 路径')
_ap.add_argument('--orig', default='160,83', help='信息卡绘制原点 逻辑坐标 LX,LY (默认 160,83)')
_args = _ap.parse_args()
_BX, _BY, _BW, _BH = (int(v) for v in _args.btn.split(','))
ORIGIN_LX, ORIGIN_LY = (int(v) for v in _args.orig.split(','))
if _args.src: SRC = _args.src
if _args.out: DST = _args.out

# ---------- 常量 ----------
CAVE_RVA = 0x135000
CAVE_VA  = 0x400000 + CAVE_RVA      # 0x535000
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
VASSAL_THUNK_VA= 0x535480           # 普通属下一页: 清 G_FAMILY 后 jmp 0x462d40
G_FAMILY       = 0x5354C0           # dword: 1=族谱绘制
STR_FMT3       = 0x5354D0           # "%s %s %s\0"
R_SELF   = 0x5354E0                 # "本人"
R_CHILD  = 0x5354F0                 # "子女"
R_FATHER = 0x535500                 # "父亲"
R35      = 0x535510                 # 柴田胜丰: "养子"
R38      = 0x535520                 # 佐久间盛政: "甥"
R42      = 0x535530                 # 佐久间安政: "姻戚"
R45      = R38                      # 佐久间正胜: "甥"
RELSTR   = 0x535600                 # dword[370]: builder 按行写入关系串地址

# ---------- 柴田一门内置(按“运行时姓名”匹配, 不按 id) ----------
SUR_BASE, GIV_BASE, NAME_STRIDE, NAME_RANGE = 0x520660, 0x521aa8, 7, 0x3e8
EBASE_END = EBASE + ECOUNT * ESTRIDE
TARGETS   = 0x535C00                # 洞内: 内置名单表, 5×(姓dword,名dword,关系串ptr)=60B
# 注意: SUR_BASE 实际是名表, GIV_BASE 实际是姓表 (与变量名相反!)
NAME_FAMILY = (
    (0xD2BCA4CA, 0xEFCCF1B2, R_SELF),   # 名=胜家, 姓=柴田  -> 柴田胜家  本人
    (0xA2CAC5D0, 0xDBD5A3C9, R42),      # 名=信盛, 姓=佐久间 -> 佐久间信盛 姻戚(义兄, 其子盛政为胜家之甥)
)
# 触发判定: 先比 0x520660(名表) 再比 0x521aa8(姓表)
# 注: 上一版把它们写反了(以为 SUR_BASE 是姓表), 且名单里的 柴田胜丰/佐久间盛政/安政/正胜
#     在 1560 年剧本的 370 实体里并不存在(实测全表只有 2 个 柴田/佐久间), 故只剩本人一行.
TRIG_SUR, TRIG_GIV = 0xD2BCA4CA, 0xEFCCF1B2   # 名=胜家, 姓=柴田

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
fb.jr8(0x73, 'nloop')                               # jae nloop
fb.b(0x6B, 0xC5, NAME_STRIDE)                       # imul eax,ebp,7
fb.b(0x05); fb.dw(SUR_BASE)                         # add eax,SUR_BASE
fb.b(0x81, 0x38); fb.dw(TRIG_SUR)                   # cmp dword[eax],"柴田"
fb.jr8(0x75, 'nloop')                               # jne nloop
fb.b(0x05); fb.dw(GIV_BASE - SUR_BASE)              # add eax,(名表-姓表)
fb.b(0x81, 0x38); fb.dw(TRIG_GIV)                   # cmp dword[eax],"胜家"
fb.jr8(0x75, 'nloop')                               # jne nloop
fb.jmpabs('shib')

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
fb.label('nskip')
fb.b(0x83, 0xC2, 0x2F)                             # add edx,47
fb.b(0x49)                                         # dec ecx
fb.jr8(0x75, 'nloop')
fb.b(0x8B, 0xC6)                                   # mov eax,esi
fb.jmpabs('end')

fb.label('shib')
fb.b(0xBA); fb.dw(EBASE)
fb.label('sloop')
fb.b(0x81, 0xFA); fb.dw(EBASE_END)                  # cmp edx,EBASE_END
fb.jr8(0x73, 'send')
fb.b(0x0F, 0xB7, 0x42, 0x00)                        # movzx eax,[edx+0]
fb.b(0x3D); fb.dw(NAME_RANGE)                       # cmp eax,0x3e8
fb.jr8(0x73, 'sskip')
fb.b(0x6B, 0xC0, NAME_STRIDE)                       # imul eax,7
fb.b(0x8D, 0x98); fb.dw(SUR_BASE)                  # lea ebx,[eax+SUR_BASE]
fb.b(0x8D, 0xA8); fb.dw(GIV_BASE)                  # lea ebp,[eax+GIV_BASE]
fb.b(0xBF); fb.dw(TARGETS)                          # mov edi,TARGETS
fb.b(0xB9); fb.dw(len(NAME_FAMILY))                # mov ecx,5
fb.label('tloop')
fb.b(0x8B, 0x07)                                   # mov eax,[edi]
fb.b(0x39, 0x03)                                   # cmp [ebx],eax
fb.jr8(0x75, 'next')
fb.b(0x8B, 0x47, 0x04)                             # mov eax,[edi+4]
fb.b(0x39, 0x45, 0x00)                             # cmp [ebp],eax
fb.jr8(0x75, 'next')
fb.b(0x8B, 0x47, 0x08)                             # mov eax,[edi+8]
fb.jr8(0xEB, 'found')
fb.label('next')
fb.b(0x83, 0xC7, 12)                               # add edi,12
fb.b(0x49)
fb.jr8(0x75, 'tloop')
fb.jr8(0xEB, 'sskip')
fb.label('found')
fb.b(0x8B, 0x1D); fb.dw(LISTBUF)
fb.b(0x89, 0x14, 0xB3)
fb.b(0xBB); fb.dw(RELSTR)
fb.b(0x89, 0x04, 0xB3)
fb.b(0x46)
fb.label('sskip')
fb.b(0x83, 0xC2, ESTRIDE)
fb.jr8(0xEB, 'sloop')
fb.label('send')
fb.b(0x8B, 0xC6)
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
HIT_PAD = 3                                        # 命中框比文字框各向外扩 3px(容错)
HIT_W, HIT_H = BTN_W + 2 * HIT_PAD, BTN_H + 2 * HIT_PAD
# 局部坐标系实测锚点: 能力块 SetRect(0x18,0x7a,0x58,0x78) = (24,122,88,120),
#                     信赖度 SetRect(0x18,0xfa,0x118,0x18) = (24,250,280,24)
# 按钮放在「部将」正下方 (局部 245,57)
G_LBDOWN  = 0x535EE0    # dword: WM_LBUTTONDOWN 累计次数(游戏 WndProc 里 inc)
G_LBSEEN  = 0x535EE4    # dword: ft_click 已消费到哪一次
G_LBPREV  = 0x535EE8    # dword: 轮询式边沿检测的上一状态
G_LOOPCNT = 0x535EEC    # dword: 诊断——信息卡消息循环转了多少圈

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
d.label('skip')
d.b(0x8B, 0xCE)                              # mov ecx,esi
d.callabs(FLUSH_FN)                          # 原指令: call 0x403cd0
d.b(0x5F, 0x5D, 0x5B, 0x5A, 0x59, 0x58)      # pop edi,ebp,ebx,edx,ecx,eax
d.b(0x5F, 0x5E, 0x5B)                        # 原收尾: pop edi,esi,ebx
d.b(0x83, 0xC4, 0x5C)                        # add esp,0x5c
d.b(0xC3)                                    # ret
btn_draw = d.resolve()
assert (BTN_DRAW_VA - CAVE_VA) + len(btn_draw) <= (TILE_TAB - CAVE_VA), 'ft_btn_draw 撞 TILE_TAB'

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
n.callabs(CAVE_VA)                           # call family_entry
n.b(0x61)                                    # popad
n.jr8(0xEB, 'skip')                          # jmp skip
n.label('tryf9')
n.callabs(KBD_VA)                            # F9 备用
n.b(0x85, 0xC0)
n.jr8(0x74, 'skip')
n.b(0x60)
n.callabs(CAVE_VA)
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
_tg = bytearray()
for _s, _g, _r in NAME_FAMILY:
    _tg += struct.pack('<III', _s, _g, _r)
put(TARGETS, bytes(_tg))

for chk_va, chk_sz in ((G_GS, 5), (G_FAMILY, 4), (G_BTN_CX, 0x38), (G_LBDOWN, 0x10), (0x535F10, 0x70)):
    assert bytes(cave[chk_va - CAVE_VA:chk_va - CAVE_VA + chk_sz]) == b'\0' * chk_sz, 'globals 区非零 %06X' % chk_va
fo = off_of(CAVE_RVA)
b = bytearray(open(SRC, 'rb').read())
assert b[fo:fo + CAVE_SIZE] == bytes(CAVE_SIZE), '洞区非全零(已被占用): off=%X' % fo
b[fo:fo + CAVE_SIZE] = cave
print('OK  洞 @RVA %06X entry=%06X builder=%06X kbd=%06X nav=%06X click=%06X btndraw=%06X (%dB)'
      % (CAVE_RVA, CAVE_VA, builder_va, KBD_VA, NAV_VA, CLICK_VA, BTN_DRAW_VA, len(btn_draw)))
print('OK  按钮文字 面板局部(%d,%d) %dx%d  "家族族谱"  命中框 逻辑(%d,%d) %dx%d' % (BTN_X, BTN_Y, BTN_W, BTN_H, ORIGIN_LX+BTN_X-HIT_PAD, ORIGIN_LY+BTN_Y-HIT_PAD, HIT_W, HIT_H))

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
    roundtrip('ft_click', CLICK_VA, click)
    roundtrip('ft_btn_draw', BTN_DRAW_VA, btn_draw)
    roundtrip('family_builder', builder_va, body)
    roundtrip('ft_paint', FT_PAINT_VA, paint)
    roundtrip('vassal_thunk', VASSAL_THUNK_VA, thunk)
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

# ---------- 挂钩调查卡循环头 ----------
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

try:
    open(DST, 'wb').write(bytes(b))
    out = DST
except PermissionError:
    out = DST[:-4] + 'b.exe'
    open(out, 'wb').write(bytes(b))
print('\n已生成:', out, len(b), '字节')
