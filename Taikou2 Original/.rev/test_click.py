"""点击测试: 启动 zoom.exe -> 等菜单 -> 点击"开始新游戏" -> 截图验证鼠标映射"""
import ctypes, struct, sys, time, os, zlib
from ctypes import wintypes

k32 = ctypes.WinDLL('kernel32', use_last_error=True)
u32 = ctypes.WinDLL('user32')
g32 = ctypes.WinDLL('gdi32')

class SI2(ctypes.Structure):
    _fields_ = [('cb', wintypes.DWORD), ('lpReserved', wintypes.LPVOID), ('lpDesktop', wintypes.LPVOID),
                ('lpTitle', wintypes.LPVOID), ('dwX', wintypes.DWORD), ('dwY', wintypes.DWORD),
                ('dwXSize', wintypes.DWORD), ('dwYSize', wintypes.DWORD),
                ('dwXCountChars', wintypes.DWORD), ('dwYCountChars', wintypes.DWORD),
                ('dwFillAttribute', wintypes.DWORD), ('dwFlags', wintypes.DWORD),
                ('wShowWindow', wintypes.WORD), ('cbReserved2', wintypes.WORD),
                ('lpReserved2', wintypes.LPVOID), ('hStdInput', wintypes.HANDLE),
                ('hStdOutput', wintypes.HANDLE), ('hStdError', wintypes.HANDLE)]
class PI(ctypes.Structure):
    _fields_ = [('hProcess', wintypes.HANDLE), ('hThread', wintypes.HANDLE),
                ('dwProcessId', wintypes.DWORD), ('dwThreadId', wintypes.DWORD)]

EXE = r'F:\Games\Taikou 2\Taikou2 Original\TAIK2W95_zoom.exe'
si = SI2(); si.cb = ctypes.sizeof(si)
pi = PI()
ok = k32.CreateProcessA(EXE.encode(), None, None, None, False, 0, None,
                        os.path.dirname(EXE).encode(), ctypes.byref(si), ctypes.byref(pi))
print('CreateProcess', ok, 'pid', pi.dwProcessId)
hp, pid = pi.hProcess, pi.dwProcessId

def rd(va, n):
    buf = ctypes.create_string_buffer(n)
    got = ctypes.c_size_t()
    if not k32.ReadProcessMemory(hp, ctypes.c_void_p(va), buf, n, ctypes.byref(got)):
        return None
    return buf.raw[:got.value]

# 等菜单稳定 (present >= 71 且稳定)
t0 = time.time(); last = -1; stable = 0
while time.time() - t0 < 20:
    d = rd(0x534040, 4)
    cnt = struct.unpack('<I', d)[0] if d else 0
    if cnt != last:
        last = cnt; stable = 0
    else:
        stable += 1
        if cnt >= 71 and stable > 12: break
    time.sleep(0.25)
print('[%5.2f] present=%d 菜单应已就绪' % (time.time()-t0, last))

found = []
@ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)
def cb(hwnd, lp):
    p = wintypes.DWORD()
    u32.GetWindowThreadProcessId(hwnd, ctypes.byref(p))
    if p.value == pid and u32.IsWindowVisible(hwnd):
        b = ctypes.create_unicode_buffer(64)
        u32.GetWindowTextW(hwnd, b, 64)
        if b.value.strip(): found.append(hwnd)
    return True
u32.EnumWindows(cb, 0)
best = None; barea = -1
for h0 in found:
    r0 = wintypes.RECT()
    u32.GetClientRect(h0, ctypes.byref(r0))
    if r0.right*r0.bottom > barea: barea = r0.right*r0.bottom; best = h0
u32.SetForegroundWindow(best)
time.sleep(0.6)
wr = wintypes.RECT()
u32.GetWindowRect(best, ctypes.byref(wr))
print('窗口 @(%d,%d)' % (wr.left, wr.top))

def shot(name):
    r = wintypes.RECT()
    u32.GetClientRect(best, ctypes.byref(r))
    w, h = r.right, r.bottom
    hdcW = u32.GetDC(0)
    mdc = g32.CreateCompatibleDC(hdcW)
    bmp = g32.CreateCompatibleBitmap(hdcW, w, h)
    g32.SelectObject(mdc, bmp)
    g32.BitBlt(mdc, 0, 0, w, h, hdcW, wr.left, wr.top, 0x00CC0020)
    bi = struct.pack('<IiiHHIIiiII', 40, w, -h, 1, 24, 0, 0, 0, 0, 0, 0)
    buf = ctypes.create_string_buffer(w*h*3)
    g32.GetDIBits(mdc, bmp, 0, h, buf, ctypes.create_string_buffer(bi, len(bi)), 0)
    raw = b''.join(b'\x00' + buf.raw[y*w*3:(y+1)*w*3] for y in range(h))
    def chunk(t, dd):
        c = t + dd
        return struct.pack('>I', len(dd)) + c + struct.pack('>I', zlib.crc32(c))
    png = (b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', w, h, 8, 2, 0, 0, 0))
           + chunk(b'IDAT', zlib.compress(raw, 6)) + chunk(b'IEND', b''))
    out = r'F:\Games\Taikou 2\Taikou2 Original\.rev\%s' % name
    open(out, 'wb').write(png)
    print('截图:', name, len(png))
    return out

# 截图1: 菜单 (对照)
shot('click_0_menu.png')

# 点击"开始新游戏": 客户区坐标约 (545,310)。截图含标题栏+菜单栏约 47px。
# 屏幕坐标 = wr.left + 545, wr.top + 310 + 47(非客户区高度近似)
r = wintypes.RECT()
u32.GetClientRect(best, ctypes.byref(r))
# 精确非客户区高度: window height - client height
wh = wr.bottom - wr.top
nonclient_top = wh - r.bottom
cx = wr.left + 545
cy = wr.top + nonclient_top + 310
print('点击屏幕坐标 (%d,%d)  非客户区高=%d' % (cx, cy, nonclient_top))
u32.SetCursorPos(cx, cy)
time.sleep(0.5)
shot('click_1_hover.png')
u32.mouse_event(0x0002, 0, 0, 0, 0)  # left down
time.sleep(0.08)
u32.mouse_event(0x0004, 0, 0, 0, 0)  # left up
time.sleep(2.5)
shot('click_2_after.png')

# 再读 present 是否增长 (说明游戏进入了新画面继续绘制)
d = rd(0x534040, 4)
print('present after click =', struct.unpack('<I', d)[0])
time.sleep(3)
shot('click_3_later.png')
k32.TerminateProcess(hp, 0)
print('done')
