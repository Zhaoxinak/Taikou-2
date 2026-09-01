# -*- coding: utf-8 -*-
# <auto: portable root>
import os as _os
def _find_root(_p):
    for _ in range(8):
        if _os.path.isdir(_os.path.join(_p, 'scripts')) and _os.path.isfile(_os.path.join(_p, 'project.godot')):
            return _p
        _p = _os.path.dirname(_p)
    return _p
_ROOT = _find_root(_os.path.dirname(_os.path.abspath(__file__)))
# </auto: portable root>
import sys, struct, collections
sys.path.insert(0, _ROOT + '/scripts')
from real_assets import ls11_decompress

D = ls11_decompress(open(_ROOT + '/Taikou2 Original/ANMSEQ.LZW', 'rb').read())
N = len(D)
NENT = 520
ENT = [struct.unpack_from('<HH', D, 4 + 4 * i) for i in range(NENT)]

# opcode -> (name, operand_bytes)
OPS = {
    0x00: ('END', 0),
    0x43: ('SELECT', 1),
    0x49: ('CALL_47AD60', 0),
    0x4E: ('CLR_525340', 0),
    0x4F: ('CALL_47ADC0', 0),
    0x50: ('SET_W8', 1),
    0x53: ('CALL_4966D0', 0),
    0x57: ('CALL_496B50', 1),
    0x58: ('SET_W0', 1),
    0x59: ('SET_W2', 1),
}


def strict_decode(buf):
    """严格解码：不许越界取操作数；遇 0x00 结束；返回 (ok, steps, err)"""
    pc, steps = 0, []
    n = len(buf)
    while True:
        if pc >= n:
            return False, steps, 'PC overflow (no END)'
        op = buf[pc]
        pc += 1
        name, narg = OPS.get(op, ('SKIP', 0))
        if pc + narg > n:
            return False, steps, f'operand OOB op=0x{op:02x} at {pc-1}'
        arg = buf[pc] if narg else None
        if narg == 1 and op == 0x43 and arg >= 0x14:
            return False, steps, f'SELECT out of range {arg}'
        pc += narg
        steps.append((op, name, arg))
        if op == 0x00:
            break
    return (pc == n), steps, ('trailing bytes' if pc != n else '')


ok = bad = 0
errs = collections.Counter()
op_hist = collections.Counter()
firstbyte = collections.Counter()
lens_by_nstep = []
for i, (off, ln) in enumerate(ENT):
    buf = D[off:off + ln]
    good, steps, err = strict_decode(buf)
    if good:
        ok += 1
    else:
        bad += 1
        errs[err.split(' at')[0]] += 1
        if bad <= 10:
            print(f'  BAD #{i} off=0x{off:04x} len={ln}: {err}  bytes={buf.hex(" ")}')
    for op, name, arg in steps:
        op_hist[(op, name)] += 1
    if buf:
        firstbyte[buf[0]] += 1
    lens_by_nstep.append(len(steps))

print(f'strict decode: {ok}/{NENT} OK, {bad} bad')
print('errors:', errs.most_common())
print()
print('opcode histogram (op, name, count):')
for (op, name), c in sorted(op_hist.items()):
    print(f'  0x{op:02x} {name:<14s} {c}')
print()
print('first byte hist:', sorted(firstbyte.items(), key=lambda x: -x[1])[:20])
print('last byte all 0x00?', all(D[o + l - 1] == 0 for o, l in ENT))
print('steps min/max', min(lens_by_nstep), max(lens_by_nstep))
