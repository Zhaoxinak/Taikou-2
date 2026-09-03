# -*- coding: utf-8 -*-
"""
续243 店铺设施流 ref（画师 slot7 / 医师 slot10 / 教会 slot4 / 南蛮商馆 slot3）
==============================================================================
突破（详见 BREAKTHROUGHS.md 续243）：
  1. slot7 = 画师（续242 遗漏的第 11 设施，id19,20）：
     - 袄绘依頼：好感 >=0x1e(30) 门（@0x444508）→ 0x47bcc0(msg 1376) 确认 →
       所持金 [0x51662e] >= 0x320(80贯) 检查 → 0x44e350(0x320) 支付 →
       +0x0a = 20 + rand(41)（完成剩余天数，@0x44458c..a0）→ +0x08 = 1（制作中）。
     - 鉴定 5 贯（msg 1390）；收购珍品（1383-1385）。
  2. 医师（slot10，id26-28）：
     - +0x08 word = 就诊亲密度（就诊时 +10，@0x4450be）；==0x64(100) → 免费治疗。
     - 治疗免费判定（0x4451a0）：好感(+0x07)==100 必免，否则 rand(100) < 好感-10；
       不免则 0x44e540(5) 好感 -5。治疗 = 推进 0x20-时（次日 8 点）+ 主/同伴体力满（0x49a630）。
     - 诊金公式 0x4453a0(实体, 亲密度) = gap×(100-亲密度)×身分 /100：
       gap = byte[+0x20]-byte[+0x21]、身分 = word[+0x2c]>>8 &7、
       ÷100(0x51eb851f sar5) → ÷10(0x66666667 sar2) → ×10（取 10 的倍数）、最低 10。
     - 穷人流：+0x0a = 免费治疗计数 sat_add cap3（0x4ebca0）；==3 → msg 674 →
       计数清 0 + 0x44e560(0xa) 好感 -10。
     - 买药：药罐 = word[S6+0x26]>>12（getter 0x49bae0），上限 10（cmp ax,0xa）；
       msg 681「一服药5贯」；总价 = min(...)*10 经 0x44e350。
  3. 教会（slot4，id11,12）：
     - 义工（0x44c330..）：好感(+0x07) >=0x46(70) → +5；0x49f7a0() 分歧 → +5/+10；
       +0x0b bit1/bit0 = 义工首回标记（各再 +5，or 写回 0x49bfe0）；
       +0x07 义工增长上限钳 0x45(69)；受益 = 实体+0x0e（魅力）+1（0x4a3000, cap100）。
     - 大名情报（0x44caeb..）：捐额 eax → 情报费 = 5 - 捐额/20 贯（÷20 魔数
       0x666667 sar3）；捐 100 贯（cmp ax,0x64）→ 免费；支付 = 费×10 经 0x44e350；
       内容 = 大名外交关系（msg 4650）。
     - 介绍信（msg 4625 @0x44d0ec）→ 南蛮 739/740 神父介绍信链。
  4. 南蛮商馆（slot3，id9,10）：
     - 陌生人门（0x450c40..）：+0x07 == 0 → msg 738「不和陌生人做生意」→ 介绍信流；
       有关系 → 问候 msg = 0x2b6 + sbb(+7 < 0x32)（<50 → 693「欢迎」，>=50 → 694「多买点」）。
     - 洋枪 10 支价格（0x450813..）= 15 - 好感/30 贯（÷30 魔数 0x88888889 sar4）；
       好感 ==100 → 特殊路径 0x4508d0。
  5. 通用 setter bodies：0x49bfc0(word[ecx+8]=arg) / 0x49bfd0(byte[ecx+0xa]=arg) /
     0x49bfe0(byte[ecx+0xb]=arg)，均 ret 4。

运行：任何 python（需 capstone）。ALL PASS 或首个 FAIL 退出码 1。
"""
import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MEM = open(os.path.join(_ROOT, 'scripts', '_unpacked_mem.bin'), 'rb').read()
BASE = 0x400000

from capstone import Cs, CS_ARCH_X86, CS_MODE_32  # noqa: E402

_md = Cs(CS_ARCH_X86, CS_MODE_32)
_md.skipdata = True

PASS = 0
FAIL = 0


def check(name, cond, detail=''):
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"  [ ok ] {name}")
    else:
        FAIL += 1
        print(f"  [FAIL] {name}  {detail}")


def at(va, n):
    return MEM[va - BASE: va - BASE + n].hex()


def call_target(va):
    assert MEM[va - BASE] == 0xE8, hex(va)
    import struct
    rel = struct.unpack_from('<i', MEM, va - BASE + 1)[0]
    return va + 5 + rel


def win(va, n):
    return [(i.mnemonic, i.op_str) for i in _md.disasm(MEM[va - BASE: va - BASE + n], va)]


