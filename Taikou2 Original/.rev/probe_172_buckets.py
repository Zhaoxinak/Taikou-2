# 0x172 使用点分桶 + 实体池区间散引变体清点（扩容 patch 清单前置）
import json, struct, pefile
from collections import Counter

# 1) 127 个 SET/mov 点按“序列化器函数区间”分桶
# 序列化器 16 对函数 = 0x47dae0..0x47f1b0 (SNDATA_SPEC: 读/写序列化器族)
SER_LO, SER_HI = 0x47DA00, 0x47F200
sites = json.load(open("_sites_172.json", encoding="utf-8"))
mov = [s for s in sites if s["kind"] == "SET/mov"]
push = [s for s in sites if s["kind"] == "SET/push"]
cmp0 = [s for s in sites if s["kind"] == "CMP(no-jcc)"]
bnd = [s for s in sites if s["kind"] == "BOUND"]
def bucket(s):
    va = s["addr"]
    if SER_LO <= va < SER_HI: return "serializer(保370)"
    return "runtime(改N)"
cm = Counter(bucket(s) for s in mov)
print("mov/push 循环常数 %d 点: %s" % (len(mov) + len(push), dict(cm)))
for s in mov + push:
    print("  +%06X [%s] %-28s | next: %s" % (
        s["off"], bucket(s)[:2], s["text"], s["next"]))
print("\nCMP(no-jcc) %d 点(人工判):" % len(cmp0))
for s in cmp0:
    print("  +%06X %-28s | next: %s" % (s["off"], s["text"], s["next"]))

# 2) .text 中落在池区间 [0x519868,0x51DC56) 的所有 dword 窗口（找基址变体引用）
pe = pefile.PE(r"F:\Games\Taikou 2\Taikou2 Original\TAIK2W95_zoom.exe")
BASE = pe.OPTIONAL_HEADER.ImageBase
t = [s for s in pe.sections if s.Name.rstrip(b"\0") == b".text"][0].get_data()
lo, hi = 0x519868, 0x51DC56
vals = Counter()
for pos in range(0, len(t) - 3):
    v = struct.unpack_from("<I", t, pos)[0]
    if lo <= v < hi:
        vals[v] += 1
print("\n池区间内 dword 引用变体:")
for v, c in sorted(vals.items()):
    tag = "== EBASE" if v == lo else ("== EBASE+%d" % ((v - lo) if v - lo < 0x100 else (v - lo)))
    print("  0x%08X x%-4d %s" % (v, c, tag))
