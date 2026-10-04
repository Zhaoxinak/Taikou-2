"""tkwatch.py — 只读实时观察器: 附着到**已在运行**的游戏进程, 打印族谱点击命中的详情。

不启动、不结束游戏(见 no-launch 约束)。它只做两件事:
  1. 找到 TAIK2W95* 主窗口 -> 取其 pid -> OpenProcess(PROCESS_VM_READ) 只读附着;
  2. 每 ~0.15s 读一次:
       - SELDETOFF (RSTATE+0xF8): 点中节点时是详情串在 .fdata POOL 里的偏移,
         未选中/刚关树 = 0xFFFFFFFF。据此还原并打印那行 GBK 文案。
       - tk_tree.log 末字节: 崩溃时最后写入的阶段就是崩溃点(A0=命中测试, A1=画详情)。

用法: 先像平常一样进游戏、开族谱, 再在另一个终端 `python tkwatch.py`, 然后手点人物。
"""
import ctypes, json, os, struct, sys, time
from ctypes import wintypes

try:    # 强制行缓冲: 后台终端/重定向里也能实时看到输出(默认块缓冲会憋着不刷)
    sys.stdout.reconfigure(encoding='utf-8', line_buffering=True)
except Exception:
    pass

k32 = ctypes.WinDLL('kernel32', use_last_error=True)
u32 = ctypes.WinDLL('user32')
g32 = ctypes.WinDLL('gdi32')

# QueryFullProcessImageNameW 由 kernel32 导出(不是 psapi)。
k32.QueryFullProcessImageNameW.restype = wintypes.BOOL
k32.QueryFullProcessImageNameW.argtypes = [wintypes.HANDLE, wintypes.DWORD,
                                           wintypes.LPWSTR, ctypes.POINTER(wintypes.DWORD)]

REV = os.path.dirname(os.path.abspath(__file__))
GAME = os.path.dirname(REV)
LOG = os.path.join(REV, 'tk_tree.log')   # MOD 用绝对路径写这里(.rev), 不是项目根
M = json.load(open(os.path.join(REV, 'tree_blobs.json')))
RSTATE = M['rstate']
POOL = M['pool']
SELDET = RSTATE + 0xF8          # 点选节点详情串在 POOL 内的偏移; 0xFFFFFFFF=未选
CARD_CUR = 0x514EE8
BGM_CNT = 0x543C40              # big.exe BGM-STUB 埋点: play 请求被抑制次数(证明背景乐路径命中并拦下)
# 详情记录必须落在 [POOL, DETLTAB) 内; 越过即 .fdata 里读到别的东西(搬家/越界征兆)
POOL_HI = M['sec_va'] + 0x3100  # O_DETAILTAB: 串池区上界
SEC_HI = M['sec_va'] + M['sec_sz']

# 阶段标记 = tree_render.py 里每个 logb(a, n)/stage(a, n) 的常量(实测 2026-10-05 校正)
MEAN = {
    0x00: 'tree_show 入口', 0x01: 'stage1 取DC', 0x02: 'stage2 客户区',
    0x03: 'stage3 尺寸', 0x04: 'stage4 居中', 0x05: 'stage5 建资源',
    0x06: '循环顶(脏检查)', 0x07: 'frame已画', 0x08: 'edges已画',
    0x09: 'nodes已画', 0x0D: 'detail已画', 0x0A: 'pump已跑',
    0x0B: 'stage11 释放资源', 0x0C: 'stage12 退出',
    0x20: 'log_init', 0x30: 'make_res', 0x3F: '画笔/刷子', 0x40: '字体',
    0x60: 'pump 读输入', 0x6F: 'pump 收尾', 0x6E: 'quit 收尾',
    0x70: 'draw_frame', 0x7F: 'draw_frame 收尾',
    0x80: 'draw_edges', 0x8F: 'draw_edges 收尾',
    0x90: 'draw_nodes', 0x9F: 'draw_nodes 收尾',
    0xA0: 'pump: 单击->命中测试', 0xA1: 'draw_detail: 进入(未选则直接跳)',
    0xA2: 'detail: SelectClipRgn 已返回', 0xA3: 'detail: 主行TextOut 已返回',
    0xA4: 'detail: 档案行TextOut 已返回',
    0xE0: 'tree_entry 进入', 0xE3: 'tree_entry: 命中家族',
    0xE4: 'tree_entry: 未命中(兜底)', 0xE5: 'tree_entry: 兜底柴田',
}