def has(seq, m, o):
    return (m, o) in seq


# =====================================================================
print("== A. 画师 slot7（袄绘依頼 / 鉴定） ==")
# A1 msg 锚
check("A1a push 0x559(1369 依頼) @0x4444f4", at(0x4444f4, 5) == '6859050000')
check("A1b push 0x560(1376 80贯确认) @0x44452d", at(0x44452d, 5) == '6860050000')
check("A1c push 0x561(1377 材料费) @0x444550", at(0x444550, 5) == '6861050000')
check("A1d push 0x562(1378 全力制作) @0x444571", at(0x444571, 5) == '6862050000')
check("A1e push 0x56e(1390 鉴定5贯) @0x444733", at(0x444733, 5) == '686e050000')
check("A1f push 0x55f(1375 谢绝请求) @0x4445cd", at(0x4445cd, 5) == '685f050000')
# A2 好感 >=0x1e 门
seq = win(0x444508, 10)
check("A2 好感门 cmp byte[ecx+7],0x1e @0x444508",
      seq[:2] == [('cmp', 'byte ptr [ecx + 7], 0x1e'), ('jb', '0x4445c8')], str(seq))
# A3 支付 0x320(80贯) 经 0x44e350
seq = win(0x44457f, 0x10)
ok = (seq[0] == ('push', '0x320') and
      call_target(0x444584) == 0x44e350)
check("A3 支付 0x320(80贯) → 0x44e350 @0x44457f", ok, str(seq[:2]))
# A4 完成天数 = 20 + rand(41) → +0x0a
seq = win(0x44458c, 0x1a)
ok = (seq[0] == ('push', '0x29') and
      call_target(0x44458e) == 0x4ebd60 and
      ('add', 'eax, 0x14') in seq and
      ('push', 'eax') in seq and
      any(m == 'call' and o == '0x49bfd0' for m, o in seq))
check("A4 +0x0a = 20+rand(41)（袄绘剩余天数）@0x44458c", ok, str(seq[:5]))
# A5 +0x08 = 1（制作中）
ok = (at(0x4445ab, 2) == '6a01' and call_target(0x4445ad) == 0x49bfc0)
check("A5 +0x08 = 1（制作中标记）@0x4445ab", ok)
# A6 slot7 归属：SLOTS[19]=SLOTS[20]=7（id19,20=画师 2 家）
check("A6 SLOTS[19]=SLOTS[20]=7",
      at(0x44e81c + 19, 1) == '07' and at(0x44e81c + 20, 1) == '07')

# =====================================================================
print("== B. 医师 slot10（就诊 / 治疗 / 诊金 / 穷人流 / 买药） ==")
# B1 +0x08 亲密度 += 10（就诊）
seq = win(0x4450be, 9)
ok = (('add', 'edi, 0xa') in seq and ('push', 'edi') in seq and
      any(m == 'call' and o == '0x49bfc0' for m, o in seq))
check("B1a 就诊 +0x08 += 10 @0x4450be", ok, str(seq))
seq = win(0x4450c7, 6)
check("B1b cmp si,0x64（亲密度 100 → 免费）@0x4450c7",
      seq == [('cmp', 'si, 0x64'), ('jne', '0x4450f0')], str(seq))
# B2 免费判定：好感100 必免 / rand(100)<好感-10 / 否则 0x44e540(5)
seq = win(0x4451be, 0x3a)
ok = (('cmp', 'si, 0x64') in seq and
      ('je', '0x4451f6') in seq and
      ('sub', 'eax, 0xa') in seq and
      ('push', '0x64') in seq and
      any(m == 'call' and o == '0x4ebd60' for m, o in seq) and
      any(m == 'call' and o == '0x44e540' for m, o in seq) and
      ('push', '5') in seq)
check("B2 治疗免费判定 rand(100)<好感-10 else 0x44e540(5) @0x4451be", ok, str(seq[:8]))
# B3 治疗执行：推进 0x20-时 + 主/同伴体力满 0x49a630
seq = win(0x4451f6, 0x50)
ok = (('mov', 'ecx, 0x20') in seq and ('sub', 'ecx, eax') in seq and
      any(m == 'call' and o == '0x4a0d50' for m, o in seq) and
      any(m == 'call' and o == '0x49a630' for m, o in seq))
