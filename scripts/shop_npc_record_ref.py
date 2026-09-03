# -*- coding: utf-8 -*-
"""
续242 店铺主人格记录表 ref（shop NPC record table）
====================================================
突破（详见 BREAKTHROUGHS.md 续242）：
  1. 入店总分发器 0x44e710(shop_id)：[0x52063c] = 0x517850 + shop_id*12
     （店铺主人格记录表 30 记录 x 12B = 0x517850..0x5179b8，恰顶国政治表 0x5179b8）。
     shop_id >= 0x1e(30) → [0x52063c] = NULL；离店尾 0x44e7d4 恒置 NULL。
  2. id→handler 字节表 @0x44e81c（30 项）+ 槽跳表 @0x44e7e8（13 项，第 13 项=出店路径）。
     设施身份（msg 锚）：商家x5 / 茶人x1 / 铁炮锻冶x3 / 南蛮商馆x2 / 教会x2 /
     道场x3 / 公家x3 / 寺x3 / 忍里x2 / 医师x3 / #29=闇商人（专属事件流 0x460890）。
  3. +0x07 = 店主对主角的「关系值」（语义随设施）：
     - setter 三件套：0x49bfb0(直写) / 0x4a3630(sat_add cap 100, thiscall) /
       0x44e560(sat_sub floor 1 消费站) / 0x44e540 = 0x4a3630 的 [0x52063c] 薄包装。
     - 商家初访置 1（0x4577a2）；0x44be13/0x44c394 上限钳 0x45 写入；0x47275b 置 0x64。
     - 纠偏续241：学做生意门 40/70/100 与学费 90-N/2 中的 byte[[0x52063c]+0x07]
       = 商家好感（非「商人资本」）——学费公式即好感折扣。
  4. 闇商人记录 #29(0x5179ac)：0x460890 事件流硬编码指针；0x461da0 = 事件可用判定
     (word[S6+8] ∈ {0,1})；四 mode 门 `cmp byte[+7],2`（0x460945/0x460fe0/0x461452/
     0x4619f2）+ 两处 cap-3 计数写器（0x460a23/0x4614a8）—— 交易阶段计数 0..3。
  5. 持有物选择对话框 0x44e110：0x47b590(msg, cb=0x44e0c0, 0, 0xffff) → 0x47b430
     (msg,8,cb,0,0xffff,1)；返回 选中 idx / -1=取消哨兵；选中 → [0x517838][idx] 取
     对象 → 0x44d240 = 置 [0x5236f2] 并 jmp 0x4b0ad0(ecx=0x523680) 茶室/鉴定 UI。
     0x44e0c0 = 条目绘制回调（vtable [edx+4]/[edx+8]，word[obj+8] bit0x80/bit8 分支）。

运行：任何 python（需 capstone）。ALL PASS 或首个 FAIL 退出码 1。
"""
import os
import struct
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
    return MEM[va - BASE: va - BASE + n]


def dword(va):
    return struct.unpack_from('<I', MEM, va - BASE)[0]


def call_target(va):
    """E8 rel32 at va -> absolute target"""
    assert MEM[va - BASE] == 0xE8
    rel = struct.unpack_from('<i', MEM, va - BASE + 1)[0]
    return va + 5 + rel


def disasm_window(va, n):
    return list(_md.disasm(MEM[va - BASE: va - BASE + n], va))


def find_all(pattern, lo=0, hi=len(MEM)):
    out, i = [], lo
    p = bytes.fromhex(pattern)
    while True:
        i = MEM.find(p, i, hi)
        if i < 0:
            return out
        out.append(BASE + i)
        i += 1


# =====================================================================
print("== A. 入店总分发器 0x44e710 ==")
# A1 序言几何：ebx=shop_id；范围检查 0x18..0x1c
check("A1a mov ebx,[esp+8]", at(0x44e711, 4).hex() == '8b5c2408')
check("A1b cmp bx,0x18", at(0x44e715, 4).hex() == '6683fb18')
check("A1c cmp bx,0x1c", at(0x44e71b, 4).hex() == '6683fb1c')
# A2 记录表 lea ecx,[eax*4+0x517850] + 存 [0x52063c]
check("A2a lea ecx,[eax*4+0x517850] @0x44e74c",
      at(0x44e74c, 7).hex() == '8d0c8550785100')
check("A2b mov [0x52063c],ecx @0x44e753",
      at(0x44e753, 6).hex() == '890d3c065200')
