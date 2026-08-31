import struct, collections
from capstone import *

MEM_PATH = "F:/Games/Taikou 2/scripts/_unpacked_mem.bin"
BASE = 0x400000

with open(MEM_PATH, "rb") as f:
    MEM = f.read()
SIZE = len(MEM)
print(f"image size = {SIZE} ({SIZE/1024/1024:.2f} MB), BASE={BASE:#x}")

md = Cs(CS_ARCH_X86, CS_MODE_32)
md.detail = True

def disasm_window(center_va, before=0x28, after=0x48):
    off = center_va - BASE
    start = max(0, off - before)
    end = min(SIZE, off + after)
    out = []
    for ins in md.disasm(MEM[start:end], start + BASE):
        mark = " >>>" if ins.address == center_va else "    "
        out.append(f"{mark} {ins.address:#010x}: {ins.mnemonic} {ins.op_str}")
    return "\n".join(out)

def dword_scan(target):
    b = struct.pack("<I", target)
    res = []
    start = 0
    while True:
        i = MEM.find(b, start)
        if i < 0:
            break
        res.append(i)
        start = i + 1
    return res

# Correct writer addresses (from probe_ai7) vs the ones probe_ai9 actually searched
CORRECT = {
    0x469480: "writer_0(?)",
    0x4694aa: "writer_1(?)",
    0x46950c: "writer_2(?)",
    0x469547: "writer_3(?)",
}
WRONG = {
    0x469480: "w0",
    0x4694a0: "w1(WRONG)",
    0x4694e0: "w2(WRONG)",
    0x469530: "w3(WRONG)",
}

for title, targs in [("CORRECT writer addresses", CORRECT),
                     ("probe_ai9 WRONG addresses", WRONG)]:
    print("\n" + "=" * 72)
    print(title)
    print("=" * 72)
    any_hit = False
    for t, name in targs.items():
        offs = dword_scan(t)
        if not offs:
            print(f"\n  {name} {t:#010x}: 0 dword refs")
            continue
        any_hit = True
        print(f"\n  {name} {t:#010x}: {len(offs)} dword refs")
        for o in offs[:50]:
            va = o + BASE
            print(f"\n    ref @ {va:#010x} (off {o}):")
            print(disasm_window(va))
    if not any_hit:
        print("   (none of these addresses appear as dwords anywhere)")