check("B3 治疗 = 0x4a0d50(0x20-时) + 0x49a630 体力满 @0x4451f6", ok, str(seq[:6]))
# B4 诊金公式 0x4453a0
seq = win(0x4453a0, 0x6c)
ok = (('mov', 'cl, byte ptr [eax + 0x20]') in seq and
      ('mov', 'dl, byte ptr [eax + 0x21]') in seq and
      ('mov', 'esi, 0x64') in seq and
      ('mov', 'ax, word ptr [eax + 0x2c]') in seq and
      ('shr', 'eax, 8') in seq and ('and', 'eax, 7') in seq and
      ('mov', 'eax, 0x51eb851f') in seq and ('sar', 'edx, 5') in seq and
      ('mov', 'eax, 0x66666667') in seq and ('sar', 'edx, 2') in seq and
      ('lea', 'eax, [edx + edx*4]') in seq and ('shl', 'eax, 1') in seq and
      ('cmp', 'ax, 0xa') in seq and ('mov', 'eax, 0xa') in seq)
check("B4 诊金 = gap×(100-亲密度)×身分/100 取10倍数 min10 @0x4453a0", ok)
# B5 穷人流：+0x0a = 免费计数 cap3；==3 → 清0 + 0x44e560(0xa)
seq = win(0x445302, 0x70)
ok = (('movzx', 'cx, byte ptr [eax + 0xa]') in seq and
      ('push', '3') in seq and ('push', '1') in seq and
      any(m == 'call' and o == '0x4ebca0' for m, o in seq) and
      ('cmp', 'byte ptr [eax + 0xa], 3') in seq and
      ('push', '0') in seq and
      any(m == 'call' and o == '0x49bfd0' for m, o in seq) and
      ('push', '0xa') in seq and
      any(m == 'call' and o == '0x44e560' for m, o in seq))
check("B5 穷人流 +0x0a cap3 → 清0 + 0x44e560(0xa) 好感-10 @0x445302", ok, str(seq[:6]))
# B6 买药：药罐 getter / 上限 10 / ×10 支付
check("B6a getter 0x49bae0 = word[S6+0x26]>>12",
      at(0x49bae0, 10) == '33c0668b4126c1e80cc3')
seq = win(0x44561e, 0x12)
ok = (('mov', 'ecx, 0x516610') in seq and
      any(m == 'call' and o == '0x49bae0' for m, o in seq) and
      ('cmp', 'ax, 0xa') in seq)
check("B6b 药罐 = 0x49bae0() 上限 10 @0x44561e", ok, str(seq))
seq = win(0x4456f1, 0x10)
ok = (('lea', 'eax, [eax + eax*4]') in seq and ('shl', 'eax, 1') in seq and
      ('push', 'eax') in seq and call_target(0x4456fd) == 0x44e350)
check("B6c 总价 ×10 → 0x44e350 @0x4456f7", ok, str(seq))
check("B6d msg 681(一服5贯) push 0x2a9 @0x44566a", at(0x44566a, 5) == '68a9020000')

# =====================================================================
print("== C. 教会 slot4（义工 / 大名情报 / 介绍信） ==")
# C1 义工好感上限钳 0x45(69)
seq = win(0x44c384, 0x16)
ok = (('mov', 'al, byte ptr [ecx + 7]') in seq and
      ('cmp', 'eax, 0x45') in seq and ('mov', 'eax, 0x45') in seq and
      any(m == 'call' and o == '0x49bfb0' for m, o in seq))
check("C1 +0x07 义工增长钳 0x45 @0x44c384", ok, str(seq))
# C2 好感>=70 → +5
seq = win(0x44c337, 8)
ok = (seq[0] == ('cmp', 'byte ptr [ecx + 7], 0x46') and
      seq[1][0] == 'jb' and
      ('push', '5') in seq and call_target(0x44c33f) == 0x4a3630)
check("C2 好感>=0x46(70) → 0x4a3630(5) @0x44c337", ok, str(seq))
# C3 +5/+10 分歧（neg/sbb/and5/add5）
seq = win(0x44c344, 0x16)
ok = (call_target(0x44c344) == 0x49f7a0 and
      ('neg', 'eax') in seq and ('sbb', 'eax, eax') in seq and
      ('and', 'eax, 5') in seq and ('add', 'eax, 5') in seq and
      ('push', 'eax') in seq and call_target(0x44c35a) == 0x4a3630)
check("C3 义工好感 +5/+10 分歧 @0x44c344", ok, str(seq[:6]))
# C4 +0x0b bit1/bit0 义工首回标记
seq = win(0x44c365, 0x44)
ok = (('movzx', 'bx, byte ptr [ecx + 0xb]') in seq and
      ('test', 'bl, 2') in seq and ('or', 'ebx, 2') in seq and
      ('test', 'bl, 1') in seq and
      any(m == 'call' and o == '0x49bfe0' for m, o in seq))
