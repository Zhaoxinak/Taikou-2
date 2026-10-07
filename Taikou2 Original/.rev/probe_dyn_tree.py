# -*- coding: utf-8 -*-
"""只读探针: 为什么动态族谱没点亮新生儿?

不启动/不结束游戏, 只 ReadProcessMemory。一次把三件事摆出来:
  A) 正在跑的 exe 到底有没有"点亮桩"(DYN_FN 是否被 build_big 写进去) + 桩的四个埋点读数;
  B) 新生儿侧: 排程表条目 + 实体行 (oid / 父链 +0x1d / 状态字 / 国城 / 姓名);
  C) 开树侧: FAMP 指向的 FAM_DIR 记录 + OIDTAB 静态段 oid => 桩用来匹配的"本人 oid"到底是几号。
结论口径: 孩子要出现在树上, 必须 word[ent+0x1d] == 本人 oid(史实家 OIDTAB[start*2+subject] /
  通用家 DYN_SLOT 那张卡的 oid), **且** word[ent+0x2c] 过桩的三选一在岗门
  ((v&0x8080)==0x8080 在岗 / (v&0x879F)==0x001B 儿童 / ==0x010F 元服后)。
  本文件在 2026-10-07 修掉两处读数 bug(父链错读成 +0x4; start 忘了 /2 编码), 门模拟与桩同步。
"""
import ctypes
import ctypes.wintypes as wt
import hashlib
import json
import os
import struct
import sys

sys.stdout.reconfigure(encoding='utf-8')
u32 = ctypes.windll.user32
k32 = ctypes.windll.kernel32
REV = os.path.dirname(os.path.abspath(__file__))
GAME = os.path.dirname(REV)
LY = json.load(open(os.path.join(REV, '_big_layout.json'), encoding='utf-8'))
TB = json.load(open(os.path.join(REV, 'tree_blobs.json'), encoding='utf-8'))
def _h(d):
    out = {}
    for k, v in d.items():
        try:
            out[k] = int(v, 16) if isinstance(v, str) else v
        except ValueError:
            out[k] = v
    return out


TD = _h(LY['tree_dyn'])
V = _h(LY['v'])
MU = _h(LY['menu'])
POOL, STRIDE, CAP = LY['pool_va'], LY['stride'], LY['cap']
SUR, GIV = LY['sur_va'], LY['giv_va']       # 名表 / 姓表 (变量名沿用旧口径)
VM = 0x0010
QI = 0x0400

k32.QueryFullProcessImageNameW.restype = wt.BOOL
k32.QueryFullProcessImageNameW.argtypes = [wt.HANDLE, wt.DWORD, wt.LPWSTR, ctypes.POINTER(wt.DWORD)]


def windows():
    hits = []

    @ctypes.WINFUNCTYPE(ctypes.c_bool, wt.HWND, wt.LPARAM)
    def cb(h, lp):
        if u32.IsWindowVisible(h):
            pid = wt.DWORD()
            u32.GetWindowThreadProcessId(h, ctypes.byref(pid))
            r = wt.RECT()
            u32.GetClientRect(h, ctypes.byref(r))
            if r.right >= 800 and pid.value:
                hits.append((h, pid.value))
        return True
    u32.EnumWindows(cb, 0)
    return hits


def attach():
    for h, pid in windows():
        hp = k32.OpenProcess(QI, False, pid)
        if not hp:
            continue
        buf = ctypes.create_unicode_buffer(260)
        sz = wt.DWORD(260)
        name = None
        if k32.QueryFullProcessImageNameW(hp, 0, buf, ctypes.byref(sz)):
            name = buf.value
        k32.CloseHandle(hp)
        if name and os.path.basename(name).upper().startswith('TAIK2W95'):
            hp = k32.OpenProcess(VM | QI, False, pid)
            return hp, pid, name
    return None, None, None


def gate_ok(st):
    """桩里的三选一在岗门(tree_dyn.SRC td_scan): 过不了这条, 父链再对也不会点亮。"""
    if st is None:
        return False
    return ((st & 0x8080) == 0x8080) or ((st & 0x879F) in (0x001B, 0x010F))


def gate(st):
    if st is None:
        return '?'
    if (st & 0x8080) == 0x8080:
        return '在岗'
    v = st & 0x879F
    return {0x001B: '儿童', 0x010F: '元服后'}.get(v, '过不了(%04X)' % v)


