"""dump_ents.py — 从运行中的游戏进程 dump 实体表 (370 x 47), 供家族族谱取证
不修改任何 exe / 数据, 只读内存。产物: ents_dump.json + 控制台分析
"""
import ctypes, json, os, struct, sys, time, traceback
from ctypes import wintypes

k32 = ctypes.WinDLL('kernel32', use_last_error=True)
u32 = ctypes.WinDLL('user32')
k32.OpenProcess.restype = wintypes.HANDLE
k32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
k32.ReadProcessMemory.restype = wintypes.BOOL
k32.ReadProcessMemory.argtypes = [wintypes.HANDLE, wintypes.LPCVOID, wintypes.LPVOID,
                                  ctypes.c_size_t, ctypes.POINTER(ctypes.c_size_t)]
u32.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
u32.EnumWindows.argtypes = [ctypes.c_void_p, wintypes.LPARAM]
u32.GetClientRect.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.RECT)]

GAME = r'F:/Games/Taikou 2\Taikou2 Original'
EXE = os.path.join(GAME, os.environ.get('EXE', 'TAIK2W95_family.exe'))
REV = os.path.join(GAME, '.rev')

EBASE, ESTRIDE, ECOUNT = 0x519868, 47, 0x172
SUR_BASE, GIV_BASE, NAME_STRIDE = 0x520660, 0x521aa8, 7


class SI2(ctypes.Structure):
    _fields_ = [('cb', wintypes.DWORD), ('a', wintypes.LPVOID), ('b', wintypes.LPVOID), ('c', wintypes.LPVOID),
                ('x', wintypes.DWORD), ('y', wintypes.DWORD), ('xs', wintypes.DWORD), ('ys', wintypes.DWORD),
                ('x1', wintypes.DWORD), ('y1', wintypes.DWORD), ('fa', wintypes.DWORD), ('fl', wintypes.DWORD),
                ('sw', wintypes.WORD), ('r2', wintypes.WORD), ('r3', wintypes.LPVOID), ('h1', wintypes.HANDLE),
                ('h2', wintypes.HANDLE), ('h3', wintypes.HANDLE)]


class PI(ctypes.Structure):
    _fields_ = [('hp', wintypes.HANDLE), ('ht', wintypes.HANDLE), ('pid', wintypes.DWORD), ('tid', wintypes.DWORD)]


def wins(pid):
    out = []

    @ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)
    def cb(h, lp):
        p = wintypes.DWORD(); u32.GetWindowThreadProcessId(h, ctypes.byref(p))
        if p.value == pid and u32.IsWindowVisible(h):
            r = wintypes.RECT(); u32.GetClientRect(h, ctypes.byref(r)); out.append((h, r.right, r.bottom))
        return True
    u32.EnumWindows(cb, 0); return out


def gbk7(b):
    b = b.split(b'\x00')[0]
    for enc in ('gbk', 'cp936', 'latin1'):
        try:
            return b.decode(enc)
        except Exception:
            pass
    return repr(b)


