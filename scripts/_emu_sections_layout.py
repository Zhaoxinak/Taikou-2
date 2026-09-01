#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""对所有 18 个序列化器统计「读宽序列」(B/W)，并检测每段的定长周期。

原理（续99 在城表上验证有效）：挂钩 0x47da10，用**调用方返回地址**区分读宽
  0x47d927 -> 来自 0x47d910 => BYTE (1B)
  0x47da59 / 0x47da64 -> 来自 0x47da50 的两次调用 => WORD (2B)
两个 W 半调用折叠为一个 'W'，得到每段真实的字段宽序列，进而定 stride。
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

import struct, json
from unicorn import Uc, UC_ARCH_X86, UC_MODE_32, UC_HOOK_CODE, UcError
import unicorn.x86_const as X

IMG = open(_ROOT + '/scripts/_unpacked_mem.bin', 'rb').read()
DISK = open(_ROOT + '/Taikou2 Original/SNDATA1.TR2', 'rb').read()
BASE = 0x400000
STACK = 0x800000; STACK_TOP = STACK + 0x20000
OBJ = 0x820000; SCRATCH = 0x840000; SCRATCH_END = 0x860000

SUB1 = [0x47dae0, 0x47dce0, 0x47e130, 0x47e3a0, 0x47e440, 0x47e5a0,
        0x47e770, 0x47ea80, 0x47ebb0, 0x47ecb0, 0x47ed10, 0x47ed70,
        0x47ee50, 0x47ef00, 0x47f050, 0x47f0a0, 0x47f1b0, 0x47f210]
SUB_LABEL = {a: 'S%d' % i for i, a in enumerate(SUB1)}

SPEC = {
    0x47f5b0:('n',0,0), 0x47ae80:('n',0,0), 0x4ebd60:('n',0,0),
    0x49a210:('n',4,0), 0x49a1c0:('n',4,0), 0x49a1f0:('n',4,0), 0x49a250:('n',4,0),
    0x492850:('str',0,0), 0x492800:('open',0,1), 0x492820:('n',0,0),
    0x4eb5c0:('mal',4,0), 0x4edfa0:('cp',0,0), 0x4edf70:('cp',0,0),
    0x4411b0:('rd',8,0), 0x441190:('rd2',0,0),
}
BYTE_CALLERS = {0x47d927}
WORD_CALLERS = {0x47da59, 0x47da64}

uc = Uc(UC_ARCH_X86, UC_MODE_32)
uc.mem_map(BASE, len(IMG), 7); uc.mem_write(BASE, IMG)
uc.mem_map(STACK, 0x20000, 7)
uc.mem_map(OBJ, 0x1000, 7)
uc.mem_map(SCRATCH, SCRATCH_END - SCRATCH, 7)
uc.mem_write(OBJ + 0x8c, struct.pack('<H', 0))
uc.reg_write(X.UC_X86_REG_ESP, STACK_TOP)
uc.reg_write(X.UC_X86_REG_ECX, OBJ)

fpos = 0; malloc_ptr = SCRATCH; cur = 'PRE'
raw = {}       # section -> list of caller va


def do_return(cleanup, value=None):
    esp = uc.reg_read(X.UC_X86_REG_ESP)
    ret = struct.unpack('<I', uc.mem_read(esp, 4))[0]
    esp += 4 + cleanup
    uc.reg_write(X.UC_X86_REG_ESP, esp)
    if value is not None:
        uc.reg_write(X.UC_X86_REG_EAX, value)
    uc.reg_write(X.UC_X86_REG_EIP, ret)


