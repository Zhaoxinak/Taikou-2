import ctypes, os, time, sys
from ctypes import wintypes

k32 = ctypes.WinDLL('kernel32', use_last_error=True)
u32 = ctypes.WinDLL('user32', use_last_error=True)

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

exe = sys.argv[1] if len(sys.argv) > 1 else r'F:\Games\Taikou 2\Taikou2 Original\TAIK2W95_clean.exe'
wait = float(sys.argv[2]) if len(sys.argv) > 2 else 6.0
cwd = os.path.dirname(exe)

si = STARTUPINFO(); si.cb = ctypes.sizeof(si)
pi = PROCESS_INFORMATION()
ok = k32.CreateProcessA(exe.encode(), None, None, None, False, 0, None,
                        cwd.encode(), ctypes.byref(si), ctypes.byref(pi))
print('CreateProcess:', 'OK' if ok else '失败 %d' % ctypes.get_last_error())
if not ok:
    sys.exit(1)
print('pid =', pi.dwProcessId)
time.sleep(wait)

code = wintypes.DWORD()
k32.GetExitCodeProcess(pi.hProcess, ctypes.byref(code))
print('退出码 =', code.value, '(259 = STILL_ACTIVE 仍在运行)')

# 枚举该进程的窗口
found = []
WNDENUMPROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)

def cb(hwnd, lparam):
    pid = wintypes.DWORD()
    u32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    if pid.value == pi.dwProcessId:
        n = u32.GetWindowTextLengthA(hwnd)
        buf = ctypes.create_string_buffer(n + 1)
        u32.GetWindowTextA(hwnd, buf, n + 1)
        vis = u32.IsWindowVisible(hwnd)
        r = wintypes.RECT()
        u32.GetWindowRect(hwnd, ctypes.byref(r))
        found.append((hex(hwnd), buf.value.decode('latin1'), bool(vis),
                      (r.right - r.left, r.bottom - r.top)))
    return True

u32.EnumWindows(WNDENUMPROC(cb), 0)
print('窗口数 =', len(found))
for h, t, v, sz in found:
    print('   %s 可见=%s %dx%d  标题=%r' % (h, v, sz[0], sz[1], t))

k32.TerminateProcess(pi.hProcess, 0)
k32.CloseHandle(pi.hThread); k32.CloseHandle(pi.hProcess)
print('已结束')