check("A2c mov [0x52063c],0 @0x44e75b (id>=0x1e)",
      at(0x44e75b, 10).hex() == 'c7053c06520000000000')
# A3 出店尾：push 0 → 存 NULL → 0x44de80(0)
check("A3a push 0 @0x44e7d2", at(0x44e7d2, 2).hex() == '6a00')
check("A3b mov [0x52063c],0 @0x44e7d4 (离店置 NULL)",
      at(0x44e7d4, 10).hex() == 'c7053c06520000000000')
check("A3c call 0x44de80 @0x44e7de", call_target(0x44e7de) == 0x44de80)
# A4 槽跳表 @0x44e7e8（12 handler + 第13项=出店路径 0x44e7d2）
TBL = [0x44e780, 0x44e787, 0x44e78e, 0x44e795, 0x44e79c,
       0x44e7a3, 0x44e7aa, 0x44e7b1, 0x44e7b8, 0x44e7bf,
       0x44e7c6, 0x44e7cd, 0x44e7d2]
got = [dword(0x44e7e8 + i * 4) for i in range(13)]
check("A4 槽跳表 13 项", got == TBL, f"{[hex(x) for x in got]}")
# A5 id→slot 字节表 @0x44e81c（30 项）
SLOTS = [0, 0, 0, 0, 0, 1, 2, 2, 2, 3, 3, 4, 4, 5, 5, 5,
         6, 6, 6, 7, 7, 8, 8, 8, 9, 9, 0xa, 0xa, 0xa, 0x0c, 0x0b]
got = list(at(0x44e81c, 31))
check("A5 id→slot 字节表 31 项", got == SLOTS, f"{got}")
# A6 分发体：跳表 13 项本身就是 e8 rel32 call 指令站址，其目标才是 12 个 handler
HANDLERS = [0x457760, 0x441d10, 0x446020, 0x44f820, 0x44bb00, 0x4476b0,
            0x449e90, 0x444280, 0x45a800, 0x451560, 0x444e80, 0x44b5e0]
calls = [call_target(va) for va in TBL[:12]]
check("A6 跳表前 12 项 = call 站址，目标 == 12 handler", calls == HANDLERS,
      f"{[hex(x) for x in calls]}")
# A7 低 id 守卫：<0x18 须 0x4705b0(0) 放行
check("A7a call 0x4705b0 @0x44e723", call_target(0x44e723) == 0x4705b0)
check("A7b call 0x44de80(1) @0x44e735", call_target(0x44e735) == 0x44de80)

# =====================================================================
print("== B. 记录表几何与指针生命周期 ==")
# B1 [0x52063c] 全镜像引用计数与存储站全集
occ = find_all('3c065200')
check("B1a raw 0x52063c 引用 = 768", len(occ) == 768, str(len(occ)))
stores = []
for va in occ:
    fo = va - BASE
    if fo < 2:          # 文件头部误命中，无前置操作码可读
        continue
    op1, op2 = MEM[fo - 1], MEM[fo - 2]
    if op1 == 0xA3:                       # mov [moffs],eax
        stores.append(va - 1)
    elif op2 == 0xC7 and op1 == 0x05:     # mov [moffs],imm32
        stores.append(va - 2)
    elif op2 == 0x89 and op1 in (0x05, 0x0D, 0x15, 0x1D, 0x25, 0x2D, 0x35, 0x3D):
        stores.append(va - 2)             # mov [moffs],reg
check("B1b 存储站全集 = {0x44e753,0x44e75b,0x44e7d4,0x460890}",
      sorted(set(stores)) == [0x44e753, 0x44e75b, 0x44e7d4, 0x460890],
      f"{[hex(x) for x in sorted(set(stores))]}")
# B2 0x460890 闇商人事件入口：硬编码 0x5179ac
check("B2a mov [0x52063c],0x5179ac @0x460890",
      at(0x460890, 10).hex() == 'c7053c065200ac795100')
check("B2b 0x5179ac = 记录 #29", 0x5179ac == 0x517850 + 29 * 12)
check("B2c 记录表尾 0x5179b8 = 国政治表基址", 0x517850 + 30 * 12 == 0x5179b8)
check("B2d call 0x461da0 @0x46089a", call_target(0x46089a) == 0x461da0)
# B3 0x461da0 = 事件可用判定 word[S6+8]∈{0,1}
check("B3a 0x49f6b0 = mov eax,0x516610(S6); ret",
      at(0x49f6b0, 5).hex() == 'b810665100')
