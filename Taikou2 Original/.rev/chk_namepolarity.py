# -*- coding: utf-8 -*-
"""chk_namepolarity.py — 定论: 运行时两张姓名字表 (0x520660 / 0x521AA8) 各放姓还是名

三方对齐:
  A) BSDATA{1}.TR2.orig 记录: rec[0:7] / rec[7:14]  (gen_child_preload 按 前+后 拼出全名)
  B) ents_dump.json  —— 真机内存 dump, dump_ents.py 里 given<-0x520660, surname<-0x521AA8
  C) INST 0x47F7B0 的两个 7 字节写入循环的目标地址与顺序 (clean_dump.bin, offset==RVA)
输出 -> _namepolarity.txt (UTF-8)
"""
import json, os, struct, sys

ROOT = r'F:\Games\Taikou 2\Taikou2 Original'
REV = os.path.join(ROOT, '.rev')
R, NREC = 59, 700
TA, TB = 0x520660, 0x521AA8          # dump_ents.py 里的 SUR_BASE / GIV_BASE
STRIDE = 7
BASE = 0x400000

out = open(os.path.join(REV, '_namepolarity.txt'), 'w', encoding='utf-8')


def w(*a):
    print(*a, file=out)


def gbk7(b):
    return b.split(b'\0')[0].decode('gbk', 'replace')


bsd = open(os.path.join(ROOT, 'BSDATA1.TR2.orig'), 'rb').read()
assert len(bsd) == R * NREC
ents = json.load(open(os.path.join(REV, 'ents_dump.json'), encoding='utf-8'))
w('ents_dump.json: %d 条 (字段 given=%s@0x%X, surname=%s@0x%X)'
  % (len(ents), 'dump_ents 里读 TA', TA, 'dump_ents 里读 TB', TB))

# ---------- B) 真机表 vs BSDATA 字段 ----------
w('\n=== A) 真机内存两表 vs BSDATA rec[0:7]/rec[7:14] (按 oid 对齐) ===')
w('%-5s %-6s %-8s | %-8s(0x520660) %-8s(0x521AA8) | 判定' % ('oid', 'bs[0:7]', 'bs[7:14]', 'tabA', 'tabB'))
score_a = {'same': 0, 'cross': 0, 'none': 0}
score_b = {'same': 0, 'cross': 0, 'none': 0}
seen = set()
for e in ents:
    oid = e.get('oid')
    if not isinstance(oid, int) or oid >= NREC or oid in seen:
        continue
    seen.add(oid)
    rec = bsd[oid * R:oid * R + R]
    f0, f1 = gbk7(rec[0:7]), gbk7(rec[7:14])
    A, B = e.get('given') or '', e.get('surname') or ''
    if not f0 and not f1:
        continue
    def tag(x):
        if x == f0:
            return 'same'
        if x == f1:
            return 'cross'
        return 'none'
    ta, tb = tag(A), tag(B)
    score_a[ta] += 1
    score_b[tb] += 1
    if len(seen) <= 30 or ta == 'none' and tb == 'none' and A and B:
        w('%-5d %-6s %-8s | %-8s %-8s | A=%s B=%s' % (oid, f0, f1, A, B, ta, tb))

w('\n表A(0x520660): 同序(=rec[0:7]) %d / 交叉(=rec[7:14]) %d / 都不符 %d' %
  (score_a['same'], score_a['cross'], score_a['none']))
w('表B(0x521AA8): 同序(=rec[0:7]) %d / 交叉(=rec[7:14]) %d / 都不符 %d' %
  (score_b['same'], score_b['cross'], score_b['none']))
w('可比对 oid 数: %d' % len(seen))

# ---------- C) INST 写入顺序 ----------
w('\n=== B) INST 0x47F7B0 中的表地址常量 (clean_dump.bin, off=VA-0x400000) ===')
d = open(os.path.join(REV, 'clean_dump.bin'), 'rb').read()
sys.path.insert(0, REV)
try:
    import capstone
    md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)
    md.detail = True
    code = d[0x47F7B0 - BASE: 0x47F7B0 - BASE + 0x360]
    order = []
    for i in md.disasm(code, 0x47F7B0):
        s = i.op_str
        for t, nm in ((TA, 'TA(0x520660)'), (TB, 'TB(0x521AA8)')):
            if '%x' % t in s or hex(t) in s:
                w('  %08X  %-10s %-40s  <== %s' % (i.address, i.mnemonic, s, nm))
                if t not in [x[0] for x in order]:
                    order.append((t, nm, i.address))
    w('  首次出现顺序: %s' % ' -> '.join(x[1] for x in order))
except Exception as ex:
    w('  capstone 跳过: %r' % (ex,))

w('\n=== 结论 ===')
w('(见上方统计自行判定; 若要 tableA=姓 则 score_a["same"] 应远大于 cross)')
out.close()
print('-> .rev/_namepolarity.txt')
