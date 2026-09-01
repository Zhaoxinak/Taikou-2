"""对 0x49b970/990/9b0 三个 setter 的全部 call 站点，做【寄存器感知】的 ecx 溯源：
- 向前扫描到函数边界（最近 ret/call 外部 或 函数起点）
- 追踪 ecx：mov ecx,0x516610(直接) / mov ecx,reg 且 reg 最近被赋 0x516610(一级跳转) / mov ecx,[mem] 等
- 报告每个调用点 ecx 是否 = 0x516610（即真写 S6）
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
SIZE = {off: s[0] for off, s in d.items()}
TEXT = {off: s[1] for off, s in d.items()}
STARTS = sorted(starts)
md = Cs(CS_ARCH_X86, CS_MODE_32); md.detail = False

SETTERS = {0x49b970: '+0x16', 0x49b990: '+0x18', 0x49b9b0: '+0x1a'}

def func_off_of(off):
    best = None
    for s in STARTS:
        if s <= off:
            if best is None or s > best: best = s
        else: break
    return best if best is not None else off

def disasm_func_off(foff, maxlen=0x600):
    out = []
    o = foff
    end = foff + maxlen
    while o < end and o in SIZE:
        sz = SIZE[o]
        out.append((o, TEXT[o]))
        if TEXT[o] == 'ret':
            break
        o += sz
    return out

def trace_ecx_is_s6(insns, call_idx):
    """insns: list of (off,text) from function start. call_idx = index of the call.
    返回 (is_s6:bool, chain:list[str])。"""
    chain = []
    # 当前 ecx 已知常量
    ecx_const = None
    ecx_reg = None
    # 寄存器最近赋值（常量）
    reg_const = {}
    for i in range(call_idx - 1, -1, -1):
        off, t = insns[i]
        # 函数边界保护：遇到 call（非我们要的）或 ret 也停止（应不会发生，因为 function 内）
        if t.startswith('mov ecx, '):
            arg = t[len('mov ecx, '):]
            if arg == '0x516610':
                return (True, chain[::-1] + [f'0x{BASE+off:06x} {t}'])
            if arg.startswith('0x') and 'ptr' not in arg:
                # mov ecx, 0xYYYYYY
                return (False, chain[::-1] + [f'0x{BASE+off:06x} {t} (ecx=其他常量)'])
            if arg in reg_const:
                if reg_const[arg] == 0x516610:
                    return (True, chain[::-1] + [f'0x{BASE+off:06x} {t} (reg {arg}=0x516610)'])
                else:
                    return (False, chain[::-1] + [f'0x{BASE+off:06x} {t} (reg {arg}={reg_const[arg]:#x})'])
            # ecx = reg（未知）-> 标记为不确定但按非S6保守
            chain.append(f'0x{BASE+off:06x} {t} (ecx=reg {arg}, 来源未定)')
            return (False, chain[::-1])
        if t.startswith('lea ecx, '):
            return (False, chain[::-1] + [f'0x{BASE+off:06x} {t}'])
        if t.startswith('mov e') and ', ' in t:
            dst, src = t[4:].split(',', 1) if t.startswith('mov ') else (None, None)
            # 记录 reg = const
            if t.startswith('mov ') and dst in ('eax', 'ebx', 'ecx', 'edx', 'esi', 'edi', 'ebp'):
                a = src.strip()
                if a.startswith('0x') and 'ptr' not in a:
                    reg_const[dst] = int(a, 16)
                elif a.startswith('dword ptr') or a.startswith('word ptr') or a.startswith('byte ptr'):
                    reg_const[dst] = None  # 内存来源，未知
                # else 寄存器间传递，保留之前的 reg_const（近似）
        # 遇到 call 之前已经处理；跳过 call 不影响
    return (False, chain[::-1] + ['<函数起点未找到 ecx 赋值>'])

# 收集 call 站点
calls = {off: [] for off in SETTERS}
for off, s in SIZE.items():
    t = TEXT[off]
    if t.startswith('call 0x'):
        try: tg = int(t[5:], 16)
        except: continue
        if tg in SETTERS:
            calls[tg].append(off)

summary = []
for setter, label in SETTERS.items():
    print(f"\n##### {label} setter 0x{setter:04x} : {len(calls[setter])} call 站点 #####")
    for cs_off in calls[setter]:
        fn = func_off_of(cs_off)
        insns = disasm_func_off(fn)
        # 找 call 在 insns 中的索引
        cidx = None
        for i, (o, t) in enumerate(insns):
            if o == cs_off:
                cidx = i; break
        if cidx is None:
            print(f"  0x{BASE+cs_off:06x}: 不在函数指令序列内")
            continue
        is_s6, chain = trace_ecx_is_s6(insns, cidx)
        verdict = "✅ S6 写入" if is_s6 else "❌ 非S6(写其它struct)"
        print(f"  call @0x{BASE+cs_off:06x} (fn 0x{BASE+fn:06x}): {verdict}")
        for c in chain:
            print(f"      {c}")
        summary.append((label, BASE+cs_off, is_s6))

print("\n===== 汇总 =====")
n_s6 = sum(1 for _, _, s in summary if s)
print(f"S6 真实写入点: {n_s6} / {len(summary)}")
for label, va, s in summary:
    print(f"  {label} @0x{va:06x}: {'S6' if s else 'other'}")
