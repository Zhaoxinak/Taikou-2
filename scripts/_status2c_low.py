# -*- coding: utf-8 -*-
# _status2c_low.py — 全镜像扫 +0x2c 低字节(byte ptr [reg+0x2c]) 的 setter / 消费者。
# 排除 esp 基址（栈局部变量噪声）；ebp 保留但标记（MSVC /Oy 下 ebp 是通用寄存器）。
import io, sys, struct
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
from capstone import *
from capstone.x86 import *

BASE = 0x400000
MEM = open('scripts/_unpacked_mem.bin', 'rb').read()
CODE_LO, CODE_HI = 0x400000, 0x600000
md = Cs(CS_ARCH_X86, CS_MODE_32); md.detail = True
def off(va): return va - BASE

WR = {'mov', 'or', 'and', 'xor', 'add', 'sub', 'shl', 'shr', 'inc', 'dec'}
TGT = 0x2c

def build_fn_bounds():
    fn_starts = set()
    i, n = 0, len(MEM) - 5
    while i < n:
        b = MEM[i]
        if b == 0xE8:
            rel = struct.unpack('<i', MEM[i+1:i+5])[0]
            t = (BASE + i + 5 + rel) & 0xffffffff
            if CODE_LO <= t < CODE_HI: fn_starts.add(t)
        elif b in (0xC3, 0xC2): fn_starts.add(BASE + i + 1)
        elif b == 0xE9:
            rel = struct.unpack('<i', MEM[i+1:i+5])[0]
            t = (BASE + i + 5 + rel) & 0xffffffff
            if t > BASE + i and CODE_LO <= t < CODE_HI: fn_starts.add(t)
        i += 1
    k = 0
    while True:
        p = MEM.find(b'\x55\x89\xe5', k)
        if p < 0: break
        fn_starts.add(BASE + p); k = p + 1
    fl = sorted(fn_starts)
    nxt = {}
    for i2 in range(len(fl)):
        nxt[fl[i2]] = fl[i2+1] if i2+1 < len(fl) else fl[i2] + 0x800
    return fl, nxt

def disasm_fn(va, max_bytes):
    end = va + max_bytes; cur = va; out = []
    while cur < end:
        chunk = MEM[off(cur):off(end)]
        got = list(md.disasm(chunk, cur))
        if not got: cur += 1; continue
        for ins in got:
            if ins.address >= end: break
            out.append(ins)
        last = out[-1]; n2 = last.address + last.size
        cur = n2 if n2 > cur else cur + 1
    return out

def main():
    fl, fn_next = build_fn_bounds()
    byimm = {}          # imm -> list of (addr, m, ops, fn)
    noimm = []          # 无立即数
    wordlow = []        # word ptr 且 imm<0x100
    fncount = {}
    for fn in fl:
        nxt = fn_next[fn]
        if nxt - fn > 0x800: nxt = fn + 0x800
        try:
            insns = disasm_fn(fn, nxt - fn)
        except Exception:
            continue
        for ins in insns:
            ops = ins.op_str
            if '0x2c]' not in ops and '+ 0x2c]' not in ops:
                continue
            memop = None
            for o in ins.operands:
                if o.type == CS_OP_MEM and (o.mem.disp & 0xfff) == TGT:
                    memop = o; break
            if memop is None:
                continue
            bname = md.reg_name(memop.mem.base) if memop.mem.base else None
            if bname == 'esp':
                continue  # 栈局部，跳过
            is_byte = 'byte ptr' in ops
            is_word = 'word ptr' in ops
            imm = None
            if len(ins.operands) > 1 and ins.operands[1].type == CS_OP_IMM:
                imm = ins.operands[1].imm & 0xffffffff
            e = (ins.address, ins.mnemonic, ops, fn, imm, is_byte, is_word)
            if is_word and imm is not None and imm < 0x100:
                wordlow.append(e)
            if is_byte:
                if imm is not None:
                    byimm.setdefault(imm, []).append(e)
                else:
                    noimm.append(e)
                fncount[fn] = fncount.get(fn, 0) + 1
    print("##### byte[+0x2c] 按立即数分组 #####")
    for imm in sorted(byimm):
        lst = byimm[imm]
        print(f"\n--- imm=0x{imm:x} ({imm}) : {len(lst)} 处 ---")
        for (a, m, ops, fn, im, ib, iw) in lst[:40]:
            print(f"  0x{a:x}: {m} {ops}   fn=0x{fn:x}")
    print("\n##### byte[+0x2c] 无立即数 (寄存器/动态) #####")
    for (a, m, ops, fn, im, ib, iw) in noimm[:60]:
        print(f"  0x{a:x}: {m} {ops}   fn=0x{fn:x}")
    print(f"\n##### word[+0x2c] 低字节级立即数 (<0x100) : {len(wordlow)} 处 #####")
    for (a, m, ops, fn, im, ib, iw) in wordlow[:60]:
        print(f"  0x{a:x}: {m} {ops}   fn=0x{fn:x}")
    print("\n##### 含 byte[+0x2c] 的函数（按次数排序，寻找 setter 簇） #####")
    for fn, c in sorted(fncount.items(), key=lambda x: -x[1])[:30]:
        print(f"  fn=0x{fn:x}: {c} 次")
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
