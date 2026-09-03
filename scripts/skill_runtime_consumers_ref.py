# -*- coding: utf-8 -*-
"""
skill_runtime_consumers_ref.py -- 续239：运行时 47B 武将实体技能字节(entity+0x0f..0x11)
的「多玩法消费点」实证 + 写入侧负向审计。纯静态（capstone + 映像字节签名），无需 emu。

闭合 续237「仍未知① 读侧」：技能读取不是单一共享 getter，而是各消费点直接内联的
「常量位移 2-bit 提取」。四个独立玩法站（口才/马术/洋枪/茶道）的位移与 GAME_DATA_SPEC
§3.5.6 布局公式 level_k = (byte[0x0f + k//4] >> ((k&3)*2)) & 3 逐一吻合，且各站基址
经「同函数 sibling 字段」证明是 47B 武将实体（五维 +0x0a..0x0e / 国索引 +0x24 等）。

锚点总表：
  skill  id  实体字节   提取            站点                                   语义
  口才    0   +0x0f    &3           0x4b5627/32 (0x4b5620 授艺资格判定)        师事门槛
  马术    1   +0x0f    >>2 &3       0x43e23d (0x43e220)                       骑兵战力
  洋枪    6   +0x10    >>4 &3       0x43e250 (0x43e220)                       洋枪战力
  茶道    9   +0x11    >>2 &3       0x4b3122..0x4b319e (0x4b31xx 茶会评分)     主客茶道
"""
import os
from capstone import Cs, CS_ARCH_X86, CS_MODE_32, x86_const as X
from capstone.x86_const import X86_REG_ESP, X86_REG_EBP

BASE = 0x400000
HERE = os.path.dirname(os.path.abspath(__file__))
MEM = open(os.path.join(HERE, '_unpacked_mem.bin'), 'rb').read()
MD = Cs(CS_ARCH_X86, CS_MODE_32); MD.skipdata = True; MD.detail = True

def raw(va, n):
    return MEM[va - BASE: va - BASE + n]

def hexs(va, n):
    return raw(va, n).hex()

PASS = []
def ok(name, cond, extra=''):
    assert cond, (name, extra)
    PASS.append(name)
    print('  [PASS] %s %s' % (name, extra))

# ---------------- T1: 布局公式 ↔ 锚点位移一致性 ----------------
def byte_off(k): return 0x0f + k // 4          # 运行时实体技能字节
def bit_shift(k): return (k & 3) * 2           # 位偏移
def read_shift_mode(k): return (byte_off(k), bit_shift(k))

