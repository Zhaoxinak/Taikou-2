"""test_tree2.py — 验证「树形家族树」实机渲染

流程(全部沿用 verify2.py 里已验证过的坐标):
  启动 -> ESC 跳开场动画 -> 新游戏 -> 连点确认 -> ESC x2 到大地图
  -> 开武将信息卡 -> 点右上「家族族谱」页签 -> 读 tk_tree.log 判定渲染层跑到哪一步

判定依据:
  tk_tree.log 由渲染层自己写(WriteFile 落盘), 每推进一个阶段追加 1 字节:
    00 入show / 20 入resolve_api / 2F 出 / 30 入make_res / 3F 出 / 50 入wait_rel
    5F 出 / 6x pump / 70-7F draw_frame / 8x draw_edges / 9x draw_nodes
    E0 入entry / E1 无武将 / E2 槽位越界 / E3 命中家族 / E4 兜底柴田 / E5 无兜底
  进程若崩, 日志最后一个字节就是崩溃点。
"""
import ctypes, os, struct, time, json, traceback
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
AVI = os.path.join(GAME, 'OPENNING.AVI')
LOG = os.path.join(GAME, '.rev', 'tk_tree.log')
M = json.load(open(os.path.join(GAME, '.rev', 'tree_blobs.json')))

PRESENT = 0x534040
CARD_CUR = 0x514EE8
G_FAMILY = 0x5354C0
RSTATE = M['rstate']         # 由 build 脚本导出的 .fdata 布局, 别再手写死
RS_STAGE = RSTATE + 0x10
RS_QUIT = RSTATE + 0x0C
RS_HDC = RSTATE + 0x04
RS_FAMP = RSTATE + 0x08
GDIOK = RSTATE + 0x70

MEAN = {0x00: 'show入口', 0x01: 'show1已解析API', 0x02: 'show2', 0x03: 'show3', 0x04: 'show4',
        0x05: 'show5资源已建', 0x06: 'show6等待松开完', 0x07: 'show7帧开始', 0x08: 'show8描边完',
        0x09: 'show9节点完', 0x0A: 'show10消息泵完', 0x0B: 'show11循环回跳', 0x0C: 'show12退出',
        0x0D: 'show13收尾',
        0x20: 'resolve_api入', 0x2F: 'resolve_api出', 0x30: 'make_res入', 0x3F: 'make_res出',
        0x40: 'free_res入', 0x4F: 'free_res出', 0x50: 'wait_rel入', 0x5F: 'wait_rel出',
        0x60: 'pump入', 0x6E: 'pump收到退出', 0x6F: 'pump出',
        0x70: 'draw_frame入', 0x7F: 'draw_frame出',
        0x80: 'draw_edges入', 0x8F: 'draw_edges出',
        0x90: 'draw_nodes入', 0x9F: 'draw_nodes出',
        0xF0: 'log_init入',
        0xE0: 'entry入', 0xE1: '无当前武将', 0xE2: '槽位越界', 0xE3: '命中真实家族',
        0xE4: '未命中->兜底柴田', 0xE5: '未命中且无兜底'}


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
        if p.value == pid and u32.IsWindowVisible(h):
            r = wintypes.RECT(); u32.GetClientRect(h, ctypes.byref(r))
            out.append((h, r.right, r.bottom))
        return True
    u32.EnumWindows(cb, 0); return out


hp = hk = main = None
try:
    assert os.path.exists(AVI), 'OPENNING.AVI 缺失!'
    if os.path.exists(LOG):
        os.remove(LOG)
    si = SI2(); si.cb = ctypes.sizeof(si); pi = PI()
    assert k32.CreateProcessA(EXE.encode(), None, None, None, False, 0, None,
                              GAME.encode(), ctypes.byref(si), ctypes.byref(pi)), 'CreateProcess 失败'
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

    def exitcode():
        c = wintypes.DWORD(); k32.GetExitCodeProcess(hp, ctypes.byref(c)); return c.value

    def logbytes():
        return open(LOG, 'rb').read() if os.path.exists(LOG) else b''

    def show(tag):
        d = logbytes()
        print('  [%-14s] alive=%-5s STAGE=%-3s GDIOK=%-2s QUIT=%-2s HDC=0x%-6X FAMP=0x%-6X '
              'CARD=0x%-6X FAMILY=%s log=%s'
              % (tag, alive(), g(RS_STAGE), g(GDIOK), g(RS_QUIT), g(RS_HDC) or 0,
                 g(RS_FAMP) or 0, g(CARD_CUR) or 0, g(G_FAMILY),
                 ' '.join('%02X' % v for v in d)), flush=True)
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
            u32.keybd_event(0x1B, 0, 0, 0); time.sleep(0.05); u32.keybd_event(0x1B, 0, 2, 0)
        time.sleep(0.4)
    print('present=%s main=%s' % (last, main), flush=True)
    assert main and alive(), '标题阶段就死了 exit=0x%X' % exitcode()

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

    click(545, 310, 2.0)
    if not show('新游戏'):
        print('!! 死于 click(545,310) exit=0x%X' % exitcode()); raise SystemExit
    for i in range(3):
        click(640, 415, 2.5)
        if not show('确认%d' % i):
            print('!! 死于 click(640,415)#%d exit=0x%X' % (i, exitcode())); raise SystemExit
    key(0x1B, 1.2); key(0x1B, 1.2)
    if not show('大地图'):
        print('!! 死于 ESC exit=0x%X' % exitcode()); raise SystemExit

    print('=== 点「家族族谱」页签 ===', flush=True)
    for i, (px, py) in enumerate(((847, 258), (860, 268), (835, 250))):
        click(px, py, 1.0)
        u32.SetForegroundWindow(main)
        st = g(RS_STAGE)
        for j in range(6):
            time.sleep(0.4)
            if not show('tab%d.%d' % (i, j)):
                print('!! 点页签后崩溃 -- 日志最后一步: %s'
                      % (' '.join('%02X' for v in logbytes())), flush=True)
                raise SystemExit
            if logbytes():
                break
        if logbytes():
            print('  >>> 命中! 渲染层已启动 @(%d,%d)' % (px, py), flush=True)
            break
        key(0x1B, 0.8)
    time.sleep(3.0)
    show('保持3s')
    key(0x1B, 1.2)
    show('ESC关闭')
    key(0x1B, 1.2)
    show('再ESC')
    print('=== 日志轨迹 ===')
    d = logbytes()
    print('  ' + ' '.join('%02X' % v for v in d))
    print('  末步: %s' % MEAN.get(d[-1], '?') if d else '  (空)')
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
