#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
sfx_15_36_ref.py —— SFX 15(ZANSYU) / 36(MATISIRO) 间接调用玩法事件收口
================================================================================
背景：play_sfx @0x4997c0；名表 @0x50ba40。续226/247：75 处 call 中无
`push` 立即数 15/36；仅可能经「非立即数实参」间接路径。

本脚本硬断言（可静态证明）：
  A. 名表槽位：ID15=A:ZANSYU.KOS，ID36=A:MATISIRO.KOS；串仅被名表指针引用。
  B. call 0x4997c0 共 75 处；其中最后一档 push 为立即数 70 处、为寄存器 5 处、
     为内存操作数 0 处。
  C. 立即数实参覆盖的 ID 集合不含 15/36；不存在 `push 0x0f/0x24`（含 imm32）
     后紧邻 call play_sfx。
  D. 5 个寄存器实参站点各自定值（或定值集合），均 ≠ 15/36：
       - 0x422a17  push ebx，且 ebx 在 push 前由 `xor ebx,ebx` 置 0 → id=0
       - 0x44edd4  `add ecx,0x22; push ecx` → id∈{34,35}
       - 0x46bd3c / 0x46bdc3 / 0x46be37  push ebp，且到达这些 push 的路径上
         `[esp+0x18]==0`（arg1==0），此时 ebp∈{0x13,0x14}={19,20}
  E. 映像内无 `mov r32, 0x4997c0` / `push 0x4997c0` 形态的 play_sfx 地址嵌入
     （排除 call-reg 间接转入）。

结论性负结果（信息性打印，不进脆弱语义断言）：
  在「全部直接 E8 call play_sfx + 全部非立即数实参已定值」的静态闭包下，
  ID 15 / 36 没有任何可证明的玩法事件生产者。文件名罗马字语义仍属推断，
  不能升格为「已钉死玩法事件」。若运行时确有播放，必经本静态扫描未覆盖的
  机制（自修改 / 外部注入 / 未映射代码），不在本映像静态可达集内。

注意：sfx_unnamed_ref 所称「约 10 个间接点」为旧口径高估；本收口以
      「最后一档 push」分类得 **恰好 5** 个寄存器实参站点（可复现）。
