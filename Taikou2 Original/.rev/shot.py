"""
启动目标 exe（调试模式），周期性截取主窗口画面并抓崩溃现场。

用法:
  python .rev/shot.py <exe> <总秒数> [截图间隔] [--keys] [--click X,Y]
    --keys      每 5 秒发一次 Enter
    --click X,Y 在指定屏幕坐标点击一次（可多次给出），在 t=CLICK_AT 秒时执行
"""
import ctypes, os, sys, time, struct
from ctypes import wintypes

k32 = ctypes.WinDLL('kernel32', use_last_error=True)
u32 = ctypes.WinDLL('user32', use_last_error=True)
g32 = ctypes.WinDLL('gdi32', use_last_error=True)

EXE = sys.argv[1] if len(sys.argv) > 1 else r'F:\Games\Taikou 2\Taikou2 Original\TAIK2W95_clean.exe'
RUN = float(sys.argv[2]) if len(sys.argv) > 2 else 40.0
INTERVAL = float(sys.argv[3]) if len(sys.argv) > 3 else 5.0
DO_KEYS = '--keys' in sys.argv
CWD = os.path.dirname(EXE)
SHOTDIR = os.path.join(CWD, '.rev', 'shots')
os.makedirs(SHOTDIR, exist_ok=True)

# 解析 --click X,Y [--at T]
clicks = []
i = 4
while i < len(sys.argv):
    if sys.argv[i] == '--click' and i + 1 < len(sys.argv):
        xy = sys.argv[i + 1].split(',')
        clicks.append((int(xy[0]), int(xy[1])))
        i += 2
    else:
        i += 1

EXC = {0xC0000005: 'ACCESS_VIOLATION', 0xC0000094: 'ILLEGAL_INSTRUCTION',
       0xC00000FD: 'STACK_OVERFLOW', 0xC000008E: 'DIVIDE_BY_ZERO',
       0xC0000409: 'STACK_BUFFER_OVERRUN', 0xC0000417: 'FAIL_FAST',
       0xC0000095: 'BREAKPOINT'}


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
nullcount = [0]
quiet_others = [0]


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


# ---------------- 截图 ----------------
def grab(rect):
    x, y, w, h = rect
    hdc = u32.GetDC(0)
    mem = g32.CreateCompatibleDC(hdc)
    bmp = g32.CreateCompatibleBitmap(hdc, w, h)
    old = g32.SelectObject(mem, bmp)
    g32.BitBlt(mem, 0, 0, w, h, hdc, x, y, 0x00CC0020)  # SRCCOPY
    class BITMAPINFOHEADER(ctypes.Structure):
        _fields_ = [('biSize', wintypes.DWORD), ('biWidth', ctypes.c_int),
                    ('biHeight', ctypes.c_int), ('biPlanes', wintypes.WORD),
                    ('biBitCount', wintypes.WORD), ('biCompression', wintypes.DWORD),
                    ('biSizeImage', wintypes.DWORD), ('biXPelsPerMeter', ctypes.c_int),
                    ('biYPelsPerMeter', ctypes.c_int), ('biClrUsed', wintypes.DWORD),
                    ('biClrImportant', wintypes.DWORD)]
    bi = BITMAPINFOHEADER()
    bi.biSize = ctypes.sizeof(bi)
    bi.biWidth = w; bi.biHeight = -h       # top-down
    bi.biPlanes = 1; bi.biBitCount = 32; bi.biCompression = 0
    stride = w * 4
    buf = ctypes.create_string_buffer(stride * h)
    g32.GetDIBits(mem, bmp, 0, h, buf, ctypes.byref(bi), 0)
    g32.SelectObject(mem, old)
    g32.DeleteObject(bmp)
    g32.DeleteDC(mem)
    u32.ReleaseDC(0, hdc)
    data = buf.raw[:stride * h]
    # 写 BMP (BGRA -> BGR)
    hdr = b'BM' + struct.pack('<IHHI', 14 + 40 + stride * h, 0, 0, 14 + 40)
    dib = struct.pack('<IiiHHIIiiII', 40, w, -h, 1, 32, 0, stride * h, 0, 0, 0, 0)
    body = bytearray()
    for row in range(h):
        line = data[row * stride:(row + 1) * stride]
        for px in range(w):
            b, g, r, a = line[px * 4:px * 4 + 4]
            body += bytes((b, g, r, 0))
    return bytes(hdr) + dib + bytes(body)


