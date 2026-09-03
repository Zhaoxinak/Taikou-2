# -*- coding: utf-8 -*-
r"""
sndata_leaf_field_scan.py -- 续226 探针 v3：6 类 leaf 的 record 字段读点（寄存器污点追踪 + 覆盖消除）
=================================================================================
v2 仍噪声：只「添加」不「删除」记录寄存器 —— callee 复用 eax/ecx 装其它数据时被误判为记录指针；
且 lea 大常量跨越到相邻结构。

v3 改进：
 - 覆盖消除：mov/lea/xor/and/arith 重定义某 reg 时，按源判定其是否仍是记录指针（否则移出 rec/derived）。
 - [esp/ebp+imm] 读 = 从栈帧载入记录指针 → dst 入 rec（thiscall 传参 / 栈取 rec）。
 - lea 派生指针常量 >= 0x31 视为跨结构，丢弃；收集时仅 (c+disp)<0x31 才算记录字段。
 - 自动定 seed：函数体内对各 GP 的 [reg+off](off<0x31) 读计数，取最多者作记录基址。
 - callee 以调用点父函数的 rec_regs 为种子（调用约定传参），深度=1。

用法：python scripts/sndata_leaf_field_scan.py
"""
import sys, os, re
from capstone import Cs, CS_ARCH_X86, CS_MODE_32
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _disasm_all import load_image, BASE

MEM = load_image()
GP = ['eax','ecx','edx','esi','edi','ebx']
_RE_GP = re.compile(r'\[(' + '|'.join(GP) + r') \+ (0x[0-9a-f]+|[0-9]+)\]')
_RE_GP_ANY = re.compile(r'\[((?:eax|ecx|edx|esi|edi|ebx|esp|ebp))(?:\s*\+\s*(0x[0-9a-f]+|[0-9]+))?\]')
_LEA = re.compile(r'^(' + '|'.join(GP) + r')(?:\s*\+\s*(0x[0-9a-f]+|[0-9]+))?$')

def va2off(va): return va - BASE
def rd(va, n): return MEM[va2off(va):va2off(va)+n]
def disasm(va, n):
    md = Cs(CS_ARCH_X86, CS_MODE_32); md.skipdata = True
    return list(md.disasm(rd(va, n), va))

_BRANCH = ('jmp','ja','jae','jb','jbe','je','jne','jg','jge','jl','jle',
           'jo','jno','js','jns','jp','jnp','jcxz','jecxz','loop','loope','loopne')
def _imm(s): return int(s,16) if s.lower().startswith("0x") else int(s)
def _is_prologue(ins):
    """判断一条指令是否像新函数的 prologue 起点（用于函数边界判定）。"""
    if ins is None: return True
    m = ins.mnemonic
    if m in ('ret','retn','retf','nop','int3'): return True
    if m == 'sub' and ins.op_str.startswith('esp'): return True
    if m == 'push': return True
    if m == 'mov' and 'ebp' in ins.op_str and 'esp' in ins.op_str: return True
    return False

def disasm_func(va, win=0x800):
    """界定本函数体：
    - 仅按 jmp/jcc 前向分支延伸 maxaddr（call 不延伸，避免把被调子函数的读泄漏进来）。
    - 遇 ret 时：若其后紧邻指令是「新函数 prologue」（sub esp / push / mov ebp,esp / nop / ret）则停（函数结束）；
      否则视为同函数的多出口 ret，继续（覆盖 si<100 / si>=100 等多分支各自读的字段）。
    - 越过 maxaddr+0x10 亦停（防泄漏下一函数）。
    """
    insns = disasm(va, win)
    maxaddr = va + 0x200
    extended = False
    keep = []
    for idx, ins in enumerate(insns):
        if ins.address > maxaddr + 0x10:
            break
        keep.append(ins)
        if ins.mnemonic in ('ret','retn','retf'):
            nxt = insns[idx+1] if idx+1 < len(insns) else None
            if not extended or ins.address > maxaddr or _is_prologue(nxt):
                break
        if ins.mnemonic in _BRANCH and ins.op_str.startswith('0x'):
            t = _imm(ins.op_str)
            if t >= va:
                maxaddr = max(maxaddr, t); extended = True
    return keep

