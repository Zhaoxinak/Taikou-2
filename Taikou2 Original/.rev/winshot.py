"""枚举游戏主窗口, 置前并截图"""
import ctypes, struct, sys, time
from ctypes import wintypes

u32 = ctypes.WinDLL('user32')
g32 = ctypes.WinDLL('gdi32')

found = []

@ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)
def cb(hwnd, lp):
    pid = wintypes.DWORD()
    u32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    if pid.value == TARGET_PID and u32.IsWindowVisible(hwnd):
        buf = ctypes.create_unicode_buffer(64)
        u32.GetWindowTextW(hwnd, buf, 64)
        t = buf.value
        if t.strip():
            found.append((hwnd, t))
    return True

TARGET_PID = int(sys.argv[1])
u32.EnumWindows(cb, 0)
print('窗口:', [(hex(h), t) for h, t in found])
if not found:
    sys.exit('未找到窗口')

# 选客户区最大的窗口 (跳过 AVI 播放小窗)
found.sort(key=lambda x: -1)
best = None; barea = -1
for hwnd0, t in found:
    r0 = wintypes.RECT()
    u32.GetClientRect(hwnd0, ctypes.byref(r0))
    if r0.right * r0.bottom > barea:
        barea = r0.right * r0.bottom; best = (hwnd0, t, r0.right, r0.bottom)
print('选择:', best)
hwnd = best[0]
u32.SetForegroundWindow(hwnd)
time.sleep(0.6)
r = wintypes.RECT()
u32.GetClientRect(hwnd, ctypes.byref(r))
w, h = r.right, r.bottom
print('客户区: %dx%d' % (w, h))
if w < 100:
    sys.exit('客户区异常')

hdcW = u32.GetDC(0)          # 屏幕 DC
wr = wintypes.RECT()
u32.GetWindowRect(hwnd, ctypes.byref(wr))
x, y = wr.left, wr.top
print('窗口位置: (%d,%d) 客户区 %dx%d' % (x, y, w, h))
mdc = g32.CreateCompatibleDC(hdcW)
bmp = g32.CreateCompatibleBitmap(hdcW, w, h)
g32.SelectObject(mdc, bmp)
# 屏幕位块传输窗口客户区
g32.BitBlt(mdc, 0, 0, w, h, hdcW, x, 0, 0x00CC0020)

bi = struct.pack('<IiiHHIIiiII', 40, w, -h, 1, 24, 0, 0, 0, 0, 0, 0)
buf = ctypes.create_string_buffer(w * h * 3)
g32.GetDIBits(mdc, bmp, 0, h, buf, ctypes.create_string_buffer(bi, len(bi)), 0)

# BMP -> PNG (zlib)
import zlib
raw = b''.join(b'\x00' + buf.raw[y*w*3:(y+1)*w*3] for y in range(h))
def chunk(t, d):
    c = t + d
    return struct.pack('>I', len(d)) + c + struct.pack('>I', zlib.crc32(c))
png = (b'\x89PNG\r\n\x1a\n'
       + chunk(b'IHDR', struct.pack('>IIBBBBB', w, h, 8, 2, 0, 0, 0))
       + chunk(b'IDAT', zlib.compress(raw, 6))
       + chunk(b'IEND', b''))
out = sys.argv[2]
open(out, 'wb').write(png)
print('已保存', out)
