# -*- coding: utf-8 -*-
"""probe_genpuku.py —— M4 元服前置探针 (只读 big.exe / clean_dump, 不开游戏)

要回答的四个问题 (答完才允许写 M4 桩):
  Q1 `0x4A4FC0` 元服初始化到底做什么 —— 全链反汇编 + 它读了实体的哪些字段。
  Q2 **R7**: 它会不会给这个人**另找槽位**(搬进 0..369)、或调用会整池搬迁的例程。
  Q3 主君 setter 到底是不是 `0x49A7D0` (PLAN §3 这么写, CHILD_STATE_RECIPE 的访问器表里没有它)
     —— 按"两条独立证据": ①访问器簇的字节形状 ②全镜像调用点传的参数语义。
  Q4 原生自己怎么调用 `0x4A4FC0` (调用点前有什么年龄/身分门), 以及 cap-3 增函数族
     `0x4A3040 + k*0x20` 的约定 —— 元服那月要不要顺手把属性拉到成年档。

输出 _probe_genpuku.txt (UTF-8)。
"""
import json, os, struct, sys, pathlib
import capstone

try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

ROOT = pathlib.Path(__file__).resolve().parent.parent
REV = ROOT / '.rev'
OUT = open(REV / '_probe_genpuku.txt', 'w', encoding='utf-8')


def w(*a):
    print(*a, file=OUT)
    print(*a)


LY = json.load(open(REV / '_big_layout.json', encoding='utf-8'))
d = open(ROOT / 'TAIK2W95_big.exe', 'rb').read()
CLN = open(REV / 'clean_dump.bin', 'rb').read()
pe = struct.unpack_from('<I', d, 0x3C)[0]
opt = struct.unpack_from('<H', d, pe + 20)[0]
SECS = []
for i in range(struct.unpack_from('<H', d, pe + 6)[0]):
    o = pe + 24 + opt + i * 40
    nm = d[o:o + 8].rstrip(b'\0').decode()
    vsz = struct.unpack_from('<I', d, o + 8)[0]
    va, rawsz, raw = struct.unpack_from('<III', d, o + 12)
    SECS.append((nm, 0x400000 + va, vsz, rawsz, raw))
CB = 0x400000


def bytes_at(va, n, img=None):
    """按 VA 找分区取字节 (本 exe 的 .text 只到 0x4C4000, 别用单段假设)"""
    img = d if img is None else img
    for nm, sva, vsz, rawsz, raw in SECS:
        if sva <= va < sva + max(vsz, rawsz):
            off = raw + (va - sva)
            return img[off:off + n]
    raise KeyError('VA %08X 不在任何段内' % va)


md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)


def disasm(va, n=None, img=None, upto=None):
    """从 va 线性反汇编到 ret (或 upto 条)"""
    if n is None:
        n = 0x400
    buf = bytes_at(va, n, img)
    out = []
    for i in md.disasm(buf, va):
        out.append(i)
        if upto and len(out) >= upto:
            break
        if i.mnemonic == 'ret':
            break
    return out


def txt(i):
    return '%08X  %-8s %s' % (i.address, i.mnemonic, i.op_str)


def calls_of(ins_list):
    """本段里出现的 call 目标 (直接 rel32 + 内存 IAT)"""
    out = []
    for i in ins_list:
        if i.mnemonic == 'call':
            out.append(i.op_str)
    return out


# ---------------- 调用点索引: 全镜像扫 E8 rel32 -> 目标 VA ----------------
LO, HI = 0x401000, 0x4FA000
CALLS = {}          # target -> [site]
for nm, sva, vsz, rawsz, raw in SECS:
    if nm not in ('.text', '.data'):
        continue
    base, size = sva, min(vsz, rawsz)
    body = d[raw:raw + size]
    for off in range(0, len(body) - 5):
        va = base + off
        if not (LO <= va <= HI):
            continue
        if body[off] != 0xE8:
            continue
        rel = struct.unpack_from('<i', body, off + 1)[0]
        t = va + 5 + rel
        if LO <= t <= HI:
            CALLS.setdefault(t, []).append(va)


def callers(t):
    return sorted(CALLS.get(t, []))


w('=' * 78)
w('M4 元服探针  (big.exe %d B)' % len(d))
w('=' * 78)

# ================= Q1/Q2: 0x4A4FC0 =================
GF = 0x4A4FC0
w('\n--- Q1 元服初始化 0x4A4FC0 全链 ---')
head = disasm(GF)
w('\n'.join(txt(i) for i in head))
w('\n  长度 %dB  尾部 %s' % (head[-1].address + head[-1].size - GF, txt(head[-1])))
w('  直接 call: %s' % calls_of(head))

SUBS = {}
for op in calls_of(head):
    if op.startswith('0x'):
        t = int(op, 16)
        SUBS[t] = disasm(t)
for t in sorted(SUBS):
    w('\n--- 子例程 0x%08X (%dB) ---' % (t, SUBS[t][-1].address + SUBS[t][-1].size - t))
    w('\n'.join(txt(i) for i in SUBS[t]))
    inner = calls_of(SUBS[t])
    if inner:
        w('  它的 call: %s' % inner)
        for op in inner:
            if op.startswith('0x') and int(op, 16) not in SUBS and int(op, 16) < GF + 0x1000:
                pass

# 实体字段读写清单 (ecx 是实体指针)
w('\n--- Q1b 元服链里出现的 [ecx+off] / [reg+off] 位移 ---')
FIELDS = {}
for t in [GF] + sorted(SUBS):
    for i in (head if t == GF else SUBS[t]):
        if '[ec' in i.op_str or '[eax' in i.op_str or '[edi' in i.op_str or '[esi' in i.op_str:
            FIELDS.setdefault(i.op_str, []).append('%08X@%08X' % (i.address, t))
for k in sorted(FIELDS):
    w('  %-42s %s' % (k, ','.join(FIELDS[k][:6])))

# ================= Q3: 访问器簇 =================
w('\n--- Q3 实体访问器簇 0x49A5C0..0x49A8E0 线性反汇编 ---')
ins = list(md.disasm(bytes_at(0x49A5C0, 0x320), 0x49A5C0))
for i in ins:
    w('  ' + txt(i))

w('\n--- Q3b 谁调用 0x49A7D0 / 0x49A7E0 / 0x49A6D0 ---')
for t in (0x49A7D0, 0x49A7E0, 0x49A6D0, 0x49A860):
    cs = callers(t)
    w('  0x%08X 调用点 %d 处: %s' % (t, len(cs), ' '.join('%06X' % c for c in cs[:14])))

# ================= Q4: 原生怎么调 0x4A4FC0 =================
w('\n--- Q4 0x4A4FC0 的调用点与它前面的门 ---')
for c in callers(GF):
    pre = bytes_at(c - 0x30, 0x30 + 5)
    ins = list(md.disasm(pre, c - 0x30))
    w('\n  调用点 %08X, 前 0x30 字节:' % c)
    for i in ins[-14:]:
        w('    ' + txt(i))

w('\n--- Q4b cap-3 增函数族 0x4A3040 + k*0x20 (k=0..5) ---')
for k in range(0, 7):
    t = 0x4A3040 + k * 0x20
    ins = disasm(t, upto=24)
    w('\n  k=%d @%08X (%s):' % (k, t, 'callers=%d' % len(callers(t))))
    for i in ins[:12]:
        w('    ' + txt(i))

OUT.close()
print('\n明细 -> .rev/_probe_genpuku.txt')
