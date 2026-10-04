"""零干扰探针: 启动 zoom.exe, 高频轮询 0x434000 (g_pSB) 和洞页字符串"""
import ctypes, struct, sys, time, os
from ctypes import wintypes

k32 = ctypes.WinDLL('kernel32', use_last_error=True)

class SI(ctypes.Structure):
    _fields_ = [('cb', wintypes.DWORD)] + [('f%d' % i, wintypes.HANDLE) for i in range(15)] + \
               [('extra', wintypes.BYTE * 64)]
class PI(ctypes.Structure):
    _fields_ = [('hProcess', wintypes.HANDLE), ('hThread', wintypes.HANDLE),
                ('dwProcessId', wintypes.DWORD), ('dwThreadId', wintypes.DWORD)]

EXE = sys.argv[1] if len(sys.argv) > 1 else r'F:\Games\Taikou 2\Taikou2 Original\TAIK2W95_zoom.exe'
si = SI(); si.cb = ctypes.sizeof(SI)
# 真正的 STARTUPINFOA 需要完整布局, 用简化: 手动构 68 字节
class SI2(ctypes.Structure):
    _fields_ = [('cb', wintypes.DWORD), ('lpReserved', wintypes.LPVOID), ('lpDesktop', wintypes.LPVOID),
                ('lpTitle', wintypes.LPVOID), ('dwX', wintypes.DWORD), ('dwY', wintypes.DWORD),
                ('dwXSize', wintypes.DWORD), ('dwYSize', wintypes.DWORD),
                ('dwXCountChars', wintypes.DWORD), ('dwYCountChars', wintypes.DWORD),
                ('dwFillAttribute', wintypes.DWORD), ('dwFlags', wintypes.DWORD),
                ('wShowWindow', wintypes.WORD), ('cbReserved2', wintypes.WORD),
                ('lpReserved2', wintypes.LPVOID), ('hStdInput', wintypes.HANDLE),
                ('hStdOutput', wintypes.HANDLE), ('hStdError', wintypes.HANDLE)]
si = SI2(); si.cb = ctypes.sizeof(si)
pi = PI()
ok = k32.CreateProcessA(EXE.encode(), None, None, None, False, 0, None,
                        os.path.dirname(EXE).encode(), ctypes.byref(si), ctypes.byref(pi))
print('CreateProcess', ok, 'pid', pi.dwProcessId)
if not ok:
    sys.exit(1)

hp = pi.hProcess
t0 = time.time()
last = None
n = 0
while time.time() - t0 < 8:
    buf = ctypes.create_string_buffer(64)
    got = ctypes.c_size_t()
    if not k32.ReadProcessMemory(hp, ctypes.c_void_p(0x434000), buf, 64, ctypes.byref(got)):
        ec = ctypes.get_last_error()
        print('[%6.3f] 读失败 err=%d (进程可能已退出)' % (time.time()-t0, ec))
        break
    g = struct.unpack_from('<I', buf.raw, 0)[0]
    s1 = buf.raw[0x20:0x30]
    s2 = buf.raw[0x30:0x3A]
    code = buf.raw[0x80:0x86]
    code = buf.raw[0x80:0x86]
    state = (g, s1, s2, code)
    if state != last:
        n += 1
        print('[%6.3f] g_pSB=%08X  str="%s"/"%s"  code头=%s' %
              (time.time()-t0, g, s1.split(b'\0')[0].decode('latin1'),
               s2.split(b'\0')[0].decode('latin1'), code.hex(' ')))
        last = state
    if n > 30:
        break
ec = wintypes.DWORD()
k32.GetExitCodeProcess(hp, ctypes.byref(ec))
print('退出码:', hex(ec.value))
k32.TerminateProcess(hp, 0)
