"""verify_ptr.py — 验证 0x524a20 是否存放 BSDATA 常驻缓冲指针
(GAME_DATA_SPEC.md 记载 LoadBSDATA 0x47fa90 的目标常驻缓冲 = 0x524a20, 大小 0xa154=41300=700*59)
"""
import ctypes, os, struct, time, traceback
from ctypes import wintypes

k32 = ctypes.WinDLL('kernel32', use_last_error=True); u32 = ctypes.WinDLL('user32')
k32.OpenProcess.restype = wintypes.HANDLE
k32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
k32.ReadProcessMemory.restype = wintypes.BOOL
k32.ReadProcessMemory.argtypes = [wintypes.HANDLE, wintypes.LPCVOID, wintypes.LPVOID,
                                  ctypes.c_size_t, ctypes.POINTER(ctypes.c_size_t)]
u32.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
u32.EnumWindows.argtypes = [ctypes.c_void_p, wintypes.LPARAM]

GAME = r'F:/Games/Taikou 2\Taikou2 Original'
EXE = os.path.join(GAME, os.environ.get('EXE', 'TAIK2W95_family.exe'))


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
    time.sleep(9.0)

    def rd(va, n):
        b = ctypes.create_string_buffer(n); got = ctypes.c_size_t()
        if not k32.ReadProcessMemory(hk, ctypes.c_void_p(va), b, n, ctypes.byref(got)):
            return None
        return b.raw[:got.value]

    def s7(d, o):
        d = d[o:o + 7].split(b'\x00')[0]
        try:
            return d.decode('gbk')
        except Exception:
            return repr(d)

    for slot in (0x524a20, 0x524a24, 0x524a18, 0x524a10):
        d = rd(slot, 4)
        v = struct.unpack('<I', d)[0] if d else 0
        print('@%08X : %08X' % (slot, v), flush=True)

    PTR = rd(0x524a20, 4)
    p = struct.unpack('<I', PTR)[0] if PTR else 0
    print('\ndword[0x524a20] = 0x%08X' % p, flush=True)
    if p:
        head = rd(p, 59 * 3)
        if head:
            print(' 记录0: 名=%-6s 姓=%-6s father=%d' % (s7(head, 0), s7(head, 7), struct.unpack_from('<H', head, 0x29)[0]))
            print(' 记录1: 名=%-6s 姓=%-6s father=%d' % (s7(head, 59), s7(head, 59 + 7), struct.unpack_from('<H', head, 59 + 0x29)[0]))
            r36 = rd(p + 36 * 59, 59)
            print(' 记录36:名=%-6s 姓=%-6s father=%d' % (s7(r36, 0), s7(r36, 7), struct.unpack_from('<H', r36, 0x29)[0]))
            r699 = rd(p + 699 * 59, 59)
            print(' 记录699:名=%-6s 姓=%-6s' % (s7(r699, 0), s7(r699, 7)))
            print(' --> %s' % ('✔ 0x524a20 就是母表指针' % () if s7(head, 59) == '胜家' and s7(head, 59 + 7) == '柴田' else '✖ 不匹配'), flush=True)
    # 顺便: 两个剧本切换会不会变? 读第二份?
    print('\n--- 检查附近其他可能指针 ---', flush=True)
    for off in (-8, -4, 4, 8, 0x40, -0x40):
        d = rd(0x524a20 + off, 4)
        print('  @%08X = %08X' % (0x524a20 + off, struct.unpack('<I', d)[0] if d else 0), flush=True)
except Exception:
    print('EXC', traceback.format_exc(), flush=True)
finally:
    try:
        k32.TerminateProcess(pi.hp, 0)
    except Exception:
        pass
print('done', flush=True)