def _split2(os_):
    p = os_.split(',', 1)
    return (p[0].strip(), p[1].strip()) if len(p)==2 else None

def _src_kind(src, rec, derived):
    """src 操作数性质（供 mov/lea 区分「载入值」与「派生指针」）：
    'stack' = [esp/ebp+disp]（栈帧载入记录指针）；
    'mem'   = [gp+disp]（非栈内存载入，是字段「值」）；
    'reg'   = 纯 GP 寄存器（裸名）；
    'none'  = 立即数/其它。
    注：用 search 而非 match（mov 源带 'dword ptr ' 之类 size 前缀，须从串中找出 [base+disp]）。
    """
    m = _RE_GP_ANY.search(src)
    if m:
        base = m.group(1)
        if base in ('esp','ebp'): return 'stack'
        return 'mem'
    s = src.strip()
    s = re.sub(r'^(byte|word|dword) ptr\s*', '', s).strip()
    if s in rec or s in derived: return 'reg'
    return 'none'

def trace_fields(va, seed=None, win=0x400, depth=0, max_depth=1, allow=None):
    insns = disasm_func(va, win)
    if seed is None:
        cnt = {r:0 for r in GP}
        for ins in insns:
            for m in _RE_GP.finditer(ins.op_str):
                if _imm(m.group(2)) < 0x31: cnt[m.group(1)] += 1
        best = max(cnt, key=cnt.get)
        seed = [best] if cnt[best] > 0 else ['eax']
    rec = set(seed); derived = {}
    stack = {}; vsp = 0
    offs = set(); calls = []
    for ins in insns:
        mn, os_ = ins.mnemonic, ins.op_str
        # --- 收集读点 ---
        for m in _RE_GP.finditer(os_):
            reg, disp = m.group(1), _imm(m.group(2))
            if 0 <= disp < 0x31:
                if reg in rec: offs.add(disp)
                elif reg in derived:
                    c = derived[reg][1]
                    if 0 <= c + disp < 0x31: offs.add(c + disp)
        # --- 传播 ---
        if mn in ('mov','movzx','movsx'):
            p = _split2(os_)
            if p:
                dst, src = p
                if dst in ('esp','ebp'): continue
                k = _src_kind(src, rec, derived)
                if k == 'stack':
                    # 从栈帧载入记录指针 → dst 是记录指针
                    rec.add(dst); derived.pop(dst, None)
                elif k == 'mem':
                    # 内存载入 = 字段「值」（无论基址是否在 rec，dst 都不再是记录指针）
                    rec.discard(dst); derived.pop(dst, None)
                elif k == 'reg':
                    s = src.strip()
                    if s in rec: rec.add(dst); derived.pop(dst, None)
                    elif s in derived: derived[dst] = derived[s]; rec.discard(dst)
                    else: rec.discard(dst); derived.pop(dst, None)
                else:
                    rec.discard(dst); derived.pop(dst, None)
        elif mn == 'lea':
            p = _split2(os_)
            if p:
                dst, src = p
                if dst in ('esp','ebp'): continue
                m = _LEA.match(src.strip())
                if m:
                    base = m.group(1); const = _imm(m.group(2)) if m.group(2) else 0
                    if const >= 0x31:          # 跨结构，丢弃派生
                        rec.discard(dst); derived.pop(dst, None)
                    elif base in rec: derived[dst] = (base, 0); rec.discard(dst)
                    elif base in derived: derived[dst] = (derived[base][0], derived[base][1] + const); rec.discard(dst)
                    else: rec.discard(dst); derived.pop(dst, None)
                else:
                    rec.discard(dst); derived.pop(dst, None)
        elif mn == 'push':
            vsp -= 4
            stack[vsp] = (os_ in rec) or (os_ in derived)
        elif mn == 'pop':
            if os_ in ('esp','ebp'): vsp += 4; continue
            if vsp in stack and stack[vsp]: rec.add(os_)
            else: rec.discard(os_); derived.pop(os_, None)
            vsp += 4
        elif mn in ('xor','and','or','imul','mul','div','idiv','neg','shl','shr','sar','sub','add'):
            p = _split2(os_)
            if p:
                dst = p[0]
                if dst in rec or dst in derived:
                    if mn in ('add','sub') and len(p)==2 and re.match(r'^-?0x?[0-9a-f]+$', p[1], re.I):
                        imm = _imm(p[1]); c = imm if mn=='add' else -imm
                        derived[dst] = (dst, c)   # 指针算术 → 派生
                    else:
                        rec.discard(dst); derived.pop(dst, None)
        elif mn in ('call','jmp') and os_.startswith('0x'):
            tgt = _imm(os_)
            if BASE <= tgt < BASE + len(MEM):
                calls.append((tgt, set(rec), dict(derived)))
            if mn == 'call': rec.add('eax')   # getter 常经 eax 返回记录指针
    if depth < max_depth:
        for cv, cr, cd in calls:
            if allow is not None and cv not in allow:
                continue   # 只追「真正的记录消费 callee」，排除 getter/共享基础设施
            offs |= trace_fields(cv, list(set(cr) | {b for b,_ in cd.values()}),
                                 win=0x300, depth=depth+1, max_depth=max_depth, allow=allow)
    return offs

