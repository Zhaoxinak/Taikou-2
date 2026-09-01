# -*- coding: utf-8 -*-
"""
Unicorn 探针：验证买价标记函数 0x445ff0 的 ×1.5 公式。
脱壳映像 F:/Games/Taikou 2/scripts/_unpacked_mem.bin (2MB, VA 0x400000)
目标：确认 买价 = base × 1.5（整数），并观察 base>=500 时的 0x4ebc80 钳制行为。
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

import struct
from unicorn import Uc, UC_ARCH_X86, UC_MODE_32, UC_MEM_FETCH_UNMAPPED
from unicorn.x86_const import UC_X86_REG_EAX, UC_X86_REG_ECX, UC_X86_REG_ESP, UC_X86_REG_EIP

BIN = _ROOT + '/scripts/_unpacked_mem.bin'
data = open(BIN, "rb").read()
assert len(data) == 0x200000, len(data)

BASE = 0x400000
SIZE = 0x200000
STACK = 0x300000
STACKSZ = 0x10000
FN = 0x445ff0
RET = 0x446015  # ret 指令地址 -> emu 到达即停，不执行 ret

mu = Uc(UC_ARCH_X86, UC_MODE_32)
mu.mem_map(BASE, SIZE)          # flat RWX
mu.mem_write(BASE, data)
mu.mem_map(STACK, STACKSZ)      # 栈

def run(arg):
    mu.mem_write(STACK + STACKSZ - 8, struct.pack("<II", 0xDEADBEEF, arg & 0xFFFF))
    mu.reg_write(UC_X86_REG_ESP, STACK + STACKSZ - 8)
    mu.reg_write(UC_X86_REG_EIP, FN)
    try:
        mu.emu_start(FN, RET, timeout=2000, count=200)
        eax = mu.reg_read(UC_X86_REG_EAX)
        ecx = mu.reg_read(UC_X86_REG_ECX)
        return ("OK", eax & 0xFFFFFFFF, ecx & 0xFFFFFFFF)
    except Exception as e:
        return ("ERR", str(e)[:80], None)

# 纯算术区 (<500): 应 = arg*3/2
print("=== 0x445ff0 买价标记函数验证（base 区间 1..499，纯算术 ×1.5）===")
fails = 0
for arg in [1, 2, 10, 33, 100, 200, 333, 499]:
    st, eax, ecx = run(arg)
    expect = (arg * 3) // 2
    ok = (st == "OK" and eax == expect)
    if not ok: fails += 1
    print(f"  arg={arg:4d}  -> eax={eax!s:8}  expect={expect:4d}  {'OK' if ok else 'FAIL ' + str(st)}")

print("\n=== base >= 500（触发 0x4ebc80 钳制路径）===")
for arg in [500, 600, 1000, 2000, 3000]:
    st, eax, ecx = run(arg)
    print(f"  arg={arg:4d}  -> eax={eax!s:10}  ecx={ecx}  status={st}")

print(f"\n纯算术区失败数: {fails}")
