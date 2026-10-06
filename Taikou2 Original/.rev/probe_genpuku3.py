# -*- coding: utf-8 -*-
"""probe_genpuku3.py —— 元服派发器的入口到底在哪 + [+0x2d]&7 的实测语义

probe_genpuku2 的发现 (需要第二条证据才能进配方):
  * `0x4A4FC0(ent)` 不是"初始化", 而是**归属挂载派发器**:
      `[ent+0x2d]&7 == 0` -> 只写 +0x12=0xff / +0x13=城-0x38, 然后 0x4A5350
      `[ent+0x2d]&7 != 0` -> 依次试 0x4A5010(随主君) / 0x4A5220(随父, 读 [+0x1d] 父oid)
                             / 0x4A5290(随本城城主), 谁成功就停, 最后 0x4A5350
    真正的挂载原语是 `0x4A5100(主人, 本人)`: 本人国/城 := 主人国/城, 并把本人
    slot 记进 `0x51eb88 + 城*31` 的城列表 (0x4A0540), 再 0x49A730(0)/+0x16=0/+0x12=0xff/+0x13=城-0x38。
  * 全镜像扫 E8/E9/EB/立即数 都没找到 `0x4A4FC0` 的调用者 => **它可能真是死代码**,
    也可能调用者在 0x401000..0x4FA000 之外。本脚本 A 段把扫描面铺满整个 exe 来定论。

本脚本要定四件事:
  A) 0x4A4FC0 / 0x4A5100 / 0x4A5010 / 0x4A5220 / 0x4A5290 / 0x4A5350 的全镜像调用点 (任意段、任意跳法)
  B) 原生登场例程 0x4A4D10 与月度例程 0x4A5370 里到底调了谁 (元服在原生里走哪条路)
  C) byte[ent+0x2d] = BSDATA rec[0x39] 的实测分布: 14 个孩子 + 在场成年人对照
     —— 判定"门是否天然开着", 以及 [+0x2d]&7 与 主君/身分码 的相关性
  D) 0x4A0540(城列表插入) 的容量与"满了怎么办"
"""
import json, struct, sys, pathlib
import capstone

try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

ROOT = pathlib.Path(__file__).resolve().parent.parent
REV = ROOT / '.rev'
OUT = open(REV / '_probe_genpuku3.txt', 'w', encoding='utf-8')


def w(*a):
    print(*a, file=OUT)
    print(*a)


LY = json.load(open(REV / '_big_layout.json', encoding='utf-8'))
V = LY['v']
d = open(ROOT / 'TAIK2W95_big.exe', 'rb').read()
pe = struct.unpack_from('<I', d, 0x3C)[0]
opt = struct.unpack_from('<H', d, pe + 20)[0]
SECS = []
for i in range(struct.unpack_from('<H', d, pe + 6)[0]):
    o = pe + 24 + opt + i * 40
    nm = d[o:o + 8].rstrip(b'\0').decode()
    vsz = struct.unpack_from('<I', d, o + 8)[0]
    va, rawsz, raw = struct.unpack_from('<III', d, o + 12)
    SECS.append((nm, 0x400000 + va, vsz, rawsz, raw))
    w('段 %-8s va=%08X vsz=%06X rawsz=%06X raw=%06X' % (nm, 0x400000 + va, vsz, rawsz, raw))


def bytes_at(va, n):
    for nm, sva, vsz, rawsz, raw in SECS:
        if sva <= va < sva + max(vsz, rawsz):
            off = raw + (va - sva)
            return d[off:off + n]
    raise KeyError(va)


md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)
CODE_LO, CODE_HI = 0x401000, 0x520000
TGTS = [0x4A4FC0, 0x4A5010, 0x4A5100, 0x4A5220, 0x4A5290, 0x4A5350, 0x4A5420, 0x4A5500,
        0x4A0540, 0x4A4D10, 0x4A5370, 0x49F5D0, 0x49F5E0, 0x4BA410]
REACH = {t: [] for t in TGTS}
w('\n=== A) 全镜像 (所有段, 任意 E8/E9/EB/立即数) 到目标簇的引用 ===')
for nm, sva, vsz, rawsz, raw in SECS:
    size = min(vsz, rawsz)
    body = d[raw:raw + size]
    for off in range(len(body) - 5):
        va = sva + off
        b = body[off]
        if b in (0xE8, 0xE9):
            t = va + 5 + struct.unpack_from('<i', body, off + 1)[0]
            kind = 'call' if b == 0xE8 else 'jmp'
            if t in REACH and CODE_LO <= va:
                REACH[t].append('%s %08X %s' % (nm, va, kind))
        elif b == 0xEB:
            t = va + 2 + struct.unpack_from('<b', body, off + 1)[0]
            if t in REACH:
                REACH[t].append('%s %08X jmp8' % (nm, va))
        v = struct.unpack_from('<I', body, off)[0]
        if v in REACH:
            REACH[v].append('%s %08X [imm/表项]' % (nm, va))
