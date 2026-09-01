
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
import struct

BIN = _ROOT + '/scripts/_unpacked_mem.bin'
BASE = 0x400000
data = open(BIN, "rb").read()

# battle-specific buffer addresses to hunt for (absolute immediates)
targets = {
    0x512e58: "battle buf A (180B, A-head)",
    0x512868: "battle buf B (760B, terrain)",
    0x512b60: "battle buf C (760B, deploy)",
    0x524978: "decoded battle image/buffer",
    0x522ce4: "92-castle 1B array",
    0x522c88: "scenario state buf",
    0x517720: "96B runtime record buf",
    0x503700: "HKMAPNEW.LZW filename",
    0x4fb0a8: "vtable ptr (battle?)",
}

# also scan for relative call targets into known battle funcs
call_targets = {
    0x43a400: "battle variant loader fn",
    0x43a580: "battle tile/terrain builder fn",
    0x43e820: "terrain generator fn",
    0x438fa0: "deploy decryptor A",
    0x438fc0: "deploy decryptor B",
    0x4390c0: "high-nibble accessor",
}

hits = {}
for t, label in targets.items():
    pat = struct.pack("<I", t)
    hs = [BASE + i for i in range(0, len(data)-3) if data[i:i+4] == pat]
    if hs:
        hits[t] = (label, hs)

print("=== absolute-addr xrefs (battle buffers) ===")
for t, (label, hs) in hits.items():
    print(f"\n0x{t:06x} {label}: {len(hs)} hits")
    for h in hs[:30]:
        print(f"   VA 0x{h:06x}")

print("\n=== relative call targets into battle funcs ===")
for t, label in call_targets.items():
    # E8 rel32 => target = addr+5+rel
    pat = b"\xe8" + struct.pack("<i", (t - (0)) & 0)  # placeholder
    # brute: scan for E8 then compute
    hs = []
    i = 0
    while i < len(data)-5:
        if data[i] == 0xe8:
            rel = struct.unpack("<i", data[i+1:i+5])[0]
            tgt = (BASE + i + 5 + rel)
            if tgt == t:
                hs.append(BASE + i)
        i += 1
    if hs:
        print(f"\ncall 0x{t:06x} {label}: {len(hs)} callers")
        for h in hs[:20]:
            print(f"   call @ VA 0x{h:06x}")
