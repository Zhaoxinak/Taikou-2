"""
太阁立志传2 —— 零干扰崩溃监视器（"外置 log 系统"）

设计原则：
  * 不插任何 int3 断点 -> 游戏全速运行，手感和平时完全一样
  * 由玩家手动操作进入大地图，崩溃瞬间由调试器接管
  * 崩溃时输出：异常类型/地址、寄存器、栈内容、EBP 回溯、
    崩溃点机器码、已加载模块表、崩溃前最近 N 次异常
  * 同时把主模块内存 dump 成文件，方便离线分析
  * 可选周期性截屏（PNG），用于确认进度

用法:
    python .rev/spy.py [exe] [秒数] [--shot N] [--hooks] [--freeze]
      --shot N   每 N 秒截一张图（默认不截）
      --hooks    额外安装文件 API 断点（会降速，一般不用）
      --freeze   崩溃后不杀进程，挂起等待人工附加
"""
import ctypes, os, sys, time, struct, zlib
from ctypes import wintypes
from collections import deque

k32 = ctypes.WinDLL('kernel32', use_last_error=True)
u32 = ctypes.WinDLL('user32', use_last_error=True)
g32 = ctypes.WinDLL('gdi32', use_last_error=True)

EXE = sys.argv[1] if len(sys.argv) > 1 else r'F:\Games\Taikou 2\Taikou2 Original\TAIK2W95_clean.exe'
RUN = float(sys.argv[2]) if len(sys.argv) > 2 else 300.0
SHOT = 0.0
FREEZE = '--freeze' in sys.argv
USE_HOOKS = '--hooks' in sys.argv
CRASHSHOT = '--crashshot' in sys.argv
if '--shot' in sys.argv:
    i = sys.argv.index('--shot')
    SHOT = float(sys.argv[i + 1]) if i + 1 < len(sys.argv) else 5.0

CWD = os.path.dirname(EXE)
LOGPATH = os.path.join(CWD, '.rev', 'spy.log')
SHOTDIR = os.path.join(CWD, '.rev', 'spyshot')
os.makedirs(SHOTDIR, exist_ok=True)

IMAGEBASE = 0x400000
IMAGESIZE = 0x136000          # 主模块大小（clean 版）
SYSDIR = os.path.join(os.environ.get('SystemRoot', r'C:\Windows'), 'SysWOW64')
if not os.path.isdir(SYSDIR):
    SYSDIR = os.path.join(os.environ.get('SystemRoot', r'C:\Windows'), 'System32')

EXC = {
    0xC0000005: 'ACCESS_VIOLATION 访问违规',
    0xC0000094: 'ILLEGAL_INSTRUCTION 非法指令',
    0xC0000095: 'BREAKPOINT',
    0xC00000FD: 'STACK_OVERFLOW 栈溢出',
    0xC000008E: 'DIVIDE_BY_ZERO 除零',
    0xC000008C: 'ARRAY_BOUNDS_EXCEEDED 数组越界',
    0xC0000409: 'STACK_BUFFER_OVERRUN 栈缓冲溢出（/GS 检测到）',
    0xC0000025: 'NONCONTINUABLE',
    0xC0000026: 'INVALID_DISPOSITION 异常处理链被破坏',
    0xC0000374: 'HEAP_CORRUPTION 堆损坏',
    0xC0000602: 'FAIL_FAST（解码器等主动自杀）',
    0xC000041D: 'FATAL_USER_CALLBACK',
    0xC000001D: 'ILLEGAL_INSTRUCTION',
    0xC0000006: 'IN_PAGE_ERROR 内存页无法载入（读光盘失败等）',
    0x80000003: 'BREAKPOINT',
}

HOOKS = {
    'kernel32.dll': [
        ('CreateFileA', [(1, 's'), (2, 'x')]),
        ('_lopen', [(1, 's'), (2, 'i')]),
        ('_lread', []),
        ('GetDriveTypeA', [(1, 's')]),
        ('GetProcAddress', [(2, 's')]),
        ('LoadLibraryA', [(1, 's')]),
    ],
}


