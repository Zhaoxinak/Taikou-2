# -*- coding: utf-8 -*-
"""probe_genpuku2.py —— 元服链线性全量拆 (0x4A4FC0 起, 不在第一个 ret 停)

probe_genpuku.py 的 Q1 只看了 0x4A4FC0 的短路径 (34B 就 ret), 但它的
`test byte[esi+0x2d],7 / jne 0x4a4fe2` 跳进了后面的大块 —— Q3b 显示 0x4A5033/0x4A507B
在那片区域调主君 setter 0x49A7D0, 那才是真正的挂载逻辑。本脚本:
  A) 线性反汇编 0x4A4FC0..0x4A5400, 标出每个 jmp/jcc 目标落在窗口外的哪
  B) 谁跳进这块 (E8/EB/E9 到 0x4A4FC0..0x4A5010 的所有站点 + 直接地址立即数引用)
  C) 0x49F5D0 / 0x4A5350 返回什么 (ax 的来源)
  D) byte[+0x2d] 的全部引用点 (元服门的语义 = 这个字节的低 3 位是什么)
"""
import json, struct, sys, pathlib
import capstone

try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

ROOT = pathlib.Path(__file__).resolve().parent.parent
REV = ROOT / '.rev'
OUT = open(REV / '_probe_genpuku2.txt', 'w', encoding='utf-8')


def w(*a):
    print(*a, file=OUT)


LY = json.load(open(REV / '_big_layout.json', encoding='utf-8'))
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


def bytes_at(va, n):
    for nm, sva, vsz, rawsz, raw in SECS:
        if sva <= va < sva + max(vsz, rawsz):
            return d[raw + (va - sva): raw + (va - sva) + n]
    raise KeyError(va)


md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)
LO, HI = 0x401000, 0x4FA000
BODY = {}
for nm, sva, vsz, rawsz, raw in SECS:
    if nm in ('.text', '.data'):
        BODY[nm] = (sva, min(vsz, rawsz), d[raw:raw + min(vsz, rawsz)])

W0, W1 = 0x4A4FC0, 0x4A5400
w('=== A) 0x4A4FC0..0x4A5400 线性反汇编 ===')
ins = list(md.disasm(bytes_at(W0, W1 - W0), W0))
for i in ins:
    mark = ''
    if i.mnemonic.startswith('j') and i.op_str.startswith('0x'):
        t = int(i.op_str, 16)
        mark = '   -> %s %08X' % ('窗口内' if W0 <= t < W1 else '窗口外', t)
    w('%08X  %-7s %-38s%s' % (i.address, i.mnemonic, i.op_str, mark))
w('\n  指令 %d 条, 覆盖到 %08X (窗口 %08X) —— 断掉说明撞上非法字节'
  % (len(ins), ins[-1].address + ins[-1].size, W1))

w('\n=== B) 谁进入这块 (call/jmp 到 0x4A4FC0..0x4A5010, 以及立即数引用) ===')
for nm, (sva, size, body) in BODY.items():
    for off in range(len(body) - 5):
        va = sva + off
        if not (LO <= va <= HI):
            continue
        b = body[off]
        if b == 0xE8 or b == 0xE9:
            rel = struct.unpack_from('<i', body, off + 1)[0]
            t = va + 5 + rel
            if W0 <= t < W0 + 0x60:
                w('  %-6s %08X  %s -> %08X' % (nm, va, 'call' if b == 0xE8 else 'jmp', t))
        elif b in (0xEB,):
            rel = struct.unpack_from('<b', body, off + 1)[0]
            t = va + 2 + rel
            if W0 <= t < W0 + 0x60:
                w('  %-6s %08X  short jmp -> %08X' % (nm, va, t))
        v = struct.unpack_from('<I', body, off)[0]
        if W0 <= v < W0 + 0x60 and b != 0xE8:
            w('  %-6s %08X  [dword 立即数/表项 = %08X] (前字节 %02X)' % (nm, va, v, b))

w('\n=== C) 0x49F5D0 (被 0x4A5350 调, 返 ax) ===')
for i in md.disasm(bytes_at(0x49F5D0, 0x60), 0x49F5D0):
    w('%08X  %-7s %s' % (i.address, i.mnemonic, i.op_str))
    if i.mnemonic == 'ret':
        break

w('\n=== D) byte[+0x2d] 与 byte[+0x12]/[+0x13]/[+0x16] 的引用点 ===')
PAT = {'+0x2d': [b'\x2d', ], }
# 用反汇编窗口扫: 0x401000..0x4C4000 分块, 找含 [+0x2d] 的指令 (代价可控: 只扫 .text)
import collections
HITS = collections.defaultdict(list)
for nm, (sva, size, body) in BODY.items():
    step = 0x2000
    for base in range(0, size, step):
        chunk = body[base: base + step + 16]
        va = sva + base
        for i in md.disasm(chunk, va):
            s = i.op_str
            for off in ('0x2d', '0x12', '0x13', '0x16'):
                if ('+ %s]' % off) in s:
                    HITS[off].append('%s:%08X %s %s' % (nm, i.address, i.mnemonic, s))
for off in ('0x2d', '0x12', '0x13', '0x16'):
    h = HITS[off]
    w('\n  [%s] 引用 %d 处:' % (off, len(h)))
    for x in h[:40]:
        w('    ' + x)
OUT.close()
print('明细 -> .rev/_probe_genpuku2.txt')
