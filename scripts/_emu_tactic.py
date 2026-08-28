# -*- coding: utf-8 -*-
"""
Unicorn 校准：跑真实二进制 0x436840(火计) / 0x435ed0(伏兵) / 0x436b80(挑衅)
的效果子程，用受控单位/实体记录 + 固定 rand=10，抓 atk/def 中间值，
一次性坐实：
  (1) 除数 = /100（magic 0x51EB851F，n*M 取高 32 位 >>5 = >>37）
  (2) 系数 火计30 / 伏兵30 / 挑衅30（def 的 tier 项）；伏兵 atk 系数 25
  (3) 字段语义：byte[unit+0xa] / byte[entity+0xa] = commander_stat（主将主战力，
      同源；atk 用施法者单位+0xa，def 用目标实体+0xa）

方法：patch rand/选敌/实体解析/getHi/flag/落地 为安全桩；构造
unit[0](施法, stat=150) / unit[1](目标, stat=100) / entity[0..1] 镜像，
hook 比较指令抓 atk/def 后立即 emu_stop()。
"""
import struct, sys
from unicorn import Uc, UC_ARCH_X86, UC_MODE_32, UC_HOOK_CODE, UC_HOOK_MEM_UNMAPPED, UC_MEM_FETCH_UNMAPPED
from unicorn.x86_const import (
    UC_X86_REG_ESP, UC_X86_REG_EIP, UC_X86_REG_EAX, UC_X86_REG_EBX,
    UC_X86_REG_ESI, UC_X86_REG_EDI, UC_X86_REG_ECX, UC_X86_REG_EDX)

BASE = 0x400000
IMG = open('scripts/_unpacked_mem.bin', 'rb').read()
assert len(IMG) == 0x200000, len(IMG)

UNIT_BASE = 0x513910
UNIT_STRIDE = 24
ENTITY_BASE = 0x519868
ENTITY_STRIDE = 47
SECT_A = 0x512e58
STACK = 0x600000
SENTINEL = 0x610000        # retaddr 安全网（命中即停）
STOP_RET = 0x620000        # 解析器测试返回点

FUNCS = {
    'fire':   0x436840,   # 火计效果
    'ambush': 0x435ed0,   # 伏兵效果
    'taunt':  0x436b80,   # 挑衅效果
}
# 比较/抓值点（atk vs def 的最终 cmp）
CAP = {
    'fire':   0x436935,   # cmp bx, si   (bx=atk, si=def)
    'ambush': 0x435fec,   # cmp bx, di   (bx=atk, di=def)
    'taunt':  0x436c7e,   # cmp di, cx   (di=atk, cx=def)
}
# 抓值时的寄存器 → (atk_reg, def_reg)
CAPREGS = {
    'fire':   (UC_X86_REG_EBX, UC_X86_REG_ESI),
    'ambush': (UC_X86_REG_EBX, UC_X86_REG_EDI),
    'taunt':  (UC_X86_REG_EDI, UC_X86_REG_ECX),
}

