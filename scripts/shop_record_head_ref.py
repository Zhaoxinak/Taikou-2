# -*- coding: utf-8 -*-
"""
续247 店铺记录头字段 + 买药÷50 + slot3/4/10 msg ref
====================================================
收口续242/243 残留：

  店铺主人格记录 30×12B @0x517850（[0x52063c] 当前记录）：
    +0x00 word  name_key   人名键（1000+idx→姓@0x5077b0 / 名@0x507888，stride7；
                           兼 SNDATA 会話セリフ MSGX 1000..1029）
    +0x02 word  shop_msg   商店セリフ MSGX（700..728；#29 闇商人 = 0xffff）
    +0x04 byte  job        职业码 0..11（名表@0x5076f0 stride11；0xb=武将类，情报池排除）
    +0x05 byte  province   所属国 ID 0..48（国情表@0x519548×5；与 [0x520603] 匹配过滤）
    +0x06 byte  rank       技艺等级 1..3（道场等与实体技能位比较）
    +0x07 byte  favor      店主好感（续242）
    +0x08 word  facility   设施状态（续243）
    +0x0a byte  progress   进度计数（续243）
    +0x0b byte  flags      事件旗位域（续243）

  买药÷50：魔数 0x51eb851f+sar4 确为有符号整数 ÷50。
    不在 0x44e350 体内——0x44e350 只是 0x44e300(0,amt)→0x4a35c0 扣 S6+0x1e。
    买药路径 0x445679：max_doses = gold÷50（每服 5 贯 = 50 内单位）；
    支付 0x44e350(doses×50)。

运行：python scripts/shop_record_head_ref.py（需 capstone）。ALL PASS 或退出码 1。
"""
import io
import json
import os
import struct
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MEM = open(os.path.join(_ROOT, 'scripts', '_unpacked_mem.bin'), 'rb').read()
BASE = 0x400000
MSG = json.load(open(os.path.join(_ROOT, 'scripts', 'msgx_all_texts.json'),
                     encoding='utf-8'))['texts']
S8 = json.load(open(os.path.join(_ROOT, 'scripts', 'msgx_text_tables.json'),
                    encoding='utf-8'))['S8_dialogue_30x12B']

from capstone import Cs, CS_ARCH_X86, CS_MODE_32  # noqa: E402

_md = Cs(CS_ARCH_X86, CS_MODE_32)
_md.skipdata = True

if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass
elif hasattr(sys.stdout, 'buffer'):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

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
    return MEM[va - BASE: va - BASE + n]


def call_target(va):
    assert MEM[va - BASE] == 0xE8, hex(va)
    rel = struct.unpack_from('<i', MEM, va - BASE + 1)[0]
    return va + 5 + rel


def win(va, n):
    return [(i.mnemonic, i.op_str) for i in _md.disasm(MEM[va - BASE:va - BASE + n], va)]


def g(i):
    return MSG.get(str(i), MSG.get(i))


def gbk_cstr(va, n):
    return at(va, n).split(b'\x00')[0].decode('gbk', 'replace')


def magic_div50(n):
    """imul 0x51eb851f; sar edx,4; add signbit — signed /50."""
    a = n if n < 0x80000000 else n - 0x100000000
    prod = a * 0x51eb851f
    edx = prod >> 32
    if edx >= 0x80000000:
        edx -= 0x100000000
    q = edx >> 4
    return q + (1 if q < 0 else 0)


def push_imm32(va):
    """Read imm32 of `push imm32` (opcode 0x68) at va."""
    assert MEM[va - BASE] == 0x68, hex(va)
    return struct.unpack_from('<I', MEM, va - BASE + 1)[0]


# =====================================================================
print("== A. record head layout (S8 + name tables) ==")
seq = win(0x47ebb0, 0x80)
ok = (('mov', 'esi, 0x517852') in seq and
      ('call', '0x47d930') in seq and
      ('call', '0x47d910') in seq and
      ('add', 'esi, 0xc') in seq and
      ('mov', 'ebx, 0x1e') in seq)
check("A1 S8 serializer 0x47ebb0 = 30x12B field order", ok, str(seq[:8]))

seq = win(0x49c2b0, 0x40)
ok = (('mov', 'ax, word ptr [ecx]') in seq and
      ('cmp', 'ax, 0x3e8') in seq and
      ('cmp', 'ax, 0x7d0') in seq and
      ('add', 'eax, 0x5077b0') in seq)
check("A2a 0x49c2b0: word[+0] in [1000,2000) -> sei table 0x5077b0x7", ok)

