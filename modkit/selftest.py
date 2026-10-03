"""modkit 自检：解包 -> 重打包 -> 再解包，结果必须逐字节一致。

用法：  python modkit/selftest.py
注意：须在工程根运行（脚本会用相对路径找 Taikou2 Original/）。
"""

import glob
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ls11 import LS11File

SRC = os.path.join("Taikou2 Original")


def main():
    files = sorted(glob.glob(os.path.join(SRC, "*.LZW")) +
                   glob.glob(os.path.join(SRC, "*.lZW")))
    npass = nfail = 0
    rows = []
    for f in files:
        name = os.path.basename(f)
        try:
            src = LS11File(open(f, "rb").read())
            packed = src.repack()
            back = LS11File(packed)
            assert len(src.segments) == len(back.segments), (
                f"段数不符 {len(src.segments)} != {len(back.segments)}")
            for i, (a, b) in enumerate(zip(src.segments, back.segments)):
                assert a == b, f"段 {i} 内容不一致"
            npass += 1
            orig = len(open(f, "rb").read())
            rows.append((name, len(src.segments), src.decompressed_size,
                         orig, len(packed), src.toc_records and 0 or 0, True))
        except Exception as e:
            nfail += 1
            rows.append((name, 0, 0, 0, 0, 0, False))
            print(f"  FAIL {name}: {type(e).__name__}: {e}")

    print()
    hdr = f'{"文件":16s} {"段数":>5s} {"首段长":>7s} {"原大小":>9s} {"重打包":>9s} {"体积差":>9s} {"pass":>5s}'
    print(hdr)
    print("-" * len(hdr))
    for name, nseg, dsize, orig, new, _tail, ok in rows:
        if not ok:
            print(f"{name:16s}  ---- FAIL ----")
            continue
        print(f'{name:16s} {nseg:5d} {dsize:7d} {orig:9d} {new:9d} {new-orig:+9d} {"OK":>5s}')
    print("-" * len(hdr))
    print(f"通过 {npass} / 失败 {nfail}")
    return 1 if nfail else 0


if __name__ == "__main__":
    sys.exit(main())
