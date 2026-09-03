# -*- coding: utf-8 -*-
"""
skill_writer_consumers_ref.py -- 续241：技能写器 19 调用点之 13 消费站逐一玩法归位
（k0 口才/修行 已闭 续240；k5 兵法/修行、k7 筑城/修行 已闭 续240 D/E 节；
 本 ref 覆盖其余 13 站 = k1马术/k2算术/k3剑术/k4忍术/k6洋枪/k8礼法/k9茶道）。

技能增长完整事件表（消费侧语义，全部自函数体精读坐死）：
  k1 马术 = 马屋打工（0x45d7a0 入口 → 0x45d830 yes/no → 0x45d950 仕事）
    - 门：主角+同伴 现在体力(byte[+0x21]) 均 >= 45(0x2d)；店主义务工钱 =
      min((30-时)/4, 5) 文 x(同伴?2:1)，0x47bcc0 拒绝即中止
    - 主角站 0x45d9e3：级<3 且 rand(5*新级)==0 → +1；打工耗体力 0x4a31b0
    - 同伴站 0x45da41：同概率门 且 ebx==0（主角本回合未升——每次打工至多升一人）
    - 升级提示 0x4704e0(实体, 0x507b58+1*5=0x507b5d 马术名, 新级)；收尾推进到 32-时(0x4a0d50)
  k2 算术 = 商家学做生意（菜单 dispatcher 0x4577c3 → 0x458e20(学者=主角)）
    - 门 0x459000(商人资本 N=byte[[0x52063c]+0x07], 学者级 L)：L0需N>=40 / L1需N>=70 /
      L2需N>=100 / L==3 → msg 570「别开玩笑，我还想学呢」拒绝
    - 学费 0x4590d0(L,N)：L0=90-N/2 / L1=600-3N / L2=5000-2N（贯），实付 x10 文(0x44e350)
    - 学者站 0x458f8e：交费后必然 +1（无概率门）；同伴站 0x458fc0：同伴级<=学者级(flag)
      才 +1，同伴级>学者级 → msg 568/569「资料毫无用处/带个不擅计算的人来」同伴不学
    - 时间：推进到 24-时(次日0点) 再 +14h（学到次日下午两点）；名表 0x507b62 x2
  k3 剑术 = 道场试合（0x448990，唯一站 0x448b56）
    - 前置：体力满（byte[+0x21]==byte[+0x20]），不满 → seq 0x62e「再好好地练武去」
    - 与师父([0x52063c])试合三态：胜 0x640 / 惜败 0x642 → 剑术<3 则 +1；败 0x643 不加
    - 师父记录弟子等级(0x49bfb0)；0x4a0d50(4,1) 耗 4h；名表 0x507b67；尾声 seq 0x646/7/8
  k4 忍术 = 忍里修业（leaf 0x451f90，三调用方）
    - 合格流 0x451e70（msg 2704「嗯，这下合格了」/2706）；再指导流 0x452160
      （师父 2729「你还得再费费劲」+弟子 2689 后仍 +1）；leaf 内无条件 +1 + 0x4704e0(0x507b6c)
  k6 洋枪 = 铁炮锻冶打工（0x447110 循环 → 0x447230 收尾双站）
    - 门：主角+同伴 体力 均 >= 45(0x2d)；店主([0x52063c]) msg 628/629「一人一天200文」
      0x47bcc0 确认；同意后 0x447230(主角,同伴) → 收尾 0x45cc90()==1 → 0x45ccd0 → jmp 回循环
    - 主角站 0x44736c / 同伴站 0x4473dd：各自独立判定 级<3 且 rand(5*新级)==0 → +1
      （与马屋不同：无单名额限制，可同回合双升）；名表 0x507b76 x2；新级==2 换 msg 0x277/0x279
  k8 礼法 = 寺庙 30 日修行（0x45ade0）
    - 30 日 fast-forward 循环（cmp di,0x1e；每迭代 0x4a0d50(0x18,1)=1天）
    - 主角站 0x45aefd：修行结束必然 +1（无概率门）
    - 同伴站 0x45af25：有资格(ebp，前置五维审查 0x45b100) → 必然；否则 rand(10)==0 且 级<3
    - ⚠ 唯一不调 0x4704e0 / 无名表引用的写站（礼法升级无独立提示，收尾 0x45b3d0(主角,同伴,资格)）
  k9 茶道 = 茶人品茶（0x442a80(主角茶道级) → 0x442d70(级, 茶具品质) + 满级分支 0x442f70）
    - 0x442a80：级 0/1/2+ → 茶具品质上限 0/6/13（0x442010 掷茶具）；
      茶具品质 = byte[茶具项+0x08]>>3 & 0xf（4-bit）
    - 主角站 0x442e5d：级 0/1/2 → rand(10/25/30) < 茶具品质 → +1；级==3 → 转调满级分支
    - 同伴站 0x442ed1：(同伴级==2 且 品质<13) 或 (级==1 且 <6) 或 级==0 → msg 929 → +1
    - 满级分支 0x442f70 0x44304c：同伴级<3 且 rand(600=0x258) < 同伴五维字节和
      （dword[+0xa] 四维 + byte[+0xe] 魅力）→ +1；名表 0x507b85 x3
消息链（msgx）：马屋 765/766/772/773/841/842；商家 545-556/565/567-571；
道场 seq 0x62e/0x63f/0x640/0x642/0x643/0x646-8（msg 1606/1607/1608）；
忍里 2689/2704/2706/2729；铁炮 625-629/649/841；寺庙 4810-4814/4827-4830；
茶道 917/918/922-931/934-936（927=0x39f/929=0x3a1/934=0x3a6）。
"""
import os
from capstone import Cs, CS_ARCH_X86, CS_MODE_32
from capstone.x86_const import X86_OP_IMM, X86_OP_MEM, X86_OP_REG

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

