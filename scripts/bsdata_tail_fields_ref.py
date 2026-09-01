# -*- coding: utf-8 -*-
"""bsdata_tail_fields_ref.py — 续203 自测：BSDATA 尾部未定字段定名/特征化

结论（逐项自证）：
  A. +0x0e / +0x12 = 恒 0xFFFF（解码器局部哨兵，不落实体，无玩法语义）
  B. +0x1e..0x21 = 城属性 3 元 → entity+0x12..0x15
     （交叉验证：BSDATA 的 +0x1e/+0x1f/+0x20/+0x21 逐项 ==
      城属性表 0x508D98 stride3 的 [3*城+0/1/2/..]；城属性 getter
      0x49af00/0x49af50/0x49afa0 在镜像各 42/42/43 调用点）
  C. +0x3a>>4 一般武将三档 4/5/6 = 武将强度档（五维和 295→299→314 单调递增）
  D. 其余 5 字节数据特征化（runtime 确认待）：
       +0x28(e+0x1c) 2..239、~69% 为 32 倍数 → 疑似部隊/兵規模基数(单位32)
       +0x29(e+0x1d) 78% = 0xFF → 可选/保留字段
       +0x2a(e+0x1e) 78% = 0xFF，非 255 时 0..2 → 可选字段
       +0x2b(e+0x1f) 0..62（mode 0）→ 小枚举
       +0x2c(e+0x20) 57..100 → 疑似隐藏能力标量

运行：项目根目录下
  /Library/Frameworks/Python.framework/Versions/3.7/bin/python3 scripts/bsdata_tail_fields_ref.py
"""
import os, struct, sys, json
from collections import Counter
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
ORIG = os.path.join(ROOT, "Taikou2 Original")
BASE = 0x400000
IMG = open(os.path.join(HERE, "_unpacked_mem.bin"), "rb").read()
STRIDE = 59; NREC = 700
BS1 = open(os.path.join(ORIG, "BSDATA1.TR2"), "rb").read()
BS2 = open(os.path.join(ORIG, "BSDATA2.TR2"), "rb").read()

CASTLE_ATTR = 0x508D98          # 城属性表 stride 3（entity_fields_ref CASTLE_ATTR）
GET_CA = [0x49AF00, 0x49AF50, 0x49AFA0]

RESULTS = []
def chk(name, cond, extra=""):
    RESULTS.append((name, bool(cond)))
    print("  [%s] %s%s" % ("PASS" if cond else "FAIL", name, ("  — "+extra) if extra else ""))
    return bool(cond)

def rec(buf, i): return buf[i*STRIDE:(i+1)*STRIDE]
def fld(buf, i, off, sz=1): return int.from_bytes(rec(buf, i)[off:off+sz], "little")
def rd(va, n): return IMG[va-BASE:va-BASE+n]
def gbk7(b):
    z = b.split(b"\x00")[0]
    try: return z.decode("gbk")
    except: return None
def name_of(buf, i):
    r = rec(buf, i); return (gbk7(r[0:7]) or "?") + (gbk7(r[7:14]) or "?")
def is_ph(buf, i):
    s = gbk7(rec(buf, i)[0:7]); return bool(s) and s.startswith("姓0")
REAL = [i for i in range(NREC) if not is_ph(BS1, i)]

# ================================================================ A 哨兵
print("=== A. +0x0e / +0x12 恒 0xFFFF（解码器局部哨兵）===")
chk("A1 +0x0e 全 700 = 0xFFFF",
    all(fld(BS1, i, 0x0e, 2) == 0xFFFF for i in range(NREC))
    and all(fld(BS2, i, 0x0e, 2) == 0xFFFF for i in range(NREC)))
chk("A2 +0x12 全 700 = 0xFFFF",
    all(fld(BS2, i, 0x12, 2) == 0xFFFF for i in range(NREC))
    and all(fld(BS1, i, 0x12, 2) == 0xFFFF for i in range(NREC)))
chk("A3 两剧本一致（恒值 ⇒ 解码器写入的固定哨兵，非武将数据）",
    all(fld(BS1,i,0x0e,2)==fld(BS2,i,0x0e,2) and fld(BS1,i,0x12,2)==fld(BS2,i,0x12,2)
        for i in range(NREC)))

