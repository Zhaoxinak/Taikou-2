"""font_test2.py — 追查 TextOutA 为何返回 0

已确认: 在游戏窗口 DC 上 Rectangle/Ellipse/LineTo 能画, 但 TextOutA **返回 0**。
本脚本逐项排查:
  1. GetLastError（窗口 DC 上失败的真实原因）
  2. GetDeviceCaps(TEXTCAPS) / GetCurrentObject(OBJ_FONT) / GetTextFaceA
     —— 该 DC 到底有没有字体、支不支持文字输出
  3. ExtTextOutA / DrawTextA / TextOutW 是否同样失败
  4. 在**内存 DC**(CreateCompatibleDC + 位图)上画字是否成功
     —— 若成功, 说明问题只出在窗口 DC, 解法是「离屏画好再 BitBlt」
"""
import ctypes, os, struct, time, zlib
from ctypes import wintypes

k32 = ctypes.WinDLL('kernel32', use_last_error=True)
u32 = ctypes.WinDLL('user32')
g32 = ctypes.WinDLL('gdi32')

k32.OpenProcess.restype = wintypes.HANDLE
k32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
k32.ReadProcessMemory.restype = wintypes.BOOL
k32.ReadProcessMemory.argtypes = [wintypes.HANDLE, wintypes.LPCVOID, wintypes.LPVOID,
                                  ctypes.c_size_t, ctypes.POINTER(ctypes.c_size_t)]
u32.EnumWindows.argtypes = [ctypes.c_void_p, wintypes.LPARAM]
u32.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
u32.GetWindowThreadProcessId.restype = wintypes.DWORD
u32.GetClientRect.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.RECT)]
for f in ('GetDC', 'CreateCompatibleDC'):
    getattr(u32 if f == 'GetDC' else g32, f).restype = wintypes.HDC
u32.GetDC.argtypes = [wintypes.HWND]
g32.CreateCompatibleDC.argtypes = [wintypes.HDC]
g32.CreateCompatibleBitmap.restype = wintypes.HANDLE
g32.CreateCompatibleBitmap.argtypes = [wintypes.HDC, ctypes.c_int, ctypes.c_int]
g32.SelectObject.restype = wintypes.HANDLE
g32.SelectObject.argtypes = [wintypes.HDC, wintypes.HANDLE]
g32.GetCurrentObject.restype = wintypes.HANDLE
g32.GetCurrentObject.argtypes = [wintypes.HDC, ctypes.c_uint]
g32.GetDeviceCaps.argtypes = [wintypes.HDC, ctypes.c_int]
g32.GetTextFaceA.argtypes = [wintypes.HDC, ctypes.c_int, ctypes.c_char_p]
g32.TextOutA.argtypes = [wintypes.HDC, ctypes.c_int, ctypes.c_int, ctypes.c_char_p, ctypes.c_int]
g32.TextOutW.argtypes = [wintypes.HDC, ctypes.c_int, ctypes.c_int, ctypes.c_wchar_p, ctypes.c_int]
g32.ExtTextOutA.argtypes = [wintypes.HDC, ctypes.c_int, ctypes.c_int, ctypes.c_uint,
                            ctypes.c_void_p, ctypes.c_char_p, ctypes.c_uint, ctypes.c_void_p]
u32.DrawTextA.argtypes = [wintypes.HDC, ctypes.c_char_p, ctypes.c_int, ctypes.c_void_p, ctypes.c_uint]
g32.SetTextColor.argtypes = [wintypes.HDC, wintypes.DWORD]
g32.SetBkMode.argtypes = [wintypes.HDC, ctypes.c_int]
g32.Rectangle.argtypes = [wintypes.HDC, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int]
g32.BitBlt.argtypes = [wintypes.HDC, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int,
                       wintypes.HDC, ctypes.c_int, ctypes.c_int, wintypes.DWORD]
g32.GetDIBits.argtypes = [wintypes.HDC, wintypes.HANDLE, ctypes.c_uint, ctypes.c_uint,
                          ctypes.c_void_p, ctypes.c_void_p, ctypes.c_uint]
g32.GetStockObject.restype = wintypes.HANDLE
g32.GetStockObject.argtypes = [ctypes.c_int]

GAME = r'F:\Games\Taikou 2\Taikou2 Original'
EXE = os.path.join(GAME, 'TAIK2W95_family.exe')
REV = os.path.join(GAME, '.rev')


class SI2(ctypes.Structure):
    _fields_ = [('cb', wintypes.DWORD), ('a', wintypes.LPVOID), ('b', wintypes.LPVOID), ('c', wintypes.LPVOID),
                ('x', wintypes.DWORD), ('y', wintypes.DWORD), ('xs', wintypes.DWORD), ('ys', wintypes.DWORD),
                ('x1', wintypes.DWORD), ('y1', wintypes.DWORD), ('fa', wintypes.DWORD), ('fl', wintypes.DWORD),
                ('sw', wintypes.WORD), ('r2', wintypes.WORD), ('r3', wintypes.LPVOID), ('h1', wintypes.HANDLE),
                ('h2', wintypes.HANDLE), ('h3', wintypes.HANDLE)]


