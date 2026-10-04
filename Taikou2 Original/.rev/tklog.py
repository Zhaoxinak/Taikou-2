"""tklog.py — 启动游戏 -> 走导航到武将信息卡 -> 反复点「家族族谱」 -> 实时打印 tk_tree.log

崩溃诊断日志由渲染层自己写盘(tree_render.logb), 进程死了日志还在,
最后一个字节就是崩溃点。本脚本负责把日志实时打出来。

用法: python tklog.py
"""
import ctypes, json, os, struct, time, traceback
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
RS_STAGE, RS_QUIT = RSTATE + 0x10, RSTATE + 0x0C
GDIOK = RSTATE + 0x70

# 阶段号 -> 含义(与 tree_render.py 里的 logb() 参数一一对应)
MEAN = {
    0x00: 'tree_show 入口(已开窗日志)',
    0x01: 'tree_show: 准备解析 API', 0x02: 'resolve 完成, 准备 GetActiveWindow',
    0x03: 'GetActiveWindow 成功, 准备 GetDC', 0x04: 'GetDC 成功, 准备建资源',
    0x05: 'make_res 完成, 准备等左键松开', 0x06: 'wait_rel 完成, 进入模态循环',
    0x07: '循环: 画框', 0x08: '循环: 画连线', 0x09: '循环: 画节点',
    0x0A: '循环: pump', 0x0B: '已回到循环判定', 0x0C: '退出循环, 释放资源',
    0x0D: 'ReleaseDC 完成, 收尾',
    0x20: 'resolve_api 进入', 0x2F: 'resolve_api 完成',
    0x30: 'make_res 进入', 0x3F: 'make_res 完成',
    0x40: 'free_res 进入', 0x4F: 'free_res 完成',
    0x50: 'wait_rel 进入', 0x5F: 'wait_rel 完成',
    0x60: 'pump 进入', 0x6E: 'pump: 判定退出', 0x6F: 'pump 完成',
    0x70: 'draw_frame 进入', 0x7F: 'draw_frame 完成',
    0x80: 'draw_edges 进入', 0x8F: 'draw_edges 完成',
    0x90: 'draw_nodes 进入', 0x9F: 'draw_nodes 完成',
    0xE0: 'tree_entry 进入', 0xE1: 'tree_entry: 无当前武将',
    0xE2: 'tree_entry: 槽位越界', 0xE3: 'tree_entry: 命中家族',
    0xE4: 'tree_entry: 未命中, 兜底柴田', 0xE5: 'tree_entry: 未命中且无兜底',
    0xA0: 'pump: 单击 -> 开始命中测试', 0xA1: 'draw_detail: 绘制选中详情条',
    0x0D: 'tree_show: 画完详情',
}


def explain(data):
    out = []
    for i, v in enumerate(data):
        out.append('%02d:%02X %s' % (i, v, MEAN.get(v, '?')))
    return out


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