PROCESS_VM_READ = 0x0010
PROCESS_QUERY_INFORMATION = 0x0400


def shot(hwnd, tag):
    """抓客户区整屏存 BMP, 让我能看到点击后详情的实际排布(文字挤成一堆长什么样)。"""
    w = wintypes.RECT(); u32.GetClientRect(hwnd, ctypes.byref(w))
    W, H = w.right, w.bottom
    if W < 10 or H < 10:
        return
    hdc = u32.GetDC(hwnd); mem = g32.CreateCompatibleDC(hdc)
    bm = g32.CreateCompatibleBitmap(hdc, W, H)
    g32.SelectObject(mem, bm); g32.BitBlt(mem, 0, 0, W, H, hdc, 0, 0, 0xCC0020)

    class BIH(ctypes.Structure):
        _fields_ = [('biSize', wintypes.DWORD), ('biWidth', wintypes.LONG),
                    ('biHeight', wintypes.LONG), ('biPlanes', wintypes.WORD),
                    ('biBitCount', wintypes.WORD), ('biCompression', wintypes.DWORD),
                    ('biSizeImage', wintypes.DWORD), ('biXPelsPerMeter', wintypes.LONG),
                    ('biYPelsPerMeter', wintypes.LONG), ('biClrUsed', wintypes.DWORD),
                    ('biClrImportant', wintypes.DWORD)]
    bi = BIH(); bi.biSize = ctypes.sizeof(bi)
    bi.biWidth, bi.biHeight, bi.biPlanes, bi.biBitCount = W, -H, 1, 24
    raw = ctypes.create_string_buffer(W * H * 3)
    g32.GetDIBits.argtypes = [wintypes.HDC, wintypes.HBITMAP, wintypes.UINT, wintypes.UINT,
                              ctypes.c_void_p, ctypes.c_void_p, wintypes.UINT]
    g32.GetDIBits(mem, bm, 0, H, raw, ctypes.byref(bi), 0)
    body = b''.join(b'\x00' + raw.raw[y * W * 3:(y + 1) * W * 3] for y in range(H))
    hdr = struct.pack('<2sIHHI', b'BM', 14 + 40 + len(body), 0, 0, 14 + 40)
    dib = struct.pack('<IiiHHIIiiII', 40, W, -H, 1, 24, 0, len(body), 0, 0, 0, 0)
    p = os.path.join(REV, 'tk_det_%s.bmp' % tag)
    open(p, 'wb').write(hdr + dib + body)
    g32.DeleteObject(bm); g32.DeleteObject(mem); u32.ReleaseDC(hwnd, hdc)
    print('  [shot] %s  (%dx%d)' % (p, W, H))


def find_game_pid():
    """返回第一个可见、客户区宽>=800、进程名以 TAIK2W95 开头的窗口 (hwnd, pid)。"""
    hits = []

    @ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)
    def cb(h, lp):
        if not u32.IsWindowVisible(h):
            return True
        pid = wintypes.DWORD()
        u32.GetWindowThreadProcessId(h, ctypes.byref(pid))
        r = wintypes.RECT()
        u32.GetClientRect(h, ctypes.byref(r))
        if r.right >= 800 and pid.value:
            hits.append((h, pid.value))
        return True
    u32.EnumWindows(cb, 0)

    for h, pid in hits:
        hp = k32.OpenProcess(PROCESS_QUERY_INFORMATION, False, pid)
        if not hp:
            continue
        try:
            buf = ctypes.create_unicode_buffer(260)
            size = wintypes.DWORD(260)
            if k32.QueryFullProcessImageNameW(hp, 0, buf, ctypes.byref(size)):
                if os.path.basename(buf.value).upper().startswith('TAIK2W95'):
                    return h, pid
        finally:
            k32.CloseHandle(hp)
    return None, None


def wait_for_game(timeout):
    """轮询等待游戏窗口出现(可超时); 返回 (hwnd, pid) 或 (None, None)。"""
    t0 = time.time(); notice = 0.0
    while True:
        h, pid = find_game_pid()
        if pid:
            return h, pid
        if timeout and time.time() - t0 > timeout:
            return None, None
        if time.time() - notice > 5:
            notice = time.time()
            print('[等待] 未发现 TAIK2W95* 游戏窗口, 请手动启动游戏后自动附着...')
        time.sleep(0.5)


