# -*- coding: utf-8 -*-
"""
隔离仿真验证：Unicorn 跑真实二进制 0x42d270（合战一回合结算），
与一个独立重写的纯 Python 参考实现比对，验证 battle_formula_ref 的正确性。

上下文构造（干净可控）：
  - 直接模式：单位 word@0xa = 合法实体索引(0..14) -> 攻防从实体表 0x519868 取（不减半）
  - battle_type = 1 (0x513548)  -> 除数用 window0，且跳过 hi±1 对冲(mode_m1? 实际由 0x43ca10 控制)
  - mode_m1 = 0 (0x511bf8)     -> 无免伤/无 >>3
  - section A 全部 0x03        -> 低4位=3(除数表[3]=7), 高4位=0(无对冲), 且 !=10(无handle_stat)
"""
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

import struct, sys
sys.path.insert(0, 'scripts')
from capstone import Cs, CS_ARCH_X86, CS_MODE_32
from unicorn import Uc, UC_ARCH_X86, UC_MODE_32, UC_HOOK_CODE, UC_HOOK_MEM_UNMAPPED, UC_MEM_FETCH_UNMAPPED
from unicorn.x86_const import UC_X86_REG_ESP, UC_X86_REG_EIP, UC_X86_REG_EAX, UC_X86_REG_AX, UC_X86_REG_EDX, UC_X86_REG_ESI

BASE = 0x400000
IMG = open(_ROOT + '/scripts/_unpacked_mem.bin', 'rb').read()
assert len(IMG) == 0x200000, len(IMG)

TABLE = [10, 12, 15, 7, 7, 15, 100, 100, 10, 10, 12, 7, 7, 10, 10, 8, 100, 100, 12, 12]

UNIT_BASE = 0x513910
UNIT_STRIDE = 24
N_UNITS = 15
ENTITY_BASE = 0x519868
ENTITY_STRIDE = 47
SECT_A = 0x512e58
STACK = 0x600000
FUNC = 0x42d270
STOP = 0x42d4a7

md = Cs(CS_ARCH_X86, CS_MODE_32)


def build_mem(spec):
    mu = Uc(UC_ARCH_X86, UC_MODE_32)
    mu.mem_map(BASE, 0x200000)
    mu.mem_write(BASE, IMG)
    mu.mem_map(STACK, 0x1000)

    mu.mem_write(0x513548, bytes([spec['battle_type'] & 0xff]))
    mu.mem_write(0x511bf8, struct.pack('<I', spec['mode_m1']))
    mu.mem_write(0x51352c, struct.pack('<I', spec['mode_m2']))
    mu.mem_write(0x513540, bytes([spec['parity'] & 0xff]))
    mu.mem_write(0x513534, bytes([spec.get('handle_stat', 0) & 0xff]))

    assert len(spec['sect_a']) == 180
    mu.mem_write(SECT_A, bytes(spec['sect_a']))

    ent = bytearray(ENTITY_STRIDE * N_UNITS)
    units = bytearray(UNIT_STRIDE * N_UNITS)
    for i, u in enumerate(spec['units']):
        off = i * UNIT_STRIDE
        struct.pack_into('<H', units, off + 0x0a, i)        # 直接模式：实体索引
        struct.pack_into('<H', units, off + 0x0c, u['troops'])
        units[off + 0x11] = u['morale'] & 0xff
        units[off + 0x12] = u['morale_loss'] & 0xff
        st = (u['category'] & 3) | (0xF0 if not u['active'] else 0)
        units[off + 0x13] = st
        units[off + 0x15] = 0x04 if u['side'] == 1 else 0x00
        eo = i * ENTITY_STRIDE
        ent[eo + 0x0a] = u['def_'] & 0xff
        ent[eo + 0x0b] = u['atk'] & 0xff
        ent[eo + 0x0f] = (u.get('equip_cat1', 0) & 3) << 2
        ent[eo + 0x10] = (u.get('equip_cat2', 0) & 3) << 4
    mu.mem_write(ENTITY_BASE, bytes(ent))
    mu.mem_write(UNIT_BASE, bytes(units))

    def cmdr(c):
        b = bytearray(0x30)
        b[0x00] = c['col'] & 0xff
        b[0x02] = c['row'] & 0xff
        b[0x04] = c['kind'] & 0xff
        b[0x2c] = c['flags'] & 0xff
        return bytes(b)
    pA = STACK + 0x200
    pB = STACK + 0x240
    mu.mem_write(pA, cmdr(spec['pA']))
    mu.mem_write(pB, cmdr(spec['pB']))

    E0 = STACK + 0x1000 - 0x100
    mu.mem_write(E0, struct.pack('<I', 0xDEADBEEF))
    mu.mem_write(E0 + 4, struct.pack('<I', pA))
    mu.mem_write(E0 + 8, struct.pack('<I', pB))
    mu.reg_write(UC_X86_REG_ESP, E0)
    mu.reg_write(UC_X86_REG_EIP, FUNC)
    return mu, pA, pB


