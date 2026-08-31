from capstone import *

MEM_PATH = "F:/Games/Taikou 2/scripts/_unpacked_mem.bin"
BASE = 0x400000
with open(MEM_PATH, "rb") as f:
    MEM = f.read()
SIZE = len(MEM)

md = Cs(CS_ARCH_X86, CS_MODE_32)
md.detail = True

# Candidate entry points of the 4 action-writer functions
WRITERS = {0x469480, 0x4694a0, 0x4694e0, 0x469530,
           0x46947a, 0x4694aa, 0x46950c, 0x469547}

CFLOW = {"call","jmp","je","jne","jb","jbe","ja","jae","jg","jge","jl","jle",
         "js","jns","jo","jno","jp","jnp","jcxz","jecxz","loop","loope","loopne"}

import re
_HEX = re.compile(r"^0x([0-9a-fA-F]+)$")
def get_imm_target(ins):
    m = _HEX.match(ins.op_str.strip())
    if m:
        return int(m.group(1), 16) & 0xffffffff
    return None

# 1) Scan duel module 0x466000-0x46c000 for control flow targeting a writer
print("="*72)
print("Control-flow instructions targeting the 4 writer entries (0x466000-0x46c000)")
print("="*72)
hits = []
for ins in md.disasm(MEM[0x66000:0x6c000], 0x466000):
    if ins.mnemonic in CFLOW:
        t = get_imm_target(ins)
        if t in WRITERS:
            hits.append(ins)
            print(f"  {ins.address:#010x}: {ins.mnemonic} {ins.op_str}   -> targets writer {t:#010x}")

if not hits:
    print("  (none found in duel module)")

# 2) Find callers of special-submenu callback 0x468250 and main-menu cb 0x4682f0
print("\n" + "="*72)
print("e8 callers of 0x468250 (special submenu) and 0x4682f0 (main menu)")
print("="*72)
import struct
for target in (0x468250, 0x4682f0):
    b = struct.pack("<I", (target - 0x400000 - 5) & 0xffffffff)
    # e8 rel32 = target - (callsite+5); the 4-byte rel stored = target - callsite - 5
    found = []
    start = 0
    while True:
        i = MEM.find(b, start)
        if i < 0:
            break
        callsite = i + BASE
        # verify it's an e8 at i-1
        if MEM[i-1] == 0xe8:
            found.append(callsite)
        start = i + 1
    print(f"\n  callers of {target:#010x}: {found}")
    for c in found:
        print(f"    called from {c:#010x}")
