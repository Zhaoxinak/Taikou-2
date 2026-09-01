
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
MEM = open(_ROOT + '/scripts/_unpacked_mem.bin', "rb").read()
BASE = 0x400000

def find_pat(pat):
    hits = []
    start = 0
    while True:
        i = MEM.find(pat, start)
        if i < 0:
            break
        hits.append(BASE + i)
        start = i + 1
    return hits

addr = 0x516638
a = addr.to_bytes(4, "little")

# set bit2: or byte[0x516638], 4  -> 80 0d <addr> 04
set_hits = find_pat(b'\x80\x0d' + a + b'\x04')
# clear bit2: and byte[0x516638], 0xfb -> 80 25 <addr> fb
clr_hits = find_pat(b'\x80\x25' + a + b'\xfb')
# any 'or byte[addr], imm8' (capture imm)
ors = []
for imm in range(0x100):
    for va in find_pat(b'\x80\x0d' + a + bytes([imm])):
        ors.append((va, imm))
# mov byte[addr], imm8
movs = []
for imm in range(0x100):
    for va in find_pat(b'\xc6\x05' + a + bytes([imm])):
        movs.append((va, imm))

with open(_ROOT + '/scripts/_castleflag_set.txt', "w", encoding="utf-8") as f:
    f.write(f"=== 0x516638 城主flag 写入 ===\n")
    f.write(f"or byte[..],4 (set 城主): {len(set_hits)} -> {[f'{x:08x}' for x in set_hits]}\n")
    f.write(f"and byte[..],0xfb (clear 城主): {len(clr_hits)} -> {[f'{x:08x}' for x in clr_hits]}\n")
    f.write(f"or byte[..],imm: {len(ors)} -> {[(f'{v:08x}',h) for v,h in ors]}\n")
    f.write(f"mov byte[..],imm: {len(movs)} -> {[(f'{v:08x}',h) for v,h in movs]}\n")

print(f"set4={set_hits}  clr_fb={clr_hits}  or_imm={len(ors)}  mov_imm={len(movs)}")
