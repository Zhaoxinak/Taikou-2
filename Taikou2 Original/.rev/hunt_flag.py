"""运行时扫描：找出控制标题菜单可见项的内存 flag。

思路（分组二分）：
  1. 启动到标题菜单，记下菜单框区域的像素基线
  2. 把候选内存区按 N 个 dword 一组，全置 1，等一帧，再比对该区域
  3. 若像素变化 -> 该组有嫌疑，二分定位到单个 dword / byte
  4. 每次测试后恢复原值，避免污染

用法： python .rev/hunt_flag.py [起始地址] [结束地址]
"""
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

# 菜单框在 1280x800 客户区内的位置（2x 拉伸自 640x400）
MENU_X, MENU_Y, MENU_W, MENU_H = 355, 248, 370, 275
PRESENT_VA = 0x534040
GROUP = 256            # 每组 dword 数


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


def menu_shot(hwnd):
    """抓整窗客户区（走已验证的 burst.png 路径），返回 (全图bytes, 菜单区bytes)。"""
    r = wintypes.RECT()
    u32.GetClientRect(hwnd, ctypes.byref(r))
    w, hh = r.right, r.bottom
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
    full = bytes(buf.raw)
    u32.ReleaseDC(0, hdcW)
    # 切出菜单区（每像素 3 字节，自下而上）
    row = w * 3
    parts = []
    for y in range(MENU_Y, min(MENU_Y + MENU_H, hh)):
        off = (hh - 1 - y) * row
        parts.append(full[off + MENU_X * 3: off + (MENU_X + MENU_W) * 3])
    return full, b"".join(parts)


