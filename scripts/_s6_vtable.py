"""S6 对象方法表 (0x49b960..0x49be00) 解析：
   逐个函数抽取 (字段偏移, 位宽, 方向, 钳制/比较立即数)。
   C++ __thiscall: this 在 ecx，字段 = [ecx + disp]。"""
from capstone import Cs, CS_ARCH_X86, CS_MODE_32
from capstone.x86 import X86_OP_MEM, X86_REG_ECX

IMG = open('scripts/_unpacked_mem.bin','rb').read()
BASE = 0x400000
START, END = 0x49b960, 0x49be00

md = Cs(CS_ARCH_X86, CS_MODE_32); md.detail = True

# 线性反汇编整段
code = IMG[START-BASE:END-BASE]
insts = list(md.disasm(code, START))

# 按 ret 切分函数（每个 getter/setter 以 ret 结束；含分支的函数取最后 ret）
funcs = []
cur = []
for ins in insts:
    cur.append(ins)
    if ins.mnemonic == 'ret':
        funcs.append(cur)
        cur = []
if cur: funcs.append(cur)

def analyze(fn):
    offs = {}        # disp -> {'w':set,'rw':set}
    clamps = []      # (imm, mnem)
    for ins in fn:
        if ins.mnemonic == 'cmp' and len(ins.operands) == 2 and ins.operands[1].type == 2:
            clamps.append((ins.operands[1].imm & 0xffff, ins.op_str))
        if ins.operands:
            for op in ins.operands:
                if op.type == X86_OP_MEM and op.mem.base == X86_REG_ECX:
                    disp = op.mem.disp & 0xff
                    w = 'W' if 'word' in ins.op_str else ('B' if 'byte' in ins.op_str else '?')
                    rw = 'W' if (ins.mnemonic=='mov' and 'ptr' in ins.op_str.split(',')[0]) else 'R'
                    offs.setdefault(disp, {'w':set(),'rw':set()})
                    offs[disp]['w'].add(w); offs[disp]['rw'].add(rw)
    return offs, clamps

print(f"共 {len(funcs)} 个函数")
for idx, fn in enumerate(funcs):
    fstart = fn[0].address
    offs, clamps = analyze(fn)
    if not offs and not clamps:
        # 可能用 lea 计算偏移，兜底打印前两条
        pass
    parts = []
    for d in sorted(offs):
        w = '/'.join(sorted(offs[d]['w']))
        rw = '/'.join(sorted(offs[d]['rw']))
        parts.append(f"+{d:02x}({w},{rw})")
    clamp_s = ''
    if clamps:
        clamp_s = '  CLAMP=' + ','.join(f'{hex(c)}' for c,_ in clamps)
    if parts or clamp_s:
        print(f"0x{fstart:06x}  {(' '.join(parts))}{clamp_s}")
