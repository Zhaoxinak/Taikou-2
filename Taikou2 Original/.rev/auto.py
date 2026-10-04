"""
基于 shot.py 的分步推进：执行动作序列（点击/按键），周期截图，抓崩溃。

动作序列写在 ACTIONS 里（相对窗口左上角的坐标）。
"""
import ctypes, os, sys, time, struct
from ctypes import wintypes

k32 = ctypes.WinDLL('kernel32', use_last_error=True)
u32 = ctypes.WinDLL('user32', use_last_error=True)
g32 = ctypes.WinDLL('gdi32', use_last_error=True)

EXE = r'F:\Games\Taikou 2\Taikou2 Original\TAIK2W95_clean.exe'
RUN = 70.0
CWD = os.path.dirname(EXE)
SHOTDIR = os.path.join(CWD, '.rev', 'shots2')
os.makedirs(SHOTDIR, exist_ok=True)

# 动作序列: (时刻秒, 类型, 参数)  click 用相对窗口左上角坐标
ACTIONS = [
    (2.0,  'click', (555, 344)),   # 「确定」按钮
    (6.0,  'key', 0x0D),
    (9.0,  'key', 0x0D),
    (12.0, 'key', 0x0D),
    (15.0, 'key', 0x0D),
    (18.0, 'key', 0x0D),
    (21.0, 'key', 0x0D),
    (24.0, 'key', 0x0D),
    (27.0, 'key', 0x0D),
    (30.0, 'key', 0x0D),
    (33.0, 'key', 0x0D),
]

EXC = {0xC0000005: 'ACCESS_VIOLATION', 0xC0000094: 'ILLEGAL_INSTRUCTION',
       0xC00000FD: 'STACK_OVERFLOW', 0xC000008E: 'DIVIDE_BY_ZERO',
       0xC0000409: 'STACK_BUFFER_OVERRUN'}

# ---------- DEBUG_EVENT 等 ----------
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
                ('Extended', ctypes.c_byte * 512)]


IMAGEBASE = 0x400000
modules = [(IMAGEBASE, 0x136000, 'MAIN')]
av_seen = {}


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


def write_png(path, w, h, bgra, stride):
    import zlib
    raw = bytearray()
    for row in range(h):
        line = bgra[row * stride:(row + 1) * stride]
        raw.append(0)
        for px in range(w):
            b, g, r, _a = line[px * 4:px * 4 + 4]
            raw += bytes((r, g, b))
    comp = zlib.compress(bytes(raw), 6)

    def chunk(tag, data):
        c = tag + data
        return struct.pack('>I', len(data)) + c + struct.pack('>I', zlib.crc32(c) & 0xFFFFFFFF)

    png = b'\x89PNG\r\n\x1a\n'
    png += chunk(b'IHDR', struct.pack('>IIBBBBB', w, h, 8, 2, 0, 0, 0))
    png += chunk(b'IDAT', comp)
    png += chunk(b'IEND', b'')
    open(path, 'wb').write(png)


def grab(w, h):
    hdc = u32.GetDC(0)
    mem = g32.CreateCompatibleDC(hdc)
    bmp = g32.CreateCompatibleBitmap(hdc, w, h)
    old = g32.SelectObject(mem, bmp)
    g32.BitBlt(mem, 0, 0, w, h, hdc, 0, 0, 0x00CC0020)
    class BIH(ctypes.Structure):
        _fields_ = [('biSize', wintypes.DWORD), ('biWidth', ctypes.c_int),
                    ('biHeight', ctypes.c_int), ('biPlanes', wintypes.WORD),
                    ('biBitCount', wintypes.WORD), ('biCompression', wintypes.DWORD),
                    ('biSizeImage', wintypes.DWORD), ('biX', ctypes.c_int),
                    ('biY', ctypes.c_int), ('biClrUsed', wintypes.DWORD),
                    ('biClrImportant', wintypes.DWORD)]
    bi = BIH(); bi.biSize = ctypes.sizeof(bi)
    bi.biWidth = w; bi.biHeight = -h; bi.biPlanes = 1
    bi.biBitCount = 32; bi.biCompression = 0
    stride = w * 4
    buf = ctypes.create_string_buffer(stride * h)
    g32.GetDIBits(mem, bmp, 0, h, buf, ctypes.byref(bi), 0)
    g32.SelectObject(mem, old)
    g32.DeleteObject(bmp); g32.DeleteDC(mem)
    u32.ReleaseDC(0, hdc)
    return buf.raw[:stride * h], stride