seq = win(0x49c310, 0x40)
ok = (('mov', 'ax, word ptr [ecx]') in seq and
      ('cmp', 'ax, 0x3e8') in seq and
      ('add', 'eax, 0x507888') in seq)
check("A2b 0x49c310: word[+0] in [1000,2000) -> mei table 0x507888x7", ok)

check("A3a sei[0]=今井", gbk_cstr(0x5077b0, 7) == '今井')
check("A3b mei[0]=宗久", gbk_cstr(0x507888, 7) == '宗久')
check("A3c sei[26]=施药院", gbk_cstr(0x5077b0 + 26 * 7, 7) == '施药院')
check("A3d mei[29]=奸商", gbk_cstr(0x507888 + 29 * 7, 7) == '奸商')

check("A4a S8 W0 = 1000..1029", [r['talk_id'] for r in S8] == list(range(1000, 1030)))
check("A4b S8 W1 = 700..728 + 0xffff",
      [r['shop_id'] for r in S8[:29]] == list(range(700, 729)) and S8[29]['shop_id'] == 0xffff)

seq = win(0x47b900, 0x50)
ok = (('mov', 'si, word ptr [eax + 2]') in seq and
      ('call', '0x49f190') in seq and
      ('call', '0x47b660') in seq)
check("A5 0x47b900 reads word[shop+2] (shop_msg) into dialog", ok)

# =====================================================================
print("== B. job(+4) / province(+5) / rank(+6) ==")
JOBS = ['大商人', '茶道大师', '洋枪铸造', '南蛮商人', '传教士',
        '剑客', '公卿', '画匠', '僧侣', '忍者', '名医', '神秘商人']
got = [gbk_cstr(0x5076f0 + i * 11, 11) for i in range(12)]
check("B1 job name table 0x5076f0 x12", got == JOBS, str(got))

SLOTS = list(at(0x44e81c, 30))
ok = all(S8[i]['b4'] == SLOTS[i] for i in range(29)) and S8[29]['b4'] == 11 and SLOTS[29] == 0x0c
check("B2 S8.b4(job) == id->slot (#29=神秘商人/exit)", ok,
      f"mismatch={[i for i in range(29) if S8[i]['b4'] != SLOTS[i]]}")

seq = win(0x45eb30, 0x50)
ok = (('mov', 'ecx, 0x517854') in seq and
      ('cmp', 'byte ptr [ecx], 0xb') in seq and
      ('cmp', 'byte ptr [ecx + 3], 0xa') in seq)
check("B3 intel pool 0x45eb30: job(+4)!=0xb and favor(+7)<0xa", ok)

seq = win(0x447f55, 0x40)
ok = (('mov', 'cl, byte ptr [eax + 5]') in seq and
      ('cmp', 'cl, 0x31') in seq and
      any(m == 'lea' and '0x519548' in o for m, o in seq))
check("B4a +5 < 0x31 -> lea [id*5+0x519548] province @0x447f65", ok, str(seq[:8]))

seq = win(0x46fda0, 0x40)
ok = (('mov', 'dl, byte ptr [0x520603]') in seq and
      ('mov', 'eax, 0x517850') in seq and
      ('cmp', 'byte ptr [eax + 5], dl') in seq)
check("B4b 0x46fda0: filter byte[+5] == [0x520603] current province", ok)

ranks = sorted({r['b6'] for r in S8})
check("B5a S8.b6 in {1,2,3}", ranks == [1, 2, 3], str(ranks))

seq = win(0x448294, 0x40)
ok = (('mov', 'eax, dword ptr [0x52063c]') in seq and
      ('movzx', 'di, byte ptr [eax + 6]') in seq and
      ('mov', 'cx, word ptr [eax + 2]') in seq)
check("B5b dojo reads byte[+6](rank)+word[+2] @0x44829e", ok, str(seq[:8]))

# =====================================================================
print("== C. payment 0x44e350 and buy-medicine /50 ==")
seq = win(0x44e350, 0x20)
ok = seq[0] == ('mov', 'eax, dword ptr [esp + 4]') and \
     ('push', '0') in seq and call_target(0x44e357) == 0x44e300
check("C1 0x44e350 -> 0x44e300(0, amt)", ok, str(seq[:5]))

seq = win(0x44e300, 0x50)
ok = (('mov', 'ecx, 0x516610') in seq and
      ('call', '0x4a35c0') in seq and
      ('call', '0x4a3590') in seq)
check("C2 0x44e300: mode0->0x4a35c0(sub) / mode1->0x4a3590(add) S6", ok)

