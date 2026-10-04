"""probe_fam.py — 进剧本后只读 dump 实体数组 + 姓/名表, 找出「柴田/佐久间」到底能不能按姓名匹配到.
判据与 family_builder 一致: idx=word[ent+0]; 姓=*(0x520660+idx*7) 4字节; 名=*(0x521aa8+idx*7) 4字节.
结束杀进程 + 还原 OPENNING.AVI。"""
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
AVI = os.path.join(GAME, 'OPENNING.AVI'); TMP = AVI + '.prb'
EBASE, STRIDE, N = 0x519868, 47, 0x172
SUR, GIV, NS = 0x520660, 0x521aa8, 7
class SI2(ctypes.Structure):
    _fields_ = [('cb', wintypes.DWORD), ('a', wintypes.LPVOID), ('b', wintypes.LPVOID), ('c', wintypes.LPVOID),
                ('x', wintypes.DWORD), ('y', wintypes.DWORD), ('xs', wintypes.DWORD), ('ys', wintypes.DWORD),
                ('x1', wintypes.DWORD), ('y1', wintypes.DWORD), ('fa', wintypes.DWORD), ('fl', wintypes.DWORD),
                ('sw', wintypes.WORD), ('r2', wintypes.WORD), ('r3', wintypes.LPVOID), ('h1', wintypes.HANDLE),
                ('h2', wintypes.HANDLE), ('h3', wintypes.HANDLE)]
class PI(ctypes.Structure):
    _fields_ = [('hp', wintypes.HANDLE), ('ht', wintypes.HANDLE), ('pid', wintypes.DWORD), ('tid', wintypes.DWORD)]
hp = hk = None
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
    t0 = time.time(); last = -1; stable = 0; main = None
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
        d = rd(0x534040, 4); c = struct.unpack('<I', d)[0] if d else -1
        stable = stable + 1 if c == last else 0; last = c
        if c >= 71 and stable > 6 and main: break
        time.sleep(0.4)
    print('title present=%s' % last, flush=True)
    u32.SetForegroundWindow(main); time.sleep(0.4)
    wr = wintypes.RECT(); u32.GetWindowRect(main, ctypes.byref(wr))
    r = wintypes.RECT(); u32.GetClientRect(main, ctypes.byref(r)); nct = (wr.bottom - wr.top) - r.bottom
    def click(px, py, w=1.0):
        u32.SetCursorPos(wr.left + px, wr.top + nct + py); time.sleep(0.3)
        u32.mouse_event(2, 0, 0, 0, 0); time.sleep(0.1); u32.mouse_event(4, 0, 0, 0, 0); time.sleep(w)
    click(545, 310, 2.0); click(640, 415, 2.5); click(640, 415, 2.5); click(640, 415, 3.0)
    time.sleep(1.5)
    blob = rd(EBASE, STRIDE * N)
    if not blob: print('实体读取失败'); raise SystemExit
    def nm(idx, base):
        if idx >= 1000: return None
        s = rd(base + idx * NS, 7)
        return s.split(b'\x00')[0] if s else None
    hits = []
    for i in range(N):
        e = blob[i * STRIDE:(i + 1) * STRIDE]
        idx = struct.unpack('<H', e[0:2])[0]
        sur = nm(idx, SUR); giv = nm(idx, GIV)
        if sur is None: continue
        try:
            st = sur.decode('gbk') + giv.decode('gbk')
        except Exception:
            st = repr(sur) + repr(giv)
        if ('柴田' in st) or ('佐久间' in st) or ('佐久' in st):
            hits.append((i, idx, st, struct.unpack('<H', e[0x1d:0x1f])[0], struct.unpack('<H', e[0x2c:0x2e])[0]))
    print('命中 柴田/佐久间 的实体 %d 个:' % len(hits), flush=True)
    for i, idx, st, fa, stt in hits:
        print('  slot=%-3d nameidx=%-5d %-10s father=%-5d status=0x%04x  (status>>8)&7=%d 父位0x1d=%d'
              % (i, idx, st, fa, stt, (stt >> 8) & 7, fa), flush=True)
    # 顺便统计分布
    cnt_lt1000 = sum(1 for i in range(N) if struct.unpack('<H', blob[i * STRIDE:i * STRIDE + 2])[0] < 1000)
    print('nameidx<1000 的实体数 =', cnt_lt1000, flush=True)
    for label, base in (('姓表0x520660', SUR), ('名表0x521aa8', GIV)):
        raw = rd(base + 35 * NS, 7)
        print('  %s[35] = %r' % (label, raw), flush=True)
    print('  姓表前 40 项:' , flush=True)
    for k in range(0, 40):
        s = rd(SUR + k * NS, 7)
        print('    [%2d] %r' % (k, s), flush=True)
except Exception:
    print('EXC', traceback.format_exc(), flush=True)
finally:
    for h in (hp, hk):
        try:
            if h: k32.TerminateProcess(h, 0)
        except Exception: pass
    if os.path.exists(TMP): shutil.move(TMP, AVI)
    print('cleanup; AVI=%s' % os.path.exists(AVI), flush=True)
