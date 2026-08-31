# -*- coding: utf-8 -*-
"""
_modeflag_consumers.py — 探索：5 个合战全局模式标志的全部绝对引用 + 消费侧上下文反汇编
目标（续186 已定位）：
  mode_m1     0x511bf8
  mode_m2     0x51352c
  parity      0x513540
  battle_type 0x513548
  handle_stat 0x513534
方法：raw 4-byte LE 字面扫描（drift-free）+ capstone 局部反汇编窗口。
输出每个引用点的 VA、访问形态（写/读/运算）、所在函数区间、上下各 ~12 条指令。
"""
import os, struct
from capstone import Cs, CS_ARCH_X86, CS_MODE_32, CS_OP_MEM

HERE = os.path.dirname(os.path.abspath(__file__))
MEM = os.path.join(HERE, "_unpacked_mem.bin")
BASE = 0x400000

TARGETS = {
    0x511bf8: "mode_m1",
    0x51352c: "mode_m2",
    0x513540: "parity",
    0x513548: "battle_type",
    0x513534: "handle_stat",
}


def load():
    b = open(MEM, "rb").read()
    return b


def find_literal_refs(b, addr):
    """返回所有『字面引用 addr』的文件偏移（drift-free）。"""
    pat = struct.pack("<I", addr)
    hits = []
    start = 0
    while True:
        i = b.find(pat, start)
        if i == -1:
            break
        hits.append(i)
        start = i + 1
    return hits


def disassemble_around(b, va, before=12, after=12):
    """在 va 附近反汇编，返回指令列表 [(va, mnem, op_str), ...]。"""
    md = Cs(CS_ARCH_X86, CS_MODE_32)
    md.detail = False
    # 以 va 为起点向前找指令边界不可行（变长），改为：反汇编从 va-before_bytes 到 va+after_bytes 的线性窗口
    # 但变长会错位；改为从 va 向后反汇编 after 条，以及从 va 向前用“扫描前一条”近似。
    # 简化：从 va-0x30 线性反汇编 64 条，截取覆盖 va 的窗口。
    pre = 0x30
    start_off = (va - BASE) - pre
    if start_off < 0:
        start_off = 0
    code = b[start_off: start_off + 0x120]
    try:
        insns = list(md.disasm(code, BASE + start_off))
    except Exception:
        return []
    # 定位覆盖 va 的窗口
    out = []
    for ins in insns:
        out.append((ins.address, ins.mnemonic, ins.op_str))
    return out


def classify(insns, target_va):
    """找出引用 target_va 的那条指令并判定形态。"""
    res = []
    for i, (va, mn, ops) in enumerate(insns):
        if f"0x{target_va:x}" in ops.replace("0X", "0x"):
            # 判定写/读/运算
            kind = "?"
            # 写：目标在 op_str 左侧（如 mov [0x..], reg / xor [0x..], reg）
            if mn in ("mov", "xor", "add", "sub", "and", "or", "inc", "dec", "cmp") and f"[0x{target_va:x}]" in ops:
                if mn == "cmp":
                    kind = "read(cmp)"
                elif mn in ("mov", "xor", "add", "sub", "and", "or", "inc", "dec"):
                    kind = "WRITE" if "=" not in ops.split(",")[0] else "read"
                    # mov [0x..], reg => 写；mov reg, [0x..] => 读
                    if f"[0x{target_va:x}]" == ops.split(",")[0].strip():
                        kind = "WRITE"
                    elif f"[0x{target_va:x}]" in ops.split(",")[1]:
                        kind = "read"
            res.append((va, mn, ops, kind))
    return res


def main():
    b = load()
    for addr, name in TARGETS.items():
        print(f"\n########## {name} @ 0x{addr:x} ##########")
        hits = find_literal_refs(b, addr)
        print(f"  字面引用数 = {len(hits)}")
        for off in hits:
            va = off + BASE
            insns = disassemble_around(b, va)
            cls = classify(insns, addr)
            # 找引用点附近的窗口（覆盖 va 前后各 ~10 条）
            idx = next((k for k, x in enumerate(insns) if x[0] == va), None)
            lo = max(0, (idx or 0) - 10)
            hi = min(len(insns), (idx or 0) + 10)
            print(f"\n  --- 引用点 VA=0x{va:x} (off=0x{off:x}) ---")
            for v, m, o in insns[lo:hi]:
                mark = " <<<" if v == va else ""
                print(f"    0x{v:06x}  {m:6s} {o}{mark}")
            for c in cls:
                print(f"    [判定] 0x{c[0]:06x} {c[1]} {c[2]}  => {c[3]}")


if __name__ == "__main__":
    main()
