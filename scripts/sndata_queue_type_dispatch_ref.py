#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""续224 自测：SNDATA 49B 记录「队列抽干端 per-record 处理器」= 顾问咨询六类消费模型。
=====================================================================================
断言链（全部纯静态·capstone 反汇编，推翻续221「215 细类型各自独立消费」假设）：
 T1 抽干端处理器 0x4624f0 读 id 字(偏移0) → call 0x462fd0(type getter) → cmp eax,5 → jmp [eax*4+0x462584]
 T2 跳转表 0x462584 解 6 项 → handler{0x462510,0x462517,0x462559,0x462560,0x462567,0x46256e}（同 fn 0x4624c0）
 T3 type getter 0x462fd0 = pop(0x49f6b0) + 名表 0x504938(6x9B) + 二分 0x47bed0
 T4 名表 0x504938 六类名 = 勢力図/米市行情/家中排行/大名情報/持有物品/属下武将（顾问咨询六类）
 T5 type1 内联子分派 on id&0xffff: 2→0x461ed0 / 3→0x4630c0 / 8→0x4632e0（续221 细类型折叠进粗类）
 T6 各 handler 字段读点：T1默认@1/@2/@3/@8/@0x25；T1_8 word@8；T2 word@0x2c
 T7 入队链 0x462460→call 0x4eefa0 + 0x526c58 + 阈值 0x7f7(2047)→call 0x47ae20(drain)
 T8 0x4624f0 调用链 0x46e260→0x48b5f0→0x48b1d0（callers 唯一，pop 同一 0x526c50 队列）