# ---------------- PE 导出表 ----------------
def pe_exports(path):
    d = open(path, 'rb').read()
    e_lfanew = struct.unpack_from('<I', d, 0x3C)[0]
    if struct.unpack_from('<I', d, e_lfanew)[0] != 0x4550:
        return {}
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
    if off is None:
        return {}
    (flags, ts, ver, name_rva, base, naddr, nname,
     addr_rva, name_tab, ord_rva) = struct.unpack_from('<IIIIIIIIII', d, off)
    aoff = r2o(addr_rva); noff = r2o(name_tab)
    oo = r2o(ord_rva)
    out = {}
    for i in range(nname):
        nr, = struct.unpack_from('<I', d, noff + i * 4)
        stro = r2o(nr)
        if stro is None:
            continue
        e = d.index(b'\0', stro)
        nm = d[stro:e].decode('latin1')
        idx, = struct.unpack_from('<H', d, oo + i * 2)
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


class CONTEXT(ctypes.Structure):
    """WOW64_CONTEXT：只有 Dr0-Dr3 + Dr6-Dr7，64 位调试器读 32 位进程必须用它"""
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


# ---------------- 全局 ----------------
hp = None
logfile = None
mods = {}            # base -> (name, size)
recent = deque(maxlen=60)
hooks = {}
orig_bytes = {}
pending_ret = {}
temp_off = []
t00 = [0.0]
seq = [0]
shot_n = [0]
last_shot = [0.0]


def L(msg):
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
    if not addr:
        return b''
    buf = ctypes.create_string_buffer(n)
    got = ctypes.c_size_t(0)
    if k32.ReadProcessMemory(hp, ctypes.c_void_p(addr), buf, n, ctypes.byref(got)):
        return buf.raw[:got.value]
    return b''


def read_u32(addr):
    d = readmem(addr, 4)
    return struct.unpack('<I', d)[0] if len(d) == 4 else 0


def read_cstr(addr, maxn=300):
    if not addr or addr < 0x10000:
        return ''
    d = readmem(addr, maxn)
    i = d.find(b'\0')
    return d[:i if i >= 0 else len(d)].decode('gbk', 'replace')


def where(addr):
    best = None
    for base, (name, size) in mods.items():
        if base <= addr and (best is None or base > best[0]):
            best = (base, name, size)
    if best:
        base, name, size = best
        if size and addr - base > size:
            return '%s+0x%X(超界!)' % (name, addr - base)
        return '%s+0x%X' % (name, addr - base)
    return hex(addr)


# ---------------- 截屏 ----------------
def write_png(path, w, h, rgb):
    raw = b''.join(b'\x00' + rgb[y * w * 3:(y + 1) * w * 3] for y in range(h))

    def chunk(typ, data):
        return (struct.pack('>I', len(data)) + typ + data +
                struct.pack('>I', zlib.crc32(typ + data) & 0xFFFFFFFF))

    png = (b'\x89PNG\r\n\x1a\n'
           + chunk(b'IHDR', struct.pack('>IIBBBBB', w, h, 8, 2, 0, 0, 0))
           + chunk(b'IDAT', zlib.compress(raw, 6))
           + chunk(b'IEND', b''))
    open(path, 'wb').write(png)