def main():
    lo = int(sys.argv[1], 16) if len(sys.argv) > 1 else 0x510000
    hi = int(sys.argv[2], 16) if len(sys.argv) > 2 else 0x534000
    print('扫描范围 0x%08x - 0x%08x  (%d dword)' % (lo, hi, (hi - lo) // 4), flush=True)

    kill_games()
    si = SI2()
    si.cb = ctypes.sizeof(si)
    pi = PI()
    k32.CreateProcessA(EXE.encode(), None, None, None, False, 0, None,
                       GAME.encode(), ctypes.byref(si), ctypes.byref(pi))
    hp, pid = pi.hp, pi.pid
    h = None
    for _ in range(80):
        h = find_main(pid)
        if h:
            break
        time.sleep(0.2)
    if not h:
        print('no window')
        return 1
    hk = k32.OpenProcess(0x1F0FFF | 0x0004, False, pid)   # PROCESS_VM_OPERATION
    time.sleep(2)
    u32.SetForegroundWindow(h)
    u32.keybd_event(0x1B, 0, 0, 0)
    time.sleep(0.05)
    u32.keybd_event(0x1B, 0, 2, 0)
    def poke(hwnd):
        """标题菜单是静止画面，不会自动重绘；移动鼠标强制触发一帧刷新。"""
        r = wintypes.RECT()
        u32.GetWindowRect(hwnd, ctypes.byref(r))
        u32.SetCursorPos(r.left + 540, r.top + 300)   # 划过菜单 -> 触发重绘
        time.sleep(0.08)
        u32.SetCursorPos(r.left + 8, r.top + 780)     # 停到菜单外 -> 消除高亮
        time.sleep(0.14)

    print('跳过片头中...', flush=True)

    def present():
        b = ctypes.create_string_buffer(4)
        got = ctypes.c_size_t()
        if not k32.ReadProcessMemory(hk, ctypes.c_void_p(PRESENT_VA), b, 4, ctypes.byref(got)):
            return -1
        return struct.unpack('<I', b.raw)[0]

    # ESC 需要重试：游戏刚起来时可能还没准备好接收按键
    ok = False
    for attempt in range(6):
        time.sleep(1.5)
        u32.SetForegroundWindow(h)
        u32.keybd_event(0x1B, 0, 0, 0)
        time.sleep(0.05)
        u32.keybd_event(0x1B, 0, 2, 0)
        time.sleep(1.5)
        pv = present()
        print('  ESC 第%d次 -> present=%d' % (attempt + 1, pv), flush=True)
        if pv > 150:
            ok = True
            break
    if not ok:
        print('  !! ESC 未能跳过片头，退出', flush=True)
        kill_games()
        return 4
    print('已跳过片头，等待菜单渲染稳定', flush=True)

    # 必须等 present 稳定（标题菜单是静止画面）再取基线，否则会全程误判
    last, stable, tw = -1, 0, time.time()
    while time.time() - tw < 40:
        cur = present()
        if cur == last and cur >= 0:
            stable += 1
        else:
            stable = 0
        last = cur
        if stable >= 8:
            break
        time.sleep(0.3)
    print('present 稳定在 %d' % last, flush=True)
    time.sleep(0.5)

    poke(h)
    p0 = present()
    time.sleep(0.2)
    full0, base = menu_shot(h)
    poke(h)
    time.sleep(0.2)
    _f, chk = menu_shot(h)
    if chk != base:
        print('  !! 重复截图不一致（画面仍在动），基线不可靠，退出', flush=True)
        kill_games()
        return 3
    print('  基线可重复 ✓', flush=True)
    print('基线 present=%d  菜单区 %d 字节  md5=%s' % (p0, len(base), hash(base) & 0xffffff), flush=True)

    def rd(va, n):
        b = ctypes.create_string_buffer(n)
        got = ctypes.c_size_t()
        if not k32.ReadProcessMemory(hk, ctypes.c_void_p(va), b, n, ctypes.byref(got)):
            return None
        return b.raw[:got.value]

    def wr(va, data):
        n = len(data)
        b = ctypes.create_string_buffer(data, n)
        w = ctypes.c_size_t()
        return k32.WriteProcessMemory(hk, ctypes.c_void_p(va), b, n, ctypes.byref(w))

    def alive():
        c = wintypes.DWORD()
        k32.GetExitCodeProcess(hk, ctypes.byref(c))
        return c.value == 259

    addr = lo
    suspects = []
    t0 = time.time()
    tested = 0
    while addr < hi:
        n = min(GROUP * 4, hi - addr)
        orig = rd(addr, n)
        if orig is None:
            addr += n
            continue
        blk = bytearray(orig)
        for i in range(0, n, 4):
            struct.pack_into('<I', blk, i, 0x00000001)
        wr(addr, bytes(blk))
        time.sleep(0.10)
        poke(h)
        cur = present()
        if not alive() or cur < 0:
            print('  !! 游戏在 0x%08x 处崩溃，跳过' % addr, flush=True)
            kill_games()
            return 2
        _full, shot = menu_shot(h)
        wr(addr, orig)          # 立即恢复
        if shot != base:
            print('  ** 组 0x%08x+ n=%d  菜单像素变化！ (present %d->%d)' % (addr, n, p0, cur), flush=True)
            suspects.append((addr, n))
        addr += n
        tested += 1
    print('分组扫描完成: %d 组, 用时 %.0fs, 嫌疑组 %d' % (tested, time.time() - t0, len(suspects)), flush=True)

    # 对嫌疑组做二分细化
    for base_addr, n in suspects:
        print('\n--- 细化 0x%08x (%d 字节) ---' % (base_addr, n), flush=True)
        step = 4
        cur_addr, cur_n = base_addr, n
        while cur_n > 4:
            half = (cur_n // 2) & ~3
            changed = []
            for off in range(0, cur_n, half):
                a = cur_addr + off
                m = min(half, cur_n - off)
                o = rd(a, m)
                if o is None:
                    continue
                bl = bytearray(o)
                for i in range(0, m, 4):
                    struct.pack_into('<I', bl, i, 1)
                wr(a, bytes(bl))
                time.sleep(0.10)
                poke(h)
                if not alive():
                    wr(a, o)
                    kill_games()
                    print('  崩溃，停止')
                    return 2
                _f2, s2 = menu_shot(h)
                wr(a, o)
                if s2 != base:
                    changed.append((a, m))
            if not changed:
                break
            # 在第一个变化组内继续
            cur_addr, cur_n = changed[0]
            print('  缩小到 0x%08x n=%d' % (cur_addr, cur_n), flush=True)
        o = rd(cur_addr, cur_n)
        print('  最终嫌疑地址 0x%08x  当前值=%s' % (cur_addr, o.hex(' ') if o else '?'), flush=True)

    kill_games()
    return 0


if __name__ == '__main__':
    sys.exit(main())
