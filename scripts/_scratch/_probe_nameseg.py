# -*- coding: utf-8 -*-
"""采样 0x49c2b0 四段路由指向的名表，确定各段语义。"""
import struct, os

HERE = os.path.dirname(os.path.abspath(__file__))
BASE = 0x400000
MEM = open(os.path.join(HERE, "_unpacked_mem.bin"), "rb").read()
SZ = len(MEM)

OUT = []
def emit(s=""):
    OUT.append(s)

def cstr(va, maxn=64):
    o = va - BASE
    if o < 0 or o >= SZ:
        return None
    e = MEM.find(b"\x00", o, o + maxn)
    if e < 0:
        e = o + maxn
    return MEM[o:e].decode("gbk", "replace")

def u32(va):
    return struct.unpack_from("<I", MEM, va - BASE)[0]

SEGS = [
    ("id 0..999",      0x521AA8, 7, 0),
    ("id 1000..1999",  0x5077B0, 7, 1000),
    ("id 3000+",       0x507978, 7, 3000),
]
for (tag, tab, stride, baseid) in SEGS:
    emit("=" * 70)
    emit("%s   表 0x%08x  stride %d" % (tag, tab, stride))
    row = []
    for i in range(24):
        row.append("%d:%s" % (baseid + i, cstr(tab + i * stride)))
    emit("  " + "  ".join(row))

emit("")
emit("=" * 70)
emit("id 2000..2999 -> dword[0x506c54] = 0x%08x -> %r" % (u32(0x506C54), cstr(u32(0x506C54))))
emit("")
emit("周边名表对照（memory 已知）:")
for (tab, stride, tag) in ((0x506C68, 7, "9 地方"), (0x5076F0, 11, "10 职业"),
                           (0x507FC0, 7, "5 科目"), (0x507B58, 5, "10 技能"),
                           (0x506CA8, 9, "名称索引总表")):
    row = [cstr(tab + i * stride) for i in range(8)]
    emit("  0x%08x stride %-2d %-12s %s" % (tab, stride, tag, " ".join(str(x) for x in row)))

open(os.path.join(HERE, "_nameseg.txt"), "w", encoding="utf-8").write("\n".join(OUT))
print("see _nameseg.txt")
