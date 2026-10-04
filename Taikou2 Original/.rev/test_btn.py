"""test_btn.py — 实机验证 ft4 的「家族族谱按钮」:
  启动 -> 跳过 AVI -> 新游戏 -> 选主角 -> 大地图 -> 开武将信息卡 -> 截图 -> 点按钮 -> 截图
每步都截图 + 读洞内全局(按钮客户区矩形), 纯自动化, 结束杀进程并还原 AVI。
"""
import ctypes, os, struct, time, zlib, shutil, traceback, sys
from ctypes import wintypes
k32 = ctypes.WinDLL('kernel32', use_last_error=True); u32 = ctypes.WinDLL('user32'); g32 = ctypes.WinDLL('gdi32')
# 必须设定, 否则 64 位句柄被截断成 int -> OpenProcess 看似成功实际无效
k32.OpenProcess.restype = wintypes.HANDLE
k32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
k32.ReadProcessMemory.restype = wintypes.BOOL
k32.ReadProcessMemory.argtypes = [wintypes.HANDLE, wintypes.LPCVOID, wintypes.LPVOID,
                                  ctypes.c_size_t, ctypes.POINTER(ctypes.c_size_t)]
u32.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
u32.GetWindowThreadProcessId.restype = wintypes.DWORD
u32.EnumWindows.argtypes = [ctypes.c_void_p, wintypes.LPARAM]
u32.GetClientRect.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.RECT)]
u32.GetWindowRect.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.RECT)]
GAME = r'F:/Games/Taikou 2\Taikou2 Original'
EXE = os.path.join(GAME, 'TAIK2W95_family.exe')
AVI = os.path.join(GAME, 'OPENNING.AVI'); REV = os.path.join(GAME, '.rev')
moved = []
BTN_CX, BTN_CY, BTN_PREV = 0x535E40, 0x535E44, 0x535E48
BTN_W, BTN_H = 72, 18

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

