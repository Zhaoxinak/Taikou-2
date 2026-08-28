#!/usr/bin/env python3
"""Generic VA-range disassembler for the unpacked TAIK2 image.
Base VA = 0x400000 (flat unpacked mem dump). capstone 32-bit.
Usage: python _disasm_va.py START_VA END_VA [BIN]
Annotates: writes to 0x52xxxx globals, calls to XOR-stream primitives
(0x47da10 read1B / 0x47da50 read2B / 0x47da80 write1B / 0x47dac0 write2B).
"""
import sys
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

BIN = r"F:/Games/Taikou 2/scripts/_unpacked_mem.bin"
BASE = 0x400000

PRIM = {
    0x47da10: "READ1B",
    0x47da50: "READ2B",
    0x47da80: "WRITE1B",
    0x47dac0: "WRITE2B",
}

def main():
    if len(sys.argv) < 3:
        print("usage: _disasm_va.py START END [BIN]")
        return
    start = int(sys.argv[1], 0)
    end = int(sys.argv[2], 0)
    if len(sys.argv) > 3:
        binpath = sys.argv[3]
    else:
        binpath = BIN
    data = open(binpath, "rb").read()
    off0 = start - BASE
    code = data[off0:off0 + (end - start)]
    md = Cs(CS_ARCH_X86, CS_MODE_32)
    md.detail = True
    for ins in md.disasm(code, start):
        if ins.address >= end:
            break
        line = f"{ins.address:#010x}  {ins.mnemonic} {ins.op_str}"
        note = ""
        # detect call to XOR primitive
        if ins.mnemonic == "call" and ins.op_str.startswith("0x"):
            t = int(ins.op_str, 16)
            if t in PRIM:
                note = f"   ;; {PRIM[t]}"
        # detect global write 0x52xxxx
        for op in getattr(ins, "operands", []) or []:
            if op.type == 3:  # memory
                d = op.mem.disp
                if 0x520000 <= d <= 0x520fff:
                    note = (note + f"   ;; GLOBAL[{d:#x}]").strip()
        print(line + note)

if __name__ == "__main__":
    main()
