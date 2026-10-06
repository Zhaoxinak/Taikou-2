"""tkwatch.py — 只读实时观察器: 附着到**已在运行**的游戏进程, 打印族谱点击命中的详情。

不启动、不结束游戏(见 no-launch 约束)。它只做两件事:
  1. 找到 TAIK2W95* 主窗口 -> 取其 pid -> OpenProcess(PROCESS_VM_READ) 只读附着;
  2. 每 ~0.15s 读一次:
       - SELDETOFF (RSTATE+0xF8): 点中节点时是详情串在 .fdata POOL 里的偏移,
         未选中/刚关树 = 0xFFFFFFFF。据此还原并打印那行 GBK 文案。
       - tk_tree.log 末字节: 崩溃时最后写入的阶段就是崩溃点(A0=命中测试, A1=画详情)。
       - M3b 成长/培养 + M4 元服 + M6 影子档 共 22+9 个埋点, 变化时打印并当场核身份式:
         CMD=ROLL+REJECT / ROLL=OK+FAIL / SAVE=SAVED+WERR / LOAD=RESTORE+REJECT /
         元服: FREEZE == CHILD_GENPUKU == MOUNT+RONIN
       - KID_TAB 有动作的孩子逐行(含 +10 元服归属码: 未/随父/国主/浪人)

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
# --- big.exe 埋点 + 运行池读数: 地址取自 build_big.py 落的 _big_layout.json (换 CAP 不用改本脚本)
try:
    _LY = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                      '_big_layout.json'), encoding='utf-8'))
except Exception:
    _LY = None
if _LY:
    _V = _LY['v']
    BGM_CNT = _V['BGM_CNT']
    APPEAR_CNT, VACANT_CNT = _V['APPEAR_CNT'], _V['VACANT_CNT']
    MONTH_CNT, ARMED_CNT = _V['MONTH_CNT'], _V['ARMED_CNT']
    ENT_POOL, ENT_STRIDE = _LY['pool_va'], _LY['stride']
    SUR_TAB, GIV_TAB = _LY['sur_va'], _LY['giv_va']
    RES_LO, RES_N = _LY['reserve_lo'], _LY['reserve_n']
    ENT_CAP = _LY['cap']
    GROWTH = dict(_LY['growth_ctrs'])          # 4B 埋点表 (名->VA): 成长/培养 + M4 元服两个 + M6 影子存档九个
    KID_TAB, KID_ESZ = _V['KID_TAB'], _LY['kid_esz']
    CMD_RING, CHILD_BM = _V['CMD_RING'], _V['CHILD_BM']
    GENPUKU = _V['CHILD_GENPUKU']
else:
    BGM_CNT = 0x543C40            # BGM-STUB 埋点: play 请求被抑制次数
    APPEAR_CNT = 0x543C48         # 真正登场人次 (0x4A4F40 trampoline 计数)
    VACANT_CNT = 0x543C4C         # 待登场槽被扫到次数 (每月每空槽 +1)
    MONTH_CNT = 0x543C50          # 登场例程执行次数 (约等于推进的月数)
    ARMED_CNT = 0x543C54          # 池尾空槽武装成 0x800B 的次数
    ENT_POOL, ENT_STRIDE, SUR_TAB, GIV_TAB = 0x53C000, 47, 0x541E00, 0x542C00
    RES_LO, RES_N, ENT_CAP = 354, 16, 512
    GROWTH, KID_TAB, KID_ESZ, CMD_RING, CHILD_BM = {}, 0, 0, 0, 0   # 无 layout json: 不盯成长
    GENPUKU = 0x54B6C8
DATE_Y, DATE_M = 0x5205F0, 0x5205F1
PUKU_AGE = _LY.get('genpuku_age', 15) if _LY else 15      # M4 元服线 (虚岁)
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
    last_appear = None

    def slot_status(k):
        d = dw(ENT_POOL + k * ENT_STRIDE + 0x2c)
        return None if d is None else d & 0xFFFF

    def slot_name(k):
        # 极性: SUR_TAB(=原 0x520660) 是**名**表, GIV_TAB(=原 0x521AA8) 是**姓**表
        s = (rd(GIV_TAB + k * 7, 7) or b'').split(b'\0')[0]
        g = (rd(SUR_TAB + k * 7, 7) or b'').split(b'\0')[0]
        return (s + g).decode('gbk', 'replace').strip()

    def kid_rows():
        """KID_TAB 里有动作的孩子逐行列一遍 (12B/槽: +0 亲密 u16 / +2 已投入点 u16 /
        +4 五维增量位图 / +5 自然累加器 / +6 上次活动 / +8 教席 / +9 上次结算月+1, 0=从未 /
        +10 元服归属 0未 1随父 2挂国主 3浪人)。只在埋点有变化时被调用, 所以不必省着读。"""
        if not (GROWTH and KID_TAB and CMD_RING):
            return []
        bm = rd(CHILD_BM, (ENT_CAP + 7) // 8)
        if not bm:
            return []
        out = []
        for s in range(ENT_CAP):
            if not (bm[s >> 3] >> (s & 7)) & 1:
                continue
            r = rd(KID_TAB + s * KID_ESZ, KID_ESZ)
            if not r or len(r) < KID_ESZ:
                continue
            pk = struct.unpack_from('<H', r, 10)[0]
            if r[4] == 0 and struct.unpack_from('<H', r, 2)[0] == 0 and r[9] == 0 and pk == 0:
                continue                       # 完全没动过, 不刷屏
            st = struct.unpack_from('<HH', r, 0)
            out.append('槽%-4d %-8s 亲密%-3d 投入%-3d 增量%s 累加%2d 活动%s 教席%s 上月%s 元服%s'
                       % (s, slot_name(s) or '?', st[0], st[1],
                          ''.join('%d' % ((r[4] >> d) & 1) for d in range(5)),
                          r[5],
                          # +6/+8 开局是 0(=表里的 读书/自学), 只有结算过才有意义
                          '-' if r[9] == 0 else r[6],
                          '-' if r[9] == 0 else r[8],
                          '从未' if r[9] == 0 else r[9] - 1,
                          {0: '未', 1: '随父', 2: '国主', 3: '浪人'}.get(pk, '?%d' % pk)))
        return out

    last_growth = None
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

            # [登场] big.exe 4i: 每月钩进大地图后自动推进, 到年份就有人元服登场。
            # 待登场空槽=还没被填的 0x800B; 已入住=被填上的槽(附姓名, 应能在游戏里找到这人)。
            ap = dw(APPEAR_CNT)
            if ap is not None:
                yb, mb = rd(DATE_Y, 1), rd(DATE_M, 1)
                vc, mh, ar = dw(VACANT_CNT), dw(MONTH_CNT), dw(ARMED_CNT)
                armed, fills = 0, []
                for k in range(RES_LO, RES_LO + RES_N):
                    s = slot_status(k)
                    if s is None:
                        break
                    if s == 0x800B:
                        armed += 1
                    elif s != 0x808F:
                        nm = slot_name(k)
                        fills.append('%d:%s' % (k, nm or '?'))
                date = '%d年%d月' % (1560 + yb[0], mb[0]) if yb and mb else '日期?'
                sig = (date, ap, armed, tuple(fills))
                if sig != last_appear:
                    print('[登场] %s | 例程跑 %s 月次 武装 %s 次 | 待登场空槽 %d/%d | 登场人次 %d | 空槽遭遇 %d'
                          % (date, mh, ar, armed, RES_N, ap, vc))
                    if fills:
                        print('       已入住: ' + '  '.join(fills))
                    last_appear = sig

            # [成长/培养] 埋点表(20 个成长/培养 + 9 个影子存档)。只在数值变化时打印, 并当场核对身份式:
            #   CMD = ROLL + REJECT (每条指令要么被门拒掉, 要么真掷骰)
            #   ROLL = OK + FAIL    (掷了就必有一个结果)
            #   SAVE = SAVED + WERR / LOAD = RESTORE + REJECT (M6 影子档两方向各自的落地式)
            if GROWTH:
                gv = {k: dw(a) for k, a in GROWTH.items()}
                hd, tl = dw(CMD_RING), dw(CMD_RING + 4)
                if None not in gv.values() and hd is not None:
                    sig = tuple(gv[n] for n in GROWTH) + (hd - tl,)
                    if sig != last_growth:
                        yb2, mb2 = rd(DATE_Y, 1), rd(DATE_M, 1)
                        date2 = '%d年%d月' % (1560 + yb2[0], mb2[0]) if yb2 and mb2 else '日期?'
                        bad = []
                        if gv['GROWTH_CMD'] != gv['GROWTH_ROLL'] + gv['GROWTH_REJECT']:
                            bad.append('!! CMD(%d) != ROLL+REJECT(%d)'
                                       % (gv['GROWTH_CMD'], gv['GROWTH_ROLL'] + gv['GROWTH_REJECT']))
                        if gv['GROWTH_ROLL'] != gv['GROWTH_OK'] + gv['GROWTH_FAIL']:
                            bad.append('!! ROLL(%d) != OK+FAIL(%d)'
                                       % (gv['GROWTH_ROLL'], gv['GROWTH_OK'] + gv['GROWTH_FAIL']))
                        print('[成长] %s | 自然: 趟%d 结算%d 重月%d 触顶%d 加点+%d'
                              % (date2, gv['GROWTH_PASS'], gv['GROWTH_SETTLED'], gv['GROWTH_DUPM'],
                                 gv['GROWTH_FULL'], gv['GROWTH_NATURAL']))
                        print('       培养: 指令%d 掷骰%d 成功%d 落空%d 拒收%d | 环 head=%d tail=%d 待发%d%s'
                              % (gv['GROWTH_CMD'], gv['GROWTH_ROLL'], gv['GROWTH_OK'],
                                 gv['GROWTH_FAIL'], gv['GROWTH_REJECT'], hd, tl, hd - tl,
                                 ('  ' + ' '.join(bad)) if bad else ''))
                        # M4 元服三条身份式: FREEZE == CHILD_GENPUKU == MOUNT + RONIN (每人恰计一次)
                        if 'GROWTH_PUKU_MOUNT' in gv:
                            _gp, _pm, _pr = dw(GENPUKU), gv['GROWTH_PUKU_MOUNT'], gv['GROWTH_PUKU_RONIN']
                            _gb = []
                            if _gp is None:
                                _gb.append('!! 读不到 CHILD_GENPUKU@0x%06X' % GENPUKU)
                            else:
                                if _gp != gv['GROWTH_FREEZE']:
                                    _gb.append('!! 元服%d != FREEZE%d (有人被元服两次或支路漏计)'
                                               % (_gp, gv['GROWTH_FREEZE']))
                                if _pm + _pr != _gp:
                                    _gb.append('!! 挂%d+浪%d != 元服%d (有孩子没归属也出了支)'
                                               % (_pm, _pr, _gp))
                            print('       元服: 人次%d 挂上%d 浪人%d 冻结%d (阈值 虚岁>=%d)%s'
                                  % (-1 if _gp is None else _gp, _pm, _pr, gv['GROWTH_FREEZE'],
                                     PUKU_AGE, ('  ' + ' '.join(_gb)) if _gb else ''))
                        if 'SIDECAR_SAVE' in gv:
                            _sc = [gv['SIDECAR_SAVE'], gv['SIDECAR_SAVED'], gv['SIDECAR_WERR'],
                                   gv['SIDECAR_SLOT'], gv['SIDECAR_LOAD'], gv['SIDECAR_RESTORE'],
                                   gv['SIDECAR_MISS'], gv['SIDECAR_REJECT'], gv['SIDECAR_GATE']]
                            _sb = []
                            if _sc[0] != _sc[1] + _sc[2]:
                                _sb.append('!! SAVE(%d) != SAVED+WERR(%d)' % (_sc[0], _sc[1] + _sc[2]))
                            if _sc[4] != _sc[5] + _sc[7]:
                                _sb.append('!! LOAD(%d) != RESTORE+REJECT(%d)' % (_sc[4], _sc[5] + _sc[7]))
                            if _sc[3]:
                                _sb.append('!! SLOT 解析失败 %d 次(钩点上下文变了?)' % _sc[3])
                            print('       影子档: 保存%d 落地%d 写错%d | 载入%d 复原%d 拒收%d 无档%d 门%d 槽错%d%s'
                                  % (_sc[0], _sc[1], _sc[2], _sc[4], _sc[5], _sc[7], _sc[6], _sc[8],
                                     _sc[3], ('  ' + ' '.join(_sb)) if _sb else ''))
                        for ln in kid_rows():
                            print('       ' + ln)
                        last_growth = sig

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