def grab(hwnd):
    r = wintypes.RECT()
    if not u32.GetWindowRect(hwnd, ctypes.byref(r)):
        return None
    w, h = r.right - r.left, r.bottom - r.top
    if w <= 0 or h <= 0:
        return None
    hdc = u32.GetWindowDC(hwnd)
    if not hdc:
        return None
    mdc = g32.CreateCompatibleDC(hdc)
    bmp = g32.CreateCompatibleBitmap(hdc, w, h)
    old = g32.SelectObject(mdc, bmp)
    ok = g32.BitBlt(mdc, 0, 0, w, h, hdc, 0, 0, 0x00CC0020)
    g32.SelectObject(mdc, old)
    # 注意：BITMAPINFO 必须用可写缓冲，GetDIBits 会回写 biSizeImage 等字段；
    # 传 struct.pack 得到的只读 bytes 会让 Python 直接段错误。
    bis = ctypes.create_string_buffer(
        struct.pack('<IiiHHIIiiII', 40, w, -h, 1, 24, 0, w * h * 3, 0, 0, 0, 0), 40)
    buf = ctypes.create_string_buffer(w * h * 3)
    g32.GetDIBits(mdc, bmp, 0, h, buf, bis, 0)
    g32.DeleteObject(bmp); g32.DeleteDC(mdc); u32.ReleaseDC(hwnd, hdc)
    return (w, h, buf.raw[:w * h * 3]) if ok else None


def find_main_window(pid):
    state = {'best': 0, 'hw': None}
    WNDENUMPROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)

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


# ---------------- 断点（可选） ----------------
def put_bp(addr, dll, fn, params, persist=True):
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
        return
    orig_bytes[addr] = orig
    hooks[addr] = (dll, fn, params, persist)


def remove_bp(addr, persist):
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


def on_call(addr, ctx):
    dll, fn, params, _p = hooks[addr]
    seq[0] += 1
    t = time.time() - t00[0]
    args = []
    for idx, typ in params:
        v = read_u32(ctx.Esp + 4 * idx)
        if typ == 's':
            args.append(repr(read_cstr(v)) if v >= 0x10000 else '#%d' % v)
        elif typ == 'x':
            args.append('0x%X' % v)
        else:
            args.append(str(v))
    L('[%7.2fs] #%d CALL %s!%s(%s)  from=%s'
      % (t, seq[0], dll, fn, ', '.join(args), where(read_u32(ctx.Esp))))
    ret = read_u32(ctx.Esp)
    if ret and ret not in orig_bytes:
        put_bp(ret, dll, fn + '::ret', [], persist=False)
        pending_ret[ret] = (fn, seq[0])


def on_return(addr, ctx):
    fn, s = pending_ret.pop(addr, ('?', 0))
    eax = ctx.Eax
    note = ''
    if fn == 'CreateFileA':
        note = '  ==> 失败(-1) !!!' if eax == 0xFFFFFFFF else '  ==> 句柄 0x%X' % eax
    elif fn == '_lopen':
        note = '  ==> 失败(-1) !!!' if eax == 0xFFFFFFFF else '  ==> 句柄 %d' % eax
    elif fn == 'GetProcAddress':
        note = '  ==> NULL !!!' if eax == 0 else '  ==> 0x%08X' % eax
    elif fn == 'LoadLibraryA':
        note = '  ==> 失败(NULL) !!!' if eax == 0 else '  ==> 0x%08X' % eax
    elif fn == 'GetDriveTypeA':
        note = '  ==> %d (5=CDROM)' % eax
    L('          #%d RET  %s = 0x%08X%s' % (s, fn, eax, note))


