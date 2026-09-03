# -*- coding: utf-8 -*-
"""
skill_inc_writer_ref.py -- 续240：武将技能「写侧」机制坐死 —— cap-3 递增器族
0x4a3040 + k*0x20 (k=0..9) 是技能写器库（寄存器中介 RMW：2-bit 字段 +1、封顶 3），
并闭合 §4.3.3 修行 mode0-2 增长写入器精确站点（0x45fca0 及其同映射双胞胎 0x4de0e0，
mode→skill {0:口才, 1:筑城, 2:兵法}）。承接 续239（读侧）「仍未知②」。

helper 约定：ecx = 3 字节打包块基址（47B 武将实体 = entity+0x0f）；helper k 操作
byte[ecx + k>>2] 的 (k&3)*2 位。idiom：
  dl=[ecx+boff]; al=(dl>>sh)&3(或 and3 直取); if al<3 { al++; dl &= ~(3<<sh);
  [ecx+boff] = (dl & mask) | (al<<sh) }   —— 即写侧唯一机制（与 续239 读侧公式同构反向）。

锚点：
  helper k0 @0x4a3040  [ecx+0] &3    mask fc   (口才)
  helper k5 @0x4a30e0  [ecx+1] >>2   mask f3   (兵法)
  helper k7 @0x4a3120  [ecx+1] >>6   mask 3f   (筑城)
mode0-2 驱动 0x45fca0（唯一调用方 0x45f3eb）：
  mode0(学习内政)→读[ent+0xf]&3→call k0@0x45fdc8；mode1(学习外交)→读[ent+0x10]>>6→call k7@0x45fd8d；
  mode2(学习魅力)→读[ent+0x10]>>2&3→call k5@0x45fd3d；成功后 fame += (旧级+1)*500
  (0x45fe18 inc edi + lea×3 + shl2 = ×500 → call 0x4a3210)；消息名索引 {0→0,1→7,2→5}→0x507b58+id*5。
双胞胎 0x4de0e0（带天数推进）：mode0→k0@0x4de171 / mode1→k7@0x4de155 / mode2→k5@0x4de139，
每次递增后回读新级（+0xf&3 / +0x10>>6 / +0x10>>2&3）佐证写的就是技能字节。
"""
import os
from capstone import Cs, CS_ARCH_X86, CS_MODE_32, x86_const as X

BASE = 0x400000
HERE = os.path.dirname(os.path.abspath(__file__))
MEM = open(os.path.join(HERE, '_unpacked_mem.bin'), 'rb').read()
MD = Cs(CS_ARCH_X86, CS_MODE_32); MD.skipdata = True; MD.detail = True

def raw(va, n):
    return MEM[va - BASE: va - BASE + n]

def hexs(va, n):
    return raw(va, n).hex()

def dis(va, n):
    return list(MD.disasm(raw(va, n), va))

PASS = []
def ok(name, cond, extra=''):
    assert cond, (name, extra)
    PASS.append(name)
    print('  [PASS] %s %s' % (name, extra))

FAM = [0x4a3040 + k * 0x20 for k in range(10)]
def k_sh(k): return (k & 3) * 2
def k_mask(k): return (~(3 << k_sh(k))) & 0xff

