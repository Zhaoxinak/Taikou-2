# -*- coding: utf-8 -*-
"""E8 direct-caller scan for the overall-AI decision functions."""
import sys
from capstone import *
from capstone.x86 import *

IMG = r"F:/Games/Taikou 2/scripts/_unpacked_mem.bin"
BASE = 0x400000
md = Cs(CS_ARCH_X86, CS_MODE_32)

with open(IMG, 'rb') as f:
    data = f.read()

TARGETS = {
    "ai_top_tick_4a0d50": 0x4a0d50,
    "ai_think_4a6ba0":    0x4a6ba0,
    "prov_dispatch_4a70b0": 0x4a70b0,
    "ai_diplo_4a84e0":    0x4a84e0,
    "ai_assign_gov_4a8250": 0x4a8250,
    "ai_attack_4a8870":   0x4a8870,
    "ai_develop_4a8e80":  0x4a8e80,
    "ai_transfer_4a97d0": 0x4a97d0,
    "ai_reinforce_4a92c0": 0x4a92c0,
    "ai_recruit_4a94e0":  0x4a94e0,
}

def count_callers(target):
    n = 0
    callers = []
    i = 0
    N = len(data)
    while i < N - 5:
        if data[i] == 0xE8:
            imm = int.from_bytes(data[i+1:i+5], 'little', signed=True)
            tgt = (BASE + i + 5 + imm) & 0xffffffff
            if tgt == target:
                n += 1
                callers.append(BASE + i)
        i += 1
    return n, callers

for name, va in TARGETS.items():
    n, callers = count_callers(va)
    # restrict to callers inside the AI region for clarity
    print(f"{name} (0x{va:x}): {n} direct E8 caller(s)")
    # show up to 6 caller sites
    shown = callers[:6]
    for c in shown:
        print(f"    call @0x{c:x}")
