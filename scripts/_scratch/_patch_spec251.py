# -*- coding: utf-8 -*-
from pathlib import Path
import re
p = Path(r"F:/Games/Taikou 2/GAME_DATA_SPEC.md")
t = p.read_text(encoding="utf-8")
pat = r"- \*\*残留敞口（已大幅收敛，续250 审计）\*\*：[^\n]+"
new = (
    "- **残留敞口（已大幅收敛，续251 审计）**：计略/兵种名/阵形名负结果/评价词/`@28`/城种 bit2..5 **已闭**。"
    "**仅余 emu 运行期增强（不阻塞复刻）**：① `0x518588` 矩阵全表逐格值（清零器+静态种子已钉 · 续248/251）；"
    "② 评价词绘制循环行序/频率；③ S7 `+0x04`/`+0x0c` 写入路径。"
)
t2, n = re.subn(pat, new, t, count=1)
print("n=", n)
p.write_text(t2, encoding="utf-8")
