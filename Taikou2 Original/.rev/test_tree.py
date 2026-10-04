"""test_tree.py — 树形家族树 实机验证

导航序列沿用 verify2.py(已验证能打开武将信息卡并命中「家族族谱」页签)。

诊断地址:
  洞内   G_CLICK=0x535F20 G_HIT=0x535F24 G_IN=0x535F3C G_LOOPCNT=0x535EEC
         G_BTN_CX=0x535E40 G_BTN_CY=0x535E44  CARD_CUR=0x514EE8  G_FAMILY=0x5354C0
  新节   RSTATE=0x136200  (见 tree_blobs.json)
         +0x04 HDC  +0x08 FAMP  +0x0C QUIT  +0x10 STAGE  +0x6C READY  +0x70 GDIOK
  GDI_TAB=0x136000  20 槽
"""
import ctypes, json, os, struct, time, zlib, traceback
from ctypes import wintypes

k32 = ctypes.WinDLL('kernel32', use_last_error=True); u32 = ctypes.WinDLL('user32'); g32 = ctypes.WinDLL('gdi32')
k32.CreateProcessA.restype = wintypes.BOOL
k32.OpenProcess.restype = wintypes.HANDLE
k32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
k32.ReadProcessMemory.restype = wintypes.BOOL
k32.ReadProcessMemory.argtypes = [wintypes.HANDLE, wintypes.LPCVOID, wintypes.LPVOID,
                                  ctypes.c_size_t, ctypes.POINTER(ctypes.c_size_t)]
u32.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
u32.GetWindowThreadProcessId.restype = wintypes.DWORD
u32.EnumWindows.argtypes = [ctypes.c_void_p, wintypes.LPARAM]
u32.GetClientRect.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.RECT)]

GAME = r'F:\Games\Taikou 2\Taikou2 Original'
EXE = os.path.join(GAME, 'TAIK2W95_family.exe')
AVI = os.path.join(GAME, 'OPENNING.AVI'); REV = os.path.join(GAME, '.rev')
M = json.load(open(os.path.join(REV, 'tree_blobs.json')))

G_CLICK, G_HIT, G_IN, G_LOOPCNT = 0x535F20, 0x535F24, 0x535F3C, 0x535EEC
G_BTN_CX, G_BTN_CY, G_FAMILY = 0x535E40, 0x535E44, 0x5354C0
CARD_CUR = 0x514EE8
RSTATE = M['rstate']; GDI_TAB = M['gdi_tab']; N_API = M['n_api']
RS_HDC, RS_FAMP, RS_QUIT, RS_STAGE, RS_READY = RSTATE + 0x04, RSTATE + 0x08, RSTATE + 0x0C, RSTATE + 0x10, RSTATE + 0x6C
GDIOK = RSTATE + 0x70


class SI(ctypes.Structure):
    _fields_ = [('cb', wintypes.DWORD)] + [('_pad%d' % i, ctypes.c_char * 64) for i in range(1)]


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


hp = main = None; alive = {'ok': True}
lf = open(os.path.join(REV, 'tree_diag.log'), 'w', encoding='utf-8')


def log(*a):
    s = ' '.join(str(x) for x in a)
    print(s, flush=True); lf.write(s + '\n'); lf.flush()


