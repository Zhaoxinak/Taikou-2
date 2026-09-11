# -*- coding: utf-8 -*-
"""Deeper scan: all regs, callers, getters for +0x1c..+0x20."""
from capstone import Cs, CS_ARCH_X86, CS_MODE_32
import struct, collections, os, re

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPTS = os.path.dirname(HERE)
BASE = 0x400000
mem = open(os.path.join(SCRIPTS, "_unpacked_mem.bin"), "rb").read()
md = Cs(CS_ARCH_X86, CS_MODE_32)

# ModR/M: [reg+disp8] with disp in 0x1c..0x20
# regs: eax=0 ecx=1 edx=2 ebx=3 esp=4 ebp=5 esi=6 edi=7
# for 8-bit disp: mod=01, rm=reg → byte = 0x40|rm  for [reg+disp] without SIB
# opcode prefixes vary

REGS = {0: "eax", 1: "ecx", 2: "edx", 3: "ebx", 5: "ebp", 6: "esi", 7: "edi"}

def find_disp8_ops(disp, label_ops):
    """Find instructions with [reg+disp8] for given disp across code."""
    hits = []
    # scan code range
    lo, hi = 0x1000, min(len(mem), 0xF0000)
    i = lo
    while i < hi - 6:
        # look for modrm with mod=01 and disp==target
        # common: XX YY DD where YY is modrm
        b0 = mem[i]
        # try 1-byte opcode
        for op_len in (1, 2):
            if i + op_len + 2 >= hi:
                continue
            modrm = mem[i + op_len]
            mod = (modrm >> 6) & 3
            rm = modrm & 7
            if mod != 1 or rm == 4:  # need disp8, no SIB for simplicity
                continue
            if mem[i + op_len + 1] != disp:
                continue
            if rm not in REGS:
                continue
            va = BASE + i
            # disasm from a bit earlier to sync? just disasm at va
            chunk = mem[i:i+16]
            ins = next(md.disasm(chunk, va), None)
            if not ins:
                continue
            if f"+ {disp:#x}" not in ins.op_str and f"+ {disp}" not in ins.op_str:
                # also accept +0x1c style from capstone
                if f"+ {disp:#x}" not in ins.op_str.replace("0x0", "0x"):
                    continue
            hits.append((va, ins.mnemonic, ins.op_str, REGS[rm]))
        i += 1
    return hits

# Faster: pattern scan for modrm+disp
def scan_disp(disp):
    hits = []
    lo, hi = 0x1000, min(len(mem), 0xF0000)
    i = lo
    while i < hi - 8:
        # any byte that could be modrm with mod=01, then disp
        modrm = mem[i]
        mod = (modrm >> 6) & 3
        rm = modrm & 7
        if mod == 1 and rm in REGS and mem[i+1] == disp:
            # try disasm starting at i-1 and i-2 and i
            found = False
            for back in (2, 1, 0, 3):
                start = i - back
                if start < lo:
                    continue
                ins = next(md.disasm(mem[start:start+16], BASE+start), None)
                if not ins:
                    continue
                # instruction should cover the modrm at i
                if ins.address <= BASE+i < ins.address + ins.size:
                    if f"+ {disp:#x}" in ins.op_str or (f"+ {disp}" in ins.op_str and f"+ {disp:#x}" not in ""):
                        # filter: op_str contains the displacement properly
                        if re.search(rf"\+ {disp:#x}\b", ins.op_str) or re.search(rf"\+ {disp}\b", ins.op_str):
                            hits.append((ins.address, ins.mnemonic, ins.op_str))
                            found = True
                            break
            if found:
                i += 2
                continue
        i += 1
    # dedupe
    seen = set()
    out = []
    for h in hits:
        if h[0] in seen:
            continue
        seen.add(h[0])
        out.append(h)
    return out

for d in range(0x1c, 0x21):
    print(f"\n========== +{d:#x} ALL ACCESSORS ==========")
    hs = scan_disp(d)
    print(f"count={len(hs)}")
    for a, m, o in hs[:80]:
        print(f"  {a:#x}: {m:8} {o}")
    if len(hs) > 80:
        print(f"  ... +{len(hs)-80} more")

# Count e8 calls to known setters
SETTERS = {
    0x49AB80: "+0x1c|=4",
    0x49ABA0: "+0x1c|=8",
    0x49ABC0: "+0x1c|=0x10",
    0x49ABE0: "+0x1c|=0x20",
    0x49AC00: "set +0x1d",
    0x49AC30: "set +0x1e",
    0x49A650: "set +0x20 clamp100",
    0x49A630: "get? +0x20",
    0x49A640: "set +0x21?",
}

def count_calls(target):
    c = 0
    addrs = []
    for off in range(0x1000, min(len(mem), 0xF0000) - 5):
        if mem[off] != 0xE8:
            continue
        rel = struct.unpack_from("<i", mem, off + 1)[0]
        if BASE + off + 5 + rel == target:
            c += 1
            if len(addrs) < 20:
                addrs.append(BASE + off)
    return c, addrs

print("\n========== CALLERS ==========")
for t, name in SETTERS.items():
    c, addrs = count_calls(t)
    print(f"\n{t:#x} ({name}): {c} calls")
    for a in addrs:
        print(f"  from {a:#x}")

# Disasm around 0x49a630-0x49a660 (stamina getters/setters)
print("\n========== stamina cluster 0x49a620..0x49a6a0 ==========")
code = mem[0x49a620 - BASE:0x49a6a0 - BASE]
for ins in md.disasm(code, 0x49a620):
    print(f"  {ins.address:#x}: {ins.mnemonic:8} {ins.op_str}")

# Look for +0x1f specifically - maybe word access to +0x1d covering +0x1e
print("\n========== word [reg+0x1d] accesses (covers 1d/1e) ==========")
# and word [ecx+0x1d] = 81 61 1d / 81 49 1d etc — already have setters
# movzx from [reg+0x1f]
hs1f = scan_disp(0x1f)
print("done 1f")

# Also check ebx/esi variants for +0x20 used in 体力恢复 formula 0x4453a0
print("\n========== disasm 0x4453a0 (体力恢复 gap formula) ==========")
code = mem[0x4453a0 - BASE:0x4453a0 - BASE + 0x80]
for ins in md.disasm(code, 0x4453a0):
    print(f"  {ins.address:#x}: {ins.mnemonic:8} {ins.op_str}")
    if ins.mnemonic == "ret" and ins.address > 0x4453c0:
        break
