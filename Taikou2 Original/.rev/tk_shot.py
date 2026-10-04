"""tk_shot.py — 打开家族树 -> 截图 -> 验证平移 -> 关闭

流程: 启动 -> ESC 跳动画 -> 新游戏 -> 大地图 -> 点「家族族谱」页签
      -> 截图(整棵树) -> 方向键平移 -> 分别截图 -> ESC 关闭
用法: python tk_shot.py
"""
import ctypes, json, os, struct, time, zlib, traceback
from ctypes import wintypes

k32 = ctypes.WinDLL('kernel32', use_last_error=True)
u32 = ctypes.WinDLL('user32')
g32 = ctypes.WinDLL('gdi32')
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
g32.CreateCompatibleDC.argtypes = [wintypes.HDC]; g32.CreateCompatibleDC.restype = wintypes.HDC
g32.CreateCompatibleBitmap.argtypes = [wintypes.HDC, ctypes.c_int, ctypes.c_int]
g32.CreateCompatibleBitmap.restype = wintypes.HBITMAP
g32.SelectObject.argtypes = [wintypes.HDC, wintypes.HGDIOBJ]; g32.SelectObject.restype = wintypes.HGDIOBJ
g32.BitBlt.argtypes = [wintypes.HDC, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int,
                       wintypes.HDC, ctypes.c_int, ctypes.c_int, wintypes.DWORD]
g32.GetDIBits.argtypes = [wintypes.HDC, wintypes.HBITMAP, ctypes.c_uint, ctypes.c_uint,
                          ctypes.c_void_p, ctypes.c_void_p, ctypes.c_uint]

GAME = r'F:\Games\Taikou 2\Taikou2 Original'
EXE = os.environ.get('TK_EXE') or os.path.join(GAME, 'TAIK2W95_family.exe')
AVI = os.path.join(GAME, 'OPENNING.AVI')
REV = os.path.join(GAME, '.rev')
TAG = os.environ.get('TAG', 'tree')

M = json.load(open(os.path.join(REV, 'tree_blobs.json')))
RV = M['rstate']
RS = dict(HWND=0x00, HDC=0x04, FAMP=0x08, QUIT=0x0C, STAGE=0x10,
          PANX=0x68, PANY=0x6C,
          MX0=0x70, MY0=0x74, DRAG=0x78, MOVED=0x7C,
          WX0=0x80, WY0=0x84, WX1=0x88, WY1=0x8C,
          VX0=0x90, VY0=0x94, VX1=0x98, VY1=0x9C,
          CW=0xA0, CH=0xA4)