def stream(hwnd, pid):
    """附着到 pid 并实时打印 SELDETOFF 详情 + tk_tree.log 末字节, 直到进程消失。"""
    hp = k32.OpenProcess(PROCESS_VM_READ | PROCESS_QUERY_INFORMATION, False, pid)
    if not hp:
        print('OpenProcess 失败 (err=%d)' % ctypes.get_last_error())
        return False
    print('== 附着 pid=%d hwnd=%s  SELDETOFF@0x%X POOL@0x%X  (只读, 不影响游戏)'
          % (pid, hwnd, SELDET, POOL))

    def rd(va, n):
        b = ctypes.create_string_buffer(n)
        got = ctypes.c_size_t()
        return b.raw[:got.value] if k32.ReadProcessMemory(hp, ctypes.c_void_p(va), b, n,
                                                          ctypes.byref(got)) else None

    def dw(va):
        d = rd(va, 4)
        return struct.unpack('<I', d)[0] if d and len(d) == 4 else None

    def detail_text(off):
        """v11 详情记录 = [u8 len1][gbk 主行][u8 len2][gbk 档案行](len2=0 则无档案行).
        带 .fdata 边界校验: 越出串池区[POOL,POOL_HI) 就标注, 用来坐实'搬家/越界'征兆。"""
        head = rd(POOL + off, 1)
        if not head:
            return None
        l1 = head[0]
        s1 = rd(POOL + off + 1, l1)
        if s1 is None or len(s1) < l1:
            return None
        e2 = POOL + off + 1 + l1
        warn = ''
        if e2 + 1 > POOL_HI:
            warn = '  !!越出串池区(>%X)' % POOL_HI
        line1 = s1.decode('gbk', 'replace')
        h2 = rd(e2, 1)
        if not h2:
            return '%s%s' % (line1, warn)
        l2 = h2[0]
        if l2 == 0:
            return '%s%s' % (line1, warn)
        s2 = rd(e2 + 1, l2)
        if s2 is None or len(s2) < l2:
            return '%s |档案截断%s' % (line1, warn)
        if e2 + 1 + l2 > POOL_HI:
            warn = '  !!档案行越出串池区(>%X)' % POOL_HI
        return '%s  ‖  %s%s' % (line1, s2.decode('gbk', 'replace'), warn)

    last_off = 'init'
    last_tail = b''
    last_bgm = None
    ok = True
    try:
        while True:
            off = dw(SELDET)
            if off is None:
                print('!! 读不到进程内存 -> 游戏可能已退出, 重新等待...')
                ok = False
                break
            key = '未选中' if off == 0xFFFFFFFF else ('0x%04X %s' % (off, detail_text(off)))
            if key != last_off:
                card = dw(CARD_CUR)
                print('[SELDET] %s   (CARD_CUR=0x%06X)' % (key, card or 0))
                last_off = key
                if off != 0xFFFFFFFF:
                    shot(hwnd, '%04X' % off)   # 点中新人物 -> 立刻抓一帧看排版

            bgm = dw(BGM_CNT)
            if bgm is not None and bgm != last_bgm:
                print('  [BGM] 背景乐 play 请求被抑制累计 %d 次 (0x%X)  -> 崩溃源(DirectShow图)已切断'
                      % (bgm, BGM_CNT))
                last_bgm = bgm

            if os.path.exists(LOG):
                d = open(LOG, 'rb').read()
                if d != last_tail:
                    tail = d[-1] if d else None
                    tag = MEAN.get(tail, '?' if tail is not None else '空')
                    print('  [log] %d B  末字节=0x%02X %s' % (len(d), tail or 0, tag))
                    last_tail = d
            time.sleep(0.15)
    finally:
        k32.CloseHandle(hp)
    return ok


def main():
    timeout = 0
    for arg in sys.argv[1:]:
        try:
            timeout = int(arg)
        except ValueError:
            pass
    try:
        while True:
            hwnd, pid = wait_for_game(timeout)
            if not pid:
                print('[超时] 未等到游戏, 退出。')
                return
            if not stream(hwnd, pid):
                if timeout:
                    return
                time.sleep(1.0)   # 游戏重启后再次附着
    except KeyboardInterrupt:
        print('停止观察。')


if __name__ == '__main__':
    main()