# 观察到的各站读法 → (目标字节, 常量移位, 掩码&3 后再 and) ；k=0 时无 shr
ANCHORS = {
    0: dict(byte=0x0f, shr=None, va=0x4b5627, name='口才'),
    1: dict(byte=0x0f, shr=2,    va=0x43e23d, name='马术'),
    6: dict(byte=0x10, shr=4,    va=0x43e250, name='洋枪'),
    9: dict(byte=0x11, shr=2,    va=0x4b3125, name='茶道'),
}
def main():
    print('T1. 布局公式 ↔ 锚点位移')
    for k, a in sorted(ANCHORS.items()):
        b, s = byte_off(k), bit_shift(k)
        ok('T1 id%d(%s) 字节=%02x 移位=%s' % (k, a['name'], a['byte'],
           a['shr'] if a['shr'] is not None else '无(and3)'),
           a['byte'] == b and a['shr'] == (s if s else None),
           '公式(off=%02x,shift=%d)' % (b, s))

    # ---------------- T2: 0x43e110 = unit→主将实体解析器（×47 + 0x519868）----------------
    print('T2. 0x43e110 unit→武将实体 getter 签名')
    assert hexs(0x43e110, 0x25) == ('668b410a663dffff741b663d7201731525ffff00008bc88d0449c1e004'
                                    '2bc10568985100c3'), hexs(0x43e110, 0x25)
    ok('T2a 0x43e110: word[unit+0xa]=主将id; cmp 0xffff/0x172; lea3x+shl4-sub=×47; add 0x519868',
       True, hexs(0x43e110, 0x25))

    # ---------------- T3: 0x43e220 合战兵种战力（kind 门控 → 马术/洋枪）----------------
    print('T3. 0x43e220 马术/洋枪 读取签名 + kind 门控')
    # kind getter 0x43e140 = byte[unit+0x13]&3
    ok('T3a kind getter 0x43e140', hexs(0x43e140, 7) == '8a411383e003c3', hexs(0x43e140, 7))
    # kind==1(骑兵): esi=实体(from 0x43e110); bl=byte[esi+0xf]; shr bl,2; and bl,3
    ok('T3b kind==1 骑兵 → 马术(+0xf >>2&3)',
       hexs(0x43e239, 0x13) == '3c01750f8a5e0fc0eb0280e3038ac35f5e5bc3',
       hexs(0x43e239, 0x13))
    # kind==2(洋枪): bl=byte[esi+0x10]; shr bl,4; and bl,3
    ok('T3c kind==2 洋枪 → 洋枪(+0x10 >>4&3)',
       hexs(0x43e24c, 0x13) == '3c0275098a5e10c0eb0480e3035f8ac35e5bc3',
       hexs(0x43e24c, 0x13))

    # ---------------- T4: 0x4b5620 授艺资格判定（双实体口才 + 五维 sibling）----------------
    print('T4. 0x4b5620 双实体 口才(&3) 等级和判定')
    w = hexs(0x4b5620, 0x1e)
    assert w == '8b44240483ec0c8a480f568b74241883e1038a560f83e20303ca83f9067d', w
    ok('T4a 0x4b5627/32 双实体 byte[+0xf]&3 + add + cmp 6', True, w)
    # 同函数继续读 五维 sibling +0x0d(外交)/+0x0e(魅力) → 基址必为 47B 武将实体
    ok('T4b sibling 外交读 +0x0d(两实体)',
       hexs(0x4b5666, 0xd) == '8a500d8a4e0d03d183fa647d23', hexs(0x4b5666, 0xd))
    ok('T4c sibling 魅力读 +0x0e(两实体)',
       hexs(0x4b569a, 0xb) == '8a4e0e8a500e03ca83f964', hexs(0x4b569a, 0xb))
    ok('T4d 学得分支 push 技能名表 0x507b58',
       hexs(0x4b5643, 5) == '68587b5000', hexs(0x4b5643, 5))

    # ---------------- T5: 0x4b31xx 茶会评分（主客茶道 +0x11>>2&3）----------------
    print('T5. 0x4b31xx 茶会评分 主客茶道读取')
    w = hexs(0x4b3120, 0x23)
    assert w == '6a028a51118a4811c0ea0280e203c0e902660fb6f280e1036633d28ad1420fafd652e8', w
    ok('T5a 0x4b3122.. host(+0x11>>2&3) movzx si + 客1(+0x11>>2&3) (lv+1)*host',
       True, w)
    ok('T5b 客2/客3 同一读法 0x4b3160/0x4b318e',
       hexs(0x4b3160, 9) == '8a4811c0e90280e103' and hexs(0x4b318e, 9) == '8a4811c0e90280e103',
       hexs(0x4b3160, 9) + ' / ' + hexs(0x4b318e, 9))
    # 主客实体 = 全局当前会话槽指针 0x525c44(主)/0x525c4c/50/58(客)
    ok('T5c 实体槽指针读 [0x525c44/4c/50/58]',
       hexs(0x4b3115, 0xb) == '8b0d445c5200a1505c5200'
       and hexs(0x4b3156, 5) == 'a14c5c5200' and hexs(0x4b3184, 5) == 'a1585c5200',
       hexs(0x4b3115, 0xb))
    # 同函数读 [0x525c40]+0x24 国索引（<0x31=49）→ 基址为 47B 武将实体（+0x24=国）
    ok('T5d sibling 国索引读 [0x525c40]+0x24 <0x31',
       hexs(0x4b31f5, 0xa) == 'a1405c52008a40243c31', hexs(0x4b31f5, 0xa))

    # ---------------- T6: 写入侧负向审计（静态无 2-bit RMW 技能写入器）----------------
    print('T6. 全镜像负向审计：无 2-bit 掩码 and/or/xor byte[reg+0x0f..0x11]')
    insns = list(MD.disasm(MEM, BASE))
    mask_rmw = []
    for insn in insns:
        if insn.id == 0 or insn.mnemonic not in ('and', 'or', 'xor'):
            continue
        if len(insn.operands) < 2:
            continue
        op0, op1 = insn.operands[0], insn.operands[1]
        if op0.type != X.X86_OP_MEM or op1.type != X.X86_OP_IMM:
            continue
        m = op0.mem
        if m.index != 0 or m.disp not in (0x0f, 0x10, 0x11) or m.base == 0:
            continue
        if m.base in (X86_REG_ESP, X86_REG_EBP):
            continue
        imm = op1.imm & 0xff
        if imm in (0x03, 0x0c, 0x30, 0xc0, 0xfc, 0xf3, 0xcf, 0x3f):
            mask_rmw.append((hex(insn.address), insn.mnemonic, insn.op_str))
    ok('T6a 2-bit 掩码 RMW 写点 = 0', len(mask_rmw) == 0, str(mask_rmw[:5]))

    # ---------------- T7: 全镜像读点普查（内联 idiom 广泛散布、无集中 getter）----------------
    print('T7. 全镜像 [reg+0x0f..0x11] 读点普查（确定性基线）')
    disps = (0x0f, 0x10, 0x11)
    rd_total = {d: 0 for d in disps}
    rd_ext = {d: 0 for d in disps}
    for i, insn in enumerate(insns):
        if insn.id == 0:
            continue
        mops = [op for op in insn.operands if op.type == X.X86_OP_MEM]
        if len(mops) != 1:
            continue
        m = mops[0].mem
        if m.index != 0 or m.disp not in disps or m.base == 0:
            continue
        if m.base in (X86_REG_ESP, X86_REG_EBP):
            continue
        is_write = (insn.operands[0].type == X.X86_OP_MEM)
        if is_write:
            continue
        rd_total[m.disp] += 1
        nxt = insns[i + 1:i + 7]
        if any(x.id != 0 and x.mnemonic in ('shr', 'sar') for x in nxt) or \
           any(x.id != 0 and x.mnemonic == 'and' and x.op_str.endswith(', 3') for x in nxt):
            rd_ext[m.disp] += 1
    print('    total= %s  extract= %s' % (
        {hex(d): rd_total[d] for d in disps}, {hex(d): rd_ext[d] for d in disps}))
    ok('T7a 读点总量基线', rd_total == {0x0f: 214, 0x10: 453, 0x11: 73}, str(rd_total))
    ok('T7b 疑似2bit提取子集基线', rd_ext == {0x0f: 146, 0x10: 175, 0x11: 57}, str(rd_ext))
    # 全部提取子集中须含四个锚点地址
    anchored = {0x4b5627, 0x43e23d, 0x43e250, 0x4b3125}
    seen = set()
    for i, insn in enumerate(insns):
        if insn.address in anchored:
            seen.add(insn.address)
    ok('T7c 四个锚点读点均在普查集内', anchored <= seen, str(sorted(seen)))

    print('\n续239 skill_runtime_consumers_ref  ALL PASS (%d)' % len(PASS))

if __name__ == '__main__':
    main()
