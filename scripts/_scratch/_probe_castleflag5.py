
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

a = bytes([0x38,0x16,0x51,0x00])   # 0x516638 LE
occ = []
s = 0
while True:
    i = MEM.find(a, s)
    if i < 0: break
    occ.append(BASE + i)
    s = i + 1

# classify by the 1-2 bytes immediately before the address
from collections import Counter
pre = Counter()
for va in occ:
    off = off_of(va)
    prebyte = MEM[off-1]
    pre2 = MEM[off-2:off]
    pre[pre2.hex()] += 1

with open(_ROOT + '/scripts/_castleflag_occ.txt', "w", encoding="utf-8") as f:
    f.write(f"=== 0x516638 (LE 38 16 51 00) 出现 {len(occ)} 次；前缀 2 字节分布 ===\n")
    for k,v in pre.most_common():
        f.write(f"  {k} : {v}\n")
    f.write("\n--- 写入候选（前缀为 88/89/8a/8b mov r/m8,r8 | a2/a3 | c6/c7 | 80/81/83 or/and）---\n")
    writers = []
    for va in occ:
        off = off_of(va)
        pb = MEM[off-2:off]  # 2 bytes before addr
        # a2/a3: 1 byte before
        b1 = MEM[off-1]
        b2 = MEM[off-2]
        is_store = False
        reason = ""
        if b1 in (0xa2, 0xa3):
            is_store = True; reason = "a2/a3"
        elif b2 == 0xc6 or b2 == 0xc7:
            is_store = True; reason = "c6/c7"
        elif b2 in (0x88,0x89,0x8a,0x8b):
            is_store = True; reason = "88-8b"
        elif b2 == 0x80 or b2 == 0x81 or b2 == 0x83:
            is_store = True; reason = "80/81/83"
        if is_store:
            writers.append((va, reason))
            f.write(f"{va:08x}  {reason}\n")

print(f"[OK ] occ={len(occ)}, writers={len(writers)}")