class PI(ctypes.Structure):
    _fields_ = [('hp', wintypes.HANDLE), ('ht', wintypes.HANDLE),
                ('pid', wintypes.DWORD), ('tid', wintypes.DWORD)]


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
    si = SI2(); si.cb = ctypes.sizeof(si); pi = PI()
    assert k32.CreateProcessA(EXE.encode(), None, None, None, False, 0, None,
                              GAME.encode(), ctypes.byref(si), ctypes.byref(pi))
    hp, pid = pi.hp, pi.pid
    hk = k32.OpenProcess(0x1F0FFF, False, pid)

    def rd(va, n):
        b = ctypes.create_string_buffer(n); got = ctypes.c_size_t()
        if not k32.ReadProcessMemory(hk, ctypes.c_void_p(va), b, n, ctypes.byref(got)):
            return None
        return b.raw[:got.value]

    def esc():
        u32.keybd_event(0x1B, 0, 0, 0); time.sleep(0.05); u32.keybd_event(0x1B, 0, 2, 0)

    t0 = time.time(); last = -1; stable = 0; sk = 0.0
    while time.time() - t0 < 60:
        for h, w, hh in wins(pid):
            if w >= 800:
                main = h
        d = rd(0x534040, 4); cnt = struct.unpack('<I', d)[0] if d else -1
        stable = stable + 1 if cnt == last else 0; last = cnt
        if cnt >= 71 and stable > 8 and main:
            break
        if time.time() - sk > 1.2:
            sk = time.time()
            if main:
                u32.SetForegroundWindow(main)
            esc()
        time.sleep(0.4)
    assert main, '主窗口未找到'
    cr = wintypes.RECT(); u32.GetClientRect(main, ctypes.byref(cr))
    CW, CH = cr.right, cr.bottom
    pt = wintypes.POINT(0, 0); u32.ClientToScreen(main, ctypes.byref(pt))
    CX0, CY0 = pt.x, pt.y

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
        p = os.path.join(REV, 'ft2_%s.png' % tag); open(p, 'wb').write(png)
        return p

    def le(tag):
        return '%s err=%d' % (tag, ctypes.get_last_error())

    hdc = u32.GetDC(main)
    print('窗口 DC = 0x%X   client %dx%d' % (hdc or 0, CW, CH), flush=True)

    print('--- 窗口 DC 能力 ---', flush=True)
    print('   TEXTCAPS(34)   = 0x%X' % g32.GetDeviceCaps(hdc, 34), flush=True)
    print('   BITSPIXEL(12)  = %d' % g32.GetDeviceCaps(hdc, 12), flush=True)
    print('   TECHNOLOGY(2)  = %d  (0=RASTER 1=VECTOR 2=TRUETYPE...)' % g32.GetDeviceCaps(hdc, 2), flush=True)
    for oid, nm in ((6, 'FONT'), (7, 'BRUSH'), (8, 'PEN')):
        print('   GetCurrentObject(%-5s)= 0x%X' % (nm, g32.GetCurrentObject(hdc, oid) or 0), flush=True)
    face = ctypes.create_string_buffer(64)
    n = g32.GetTextFaceA(hdc, 64, face)
    print('   GetTextFaceA -> %d  %r' % (n, face.value), flush=True)

    print('--- 窗口 DC 文字输出尝试 ---', flush=True)
    ctypes.set_last_error(0)
    r = g32.TextOutA(hdc, 220, 140, b'ABC abc 123', -1)
    print('   TextOutA  ascii  -> %s  %s' % (r, le('')), flush=True)
    ctypes.set_last_error(0)
    r = g32.TextOutA(hdc, 220, 170, '柴田胜家'.encode('gbk'), -1)
    print('   TextOutA  gbk    -> %s  %s' % (r, le('')), flush=True)
    ctypes.set_last_error(0)
    r = g32.TextOutW(hdc, 220, 200, '柴田胜家', -1)
    print('   TextOutW  wide   -> %s  %s' % (r, le('')), flush=True)
    ctypes.set_last_error(0)
    r = g32.ExtTextOutA(hdc, 220, 230, 0, None, b'ABC abc 123', 11, None)
    print('   ExtTextOutA      -> %s  %s' % (r, le('')), flush=True)
    ctypes.set_last_error(0)
    rc = struct.pack('<iiii', 220, 260, 700, 290)
    r = u32.DrawTextA(hdc, b'ABC abc 123', 11, ctypes.create_string_buffer(rc, 16), 0)
    print('   DrawTextA        -> %s  %s' % (r, le('')), flush=True)

    print('--- 内存 DC 对照(在 Python 进程内建位图, 同进程 GDI 句柄有效) ---', flush=True)
    dcv = u32.GetDC(0)
    mdc = g32.CreateCompatibleDC(dcv)
    bmp = g32.CreateCompatibleBitmap(dcv, 640, 240)
    g32.SelectObject(mdc, bmp)
    g32.SetBkMode(mdc, 1)
    g32.SetTextColor(mdc, 0x00000000)
    fnt = g32.CreateFontA(-20, 0, 0, 0, 400, 0, 0, 0, 134, 0, 0, 0, 0, '宋体'.encode('gbk'))
    g32.SelectObject(mdc, fnt)
    ctypes.set_last_error(0)
    r1 = g32.TextOutA(mdc, 10, 10, '柴田胜家'.encode('gbk'), -1)
    print('   内存DC 宋体/GB2312 中文 -> %s  %s' % (r1, le('')), flush=True)
    ctypes.set_last_error(0)
    r2 = g32.TextOutA(mdc, 10, 45, b'ABC abc 123', -1)
    print('   内存DC 宋体 ASCII      -> %s  %s' % (r2, le('')), flush=True)
    # 把内存 DC 内容贴到游戏窗口, 看是否可见
    g32.BitBlt(hdc, 300, 400, 640, 240, mdc, 0, 0, 0x00CC0020)
    time.sleep(0.5)
    p = shot('00_all')
    print('   shot %s' % p, flush=True)
finally:
    try:
        if hp:
            k32.TerminateProcess(hp, 0)
    except Exception:
        pass
    print('cleanup', flush=True)
