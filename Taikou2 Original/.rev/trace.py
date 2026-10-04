"""
太阁立志传2 —— 外置 API 日志追踪器（不需要改动 exe，也不需要编译器）

原理：以调试器身份启动游戏，在关键 Win32 API 入口插 int3 断点，
      每次调用记录参数；函数返回时记录返回值；进程崩溃时把
      「最近 N 条调用 + 崩溃现场(寄存器/栈)」写进日志文件。

用法:
    python .rev/trace.py [exe路径] [运行秒数]

输出:
    控制台实时打印 + .rev/taikou2_trace.log
"""
import ctypes, os, sys, time, struct
from ctypes import wintypes
from collections import deque

k32 = ctypes.WinDLL('kernel32', use_last_error=True)
u32 = ctypes.WinDLL('user32', use_last_error=True)

EXE = sys.argv[1] if len(sys.argv) > 1 else r'F:\Games\Taikou 2\Taikou2 Original\TAIK2W95_clean.exe'
RUN = float(sys.argv[2]) if len(sys.argv) > 2 else 120.0
AUTO_KEYS = '--keys' in sys.argv
CWD = os.path.dirname(EXE)
LOGPATH = os.path.join(CWD, '.rev', 'taikou2_trace.log')

IMAGEBASE = 0x400000
SYSDIR = os.path.join(os.environ.get('SystemRoot', r'C:\Windows'), 'SysWOW64')
if not os.path.isdir(SYSDIR):
    SYSDIR = os.path.join(os.environ.get('SystemRoot', r'C:\Windows'), 'System32')

# 要追踪的函数：dll -> [(函数名, [(参数序号, 类型)] )]
# 类型: s=字符串指针  i=整数  x=十六进制
HOOKS = {
    'kernel32.dll': [
        ('CreateFileA', [(1, 's'), (2, 'x'), (3, 'x')]),
        ('GetProcAddress', [(2, 's')]),
        ('LoadLibraryA', [(1, 's')]),
        ('GetDriveTypeA', [(1, 's')]),
        ('GetFileAttributesA', [(1, 's')]),
        ('GetVolumeInformationA', [(1, 's')]),
        ('_lopen', [(1, 's'), (2, 'i')]),
        ('_lread', []),
        ('_lclose', []),
        ('ReadFile', []),
        ('CreateFileMappingA', []),
        ('lstrlen', []),
        ('GetLastError', []),
        ('SetUnhandledExceptionFilter', []),
        ('ExitProcess', [(1, 'i')]),
    ],
    'winmm.dll': [
        ('mciSendStringA', [(1, 's')]),
        ('mciSendCommandA', []),
        ('midiOutOpen', []),
        ('waveOutOpen', []),
    ],
    'ddraw.dll': [
        ('DirectDrawCreate', []),
    ],
}

EXC = {0xC0000005: 'ACCESS_VIOLATION', 0xC0000094: 'ILLEGAL_INSTRUCTION',
       0xC00000FD: 'STACK_OVERFLOW', 0xC000008E: 'DIVIDE_BY_ZERO',
       0xC0000409: 'STACK_BUFFER_OVERRUN', 0xC0000025: 'NONCONTINUABLE'}