w = disasm_window(0x461db6, 0x18)
seq = [(i.mnemonic, i.op_str) for i in w]
check("B3b word[S6+8]∈{0,1}→1 判定序列",
      any(m == 'cmp' and o == 'word ptr [eax + 8], 0' for m, o in seq) and
      any(m == 'cmp' and o == 'word ptr [eax + 8], 2' for m, o in seq) and
      any(m == 'mov' and o == 'eax, 1' for m, o in seq), str(seq))
# B4 闇商人入口问候 msg 0xfad(4013)
check("B4a push 0xfad @0x4608a8", at(0x4608a8, 5).hex() == '68ad0f0000')
check("B4b call 0x47b900 @0x4608ae", call_target(0x4608ae) == 0x47b900)
# B5 四 mode 的 `cmp byte[ecx+7],2` 门（交易阶段计数）
gates = sorted(va for va in find_all('8b0d3c06520080790702'))
check("B5 cmp byte[+7],2 门 = 4 处",
      gates == [0x46093f, 0x460fda, 0x46144c, 0x4619ec],
      f"{[hex(x) for x in gates]}")
# B6 cap-3 计数写器 ×2（movzx [ecx+7] → inc → cmp 3/jbe → mov 3 → push → 0x49bfb0）
for va, tag in ((0x460a23, 'mode0'), (0x4614a8, 'mode1')):
    w = disasm_window(va, 0x24)
    seq = [(i.mnemonic, i.op_str) for i in w]
    ok = (('mov', 'ecx, dword ptr [0x52063c]') in seq and
          ('movzx', 'ax, byte ptr [ecx + 7]') in seq and
          ('inc', 'eax') in seq and
          any(m == 'cmp' and o == 'eax, 3' for m, o in seq) and
          any(m == 'mov' and o == 'eax, 3' for m, o in seq) and
          any(m == 'call' and o == '0x49bfb0' for m, o in seq))
    check(f"B6 cap-3 写器@0x{va:06x}({tag})", ok, str(seq[:6]))

# =====================================================================
print("== C. +0x07 关系值 setter 三件套与写侧谱系 ==")
# C1 直写器 0x49bfb0 = byte[ecx+7]=al; ret 4（10 字节全序列）
check("C1 0x49bfb0 字节", at(0x49bfb0, 10).hex() == '8a442404884107c20400')
# C2 饱和加 cap100：0x4a3630 (thiscall ret 4, NULL 守卫)
w = disasm_window(0x4a3630, 0x24)
seq = [(i.mnemonic, i.op_str) for i in w]
ok = (('push', 'esi') in seq and
      ('mov', 'esi, ecx') in seq and
      ('test', 'esi, esi') in seq and
      ('movzx', 'cx, byte ptr [esi + 7]') in seq and
      ('push', '0x64') in seq and
      any(m == 'call' and o == '0x4ebca0' for m, o in seq) and
      ('mov', 'byte ptr [esi + 7], al') in seq and
      ('ret', '4') in seq)
check("C2 0x4a3630 = sat_add(byte[+7],arg,cap0x64) + NULL 守卫", ok, str(seq[:8]))
# C3 0x44e540 = [0x52063c] 薄包装
check("C3 0x44e540 = mov ecx,[0x52063c]; push arg; call 0x4a3630",
      at(0x44e540, 16).hex() == '8b4424048b0d3c06520050e8e0500500' and
      call_target(0x44e54b) == 0x4a3630)
# C4 0x44e560 = sat_sub 消费站（floor 1）
w = disasm_window(0x44e560, 0x35)
seq = [(i.mnemonic, i.op_str) for i in w]
ok = (('movzx', 'dx, byte ptr [ecx + 7]') in seq and
      call_target(0x44e571) == 0x4ebcd0 and
      ('cmp', 'eax, 1') in seq and
      ('mov', 'eax, 1') in seq and
      call_target(0x44e58f) == 0x49bfb0)
check("C4 0x44e560 = 好感消费 max(1, N-arg) → 0x49bfb0", ok)
# C5 商家初访置 1（0x4577a2）
w = disasm_window(0x457799, 0x18)
seq = [(i.mnemonic, i.op_str) for i in w]
ok = (('mov', 'al, byte ptr [ecx + 7]') in seq and
      ('test', 'al, al') in seq and
      call_target(0x4577aa) == 0x49bfb0)
