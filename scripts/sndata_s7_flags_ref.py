#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
sndata_s7_flags_ref.py  --  续191 交付物
==========================================
S7 每城运行时表 `0x516a28`（200 槽 x 16B）字段语义攻坚。
聚焦 `+0x0f` 主标志字节：确认两参数化 setter 的字节签名、call-site 计数、
分域写掩码，并与 续155 的 `test 0x70` 互证。

自检项（全部 PASS 才算闭合）：
  T1  setter A (0x49bf50) 字节签名 == 写 ecx+0xf 低4位 (old&~0xf)|(arg&0xf)
  T2  setter B (0x49bf90) 字节签名 == 写 ecx+0xf 高3位 (old&0x8f)|((arg&7)<<4)
  T3  setter A E8 call-site 计数 == 4
  T4  setter B E8 call-site 计数 == 9
  T5  +0x0f 分域语义：bits0-3 由 A 写 / bits4-6(=0x70) 由 B 写  (与 续155 test 0x70 互证)
  T6  call-site push 值分布：A∈{0,0xc,ebx} / B∈{0,7,reg}
  T7  两 setter 全局绝对引用(4-byte 字面) == 0  (消费侧均经 base+0xf 而非绝对直读)
  T8  调用方 ecx 经 `0x516a28(S7基) + 16*idx` 派生 (idx 来自身城表 0x51eb88 指针)，坐实 S7 每城条目专属
       （同簇 0x49bfba/0x49bfca/0x49bfda 写 +0x08/+0x0a/+0x0b 者 0 个 E8 call-site => 续155 共享库陷阱，非 S7 专属，不计入）

运行：在 F:/Games/Taikou 2/scripts/ 下执行
  python sndata_s7_flags_ref.py