check("C4 +0x0b bit1/bit0 义工首回标记 → 0x49bfe0 @0x44c365", ok, str(seq[:6]))
# C5 受益 = 实体+0x0e 魅力 +1（0x4a3000 = byte[ecx+4] sat_add cap100）
check("C5a 0x4a3000 = sat_add(byte[ecx+4],arg,cap0x64)",
      at(0x4a3000, 4) == '8b442404' and
      ('movzx', 'cx, byte ptr [esi + 4]') in win(0x4a3000, 0x1c) and
      ('mov', 'byte ptr [esi + 4], al') in win(0x4a3000, 0x1c) and
      any(m == 'call' and o == '0x4ebca0' for m, o in win(0x4a3000, 0x1c)))
seq = win(0x44c318, 8)
ok = (('push', '1') in seq and ('lea', 'ecx, [esi + 0xa]') in seq and
      call_target(0x44c31d) == 0x4a3000)
check("C5b 义工受益 0x4a3000(实体+0x0e, 1) @0x44c318", ok, str(seq))
# C6 大名情报：费 = 5 - 捐/20；捐100免费；×10 支付
seq = win(0x44caeb, 0x20)
ok = (('mov', 'esi, 5') in seq and
      ('mov', 'eax, 0x66666667') in seq and ('sar', 'edx, 3') in seq and
      ('sub', 'esi, edx') in seq)
check("C6a 情报费 = 5 - 捐额/20（÷20 魔数 sar3）@0x44caeb", ok, str(seq[:6]))
seq = win(0x44caca, 7)
check("C6b 捐 100 贯 → 免费（cmp ax,0x64 sete）@0x44caca",
      seq == [('cmp', 'ax, 0x64'), ('sete', 'dl')], str(seq))
seq = win(0x44cb71, 8)
ok = (('lea', 'eax, [esi + esi*4]') in seq and ('shl', 'eax, 1') in seq and
      call_target(0x44cb77) == 0x44e350)
check("C6c 情报费 ×10 → 0x44e350 @0x44cb71", ok, str(seq))
# C7 介绍信 msg 4625
check("C7 push 0x1211(4625 介绍信) @0x44d0ec", at(0x44d0ec, 5) == '6811120000')

# =====================================================================
print("== D. 南蛮商馆 slot3（陌生人门 / 洋枪） ==")
# D1 陌生人门 +0x07==0 → msg 738
seq = win(0x450c48, 7)
check("D1a mov cl,[eax+7]; test cl,cl @0x450c48",
      seq == [('mov', 'cl, byte ptr [eax + 7]'), ('test', 'cl, cl'),
              ('je', '0x450c8b')], str(seq))
check("D1b push 0x2e2(738 陌生人) @0x450c97", at(0x450c97, 5) == '68e2020000')
# D2 问候 sbb 分歧 693/694（好感 50）
seq = win(0x450c61, 0x10)
ok = (('cmp', 'byte ptr [eax + 7], 0x32') in seq and
      ('sbb', 'ecx, ecx') in seq and ('add', 'ecx, 0x2b6') in seq)
check("D2 问候 msg = 0x2b6 + sbb（693 欢迎/694 多买点，门 0x32）@0x450c61", ok, str(seq))
# D3 洋枪 10 支 = 15 - 好感/30 贯；好感100 → 0x4508d0
seq = win(0x450801, 0x34)
ok = (('cmp', 'si, 0x64') in seq and
      ('mov', 'eax, 0x88888889') in seq and ('sar', 'edx, 4') in seq and
      ('mov', 'esi, 0xf') in seq and ('sub', 'esi, edx') in seq)
check("D3a 洋枪价 = 15 - 好感/30（÷30 魔数 0x88888889 sar4）@0x450819", ok, str(seq[:6]))
seq = win(0x450807, 6)
check("D3b 好感100 → 0x4508d0 特殊路径 @0x450807",
      seq[0] == ('push', 'edi') and call_target(0x450808) == 0x4508d0, str(seq))
# D4 msg 729「10支%u贯」
check("D4 push 0x2d9(729) @0x450842", at(0x450842, 5) == '68d9020000')

# =====================================================================
print("== E. 通用 setter/getter bodies ==")
check("E1 0x49bfc0 = word[ecx+8]=arg; ret 4", at(0x49bfc0, 12) == '668b44240466894108c20400')
check("E2 0x49bfd0 = byte[ecx+0xa]=arg; ret 4", at(0x49bfd0, 10) == '8a44240488410ac20400')
check("E3 0x49bfe0 = byte[ecx+0xb]=arg; ret 4", at(0x49bfe0, 10) == '8a44240488410bc20400')
check("E4 0x49bae0 = (word[ecx+0x26]>>12)&0xffff", at(0x49bae0, 10) == '33c0668b4126c1e80cc3')

# =====================================================================
print()
print(f"结果: {PASS} PASS / {FAIL} FAIL  (共 {PASS + FAIL})")
sys.exit(1 if FAIL else 0)