check("C5 商家入口 +7==0 → 置 1 @0x4577a2", ok)
# C6 上限钳 0x45 写入 ×2（mov eax,0x45 @call-6 → push → call 0x49bfb0）
for va in (0x44be13, 0x44c394):
    check(f"C6 mov eax,0x45 → 0x49bfb0 (call@0x{va:06x})",
          at(va - 6, 5).hex() == 'b845000000' and call_target(va) == 0x49bfb0)
# C7 置 0x64 @0x472759→0x47275b（实测 6a64 | e8→0x49bfb0）
check("C7 push 0x64 → 0x49bfb0 @0x47275b",
      at(0x472759, 2).hex() == '6a64' and call_target(0x47275b) == 0x49bfb0)
# C8 阈值读取锚（好感量表 0..100 的门）：(site, imm)——capstone 立即数打十六进制
thresh = [(0x443cb7, 0x50), (0x444508, 0x1e), (0x44472d, 0x28), (0x44676c, 0x5a),
          (0x4468c6, 0x64), (0x446c47, 0x50), (0x4503e2, 0x64), (0x450c61, 0x32),
          (0x4586a1, 0x64), (0x458bb7, 0x64), (0x44c337, 0x46), (0x44ac20, 0x1e)]
for va, imm in thresh:
    ins = [i for i in disasm_window(va, 5)][0]
    ok = ins.mnemonic == 'cmp' and ins.op_str.startswith('byte ptr [') and \
        ins.op_str.endswith(f'], 0x{imm:x}')
    check(f"C8 cmp byte[reg+7],{imm} @0x{va:06x}", ok, ins.op_str)
# C9 学做生意门读好感（纠偏续241「商人资本」）：0x458e34 = movzx bp,byte[eax+7]
w = disasm_window(0x458e29, 0x14)
seq = [(i.mnemonic, i.op_str) for i in w]
ok = (('mov', 'eax, dword ptr [0x52063c]') in seq and
      ('movzx', 'bp, byte ptr [eax + 7]') in seq and
      ('lea', 'ebx, [edi + 0xf]') in seq)
check("C9 学做生意 0x458e34 读 byte[[0x52063c]+7]（好感）", ok, str(seq[:4]))

# =====================================================================
print("== D. 持有物选择对话框 0x44e110 ==")
# D1 主体：查找→ -1 哨兵 → [0x517838][idx] → 0x44d240；返回 si
check("D1a push 0xffff/0/0x44e0c0 序列",
      at(0x44e115, 12).hex() == '68ffff00006a0068c0e04400')
check("D1b call 0x47b590 @0x44e122", call_target(0x44e122) == 0x47b590)
check("D1c cmp si,-1 @0x44e12c", at(0x44e12c, 4).hex() == '6683feff')
check("D1d mov edx,[0x517838] @0x44e132",
      at(0x44e132, 6).hex() == '8b1538785100')
check("D1e call 0x44d240 @0x44e13f", call_target(0x44e13f) == 0x44d240)
check("D1f mov ax,si（返回选中 idx/-1）@0x44e147",
      at(0x44e147, 3).hex() == '668bc6')
# D2 0x47b590：arg<=0 → -1；否则 0x47b430(arg,8,cb,0,0xffff,1)
check("D2a or ax,0xffff（-1 哨兵）@0x47b5b6", at(0x47b5b6, 4).hex() == '660dffff')
check("D2b push 8/arg → 0x47b430 @0x47b5aa/ad",
      at(0x47b5aa, 2).hex() == '6a08' and call_target(0x47b5ad) == 0x47b430)
# D3 条目绘制回调 0x44e0c0：[0x517838]+idx*4 → vtable，word[obj+8] bit 分支
check("D3a mov ecx,[0x517838] @0x44e0c5", at(0x44e0c5, 6).hex() == '8b0d38785100')
check("D3b mov esi,[ecx+eax*4] @0x44e0cc", at(0x44e0cc, 3).hex() == '8b3481')
check("D3c word[obj+8] bit0x80 / bit1(ah) 分支 @0x44e0d3/d7",
      at(0x44e0d3, 2).hex() == 'a880' and at(0x44e0d7, 3).hex() == 'f6c401')
