"""
把加壳的 TAIK2W95.exe 跑起来，让 UPX 存根执行到末尾后冻住，
再用 ReadProcessMemory dump 出干净的内存镜像。

做法：把存根最后一条 `jmp OEP`(E9 xx xx xx xx) 改成 `EB FE`(死循环)。
存根已经完成 解压 + call修正 + IAT重建 + VirtualProtect，
所以冻住时内存里就是完整的原始映像。
"""
import ctypes, struct, os, sys, time
from ctypes import wintypes

k32 = ctypes.WinDLL('kernel32', use_last_error=True)

PROCESS_ALL = 0x1F0FFF

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

IMAGEBASE = 0x400000
SIZEOFIMAGE = 0x133000

src = r'F:\Games\Taikou 2\Taikou2 Original\TAIK2W95.exe'
work = r'F:\Games\Taikou 2\Taikou2 Original\.rev\_dbg_run.exe'

data = bytearray(open(src, 'rb').read())

# 存根最后一条 jmp OEP：RVA 0x131343 -> file 0x6D743
JMP_OFF = 0x6D743
print('jmp 处字节:', bytes(data[JMP_OFF:JMP_OFF+5]).hex(' '))
assert bytes(data[JMP_OFF:JMP_OFF+5]) == b'\xe9\x68\x31\xfc\xff', 'jmp 位置不对'
rel = struct.unpack_from('<i', data, JMP_OFF+1)[0]
oep = (0x131343 + 5) + rel
print('真实 OEP RVA =', hex(oep))

# 改成 EB FE (死循环)
data[JMP_OFF:JMP_OFF+5] = b'\xeb\xfe\x90\x90\x90'
open(work, 'wb').write(bytes(data))
print('已写出打补丁副本:', work)

si = STARTUPINFO()
si.cb = ctypes.sizeof(si)
pi = PROCESS_INFORMATION()

ok = k32.CreateProcessA(work.encode(), None, None, None, False,
                       0, None, os.path.dirname(work).encode(),
                       ctypes.byref(si), ctypes.byref(pi))
if not ok:
    print('CreateProcess 失败', ctypes.get_last_error())
    sys.exit(1)
print('进程已启动 pid=%d' % pi.dwProcessId)

time.sleep(4.0)

buf = ctypes.create_string_buffer(SIZEOFIMAGE)
read = ctypes.c_size_t(0)
ok = k32.ReadProcessMemory(pi.hProcess, ctypes.c_void_p(IMAGEBASE),
                           buf, SIZEOFIMAGE, ctypes.byref(read))
print('ReadProcessMemory ok=%s 读到 %d 字节' % (ok, read.value))

k32.TerminateProcess(pi.hProcess, 0)
k32.CloseHandle(pi.hThread)
k32.CloseHandle(pi.hProcess)

if not ok or read.value < SIZEOFIMAGE:
    print('dump 不完整')
    sys.exit(1)

dump = buf.raw[:SIZEOFIMAGE]
out = r'F:\Games\Taikou 2\Taikou2 Original\.rev\clean_dump.bin'
open(out, 'wb').write(dump)
print('已保存:', out)

# 跟 HD 版比对
hd = open(r'F:\Games\Taikou 2\Taikou2 Original\TAIK2W95_HD.exe', 'rb').read()

def cmp(name, a, b):
    n = min(len(a), len(b))
    diff = [i for i in range(n) if a[i] != b[i]]
    print('\n=== %s  长度 clean=%d hd=%d  不同字节 %d 个 ===' % (name, len(a), len(b), len(diff)))
    if diff:
        print('  首个差异 +%s: clean=%s  hd=%s' % (
            hex(diff[0]), a[diff[0]:diff[0]+8].hex(' '), b[diff[0]:diff[0]+8].hex(' ')))
        print('  末个差异 +%s' % hex(diff[-1]))
        # 差异区间
        ranges = []
        s = diff[0]; p = diff[0]
        for i in diff[1:]:
            if i - p > 64:
                ranges.append((s, p)); s = i
            p = i
        ranges.append((s, p))
        print('  差异区间 (%d 段):' % len(ranges))
        for a1, b1 in ranges[:20]:
            print('    %s .. %s  (%d 字节)' % (hex(a1), hex(b1), b1-a1+1))
    return diff

cmp('.text  (RVA 0x1000)', dump[0x1000:0xc4000], hd[0x400:0xc4000])
cmp('.data  (RVA 0xc4000)', dump[0xc4000:0x132000], hd[0xc4000:0x132000])
