"""dbg_tree.py — 把你自己变成调试器跑游戏, 抓「点击家族族谱后闪退」的真凶

为什么需要它: 老 KOEI 游戏自带异常处理, 一旦发生异常就静默 ExitProcess,
            表面上只看到「闪退」, 拿不到出错地址。
            这里用 DEBUG_PROCESS 启动, WaitForDebugEvent 收异常,
            直接打印 ExceptionCode / ExceptionAddress / 访问违规的读写地址。

用法: python dbg_tree.py
"""
import ctypes, json, os, struct, time, traceback
from ctypes import wintypes

k32 = ctypes.WinDLL('kernel32', use_last_error=True)
u32 = ctypes.WinDLL('user32'); g32 = ctypes.WinDLL('gdi32')

k32.CreateProcessA.restype = wintypes.BOOL
k32.OpenProcess.restype = wintypes.HANDLE
k32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
k32.ReadProcessMemory.restype = wintypes.BOOL
k32.ReadProcessMemory.argtypes = [wintypes.HANDLE, wintypes.LPCVOID, wintypes.LPVOID,
                                  ctypes.c_size_t, ctypes.POINTER(ctypes.c_size_t)]
k32.WaitForDebugEvent.restype = wintypes.BOOL
k32.WaitForDebugEvent.argtypes = [ctypes.POINTER(ctypes.c_char * 96), wintypes.DWORD]
k32.ContinueDebugEvent.restype = wintypes.BOOL
k32.ContinueDebugEvent.argtypes = [wintypes.DWORD, wintypes.DWORD, wintypes.DWORD]
u32.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
u32.GetWindowThreadProcessId.restype = wintypes.DWORD
u32.EnumWindows.argtypes = [ctypes.c_void_p, wintypes.LPARAM]
u32.GetClientRect.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.RECT)]

DEBUG_PROCESS = 0x00000001
EXCEPTION_DEBUG_EVENT = 1
OUTPUT_DEBUG_STRING_EVENT = 8
DBG_CONTINUE = 0x00010002
DBG_EXCEPTION_NOT_HANDLED = 0x80010001

ENAME = {
    0x80000003: 'BREAKPOINT', 0x80000004: 'SINGLE_STEP',
    0xC0000005: 'ACCESS_VIOLATION', 0xC0000094: 'INT_DIVIDE_BY_ZERO',
    0xC0000095: 'INT_OVERFLOW', 0xC00000FD: 'STACK_OVERFLOW',
    0xC000001D: 'ILLEGAL_INSTRUCTION', 0xC0000025: 'NONCONTINUABLE',
    0xC000008C: 'ARRAY_BOUNDS_EXCEEDED', 0xC000008E: 'FLT_DIVIDE_BY_ZERO',
    0xC0000135: 'DLL_NOT_FOUND', 0x80000026: 'DIGITAL_INPUT',
}
ACCESS_TYPE = {0: 'READ', 1: 'WRITE', 8: 'DEP'}


class EXCEPTION_RECORD32(ctypes.Structure):
    _fields_ = [('ExceptionCode', wintypes.DWORD), ('ExceptionFlags', wintypes.DWORD),
                ('ExceptionRecord', wintypes.DWORD), ('ExceptionAddress', wintypes.DWORD),
                ('NumberParameters', wintypes.DWORD), ('ExceptionInformation', wintypes.DWORD * 15)]


class EXCEPTION_DEBUG_INFO(ctypes.Structure):
    _fields_ = [('ExceptionRecord', EXCEPTION_RECORD32), ('dwFirstChance', wintypes.DWORD)]


class OUTPUT_DEBUG_STRING_INFO(ctypes.Structure):
    _fields_ = [('lpDebugStringData', wintypes.DWORD), ('fUnicode', ctypes.c_ushort),
                ('nDebugStringLength', ctypes.c_ushort)]


class DEBUG_EVENT(ctypes.Structure):
    _fields_ = [('dwDebugEventCode', wintypes.DWORD), ('dwProcessId', wintypes.DWORD),
                ('dwThreadId', wintypes.DWORD), ('u', ctypes.c_byte * 88)]

GAME = r'F:\Games\Taikou 2\Taikou2 Original'
EXE = os.path.join(GAME, 'TAIK2W95_family.exe')
REV = os.path.join(GAME, '.rev')
M = json.load(open(os.path.join(REV, 'tree_blobs.json')))

G_CLICK, G_HIT, G_IN, G_LOOPCNT = 0x535F20, 0x535F24, 0x535F3C, 0x535EEC
CARD_CUR = 0x514EE8
RSTATE = M['rstate']
RS_STAGE, RS_QUIT = RSTATE + 0x10, RSTATE + 0x0C
GDIOK = RSTATE + 0x70

