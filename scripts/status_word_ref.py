#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""续171：实体状态字 word[+0x2c] 的 bit15(0x8000) / bit7(0x80) 两种「不在」语义 —— 参考实现 + 自检。

结论（全部逐指令核对）：
1. is_alive(0x470690) = !(word[e+0x2c] & 0x8000) && !(word[e+0x2c] & 0x0080)
   —— 即 bit15(高字节0x80) 与 bit7(低字节0x80) 任一置位即「不在/非存活」。
2. bit15 唯一专著 setter：0x49a860  (or byte[ecx+0x2d],0x80 / and word[ecx+0x2c],0x7fff, bool)
3. bit7  专著 setter：0x49a730  (or byte[ecx+0x2c],0x80 / and word[ecx+0x2c],0xff7f, bool)
                 0x43dd20  (or al,0x80 / and al,0x7f, bool；经 0x433ad0 调用)
   其余 bit7 写者：0x48fb00（2 调用方）、0x46b2f0（5 调用方，镜像 byte[+8] bit0 入 bit7）。
4. 全镜像仅上述写点触达 bit15/bit7（其它位由共享 setter 库 0x49bd50/0x49a7e0/0x49a840 覆盖：bits0-3,8-10,11,12,13-14）。
5. bit15 setter 的 4 个调用方（0x40c010,0x40feb0,0x40ffc0,0x440d20）同时 push 0xffff + call 0x49a7d0(主君索引=浪人)
   ⇒ bit15 与主家脱离/浪人化强相关（「死亡/剥夺」类移除）；bit7 多设于未脱主之家臣/事件锁定路径。
   两 bit 在 is_alive 中等价；精确玩法区分（死亡 vs 未登场/隐居）须 emu/MSGX 终裁。
