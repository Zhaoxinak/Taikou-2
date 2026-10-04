"""最终验证: 原始长 AVI -> 菜单 -> 点击开始新游戏 -> 大地图, 全程截图"""
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
si = SI2(); si.cb = ctypes.sizeof(si); pi = PI()
ok = k32.CreateProcessA(EXE.encode(), None, None, None, False, 0, None,
                        os.path.dirname(EXE).encode(), ctypes.byref(si), ctypes.byref(pi))
print('CreateProcess', ok, 'pid', pi.dwProcessId, flush=True)
hp, pid = pi.hProcess, pi.dwProcessId

def rd(va, n):
    b = ctypes.create_string_buffer(n); got = ctypes.c_size_t()
    if not k32.ReadProcessMemory(hp, ctypes.c_void_p(va), b, n, ctypes.byref(got)): return None
    return b.raw[:got.value]

# 等长 AVI 播完 -> 菜单 (present 大量增长)
t0 = time.time(); last = -1; stable = 0
while time.time() - t0 < 320:
    d = rd(0x534040, 4)
    cnt = struct.unpack('<I', d)[0] if d else -1
    if cnt != last:
        print('[%6.1f] present=%d' % (time.time()-t0, cnt), flush=True); last = cnt; stable = 0
    else:
        stable += 1
        if cnt >= 300 and stable > 10: break
    time.sleep(0.5)
print('等待结束 t=%.1f present=%d' % (time.time()-t0, last), flush=True)

def find_win():
    found = []
    @ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)
    def cb(h, lp):
        p = wintypes.DWORD(); u32.GetWindowThreadProcessId(h, ctypes.byref(p))
        if p.value == pid and u32.IsWindowVisible(h):
            b = ctypes.create_unicode_buffer(64); u32.GetWindowTextW(h, b, 64)
            if b.value.strip(): found.append(h)
        return True
    u32.EnumWindows(cb, 0)
    if not found: return None
    best, ba = None, -1
    for h0 in found:
        r0 = wintypes.RECT(); u32.GetClientRect(h0, ctypes.byref(r0))
        if r0.right*r0.bottom > ba: ba = r0.right*r0.bottom; best = h0
    return best

hwnd = find_win()
if not hwnd:
    print('无窗口'); k32.TerminateProcess(hp, 0); sys.exit(1)
u32.SetForegroundWindow(hwnd); time.sleep(0.8)

def shot(name):
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
    o = r'F:\Games\Taikou 2\Taikou2 Original\.rev\%s' % name
    open(o, 'wb').write(png)
    print('截图', name, len(png), flush=True)

shot('final_1_menu.png')
wr = wintypes.RECT(); u32.GetWindowRect(hwnd, ctypes.byref(wr))
r = wintypes.RECT(); u32.GetClientRect(hwnd, ctypes.byref(r))
nctop = (wr.bottom - wr.top) - r.bottom
cx, cy = wr.left + 545, wr.top + nctop + 310
print('点击 (%d,%d)' % (cx, cy), flush=True)
u32.SetCursorPos(cx, cy); time.sleep(0.4)
u32.mouse_event(0x0002, 0, 0, 0, 0); time.sleep(0.08); u32.mouse_event(0x0004, 0, 0, 0, 0)
time.sleep(4); shot('final_2_game.png')
time.sleep(8); shot('final_3_map.png')
print('present 最终 =', struct.unpack('<I', rd(0x534040, 4))[0], flush=True)
k32.TerminateProcess(hp, 0)
print('done', flush=True)
