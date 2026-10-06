# -*- coding: utf8 -*-
"""chk_child_sites.py —— M2 开工前站点体检 (只读 big.exe / clean_dump, 不开游戏)

要确认的四件事:
  1) 两个钩子站点仍是 clean 原文 (E8 call), 没被 4a..4i 的补丁占用
  2) P2 有没有把 0x4A4F1A `cmp si,0x172`(登场例程算实体指针的界) 抬到 CAP —— R1 的开关
  3) 预载目标槽 463..475 在 .edata 静态镜像里确实是空槽 0x808F, 且姓/名表全 0
  4) 月钩 0x4A4CC0 / 载入链最后一跳 0x47F71F 的解码边界
"""
import json, os, struct, sys, pathlib
import capstone

try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

ROOT = pathlib.Path(__file__).resolve().parent.parent
REV = ROOT / '.rev'
sys.path.insert(0, str(REV))
import child_stub as CS

LY = json.load(open(REV / '_big_layout.json', encoding='utf-8'))
EXE = ROOT / 'TAIK2W95_big.exe'
d = open(EXE, 'rb').read()
pe = struct.unpack_from('<I', d, 0x3C)[0]
nsec = struct.unpack_from('<H', d, pe + 6)[0]
opt = struct.unpack_from('<H', d, pe + 20)[0]
secs = []
for i in range(nsec):
    o = pe + 24 + opt + i * 40
    nm = d[o:o + 8].rstrip(b'\x00').decode()
    va, rawsz, raw = struct.unpack_from('<III', d, o + 12)
    secs.append((nm, 0x400000 + va, rawsz, raw))


def sec(nm):
    return [s for s in secs if s[0] == nm][0]


tnm, tva, tsz, traw = sec('.text')
enm, eva, esz, eraw = sec('.edata')


def T(va, n):
    return d[traw + (va - tva): traw + (va - tva) + n]


def E(va, n):
    return d[eraw + (va - eva): eraw + (va - eva) + n]


POOL, STRIDE, CAP = LY['pool_va'], LY['stride'], LY['cap']
print('big.exe %dB  .text 0x%06X..  .edata 0x%06X..0x%06X (raw 0x%X)'
      % (len(d), tva, eva, eva + esz, eraw))

# 1) 钩子站点 (开工前=原文; 建好后=E8 跳桩, 两种都合法, 只报不炸)
for site, want in CS.SITE_ORIG.items():
    got = T(site, 5)
    md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)
    ins = list(md.disasm(T(site, 5), site))
    if got == want:
        print('钩子 0x%06X: %-14s 未挂钩(开工前状态)  [%s %s]'
              % (site, got.hex(), ins[0].mnemonic if ins else '?', ins[0].op_str if ins else ''))
    else:
        tgt = site + 5 + struct.unpack_from('<i', got, 1)[0] if got[:1] == b'\xE8' else -1
        print('钩子 0x%06X: %-14s 已挂钩 -> 0x%06X  [%s %s]'
              % (site, got.hex(), tgt, ins[0].mnemonic if ins else '?', ins[0].op_str if ins else ''))
        assert tgt in (LY['v']['CHILD_MONTH_HOOK'], LY['v']['CHILD_LOAD_HOOK']), \
            '站点既不是原文也不是已知钩子: %08X -> %08X' % (site, tgt)

# 2) R1: 登场例程的实体界
bound_va = 0x4A4F1A
print('R1 @0x%06X: %s  ->  %s' % (bound_va, T(bound_va, 5).hex(),
                                  T(bound_va, 5) == b'\x66\x81\xfe\x72\x01' and '仍是 0x172 (需抬到 CAP)'
                                  or '已改: ' + hex(struct.unpack_from('<H', T(bound_va, 5), 3)[0])))

# 3) 预载目标槽
slots = [int(x) for x in os.environ.get('CHK_SLOTS', ' '.join(str(463 + i) for i in range(13))).split()]
bad = []
for s in slots:
    st = struct.unpack_from('<H', E(POOL + s * STRIDE + 0x2c, 2), 0)[0]
    ent = E(POOL + s * STRIDE, STRIDE)
    sur = E(LY['surname_tab_va'] + s * 7, 7)
    giv = E(LY['given_tab_va'] + s * 7, 7)
    print('槽 %d: 状态字 %04X  实体 %s  姓 %s  名 %s' % (s, st, ent.hex(), sur.hex(), giv.hex()))
    if st != 0x808F or sur.strip(b'\x00') or giv.strip(b'\x00'):
        bad.append(s)
print('非空槽 %d 个' % len(bad), bad)
assert not bad, '目标槽必须逐槽静态空槽 0x808F 且姓名表全 0 (R4)'

# 4) 上下文解码
for va, ln in ((0x4A4CB8, 16), (0x47F714, 16)):
    md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)
    print('--- 0x%06X ---' % va)
    for i in md.disasm(T(va, ln), va):
        print('  %08X  %-22s %s %s' % (i.address, i.bytes.hex(), i.mnemonic, i.op_str))
