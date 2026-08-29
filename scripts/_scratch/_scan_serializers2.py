#!/usr/bin/env python3
"""Track walking-pointer registers in the serializer region to recover each
serializer's entity struct layout (field offset + size) and candidate counts.
For each serializer (between 'ret' boundaries), prints:
  - address range
  - sequence of reads as  R1/R2 @ <base>+<off>
  - small immediate constants (candidate array counts: 92, 700, 370, ...)
"""
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

BIN = r"F:/Games/Taikou 2/scripts/_unpacked_mem.bin"
BASE = 0x400000
START, END = 0x47dae0, 0x47f1c0

data = open(BIN, "rb").read()
off0 = START - BASE
code = data[off0:off0 + (END - START)]
md = Cs(CS_ARCH_X86, CS_MODE_32)
md.detail = True

PRIM = {0x47d910: "R1", 0x47d930: "R2"}

def reg(n):
    return n

# reg_state: name -> [base_label, offset_int]
def new_state():
    return {}

def apply_mov(state, dst, src_imm_or_label):
    pass

def resolve_op(op, state):
    # returns (label, off) for a register operand
    if op.type == 1:  # REG
        return state.get(op.reg, ["?", 0])
    if op.type == 2:  # IMM
        return [f"{op.imm:#x}", 0]
    if op.type == 3:  # MEM
        base = op.mem.base
        disp = op.mem.disp
        if base == 0:
            return [f"{disp:#x}", 0]
        b = state.get(base, ["?", 0])
        return [b[0], b[1] + disp]
    return ["?", 0]

def set_reg(state, r, val):
    state[r] = val

def lea(state, dst, src_op):
    # src is MEM
    base = src_op.mem.base
    disp = src_op.mem.disp
    if base == 0:
        set_reg(state, dst, [f"{disp:#x}", 0])
    else:
        b = state.get(base, ["?", 0])
        set_reg(state, dst, [b[0], b[1] + disp])

instrs = list(md.disasm(code, START))
# group by function (between rets)
funcs = []
cur = {"start": START, "reads": [], "consts": []}
state = new_state()
pending = None
for ins in instrs:
    if ins.address >= END:
        break
    mnem = ins.mnemonic
    ops = ins.operands
    if mnem == "ret" or mnem == "retn":
        cur["end"] = ins.address
        funcs.append(cur)
        cur = {"start": ins.address + 1, "reads": [], "consts": []}
        state = new_state()
        pending = None
        continue
    if mnem == "lea" and len(ops) == 2:
        lea(state, ops[0].reg, ops[1])
    elif mnem == "mov" and len(ops) == 2:
        if ops[1].type == 2:  # imm
            set_reg(state, ops[0].reg, [f"{ops[1].imm:#x}", 0])
        elif ops[1].type == 1:  # reg
            set_reg(state, ops[0].reg, list(state.get(ops[1].reg, ["?", 0])))
    elif mnem == "add" and len(ops) == 2 and ops[1].type == 2:
        r = ops[0].reg
        s = state.get(r, ["?", 0])
        s = list(s); s[1] += ops[1].imm
        set_reg(state, r, s)
    elif mnem == "inc" and len(ops) == 1:
        r = ops[0].reg
        s = state.get(r, ["?", 0])
        s = list(s); s[1] += 1
        set_reg(state, r, s)
    elif mnem == "push" and len(ops) == 1 and ops[0].type == 1:
        pending = state.get(ops[0].reg, ["?", 0])
    elif mnem == "push" and len(ops) == 1 and ops[0].type == 2:
        pending = [f"{ops[0].imm:#x}", 0]
    elif mnem == "call" and ops and ops[0].type == 2:
        t = ops[0].imm
        if t in PRIM:
            lbl, off = (pending if pending else ["?", 0])
            cur["reads"].append(f"{PRIM[t]}@{lbl}+{off:#x}")
            pending = None
        else:
            pending = None
            # small immediate loads as candidate counts
    # capture small immediate moves as candidate counts (only register-imm form)
    if mnem == "mov" and len(ops) == 2 and ops[1].type == 2 and 1 < ops[1].imm < 2000:
        cur["consts"].append((ins.address, ops[1].imm))

print(f"# {len(funcs)} serializer functions")
for f in funcs:
    print(f"\n### fn {f['start']:#010x}..{f.get('end',0):#010x}  reads={len(f['reads'])}")
    print("  consts:", f["consts"][:12])
    # print reads, collapsing consecutive identical targets would help but keep raw
    print("  ".join(f["reads"]))