GDI_TAB = M['gdi_tab']
RC_VA = M['sec_va'] + 0x4C0        # O_SCRATCH: RECT(16) + MSG(28) + POINT(8)
PT_VA = RC_VA + 16 + 28
API_NAMES = ['Sleep', 'GetActiveWindow', 'PeekMessageA', 'GetDC', 'ReleaseDC', 'CreatePen',
             'CreateSolidBrush', 'SelectObject', 'DeleteObject', 'Rectangle', 'Ellipse',
             'MoveToEx', 'LineTo', 'SetTextColor', 'SetBkMode', 'SetTextAlign', 'TextOutA',
             'CreateFontA', 'GetStockObject', 'GetAsyncKeyState', 'CreateFileA', 'WriteFile',
             'GetClientRect', 'GetCursorPos', 'IntersectClipRect', 'SelectClipRgn']


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
    assert os.path.exists(AVI)
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

    def g(va, sg=True):
        d = rd(va, 4)
        return struct.unpack('<i' if sg else '<I', d)[0] if d and len(d) == 4 else None

    def alive():
        c = wintypes.DWORD()
        return bool(k32.GetExitCodeProcess(hp, ctypes.byref(c)) and c.value == 259)

    t0 = time.time(); last = -1; stable = 0; sk = 0.0
    while time.time() - t0 < 90:
        for h, w, hh in wins(pid):
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
    assert main, '主窗口未找到'
    u32.SetForegroundWindow(main); time.sleep(0.4)
    cr = wintypes.RECT(); u32.GetClientRect(main, ctypes.byref(cr))
    CW, CH = cr.right, cr.bottom
    pt = wintypes.POINT(0, 0); u32.ClientToScreen(main, ctypes.byref(pt))
    CX0, CY0 = pt.x, pt.y
    print('client %dx%d @screen (%d,%d)' % (CW, CH, CX0, CY0), flush=True)

    def click(px, py, wait=0.8):
        u32.SetForegroundWindow(main)
        u32.SetCursorPos(CX0 + px, CY0 + py); time.sleep(0.35)
        u32.mouse_event(2, 0, 0, 0, 0); time.sleep(0.10)
        u32.mouse_event(4, 0, 0, 0, 0); time.sleep(wait)

    def key(vk, wait=0.8):
        u32.keybd_event(vk, 0, 0, 0); time.sleep(0.06)
        u32.keybd_event(vk, 0, 2, 0); time.sleep(wait)

    def hold(vk, ms):
        """按住某键 —— 平移是每帧轮询 GetAsyncKeyState, 一闪而过的敲击可能被漏掉"""
        u32.SetForegroundWindow(main); time.sleep(0.15)
        u32.keybd_event(vk, 0, 0, 0); time.sleep(ms / 1000.0)
        u32.keybd_event(vk, 0, 2, 0); time.sleep(0.35)

    def shot(tag):
        u32.SetForegroundWindow(main); time.sleep(0.35)
        dcv = u32.GetDC(0); mdc = g32.CreateCompatibleDC(dcv)
        bmp = g32.CreateCompatibleBitmap(dcv, CW, CH)
        g32.SelectObject(mdc, bmp)
        g32.BitBlt(mdc, 0, 0, CW, CH, dcv, CX0, CY0, 0x00CC0020)
        bi = struct.pack('<IiiHHIIiiII', 40, CW, -CH, 1, 24, 0, 0, 0, 0, 0, 0)
        buf = ctypes.create_string_buffer(CW * CH * 3)
        g32.GetDIBits(mdc, bmp, 0, CH, buf, ctypes.create_string_buffer(bi, len(bi)), 0)
        # 24bpp DIB 在内存里是 BGR 顺序, 写 PNG 前必须换成 RGB
        # (不换的话截图里所有颜色 R/B 颠倒, 会把正确配色误判成写错)
        src = buf.raw
        rows = []
        for y in range(CH):
            ln = bytearray(src[y * CW * 3:(y + 1) * CW * 3])
            ln[0::3], ln[2::3] = ln[2::3], ln[0::3]
            rows.append(b'\x00' + bytes(ln))
        raw = b''.join(rows)

        def ch(t, dd):
            c = t + dd
            return struct.pack('>I', len(dd)) + c + struct.pack('>I', zlib.crc32(c))
        png = (b'\x89PNG\r\n\x1a\n' + ch(b'IHDR', struct.pack('>IIBBBBB', CW, CH, 8, 2, 0, 0, 0))
               + ch(b'IDAT', zlib.compress(raw, 6)) + ch(b'IEND', b''))
        p = os.path.join(REV, 'tk_%s_%s.png' % (TAG, tag))
        open(p, 'wb').write(png)
        print('  shot %-10s %7dB  %s' % (tag, len(png), os.path.basename(p)), flush=True)
        return p, raw

    G_CAVE = dict(PCALL=0x535F44, BUSY=0x535F40, LBDOWN=0x535EE0, LBSEEN=0x535EE4,
                  LBPREV=0x535EE8, LOOPCNT=0x535EEC, CLICK=0x535F20, HIT=0x535F24,
                  IN=0x535F3C, MX=0x535F18, MY=0x535F1C, HOOK=0x535E50, CNT_B=0x535E58)

    def diag(tag):
        d = {k: g(v) for k, v in G_CAVE.items()}
        print('  <%s> ft_probe=%s 卡片循环=%s ft_click=%s 命中=%s LBDOWN=%s LBSEEN=%s '
              '鼠标逻辑=(%s,%s) 在框内=%s 卡片绘制=%s 卡片绘制B=%s'
              % (tag, d['PCALL'], d['LOOPCNT'], d['CLICK'], d['HIT'], d['LBDOWN'],
                 d['LBSEEN'], d['MX'], d['MY'], d['IN'], d['HOOK'], d['CNT_B']), flush=True)
        return d

    def state(tag):
        s = {k: g(RV + v) for k, v in RS.items()}
        print('  [%-10s] STAGE=%-3s PAN=(%s,%s) 面板 x%s..%s y%s..%s 视口 x%s..%s y%s..%s '
              'DRAG=%s MOVED=%s FAMP=0x%X'
              % (tag, s['STAGE'], s['PANX'], s['PANY'], s['WX0'], s['WX1'], s['WY0'], s['WY1'],
                 s['VX0'], s['VX1'], s['VY0'], s['VY1'], s['DRAG'], s['MOVED'], s['FAMP'] or 0),
              flush=True)
        print('  [%-10s] HWND=0x%X HDC=0x%X CW=%s CH=%s  RC=(%s,%s,%s,%s)'
              % (tag, s['HWND'] or 0, s['HDC'] or 0, s['CW'], s['CH'],
                 g(RC_VA), g(RC_VA + 4), g(RC_VA + 8), g(RC_VA + 12)), flush=True)
        d = rd(RV, 0x100)
        if d:
            for i in range(0, 0x100, 16):
                print('   %04X  %s' % (i, ' '.join('%02X' % b for b in d[i:i + 16])), flush=True)
        return s

    LOG = os.path.join(REV, 'tk_tree.log')
    try:                       # 沙箱会拦截 os.remove, 改成截断即可
        open(LOG, 'wb').close()
    except Exception:
        pass

    def logn():
        return len(open(LOG, 'rb').read()) if os.path.exists(LOG) else 0

    # ---- 到大地图(坐标取自 verify2.py 里验证过的序列) ----
    time.sleep(1.5); click(545, 310, 2.0)
    click(640, 415, 2.5); click(640, 415, 2.5); click(640, 415, 3.0)
    key(0x1B, 1.2); key(0x1B, 1.2)
    shot('00_map')
    state('map')

    # ---- 卡片重绘速率: 决定「挂在绘制收尾」的探测能不能独立工作 ----
    print('=== 卡片重绘速率 (空闲 1.2s) ===', flush=True)
    c0 = diag('t0')
    time.sleep(1.2)
    c1 = diag('t1')
    print('   1.2s 内: 卡片绘制 %s 次 / ft_probe %s 次 / 卡片循环 %s 圈'
          % ((c1['HOOK'] or 0) - (c0['HOOK'] or 0), (c1['PCALL'] or 0) - (c0['PCALL'] or 0),
             (c1['LOOPCNT'] or 0) - (c0['LOOPCNT'] or 0)), flush=True)

    # ---- 点卡片右上「家族族谱」页签 ----
    print('=== 点页签打开家族树 ===', flush=True)
    hit = None
    for i, (px, py) in enumerate(((847, 258), (860, 268), (835, 250), (855, 262))):
        n0 = logn()
        click(px, py, 0.8)
        time.sleep(1.5)
        diag('click%d@%d,%d' % (i, px, py))
        if logn() > n0:
            hit = (px, py)
            print('   >>> 页签命中 @(%d,%d)' % (px, py), flush=True)
            break
        print('   tab%d @(%d,%d) 无反应' % (i, px, py), flush=True)
    if not hit:
        print('   页签未命中 -> 按 F9 兜底', flush=True)
        key(0x78, 1.5)
    time.sleep(1.0)
    shot('01_open')
    s1 = state('open')

    # ---- 连拍: 区分「根本没画」和「画了但被游戏重绘盖掉」 ----
    print('=== 连拍 14 帧 (每 60ms) ===', flush=True)
    prev = None
    nz = 0
    for i in range(14):
        _, cur = shot('b%02d' % i)
        if prev is not None:
            dd = sum(1 for a, b in zip(cur, prev) if a != b)
            if dd:
                nz += 1
            print('   帧%02d 与前一帧差 %6d 像素 (%.2f%%)' % (i, dd, dd * 100.0 / len(cur)),
                  flush=True)
        prev = cur
        time.sleep(0.06)
    print('   有变化的帧: %d / 13  ->  %s' % (nz, '画面在动(疑似被重绘)' if nz else '画面静止'), flush=True)

    # ---- 平移测试 ----
    print('=== 平移测试 ===', flush=True)
    for vk, ms, tag in ((0x27, 350, '02_right'), (0x28, 350, '03_down'),
                        (0x25, 700, '04_left'), (0x26, 350, '05_up')):
        hold(vk, ms)
        shot(tag)
        state(tag)

    # ---- 关闭 ----
    # ---- 鼠标拖拽平移 ----
    print('=== 拖拽测试 (按住左键上移 90px) ===', flush=True)
    u32.SetForegroundWindow(main); time.sleep(0.3)
    u32.SetCursorPos(CX0 + 640, CY0 + 500); time.sleep(0.25)
    u32.mouse_event(2, 0, 0, 0, 0); time.sleep(0.25)           # LEFTDOWN
    for k in range(1, 10):
        u32.SetCursorPos(CX0 + 640, CY0 + 500 - k * 10)
        time.sleep(0.05)
    time.sleep(0.25)
    u32.mouse_event(4, 0, 0, 0, 0); time.sleep(0.6)            # LEFTUP
    shot('07_drag')
    state('drag')

    key(0x1B, 1.5)
    shot('06_closed')
    state('closed')
    print('alive=%s' % alive(), flush=True)
    print('log=%s' % (' '.join('%02X' % b for b in open(LOG, 'rb').read()[-40:])
                      if os.path.exists(LOG) else '(无)'), flush=True)
    if os.path.exists(LOG):
        head = [b for b in open(LOG, 'rb').read()[:24]]
        print('log头=%s' % ' '.join('%02X' % b for b in head), flush=True)
        # E0=tree_entry 入口, E3=按(名,姓)命中家族, E4=未命中->兜底, E5=未命中->放弃
        hit = 'E3(命中)' if 0xE3 in head else ('E4(兜底)' if 0xE4 in head else
                                              ('E5(放弃)' if 0xE5 in head else '?'))
        print('家族查表: %s' % hit, flush=True)
    print('--- GDI_TAB 空槽检查 ---', flush=True)
    raw = rd(GDI_TAB, len(API_NAMES) * 4)
    if raw:
        empty = [API_NAMES[i] for i in range(len(API_NAMES))
                 if struct.unpack_from('<I', raw, i * 4)[0] == 0]
        print('   空槽: %s' % (empty or '无'), flush=True)
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