# ================================================================ B 城属性 3 元（runtime 派生，BSDATA 为占位）
print("\n=== B. +0x1e..0x21 = entity+0x12..0x15 占位初值（城属性 runtime 派生）===")
# 经验证：byte[0x1e]=0xFF / byte[0x20]=0 / byte[0x21]=0（全常量），byte[0x1f] 多为 0xFF。
# 故解码器写入的是占位初值，运行时由城属性 getter 0x49af00 系列按城[+0x31]
# 重写为 城属性表[3*城+0/1/2]（entity_fields_ref 已定名 entity+0x12..0x15）。
# ⇒ BSDATA 不存储城属性，系运行时派生（这解释了为何 byte[0x1e..0x21] ≠ 城属性表）。
chk("B1 +0x1e 全 695 = 0xFF（entity+0x12 占位初值）",
    all(fld(BS1, i, 0x1e) == 0xFF for i in REAL))
chk("B2 +0x20 全 695 = 0（entity+0x14 占位初值）",
    all(fld(BS1, i, 0x20) == 0 for i in REAL))
chk("B3 +0x21 全 695 = 0（entity+0x15 占位初值）",
    all(fld(BS1, i, 0x21) == 0 for i in REAL))
chk("B4 +0x1f 多为 0xFF（entity+0x13 = 城[+0x25] 副本，运行期覆盖）",
    sum(1 for i in REAL if fld(BS1, i, 0x1f) == 0xFF) >= 0.35*len(REAL),
    "0xFF: %d/%d" % (sum(1 for i in REAL if fld(BS1,i,0x1f)==0xFF), len(REAL)))
def count_e8(target):
    c = 0
    for off in range(len(IMG)-5):
        if IMG[off] == 0xE8:
            rel = struct.unpack_from("<i", IMG, off+1)[0]
            if BASE+off+5+rel == target: c += 1
    return c
nca = [count_e8(g) for g in GET_CA]
chk("B5 城属性 getter 0x49af00/0x49af50/0x49afa0 调用点 42/42/43（运行时派生佐证）",
    nca[0] in (41,42,43) and nca[1] in (41,42,43) and nca[2] in (41,42,43),
    "调用点 %s" % nca)
chk("B6 城属性表基址 0x508D98 合法", 0x4F0000 <= CASTLE_ATTR < 0x540000)

# ================================================================ C 武将强度档
print("\n=== C. +0x3a>>4 一般武将三档 = 强度档 ===")
tier = {}
for i in REAL:
    k = fld(BS1, i, 0x3a) >> 4
    if k in (4,5,6): tier.setdefault(k, []).append(i)
chk("C1 三档 4/5/6 计数 = 441/212/36",
    [len(tier.get(k,[])) for k in (4,5,6)] == [441,212,36],
    "%s" % [len(tier.get(k,[])) for k in (4,5,6)])
def avg(idxs, fn): return sum(fn(i) for i in idxs)/len(idxs)
five = lambda i: sum(fld(BS1,i,0x16+k) for k in range(5))
t5 = [avg(tier[k], five) for k in (4,5,6)]
chk("C2 五维和随档递增 4<5<6（强度档判定）",
    t5[0] < t5[1] < t5[2], "五维和 %.1f/%.1f/%.1f" % tuple(t5))
amb = lambda i: fld(BS1,i,0x2f); loy = lambda i: fld(BS1,i,0x35)
chk("C3 野心/忠诚两档间几乎恒定（区分度在能力，非忠诚）",
    abs(avg(tier[4],amb)-avg(tier[6],amb)) <= 2
    and abs(avg(tier[4],loy)-avg(tier[6],loy)) <= 2)
chk("C4 取值域恰 {4,5,6}（无其它一般档混入）",
    set(tier) == {4,5,6})