def _breg(src):
    m = _RE_GP_ANY.match(src.strip())
    return m.group(1) if m else src

LEAVES = [
    ("T0_勢力図",  0x4625a0),
    ("T1_米市",    0x461ed0),
    ("T1_8_米市",  0x4632e0),
    ("T2_家中",    0x462670),
    ("T3_大名",    0x462a80),
    ("T4_持有_a",  0x462bc0),
    ("T4_持有_b",  0x462cf0),
    ("T5_属下",    0x462e10),
]

if __name__ == "__main__":
    # 续226 校验驱动：每个 leaf/consumer 用手动确定的 rec 基址寄存器 + 只追「真正的记录消费 callee」
    # （排除 getter 0x49f5e0/0x49f670/0x49f5d0 与共享基础设施，它们内部碰的是自己的结构而非记录）
    CURATED = [
        # (标签, va, seed寄存器, 允许递归的 callee)
        ("T0_cb_0x462620",   0x462620, ['eax'], set()),        # mov eax,[esp+8]=rec
        ("T0_cb_0x461de0",   0x461de0, ['edx'], set()),        # mov edx,[esp+0x14]=rec
        ("T1_leaf_0x461ed0", 0x461ed0, ['eax'], {0x462140}),   # 消费 callee 0x462140
        ("T1_cons_0x462140", 0x462140, ['eax'], set()),        # byte[rec+0xf]
        ("T1_8_0x4632e0",    0x4632e0, ['eax'], set()),        # word[rec+8]
        ("T2_0x462670",      0x462670, ['eax'], set()),        # word[rec+0x2c]
        ("T3_cons_0x462380", 0x462380, ['eax'], set()),        # rec=edi→[esp+4]; 转发给共享迭代器 0x47b590（记录字段在共享器内，不入表）
        ("T4_worker_0x462cf0",0x462cf0,['eax'], {0x4a0aa0}),   # rec=eax(getter); 消费 callee 0x4a0aa0
        ("T4_cons_0x4a0aa0", 0x4a0aa0, ['eax'], set()),
        ("T5_leaf_0x462e10", 0x462e10, ['eax'], {0x49f5d0}),   # rec=eax(getter); 取 entity idx 的 callee 0x49f5d0
        ("T5_getidx_0x49f5d0",0x49f5d0, ['eax'], set()),
    ]
    print("=== SNDATA 6 类 leaf 字段读点扫描（续226 污点追踪 v3b · 手动 seed + 白名单 callee）===")
    for name, va, seed, allow in CURATED:
        offs = trace_fields(va, list(seed), depth=0, max_depth=1, allow=allow)
        print(f"{name:18s} seed={seed}  offs={sorted(hex(x) for x in offs)}")

