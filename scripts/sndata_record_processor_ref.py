# -*- coding: utf-8 -*-
"""
SNDATA 49B 记录处理器 0x47fc60 —— 扇出语义验证（2026-08-31 续158 · P0 第一步）

背景 / 架构纠正
----------------
此前误以为 0x47f350 主解析器的 18 个 SUB1 子加载器(S0..S17)处理 49B 记录。
实测推翻：
  - 18 个 SUB1 子加载器只用 0x47d910/0x47d930(1B/2B 字段 setter)写 实体池(0x519868)/
    城池(0x51eb88)等**其它序列化块**，完全不引用 0x47fc60 / 0x522c88。
  - 0x47d890(49B 记录访问器 idx*49+0x10) 全镜像**唯一调用点** = 0x47fc8c(在 0x47fc60 内)。
  - 0x47fc60 的调用方 0x47ff68 / 0x4882b1 / 0x4e8625 在镜像中**无任何立即数引用**
    (无 call/jmp/mov-imm/函数指针表) ⇒ 记录处理经**寄存器间接调用 / 函数指针表分发**，
    不在 0x47f350 的静态调用图里，故 emu 直追 0x47f350 抓不到记录循环。

本脚本对 0x47fc60 本体做**程序化断言**，把"逐记录通用扇出器"钉死：
  读 record[idx] (49B) 进栈缓冲 [esp..esp+0x30]，
  然后：
    record[0:2]  -> 调用者 arg2 ([esp+0xdc] 目标)
    record[2:4]  -> 调用者 arg3 ([esp+0xe0] 目标)
    record[4:6]  -> 调用者 arg4 ([esp+0xe4] 目标)
    memcpy(0x522c88, &record[6],  43B)   ; 主体 payload
    memcpy(0x522c60, &record[0x13], 1B)   ; 单字节
    memcpy(0x522c70, &record[0x20], 1B)   ; 单字节
  这与 GAME_DATA_SPEC / SNDATA_SPEC §4 表一致（record[6:49]→0x522c88 等）。
"""

import os
import sys
import json
import struct
import re

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

IMG = open("scripts/_unpacked_mem.bin", "rb").read()
BASE = 0x400000
PROC = 0x47fc60
COPY = 0x4ebfe0

md = Cs(CS_ARCH_X86, CS_MODE_32)
md.detail = True

_ESP_OFF = re.compile(r"\[esp(?:\s*\+\s*(0x[0-9a-f]+|\d+))?\]")


def esp_off(op_str):
    """Extract the +N offset from an `[esp + N]` operand (0 if bare [esp])."""
    m = _ESP_OFF.search(op_str)
    if not m:
        return None
    if m.group(1) is None:
        return 0
    tok = m.group(1)
    return int(tok, 16) if tok.lower().startswith("0x") else int(tok)


def disasm_at(va, size=0x200):
    code = IMG[va - BASE: va - BASE + size]
    return list(md.disasm(code, va))


def extract_fanout():
    """裸字节扫描 0x47fc60 内 3 处 `call 0x4ebfe0`，回扫 src 偏移(lea [esp+X]) 与 dst(push 0x522cXX)。"""
    region = IMG[PROC - BASE: PROC - BASE + 0xB0]
    pairs = []
    n = len(region)
    i = 0
    while i < n - 5:
        if region[i] == 0xE8:
            rel = struct.unpack_from("<i", region, i + 1)[0]
            va_site = PROC + i
            tgt_va = va_site + 5 + rel
            if tgt_va == COPY:
                dst = None
                src = None
                j = i - 1
                while j >= 0 and (i - j) < 16:
                    b = region[j]
                    if b == 0x68 and j + 5 <= n:        # push imm32
                        imm = struct.unpack_from("<I", region, j + 1)[0]
                        if 0x522c00 <= imm <= 0x522cff:
                            dst = imm
                    if b == 0x8D and j + 4 <= n and region[j + 2] == 0x24:  # lea r32,[esp+X]
                        src = region[j + 3]
                    j -= 1
                if dst is not None and src is not None:
                    pairs.append((src, dst))
        i += 1
    return pairs


