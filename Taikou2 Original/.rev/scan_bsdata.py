"""scan_bsdata.py — 扫描运行中游戏的进程内存, 定位 BSDATA 母表(700 x 59)是否常驻
判据: 搜 GBK "柴田" -> 校验候选地址是否符合记录结构(姓7B @0x00, 名7B @0x07, father@0x29)
只读内存, 不改动任何东西。
"""
import ctypes, os, struct, sys, time, traceback
from ctypes import wintypes

k32 = ctypes.WinDLL('kernel32', use_last_error=True)
u32 = ctypes.WinDLL('user32')
k32.OpenProcess.restype = wintypes.HANDLE
k32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
k32.ReadProcessMemory.restype = wintypes.BOOL
k32.ReadProcessMemory.argtypes = [wintypes.HANDLE, wintypes.LPCVOID, wintypes.LPVOID,
                                  ctypes.c_size_t, ctypes.POINTER(ctypes.c_size_t)]
k32.VirtualQueryEx.restype = ctypes.c_size_t
k32.VirtualQueryEx.argtypes = [wintypes.HANDLE, wintypes.LPCVOID, ctypes.c_void_p, ctypes.c_size_t]
u32.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
u32.EnumWindows.argtypes = [ctypes.c_void_p, wintypes.LPARAM]

GAME = r'F:/Games/Taikou 2\Taikou2 Original'
EXE = os.path.join(GAME, os.environ.get('EXE', 'TAIK2W95_family.exe'))
REV = os.path.join(GAME, '.rev')
NEEDLE = '柴田'.encode('gbk')
NEEDLE2 = '胜家'.encode('gbk')


class SI2(ctypes.Structure):
    _fields_ = [('cb', wintypes.DWORD), ('a', wintypes.LPVOID), ('b', wintypes.LPVOID), ('c', wintypes.LPVOID),
                ('x', wintypes.DWORD), ('y', wintypes.DWORD), ('xs', wintypes.DWORD), ('ys', wintypes.DWORD),
                ('x1', wintypes.DWORD), ('y1', wintypes.DWORD), ('fa', wintypes.DWORD), ('fl', wintypes.DWORD),
                ('sw', wintypes.WORD), ('r2', wintypes.WORD), ('r3', wintypes.LPVOID), ('h1', wintypes.HANDLE),
                ('h2', wintypes.HANDLE), ('h3', wintypes.HANDLE)]


class PI(ctypes.Structure):
    _fields_ = [('hp', wintypes.HANDLE), ('ht', wintypes.HANDLE), ('pid', wintypes.DWORD), ('tid', wintypes.DWORD)]


class MBI(ctypes.Structure):
    _fields_ = [('BaseAddress', ctypes.c_void_p), ('AllocationBase', ctypes.c_void_p),
                ('AllocationProtect', wintypes.DWORD), ('__align', wintypes.DWORD),
                ('RegionSize', ctypes.c_size_t), ('State', wintypes.DWORD),
                ('Protect', wintypes.DWORD), ('Type', wintypes.DWORD)]


def wins(pid):
    out = []

    @ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)
    def cb(h, lp):
        p = wintypes.DWORD(); u32.GetWindowThreadProcessId(h, ctypes.byref(p))
        if p.value == pid and u32.IsWindowVisible(h):
            r = wintypes.RECT(); u32.GetClientRect(h, ctypes.byref(r)); out.append((h, r.right, r.bottom))
        return True
    u32.EnumWindows(cb, 0); return out


def scan(hk, needles, lo=0x400000, hi=0x80000000):
    hits = []
    addr = lo; mbi = MBI()
    CH = 1 << 20
    while addr < hi:
        if not k32.VirtualQueryEx(hk, ctypes.c_void_p(addr), ctypes.byref(mbi), ctypes.sizeof(mbi)):
            addr += 0x1000; continue
        base = mbi.BaseAddress or 0
        size = mbi.RegionSize or 0
        ok = (mbi.State == 0x1000 and not (mbi.Protect & 0x100)
              and (mbi.Protect & (0x02 | 0x04 | 0x20 | 0x40)))
        if ok and size:
            off = 0
            while off < size:
                n = min(CH, size - off)
                buf = ctypes.create_string_buffer(n); got = ctypes.c_size_t()
                if k32.ReadProcessMemory(hk, ctypes.c_void_p(base + off), buf, n, ctypes.byref(got)) and got.value:
                    d = buf.raw[:got.value]
                    for nd in needles:
                        p = 0
                        while True:
                            i = d.find(nd, p)
                            if i < 0:
                                break
                            hits.append((base + off + i, nd))
                            p = i + 1
                off += n
        addr = base + size if size else addr + 0x1000
    return hits


hp = hk = main = None
try:
    si = SI2(); si.cb = ctypes.sizeof(si); pi = PI()
    k32.CreateProcessA(EXE.encode(), None, None, None, False, 0, None, GAME.encode(),
                       ctypes.byref(si), ctypes.byref(pi))
    hp, pid = pi.hp, pi.pid
    hk = k32.OpenProcess(0x1F0FFF, False, pid)
    t0 = time.time()
    while time.time() - t0 < 30:
        for h, w, hh in wins(pid):
            if w >= 800:
                main = h
        if main:
            break
        time.sleep(0.4)
    time.sleep(8.0)
    print('main=%s, 开始扫描(标题阶段)...' % main, flush=True)
    hits = scan(hk, [NEEDLE])
    print('标题阶段 "柴田" 命中 %d 处' % len(hits), flush=True)

    def rd(va, n):
        b = ctypes.create_string_buffer(n); got = ctypes.c_size_t()
        if not k32.ReadProcessMemory(hk, ctypes.c_void_p(va), b, n, ctypes.byref(got)):
            return None
        return b.raw[:got.value]

    def analyze(hits, tag):
        cands = []
        for a, nd in hits:
            # 该地址是否可能是记录起点(姓字段)? 检查 a+7 处是否为名字段
            nm = rd(a + 7, 7)
            if not nm:
                continue
            name7 = nm.split(b'\x00')[0]
            fa = rd(a + 0x29, 2)
            fv = struct.unpack('<H', fa)[0] if fa else None
            # 前一条: a-59
            prev = rd(a - 59, 7)
            cands.append((a, name7, fv, prev.split(b'\x00')[0][:7] if prev else b''))
        print('--- %s 候选 %d ---' % (tag, len(cands)))
        for a, name7, fv, prev in cands[:20]:
            try:
                nms = name7.decode('gbk')
            except Exception:
                nms = repr(name7)
            try:
                pv = prev.decode('gbk')
            except Exception:
                pv = repr(prev)
            print('  @%08X 名=%-8s father=%-6s  -59B处姓=%s' % (a, nms, fv, pv))
        return cands

    analyze(hits, '标题阶段')

    # 进游戏后再扫一次
    u32.SetForegroundWindow(main); time.sleep(0.5)
    for _ in range(3):
        u32.keybd_event(0x1B, 0, 0, 0); time.sleep(0.05); u32.keybd_event(0x1B, 0, 2, 0); time.sleep(1.0)
    time.sleep(6.0)
    hits2 = scan(hk, [NEEDLE])
    print('\n进入游戏后 "柴田" 命中 %d 处' % len(hits2), flush=True)
    analyze(hits2, '游戏中')
except Exception:
    print('EXC', traceback.format_exc(), flush=True)
finally:
    try:
        k32.TerminateProcess(hp, 0)
    except Exception:
        pass
    print('done', flush=True)