def run_binary(spec, debug=False):
    mu, pA, pB = build_mem(spec)
    cap = {}

    def hook_code(mu, address, size, data):
        if address == STOP:
            mu.emu_stop()
            return
        if address == 0x42d2a4:
            cap['R1'] = mu.reg_read(UC_X86_REG_EAX)          # 0x42d5a0 返回值
        elif address == 0x42d2b5:
            cap['R2'] = mu.reg_read(UC_X86_REG_EAX)          # 0x42d730 返回值
        elif address == 0x42d2bf:
            cap['n0'] = mu.reg_read(UC_X86_REG_AX) & 0xffff  # 0x43e550 -> side0 数
        elif address == 0x42d2db:
            cap['n1'] = mu.reg_read(UC_X86_REG_AX) & 0xffff  # 0x43e520 -> side1 数
        elif address == 0x42d360:
            cap['base0'] = mu.reg_read(UC_X86_REG_EAX)       # esp+0x28 -> 打 side0
        elif address == 0x42d3a6:
            cap['base1'] = mu.reg_read(UC_X86_REG_EAX)       # esp+0x2c -> 打 side1
        elif address == 0x42d6f5:
            # 单位战力计算末尾：edx = 该单位最终战力；esi = 单位指针
            edx = mu.reg_read(UC_X86_REG_EDX) & 0xffff
            esi = mu.reg_read(UC_X86_REG_ESI)
            cat = mu.mem_read(esi + 0x13, 1)[0] & 3
            side = (mu.mem_read(esi + 0x15, 1)[0] >> 2) & 1
            cap.setdefault('perunit', []).append((side, cat, edx))

    def hook_mem(mu, access, address, size, value, data):
        # 未映射取指 = import 桩(脱壳后 IAT 全 0x3000) -> 跳回调用者
        if access == UC_MEM_FETCH_UNMAPPED:
            esp = mu.reg_read(UC_X86_REG_ESP)
            ret = int.from_bytes(mu.mem_read(esp, 4), 'little')
            mu.reg_write(UC_X86_REG_ESP, esp + 4)
            mu.reg_write(UC_X86_REG_EIP, ret)
            mu.reg_write(UC_X86_REG_EAX, 0)
            return True
        # 其它未映射(数据读/写) -> 放行(视作 0)，避免脱壳映像缺页中断
        return True

    mu.hook_add(UC_HOOK_MEM_UNMAPPED, hook_mem)
    mu.hook_add(UC_HOOK_CODE, hook_code)
    mu.emu_start(FUNC, STOP + 1)

    troops = []
    for i in range(N_UNITS):
        t = struct.unpack_from('<H', mu.mem_read(UNIT_BASE + i * UNIT_STRIDE + 0x0c, 2))[0]
        troops.append(t)
    if debug:
        print('   [binary] R1=%s R2=%s n0=%s n1=%s base0=%s base1=%s' % (
            cap.get('R1'), cap.get('R2'), cap.get('n0'), cap.get('n1'),
            cap.get('base0'), cap.get('base1')))
        print('   [binary] per-unit strength (side,cat,str):', cap.get('perunit'))
    return troops