check("D3d vtable call [edx+4]/[edx+8]",
      at(0x44e0ed, 2).hex() == 'ff52' and at(0x44e0ff, 2).hex() == 'ff50')
# D4 0x44d240 = 选中对象 → 茶室/鉴定 UI
check("D4a mov ecx,0x523680 @0x44d244", at(0x44d244, 5).hex() == 'b980365200')
check("D4b mov [0x5236f2],eax @0x44d249", at(0x44d249, 5).hex() == 'a3f2365200')
check("D4c jmp 0x4b0ad0 @0x44d24e",
      MEM[0x44d24e - BASE] == 0xE9 and
      0x44d24e + 5 + struct.unpack_from('<i', MEM, 0x44d24e - BASE + 1)[0] == 0x4b0ad0)
# D5 xref：0x44e110 调用方恰 9 处
xref = set()
for i in _md.disasm(MEM, BASE):
    try:
        if i.mnemonic == 'call' and i.op_str == '0x44e110':
            xref.add(i.address)
    except Exception:
        continue
EXP9 = {0x441f0a, 0x442347, 0x4425bc, 0x442ada, 0x444622,
        0x44f95c, 0x4501b4, 0x457902, 0x457f3c}
check("D5 0x44e110 调用方 = 9 处全枚举", xref == EXP9,
      f"{sorted(hex(x) for x in xref)}")
# D6 0x44e540 调用方 21 处 + 品茶锚 0x442e2c
x6 = set()
for i in _md.disasm(MEM, BASE):
    try:
        if i.mnemonic == 'call' and i.op_str == '0x44e540':
            x6.add(i.address)
    except Exception:
        continue
check("D6 0x44e540 调用方 = 21 处（含品茶站 0x442e2c）",
      len(x6) == 21 and 0x442e2c in x6, str(len(x6)))

# =====================================================================
print("== E. 设施身份锚（msg 锚 + 区间包含） ==")
# E1 招呼 msg 立即数锚（push imm32 站址直读）
def msg_at_push(va):
    return struct.unpack_from('<I', MEM, va - BASE)[0]

check("E1a 商家 msg 481(0x1e1) @0x4577b5", at(0x4577b5, 5).hex() == '68e1010000')
check("E1b 锻冶 msg 585(0x249) @0x4461a0", at(0x4461a0, 5).hex() == '6849020000')
check("E1c 寺 msg 4829(0x12dd) @0x45ae58", at(0x45ae58, 5).hex() == '68dd120000')
check("E1d 忍里 msg 2671(0xa6f) @0x4517e0", at(0x4517e0, 5).hex() == '686f0a0000')
check("E1e 公家 msg 4923(0x133b) @0x44a174", at(0x44a174, 5).hex() == '683b130000')
# E2 已知宿主函数落点在对应槽 handler 区间（地址序弱证据，明示于注释）
ranges = {
    '商家(slot0)': (0x457760, 0x45a800, [0x458e20, 0x4577a2]),  # 学做生意 f2/初访置1
    '茶人(slot1)': (0x441d10, 0x444280, [0x442a80]),      # 品茶 f9
    '锻冶(slot2)': (0x446020, 0x4476b0, [0x447110]),      # 铁炮打工 f6
    '道场(slot5)': (0x4476b0, 0x449e90, [0x448990]),      # 试合 f3
    '公家(slot6)': (0x449e90, 0x44b5e0, [0x44a76a, 0x44aabe]),  # 好感站
    '寺(slot8)':   (0x45a800, 0xFFFFFFFF, [0x45ade0]),    # 30日修行 f8
    '忍里(slot9)': (0x451560, 0x457760, [0x451f90]),      # 修业 leaf f4
}
for name, (lo, hi, hosts) in ranges.items():
    for h in hosts:
        check(f"E2 {name} 含 0x{h:06x}", lo <= h < hi)
# E3 闇商人 #29 不在入店表：slot 索引 29 = 0x0c → 跳表第 13 项 = 出店 0x44e7d2
check("E3 slot[29]=0x0c → 跳表[12]=0x44e7d2（非设施 handler）",
      at(0x44e81c + 29, 1) == b'\x0c' and dword(0x44e7e8 + 12 * 4) == 0x44e7d2)

# =====================================================================
print()
print(f"结果: {PASS} PASS / {FAIL} FAIL  (共 {PASS + FAIL})")
sys.exit(1 if FAIL else 0)
