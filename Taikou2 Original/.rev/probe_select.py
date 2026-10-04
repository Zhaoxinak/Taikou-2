"""跳到「武将选择」画面并连拍，看清可选主角列表长什么样。

临时移走 OPENNING.AVI 以秒进标题菜单；结束一定恢复。
"""
import ctypes, os, shutil, struct, sys, time, zlib
from ctypes import wintypes

k32 = ctypes.WinDLL('kernel32', use_last_error=True)
u32 = ctypes.WinDLL('user32')
g32 = ctypes.WinDLL('gdi32')

GAME = r'F:\Games\Taikou 2\Taikou2 Original'
EXE = os.path.join(GAME, 'TAIK2W95_zoom.exe')
AVI = os.path.join(GAME, 'OPENNING.AVI')
REV = os.path.join(GAME, '.rev')


class SI2(ctypes.Structure):
    _fields_ = [('cb', wintypes.DWORD), ('a', wintypes.LPVOID), ('b', wintypes.LPVOID), ('c', wintypes.LPVOID),
                ('x', wintypes.DWORD), ('y', wintypes.DWORD), ('xs', wintypes.DWORD), ('ys', wintypes.DWORD),
                ('x1', wintypes.DWORD), ('y1', wintypes.DWORD), ('fa', wintypes.DWORD), ('fl', wintypes.DWORD),
                ('sw', wintypes.WORD), ('r2', wintypes.WORD), ('r3', wintypes.LPVOID), ('h1', wintypes.HANDLE),
                ('h2', wintypes.HANDLE), ('h3', wintypes.HANDLE)]


class PI(ctypes.Structure):
    _fields_ = [('hp', wintypes.HANDLE), ('ht', wintypes.HANDLE), ('pid', wintypes.DWORD), ('tid', wintypes.DWORD)]


def kill_games():
    class PE(ctypes.Structure):
        _fields_ = [('dwSize', wintypes.DWORD), ('c1', wintypes.DWORD), ('pid', wintypes.DWORD),
                    ('hid', ctypes.c_size_t), ('mid', wintypes.DWORD), ('th', wintypes.DWORD),
                    ('ppid', wintypes.DWORD), ('pri', ctypes.c_long), ('fl', wintypes.DWORD),
                    ('nm', ctypes.c_wchar * 260)]
    h = k32.CreateToolhelp32Snapshot(0x2, 0)
    pe = PE(); pe.dwSize = ctypes.sizeof(PE); n = 0
    if k32.Process32FirstW(h, ctypes.byref(pe)):
        while True:
            if 'TAIK2W95' in pe.nm.upper():
                ph = k32.OpenProcess(1, False, pe.pid)
                if ph:
                    k32.TerminateProcess(ph, 0); k32.CloseHandle(ph); n += 1
            if not k32.Process32NextW(h, ctypes.byref(pe)):
                break
    k32.CloseHandle(h)
    if n:
        time.sleep(0.8)
    return n


def find_main(pid):
    f = []

    @ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)
    def cb(h, lp):
        p = wintypes.DWORD()
        u32.GetWindowThreadProcessId(h, ctypes.byref(p))
        if p.value == pid and u32.IsWindowVisible(h):
            r = wintypes.RECT()
            u32.GetClientRect(h, ctypes.byref(r))
            if r.right >= 800:
                f.append(h)
        return True
    u32.EnumWindows(cb, 0)
    return f[0] if f else None


def grab(hwnd):
    r = wintypes.RECT(); u32.GetClientRect(hwnd, ctypes.byref(r))
    w, h = r.right, r.bottom
    wr = wintypes.RECT(); u32.GetWindowRect(hwnd, ctypes.byref(wr))
    hdcW = u32.GetDC(0); mdc = g32.CreateCompatibleDC(hdcW)
    bmp = g32.CreateCompatibleBitmap(hdcW, w, h)
    g32.SelectObject(mdc, bmp)
    g32.BitBlt(mdc, 0, 0, w, h, hdcW, wr.left, wr.top, 0x00CC0020)
    bi = struct.pack('<IiiHHIIiiII', 40, w, -h, 1, 24, 0, 0, 0, 0, 0, 0)
    buf = ctypes.create_string_buffer(w * h * 3)
    g32.GetDIBits(mdc, bmp, 0, h, buf, ctypes.create_string_buffer(bi, len(bi)), 0)
    g32.DeleteObject(bmp); g32.DeleteDC(mdc); u32.ReleaseDC(0, hdcW)
    return wr, buf.raw


def shot(hwnd, path):
    wr, raw = grab(hwnd)
    w = 1280; h = 800
    rows = b''.join(b'\x00' + raw[y * w * 3:(y + 1) * w * 3] for y in range(h))

    def ch(t, dd):
        c = t + dd
        return struct.pack('>I', len(dd)) + c + struct.pack('>I', zlib.crc32(c))
    open(path, 'wb').write(b'\x89PNG\r\n\x1a\n'
                           + ch(b'IHDR', struct.pack('>IIBBBBB', w, h, 8, 2, 0, 0, 0))
                           + ch(b'IDAT', zlib.compress(rows, 6)) + ch(b'IEND', b''))
    return path


def click(hwnd, cx, cy):
    wr = wintypes.RECT(); u32.GetWindowRect(hwnd, ctypes.byref(wr))
    r = wintypes.RECT(); u32.GetClientRect(hwnd, ctypes.byref(r))
    nctop = (wr.bottom - wr.top) - r.bottom
    u32.SetCursorPos(wr.left + cx, wr.top + nctop + cy)
    time.sleep(0.35)
    u32.mouse_event(0x0002, 0, 0, 0, 0)
    time.sleep(0.08)
    u32.mouse_event(0x0004, 0, 0, 0, 0)
    time.sleep(0.2)


def key(vk):
    u32.keybd_event(vk, 0, 0, 0); time.sleep(0.05); u32.keybd_event(vk, 0, 2, 0)


def main():
    kill_games()
    bak = AVI + '.probeskip'
    if os.path.exists(AVI):
        shutil.move(AVI, bak)
    try:
        si = SI2(); si.cb = ctypes.sizeof(si); pi = PI()
        k32.CreateProcessA(EXE.encode(), None, None, None, False, 0, None,
                           GAME.encode(), ctypes.byref(si), ctypes.byref(pi))
        hp, pid = pi.hp, pi.pid
        hk = k32.OpenProcess(0x1F0FFF, False, pid)
        hwnd = None
        for _ in range(60):
            hwnd = find_main(pid)
            if hwnd:
                break
            time.sleep(0.3)
        if not hwnd:
            print('no window'); return 1
        print('hwnd', hex(hwnd), flush=True)
        u32.SetForegroundWindow(hwnd)
        time.sleep(1.0)
        for _ in range(6):
            key(0x1B)
            time.sleep(0.4)
        time.sleep(3.0)
        shot(hwnd, os.path.join(REV, 'sel_0_menu.png'))
        print('菜单已截', flush=True)
        # 「开始新游戏」按钮中心：逻辑(320,160) -> 客户区(640,320)
        click(hwnd, 640, 320)
        time.sleep(0.6)
        for i in range(14):
            shot(hwnd, os.path.join(REV, 'sel_%02d.png' % i))
            time.sleep(0.45)
        print('连拍完成', flush=True)
        k32.TerminateProcess(hk, 0)
    finally:
        kill_games()
        if os.path.exists(bak):
            shutil.move(bak, AVI)
        print('AVI 已恢复', flush=True)


if __name__ == '__main__':
    sys.exit(main())
