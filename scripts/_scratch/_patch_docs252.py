# -*- coding: utf-8 -*-
from pathlib import Path
import re
p = Path(r"F:/Games/Taikou 2/GAME_DATA_SPEC.md")
t = p.read_text(encoding="utf-8")
pat = r"- \*\*残留敞口（已大幅收敛，续251 审计）\*\*：[^\n]+"
new = (
    "- **残留敞口（续252 清零）**：非图像结构/数据层 **已闭**（含 S13 `0x518588` 目标状态机协议 · 续252）。"
    "仅余图像豁免；可选评价词绘制频率 / S7 写入路径属低优先增强，不阻塞复刻。"
)
t2, n = re.subn(pat, new, t, count=1)
print("spec n=", n)
p.write_text(t2, encoding="utf-8")

# SNDATA S13 line append note
sp = Path(r"F:/Games/Taikou 2/SNDATA_SPEC.md")
st = sp.read_text(encoding="utf-8")
old = "写回器 `0x4a0ff0/0x4a1010/0x4a1030`） |"
new2 = (
    "写回器 `0x4a0ff0/0x4a1010/0x4a1030`；"
    "**续252**：emu 闭合——无 ROM 全表；A=实体索引/哨兵、B=量级(常2000)、C=小枚举；"
    "`0x409650`清零、`0x40a350`种子、`0x410a70` col4→col0 履历平移；"
    "`matrix_518588_runtime_ref.py` 13/13） |"
)
if old in st:
    sp.write_text(st.replace(old, new2, 1), encoding="utf-8")
    print("sndata patched")
else:
    print("sndata pattern miss")
