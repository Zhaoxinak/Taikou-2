"""tk_tab.py — 把 .fdata 里的 GDI_TAB / HWND / 日志句柄 挖出来, 和本机算出的真值对比

用法: python tk_tab.py
"""
import ctypes, json, os, struct, time, traceback
from ctypes import wintypes

k32 = ctypes.WinDLL('kernel32', use_last_error=True)
u32 = ctypes.WinDLL('user32')
k32.CreateProcessA.restype = wintypes.BOOL
k32.OpenProcess.restype = wintypes.HANDLE
k32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
k32.ReadProcessMemory.restype = wintypes.BOOL
k32.ReadProcessMemory.argtypes = [wintypes.HANDLE, wintypes.LPCVOID, wintypes.LPVOID,
                                  ctypes.c_size_t, ctypes.POINTER(ctypes.c_size_t)]
k32.GetExitCodeProcess.restype = wintypes.BOOL
k32.GetExitCodeProcess.argtypes = [wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD)]
u32.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
u32.GetWindowThreadProcessId.restype = wintypes.DWORD
u32.EnumWindows.argtypes = [ctypes.c_void_p, wintypes.LPARAM]
u32.GetClientRect.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.RECT)]

GAME = r'F:\Games\Taikou 2\Taikou2 Original'
EXE = os.path.join(GAME, 'TAIK2W95_family.exe')
REV = os.path.join(GAME, '.rev')
M = json.load(open(os.path.join(REV, 'tree_blobs.json')))

SEC_VA = M['sec_va']
GDI_TAB = M['gdi_tab']
RSTATE = M['rstate']
RS_HWND, RS_HDC, RS_FAMP = RSTATE + 0, RSTATE + 4, RSTATE + 8
RS_LOGH = RSTATE + 0x74
RS_STAGE = RSTATE + 0x10
GDIOK = RSTATE + 0x70
NAM_VA = SEC_VA + 0x80

API_NAMES = ['Sleep', 'GetActiveWindow', 'PeekMessageA', 'GetDC', 'ReleaseDC', 'CreatePen',
             'CreateSolidBrush', 'SelectObject', 'DeleteObject', 'Rectangle', 'Ellipse',
             'MoveToEx', 'LineTo', 'SetTextColor', 'SetBkMode', 'SetTextAlign', 'TextOutA',
             'CreateFontA', 'GetStockObject', 'GetAsyncKeyState', 'CreateFileA', 'WriteFile']

# 本机真值(同一台机器, base 不同但函数内容可比对: 用 kernel32 里 Sleep 的偏移做基准)
kb = ctypes.WinDLL('kernel32'); ub = ctypes.WinDLL('user32'); gb = ctypes.WinDLL('gdi32')
k32.GetModuleHandleA.restype = wintypes.HMODULE
k32.GetProcAddress.restype = ctypes.c_void_p
k32.GetProcAddress.argtypes = [wintypes.HMODULE, ctypes.c_char_p]
h_k = k32.GetModuleHandleA(b'kernel32.dll')
h_u = k32.GetModuleHandleA(b'user32.dll')
h_g = k32.GetModuleHandleA(b'gdi32.dll')
TRUE = {}
for mod, hm in (('kernel32', h_k), ('user32', h_u), ('gdi32', h_g)):
    for n in API_NAMES:
        p = k32.GetProcAddress(hm, n.encode())
        if p:
            TRUE[(mod, n)] = p
# 基准: 用本机 Sleep 的地址 vs 目标进程里 Sleep 的地址, 得出模块加载基址差
BASEOF = {}
for mod, hm in (('kernel32', h_k), ('user32', h_u), ('gdi32', h_g)):
    BASEOF[mod] = hm


class SI2(ctypes.Structure):
    _fields_ = [('cb', wintypes.DWORD), ('a', wintypes.LPVOID), ('b', wintypes.LPVOID), ('c', wintypes.LPVOID),
                ('x', wintypes.DWORD), ('y', wintypes.DWORD), ('xs', wintypes.DWORD), ('ys', wintypes.DWORD),
                ('x1', wintypes.DWORD), ('y1', wintypes.DWORD), ('fa', wintypes.DWORD), ('fl', wintypes.DWORD),
                ('sw', wintypes.WORD), ('r2', wintypes.WORD), ('r3', wintypes.LPVOID), ('h1', wintypes.HANDLE),
                ('h2', wintypes.HANDLE), ('h3', wintypes.HANDLE)]


class PI(ctypes.Structure):
    _fields_ = [('hp', wintypes.HANDLE), ('ht', wintypes.HANDLE),
                ('pid', wintypes.DWORD), ('tid', wintypes.DWORD)]


def wins(pid):
    out = []

    @ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)
    def cb(h, lp):
        p = wintypes.DWORD(); u32.GetWindowThreadProcessId(h, ctypes.byref(p))
        if p.value == pid:
            r = wintypes.RECT(); u32.GetClientRect(h, ctypes.byref(r))
            out.append((h, r.right, r.bottom, bool(u32.IsWindowVisible(h))))
        return True
    u32.EnumWindows(cb, 0); return out


