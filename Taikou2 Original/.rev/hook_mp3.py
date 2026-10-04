"""
验证 BGM 是否真的在播放
========================
1) 定期用进程模块快照找到 mp3.dll，在其 mp3play / mp3stop 上布断点
2) 打印每次调用传入的文件路径
3) --keys: 自动向游戏主窗口发 Enter，跳过开场动画推进到游戏内

用法:
    python .rev/hook_mp3.py <exe> <秒数> [--keys]
"""
import ctypes
import os
import struct
import sys
import time
from ctypes import wintypes

k32 = ctypes.WinDLL('kernel32', use_last_error=True)
u32 = ctypes.WinDLL('user32', use_last_error=True)

THREAD_ALL = 0x1F03FF
CONTEXT_FULL = 0x00010007
DBG_CONTINUE = 0x00010002
DBG_EXCEPTION_NOT_HANDLED = 0x80010001
TH32CS_SNAPMODULE = 0x00000008
TH32CS_SNAPMODULE32 = 0x00000010
WM_KEYDOWN = 0x0100
WM_KEYUP = 0x0101
VK_RETURN = 0x0D
VK_SPACE = 0x20
VK_ESCAPE = 0x1B


class WOW64_CONTEXT(ctypes.Structure):
    _fields_ = [
        ('ContextFlags', wintypes.DWORD),
        ('Dr0', wintypes.DWORD), ('Dr1', wintypes.DWORD),
        ('Dr2', wintypes.DWORD), ('Dr3', wintypes.DWORD),
        ('Dr6', wintypes.DWORD), ('Dr7', wintypes.DWORD),
        ('FloatSave', ctypes.c_byte * 112),
        ('SegGs', wintypes.DWORD), ('SegFs', wintypes.DWORD),
        ('SegEs', wintypes.DWORD), ('SegDs', wintypes.DWORD),
        ('Edi', wintypes.DWORD), ('Esi', wintypes.DWORD),
        ('Ebx', wintypes.DWORD), ('Edx', wintypes.DWORD),
        ('Ecx', wintypes.DWORD), ('Eax', wintypes.DWORD),
        ('Ebp', wintypes.DWORD), ('Eip', wintypes.DWORD),
        ('SegCs', wintypes.DWORD), ('EFlags', wintypes.DWORD),
        ('Esp', wintypes.DWORD), ('SegSs', wintypes.DWORD),
        ('ExtendedRegisters', ctypes.c_byte * 512),
    ]


class STARTUPINFO(ctypes.Structure):
    _fields_ = [('cb', wintypes.DWORD), ('lpReserved', wintypes.LPWSTR),
                ('lpDesktop', wintypes.LPWSTR), ('lpTitle', wintypes.LPWSTR),
                ('dwX', wintypes.DWORD), ('dwY', wintypes.DWORD),
                ('dwXSize', wintypes.DWORD), ('dwYSize', wintypes.DWORD),
                ('dwXCountChars', wintypes.DWORD), ('dwYCountChars', wintypes.DWORD),
                ('dwFillAttribute', wintypes.DWORD), ('dwFlags', wintypes.DWORD),
                ('wShowWindow', wintypes.WORD), ('cbReserved2', wintypes.WORD),
                ('lpReserved2', ctypes.POINTER(ctypes.c_char)),
                ('hStdInput', wintypes.HANDLE), ('hStdOutput', wintypes.HANDLE),
                ('hStdError', wintypes.HANDLE)]


class PROCESS_INFORMATION(ctypes.Structure):
    _fields_ = [('hProcess', wintypes.HANDLE), ('hThread', wintypes.HANDLE),
                ('dwProcessId', wintypes.DWORD), ('dwThreadId', wintypes.DWORD)]


class DEBUG_EVENT(ctypes.Structure):
    _fields_ = [('dwDebugEventCode', wintypes.DWORD),
                ('dwProcessId', wintypes.DWORD), ('dwThreadId', wintypes.DWORD),
                ('u', ctypes.c_byte * 160)]


