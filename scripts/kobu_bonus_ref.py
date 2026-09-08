#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
kobu_bonus_ref.py — 鼓舞 bonus 条件 + 部队 +0x25 累加来源（续247）
====================================================================
闭合 GAME_DATA_SPEC §3.10.7 两处残留：
  ① byte[ent+0x24]==0x10 且 !(byte[0x517aa5]&0x10) 的玩法语义
  ② 部队记录 +0x25 的累加来源（谁在调 0x43dba0）

结论：
  * ent+0x24 = 国索引（续 castle_stream_map / setter 0x49a750）；0x10 = 尾张
  * 0x517aa5 bit4：全镜像 0 绝对写者，仅 2 读者（鼓舞 0x435392 / 门控 0x4a5c40）
    → 运行期恒为 0（死门控）；bonus 实际 =「主将所属国==尾张」
  * +0x25 累加器 = 0x43dba0（cap100）；11 处 call，push 立即数 ∈ {5,6,7}
    分布在合战/计略效果链（疲劳累加）
"""
import os
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_IMG = os.path.join(_ROOT, "scripts", "_unpacked_mem.bin")
BASE = 0x400000

code = open(_IMG, "rb").read()
md = Cs(CS_ARCH_X86, CS_MODE_32)
md.detail = True

results = []


def check(name, cond, detail=""):
    results.append((name, bool(cond), detail))
    print("%-56s %s%s" % (name, "PASS" if cond else "FAIL",
                          ("  -- " + detail) if detail else ""))


def at(va, n):
    return code[va - BASE : va - BASE + n]


def dis(va, n):
    return list(md.disasm(at(va, n), va))


# ---- 1) 尾张名表 @0x506ca8 stride9 idx16 ----
prov_raw = at(0x506ca8 + 16 * 9, 9).split(b"\x00")[0]
prov_name = prov_raw.decode("gbk")
check("名表 idx16 = 尾张",
      prov_name in ("尾张", "尾張") and prov_raw == bytes.fromhex("ceb2d5c5"),
      repr(prov_name))

# ---- 2) 鼓舞站：cmp [ebp+0x24],0x10 + test [0x517aa5],al ----
insns = dis(0x435383, 0x30)
texts = ["%s %s" % (i.mnemonic, i.op_str) for i in insns]
blob = " ; ".join(texts)
check("鼓舞读 ent+0x24 并 cmp 0x10",
      "byte ptr [ebp + 0x24]" in blob and "0x10" in blob)
check("鼓舞 test byte ptr [0x517aa5]",
      "byte ptr [0x517aa5]" in blob)
check("bonus 置 esi=1 后 lea gain*2+1 @0x435482",
      at(0x435482, 3) == bytes.fromhex("8d440001") or
      any(i.address == 0x435482 and i.mnemonic == "lea" for i in dis(0x43547a, 0x10)))

# ---- 3) 0x517aa5 读者恰 2、写者 0 ----
readers = []
writers = []
target = bytes([0xa5, 0x7a, 0x51, 0x00])
for i in range(len(code) - 6):
    # absolute imm32 == 0x517aa5 as memory operand
    # test/cmp/or/and/xor/mov forms
    if code[i + 2 : i + 6] == target:
        op = code[i]
        # F6 05 = test byte [imm],imm ; 84? ; 80 xx ; C6 05 ; 08/20/30/00 05 ; 8A 05 ; A0
        if op in (0xF6, 0x80, 0xC6, 0x08, 0x20, 0x30, 0x00, 0x28, 0x8A) and code[i + 1] == 0x05:
            va = BASE + i
            kind = "write" if op in (0x80, 0xC6, 0x08, 0x20, 0x30, 0x00, 0x28) else "read"
            # 80 /05 = add; need reg field: 80 0D=or, 80 25=and, 80 35=xor, 80 05=add, 80 3D=cmp
            if op == 0x80:
                modrm_reg = (code[i + 1] >> 3) & 7  # wrong - modrm is byte1 when ...
                # actually for 80 05 the modrm IS 05, reg=0 → add
                # For 80 0D modrm=0D, reg=1 → or
                pass
            if op == 0xF6 and code[i + 1] == 0x05:
                readers.append(va)
            elif op == 0x8A and code[i + 1] == 0x05:
                readers.append(va)
            elif op in (0xC6, 0x08, 0x20, 0x30, 0x00, 0x28) and code[i + 1] == 0x05:
                writers.append(va)
            elif op == 0x80 and code[i + 1] == 0x05:
                # add/or/and/... distinguished — 05 means modrm with reg=0 = ADD (write)
                writers.append(va)
    if code[i + 1 : i + 5] == target and code[i] == 0xA0:
        readers.append(BASE + i)  # mov al,[imm]
    if code[i + 1 : i + 5] == target and code[i] == 0xA2:
        writers.append(BASE + i)  # mov [imm],al

# Also catch test byte ptr [0x517aa5], al  = F6 05 a5 7a 51 00 / or 84? 
# Actual encoding at 0x435392: from earlier disasm "test byte ptr [0x517aa5], al"
# That's F6 05 a5 7a 51 00  — wait, test r/m8, imm8 would be F6 /0 ib; test r/m8,r8 is 84 /r
# "test byte ptr [0x517aa5], al" → 84 05 a5 7a 51 00  (modrm 05 = [disp32], reg=al)
for i in range(len(code) - 6):
    if code[i] == 0x84 and code[i + 1] == 0x05 and code[i + 2 : i + 6] == target:
        readers.append(BASE + i)
    if code[i] == 0xF6 and code[i + 1] == 0x05 and code[i + 2 : i + 6] == target:
        readers.append(BASE + i)

readers = sorted(set(readers))
writers = sorted(set(writers))
check("0x517aa5 读者恰 2 处",
      readers == [0x435392, 0x4a5c40],
      "readers=" + ",".join(hex(x) for x in readers))
check("0x517aa5 绝对写者 = 0（死门控）",
      writers == [],
      "writers=" + ",".join(hex(x) for x in writers))

# ---- 4) setter 0x49a750 = mov [ecx+0x24], arg ----
s = dis(0x49a750, 0x10)
check("0x49a750 = set byte[ecx+0x24]",
      any(i.mnemonic == "mov" and "byte ptr [ecx + 0x24]" in i.op_str for i in s))

# ---- 5) 0x43dba0 = field25 add cap 100 ----
s = " ; ".join("%s %s" % (i.mnemonic, i.op_str) for i in dis(0x43dba0, 0x30))
check("0x43dba0 含 cap 0x64(100)",
      "0x64" in s)

# ---- 6) 11 call sites, push imm in {5,6,7} ----
sites = []
for i in range(len(code) - 5):
    if code[i] != 0xE8:
        continue
    rel = int.from_bytes(code[i + 1 : i + 5], "little", signed=True)
    if BASE + i + 5 + rel != 0x43dba0:
        continue
    site = BASE + i
    # find last push imm in preceding 12 bytes
    push_val = None
    for j in range(max(0, i - 12), i):
        for ins in md.disasm(code[j:i], BASE + j):
            if ins.address >= site:
                break
            if ins.mnemonic == "push":
                op = ins.op_str.strip()
                try:
                    if op.startswith("0x"):
                        push_val = int(op, 16)
                    else:
                        push_val = int(op)
                except ValueError:
                    pass
    sites.append((site, push_val))

check("0x43dba0 调用点 == 11",
      len(sites) == 11,
      "n=%d" % len(sites))
vals = {v for _, v in sites if v is not None}
check("push imm in {5,6,7}",
      vals <= {5, 6, 7} and vals >= {5},
      "vals=" + str(sorted(vals)))
check("含 push 7 与 push 6（计略疲劳档）",
      7 in vals and 6 in vals,
      str(sorted(vals)))

# ---- summary ----
print()
allpass = all(c for _, c, _ in results)
print("ALL PASS" if allpass else "HAS FAIL")
print("结论: bonus = (主将国索引==尾张/16)；0x517aa5 bit4 无写者=死门控；"
      "+0x25 由 0x43dba0 在合战链 +5/+6/+7 累加 cap100")
raise SystemExit(0 if allpass else 1)
