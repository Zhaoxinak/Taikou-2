# -*- coding: utf-8 -*-
"""
Parse the per-type decoder 0x47ff68 into case blocks.

Strategy
--------
0x47ff68 is a compiled switch keyed on ax = [esp+0x18] (the record type).
Each case = a guard (test/cmp ax + conditional jump to next case) followed by
a body that copies payload bytes from 0x522c88/0x522c60/0x522c70 into
per-type scenario buffers (0x509xxx) via 0x4ebfe0/0x4ec010 (memcpy-like).

We segment the function by 'ret' boundaries and collect, per case:
  - guard predicate(s) on ax  -> deduced type value
  - push 0x509xxx  (destination buffer)
  - push 0x522c88 / 0x522c60 / 0x522c70 (payload source)
  - call 0x4ebfe0 / 0x4ec010  (memcpy(src,dst) or memcpy(dst,src))
"""
import os, sys, struct
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

HERE = os.path.dirname(os.path.abspath(__file__))
IMG = open(os.path.join(HERE, "_unpacked_mem.bin"), "rb").read()
BASE = 0x400000
DISP = 0x47ff68
md = Cs(CS_ARCH_X86, CS_MODE_32)
md.detail = True

# Disassemble a generous window; find function end = first 'ret' after a large gap
# (functions here end with ret; we'll just take a big fixed window).
WINDOW = 0x6000
insns = []
code = IMG[DISP - BASE: DISP - BASE + WINDOW]
for ins in md.disasm(code, DISP):
    insns.append(ins)
    if len(insns) > 4000:
        break

# index by address
addr2ins = {ins.address: ins for ins in insns}

# Find case start addresses: function entry + targets of conditional jumps that
# guard cases. A guard jump target is a "case entry" candidate.
case_starts = set([DISP])
for ins in insns:
    if ins.mnemonic in ('jne', 'jge', 'jg', 'jl', 'jle', 'je', 'ja', 'jb', 'jae', 'jbe', 'jmp'):
        tgt = None
        # parse target addr from op_str
        s = ins.op_str.strip()
        try:
            tgt = int(s, 16) if s.lower().startswith('0x') else int(s)
        except ValueError:
            tgt = None
        if tgt and DISP <= tgt <= DISP + WINDOW:
            case_starts.add(tgt)

# Sort case starts
starts = sorted(case_starts)

def case_type_guess(block):
    """From the guard comparisons at the top of a case, guess the type value."""
    types = []
    for ins in block:
        s = ins.op_str.lower()
        if ins.mnemonic == 'test' and 'ax' in s and ', ax' in s:
            # test ax, ax  -> checks ==0
            types.append(('test0', None))
        if ins.mnemonic == 'cmp' and 'ax' in s:
            # cmp ax, N  or cmp ..., ax
            parts = [p.strip() for p in s.split(',')]
            for p in parts:
                if p.startswith('0x') or p.isdigit():
                    types.append(('cmp', int(p, 16) if p.lower().startswith('0x') else int(p)))
    return types

# Segment: each case runs from a start addr until the next start addr (or a ret)
results = []
for idx, st in enumerate(starts):
    end = starts[idx + 1] if idx + 1 < len(starts) else (st + 0x200)
    block = [ins for ins in insns if st <= ins.address < end]
    # stop block at first ret
    body = []
    for ins in block:
        body.append(ins)
        if ins.mnemonic in ('ret', 'retn'):
            break
    # collect buffer / payload / memcpy info
    buffers = []
    payloads = []
    memcpys = []
    for ins in body:
        s = ins.op_str.lower()
        if ins.mnemonic == 'push':
            imm = ins.op_str.strip()
            try:
                v = int(imm, 16) if imm.lower().startswith('0x') else int(imm)
            except ValueError:
                v = None
            if v is not None:
                if 0x509000 <= v <= 0x50b000:
                    buffers.append(hex(v))
                if v in (0x522c88, 0x522c60, 0x522c70):
                    payloads.append(hex(v))
        if ins.mnemonic == 'call':
            t = ins.op_str.strip().lower()
            if t in ('0x4ebfe0', '0x4ec010'):
                memcpys.append(t)
    results.append({
        'start': hex(st),
        'n_ins': len(body),
        'type_guess': case_type_guess(body[:6]),
        'buffers': buffers,
        'payloads': payloads,
        'memcpys': memcpys,
    })

print("Function 0x47ff68: %d instructions, %d case-start candidates" % (len(insns), len(starts)))
print("="*100)
for r in results[:60]:
    print("%-10s ins=%-3d type=%s bufs=%s pl=%s mc=%d" % (
        r['start'], r['n_ins'], r['type_guess'], r['buffers'][:6], r['payloads'], len(r['memcpys'])))
print("... total cases:", len(results))
