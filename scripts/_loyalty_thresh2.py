
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
import io, sys, struct
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
from capstone import *
from capstone.x86 import *

BASE = 0x400000
MEM = open(_ROOT + '/scripts/_unpacked_mem.bin', 'rb').read()
md = Cs(CS_ARCH_X86, CS_MODE_32)
md.detail = True

def off(v): return v - BASE
def dis(v, n):
    return list(md.disasm(MEM[off(v):off(v)+n], v))

# 1) 所有 cmp imm 在 0x28/0x5f 附近是否读 byte[+0x29]
def is_read_29(ins):
    if ins.mnemonic not in ('mov', 'movzx', 'movsx'):
        return False
    if len(ins.operands) != 2: return False
    src = ins.operands[1]
    if src.type != CS_OP_MEM: return False
    if src.mem.base == 0 and src.mem.index == 0: return False
    return (src.mem.disp & 0xff) == 0x29

candidates = []
i, n = 0, len(MEM) - 8
while i < n:
    data = MEM[i:i+8]
    try:
        ins = next(md.disasm(data, BASE+i))
    except Exception:
        i += 1; continue
    # cmp r/m8, imm8  (0x80 /7)  or cmp r/m32, imm (0x81 /7)
    if ins.mnemonic == 'cmp' and len(ins.operands) == 2:
        op1, op2 = ins.operands
        if op2.type == CS_OP_IMM:
            imm = op2.imm & 0xff
            if imm in (0x28, 0x5f):
                # 回看前若干指令是否有读 byte[+0x29]
                ctx = dis(BASE+i-0x20, 0x28)
                for c in ctx:
                    if is_read_29(c):
                        candidates.append((BASE+i, imm, c.address))
                        break
    i = (BASE+i - BASE) + ins.size

print("=== cmp imm 0x28/0x5f 且前驱读 byte[+0x29] ===")
for va, imm, rd in candidates:
    print("  cmp@0x%x imm=0x%x (%d)  <- read@0x%x" % (va, imm, imm, rd))

# 2) 反向：所有读 byte[+0x29] 后紧跟的 cmp 立即数分布
print("\n=== 读 byte[+0x29] 后 3 条内 cmp 立即数分布 ===")
dist = {}
i, n = 0, len(MEM) - 12
while i < n:
    data = MEM[i:i+12]
    try:
        ins = next(md.disasm(data, BASE+i))
    except Exception:
        i += 1; continue
    if is_read_29(ins):
        va = BASE + i
        nxt = dis(va+ins.size, 0x14)
        for k in range(1, len(nxt)):
            c = nxt[k]
            if c.mnemonic == 'cmp' and len(c.operands) == 2 and c.operands[1].type == CS_OP_IMM:
                imm = c.operands[1].imm & 0xff
                dist[imm] = dist.get(imm, 0) + 1
    i = (BASE+i - BASE) + ins.size

for imm in sorted(dist):
    print("  imm=0x%x (%d) : %d 次" % (imm, imm, dist[imm]))