def write_png(path, w, h, bgra, stride):
    """把 BGRA(32bpp) 数据写成 PNG（纯 Python + zlib）"""
    import zlib
    raw = bytearray()
    for row in range(h):
        line = bgra[row * stride:(row + 1) * stride]
        raw.append(0)                      # filter type 0
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


def dump_ctx(hp, ev, r, title):
    c = r.ExceptionCode
    addr = r.ExceptionAddress or 0
    hThread = k32.OpenThread(0x1F03FF, False, ev.dwThreadId)
    ctx = CONTEXT(); ctx.ContextFlags = CONTEXT_FULL
    got_ctx = False
    if hThread:
        # 64 位调试器读取 32 位被调试进程必须用 Wow64GetThreadContext
        wow64get = getattr(k32, 'Wow64GetThreadContext', None)
        if wow64get:
            got_ctx = bool(wow64get(hThread, ctypes.byref(ctx)))
        if not got_ctx:
            got_ctx = bool(k32.GetThreadContext(hThread, ctypes.byref(ctx)))
        k32.CloseHandle(hThread)
    if not got_ctx:
        print('  (无法获取线程上下文)')
    print('\n' + '=' * 72)
    print('!!! %s  0x%08X 首次=%s' % (title, c, bool(ev.u.Exception.dwFirstChance)))
    print('异常地址 VA=0x%08X  %s' % (addr, ('主模块 RVA=0x%X' % (addr - IMAGEBASE))
                                   if 0x400000 <= addr < 0x540000 else where(addr)))
    if c == 0xC0000005 and r.NumberParameters:
        print('  操作=%s (0读 1写 8执行) 目标=0x%08X %s'
              % (r.ExceptionInformation[0], r.ExceptionInformation[1],
                 where(r.ExceptionInformation[1])))
    print('EAX=%08X EBX=%08X ECX=%08X EDX=%08X' % (ctx.Eax, ctx.Ebx, ctx.Ecx, ctx.Edx))
    print('ESI=%08X EDI=%08X EBP=%08X ESP=%08X EIP=%08X'
          % (ctx.Esi, ctx.Edi, ctx.Ebp, ctx.Esp, ctx.Eip))
    if ctx.Eip:
        print('EIP 字节:', readmem(hp, ctx.Eip, 24).hex(' '))
    # 调用于 EIP=0 时，返回地址就在栈顶
    print('栈顶 8 个 dword:')
    st = readmem(hp, ctx.Esp, 32)
    for j in range(0, len(st) - 3, 4):
        v = struct.unpack('<I', st[j:j + 4])[0]
        print('   [%08X] %08X  %s' % (ctx.Esp + j, v, where(v)))
    print('栈回溯 (EBP 链):')
    ebp = ctx.Ebp
    for j in range(12):
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
    print('CreateProcess:', 'OK' if ok else '失败 %d' % ctypes.get_last_error())
    if not ok:
        sys.exit(1)
    hp = pi.hProcess
    print('pid =', pi.dwProcessId)
    t0 = time.time()
    last_shot = 0.0
    last_key = 0.0
    n = 0
    fatal = False
    main_hw = None

    while time.time() - t0 < RUN and not fatal:
        ev = DEBUG_EVENT()
        if k32.WaitForDebugEvent(ctypes.byref(ev), 100):
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
                    cont = 0x00010002
                elif not (0x400000 <= addr < 0x540000):
                    # 地址不在主模块：可能是"调用空指针" (EIP=0) —— 必须看栈回溯
                    op = r.ExceptionInformation[0] if r.NumberParameters else -1
                    tgt = r.ExceptionInformation[1] if r.NumberParameters > 1 else 0
                    null_call = (addr == 0) or (op == 8 and tgt == 0)
                    if null_call:
                        nullcount[0] += 1
                        if nullcount[0] <= 2:
                            print('\n### 空指针调用 #%d  (VA=0x%08X, op=%s, tgt=0x%X)'
                                  % (nullcount[0], addr, op, tgt))
                            dump_ctx(hp, ev, r, '空指针调用')
                    elif quiet_others[0] < 3:
                        quiet_others[0] += 1
                        print('  [忽略] 非主模块异常 0x%08X @ %s %s' % (c, hex(addr), where(addr)))
                    cont = 0x00010002
                else:
                    fatal = True
                    cont = 0x80010001
                    dump_ctx(hp, ev, r, '致命异常')
            elif code == 5:
                print('进程退出，退出码 =', struct.unpack('<I', bytes(ev.u.raw[:4]))[0])
                fatal = True
            k32.ContinueDebugEvent(ev.dwProcessId, ev.dwThreadId, cont)
            continue

        now = time.time()
        # 找主窗口
        if main_hw is None or now - last_shot > INTERVAL:
            best = 0
            WNDENUMPROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)

            def cb(hwnd, lp):
                nonlocal main_hw, best
                p = wintypes.DWORD()
                u32.GetWindowThreadProcessId(hwnd, ctypes.byref(p))
                if p.value != pi.dwProcessId:
                    return True
                cn = ctypes.create_string_buffer(256)
                u32.GetClassNameA(hwnd, cn, 256)
                if cn.value.decode('latin1') == 'AVIWnd32':
                    return True
                r = wintypes.RECT(); u32.GetWindowRect(hwnd, ctypes.byref(r))
                sz = (r.right - r.left) * (r.bottom - r.top)
                if u32.IsWindowVisible(hwnd) and sz > best:
                    best = sz; main_hw = hwnd
                return True

            u32.EnumWindows(WNDENUMPROC(cb), 0)

        if now - last_shot >= INTERVAL and main_hw:
            last_shot = now
            r = wintypes.RECT(); u32.GetWindowRect(main_hw, ctypes.byref(r))
            rect = (r.left, r.top, r.right - r.left, r.bottom - r.top)
            n += 1
            fn = os.path.join(SHOTDIR, 's%02d_%03.0fs.png' % (n, now - t0))
            r2 = wintypes.RECT(); u32.GetWindowRect(main_hw, ctypes.byref(r2))
            img = grab((r2.left, r2.top, r2.right - r2.left, r2.bottom - r2.top))
            # grab 返回 BMP：跳过 14+40 头，取 BGRA 行
            body = img[54:]
            w0 = r2.right - r2.left
            write_png(fn, w0, r2.bottom - r2.top, body, w0 * 4)
            print('[%5.1fs] 截图 %s' % (now - t0, fn))
            sys.stdout.flush()

        if DO_KEYS and now - last_key >= 5.0 and main_hw:
            last_key = now
            u32.SetForegroundWindow(main_hw)
            u32.PostMessageA(main_hw, 0x0100, 0x0D, 0)
            time.sleep(0.05)
            u32.PostMessageA(main_hw, 0x0101, 0x0D, 0)
            print('[%5.1fs] 发 Enter' % (now - t0))

        for (cx, cy) in list(clicks):
            if now - t0 > 8.0 and main_hw:
                clicks.remove((cx, cy))
                u32.SetForegroundWindow(main_hw)
                lp = ((cy & 0xFFFF) << 16) | (cx & 0xFFFF)
                u32.PostMessageA(main_hw, 0x0201, 1, lp)
                time.sleep(0.05)
                u32.PostMessageA(main_hw, 0x0202, 0, lp)
                print('[%5.1fs] 点击 (%d,%d)' % (now - t0, cx, cy))

    code = wintypes.DWORD()
    k32.GetExitCodeProcess(hp, ctypes.byref(code))
    print('结束. 退出码 =', code.value, '(259=仍在运行)  截图数 =', n)
    try:
        k32.DebugActiveProcessStop(pi.dwProcessId)
    except Exception:
        pass
    k32.TerminateProcess(hp, 0)
    k32.CloseHandle(pi.hThread); k32.CloseHandle(hp)


if __name__ == '__main__':
    main()
