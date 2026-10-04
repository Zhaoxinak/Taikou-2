# -*- coding: utf-8 -*-
"""exp_card.py — 探索: 如何打开"他人武将信息卡"(带家族族谱按钮的那张)
从已进游戏的状态出发: 点「情报」-> 截图 -> 试探菜单 -> 截图
"""
import ctypes, os, struct, sys, time, traceback, zlib
from ctypes import wintypes

sys.stdout.reconfigure(encoding='utf-8')

k32 = ctypes.WinDLL('kernel32', use_last_error=True)
u32 = ctypes.WinDLL('user32')
g32 = ctypes.WinDLL('gdi32')
k32.OpenProcess.restype = wintypes.HANDLE
k32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
k32.ReadProcessMemory.restype = wintypes.BOOL
k32.ReadProcessMemory.argtypes = [wintypes.HANDLE, wintypes.LPCVOID, wintypes.LPVOID,
                                  ctypes.c_size_t, ctypes.POINTER(ctypes.c_size_t)]
u32.EnumWindows.argtypes = [ctypes.c_void_p, wintypes.LPARAM]
u32.GetClientRect.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.RECT)]

GAME = r'F:/Games/Taikou 2\Taikou2 Original'
EXE = os.path.join(GAME, 'TAIK2W95_family.exe')
REV = os.path.join(GAME, '.rev')
TAG = os.environ.get('TAG', 'exp')
G_BTN_CX, G_BTN_CY, G_IN = 0x535E40, 0x535E44, 0x535F3C


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
        p = wintypes.DWORD()
        u32.GetWindowThreadProcessId(h, ctypes.byref(p))
        if p.value == pid and u32.IsWindowVisible(h):
            r = wintypes.RECT()
            u32.GetClientRect(h, ctypes.byref(r))
            out.append((h, r.right, r.bottom))
        return True
    u32.EnumWindows(cb, 0)
    return out


si = SI2(); si.cb = ctypes.sizeof(si); pi = PI()
k32.CreateProcessA(EXE.encode(), None, None, None, False, 0, None, GAME.encode(),
                   ctypes.byref(si), ctypes.byref(pi))
hk = k32.OpenProcess(0x1F0FFF, False, pi.pid)
hp = None
try:
    main = None
    t0 = time.time()
    while time.time() - t0 < 30:
        for h, w, hh in wins(pi.pid):
            if w >= 800:
                main = h
        if main:
            break
        time.sleep(0.4)

    def rd(va, n):
        b = ctypes.create_string_buffer(n); got = ctypes.c_size_t()
        if not k32.ReadProcessMemory(hk, ctypes.c_void_p(va), b, n, ctypes.byref(got)):
            return None
        return b.raw[:got.value]

    def g(va):
        d = rd(va, 4)
        return struct.unpack('<I', d)[0] if d else -1

    def key(vk, w=0.8):
        u32.keybd_event(vk, 0, 0, 0); time.sleep(0.06)
        u32.keybd_event(vk, 0, 2, 0); time.sleep(w)

    # 等标题
    t1 = time.time(); sk = 0
    while time.time() - t1 < 100:
        if time.time() - sk > 1.0:
            sk = time.time(); u32.SetForegroundWindow(main); key(0x1B, 0.05)
        if g(0x534040) >= 71:
            break
        time.sleep(0.4)
    print('到标题 %.1fs' % (time.time() - t1), flush=True)

    rc = wintypes.RECT(); u32.GetClientRect(main, ctypes.byref(rc))
    pt = wintypes.POINT(0, 0); u32.ClientToScreen(main, ctypes.byref(pt))
    CX0, CY0 = pt.x, pt.y
    print('client %dx%d @screen (%d,%d)' % (rc.right, rc.bottom, CX0, CY0), flush=True)

    def click(px, py, w=1.5):
        u32.SetForegroundWindow(main); time.sleep(0.2)
        u32.SetCursorPos(CX0 + px, CY0 + py); time.sleep(0.35)
        u32.mouse_event(2, 0, 0, 0, 0); time.sleep(0.10)
        u32.mouse_event(4, 0, 0, 0, 0); time.sleep(w)

    def move(px, py):
        u32.SetForegroundWindow(main); time.sleep(0.2)
        u32.SetCursorPos(CX0 + px, CY0 + py); time.sleep(0.35)

    def shot(tag):
        u32.SetForegroundWindow(main); time.sleep(0.25)
        CW, CH = rc.right, rc.bottom
        dcv = u32.GetDC(0); mdc = g32.CreateCompatibleDC(dcv); bmp = g32.CreateCompatibleBitmap(dcv, CW, CH)
        g32.SelectObject(mdc, bmp); g32.BitBlt(mdc, 0, 0, CW, CH, dcv, CX0, CY0, 0x00CC0020)
        bi = struct.pack('<IiiHHIIiiII', 40, CW, -CH, 1, 24, 0, 0, 0, 0, 0, 0)
        buf = ctypes.create_string_buffer(CW * CH * 3)
        g32.GetDIBits(mdc, bmp, 0, CH, buf, ctypes.create_string_buffer(bi, len(bi)), 0)
        raw = b''.join(b'\x00' + buf.raw[y * CW * 3:(y + 1) * CW * 3] for y in range(CH))
        g32.DeleteObject(bmp); g32.DeleteDC(mdc); u32.ReleaseDC(0, dcv)

        def ch(t, dd):
            c = t + dd
            return struct.pack('>I', len(dd)) + c + struct.pack('>I', zlib.crc32(c))
        png = (b'\x89PNG\r\n\x1a\n' + ch(b'IHDR', struct.pack('>IIBBBBB', CW, CH, 8, 2, 0, 0, 0))
               + ch(b'IDAT', zlib.compress(raw, 6)) + ch(b'IEND', b''))
        p = os.path.join(REV, 'f2_%s_%s.png' % (TAG, tag)); open(p, 'wb').write(png)
        print('  shot %-12s  BTN=(%s,%s) IN=%s' % (tag, g(G_BTN_CX), g(G_BTN_CY), g(G_IN)), flush=True)
        return p

    time.sleep(2.0); shot('00_title')
    click(545, 310, 2.0); click(640, 415, 2.5); click(640, 415, 2.5)
    click(640, 415, 3.0); key(0x1B, 1.2); key(0x1B, 1.2)
    shot('03_game')
    print('  已进游戏 BTN=(%s,%s)' % (g(G_BTN_CX), g(G_BTN_CY)), flush=True)

    # 点「情报」按钮 (客户区约 1030,632)
    # 右下按钮行: 调查/交谈/交战/情报/功能 (客户区 y~733)
    click(1220, 733, 2.0); shot('20_kinou')
    key(0x1B, 1.5); click(1138, 733, 2.0); shot('21_jouhou')
    key(0x1B, 1.5); click(1056, 733, 2.0); shot('22_senkou')
except Exception:
    print('EXC', traceback.format_exc(), flush=True)
finally:
    for h in (hp, hk):
        try:
            if h:
                k32.TerminateProcess(h, 0)
        except Exception:
            pass
    print('cleanup', flush=True)
