#!/usr/bin/env python3
# 续233: resolve 伪兵 0x43a440 造兵数 — static table @0x503712, 29 callers.
# Goal: find which caller is 伪兵 (feint) and what index it passes, so we can
# give the table a semantic layout (which entry = feint dummy-soldier count).
import struct, sys
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

BASE = 0x400000
MEM = open("/Users/ts/Downloads/Taikou 2/scripts/_unpacked_mem.bin", "rb").read()
def va2off(va): return va - BASE
def read(va, n): return MEM[va2off(va):va2off(va)+n]

TARGET = 0x43a440
CALLERS = [0x427779, 0x428342, 0x4284b8, 0x428780, 0x428b28, 0x428c6a, 0x428db3,
           0x42922d, 0x429a28, 0x429ba1, 0x42c25c, 0x42c2c3, 0x43568c, 0x436f0a,
           0x43a797, 0x43a8cc, 0x43a95d, 0x43ab92, 0x43ad11, 0x43ae1a, 0x43b1a5,
           0x43bb01, 0x43bdfa, 0x43c076, 0x43c381, 0x43c49e, 0x43c655, 0x43c74a, 0x43d5a8]

md = Cs(CS_ARCH_X86, CS_MODE_32)
md.detail = True

# ---- dump table @0x503712 (64 words) ----
print("=== table @0x503712 (idx : value) ===")
tbl = read(0x503712, 64*2)
words = struct.unpack("<64H", tbl)
for i in range(0, 64, 4):
    print("  ", i, words[i], " ", i+1, words[i+1], " ", i+2, words[i+2], " ", i+3, words[i+3])

# ---- for each caller, disassemble window BEFORE the call to find pushed arg ----
print("\n=== caller arg probes ===")
for cva in CALLERS:
    start = cva - 60
    end   = cva + 6
    code = read(start, end - start)
    arg_imm = None      # immediate pushed
    arg_reg = None      # register pushed
    found_call = False
    for ins in md.disasm(code, start):
        if ins.address == cva:
            found_call = True
            continue
        if ins.address < cva:
            # look for push immediately before call; capture last one seen
            if ins.mnemonic == 'push':
                op = ins.op_str
                if op.startswith('0x') or op.isdigit():
                    try:
                        arg_imm = int(op, 16) if op.startswith('0x') else int(op)
                        arg_reg = None
                    except: pass
                else:
                    arg_reg = op
                    arg_imm = None
    tag = ""
    if arg_imm is not None:
        tag = "push imm 0x%x = %d" % (arg_imm & 0xffff, arg_imm & 0xffff)
    elif arg_reg is not None:
        tag = "push reg %s" % arg_reg
    else:
        tag = "?? (no push found before call)"
    print("  0x%06x -> %s" % (cva, tag))
