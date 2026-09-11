# -*- coding: utf-8 -*-
"""Scan _unpacked_mem.bin for entity +0x1c..+0x20 accessors via Capstone."""
from capstone import Cs, CS_ARCH_X86, CS_MODE_32
import struct, collections, os

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPTS = os.path.dirname(HERE)
ROOT = os.path.dirname(SCRIPTS)
BASE = 0x400000
mem = open(os.path.join(SCRIPTS, "_unpacked_mem.bin"), "rb").read()
md = Cs(CS_ARCH_X86, CS_MODE_32)
md.detail = True

def scan_range(start, end, label):
    code = mem[start - BASE:end - BASE]
    hits = collections.defaultdict(list)
    for ins in md.disasm(code, start):
        ops = getattr(ins, "operands", None)
        # fallback: parse op_str for [reg + 0x1c] style
        s = ins.op_str
        for d in range(0x1c, 0x21):
            patterns = [
                f"+ {d:#x}",
                f"+{d:#x}",
                f"+ {d}",
                f"+{d}",
            ]
            # also 0x1c without +
            if any(p in s and "[" in s for p in patterns):
                # filter false positives like +0x1c0
                ok = False
                for p in patterns:
                    idx = s.find(p)
                    while idx >= 0:
                        after = s[idx + len(p):idx + len(p) + 1]
                        if after in ("", "]", ",", " ") or after.isspace():
                            ok = True
                            break
                        idx = s.find(p, idx + 1)
                    if ok:
                        break
                if ok:
                    hits[d].append((ins.address, ins.mnemonic, ins.op_str))
    print(f"\n===== {label} {start:#x}..{end:#x} =====")
    for d in range(0x1c, 0x21):
        print(f"\n--- +{d:#x} ({len(hits[d])} hits) ---")
        for a, m, o in hits[d][:50]:
            print(f"  {a:#x}: {m:8} {o}")
    return hits

# 1) setter library
hits_set = scan_range(0x49a000, 0x49b400, "setter lib")

# 2) find function entries: walk back to previous ret / alignment
print("\n===== function entries (setter lib) =====")
for d in range(0x1c, 0x21):
    seen = set()
    for a, m, o in hits_set[d]:
        entry = None
        for back in range(0, 0x60):
            va = a - back
            off = va - BASE
            if off < 1:
                break
            prev = mem[off - 1]
            # aligned after ret/int3
            if (va & 0xF) == 0 and prev in (0xC3, 0xCC):
                entry = va
                break
            if prev == 0xC2 and (va & 0xF) == 0:  # ret imm16 ends just before
                entry = va
                break
        key = (entry, a)
        if key in seen:
            continue
        seen.add(key)
        print(f"  +{d:#x} entry={entry:#x if entry else 0} access={a:#x}: {m} {o}")

# 3) Disassemble known setters fully
KNOWN = [
    0x49AB80, 0x49ABA0, 0x49ABC0, 0x49ABE0,  # +0x1c bits
    0x49AC00, 0x49AC30,  # +0x1d/+0x1e
    0x49A650, 0x49A670, 0x49A690, 0x49A6B0,  # around stamina
    0x49A5E0, 0x49A600, 0x49A620, 0x49A640,
]
print("\n===== known/nearby setter disasm =====")
for ea in KNOWN:
    print(f"\n--- {ea:#x} ---")
    code = mem[ea - BASE:ea - BASE + 0x40]
    for ins in md.disasm(code, ea):
        print(f"  {ins.address:#x}: {ins.mnemonic:8} {ins.op_str}")
        if ins.mnemonic.startswith("ret"):
            break

# 4) Broad binary scan for opcode patterns writing these offsets
# mov [reg+0x1c], al/imm  etc — look for displacement bytes
print("\n===== raw displacement xref counts (whole image, approximate) =====")
# x86: 88 41 1c = mov [ecx+0x1c], al ; 80 49 1c xx = or [ecx+0x1c], imm
# C6 41 1c xx = mov [ecx+0x1c], imm8
patterns = {
    "mov [ecx+d],al": bytes([0x88, 0x41]),
    "mov [ecx+d],imm8": bytes([0xC6, 0x41]),
    "or  [ecx+d],imm8": bytes([0x80, 0x49]),
    "and [ecx+d],imm8": bytes([0x80, 0x61]),
    "movzx eax,[ecx+d]": bytes([0x0F, 0xB6, 0x41]),
    "mov al,[ecx+d]": bytes([0x8A, 0x41]),
    "cmp [ecx+d],imm8": bytes([0x80, 0x79]),
    "test [ecx+d],imm8": bytes([0xF6, 0x41]),
}
for d in range(0x1c, 0x21):
    print(f"\n  offset +{d:#x}:")
    for name, pref in patterns.items():
        count = 0
        addrs = []
        needle = pref + bytes([d])
        start = 0
        while True:
            i = mem.find(needle, start)
            if i < 0:
                break
            va = BASE + i
            # filter to code-ish range
            if 0x401000 <= va <= 0x4F0000:
                count += 1
                if len(addrs) < 12:
                    addrs.append(va)
            start = i + 1
        print(f"    {name}: {count}  e.g. {[hex(a) for a in addrs]}")
PY