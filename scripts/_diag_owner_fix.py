import sys, os, json
ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)
from emu_harness import Emu, BIN
BASE = 0x400000
data = open(os.path.join(ROOT, "_unpacked_mem.bin"), "rb").read()
from capstone import Cs, CS_ARCH_X86, CS_MODE_32
from _disasm_all import disasm_all

def nop_start(va, limit=0x800):
    """向后扫描 >=2 连续 0x90 填充，取填充结束后的首个非 nop 字节作为函数起点。"""
    off = va - BASE
    i = off
    while i > off - limit and i >= 2:
        if data[i-1] == 0x90 and data[i-2] == 0x90 and data[i] != 0x90:
            return BASE + i
        i -= 1
    return None

def aligned(start, call_va):
    md = Cs(CS_ARCH_X86, CS_MODE_32); md.detail = False
    n = call_va - start + 8
    for ins in disasm_all(md, data[start-BASE:start-BASE+n], start):
        if ins.address == call_va: return True
        if ins.address > call_va: return False
    return False

fm = json.load(open(os.path.join(ROOT, "s15_segc_fullmap.json"), encoding="utf-8"))
print("call_va      fullmap_owner  nop_owner   ali(fm) ali(nop)  VERDICT")
bad = []
for e in fm["mapping"]:
    cv = int(e["set_c_call"], 16); ow = int(e["owner_fn"], 16)
    ns = nop_start(cv)
    a1 = aligned(ow, cv); a2 = aligned(ns, cv) if ns else False
    v = "OK" if ow == ns else "MISMATCH"
    if ow != ns: bad.append((e["set_c_call"], e["owner_fn"], hex(ns) if ns else None))
    print(f"{e['set_c_call']:<12} {e['owner_fn']:<14} {hex(ns) if ns else '-':<11} {str(a1):<7} {str(a2):<8} {v}")
print("\nMISMATCH 共", len(bad))
for b in bad: print("  ", b)
