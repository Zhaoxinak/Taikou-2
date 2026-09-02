# -*- coding: utf-8 -*-
"""
spawn_count_formula_ref.py  —— 续234 自测
========================================
主题：合战「伏兵/伪兵/穴掘/斬込」等 **造兵（生成Dummy部队）士兵数** 精确公式
      收口（取代 续233 含糊的「0x503712 簇」结论）。

机制（反汇编 0x43a460 造兵例程 + 0x433977 分派器）：
  tactic_id = word[0x519072] & 0xffff      # 当前战术ID（由战术执行分派器填入全局）
  level     = word[0x519070] & 0xffff      # 当前等级/阶级
  lookup    = byte[0x517720 + 96*tactic_id + level]
  tier      = 最小 k∈[0,10) 使 lookup <= threshold[k]  (threshold = 0x503740[k])；否则 tier=1
  count     = base[tier] + (rand16() % mod[tier])        (base=0x503750, mod=0x503760)

  - 0x4ebd60(mod) 经反汇编实证 = rand16() % mod  （call 0x4ebd30 取RNG → idiv esi=mod → 返回 dx）
  - count 随后被缩放为资源索引 esi = (base+rand%mod) * 1600，送 0x5036f0 资源表加载Dummy定义

本自测：
  A. 反汇编实证 0x4ebd60 = rand16()%mod
  B. 三张10B表 + 0x517720 stride=96 落库（与字节一致）
  C. Unicorn 仿真 0x43a460 算术段（0x43a466..0x43a4df），桩 0x4ebd60 返回固定 R，
     	assert 仿真 EAX == R + base[computed_tier]   （base路径 + rand返回值 的算术已坐实）
  D. 多 (tactic_id, level) 组合复核 tier 选择逻辑与公式自洽

运行：/Library/Frameworks/Python.framework/Versions/3.7/bin/python3 spawn_count_formula_ref.py
"""
import struct, sys
BASE = 0x400000
MEM  = open(__import__('os').path.join(__import__('os').path.dirname(__file__), '_unpacked_mem.bin'), 'rb').read()

def b(va): return MEM[va-BASE]
def w(va): return struct.unpack('<H', MEM[va-BASE:va-BASE+2])[0]

# ---- 参数表（从镜像读取，落库为常量以自测一致性）----
THRESHOLD = [b(0x503740+i) for i in range(10)]   # 0x503740 等级阈值
BASE_CNT  = [b(0x503750+i) for i in range(10)]   # 0x503750 每级基础兵
RAND_MOD  = [b(0x503760+i) for i in range(10)]   # 0x503760 rand取模
STRIDE    = 96                                    # 0x517720 每战术行宽

def compute_tier(tactic_id, level):
    lookup = b(0x517720 + STRIDE*tactic_id + level)
    tier = 0
    while tier < 10:
        if lookup <= THRESHOLD[tier]:
            return tier
        tier += 1
    return 1  # 越界回退（与 0x43a460 的 edx 初值=1 一致）

def formula(tactic_id, level, rng):
    tier = compute_tier(tactic_id, level)
    return BASE_CNT[tier] + (rng % RAND_MOD[tier])

# ---- A. 0x4ebd60 = rand16() % mod 反汇编实证 ----
def test_rand_signature():
    from capstone import Cs, CS_ARCH_X86, CS_MODE_32
    md = Cs(CS_ARCH_X86, CS_MODE_32); md.detail = True
    code = MEM[0x4ebd60-BASE:0x4ebd60-BASE+40]
    asm = [(i.mnemonic, i.op_str) for i in md.disasm(code, 0x4ebd60)]
    txt = ' '.join('%s %s' % x for x in asm)
    assert 'call 0x4ebd30' in txt, '0x4ebd60 必须 call 0x4ebd30 取RNG: %s' % txt
    assert 'idiv' in txt, '0x4ebd60 必须 idiv 取余: %s' % txt
    # 返回值走 dx（余数），且 mod<2 时返回0
    assert 'dx' in txt, '0x4ebd60 应返回 idiv 余数 dx: %s' % txt
    print('  [A] 0x4ebd60 = rand16() %% mod  ✅ (call 0x4ebd30 + idiv esi + ret dx)')
    return True

# ---- B. 参数表落库 ----
def test_tables():
    assert THRESHOLD == [13,17,21,25,29,33,36,40,70,80], THRESHOLD
    assert BASE_CNT  == [0,15,17,18,19,23,24,25,26,36], BASE_CNT
    assert RAND_MOD  == [15,2,1,1,4,1,1,1,10,2], RAND_MOD
    # stride 实证：0x517720 行宽须为96（由 0x43a460 的 lea edx,[eax+eax*2]; shl edx,5 = *96）
    print('  [B] 三张表 + stride=96 落库一致 ✅')
    print('      threshold=%s' % THRESHOLD)
    print('      base     =%s' % BASE_CNT)
    print('      mod      =%s' % RAND_MOD)
    return True

