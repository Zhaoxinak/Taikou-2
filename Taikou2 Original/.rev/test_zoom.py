"""zoom.exe 一体化验证: 启动 -> 等 AVI 播完 -> 读洞页状态 -> 屏幕DC截图 -> 杀进程"""
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
if not ok:
    sys.exit(1)
hp, pid = pi.hProcess, pi.dwProcessId

def rd(va, n):
    buf = ctypes.create_string_buffer(n)
    got = ctypes.c_size_t()
    if not k32.ReadProcessMemory(hp, ctypes.c_void_p(va), buf, n, ctypes.byref(got)):
        return None
    return buf.raw[:got.value]

# --- 等待: present 计数 (0x534040) 上升到稳定 ---
t0 = time.time()
last_cnt = -1
stable = 0
while time.time() - t0 < 20:
    d = rd(0x534000, 0x48)
    if d is None:
        print('[%5.2f] 读失败' % (time.time()-t0)); break
    cnt, ret = struct.unpack_from('<II', d, 0x40)
    if cnt != last_cnt:
        print('[%5.2f] present=%d sb_ret=%d' % (time.time()-t0, cnt, ret))
        last_cnt = cnt; stable = 0
    else:
        stable += 1
        if cnt >= 10 and stable > 12:
            break
    time.sleep(0.25)

# --- 洞页状态 ---
d = rd(0x534000, 0x48)
if d:
    gpsb = struct.unpack_from('<I', d, 0)[0]
    rect = struct.unpack_from('<iiii', d, 0x10)
    cnt, ret = struct.unpack_from('<II', d, 0x40)
    print('g_pSB=%08X  RECT=(%d,%d,%d,%d)  present=%d  StretchBlt_ret=%d' %
          (gpsb, rect[0], rect[1], rect[2], rect[3], cnt, ret))

# --- 找窗口并截图 (屏幕 DC) ---
found = []
@ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)
def cb(hwnd, lp):
    p = wintypes.DWORD()
    u32.GetWindowThreadProcessId(hwnd, ctypes.byref(p))
    if p.value == pid and u32.IsWindowVisible(hwnd):
        b = ctypes.create_unicode_buffer(64)
        u32.GetWindowTextW(hwnd, b, 64)
        if b.value.strip():
            found.append(hwnd)
    return True
u32.EnumWindows(cb, 0)
print('窗口:', [hex(h) for h in found])
if not found:
    print('无窗口, 杀进程'); k32.TerminateProcess(hp, 0); sys.exit(1)
best = None; barea = -1
for h0 in found:
    r0 = wintypes.RECT()
    u32.GetClientRect(h0, ctypes.byref(r0))
    if r0.right * r0.bottom > barea:
        barea = r0.right * r0.bottom; best = h0
u32.SetForegroundWindow(best)
time.sleep(0.8)
r = wintypes.RECT()
u32.GetClientRect(best, ctypes.byref(r))
w, h = r.right, r.bottom
wr = wintypes.RECT()
u32.GetWindowRect(best, ctypes.byref(wr))
print('客户区 %dx%d @(%d,%d)' % (w, h, wr.left, wr.top))

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
out = r'F:\Games\Taikou 2\Taikou2 Original\.rev\z_fix.png'
open(out, 'wb').write(png)
print('截图:', out, len(png), '字节')
k32.TerminateProcess(hp, 0)