def main():
    hp, pid, exe = attach()
    if not hp:
        print('未发现 TAIK2W95* 游戏窗口 (请先手动开游戏, 本脚本只读附着)')
        return 1
    print('== 附着 pid=%d  %s' % (pid, exe))
    base = os.path.basename(exe)
    disk = os.path.join(GAME, base)
    if os.path.exists(disk):
        h_run = hashlib.sha256(open(exe, 'rb').read()).hexdigest()[:12]
        h_disk = hashlib.sha256(open(disk, 'rb').read()).hexdigest()[:12]
        st = os.stat(disk)
        print('   盘上同名档 %d B  sha %s ; 进程镜像 sha %s ; %s'
              % (st.st_size, h_disk, h_run, '一致' if h_disk == h_run else '**不一致: 跑的是旧 exe**'))

    def rd(va, n):
        b = ctypes.create_string_buffer(n)
        got = ctypes.c_size_t()
        if k32.ReadProcessMemory(hp, ctypes.c_void_p(va), b, n, ctypes.byref(got)):
            return b.raw[:got.value]
        return None

    def dw(va):
        d = rd(va, 4)
        return struct.unpack('<I', d)[0] if d and len(d) == 4 else None

    def word(va):
        d = rd(va, 2)
        return struct.unpack('<H', d)[0] if d and len(d) == 2 else None

    def gbk(b):
        return (b or b'').split(b'\0')[0].decode('gbk', 'replace')

    print('\n--- A) 点亮桩在不在场 / 埋点读数 ---')
    fn = dw(TD['dyn_fn'])
    print('  DYN_FN 0x%06X -> 0x%06X  %s' % (TD['dyn_fn'], fn or 0,
          '桩已挂上' if fn == TD['code_va'] else '**桩没挂上(旧 exe 或 family.exe)**' if not fn else '指向别处'))
    for nm in ('dyn_lit', 'dyn_call', 'dyn_nosub', 'dyn_slot'):
        print('  %-9s = %s' % (nm.upper(), dw(TD[nm])))
    ctr = ['CHILD_PRELOAD', 'CHILD_REARM', 'CHILD_SCAN', 'CHILD_SKIP', 'CHILD_PLACE',
           'CHILD_GENPUKU', 'MONTH_CNT']
    print('  ' + '  '.join('%s=%s' % (c, dw(V[c])) for c in ctr))
    print('  BIRTH_COUNT=%s  PAGE_ROWS=%s  PAGE_NAV=%s'
          % (dw(MU['cnt_birth']), dw(MU['cnt_rows']), dw(MU['cnt_nav'])))

    print('\n--- B) 池首可变区 (桩每次开树写的内容) ---')
    print('  本人串 @0x%06X: %r' % (TD['gen_name_rec'], gbk(rd(TD['gen_name_rec'], 15))))
    print('  标题串 @0x%06X: %r' % (TD['gen_title_rec'], gbk(rd(TD['gen_title_rec'], 15))))
    for k in range(TD['dyn_slots']):
        a = TD['dyn_pool'] + k * TD['dyn_str_sz']
        print('  子嗣槽%d @0x%06X: %r' % (k, a, gbk(rd(a, 15))))

    print('\n--- C) 当前开的是哪一族 (FAMP) ---')
    famp = dw(TD['famp'])
    if famp and 0x536000 <= famp < 0x536000 + 0x6000:
        rec = rd(famp, 24)
        name_off, surname_off = struct.unpack_from('<II', rec, 0)
        start, count, title = rec[8], rec[9], struct.unpack_from('<H', rec, 10)[0]
        subject, static_n, gen_flag = rec[20], rec[21], rec[22]
        print('  FAMP 0x%06X : start=%d count=%d subject=%d static_n=%d GEN_FLAG=%d'
              % (famp, start, count, subject, static_n, gen_flag))
        print('  姓串@0x%06X=%r 名串@0x%06X=%r 标题@0x%06X=%r'
              % (surname_off, gbk(rd(surname_off, 12)), name_off, gbk(rd(name_off, 12)),
                 TB['pool'] + title, gbk(rd(TB['pool'] + title, 12))))
        if gen_flag:
            ent = word(TD['dyn_slot'])
            e = rd(POOL + ent * STRIDE, 0x20) if ent is not None else None
            print('  通用块: DYN_SLOT=%s 本人 oid=%s' % (ent, struct.unpack('<H', e[2:4])[0] if e else '?'))
            sub_oid = struct.unpack('<H', e[2:4])[0] if e else None
        else:
            _s = word(TD['oidtab'] + (start + subject) * 2)
            sub_oid = None if _s in (None, 0xFFFF) else _s
            print('  史实家: OIDTAB[%d+%d] 本人 oid=%s' % (start, subject, sub_oid))
    else:
        sub_oid = None
        print('  FAMP=%s 不在 .fdata 里 (没开过树/已被清)' % hex(famp) if famp else '  FAMP=0 (还没开过树)')

    print('\n--- D) 排程表 (生孩子往这里追加, child_pass 据此实例化) ---')
    ent_sz = 8
    rows = []
    for k in range(64):
        a = V['CHILD_SCHED'] + k * ent_sz
        r = rd(a, ent_sz)
        if not r or len(r) < ent_sz:
            break
        oid, slot, fslot, guo, cheng = struct.unpack_from('<HHHBB', r, 0)
        if oid == 0xFFFF:
            break
        rows.append((oid, slot, fslot, guo, cheng))
    print('  共 %d 条: oid/slot/fslot/国/城' % len(rows))
    for oid, slot, fslot, guo, cheng in rows:
        print('    oid=%-4d slot=%-5d fslot=%-5d 国=0x%02X 城=%d' % (oid, slot, fslot, guo, cheng))

    print('\n--- E) 儿童位图里的在场实体 (父链 = 树判据) ---')
    bm = rd(V['CHILD_BM'], (CAP + 7) // 8)
    kids = [s for s in range(CAP) if bm and (bm[s >> 3] >> (s & 7)) & 1]
    print('  位图命中 %d 槽' % len(kids))
    for s in kids:
        e = rd(POOL + s * STRIDE, 0x30)
        if not e or len(e) < 0x30:
            print('    slot=%d 读不到' % s)
            continue
        eslot, eoid = struct.unpack_from('<HH', e, 0)
        father = struct.unpack_from('<H', e, 0x1d)[0]      # ★父链在 +0x1d, 不是 +0x4
        st = struct.unpack_from('<H', e, 0x2c)[0]
        gc = struct.unpack_from('<H', e, 0x24)[0]
        nm = gbk(rd(GIV + s * 7, 7)) + gbk(rd(SUR + s * 7, 7))
        lit = '' if sub_oid is None else (' <== 父链命中本人' if father == sub_oid else '')
        print('    slot=%-4d(+0=%d) oid=%-4d 父(+1d)=%-5d 状态=0x%04X 在岗门=%s 国=0x%02X 城=%d %s%s'
              % (s, eslot, eoid, father, st, gate(st), gc >> 8, gc & 0xFF, nm, lit))
    if sub_oid is not None:
        acc = [s for s in kids
               if word(POOL + s * STRIDE + 0x1d) == sub_oid and gate_ok(word(POOL + s * STRIDE + 0x2c))]
        print('  本树"本人 oid"=%s => 父链命中且过桩的在岗门的 %d 个: %s'
              % (sub_oid, len(acc), acc))

    print('\n--- F) 两张卡指针 (tree_entry 用 0x514EE8; 0x516624 曾判定=主角) ---')
    for g in (0x514EE8, 0x516624):
        p = dw(g)
        if p and POOL <= p < POOL + CAP * STRIDE:
            s = (p - POOL) // STRIDE
            e = rd(POOL + s * STRIDE, 4)
            print('  [0x%06X]=0x%06X -> slot=%d oid=%s 名=%r'
                  % (g, p, s, struct.unpack('<H', e[2:4])[0] if e else '?',
                     gbk(rd(GIV + s * 7, 7)) + gbk(rd(SUR + s * 7, 7))))
        else:
            print('  [0x%06X]=%s (不在池内)' % (g, hex(p) if p else 0))
    print('\n--- G) 影子存档 (孩子的持久化: 没它读档就全丢) ---')
    import time
    SC = _h(LY['sc'])
    exp = SC['file_sz']
    tot = 0
    for k in range(SC['slot_max']):
        p = os.path.join(GAME, 'TKMODSAVE_%d.DAT' % k)
        if not os.path.exists(p):
            continue
        st = os.stat(p)
        tot += 1
        d = open(p, 'rb').read(0x30)
        ok = d[:4] == b'TKSD' and d[0x14:0x18] == b'KSD1'
        flag = '完整' if st.st_size == exp else (
            '**只有头 48B => 六段载荷没落地(半截写/WERR), 读档必 REJECT, 孩子会丢**'
            if st.st_size == SC['hdr_sz'] else '大小 %d != 预期 %d' % (st.st_size, exp))
        print('  %s  %d B  mtime=%s  %s  %s'
              % (os.path.basename(p), st.st_size,
                 time.strftime('%m-%d %H:%M', time.localtime(st.st_mtime)),
                 '头 magic/commit 齐' if ok else '**头都不对**', flag))
    if not tot:
        print('  没有 TKMODSAVE_*.DAT —— 这局还没在游里按过保存')
    print('  预期整档 %d B = 头 %d + %s'
          % (exp, SC['hdr_sz'], ' + '.join('%s%d' % (n, sz)
                                           for n, (_, sz) in zip(SC['block_names'], SC['blocks']))))
    print('  埋点 SIDECAR: ' + '  '.join(
        '%s=%s' % (c, dw(SC['ctrs'][c])) for c in ('SIDECAR_SAVE', 'SIDECAR_SAVED', 'SIDECAR_WERR',
                                                   'SIDECAR_LOAD', 'SIDECAR_RESTORE',
                                                   'SIDECAR_MISS', 'SIDECAR_REJECT')))
    k32.CloseHandle(hp)
    return 0


if __name__ == '__main__':
    sys.exit(main())
