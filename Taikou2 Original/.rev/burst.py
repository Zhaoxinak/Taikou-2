"""启动游戏 -> ESC 跳过片头 -> 高速连拍，抓 ESC 之后的完整界面演进。"""
import ctypes
import os
import struct
import sys
import time
import zlib
from ctypes import wintypes

k32 = ctypes.WinDLL('kernel32', use_last_error=True)
u32 = ctypes.WinDLL('user32')
g32 = ctypes.WinDLL('gdi32')

EXE = r'F:\Games\Taikou 2\Taikou2 Original\TAIK2W95_zoom.exe'
GAME = r'F:\Games\Taikou 2\Taikou2 Original'
REV = os.path.join(GAME, '.rev')


class SI2(ctypes.Structure):
    _fields_ = [('cb', wintypes.DWORD), ('a', wintypes.LPVOID), ('b', wintypes.LPVOID), ('c', wintypes.LPVOID),
                ('x', wintypes.DWORD), ('y', wintypes.DWORD), ('xs', wintypes.DWORD), ('ys', wintypes.DWORD),
                ('x1', wintypes.DWORD), ('y1', wintypes.DWORD), ('fa', wintypes.DWORD), ('fl', wintypes.DWORD),
                ('sw', wintypes.WORD), ('r2', wintypes.WORD), ('r3', wintypes.LPVOID), ('h1', wintypes.HANDLE),
                ('h2', wintypes.HANDLE), ('h3', wintypes.HANDLE)]


class PI(ctypes.Structure):
    _fields_ = [('hp', wintypes.HANDLE), ('ht', wintypes.HANDLE), ('pid', wintypes.DWORD), ('tid', wintypes.DWORD)]


def procs():
    class PE(ctypes.Structure):
        _fields_ = [('dwSize', wintypes.DWORD), ('c1', wintypes.DWORD), ('pid', wintypes.DWORD),
                    ('hid', ctypes.c_size_t), ('mid', wintypes.DWORD), ('th', wintypes.DWORD),
                    ('ppid', wintypes.DWORD), ('pri', ctypes.c_long), ('fl', wintypes.DWORD), ('nm', ctypes.c_wchar * 260)]
    h = k32.CreateToolhelp32Snapshot(0x2, 0)
    r = {}
    pe = PE()
    pe.dwSize = ctypes.sizeof(PE)
    if k32.Process32FirstW(h, ctypes.byref(pe)):
        while True:
            r[pe.pid] = pe.nm
            if not k32.Process32NextW(h, ctypes.byref(pe)):
                break
    k32.CloseHandle(h)
    return r


def kill_games():
    n = 0
    for p, nm in procs().items():
        if 'TAIK2W95' in nm.upper():
            h = k32.OpenProcess(1, False, p)
            if h:
                k32.TerminateProcess(h, 0)
                k32.CloseHandle(h)
                n += 1
    if n:
        time.sleep(0.6)
    return n


def wins(pid):
    o = []
    @ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)
    def cb(h, lp):
        p = wintypes.DWORD()
        u32.GetWindowThreadProcessId(h, ctypes.byref(p))
        if p.value == pid and u32.IsWindowVisible(h):
            b = ctypes.create_unicode_buffer(160)
            u32.GetWindowTextW(h, b, 160)
            r = wintypes.RECT()
            u32.GetClientRect(h, ctypes.byref(r))
            o.append((h, b.value, r.right, r.bottom))
        return True
    u32.EnumWindows(cb, 0)
    return o


def png(hwnd, path):
    r = wintypes.RECT()
    u32.GetClientRect(hwnd, ctypes.byref(r))
    w, hh = r.right, r.bottom
    if w < 20 or hh < 20:
        return 0, 0.0
    wr = wintypes.RECT()
    u32.GetWindowRect(hwnd, ctypes.byref(wr))
    hdcW = u32.GetDC(0)
    mdc = g32.CreateCompatibleDC(hdcW)
    bmp = g32.CreateCompatibleBitmap(hdcW, w, hh)
    g32.SelectObject(mdc, bmp)
    g32.BitBlt(mdc, 0, 0, w, hh, hdcW, wr.left, wr.top, 0x00CC0020)
    bi = struct.pack('<IiiHHIIiiII', 40, w, -hh, 1, 24, 0, 0, 0, 0, 0, 0)
    buf = ctypes.create_string_buffer(w * hh * 3)
    g32.GetDIBits(mdc, bmp, 0, hh, buf, ctypes.create_string_buffer(bi, len(bi)), 0)
    raw = b''.join(b'\x00' + buf.raw[y * w * 3:(y + 1) * w * 3] for y in range(hh))

    def ch(t, dd):
        c = t + dd
        return struct.pack('>I', len(dd)) + c + struct.pack('>I', zlib.crc32(c))
    open(path, 'wb').write(b'\x89PNG\r\n\x1a\n'
                           + ch(b'IHDR', struct.pack('>IIBBBBB', w, hh, 8, 2, 0, 0, 0))
                           + ch(b'IDAT', zlib.compress(raw, 6)) + ch(b'IEND', b''))
    nb = sum(1 for i in range(0, len(raw), 3) if raw[i:i + 3] != b'\x00\x00\x00') / (len(raw) // 3)
    return len(raw) // 3, nb


def main():
    print('清理残留:', kill_games(), flush=True)
    si = SI2()
    si.cb = ctypes.sizeof(si)
    pi = PI()
    k32.CreateProcessA(EXE.encode(), None, None, None, False, 0, None,
                       GAME.encode(), ctypes.byref(si), ctypes.byref(pi))
    hp, pid = pi.hp, pi.pid
    print('pid', pid, flush=True)
    hk = k32.OpenProcess(0x1F0FFF, False, pid)

    def present():
        b = ctypes.create_string_buffer(4)
        got = ctypes.c_size_t()
        if not k32.ReadProcessMemory(hk, ctypes.c_void_p(0x534040), b, 4, ctypes.byref(got)):
            return -1
        return struct.unpack('<I', b.raw)[0]

    main_h = None
    for _ in range(80):
        for h, t, w, hh in wins(pid):
            if w >= 800:
                main_h = h
                break
        if main_h:
            break
        time.sleep(0.2)
    if not main_h:
        print('no window')
        return 1
    print('main hwnd', hex(main_h), 'present', present(), flush=True)

    t0 = time.time()
    time.sleep(2.0)
    u32.SetForegroundWindow(main_h)
    u32.keybd_event(0x1B, 0, 0, 0)
    time.sleep(0.05)
    u32.keybd_event(0x1B, 0, 2, 0)
    print('[%.2fs] ESC pressed' % (time.time() - t0), flush=True)

    # 高速连拍
    for delay in [0.15, 0.25, 0.4, 0.6, 0.9, 1.3, 2.0, 3.0, 4.5, 6.0, 8.0]:
        time.sleep(delay if t0 == 0 else 0)
        el = time.time() - t0
        if not u32.IsWindow(main_h):
            print('  窗口消失')
            break
        n, nb = png(main_h, os.path.join(REV, 'flow_%05.2f.png' % el))
        print('  [%5.2fs] %d px  nonblack %3.0f%%  present=%d' % (el, n, nb * 100, present()), flush=True)
        time.sleep(0.12)
    k32.TerminateProcess(hk, 0)
    k32.CloseHandle(hk)
    print('清理:', kill_games(), flush=True)


if __name__ == '__main__':
    sys.exit(main())
