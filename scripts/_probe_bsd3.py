# -*- coding: utf-8 -*-
"""BSDATA 整文件加载器(0x47fad8 push 0xa154) + 59 步长访问器扫描。"""
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

import struct, re
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

MEM_PATH = _ROOT + '/scripts/_unpacked_mem.bin'
BASE = 0x400000
mem = open(MEM_PATH, "rb").read()
md = Cs(CS_ARCH_X86, CS_MODE_32)
md.detail = True


def dis(va, maxb=4000, n=200, stop_ret=True):
    o = va - BASE
    out = []
    for ins in md.disasm(mem[o:o + maxb], va):
        out.append((ins.address, ins.mnemonic, ins.op_str))
        if stop_ret and ins.mnemonic == "ret":
            break
        if len(out) >= n:
            break
    return out


def find_fn_start(addr, maxback=0x600):
    """向上找 55 8B EC (push ebp; mov ebp,esp) 或 56/57 等常见序言。"""
    o = addr - BASE
    for i in range(o, max(0, o - maxback), -1):
        if mem[i] == 0x55 and mem[i + 1] == 0x8B and mem[i + 2] == 0xEC:
            return BASE + i
    return None


print("=" * 78)
print("A. 含 0x47fad8 (push 0xa154 = 41300) 的函数")
print("=" * 78)
st = find_fn_start(0x47FAD8)
print(f"函数起点: {st:#x}" if st else "未找到 55 8B EC 序言")
if st:
    for a, m, o in dis(st, 4000, 220):
        mark = " <<<" if a == 0x47FAD8 else ""
        print(f"  {a:08x}  {m:<8} {o}{mark}")

print("\n" + "=" * 78)
print("B. 全镜像扫 imul r32,r32,59 (0x3b) 与 imul r32,r32,imm32=59")
print("=" * 78)
pats = {
    "imul eax,eax,0x3b": b"\x6b\xc0\x3b",
    "imul ecx,ecx,0x3b": b"\x6b\xc9\x3b",
    "imul edx,edx,0x3b": b"\x6b\xd2\x3b",
    "imul ebx,ebx,0x3b": b"\x6b\xdb\x3b",
    "imul esi,esi,0x3b": b"\x6b\xf6\x3b",
    "imul edi,edi,0x3b": b"\x6b\xff\x3b",
    "imul eax,eax,59d":  b"\x69\xc0\x3b\x00\x00\x00",
    "imul ecx,ecx,59d":  b"\x69\xc9\x3b\x00\x00\x00",
    "imul edx,edx,59d":  b"\x69\xd2\x3b\x00\x00\x00",
    "imul esi,esi,59d":  b"\x69\xf6\x3b\x00\x00\x00",
    "imul edi,edi,59d":  b"\x69\xff\x3b\x00\x00\x00",
}
tot = 0
for name, p in pats.items():
    idxs = [m.start() for m in re.finditer(re.escape(p), mem)]
    if idxs:
        tot += len(idxs)
        print(f"  {name:<24} x{len(idxs)}  {[hex(BASE + i) for i in idxs[:12]]}")
print(f"  -> 合计 {tot}")

print("\n" + "=" * 78)
print("C. 全镜像扫 ''59'' 作为乘法立即数 (任何 imul r,r,imm8==0x3b)")
print("=" * 78)
# 通用: 6B <modrm> 3B
hits = []
for i in range(len(mem) - 3):
    if mem[i] == 0x6B and mem[i + 2] == 0x3B:
        hits.append(BASE + i)
print(f"  imul r32,r32,0x3b 共 {len(hits)} 处: {[hex(h) for h in hits[:30]]}")

print("\n" + "=" * 78)
print("D. 含 0x47f3fc (push 0x2bc=700, push 0x519288) 的函数")
print("=" * 78)
st2 = find_fn_start(0x47F3FC)
print(f"函数起点: {st2:#x}" if st2 else "未找到")
if st2:
    for a, m, o in dis(st2, 3000, 160):
        mark = " <<<" if a in (0x47F3FC, 0x47F419) else ""
        print(f"  {a:08x}  {m:<8} {o}{mark}")
