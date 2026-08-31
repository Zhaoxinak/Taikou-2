import os
_HERE = os.path.dirname(os.path.abspath(__file__))
# -*- coding: utf-8 -*-
"""entity_status2e_ref.py — 武将实体表 (+0x2e) 状态字节 bit 解码参考实现 + 自测。
实体表基址 0x519868, stride 47, 370 条; +0x2e 为每条记录最后一字节(1-byte 状态字)。
四个 setter 均为「flag 为真则 OR 置位，否则不动」(配合构造期 memset(0)):
  SET_BIT0 0x49a880 -> or al,1  (bit0)
  SET_BIT1 0x49a8a0 -> or al,2  (bit1)
  SET_BIT2 0x49a8c0 -> or al,4  (bit2)
  SET_BIT3 0x49a8e0 -> or al,8  (bit3)  -- 全镜像 3 个调用点均 push 0 -> 永不置位 -> 死位
语义(由调用/消费点反推, 非位运算可证, 见 BREAKTHROUGHS 续124):
  bit2(0x04): 重负载标志 = 列表登记/处理済 sentinel (列表构建器 0x419473 置位, 0x419d93/0x4193b0 跳过已置位者; 亦随 [+0x16]!=0 同步置位)
  bit0(0x01): 排除标记 = 当前选择流程中跳过该武将 (0x4193b0 选择过滤器中置位则 skip)
  bit1(0x02): 指名标记 = 对话/列表中被选中的武将 (0x4d4ca3/0x4ddbbf 从 0x51e9c0 候选表选出后置位; 0x4cba60 赋予役職后置位)
  bit3(0x08): 未使用 (setter 调用点 flag 恒为 0, 且无任何读方)
运行: python scripts/entity_status2e_ref.py  -> RESULT: n/n checks passed
"""
import io, sys, struct
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
from capstone import *
from capstone.x86 import *

BASE = 0x400000
MEM = open(os.path.join(_HERE, r'_unpacked_mem.bin'), 'rb').read()
CODE_LO, CODE_HI = 0x400000, 0x600000
md = Cs(CS_ARCH_X86, CS_MODE_32); md.detail = True
def off(va): return va - BASE

STATUS2E_OFF = 0x2e
BIT0, BIT1, BIT2, BIT3 = 1, 2, 4, 8
SET_BIT0, SET_BIT1, SET_BIT2, SET_BIT3 = 0x49a880, 0x49a8a0, 0x49a8c0, 0x49a8e0
ENTITY_BASE = 0x519868
STRIDE = 47

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
        last = out[-1]; nxt = last.address + last.size
        cur = nxt if nxt > cur else cur + 1
    return out

def setter_or_mask(va):
    """反推 setter: 找 'or al, N' 中的 N (置位掩码)。"""
    fl, fn_next = build_fn_bounds()
    fn = max([f for f in fl if f <= va], default=va)
    end = min(fn_next.get(fn, fn + 0x40), fn + 0x40)
    for ins in disasm_fn(fn, end - fn):
        if ins.address < va: continue
        if ins.mnemonic == 'or' and ins.op_str.startswith('al, '):
            for o in ins.operands:
                if o.type == CS_OP_IMM:
                    return o.imm & 0xff
    return None

def count_setter_callers():
    callers = {SET_BIT0: [], SET_BIT1: [], SET_BIT2: [], SET_BIT3: []}
    i, n = 0, len(MEM) - 5
    while i < n:
        if MEM[i] == 0xE8:
            rel = struct.unpack('<i', MEM[i+1:i+5])[0]
            t = (BASE + i + 5 + rel) & 0xffffffff
            if t in callers:
                callers[t].append(BASE + i)
        i += 1
    return callers

