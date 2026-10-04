"""tkprobe.py — 逐步探测: 启动后每一步都报「是否存活 + tk_tree.log + 关键全局变量」

用来定位「导航阶段就退出」到底是哪个动作弄死的。
用法: python tkprobe.py [步骤数]
"""
import ctypes, json, os, struct, sys, time, traceback
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
LOG = os.path.join(GAME, 'tk_tree.log')
REV = os.path.join(GAME, '.rev')
M = json.load(open(os.path.join(REV, 'tree_blobs.json')))
RSTATE = M['rstate']
CARD_CUR = 0x514EE8
RS_STAGE = RSTATE + 0x10
PRESENT = 0x534040
G_LOOPCNT = 0x535EEC
G_CLICK = 0x535F20
G_HIT = 0x535F24
G_IN = 0x535F3C
G_FAMILY = 0x5354C0

MEAN = {0x00: 'show入口', 0x01: 'show1', 0x02: 'show2', 0x03: 'show3', 0x04: 'show4',
        0x05: 'show5', 0x06: 'show6', 0x07: 'show7', 0x08: 'show8', 0x09: 'show9',
        0x0A: 'show10', 0x0B: 'show11', 0x0C: 'show12', 0x0D: 'show13',
        0x20: 'api入', 0x2F: 'api出', 0x30: 'mk入', 0x3F: 'mk出', 0x40: 'fr入',
        0x4F: 'fr出', 0x50: 'wt入', 0x5F: 'wt出', 0x60: 'pm入', 0x6E: 'pm退',
        0x6F: 'pm出', 0x70: 'df入', 0x7F: 'df出', 0x80: 'de入', 0x8F: 'de出',
        0x90: 'dn入', 0x9F: 'dn出', 0xE0: 'entry入', 0xE1: '无武将',
        0xE2: '槽位越界', 0xE3: '命中', 0xE4: '兜底', 0xE5: '无兜底'}


class PI(ctypes.Structure):
    _fields_ = [('hp', wintypes.HANDLE), ('ht', wintypes.HANDLE),
                ('pid', wintypes.DWORD), ('tid', wintypes.DWORD)]


def wins(pid):
    out = []

    @ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)
    def cb(h, lp):
        p = wintypes.DWORD(); u32.GetWindowThreadProcessId(h, ctypes.byref(p))
        if p.value == pid and u32.IsWindowVisible(h):
            r = wintypes.RECT(); u32.GetClientRect(h, ctypes.byref(r))
            out.append((h, r.right, r.bottom))
        return True
    u32.EnumWindows(cb, 0); return out


hp = hk = main = None
try:
    if os.path.exists(LOG):
        os.remove(LOG)
    sb = ctypes.create_string_buffer(68); struct.pack_into('<I', sb, 0, 68)
    pi = PI()
    assert k32.CreateProcessA(EXE.encode(), None, None, None, False, 0, None,
                              GAME.encode(), sb, ctypes.byref(pi)), 'CreateProcess 失败'
    hp, pid = pi.hp, pi.pid
    hk = k32.OpenProcess(0x1F0FFF, False, pid)
    print('pid=%d' % pid)

    def rd(va, n):
        b = ctypes.create_string_buffer(n); got = ctypes.c_size_t()
        return b.raw[:got.value] if k32.ReadProcessMemory(hk, ctypes.c_void_p(va), b, n,
                                                          ctypes.byref(got)) else None

    def g(va):
        d = rd(va, 4)
        return struct.unpack('<I', d)[0] if d and len(d) == 4 else None

    def alive():
        c = wintypes.DWORD()
        return bool(k32.GetExitCodeProcess(hp, ctypes.byref(c)) and c.value == 259)

    def exitcode():
        c = wintypes.DWORD()
        k32.GetExitCodeProcess(hp, ctypes.byref(c))
        return c.value

    def st(tag):
        d = b''
        if os.path.exists(LOG):
            d = open(LOG, 'rb').read()
        print('  [%-14s] 存活=%-5s present=%-6s CARD=0x%06X STAGE=%-4s FAM=%-3s '
              'LOOP=%-6s CLICK=%-4s HIT=%-3s IN=%-3s log=%s'
              % (tag, alive(), g(PRESENT), g(CARD_CUR) or 0, g(RS_STAGE),
                 g(G_FAMILY), g(G_LOOPCNT), g(G_CLICK), g(G_HIT), g(G_IN),
                 ' '.join('%02X%s' % (v, '') for v in d)))
        return alive()

    t0 = time.time(); last = -1; stable = 0; skip_t = 0.0
    while time.time() - t0 < 90:
        for h, w, hh in wins(pid):
            if w >= 800:
                main = h
        d = rd(PRESENT, 4); cnt = struct.unpack('<I', d)[0] if d else -1
        stable = stable + 1 if cnt == last else 0; last = cnt
        if cnt >= 71 and stable > 8 and main:
            break
        if time.time() - skip_t > 1.2:
            skip_t = time.time()
            if main:
                u32.SetForegroundWindow(main)
            u32.keybd_event(0x1B, 0, 0, 0); time.sleep(0.05)
            u32.keybd_event(0x1B, 0, 2, 0)
        time.sleep(0.4)
    print('present=%s main=%s' % (last, main))
    assert main and st('等到标题'), '标题阶段就死了 exit=0x%X' % exitcode()

    u32.SetForegroundWindow(main); time.sleep(0.4)
    pt = wintypes.POINT(0, 0); u32.ClientToScreen(main, ctypes.byref(pt))
    CX0, CY0 = pt.x, pt.y

    def click(px, py, wait=1.2):
        u32.SetForegroundWindow(main)
        u32.SetCursorPos(CX0 + px, CY0 + py); time.sleep(0.30)
        u32.mouse_event(2, 0, 0, 0, 0); time.sleep(0.10)
        u32.mouse_event(4, 0, 0, 0, 0); time.sleep(wait)

    def key(vk, wait=1.0):
        u32.keybd_event(vk, 0, 0, 0); time.sleep(0.06)
        u32.keybd_event(vk, 0, 2, 0); time.sleep(wait)

    print('--- 空转 5s(不输入) ---')
    time.sleep(5.0)
    if not st('空转后'):
        print('!! 不输入也会死 exit=0x%X' % exitcode()); raise SystemExit

    print('--- click(545,310) 「开始新游戏」---')
    click(545, 310, 2.0)
    if not st('新游戏'):
        print('!! 死于 click(545,310) exit=0x%X' % exitcode()); raise SystemExit

    print('--- click(640,415) x3 角色/能力确认 ---')
    for i in range(3):
        click(640, 415, 2.5)
        if not st('确认%d' % i):
            print('!! 死于 click(640,415)#%d exit=0x%X' % (i, exitcode())); raise SystemExit

    print('--- ESC x2 ---')
    key(0x1B, 1.2)
    if not st('ESC1'):
        print('!! 死于 ESC1 exit=0x%X' % exitcode()); raise SystemExit
    key(0x1B, 1.2)
    if not st('ESC2'):
        print('!! 死于 ESC2 exit=0x%X' % exitcode()); raise SystemExit
    print('导航完成')
except SystemExit:
    pass
except Exception:
    print(traceback.format_exc())
finally:
    try:
        if hp and alive():
            k32.TerminateProcess(hp, 0)
    except Exception:
        pass
    print('done')