# ---------------------------------------------------------------------------
# 独立纯 Python 参考实现（依据 0x42d270 完整反汇编重写）
# ---------------------------------------------------------------------------

def troop_scale(t):
    if t <= 100: return t
    if t <= 300: return t // 2 + 50
    if t <= 500: return t // 4 + 125
    if t <= 1000: return t // 5 + 150
    return (3 * t) // 20 + 200


def ustr(u):
    """单单位战力（与 0x43e260/0x43e200 等访问器一致）。"""
    cat = u['category']
    atk = u['atk']
    if cat == 1:
        v = atk + 15 * (u.get('equip_cat1', 0) & 3) + 20
    elif cat == 2:
        v = (atk * 2) // 3 if u.get('mode_m2', 0) else atk + 25 * (u.get('equip_cat2', 0) & 3) + 10
    else:
        v = atk
    m = max(0, u['morale'] - u['morale_loss'])
    v = v * (100 + m // 10) // 100
    v = max(v, 10)
    v = v * troop_scale(u['troops']) // 23
    return v


def ref_battle(spec):
    units = spec['units']
    n0 = sum(1 for u in units if u['active'] and u['side'] == 0)
    n1 = sum(1 for u in units if u['active'] and u['side'] == 1)

    # army_strength(1) = side1 总战力; army_strength(0) = side0 总战力
    S1_raw = sum(ustr(u) for u in units if u['active'] and u['side'] == 1)
    S0_raw = sum(ustr(u) for u in units if u['active'] and u['side'] == 0)

    # R1 = 0x42d5a0() = army_strength(1) = side1 总战力 -> 用于 base0(打 side0)
    #   0x42d5a0: R1 = S1; if (0x42c150()!=0 [mode_m1]) AND (0x43cab0()!=0 [parity&1]) -> R1 >>= 3
    R1 = S1_raw
    if spec['mode_m1'] and (spec['parity'] & 1):
        R1 >>= 3

    # R2 = 0x42d730(pA,pB) = army_strength(0) = side0 总战力 -> 用于 base1(打 side1)
    #   0x42d730: R2 = S0*4/5; if pA.kind==pB.kind -> R2*4/5
    #   （实测：flags 位 0x10 / 0x40 在此函数完全不读取；0x42b8c0 的额外减半不在本路径）
    R2 = S0_raw * 4 // 5
    if spec['pA']['kind'] == spec['pB']['kind']:
        R2 = R2 * 4 // 5

    def atk_div(col, row):
        v = spec['sect_a'][row * 20 + col] & 0x0F
        d = TABLE[v] if spec['battle_type'] != 0 else TABLE[8 + v]
        return d

    modB = atk_div(spec['pB']['col'], spec['pB']['row'])   # 攻方=side1, 用 pB 的 section A
    modA = atk_div(spec['pA']['col'], spec['pA']['row'])   # 攻方=side0, 用 pA 的 section A
    if spec['battle_type'] == 0:
        # 仅 battle_type==0 才做 hi±1 对冲(0x43ca10 在 !=0 时跳过)
        hiB = spec['sect_a'][spec['pB']['row'] * 20 + spec['pB']['col']] >> 4
        hiA = spec['sect_a'][spec['pA']['row'] * 20 + spec['pA']['col']] >> 4
        if hiB > hiA: modB += 1
        elif hiB < hiA: modB -= 1
        if hiA > hiB: modA += 1
        elif hiA < hiB: modA -= 1

    # 二进制真实顺序(0x42d270)：base = 14 * (R // n) // mod （先 idiv n，再 *14，再 idiv mod）
    base0 = 14 * (R1 // n0) // modB if (n0 and modB) else 0
    base1 = 14 * (R2 // n1) // modA if (n1 and modA) else 0

    res = [dict(u) for u in units]
    for u in res:
        if not u['active']:
            continue
        side = u['side']
        # side0 承受 side1(R1) 全力；side1 承受 side0(R2)
        base = base0 if side == 0 else base1
        dmg = base // (u['def_'] // 4 + 50) + 1
        if side == 1 and spec['mode_m1']:
            dmg = 0                                      # 0x42d446: side1 免伤(mode_m1)
        u['troops'] = max(0, u['troops'] - dmg)
    return [u['troops'] for u in res]


# ---------------------------------------------------------------------------
def make_spec(scenario):
    if scenario == 'a':
        units = []
        for i in range(4):
            units.append(dict(troops=500, morale=80, morale_loss=10, category=0, active=True,
                              side=0, atk=70, def_=60, equip_cat1=2, equip_cat2=1))
        for i in range(4):
            units.append(dict(troops=400, morale=60, morale_loss=20, category=1, active=True,
                              side=1, atk=55, def_=50, equip_cat1=1, equip_cat2=0))
        while len(units) < 15:
            units.append(dict(troops=0, morale=0, morale_loss=0, category=0, active=False,
                              side=0, atk=0, def_=0, equip_cat1=0, equip_cat2=0))
        return dict(battle_type=1, mode_m1=0, mode_m2=0, parity=0,
                    sect_a=bytes([0x03] * 180),
                    pA=dict(col=0, row=0, kind=1, flags=0),
                    pB=dict(col=1, row=0, kind=2, flags=0),
                    units=units)
    if scenario == 'b':
        # 7+7 = 14 单位(≤15 槽)
        rnd = [(600, 90, 5, 2, 1, 80, 70), (300, 40, 30, 0, 0, 40, 30), (450, 70, 15, 1, 1, 60, 55),
               (550, 85, 10, 2, 1, 75, 65), (200, 30, 25, 0, 0, 35, 25), (700, 95, 0, 1, 1, 90, 80),
               (350, 50, 20, 2, 1, 50, 45)]
        units = []
        for (tr, mo, ml, cat, sd, at, df) in rnd:
            units.append(dict(troops=tr, morale=mo, morale_loss=ml, category=cat, active=True,
                              side=0, atk=at, def_=df, equip_cat1=cat, equip_cat2=cat))
        for (tr, mo, ml, cat, sd, at, df) in rnd:
            units.append(dict(troops=tr, morale=mo, morale_loss=ml, category=cat, active=True,
                              side=1, atk=at, def_=df, equip_cat1=cat, equip_cat2=cat))
        while len(units) < 15:
            units.append(dict(troops=0, morale=0, morale_loss=0, category=0, active=False,
                              side=0, atk=0, def_=0, equip_cat1=0, equip_cat2=0))
        return dict(battle_type=1, mode_m1=0, mode_m2=0, parity=0,
                    sect_a=bytes([0x03] * 180),
                    pA=dict(col=3, row=2, kind=1, flags=0),
                    pB=dict(col=5, row=4, kind=1, flags=0),
                    units=units)
    if scenario == 'c':
        s = make_spec('a')
        s['units'][0]['active'] = False
        s['units'][1]['active'] = False
        s['pA'] = dict(col=7, row=8, kind=3, flags=0x10)
        s['pB'] = dict(col=2, row=1, kind=3, flags=0)
        return s


if __name__ == '__main__':
    all_ok = True
    for sc in ('a', 'b', 'c'):
        spec = make_spec(sc)
        bin_tr = run_binary(spec, debug=True)
        ref_tr = ref_battle(spec)
        ok = bin_tr == ref_tr
        all_ok &= ok
        print(f'=== scenario {sc}: {"PASS" if ok else "FAIL"} ===')
        if not ok:
            for i, (b, r) in enumerate(zip(bin_tr, ref_tr)):
                if b != r:
                    u = spec['units'][i]
                    print(f'  unit[{i:2d}] side={u["side"]} active={u["active"]} cat={u["category"]} '
                          f'bin={b:5d} ref={r:5d}  <-- MISMATCH')
        else:
            print('  bin :', bin_tr)
            print('  ref :', ref_tr)
    print('\nRESULT:', 'ALL PASS' if all_ok else 'MISMATCH FOUND')
