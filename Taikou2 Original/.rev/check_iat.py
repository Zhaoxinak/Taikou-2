"""
检查运行中进程的 IAT：逐项读出函数地址，找出仍为 0（未被 loader 填充）的项。
用法: python .rev/check_iat.py [exe]
"""
import ctypes, os, sys, time, struct
from ctypes import wintypes

k32 = ctypes.WinDLL('kernel32', use_last_error=True)

EXE = sys.argv[1] if len(sys.argv) > 1 else r'F:\Games\Taikou 2\Taikou2 Original\TAIK2W95_clean.exe'
CWD = os.path.dirname(EXE)
IMAGEBASE = 0x400000


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


def parse_imports(path):
    """解析 exe 自身的导入表 -> [(dll, iat_rva, [names])]"""
    d = open(path, 'rb').read()
    e_lfanew = struct.unpack_from('<I', d, 0x3C)[0]
    opt = e_lfanew + 24
    magic, = struct.unpack_from('<H', d, opt)
    ddoff = opt + (96 if magic == 0x10B else 112)
    imp_rva, imp_size = struct.unpack_from('<II', d, ddoff + 8)   # 目录项 1 = IMPORT
    nsec, = struct.unpack_from('<H', d, e_lfanew + 6)
    opt_size, = struct.unpack_from('<H', d, e_lfanew + 20)
    secs = []
    so = opt + opt_size
    for i in range(nsec):
        o = so + i * 40
        nm = d[o:o + 8].rstrip(b'\0').decode('latin1')
        vs, va, rs, ra = struct.unpack_from('<IIII', d, o + 8)
        secs.append((nm, va, vs, ra, rs))

    def r2o(rva):
        for nm, va, vs, ra, rs in secs:
            if va <= rva < va + max(vs, rs):
                return ra + (rva - va)
        return None

    def cstr(rva):
        o = r2o(rva)
        e = d.index(b'\0', o)
        return d[o:e].decode('latin1')

    out = []
    p = r2o(imp_rva)
    while True:
        oft, ts, fc, name_rva, ft = struct.unpack_from('<IIIII', d, p)
        if not name_rva and not ft:
            break
        dll = cstr(name_rva)
        names = []
        q = r2o(oft or ft)
        while True:
            v, = struct.unpack_from('<I', d, q)
            if v == 0:
                break
            if v & 0x80000000:
                names.append('ordinal#%d' % (v & 0xFFFF))
            else:
                o2 = r2o(v)
                e2 = d.index(b'\0', o2)
                names.append(d[o2 + 2:e2].decode('latin1'))
            q += 4
        out.append((dll, ft, names))
        p += 20
    return out


def main():
    imports = parse_imports(EXE)
    print('导入表: %d 个 DLL' % len(imports))
    si = STARTUPINFO(); si.cb = ctypes.sizeof(si)
    pi = PROCESS_INFORMATION()
    ok = k32.CreateProcessA(EXE.encode(), None, None, None, False, 0,
                            None, CWD.encode(), ctypes.byref(si), ctypes.byref(pi))
    if not ok:
        print('CreateProcess 失败', ctypes.get_last_error())
        sys.exit(1)
    print('pid =', pi.dwProcessId, ' 等待 3 秒让 loader 填完 IAT...')
    time.sleep(3.0)

    total = 0
    zeros = []
    for dll, iat_rva, names in imports:
        print('\n--- %s  IAT@RVA 0x%X  %d 个函数 ---' % (dll, iat_rva, len(names)))
        n = len(names)
        buf = ctypes.create_string_buffer(n * 4 + 4)
        got = ctypes.c_size_t(0)
        va = IMAGEBASE + iat_rva
        okr = k32.ReadProcessMemory(pi.hProcess, ctypes.c_void_p(va), buf, n * 4,
                                    ctypes.byref(got))
        if not okr:
            print('   读取 IAT 失败', ctypes.get_last_error())
            continue
        vals = struct.unpack('<%dI' % n, buf.raw[:n * 4])
        for i, (nm, v) in enumerate(zip(names, vals)):
            total += 1
            flag = ''
            if v == 0:
                flag = '   <<<<<< 为 0！未被填充'
                zeros.append((dll, nm, iat_rva + i * 4))
            print('   %-28s 0x%08X%s' % (nm, v, flag))

    print('\n总计 %d 个 IAT 项，其中为 0 的有 %d 个' % (total, len(zeros)))
    if zeros:
        print('!!! 未填充项:')
        for dll, nm, rva in zeros:
            print('    %s!%s   IAT RVA 0x%X' % (dll, nm, rva))

    k32.TerminateProcess(pi.hProcess, 0)
    k32.CloseHandle(pi.hThread); k32.CloseHandle(pi.hProcess)


if __name__ == '__main__':
    main()
