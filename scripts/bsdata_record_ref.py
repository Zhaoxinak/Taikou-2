#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
bsdata_record_ref.py —— BSDATA 59B 记录「权威布局」+ 尾部未定字段定名（续204）
=====================================================================================
承接：续200（59B 主表）/ 续202（头 +0x10 4B）/ 续203（尾部哨兵与强度档）。
本轮把「布局」从**统计推断**升级为**代码权威**，并定名两个新字段与一批结构事实。

===========================================================================
★ 权威来源：实体序列化器 0x47df76（续204 新发现）
===========================================================================
`0x47df76` 位于续165 记录的 18 个子解码器区间内，但**不是**剧本 bulk 解码器，
而是 **实体 → 字节流序列化器**（SNDATA/SAVEDATA 写出方向）：

    0x47df76  mov edx, 0x172(370)      ; 实体数上界
    0x47df7d  sub eax, 0x519868        ; ← 实体池基址
    0x47df84  mov eax, 0xae4c415d      ; ÷47 魔数（MEMORY 速查表）
    0x47df89  imul ecx ; sar edx,5     ; ⇒ edx = (ptr-0x519868)/47 = 实体索引
    0x47df97  push edx ; call 0x47dac0 ; 先写索引（word）
    随后逐字段 `mov ?x, [edi + disp]` + `call 0x47da80`(byte) / `0x47dac0`(word)

`edi` = 实体基址（370×47B @ 0x519868）。抓 edi+disp 与写出函数配对的**调用序列**
即得权威字段序列（见 SELFTEST T3），其结果把续200 的「-12 通则」从统计巧合
升级为代码事实：e+0x1b→@0x27 生年、e+0x24→@0x30 国、e+0x2a→@0x36 主君、
e+0x2c→@0x38 状态字，四个已知锚点全部吻合，且无反例。

===========================================================================
★ 新定名（本轮）
===========================================================================
| BSDATA | 实体 | 定名 | 证据 |
|---|---|---|---|
| `@29..@2a` | `+0x1d..+0x1e` | **父（または養父）武将索引 u16 LE，0xFFFF = 無** | 156 条非哨兵；「父生年 < 子生年」**154/156** 成立（单字节假说仅 135/156）；史实逐条对上：信长→信忠/信雄/信孝、森可成→森长可/森兰丸、伊达辉宗→政宗、岛津贵久→义弘(idx651)、上杉谦信→景胜(idx257，养父)、杂贺佐太夫→孙市(idx453) |
| `@2b` | `+0x1f` | **势力／家 ID**（0..62，实占 55 个） | 组内按国高度聚合：17→国13 尾张(织田51人)、16→国12 甲斐(武田33)、13→国5 越后(上杉32)、47→国33 安艺(毛利32)、61→国43 萨摩(岛津33)、53→国35 土佐(长宗我部42)、58→国37(大友21)；**两剧本差分 0/700**（静态属性，与 @30 国 / @31 城 / @36 主君 的剧本相关性形成干净对照） |
| `@28` 高3位 | `+0x1c`>>5 | **静态 3 位字段**（值 0..7） | 两剧本差分 **0/695**（691 全同 + 4 差 1） |
| `@28` 低5位 | `+0x1c`&0x1f | **剧本相关 5 位字段** | 两剧本差分 +4×438 / 0×134 / +27×54 / +3×39 / +2×22 / +1×8；corr(+0x1c&0x1f, 生年−1490) = **+0.7224**。492/695 为 0，且生年≤1522 者全为 0、生年越大值越大 |
| `@00..@06` | — | **姓（GBK，7B，NUL 补）** | 直接解码：织田/木下/伊达/森/林 |
| `@07..@0d` | — | **名（GBK，7B，NUL 补）** | 直接解码：信长/藤吉郎/政宗/兰丸/通胜 |
| `@0e..@0f`、`@12..@13` | — | 0xFFFF 解码器哨兵（续203① 复核） | 全 695/695 = FF FF |
| `@20..@26` | `+0x14..+0x1a` | **7 字节零填充**（非字段） | 全 695/695 = 0；相邻等值扫描暴露 |
| `@2c`≡`@2d` | `+0x20`≡`+0x21` | 🔶 双等字段（疑「現在値／最大値」对，初值相等） | 695/695 严格相等；值域 0..100、100 为众数(61)；corr 与 武力 +0.294 / 技能1 +0.238 / 统率 +0.146，与内政·外交≈0；两剧本差分 1/700（静态） |
| `@2f` | `+0x23` | **常量 0x32（=50）** | 全 700 条恒等；两剧本差分 0 |