# ---------------- PE 导出表解析（读 32 位系统 DLL） ----------------
def pe_exports(path):
    d = open(path, 'rb').read()
    e_lfanew = struct.unpack_from('<I', d, 0x3C)[0]
    pe = struct.unpack_from('<I', d, e_lfanew)[0]
    assert pe == 0x4550, '不是 PE: %s' % path
    nsec, = struct.unpack_from('<H', d, e_lfanew + 6)
    opt_size, = struct.unpack_from('<H', d, e_lfanew + 20)
    opt = e_lfanew + 24
    magic, = struct.unpack_from('<H', d, opt)
    ddoff = opt + (96 if magic == 0x10B else 112)
    exp_rva, exp_size = struct.unpack_from('<II', d, ddoff)
    if not exp_rva:
        return {}
    secs = []
    so = opt + opt_size
    for i in range(nsec):
        o = so + i * 40
        name = d[o:o + 8].rstrip(b'\0').decode('latin1')
        vs, va, rs, ra = struct.unpack_from('<IIII', d, o + 8)
        secs.append((name, va, vs, ra, rs))

    def r2o(rva):
        for name, va, vs, ra, rs in secs:
            if va <= rva < va + max(vs, rs):
                return ra + (rva - va)
        return None

    off = r2o(exp_rva)
    (flags, ts, ver, name_rva, base, naddr, nname,
     addr_rva, name_rva_tab, ord_rva) = struct.unpack_from('<IIIIIIIIII', d, off)
    aoff = r2o(addr_rva); noff = r2o(name_rva_tab)
    out = {}
    for i in range(nname):
        nr, = struct.unpack_from('<I', d, noff + i * 4)
        stro = r2o(nr)
        e = d.index(b'\0', stro)
        nm = d[stro:e].decode('latin1')
        idx, = struct.unpack_from('<H', d, ord_rva and r2o(ord_rva) + i * 2 or 0)
        frva, = struct.unpack_from('<I', d, aoff + idx * 4)
        out[nm] = frva
    return out


# ---------------- 调试结构 ----------------
class EXCEPTION_RECORD(ctypes.Structure):
    _fields_ = [('ExceptionCode', wintypes.DWORD), ('ExceptionFlags', wintypes.DWORD),
                ('ExceptionRecord', ctypes.c_void_p), ('ExceptionAddress', ctypes.c_void_p),
                ('NumberParameters', wintypes.DWORD),
                ('ExceptionInformation', ctypes.c_ulonglong * 15)]


class EXC_INFO(ctypes.Structure):
    _fields_ = [('ExceptionRecord', EXCEPTION_RECORD), ('dwFirstChance', wintypes.DWORD)]


class LOAD_DLL_INFO(ctypes.Structure):
    _fields_ = [('hFile', wintypes.HANDLE), ('lpBaseOfDll', ctypes.c_void_p),
                ('dwDebugInfoFileOffset', wintypes.DWORD), ('nDebugInfoSize', wintypes.DWORD),
                ('lpImageName', ctypes.c_void_p), ('fUnicode', wintypes.WORD)]


class UNION(ctypes.Union):
    _fields_ = [('Exception', EXC_INFO), ('LoadDll', LOAD_DLL_INFO),
                ('raw', ctypes.c_byte * 256)]


class DEBUG_EVENT(ctypes.Structure):
    _fields_ = [('dwDebugEventCode', wintypes.DWORD), ('dwProcessId', wintypes.DWORD),
                ('dwThreadId', wintypes.DWORD), ('u', UNION)]


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


CONTEXT_FULL = 0x10007
# 注意：WOW64_CONTEXT 只有 Dr0-Dr3 + Dr6-Dr7（没有 Dr4/Dr5），
# 64 位调试器读 32 位进程必须用这个布局，否则所有寄存器都会错位。
class CONTEXT(ctypes.Structure):
    _fields_ = [('ContextFlags', wintypes.DWORD),
                ('Dr0', wintypes.DWORD), ('Dr1', wintypes.DWORD),
                ('Dr2', wintypes.DWORD), ('Dr3', wintypes.DWORD),
                ('Dr6', wintypes.DWORD), ('Dr7', wintypes.DWORD),
                ('FloatSave', ctypes.c_byte * 112),
                ('SegGs', wintypes.DWORD), ('SegFs', wintypes.DWORD),
                ('SegEs', wintypes.DWORD), ('SegDs', wintypes.DWORD),
                ('Edi', wintypes.DWORD), ('Esi', wintypes.DWORD), ('Ebx', wintypes.DWORD),
                ('Edx', wintypes.DWORD), ('Ecx', wintypes.DWORD), ('Eax', wintypes.DWORD),
                ('Ebp', wintypes.DWORD), ('Eip', wintypes.DWORD),
                ('SegCs', wintypes.DWORD), ('EFlags', wintypes.DWORD),
                ('Esp', wintypes.DWORD), ('SegSs', wintypes.DWORD),
                ('Extended', ctypes.c_byte * 512)]