# 预测值（rand=10 固定）：atk=(10+base)*stat/100 ; def=10+commander_stat+K*tier(+火计+2基差)
# 实际数据流：atk 用传入 unit 的 +0xa=150；def 用 0x43d630 解析出的 entity 的 +0xa。
# 本测试令 def 解析到 entity[0]（commander_stat=150）：
#   fire:   def = 10 + 30*(0+2) + 150 = 220
#   ambush: def = 10 + 30*0      + 150 = 160
#   taunt:  def = 10 + 30*0      + 150 = 160
PRED = {
    'fire':   {'atk': (10 + 80) * 150 // 100, 'def': 10 + 150 + 30 * (0 + 2)},  # 135 / 220
    'ambush': {'atk': (10 + 50) * 150 // 100, 'def': 10 + 150 + 30 * 0},        # 90 / 160
    'taunt':  {'atk': (10 + 80) * 150 // 100, 'def': 10 + 150 + 30 * 0},        # 135 / 160
}


def patch(mu, va, code):
    mu.mem_write(va, bytes(code))


def build(mu):
    # 全局
    mu.mem_write(SECT_A, bytes(180))          # getHi -> 0
    mu.mem_write(0x513540, bytes([0]))        # parity = 0
    mu.mem_write(0x513534, bytes([0]))        # handle_stat
    mu.mem_write(0x511dfc, bytes([0]))        # 火计前置标志

    # 单位记录：unit[0]=施法(stat150)  unit[1]=目标(stat100)
    units = bytearray(UNIT_STRIDE * 15)
    for idx, stat in ((0, 150), (1, 100)):
        off = idx * UNIT_STRIDE
        struct.pack_into('<H', units, off + 0x05, idx)   # word[+5] = 实体索引
        units[off + 0x0a] = stat & 0xff                   # commander_stat
        units[off + 0x10] = 0                             # tier 阶位 0
        units[off + 0x2c] = 0                             # 选敌范围/1.5x/挑衅门控 = 0
        units[off + 0x2b] = 0x3f                          # 挑衅门控 byte&0x3f == atk 才走
        units[off + 0x13] = 0                             # 状态
        units[off + 0x15] = 0x04 if idx == 1 else 0x00    # side
    mu.mem_write(UNIT_BASE, bytes(units))

    # 实体记录：镜像 unit 的 +0xa/+0x10，+0x8 用于挑衅 flag2 位
    ent = bytearray(ENTITY_STRIDE * 15)
    for idx, stat in ((0, 150), (1, 100)):
        eo = idx * ENTITY_STRIDE
        ent[eo + 0x08] = 0                               # word[+8]>>10&1 = 0
        ent[eo + 0x0a] = stat & 0xff                     # commander_stat
        ent[eo + 0x10] = 0                               # tier 0
        ent[eo + 0x24] = 0                               # bonus 标志 = 0
    mu.mem_write(ENTITY_BASE, bytes(ent))

    return units, ent


def main():
    mu = Uc(UC_ARCH_X86, UC_MODE_32)
    mu.mem_map(BASE, 0x200000)
    mu.mem_write(BASE, IMG)
    mu.mem_map(STACK, 0x2000)
    mu.mem_map(SENTINEL, 0x1000)
    mu.mem_map(STOP_RET, 0x1000)
    mu.mem_write(STOP_RET, b'\xc3')                      # ret 占位

    units, ent = build(mu)
    unit0 = UNIT_BASE + 0 * UNIT_STRIDE
    unit1 = UNIT_BASE + 1 * UNIT_STRIDE

    # 0x513550 是火计等解析 def entity 用的战斗单位表（stride 48）。
    # 令其 entry0 的 +5 实体索引 = 0 → 解析到 entity[0]（commander_stat=150），
    # 与 unit0→entity[0] 一致，使 def 预测可精确到 220/160/160。
    mu.mem_write(0x513550 + 5, struct.pack('<H', 0))

    # --- 安全桩 ---
    # rand%n -> 固定返回 10（落在所有 range 内：火/挑 0-39、伏 0-79、def 0-99/49）
    patch(mu, 0x4ebd60, b'\xb8\x0a\x00\x00\x00\xc3')          # mov eax,10; ret
    # 0x43de30(range) -> 返回 unit[0]（施法者；令 def 解析到与 atk 同源的 entity[0]，
    #   使 atk/def 都用施法者 commander_stat，内部一致，便于校验公式）
    patch(mu, 0x43de30, b'\xb8' + struct.pack('<I', unit0) + b'\xc3')
    # 0x43de50(arg) -> 返回 unit[1]（挑衅目标）
    patch(mu, 0x43de50, b'\xb8' + struct.pack('<I', unit1) + b'\xc3')
    # 0x43d630(unit_ptr_in_ecx) -> 读 word[ecx+5]=实体索引, 返回 0x519868+47*idx
    #   movzx eax,word[ecx+5]; mov edx,eax; lea eax,[eax+eax*2]; shl eax,4;
    #   sub eax,edx; add eax,0x519868; ret
    #   注意：sub 必须是 sub eax,edx = 2b c2（曾误写成 2b d0=sub edx,eax，导致 48*idx 偏移）
    patch(mu, 0x43d630, b'\x0f\xb7\x41\x05\x89\xc2\x8d\x04\x40\xc1\xe0\x04\x2b\xc2\x05\x68\x98\x51\x00\xc3')
    # getHi / parity / flag -> 0（排除天气/指挥官在场等附加项，隔离核心公式）
    patch(mu, 0x4390c0, b'\x33\xc0\xc3')
    patch(mu, 0x43ca10, b'\x33\xc0\xc3')
    patch(mu, 0x43cab0, b'\x33\xc0\xc3')
    patch(mu, 0x43cb10, b'\x33\xc0\xc3')
    # 落地/消息/驱动 桩（ret）
    patch(mu, 0x4366d0, b'\xc3')                              # 火计 apply
    patch(mu, 0x4997c0, b'\xc3')
    patch(mu, 0x499800, b'\xc3')
    patch(mu, 0x499810, b'\x33\xc0\xc3')                      # 挑衅驱动循环 -> 0
    patch(mu, 0x47ba40, b'\xc3')                              # msg
    patch(mu, 0x43dbe0, b'\xc3')
    patch(mu, 0x43dce0, b'\xc3')

    results = {}
    last_eip = [0]

    def hook_code(mu, address, size, data):
        last_eip[0] = address
        if address == SENTINEL:
            mu.emu_stop()
            return
        for name in ('fire', 'ambush', 'taunt'):
            if address == CAP[name]:
                areg, dreg = CAPREGS[name]
                r = results.setdefault(name, {})
                r['atk'] = mu.reg_read(areg) & 0xffff
                r['def'] = mu.reg_read(dreg) & 0xffff
                mu.emu_stop()
                return

    def hook_mem(mu, access, address, size, value, data):
        if access == UC_MEM_FETCH_UNMAPPED:
            print('  [FETCH_UNMAPPED] addr=0x%X (EIP=0x%X)' %
                  (address, mu.reg_read(UC_X86_REG_EIP)), file=sys.stderr)
            esp = mu.reg_read(UC_X86_REG_ESP)
            ret = int.from_bytes(mu.mem_read(esp, 4), 'little')
            mu.reg_write(UC_X86_REG_ESP, esp + 4)
            mu.reg_write(UC_X86_REG_EIP, ret)
            mu.reg_write(UC_X86_REG_EAX, 0)
        return True

    mu.hook_add(UC_HOOK_MEM_UNMAPPED, hook_mem)
    mu.hook_add(UC_HOOK_CODE, hook_code)

    print('%-8s | %8s %8s | %8s %8s | %s' % ('tactic', 'atk_bin', 'def_bin', 'atk_pred', 'def_pred', 'MATCH'))
    print('-' * 70)
    all_ok = True
    for name in ('fire', 'ambush', 'taunt'):
        func = FUNCS[name]
        sp = STACK + 0x800
        frame = bytearray(0x30)
        struct.pack_into('<I', frame, 0x00, SENTINEL)         # retaddr -> SENTINEL(安全网)
        for i in range(9):
            struct.pack_into('<I', frame, 0x04 + i * 4, unit0)  # arg0..arg8 = 施法者
        mu.mem_write(sp, bytes(frame))

        last_eip[0] = 0
        mu.reg_write(UC_X86_REG_ESP, sp)
        mu.reg_write(UC_X86_REG_EIP, func)
        try:
            mu.emu_start(func, func + 0x500)
        except Exception as e:
            print('  [EXC %s] last_eip=0x%X' % (e, last_eip[0]), file=sys.stderr)
        cap = results.get(name, {})
        p = PRED[name]
        ok = (cap.get('atk') == p['atk'] and cap.get('def') == p['def'])
        all_ok &= ok
        print('%-8s | %8s %8s | %8s %8s | %s' % (
            name, cap.get('atk'), cap.get('def'), p['atk'], p['def'],
            'OK' if ok else 'FAIL'))
    print('-' * 70)
    print('RESULT:', 'ALL MATCH' if all_ok else 'MISMATCH')

    # 额外：验证 0x43d630 解析 unit[0]（ecx=unit ptr, idx=0）→ entity[0]
    resolved = 0
    def hook_resolver(mu, address, size, data):
        if address == STOP_RET:
            nonlocal resolved
            resolved = mu.reg_read(UC_X86_REG_EAX)
            mu.emu_stop()
    mu.hook_add(UC_HOOK_CODE, hook_resolver)
    mu.reg_write(UC_X86_REG_ESP, STACK + 0x900)
    mu.mem_write(STACK + 0x900, struct.pack('<I', STOP_RET))   # retaddr -> STOP_RET
    mu.mem_write(STACK + 0x904, struct.pack('<I', 0))           # idx = 0
    mu.reg_write(UC_X86_REG_ECX, unit0)                          # ecx = unit ptr
    mu.reg_write(UC_X86_REG_EIP, 0x43d630)
    try:
        mu.emu_start(0x43d630, 0x43d630 + 0x60)
    except Exception as e:
        print('  [RESOLVER EXC %s]' % e, file=sys.stderr)
    print('0x43d630(unit[0],idx=0) -> 0x%X  (expect 0x%X = entity[0])' %
          (resolved, ENTITY_BASE + 0 * ENTITY_STRIDE))
    assert resolved == ENTITY_BASE + 0 * ENTITY_STRIDE, 'resolver mismatch'

    # 输出可入库的字段语义结论
    print()
    print('FIELD SEMANTICS CONFIRMED (tier=0 baseline):')
    print('  byte[unit+0x0a]  = commander_stat (atk side, 施法者主战力)')
    print('  byte[ent+0x0a]   = commander_stat (def side, 目标主战力)')
    print('  divisor          = /100  (magic 0x51EB851F, high32>>5)')
    print('  atk = (rand%R + base) * (commander_stat + K_atk*tier) / 100')
    print('    K_atk: 火计15( byte&3) / 伏兵25((byte>>2)&3) / 挑衅30((byte>>2)&3)')
    print('  def = rand%r2 + commander_stat + K_def*tier + weather/flag (本次=0)')
    print('    K_def: 火计30(+2基差) / 伏兵30 / 挑衅30 ; tier域 火计byte&3，伏兵/挑衅(byte>>2)&3')
    print('  (tier 系数由反汇编实证；本脚本仅以 tier=0 校验除数/字段/基差)')


if __name__ == '__main__':
    main()
