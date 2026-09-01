#!/usr/bin/env python3

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
# 扫描国政治表消费者：找所有引用 0x5179b8 / 0x5179bc (本表) 与 0x519868 (武将表) 的位置，
# 反汇编其前 0x50 字节，人工看字段(+0x04/+0x05/+0x06)如何被用作索引。
import struct
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

BIN = _ROOT + '/scripts/_unpacked_mem.bin'
BASE = 0x400000
data = open(BIN, "rb").read()

def off(va): return va - BASE
cs = Cs(CS_ARCH_X86, CS_MODE_32)
cs.detail = True

targets = {
    0x5179b8: "PROV_TBL",
    0x5179bc: "PROV_TBL+4",
    0x519868: "GEN_TBL",
}

# 找所有 4 字节 LE 立即数命中
hits = []
for imm, name in targets.items():
    pat = struct.pack("<I", imm)
    start = 0
    while True:
        i = data.find(pat, start)
        if i < 0: break
        hits.append((i, imm, name))
        start = i + 1

hits.sort()
print(f"total hits: {len(hits)}")
# 每个命中反汇编前 0x50 字节
seen_funcs = set()
for i, imm, name in hits:
    va = BASE + i
    # 只打印引用 PROV 表本身的（更聚焦）；GEN 表命中太多，单独统计计数
    if name.startswith("PROV"):
        print(f"\n----- ref {name} @ {va:#08x} (imm {imm:#x}) -----")
        code = data[i-0x50:i+8]
        for ins in cs.disasm(code, va-0x50):
            print(f"{ins.address:#08x}  {ins.mnemonic} {ins.op_str}")

# GEN 表命中计数（不展开，太多）
gen = [h for h in hits if h[2]=="GEN_TBL"]
print(f"\n[GEN_TBL 0x519868 引用总数: {len(gen)}，不展开]")