# .fdata 代码区范围 —— 崩溃落在这里就坐实是渲染层的问题
CODE_LO = M['blobs'][0]['va']
CODE_HI = M['blobs'][-1]['va'] + M['blobs'][-1]['size']
BL = {b['name']: (b['va'], b['va'] + b['size']) for b in M['blobs']}

lf = open(os.path.join(REV, 'dbg_tree.log'), 'w', encoding='utf-8')
EV = []          # (t, text)
ARMED = [False]  # 主流程设臂后才记录
STOP = [False]
EXC_N = [0]


def log(*a):
    s = ' '.join(str(x) for x in a)
    print(s, flush=True); lf.write(s + '\n'); lf.flush()


def where(va):
    for nm, (lo, hi) in BL.items():
        if lo <= va < hi:
            return '  <- .fdata 的 %s 段 (+0x%X)' % (nm, va - lo)
    if 0x535000 <= va < 0x536000:
        return '  <- 旧代码洞 0x535xxx'
    return ''


class PI(ctypes.Structure):
    _fields_ = [('hp', wintypes.HANDLE), ('ht', wintypes.HANDLE), ('pid', wintypes.DWORD), ('tid', wintypes.DWORD)]


def pump():
    """调试事件泵 —— 后台线程"""
    ev = DEBUG_EVENT()
    n = 0
    while not STOP[0]:
        ctypes.memset(ctypes.byref(ev), 0, ctypes.sizeof(ev))
        if not k32.WaitForDebugEvent(ctypes.cast(ctypes.byref(ev), ctypes.POINTER(ctypes.c_char * 96)), 200):
            continue
        cont = DBG_CONTINUE
        code = ev.dwDebugEventCode
        try:
            if code == EXCEPTION_DEBUG_EVENT:
                edi = ctypes.cast(ctypes.byref(ev, DEBUG_EVENT.u.offset),
                                  ctypes.POINTER(EXCEPTION_DEBUG_INFO)).contents
                er = edi.ExceptionRecord
                ec, addr = er.ExceptionCode, er.ExceptionAddress
                nm = ENAME.get(ec, '?')
                EXC_N[0] += 1
                if ec not in (0x80000003, 0x80000004):
                    cont = DBG_EXCEPTION_NOT_HANDLED
                if ARMED[0]:
                    extra = ''
                    if ec == 0xC0000005 and er.NumberParameters >= 2:
                        extra = '  %s 目标=0x%08X' % (ACCESS_TYPE.get(er.ExceptionInformation[0], '?'),
                                                  er.ExceptionInformation[1])
                    log('EXC #%d code=0x%08X(%s) addr=0x%08X first=%d%s%s'
                        % (EXC_N[0], ec, nm, addr, edi.dwFirstChance, extra, where(addr)))
                    EV.append((time.time(), '0x%08X %s @0x%08X' % (ec, nm, addr)))
                    n += 1
            elif code == OUTPUT_DEBUG_STRING_EVENT:
                od = ctypes.cast(ctypes.byref(ev, DEBUG_EVENT.u.offset),
                                 ctypes.POINTER(OUTPUT_DEBUG_STRING_INFO)).contents
                log('DBGSTR len=%d ptr=0x%08X' % (od.nDebugStringLength, od.lpDebugStringData))
        except Exception as e:
            log('pump EXC %r' % e)
        k32.ContinueDebugEvent(ev.dwProcessId, ev.dwThreadId, cont)
        if n > 60:
            log('...异常过多, 停止记录')
            ARMED[0] = False


def wins(pid):
    out = []

    @ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)
    def cb(h, lp):
        p = wintypes.DWORD(); u32.GetWindowThreadProcessId(h, ctypes.byref(p))
        if p.value == pid and u32.IsWindowVisible(h):
            r = wintypes.RECT(); u32.GetClientRect(h, ctypes.byref(r)); out.append((h, r.right, r.bottom))
        return True
    u32.EnumWindows(cb, 0); return out


