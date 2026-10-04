"""gdi_probe.py — 关键可行性实验: 能否在游戏窗口上用 GDI 自绘?

背景: 用户要求把家族树做成「树形图形界面」(参考信长之野望·大志)。
      游戏原生 UI 是 tile 拼的, 没有通用填充矩形/画线 API, 故考虑 GDI 自绘。
      但前提是: **游戏的重绘不会立刻把 GDI 画的内容擦掉**。

流程: 启动 -> 跳过开场动画 -> 新游戏 -> 大地图 -> GetDC(窗口) 画框/线/字
      -> 立刻截图, 1.2s 后截图, 2.4s 后截图 (对比是否被擦)
"""
import ctypes, os, struct, time, zlib, shutil
from ctypes import wintypes

k32 = ctypes.WinDLL('kernel32', use_last_error=True)
u32 = ctypes.WinDLL('user32')
g32 = ctypes.WinDLL('gdi32')
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
u32.GetDC.restype = wintypes.HDC
u32.GetDC.argtypes = [wintypes.HWND]
u32.ReleaseDC.argtypes = [wintypes.HWND, wintypes.HDC]
g32.CreatePen.restype = wintypes.HANDLE
g32.CreatePen.argtypes = [ctypes.c_int, ctypes.c_int, wintypes.DWORD]
g32.SelectObject.restype = wintypes.HANDLE
g32.SelectObject.argtypes = [wintypes.HDC, wintypes.HANDLE]
g32.Rectangle.argtypes = [wintypes.HDC, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int]
g32.MoveToEx.argtypes = [wintypes.HDC, ctypes.c_int, ctypes.c_int, ctypes.c_void_p]
g32.LineTo.argtypes = [wintypes.HDC, ctypes.c_int, ctypes.c_int]
g32.SetTextColor.argtypes = [wintypes.HDC, wintypes.DWORD]
g32.SetBkMode.argtypes = [wintypes.HDC, ctypes.c_int]
g32.TextOutA.argtypes = [wintypes.HDC, ctypes.c_int, ctypes.c_int, ctypes.c_char_p, ctypes.c_int]
g32.Ellipse.argtypes = [wintypes.HDC, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int]
# 抓图相关: 必须声明 argtypes, 否则 64 位 HDC 会被当 int 溢出
g32.CreateCompatibleDC.restype = wintypes.HDC
g32.CreateCompatibleDC.argtypes = [wintypes.HDC]
g32.CreateCompatibleBitmap.restype = wintypes.HANDLE
g32.CreateCompatibleBitmap.argtypes = [wintypes.HDC, ctypes.c_int, ctypes.c_int]
g32.BitBlt.argtypes = [wintypes.HDC, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int,
                       wintypes.HDC, ctypes.c_int, ctypes.c_int, wintypes.DWORD]
g32.GetDIBits.argtypes = [wintypes.HDC, wintypes.HANDLE, ctypes.c_uint, ctypes.c_uint,
                          ctypes.c_void_p, ctypes.c_void_p, ctypes.c_uint]

GAME = r'F:/Games/Taikou 2\Taikou2 Original'
EXE = os.path.join(GAME, 'TAIK2W95_family.exe')
AVI = os.path.join(GAME, 'OPENNING.AVI')
REV = os.path.join(GAME, '.rev')
TAG = os.environ.get('TAG', 'g')
G_BTN_CX, G_BTN_CY = 0x535E40, 0x535E44


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
    assert os.path.exists(AVI), 'OPENNING.AVI 缺失'
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
    print('client %dx%d @screen(%d,%d)' % (CW, CH, CX0, CY0), flush=True)

    def click(px, py, wait=0.8):
        u32.SetCursorPos(CX0 + px, CY0 + py); time.sleep(0.35)
        u32.mouse_event(2, 0, 0, 0, 0); time.sleep(0.10); u32.mouse_event(4, 0, 0, 0, 0); time.sleep(wait)

    def key(vk, wait=0.8):
        u32.keybd_event(vk, 0, 0, 0); time.sleep(0.06); u32.keybd_event(vk, 0, 2, 0); time.sleep(wait)

    def shot(tag):
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
        p = os.path.join(REV, 'gp_%s_%s.png' % (TAG, tag)); open(p, 'wb').write(png)
        print('  shot %-14s BTN=(%s,%s)' % (tag, g(G_BTN_CX), g(G_BTN_CY)), flush=True)
        return p

    # ---- 走到大地图 ----
    time.sleep(2.0); shot('00_title')
    click(545, 310, 2.0)
    click(640, 415, 2.5); click(640, 415, 2.5); click(640, 415, 3.0)
    key(0x1B, 1.2); key(0x1B, 1.2); shot('01_map')

    # ---- GDI 实验 ----
    print('=== GDI 自绘实验 ===', flush=True)
    hdc = u32.GetDC(main)
    print('  GetDC -> 0x%X' % (hdc or 0), flush=True)
    pen = g32.CreatePen(0, 4, 0x0000FF)          # 粗红笔 (COLORREF = 0x00BBGGRR)
    old = g32.SelectObject(hdc, pen)
    g32.Rectangle(hdc, 100, 100, 900, 620)
    g32.SelectObject(hdc, g32.CreatePen(0, 2, 0x00FF00))   # 绿笔
    g32.MoveToEx(hdc, 100, 400, None); g32.LineTo(hdc, 900, 400)
    g32.MoveToEx(hdc, 500, 100, None); g32.LineTo(hdc, 500, 620)
    g32.SelectObject(hdc, g32.CreatePen(0, 2, 0x00FFFF))   # 黄笔
    g32.Ellipse(hdc, 380, 300, 480, 400)
    g32.SetBkMode(hdc, 1)                        # TRANSPARENT
    g32.SetTextColor(hdc, 0x00FFFFFF)            # 白字
    g32.TextOutA(hdc, 150, 150, b'GDI PROBE: rect+line+ellipse+text', 33)
    g32.SelectObject(hdc, old)
    shot('02_gdi_now')
    time.sleep(1.2); shot('03_gdi_1s2')
    time.sleep(1.2)
    # 移动一下鼠标(制造游戏重绘)再截
    u32.SetCursorPos(CX0 + 1000, CY0 + 400); time.sleep(1.0)
    shot('04_gdi_aftermove')
    u32.ReleaseDC(main, hdc)
    print('done', flush=True)
except Exception:
    import traceback
    print('EXC', traceback.format_exc(), flush=True)
finally:
    for h in (hp, hk):
        try:
            if h:
                k32.TerminateProcess(h, 0)
        except Exception:
            pass
    print('cleanup', flush=True)
