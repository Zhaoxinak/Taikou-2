#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""debug: trace 0x492e20 执行尾部 + 关键地址命中，弄清 0x4ec8c0 / 0x441330 / 0x4fb07c 调用图。"""
import os, struct
from unicorn import UC_ARCH_X86, UC_MODE_32, UC_HOOK_CODE
from unicorn.x86_const import UC_X86_REG_ESP, UC_X86_REG_EIP, UC_X86_REG_EAX
from emu_sndata_read import Emu

def main():
    e = Emu()
    trace = []
    WATCH = {0x4ec8c0, 0x4802e0, 0x4fb07c, 0x441330, 0x441170, 0x441360, 0x47d720, 0x47d890}
    def on_code(mu, address, size, ud):
        if address in WATCH:
            trace.append(("HIT", address))
        elif 0x492e20 <= address < 0x492e20+0x300:
            trace.append(("C", address))
    e.mu.hook_add(UC_HOOK_CODE, on_code)
    # 桩 I/O 回调槽（防 0x3000 崩）
    STUB = 0x900000
    e.mem_map(STUB, 0x1000); e.write(STUB, b"\xc3"*0x1000)
    e.write(0x4fb0a8, struct.pack("<I", STUB))   # lseek
    e.write(0x4fb0a0, struct.pack("<I", STUB+0x10))  # read
    e.write(0x4fb09c, struct.pack("<I", STUB+0x20))  # flush
    e.write(0x4fb07c, struct.pack("<I", STUB+0x30))  # loader
    try:
        e.call(0x492e20, args=[0x506b20], regs={UC_X86_REG_EAX:0x510000}, max_steps=0x200000)
        print("OK, no crash")
    except Exception as ex:
        print("CRASH:", ex, "last_eip=0x%06x" % e.last[0])
    print("--- trace tail ---")
    for tag, a in trace[-40:]:
        print(f"  {tag} 0x{a:06x}")
    # 统计命中
    from collections import Counter
    c = Counter(a for tag,a in trace if tag=="HIT")
    print("--- HIT 计数 ---", {f"0x{k:06x}":v for k,v in c.items()})

if __name__ == "__main__":
    main()
