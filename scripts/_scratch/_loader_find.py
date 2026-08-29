"""Find the castle-table loader: a function that writes many distinct field
offsets into 0x51eb88 in a loop (populates the 200-entry table)."""
import collections
from capstone import Cs, CS_ARCH_X86, CS_MODE_32
from capstone.x86 import (X86_REG_EAX, X86_REG_EBX, X86_REG_ECX, X86_REG_EDX,
                          X86_REG_ESI, X86_REG_EDI, X86_REG_EBP)

MEM = open('_unpacked_mem.bin','rb').read()
BASE = 0x400000; SZ = len(MEM)
md = Cs(CS_ARCH_X86, CS_MODE_32); md.detail = True
TARGET = 0x51eb88; STRIDE = 31
REGN = {X86_REG_EAX:'eax',X86_REG_EBX:'ebx',X86_REG_ECX:'ecx',X86_REG_EDX:'edx',
        X86_REG_ESI:'esi',X86_REG_EDI:'edi',X86_REG_EBP:'ebp'}

# Pass 1: base loads
loads = []
addr = BASE
while addr < BASE + SZ:
    try: ins = next(md.disasm(MEM[addr-BASE:addr-BASE+16], addr))
    except Exception: addr += 1; continue
    s = ins.mnemonic+' '+ins.op_str
    if '0x%x'%TARGET in s and ins.mnemonic in ('add','mov','lea') and len(ins.operands)==2:
        d = ins.operands[0]
        if d.type==1 and REGN.get(d.reg): loads.append((addr, REGN[d.reg]))
    addr = ins.address + ins.size

def analyze(va, dst):
    anchored = {dst}
    writes = collections.Counter()      # disp -> count (write)
    reads = collections.Counter()
    loopmax = 0
    end = min(va+2000, BASE+SZ-16)
    try: rows = list(md.disasm(MEM[va-BASE:end-BASE], va))
    except: return None
    for ins in rows:
        s = ins.mnemonic+' '+ins.op_str
        if ins.mnemonic in ('add','mov','lea') and '0x%x'%TARGET in s and len(ins.operands)==2:
            d = ins.operands[0]
            if d.type==1 and REGN.get(d.reg): anchored.add(REGN[d.reg])
        for o in ins.operands:
            if o.type==3 and REGN.get(o.mem.base) in anchored:
                disp = o.mem.disp
                if 0 <= disp <= STRIDE+3:
                    w = 4
                    if 'byte ' in s: w=1
                    elif 'word ' in s: w=2
                    # is it a write? dst mem operand
                    is_write = (ins.operands[0].type==3)
                    if is_write: writes[disp]+=1
                    else: reads[disp]+=1
        if ins.mnemonic=='cmp' and len(ins.operands)==2:
            for o in ins.operands:
                if o.type==2 and o.imm>0 and o.imm<0x1000:
                    loopmax = max(loopmax, o.imm)
    return (len(writes), len(set(writes)), len(reads), loopmax, va)

results = []
for va,dst in loads:
    r = analyze(va,dst)
    if r and r[1] >= 4:   # writes to >=4 distinct offsets => candidate loader/updater
        results.append(r)

results.sort(key=lambda x:(-x[1], -x[0]))
print("=== candidate castle-table writers (distinct-write-offsets desc) ===")
for nw, nd, nr, lm, va in results[:25]:
    print("  @%08x  distinct_writes=%2d total_writes=%3d reads=%3d loopmax=%d" % (va, nd, nw, nr, lm))