# ---------------- 崩溃 dump ----------------
def dump_crash(ev, r, tag, pid):
    c = r.ExceptionCode
    addr = r.ExceptionAddress or 0
    ctx = get_ctx(ev.dwThreadId)
    L('')
    L('=' * 78)
    L('### %s' % tag)
    L('异常码 0x%08X  %s' % (c, EXC.get(c, '(未知)')))
    L('发生时刻: 启动后 %.2f 秒' % (time.time() - t00[0]))
    L('线程 tid=%d' % ev.dwThreadId)
    L('异常地址 VA=0x%08X   %s' % (addr, where(addr)))
    if IMAGEBASE <= addr < IMAGEBASE + IMAGESIZE:
        rva = addr - IMAGEBASE
        L('   >> 主模块 RVA = 0x%X' % rva)
        L('   >> clean_dump.bin 文件偏移 = 0x%X' % rva)
        L('   >> TAIK2W95_clean.exe 文件偏移 = 0x%X (.text节 VA0x1000->raw0x400, 需按节判断)' % rva)
    if c == 0xC0000005 and r.NumberParameters >= 2:
        op = r.ExceptionInformation[0]; tgt = r.ExceptionInformation[1]
        L('操作 = %d (%s)   目标地址 = 0x%08X  %s'
          % (op, {0: '读', 1: '写', 8: '执行'}.get(op, '?'), tgt, where(tgt)))
    if not ctx:
        L('(无法读取线程上下文)')
    else:
        L('')
        L('寄存器:')
        L('  EAX=%08X  EBX=%08X  ECX=%08X  EDX=%08X'
          % (ctx.Eax, ctx.Ebx, ctx.Ecx, ctx.Edx))
        L('  ESI=%08X  EDI=%08X  EBP=%08X  ESP=%08X  EIP=%08X'
          % (ctx.Esi, ctx.Edi, ctx.Ebp, ctx.Esp, ctx.Eip))
        L('  EFLAGS=%08X  CS=%04X SS=%04X DS=%04X ES=%04X FS=%04X GS=%04X'
          % (ctx.EFlags, ctx.SegCs, ctx.SegSs, ctx.SegDs, ctx.SegEs, ctx.SegFs, ctx.SegGs))
        L('')
        L('崩溃点机器码 (EIP-16 .. EIP+48):')
        st = ctx.Eip - 16 if ctx.Eip >= 16 else ctx.Eip
        code = readmem(st, 64)
        for j in range(0, len(code), 16):
            row = code[j:j + 16]
            mark = ' <== EIP' if st + j <= ctx.Eip < st + j + 16 else ''
            L('  %08X  %s  %s%s'
              % (st + j, row.hex(' '),
                 ''.join(chr(b) if 32 <= b < 127 else '.' for b in row), mark))
        L('')
        L('栈顶 16 dword:')
        sp = ctx.Esp
        sd = readmem(sp, 64)
        for j in range(0, len(sd) - 3, 4):
            v = struct.unpack('<I', sd[j:j + 4])[0]
            txt = ''
            if v >= 0x10000:
                s = read_cstr(v, 40)
                if s and all(32 <= ord(ch) < 127 or ord(ch) > 127 for ch in s[:20]) and len(s) >= 3:
                    txt = '   "%s"' % s[:40]
            L('    [ESP+%02X] %08X  %s%s%s'
              % (j, v, where(v), '   <== 主模块' if IMAGEBASE <= v < IMAGEBASE + IMAGESIZE else '', txt))
        L('')
        L('EBP 调用栈回溯:')
        ebp = ctx.Ebp
        for j in range(22):
            if not ebp or ebp & 3 or ebp < 0x1000:
                break
            d = readmem(ebp, 8)
            if len(d) < 8:
                break
            prev, ret = struct.unpack('<II', d)
            arg1 = read_u32(ebp + 8)
            L('    #%-2d ret=0x%08X %-28s arg1=0x%08X%s'
              % (j, ret, where(ret), arg1,
                 '   <== 主模块' if IMAGEBASE <= ret < IMAGEBASE + IMAGESIZE else ''))
            if prev <= ebp or prev - ebp > 0x100000:
                break
            ebp = prev

    L('')
    L('崩溃前最近 30 次异常/调用:')
    for m in list(recent)[-30:]:
        L('    ' + m)
    L('')
    L('已加载模块 (基址 / 名称):')
    for base in sorted(mods):
        nm, sz = mods[base]
        L('    0x%08X  %-40s size=0x%X' % (base, nm, sz or 0))

    # dump 主模块内存，便于离线分析
    try:
        mem = readmem(IMAGEBASE, IMAGESIZE)
        if len(mem) > 0x1000:
            fn = os.path.join(CWD, '.rev', 'crash_mem.bin')
            open(fn, 'wb').write(mem)
            L('')
            L('主模块内存已 dump -> %s (%d 字节)' % (fn, len(mem)))
    except Exception as e:
        L('dump 内存失败: %s' % e)

    # 崩溃瞬间的截图默认关闭：崩溃后窗口可能已销毁，GDI 抓图会让调试器自身段错误。
    # 需要时用 --crashshot 打开。
    if CRASHSHOT:
        try:
            hw = find_main_window(pid)
            if hw and u32.IsWindow(hw):
                g = grab(hw)
                if g:
                    w, h, rgb = g
                    fn = os.path.join(SHOTDIR, 'crash.png')
                    write_png(fn, w, h, rgb)
                    L('崩溃瞬间截图 -> %s (%dx%d)' % (fn, w, h))
        except Exception as e:
            L('(崩溃截图失败: %s)' % e)
    L('=' * 78)
    L('')


