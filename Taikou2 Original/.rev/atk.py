# -*- coding: utf-8 -*-
"""atk.py — 附着到**已运行**的太阁进程: 截图 + 读补丁诊断变量 + 可选点击/按键
用法:
  python atk.py shot            只看当前画面
  python atk.py click X Y [...] 依次点击(客户区坐标)并各截一张
  python atk.py key 0x1B [...]  依次按键
"""
import ctypes, os, struct, sys, time, zlib
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
u32.PrintWindow.argtypes = [wintypes.HWND, wintypes.HDC, wintypes.UINT]

REV = os.path.dirname(os.path.abspath(__file__))
TAG = os.environ.get('TAG', 'atk')

# 诊断变量(与 build_fam_btn2.py 一致)
V = {
    'G_FAMILY': 0x5354C0, 'G_FAMSEL': 0x5355D8,
    'G_BTN_CX': 0x535E40, 'G_BTN_CY': 0x535E44,
    'G_IN': 0x535F3C, 'G_CLICK': 0x535F20, 'G_HIT': 0x535F24,
    'G_LOOPCNT': 0x535EEC, 'G_MX': 0x535F28, 'G_MY': 0x535F2C,
    'CARD_CUR': 0x514EE8, 'CARD_OBJ': 0x520630,
}


def find_proc():
    import subprocess
    out = subprocess.run(['tasklist', '/FI', 'IMAGENAME eq TAIK2W95_family.exe', '/FO', 'CSV', '/NH'],
                         capture_output=True, text=True, errors='ignore').stdout
    for line in out.splitlines():
        if 'TAIK2W95_family.exe' in line:
            return int(line.split('","')[1].strip('"'))
    return None


def wins(pid):
    out = []

    @ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)
    def cb(h, lp):
        p = wintypes.DWORD()
        u32.GetWindowThreadProcessId(h, ctypes.byref(p))
        if p.value == pid and u32.IsWindowVisible(h):
            r = wintypes.RECT()
            u32.GetClientRect(h, ctypes.byref(r))
            if r.right >= 800:
                out.append((h, r.right, r.bottom))
        return True
    u32.EnumWindows(cb, 0)
    return out


def main():
    pid = find_proc()
    if not pid:
        print('未找到 TAIK2W95_family.exe 进程'); return
    ws = wins(pid)
    if not ws:
        print('未找到主窗口'); return
    hwnd, cw, ch = ws[0]
    print('PID=%d HWND=0x%X 客户区 %dx%d' % (pid, hwnd, cw, ch))
    hk = k32.OpenProcess(0x1F0FFF, False, pid)

    def rd(va, n):
        b = ctypes.create_string_buffer(n); got = ctypes.c_size_t()
        if not k32.ReadProcessMemory(hk, ctypes.c_void_p(va), b, n, ctypes.byref(got)):
            return None
        return b.raw[:got.value]

    def g(va):
        d = rd(va, 4)
        return struct.unpack('<I', d)[0] if d else -1

    pt = wintypes.POINT()
    u32.GetClientRect(hwnd, ctypes.byref(wintypes.RECT()))
    u32.ClientToScreen(hwnd, ctypes.byref(pt)) if False else None
    r = wintypes.RECT(); u32.GetClientRect(hwnd, ctypes.byref(r))
    o = wintypes.POINT(0, 0); u32.ClientToScreen(hwnd, ctypes.byref(o))
    print('客户区屏幕原点 (%d,%d)' % (o.x, o.y))

    def shot(tag):
        hdc = u32.GetDC(0)
        mdc = g32.CreateCompatibleDC(hdc)
        bmp = g32.CreateCompatibleBitmap(hdc, cw, ch)
        g32.SelectObject(mdc, bmp)
        # BitBlt 直接抓屏幕(比 PrintWindow 对 DirectDraw 老游戏更可靠)
        g32.BitBlt(mdc, 0, 0, cw, ch, hdc, o.x, o.y, 0x00CC0020)
        bi = struct.pack('<IiiHHIIiiII', 40, cw, -ch, 1, 32, 0, 0, 0, 0, 0, 0)
        buf = ctypes.create_string_buffer(cw * ch * 4)
        g32.GetDIBits(mdc, bmp, 0, ch, buf, bi, 0)
        g32.DeleteObject(bmp); g32.DeleteDC(mdc); u32.ReleaseDC(0, hdc)
        raw = bytearray()
        for y in range(ch):
            raw.append(0)
            row = buf.raw[y * cw * 4:(y + 1) * cw * 4]
            for x in range(cw):
                raw += bytes((row[x * 4 + 2], row[x * 4 + 1], row[x * 4]))
        def chk(t, d):
            return struct.pack('>I', len(d)) + t + d + struct.pack('>I', zlib.crc32(t + d) & 0xFFFFFFFF)
        png = (b'\x89PNG\r\n\x1a\n' + chk(b'IHDR', struct.pack('>IIBBBBB', cw, ch, 8, 2, 0, 0, 0))
               + chk(b'IDAT', zlib.compress(bytes(raw), 6)) + chk(b'IEND', b''))
        p = os.path.join(REV, 'a_%s_%s.png' % (TAG, tag))
        open(p, 'wb').write(png)
        print('  shot %s -> %s' % (tag, os.path.basename(p)), flush=True)
        return p

    def dump(tag):
        s = '  '.join('%s=%s' % (k, hex(g(a)) if g(a) >= 0 else '?') for k, a in V.items())
        print('  [%s] %s' % (tag, s), flush=True)

    def click(x, y, w=1.6):
        u32.SetForegroundWindow(hwnd)
        u32.SetCursorPos(o.x + x, o.y + y)
        time.sleep(0.25)
        u32.mouse_event(2, 0, 0, 0, 0); time.sleep(0.08)
        u32.mouse_event(4, 0, 0, 0, 0)
        time.sleep(w)

    def key(vk, w=1.0):
        u32.SetForegroundWindow(hwnd)
        u32.keybd_event(vk, 0, 0, 0); time.sleep(0.08)
        u32.keybd_event(vk, 0, 2, 0)
        time.sleep(w)

    args = sys.argv[1:]
    if not args or args[0] == 'shot':
        dump('now'); shot('now')
        return
    mode = args[0]
    if mode == 'click':
        nums = [int(v) for v in args[1:]]
        for i in range(0, len(nums), 2):
            click(nums[i], nums[i + 1])
            dump('after_click_%d,%d' % (nums[i], nums[i + 1]))
            shot('c%02d_%d_%d' % (i // 2, nums[i], nums[i + 1]))
    elif mode == 'key':
        for i, v in enumerate(args[1:]):
            key(int(v, 0))
            dump('after_key_%s' % v)
            shot('k%02d_%s' % (i, v))


main()