def shot(hwnd, tag):
    w = wintypes.RECT(); u32.GetClientRect(hwnd, ctypes.byref(w))
    W, H = w.right, w.bottom
    if W < 10 or H < 10:
        return
    hdc = u32.GetDC(hwnd); mem = g32.CreateCompatibleDC(hdc)
    bm = g32.CreateCompatibleBitmap(hdc, W, H)
    g32.SelectObject(mem, bm); g32.BitBlt(mem, 0, 0, W, H, hdc, 0, 0, 0xCC0020)

    class BITMAPINFOHEADER(ctypes.Structure):
        _fields_ = [('biSize', wintypes.DWORD), ('biWidth', wintypes.LONG),
                    ('biHeight', wintypes.LONG), ('biPlanes', wintypes.WORD),
                    ('biBitCount', wintypes.WORD), ('biCompression', wintypes.DWORD),
                    ('biSizeImage', wintypes.DWORD), ('biXPelsPerMeter', wintypes.LONG),
                    ('biYPelsPerMeter', wintypes.LONG), ('biClrUsed', wintypes.DWORD),
                    ('biClrImportant', wintypes.DWORD)]
    bi = BITMAPINFOHEADER(); bi.biSize = ctypes.sizeof(bi)
    bi.biWidth, bi.biHeight, bi.biPlanes, bi.biBitCount = W, -H, 1, 24
    raw = ctypes.create_string_buffer(W * H * 3)
    g32.GetDIBits.argtypes = [wintypes.HDC, wintypes.HBITMAP, wintypes.UINT, wintypes.UINT,
                              ctypes.c_void_p, ctypes.c_void_p, wintypes.UINT]
    g32.GetDIBits(mem, bm, 0, H, raw, ctypes.byref(bi), 0)
    rows = []
    for y in range(H):
        rows.append(b'\x00' + raw.raw[y * W * 3:(y + 1) * W * 3])
    body = b''.join(rows)
    hdr = struct.pack('<2sIHHI', b'BM', 14 + 40 + len(body), 0, 0, 14 + 40)
    d = struct.pack('<IiiHHIIiiII', 40, W, -H, 1, 24, 0, len(body), 0, 0, 0, 0)
    open(os.path.join(REV, 'tk_%s.bmp' % tag), 'wb').write(hdr + d + body)
    g32.DeleteObject(bm); g32.DeleteObject(mem); u32.ReleaseDC(hwnd, hdc)


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

    # 与 verify2.py 同一套等待: 0x534040 是「画面呈现计数」, >=71 且稳定才说明
    # 开场动画(KOEILOGO/OPENNING.AVI)放完、进入标题画面了。
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
            u32.keybd_event(0x1B, 0, 0, 0); time.sleep(0.05)
            u32.keybd_event(0x1B, 0, 2, 0)
        time.sleep(0.4)
    print('present=%s main=%s' % (last, main))
    assert main, '主窗口未找到'
    u32.SetForegroundWindow(main); time.sleep(0.4)
    wr = wintypes.RECT(); u32.GetWindowRect(main, ctypes.byref(wr))
    cr = wintypes.RECT(); u32.GetClientRect(main, ctypes.byref(cr))
    pt = wintypes.POINT(0, 0); u32.ClientToScreen(main, ctypes.byref(pt))
    CX0, CY0 = pt.x, pt.y
    print('client %dx%d @screen(%d,%d) winrect=(%d,%d)' % (cr.right, cr.bottom, CX0, CY0, wr.left, wr.top))

    def click(px, py, wait=0.8):
        u32.SetForegroundWindow(main)
        u32.SetCursorPos(CX0 + px, CY0 + py); time.sleep(0.30)
        u32.mouse_event(2, 0, 0, 0, 0); time.sleep(0.10)
        u32.mouse_event(4, 0, 0, 0, 0); time.sleep(wait)

    def key(vk, wait=0.8):
        u32.keybd_event(vk, 0, 0, 0); time.sleep(0.06)
        u32.keybd_event(vk, 0, 2, 0); time.sleep(wait)

    last = b''
    def poplog(tag=''):
        global last
        if os.path.exists(LOG):
            d = open(LOG, 'rb').read()
            if d != last:
                print('  --- tk_tree.log %s (%d B) ---' % (tag, len(d)))
                for line in explain(d):
                    print('      ' + line)
                last = d
                return d
        return last

    def alive():
        c = wintypes.DWORD()
        return bool(k32.GetExitCodeProcess(hp, ctypes.byref(c)) and c.value == 259)

    time.sleep(2.0)
    click(545, 310, 2.0)
    click(640, 415, 2.5); click(640, 415, 2.5); click(640, 415, 3.0)
    key(0x1B, 1.2); key(0x1B, 1.2)
    shot(main, '00_map')
    print('CARD_CUR=%s' % g(CARD_CUR))
    poplog('导航后')

    # 走到信息卡
    for attempt in range(20):
        if not alive():
            print('!! 进程在导航阶段就退出了'); break
        if g(CARD_CUR):
            print('信息卡已打开 CARD_CUR=0x%06X (第 %d 轮)' % (g(CARD_CUR) or 0, attempt))
            break
        px, py = ((1008, 473), (960, 460), (640, 415), (640, 470))[attempt % 4]
        click(px, py, 0.9)
        if attempt % 4 == 3:
            key(0x1B, 0.5)
    shot(main, '01_card')
    print('CARD_CUR=%s STAGE=%s GDIOK=%s' % (g(CARD_CUR), g(RS_STAGE), g(GDIOK)))

    # 点「家族族谱」页签
    for i, (px, py) in enumerate(((891, 264), (860, 268), (847, 258), (900, 258), (880, 270))):
        if not alive():
            print('>>> 点页签 %d 后进程已退出' % i); break
        print('== 页签%d @(%d,%d)  STAGE=%s GDIOK=%s' % (i, px, py, g(RS_STAGE), g(GDIOK)))
        click(px, py, 0.4)
        for _ in range(6):
            time.sleep(0.35)
            poplog('页签%d' % i)
            if not alive():
                break
        shot(main, '02_tab%d' % i)
        if not alive():
            print('>>> 崩溃发生在页签 %d @(%d,%d)' % (i, px, py)); break
    poplog('最终')
    print('存活=%s CARD_CUR=%s' % (alive(), g(CARD_CUR)))
except Exception:
    print(traceback.format_exc())
finally:
    try:
        if hp:
            k32.TerminateProcess(hp, 0)
    except Exception:
        pass
    print('done')