"""
import struct, pickle, sys
sys.path.insert(0, "scripts")
from capstone import Cs, CS_ARCH_X86, CS_MODE_32
from _disasm_all import load_image

BASE = 0x400000
code = load_image()
pkl = pickle.load(open("scripts/_insn_addrs.pkl", "rb"))
FUNCS_S = sorted(pkl[1])

def fn_start(va):
    fo = va - BASE
    lo, hi = 0, len(FUNCS_S) - 1
    best = None
    while lo <= hi:
        m = (lo + hi) // 2
        if FUNCS_S[m] <= fo:
            best = FUNCS_S[m]; lo = m + 1
        else:
            hi = m - 1
    return (BASE + best) if best is not None else None

def dis(va, n):
    md = Cs(CS_ARCH_X86, CS_MODE_32); md.detail = True
    return list(md.disasm(code[va-BASE:va-BASE+n], va))

def calls_of(tgt):
    out = set(); off = 0
    while True:
        idx = code.find(b'\xe8', off)
        if idx < 0: break
        rel = struct.unpack("<i", code[idx+1:idx+5])[0]
        va = BASE + idx + 5 + rel
        if va == tgt: out.add(BASE + idx)
        off = idx + 1
    return out

results = []
def chk(name, cond, extra=""):
    results.append((name, cond, extra))
    print(("PASS" if cond else "FAIL"), name, extra)

# T1 0x4624f0 分派结构
ins = [(i.mnemonic, i.op_str) for i in dis(0x4624f0, 0x100)]
t1 = any((m == "call" and o == "0x462fd0") for m, o in ins) \
   and any((m == "cmp" and "5" in o) for m, o in ins) \
   and any((m == "jmp" and "0x462584" in o) for m, o in ins)
chk("T1_4624f0_dispatch", t1)

# T2 跳转表 0x462584 六项
raw = code[0x462584-BASE:0x462584-BASE+24]
jt = [struct.unpack("<I", raw[i*4:i*4+4])[0] for i in range(6)]
expected_jt = [0x462510, 0x462517, 0x462559, 0x462560, 0x462567, 0x46256e]
chk("T2_jumptable_6handlers", jt == expected_jt, f"jt={[hex(x) for x in jt]}")

# T3 0x462fd0 = pop + 名表 + 二分
ins3 = [(i.mnemonic, i.op_str) for i in dis(0x462fd0, 0x200)]
t3 = any((m == "call" and o == "0x49f6b0") for m, o in ins3) \
   and any(("0x504938" in o) for m, o in ins3) \
   and any((m == "call" and o == "0x47bed0") for m, o in ins3)
chk("T3_462fd0_resolver", t3)

# T4 名表六类名（用原始 9 字节比对，避免 CJK 归一化问题）
tbl = code[0x504938-BASE:0x504938-BASE+54]
expected_entries = [
    b'\x20\xca\xc6\xc1\xa6\xcd\xbc\x20\x00',  # 勢力図
    b'\xc3\xd7\xca\xd0\xd0\xd0\xc7\xe9\x00',  # 米市行情
    b'\xbc\xd2\xd6\xd0\xc5\xc5\xd0\xd0\x00',  # 家中排行
    b'\xb4\xf3\xc3\xfb\xc7\xe9\xb1\xa8\x00',  # 大名情報
    b'\xb3\xd6\xd3\xd0\xce\xef\xc6\xb7\x00',  # 持有物品
    b'\xca\xf4\xcf\xc2\xce\xe4\xbd\xab\x00',  # 属下武将
]
ok = all(tbl[i*9:i*9+9] == expected_entries[i] for i in range(6))
names = [tbl[i*9:i*9+9].split(b'\x00')[0].decode('gbk', errors='replace') for i in range(6)]
chk("T4_6_category_names", ok, f"names={names}")

# T5 type1 子分派 on id&0xffff
ins5 = [(i.mnemonic, i.op_str, i.address) for i in dis(0x4624f0, 0x100)]
# 找 0x462517 起的内联子分派：and eax,0xffff ; sub eax,2 ; je 0x46254b ; dec ; je 0x462544 ; sub 6 ; je 0x462539
def has_seq(seq):
    # seq: list of (mnemonic-substr, opstr-substr)
    txt = [(m, o) for m, o, _ in ins5]
    return all(any(sm in m and so in o for m, o in txt) for sm, so in seq)
t5 = has_seq([("and", "0xffff"), ("sub", "2"), ("je", "0x46254b"), ("dec", ""), ("je", "0x462544"), ("sub", "6"), ("je", "0x462539")])
# 验证三个 je 目标确实 call 对应 handler
calls_461ed0 = any((m=="call" and o=="0x461ed0") for m,o,_ in ins5)
calls_4630c0 = any((m=="call" and o=="0x4630c0") for m,o,_ in ins5)
calls_4632e0 = any((m=="call" and o=="0x4632e0") for m,o,_ in ins5)
chk("T5_type1_subdispatch", t5 and calls_461ed0 and calls_4630c0 and calls_4632e0,
    f"seq={t5} 461ed0={calls_461ed0} 4630c0={calls_4630c0} 4632e0={calls_4632e0}")

# T6 字段读点（capstone 对 <0x10 的偏移省略 0x 前缀，故用小写精确串）
def reads(va, n, pats):
    ins = [(i.mnemonic, i.op_str) for i in dis(va, n)]
    return all(any(p in o for _, o in ins) for p in pats)
# T1 默认(0x461ed0): byte@[eax+0x25]/[eax+8]/[eax+1]/[edi+2]/[edi+3]
t6a = reads(0x461ed0, 0x200, [
    "byte ptr [eax + 0x25]", "byte ptr [eax + 8]", "byte ptr [eax + 1]",
    "byte ptr [edi + 2]", "byte ptr [edi + 3]"])
# T1_8(0x4632e0): word@[eax+8]
t6b = reads(0x4632e0, 0x80, ["word ptr [eax + 8]"])
# T2(0x462670): word@[eax+0x2c]
t6c = reads(0x462670, 0x200, ["word ptr [eax + 0x2c]"])
chk("T6_field_reads", t6a and t6b and t6c,
    f"T1def(461ed0)@1/2/3/8/0x25={t6a} T1_8(4632e0)word@8={t6b} T2(462670)word@0x2c={t6c}")

# T7 入队链 0x462460
ins7 = [(i.mnemonic, i.op_str) for i in dis(0x462460, 0x60)]
t7 = any((m=="call" and o=="0x4eefa0") for m, o in ins7) \
   and any("0x526c58" in o for m, o in ins7) \
   and any(("0x7f7" in o or "2047" in o) for m, o in ins7) \
   and any((m=="call" and o=="0x47ae20") for m, o in ins7)
chk("T7_enqueue_chain", t7)

# T8 调用链
c_4624f0 = calls_of(0x4624f0)
c_46e260 = calls_of(0x46e260)
c_48b5f0 = calls_of(0x48b5f0)
t8 = (len(c_4624f0)==1 and 0x46e2a5 in c_4624f0) \
   and (len(c_46e260)==1 and 0x48b667 in c_46e260) \
   and (len(c_48b5f0)==1 and 0x48b1d0 and any(fn_start(c)==0x48b1d0 for c in c_48b5f0))
chk("T8_call_chain", t8,
    f"4624f0<-{ [hex(fn_start(c)) for c in c_4624f0] } 46e260<-{[hex(fn_start(c)) for c in c_46e260]} 48b5f0<-{[hex(fn_start(c)) for c in c_48b5f0]}")

npass = sum(1 for _, c, _ in results if c)
print(f"\n===== {npass}/{len(results)} PASS =====")
for n, c, e in results:
    if not c: print("FAILED:", n, e)
raise SystemExit(0 if npass == len(results) else 1)