HELPERS = {k: 0x4a3040 + k * 0x20 for k in range(10)}

# 站点 → (helper, 宿主函数, 玩法)
SITES = [
    (0x45d9e3, 0x4a3060, 0x45d950, 'k1 主角 马屋仕事'),
    (0x45da41, 0x4a3060, 0x45d950, 'k1 同伴 马屋仕事'),
    (0x458f8e, 0x4a3080, 0x458e20, 'k2 学者 商家学做生意'),
    (0x458fc0, 0x4a3080, 0x458e20, 'k2 同伴 商家学做生意'),
    (0x448b56, 0x4a30a0, 0x448990, 'k3 道场试合'),
    (0x451f98, 0x4a30c0, 0x451f90, 'k4 忍里修业 leaf'),
    (0x44736c, 0x4a3100, 0x447230, 'k6 主角 铁炮锻冶'),
    (0x4473dd, 0x4a3100, 0x447230, 'k6 同伴 铁炮锻冶'),
    (0x45aefd, 0x4a3140, 0x45ade0, 'k8 主角 寺庙30日'),
    (0x45af25, 0x4a3140, 0x45ade0, 'k8 同伴 寺庙30日'),
    (0x442e5d, 0x4a3160, 0x442d70, 'k9 主角 茶人品茶'),
    (0x442ed1, 0x4a3160, 0x442d70, 'k9 同伴 茶人品茶'),
    (0x44304c, 0x4a3160, 0x442f70, 'k9 满级分支 同伴'),
]

def call_at(va, target, span=8):
    """va 处（或 va 后 span 内）存在 call target"""
    for x in dis(va, span + 8):
        if x.address > va + span:
            break
        if x.mnemonic == 'call' and len(x.operands) == 1 \
           and x.operands[0].type == X86_OP_IMM and x.operands[0].imm == target:
            return True
    return False

def imm_in(lo, hi, val):
    """[lo,hi) 内出现立即数 val（push/mov/cmp 任一形式）"""
    for x in dis(lo, hi - lo):
        if x.mnemonic in ('data',):
            continue
        try:
            ops = x.operands
        except Exception:
            continue
        for op in ops:
            if op.type == X86_OP_IMM and (op.imm & 0xffffffff) == val:
                return x.address
    return None

