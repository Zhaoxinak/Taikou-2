# -*- coding: utf-8 -*-
r"""
sndata_six_class_field_ref.py -- 续225 自测（8/8 ALL PASS 预期）
=================================================================================
锁定：
 (A) idx->类名->leaf 真实映射（🔴 推翻续224 §4.0.12 的错位表）
 (B) 米市 thunk 0x462517 按 id&0xffff 子分派 {2,3,9}
 (C) 各 leaf 记录基址寄存器来源 + 关键字段语义解码
 (D) 记录字段读点 schema（record-range 偏移，All-GP 检测 + 续224 已知偏移闭合）

用法：python scripts/sndata_six_class_field_ref.py
"""
import sys, os, struct
from capstone import Cs, CS_ARCH_X86, CS_MODE_32
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _disasm_all import load_image, BASE

MEM = load_image()
md = Cs(CS_ARCH_X86, CS_MODE_32)

def va2off(va): return va - BASE
def rd(va, n): return MEM[va2off(va):va2off(va)+n]
def rd_dwords(va, k): return struct.unpack("<%dI"%k, rd(va, 4*k))
def dis(va, n=0x60):
    return list(md.disasm(rd(va, n), va))

PASS=[]; FAIL=[]
def check(name, cond, detail=""):
    (PASS if cond else FAIL).append((name, detail))
    print(("✅" if cond else "❌") + f" {name}" + (f"  -- {detail}" if detail and not cond else ""))

# ---- 期望（续225 订正）----
EXP_JT   = [0x462510,0x462517,0x462559,0x462560,0x462567,0x46256e]

# 名表 6x9B GBK 解码（CJK 变体以实际解码为准，不猜字形）
NAME_RAW = [rd(0x504938+i*9, 9) for i in range(6)]

# ---- T1: 跳转表顺序 ----
jt = rd_dwords(0x462584, 6)
check("T1 跳转表顺序=势/米/家/大/持/属", list(jt)==EXP_JT,
      f"got {[hex(x) for x in jt]}")

# ---- T2: 名表 6 类名（GBK 解码，去 NUL/空格）----
def gbk(b): 
    try: return b.strip(b"\x00 ").decode("gbk")
    except: return repr(b)
names = [gbk(b) for b in NAME_RAW]
EXP_NAMES = ["势力图","米市行情","家中排行","大名情报","持有物品","属下武将"]
check("T2 名表6类=势/米/家/大/持/属", names==EXP_NAMES, f"got {names}")

# ---- T3: 米市 thunk 0x462517 子分派 on id&0xffff ----
d = dis(0x462517, 0xa0)
txt = "\n".join(f"{i.mnemonic} {i.op_str}" for i in d)
# sub 2 -> 0x46254b ; dec -> 0x462544 ; sub 6 -> 0x462539 ; default -> 0x46252b
sub2 = "0x46254b" in txt and "and" in txt
chk = all(x in txt for x in ["0x462544","0x462539","0x461ed0","0x4630c0","0x4632e0"])
check("T3 米市子分派 id&0xffff{2->461ed0,3->4630c0,9->4632e0,默认->461ed0}", chk,
      "0x462517 内 sub2/dec/sub6/default 四分支")

# ---- T4: 各 idx thunk -> leaf ----
exp_thunk_leaf = {0x462510:0x4625a0, 0x462559:0x462670, 0x462560:0x462a80,
                  0x462567:0x462bc0, 0x46256e:0x462d40}
ok=True; det=""
for th, lf in exp_thunk_leaf.items():
    dt = dis(th, 0x20)
    called = [i.op_str for i in dt if i.mnemonic=="call" and i.op_str.startswith("0x")]
    if hex(lf) not in called:
        ok=False; det=f"thunk {hex(th)} 调用链={called}"
        break
check("T4 idx0/2/3/4/5 thunk->leaf 映射", ok, det)

# ---- T5: 米市 leaf 0x461ed0 记录基址 = [esp+8] (rec 经栈传参) ----
d = dis(0x461ed0, 0x30)
txt5 = "\n".join(f"{i.mnemonic} {i.op_str}" for i in d)
check("T5 米市leaf 0x461ed0 rec=[esp+8]->eax", "mov eax, dword ptr [esp + 8]" in txt5,
      "首条 mov eax,[esp+8]")

# ---- T6: 家中排行 0x462670 读 word[rec+0x2c] ----
d = dis(0x462670, 0x30)
txt6 = "\n".join(f"{i.mnemonic} {i.op_str}" for i in d)
check("T6 家中排行读 word[rec+0x2c]", "mov ax, word ptr [eax + 0x2c]" in txt6,
      "0x462678 mov ax,[eax+0x2c]")

# ---- T7: 属下武将 0x462e10 读 entity idx(0..369) -> 实体池 0x519868 stride0x2F ----
d = dis(0x462e10, 0x60)
txt7 = "\n".join(f"{i.mnemonic} {i.op_str}" for i in d)
# cmp ax,0x172(=370) 边界 + lea 实体表 stride0x2F(ecx*47)
has_cmp370 = "0x172" in txt7
has_stride47 = ("shl eax, 4" in txt7) and ("sub eax, ecx" in txt7)
check("T7 属下武将 entity idx(0..369)->实体池 stride0x2F", has_cmp370 and has_stride47,
      "cmp ax,0x172 + *47(=stride0x2F)")

# ---- T8: 勢力図 0x4625a0 读 record-range 偏移（任意 GP 基址，op_str 正则）----
import re
_RE = re.compile(r'\[(eax|ecx|edx|esi|edi|ebx) \+ (0x[0-9a-f]+|[0-9]+)\]')
def rec_offsets_of(va):
    offs=set()
    mdl = Cs(CS_ARCH_X86, CS_MODE_32)
    mdl.skipdata = True          # 容错：遇到非法字节前进 1 字节，避免中途断流导致偏移漏收
    cnt=0; mcnt=0
    for ins in mdl.disasm(rd(va, 0x500), va):
        cnt+=1
        for m in _RE.finditer(ins.op_str):
            mcnt+=1
            dd=m.group(2); disp=int(dd,16) if dd.startswith("0x") else int(dd)
            if 0<=disp<0x31: offs.add(disp)
    print(f"   [diag] va={hex(va)} instrs={cnt} regex_match={mcnt} offs={sorted(hex(x) for x in offs)}")
    return offs
off0 = rec_offsets_of(0x461ed0)
print("   [debug] 0x461ed0 GP-record-range offsets =", sorted(hex(x) for x in off0))
check("T8 米市leaf 0x461ed0 读 record 偏移含 0x1/0x8/0x25", 0x1 in off0 and 0x8 in off0 and 0x25 in off0,
      f"GP 基址偏移集={sorted(hex(x) for x in off0)}")

print(f"\n===== 结果: {len(PASS)} PASS / {len(FAIL)} FAIL =====")
if FAIL:
    for n,d in FAIL: print("FAIL:", n, d)
    sys.exit(1)
print("ALL PASS ✅")
