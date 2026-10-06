"""
单线程调试器：WaitForDebugEvent 循环的间隙里做窗口探测 / 自动化推进，
任何致命异常都抓现场（寄存器 + 栈 + 模块归属 + EIP 字节）。

用法:
  python .rev/dbg_crash.py <exe> [秒数] [--ev] [--keys] [--click]
    --ev    打印每个调试事件
    --keys  周期性向主窗口发 Enter / 空格，试图推进流程
    --click 周期性点击主窗口中心及按钮位置
"""
import ctypes, os, sys, time, struct
from ctypes import wintypes

try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

k32 = ctypes.WinDLL('kernel32', use_last_error=True)
u32 = ctypes.WinDLL('user32', use_last_error=True)

EXE = sys.argv[1] if len(sys.argv) > 1 else r'F:\Games\Taikou 2\Taikou2 Original\TAIK2W95_big.exe'
RUN = float(sys.argv[2]) if len(sys.argv) > 2 else 300.0
DEBUG_EVENTS = '--ev' in sys.argv
DO_KEYS = '--keys' in sys.argv
DO_CLICK = '--click' in sys.argv
CWD = os.path.dirname(EXE)

EXC = {
    0xC0000005: 'ACCESS_VIOLATION', 0xC0000094: 'ILLEGAL_INSTRUCTION',
    0xC0000095: 'BREAKPOINT', 0xC00000FD: 'STACK_OVERFLOW',
    0xC000008E: 'DIVIDE_BY_ZERO', 0xC000001D: 'ILLEGAL_INSTRUCTION2',
    0xC0000025: 'NONCONTINUABLE', 0xC000008C: 'ARRAY_BOUNDS',
    0xC0000096: 'PRIV_INSTRUCTION', 0x80000003: 'BREAKPOINT(HARD)',
    0x406D1388: 'MSVC_ThreadName', 0xC0000093: 'FLT_DENORMAL',
    0xC0000092: 'FLT_...', 0xC0000417: 'STATUS_FAIL_FAST',
    0xE0434352: 'CLR_EXCEPTION', 0xC0000409: 'STACK_BUFFER_OVERRUN',
}


class EXCEPTION_RECORD(ctypes.Structure):
    _fields_ = [('ExceptionCode', wintypes.DWORD), ('ExceptionFlags', wintypes.DWORD),
                ('ExceptionRecord', ctypes.c_void_p), ('ExceptionAddress', ctypes.c_void_p),
                ('NumberParameters', wintypes.DWORD),
                ('ExceptionInformation', ctypes.c_ulonglong * 15)]


class EXCEPTION_DEBUG_INFO(ctypes.Structure):
    _fields_ = [('ExceptionRecord', EXCEPTION_RECORD), ('dwFirstChance', wintypes.DWORD)]


class LOAD_DLL_DEBUG_INFO(ctypes.Structure):
    _fields_ = [('hFile', wintypes.HANDLE), ('lpBaseOfDll', ctypes.c_void_p),
                ('dwDebugInfoFileOffset', wintypes.DWORD), ('nDebugInfoSize', wintypes.DWORD),
                ('lpImageName', ctypes.c_void_p), ('fUnicode', wintypes.WORD)]


