#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""S6 事件上下文 (0x516610, 46B=0x2e) 字段访问谱扫描。

方法：
 1. E8 rel32 收集函数起点，逐起点线性反汇编到 ret（物化成 list，禁止嵌套 disasm 迭代）；
 2. 找全部 `call 0x49f6b0`（= mov eax,0x516610; ret）；
 3. 从每个调用点前向 ~90 条指令做寄存器追踪：call 后 eax=ctx，
    追踪 mov reg,ctxreg / mov reg2,reg1 传播；
 4. 记录 mem 操作数 base∈ctxregs 且 disp∈[0,0x2d] 的访问：宽度/读/写/助记符/立即数；
 5. 另做 0x516610..0x51663d 绝对地址扫描作为补充。
"""
import struct, sys, collections, json, os, pickle
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

IMG = open('scripts/_unpacked_mem.bin', 'rb').read()
BASE = 0x400000
N = len(IMG)
S6 = 0x516610
SIZE = 0x2e
CTXGET = 0x49f6b0

md = Cs(CS_ARCH_X86, CS_MODE_32); md.detail = True

CANON = {'eax': 'eax', 'ax': 'eax', 'al': 'eax', 'ah': 'eax',
         'ebx': 'ebx', 'bx': 'ebx', 'bl': 'ebx', 'bh': 'ebx',
         'ecx': 'ecx', 'cx': 'ecx', 'cl': 'ecx', 'ch': 'ecx',
         'edx': 'edx', 'dx': 'edx', 'dl': 'edx', 'dh': 'edx',
         'esi': 'esi', 'si': 'esi', 'edi': 'edi', 'di': 'edi',
         'ebp': 'ebp', 'bp': 'ebp', 'esp': 'esp', 'sp': 'esp'}


def flat(ins):
    """CsInsn -> 纯数据元组（CtInsn 不可 pickle）。"""
    ops = []
    for o in ins.operands:
        if o.type == 1:      # REG
            ops.append(('r', CANON.get(ins.reg_name(o.reg), ins.reg_name(o.reg)), o.size))
        elif o.type == 2:    # IMM
            ops.append(('i', o.imm))
        elif o.type == 3:    # MEM
            m = o.mem
            bn = ins.reg_name(m.base) if m.base else ''
            inn = ins.reg_name(m.index) if m.index else ''
            ops.append(('m', bn, inn, m.disp, o.size))
    return (ins.address, ins.size, ins.mnemonic, ins.op_str, ops)


def build_funcs():
    cache = 'scripts/_func_bodies.pkl'
    if os.path.exists(cache) and os.path.getsize(cache) > 1000:
        return pickle.load(open(cache, 'rb'))
    st = set()
    for i in range(N - 5):
        if IMG[i] == 0xE8:
            rel = struct.unpack('<i', IMG[i + 1:i + 5])[0]
            tgt = i + 5 + rel
            if 0 <= tgt < N:
                st.add(tgt)
    print(f'函数起点 {len(st)}', file=sys.stderr)
    funcs = {}
    for s in sorted(st):
        end = min(s + 0x6000, N)
        body = []
        for ins in list(md.disasm(IMG[s:end], BASE + s)):   # 物化成 list
            body.append(flat(ins))
            if ins.mnemonic in ('ret', 'retn', 'retf', 'hlt', 'ud2'):
                break
            if ins.mnemonic == 'jmp' and ins.operands and ins.operands[0].type == 2:
                break
            if ins.address - BASE >= end:
                break
        if body:
            funcs[s] = body
    print(f'函数体 {len(funcs)} 条', file=sys.stderr)
    pickle.dump(funcs, open(cache, 'wb'))
    return funcs


NOWRITE = ('push', 'test', 'cmp')


def analyze(funcs):
    hits, calls = [], []
    for s, body in funcs.items():
        for k, (addr, sz, mn, txt, ops) in enumerate(body):
            if mn != 'call' or not ops or ops[0][0] != 'i' or ops[0][1] != CTXGET:
                continue
            calls.append((s, k, addr))
            ctx = {'eax'}
            for j in range(k + 1, min(k + 90, len(body))):
                a2, s2, mn2, txt2, ops2 = body[j]
                # --- 传播 ---
                if mn2 == 'mov' and len(ops2) == 2 and ops2[0][0] == 'r' and ops2[1][0] == 'r':
                    dn, sn = ops2[0][1], ops2[1][1]
                    if sn in ctx:
                        ctx.add(dn)
                    elif dn in ctx:
                        ctx.discard(dn)
                elif mn2 in ('xor', 'sub') and len(ops2) == 2 and ops2[0][0] == 'r' \
                        and ops2[1][0] == 'r' and ops2[0][1] == ops2[1][1]:
                    ctx.discard(ops2[0][1])
                # --- 访问记录 ---
                for oi, o in enumerate(ops2):
                    if o[0] != 'm' or o[2]:
                        continue
                    if o[1] not in ctx:
                        continue
                    disp = o[3]
                    if disp < 0 or disp >= SIZE:
                        continue
                    imm = next((x[1] for x in ops2 if x[0] == 'i'), None)
                    hits.append(dict(func=s, va=a2, disp=disp, width=o[4], mn=mn2,
                                     rw='W' if (oi == 0 and mn2 not in NOWRITE) else 'R',
                                     imm=imm, text=f'{mn2} {txt2}'))
    return hits, calls


def abs_scan(funcs):
    out = []
    for s, body in funcs.items():
        for (a2, s2, mn2, txt2, ops2) in body:
            for oi, o in enumerate(ops2):
                if o[0] != 'm' or o[1] or o[2]:
                    continue
                if S6 <= o[3] < S6 + SIZE:
                    imm = next((x[1] for x in ops2 if x[0] == 'i'), None)
                    out.append(dict(func=s, va=a2, disp=o[3] - S6, width=o[4], mn=mn2,
                                    rw='W' if (oi == 0 and mn2 not in NOWRITE) else 'R',
                                    imm=imm, text=f'{mn2} {txt2}'))
    return out


if __name__ == '__main__':
    funcs = build_funcs()
    hits, calls = analyze(funcs)
    ab = abs_scan(funcs)
    print(f'call 0x49f6b0 调用点: {len(calls)}')
    print(f'寄存器间接 [ctx+N] 命中: {len(hits)}')
    print(f'绝对地址 [0x516610+N] 命中: {len(ab)}')
    allh = hits + ab
    bydisp = collections.defaultdict(list)
    for h in allh:
        bydisp[h['disp']].append(h)
    print('\n偏移 宽  R  W  立即数集合 / 助记符')
    for d in range(SIZE):
        hs = bydisp.get(d, [])
        if not hs:
            print(f'+{d:02x}   --         (无直接访问)')
            continue
        ws = collections.Counter(h['width'] for h in hs)
        rw = collections.Counter(h['rw'] for h in hs)
        imms = [f'{v}×{c}' for v, c in sorted(collections.Counter(
            h['imm'] for h in hs if h['imm'] is not None).items(), key=lambda x: -x[1])[:6]]
        mns = collections.Counter(h['mn'] for h in hs)
        print(f"+{d:02x}  w={dict(ws)}  R={rw.get('R',0):3d} W={rw.get('W',0):2d}  "
              f"imm={imms}  mn={dict(mns)}")
    json.dump(dict(hits=allh, calls=len(calls)),
              open('scripts/s6_ctx_access.json', 'w'), ensure_ascii=False, indent=1)
    print('\n-> scripts/s6_ctx_access.json')
