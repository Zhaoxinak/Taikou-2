# -*- coding: utf-8 -*-
"""
#36/#38 terrain attack/defense hunt.

Both previous candidates were falsified:
  0x513a78 -> facility instance slots (runtime)
  0x5037b8 -> weather "keep" probability table

New lead: follow the *battle terrain map* itself.
  TERRAIN_MAP  @ 0x512868   (40x19 nibbles, low nibble = terrain id 0..15)

Anything that reads the terrain nibble and then indexes a *static* table is a
terrain effect table.  Print every xref plus its instruction neighbourhood, and
flag static-table indexing patterns nearby.
"""
import sys, io, struct, bisect
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
from capstone import *
from capstone.x86 import *

BASE = 0x400000
MEM = open('scripts/_unpacked_mem.bin', 'rb').read()
TEXT_START, TEXT_END = 0x401000, 0x4d0000
md = Cs(CS_ARCH_X86, CS_MODE_32)
md.detail = True

TARGETS = {
    0x512868: 'TERRAIN_MAP',
    0x512b60: 'DEPLOY_MAP',
    0x513910: 'UNIT_SLOTS',
}

# ---- function start set (all call rel32 targets) -------------------------
def starts():
    s = set()
    i = 0
    while True:
        i = MEM.find(b'\xe8', i, TEXT_END - BASE)
        if i < 0:
            break
        rel = struct.unpack_from('<i', MEM, i + 1)[0]
        t = (i + BASE) + 5 + rel
        if TEXT_START <= t < TEXT_END:
            s.add(t)
        i += 1
    return sorted(s)

ST = starts()

def owner(va):
    k = bisect.bisect_right(ST, va) - 1
    return ST[k] if k >= 0 else 0

# ---- collect xrefs -------------------------------------------------------
def xrefs(addr):
    pat = struct.pack('<I', addr)
    out = []
    i = 0
    while True:
        i = MEM.find(pat, i, TEXT_END - BASE)
        if i < 0:
            break
        out.append(i + BASE)
        i += 1
    return out

def dis_around(va, back=0x30, fwd=0x30):
    """Disassemble a window, resyncing so that `va` lands on an instruction."""
    for s in range(va - back, va + 1):
        lines = []
        hit = False
        for ins in md.disasm(MEM[s - BASE: va + fwd - BASE], s):
            lines.append(ins)
            if ins.address <= va < ins.address + ins.size:
                hit = True
        if hit and lines:
            return lines
    return list(md.disasm(MEM[va - BASE - 4: va + fwd - BASE], va - 4))

STATIC_LO, STATIC_HI = 0x500000, 0x512000   # static initialised data (tables)

def scan(addr, name):
    print(f'\n################ {name} @ {addr:#x} ################')
    xs = xrefs(addr)
    print(f'raw dword occurrences: {len(xs)}')
    byfunc = {}
    for x in xs:
        f = owner(x)
        byfunc.setdefault(f, []).append(x)
    for f in sorted(byfunc):
        print(f'  func {f:#x}: {len(byfunc[f])} refs  -> ' +
              ' '.join(f'{a:#x}' for a in byfunc[f][:8]))
    return byfunc

def static_tables_near(func_start, span=0x400):
    """List static-data addresses referenced inside a function."""
    found = {}
    cur = func_start
    stop = min(func_start + span, TEXT_END)
    for ins in md.disasm(MEM[cur - BASE: stop - BASE], cur):
        for op in ins.operands:
            if op.type == X86_OP_MEM:
                d = op.mem.disp & 0xffffffff
                if STATIC_LO <= d < STATIC_HI:
                    found.setdefault(d, []).append((ins.address, ins.mnemonic, ins.op_str))
            elif op.type == X86_OP_IMM:
                d = op.imm & 0xffffffff
                if STATIC_LO <= d < STATIC_HI:
                    found.setdefault(d, []).append((ins.address, ins.mnemonic, ins.op_str))
    return found

if __name__ == '__main__':
    for a, n in TARGETS.items():
        bf = scan(a, n)
        for f in sorted(bf):
            tabs = static_tables_near(f)
            if tabs:
                print(f'    -- static tables inside func {f:#x}:')
                for d, uses in sorted(tabs.items()):
                    u = uses[0]
                    print(f'        {d:#x}  ({len(uses)}x)  {u[0]:#x} {u[1]} {u[2]}')
