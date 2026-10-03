"""modkit 命令行：解开 / 装回 LS11 容器。

    python modkit/cli.py info NAME            查看容器结构
    python modkit/cli.py unpack NAME          解单个容器 -> modkit/work/NAME/seg_*.bin
    python modkit/cli.py unpack-all           解全部容器
    python modkit/cli.py repack NAME          从 modkit/work/NAME/ 装回 -> modkit/output/NAME.LZW

约定：改完的段必须**保持原来的字节长度**（等长替换），这样 TOC 长度表、
LS11 段长都不用动，风险最低。长度变了 repack 会直接报错拦下来 —— 宁可不做，
也不要写出一个游戏读一半就崩的文件。

产出一律落在 modkit/output/，绝不覆盖 Taikou2 Original/ 里的原版。
"""

import glob
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ls11 import LS11File

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "Taikou2 Original")
WORK = os.path.join(ROOT, "modkit", "work")
OUT = os.path.join(ROOT, "modkit", "output")


def all_containers():
    files = glob.glob(os.path.join(SRC, "*.LZW")) + glob.glob(os.path.join(SRC, "*.lZW"))
    seen, out = set(), []
    for f in files:
        key = os.path.basename(f).upper()
        if key not in seen:
            seen.add(key)
            out.append(f)
    return sorted(out, key=lambda p: os.path.basename(p).upper())


def stem(path):
    b = os.path.basename(path)
    return os.path.splitext(b)[0].upper()


def cmd_info(name):
    hit = [p for p in all_containers() if stem(p) == name.upper()]
    if not hit:
        print(f"找不到容器 {name}")
        return 1
    p = hit[0]
    f = LS11File(open(p, "rb").read())
    sizes = f.segment_sizes()
    print(f"{os.path.basename(p)}  文件 {os.path.getsize(p)}B  "
          f"首段 {sizes[0]}B  data_offset {f.data_offset:#x}")
    print(f"  段数 {len(sizes)}   (header 描述第 1 段 + TOC {len(f.toc_records)} 条)")
    for i, s in enumerate(sizes[:8]):
        head = f.segments[i][:4]
        kind = head.decode("latin1")
        print(f"    段{i:4d} {s:7d}B  头4字节 {head.hex(' ')}  ({kind})")
    if len(sizes) > 8:
        print(f"    ... 其余 {len(sizes) - 8} 段")
    return 0


def _unpack(path):
    f = LS11File(open(path, "rb").read())
    d = os.path.join(WORK, stem(path))
    os.makedirs(d, exist_ok=True)
    for i, seg in enumerate(f.segments):
        with open(os.path.join(d, f"seg_{i:04d}.bin"), "wb") as fp:
            fp.write(seg)
    # 记录每段的应有长度，repack 时据此校验
    with open(os.path.join(d, "_sizes.txt"), "w") as fp:
        fp.write("\n".join(str(s) for s in f.segment_sizes()))
    return len(f.segments), d


def cmd_unpack(name):
    hit = [p for p in all_containers() if stem(p) == name.upper()]
    if not hit:
        print(f"找不到容器 {name}")
        return 1
    n, d = _unpack(hit[0])
    print(f"{os.path.basename(hit[0])} -> {d}  ({n} 段)")
    return 0


def cmd_unpack_all():
    total = 0
    for p in all_containers():
        n, d = _unpack(p)
        total += n
        print(f"  {os.path.basename(p):16s} {n:5d} 段 -> {d}")
    print(f"共解出 {total} 段，落在 {WORK}")
    return 0


def cmd_repack(name):
    name = name.upper()
    d = os.path.join(WORK, name)
    if not os.path.isdir(d):
        print(f"没有解包目录 {d}，先跑 unpack")
        return 1
    src = [p for p in all_containers() if stem(p) == name]
    if not src:
        print(f"找不到原始容器 {name}")
        return 1
    f = LS11File(open(src[0], "rb").read())
    sizes = f.segment_sizes()
    segs = sorted(glob.glob(os.path.join(d, "seg_*.bin")))
    if len(segs) != len(sizes):
        print(f"段数不符：目录 {len(segs)} 段，容器要求 {len(sizes)} 段")
        return 1
    new = []
    for i, path in enumerate(segs):
        data = open(path, "rb").read()
        if len(data) != sizes[i]:
            print(f"段 {i} 长度错误：{len(data)}B，应为 {sizes[i]}B（须等长替换）")
            return 1
        new.append(data)
    f.segments = new
    packed = f.repack()
    os.makedirs(OUT, exist_ok=True)
    dst = os.path.join(OUT, os.path.basename(src[0]))
    with open(dst, "wb") as fp:
        fp.write(packed)

    back = LS11File(packed)
    for i, (a, b) in enumerate(zip(new, back.segments)):
        assert a == b, f"回读不一致：段 {i}"
    print(f"写出 {dst}  ({len(packed)}B)  回读逐字节一致")
    return 0


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 1
    cmd = sys.argv[1]
    if cmd == "info" and len(sys.argv) > 2:
        return cmd_info(sys.argv[2])
    if cmd == "unpack" and len(sys.argv) > 2:
        return cmd_unpack(sys.argv[2])
    if cmd == "unpack-all":
        return cmd_unpack_all()
    if cmd == "repack" and len(sys.argv) > 2:
        return cmd_repack(sys.argv[2])
    print(__doc__)
    return 1


if __name__ == "__main__":
    sys.exit(main())
