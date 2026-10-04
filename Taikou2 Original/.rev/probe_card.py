"""test_fam2.py — 实机验证家族族谱按钮 v3
流程: 启动 -> 开场动画(按 ESC 跳过, 不再改名禁用 AVI) -> 新游戏 -> 选主角
      -> 大地图 -> 开武将信息卡 -> 截图(基准) -> 悬停截图 -> 点击 -> 截图
截图用 ClientToScreen 得到的**真实客户区原点**, 便于和逻辑坐标精确对齐。

注意: OPENNING.AVI 必须保持原名存在于游戏目录, 本脚本通过按键跳过来加速,
      绝不移动/改名该文件(早期版本会 move 成 .tstb, 导致动画丢失)。
"""
import ctypes, os, struct, time, zlib, shutil, traceback
from ctypes import wintypes

k32 = ctypes.WinDLL('kernel32', use_last_error=True); u32 = ctypes.WinDLL('user32'); g32 = ctypes.WinDLL('gdi32')
k32.OpenProcess.restype = wintypes.HANDLE
k32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
k32.ReadProcessMemory.restype = wintypes.BOOL
k32.ReadProcessMemory.argtypes = [wintypes.HANDLE, wintypes.LPCVOID, wintypes.LPVOID,
                                  ctypes.c_size_t, ctypes.POINTER(ctypes.c_size_t)]
u32.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
u32.GetWindowThreadProcessId.restype = wintypes.DWORD
u32.EnumWindows.argtypes = [ctypes.c_void_p, wintypes.LPARAM]
u32.GetClientRect.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.RECT)]
u32.GetWindowRect.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.RECT)]

GAME = r'F:/Games/Taikou 2\Taikou2 Original'
EXE = os.path.join(GAME, 'TAIK2W95_familyb.exe')
AVI = os.path.join(GAME, 'OPENNING.AVI'); REV = os.path.join(GAME, '.rev')
TAG = os.environ.get('TAG', 'v3')
moved = []
G_IN, G_BTN_CX, G_BTN_CY, G_HIT, G_CLICK = 0x535F3C, 0x535E40, 0x535E44, 0x535F24, 0x535F20


class SI2(ctypes.Structure):
    _fields_ = [('cb', wintypes.DWORD), ('a', wintypes.LPVOID), ('b', wintypes.LPVOID), ('c', wintypes.LPVOID),
                ('x', wintypes.DWORD), ('y', wintypes.DWORD), ('xs', wintypes.DWORD), ('ys', wintypes.DWORD),
                ('x1', wintypes.DWORD), ('y1', wintypes.DWORD), ('fa', wintypes.DWORD), ('fl', wintypes.DWORD),
                ('sw', wintypes.WORD), ('r2', wintypes.WORD), ('r3', wintypes.LPVOID), ('h1', wintypes.HANDLE),
                ('h2', wintypes.HANDLE), ('h3', wintypes.HANDLE)]


class PI(ctypes.Structure):
    _fields_ = [('hp', wintypes.HANDLE), ('ht', wintypes.HANDLE), ('pid', wintypes.DWORD), ('tid', wintypes.DWORD)]


def wins(pid):
    out = []

    @ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)
    def cb(h, lp):
        p = wintypes.DWORD(); u32.GetWindowThreadProcessId(h, ctypes.byref(p))
        if p.value == pid and u32.IsWindowVisible(h):
            r = wintypes.RECT(); u32.GetClientRect(h, ctypes.byref(r)); out.append((h, r.right, r.bottom))
        return True
    u32.EnumWindows(cb, 0); return out


