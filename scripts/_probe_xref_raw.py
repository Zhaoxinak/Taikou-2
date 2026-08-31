# -*- coding: utf-8 -*-
# 字节级 e8 rel32 调用引用扫描（不受线性反汇编漂移影响）
import struct

MEM = open(r"F:/Games/Taikou 2/scripts/_unpacked_mem.bin", "rb").read()
BASE = 0x400000
N = len(MEM)

def xref_call(target):
    """找所有 call target 的调用点（e8 rel32）"""
    res = []
    tgt = target & 0xffffffff
    i = 0
    while i + 5 <= N:
        if MEM[i] == 0xe8:
            rel = struct.unpack_from("<i", MEM, i+1)[0] & 0xffffffff
            nxt = (BASE + i + 5) & 0xffffffff
            dest = (nxt + rel) & 0xffffffff
            if dest == tgt:
                res.append(BASE + i)
        i += 1
    return res

targets = {
    "host_daimyo_A 0x4c2d70": 0x4c2d70,
    "host_daimyo_B 0x416c80": 0x416c80,
    "host_succession 0x4a4030": 0x4a4030,
    "host_init 0x40fed0": 0x40fed0,
    "set_rank 0x49a7e0": 0x49a7e0,
    "renderer 0x4e87e0": 0x4e87e0,
}
for name, t in targets.items():
    xs = xref_call(t)
    print(f"\n### xref {name}: {len(xs)} callers")
    for x in xs[:40]:
        print(f"    0x{x:08x}")
