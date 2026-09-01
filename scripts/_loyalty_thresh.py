
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

THRESH = {0x28: '40', 0x32: '50', 0x5f: '95', 0x64: '100'}

# 全镜像扫描 cmp byte[reg+0x29], imm
hits = []
i, n = 0, len(MEM) - 6
while i < n:
    b = MEM[i]
    if b == 0x80:  # cmp imm
        # 0x80 /7 ib : 80 /r ib ; modrm
        modrm = MEM[i+1]
        if modrm & 0x38 == 0x38:  # /7 = cmp
            mod = modrm >> 6
            rm = modrm & 7
            # 只取 mem 寻址且 disp32/disp8 且 base 是 reg
            if mod == 1 or mod == 2:  # disp8/disp32
                if rm != 4 and rm != 5:  # 非 SIB / 非 disp32-only
                    disp_off = 2 if mod == 1 else 3
                    disp = MEM[i+disp_off] if mod == 1 else struct.unpack('<i', MEM[i+disp_off:i+disp_off+4])[0]
                    if (disp & 0xff) == 0x29:
                        imm = MEM[i + (3 if mod==1 else 6)] if mod==1 else MEM[i+7]
                        if imm in THRESH:
                            hits.append((BASE+i, imm))
    i += 1

print("=== cmp byte[reg+0x29], {40/50/95/100} 命中 ===")
for va, imm in hits:
    print("  0x%x: cmp 0x%x (%s)" % (va, imm, THRESH[imm]))

# 反汇编 40 与 95 的上下文
for tgt_imm in (0x28, 0x5f):
    sites = [va for va, imm in hits if imm == tgt_imm]
    print("\n===== 阈值 %d (0x%x) : %d 处 =====" % (THRESH[tgt_imm] and int(THRESH[tgt_imm]), tgt_imm, len(sites)))
    for s in sites[:6]:
        print("  --- 0x%x ---" % s)
        for ins in dis(s-0x30, 0x70):
            mk = '  <<<' if ins.address == s else ''
            print("    0x%x: %s %s%s" % (ins.address, ins.mnemonic, ins.op_str, mk))
