# -*- coding: utf-8 -*-
"""Re-syncing linear disassembler for one function. Usage:
   python _dumpfn.py <VA_hex> [max_bytes_hex]
Annotates known symbols. Handles embedded data by re-syncing (+1 byte)."""
import io, sys, struct
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
from capstone import *
from capstone.x86 import *

BASE = 0x400000
MEM = open('scripts/_unpacked_mem.bin', 'rb').read()
md = Cs(CS_ARCH_X86, CS_MODE_32); md.detail = True

SYM = {
    0x49f6b0: 'getCtx', 0x49b860: 'FIRE', 0x44e280: 'curProv',
    0x470210: '?470210', 0x470240: '?470240', 0x47b280: 'GUI', 0x47b900: 'msgDispatch',
    0x496ba0: 'stateEng', 0x49f610: 'subEval', 0x4e83e0: 'subEval2', 0x4e84b0: '?4e84b0',
    0x4ebca0: '?4ebca0', 0x4ebd60: 'rand%n', 0x4ebd30: 'rand',
    0x448f10: '?448f10', 0x4491a0: '?4491a0', 0x44dc60: '?44dc60', 0x49b280: '?49b280',
    0x49b2b0: '?49b2b0', 0x4a0d50: '?4a0d50', 0x44cc90: '?44cc90', 0x44ccf0: '?44ccf0',
    0x44e350: '?44e350', 0x44e5c0: '?44e5c0', 0x49c2b0: '?49c2b0', 0x49f5e0: '?49f5e0',
    0x4a07f0: '?4a07f0', 0x49a9a0: '?49a9a0', 0x49a9e0: '?49a9e0', 0x49aac0: '?49aac0',
    0x49ac00: '?49ac00', 0x49f9b0: '?49f9b0', 0x4a32c0: '?4a32c0', 0x49ac90: '?49ac90',
    0x49bf90: '?49bf90', 0x49f430: '?49f430', 0x49f7a0: '?49f7a0', 0x4b46c0: '?4b46c0',
    0x4b49f0: '?4b49f0', 0x4b4a90: '?4b4a90', 0x4e7f60: '?4e7f60', 0x4e84f0: '?4e84f0',
}

def off(va): return va - BASE

def disasm_fn(va, max_bytes=0x800):
    cur = va
    end = va + max_bytes
    out = []
    while cur < end:
        chunk = MEM[off(cur):off(end)]
        got = list(md.disasm(chunk, cur))
        if not got:
            cur += 1
            continue
        for ins in got:
            if ins.address >= end:
                break
            out.append(ins)
        last = out[-1]
        nxt = last.address + last.size
        if nxt <= cur:
            cur += 1
        else:
            cur = nxt
    return out

if __name__ == '__main__':
    va = int(sys.argv[1], 16)
    maxb = int(sys.argv[2], 16) if len(sys.argv) > 2 else 0x800
    for ins in disasm_fn(va, maxb):
        s = f"{ins.address:08x}  {ins.bytes.hex():18s} {ins.mnemonic} {ins.op_str}"
        if ins.address in SYM:
            s += f"   ; << {SYM[ins.address]}"
        print(s)
