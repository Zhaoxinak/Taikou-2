# -*- coding: utf-8 -*-
"""判定 all_messages.txt 各 MESSAGE 段的真实编码。"""
import os, re

HERE = os.path.dirname(os.path.abspath(__file__))
path = os.path.join(HERE, "_probe", "msgx", "all_messages.txt")
raw = open(path, "rb").read()

OUT = []
def emit(s=""):
    OUT.append(s)

CANDS = ["gbk", "gb18030", "cp932", "shift_jis", "utf-8", "big5", "euc-kr"]
TESTS = [(1, 0), (2, 1491), (3, 610), (3, 13), (4, 0)]
for (f, i) in TESTS:
    m = re.search((r"\[MESSAGE%d\.LZW#%d\]\s*(.*?)\r?\n" % (f, i)).encode("ascii"), raw)
    emit("=" * 70)
    emit("MESSAGE%d.LZW#%d" % (f, i))
    if not m:
        emit("  (未找到)")
        continue
    b = m.group(1)
    emit("  bytes: " + b[:40].hex(" "))
    for c in CANDS:
        try:
            s = b.decode(c)
            emit("  %-10s %s" % (c, s[:56]))
        except Exception as e:
            emit("  %-10s <失败: %s>" % (c, type(e).__name__))

open(os.path.join(HERE, "_enc.txt"), "w", encoding="utf-8").write("\n".join(OUT))
print("see _enc.txt")
