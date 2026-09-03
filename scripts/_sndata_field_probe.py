# -*- coding: utf-8 -*-
r"""
_sndata_field_probe.py v2 -- 续224 下一步(A)：6 类 handler 逐字节字段读点
=================================================================================
修正 v1 的寄存器名 bug（手编 REGNAME 与 capstone 枚举不符）→ 改用 md.reg_name()。
增加「记录指针别名追踪」：记录以 eax 传入（续224 证 T1 经 eax 读 rec+1/2/3/8/0x25），
沿 `mov X,Y`(Y∈rec_regs) 传播别名；凡 [reg+imm] 读且 reg∈rec_regs 且 imm∈[0,0x31)
即记录字段。子调用若以 rec 寄存器为参数进入，则以其入口寄存器为种子递归一层。
"""
import sys, os
from capstone import Cs, CS_ARCH_X86, CS_MODE_32, CS_AC_READ, CS_AC_WRITE
from capstone.x86 import X86_OP_MEM

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _disasm_all import load_image, BASE

MEM = load_image()
md = Cs(CS_ARCH_X86, CS_MODE_32)
md.detail = True

# 续225 订正：idx->类->leaf 真实映射（来自跳转表 0x462584 + 6 thunk 反汇编）
HANDLERS = {
    0: ("勢力図",   [0x4625a0]),
    1: ("米市行情", [0x461ed0, 0x4630c0, 0x4632e0]),
    2: ("家中排行", [0x462670]),
    3: ("大名情報", [0x462a80]),
    4: ("持有物品", [0x462bc0, 0x462cf0]),
    5: ("属下武将", [0x462d40, 0x462e10]),
}

KNOWN_REC_OFFSETS = {1, 2, 3, 8, 0x25, 0x2c}  # 续224 已知

def va2off(va): return va - BASE

def disasm_window(va, max_bytes=0x500):
    off = va2off(va)
    data = MEM[off:off + max_bytes]
    out = []
    for ins in md.disasm(data, va):
        out.append(ins)
        m = ins.mnemonic
        if m.startswith("ret") or m == "iret":
            break
    return out

def mem_reads(ins):
    res = []
    if ins.id == 0:
        return res
    for op in ins.operands:
        if op.type != X86_OP_MEM:
            continue
        acc = getattr(op, "access", None)
        is_read = True
        if acc is not None and (acc & CS_AC_WRITE) and not (acc & CS_AC_READ):
            is_read = False
        base = md.reg_name(op.mem.base) if op.mem.base else "(imm)"
        res.append((base, op.mem.disp, is_read))
    return res

def extract_record_fields(va, seed_regs, depth=0, seen=None):
    """返回 set of (reg, disp) 记录字段读点。seed_regs=入口记录寄存器集合。"""
    if seen is None: seen = set()
    if va in seen or depth > 1: return set()
    seen.add(va)
    insns = disasm_window(va)
    rec_regs = set(seed_regs)
    fields = set()
    # 别名传播：先扫一遍建别名。种子=edi（dispatch 全程 callee-saved 持 rec 指针），
    # 各 leaf 经 mov/lea 把 edi 拷到 eax/ecx/esi/ebx 等。
    for ins in insns:
        if ins.mnemonic == "mov" and len(ins.operands) == 2:
            dst = md.reg_name(ins.operands[0].reg) if ins.operands[0].type == 2 else None
            src = ins.operands[1]
            if dst and src.type == 2 and md.reg_name(src.reg) in rec_regs:
                rec_regs.add(dst)
        elif ins.mnemonic == "lea" and len(ins.operands) == 2:
            dst = md.reg_name(ins.operands[0].reg) if ins.operands[0].type == 2 else None
            src = ins.operands[1]
            if dst and src.type == 3 and src.mem.base and md.reg_name(src.mem.base) in rec_regs:
                rec_regs.add(dst)
    # 再扫字段读
    callees = []
    for ins in insns:
        for (base, disp, is_read) in mem_reads(ins):
            if base in rec_regs and is_read and 0 <= disp < 0x31:
                fields.add((base, disp))
        if ins.mnemonic == "call" and ins.op_str.startswith("0x"):
            callees.append(int(ins.op_str, 16))
    # 直接子调用：若参数传了 rec 寄存器，则以其入口寄存器（按 cdecl[thiscall] 取 eax/ecx/edx/第一个 push）为种子递归
    for cv in callees:
        if not (0x460000 <= cv <= 0x527000): continue
        # 取子调用入口参数寄存器：看 call 前最后一条 mov/push 的源寄存器
        sub_seed = set()
        # 简化：用当前 rec_regs 中常见传参寄存器（eax/ecx/edx/esi/edi/ebx）作种子
        sub_seed = {r for r in rec_regs if r in ("eax","ecx","edx","esi","edi","ebx")}
        if not sub_seed:
            sub_seed = {"eax"}
        fields |= extract_record_fields(cv, sub_seed, depth+1, seen)
    return fields

def main():
    for idx, (name, vas) in HANDLERS.items():
        print(f"\n{'='*72}\n### 类[{idx}] {name}   handlers={[hex(v) for v in vas]}\n{'='*72}")
        for hva in vas:
            # 种子=edi（dispatch 全程 callee-saved 持 rec 指针；各 leaf 经 mov/lea 派生别名）
            seed = {"edi"}
            flds = extract_record_fields(hva, seed)
            # 标准化：(reg,disp) 按 disp 排序
            by_off = {}
            for (reg, disp) in flds:
                by_off.setdefault(disp, set()).add(reg)
            print(f"  handler {hex(hva)}: 记录字段读点 =")
            for disp in sorted(by_off):
                regs = ",".join(sorted(by_off[disp]))
                mark = "  (已知)" if disp in KNOWN_REC_OFFSETS else ""
                print(f"      rec+0x{disp:02x}  <- [{regs}]{mark}")

if __name__ == "__main__":
    main()
