# -*- coding: utf-8 -*-

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
# _status2d_extract.py — 找 +0x2d 高字节 F2B(2-bit) 取值→dispatch 点，以及 F4 写入点(or/and byte[+0x2d])
import io, sys, struct
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
from capstone import *
from capstone.x86 import *

BASE = 0x400000
MEM = open(_ROOT + '/scripts/_unpacked_mem.bin', 'rb').read()
md = Cs(CS_ARCH_X86, CS_MODE_32); md.detail = True
def off(v): return v - BASE
def dis(va, n): return list(md.disasm(MEM[off(va):off(va)+n], va))
def rname(o):
    try: return md.reg_name(o.reg)
    except Exception: return None

# 1) F2B 取值点: 读 byte[reg+0x2d] 后 shr 5 / and 3 ; 或 读 word[reg+0x2c] 后 shr 0xd / and 3
print("===== F2B 取值/dispatch 点 (shr 5 + and 3 / shr 0xd + and 3) =====")
hits = []
i, n = 0, len(MEM) - 12
while i < n:
    ins_list = dis(BASE + i, 12)
    for k, ins in enumerate(ins_list):
        if ins.address != BASE + i: break
        # 找 shr reg, 5 或 shr reg, 0xd
        if ins.mnemonic == 'shr' and len(ins.operands) == 2 and ins.operands[1].type == CS_OP_IMM and ins.operands[1].imm in (5, 0xd):
            # 检查前 4 条是否读 byte[+0x2d] 或 word[+0x2c] 到同寄存器
            reg = rname(ins.operands[0])
            found = False
            for j in range(max(0,k-4), k):
                p = ins_list[j]
                if len(p.operands) >= 1 and p.operands[0].type == CS_OP_REG and rname(p.operands[0]) == reg:
                    if len(p.operands) == 2 and p.operands[1].type == CS_OP_MEM and p.operands[1].mem.index == 0:
                        d = p.operands[1].mem.disp & 0xffffffff
                        if d in (0x2d, 0x2c):
                            found = True; break
            if found:
                # 后 3 条是否 and 3
                nxt = ins_list[k+1] if k+1 < len(ins_list) else None
                and3 = nxt and nxt.mnemonic == 'and' and len(nxt.operands)==2 and nxt.operands[1].type==CS_OP_IMM and nxt.operands[1].imm==3
                hits.append((ins.address, reg, d if found else None, and3))
    i += 1
for va, reg, src, a3 in hits:
    print("  0x%x : shr %s,%s after load %s  and3=%s" % (va, reg, '5' if va else '?', src, a3))

# 2) F4 写入点: or byte[reg+0x2d],0x10 ; and byte[reg+0x2d],0xef ; 以及通过 packer 0x49a7e0 的 arg bit4
print("\n===== F4 写入点 (or/and byte[+0x2d] 带 0x10/0xef) =====")
f4w = []
i, n = 0, len(MEM) - 8
while i < n:
    ins_list = dis(BASE + i, 8)
    for ins in ins_list:
        if ins.address != BASE + i: break
        if ins.mnemonic in ('or','and') and len(ins.operands)==2:
            op0, op1 = ins.operands
            if op0.type == CS_OP_MEM and op0.mem.index == 0 and (op0.mem.disp & 0xffffffff)==0x2d and op1.type==CS_OP_IMM:
                m = op1.imm & 0xff
                if m in (0x10, 0xef):
                    f4w.append((ins.address, ins.mnemonic, m))
    i += 1
for va, mn, m in f4w:
    print("  0x%x : %s byte[+0x2d], 0x%x" % (va, mn, m))
print("  (若仅 0x49a828/0x49a82f 自身出现，则 F4 由 packer 0x49a7e0 经 arg 写入)")

# 3) packer 0x49a7e0 调用点: arg (push) 是否带 bit4(0x10)
print("\n===== packer 0x49a7e0 调用点 arg 含 bit4?(即 0x10) =====")
pk=[]
i, n = 0, len(MEM) - 5
while i < n:
    if MEM[i] == 0xE8:
        rel = struct.unpack('<i', MEM[i+1:i+5])[0]
        t = (BASE + i + 5 + rel) & 0xffffffff
        if t == 0x49a7e0:
            ca = BASE + i
            pre = dis(ca-32, 32)
            arg = '?'
            for ins in pre:
                if ins.address >= ca: break
                if ins.mnemonic == 'push':
                    arg = ins.op_str
                    if arg.startswith('0x') or arg.isdigit():
                        arg = int(arg, 16) if arg.startswith('0x') else int(arg)
            pk.append((ca, arg))
    i += 1
print("  packer callers=%d" % len(pk))
for ca, arg in pk[:60]:
    bit4 = (isinstance(arg,int) and (arg & 0x10)) if isinstance(arg,int) else False
    if bit4:
        print("  0x%x push=0x%x  (bit4 SET!)" % (ca, arg))
print("  (仅列出 bit4 置位的 packer 调用; 若无则说明 F4 由 inline 或 0x49a828 写入)")
