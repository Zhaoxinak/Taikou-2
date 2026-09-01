"""追溯 S6 三个 60000 钳制字段的真实写入点。

共享方法库陷阱：setter 0x49b970/0x49b990/0x49b9b0 被很多 struct 复用。
只有 ecx 被显式加载为 0x516610 的调用才是 S6 的写入。
本脚本：
  1. 从指令 pickle 找所有 call 0x49b970/.../0x49b9b0
  2. 定位其所属函数（最近的前驱 starts 入口）
  3. 线性反汇编该函数，确认 ecx 在调用前被设为 0x516610（且中间无其它 ecx 赋值）
  4. 抓 push 的实参来源（指令级），报告上下文
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

import pickle, struct
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

BASE = 0x400000
IMG = open(_ROOT + '/scripts/_unpacked_mem.bin', 'rb').read()
d, starts = pickle.load(open(_ROOT + '/scripts/_insn_addrs.pkl', 'rb'))
INSN = {va: (s[0], s[1]) for va, s in d.items()}  # va(=BASE+off) -> (size, text)
SIZE = {va: s[0] for va, s in INSN.items()}
TEXT = {va: s[1] for va, s in INSN.items()}
STARTS = sorted(starts)

md = Cs(CS_ARCH_X86, CS_MODE_32)
md.detail = False

SETTERS = {0x49b970: '+0x16', 0x49b990: '+0x18', 0x49b9b0: '+0x1a'}

def func_of(va):
    best = None
    for s in STARTS:
        if s <= va:
            if best is None or s > best:
                best = s
        else:
            break
    return best if best is not None else va

def disasm_func(fstart, maxlen=0x500):
    """从 fstart 线性反汇编到 ret/jmp 外部或 maxlen。返回 [(va,text)]。"""
    out = []
    off = fstart - BASE
    end = off + maxlen
    while off < end:
        if off not in SIZE:
            break
        sz, txt = INSN[BASE + off]
        out.append((BASE + off, txt))
        if txt in ('ret', 'retf') or txt.startswith('jmp ') and '0x' in txt:
            # jmp 到外部地址（非短跳）通常结束函数；但保守只遇 ret 停
            if txt == 'ret':
                break
        off += sz
    return out

def find_ecx_chain(insns, callva):
    """在 call 之前找 ecx 设定链。返回 (ecx_is_s6, push_val_insn_text)。"""
    idx = None
    for i, (va, t) in enumerate(insns):
        if va == callva:
            idx = i
            break
    if idx is None:
        return (False, None)
    ecx_set_to_516610 = False
    ecx_clobbered_after = False
    push_instrs = []
    # 从 call 向前扫到函数起点
    for i in range(idx - 1, -1, -1):
        va, t = insns[i]
        if t == 'mov ecx, 0x516610':
            ecx_set_to_516610 = True
            break
        if t.startswith('mov ecx,') or t.startswith('lea ecx,') or t.startswith('add ecx,') or t.startswith('sub ecx,'):
            # ecx 被设成别的东西 -> 不是 S6
            ecx_clobbered_after = True
            break
        if t.startswith('push '):
            push_instrs.append((va, t))
    if not ecx_set_to_516610:
        return (False, None)
    # push_instrs 是倒序；最后一个 push 是最近压入的（即 setter 的 arg）
    # setter 签名：push arg; mov ecx,0x516610; call setter
    return (True, push_instrs[0] if push_instrs else None)

# 收集所有 call 站点
call_sites = {off: [] for off in SETTERS}
for va, (sz, txt) in INSN.items():
    if txt.startswith('call 0x'):
        target = int(txt[5:], 16)
        if target in SETTERS:
            call_sites[target].append(va)

print("=== 各 setter 的 call 站点数 ===")
for off, sites in call_sites.items():
    print(f"{SETTERS[off]} setter 0x{off:04x}: {len(sites)} 个 call 站点")

# 对每个 setter，找 S6 真实写入点
results = {}
for off, sites in call_sites.items():
    s6_writes = []
    for cs in sites:
        fn = func_of(cs)
        insns = disasm_func(fn)
        ok, pushi = find_ecx_chain(insns, cs)
        if ok:
            s6_writes.append((cs, fn, pushi))
    results[off] = s6_writes
    print(f"\n=== {SETTERS[off]} (0x{off:04x}): {len(s6_writes)} 个 S6 真实写入点 ===")
    for cs, fn, pushi in s6_writes:
        print(f"  call @0x{cs:06x}  (fn 0x{fn:06x})  push={pushi}")

# 对发现的 S6 写入点，dump 整个函数上下文（前 0x180 字节）
for off, s6_writes in results.items():
    if not s6_writes:
        continue
    print(f"\n\n########## {SETTERS[off]} 写入函数上下文 ##########")
    seen = set()
    for cs, fn, pushi in s6_writes:
        if fn in seen:
            continue
        seen.add(fn)
        print(f"\n----- fn 0x{fn:06x} (S6 write @0x{cs:06x}) -----")
        for ins in md.disasm(IMG[fn - BASE: fn - BASE + 0x1c0], fn):
            mark = ' <<<S6WRITE' if ins.address == cs else ''
            print(f"  0x{ins.address:06x}  {ins.mnemonic} {ins.op_str}{mark}")