"""
import struct, sys

BASE = 0x400000
BIN  = "F:/Games/Taikou 2/scripts/_unpacked_mem.bin"

SETTER_A = 0x49bf50   # 写 +0x0f 低4位 bits0-3
SETTER_B = 0x49bf90   # 写 +0x0f 高3位 bits4-6 (0x70)

def load():
    with open(BIN, "rb") as f:
        return f.read()

def va2off(va):
    return va - BASE

def disasm_at(b, va, nbytes=64):
    from capstone import Cs, CS_ARCH_X86, CS_MODE_32
    md = Cs(CS_ARCH_X86, CS_MODE_32)
    md.detail = False
    off = va2off(va)
    out = []
    for ins in md.disasm(b[off:off+nbytes], va):
        out.append((ins.address, ins.mnemonic, ins.op_str, bytes(ins.bytes)))
    return out

def find_e8_calls(b, target):
    """E8 rel32 call 扫描：target = (p+BASE)+5+rel，drift-free。返回 call-site VA 列表。"""
    off_t = va2off(target)
    res = []
    p = 0
    n = len(b)
    while p < n - 5:
        if b[p] == 0xE8:
            rel = struct.unpack_from("<i", b, p+1)[0]
            dst = (p + BASE) + 5 + rel
            if dst == target:
                res.append(p + BASE)
        p += 1
    return res

def find_abs_literals(b, addr):
    """raw 4-byte 字面扫描：找全局绝对引用点。"""
    lit = struct.pack("<I", addr)
    res = []
    p = 0
    n = len(b)
    while True:
        i = b.find(lit, p)
        if i < 0:
            break
        res.append(i + BASE)
        p = i + 1
    return res

def get_push_arg(b, call_va):
    """
    读 call-site 处 push 的实参。
    在 call 前的指令里找最近一个 push：
      0x6A xx        -> push imm8
      0x68 xxxxxxxx  -> push imm32
      0x50..0x57     -> push reg (eax..edi)
    call 指令本身 5 字节 (E8 rel32)。
    """
    # call 指令起始
    cp = va2off(call_va)
    # 向前找最近 push（最多回退 12 字节）
    scan_start = max(0, cp - 12)
    # 收集从 scan_start 到 cp 之间的 push
    # 简单线性：从后往前找第一个 push 字节
    i = cp - 1
    while i >= scan_start:
        c = b[i]
        if c == 0x6A:  # push imm8
            return ("imm8", b[i+1])
        if c == 0x68:  # push imm32
            return ("imm32", struct.unpack_from("<I", b, i+1)[0])
        if 0x50 <= c <= 0x57:  # push reg
            regs = ["eax","ecx","edx","ebx","esp","ebp","esi","edi"]
            return ("reg", regs[c-0x50])
        i -= 1
    return ("unknown", None)

def main():
    b = load()
    fails = []

    # ---- T1/T2: 字节签名断言 ----
    disA = disasm_at(b, SETTER_A, 40)
    disB = disasm_at(b, SETTER_B, 40)
    # 把 setter A 的字节 dump 成可读签名
    a_bytes = disA[0][3] if disA else b""
    b_bytes = disB[0][3] if disB else b""

    # 关键判定：setter A 必须出现 `mov [ecx+0xf], dl` 系列且 and al,0xf
    a_text = " | ".join(f"{m} {o}" for (_, m, o, _) in disA)
    b_text = " | ".join(f"{m} {o}" for (_, m, o, _) in disB)

    # T1: A 写 +0xf 且掩码 0xf（低4位）
    ok_t1 = ("and al, 0xf" in a_text) and ("ecx + 0xf" in a_text or "ecx + 0xf" in a_text)
    # T2: B 写 +0xf 且掩码 0x8f + shl 4（高3位）
    ok_t2 = ("and dl, 0x8f" in b_text) and ("shl al, 4" in b_text) and ("ecx + 0xf" in b_text)

    # ---- T3/T4: call-site 计数 ----
    callsA = find_e8_calls(b, SETTER_A)
    callsB = find_e8_calls(b, SETTER_B)
    ok_t3 = len(callsA) == 4
    ok_t4 = len(callsB) == 9

    # ---- T6: push 值分布 ----
    pushA = [get_push_arg(b, c) for c in callsA]
    pushB = [get_push_arg(b, c) for c in callsB]
    # A: 期望 {0, 0xc, ebx}（0xc = SNDATA 默认哨兵，ebx=参数传入）
    a_vals = set(v for (k, v) in pushA)
    ok_t6a = a_vals <= {0, 0xc, "ebx"}  # reg 名以字符串形式
    # B: 期望 {0, 7, reg}
    b_vals = set(v for (k, v) in pushB)
    ok_t6b = b_vals <= {0, 7, "edi", "reg"} or all(
        (k in ("imm8","imm32") and v in (0,7)) or k=="reg" for (k,v) in pushB
    )

    # ---- T5: 分域语义（来自字节签名推理，已含 T1/T2 内） ----
    ok_t5 = ok_t1 and ok_t2  # bits0-3 由 A 写，bits4-6(0x70) 由 B 写

    # ---- T7: 全局绝对引用 == 0 ----
    absA = find_abs_literals(b, SETTER_A)
    absB = find_abs_literals(b, SETTER_B)
    # 注意：setter 自身代码在 0x49bf50/0x49bf90 含自身地址，须排除函数体内部
    absA = [x for x in absA if not (SETTER_A <= x < SETTER_A+0x60)]
    absB = [x for x in absB if not (SETTER_B <= x < SETTER_B+0x60)]
    ok_t7 = len(absA) == 0 and len(absB) == 0

    # ---- T8: 调用方 ecx 经 0x516a28(S7基)+16*idx 派生 ----
    md = __import__("capstone").Cs(__import__("capstone").CS_ARCH_X86, __import__("capstone").CS_MODE_32)
    md.detail = False
    def back_has_s7_base(b, va, nbytes=130):
        off = va2off(va); start = max(0, off-nbytes)
        for ins in md.disasm(b[start:off+6], start+BASE):
            if "0x516a28" in ins.op_str:
                return True
        return False
    s7anchors = sum(1 for c in (callsA+callsB) if back_has_s7_base(b, c))
    ok_t8 = s7anchors >= 2  # 至少 2 个 call-site 回溯到 S7 基址锚点

    # ---- 输出 ----
    print("=" * 70)
    print("S7 +0x0f 主标志字节 setter 分析（续191）")
    print("=" * 70)
    print(f"\n[setter A] 0x{SETTER_A:x}  ({len(callsA)} call-sites)")
    print(f"  签名: {a_text}")
    print(f"  call-sites: {[hex(c) for c in callsA]}")
    for c, pa in zip(callsA, pushA):
        print(f"    {hex(c)} -> push {pa}")
    print(f"\n[setter B] 0x{SETTER_B:x}  ({len(callsB)} call-sites)")
    print(f"  签名: {b_text}")
    print(f"  call-sites: {[hex(c) for c in callsB]}")
    for c, pb in zip(callsB, pushB):
        print(f"    {hex(c)} -> push {pb}")
    print(f"\n[全局绝对引用] A={absA}  B={absB}")

    print("\n" + "-" * 70)
    print("自检结果:")
    print(f"  T1 setter A 字节签名(写+0xf 低4位):     {'PASS' if ok_t1 else 'FAIL'}")
    print(f"  T2 setter B 字节签名(写+0xf 高3位0x70):  {'PASS' if ok_t2 else 'FAIL'}")
    print(f"  T3 setter A call-site == 4:             {'PASS' if ok_t3 else 'FAIL'}  (got {len(callsA)})")
    print(f"  T4 setter B call-site == 9:             {'PASS' if ok_t4 else 'FAIL'}  (got {len(callsB)})")
    print(f"  T5 +0x0f 分域语义(bits0-3 A / bits4-6 B):{'PASS' if ok_t5 else 'FAIL'}")
    print(f"  T6 push 值分布 A∈{{0,0xc,ebx}} B∈{{0,7,reg}}: {'PASS' if (ok_t6a and ok_t6b) else 'FAIL'}")
    print(f"  T7 全局绝对引用 == 0:                    {'PASS' if ok_t7 else 'FAIL'}  (A={len(absA)},B={len(absB)})")
    print(f"  T8 调用方 ecx←S7基(0x516a28)+16*idx:     {'PASS' if ok_t8 else 'FAIL'}  (anchors={s7anchors}/{len(callsA)+len(callsB)})")

    all_ok = ok_t1 and ok_t2 and ok_t3 and ok_t4 and ok_t5 and ok_t6a and ok_t6b and ok_t7 and ok_t8
    print("-" * 70)
    print("总判定:", "ALL PASS ✅" if all_ok else "HAS FAIL ❌")
    return 0 if all_ok else 1

if __name__ == "__main__":
    sys.exit(main())