def main():
    # ---------------- A: 10 helper 族（32B 对齐 + 规范字节） ----------------
    print('A. cap-3 递增器族 0x4a3040 + k*0x20（规范字节回归）')
    CANON = {
        0: '8a118ac224033c037309fec080e2fc0ac28801c3',
        1: '8a118ac2c0e80224033c03730cfec080e2f3c0e0020ac28801c3',
        2: '8a118ac2c0e80424033c03730cfec080e2cfc0e0040ac28801c3',
        3: '8a118ac2c0e8063c03730cfec080e23fc0e0060ac28801c3',
        4: '8a51018ac224033c03730afec080e2fc0ac2884101c3',
        5: '8a51018ac2c0e80224033c03730dfec080e2f3c0e0020ac2884101c3',
        6: '8a51018ac2c0e80424033c03730dfec080e2cfc0e0040ac2884101c3',
        7: '8a51018ac2c0e8063c03730dfec080e23fc0e0060ac2884101c3',
        8: '8a51028ac224033c03730afec080e2fc0ac2884102c3',
        9: '8a51028ac2c0e80224033c03730dfec080e2f3c0e0020ac2884102c3',
    }
    for k, va in enumerate(FAM):
        ins = dis(va, 0x20)
        ret = next((x.address for x in ins if x.mnemonic == 'ret'), None)
        assert ret is not None, ('no ret in helper %d' % k, hex(va))
        body = hexs(va, ret + 1 - va)
        ok('A%d helper k%d @%x' % (k, k, va), body == CANON[k], body)
    ok('A10 族基址=0x4a3040、stride=0x20、10 成员', FAM[0] == 0x4a3040
       and all(FAM[k] - FAM[k - 1] == 0x20 for k in range(1, 10)), hex(FAM[0]))

    # ---------------- B: 语义解码（capstone 重解析） ----------------
    print('B. 语义解码：byte[ecx + k>>2] 位 (k&3)*2，cap-3')
    for k, va in enumerate(FAM):
        sh, mask, boff = k_sh(k), k_mask(k), k >> 2
        ins = dis(va, 0x20)
        load = ins[0]
        ok('B%d load mov dl,[ecx+%d]' % (k, boff),
           load.mnemonic == 'mov' and load.operands[1].type == X.X86_OP_MEM
           and load.operands[1].mem.disp == boff, load.op_str)
        ops = ins[1:]
        if sh == 0:
            ok('B%d sh==0 → and al,3' % k,
               any(x.mnemonic == 'and' and x.op_str == 'al, 3' for x in ops), '')
        else:
            ok('B%d shr al,%d' % (k, sh),
               any(x.mnemonic == 'shr' and x.op_str.startswith('al') for x in ops), '')
            if sh != 6:
                ok('B%d shr 后 and al,3' % k,
                   any(x.mnemonic == 'and' and x.op_str == 'al, 3' for x in ops), '')
        ok('B%d and dl,0x%02x' % (k, mask),
           any(x.mnemonic == 'and' and x.op_str == ('dl, 0x%x' % mask) for x in ops), '')
        ok('B%d cmp al,3 + inc al' % k,
           any(x.mnemonic == 'cmp' and x.op_str == 'al, 3' for x in ops)
           and any(x.mnemonic == 'inc' and x.op_str == 'al' for x in ops), '')
        store = next((x for x in ins if x.mnemonic == 'mov'
                      and x.operands[0].type == X.X86_OP_MEM
                      and x.operands[1].type == X.X86_OP_REG), None)
        ok('B%d 写回 mov [ecx+%d],al' % (k, boff),
           store is not None and store.operands[0].mem.disp == boff
           and store.operands[1].reg == X.X86_REG_AL,
           store.op_str if store else 'none')

    # ---------------- C: 全镜像调用点审计 ----------------
    print('C. 全镜像 call 站点（19 站点，分组=技能 k）')
    insns = list(MD.disasm(MEM, BASE))
    famset = set(FAM)
    sites = {}
    for x in insns:
        if x.mnemonic == 'call' and len(x.operands) == 1 \
           and x.operands[0].type == X.X86_OP_IMM and x.operands[0].imm in famset:
            sites.setdefault(x.operands[0].imm, []).append(x.address)
    EXPECT = {
        0x4a3040: [0x45fdc8, 0x4de171],
        0x4a3060: [0x45d9e3, 0x45da41],
        0x4a3080: [0x458f8e, 0x458fc0],
        0x4a30a0: [0x448b56],
        0x4a30c0: [0x451f98],
        0x4a30e0: [0x45fd3d, 0x4de139],
        0x4a3100: [0x44736c, 0x4473dd],
        0x4a3120: [0x45fd8d, 0x4de155],
        0x4a3140: [0x45aefd, 0x45af25],
        0x4a3160: [0x442e5d, 0x442ed1, 0x44304c],
    }
    total = sum(len(v) for v in EXPECT.values())
    ok('C1 站点总数=19 且与期望一致',
       total == 19 and sites == {t: sorted(v) for t, v in EXPECT.items()},
       '; '.join('%x:%d' % (t, len(sites.get(t, []))) for t in sorted(EXPECT)))
    allsites = set(a for lst in sites.values() for a in lst)
    ok('C2 修行三站 0x45fd3d/8d/c8 在调用点集(值域)',
       {0x45fd3d, 0x45fd8d, 0x45fdc8} <= allsites,
       'k5@%x k7@%x k0@%x' % (0x45fd3d, 0x45fd8d, 0x45fdc8))

    # ---------------- D: 0x45fca0 mode0-2 写入器（读级 + inc + fame + 名索引） ----------------
    print('D. 0x45fca0 修行 mode0-2（字节窗口）')
    # mode2 兵法: lea ecx,[esi+0xf] 读 [esi+0x10]>>2&3 → call k5(0x4a30e0)
    ok('D1 mode2(兵法) 0x45fd2e..42',
       hexs(0x45fd2e, 0x14) == '8a46108d4e0fc0e8022403660fb6f8e89e330400',
       hexs(0x45fd2e, 0x14))
    # mode1 筑城: 读 [esi+0x10]>>6 → call k7(0x4a3120)
    ok('D2 mode1(筑城) 0x45fd80..92',
       hexs(0x45fd80, 0x12) == '8a46108d4e0fc0e806660fb6f8e88e330400',
       hexs(0x45fd80, 0x12))
    # mode0 口才: 读 [esi+0xf]&3 → call k0(0x4a3040)
    ok('D3 mode0(口才) 0x45fdbb..cd',
       hexs(0x45fdbb, 0x12) == '8a560f8d4e0f80e203660fb6fae873320400',
       hexs(0x45fdbb, 0x12))
    # fame += 新级*500（inc edi + (edi*5)*5*5<<2 → call 0x4a3210）
    ok('D4 fame×500 0x45fe18..2d',
       hexs(0x45fe18, 0x15) == '478bcb8d04bf8d04808d0480c1e00250e8e3330400',
       hexs(0x45fe18, 0x15))
    # mode→skill 消息名索引 {mode2→5, mode1→7, mode0→0}
    ok('D5 名索引立即数 {2→5,1→7,0→0} @0x45fe3c/43/4a',
       hexs(0x45fe3c, 5) == 'b805000000' and hexs(0x45fe43, 5) == 'b807000000'
       and hexs(0x45fe4a, 2) == '33c0', hexs(0x45fe3c, 0x12))
    # 技能名表 0x507b58 + id*5
    ok('D6 名表指针 lea ecx,[eax+eax*4+0x507b58] @0x45fe58',
       hexs(0x45fe58, 7) == '8d8c80587b5000', hexs(0x45fe58, 7))
    callers = [x.address for x in insns
               if x.mnemonic == 'call' and len(x.operands) == 1
               and x.operands[0].type == X.X86_OP_IMM
               and x.operands[0].imm == 0x45fca0]
    ok('D7 0x45fca0 唯一调用方 = 0x45f3eb', callers == [0x45f3eb],
       ' '.join(hex(a) for a in callers))

    # ---------------- E: 双胞胎驱动 0x4de0e0 同映射（递增后回读新级） ----------------
    print('E. 0x4de0e0 授艺驱动（带天数推进）同 mode→skill 映射')
    ok('E1 mode2→k5(0x4a30e0) @0x4de136',
       hexs(0x4de136, 8) == '8d4b0fe8a24ffcff', hexs(0x4de136, 8))
    ok('E2 mode1→k7(0x4a3120) @0x4de152',
       hexs(0x4de152, 8) == '8d4b0fe8c64ffcff', hexs(0x4de152, 8))
    ok('E3 mode0→k0(0x4a3040) @0x4de16c',
       hexs(0x4de16c, 10) == '8d730f8bcee8ca4efcff', hexs(0x4de16c, 10))
    ok('E4 mode0 递增后回读 byte[+0xf]&3 @0x4de176',
       hexs(0x4de176, 8) == '8a0e80e1036633d2', hexs(0x4de176, 8))
    ok('E5 mode1 递增后回读 byte[+0x10]>>6 @0x4de15a',
       hexs(0x4de15a, 8) == '8a5310c0ea066633', hexs(0x4de15a, 8))
    ok('E6 mode2 递增后回读 byte[+0x10]>>2&3 @0x4de13e',
       hexs(0x4de13e, 0xb) == '8a4310c0e80224036633c9', hexs(0x4de13e, 0xb))

    # ---------------- F: 站点 ecx 基址约定（mem 形式 disp 必须 = 0xf） ----------------
    print('F. 站点 ecx 基址约定审计（mem 型定义 disp==0xf）')
    n_mem = n_other = 0
    bad = []
    for t in sorted(sites):
        for va in sites[t]:
            pre = dis(va - 32, 32)
            ecxdef = None
            for x in reversed(pre):
                if x.operands and x.operands[0].type == X.X86_OP_REG \
                   and x.operands[0].reg == X.X86_REG_ECX:
                    ecxdef = x
                    break
            assert ecxdef is not None, ('no ecx def before', hex(va))
            o = ecxdef.operands
            if len(o) > 1 and o[1].type == X.X86_OP_MEM \
               and o[1].mem.base not in (X.X86_REG_ESP, X.X86_REG_EBP):
                n_mem += 1
                if o[1].mem.disp != 0xf:
                    bad.append((hex(va), ecxdef.op_str))
            else:
                n_other += 1  # 寄存器/栈中转，属间接（含 mov ecx,esi←lea +0xf）
    ok('F1 mem 型 ecx 定义 %d 处全部 disp==0xf' % n_mem,
       bad == [], str(bad[:3]))
    ok('F2 直接 +0xf 型站点 ≥8（其余为寄存器/栈中转）', n_mem >= 8,
       'mem=%d indirect=%d' % (n_mem, n_other))

    print('\n续240 skill_inc_writer_ref  ALL PASS (%d)' % len(PASS))

if __name__ == '__main__':
    main()
