"""抽取「实体字段增量族」：所有包含 call 0x4ebca0(饱和加) 的函数，
解析其 (目标字段偏移, 位宽, 上限常量)，输出完整族表。
饱和加 sat_add(a,b,cap) = min(a+b, cap)；饱和减 sat_sub(a,b) = (a>b)?a-b:0 @0x4ebcd0
"""
# <auto: portable root (injected by _fix_win_paths.py)>
import os as _os
def _find_root(_p):
    for _ in range(8):
        if _os.path.isdir(_os.path.join(_p, 'scripts')) and _os.path.isfile(_os.path.join(_p, 'project.godot')):
            return _p
        _p = _os.path.dirname(_p)
    return _p
_ROOT = _find_root(_os.path.dirname(_os.path.abspath(__file__)))
# </auto: portable root>

import pickle, re
from collections import defaultdict
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

BASE = 0x400000
IMG = open(_ROOT + '/scripts/_unpacked_mem.bin', 'rb').read()
d, starts = pickle.load(open(_ROOT + '/scripts/_insn_addrs.pkl', 'rb'))
SIZE = {off: s[0] for off, s in d.items()}
TEXT = {off: s[1] for off, s in d.items()}
md = Cs(CS_ARCH_X86, CS_MODE_32); md.detail = False
STARTS = sorted(starts)

def disasm_func_off(foff, maxlen=0x60):
    out = []; o = foff; end = foff + maxlen
    while o < end and o in SIZE:
        out.append((o, TEXT[o]))
        if TEXT[o] == 'ret': break
        o += SIZE[o]
    return out

SAT_ADD = 0x4ebca0
rows = []
for fn in STARTS:
    insns = disasm_func_off(fn)
    if not any(t == f'call 0x{SAT_ADD:x}' for _, t in insns):
        continue
    code = insns
    # 解析：找 movzx ?x, (byte|word) ptr [esi + 0xNN]  （读取当前值）
    #       找 push 0xNNNN （上限常量）
    #       找 mov (byte|word) ptr [esi + 0xNN], ?l  （写回）
    cur = None      # 读取的字段偏移
    cap = None      # 上限常量
    wback = None    # 写回偏移
    width = None
    for off, t in code:
        m = re.search(r'movzx\s+\w+,\s+(byte|word) ptr \[(\w+) \+ 0x([0-9a-f]+)\]', t)
        if m:
            width = 'B' if m.group(1) == 'byte' else 'W'
            if cur is None:
                cur = int(m.group(3), 16)
            continue
        m = re.search(r'mov\s+(byte|word) ptr \[(\w+) \+ 0x([0-9a-f]+)\],\s+\w+$', t)
        if m:
            wback = int(m.group(3), 16)
            continue
        m = re.match(r'push 0x([0-9a-f]+)$', t)
        if m:
            v = int(m.group(1), 16)
            if 0x10 <= v <= 0xffff and cap is None:
                cap = v
    if wback is None and cur is not None:
        wback = cur
    if wback is not None:
        rows.append({
            'fn': BASE + fn, 'field': wback, 'read': cur, 'cap': cap,
            'width': width or 'B',
            'code': ' | '.join(t for _, t in code),
        })

rows.sort(key=lambda r: r['fn'])
print(f"实体字段增量族（call 0x4ebca0 饱和加）：{len(rows)} 个包装器\n")
print(f"{'包装器':<10} {'字段':>6} {'宽':>3} {'上限':>10}  说明")
for r in rows:
    cap_s = f"0x{r['cap']:x}({r['cap']})" if r['cap'] is not None else '寄存器传入'
    print(f"0x{r['fn']:06x}  +{r['field']:02x}    {r['width']:>2}  {cap_s:>12}  {r['code'][:70]}")

# 去重统计
print("\n===== 按 (字段, 上限) 聚合 =====")
agg = defaultdict(list)
for r in rows:
    agg[(r['field'], r['cap'], r['width'])].append(r['fn'])
for (f, c, w) in sorted(agg, key=lambda x: (x[0] is None, x[0])):
    cap_s = f"{c}(0x{c:x})" if c is not None else 'reg'
    print(f"  +{f:02x} [{w}] cap={cap_s:<12} → {len(agg[(f,c,w)])} 个包装器: "
          + ', '.join(f"0x{v:06x}" for v in agg[(f,c,w)]))

import json
json.dump([{k: (hex(v) if k == 'fn' else v) for k, v in r.items()} for r in rows],
          open(_ROOT + '/scripts/entity_inc_family.json', 'w'), ensure_ascii=False, indent=2)
print("\nwritten scripts/entity_inc_family.json")