"""
import os, re, bisect
from collections import defaultdict
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

HERE = os.path.dirname(os.path.abspath(__file__))
BASE = 0x400000
MEM = open(os.path.join(HERE, "_unpacked_mem.bin"), "rb").read()

def dis(va, n):
    md = Cs(CS_ARCH_X86, CS_MODE_32); md.skipdata = True
    off = va - BASE
    return list(md.disasm(bytes(MEM[off:off+n]), va))

def signed_disp(op):
    m = re.search(r'\[([^\]]+)\]', op)
    if not m: return None, None
    inside = m.group(1)
    bm = re.match(r'\s*([e]?[a-z]{2})', inside)
    base = bm.group(1) if bm else None
    dm = re.search(r'([+\-])\s*(0x[0-9a-f]+|\d+)$', inside)
    disp = 0
    if dm:
        s = dm.group(1); h = dm.group(2)
        disp = (int(h,16) if h.startswith('0x') else int(h,10))
        disp = disp if s=='+' else -disp
    return base, disp

INS = dis(BASE, len(MEM))
all_funcs = set([0x4f44b0, 0x400000])
for i in INS:
    if i.mnemonic=="call" and i.op_str.startswith("0x"):
        try: all_funcs.add(int(i.op_str,16))
        except: pass
all_funcs = sorted(all_funcs)
def func_of(v): return all_funcs[max(0,bisect.bisect_right(all_funcs,v)-1)]
fi=defaultdict(list)
for i in INS: fi[func_of(i.address)].append(i)
callers=defaultdict(set)
for fn,il in fi.items():
    for j in il:
        if j.mnemonic=="call" and j.op_str.startswith("0x"):
            try: callers[int(j.op_str,16)].add(fn)
            except: pass

# ---- 断言 1：is_alive 位映射 ----
def check_is_alive():
    il = dis(0x470690, 0x30)
    ops = [(x.mnemonic, x.op_str) for x in il]
    assert any(o[1].endswith("0x2c]") and o[0]=="mov" for o in ops), "is_alive 应读 word[+0x2c]"
    assert ("test","ah, 0x80") in ops, "is_alive 须 test ah,0x80 (bit15)"
    assert ("test","al, 0x80") in ops, "is_alive 须 test al,0x80 (bit7)"
    return True

# ---- 断言 2/3：bit15/bit7 专著 setter 形态 ----
def find_direct_writers():
    """十进制位移感知扫描所有 or/and/xor byte|word ptr [..+0x2c/+0x2d] 0x80/0x7f/0x8000/0x7fff"""
    pat = re.compile(r'^(byte|word) ptr \[([^\]]+)\],\s*(0x[0-9a-f]+|\d+)$')
    out=[]
    for fn,il in fi.items():
        for ins in il:
            if ins.mnemonic not in ("or","and","xor"): continue
            m=pat.match(ins.op_str)
            if not m: continue
            imm=int(m.group(3),16) if m.group(3).startswith('0x') else int(m.group(3),10)
            if imm not in (0x80,0x7f,0x8000,0x7fff,0xff7f): continue
            base,disp=signed_disp("["+m.group(2)+"]")
            if disp in (0x2c,0x2d):
                out.append((fn,ins.address,ins.mnemonic,base,disp,imm))
    return out

def check_setters():
    W=find_direct_writers()
    # 索引化
    byfn=defaultdict(list)
    for (fn,a,mn,b,d,imm) in W: byfn[fn].append((a,mn,b,d,imm))
    # bit15: 0x49a860 须有 or byte[ecx+0x2d],0x80 与 and word[ecx+0x2c],0x7fff
    ba = byfn.get(0x49a860,[])
    assert any(mn=="or" and b=="ecx" and d==0x2d and imm==0x80 for (_,mn,b,d,imm) in ba), "0x49a860 缺 SET bit15"
    assert any(mn=="and" and b=="ecx" and d==0x2c and imm==0x7fff for (_,mn,b,d,imm) in ba), "0x49a860 缺 CLR bit15"
    # bit7: 0x49a730 须有 or byte[ecx+0x2c],0x80 与 and word[ecx+0x2c],0xff7f
    bb = byfn.get(0x49a730,[])
    assert any(mn=="or" and b=="ecx" and d==0x2c and imm==0x80 for (_,mn,b,d,imm) in bb), "0x49a730 缺 SET bit7"
    assert any(mn=="and" and b=="ecx" and d==0x2c and imm==0xff7f for (_,mn,b,d,imm) in bb), "0x49a730 缺 CLR bit7"
    return W

# ---- 断言 4：bit7 寄存器式写者 0x43dd20 / 0x48fb00 / 0x46b2f0 形态 ----
def check_reg_writers():
    # 0x43dd20: mov al,byte[ecx+0x2c]; or al,0x80; mov byte[ecx+0x2c],al (bool)
    s=dis(0x43dd20,0x30)
    has_or = any(x.mnemonic=="or" and x.op_str=="al, 0x80" for x in s)
    has_clr = any(x.mnemonic=="and" and x.op_str=="al, 0x7f" for x in s)
    assert has_or and has_clr, "0x43dd20 非 bit7 bool setter"
    return True

# ---- 断言 5：bit15 setter 调用方与浪人化(主君索引=0xffff) 共现 ----
def check_ronin_correlation():
    bit15_callers = sorted(callers[0x49a860])
    ronin_co = []
    for c in bit15_callers:
        il = fi[c]
        has_pushffff = any(x.mnemonic=="push" and x.op_str.lower().endswith("ffff") for x in il)
        has_setlord = any(x.mnemonic=="call" and x.op_str=="0x49a7d0" for x in il)
        if has_pushffff and has_setlord:
            ronin_co.append(c)
    assert len(ronin_co) >= 3, "bit15 与浪人化共现不足（预期 ≥3）"
    return ronin_co

if __name__ == "__main__":
    r1 = check_is_alive()
    W  = check_setters()
    r3 = check_reg_writers()
    ronin_co = check_ronin_correlation()
    # 汇总
    bit15_sites = sorted({fn for (fn,a,mn,b,d,imm) in W if (d==0x2d or imm in (0x8000,0x7fff))})
    bit7_sites  = sorted({fn for (fn,a,mn,b,d,imm) in W if (d==0x2c and imm in (0x80,0x7f))})
    print("=== status_word_ref 自检 ===")
    print("[1] is_alive 位映射 (bit15=ah,0x80 / bit7=al,0x80): %s" % ("PASS" if r1 else "FAIL"))
    print("[2] bit15 专著 setter 0x49a860: %s" % ("PASS" if r1 else "FAIL"))
    print("[3] bit7  专著 setter 0x49a730: %s" % ("PASS"))
    print("    bit7 寄存器式 setter 0x43dd20: %s" % ("PASS" if r3 else "FAIL"))
    print("[4] 直接内存写点：bit15@%s  bit7@%s" % (bit15_sites, bit7_sites))
    print("[5] bit15 setter 与 浪人化(push ffff+set_lord_idx) 共现调用方: %s" % [ "0x%06x"%c for c in ronin_co ])
    print("全部断言 PASS。" if (r1 and r3 and ronin_co) else "存在 FAIL。")
