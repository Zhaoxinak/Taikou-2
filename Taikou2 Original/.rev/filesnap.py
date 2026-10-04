"""找出游戏运行时会写哪些文件（通关记录的持久化位置就在其中）。

流程：快照 -> 启动到标题菜单(ESC跳过) -> 结束 -> 再快照 -> 对比。
"""
import ctypes
import hashlib
import os
import sys
import time
from ctypes import wintypes

GAME = r'F:\Games\Taikou 2\Taikou2 Original'
REV = os.path.join(GAME, '.rev')
EXE = os.path.join(GAME, 'TAIK2W95_zoom.exe')
SNAP = os.path.join(REV, 'filesnap.json')

k32 = ctypes.WinDLL('kernel32', use_last_error=True)
u32 = ctypes.WinDLL('user32')


def snapshot():
    out = {}
    for n in sorted(os.listdir(GAME)):
        p = os.path.join(GAME, n)
        if not os.path.isfile(p) or os.path.abspath(p) == os.path.abspath(__file__):
            continue
        try:
            b = open(p, 'rb').read()
        except Exception:
            continue
        out[n] = (hashlib.md5(b).hexdigest(), len(b))
    return out


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
    found = []
    @ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)
    def cb(h, lp):
        p = wintypes.DWORD()
        u32.GetWindowThreadProcessId(h, ctypes.byref(p))
        if p.value == pid and u32.IsWindowVisible(h):
            r = wintypes.RECT()
            u32.GetClientRect(h, ctypes.byref(r))
            if r.right >= 800:
                found.append(h)
        return True
    u32.EnumWindows(cb, 0)
    return found[0] if found else None


def main():
    kill_games()
    before = snapshot()
    print('启动前快照 %d 个文件' % len(before), flush=True)

    si = SI2()
    si.cb = ctypes.sizeof(si)
    pi = PI()
    k32.CreateProcessA(EXE.encode(), None, None, None, False, 0, None,
                       GAME.encode(), ctypes.byref(si), ctypes.byref(pi))
    hp, pid = pi.hp, pi.pid
    print('pid', pid, flush=True)
    h = find_main(pid)
    if h:
        time.sleep(2)
        u32.SetForegroundWindow(h)
        u32.keybd_event(0x1B, 0, 0, 0)
        time.sleep(0.05)
        u32.keybd_event(0x1B, 0, 2, 0)
        print('ESC 跳过片头', flush=True)
    time.sleep(6)          # 停在标题菜单
    # 用窗口菜单「结束(X)」正常退出，让游戏自己写盘
    if h:
        u32.PostMessageW(h, 0x0111, 0xFDE1, 0)   # WM_COMMAND 结束游戏
        print('已发 结束游戏 命令', flush=True)
    time.sleep(3)
    if not k32.TerminateProcess(hp, 0):
        print('正常退出失败，强制结束')
    k32.CloseHandle(hp)
    kill_games()
    time.sleep(1.5)

    after = snapshot()
    print('启动后快照 %d 个文件' % len(after), flush=True)
    changed = []
    for n, (hsh, sz) in after.items():
        if n in before and before[n][0] != hsh:
            changed.append((n, before[n][1], sz))
        elif n not in before:
            changed.append((n, -1, sz))
    print('\n=== 被游戏改写/新建的文件 ===')
    for n, o, a in changed:
        print('  %-24s %8d -> %8d  (%+d)' % (n, o, a, a - o))
    if not changed:
        print('  （无）')
    import json
    with open(SNAP, 'w', encoding='utf-8') as f:
        json.dump({'before': before, 'after': after}, f, indent=1, ensure_ascii=False)
    print('\n快照已存 %s' % SNAP)


if __name__ == '__main__':
    main()