class MODULEENTRY32(ctypes.Structure):
    _fields_ = [('dwSize', wintypes.DWORD), ('th32ModuleID', wintypes.DWORD),
                ('th32ProcessID', wintypes.DWORD), ('GlblcntUsage', wintypes.DWORD),
                ('ProccntUsage', wintypes.DWORD),
                ('modBaseAddr', ctypes.POINTER(ctypes.c_byte)),
                ('modBaseSize', wintypes.DWORD), ('hModule', wintypes.HANDLE),
                ('szModule', ctypes.c_char * 256),
                ('szExePath', ctypes.c_char * 260)]


def get_ctx(hThread):
    ctx = WOW64_CONTEXT()
    ctx.ContextFlags = CONTEXT_FULL
    if k32.Wow64GetThreadContext(hThread, ctypes.byref(ctx)):
        return ctx
    ctx2 = WOW64_CONTEXT()
    ctx2.ContextFlags = CONTEXT_FULL
    k32.GetThreadContext(hThread, ctypes.byref(ctx2))
    return ctx2


def set_ctx(hThread, ctx):
    return k32.Wow64SetThreadContext(hThread, ctypes.byref(ctx))


def rdmem(hp, addr, n):
    buf = ctypes.create_string_buffer(n)
    got = ctypes.c_size_t()
    if k32.ReadProcessMemory(hp, ctypes.c_void_p(addr), buf, n, ctypes.byref(got)):
        return buf.raw[:got.value]
    return b''


def wr(hp, addr, data):
    old = wintypes.DWORD()
    k32.VirtualProtectEx(hp, ctypes.c_void_p(addr), len(data), 0x40,
                         ctypes.byref(old))
    k32.WriteProcessMemory(hp, ctypes.c_void_p(addr), data, len(data), None)
    k32.VirtualProtectEx(hp, ctypes.c_void_p(addr), len(data), old.value,
                         ctypes.byref(old))


def rdstr(hp, addr, limit=260):
    d = rdmem(hp, addr, limit)
    i = d.find(b'\x00')
    return (d[:i] if i >= 0 else d).decode('latin1')


def find_module(pid, name):
    snap = k32.CreateToolhelp32Snapshot(TH32CS_SNAPMODULE | TH32CS_SNAPMODULE32,
                                        pid)
    if snap == wintypes.HANDLE(-1).value or snap is None:
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
            res.append((hwnd, (r.right - r.left) * (r.bottom - r.top)))
        return True

    u32.EnumWindows(cb, 0)
    if not res:
        return 0
    return max(res, key=lambda x: x[1])[0]


def press(hwnd, vk):
    u32.PostMessageA(hwnd, WM_KEYDOWN, vk, 0)
    time.sleep(0.05)
    u32.PostMessageA(hwnd, WM_KEYUP, vk, 0)


class RECT(ctypes.Structure):
    _fields_ = [('left', ctypes.c_long), ('top', ctypes.c_long),
                ('right', ctypes.c_long), ('bottom', ctypes.c_long)]


