"""观察模式: 启动后按时间点截图(不点击), 用于判断开场动画是否播放"""
import ctypes, struct, sys, time, os, zlib
from ctypes import wintypes

k32 = ctypes.WinDLL('kernel32', use_last_error=True)
u32 = ctypes.WinDLL('user32')
g32 = ctypes.WinDLL('gdi32')

class SI2(ctypes.Structure):
    _fields_ = [('cb', wintypes.DWORD)] + [('pad%d' % i, wintypes.LPVOID) for i in range(3)] + \
               [('dwX', wintypes.DWORD), ('dwY', wintypes.DWORD), ('dwXSize', wintypes.DWORD),
                ('dwYSize', wintypes.DWORD), ('dwXCountChars', wintypes.DWORD),
                ('dwYCountChars', wintypes.DWORD), ('dwFillAttribute', wintypes.DWORD),
                ('dwFlags', wintypes.DWORD), ('wShowWindow', wintypes.WORD),
                ('cbReserved2', wintypes.WORD), ('lpReserved2', wintypes.LPVOID),
                ('hStdInput', wintypes.HANDLE), ('hStdOutput', wintypes.HANDLE),
                ('hStdError', wintypes.HANDLE)]
class PI(ctypes.Structure):
    _fields_ = [('hProcess', wintypes.HANDLE), ('hThread', wintypes.HANDLE),
                ('dwProcessId', wintypes.DWORD), ('dwThreadId', wintypes.DWORD)]

TAG = sys.argv[1]                      # 输出前缀
TIMES = [float(x) for x in sys.argv[2:]] or [8, 25, 49]
EXE = r'F:\Games\Taikou 2\Taikou2 Original\TAIK2W95_zoom.exe'
si = SI2(); si.cb = ctypes.sizeof(si); pi = PI()
ok = k32.CreateProcessA(EXE.encode(), None, None, None, False, 0, None,
                        os.path.dirname(EXE).encode(), ctypes.byref(si), ctypes.byref(pi))
print('pid', pi.dwProcessId, flush=True)
hp, pid = pi.hProcess, pi.dwProcessId

def rd(va, n):
    b = ctypes.create_string_buffer(n); got = ctypes.c_size_t()
    if not k32.ReadProcessMemory(hp, ctypes.c_void_p(va), b, n, ctypes.byref(got)): return None
    return b.raw[:got.value]

def find_win():
    found = []
    @ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)
    def cb(h, lp):
        p = wintypes.DWORD(); u32.GetWindowThreadProcessId(h, ctypes.byref(p))
        if p.value == pid:
            b = ctypes.create_unicode_buffer(64); u32.GetWindowTextW(h, b, 64)
            cls = ctypes.create_unicode_buffer(64); u32.GetClassNameW(h, cls, 64)
            if u32.IsWindowVisible(h):
                found.append((h, b.value, cls.value))
        return True
    u32.EnumWindows(cb, 0)
    print('  可见窗口:', [(t, c) for _, t, c in found], flush=True)
    best, ba = None, -1
    for h0, t, c in found:
        r0 = wintypes.RECT(); u32.GetClientRect(h0, ctypes.byref(r0))
        if r0.right*r0.bottom > ba: ba = r0.right*r0.bottom; best = h0
    return best

def shot(tag, hwnd):
    if not hwnd: return
    r = wintypes.RECT(); u32.GetClientRect(hwnd, ctypes.byref(r))
    w, hh = r.right, r.bottom
    wr = wintypes.RECT(); u32.GetWindowRect(hwnd, ctypes.byref(wr))
    hdcW = u32.GetDC(0)
    mdc = g32.CreateCompatibleDC(hdcW); bmp = g32.CreateCompatibleBitmap(hdcW, w, hh)
    g32.SelectObject(mdc, bmp)
    g32.BitBlt(mdc, 0, 0, w, hh, hdcW, wr.left, wr.top, 0x00CC0020)
    bi = struct.pack('<IiiHHIIiiII', 40, w, -hh, 1, 24, 0, 0, 0, 0, 0, 0)
    buf = ctypes.create_string_buffer(w*hh*3)
    g32.GetDIBits(mdc, bmp, 0, hh, buf, ctypes.create_string_buffer(bi, len(bi)), 0)
    raw = b''.join(b'\x00' + buf.raw[y*w*3:(y+1)*w*3] for y in range(hh))
    def chunk(t, dd):
        c = t + dd
        return struct.pack('>I', len(dd)) + c + struct.pack('>I', zlib.crc32(c))
    png = (b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', w, hh, 8, 2, 0, 0, 0))
           + chunk(b'IDAT', zlib.compress(raw, 6)) + chunk(b'IEND', b''))
    o = r'F:\Games\Taikou 2\Taikou2 Original\.rev\%s.png' % tag
    open(o, 'wb').write(png)
    print('  %s -> %d 字节' % (tag, len(png)), flush=True)

t0 = time.time()
for i, tt in enumerate(TIMES):
    while time.time() - t0 < tt:
        time.sleep(0.3)
    d = rd(0x534040, 4)
    cnt = struct.unpack('<I', d)[0] if d else -1
    print('t=%5.1f present=%d' % (time.time()-t0, cnt), flush=True)
    hwnd = find_win()
    shot('%s_t%02d' % (TAG, int(tt)), hwnd)
k32.TerminateProcess(hp, 0)
print('done', flush=True)
