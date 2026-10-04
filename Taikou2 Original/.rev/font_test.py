"""font_test.py — 对照实验: 到底是「字体没建出来」还是「我的汇编有问题」

在同一个游戏窗口 DC 上, 用 Python 走两条路径各画一遍中文:
    A. 不选字体(用 DC 自带默认字体) + 中文
    B. CreateFontA(宋体, -20, GB2312_CHARSET) -> SelectObject -> 中文
    C. CreateFontA(宋体, -20, DEFAULT_CHARSET)
    D. CreateFontA("SimSun", -20, DEFAULT_CHARSET)
    E. CreateFontA(宋体, -20, GB2312) 但用 SetTextAlign(TA_CENTER)
截图后放大看哪几行有字 —— 有字的那条路径就是能用的写法。
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
u32.GetDC.restype = wintypes.HDC
u32.GetDC.argtypes = [wintypes.HWND]
u32.ReleaseDC.argtypes = [wintypes.HWND, wintypes.HDC]

g32.CreateSolidBrush.restype = wintypes.HANDLE
g32.CreateSolidBrush.argtypes = [wintypes.DWORD]
g32.CreateFontA.restype = wintypes.HANDLE
g32.CreateFontA.argtypes = [ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int,
                            ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int,
                            ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_char_p]
g32.SelectObject.restype = wintypes.HANDLE
g32.SelectObject.argtypes = [wintypes.HDC, wintypes.HANDLE]
g32.Rectangle.argtypes = [wintypes.HDC, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int]
g32.SetTextColor.argtypes = [wintypes.HDC, wintypes.DWORD]
g32.SetBkMode.argtypes = [wintypes.HDC, ctypes.c_int]
g32.SetTextAlign.argtypes = [wintypes.HDC, ctypes.c_uint]
g32.TextOutA.argtypes = [wintypes.HDC, ctypes.c_int, ctypes.c_int, ctypes.c_char_p, ctypes.c_int]
g32.GetObjectA.argtypes = [wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p]
g32.CreateCompatibleDC.restype = wintypes.HDC
g32.CreateCompatibleDC.argtypes = [wintypes.HDC]
g32.CreateCompatibleBitmap.restype = wintypes.HANDLE
g32.CreateCompatibleBitmap.argtypes = [wintypes.HDC, ctypes.c_int, ctypes.c_int]
g32.BitBlt.argtypes = [wintypes.HDC, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int,
                       wintypes.HDC, ctypes.c_int, ctypes.c_int, wintypes.DWORD]
g32.GetDIBits.argtypes = [wintypes.HDC, wintypes.HANDLE, ctypes.c_uint, ctypes.c_uint,
                          ctypes.c_void_p, ctypes.c_void_p, ctypes.c_uint]

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


class LOGFONT(ctypes.Structure):
    _fields_ = [('lfHeight', ctypes.c_long), ('lfWidth', ctypes.c_long),
                ('lfEscapement', ctypes.c_long), ('lfOrientation', ctypes.c_long),
                ('lfWeight', ctypes.c_long), ('lfItalic', ctypes.c_ubyte),
                ('lfUnderline', ctypes.c_ubyte), ('lfStrikeOut', ctypes.c_ubyte),
                ('lfCharSet', ctypes.c_ubyte), ('lfOutPrecision', ctypes.c_ubyte),
                ('lfClipPrecision', ctypes.c_ubyte), ('lfQuality', ctypes.c_ubyte),
                ('lfPitchAndFamily', ctypes.c_ubyte), ('lfFaceName', ctypes.c_char * 32)]


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
    print('pid=%d' % pid, flush=True)

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
    u32.SetForegroundWindow(main); time.sleep(0.4)
    cr = wintypes.RECT(); u32.GetClientRect(main, ctypes.byref(cr))
    CW, CH = cr.right, cr.bottom
    pt = wintypes.POINT(0, 0); u32.ClientToScreen(main, ctypes.byref(pt))
    CX0, CY0 = pt.x, pt.y
    print('client %dx%d @ (%d,%d)' % (CW, CH, CX0, CY0), flush=True)

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
        p = os.path.join(REV, 'ft_%s.png' % tag); open(p, 'wb').write(png)
        print('  shot %s' % p, flush=True)
        return p

    hdc = u32.GetDC(main)
    print('hdc = 0x%X' % (hdc or 0), flush=True)
    # 底色: 深蓝面板 + 亮底条, 让黑字/白字都能验出来
    bg = g32.CreateSolidBrush(0x00281E14)
    oldb = g32.SelectObject(hdc, bg)
    g32.Rectangle(hdc, 200, 120, 1080, 620)
    g32.SelectObject(hdc, oldb)

    C1 = '柴田胜家'                       # 要画的中文
    C2 = 'ABC abc 123'                    # ASCII 对照
    rows = []
    fs = []

    def draw(y, font, text, align=0, label=''):
        g32.SetBkMode(hdc, 1)
        g32.SetTextColor(hdc, 0x00FFFFFF)
        if font:
            g32.SelectObject(hdc, font)
        g32.SetTextAlign(hdc, align)
        t = text.encode('gbk') if isinstance(text, str) else text
        x = 640 if align == 6 else 220
        r = g32.TextOutA(hdc, x, y, t, -1)
        rows.append((y, label, r))
        print('   y=%-4d align=%d  %-28s TextOutA->%s' % (y, align, label, r), flush=True)

    # A: 默认字体
    draw(140, None, C2, 0, 'A 默认字体 ASCII')
    draw(170, None, C1, 0, 'B 默认字体 中文')
    # C: 宋体 + GB2312
    for name, cs, y, lab in ((b'\xcb\xce\xcc\xe5', 134, 210, 'C 宋体/GB2312'),
                             (b'\xcb\xce\xcc\xe5', 1, 245, 'D 宋体/DEFAULT'),
                             (b'SimSun', 1, 280, 'E SimSun/DEFAULT'),
                             (b'\xcb\xce\xcc\xe5', 134, 315, 'F 宋体/GB2312 居中')):
        h = g32.CreateFontA(-20, 0, 0, 0, 400, 0, 0, 0, cs, 0, 0, 0, 0, name)
        lf = LOGFONT(); g32.GetObjectA(h, ctypes.sizeof(LOGFONT), ctypes.byref(lf))
        fs.append(h)
        print('   CreateFontA %-14s -> 0x%X  lfHeight=%d face=%r charset=%d'
              % (lab, h or 0, lf.lfHeight, lf.lfFaceName.rstrip(b'\x00'), lf.lfCharSet), flush=True)
        draw(y, h, C1 + ' / ' + C2, align=(6 if '居中' in lab else 0), label=lab)

    # 复位到默认字体
    g32.SelectObject(hdc, g32.GetStockObject(13))     # DEFAULT_GUI_FONT
    time.sleep(0.6)
    shot('00_all')
    u32.ReleaseDC(main, hdc)
finally:
    try:
        if hp:
            k32.TerminateProcess(hp, 0)
    except Exception:
        pass
    print('cleanup', flush=True)
