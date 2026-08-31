"""针对 S6 +0x16/18/1a 三个 60000 字段，dump 全部绝对地址引用的指令 + 上下文。
注意：_insn_addrs.pkl 的键是【文件偏移】(0x1000 = VA 0x401000)，VALUE=[size,text]。
所有查找都以文件偏移进行，反汇编时 IMG[off:] @ VA=BASE+off。
"""
import pickle, struct
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

BASE = 0x400000
IMG = open('scripts/_unpacked_mem.bin', 'rb').read()
d, starts = pickle.load(open('scripts/_insn_addrs.pkl', 'rb'))
# 键 = 文件偏移
SIZE = {off: s[0] for off, s in d.items()}
TEXT = {off: s[1] for off, s in d.items()}
STARTS = sorted(starts)  # 这些也是文件偏移
md = Cs(CS_ARCH_X86, CS_MODE_32); md.detail = False

def find_insn_off(va):
    """返回包含 va 的指令的【文件偏移】。"""
    t = va - BASE
    for j in range(max(0, t - 16), t + 1):
        if j in SIZE and j <= t < j + SIZE[j]:
            return j
    return None

def func_off_of(off):
    """最近的前驱 starts（文件偏移）作为函数入口。"""
    best = None
    for s in STARTS:
        if s <= off:
            if best is None or s > best: best = s
        else:
            break
    return best if best is not None else off

def refs_for(imm):
    pat = struct.pack('<I', imm)
    out = []
    o = 0
    while True:
        i = IMG.find(pat, o)
        if i < 0: break
        o = i + 1
        hit = find_insn_off(BASE + i)
        if hit is None or hit not in SIZE: continue
        sz = SIZE[hit]
        b = list(md.disasm(IMG[hit: hit + sz + 16], BASE + hit))
        if not b: continue
        ins = b[0]
        out.append((hit, f'{ins.mnemonic} {ins.op_str}'))
    return out

for disp in (0x16, 0x18, 0x1a):
    imm = 0x516610 + disp
    refs = refs_for(imm)
    print(f"\n{'='*64}\n+{disp:02x} (0x{imm:06x}) : {len(refs)} 处引用\n{'='*64}")
    for off, txt in refs:
        va = BASE + off
        fn = func_off_of(off)
        print(f"  0x{va:06x} [{txt}]  (fn 0x{BASE+fn:06x})")
        print(f"    --- fn 0x{BASE+fn:06x} 上下文 (前0x80) ---")
        n = 0
        for ins in md.disasm(IMG[fn: fn + 0x80], BASE + fn):
            mark = ' >>>' if ins.address == va else '    '
            print(f"    {mark}0x{ins.address:06x}  {ins.mnemonic} {ins.op_str}")
            n += 1
            if n > 24: break
