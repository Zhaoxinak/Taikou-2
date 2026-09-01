"""全镜像扫描：是否存在「mov ecx,0x516610」后（同函数内、无其它 ecx 赋值打断）调用 0x49b970/990/9b0 的路径。
用指令 pickle 直接遍历，按函数分组。"""
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

# 按函数分组：从每个 start 线性反汇编到 ret
def disasm_from(foff, maxlen=0x800):
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

TARGETS = {'0x49b970', '0x49b990', '0x49b9b0'}
hits = []
for fn in STARTS:
    insns = disasm_from(fn)
    # 找 ecx=0x516610 位置，之后若遇 call 0x49b97x/9b0 且无 ecx 重赋值 -> 命中
    ecx_is_s6 = False
    for off, t in insns:
        if t == 'mov ecx, 0x516610':
            ecx_is_s6 = True
            continue
        if t.startswith('mov ecx,') or t.startswith('lea ecx,') or t.startswith('add ecx,') or t.startswith('sub ecx,'):
            ecx_is_s6 = False
            continue
        if t.startswith('call ') and t[5:] in TARGETS and ecx_is_s6:
            hits.append((BASE+fn, BASE+off, t))
            continue

print(f"全镜像扫描命中: {len(hits)} 处")
for fn, va, t in hits:
    print(f"  fn 0x{fn:06x}  call @0x{va:06x}  {t}")
if not hits:
    print("  => S6 的 +0x16/18/1a 在整个静态镜像中不存在 ecx=0x516610 的写入路径。")
