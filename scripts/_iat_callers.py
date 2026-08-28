#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Map file-I/O imports -> IAT slots -> caller functions.
INT is wiped (OFT=0) but descriptors + IAT (FT) + by-name region are intact.
We recover per-DLL import counts from each IAT, split the global by-name
region by descriptor array order, then map name->IAT slot VA and find
`call [slot]` / `jmp [slot]` callers.
"""
import struct

MEM = open("_unpacked_mem.bin", "rb").read()
BASE = 0x400000

# 1. find all ".DLL" name strings -> their RVA -> descriptor (Name field at +12)
dll_names = {}
i = 0
while True:
    k = MEM.find(b".DLL", i)
    if k < 0:
        break
    # walk back over [A-Za-z0-9] to capture full DLL name (e.g. KERNEL32)
    s = k
    while s > 0 and (48 <= MEM[s - 1] <= 57 or 65 <= MEM[s - 1] <= 90 or 97 <= MEM[s - 1] <= 122):
        s -= 1
    nm = MEM[s:k + 4].decode("latin1", "replace")
    dll_names[nm] = BASE + s
    i = k + 4

descs = []  # (desc_va, dll_name, ft_rva)
for nm, vas in dll_names.items():
    rva = vas[0] - BASE
    t = struct.pack("<I", rva)
    idx = 0
    while True:
        k = MEM.find(t, idx)
        if k < 0:
            break
        desc = BASE + k - 12  # Name field at desc+12
        oft, ts, fc, dnm, ft = struct.unpack_from("<IIIII", MEM, desc - BASE)
        if dnm == rva:
            descs.append((desc, nm, ft))
            break
        idx = k + 1

# order descriptors by their VA (array order)
descs.sort(key=lambda x: x[0])
print("Descriptors (%d):" % len(descs))
for desc, nm, ft in descs:
    print("  %s  desc=%08x IAT=%08x" % (nm, desc, BASE + ft))

# 2. count imports per DLL from its IAT (until null dword)
def iat_count(ft_rva):
    n = 0
    while struct.unpack_from("<I", MEM, (BASE + ft_rva) - BASE + n * 4)[0] != 0:
        n += 1
    return n

# 3. parse global by-name region sequentially (1-byte hint + name)
def parse_bynames(start, count):
    out = []
    p = start
    for _ in range(count):
        j = p + 1
        while MEM[j - BASE] != 0:
            j += 1
        out.append(MEM[p + 1 - BASE:j - BASE].decode("latin1", "replace"))
        p = j + 1
    return out

# 4. assign by-name entries to DLLs in descriptor order
name2slot = {}
g = 0  # global by-name pointer
BN_REGION = 0x530008
total = 0
for desc, nm, ft in descs:
    c = iat_count(ft)
    sub = parse_bynames(BN_REGION + g, c) if c > 0 else []
    for j, name in enumerate(sub):
        slot = BASE + ft + j * 4
        name2slot[name] = slot
    g += c
    total += c

print("Total imports mapped:", total, " unique names:", len(name2slot))

def callers_of_slot(slot_va):
    out = []
    t = struct.pack("<I", slot_va & 0xFFFFFFFF)
    for pat in (b"\xff\x15", b"\xff\x25"):
        tgt = pat + t
        k = 0
        while True:
            k = MEM.find(tgt, k)
            if k < 0:
                break
            out.append(BASE + k)
            k += 1
    return out

def fn_start(va):
    p = va
    while p > BASE and va - p < 0x3000:
        b = MEM[p - BASE:p - BASE + 3]
        if b[:2] == b"\x55\x8b" or b[:2] == b"\x55\x89":
            return p
        if b[0] == 0x83 and b[1] == 0xec:
            return p
        if b[:2] == b"\x8b\xff":
            return p
        p -= 1
    return va - 0x3000

TARGETS = ["_lread", "OpenFile", "_lclose", "_llseek", "GlobalAlloc",
           "GlobalLock", "GlobalUnlock", "GlobalFree", "GetCurrentDirectoryA",
           "GetDriveTypeA", "WriteFile", "ReadFile"]
print("\n=== file-I/O import callers ===")
for t in TARGETS:
    if t not in name2slot:
        print("%-20s : name not mapped (present names sample: %s)" % (t, list(name2slot)[:5]))
        continue
    slot = name2slot[t]
    cs = callers_of_slot(slot)
    fns = sorted(set(fn_start(c) for c in cs))
    print("%-20s IATslot=%08x callsites=%3d callers=%s"
          % (t, slot, len(cs), [hex(f) for f in fns[:8]]))
    if cs:
        print("      calls:", [hex(c) for c in cs[:20]])
