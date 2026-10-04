"""probe_names.py — 验证运行时姓名表 (名 0x520660 / 姓 0x521aa8) 是否覆盖全部 700 名武将
(而不是只覆盖当前在场的 370 个实体)。这决定了「不在场成员能否显示」。
"""
import ctypes, json, os, struct, time, traceback
from ctypes import wintypes

k32 = ctypes.WinDLL('kernel32', use_last_error=True); u32 = ctypes.WinDLL('user32')
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
GIVEN_T, SURNAME_T, STRIDE = 0x520660, 0x521aa8, 7


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


si = SI2(); si.cb = ctypes.sizeof(si); pi = PI()
k32.CreateProcessA(EXE.encode(), None, None, None, False, 0, None, GAME.encode(),
                   ctypes.byref(si), ctypes.byref(pi))
hk = k32.OpenProcess(0x1F0FFF, False, pi.pid)
try:
    main = None; t0 = time.time()
    while time.time() - t0 < 30:
        for h, w, hh in wins(pi.pid):
            if w >= 800:
                main = h
        if main:
            break
        time.sleep(0.4)

    def rd(va, n):
        b = ctypes.create_string_buffer(n); got = ctypes.c_size_t()
        if not k32.ReadProcessMemory(hk, ctypes.c_void_p(va), b, n, ctypes.byref(got)):
            return None
        return b.raw[:got.value]

    def key(vk, w=0.8):
        u32.keybd_event(vk, 0, 0, 0); time.sleep(0.06); u32.keybd_event(vk, 0, 2, 0); time.sleep(w)

    t1 = time.time(); skip_t = 0.0
    while time.time() - t1 < 100:
        if time.time() - skip_t > 1.0:
            skip_t = time.time(); u32.SetForegroundWindow(main); key(0x1B, 0.05)
        d = rd(0x534040, 4)
        if d and struct.unpack('<I', d)[0] >= 71:
            break
        time.sleep(0.4)
    print('到标题 %.1fs' % (time.time() - t1), flush=True)

    def dump_tables(tag):
        G = rd(GIVEN_T, STRIDE * 1000); S = rd(SURNAME_T, STRIDE * 1000)
        if not G or not S:
            print('[%s] 姓名表读取失败' % tag, flush=True); return None
        rows = []
        for i in range(1000):
            g = G[i * 7:i * 7 + 7].split(b'\x00')[0]
            s = S[i * 7:i * 7 + 7].split(b'\x00')[0]
            def dec(x):
                try:
                    return x.decode('gbk')
                except Exception:
                    return None
            rows.append((dec(g), dec(s), g, s))
        valid = [i for i, r in enumerate(rows) if r[0] and r[1]]
        print('[%s] 有效姓名槽 %d 个, 范围 %d..%d' % (tag, len(valid), min(valid) if valid else -1, max(valid) if valid else -1), flush=True)
        for i in (0, 1, 9, 11, 36, 39, 43, 46, 100, 255, 256, 266, 500, 695, 699, 742, 999):
            if i >= 1000:
                continue
            g, s, gb, sb = rows[i]
            print('   [%3d] 名=%-5s 姓=%-5s  raw=%s|%s' % (i, g, s, gb.hex(), sb.hex()), flush=True)
        return rows

    r1 = dump_tables('标题')
    # 进游戏
    rc = wintypes.RECT(); u32.GetClientRect(main, ctypes.byref(rc))
    pt = wintypes.POINT(0, 0); u32.ClientToScreen(main, ctypes.byref(pt))
    CX0, CY0 = pt.x, pt.y
    u32.SetForegroundWindow(main); time.sleep(0.5)

    def click(px, py, w=2.0):
        u32.SetCursorPos(CX0 + px, CY0 + py); time.sleep(0.35)
        u32.mouse_event(2, 0, 0, 0, 0); time.sleep(0.10); u32.mouse_event(4, 0, 0, 0, 0); time.sleep(w)
    click(545, 310, 2.0); click(640, 415, 2.5); click(640, 415, 2.5); click(640, 415, 3.0)
    key(0x1B, 1.2); key(0x1B, 1.2); time.sleep(2.5)
    r2 = dump_tables('游戏中')
    if r2:
        json.dump([{'i': i, 'given': r[0], 'surname': r[1]} for i, r in enumerate(r2)],
                  open(os.path.join(REV, 'runtime_names.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
        print(' -> runtime_names.json (%d 槽)' % len(r2), flush=True)
except Exception:
    print('EXC', traceback.format_exc(), flush=True)
finally:
    try:
        k32.TerminateProcess(pi.hp, 0)
    except Exception:
        pass
print('done', flush=True)