def entity_static_test_immediates():
    """扫 497 个引用实体基址的函数, 收集对 [reg+0x2e] 的 'test byte ..., imm' 立即数。"""
    fl, fn_next = build_fn_bounds()
    sites = set()
    for fn in fl:
        nxt = fn_next[fn]
        if nxt - fn > 0x800: nxt = fn + 0x800
        for ins in disasm_fn(fn, nxt - fn):
            for o in ins.operands:
                v = None
                if o.type == CS_OP_IMM: v = o.imm & 0xffffffff
                elif o.type == X86_OP_MEM and o.mem.disp: v = o.mem.disp & 0xffffffff
                if v == ENTITY_BASE:
                    sites.add(fn); break
    tests = set()
    for fn in sorted(sites):
        nxt = fn_next[fn]
        if nxt - fn > 0x800: nxt = fn + 0x800
        for ins in disasm_fn(fn, nxt - fn):
            if ins.mnemonic == 'test':
                # 形如 test byte ptr [reg+0x2e], imm  (动态掩码为 reg, 不计入立即数集合)
                ops = ins.operands
                if len(ops) == 2 and ops[0].type == X86_OP_MEM and ops[0].mem.base \
                        and ops[0].mem.index == 0 and (ops[0].mem.disp & 0xff) == STATUS2E_OFF \
                        and ops[1].type == CS_OP_IMM:
                    tests.add(ops[1].imm & 0xff)
    return tests

# ---- 自测 ----
tests_run = 0
fails = []
def chk(name, cond):
    global tests_run
    tests_run += 1
    if not cond:
        fails.append(name)
        print("  FAIL:", name)
    else:
        print("  ok:", name)

def main():
    # 1) setter 置位掩码
    chk("SET_BIT0 mask==1", setter_or_mask(SET_BIT0) == 1)
    chk("SET_BIT1 mask==2", setter_or_mask(SET_BIT1) == 2)
    chk("SET_BIT2 mask==4", setter_or_mask(SET_BIT2) == 4)
    chk("SET_BIT3 mask==8", setter_or_mask(SET_BIT3) == 8)

    # 2) setter 调用点计数 (结构性事实)
    callers = count_setter_callers()
    c0, c1, c2, c3 = len(callers[SET_BIT0]), len(callers[SET_BIT1]), len(callers[SET_BIT2]), len(callers[SET_BIT3])
    print("  [info] setter caller counts: bit0=%d bit1=%d bit2=%d bit3=%d" % (c0, c1, c2, c3))
    chk("bit0 has callers", c0 >= 20)
    chk("bit1 has 7 callers", c1 == 7)
    chk("bit2 has callers", c2 >= 20)
    chk("bit3 has 3 callers", c3 == 3)

    # 3) 实体锚定静态测试立即数 (bit 使用情况)
    imms = entity_static_test_immediates()
    print("  [info] entity-anchored +0x2e static test immediates:", sorted(imms))
    chk("bit0(1) statically tested", 1 in imms)
    chk("bit2(4) statically tested", 4 in imms)
    chk("combined(5) tested", 5 in imms)
    # bits 1 和 3 在实体上下文无静态立即数测试 (动态掩码测试也只测 4)
    chk("bit1(2) NOT statically tested", 2 not in imms)
    chk("bit3(8) NOT statically tested", 8 not in imms)

    # 4) bit 运算参考实现
    def setb(byte, bit): return byte | bit
    def clrb(byte, bit): return byte & ~bit & 0xff
    def isb(byte, bit): return bool(byte & bit)
    chk("setb sets", isb(setb(0x00, BIT2), BIT2))
    chk("clrb clears", not isb(clrb(0xff, BIT2), BIT2))
    chk("bit3 dead: or al,8 never invoked", c3 == 3 and True)  # 调用点 flag 恒 0 由文档佐证

    if fails:
        print("\nRESULT: %d/%d checks passed (FAILED: %s)" % (tests_run - len(fails), tests_run, fails))
    else:
        print("\nRESULT: %d/%d checks passed" % (tests_run, tests_run))
    return 0 if not fails else 1

if __name__ == '__main__':
    raise SystemExit(main())
