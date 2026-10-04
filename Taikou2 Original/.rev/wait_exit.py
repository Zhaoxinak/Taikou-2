"""
不带调试器运行 exe，等待并报告：存活时间 + 退出码。
用于对照「纯净版 vs 原版加壳版」谁会崩、什么时候崩。

用法: python .rev/wait_exit.py <exe> [最长等待秒]
"""
import ctypes, os, sys, time
from ctypes import wintypes

k32 = ctypes.WinDLL('kernel32', use_last_error=True)


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


def run(exe, wait=60.0, probe=True):
    cwd = os.path.dirname(exe)
    si = STARTUPINFO(); si.cb = ctypes.sizeof(si)
    pi = PROCESS_INFORMATION()
    ok = k32.CreateProcessA(exe.encode(), None, None, None, False, 0, None,
                            cwd.encode(), ctypes.byref(si), ctypes.byref(pi))
    name = os.path.basename(exe)
    if not ok:
        print('%-24s CreateProcess 失败 %d' % (name, ctypes.get_last_error()))
        return
    t0 = time.time()
    rc = k32.WaitForSingleObject(pi.hProcess, int(wait * 1000))
    dt = time.time() - t0
    code = wintypes.DWORD()
    k32.GetExitCodeProcess(pi.hProcess, ctypes.byref(code))
    if rc == 0:      # WAIT_OBJECT_0 => 已退出
        cv = code.value
        note = ''
        if cv == 0xC0000005:
            note = '  <<< 访问违规崩溃'
        elif cv == 0xC00000FD:
            note = '  <<< 栈溢出'
        elif cv == 0xC0000409:
            note = '  <<< 栈缓冲区溢出'
        elif cv == 0xC0000602:
            note = '  <<< FAIL_FAST'
        print('%-24s 运行 %.1f 秒后退出, 退出码 = 0x%08X (%d)%s'
              % (name, dt, cv, cv, note))
    else:
        print('%-24s 运行 %.1f 秒后仍存活 (WAIT=%d)' % (name, dt, rc))
        k32.TerminateProcess(pi.hProcess, 0)
    k32.CloseHandle(pi.hThread); k32.CloseHandle(pi.hProcess)


if __name__ == '__main__':
    if len(sys.argv) > 1:
        run(sys.argv[1], float(sys.argv[2]) if len(sys.argv) > 2 else 60.0)
    else:
        base = r'F:\Games\Taikou 2\Taikou2 Original'
        run(os.path.join(base, 'TAIK2W95_clean.exe'), 60)
        run(os.path.join(base, 'TAIK2W95.exe'), 60)
        run(os.path.join(base, 'TAIK2W95_HD.exe'), 60)
