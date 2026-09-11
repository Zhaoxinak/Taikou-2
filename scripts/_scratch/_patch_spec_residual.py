# -*- coding: utf-8 -*-
from pathlib import Path
import re

p = Path(r"F:/Games/Taikou 2/GAME_DATA_SPEC.md")
t = p.read_text(encoding="utf-8")
pat = r"- \*\*残留敞口（已大幅收敛，续235 审计）\*\*：[^\n]+"
new = (
    "- **残留敞口（已大幅收敛，续250 审计）**：计略量级/兵种·计略名/阵形名负结果/评价词绑定 **已闭**。"
    "**仅余 emu 运行期增强（不阻塞复刻）**：① `0x518588` 矩阵全表逐格值（静态种子已钉 · 续248/250）；"
    "② 城种 `+0x1c` bit3/bit4 精确名（bit2=内政/军备、bit5=築城済已闭 · 续250）；"
    "③ 评价词绘制循环行序/频率；④ S7 `+0x04`/`+0x0c` 写入路径。"
    "~~`@28`~~ → 持久化保留字段（无实体玩法读点 · 续250）；"
    "~~S15 bit1 / section A 列名~~ → 结论性静默/无主名表。"
)
t2, n = re.subn(pat, new, t, count=1)
print("replacements", n)
p.write_text(t2, encoding="utf-8")