# ---------------- 全局状态 ----------------
logbuf = deque(maxlen=4000)
logfile = None
hp = None
mods = {}            # 模块基址 -> 名字
hooks = {}           # 地址 -> (dll, 函数名, 参数说明)
orig_bytes = {}      # 地址 -> 原字节
pending_ret = {}     # 返回地址 -> (函数名, 调用序号)
temp_off = []        # [(addr, orig, persist)] 单步后需要恢复断点
call_seq = [0]
t00 = [0.0]


def L(msg):
    logbuf.append(msg)
    if logfile:
        logfile.write(msg + '\n')
        logfile.flush()
    print(msg, flush=True)


def get_ctx(tid):
    h = k32.OpenThread(0x1F03FF, False, tid)
    if not h:
        return None
    c = CONTEXT(); c.ContextFlags = CONTEXT_FULL
    ok = False
    wg = getattr(k32, 'Wow64GetThreadContext', None)
    if wg:
        ok = bool(wg(h, ctypes.byref(c)))
    if not ok:
        ok = bool(k32.GetThreadContext(h, ctypes.byref(c)))
    k32.CloseHandle(h)
    return c if ok else None


def set_ctx(tid, c):
    h = k32.OpenThread(0x1F03FF, False, tid)
    if not h:
        return False
    ok = False
    ws = getattr(k32, 'Wow64SetThreadContext', None)
    if ws:
        ok = bool(ws(h, ctypes.byref(c)))
    if not ok:
        ok = bool(k32.SetThreadContext(h, ctypes.byref(c)))
    k32.CloseHandle(h)
    return ok


def readmem(addr, n):
    buf = ctypes.create_string_buffer(n)
    got = ctypes.c_size_t(0)
    if k32.ReadProcessMemory(hp, ctypes.c_void_p(addr), buf, n, ctypes.byref(got)):
        return buf.raw[:got.value]
    return b''


def read_cstr(addr, maxn=260):
    if not addr:
        return ''
    d = readmem(addr, maxn)
    i = d.find(b'\0')
    return d[:i if i >= 0 else len(d)].decode('gbk', 'replace')


def read_u32(addr):
    d = readmem(addr, 4)
    return struct.unpack('<I', d)[0] if len(d) == 4 else 0


def put_bp(addr, dll, fn, params, persist=True):
    """在 addr 写入 int3"""
    if addr in orig_bytes:
        return
    orig = readmem(addr, 1)
    if not orig:
        return
    old = wintypes.DWORD()
    k32.VirtualProtectEx(hp, ctypes.c_void_p(addr), 1, 0x40, ctypes.byref(old))
    w = ctypes.c_size_t(0)
    okw = k32.WriteProcessMemory(hp, ctypes.c_void_p(addr), b'\xcc', 1, ctypes.byref(w))
    k32.VirtualProtectEx(hp, ctypes.c_void_p(addr), 1, old.value, ctypes.byref(old))
    if not okw or readmem(addr, 1) != b'\xcc':
        L('  !! 断点写入失败 @ %s (%s!%s) err=%d'
          % (hex(addr), dll, fn, ctypes.get_last_error()))
        return
    orig_bytes[addr] = orig
    hooks[addr] = (dll, fn, params, persist)


def remove_bp(addr, persist):
    """临时移除断点，恢复原字节；persist=True 表示单步后要重新装上"""
    if addr not in orig_bytes:
        return
    old = wintypes.DWORD()
    k32.VirtualProtectEx(hp, ctypes.c_void_p(addr), 1, 0x40, ctypes.byref(old))
    k32.WriteProcessMemory(hp, ctypes.c_void_p(addr), orig_bytes[addr], 1, None)
    k32.VirtualProtectEx(hp, ctypes.c_void_p(addr), 1, old.value, ctypes.byref(old))
    temp_off.append((addr, persist))


def rearm_all():
    for addr, persist in temp_off:
        if persist and addr in orig_bytes:
            old = wintypes.DWORD()
            k32.VirtualProtectEx(hp, ctypes.c_void_p(addr), 1, 0x40, ctypes.byref(old))
            k32.WriteProcessMemory(hp, ctypes.c_void_p(addr), b'\xcc', 1, None)
            k32.VirtualProtectEx(hp, ctypes.c_void_p(addr), 1, old.value, ctypes.byref(old))
    temp_off.clear()