def mnemo_at(va, mn, opsub='', n=8):
    for x in dis(va, n):
        if x.mnemonic == mn and opsub in x.op_str:
            return x
    return None

def main():
    # ---------------- A: 13 站点 = call helper_k（capstone 重解析） ----------------
    print('A. 13 站点调用正确 helper_k')
    for va, tgt, host, label in SITES:
        ok('A %s @%x -> %x' % (label, va, tgt), call_at(va, tgt), 'host %x' % host)

    # ---------------- B: 站点字节窗口（防漂移锚） ----------------
    print('B. 关键字节窗口')
    W = [
        ('B1 k1主角 门+站 0x45d9c2', 0x45d9c2, 0x26,
         '6683ff037420478d14bf52e88ee3080083c4046685c0750e8b4c2410bb01000000e878560400'),
        ('B2 k1同伴 rand(5*新级)+站 0x45da24', 0x45da24, 0x22,
         '8d47018d0c8051e830e3080083c4046685c075148b4c2414be01000000e81a560400'),
        ('B3 k1同伴 体力扣减+级读 0x45d9f0', 0x45d9f0, 0x14,
         '8d470f6a03894424188a00c0e8022403660fb6f8'),
        ('B4 k3 站+名表+提示器 0x448b51', 0x448b51, 0x23,
         '8d7e0f8bcfe845a505008a076633c9c0e8068ac85168677b500056e86f79020083c40c'),
        ('B5 k4 leaf 序言 0x451f90', 0x451f90, 0xd, '568b7424088d4e0fe823110500'),
        ('B6 k4 leaf 尾段 0x451f9d', 0x451f9d, 0x1b,
         '8a46106633c924038ac851686c7b500056e82de5010083c40c5ec3'),
        ('B7 k6主角 门+站 0x44734f', 0x44734f, 0x22,
         '6683ff0373538d47018d0c8051e8ff490a0083c4046685c0753f8d4d0fe88fbd0500'),
        ('B8 k6同伴 门+站 0x4473b4', 0x4473b4, 0x2e,
         '8a4310c0e8042403660fb6f06683fe0373598d46018d0c8051e88e490a0083c4046685c075458d4b0fe81ebd0500'),
        ('B9 k8 30日循环 0x45aeea', 0x45aeea, 4, '6683ff1e'),
        ('B10 k8 主角站 0x45aefa', 0x45aefa, 8, '8d4e0fe83e820400'),
        ('B11 k8 同伴 rand10门+站 0x45af02', 0x45af02, 0x28,
         '85db742985ed75186a0ae84f0e090083c4046685c075168a431124033c03730d8d4b0fe816820400'),
        ('B12 k9 满级转调 0x442d86', 0x442d86, 0x15,
         '6683fe03750f5755e8dd01000083c4085f5e5d5bc3'),
        ('B13 k9 阈值switch 0x442daa', 0x442daa, 0x44,
         '83ee00742c4e74164e75396a1ee8a48f0a0083c404663bc31bf6f7deeb2a6a19e8918f0a0083c404663bc31bf6f7deeb176a0ae87e8f0a0083c404663bc31bf6f7deeb04'),
        ('B14 k9 主角站 0x442e5a', 0x442e5a, 8, '8d4d0fe8fe020600'),
        ('B15 k9 同伴站 0x442ece', 0x442ece, 8, '8d4f0fe88a020600'),
        ('B16 k9b 五维门+rand600 0x442fbd', 0x442fbd, 0x2a,
         '8d560a8b460a894424048a4a048a561180e20c884c240880fa080f87910000006858020000e8798d0a00'),
        ('B17 k9b 满级站 0x443049', 0x443049, 8, '8d4e0fe80f010600'),
        ('B18 f6调用方 体力45门 0x44713f', 0x44713f, 0x24,
         '8a4621b22d83c4083ac21bc0b9010000004085ff74063857211bc94185c00f849b000000'),
        ('B19 f2 序言 学者级读 0x458e25', 0x458e25, 0x1e,
         '8b7c2418a13c0652008a4f0f8d5f0f660fb66807c0e90480e103660fb6f1'),
    ]
    for name, va, n, expect in W:
        ok(name, hexs(va, n) == expect, hexs(va, n))

    # ---------------- C: 门条件结构断言 ----------------
    print('C. 门条件（结构断言）')
    # k2 门槛 0x459000(资本N, 级L)：40/70/100
    ok('C1 L0 门 cmp di,0x28', mnemo_at(0x45902a, 'cmp', 'di, 0x28'), '')
    ok('C2 L1 门 cmp di,0x46', mnemo_at(0x459036, 'cmp', 'di, 0x46'), '')
    ok('C3 L2 门 cmp di,0x64', mnemo_at(0x459077, 'cmp', 'di, 0x64'), '')
    ok('C4 L3 拒绝 msg 570(0x23a)', mnemo_at(0x4590af, 'push', '0x23a'), '')
    # k2 学费 0x4590d0：90-N/2 / 600-3N / 5000-2N
    ok('C5 学费L0=0x5a-N/2', mnemo_at(0x459166, 'shr', 'dx, 1')
       and mnemo_at(0x459169, 'mov', 'esi, 0x5a'), '')
    ok('C6 学费L1=0x258-3N', mnemo_at(0x459131, 'mov', 'esi, 0x258')
       and mnemo_at(0x45913c, 'lea', 'edx, [eax + eax*2]'), '')
    ok('C7 学费L2=0x1388-2N', mnemo_at(0x4590f4, 'mov', 'esi, 0x1388')
       and mnemo_at(0x4590fe, 'lea', 'ecx, [eax + eax]'), '')
    # f2 序言：学者级 byte[+0xf]>>4&3（k2 打包读侧）
    ok('C8 f2 学者级读 + 同伴自取 0x49f610',
       mnemo_at(0x458e39, 'shr', 'cl, 4') and call_at(0x458e43, 0x49f610), '')
    # f2 同伴级比较 → flag
    ok('C9 f2 同伴级 cmp cx,si / jbe→flag',
       mnemo_at(0x458eb0, 'cmp', 'cx, si')
       and mnemo_at(0x458ed7, 'mov', 'dword ptr [esp + 0x10], 1'), '')
    # f2 k2 两站 ecx = ebx(学者+0xf) / esi(同伴+0xf)
    ok('C10 f2 学者站 ecx=ebx', mnemo_at(0x458f8c, 'mov', 'ecx, ebx')
       and call_at(0x458f8e, HELPERS[2]), '')
    ok('C11 f2 同伴站 ecx=esi', mnemo_at(0x458fbe, 'mov', 'ecx, esi')
       and call_at(0x458fc0, HELPERS[2]), '')
    # f2 学费x10 + 0x44e350
    ok('C12 f2 学费x10→0x44e350', mnemo_at(0x458f1b, 'lea', 'ecx, [ebp + ebp*4]')
       and mnemo_at(0x458f1f, 'shl', 'ecx, 1') and call_at(0x458f22, 0x44e350), '')
    # f2 时间：24-时 → 0x4a0d50；再 +14h
    ok('C13 f2 推进 24-时 与 +0xe', mnemo_at(0x458f66, 'mov', 'ecx, 0x18')
       and call_at(0x458f6e, 0x4a0d50) and mnemo_at(0x458f78, 'push', '0xe'), '')
    # k3 体力满 byte[+0x21]==byte[+0x20]
    ok('C14 k3 体力满门 cmp al,cl',
       mnemo_at(0x44899b, 'mov', 'al, byte ptr [esi + 0x21]')
       and mnemo_at(0x44899e, 'mov', 'cl, byte ptr [esi + 0x20]')
       and mnemo_at(0x4489a1, 'cmp', 'al, cl'), '')
    # k3 试合三态 + 尾声 + 4h
    for va, val in [(0x4489a9, 0x62e), (0x4489d1, 0x63f), (0x448abb, 0x640),
                    (0x448af6, 0x642), (0x448b37, 0x643), (0x448bc0, 0x646),
                    (0x448bd1, 0x647), (0x448bf1, 0x648)]:
        ok('C15 k3 seq/msg 0x%x @%x' % (val, va), mnemo_at(va, 'push', '0x%x' % val)
           or mnemo_at(va, 'mov', 'ebp, 0x%x' % val), '')
    ok('C16 k3 0x4a0d50(4,1) 耗4h', mnemo_at(0x448c0f, 'push', '4')
       and call_at(0x448c11, 0x4a0d50), '')
    # k1 调用链 0x45d7a0：主角/同伴实体 + 体力45门
    ok('C17 f1链 0x49f5e0/0x49f610', call_at(0x45d7a3, 0x49f5e0)
       and call_at(0x45d7aa, 0x49f610), '')
    ok('C18 f1链 体力>=0x2d 双检查', mnemo_at(0x45d7cd, 'cmp', 'bx, 0x2d')
       and mnemo_at(0x45d7d3, 'cmp', 'ax, 0x2d'), '')
    ok('C19 f1链 两路进 0x45d830（同伴/0）', call_at(0x45d7e0, 0x45d830)
       and call_at(0x45d7fa, 0x45d830), '')
    # 0x45d830：工钱公式 + yes/no + 进 0x45d950
    ok('C20 工钱基 30-时 /4 封顶5', mnemo_at(0x45d83c, 'mov', 'eax, 0x1e')
       and mnemo_at(0x45d85c, 'cmp', 'eax, 5'), '')
    ok('C21 同伴→工钱x2', mnemo_at(0x45d86b, 'add', 'esi, esi'), '')
    ok('C22 工钱确认 0x47bcc0 + 进0x45d950', call_at(0x45d8a3, 0x47bcc0)
       and call_at(0x45d8ba, 0x45d950), '')
    ok('C23 f1 收尾推进 32-时', mnemo_at(0x45da5e, 'mov', 'edx, 0x20')
       and call_at(0x45da68, 0x4a0d50), '')
    # f6 调用方 0x447110：主角/同伴 + 循环
    ok('C24 f6调用方 0x49f5e0/0x49f610', call_at(0x447113, 0x49f5e0)
       and call_at(0x44711a, 0x49f610), '')
    ok('C25 f6调用方 进0x447230 + jmp 回 0x44718d 打工循环',
       call_at(0x44718f, 0x447230) and mnemo_at(0x4471f6, 'jmp', '0x44718d'), '')
    # f9a 调用方 0x442a80：茶具品质 4-bit + 上限 0/6/13 + 下传
    ok('C26 茶具品质 byte[项+8]>>3&0xf', mnemo_at(0x442b25, 'mov', 'cl, byte ptr [ebx + 8]')
       and mnemo_at(0x442b28, 'shr', 'cl, 3'), '')
    ok('C27 品质上限 switch 0/6/13', mnemo_at(0x442ab9, 'mov', 'eax, 0xd')
       and mnemo_at(0x442ac0, 'mov', 'eax, 6')
       and mnemo_at(0x442ac7, 'xor', 'eax, eax'), '')
    ok('C28 0x442a80 下传 0x442d70', call_at(0x442b92, 0x442d70), '')

    # ---------------- D: 名表立即数 / 升级提示器审计 ----------------
    print('D. 技能名表 0x507b58+id*5 与 0x4704e0 提示器')
    ok('D1 k1 马术名 0x507b5d x2 @f1', [imm_in(0x45d950, 0x45dc00, 0x507b5d)] != [None]
       and imm_in(0x45dab2 - 8, 0x45dad3 + 2, 0x507b5d) is not None, '')
    # 直接数（capstone skipdata 操作数访问包 try）
    def count_imm(lo, hi, val):
        n = 0
        for x in dis(lo, hi - lo):
            try:
                ops = x.operands
            except Exception:
                continue
            for op in ops:
                if op.type == X86_OP_IMM and (op.imm & 0xffffffff) == val:
                    n += 1
        return n
    ok('D2 k2 算术名 0x507b62 x2 @f2', count_imm(0x458e20, 0x459000, 0x507b62) == 2, '')
    ok('D3 k4 忍术名 0x507b6c x1 @leaf', count_imm(0x451f90, 0x451fb8, 0x507b6c) == 1, '')
    ok('D4 k6 洋枪名 0x507b76 x2 @f6外层', count_imm(0x447230, 0x447500, 0x507b76) == 2, '')
    ok('D5 k9 茶道名 0x507b85 x3 @f9a+f9b', count_imm(0x442d70, 0x443100, 0x507b85) == 3, '')
    ok('D6 k3 剑术名 0x507b67 @f3（B4 窗口内）', hexs(0x448b66, 5) == '68677b5000', '')
    ok('D7 f8 寺庙 0x45ade0..0x45af50 无 0x4704e0/名表（礼法无独立提示）',
       count_imm(0x45ade0, 0x45af50, 0x4704e0) == 0
       and count_imm(0x45ade0, 0x45af50, 0x507b80) == 0, 'k8 唯一无提示写站')

    # ---------------- E: leaf xref / 满级转调 xref ----------------
    print('E. leaf 与满级分支 xref（全镜像）')
    insns = list(MD.disasm(MEM, BASE))
    def xrefs(target):
        out = []
        for x in insns:
            if x.mnemonic == 'call':
                try:
                    ops = x.operands
                except Exception:
                    continue
                if len(ops) == 1 and ops[0].type == X86_OP_IMM and ops[0].imm == target:
                    out.append(x.address)
        return out
    ok('E1 k4 leaf 0x451f90 调用方 = {0x451f23,0x451f40,0x4521a7}',
       xrefs(0x451f90) == [0x451f23, 0x451f40, 0x4521a7],
       ' '.join(hex(a) for a in xrefs(0x451f90)))
    ok('E2 满级分支 0x442f70 被转调自 0x442d8e（f9a 满级路径）',
       0x442d8e in xrefs(0x442f70), ' '.join(hex(a) for a in xrefs(0x442f70)))

    # ---------------- F: 消息链锚（msgx id 立即数） ----------------
    print('F. 消息链锚')
    ok('F1 茶道 927/928 (0x39f/0x3a0) 夹主角站',
       mnemo_at(0x442e4c, 'push', '0x39f') and mnemo_at(0x442e7e, 'push', '0x3a0'), '')
    ok('F2 茶道 929/930 (0x3a1/0x3a2) 夹同伴站',
       mnemo_at(0x442ec0, 'push', '0x3a1') and mnemo_at(0x442ef3, 'push', '0x3a2'), '')
    ok('F3 茶道满级 934/935/936 (0x3a6/0x3a7/0x3a8)',
       mnemo_at(0x44301a, 'push', '0x3a6') and mnemo_at(0x443028, 'push', '0x3a7')
       and mnemo_at(0x44303b, 'push', '0x3a8'), '')
    ok('F4 忍里 2704/2706 (0xa90/0xa92) 合格流',
       imm_in(0x451e70, 0x451fa0, 0xa90) is not None
       and imm_in(0x451e70, 0x451fa0, 0xa92) is not None, '')
    ok('F5 忍里 2729(0xaa9)+2689(0xa81) 再指导流',
       mnemo_at(0x452185, 'push', '0xaa9') and mnemo_at(0x452193, 'push', '0xa81'), '')
    ok('F6 铁炮 626(0x272)/628-629(0x274/0x275) 算术派生 msg',
       mnemo_at(0x447132, 'add', 'ecx, 0x272')
       and mnemo_at(0x447175, 'add', 'ebx, 0x275'), '')

    print('\n续241 skill_writer_consumers_ref  ALL PASS (%d)' % len(PASS))

if __name__ == '__main__':
    main()
