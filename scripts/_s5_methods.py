"""(A) 完整方法表 0x49b960..0x49bda8：每个函数写的 [ecx+disp] + 钳制常量
(B) 全镜像扫描：所有 ecx=0x5197b0(S5) 后调用的方法（并含 lea ecx,[0x5197b0+..] 变体）
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
from collections import defaultdict, Counter
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

BASE = 0x400000
IMG = open(_ROOT + '/scripts/_unpacked_mem.bin', 'rb').read()
d, starts = pickle.load(open(_ROOT + '/scripts/_insn_addrs.pkl', 'rb'))
SIZE = {off: s[0] for off, s in d.items()}
TEXT = {off: s[1] for off, s in d.items()}
md = Cs(CS_ARCH_X86, CS_MODE_32); md.detail = False

MT_LO, MT_HI = 0x49b960, 0x49bdb0
STARTS = sorted(starts)

def disasm_func_off(foff, maxlen=0x800):
    out = []; o = foff; end = foff + maxlen
    while o < end and o in SIZE:
        out.append((o, TEXT[o]))
        if TEXT[o] == 'ret': break
        o += SIZE[o]
    return out

print("=" * 72)
print("(A) 完整方法表 0x49b960..0x49bda8")
print("=" * 72)
# 方法表函数起点：从 starts 取落在区间内的
mt_funcs = [s for s in STARTS if MT_LO - BASE <= s < MT_HI - BASE]
methods = {}
for fo in sorted(mt_funcs):
    insns = disasm_func_off(fo)
    if not insns: continue
    va = BASE + fo
    disps = set(); clamps = set(); code = []
    for off, t in insns:
        code.append(t)
        if 'ptr [ecx + 0x' in t or 'ptr [ecx+0x' in t:
            seg = t.split('ptr [ecx + ')[-1] if 'ptr [ecx + ' in t else t.split('ptr [ecx+')[-1]
            try: disps.add(int(seg.split(']')[0], 16))
            except: pass
        for tok in t.replace(',', ' ').split():
            if tok.startswith('0x') and len(tok) > 4:
                try: clamps.add(int(tok, 16))
                except: pass
    # 只保留像钳制/掩码的常量（排除地址型）
    clamps = {c for c in clamps if c < 0x10000}
    methods[va] = (sorted(disps), sorted(clamps), code)
    print(f"0x{va:06x}  disp={[hex(x) for x in sorted(disps)]}  consts={[hex(x) for x in sorted(clamps)]}")
    print(f"          {' | '.join(code[:8])}")

print()
print("=" * 72)
print("(B) ecx=0x5197b0 (S5) 后调用的方法 —— 全镜像扫描")
print("=" * 72)
MT_SET = {hex(BASE + fo) for fo in mt_funcs}
hits = []
for fn in STARTS:
    insns = disasm_func_off(fn)
    ecx_is_s5 = False
    for off, t in insns:
        if t in ('mov ecx, 0x5197b0', 'mov ecx, 0x5197b0') or t.startswith('lea ecx, [0x5197b0') or t.startswith('lea ecx, [ecx + 0x5197b0'):
            ecx_is_s5 = True; continue
        if t.startswith('mov ecx,') or t.startswith('lea ecx,') or t.startswith('add ecx,') or t.startswith('sub ecx,'):
            ecx_is_s5 = False; continue
        if t.startswith('call 0x') and ecx_is_s5:
            tgt = t[5:]
            if tgt in MT_SET:
                hits.append((BASE + fn, BASE + off, tgt))
print(f"命中 {len(hits)} 处")
agg = Counter((fn, tgt) for fn, _, tgt in hits)
for (fn, tgt), n in sorted(agg.items()):
    disp = methods.get(int(tgt, 16), (None,))[0]
    print(f"  fn 0x{fn:06x}  -> 方法 {tgt} (disp={[hex(x) for x in disp] if disp else '?'})   ×{n}")