class UNION(ctypes.Union):
    _fields_ = [('Exception', EXCEPTION_DEBUG_INFO), ('LoadDll', LOAD_DLL_DEBUG_INFO),
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
    _fields_ = [('ContextFlags', wintypes.DWORD),
                ('Dr0', wintypes.DWORD), ('Dr1', wintypes.DWORD), ('Dr2', wintypes.DWORD),
                ('Dr3', wintypes.DWORD), ('Dr4', wintypes.DWORD), ('Dr5', wintypes.DWORD),
                ('Dr6', wintypes.DWORD), ('Dr7', wintypes.DWORD),
                ('FloatSave', ctypes.c_byte * 112),
                ('SegGs', wintypes.DWORD), ('SegFs', wintypes.DWORD),
                ('SegEs', wintypes.DWORD), ('SegDs', wintypes.DWORD),
                ('Edi', wintypes.DWORD), ('Esi', wintypes.DWORD), ('Ebx', wintypes.DWORD),
                ('Edx', wintypes.DWORD), ('Ecx', wintypes.DWORD), ('Eax', wintypes.DWORD),
                ('Ebp', wintypes.DWORD), ('Eip', wintypes.DWORD),
                ('SegCs', wintypes.DWORD), ('EFlags', wintypes.DWORD),
                ('Esp', wintypes.DWORD), ('SegSs', wintypes.DWORD),
                ('ExtendedRegisters', ctypes.c_byte * 512)]


IMAGEBASE = 0x400000
modules = [(IMAGEBASE, 0x136000, 'MAIN')]
evcount = {}
noise = {}
crash_done = False


def readmem(h, addr, n):
    buf = ctypes.create_string_buffer(n)
    got = ctypes.c_size_t(0)
    if k32.ReadProcessMemory(h, ctypes.c_void_p(addr), buf, n, ctypes.byref(got)):
        return buf.raw[:got.value]
    return b''


def where(addr):
    for base, size, name in modules:
        if base <= addr < base + size:
            return '%s+0x%X' % (name, addr - base)
    return ''


def dump_crash(hProcess, ev, r):
    c = r.ExceptionCode
    addr = r.ExceptionAddress or 0
    hThread = k32.OpenThread(0x1F03FF, False, ev.dwThreadId)
    ctx = CONTEXT(); ctx.ContextFlags = CONTEXT_FULL
    if hThread:
        k32.GetThreadContext(hThread, ctypes.byref(ctx))
        k32.CloseHandle(hThread)
    print('\n' + '=' * 72)
    print('!!! %s (0x%08X)  首次=%s' % (EXC.get(c, hex(c)), c, bool(ev.u.Exception.dwFirstChance)))
    print('异常地址 VA=0x%08X  %s  %s' % (addr, where(addr),
                                        ('主模块 RVA=0x%X' % (addr - IMAGEBASE)) if 0x400000 <= addr < 0x540000 else ''))
    if r.NumberParameters:
        print('异常参数:', [hex(r.ExceptionInformation[i]) for i in range(min(r.NumberParameters, 4))])
    if c == 0xC0000005:
        op = r.ExceptionInformation[0]; tgt = r.ExceptionInformation[1]
        print('  操作=%s (0=读 1=写 8=执行)  目标=0x%08X %s' % (op, tgt, where(tgt)))
    print('EAX=%08X EBX=%08X ECX=%08X EDX=%08X' % (ctx.Eax, ctx.Ebx, ctx.Ecx, ctx.Edx))
    print('ESI=%08X EDI=%08X EBP=%08X ESP=%08X EIP=%08X' % (ctx.Esi, ctx.Edi, ctx.Ebp, ctx.Esp, ctx.Eip))
    print('EIP 处字节:', readmem(hProcess, ctx.Eip, 24).hex(' '))
    print('栈回溯 (EBP 链):')
    ebp = ctx.Ebp
    for i in range(12):
        if ebp == 0 or ebp & 3:
            break
        data = readmem(hProcess, ebp, 8)
        if len(data) < 8:
            break
        prev, ret = struct.unpack('<II', data)
        print('   #%d  ret=0x%08X %s   (EBP=0x%08X)' % (i, ret, where(ret), ebp))
        if prev <= ebp:
            break
        ebp = prev
    print('栈原始 (ESP 起 48 字节):')
    st = readmem(hProcess, ctx.Esp, 48)
    for i in range(0, 48, 12):
        row = st[i:i + 12]
        if len(row) < 4:
            break
        v = struct.unpack('<I', row[:4])[0]
        print('   %08X  %-24s %s' % (ctx.Esp + i, row.hex(' '), where(v)))
    print('模块列表:')
    for b, s, nm in modules:
        print('   0x%08X  %s' % (b, nm))
    # 检查内存埋点标记
    print('内存埋点标记:')
    markers = [
        (0x54B676, 'F', '游戏入口 @0x4F44B0'),
        (0x54B675, 'E', '日推进外层 @0x4A0D50'),
        (0x54B677, 'G', '日推进每日早期 @0x4A0E41'),
        (0x54B674, 'D', '日推进每日晚期 @0x4A0E47'),
        (0x54B678, 'H', '月边界 @0x4A0DED'),
    ]
    fired = []
    for va, name, desc in markers:
        data = readmem(hProcess, va, 1)
        value = data[0] if len(data) > 0 else 0
        status = '✓ 已触发' if value == 0xFF else '✗ 未触发'
        print('   [%s] 0x%08X = 0x%02X  %s  (%s)' % (name, va, value, status, desc))
        if value == 0xFF:
            fired.append(name)
    if not fired:
        print('   → 没有任何埋点被触发 (崩溃在入口之前)')
    elif 'F' in fired and 'E' not in fired:
        print('   → 崩溃在: 启动 → 日推进外层之间')
    elif 'E' in fired and 'G' not in fired:
        print('   → 崩溃在: 日推进外层 → 日推进每日早期之间')
    elif 'G' in fired and 'D' not in fired:
        print('   → 崩溃在: 日推进每日早期 → 日推进每日晚期之间')
    elif 'D' in fired and 'H' not in fired:
        print('   → 崩溃在: 日推进每日晚期之后 (非月边界)')
    elif 'H' in fired:
        print('   → 崩溃在: 月边界路径 (月结算)')
    print('=' * 72)
    sys.stdout.flush()


# ---------------- 窗口探测 ----------------
def enum_windows(pid):
    out = []
    WNDENUMPROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)

    def top(hwnd, lp):
        p = wintypes.DWORD()
        u32.GetWindowThreadProcessId(hwnd, ctypes.byref(p))
        if p.value != pid:
            return True
        n = u32.GetWindowTextLengthA(hwnd)
        buf = ctypes.create_string_buffer(n + 1)
        u32.GetWindowTextA(hwnd, buf, n + 1)
        cn = ctypes.create_string_buffer(256)
        u32.GetClassNameA(hwnd, cn, 256)
        r = wintypes.RECT(); u32.GetWindowRect(hwnd, ctypes.byref(r))
        kids = []

        def ck(h2, l2):
            kcn = ctypes.create_string_buffer(256)
            u32.GetClassNameA(h2, kcn, 256)
            kn = u32.GetWindowTextLengthA(h2)
            kb = ctypes.create_string_buffer(kn + 1)
            u32.GetWindowTextA(h2, kb, kn + 1)
            kr = wintypes.RECT(); u32.GetWindowRect(h2, ctypes.byref(kr))
            kids.append((h2, kcn.value.decode('latin1'), kb.value.decode('latin1'),
                         (kr.left, kr.top, kr.right - kr.left, kr.bottom - kr.top)))
            return True

        u32.EnumChildWindows(hwnd, WNDENUMPROC(ck), 0)
        out.append((hwnd, cn.value.decode('latin1'), buf.value.decode('latin1'),
                    (r.left, r.top, r.right - r.left, r.bottom - r.top),
                    bool(u32.IsWindowVisible(hwnd)), kids))
        return True

    u32.EnumWindows(WNDENUMPROC(top), 0)
    return out


