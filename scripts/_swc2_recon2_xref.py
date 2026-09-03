# 续242 recon2: xref call sites of target helpers + read accessors of [0x52063c]+0x07
import os, sys
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

MEM = open(os.path.join(_ROOT, 'scripts', '_unpacked_mem.bin'), 'rb').read()
BASE = 0x400000
md = Cs(CS_ARCH_X86, CS_MODE_32)
md.skipdata = True

targets = {0x44e110: 'find_tea_item', 0x44e540: 'capital_add_wrap', 0x44e560: 'capital_spend', 0x4a3630: 'sat_add_cap100', 0x49bfb0: 'set_b07', 0x460890: 'fac_entry?', 0x461da0: 'npc_init?'}
calls = {t: [] for t in targets}
byte07_reads = []
byte07_writes = []

for ins in md.disasm(MEM, BASE):
    try:
        if ins.mnemonic == 'call' and ins.op_str.startswith('0x'):
            t = int(ins.op_str, 16)
            if t in calls:
                calls[t].append(ins.address)
        # byte [reg+7] patterns
        if ins.mnemonic in ('mov', 'movzx', 'cmp') and 'byte ptr [' in ins.op_str and '+ 7]' in ins.op_str:
            byte07_reads.append((ins.address, ins.mnemonic, ins.op_str))
    except Exception:
        continue

for t, name in targets.items():
    print(f"callers of 0x{t:06x} ({name}): {len(calls[t])}")
    for a in calls[t][:40]:
        print(f"   0x{a:06x}")
print()
print(f"byte[reg+7] mov/cmp sites: {len(byte07_reads)}")
