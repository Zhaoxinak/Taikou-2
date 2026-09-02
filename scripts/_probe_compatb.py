# -*- coding: utf-8 -*-
"""续232 探针：线性反汇编全镜像，找 word[entity+0x08] bits 8-10 (compat_b 位0-2) 访问器。
信号：and/test reg, 0x700  |  shr reg,8 后 and reg,0x7。
"""
import capstone
BASE = 0x400000
data = open("/Users/ts/Downloads/Taikou 2/scripts/_unpacked_mem.bin", "rb").read()
md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)
md.detail = True

hits = []
last_shr8 = None  # (va, regname)
va = BASE
end = BASE + len(data)
while va < end:
    chunk = data[va - BASE: va - BASE + 16]
    try:
        ins = next(md.disasm(chunk, va))
    except Exception:
        va += 1
        last_shr8 = None
        continue
    if ins.size == 0:
        va += 1
        last_shr8 = None
        continue
    mnem = ins.mnemonic
    ops = ins.op_str
    # shr reg, 8 -> remember reg
    if mnem.startswith("shr"):
        parts = [p.strip() for p in ops.split(",")]
        if len(parts) == 2 and parts[1] in ("8", "0x8"):
            last_shr8 = (va, parts[0])
        else:
            last_shr8 = None
    else:
        # check immediates for 0x700 / (and reg,0x7 after shr8)
        found_imm = False
        for op in ins.operands:
            if op.type == capstone.x86.X86_OP_IMM:
                imm = op.imm & 0xffffffff
                if imm == 0x700:
                    hits.append((va, mnem + " " + ops, "AND/TEST 0x700 (bits8-10)"))
                    found_imm = True
                if imm == 0x7 and mnem.startswith("and") and last_shr8 is not None:
                    dst = ops.split(",")[0].strip()
                    if dst == last_shr8[1]:
                        hits.append((va, mnem + " " + ops,
                                     "SHR8@%x + AND 0x7 => bits8-10" % last_shr8[0]))
                        found_imm = True
        if not (mnem.startswith("and") or mnem.startswith("test") or mnem.startswith("cmp")):
            # only keep shr-tracking across non-masking insns? reset if far
            pass
    va += ins.size

print("=== bits8-10 (compat_b 位0-2) 访问器候选 ===")
print("命中数:", len(hits))
for v, s, tag in hits[:80]:
    print("  %08x  %-30s [%s]" % (v, s, tag))