hp = hk = main = None
try:
    si = SI2(); si.cb = ctypes.sizeof(si); pi = PI()
    assert k32.CreateProcessA(EXE.encode(), None, None, None, False, 0, None,
                              GAME.encode(), ctypes.byref(si), ctypes.byref(pi))
    hp, pid = pi.hp, pi.pid
    hk = k32.OpenProcess(0x1F0FFF, False, pid)
    print('pid=%d' % pid, flush=True)

    def rd(va, n):
        b = ctypes.create_string_buffer(n); got = ctypes.c_size_t()
        if not k32.ReadProcessMemory(hk, ctypes.c_void_p(va), b, n, ctypes.byref(got)):
            return None
        return b.raw[:got.value]

    def g(va):
        d = rd(va, 4)
        return struct.unpack('<I', d)[0] if d and len(d) == 4 else None

    def alive():
        c = wintypes.DWORD()
        return bool(k32.GetExitCodeProcess(hp, ctypes.byref(c)) and c.value == 259)

    t0 = time.time(); last = -1; stable = 0; sk = 0.0
    while time.time() - t0 < 90:
        for h, w, hh, vis in wins(pid):
            if w >= 800:
                main = h
        d = rd(0x534040, 4); cnt = struct.unpack('<I', d)[0] if d else -1
        stable = stable + 1 if cnt == last else 0; last = cnt
        if cnt >= 71 and stable > 8 and main:
            break
        if time.time() - sk > 1.2:
            sk = time.time()
            if main:
                u32.SetForegroundWindow(main)
            u32.keybd_event(0x1B, 0, 0, 0); time.sleep(0.05); u32.keybd_event(0x1B, 0, 2, 0)
        time.sleep(0.4)
    print('present=%s main=0x%X' % (last, main or 0), flush=True)

    print('--- 进程窗口 ---')
    for h, w, hh, vis in wins(pid):
        print('   0x%08X client=%dx%d vis=%s' % (h, w, hh, vis))

    u32.SetForegroundWindow(main); time.sleep(0.4)
    pt = wintypes.POINT(0, 0); u32.ClientToScreen(main, ctypes.byref(pt))
    CX0, CY0 = pt.x, pt.y

    def click(px, py, wait=1.2):
        u32.SetForegroundWindow(main)
        u32.SetCursorPos(CX0 + px, CY0 + py); time.sleep(0.30)
        u32.mouse_event(2, 0, 0, 0, 0); time.sleep(0.10)
        u32.mouse_event(4, 0, 0, 0, 0); time.sleep(wait)

    # 先在标题界面点一下, 触发 tree_entry(兜底柴田)
    click(545, 310, 2.0)
    print('GDIOK=%s STAGE=%s' % (g(GDIOK), g(RS_STAGE)), flush=True)
    print('HWND slot =0x%08X   HDC slot=0x%08X   LOGH=0x%08X   FAMP=0x%08X'
          % (g(RS_HWND) or 0, g(RS_HDC) or 0, g(RS_LOGH) or 0, g(RS_FAMP) or 0), flush=True)
    print('GetActiveWindow() 本进程视角 = 0x%08X (目标进程真实 HWND 见上表)' % (u32.GetActiveWindow() or 0), flush=True)

    print('--- GDI_TAB ---')
    raw = rd(GDI_TAB, 22 * 4)
    if raw is None:
        print('   !! 读不到 GDI_TAB')
    else:
        for i, n in enumerate(API_NAMES):
            v = struct.unpack_from('<I', raw, i * 4)[0]
            print('   [%2d] %-18s 0x%08X %s' % (i, n, v, '' if v else '   <<< 空'))

    print('--- GDI_NAM 串池 ---')
    s = rd(NAM_VA, 0x180)
    print('   %r' % (s[:0x180] if s else None))

    print('--- 各模块句柄 ---')
    for i, mod in enumerate(('kernel32.dll', 'user32.dll', 'gdi32.dll')):
        print('   %-14s 0x%08X' % (mod, g(RSTATE + 0x60 + i * 4) or 0))
    print('--- 本机对照(本进程内 GetModuleHandleA) ---')
    print('   k32=0x%X u32=0x%X g32=0x%X' % (h_k, h_u, h_g))
    # 用 GetActiveWindow / GetDC 的本机地址做偏移基准, 推目标进程应有值
    print('   本机 GetActiveWindow=0x%X GetDC=0x%X WriteFile=0x%X'
          % (TRUE[('user32', 'GetActiveWindow')], TRUE[('gdi32', 'GetDC')],
             TRUE[('kernel32', 'WriteFile')]))
except SystemExit:
    pass
except Exception:
    print('EXC', traceback.format_exc(), flush=True)
finally:
    try:
        if hp and alive():
            k32.TerminateProcess(hp, 0)
    except Exception:
        pass
    print('done', flush=True)
