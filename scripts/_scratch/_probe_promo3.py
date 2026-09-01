# -*- coding: utf-8 -*-
"""解码晋升消息 id 0x33e-0x342；完整反汇编候选 rank 设置/晋升函数。"""
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

import struct, os, bisect, re
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

HERE = os.path.dirname(os.path.abspath(__file__))
BASE = 0x400000
mem = open(os.path.join(HERE, _ROOT + '/scripts/_unpacked_mem.bin'), "rb").read()

# ---- 消息解码 ----
def msg_by_id(mid):
    # 全局 id -> 文本（来自 all_messages.txt）
    p = os.path.join(HERE, "_probe", "msgx", "all_messages.txt")
    pat = re.compile(r'^\[(\w+\.LZW)#(\d+)\] \(id=0x([0-9a-f]+)\) (.*)$')
    for ln in open(p, encoding="utf-8"):
        m = pat.match(ln.rstrip("\n"))
        if m and int(m.group(3), 16) == mid:
            return m.group(4)
    return None

out = ["=== 晋升相关消息 ==="]
for mid in range(0x33e, 0x343):
    out.append(f"  0x{mid:04x}  {msg_by_id(mid)!r}")

# ---- 函数反汇编 ----
tg = set()
i = 0
while True:
    i = mem.find(b"\xe8", i)
    if i < 0:
        break
    rel = struct.unpack_from("<i", mem, i + 1)[0]
    t = (i + BASE) + 5 + rel
    if 0x401000 <= t < 0x4f0000:
        tg.add(t)
    i += 1
funcs = sorted(tg)
def host(va):
    k = bisect.bisect_right(funcs, va) - 1
    return funcs[k] if k >= 0 else 0

md = Cs(CS_ARCH_X86, CS_MODE_32)
md.detail = False

def disasm_func(va, name, maxlen=0x400):
    fn = host(va)
    idx = funcs.index(fn)
    end = funcs[idx + 1] if idx + 1 < len(funcs) else fn + maxlen
    code = mem[fn - BASE: end - BASE]
    asm = list(md.disasm(code, fn))
    txt = f"\n########## {name}  {va:#010x}  func={fn:#010x} ({len(asm)} 条) ##########\n"
    txt += "\n".join(f"{ins.address:#010x}  {ins.bytes.hex():<18} {ins.mnemonic:<8} {ins.op_str}" for ins in asm)
    return txt

out.append(disasm_func(0x45d300, "晋升播报 0x45d300"))
out.append(disasm_func(0x49ca90, "候选A 0x49ca90"))
out.append(disasm_func(0x49cbb0, "候选B 0x49cbb0"))
out.append(disasm_func(0x49d810, "候选C 0x49d810"))

open(os.path.join(HERE, "_promo_funcs.asm"), "w", encoding="utf-8").write("\n".join(out))
print("\n".join(out[:40]))
