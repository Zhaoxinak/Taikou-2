# -*- coding: utf-8 -*-
"""@50..@52 的张力到底是「映射错」还是「初值 > 运行期钳制」。"""
import struct
from collections import Counter

BSD1 = "F:/Games/Taikou 2/Taikou2 Original/BSDATA1.TR2"
b1 = open(BSD1, "rb").read()
REC, N = 59, 700

w = [struct.unpack_from("<H", b1, REC * i + 50)[0] for i in range(N)]
c = Counter(w)
print("=" * 76)
print("A. @50..@51 (word) 取值分布")
print("=" * 76)
for k, v in c.most_common():
    print(f"    {k:>6} (0x{k:04x})  x{v}")
print(f"\n  0xffff 哨兵: {c.get(0xFFFF, 0)}/700")
over = {k: v for k, v in c.items() if k > 60000}
print(f"  > 60000 的值: {over}")
print(f"  > 60000 且 != 0xffff: {sum(v for k, v in over.items() if k != 0xFFFF)}/700")
print(f"  非哨兵最大值: {max(k for k in c if k != 0xFFFF)}")

print("\n" + "=" * 76)
print("B. @52 (俸禄阶梯) 分布")
print("=" * 76)
v52 = Counter(b1[REC * i + 52] for i in range(N))
for k, v in sorted(v52.items()):
    print(f"    {k:>4}  x{v}")
print(f"\n  > 200 的: { {k: v for k, v in v52.items() if k > 200} }")
print(f"  ≤ 200 占比: {sum(v for k, v in v52.items() if k <= 200)}/700")

print("\n" + "=" * 76)
print("C. @48 (亲密度) vs +0x24 setter 常量 0xd(13) / 0x18(24) / 0xff(255)")
print("=" * 76)
v48 = Counter(b1[REC * i + 48] for i in range(N))
print(f"  @48 = 13 的条数: {v48.get(13, 0)}")
print(f"  @48 = 24 的条数: {v48.get(24, 0)}")
print(f"  @48 = 255 的条数: {v48.get(255, 0)}")
print(f"  @48 top6: {v48.most_common(6)}")

print("\n" + "=" * 76)
print("D. @54..@55 作为 word 是否 = 0xffff 哨兵 (对应 +0x2a)")
print("=" * 76)
w5455 = [struct.unpack_from("<H", b1, REC * i + 54)[0] for i in range(N)]
c2 = Counter(w5455)
print(f"  top5: {[(hex(k), v) for k, v in c2.most_common(5)]}")
print(f"  = 0xffff: {c2.get(0xFFFF, 0)}/700")

print("\n" + "=" * 76)
print("E. 汇总判定")
print("=" * 76)
verdicts = [
    ("@22..@29 → +0x0a..+0x11", "成立", "钳制/位域全部吻合"),
    ("@31/@49 → +0x13/+0x25", "成立", "@31==@49 700/700 ↔ 续114 实测 +0x13 是 +0x25 副本；哨兵 255 ↔ setter 常量 0xff"),
    ("@39 → +0x1b", "成立", "EXE 0x49a5c0 硬证据"),
    ("@44..@47 → +0x20..+0x23", "成立", "@44==@45 700/700；@47 恒 50 ↔ setter 常量 0x32"),
    ("@48 → +0x24", "成立", "@48=13 出现 57 次 ↔ setter 常量 0xd；@48=255 ↔ 常量 0xff"),
    ("@50..@51 → +0x26 (word)", "张力", f"非哨兵最大 {max(k for k in c if k != 0xFFFF)} vs 钳 60000"),
    ("@52 → +0x28", "张力", f"max 250 > 钳 200（{sum(v for k, v in v52.items() if k > 200)}/700 越界）"),
    ("@53 → +0x29", "成立", "max 100 = 钳 100；分布均值高符合忠诚"),
    ("@54..@55 → +0x2a (word)", "成立", f"0xffff 哨兵 {c2.get(0xFFFF,0)}/700 ↔ +0x2a 哨兵"),
    ("@56..@58 → +0x2c..+0x2e", "证据不足", "值域与已知语义不冲突但无法确证"),
]
for a, b, cc in verdicts:
    print(f"  {a:<28}{b:<10}{cc}")