def hook_code(uc, address, size, ud):
    global fpos, malloc_ptr, cur
    if address in SUB_LABEL:
        cur = SUB_LABEL[address]; raw.setdefault(cur, []); return
    if address in SPEC:
        kind, clean, val = SPEC[address]
        if kind in ('n', 'str'):
            do_return(clean, 0); return
        if kind == 'open':
            do_return(clean, 1); return
        if kind == 'mal':
            p = malloc_ptr; malloc_ptr += 0x4000
            if malloc_ptr > SCRATCH_END: malloc_ptr = SCRATCH
            do_return(clean, p); return
        if kind == 'cp':
            esp = uc.reg_read(X.UC_X86_REG_ESP)
            d = struct.unpack('<I', uc.mem_read(esp + 4, 4))[0]
            s = struct.unpack('<I', uc.mem_read(esp + 8, 4))[0]
            n = struct.unpack('<I', uc.mem_read(esp + 0xc, 4))[0]
            if 0 < n < 0x10000 and s and d:
                try: uc.mem_write(d, uc.mem_read(s, n))
                except Exception: pass
            do_return(clean, 0); return
        if kind in ('rd', 'rd2'):
            esp = uc.reg_read(X.UC_X86_REG_ESP)
            buf = struct.unpack('<I', uc.mem_read(esp + 4, 4))[0]
            cnt = struct.unpack('<I', uc.mem_read(esp + 8, 4))[0]
            n = min(cnt, max(0, len(DISK) - fpos))
            if n > 0:
                uc.mem_write(buf, DISK[fpos:fpos + n])
            if n < cnt and 0 < cnt < 0x100000:
                try: uc.mem_write(buf + n, b'\x00' * (cnt - n))
                except Exception: pass
            fpos += cnt
            do_return(clean, cnt); return
    if address == 0x47da10:
        esp = uc.reg_read(X.UC_X86_REG_ESP)
        caller = struct.unpack('<I', uc.mem_read(esp, 4))[0]
        raw.setdefault(cur, []).append(caller)
        return


uc.hook_add(UC_HOOK_CODE, hook_code)
try:
    uc.emu_start(0x47f350, 0x47f4d0)
except UcError as e:
    print('UC ERROR at EIP=0x%x:' % uc.reg_read(X.UC_X86_REG_EIP), e)

SEC_LEN = [22, 21830, 5200, 245, 539, 180, 46, 3200, 360, 80,
           120, 3800, 160, 2280, 1176, 25, 40, 133]


def fold(callers):
    """折叠 W1+W2 -> 'W'，其余 -> 'B'"""
    out = []; i = 0
    while i < len(callers):
        if callers[i] in WORD_CALLERS and i + 1 < len(callers) \
           and callers[i + 1] in WORD_CALLERS:
            out.append('W'); i += 2
        else:
            out.append('B'); i += 1
    return out


def period(seq, maxp=200):
    """最小周期 p（按字段数），要求整除且全程重复"""
    n = len(seq)
    for p in range(1, min(maxp, n) + 1):
        if n % p: continue
        if all(seq[i] == seq[i % p] for i in range(n)):
            return p
    return None


def bytes_of(pat):
    return sum(2 if c == 'W' else 1 for c in pat)


print(f"{'sect':<5}{'func':<10}{'reads':>7}{'bytes':>7}  {'周期(字段)':>9}{'周期字节':>8}{'重复':>6}  模式(首周期)")
out = {}
for i in range(len(SUB1)):
    key = 'S%d' % i
    cl = raw.get(key, [])
    pat = fold(cl)
    p = period(pat)
    nb = bytes_of(pat)
    if p:
        pb = bytes_of(pat[:p])
        rep = len(pat) // p
        show = ''.join(pat[:p])
        if len(show) > 44: show = show[:44] + '…'
        print(f"S{i:<4}{'0x%x' % SUB1[i]:<10}{len(cl):>7}{nb:>7}  {p:>9}{pb:>8}{rep:>6}  {show}")
    else:
        print(f"S{i:<4}{'0x%x' % SUB1[i]:<10}{len(cl):>7}{nb:>7}  {'无定长':>9}{'-':>8}{'-':>6}  "
              f"{''.join(pat[:44])}{'…' if len(pat) > 44 else ''}")
    out[key] = {'func': '0x%x' % SUB1[i], 'raw_calls': len(cl),
                'bytes': nb, 'period_fields': p,
                'period_bytes': bytes_of(pat[:p]) if p else None,
                'pattern': ''.join(pat[:p]) if p else ''.join(pat[:200])}
json.dump(out, open(_ROOT + '/scripts/_sections_layout.json', 'w'), indent=1)
print('\nsaved scripts/_sections_layout.json')