try:
    assert os.path.exists(AVI), 'OPENNING.AVI 缺失'
    sb = ctypes.create_string_buffer(68); struct.pack_into('<I', sb, 0, 68)
    pi = PI()
    assert k32.CreateProcessA(EXE.encode(), None, None, None, False, 0, None,
                              GAME.encode(), sb, ctypes.byref(pi)), 'CreateProcess 失败 %d' % ctypes.get_last_error()
    hp, pid = pi.hp, pi.pid
    hk = k32.OpenProcess(0x1F0FFF, False, pid)
    assert hk, 'OpenProcess 失败 %d' % ctypes.get_last_error()

    def rd(va, n):
        b = ctypes.create_string_buffer(n); got = ctypes.c_size_t()
        if not k32.ReadProcessMemory(hk, ctypes.c_void_p(va), b, n, ctypes.byref(got)):
            return None
        return b.raw[:got.value]

    def g(va, n=4):
        d = rd(va, n)
        return struct.unpack('<I', d)[0] if d and len(d) == n else None

    def diag(tag):
        cc = g(CARD_CUR) or 0
        log('  [%-10s] GDIOK=%s STAGE=%s FAMP=0x%X QUIT=%s READY=%s HDC=0x%X | BTN=(%s,%s) IN=%s CLICK=%s'
            % (tag, g(GDIOK), g(RS_STAGE), g(RS_FAMP) or 0, g(RS_QUIT), g(RS_READY), g(RS_HDC) or 0,
               g(G_BTN_CX), g(G_BTN_CY), g(G_IN), g(G_CLICK)))
        tab = [g(GDI_TAB + i * 4) for i in range(N_API)]
        log('       GDI_TAB %d/%d 已解析' % (sum(1 for v in tab if v), N_API))
        return cc

    t0 = time.time(); last = -1; stable = 0; skip_t = 0.0
    while time.time() - t0 < 90:
        for h, w, hh in wins(pid):
            if w >= 800:
                main = h
        d = rd(0x534040, 4); cnt = struct.unpack('<I', d)[0] if d else -1
        stable = stable + 1 if cnt == last else 0; last = cnt
        if cnt >= 71 and stable > 8 and main:
            break
        if time.time() - skip_t > 1.2:
            skip_t = time.time()
            if main:
                u32.SetForegroundWindow(main)
            u32.keybd_event(0x1B, 0, 0, 0); time.sleep(0.05); u32.keybd_event(0x1B, 0, 2, 0)
        time.sleep(0.4)
    log('present=%s main=%s' % (last, main))
    assert main, '主窗口未找到'
    u32.SetForegroundWindow(main); time.sleep(0.4)
    cr = wintypes.RECT(); u32.GetClientRect(main, ctypes.byref(cr))
    CW, CH = cr.right, cr.bottom
    pt = wintypes.POINT(0, 0); u32.ClientToScreen(main, ctypes.byref(pt))
    CX0, CY0 = pt.x, pt.y
    log('client %dx%d @screen (%d,%d)' % (CW, CH, CX0, CY0))
    assert CW >= 800, '客户区尺寸异常 %dx%d' % (CW, CH)

    def click(px, py, wait=0.8):
        u32.SetCursorPos(CX0 + px, CY0 + py); time.sleep(0.35)
        u32.mouse_event(2, 0, 0, 0, 0); time.sleep(0.10); u32.mouse_event(4, 0, 0, 0, 0); time.sleep(wait)

    def key(vk, wait=0.8):
        u32.keybd_event(vk, 0, 0, 0); time.sleep(0.06); u32.keybd_event(vk, 0, 2, 0); time.sleep(wait)

    def shot(tag):
        u32.SetForegroundWindow(main); time.sleep(0.2)
        dcv = u32.GetDC(0); mdc = g32.CreateCompatibleDC(dcv); bmp = g32.CreateCompatibleBitmap(dcv, CW, CH)
        g32.SelectObject(mdc, bmp); g32.BitBlt(mdc, 0, 0, CW, CH, dcv, CX0, CY0, 0x00CC0020)
        bi = struct.pack('<IiiHHIIiiII', 40, CW, -CH, 1, 24, 0, 0, 0, 0, 0, 0)
        buf = ctypes.create_string_buffer(CW * CH * 3)
        g32.GetDIBits(mdc, bmp, 0, CH, buf, ctypes.create_string_buffer(bi, len(bi)), 0)
        raw = b''.join(b'\x00' + buf.raw[y * CW * 3:(y + 1) * CW * 3] for y in range(CH))

        def ch(t, dd):
            c = t + dd
            return struct.pack('>I', len(dd)) + c + struct.pack('>I', zlib.crc32(c))
        png = (b'\x89PNG\r\n\x1a\n' + ch(b'IHDR', struct.pack('>IIBBBBB', CW, CH, 8, 2, 0, 0, 0))
               + ch(b'IDAT', zlib.compress(raw, 6)) + ch(b'IEND', b''))
        p = os.path.join(REV, 'tt_%s.png' % tag); open(p, 'wb').write(png)
        return p

    time.sleep(2.0); diag('title')
    click(545, 310, 2.0)                                   # 标题 -> 新游戏
    click(640, 415, 2.5); click(640, 415, 2.5); click(640, 415, 3.0)
    click(1008, 473, 1.5)                                  # 「进行能力设定吗？」-> 否
    key(0x1B, 1.2); key(0x1B, 1.2)

    # 自适应推进: 轮询 CARD_CUR, 未进信息卡就交替点「否」/ESC
    UI_NO = ((1008, 473), (960, 460), (640, 415), (640, 470))
    ci = 0
    for attempt in range(24):
        u32.SetForegroundWindow(main); time.sleep(0.35)
        cc = g(CARD_CUR) or 0
        if cc:
            log('  信息卡已打开 (第 %d 轮) CARD_CUR=0x%06X' % (attempt, cc))
            break
        px, py = UI_NO[ci % len(UI_NO)]; ci += 1
        if ci % 4 == 0:
            key(0x1B, 0.5)
        click(px, py, 0.9)
    else:
        log('  !! 24 轮仍未打开信息卡')
    diag('card'); shot('00_card')

    # 命中信息卡右上「家族族谱」页签
    TABS = ((891, 264), (860, 268), (847, 258), (900, 258))
    hit = None
    for i, (px, py) in enumerate(TABS):
        u32.SetCursorPos(CX0 + px, CY0 + py); time.sleep(0.5)
        u32.mouse_event(2, 0, 0, 0, 0); time.sleep(0.20); u32.mouse_event(4, 0, 0, 0, 0)
        time.sleep(0.45)
        st = g(RS_STAGE)
        log('  点页签%d @(%d,%d) STAGE=%s GDIOK=%s' % (i, px, py, st, g(GDIOK)))
        for j in range(4):
            time.sleep(0.40); shot('01_tab%d_%d' % (i, j)); diag('tab%d_%d' % (i, j))
        if st is not None and st != 0:
            hit = (px, py); break
        key(0x1B, 0.8)
    log('>>> %s' % ('命中页签 @ %s' % (hit,) if hit else '未检测到 STAGE 变化'))

    key(0x1B, 1.0); shot('03_esc'); diag('esc')
    key(0x1B, 1.0); shot('04_esc2'); diag('esc2')
except Exception:
    log('EXC ' + traceback.format_exc())
finally:
    time.sleep(0.2)
    try:
        if hp:
            k32.TerminateProcess(hp, 0)
    except Exception:
        pass
    lf.close()
    print('cleanup', flush=True)