def main():
    exe = sys.argv[1]
    run = float(sys.argv[2]) if len(sys.argv) > 2 else 40.0
    use_keys = '--keys' in sys.argv

    si = STARTUPINFO()
    si.cb = ctypes.sizeof(si)
    pi = PROCESS_INFORMATION()
    ok = k32.CreateProcessA(exe.encode(), None, None, None, False,
                            0x00000001 | 0x00000002,
                            None, os.path.dirname(exe).encode(),
                            ctypes.byref(si), ctypes.byref(pi))
    if not ok:
        print('CreateProcess 失败 err=%d' % ctypes.get_last_error())
        return
    hp = pi.hProcess
    pid = pi.dwProcessId
    print('进程已启动 pid=%d' % pid)

    mp3base = 0
    orig = {}
    pending_step = {}
    stats = {'play': [], 'stop': 0}
    t0 = time.time()
    last_probe = 0
    last_key = 0
    k32.DebugSetProcessKillOnExit(False)

    while time.time() - t0 < run:
        ev = DEBUG_EVENT()
        if not k32.WaitForDebugEvent(ctypes.byref(ev), 120):
            now = time.time()
            if not mp3base and now - last_probe > 1.0:
                last_probe = now
                mp3base = find_module(pid, 'mp3.dll')
                if mp3base:
                    print('>>> mp3.dll 已加载 @0x%08X' % mp3base)
                    for off, label in ((0x1000, 'mp3play'), (0x1060, 'mp3stop')):
                        a = mp3base + off
                        ob = rdmem(hp, a, 1)
                        if ob:
                            orig[a] = ob[0]
                            wr(hp, a, b'\xcc')
                            print('    断点 %s @0x%08X' % (label, a))
            if use_keys and now - last_key > 2.5:
                last_key = now
                hw = find_window(pid)
                if hw:
                    press(hw, VK_RETURN)
                    print('[%5.1fs] 发送 Enter' % (now - t0))
            continue

        code = ev.dwDebugEventCode
        cont = DBG_CONTINUE

        if code == 6:
            hFile = struct.unpack_from('<I', ev.u, 8)[0]
            if hFile:
                k32.CloseHandle(hFile)

        elif code == 1:
            c = struct.unpack_from('<I', ev.u, 0)[0]
            addr = struct.unpack_from('<I', ev.u, 12)[0]
            if c == 0x80000003 and addr in orig:
                ht = k32.OpenThread(THREAD_ALL, False, ev.dwThreadId)
                ctx = get_ctx(ht)
                a = addr
                wr(hp, a, bytes([orig[a]]))
                ctx.Eip = a
                if (a - mp3base) == 0x1000:
                    path = rdstr(hp, ctx.Esp + 4)
                    stats['play'].append(path)
                    print('[%5.1fs] mp3play("%s")' % (time.time() - t0, path))
                else:
                    stats['stop'] += 1
                    print('[%5.1fs] mp3stop()' % (time.time() - t0))
                sys.stdout.flush()
                ctx.EFlags |= 0x100
                set_ctx(ht, ctx)
                pending_step[ev.dwThreadId] = a
                k32.CloseHandle(ht)
            elif c == 0x80000004:
                if ev.dwThreadId in pending_step:
                    a = pending_step.pop(ev.dwThreadId)
                    ht = k32.OpenThread(THREAD_ALL, False, ev.dwThreadId)
                    ctx = get_ctx(ht)
                    ctx.EFlags &= ~0x100
                    set_ctx(ht, ctx)
                    k32.CloseHandle(ht)
                    wr(hp, a, b'\xcc')
            elif c in (0xC0000005, 0xC0000602):
                ht = k32.OpenThread(THREAD_ALL, False, ev.dwThreadId)
                ctx = get_ctx(ht)
                print('!!! 异常 0x%08X @0x%08X EIP=%08X ESP=%08X'
                      % (c, addr, ctx.Eip, ctx.Esp))
                k32.CloseHandle(ht)
                cont = DBG_EXCEPTION_NOT_HANDLED
            elif c == 0x4000001F:
                pass
            elif not struct.unpack_from('<I', ev.u, 4)[0]:
                cont = DBG_EXCEPTION_NOT_HANDLED

        k32.ContinueDebugEvent(ev.dwProcessId, ev.dwThreadId, cont)

    print()
    print('=== 统计 ===')
    print('mp3play 调用 %d 次' % len(stats['play']))
    seen = []
    for p in stats['play']:
        if p not in seen:
            seen.append(p)
    print('播放过的曲目 (%d 个不同):' % len(seen))
    for p in seen:
        print('   ', p)
    print('mp3stop 调用 %d 次' % stats['stop'])
    try:
        k32.TerminateProcess(hp, 0)
    except Exception:
        pass


if __name__ == '__main__':
    main()
