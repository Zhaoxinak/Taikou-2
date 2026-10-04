"""dump_master.py — dump 常驻的 BSDATA 母表(700 x 59) + 定位指向它的静态指针
不修 exe/数据, 只读内存。产物: master_dump.json / master_ptr.json
"""
import ctypes, json, os, struct, sys, time, traceback
from ctypes import wintypes

k32 = ctypes.WinDLL('kernel32', use_last_error=True)
u32 = ctypes.WinDLL('user32')
k32.OpenProcess.restype = wintypes.HANDLE
k32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
k32.ReadProcessMemory.restype = wintypes.BOOL
k32.ReadProcessMemory.argtypes = [wintypes.HANDLE, wintypes.LPCVOID, wintypes.LPVOID,
                                  ctypes.c_size_t, ctypes.POINTER(ctypes.c_size_t)]
k32.VirtualQueryEx.restype = ctypes.c_size_t
k32.VirtualQueryEx.argtypes = [wintypes.HANDLE, wintypes.LPCVOID, ctypes.c_void_p, ctypes.c_size_t]
u32.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
u32.EnumWindows.argtypes = [ctypes.c_void_p, wintypes.LPARAM]

GAME = r'F:/Games/Taikou 2\Taikou2 Original'
EXE = os.path.join(GAME, os.environ.get('EXE', 'TAIK2W95_family.exe'))
REV = os.path.join(GAME, '.rev')
COUNT, RSIZE = 700, 59
NAME7 = [('柴田', '胜家'), ('佐久间', '信盛'), ('毛利', '元就')]


class SI2(ctypes.Structure):
    _fields_ = [('cb', wintypes.DWORD), ('a', wintypes.LPVOID), ('b', wintypes.LPVOID), ('c', wintypes.LPVOID),
                ('x', wintypes.DWORD), ('y', wintypes.DWORD), ('xs', wintypes.DWORD), ('ys', wintypes.DWORD),
                ('x1', wintypes.DWORD), ('y1', wintypes.DWORD), ('fa', wintypes.DWORD), ('fl', wintypes.DWORD),
                ('sw', wintypes.WORD), ('r2', wintypes.WORD), ('r3', wintypes.LPVOID), ('h1', wintypes.HANDLE),
                ('h2', wintypes.HANDLE), ('h3', wintypes.HANDLE)]


class PI(ctypes.Structure):
    _fields_ = [('hp', wintypes.HANDLE), ('ht', wintypes.HANDLE), ('pid', wintypes.DWORD), ('tid', wintypes.DWORD)]


class MBI(ctypes.Structure):
    _fields_ = [('BaseAddress', ctypes.c_void_p), ('AllocationBase', ctypes.c_void_p),
                ('AllocationProtect', wintypes.DWORD), ('__align', wintypes.DWORD),
                ('RegionSize', ctypes.c_size_t), ('State', wintypes.DWORD),
                ('Protect', wintypes.DWORD), ('Type', wintypes.DWORD)]


def wins(pid):
    out = []

    @ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)
    def cb(h, lp):
        p = wintypes.DWORD(); u32.GetWindowThreadProcessId(h, ctypes.byref(p))
        if p.value == pid and u32.IsWindowVisible(h):
            r = wintypes.RECT(); u32.GetClientRect(h, ctypes.byref(r)); out.append((h, r.right, r.bottom))
        return True
    u32.EnumWindows(cb, 0); return out


def regions(hk, lo=0x400000, hi=0x80000000):
    addr = lo; mbi = MBI()
    while addr < hi:
        if not k32.VirtualQueryEx(hk, ctypes.c_void_p(addr), ctypes.byref(mbi), ctypes.sizeof(mbi)):
            addr += 0x1000; continue
        base = mbi.BaseAddress or 0; size = mbi.RegionSize or 0
        if mbi.State == 0x1000 and not (mbi.Protect & 0x100):
            yield base, size, mbi.Protect, mbi.Type
        addr = base + size if size else addr + 0x1000


