"""Find callers of each flag getter and show how the returned value is consumed."""
import struct
from capstone import Cs, CS_ARCH_X86, CS_MODE_32
BASE = 0x400000
BIN = "F:/Games/Taikou 2/scripts/_unpacked_mem.bin"
data = open(BIN, "rb").read()
md = Cs(CS_ARCH_X86, CS_MODE_32); md.detail = True; md.skipdata = True

getters = {
    0x42c151: "mode_m1",
    0x43cb11: "mode_m2",
    0x43cab1: "parity",
}

def find_calls(tgt):
    res = []
    n = len(data) - 5
    for p in range(n):
        if data[p] == 0xE8:
            rel = struct.unpack_from("<i", data, p+1)[0]
            if (p + 5 + rel) + BASE == tgt:
                res.append(p + BASE)  # call instr VA
    return res

def ctx(call_va, n=0x60):
    start = call_va - 0x20
    code = data[start-BASE: call_va-BASE+0x60]
    out = []
    for ins in md.disasm(code, start):
        out.append((ins.address, ins.mnemonic, ins.op_str))
        if ins.address >= call_va + 0x40:
            break
    return out

for gva, name in getters.items():
    sites = find_calls(gva)
    print(f"\n##### getter {name} @ {gva:#x}  ({len(sites)} callers) #####")
    for c in sites[:6]:
        print(f"  -- caller calls at {c:#08x} --")
        for a, m, o in ctx(c):
            mark = "  <== GET" if a == c else ""
            print(f"     {a:#08x}  {m} {o}{mark}")
