
# <auto: portable root (injected by _fix_win_paths.py)>
import os as _os
def _find_root(_p):
    for _ in range(8):
        if _os.path.isdir(_os.path.join(_p, 'scripts')) and _os.path.isfile(_os.path.join(_p, 'project.godot')):
            return _p
        _p = _os.path.dirname(_p)
    return _p
_ROOT = _find_root(_os.path.dirname(_os.path.abspath(__file__)))
# </auto: portable root>
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

MEM = open(_ROOT + '/scripts/_unpacked_mem.bin', "rb").read()
BASE = 0x400000
def off_of(va): return va - BASE
md = Cs(CS_ARCH_X86, CS_MODE_32); md.detail = True

TARGET = 0x49a7e0

# 1) find all call sites of set_rank
calls = []
off = 0
while off < len(MEM) - 8:
    chunk = MEM[off:off+0x4000]
    for ins in md.disasm(chunk, BASE+off):
        if ins.mnemonic == "call" and ins.op_str.lower() == f"0x{TARGET:x}":
            calls.append(ins.address)
    off += 0x4000

def dis_back(va, n=0x100):
    start = va - n
    code = MEM[off_of(start):off_of(va)]
    return [f"{i.address:08x}  {i.mnemonic} {i.op_str}" for i in md.disasm(code, start)]

with open(_ROOT + '/scripts/_setrank_callers2.txt', "w", encoding="utf-8") as f:
    f.write(f"=== set_rank(0x49a7e0) callers: {len(calls)} ===\n\n")
    for ca in calls:
        bs = dis_back(ca)
        # find the rank push: the LAST 'push imm' before the call, or last mov of 7/8
        rank = None
        for ln in reversed(bs):
            a = ln.split("  ", 1)[1] if "  " in ln else ln
            if a.startswith("push "):
                rank = a
                break
        f.write(f"\n--- caller @ {ca:08x}  lastpush= {rank} ---\n")
        f.write("\n".join(bs[-20:]) + "\n")

# grep-style summary: callers whose last push is 7 or 8
import re
sev = []
for ca in calls:
    bs = dis_back(ca)
    for ln in reversed(bs):
        a = ln.split("  ", 1)[1] if "  " in ln else ln
        if a.startswith("push "):
            m = re.search(r"0x([0-9a-f]+)|(\b\d+\b)", a)
            if m:
                v = int(m.group(1) or m.group(2), 16 if m.group(1) else 10)
                if v in (7, 8):
                    sev.append((ca, a))
            break
with open(_ROOT + '/scripts/_setrank78.txt', "w", encoding="utf-8") as f:
    f.write(f"=== set_rank callers pushing rank 7/8 (大名/城主) : {len(sev)} ===\n")
    for ca, a in sev:
        f.write(f"{ca:08x}  {a}\n")

print(f"[OK ] total callers={len(calls)}, pushing 7/8: {len(sev)}")