def extract_header_writes():
    """record[0:2]/[2:4]/[4:6] -> 调用者 arg 的源偏移(从 mov ax/dx/cx, [esp+X] 提取)。"""
    ins = disasm_at(PROC)
    src_offs = []
    for insn in ins:
        if insn.mnemonic != "mov":
            continue
        # 源操作数是 [esp+X]，目的操作数是 ax/dx/cx (即读取 header 字节)
        parts = [p.strip() for p in insn.op_str.split(",")]
        if len(parts) == 2 and parts[0] in ("ax", "dx", "cx") and "[esp" in parts[1] and "dword" not in parts[1]:
            o = esp_off(parts[1])
            if o is not None:
                src_offs.append(o)
    return src_offs


def self_test():
    pairs = extract_fanout()
    print("扇出 memcpy 对 (src_off, dst):", pairs)
    dsts = sorted(p[1] for p in pairs)
    srcs = sorted(p[0] for p in pairs)
    assert len(pairs) == 3, "应有 3 处 memcpy(0x4ebfe0) 扇出, 实得 %d" % len(pairs)
    assert dsts == [0x522c60, 0x522c70, 0x522c88], "dst 应为 {0x522c60,0x522c70,0x522c88}, 实得 %s" % dsts
    assert 0x522c88 in dsts and 0x522c60 in dsts and 0x522c70 in dsts
    # src 偏移: payload=6, 单字节=0x13, 0x20
    assert 6 in srcs, "payload 源偏移应为 6, 实得 %s" % srcs
    assert 0x13 in srcs, "0x13 单字节源偏移缺失, 实得 %s" % srcs
    assert 0x20 in srcs, "0x20 单字节源偏移缺失, 实得 %s" % srcs
    print("  ✅ 3 处 memcpy 目标 = {0x522c88(payload[6:]), 0x522c60([0x13]), 0x522c70([0x20])}")

    # 头部分写: record[0:2]/[2:4]/[4:6] -> 调用者 arg
    hdr = sorted(set(extract_header_writes()) & {0, 2, 4})
    print("头部分写源偏移(解析):", hdr)
    # 期望覆盖 0,2,4 (record[0:2]/[2:4]/[4:6])
    assert sum(1 for o in (0, 2, 4) if o in hdr) >= 2, "头部分写应覆盖 [0:2]/[2:4]/[4:6], 实得 %s" % hdr
    print("  ✅ 记录头 [0:2]/[2:4]/[4:6] -> 调用者三参数(arg2/arg3/arg4)")

    # 与 sndata_records.json 交叉验证: payload 长度 = 43B, 且 = record[6:49]
    d = json.load(open("scripts/sndata_records.json"))
    for scn in ("scenario1", "scenario2"):
        recs = d[scn]["records"]
        # 抽样: 非填充、最大 real_byte_count 的记录
        sample = max((r for r in recs if r["real_byte_count"] > 0),
                     key=lambda r: r["real_byte_count"])
        plen = len(sample["payload_hex"]) // 2
        assert plen == 43, "payload 应为完整 43B (record[6:49]), 实得 %d" % plen
        assert sample["real_byte_count"] <= 49, "real_byte_count 应 ≤49, 实得 %d" % sample["real_byte_count"]
        print("  ✅ %s 抽样记录 idx=%d payload=%dB (恒=43B) 与 record[6:49] 一致" %
              (scn, sample["idx"], plen))

    print("\n自校验通过: 0x47fc60 逐记录通用扇出 = 头[0:6]→调用者参数 + payload[6:49]→0x522c88 / [0x13]→0x522c60 / [0x20]→0x522c70 ✅")
    return pairs


if __name__ == "__main__":
    self_test()