def where(addr):
    best = None
    for base, name in mods.items():
        if base <= addr and (best is None or base > best[0]):
            best = (base, name)
    if best:
        return '%s+0x%X' % (best[1], addr - best[0])
    return hex(addr)


def on_call(addr, ctx):
    dll, fn, params, _p = hooks[addr]
    call_seq[0] += 1
    seq = call_seq[0]
    t = time.time() - t00[0]
    args = []
    for idx, typ in params:
        v = read_u32(ctx.Esp + 4 * idx)
        if typ == 's':
            if v < 0x10000:      # 可能是 ordinal
                args.append('#%d' % v)
            else:
                args.append(repr(read_cstr(v)))
        elif typ == 'x':
            args.append('0x%X' % v)
        else:
            args.append(str(v))
    L('[%7.2fs] #%d CALL %s!%s(%s)  tid=%d  from=%s'
      % (t, seq, dll, fn, ', '.join(args), ctx.Eip and 0, where(read_u32(ctx.Esp))))
    # 在返回地址埋一次性断点，用于取返回值
    ret = read_u32(ctx.Esp)
    if ret and ret not in orig_bytes:
        put_bp(ret, dll, fn + '::ret', [], persist=False)
        pending_ret[ret] = (fn, seq)


def on_return(addr, ctx):
    fn, seq = pending_ret.pop(addr, ('?', 0))
    eax = ctx.Eax
    note = ''
    if fn == 'CreateFileA':
        note = '  ==> 失败(返回 -1)' if eax == 0xFFFFFFFF else '  ==> 句柄 0x%X' % eax
    elif fn == 'GetProcAddress':
        note = '  ==> 返回 NULL !!!' if eax == 0 else '  ==> 0x%08X' % eax
    elif fn == 'LoadLibraryA':
        note = '  ==> 失败(NULL)' if eax == 0 else '  ==> 模块 0x%08X' % eax
    elif fn == 'GetDriveTypeA':
        note = '  ==> 类型 %d (5=CDROM)' % eax
    elif fn == 'GetFileAttributesA':
        note = '  ==> 失败(-1)' if eax == 0xFFFFFFFF else '  ==> 属性 0x%X' % eax
    elif fn == 'mciSendStringA':
        note = '  ==> 错误码 0x%08X' % eax if eax else '  ==> 成功'
    elif fn == 'GetLastError' or fn == 'GetVolumeInformationA':
        note = '  ==> %d%s' % (eax, ' (失败)' if eax == 0 else '')
    L('          #%d RET  %s = 0x%08X%s' % (seq, fn, eax, note))


def dump_crash(ev, r, tag):
    c = r.ExceptionCode
    addr = r.ExceptionAddress or 0
    ctx = get_ctx(ev.dwThreadId)
    L('')
    L('=' * 74)
    L('### %s  %s (0x%08X)  首次=%s' % (tag, EXC.get(c, hex(c)), c,
                                        bool(ev.u.Exception.dwFirstChance)))
    L('异常地址 VA=0x%08X  %s' % (addr, where(addr)))
    if 0x400000 <= addr < 0x540000:
        L('  >> 主模块 RVA = 0x%X (文件偏移可用 .rev 对照)' % (addr - IMAGEBASE))
    if c == 0xC0000005 and r.NumberParameters:
        op = r.ExceptionInformation[0]; tgt = r.ExceptionInformation[1]
        L('操作=%s (0读 1写 8执行) 目标=0x%08X %s' % (op, tgt, where(tgt)))
    if ctx:
        L('EAX=%08X EBX=%08X ECX=%08X EDX=%08X' % (ctx.Eax, ctx.Ebx, ctx.Ecx, ctx.Edx))
        L('ESI=%08X EDI=%08X EBP=%08X ESP=%08X EIP=%08X'
          % (ctx.Esi, ctx.Edi, ctx.Ebp, ctx.Esp, ctx.Eip))
        if ctx.Esp:
            L('栈顶 8 dword (最近的调用返回地址):')
            st = readmem(ctx.Esp, 32)
            for j in range(0, len(st) - 3, 4):
                v = struct.unpack('<I', st[j:j + 4])[0]
                L('    [%08X] %08X  %s%s' % (ctx.Esp + j, v, where(v),
                                             '   <== 主模块' if 0x400000 <= v < 0x540000 else ''))
        ebp = ctx.Ebp
        L('EBP 链回溯:')
        for j in range(14):
            if not ebp or ebp & 3:
                break
            d = readmem(ebp, 8)
            if len(d) < 8:
                break
            prev, ret = struct.unpack('<II', d)
            L('    #%d ret=0x%08X %s%s' % (j, ret, where(ret),
                                           '   <== 主模块' if 0x400000 <= ret < 0x540000 else ''))
            if prev <= ebp:
                break
            ebp = prev
    L('--- 崩溃前最近 25 次调用 ---')
    for m in list(logbuf)[-25:]:
        L('    ' + m)
    L('=' * 74)
    L('')