hp = hk = main = None
try:
    if (not os.path.exists(AVI)) and os.path.exists(AVI + '.tstb'):   # 上次被强杀没还原
        shutil.move(AVI + '.tstb', AVI); print('pre-restore OPENNING.AVI', flush=True)
    if os.path.exists(AVI): shutil.move(AVI, AVI + '.tstb'); moved.append(AVI)
    si = SI2(); si.cb = ctypes.sizeof(si); pi = PI()
    k32.CreateProcessA(EXE.encode(), None, None, None, False, 0, None, GAME.encode(), ctypes.byref(si), ctypes.byref(pi))
    hp, pid = pi.hp, pi.pid; hk = k32.OpenProcess(0x1F0FFF, False, pid)
    def rd(va, n):
        b = ctypes.create_string_buffer(n); got = ctypes.c_size_t()
        if not k32.ReadProcessMemory(hk, ctypes.c_void_p(va), b, n, ctypes.byref(got)): return None
        return b.raw[:got.value]
    t0 = time.time(); last = -1; stable = 0
    while time.time() - t0 < 45:
        for h, w, hh in wins(pid):
            if w >= 800: main = h
        d = rd(0x534040, 4); cnt = struct.unpack('<I', d)[0] if d else -1
        stable = stable + 1 if cnt == last else 0; last = cnt
        if cnt >= 71 and stable > 8 and main: break
        time.sleep(0.4)
    print('present=%s main=%s' % (last, main), flush=True)
    # 游戏已过开场 AVI —— 立刻还原文件, 避免脚本被中断时把用户的游戏目录留成缺文件状态
    for f in moved:
        if os.path.exists(f + '.tstb'): shutil.move(f + '.tstb', f)
    moved = []
    print('OPENNING.AVI restored', flush=True)
    u32.SetForegroundWindow(main); time.sleep(0.4)
    wr = wintypes.RECT(); u32.GetWindowRect(main, ctypes.byref(wr))
    r = wintypes.RECT(); u32.GetClientRect(main, ctypes.byref(r)); nct = (wr.bottom - wr.top) - r.bottom

    def click(px, py, wait=0.8):
        u32.SetCursorPos(wr.left + px, wr.top + nct + py); time.sleep(0.35)
        u32.mouse_event(2, 0, 0, 0, 0); time.sleep(0.10); u32.mouse_event(4, 0, 0, 0, 0); time.sleep(wait)

    def move(px, py):
        u32.SetCursorPos(wr.left + px, wr.top + nct + py); time.sleep(0.2)

    def key(vk, wait=0.8):
        u32.keybd_event(vk, 0, 0, 0); time.sleep(0.06); u32.keybd_event(vk, 0, 2, 0); time.sleep(wait)

    def g(va, n=4):
        d = rd(va, n); return struct.unpack('<I', d)[0] if d else None

    def shot(tag):
        u32.SetForegroundWindow(main); time.sleep(0.25)
        rr = wintypes.RECT(); u32.GetClientRect(main, ctypes.byref(rr)); w, h = rr.right, rr.bottom
        ww = wintypes.RECT(); u32.GetWindowRect(main, ctypes.byref(ww))
        dcv = u32.GetDC(0); mdc = g32.CreateCompatibleDC(dcv); bmp = g32.CreateCompatibleBitmap(dcv, w, h)
        g32.SelectObject(mdc, bmp); g32.BitBlt(mdc, 0, 0, w, h, dcv, ww.left, ww.top, 0x00CC0020)
        bi = struct.pack('<IiiHHIIiiII', 40, w, -h, 1, 24, 0, 0, 0, 0, 0, 0); buf = ctypes.create_string_buffer(w * h * 3)
        g32.GetDIBits(mdc, bmp, 0, h, buf, ctypes.create_string_buffer(bi, len(bi)), 0)
        raw = b''.join(b'\x00' + buf.raw[y * w * 3:(y + 1) * w * 3] for y in range(h))
        def ch(t, dd): c = t + dd; return struct.pack('>I', len(dd)) + c + struct.pack('>I', zlib.crc32(c))
        png = b'\x89PNG\r\n\x1a\n' + ch(b'IHDR', struct.pack('>IIBBBBB', w, h, 8, 2, 0, 0, 0)) + ch(b'IDAT', zlib.compress(raw, 6)) + ch(b'IEND', b'')
        p = os.path.join(REV, 'btn_%s.png' % tag); open(p, 'wb').write(png)
        print('  shot %-11s %6dB btn=(%s,%s) RECT=(%s,%s) %sx%s OX=%s OY=%s OX0=%s OY0=%s W=%s | CLICK=%s HIT=%s | HOOK=%s IN=%s'
              % (tag, len(png), g(BTN_CX), g(BTN_CY), g(0x535F10), g(0x535F14), g(0x535F28), g(0x535F2C),
                 g(0x535E70), g(0x535E74), g(0x535E68), g(0x535E6C), g(0x535F38),
                 g(0x535F20), g(0x535F24), g(0x535E50), g(0x535F3C)), flush=True)

    def scan_in(x0, x1, y0, y1, stepx=24, stepy=12):
        """不点击, 只移动鼠标读 G_IN —— 测出命中框在客户区上的真实范围"""
        print('  命中区扫描 (client x %d..%d / y %d..%d, 步 %d/%d)' % (x0, x1, y0, y1, stepx, stepy), flush=True)
        hdr = '     y\\x ' + ''.join('%4d' % x for x in range(x0, x1 + 1, stepx)); print(hdr, flush=True)
        hits = []
        for y in range(y0, y1 + 1, stepy):
            row = '     %4d ' % y
            for x in range(x0, x1 + 1, stepx):
                move(x, y); time.sleep(0.22)
                v = g(0x535F3C)
                row += '   %s' % ('#' if v else '.')
                if v: hits.append((x, y))
            print(row, flush=True)
        if hits:
            xs = [h[0] for h in hits]; ys = [h[1] for h in hits]
            print('  >>> 命中区 client x %d..%d  y %d..%d   -> 逻辑 x %.1f..%.1f  y %.1f..%.1f'
                  % (min(xs), max(xs), min(ys), max(ys), min(xs) / 2, max(xs) / 2, min(ys) / 2, max(ys) / 2), flush=True)
        else:
            print('  >>> 扫描范围内没有任何命中 !', flush=True)
        return hits

    time.sleep(2.0); shot('00_title')
    click(545, 310, 2.0); shot('01_newgame')
    click(640, 415, 2.5); click(640, 415, 2.5); click(640, 415, 3.0); shot('02_map')
    # 关掉可能已经弹出的族谱列表模态(ESC)
    key(0x1B, 1.2); key(0x1B, 1.2); shot('03_esc')

    cx, cy = g(BTN_CX), g(BTN_CY)
    if cx and cy:
        sx, sy = cx * 2 + BTN_W, cy * 2 + BTN_H        # 逻辑->客户区 ×2; 取按钮中心
        print('  按钮 逻辑(%d,%d) %dx%d  -> 点击客户区(%d,%d)' % (cx, cy, BTN_W, BTN_H, sx, sy), flush=True)
        move(sx, sy); time.sleep(0.4); shot('04_hover')
        # 先扫描命中区(纯移动, 不点击) —— 用于把按钮绘制位置与命中框对齐
        scan_in(700, 1020, 230, 350, 24, 12)
        shot('04b_scan')
        click(sx, sy, 2.5); shot('05_click')
        key(0x1B, 1.2); key(0x1B, 1.2); shot('06_after')
    else:
        print('  !! 按钮矩形未写入(0) —— ft_btn_draw 未执行', flush=True)
except Exception:
    print('EXC', traceback.format_exc(), flush=True)
finally:
    for h in (hp, hk):
        try:
            if h: k32.TerminateProcess(h, 0)
        except Exception: pass
    for f in moved:
        if os.path.exists(f + '.tstb'): shutil.move(f + '.tstb', f)
    print('cleanup', flush=True)
