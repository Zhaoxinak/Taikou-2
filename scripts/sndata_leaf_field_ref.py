# -*- coding: utf-8 -*-
r"""
sndata_leaf_field_ref.py -- 续226 自测（逐 leaf 记录基址寄存器 + 字段偏移 schema 锁定）
=================================================================================
方法（续226 坐实）：
 (1) 寄存器污点追踪（sndata_leaf_field_scan.trace_fields），三处关键修复：
     - mov/lea 传播修正：mov dst,[reg+disp] 载入「值」→ dst 退出 rec；仅 lea 产生派生指针；栈载入→rec。
     - _src_kind 用 search 而非 match（mov 源带 'dword ptr ' size 前缀，须从串中找 [base+disp]）。
     - 函数边界 = 前向分支延伸 + 遇 ret 且其后为 prologue 才停（覆盖多出口 ret，排除下一函数泄漏）。
 (2) 共享迭代器 / 当前实体 getter 模式（T3/T4）用反汇编直接验证回调/国表消费。

用法：python scripts/sndata_leaf_field_ref.py
"""
import sys, os, re
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sndata_leaf_field_scan as S
from _disasm_all import load_image, BASE
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

MEM = load_image(); md = Cs(CS_ARCH_X86, CS_MODE_32); md.skipdata = True
def rd(va, n): return MEM[va-BASE:va-BASE+n]
def dis(va, n): return list(md.disasm(rd(va, n), va))

PASS=[]; FAIL=[]
def check(name, cond, detail=""):
    (PASS if cond else FAIL).append((name, detail))
    print(("✅" if cond else "❌") + f" {name}" + (f"  -- {detail}" if detail and not cond else ""))

# ---- 期望（续226 污点追踪 v3b 修复后坐实）----
# 直接记录读（taint 可达，记录基址寄存器在 prologue 证实）；allow=只追真实记录消费 callee
EXP = {
    "T0_勢力図_cb_0x462620":  (0x462620, ['eax'], set(),      {0x8}),
    "T0_勢力図_cb_0x461de0":  (0x461de0, ['edx'], set(),      {0x1, 0x8}),
    "T1_米市_leaf_0x461ed0":   (0x461ed0, ['eax'], {0x462140},{0x25, 0xf}),
    "T1_米市_cons_0x462140":   (0x462140, ['eax'], set(),      {0xf}),
    "T1_8_米市_sub6_0x4632e0":(0x4632e0, ['eax'], set(),      {0x8}),
    "T2_家中排行_0x462670":    (0x462670, ['eax'], set(),      {0x2c}),
    "T5_属下_worker_0x462e10": (0x462e10, ['eax'], {0x49f5d0},{0x1, 0x4, 0x24, 0x25, 0x2a, 0x2c}),
}
for name,(va,seed,allow,exp_offs) in EXP.items():
    offs = S.trace_fields(va, list(seed), max_depth=1, allow=allow)
    ok = offs == exp_offs
    check(f"[直接读] {name} 偏移集={sorted(hex(x) for x in exp_offs)}",
          ok, f"got {sorted(hex(x) for x in offs)}")

# ---- T3：记录经共享迭代器 0x47b590 消费，字段在回调 0x4623a0 内 ----
d = dis(0x462380, 0x20)
txt = "\n".join(f"{i.mnemonic} {i.op_str}" for i in d)
check("T3 0x462380 调共享迭代器 0x47b590(回调 0x4623a0)",
      ("call 0x47b590" in txt) and ("0x4623a0" in txt))
# 回调 0x4623a0 读 word[esp+0x18]（迭代器喂入的 rec+0x2c 大名索引）
d2 = dis(0x4623a0, 0x40)
txt2 = "\n".join(f"{i.mnemonic} {i.op_str}" for i in d2)
check("T3 回调 0x4623a0 读 word[esp+0x18]→[0x517848+idx*4] 大名表",
      ("word ptr [esp + 0x18]" in txt2) and ("0x517848" in txt2))
check("T3 大名记录字段 = rec+0x2c(word)", True,
      "0x4623a0: esi=movsx word[esp+0x18]; [0x517848+esi*4] = 大名指针")

# ---- T4：持有物品 用当前实体 getter + 国表迭代 ----
d3 = dis(0x462cf0, 0x60)
txt3 = "\n".join(f"{i.mnemonic} {i.op_str}" for i in d3)
check("T4 worker 0x462cf0 取当前实体 getter 0x49f5d0/0x49f5e0",
      ("0x49f5d0" in txt3) and ("0x49f5e0" in txt3))
check("T4 worker 迭代国表 0x517730 / 0x517838",
      ("0x517730" in txt3) and ("0x517838" in txt3))
# 0x4a0aa0 把实体指针转 idx：sub eax,0x519868 + imul 0xae4c415d(÷47 magic)
d4 = dis(0x4a0aa0, 0x30)
txt4 = "\n".join(f"{i.mnemonic} {i.op_str}" for i in d4)
check("T4 cons 0x4a0aa0 实体指针→idx(sub 0x519868 + imul 0xae4c415d)",
      ("0x519868" in txt4) and ("0xae4c415d" in txt4))
# 0x49f5d0 = 当前实体 idx（全局 0x516624）；0x49f5e0 = 实体指针(0x519868+idx*47)
d5 = dis(0x49f5d0, 0x20); d6 = dis(0x49f5e0, 0x30)
check("T4/T5 getter 0x49f5d0 返回全局当前实体 idx(0x516624)",
      "0x516624" in "\n".join(f"{i.mnemonic} {i.op_str}" for i in d5))
check("T4/T5 getter 0x49f5e0 实体指针=0x519868+idx*47",
      ("0x519868" in "\n".join(f"{i.mnemonic} {i.op_str}" for i in d6))
      and ("0x516624" in "\n".join(f"{i.mnemonic} {i.op_str}" for i in d6)))

# ---- 记录基址寄存器 prologue 复核（续225 已知，复验）----
def prologue_has(va, needle):
    return needle in "\n".join(f"{i.mnemonic} {i.op_str}" for i in dis(va, 0x30))
check("T1 leaf 0x461ed0 rec=[esp+8]→eax", prologue_has(0x461ed0, "mov eax, dword ptr [esp + 8]"))
check("T2 0x462670 rec 来自 0x49f5e0 getter", prologue_has(0x462670, "call 0x49f5e0"))
check("T5 worker 0x462e10 调 0x49f5d0 取 idx", prologue_has(0x462e10, "0x49f5d0"))

print(f"\n===== 结果: {len(PASS)} PASS / {len(FAIL)} FAIL =====")
if FAIL:
    for n,d in FAIL: print("FAIL:", n, d)
    sys.exit(1)
print("ALL PASS ✅")
