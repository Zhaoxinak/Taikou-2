#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
_disasm_stub.py — 反汇编 TAIK2W95.exe 的脱壳 stub (入口 RVA 0x1311a0)
目的: 看清自解压算法 + 找到尾跳转 (tail jump) 指向的 OEP, 为纯静态模拟解压做准备。
依赖: capstone (managed venv)
映射: 节区1 vaddr=0xc4000 roff=0x400  ->  file_off = 0x400 + (rva-0xc4000)
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

from capstone import *

EXE = r"F:/Games/Taikou2/TAIK2W95.exe"
ENTRY_RVA = 0x1311A0
FILE_END = 0x6E400  # 451584
OUT = _ROOT + '/scripts/_stub_disasm.txt'

def rva_to_off(rva):
    return 0x400 + (rva - 0xC4000)

def main():
    b = open(EXE, "rb").read()
    start = rva_to_off(ENTRY_RVA)  # 0x6d5a0
    code = b[start:FILE_END]

    md = Cs(CS_ARCH_X86, CS_MODE_32)
    md.detail = False
    lines = []
    calls = []      # (addr, target)  CALL 到绝对地址
    jmps = []       # (addr, target)  JMP 到绝对地址
    for ins in md.disasm(code, ENTRY_RVA):
        a = ins.address
        s = f"{a:#010x}  {ins.bytes.hex():<20} {ins.mnemonic} {ins.op_str}"
        lines.append(s)
        # 绝对立即数跳转/调用
        for tok in ins.op_str.split(","):
            tok = tok.strip()
            if tok.startswith("0x"):
                try:
                    t = int(tok, 16)
                except ValueError:
                    continue
                # 落在"未打包"范围 [0x1000,0xc4000) 视作潜在 OEP 跳转
                if 0x1000 <= t < 0xC4000:
                    if ins.mnemonic.upper() == "CALL":
                        calls.append((a, t))
                    elif ins.mnemonic.upper().startswith("JMP"):
                        jmps.append((a, t))

    text = "\n".join(lines)
    open(OUT, "w").write(text)

    print(f"反汇编指令数: {len(lines)}  (写入 {OUT})")
    print(f"潜在 OEP 跳转 (JMP 到 [0x1000,0xc4000)): {jmps}")
    print(f"CALL 到该范围: {calls}")
    print("=" * 78)
    # 打印前 160 条, 看清 setup + 解压循环
    print("\n".join(lines[:160]))

if __name__ == "__main__":
    main()