def find_main_window(pid):
    best = 0; hw = None
    WNDENUMPROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)

    def cb(hwnd, lp):
        nonlocal best, hw
        p = wintypes.DWORD()
        u32.GetWindowThreadProcessId(hwnd, ctypes.byref(p))
        if p.value != pid:
            return True
        cn = ctypes.create_string_buffer(256)
        u32.GetClassNameA(hwnd, cn, 256)
        cls = cn.value.decode('latin1')
        if cls in ('AVIWnd32', 'MSCTFIME UI', 'IME', 'Default IME'):
            return True
        r = wintypes.RECT(); u32.GetWindowRect(hwnd, ctypes.byref(r))
        sz = (r.right - r.left) * (r.bottom - r.top)
        if u32.IsWindowVisible(hwnd) and sz > best:
            best = sz; hw = hwnd
        return True

    u32.EnumWindows(WNDENUMPROC(cb), 0)
    return hw


def dump_ctx(hp, ev, r):
    c = r.ExceptionCode
    addr = r.ExceptionAddress or 0
    hThread = k32.OpenThread(0x1F03FF, False, ev.dwThreadId)
    ctx = CONTEXT(); ctx.ContextFlags = CONTEXT_FULL
    if hThread:
        wg = getattr(k32, 'Wow64GetThreadContext', None)
        if wg:
            wg(hThread, ctypes.byref(ctx))
        else:
            k32.GetThreadContext(hThread, ctypes.byref(ctx))
        k32.CloseHandle(hThread)
    print('\n' + '=' * 72)
    print('!!! %s (0x%08X) 首次=%s' % (EXC.get(c, hex(c)), c, bool(ev.u.Exception.dwFirstChance)))
    print('异常地址 VA=0x%08X  %s' % (addr, ('主模块 RVA=0x%X' % (addr - IMAGEBASE))
                                   if 0x400000 <= addr < 0x540000 else where(addr)))
    if c == 0xC0000005 and r.NumberParameters:
        print('  操作=%s 目标=0x%08X %s' % (r.ExceptionInformation[0],
                                          r.ExceptionInformation[1],
                                          where(r.ExceptionInformation[1])))
    print('EAX=%08X EBX=%08X ECX=%08X EDX=%08X' % (ctx.Eax, ctx.Ebx, ctx.Ecx, ctx.Edx))
    print('ESI=%08X EDI=%08X EBP=%08X ESP=%08X EIP=%08X'
          % (ctx.Esi, ctx.Edi, ctx.Ebp, ctx.Esp, ctx.Eip))
    if ctx.Eip:
        print('EIP 字节:', readmem(hp, ctx.Eip, 24).hex(' '))
    print('栈顶 8 个 dword:')
    st = readmem(hp, ctx.Esp, 32)
    for j in range(0, len(st) - 3, 4):
        v = struct.unpack('<I', st[j:j + 4])[0]
        print('   [%08X] %08X  %s' % (ctx.Esp + j, v, where(v)))
    print('EBP 链:')
    ebp = ctx.Ebp
    for j in range(14):
        if not ebp or ebp & 3:
            break
        d = readmem(hp, ebp, 8)
        if len(d) < 8:
            break
        prev, ret = struct.unpack('<II', d)
        print('   #%d ret=0x%08X %s' % (j, ret, where(ret)))
        if prev <= ebp:
            break
        ebp = prev
    print('=' * 72)
    sys.stdout.flush()


