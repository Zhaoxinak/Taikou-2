"""找 0x49b970/0x49b990/0x49b9b0 的全部 call 站点，dump 其所在函数全文，定位 0x516610 如何流入 ecx。"""
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

calls = {off: [] for off in SETTERS}
for off, s in SIZE.items():
    t = TEXT[off]
    if t.startswith('call 0x'):
        try: tg = int(t[5:], 16)
        except: continue
        if tg in SETTERS:
            calls[tg].append(off)

for setter, label in SETTERS.items():
    sites = calls[setter]
    print(f"\n{'#'*70}\n{label} setter 0x{setter:04x} : {len(sites)} call 站点\n{'#'*70}")
    seen = set()
    for cs_off in sites:
        fn = func_off_of(cs_off)
        if fn in seen:
            continue
        seen.add(fn)
        print(f"\n----- fn @0x{BASE+fn:06x}  (setter call @0x{BASE+cs_off:06x}) -----")
        n = 0
        for ins in md.disasm(IMG[fn: fn + 0x300], BASE + fn):
            mark = ''
            if ins.address == BASE + cs_off: mark = ' <<<CALL'
            if '0x516610' in ins.op_str: mark += ' <<<S6BASE'
            print(f"  0x{ins.address:06x}  {ins.mnemonic} {ins.op_str}{mark}")
            n += 1
            if n > 90: break
