#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""S6 (0x516610) 是 C++ 对象：`mov ecx, 0x516610` 置 this，随后 call = 成员方法。
1. 找出全部 (mov ecx,0x516610) 后 N 条指令内的 call 目标 => 方法表；
2. 对每个方法体扫描 [ecx+disp]（disp 0..0x2d）=> 该方法的字段访问；
3. 汇总为「方法 -> 字段语义」表。
"""
import pickle, struct, sys, collections, json
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

IMG = open('scripts/_unpacked_mem.bin', 'rb').read()
BASE = 0x400000
S6, SIZE = 0x516610, 0x2e
_p = pickle.load(open('scripts/_insn_addrs.pkl', 'rb'))
insn, starts = _p[0], sorted(_p[1])
md = Cs(CS_ARCH_X86, CS_MODE_32); md.detail = True

# 有序指令列表，便于「前面几条指令」回溯
ordered = sorted(insn.keys())

# ---- 1. 找 mov ecx, 0x516610 之后的 call 目标 ----
this_sites = [o for o in ordered if insn[o][1] == 'mov ecx, 0x516610']
print(f'mov ecx, 0x516610 站点: {len(this_sites)}')

calls = collections.Counter()
call_site_fn = collections.defaultdict(list)
for o in this_sites:
    i = ordered.index(o) if False else None
    # 用二分定位下标
    import bisect
    k = bisect.bisect_left(ordered, o)
    for j in range(k + 1, min(k + 6, len(ordered))):
        t = insn[ordered[j]][1]
        if t.startswith('call '):
            tgt = int(t.split()[1], 16)
            calls[tgt] += 1
            call_site_fn[tgt].append(BASE + o)
            break
        if t.startswith('j') or t.startswith('ret'):
            break

print(f'候选方法: {len(calls)} 个\n')

# ---- 2. 逐方法扫描 [ecx+disp] ----
CANON = {'eax': 'eax', 'ax': 'eax', 'al': 'eax', 'ah': 'eax',
         'ebx': 'ebx', 'bx': 'ebx', 'bl': 'ebx', 'bh': 'ebx',
         'ecx': 'ecx', 'cx': 'ecx', 'cl': 'ecx', 'ch': 'ecx',
         'edx': 'edx', 'dx': 'edx', 'dl': 'edx', 'dh': 'edx',
         'esi': 'esi', 'si': 'esi', 'edi': 'edi', 'di': 'edi',
         'ebp': 'ebp', 'bp': 'ebp'}
NOWRITE = ('push', 'test', 'cmp')


def body(va, maxlen=0x800):
    off = va - BASE
    out = []
    for ins in list(md.disasm(IMG[off:off + maxlen], va)):
        out.append(ins)
        if ins.mnemonic in ('ret', 'retn', 'hlt', 'ud2'):
            break
    return out


methods = {}
for tgt, cnt in calls.most_common():
    b = body(tgt)
    if len(b) < 2:
        continue
    acc = []
    ctx = {'ecx'}
    for ins in b:
        # 追踪 ebx/esi/edi 从 ecx 传播
        if ins.mnemonic == 'mov' and len(ins.operands) == 2:
            d, s = ins.operands
            if d.type == 1 and s.type == 1:
                dn = CANON.get(ins.reg_name(d.reg), ins.reg_name(d.reg))
                sn = CANON.get(ins.reg_name(s.reg), ins.reg_name(s.reg))
                if sn in ctx:
                    ctx.add(dn)
                elif dn in ctx:
                    ctx.discard(dn)
        for oi, o in enumerate(ins.operands):
            if o.type != 3 or o.mem.index or not (0 <= o.mem.disp < SIZE):
                continue
            bn = ins.reg_name(o.mem.base) if o.mem.base else ''
            if bn not in ctx:
                continue
            imm = next((x.imm for x in ins.operands if x.type == 2), None)
            acc.append(dict(disp=o.mem.disp, w=o.size, mn=ins.mnemonic,
                            rw='W' if (oi == 0 and ins.mnemonic not in NOWRITE) else 'R',
                            imm=imm, text=f'{ins.mnemonic} {ins.op_str}'))
    if acc:
        methods[tgt] = dict(calls=cnt, sites=call_site_fn[tgt][:3], acc=acc)

print(f'有 [ecx+N] 字段访问的方法: {len(methods)} / {len(calls)}\n')
print('=== 方法表（按调用次数）===')
for tgt, m in sorted(methods.items(), key=lambda x: -x[1]['calls']):
    disps = sorted({a['disp'] for a in m['acc']})
    wr = sorted({a['disp'] for a in m['acc'] if a['rw'] == 'W'})
    sig = ' '.join(f"{'+%02x' % a['disp']}{a['w']}{a['rw']}" + (f"={a['imm']}" if a['imm'] is not None else '')
                   for a in m['acc'][:6])
    print(f"0x{tgt:06x}  calls={m['calls']:3d}  R/W字段={[hex(x) for x in wr]}  | {sig}")

json.dump({hex(k): v for k, v in methods.items()},
          open('scripts/s6_methods.json', 'w'), ensure_ascii=False, indent=1)
print('\n-> scripts/s6_methods.json')

# ---- 3. 字段 -> 方法反查 ----
print('\n=== 字段 -> 访问它的方法 ===')
byfield = collections.defaultdict(list)
for tgt, m in methods.items():
    for a in m['acc']:
        byfield[a['disp']].append((tgt, a))
for d in range(SIZE):
    if d not in byfield:
        print(f'+{d:02x}  (无成员方法访问)')
        continue
    rs = [f"0x{t:x}({'W' if a['rw']=='W' else 'R'}{a['w']})" for t, a in byfield[d]]
    print(f'+{d:02x}  {len(rs):3d}  ' + ' '.join(rs[:10]))