for t in TGTS:
    r = REACH[t]
    w('\n  -> %08X : %d 处' % (t, len(r)))
    for x in r[:24]:
        w('       ' + x)


def dump(va, n, tag):
    w('\n=== %s (@%08X, %dB 窗口) ===' % (tag, va, n))
    for i in md.disasm(bytes_at(va, n), va):
        w('  %08X  %-7s %-40s' % (i.address, i.mnemonic, i.op_str))


dump(0x4A4D10, 0x120, 'B1 原生登场例程 0x4A4D10')
dump(0x4A5420, 0x90, 'B2 月度例程里的 0x4A5420')
dump(0x4A5500, 0x90, 'B3 月度例程里的 0x4A5500')
dump(0x4A0540, 0x80, 'D 0x4A0540 城列表插入')

# ---- C) BSDATA rec[0x39] (= ent+0x2d) 实测 ----
w('\n=== C) byte[ent+0x2d] = BSDATA rec[0x39] 的分布 (含 &7 与 主君/身分码 对照) ===')
BSD = open(ROOT / 'BSDATA1.TR2.orig', 'rb').read()
R = 59
PRE = json.load(open(REV / '_child_preload.json', encoding='utf-8'))
KIN = json.load(open(REV / '_kin.json', encoding='utf-8'))
ents = json.load(open(REV / 'ents_dump.json', encoding='utf-8')) if (REV / 'ents_dump.json').exists() else None


def rec(oid):
    return BSD[oid * R: oid * R + R]


def stat(rec_b):
    """BSDATA 记录里我们能读懂的几项 (记录口径: 名字@1..7/8..14, 生年偏移@27, 父@0x29)"""
    birth_off = (struct.unpack_from('<H', rec_b, 27)[0] >> 7) & 0x3f
    father = struct.unpack_from('<H', rec_b, 0x29)[0]
    return dict(name=rec_b[1:15].split(b'\0')[0].decode('gbk', 'replace'),
                by1490=rec_b[27] & 0x7f, appear_off=birth_off, father=father,
                d38=rec_b[0x38], d39=rec_b[0x39], d39_7=rec_b[0x39] & 7)


w('\n  --- fam13 的 14 个孩子 (ent+0x2d <- rec+0x39, 因 ent[k]=rec[k+12]) ---')
bad = 0
for e in PRE['batches']['fam13']:
    s = stat(rec(e['oid']))
    kid = s['d39_7'] != 0
    bad += kid
    w('   槽%4d oid%3d %-14s 生年%4d 虚岁%2d 父oid%4d  rec[0x38]=%04X rec[0x39]=%02X &7=%d %s'
      % (e['slot'], e['oid'], s['name'], 1490 + s['by1490'], e['age_engine'], s['father'],
         s['d38'], s['d39'], s['d39_7'], '门开(会挂载)' if kid else '门关(只写+0x12/13)'))
w('   => 门开 %d/%d' % (bad, len(PRE['batches']['fam13'])))

w('\n  --- 全体 700 条: d39&7 的分布, 以及与 父oid/登场年 的相关性 ---')
import collections
c = collections.Counter()
by7 = collections.defaultdict(list)
for oid in range(700):
    s = stat(rec(oid))
    c[s['d39_7']] += 1
    by7[s['d39_7']].append((oid, s))
for k in sorted(c):
    sample = by7[k][:4]
    w('   &7=%d : %3d 条   例: %s' % (k, c[k], ' / '.join(
        '%d:%s(父%d,生%d)' % (o, s['name'], s['father'], 1490 + s['by1490']) for o, s in sample)))
w('\n   逐位拆开看 d39 都有哪些 bit 被用到:')
bits = collections.Counter()
for oid in range(700):
    v = rec(oid)[0x39]
    for b in range(8):
        if v >> b & 1:
            bits[b] += 1
w('   %s' % dict(sorted(bits.items())))
OUT.close()
print('\n明细 -> .rev/_probe_genpuku3.txt')