seq = win(0x4a35c0, 0x20)
ok = (('mov', 'cx, word ptr [esi + 0x1e]') in seq and
      call_target(0x4a35cd) == 0x4ebcd0)
check("C3 0x4a35c0 = sat_sub(word[S6+0x1e], amt)", ok)

ok = all(magic_div50(n) == n // 50 for n in
         [0, 1, 49, 50, 51, 99, 100, 250, 499, 500, 999, 1000, 5000])
check("C4 0x51eb851f+sar4 == signed int /50", ok)

seq = win(0x445664, 0x50)
ok = (('push', '0x2a9') in seq and
      ('mov', 'eax, 0x51eb851f') in seq and
      ('sar', 'edx, 4') in seq and
      ('call', '0x49bae0') in seq)
check("C5a buy-medicine 0x445679: gold/50 -> max_doses (msg 681)", ok, str(seq[:10]))

seq = win(0x4456f1, 0x14)
ok = (('lea', 'eax, [esi + esi*4]') in seq and
      ('lea', 'eax, [eax + eax*4]') in seq and
      ('shl', 'eax, 1') in seq and
      call_target(0x4456fd) == 0x44e350)
check("C5b pay doses*50 -> 0x44e350 @0x4456fd", ok, str(seq))

check("C5c gate gold>=0x32(50) @0x445647",
      win(0x445647, 6)[0] == ('cmp', 'si, 0x32'))
check("C5d msg 681 text has '5'", bool(g(681)) and '5' in g(681))

# =====================================================================
print("== D. slot3 nanban / slot4 church / slot10 doctor msgs ==")


def check_msg(tag, va, expect_id, substr=None):
    got_id = push_imm32(va)
    text = g(got_id)
    ok = got_id == expect_id and text is not None
    if ok and substr:
        ok = substr in text
    check(f"{tag} push {expect_id} @0x{va:06x} | {text}",
          ok, f"got={got_id} text={text}")


check_msg("D1a nanban stranger", 0x450c97, 738, '陌生人')
check_msg("D1b intro letter Q", 0x450cb0, 739, '介绍信')
check_msg("D1c priest letter", 0x450cef, 740, '神父')
seq = win(0x450c61, 0x10)
ok = (('cmp', 'byte ptr [eax + 7], 0x32') in seq and
      ('add', 'ecx, 0x2b6') in seq)
check("D1d greet msg=0x2b6+sbb -> 693/694", ok)
check("D1e msg 693 exists", g(693) is not None)
check("D1f msg 694 exists", g(694) is not None)
check_msg("D1g teppo 10", 0x450842, 729, '10')
check_msg("D1h thanks come again", 0x450dfb, 695)

check_msg("D2a church greet", 0x44bb35, 4623, '教堂')
check_msg("D2b intro letter", 0x44d0ec, 4625, '信')
check_msg("D2c intel fee", 0x44cb13, 4646, '贯')
check_msg("D2d diplomacy", 0x44cbe2, 4650, '外交')
check_msg("D2e volunteer invite", 0x44be3e, 4633)

check_msg("D3a want medicine", 0x445609, 679, '药')
check_msg("D3b one dose 5 kan", 0x44566a, 681, '5')
check_msg("D3c not enough money", 0x445653, 682, '钱')
check_msg("D3d then N kan", 0x4456db, 683, '贯')
check_msg("D3e take care", 0x44570b, 684)
check_msg("D3f poor lecture", 0x445333, 674)
check_msg("D3g anything else", 0x444fc5, 685)

# =====================================================================
print("== E. field access anchors ==")
seq = win(0x49f190, 0x20)
ok = (('push', '0x517818') in seq and call_target(0x49f19a) == 0x49f150)
check("E1 0x49f190(shop) fills name buf 0x517818 via word[+0]", ok)

seq = win(0x456db6, 0x30)
ok = (('movzx', 'di, byte ptr [esi + 4]') in seq and
      any(m == 'lea' and '0x5076f0' in o for m, o in seq))
check("E2 street event reads job(+4) -> 0x5076f0 @0x456db6", ok)

seq = win(0x44e742, 0x20)
ok = (('lea', 'eax, [eax + eax*2]') in seq and
      ('lea', 'ecx, [eax*4 + 0x517850]') in seq)
check("E3 enter-shop 0x44e749: id*12 + 0x517850", ok)

# =====================================================================
print()
print(f"结果: {PASS} PASS / {FAIL} FAIL  (共 {PASS + FAIL})")
sys.exit(1 if FAIL else 0)