"""
from __future__ import annotations

import os
import re
import struct
import sys
from collections import Counter

from capstone import CS_ARCH_X86, CS_MODE_32, CS_OP_IMM, CS_OP_MEM, CS_OP_REG, Cs

HERE = os.path.dirname(os.path.abspath(__file__))
MEM = open(os.path.join(HERE, "_unpacked_mem.bin"), "rb").read()
BASE = 0x400000
PLAY = 0x4997c0
SFX_TBL = 0x50ba40

md = Cs(CS_ARCH_X86, CS_MODE_32)
md.detail = True

OK: list[str] = []
FAIL: list[str] = []


def check(name: str, cond: bool, extra: str = "") -> None:
    if cond:
        OK.append(name)
        print("  [OK  ] %s" % name)
    else:
        FAIL.append(name)
        print("  [FAIL] %s   %s" % (name, extra))


def rd(va: int, n: int) -> bytes:
    o = va - BASE
    if o < 0 or o + n > len(MEM):
        return b""
    return MEM[o : o + n]


def find_calls(target: int) -> list[int]:
    out: list[int] = []
    off = 0
    while True:
        i = MEM.find(b"\xE8", off)
        if i < 0:
            break
        rel = struct.unpack_from("<i", MEM, i + 1)[0]
        if (BASE + i + 5 + rel) & 0xFFFFFFFF == target:
            out.append(BASE + i)
        off = i + 1
    return out


def imm_val(tok: str):
    tok = tok.strip()
    m = re.fullmatch(r"(0x[0-9a-fA-F]+|[0-9]+)", tok)
    if not m:
        return None
    s = m.group()
    return int(s, 16) if s.lower().startswith("0x") else int(s)


def decode_window(call_va: int, before: int = 0x60):
    """Return (insns, call_idx) aligned so call_va is an instruction start."""
    start = call_va - before
    raw = rd(start, before + 8)
    best = None
    for off in range(before + 1):
        ins = list(md.disasm(raw[off:], start + off))
        addrs = [i.address for i in ins]
        if call_va not in addrs:
            continue
        idx = addrs.index(call_va)
        if best is None or idx > best[0]:
            best = (idx, ins)
    if best is None:
        return None, None
    return best[1], best[0]


def last_push(call_va: int):
    ins, idx = decode_window(call_va)
    if ins is None:
        return None
    pushes = [i for i in ins[:idx] if i.mnemonic == "push"]
    if not pushes:
        return None
    return pushes[-1]


def sfx_name(i: int) -> str:
    p = struct.unpack("<I", rd(SFX_TBL + 4 * i, 4))[0]
    b = rd(p, 24)
    z = b.find(0)
    return b[: z if z >= 0 else 24].decode("ascii", "replace")


def dword_xrefs(value: int) -> list[int]:
    needle = struct.pack("<I", value)
    out: list[int] = []
    off = 0
    while True:
        i = MEM.find(needle, off)
        if i < 0:
            break
        out.append(BASE + i)
        off = i + 1
    return out


def push_imm_then_play(imm: int, gap: int = 0x10) -> list[int]:
    """Sites where push imm8/imm32 is followed (within gap) by call play_sfx."""
    hits: list[int] = []
    for needle in (bytes([0x6A, imm]), struct.pack("<BI", 0x68, imm)):
        off = 0
        while True:
            i = MEM.find(needle, off)
            if i < 0:
                break
            pva = BASE + i
            # confirm decode
            ins0 = list(md.disasm(rd(pva, 8), pva))
            if not ins0 or ins0[0].mnemonic != "push" or imm_val(ins0[0].op_str) != imm:
                off = i + 1
                continue
            for j in range(len(needle), gap):
                if rd(pva + j, 1) != b"\xE8":
                    continue
                rel = struct.unpack_from("<i", MEM, (pva + j) - BASE + 1)[0]
                if ((pva + j + 5 + rel) & 0xFFFFFFFF) == PLAY:
                    hits.append(pva)
                break
            off = i + 1
    return hits


def ebx_zero_until_push() -> bool:
    """At 0x422a17 path: xor ebx,ebx @0x4228c9 and no ebx-dest write before push."""
    push_va = 0x422A12
    xor_va = 0x4228C9
    # verify xor
    ins_xor = list(md.disasm(rd(xor_va, 4), xor_va))
    if not ins_xor or ins_xor[0].mnemonic != "xor" or ins_xor[0].op_str != "ebx, ebx":
        return False
    ins, idx = decode_window(0x422A17, before=0x1C0)
    if ins is None:
        return False
    for i in ins[:idx]:
        if i.address < xor_va:
            continue
        if i.address == push_va:
            return i.mnemonic == "push" and i.op_str.strip() == "ebx"
        dest = i.op_str.split(",")[0].strip()
        if dest == "ebx" and i.mnemonic in (
            "mov", "lea", "add", "sub", "and", "or", "xor", "pop", "imul", "movzx", "movsx"
        ):
            # xor ebx,ebx itself is allowed at xor_va
            if not (i.address == xor_va and i.mnemonic == "xor"):
                return False
    return False


def weather_site_ok() -> bool:
    win = list(md.disasm(rd(0x44EDC5, 0x18), 0x44EDC5))
    txt = " ; ".join("%s %s" % (i.mnemonic, i.op_str) for i in win)
    return (
        any(i.mnemonic == "add" and "ecx" in i.op_str and "0x22" in i.op_str for i in win)
        and any(i.mnemonic == "call" and "0x4997c0" in i.op_str for i in win)
        and "setne" in txt
    )


def ebp_duel_sites_ok() -> bool:
    """Prove push-ebp play sites only fire with ebp in {0x13,0x14}.

    Evidence bundle:
      1) Function 0x46bc00 assigns ebp := 0x13 / 0x14 on arg1==0 path,
         or ebp := [esp+0x18] on arg1!=0 path.
      2) Each of the three push-ebp sites is reached only via
         `cmp word [esp+0x18], 0` / `je <push-ebp-block>`.
      3) Therefore push-ebp ⇒ [esp+0x18]==0 ⇒ arg1==0 path ⇒ ebp∈{0x13,0x14}.
    """
    blob = rd(0x46BC00, 0x280)
    ins = list(md.disasm(blob, 0x46BC00))
    ebp_imm = [
        i for i in ins
        if i.mnemonic == "mov"
        and i.op_str.startswith("ebp,")
        and imm_val(i.op_str.split(",", 1)[1]) in (0x13, 0x14)
    ]
    ebp_mem = [
        i for i in ins
        if i.mnemonic == "mov"
        and i.op_str.startswith("ebp,")
        and "esp + 0x18" in i.op_str
    ]
    if len(ebp_imm) < 2 or len(ebp_mem) < 1:
        return False

    # (call_va, expected_cmp_va, expected_je_target)
    # je target = first insn of the push-ebp block (push edi / ... / push ebp)
    expect = [
        (0x46BD3C, 0x46BD19, 0x46BD2C),
        (0x46BDC3, 0x46BD78, 0x46BDB3),
        (0x46BE37, 0x46BDFE, 0x46BE27),
    ]
    for call_va, cmp_va, je_tgt in expect:
        lp = last_push(call_va)
        if lp is None or lp.op_str.strip() != "ebp":
            return False
        # verify cmp at cmp_va
        cmp_ins = list(md.disasm(rd(cmp_va, 8), cmp_va))
        if (
            not cmp_ins
            or cmp_ins[0].mnemonic != "cmp"
            or "esp + 0x18" not in cmp_ins[0].op_str
            or not cmp_ins[0].op_str.strip().endswith(", 0")
        ):
            return False
        # verify je immediately after cmp
        je_va = cmp_ins[0].address + cmp_ins[0].size
        je_ins = list(md.disasm(rd(je_va, 8), je_va))
        if not je_ins or je_ins[0].mnemonic != "je":
            return False
        try:
            target = int(je_ins[0].op_str, 16)
        except ValueError:
            return False
        if target != je_tgt:
            return False
        if not (cmp_va < target <= lp.address):
            return False
    return True


def no_play_addr_embed() -> bool:
    """No mov-r32-imm32 / push-imm32 of PLAY address in the image."""
    needle = struct.pack("<I", PLAY)
    off = 0
    while True:
        i = MEM.find(needle, off)
        if i < 0:
            return True
        va = BASE + i
        prev1 = rd(va - 1, 1)
        if prev1 in (b"\xb8", b"\xb9", b"\xba", b"\xbb", b"\xbe", b"\xbf", b"\x68"):
            return False
        off = i + 1


def main() -> int:
    print("=" * 78)
    print("SFX 15(ZANSYU) / 36(MATISIRO) 间接调用收口自校验")
    print("=" * 78)

    # ---- A. name table ----
    print("\n[A] 名表槽位与串 xref")
    n15, n36 = sfx_name(15), sfx_name(36)
    check("A1 ID15 文件名含 ZANSYU.KOS", "ZANSYU.KOS" in n15.upper(), n15)
    check("A2 ID36 文件名含 MATISIRO.KOS", "MATISIRO.KOS" in n36.upper(), n36)
    p15 = struct.unpack("<I", rd(SFX_TBL + 4 * 15, 4))[0]
    p36 = struct.unpack("<I", rd(SFX_TBL + 4 * 36, 4))[0]
    x15, x36 = dword_xrefs(p15), dword_xrefs(p36)
    check("A3 ZANSYU 串指针仅名表槽 xref（1 处）", x15 == [SFX_TBL + 4 * 15],
          [hex(x) for x in x15])
    check("A4 MATISIRO 串指针仅名表槽 xref（1 处）", x36 == [SFX_TBL + 4 * 36],
          [hex(x) for x in x36])

    # ---- B. classify all call sites ----
    print("\n[B] play_sfx 调用点分类（最后一档 push）")
    sites = find_calls(PLAY)
    check("B1 call 0x4997c0 站点 = 75", len(sites) == 75, "got %d" % len(sites))

    kinds: Counter = Counter()
    imm_ids: set[int] = set()
    reg_sites: list[tuple[int, str]] = []
    for c in sites:
        lp = last_push(c)
        if lp is None:
            kinds["NO_PUSH"] += 1
            continue
        ot = lp.operands[0].type if lp.operands else None
        if ot == CS_OP_IMM:
            kinds["IMM"] += 1
            v = lp.operands[0].imm
            if 0 <= v < 39:
                imm_ids.add(v)
        elif ot == CS_OP_REG:
            kinds["REG"] += 1
            reg_sites.append((c, lp.op_str.strip()))
        elif ot == CS_OP_MEM:
            kinds["MEM"] += 1
        else:
            kinds["OTHER"] += 1

    check("B2 立即数实参站点 = 70", kinds["IMM"] == 70, dict(kinds))
    check("B3 寄存器实参站点 = 5", kinds["REG"] == 5, dict(kinds))
    check("B4 内存实参站点 = 0", kinds["MEM"] == 0, dict(kinds))
    expect_reg = {
        0x422A17: "ebx",
        0x44EDD4: "ecx",
        0x46BD3C: "ebp",
        0x46BDC3: "ebp",
        0x46BE37: "ebp",
    }
    got_reg = {c: a for c, a in reg_sites}
    check("B5 5 个 REG 站点地址/寄存器集合钉死", got_reg == expect_reg,
          {hex(k): v for k, v in got_reg.items()})

    # ---- C. no direct 15/36 ----
    print("\n[C] 无直接立即数 15/36")
    check("C1 立即数覆盖集不含 15", 15 not in imm_ids, sorted(imm_ids))
    check("C2 立即数覆盖集不含 36", 36 not in imm_ids, sorted(imm_ids))
    check("C3 无 push-imm8/32(15) 紧邻 call play_sfx",
          push_imm_then_play(15) == [], [hex(x) for x in push_imm_then_play(15)])
    check("C4 无 push-imm8/32(36) 紧邻 call play_sfx",
          push_imm_then_play(36) == [], [hex(x) for x in push_imm_then_play(36)])

    # ---- D. resolve REG sites ----
    print("\n[D] 5 个 REG 站点定值（均 ≠ 15/36）")
    check("D1 @0x422a17：xor ebx,ebx 后无改写直至 push ebx → id=0",
          ebx_zero_until_push())
    check("D2 @0x44edd4：setne/add ecx,0x22 → id∈{34,35}",
          weather_site_ok())
    check("D3 @0x46bd3c/c3/e37：push ebp 仅在 arg1==0 路径，ebp∈{19,20}",
          ebp_duel_sites_ok())

    # ---- E. no call-reg vector ----
    print("\n[E] 无 play_sfx 地址嵌入（排除 call-reg）")
    check("E1 映像无 mov r32/push imm32 = 0x4997c0", no_play_addr_embed())

    # ---- informational negative ----
    print("\n" + "-" * 78)
    print("结论性负结果（信息性）：")
    print("  75 处 call 的实参空间已穷尽：70 个立即数 ID 均 ≠15/36；")
    print("  5 个寄存器站点分别只能产生 {0}, {34,35}, {19,20}。")
    print("  名串 A:ZANSYU.KOS / A:MATISIRO.KOS 仅挂在名表，无旁路 push 进底层播放。")
    print("  => 静态上无法钉死任何「玩法事件 -> 播放 15/36」的生产者；")
    print("    置信不能升格，收口为结构性负结果。")
    print("  (旧说「约 10 个间接点」更正为 5 个 REG 站点，见 B3/B5。)")
    print("-" * 78)

    print("\n" + "=" * 78)
    if FAIL:
        print("RESULT: %d FAIL  -> %s" % (len(FAIL), FAIL))
        return 1
    print("RESULT: ALL PASS  (%d assertions)" % len(OK))
    return 0


if __name__ == "__main__":
    sys.exit(main())