hp = hk = main = None
try:
    si = SI2(); si.cb = ctypes.sizeof(si); pi = PI()
    ok = k32.CreateProcessA(EXE.encode(), None, None, None, False, 0, None, GAME.encode(),
                            ctypes.byref(si), ctypes.byref(pi))
    print('CreateProcess', ok, flush=True)
    hp, pid = pi.hp, pi.pid
    hk = k32.OpenProcess(0x1F0FFF, False, pid)

    def rd(va, n):
        b = ctypes.create_string_buffer(n); got = ctypes.c_size_t()
        if not k32.ReadProcessMemory(hk, ctypes.c_void_p(va), b, n, ctypes.byref(got)):
            return None
        return b.raw[:got.value]

    def g(va, n=4):
        d = rd(va, n)
        return struct.unpack('<I', d)[0] if d and len(d) == 4 else None

    def key(vk, wait=0.8):
        u32.keybd_event(vk, 0, 0, 0); time.sleep(0.06); u32.keybd_event(vk, 0, 2, 0); time.sleep(wait)

    def click(px, py, wait=0.8):
        u32.SetCursorPos(CX0 + px, CY0 + py); time.sleep(0.35)
        u32.mouse_event(2, 0, 0, 0, 0); time.sleep(0.10); u32.mouse_event(4, 0, 0, 0, 0); time.sleep(wait)

    # ---------- 阶段1: 等主窗口 + 跳过开场动画 ----------
    t0 = time.time(); skip_t = 0.0
    while time.time() - t0 < 90:
        for h, w, hh in wins(pid):
            if w >= 800:
                main = h
        if main and time.time() - skip_t > 1.2:
            skip_t = time.time()
            u32.SetForegroundWindow(main); key(0x1B, 0.05)
        if main:
            d = rd(0x534040, 4)
            if d and struct.unpack('<I', d)[0] >= 71:
                break
        time.sleep(0.4)
    print('main=%s  after %.1fs' % (main, time.time() - t0), flush=True)
    if not main:
        raise SystemExit('no window')

    wr = wintypes.RECT(); u32.GetWindowRect(main, ctypes.byref(wr))
    cr = wintypes.RECT(); u32.GetClientRect(main, ctypes.byref(cr))
    pt = wintypes.POINT(0, 0); u32.ClientToScreen(main, ctypes.byref(pt))
    CX0, CY0, CW, CH = pt.x, pt.y, cr.right, cr.bottom
    print('client %dx%d @ (%d,%d)' % (CW, CH, CX0, CY0), flush=True)
    u32.SetForegroundWindow(main); time.sleep(0.5)

    # ---------- 阶段2: 新游戏 -> 选主角 ----------
    if os.environ.get('SKIP_UI', '0') != '1':
        click(545, 310, 2.0)
        click(640, 415, 2.5)
        click(640, 415, 2.5)
        click(640, 415, 3.0)
        key(0x1B, 1.2); key(0x1B, 1.2)
        time.sleep(3.0)

    # ---------- 阶段3: dump 实体表 ----------
    raw = rd(EBASE, ESTRIDE * ECOUNT)
    if not raw or len(raw) != ESTRIDE * ECOUNT:
        raise SystemExit('实体表读取失败 got=%s' % (len(raw) if raw else None))
    ents = []
    for i in range(ECOUNT):
        r = raw[i * ESTRIDE:(i + 1) * ESTRIDE]
        oid = struct.unpack_from('<H', r, 0x00)[0]
        father = struct.unpack_from('<H', r, 0x1d)[0]
        status = struct.unpack_from('<H', r, 0x2c)[0]
        if oid >= 1000:
            nm = gv = '?'
        else:
            nm = gbk7(rd(SUR_BASE + oid * NAME_STRIDE, NAME_STRIDE) or b'')
            gv = gbk7(rd(GIV_BASE + oid * NAME_STRIDE, NAME_STRIDE) or b'')
        ents.append({'slot': i, 'oid': oid, 'father': father, 'status': status,
                     'given': nm, 'surname': gv, 'raw': r.hex()})
    json.dump(ents, open(os.path.join(REV, 'ents_dump.json'), 'w', encoding='utf-8'),
              ensure_ascii=False, indent=1)
    print('dumped %d ents -> ents_dump.json' % len(ents), flush=True)

    # ---------- 分析 ----------
    live = [e for e in ents if e['oid'] < 1000 and (e['given'] != '?' or e['surname'] != '?')]
    print('有效实体(oid<1000 且姓名可读): %d' % len(live), flush=True)
    print('unique oid: %d' % len(set(e['oid'] for e in live)), flush=True)
    fam = [e for e in live if e['father'] != 0xFFFF]
    print('有 father 的实体: %d' % len(fam), flush=True)
    print('--- 样例 12 条 ---')
    for e in live[:12]:
        print('  slot%3d oid%4d %s %s father=%s status=%04X' %
              (e['slot'], e['oid'], e['surname'], e['given'], e['father'], e['status']))
    print('--- father != FFFF ---')
    byoid = {e['oid']: e for e in live}
    for e in fam:
        p = byoid.get(e['father'])
        print('  slot%3d %s %s (oid %d) -> father %d %s' %
              (e['slot'], e['surname'], e['given'], e['oid'], e['father'],
               ('%s %s' % (p['surname'], p['given'])) if p else '(不在场)'))
    sh = [e for e in live if e['surname'] in ('柴田', '佐久间', '织田', '毛利')]
    print('--- 特定姓 ---')
    for e in sh:
        print('  slot%3d oid%4d %s %s father=%s' % (e['slot'], e['oid'], e['surname'], e['given'], e['father']))
except Exception:
    print('EXC', traceback.format_exc(), flush=True)
finally:
    try:
        k32.TerminateProcess(hp, 0)
    except Exception:
        pass
    print('done', flush=True)