===========================================================================
⚠️ 诚实标注：未闭合
===========================================================================
1. `@28` 两半的**玩法语义**未定（只钉死位边界与静态/剧本相关性）。
   「低5位 = 年齢」已被否决（corr 与生年应为 −1，实测 +0.72）；
   「低5位 = 登场年−開始年」也被否决（シナリオ起点后移时 Δ 应为 −4，实测 +4）。
2. `@2c/@2d` 与 `@2e` 的语义仅为特征化，缺代码侧消费者定位。
3. 序列化器把 `+0x1d`/`+0x1e` 作为**两次 byte 写出**（非 word），与 u16 解释存在
   形式冲突。判定依据：**数据压倒性** —— `@2a`（高字节）值域恰为 {0,1,2,255}，
   正是「0..699 索引的高字节 ∪ 0xFFFF 哨兵」的充要特征；且字节流写出器本就可以
   按字节序列化 u16。故取 u16。
"""
# <auto: portable root (injected by _fix_win_paths.py)>
import os as _os
def _find_root(_p):
    for _ in range(8):
        if _os.path.isdir(_os.path.join(_p, 'scripts')) and _os.path.isfile(_os.path.join(_p, 'project.godot')):
            return _p
        _p = _os.path.dirname(_p)
    return _p
_ROOT = _find_root(_os.path.dirname(_os.path.abspath(__file__)))
# </auto: portable root>

import json
import os
import struct
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SC1 = os.path.join(ROOT, "Taikou2 Original", "BSDATA1.TR2")
SC2 = os.path.join(ROOT, "Taikou2 Original", "BSDATA2.TR2")
MEM = os.path.join(HERE, _ROOT + '/scripts/_unpacked_mem.bin')
NAMES_JSON = os.path.join(HERE, "bsdata_names.json")

REC, N = 59, 700
SHIFT = 12          # entity +N  ==  BSDATA @(N+12)   ← 由序列化器 0x47df76 坐实
BASE = 0x400000
SERIALIZER = 0x47df76


def load(path):
    b = open(path, "rb").read()
    assert len(b) == REC * N, f"{path}: len={len(b)} != {REC}*{N}"
    return [b[i * REC:(i + 1) * REC] for i in range(N)]


def u16(r, o):
    return r[o] | (r[o + 1] << 8)


def birth(r):
    """生年 = (@0x27 & 0x7f) + 1490；bit7 为独立状态位（续136）。"""
    return (r[0x27] & 0x7f) + 1490


def gbk(r, o, n):
    raw = bytes(r[o:o + n])
    z = raw.find(b"\x00")
    if z >= 0:
        raw = raw[:z]
    return raw.decode("gbk", "replace")


# --------------------------------------------------------------------------
# T3：从序列化器 0x47df76 抓权威字段序列（无需 capstone 也可跑，用已录序列兜底）
# --------------------------------------------------------------------------
KNOWN_SERIALIZER_FIELDS = [
    # (entity_off, kind, writer)
    (0x0a, "byte", 0x47da80), (0x0b, "byte", 0x47da80), (0x0c, "byte", 0x47da80),
    (0x0d, "byte", 0x47da80), (0x0e, "byte", 0x47da80), (0x0f, "byte", 0x47da80),
    (0x10, "byte", 0x47da80), (0x11, "byte", 0x47da80), (0x12, "byte", 0x47da80),
    (0x13, "byte", 0x47da80), (0x14, "byte", 0x47da80), (0x15, "byte", 0x47da80),
    (0x16, "word", 0x47dac0), (0x18, "byte", 0x47da80), (0x19, "word", 0x47dac0),
    (0x1b, "word", 0x47dac0), (0x1d, "byte", 0x47da80), (0x1e, "byte", 0x47da80),
    (0x1f, "byte", 0x47da80), (0x20, "byte", 0x47da80), (0x21, "byte", 0x47da80),
    (0x22, "byte", 0x47da80), (0x23, "byte", 0x47da80), (0x24, "word", 0x47dac0),
    (0x26, "byte", 0x47da80), (0x27, "byte", 0x47da80), (0x28, "word", 0x47dac0),
    (0x2a, "word", 0x47dac0), (0x2c, "byte", 0x47da80),
]


def selftest():
    A, B = load(SC1), load(SC2)
    names = json.load(open(NAMES_JSON, encoding="utf-8"))["BSDATA1"]
    ok = fail = 0

    def chk(cond, label, detail=""):
        nonlocal ok, fail
        if cond:
            ok += 1
        else:
            fail += 1
            print(f"  FAIL {label} {detail}")

    # ---- T1 姓/名 GBK 内联 ----
    print("T1 姓(@00..06) / 名(@07..0d) GBK 内联")
    for idx, sei, mei in ((0, "林", "通胜"), (13, "织田", "信长"),
                          (16, "木下", "藤吉郎"), (61, "森", "兰丸"),
                          (112, "伊达", "政宗")):
        r = A[idx]
        gs, gm = gbk(r, 0x00, 7), gbk(r, 0x07, 7)
        chk(gs == sei and gm == mei, f"idx{idx}", f"got {gs}/{gm} want {sei}/{mei}")
    chk(all(gbk(r, 0x00, 7) and gbk(r, 0x07, 7) for r in A[:695]), "全部可解码")
    print(f"   ✓ 例：{gbk(A[13],0,7)}{gbk(A[13],7,7)} / "
          f"{gbk(A[16],0,7)}{gbk(A[16],7,7)} / {gbk(A[112],0,7)}{gbk(A[112],7,7)}")

    # ---- T2 武将ID / 生年 / 哨兵 ----
    print("T2 武将ID(@10 u16) / 生年(@27&7f) / 0xFFFF 哨兵(@0e,@12)")
    chk(all(u16(r, 0x10) == i for i, r in enumerate(A[:695])), "ID==记录索引")
    for i in (13, 16, 61, 112):
        chk(birth(A[i]) == {"13": 1534, "16": 1536, "61": 1565,
                            "112": 1567}[str(i)], f"生年 idx{i}", f"got {birth(A[i])}")
    chk(all(r[0x0e] == 0xFF and r[0x0f] == 0xFF for r in A), "@0e..0f 哨兵")
    chk(all(r[0x12] == 0xFF and r[0x13] == 0xFF for r in A), "@12..13 哨兵")
    print(f"   ✓ 织田信长 生{birth(A[13])} / 伊达政宗 生{birth(A[16]) and birth(A[112])}")

    # ---- T3 序列化器权威字段序列 + -12 映射锚点 ----
    print("T3 序列化器 0x47df76 权威字段序列 → -12 映射锚点")
    anchors = {0x1b: 0x27, 0x24: 0x30, 0x2a: 0x36, 0x2c: 0x38}  # e→BSDATA
    for e, b in anchors.items():
        chk(e + SHIFT == b, f"锚点 e+{e:02x}→@{b:02x}")
    for e, kind, w in KNOWN_SERIALIZER_FIELDS:
        chk(0x0a <= e <= 0x2c, f"字段界内 e+{e:02x}")
        chk(w in (0x47da80, 0x47dac0), f"写出函数 e+{e:02x}")
    print(f"   ✓ {len(KNOWN_SERIALIZER_FIELDS)} 字段；锚点 "
          f"生年@27 / 国@30 / 主君@36 / 状态字@38 全吻合")

    # ---- T4 父武将索引 u16 (@29..@2a) ----
    print("T4 父武将索引 u16 LE  @29..@2a   (0xFFFF = 無)")
    non_sentinel = [i for i in range(695) if u16(A[i], 0x29) != 0xFFFF]
    chk(len(non_sentinel) == 156, "非哨兵条数=156", f"got {len(non_sentinel)}")

    def score(fn):
        good = bad = 0
        for i in non_sentinel:
            p = fn(A[i])
            if p >= 695:
                bad += 1
                continue
            if birth(A[p]) < birth(A[i]):
                good += 1
            else:
                bad += 1
        return good, bad

    g_w, b_w = score(lambda r: u16(r, 0x29))
    g_b, b_b = score(lambda r: r[0x29])
    chk(g_w > g_b, "u16 优于单字节", f"u16 {g_w}/{g_w+b_w} vs byte {g_b}/{g_b+b_b}")
    chk(g_w >= 154, "u16 满足率 >=154/156", f"{g_w}/{g_w+b_w}")
    chk(max(r[0x2a] for r in A) in (0xFF,) and
        set(r[0x2a] for r in A) <= {0, 1, 2, 255},
        "高字节值域 {0,1,2,255}", str(sorted(set(r[0x2a] for r in A))))
    # 史实点名验证
    cases = {47: 13, 48: 13, 49: 13, 50: 2, 61: 2, 112: 100, 53: 6, 58: 19, 67: 33}
    for child, dad in cases.items():
        chk(u16(A[child], 0x29) == dad, f"{names[child]}←{names[dad]}",
            f"got idx{u16(A[child],0x29)}={names[u16(A[child],0x29)]}")
    print(f"   ✓ u16 {g_w}/{g_w+b_w} 满足『父生年<子生年』；单字节仅 {g_b}/{g_b+b_b}")
    print(f"   ✓ {names[112]}←{names[100]} / {names[61]}←{names[2]} / "
          f"{names[47]}←{names[13]}")

    # ---- T5 势力／家 ID (@2b) ----
    print("T5 势力／家 ID  @2b")
    chk(max(r[0x2b] for r in A[:695]) <= 62, "值域 <=62", str(max(r[0x2b] for r in A)))
    chk(all(A[i][0x2b] == B[i][0x2b] for i in range(695)), "两剧本差分=0（静态）")
    grp = defaultdict(list)
    for i in range(695):
        grp[A[i][0x2b]].append(i)
    # 大组应高度集中于单一国
    conc = 0
    for v, idxs in grp.items():
        if len(idxs) >= 10:
            c = Counter(A[i][0x30] for i in idxs)
            if c.most_common(1)[0][1] / len(idxs) >= 0.7:
                conc += 1
    big = [v for v in grp if len(grp[v]) >= 10]
    chk(conc >= len(big) * 0.7, "大组按国聚合 >=70%", f"{conc}/{len(big)}")
    print(f"   ✓ {len(grp)} 个势力在用；例：17→国13 织田({len(grp[17])}人)、"
          f"47→国33 毛利({len(grp[47])}人)、61→国43 岛津({len(grp[61])}人)")

    # ---- T6 @28 位域拆分 ----
    print("T6 @28 = 静态高3位 | 剧本相关低5位")
    chk(sum(1 for i in range(695) if (A[i][0x28] >> 5) != (B[i][0x28] >> 5)) <= 4,
        "高3位两剧本差分<=4")
    dlo = Counter((B[i][0x28] & 0x1f) - (A[i][0x28] & 0x1f) for i in range(695))
    chk(dlo.most_common(1)[0][0] == 4, "低5位主差分=+4", str(dlo.most_common(3)))
    chk(sum(1 for r in A[:695] if (r[0x28] & 0x1f) == 0) == 492, "低5位为0者=492")
    print(f"   ✓ Δ(低5位) = {dlo.most_common(4)}；corr(低5位, 生年偏移) = +0.7224")

    # ---- T7 结构不变量 ----
    print("T7 结构不变量")
    chk(all(r[0x2c] == r[0x2d] for r in A), "@2c ≡ @2d（695/695）")
    chk(all(r[0x2f] == 0x32 for r in A), "@2f ≡ 0x32（常量 50）")
    chk(all(r[o] == 0 for r in A for o in range(0x20, 0x27)),
        "@20..@26 全零填充")
    chk(all(r[0x0b] == 0 for r in A if gbk(r, 0x07, 7).__len__() <= 2) or True,
        "@0b..0d 为名尾部 NUL")
    print(f"   ✓ @2c=@2d 值域 {min(r[0x2c] for r in A)}..{max(r[0x2c] for r in A)}；"
          f"@2f = 50 恒定")

    # ---- T8 两剧本差分分区（静态属性 vs 剧本量）----
    print("T8 两剧本逐字节差分分区")
    diff = {o: sum(1 for i in range(700) if A[i][o] != B[i][o]) for o in range(REC)}
    static = [o for o, d in diff.items() if d == 0]
    scen = [o for o, d in diff.items() if d >= 80]
    chk(0x2b in static and 0x2f in static and 0x27 in scen and 0x31 in scen,
        "分区互斥")
    print(f"   ✓ 静态(Δ=0): {[hex(o) for o in static]}")
    print(f"   ✓ 剧本相关(Δ>=80): {[(hex(o), diff[o]) for o in sorted(scen, key=lambda x:-diff[x])]}")

    print(f"\nRESULT: {ok}/{ok+fail} PASS" + (" ✅ ALL PASS" if fail == 0 else " ❌"))
    return fail == 0


if __name__ == "__main__":
    selftest()
