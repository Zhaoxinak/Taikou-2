"""端到端演示：改一条游戏文本 -> 重打包 -> 回读验证。

不碰 `Taikou2 Original/` 里的原版文件，产物一律写到 `modkit/output/`。
想装进游戏时，把 output 里的文件手动覆盖到游戏目录（先备份原文件）。

用法：  python modkit/demo_edit_text.py
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ls11 import LS11File
from msgx import Msgx

SRC = os.path.join("Taikou2 Original", "MESSAGE1.LZW")
OUT = os.path.join("modkit", "output", "MESSAGE1.LZW")
TARGET_INDEX = 0
NEW_TEXT = "武将的薪水。每月从城池的收入中，按俸禄发放给武将。"


def main():
    print(f"读取 {SRC}")
    f = LS11File(open(SRC, "rb").read())
    print(f"  段数={len(f.segments)} 首段={len(f.segments[0])}B")

    m = Msgx(f.segments[0])
    orig_items = list(m.items)          # 改动前的基准，用于最后统计差异
    print(f"  MSGX 条目数={m.count}")
    print(f"\n  原文 [{TARGET_INDEX}]: {m.text(TARGET_INDEX)}")

    m.set_text(TARGET_INDEX, NEW_TEXT)
    f.segments[0] = m.pack()
    assert len(f.segments[0]) == f.segment_sizes()[0], "段长发生了变化"

    packed = f.repack()
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "wb") as fp:
        fp.write(packed)
    print(f"\n  新文 [{TARGET_INDEX}]: {NEW_TEXT}")
    print(f"  已写出 {OUT}  ({len(packed)}B, 原 {os.path.getsize(SRC)}B)")

    # 回读验证
    print("\n回读校验：")
    back = LS11File(open(OUT, "rb").read())
    assert len(back.segments) == len(f.segments), "段数不符"
    for i, (a, b) in enumerate(zip(f.segments, back.segments)):
        assert a == b, f"段 {i} 内容不一致"
    mb = Msgx(back.segments[0])
    assert mb.count == m.count, "条目数不符"
    print(f"  重打包后段内容逐字节一致，条目数 {mb.count}")
    print(f"  目标条目回读：{mb.text(TARGET_INDEX)}")
    changed = [i for i in range(mb.count) if mb.items[i] != orig_items[i]]
    print(f"  相对原版发生变化的条目：{changed}")
    assert mb.text(TARGET_INDEX) == NEW_TEXT, "目标文本未生效"
    print("\n全部断言通过 —— 改文本链路可用。")


if __name__ == "__main__":
    main()