# ---------------- 主流程 ----------------
def main():
    global hp, logfile
    logfile = open(LOGPATH, 'w', encoding='utf-8', errors='replace')
    L('=== 太阁立志传2 崩溃监视器 ===')
    L('目标  : %s' % EXE)
    L('模式  : %s' % ('断点追踪' if USE_HOOKS else '零干扰（无断点，全速）'))
    L('时长  : %.0f 秒' % RUN)
    L('开始  : %s' % time.strftime('%Y-%m-%d %H:%M:%S'))
    L('')
    L('>>> 请正常操作游戏，进入到崩溃的那一步 <<<')
    L('')

    exports = {}
    if USE_HOOKS:
        for dll in HOOKS:
            p = os.path.join(SYSDIR, dll)
            if os.path.exists(p):
                try:
                    exports[dll] = pe_exports(p)
                    L('已解析 %s: %d 个导出' % (dll, len(exports[dll])))
                except Exception as e:
                    L('解析 %s 失败: %s' % (dll, e))

    si = STARTUPINFO(); si.cb = ctypes.sizeof(si)
    pi = PROCESS_INFORMATION()
    ok = k32.CreateProcessA(EXE.encode(), None, None, None, False, 0x00000001,
                            None, CWD.encode(), ctypes.byref(si), ctypes.byref(pi))
    if not ok:
        L('CreateProcess 失败 %d' % ctypes.get_last_error())
        sys.exit(1)
    hp = pi.hProcess
    mods[IMAGEBASE] = ('MAIN(太阁2)', IMAGESIZE)
    L('进程已启动 pid=%d' % pi.dwProcessId)
    L('')
    t00[0] = time.time()
    fatal = False
    exit_code = [None]

    while time.time() - t00[0] < RUN and not fatal:
        ev = DEBUG_EVENT()
        if not k32.WaitForDebugEvent(ctypes.byref(ev), 200):
            if SHOT > 0 and time.time() - last_shot[0] >= SHOT:
                last_shot[0] = time.time()
                try:
                    hw = find_main_window(pi.dwProcessId)
                    if hw:
                        g = grab(hw)
                        if g:
                            shot_n[0] += 1
                            w, h, rgb = g
                            fn = os.path.join(SHOTDIR, 's%02d_%03.0fs.png'
                                              % (shot_n[0], time.time() - t00[0]))
                            write_png(fn, w, h, rgb)
                            L('[%6.1fs] 截图 %s (%dx%d)' % (time.time() - t00[0], fn, w, h))
                except Exception:
                    pass
            continue

        code = ev.dwDebugEventCode
        cont = 0x00010002   # DBG_CONTINUE

        if code == 6:       # LOAD_DLL
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
            nm = os.path.basename(name) or hex(b)
            sz = 0
            try:
                # 从 PEB 拿不到大小，用 PE 头读 SizeOfImage
                hdr = readmem(b, 0x400)
                if len(hdr) > 0x80 and hdr[:2] == b'MZ':
                    lf = struct.unpack_from('<I', hdr, 0x3C)[0]
                    opt = lf + 24
                    sz = struct.unpack_from('<I', hdr, opt + 56)[0]
            except Exception:
                pass
            mods[b] = (nm, sz)
            recent.append('LOAD  %s @0x%08X' % (nm, b))
            if USE_HOOKS and nm.lower() in exports:
                ex = exports[nm.lower()]
                n = 0
                for fn, params in HOOKS[nm.lower()]:
                    rva = ex.get(fn)
                    if rva:
                        put_bp(b + rva, nm.lower(), fn, params)
                        n += 1
                L('[模块] %s @0x%08X  安装 %d 断点' % (nm, b, n))

        elif code == 1:     # EXCEPTION
            r = ev.u.Exception.ExceptionRecord
            c = r.ExceptionCode
            addr = r.ExceptionAddress or 0
            first = bool(ev.u.Exception.dwFirstChance)

            if c == 0x80000003 and USE_HOOKS:
                ctx = get_ctx(ev.dwThreadId)
                if ctx and addr in hooks:
                    dll, fn, params, persist = hooks[addr]
                    ctx.Eip = addr
                    if fn.endswith('::ret'):
                        on_return(addr, ctx)
                        del hooks[addr]
                        orig_bytes.pop(addr, None)
                    else:
                        on_call(addr, ctx)
                    remove_bp(addr, persist)
                    ctx.EFlags |= 0x100
                    set_ctx(ev.dwThreadId, ctx)
            elif c == 0x80000004 and USE_HOOKS:
                rearm_all()
                ctx = get_ctx(ev.dwThreadId)
                if ctx:
                    ctx.EFlags &= ~0x100
                    set_ctx(ev.dwThreadId, ctx)
            elif c in (0x406D1388, 0x4000001F, 0x40010005, 0x80000003, 0x80000004):
                cont = 0x80010001          # 交给程序
            elif not first:
                # 第二次机会 = 程序没处理 = 真崩溃
                dump_crash(ev, r, '致命异常（程序未处理，进程即将终止）', pi.dwProcessId)
                fatal = True
                cont = 0x80010001
            else:
                # 首次异常：记录下来（轻量），然后交还程序自己的 SEH
                tgt = ''
                if c == 0xC0000005 and r.NumberParameters >= 2:
                    tgt = ' 目标=0x%08X %s 操作=%d' % (r.ExceptionInformation[1],
                                                     where(r.ExceptionInformation[1]),
                                                     r.ExceptionInformation[0])
                recent.append('[%.2fs] EXC 0x%08X @%s%s'
                              % (time.time() - t00[0], c, where(addr), tgt))
                if IMAGEBASE <= addr < IMAGEBASE + IMAGESIZE:
                    L('[首异] 0x%08X %s @主模块 RVA 0x%X%s'
                      % (c, EXC.get(c, ''), addr - IMAGEBASE, tgt))
                cont = 0x80010001

        elif code == 5:     # EXIT_PROCESS
            # u.raw 是 c_byte（有符号），必须先规整成无符号字节
            ec = struct.unpack('<I', bytes(x & 0xFF for x in ev.u.raw[:4]))[0]
            exit_code[0] = ec
            L('')
            L('进程退出，退出码 = 0x%08X (%d)' % (ec, ec if ec < 2 ** 31 else ec - 2 ** 32))
            if ec not in (0,):
                L('>>> 非正常退出：0x%08X = %s' % (ec, EXC.get(ec, '(非异常码)')))
                L('崩溃前最近 30 条记录:')
                for m in list(recent)[-30:]:
                    L('    ' + m)
            fatal = True

        k32.ContinueDebugEvent(ev.dwProcessId, ev.dwThreadId, cont)

    if not fatal:
        L('')
        L('%.0f 秒到时，未捕获崩溃（进程可能仍在正常运行）' % RUN)

    if FREEZE and fatal:
        L('进程保持挂起状态，可手动附加调试器...')
        time.sleep(120)
    L('')
    L('=== 监视结束 (调用记录 %d 条) ===' % seq[0])
    logfile.close()
    try:
        k32.DebugActiveProcessStop(pi.dwProcessId)
    except Exception:
        pass
    k32.TerminateProcess(hp, 0)
    k32.CloseHandle(pi.hThread); k32.CloseHandle(hp)


if __name__ == '__main__':
    main()