def run_once(tag):
    si = SI2(); si.cb = ctypes.sizeof(si); pi = PI()
    k32.CreateProcessA(EXE.encode(), None, None, None, False, 0, None, GAME.encode(),
                       ctypes.byref(si), ctypes.byref(pi))
    hp, pid = pi.hp, pi.pid
    hk = k32.OpenProcess(0x1F0FFF, False, pid)
    try:
        main = None; t0 = time.time()
        while time.time() - t0 < 30:
            for h, w, hh in wins(pid):
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

        # 恢复开场动画后必须先走到标题画面, 否则 BSDATA 尚未加载
        t1 = time.time(); skip_t = 0.0
        while time.time() - t1 < 100:
            if time.time() - skip_t > 1.0:
                skip_t = time.time()
                u32.SetForegroundWindow(main)
                u32.keybd_event(0x1B, 0, 0, 0); time.sleep(0.05); u32.keybd_event(0x1B, 0, 2, 0)
            d = rd(0x534040, 4)
            if d and struct.unpack('<I', d)[0] >= 71:
                break
            time.sleep(0.4)
        time.sleep(3.0)
        print('[%s] 已到标题 (%.1fs)' % (tag, time.time() - t1), flush=True)
        # 进入游戏(大地图) —— 此时 BSDATA 必定已装载
        rc = wintypes.RECT(); u32.GetClientRect(main, ctypes.byref(rc))
        pt = wintypes.POINT(0, 0); u32.ClientToScreen(main, ctypes.byref(pt))
        CX0, CY0 = pt.x, pt.y
        u32.SetForegroundWindow(main); time.sleep(0.5)

        def _click(px, py, w=2.0):
            u32.SetCursorPos(CX0 + px, CY0 + py); time.sleep(0.35)
            u32.mouse_event(2, 0, 0, 0, 0); time.sleep(0.10); u32.mouse_event(4, 0, 0, 0, 0); time.sleep(w)
        _click(545, 310, 2.0)
        _click(640, 415, 2.5); _click(640, 415, 2.5); _click(640, 415, 3.0)
        u32.keybd_event(0x1B, 0, 0, 0); time.sleep(0.06); u32.keybd_event(0x1B, 0, 2, 0); time.sleep(1.2)
        u32.keybd_event(0x1B, 0, 0, 0); time.sleep(0.06); u32.keybd_event(0x1B, 0, 2, 0); time.sleep(3.0)
        print('[%s] 已进入大地图' % tag, flush=True)

        # ---- 找母表基址: 搜 "柴田" 且验证记录结构 ----
        cand = []
        needle = '柴田'.encode('gbk')
        CH = 1 << 20
        for base, size, prot, typ in regions(hk):
            off = 0
            while off < size:
                n = min(CH, size - off)
                data = rd(base + off, n)
                if data:
                    p = 0
                    while True:
                        i = data.find(needle, p)
                        if i < 0:
                            break
                        p = i + 1
                        # 实测: 母表 +0x00=名(7B), +0x07=姓(7B)。"柴田" 落在 +0x07 -> 记录起点 = 地址-7
                        rec = base + off + i - 7
                        nm = rd(rec + 0x00, 7)       # 名字段
                        if not nm:
                            continue
                        s = nm.split(b'\x00')[0]
                        if not (2 <= len(s) <= 8):
                            continue
                        try:
                            ok = s.decode('gbk').isprintable()
                        except Exception:
                            ok = False
                        if ok:
                            cand.append((rec, base, i))
                off += n
        print('[%s] 母表候选 %d 个' % (tag, len(cand)), flush=True)
        for rec, base, i in cand[:6]:
            d = rd(rec, 59)
            print('     候选 @%08X 名=%s 姓=%s father=%s' % (
                rec, d[0:7].split(b'\x00')[0].decode('gbk', 'replace'),
                d[7:14].split(b'\x00')[0].decode('gbk', 'replace'),
                struct.unpack_from('<H', d, 0x29)[0]) if d else '     (读失败)', flush=True)
        # 用 id1=柴田胜家, id36=柴田胜丰 双重校验定位真正的基址
        mbase = None
        for rec, base, i in cand:
            n1 = rd(rec + RSIZE + 0x00, 7); s1 = rd(rec + RSIZE + 0x07, 7)
            g36 = rd(rec + 36 * RSIZE + 0x07, 7)
            n36 = rd(rec + 36 * RSIZE + 0x00, 7)
            f36 = rd(rec + 36 * RSIZE + 0x29, 2)
            if not (n1 and n36 and f36 and s1 and g36):
                continue
            if (n1.split(b'\x00')[0] == '胜家'.encode('gbk')
                    and s1.split(b'\x00')[0] == '柴田'.encode('gbk')
                    and n36.split(b'\x00')[0] == '胜丰'.encode('gbk')
                    and g36.split(b'\x00')[0] == '柴田'.encode('gbk')
                    and struct.unpack('<H', f36)[0] == 1):
                mbase = rec; break
        print('[%s] 母表基址 = 0x%08X' % (tag, mbase or 0), flush=True)
        if not mbase:
            return None
        # ---- dump 母表 ----
        blob = rd(mbase, COUNT * RSIZE)
        recs = []
        for k in range(COUNT):
            r = blob[k * RSIZE:(k + 1) * RSIZE]
            def s7(o):
                return r[o:o + 7].split(b'\x00')[0].decode('gbk', 'replace')
            recs.append({
                'idx': k, 'given': s7(0x00), 'surname': s7(0x07),
                'bushou_id': struct.unpack_from('<H', r, 0x10)[0],
                'birth_year': 1490 + r[0x27], 'father': struct.unpack_from('<H', r, 0x29)[0],
                'province': r[0x30], 'city': r[0x31],
                'merit': struct.unpack_from('<H', r, 0x32)[0],
                'loyalty': r[0x35], 'lord': struct.unpack_from('<H', r, 0x36)[0],
                'status': struct.unpack_from('<H', r, 0x38)[0],
                'raw': r.hex(),
            })
        json.dump(recs, open(os.path.join(REV, 'master_dump_%s.json' % tag), 'w', encoding='utf-8'),
                  ensure_ascii=False, indent=1)
        print('[%s] dumped %d 条' % (tag, len(recs)), flush=True)
        # ---- 读资源管理全局区 0x526b80..0x526bc0 (Read 的常驻分支用 dword[0x526b95]) ----
        print('[%s] 资源全局区 dword:' % tag, flush=True)
        for a in range(0x526b80, 0x526bc4, 4):
            d = rd(a, 4)
            v = struct.unpack('<I', d)[0] if d else 0
            mark = ''
            if v and abs(v - (mbase or 0)) < 0x20000:
                mark = '   <-- 疑似指向母表 (delta %+d)' % (v - (mbase or 0))
            print('     %08X = %08X%s' % (a, v, mark), flush=True)
        # ---- 搜指针: 整个进程内存里 dword == mbase 的位置 (限定静态区) ----
        ptrs = []
        targets = {}
        for d in range(-0x40, 0x80, 2):
            targets[mbase + d] = d
        for base, size, prot, typ in regions(hk, 0x400000, 0x10000000):
            data = rd(base, size)
            if not data:
                continue
            for off in range(0, len(data) - 4, 2):
                v = struct.unpack_from('<I', data, off)[0]
                if v in targets and v:
                    ptrs.append({'at': base + off, 'value': v, 'delta': targets[v], 'type': typ})
        json.dump({'master_base': mbase, 'ptrs': ptrs},
                  open(os.path.join(REV, 'master_ptr_%s.json' % tag), 'w', encoding='utf-8'),
                  ensure_ascii=False, indent=1)
        print('[%s] 指向母表的静态指针 %d 个:' % (tag, len(ptrs)), flush=True)
        for p in ptrs[:15]:
            print('     @%08X -> %08X (delta %+d)' % (p['at'], p['value'], p['delta']), flush=True)
        # ---- 运行时姓名表 ----
        nm = rd(0x520660, 1000 * 7); gn = rd(0x521aa8, 1000 * 7)
        out = []
        for k in range(60):
            a = nm[k * 7:k * 7 + 7].split(b'\x00')[0].decode('gbk', 'replace')
            b = gn[k * 7:k * 7 + 7].split(b'\x00')[0].decode('gbk', 'replace')
            out.append('%3d 名=%-6s 姓=%-6s | 母表[%d] %s%s' % (k, a, b, k, recs[k]['surname'], recs[k]['given']))
        print('[%s] 运行时姓名表 vs 母表(前60):' % tag, flush=True)
        for l in out[:40]:
            print('   ' + l, flush=True)
        return mbase
    finally:
        try:
            k32.TerminateProcess(hp, 0)
        except Exception:
            pass


try:
    b1 = run_once('r1')
    print('母表基址 = 0x%08X' % (b1 or 0), flush=True)
except Exception:
    print('EXC', traceback.format_exc(), flush=True)
print('done', flush=True)
