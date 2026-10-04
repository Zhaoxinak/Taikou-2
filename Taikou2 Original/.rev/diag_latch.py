"""diag_latch.py — 只验证「左键锁存」是否工作 + 进程是否稳定(不点按钮).
启动 family.exe -> 等标题 -> 在远离按钮处点 6 次 -> 读 G_LBDOWN / G_LOOPCNT -> 判活。
结束时一定还原 OPENNING.AVI。"""
import ctypes, os, struct, time, shutil, traceback
from ctypes import wintypes
k32 = ctypes.WinDLL('kernel32', use_last_error=True); u32 = ctypes.WinDLL('user32')
k32.OpenProcess.restype = wintypes.HANDLE
k32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
k32.ReadProcessMemory.restype = wintypes.BOOL
k32.ReadProcessMemory.argtypes = [wintypes.HANDLE, wintypes.LPCVOID, wintypes.LPVOID,
                                  ctypes.c_size_t, ctypes.POINTER(ctypes.c_size_t)]
u32.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
GAME = r'F:\Games\Taikou 2\Taikou2 Original'
EXE = os.path.join(GAME, 'TAIK2W95_family.exe')
AVI = os.path.join(GAME, 'OPENNING.AVI'); TMP = AVI + '.tstb'
class SI2(ctypes.Structure):
    _fields_ = [('cb', wintypes.DWORD), ('a', wintypes.LPVOID), ('b', wintypes.LPVOID), ('c', wintypes.LPVOID),
                ('x', wintypes.DWORD), ('y', wintypes.DWORD), ('xs', wintypes.DWORD), ('ys', wintypes.DWORD),
                ('x1', wintypes.DWORD), ('y1', wintypes.DWORD), ('fa', wintypes.DWORD), ('fl', wintypes.DWORD),
                ('sw', wintypes.WORD), ('r2', wintypes.WORD), ('r3', wintypes.LPVOID), ('h1', wintypes.HANDLE),
                ('h2', wintypes.HANDLE), ('h3', wintypes.HANDLE)]
class PI(ctypes.Structure):
    _fields_ = [('hp', wintypes.HANDLE), ('ht', wintypes.HANDLE), ('pid', wintypes.DWORD), ('tid', wintypes.DWORD)]
hp = hk = main = None
try:
    if (not os.path.exists(AVI)) and os.path.exists(TMP): shutil.move(TMP, AVI)
    if os.path.exists(AVI): shutil.move(AVI, TMP)
    si = SI2(); si.cb = ctypes.sizeof(si); pi = PI()
    k32.CreateProcessA(EXE.encode(), None, None, None, False, 0, None, GAME.encode(), ctypes.byref(si), ctypes.byref(pi))
    hp, pid = pi.hp, pi.pid; hk = k32.OpenProcess(0x1F0FFF, False, pid)
    def rd(va, n):
        b = ctypes.create_string_buffer(n); got = ctypes.c_size_t()
        if not k32.ReadProcessMemory(hk, ctypes.c_void_p(va), b, n, ctypes.byref(got)): return None
        return b.raw[:got.value]
    def g(va):
        d = rd(va, 4); return struct.unpack('<I', d)[0] if d else None
    t0 = time.time(); last = -1; stable = 0
    while time.time() - t0 < 40:
        @ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)
        def cb(h, lp):
            global main
            p = wintypes.DWORD(); u32.GetWindowThreadProcessId(h, ctypes.byref(p))
            if p.value == pid and u32.IsWindowVisible(h):
                r = wintypes.RECT(); u32.GetClientRect(h, ctypes.byref(r))
                if r.right >= 800: main = h
            return True
        u32.EnumWindows(cb, 0)
        c = g(0x534040); stable = stable + 1 if c == last else 0; last = c
        if c and c >= 71 and stable > 6 and main: break
        time.sleep(0.4)
    print('title: present=%s main=%s' % (last, main), flush=True)
    u32.SetForegroundWindow(main); time.sleep(0.5)
    wr = wintypes.RECT(); u32.GetWindowRect(main, ctypes.byref(wr))
    r = wintypes.RECT(); u32.GetClientRect(main, ctypes.byref(r)); nct = (wr.bottom - wr.top) - r.bottom
    print('  LBDOWN(初始)=%s LOOP(初始)=%s' % (g(0x535EE0), g(0x535EEC)), flush=True)
    for i in range(6):
        u32.SetCursorPos(wr.left + 120 + i * 3, wr.top + nct + 700); time.sleep(0.12)
        u32.mouse_event(2, 0, 0, 0, 0); time.sleep(0.10); u32.mouse_event(4, 0, 0, 0, 0); time.sleep(0.35)
        print('  第%d次点击后 LBDOWN=%s LOOP=%s alive=%s' % (i + 1, g(0x535EE0), g(0x535EEC), rd(0x534040, 4) is not None), flush=True)
    time.sleep(1.5)
    print('结束: LBDOWN=%s LBS=%s LOOP=%s present=%s' % (g(0x535EE0), g(0x535EE4), g(0x535EEC), g(0x534040)), flush=True)
except Exception:
    print('EXC', traceback.format_exc(), flush=True)
finally:
    for h in (hp, hk):
        try:
            if h: k32.TerminateProcess(h, 0)
        except Exception: pass
    if os.path.exists(TMP): shutil.move(TMP, AVI)
    print('cleanup; AVI=%s' % os.path.exists(AVI), flush=True)
