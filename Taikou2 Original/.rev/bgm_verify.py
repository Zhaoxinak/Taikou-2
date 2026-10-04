"""
零干扰验证 BGM 是否真的在播放
==============================
自写的 mp3.dll 把转换后的路径写进 .data 段的 PATHBUF（模块基址 +0x3000）。
本脚本不用调试器、不下断点，直接：
  1. 正常启动游戏（全速）
  2. 自动向主窗口发 Enter 推进
  3. 周期性读 mp3.dll 的 PATHBUF —— 有 "..\\MP3\\NN.WAV" 就说明
     mp3play 真的被调用了，且扩展名转换成功

用法:
    python .rev/bgm_verify.py <exe> <秒数>
"""
import ctypes
import os
import subprocess
import sys
import time
from ctypes import wintypes

k32 = ctypes.WinDLL('kernel32', use_last_error=True)
u32 = ctypes.WinDLL('user32', use_last_error=True)

TH32CS_SNAPMODULE = 0x00000008
TH32CS_SNAPMODULE32 = 0x00000010
WM_KEYDOWN, WM_KEYUP = 0x0100, 0x0101
VK_RETURN, VK_SPACE = 0x0D, 0x20
PROCESS_QUERY_LIMITED = 0x1000
PROCESS_VM_READ = 0x0010


class MODULEENTRY32(ctypes.Structure):
    _fields_ = [('dwSize', wintypes.DWORD), ('th32ModuleID', wintypes.DWORD),
                ('th32ProcessID', wintypes.DWORD), ('GlblcntUsage', wintypes.DWORD),
                ('ProccntUsage', wintypes.DWORD),
                ('modBaseAddr', ctypes.POINTER(ctypes.c_byte)),
                ('modBaseSize', wintypes.DWORD), ('hModule', wintypes.HANDLE),
                ('szModule', ctypes.c_char * 256),
                ('szExePath', ctypes.c_char * 260)]


def find_module(pid, name):
    snap = k32.CreateToolhelp32Snapshot(TH32CS_SNAPMODULE | TH32CS_SNAPMODULE32, pid)
    if not snap or snap == wintypes.HANDLE(-1).value:
        return 0
    me = MODULEENTRY32()
    me.dwSize = ctypes.sizeof(me)
    got = k32.Module32First(snap, ctypes.byref(me))
    while got:
        if me.szModule.decode('latin1').lower() == name.lower():
            k32.CloseHandle(snap)
            return ctypes.cast(me.modBaseAddr, ctypes.c_void_p).value or 0
        got = k32.Module32Next(snap, ctypes.byref(me))
    k32.CloseHandle(snap)
    return 0


def find_window(pid):
    res = []

    @ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)
    def cb(hwnd, lp):
        p = wintypes.DWORD()
        u32.GetWindowThreadProcessId(hwnd, ctypes.byref(p))
        if p.value == pid and u32.IsWindowVisible(hwnd):
            r = wintypes.RECT()
            u32.GetWindowRect(hwnd, ctypes.byref(r))
            title = ctypes.create_unicode_buffer(256)
            u32.GetWindowTextW(hwnd, title, 256)
            res.append((hwnd, (r.right - r.left) * (r.bottom - r.top), title.value))
        return True

    u32.EnumWindows(cb, 0)
    return res


def press(hwnd, vk):
    u32.PostMessageA(hwnd, WM_KEYDOWN, vk, 0)
    time.sleep(0.05)
    u32.PostMessageA(hwnd, WM_KEYUP, vk, 0)


def main():
    exe = sys.argv[1]
    run = float(sys.argv[2]) if len(sys.argv) > 2 else 60.0

    p = subprocess.Popen([exe], cwd=os.path.dirname(exe))
    pid = p.pid
    print('进程已启动 pid=%d (无调试器，全速运行)' % pid)

    hp = k32.OpenProcess(PROCESS_VM_READ | PROCESS_QUERY_LIMITED, False, pid)
    if not hp:
        print('OpenProcess 失败 err=%d' % ctypes.get_last_error())
        return

    mp3base = 0
    seen = []
    t0 = time.time()
    last_key = 0
    last_probe = 0
    last_title = None

    while time.time() - t0 < run:
        now = time.time()
        if p.poll() is not None:
            print('\n进程已退出，退出码=%s' % p.returncode)
            break

        if now - last_probe > 0.8:
            last_probe = now
            if not mp3base:
                mp3base = find_module(pid, 'mp3.dll')
                if mp3base:
                    print('[%5.1fs] mp3.dll 已加载 @0x%08X' % (now - t0, mp3base))
            if mp3base:
                buf = ctypes.create_string_buffer(64)
                got = ctypes.c_size_t()
                if k32.ReadProcessMemory(hp, ctypes.c_void_p(mp3base + 0x3000),
                                         buf, 64, ctypes.byref(got)):
                    s = buf.raw.split(b'\x00')[0].decode('latin1')
                    if s and s not in seen:
                        seen.append(s)
                        dg = ctypes.create_string_buffer(16)
                        if k32.ReadProcessMemory(hp, ctypes.c_void_p(mp3base + 0x3100),
                                                 dg, 16, ctypes.byref(got)):
                            import struct
                            cnt, rv, flg, ptr = struct.unpack('<IIII', dg.raw)
                            print('[%5.1fs] PATHBUF="%s"  调用=%d  '
                                  'PlaySoundA返回=%d  flags=0x%X  pszSound=0x%08X'
                                  % (now - t0, s, cnt, rv, flg, ptr))
                        else:
                            print('[%5.1fs] PATHBUF = "%s"' % (now - t0, s))

        if now - last_key > 2.0:
            last_key = now
            wins = find_window(pid)
            if wins:
                hwnd, area, title = max(wins, key=lambda x: x[1])
                if title != last_title:
                    print('[%5.1fs] 窗口: %r (%d 个可见窗口)'
                          % (now - t0, title, len(wins)))
                    last_title = title
                press(hwnd, VK_RETURN)
                press(hwnd, VK_SPACE)
        time.sleep(0.2)

    print()
    print('=== 结论 ===')
    if not mp3base:
        print('X  mp3.dll 未被加载 —— 游戏还没到播放 BGM 的阶段')
    elif not seen:
        print('X  mp3.dll 已加载，但 mp3play 从未被调用')
    else:
        print('OK  mp3play 被调用过，播放了 %d 个不同文件:' % len(seen))
        for s in seen:
            print('      %s' % s)
    print('进程退出码:', p.poll())
    try:
        p.terminate()
    except Exception:
        pass


if __name__ == '__main__':
    main()