hp = hk = main = None
try:
    if (not os.path.exists(AVI)) and os.path.exists(AVI + '.tstb'):
        shutil.move(AVI + '.tstb', AVI); print('pre-restore OPENNING.AVI', flush=True)
    assert os.path.exists(AVI), 'OPENNING.AVI 缺失! 开场动画必须保留'
    print('OPENNING.AVI 存在 (%d bytes) -> 走按键跳过流程' % os.path.getsize(AVI), flush=True)
    si = SI2(); si.cb = ctypes.sizeof(si); pi = PI()
    k32.CreateProcessA(EXE.encode(), None, None, None, False, 0, None, GAME.encode(), ctypes.byref(si), ctypes.byref(pi))
    hp, pid = pi.hp, pi.pid; hk = k32.OpenProcess(0x1F0FFF, False, pid)

    def rd(va, n):
        b = ctypes.create_string_buffer(n); got = ctypes.c_size_t()
        if not k32.ReadProcessMemory(hk, ctypes.c_void_p(va), b, n, ctypes.byref(got)):
            return None
        return b.raw[:got.value]

    def g(va, n=4):
        d = rd(va, n)
        return struct.unpack('<I', d)[0] if d and len(d) == 4 else None

    def esc():
        u32.keybd_event(0x1B, 0, 0, 0); time.sleep(0.05); u32.keybd_event(0x1B, 0, 2, 0)

    t0 = time.time(); last = -1; stable = 0; skip_t = 0.0
    while time.time() - t0 < 90:
        for h, w, hh in wins(pid):
            if w >= 800:
                main = h
        d = rd(0x534040, 4); cnt = struct.unpack('<I', d)[0] if d else -1
        stable = stable + 1 if cnt == last else 0; last = cnt
        if cnt >= 71 and stable > 8 and main:
            break
        # 开场动画(KOEILOGO/OPENNING AVI)期间定期按 ESC 跳过
        if time.time() - skip_t > 1.2:
            skip_t = time.time()
            if main:
                u32.SetForegroundWindow(main)
            esc()
        time.sleep(0.4)
    print('present=%s main=%s' % (last, main), flush=True)
    u32.SetForegroundWindow(main); time.sleep(0.4)
    wr = wintypes.RECT(); u32.GetWindowRect(main, ctypes.byref(wr))
    cr = wintypes.RECT(); u32.GetClientRect(main, ctypes.byref(cr))
    CW, CH = cr.right, cr.bottom
    pt = wintypes.POINT(0, 0); u32.ClientToScreen(main, ctypes.byref(pt))
    CX0, CY0 = pt.x, pt.y
    print('client %dx%d @screen (%d,%d)  winrect=(%d,%d)' % (CW, CH, CX0, CY0, wr.left, wr.top), flush=True)

    def click(px, py, wait=0.8):
        u32.SetCursorPos(CX0 + px, CY0 + py); time.sleep(0.35)
        u32.mouse_event(2, 0, 0, 0, 0); time.sleep(0.10); u32.mouse_event(4, 0, 0, 0, 0); time.sleep(wait)

    def move(px, py):
        u32.SetCursorPos(CX0 + px, CY0 + py); time.sleep(0.25)

    def key(vk, wait=0.8):
        u32.keybd_event(vk, 0, 0, 0); time.sleep(0.06); u32.keybd_event(vk, 0, 2, 0); time.sleep(wait)

    def shot(tag):
        u32.SetForegroundWindow(main); time.sleep(0.25)
        dcv = u32.GetDC(0); mdc = g32.CreateCompatibleDC(dcv); bmp = g32.CreateCompatibleBitmap(dcv, CW, CH)
        g32.SelectObject(mdc, bmp); g32.BitBlt(mdc, 0, 0, CW, CH, dcv, CX0, CY0, 0x00CC0020)
        bi = struct.pack('<IiiHHIIiiII', 40, CW, -CH, 1, 24, 0, 0, 0, 0, 0, 0)
        buf = ctypes.create_string_buffer(CW * CH * 3)
        g32.GetDIBits(mdc, bmp, 0, CH, buf, ctypes.create_string_buffer(bi, len(bi)), 0)
        raw = b''.join(b'\x00' + buf.raw[y * CW * 3:(y + 1) * CW * 3] for y in range(CH))
        def ch(t, dd):
            c = t + dd
            return struct.pack('>I', len(dd)) + c + struct.pack('>I', zlib.crc32(c))
        png = (b'\x89PNG\r\n\x1a\n' + ch(b'IHDR', struct.pack('>IIBBBBB', CW, CH, 8, 2, 0, 0, 0))
               + ch(b'IDAT', zlib.compress(raw, 6)) + ch(b'IEND', b''))
        p = os.path.join(REV, 'f2_%s_%s.png' % (TAG, tag)); open(p, 'wb').write(png)
        print('  shot %-12s %7dB  BTN=(%s,%s) IN=%s CLICK=%s HIT=%s'
              % (tag, len(png), g(G_BTN_CX), g(G_BTN_CY), g(G_IN), g(G_CLICK), g(G_HIT)), flush=True)
        return p

    time.sleep(2.0); shot('00_title')
    click(545, 310, 2.0); shot('01_newgame')
    click(640, 415, 2.5); shot('02a')
    click(640, 415, 2.5); shot('02b')
    click(640, 415, 3.0); shot('02c')
    key(0x1B, 1.2); key(0x1B, 1.2); shot('03_map')

    def probe(tag, fx, fy, wait=1.8):
        px, py = int(CW*fx), int(CH*fy)
        click(px, py, wait)
        cc = g(0x514EE8); bx = g(G_BTN_CX)
        print('  %-12s click(%4d,%4d) CARD_CUR=0x%X BTN_CX=%s G_FAMILY=%s'
              % (tag, px, py, cc if cc else 0, bx, g(0x5354C0)), flush=True)
        shot('p_'+tag)
        return cc, bx

    print('=== 探索打开武将卡的路径 ===', flush=True)
    print('  初始 CARD_CUR=0x%X BTN_CX=%s' % (g(0x514EE8) or 0, g(G_BTN_CX)), flush=True)
    for tag, fx, fy in (('party',0.602,0.469), ('man_l',0.119,0.719), ('man_m',0.221,0.578),
                        ('castle',0.680,0.813), ('jouhou',0.924,0.933), ('kinou',0.760,0.933)):
        try:
            probe(tag, fx, fy)
        except Exception:
            print('  probe', tag, 'EXC', traceback.format_exc()[:200], flush=True)
        time.sleep(0.6)
except Exception:
    print('EXC', traceback.format_exc(), flush=True)
finally:
    for h in (hp, hk):
        try:
            if h:
                k32.TerminateProcess(h, 0)
        except Exception:
            pass
    for f in moved:
        if os.path.exists(f + '.tstb'):
            shutil.move(f + '.tstb', f)
    print('cleanup', flush=True)