def main():
    si = STARTUPINFO(); si.cb = ctypes.sizeof(si)
    pi = PROCESS_INFORMATION()
    ok = k32.CreateProcessA(EXE.encode(), None, None, None, False, 0x00000001,
                            None, CWD.encode(), ctypes.byref(si), ctypes.byref(pi))
    print('CreateProcess:', 'OK', 'pid =', pi.dwProcessId)
    hp = pi.hProcess
    t0 = time.time()
    ai = 0
    fatal = False
    nshot = 0
    last_shot = 0.0

    while time.time() - t0 < RUN and not fatal:
        ev = DEBUG_EVENT()
        if k32.WaitForDebugEvent(ctypes.byref(ev), 80):
            code = ev.dwDebugEventCode
            cont = 0x00010002
            if code == 6:
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
                modules.append((b, 0x100000, os.path.basename(name) or hex(b)))
            elif code == 1:
                r = ev.u.Exception.ExceptionRecord
                c = r.ExceptionCode
                addr = r.ExceptionAddress or 0
                if (c in (0x80000003, 0x406D1388, 0x4000001F, 0x40010005)
                        and ev.u.Exception.dwFirstChance):
                    pass
                else:
                    key = (c, addr, ev.u.Exception.dwFirstChance)
                    av_seen[key] = av_seen.get(key, 0) + 1
                    if av_seen[key] <= 2:
                        dump_ctx(hp, ev, r)
                    if c in EXC and 0x400000 <= addr < 0x540000 and not ev.u.Exception.dwFirstChance:
                        fatal = True
                        cont = 0x80010001
                    else:
                        cont = 0x00010002
            elif code == 5:
                print('进程退出，退出码 =', struct.unpack('<I', bytes(ev.u.raw[:4]))[0])
                fatal = True
            k32.ContinueDebugEvent(ev.dwProcessId, ev.dwThreadId, cont)
            continue

        now = time.time() - t0
        # 执行动作
        while ai < len(ACTIONS) and ACTIONS[ai][0] <= now:
            t, kind, arg = ACTIONS[ai]
            ai += 1
            hw = find_main_window(pi.dwProcessId)
            if not hw:
                continue
            r = wintypes.RECT(); u32.GetWindowRect(hw, ctypes.byref(r))
            if kind == 'click':
                x, y = r.left + arg[0], r.top + arg[1]
                u32.SetForegroundWindow(hw)
                time.sleep(0.1)
                u32.SetCursorPos(x, y)
                time.sleep(0.05)
                u32.mouse_event(0x0002, 0, 0, 0, 0)   # LEFTDOWN
                time.sleep(0.04)
                u32.mouse_event(0x0004, 0, 0, 0, 0)   # LEFTUP
                print('[%5.1fs] 点击 屏幕(%d,%d) 相对(%d,%d)' % (now, x, y, arg[0], arg[1]))
            elif kind == 'key':
                u32.SetForegroundWindow(hw)
                time.sleep(0.05)
                u32.keybd_event(arg, 0, 0, 0)
                time.sleep(0.04)
                u32.keybd_event(arg, 0, 2, 0)   # KEYUP
                print('[%5.1fs] 按键 VK=%02X' % (now, arg))
            sys.stdout.flush()

        # 截图
        if now - last_shot >= 4.0:
            last_shot = now
            hw = find_main_window(pi.dwProcessId)
            if hw:
                r = wintypes.RECT(); u32.GetWindowRect(hw, ctypes.byref(r))
                w = r.right - r.left; h = r.bottom - r.top
                nshot += 1
                fn = os.path.join(SHOTDIR, 'f%02d_%03.0fs.png' % (nshot, now))
                u32.SetForegroundWindow(hw)
                time.sleep(0.12)
                data, stride = grab(w, h)
                write_png(fn, w, h, data, stride)
                print('[%5.1fs] 截图 %s' % (now, fn))
                sys.stdout.flush()

    code = wintypes.DWORD()
    k32.GetExitCodeProcess(hp, ctypes.byref(code))
    print('结束. 退出码 =', code.value, '截图数 =', nshot)
    try:
        k32.DebugActiveProcessStop(pi.dwProcessId)
    except Exception:
        pass
    k32.TerminateProcess(hp, 0)
    k32.CloseHandle(pi.hThread); k32.CloseHandle(hp)


if __name__ == '__main__':
    main()
