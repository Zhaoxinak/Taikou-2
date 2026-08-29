# -*- coding: utf-8 -*-
"""导出晋升阈值表 0x504780；修正消息解码格式并解 0x33d-0x343。"""
import struct, os, re

HERE = os.path.dirname(os.path.abspath(__file__))
BASE = 0x400000
mem = open(os.path.join(HERE, "_unpacked_mem.bin"), "rb").read()

out = []
try:
    # 1) 阈值表 0x504780 (word, 前 16 项)
    out.append("=== 0x504780 rank 阈值表 (word x16) ===")
    for i in range(16):
        v = struct.unpack_from("<H", mem, 0x504780 - BASE + 2 * i)[0]
        out.append(f"  rank={i:2d}  threshold={v:#06x} ({v})")

    # 2) 修正消息格式：读 all_messages.txt 前 3 行看真实格式
    p = os.path.join(HERE, "_probe", "msgx", "all_messages.txt")
    sample = []
    with open(p, encoding="utf-8") as f:
        for j, ln in enumerate(f):
            if j >= 3:
                break
            sample.append(ln.rstrip("\n"))
    out.append("\n=== all_messages.txt 格式样例 ===")
    out.extend(sample)

    # 3) 尝试多种格式解 0x33d-0x343
    def find_by_global(pat_global):
        res = {}
        for ln in open(p, encoding="utf-8"):
            m = pat_global.match(ln.rstrip("\n"))
            if m:
                res[int(m.group(1), 16)] = m.group(2)
        return res

    maps = {}
    for pat in [
        re.compile(r'^\[(\w+\.LZW)#(\d+)\] \(id=0x([0-9a-f]+)\) (.*)$'),
        re.compile(r'^\[(\w+\.LZW)#(\d+)\] (.*)$'),
        re.compile(r'id=0x([0-9a-f]+)\) (.*)$'),
    ]:
        d = find_by_global(pat)
        if d:
            maps[pat.pattern[:20]] = d
            break

    out.append("\n=== 晋升消息 0x33d-0x343 ===")
    for mid in range(0x33d, 0x344):
        txt = None
        for d in maps.values():
            if mid in d:
                txt = d[mid]
                break
        out.append(f"  0x{mid:04x}  {txt!r}")
except Exception:
    import traceback
    out.append("ERROR:\n" + traceback.format_exc())

open(os.path.join(HERE, "_thresh.txt"), "w", encoding="utf-8").write("\n".join(out))
print("\n".join(out))