def main():
    global hp, logfile
    logfile = open(LOGPATH, 'w', encoding='utf-8', errors='replace')
    L('=== 太阁立志传2 API 追踪日志 ===')
    L('目标: %s' % EXE)
    L('开始时间: %s' % time.strftime('%Y-%m-%d %H:%M:%S'))
    L('')

    # 预解析系统 DLL 导出表
    exports = {}
    for dll in HOOKS:
        p = os.path.join(SYSDIR, dll)
        if os.path.exists(p):
            try:
                exports[dll] = pe_exports(p)
                L('已解析 %s 导出表: %d 个函数' % (dll, len(exports[dll])))
            except Exception as e:
                L('解析 %s 失败: %s' % (dll, e))
        else:
            L('未找到 %s' % p)

    si = STARTUPINFO(); si.cb = ctypes.sizeof(si)
    pi = PROCESS_INFORMATION()
    ok = k32.CreateProcessA(EXE.encode(), None, None, None, False, 0x00000001,
                            None, CWD.encode(), ctypes.byref(si), ctypes.byref(pi))
    if not ok:
        L('CreateProcess 失败 %d' % ctypes.get_last_error())
        sys.exit(1)
    hp = pi.hProcess
    mods[IMAGEBASE] = 'MAIN'
    L('进程已启动 pid=%d' % pi.dwProcessId)
    t00[0] = time.time()
    fatal = False

    def find_main_window(pid):
        best = 0; res = None
        WNDENUMPROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
        state = {'best': 0, 'hw': None}

        def cb(hwnd, lp):
            p = wintypes.DWORD()
            u32.GetWindowThreadProcessId(hwnd, ctypes.byref(p))
            if p.value != pid:
                return True
            cn = ctypes.create_string_buffer(256)
            u32.GetClassNameA(hwnd, cn, 256)
            if cn.value.decode('latin1') in ('MSCTFIME UI', 'IME', 'Default IME'):
                return True
            r = wintypes.RECT(); u32.GetWindowRect(hwnd, ctypes.byref(r))
            sz = (r.right - r.left) * (r.bottom - r.top)
            if u32.IsWindowVisible(hwnd) and sz > state['best']:
                state['best'] = sz; state['hw'] = hwnd
            return True

        u32.EnumWindows(WNDENUMPROC(cb), 0)
        return state['hw']

    last_key = [0.0]

    while time.time() - t00[0] < RUN and not fatal:
        ev = DEBUG_EVENT()
        if not k32.WaitForDebugEvent(ctypes.byref(ev), 120):
            # 空闲：周期性按键，跳过开场动画 / 推进菜单
            if AUTO_KEYS and time.time() - t00[0] - last_key[0] >= 2.5:
                last_key[0] = time.time() - t00[0]
                hw = find_main_window(pi.dwProcessId)
                if hw:
                    for vk in (0x0D, 0x20, 0x1B):      # Enter / Space / Esc
                        u32.PostMessageA(hw, 0x0100, vk, 0)
                        u32.PostMessageA(hw, 0x0101, vk, 0)
            continue
        code = ev.dwDebugEventCode
        cont = 0x00010002

        if code == 6:      # LOAD_DLL
            b = ev.u.LoadDll.lpBaseOfDll or 0
            name = ''
            try:
                p = ev.u.LoadDll.lpImageName
                if p:
                    far = ctypes.c_void_p()
                    if k32.ReadProcessMemory(hp, ctypes.c_void_p(p), ctypes.byref(far),
                                             ctypes.sizeof(far), None):
                        raw = readmem(far.value or 0, 520)
                        name = (raw.decode('utf-16-le', 'ignore') if ev.u.LoadDll.fUnicode
                                else raw.decode('latin1', 'ignore')).split('\0')[0]
            except Exception:
                pass
            nm = os.path.basename(name)
            mods[b] = nm or hex(b)
            dllkey = nm.lower()
            if dllkey in exports:
                ex = exports[dllkey]
                installed = 0
                for fn, params in HOOKS[dllkey]:
                    rva = ex.get(fn)
                    if rva:
                        put_bp(b + rva, dllkey, fn, params)
                        installed += 1
                    else:
                        L('  (%s 里没有 %s)' % (dllkey, fn))
                L('已加载 %s @0x%08X，安装 %d 个断点' % (nm, b, installed))

        elif code == 1:    # EXCEPTION
            r = ev.u.Exception.ExceptionRecord
            c = r.ExceptionCode
            addr = r.ExceptionAddress or 0
            if c == 0x80000003:                     # int3 断点
                bp_addr = addr  # 异常地址就是 int3 所在地址
                ctx = get_ctx(ev.dwThreadId)
                if ctx and bp_addr in hooks:
                    dll, fn, params, persist = hooks[bp_addr]
                    # EIP 已越过 int3，回退并恢复原指令，单步执行
                    ctx.Eip = bp_addr
                    if fn.endswith('::ret'):
                        on_return(bp_addr, ctx)
                        del hooks[bp_addr]
                        orig_bytes.pop(bp_addr, None)
                    else:
                        on_call(bp_addr, ctx)
                    remove_bp(bp_addr, persist)
                    ctx.EFlags |= 0x100              # TF 单步
                    set_ctx(ev.dwThreadId, ctx)
                elif ctx:
                    # 不是我们的断点：放行
                    pass
            elif c == 0x80000004:                   # 单步结束
                rearm_all()
                ctx = get_ctx(ev.dwThreadId)
                if ctx:
                    ctx.EFlags &= ~0x100
                    set_ctx(ev.dwThreadId, ctx)
            elif c in (0x406D1388, 0x4000001F, 0x40010005):
                cont = 0x80010001                    # 交还程序自己处理
            elif not ev.u.Exception.dwFirstChance:   # 未处理 => 进程会死
                dump_crash(ev, r, '致命异常（未被处理）')
                fatal = True
                cont = 0x80010001
            else:
                # 其它首次异常：必须交还给程序自身的 SEH，
                # 否则会被调试器"吞掉"导致程序卡在同一条指令上反复触发。
                if (c in EXC and 0x400000 <= addr < 0x540000) or (c == 0xC0000005 and addr == 0):
                    dump_crash(ev, r, '首次异常（交给程序 SEH）')
                cont = 0x80010001

        elif code == 5:    # EXIT_PROCESS
            L('进程退出，退出码 = %d' % struct.unpack('<I', bytes(ev.u.raw[:4]))[0])
            fatal = True

        k32.ContinueDebugEvent(ev.dwProcessId, ev.dwThreadId, cont)

    if not fatal:
        L('')
        L('运行 %.0f 秒结束（未捕获致命异常）' % RUN)
    L('')
    L('=== 调用总次数: %d ===' % call_seq[0])
    logfile.close()
    try:
        k32.DebugActiveProcessStop(pi.dwProcessId)
    except Exception:
        pass
    k32.TerminateProcess(hp, 0)
    k32.CloseHandle(pi.hThread); k32.CloseHandle(hp)


if __name__ == '__main__':
    main()