def main():
    global crash_done
    si = STARTUPINFO(); si.cb = ctypes.sizeof(si)
    pi = PROCESS_INFORMATION()
    ok = k32.CreateProcessA(EXE.encode(), None, None, None, False, 0x00000001,
                            None, CWD.encode(), ctypes.byref(si), ctypes.byref(pi))
    print('CreateProcess:', 'OK' if ok else '失败 %d' % ctypes.get_last_error())
    if not ok:
        sys.exit(1)
    print('pid =', pi.dwProcessId, ' 目标:', EXE)
    hp = pi.hProcess
    t0 = time.time()
    seen = set()
    last_probe = 0.0
    last_key = 0.0
    step = 0

    while True:
        if crash_done or (time.time() - t0 > RUN):
            break
        ev = DEBUG_EVENT()
        got = k32.WaitForDebugEvent(ctypes.byref(ev), 150)
        now = time.time()

        if got:
            code = ev.dwDebugEventCode
            evcount[code] = evcount.get(code, 0) + 1
            if DEBUG_EVENTS:
                print('  [dbg] event=%d tid=%d' % (code, ev.dwThreadId))
            cont = 0x00010002
            if code == 6:   # LOAD_DLL
                b = ev.u.LoadDll.lpBaseOfDll or 0
                name = ''
                try:
                    p = ev.u.LoadDll.lpImageName
                    if p:
                        far = ctypes.c_void_p()
                        if k32.ReadProcessMemory(hp, ctypes.c_void_p(p), ctypes.byref(far),
                                                 ctypes.sizeof(far), None):
                            raw = readmem(hp, far.value or 0, 520)
                            name = (raw.decode('utf-16-le', 'ignore') if ev.u.LoadDll.fUnicode
                                    else raw.decode('latin1', 'ignore')).split('\0')[0]
                except Exception:
                    pass
                nm = os.path.basename(name) or hex(b)
                modules.append((b, 0x100000, nm))
                if DEBUG_EVENTS:
                    print('        DLL 0x%08X %s' % (b, nm))
                cont = 0x00010002
            elif code == 1:  # EXCEPTION
                r = ev.u.Exception.ExceptionRecord
                c = r.ExceptionCode
                # 良性异常：断点 / WOW64 伪断点 / MSVC 线程名
                if (c in (0x80000003, 0x406D1388, 0x4000001F, 0x40010005)
                        and ev.u.Exception.dwFirstChance):
                    cont = 0x00010002
                else:
                    addr = r.ExceptionAddress or 0
                    in_main = 0x400000 <= addr < 0x540000
                    # 所有异常都捕获（包括非主模块），因为崩溃可能发生在任何地方
                    dump_crash(hp, ev, r)
                    crash_done = True
                    cont = 0x80010001
            elif code == 5:  # EXIT_PROCESS
                print('进程退出, 退出码结构体首 4 字节 =', struct.unpack('<I', bytes(ev.u.raw[:4]))[0])
                crash_done = True
            k32.ContinueDebugEvent(ev.dwProcessId, ev.dwThreadId, cont)
            continue

        # ---- 超时：做窗口探测 / 自动化推进 ----
        if now - last_probe >= 2.0:
            last_probe = now
            ws = enum_windows(pi.dwProcessId)
            for hw, cls, title, rc, vis, kids in ws:
                key = (cls, title, tuple(rc))
                if key in seen:
                    continue
                seen.add(key)
                print('[%5.1fs] 窗口 %s cls=%s 标题=%r rect=%s 可见=%s 子控件=%d'
                      % (now - t0, hex(hw), cls, title, rc, vis, len(kids)))
                for h2, c2, t2, rc2 in kids[:16]:
                    print('          子 %s cls=%s 文本=%r rect=%s' % (hex(h2), c2, t2, rc2))
            # 记录主窗口（取最大的可见窗口）
            main_hw = None
            best = 0
            for hw, cls, title, rc, vis, kids in ws:
                if vis and rc[2] * rc[3] > best:
                    best = rc[2] * rc[3]; main_hw = hw
            globals()['MAIN_HWND'] = main_hw
            sys.stdout.flush()

        if DO_KEYS and now - last_key >= 6.0:
            last_key = now
            step += 1
            hw = globals().get('MAIN_HWND')
            if hw:
                # 先置前台再发按键
                u32.SetForegroundWindow(hw)
                for vk in (0x0D, 0x20):   # Enter, Space
                    u32.PostMessageA(hw, 0x0100, vk, 0)   # WM_KEYDOWN
                    time.sleep(0.05)
                    u32.PostMessageA(hw, 0x0101, vk, 0)   # WM_KEYUP
                    time.sleep(0.05)
                print('[%5.1fs] 已发 Enter/Space (第 %d 次)  主窗口=%s' % (now - t0, step, hex(hw)))
                sys.stdout.flush()

        if DO_CLICK and now - last_key >= 6.0:
            last_key = now
            hw = globals().get('MAIN_HWND')
            if hw:
                r = wintypes.RECT(); u32.GetWindowRect(hw, ctypes.byref(r))
                cx, cy = (r.left + r.right) // 2, (r.top + r.bottom) // 2
                u32.SetForegroundWindow(hw)
                lparam = ((cy & 0xFFFF) << 16) | (cx & 0xFFFF)
                u32.PostMessageA(hw, 0x0201, 1, lparam)   # WM_LBUTTONDOWN
                time.sleep(0.05)
                u32.PostMessageA(hw, 0x0202, 0, lparam)   # WM_LBUTTONUP
                print('[%5.1fs] 已点击窗口中心 (%d,%d)' % (now - t0, cx, cy))
                sys.stdout.flush()

    if not crash_done:
        print('\n运行 %.0f 秒未捕获致命异常' % RUN)
    print('调试事件统计:', evcount, ' (1=EXCEPTION 3=CREATE_PROCESS 5=EXIT 6=LOAD_DLL)')
    code = wintypes.DWORD()
    k32.GetExitCodeProcess(hp, ctypes.byref(code))
    print('退出码 =', code.value, '(259=仍在运行)')
    try:
        k32.DebugActiveProcessStop(pi.dwProcessId)
    except Exception:
        pass
    k32.TerminateProcess(hp, 0)
    k32.CloseHandle(pi.hThread); k32.CloseHandle(hp)


if __name__ == '__main__':
    main()
