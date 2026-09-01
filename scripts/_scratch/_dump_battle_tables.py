
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
import struct, sys

BIN = _ROOT + '/scripts/_unpacked_mem.bin'
BASE = 0x400000
data = open(BIN, "rb").read()

def at(va):
    return va - BASE

def hexdump(b, wid=16):
    out = []
    for i in range(0, len(b), wid):
        chunk = b[i:i+wid]
        hexs = " ".join(f"{x:02x}" for x in chunk)
        asc = "".join(chr(x) if 0x20 <= x < 0x7e else "." for x in chunk)
        out.append(f"{i:04x}  {hexs:<{wid*3}}  {asc}")
    return "\n".join(out)

# ---- 0x517720 : 96-byte records ----
print("="*70)
print("0x517720 : 96-byte record table (dump 96*24 = 2304 bytes)")
print("="*70)
off = at(0x517720)
recs = data[off:off+96*24]
# print first 3 records in full hex, then a compact u8/u16 view of all
for r in range(3):
    print(f"\n--- record {r} (offset {r*96}) ---")
    print(hexdump(recs[r*96:r*96+96], 16))
print("\n--- compact numeric view (u8 x96) for records 0..11 ---")
for r in range(12):
    rb = recs[r*96:r*96+96]
    u8 = list(rb)
    u16 = struct.unpack("<48H", rb[:96])
    print(f"r{r:2d} u8 : {u8}")
    print(f"     u16: {list(u16)}")

# ---- 0x503700 .. 0x503800 ----
print("\n"+"="*70)
print("0x503700 .. 0x503800 (resource ptr + parallel word tables + tier tables)")
print("="*70)
off2 = at(0x503700)
blk = data[off2:off2+0x100]
print(hexdump(blk, 16))
# interpret as u32 ptr at 0x503700
print("\n@0x503700 u32 (likely ptr):", hex(struct.unpack_from("<I", blk, 0)[0]), "-> VA", hex(struct.unpack_from("<I", blk, 0)[0]))
print("@0x503704 u32:", hex(struct.unpack_from("<I", blk, 4)[0]))
# parallel word tables at +0x10 (0x503710) and +0x12 (0x503712), stride 4
print("\n0x503710 parallel word table (idx*4+0 and idx*4+2), 12 entries:")
for i in range(12):
    w0 = struct.unpack_from("<H", blk, 0x10 + i*4)[0]
    w2 = struct.unpack_from("<H", blk, 0x12 + i*4)[0]
    print(f"  i={i:2d}: +0={w0:5d}  +2={w2:5d}")
# 10-entry tier tables at +0x40 (0x503740), +0x50 (0x503750), +0x60 (0x503760)
for name,o in [("0x503740",0x40),("0x503750",0x50),("0x503760",0x60)]:
    arr = list(blk[o:o+10])
    print(f"{name} (10 u8): {arr}")