import threading
hp = hk = main = None
try:
    sb = ctypes.create_string_buffer(68); struct.pack_into('<I', sb, 0, 68)
    pi = PI()
    assert k32.CreateProcessA(EXE.encode(), None, None, None, False, DEBUG_PROCESS, None,
                              GAME.encode(), sb, ctypes.byref(pi)), 'CreateProcess 失败 %d' % ctypes.get_last_error()
    hp, pid = pi.hp, pi.pid; hk = k32.OpenProcess(0x1F0FFF, False, pid)
    log('游戏已启动 pid=%d (DEBUG_PROCESS)' % pid)
    th = threading.Thread(target=pump, daemon=True); th.start()

    def rd(va, n):
        b = ctypes.create_string_buffer(n); got = ctypes.c_size_t()
        return b.raw[:got.value] if k32.ReadProcessMemory(hk, ctypes.c_void_p(va), b, n, ctypes.byref(got)) else None

    def g(va, n=4):
        d = rd(va, n)
        return struct.unpack('<I', d)[0] if d and len(d) == n else None

    t0 = time.time(); last = -1; stable = 0; skip_t = 0.0
    while time.time() - t0 < 90:
        for h, w, hh in wins(pid):
            if w >= 800:
                main = h
        d = rd(0x534040, 4); cnt = struct.unpack('<I', d)[0] if d else -1
        stable = stable + 1 if cnt == last else 0; last = cnt
        if cnt >= 71 and stable > 8 and main:
            break
        if time.time() - skip_t > 1.2:
            skip_t = time.time()
            if main:
                u32.SetForegroundWindow(main)
            u32.keybd_event(0x1B, 0, 0, 0); time.sleep(0.05); u32.keybd_event(0x1B, 0, 2, 0)
        time.sleep(0.4)
    log('present=%s main=%s' % (last, main))
    assert main, '主窗口未找到'
    u32.SetForegroundWindow(main); time.sleep(0.4)
    cr = wintypes.RECT(); u32.GetClientRect(main, ctypes.byref(cr))
    CW, CH = cr.right, cr.bottom
    pt = wintypes.POINT(0, 0); u32.ClientToScreen(main, ctypes.byref(pt))
    CX0, CY0 = pt.x, pt.y
    log('client %dx%d' % (CW, CH))

    def click(px, py, wait=0.8):
        u32.SetCursorPos(CX0 + px, CY0 + py); time.sleep(0.35)
        u32.mouse_event(2, 0, 0, 0, 0); time.sleep(0.10); u32.mouse_event(4, 0, 0, 0, 0); time.sleep(wait)

    def key(vk, wait=0.8):
        u32.keybd_event(vk, 0, 0, 0); time.sleep(0.06); u32.keybd_event(vk, 0, 2, 0); time.sleep(wait)

    time.sleep(2.0)
    click(545, 310, 2.0)
    click(640, 415, 2.5); click(640, 415, 2.5); click(640, 415, 3.0)
    click(1008, 473, 1.5)
    key(0x1B, 1.2); key(0x1B, 1.2)

    UI_NO = ((1008, 473), (960, 460), (640, 415), (640, 470))
    ci = 0
    for attempt in range(24):
        u32.SetForegroundWindow(main); time.sleep(0.35)
        if g(CARD_CUR):
            log('信息卡已打开 CARD_CUR=0x%06X (第 %d 轮)' % (g(CARD_CUR), attempt))
            break
        px, py = UI_NO[ci % len(UI_NO)]; ci += 1
        if ci % 4 == 0:
            key(0x1B, 0.5)
        click(px, py, 0.9)
    if not g(CARD_CUR):
        log('!! 未能打开信息卡, 仍继续尝试点页签')
    log('CARD_CUR=0x%06X STAGE=%s GDIOK=%s' % (g(CARD_CUR) or 0, g(RS_STAGE), g(GDIOK)))

    ARMED[0] = True
    log('=== 武装完毕: 开始点「家族族谱」页签 ===')
    for i, (px, py) in enumerate(((891, 264), (860, 268), (847, 258), (900, 258))):
        u32.SetCursorPos(CX0 + px, CY0 + py); time.sleep(0.5)
        u32.mouse_event(2, 0, 0, 0, 0); time.sleep(0.20); u32.mouse_event(4, 0, 0, 0, 0)
        time.sleep(1.2)
        alive = bool(rd(0x534040, 4))
        log('页签%d @(%d,%d) 进程存活=%s STAGE=%s' % (i, px, py, alive, g(RS_STAGE)))
        if not alive:
            log('  >>> 进程已退出 —— 崩溃就发生在这一次点击')
            break
    time.sleep(1.5)
    ARMED[0] = False
    log('=== 结束: 共记录 %d 条异常 ===' % len(EV))
except Exception:
    log('EXC ' + traceback.format_exc())
finally:
    STOP[0] = True
    time.sleep(0.3)
    try:
        if hp:
            k32.TerminateProcess(hp, 0)
    except Exception:
        pass
    lf.close()
    print('cleanup', flush=True)