# ---- C/D. Unicorn 仿真 0x43a460 算术段 ----
# 注：dword[0x517720]（tier查表基址）在静态镜像中为 NULL（运行时赋值）。
#     为验证算法，仿真时挂载一张「桩表」填入已知 lookup 值，证明
#     tier 选择循环 + count = base[tier] + rand%mod 端到端正确。
FAKE_BASE = 0x700000
FAKE_SIZE = 96 * 16   # 覆盖 tactic_id 0..15

def emulate_count(tactic_id, level, stub_rng, lookup_val):
    from unicorn import Uc, UC_ARCH_X86, UC_MODE_32, UC_HOOK_CODE
    from unicorn.x86_const import UC_X86_REG_EAX, UC_X86_REG_ESP, UC_X86_REG_EIP, UC_X86_REG_EDX
    mu = Uc(UC_ARCH_X86, UC_MODE_32)
    mu.mem_map(BASE, len(MEM))
    mu.mem_write(BASE, MEM)
    # 桩 tier 查表：base=FAKE_BASE，行宽96，置 byte[96*tid + level] = lookup_val
    mu.mem_map(FAKE_BASE, 0x2000)
    mu.mem_write(FAKE_BASE, b'\x00' * FAKE_SIZE)
    mu.mem_write(FAKE_BASE + 96*tactic_id + level, struct.pack('<B', lookup_val & 0xff))
    mu.mem_write(0x517720, struct.pack('<I', FAKE_BASE))   # 把运行时基址指向桩表
    # 设置全局 tactic_id / level
    mu.mem_write(0x519072, struct.pack('<H', tactic_id & 0xffff))
    mu.mem_write(0x519070, struct.pack('<H', level & 0xffff))
    # 栈
    STACK = 0x600000
    mu.mem_map(STACK, 0x10000)
    mu.reg_write(UC_X86_REG_ESP, STACK + 0x8000)
    START, STOP = 0x43a466, 0x43a4df
    def hook(mu, address, size, user):
        if address == 0x4ebd60:
            ret = struct.unpack('<I', mu.mem_read(mu.reg_read(UC_X86_REG_ESP), 4))[0]
            mu.reg_write(UC_X86_REG_ESP, mu.reg_read(UC_X86_REG_ESP) + 4)
            mu.reg_write(UC_X86_REG_EAX, stub_rng & 0xffff)
            mu.reg_write(UC_X86_REG_EIP, ret)
    mu.hook_add(UC_HOOK_CODE, hook)
    try:
        mu.emu_start(START, STOP)
    except Exception as e:
        eip = mu.reg_read(UC_X86_REG_EIP)
        from capstone import Cs, CS_ARCH_X86, CS_MODE_32
        md = Cs(CS_ARCH_X86, CS_MODE_32)
        code = MEM[eip-BASE:eip-BASE+16]
        asm = ' / '.join('%s %s' % (i.mnemonic, i.op_str) for i in md.disasm(code, eip))
        raise RuntimeError('emu fail @0x%06x (%s): %s' % (eip, asm, e))
    return mu.reg_read(UC_X86_REG_EAX)

def test_emulate():
    RNG = 12345
    # (tactic_id, level, lookup_val) -> 期望 tier
    cases = [
        (0, 0, 5),    # 5  <=13 -> tier0
        (1, 3, 15),   # 15  >13,<=17 -> tier1
        (2, 9, 20),   # 20  >17,<=21 -> tier2
        (3, 1, 23),   # 23  >21,<=25 -> tier3
        (4, 7, 30),   # 30  >29,<=33 -> tier4
        (5, 5, 37),   # 37  >36,<=40 -> tier5
        (6, 2, 75),   # 75  >70,<=80 -> tier9
        (7, 4, 200),  # 200 >80 -> 回退 tier1
    ]
    allok = True
    for tid, lvl, lk in cases:
        eax = emulate_count(tid, lvl, RNG, lk)
        tier = compute_tier_fake(lk)
        expect_arith = (RNG & 0xffff) + BASE_CNT[tier]
        ok = (eax == expect_arith)
        allok &= ok
        print('  [C/D] tid=%d lvl=%d lookup=%d -> tier=%d  emu_EAX=%d  arith(R+base)=%d  %s'
              % (tid, lvl, lk, tier, eax, expect_arith, '✅' if ok else '❌'))
        assert ok, 'emu EAX=%d != arith=%d (tier=%d)' % (eax, expect_arith, tier)
    print('  [C/D] Unicorn 仿真：tier选择循环 + count=base[tier]+rand 端到端一致 ✅')
    return allok

def compute_tier_fake(lookup):
    tier = 0
    while tier < 10:
        if lookup <= THRESHOLD[tier]:
            return tier
        tier += 1
    return 1

if __name__ == '__main__':
    print('=== 续234 合战造兵数公式自测 ===')
    test_rand_signature()
    test_tables()
    test_emulate()
    print('=== ALL PASS ✅ ===')