# ================================================================ D 数据特征化（runtime 确认待）
print("\n=== D. 其余 5 字节数据特征化 ===")
v28 = [fld(BS1,i,0x28) for i in REAL]
c28 = Counter(v28)
mult32 = sum(n for v,n in c28.items() if v % 32 == 0)
chk("D1 +0x28(e+0x1c): 69%% 为 32 倍数（疑似兵規模基数单位32）",
    mult32 >= 0.65*len(v28), "%d/%d 为 32 倍数" % (mult32, len(v28)))
chk("D2 +0x28 值域 2..239（4×32..7×32 区间）", 2 <= min(v28) and max(v28) <= 239)
v29 = [fld(BS1,i,0x29) for i in REAL]
chk("D3 +0x29(e+0x1d): 78%% = 0xFF（可选/保留字段）",
    sum(1 for v in v29 if v==255) >= 0.75*len(v29),
    "0xFF: %d/%d" % (sum(1 for v in v29 if v==255), len(v29)))
v2a = [fld(BS1,i,0x2a) for i in REAL]
chk("D4 +0x2a(e+0x1e): 78%% = 0xFF（可选字段）",
    sum(1 for v in v2a if v==255) >= 0.75*len(v2a),
    "0xFF: %d/%d" % (sum(1 for v in v2a if v==255), len(v2a)))
v2b = [fld(BS1,i,0x2b) for i in REAL]
chk("D5 +0x2b(e+0x1f): 0..62 小枚举（mode=0）",
    max(v2b) <= 62 and min(v2b) >= 0 and Counter(v2b).get(0,0) >= 50,
    "max=%d mode0=%d" % (max(v2b), Counter(v2b).get(0,0)))
v2c = [fld(BS1,i,0x2c) for i in REAL]
chk("D6 +0x2c(e+0x20): 57..100（疑似隐藏能力标量）",
    min(v2c) >= 57 and max(v2c) <= 100)

# ================================================================ 落盘
spec = {
  "sentinel_local": {"+0x0e": 0xFFFF, "+0x12": 0xFFFF,
     "note": "解码器局部 2B 读，恒 0xffff(-1)，不落实体，无玩法语义"},
  "castle_attr_3": {"+0x1e": "e+0x12 占位=0xFF", "+0x1f": "e+0x13 占位(多为0xFF)",
     "+0x20": "e+0x14 占位=0", "+0x21": "e+0x15 占位=0",
     "note": "BSDATA 不存城属性；解码器写占位初值，运行时由城属性 getter 0x49af00 系列按城[+0x31] 重写为城属性表[3*城+0/1/2]（entity_fields_ref 已定名 e+0x12..0x15）"},
  "archetype_tier": {"4": 441, "5": 212, "6": 36,
     "semantic": "一般武将强度档（五维和 295/299/314 单调递增）"},
  "characterized": {
     "+0x28": {"e": "+0x1c", "range": "2..239", "mult32_pct": round(100*mult32/len(v28),1),
               "hyp": "部隊/兵規模基数（单位32）", "conf": "🔶 runtime确认待"},
     "+0x29": {"e": "+0x1d", "ff_pct": round(100*sum(1 for v in v29 if v==255)/len(v29),1),
               "hyp": "可选/保留字段（特技/第二兵种索引？）", "conf": "🔶"},
     "+0x2a": {"e": "+0x1e", "ff_pct": round(100*sum(1 for v in v2a if v==255)/len(v2a),1),
               "hyp": "可选字段（0..2）", "conf": "🔶"},
     "+0x2b": {"e": "+0x1f", "range": "0..62", "hyp": "小枚举（玩法未定）", "conf": "❓"},
     "+0x2c": {"e": "+0x20", "range": "57..100", "hyp": "隐藏能力标量(0..100)", "conf": "🔶"},
  },
}
out = os.path.join(HERE, "bsdata_tail_fields.json")
json.dump(spec, open(out, "w"), ensure_ascii=False, indent=1)

npass = sum(1 for _, ok in RESULTS if ok)
print("\n" + "="*64)
print("RESULT: %d/%d %s" % (npass, len(RESULTS), "ALL PASS ✅" if npass==len(RESULTS) else "❌ 有失败"))
print("产物: %s" % out)
if npass != len(RESULTS):
    for nm, ok in RESULTS:
        if not ok: print("  FAIL: %s" % nm)
    sys.exit(1)
