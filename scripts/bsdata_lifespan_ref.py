# -*- coding: utf-8 -*-
"""
BSDATA 生年 / 年齢编码 参考实现（续131）
========================================
钉死 bsdata_spec.json still_unknown 里挂了很久的「生日三元组」核心项，
并给出年龄计算式的 EXE 硬证据。

核心结论
--------
1. **BSDATA `@39` 的 low 7 bit = 生年 − 1490**
   即 `生年 = 1490 + (byte[39] & 0x7F)`。
   EXE 实锤 `0x49a5c0`（年齢 getter）：
       mov  cl, byte ptr [ecx + 0x1b]
       movzx ax, byte ptr [0x5205f0]
       and  ecx, 0x7f
       add  eax, 0x618          ; +1560  → 今年
       add  ecx, 0x5d2          ; +1490  → 生年
       sub  eax, ecx
       inc  eax
       ret
   ⇒ **年齢（数え年）= (byte[0x5205f0] + 1560) − ((byte[实体+0x1b] & 0x7f) + 1490) + 1**

2. **BSDATA 字段偏移 ≠ 实体字段偏移**：生年在 BSDATA 是 `@39`(0x27)，
   在运行时武将实体是 `+0x1b` —— 存在一次带重映射的拷贝，勿按同名偏移直查。

3. **`@39` bit7 是独立 flag**：年龄计算被 `and 0x7f` 抹掉；setter `0x49a5e0`
   用 XOR 惯用法只替换低 7 位、保留 bit7。数据侧 232/700 置位，且跨剧本有
   139 条翻转 ⇒ 是剧本相关的状态位（非生日的一部分）。

4. **setter `0x49a5e0`（按年龄反设生年）**：
       ax = byte[0x5205f0] - arg
       eax += 0x619                       ; 1561
       if (ax < 0x5d2) return             ; < 1490 → 不写入
       dl = byte[ecx + 0x1b]
       eax += 0x2e                        ; +46
       al ^= dl ; eax &= 0x7f
       word[ecx + 0x1b] ^= ax             ; ★ XOR 位域惯用法
   化简：`new_low7 = (Y - 年齢 + 71) & 0x7f`
   （0x619 + 0x2e = 1607；1607 − 71 = 1536 = 0x600，在 &0x7f 下等价）
   语义自洽：生年 = 今年 + 1 − 年齢，与 getter 的数え年定义互为逆运算。

🔴 对旧说的纠偏
--------------
- 续43/59 记「@39=生日月、@40=当前年龄、@41=生日年」——**@40/@41 并非年龄/生日年**：
  实测 `@40 = 32*A + B`（A∈0..7，B∈0..31，492/700 的 B=0），且 corr(生年, @40&31)=+0.628
  但 `max(0, 生年−1548)==B` 仅命中 510/700（纯 B=0 主群假象）；`@41` 有 544/700 = 255 哨兵。
- **`@43` 与 `@58` 都不是生年的函数**（82 个生年中分别有 71 / 64 个映射到多个不同值），
  且与寿命 corr 仅 −0.03 / −0.14 ⇒ 旧注「起始月 / 预期寿命」缺乏支撑，应重新定性。
"""

B1 = "F:/Games/Taikou 2/Taikou2 Original/BSDATA1.TR2"
REC, NREC = 59, 700
BASE_YEAR = 1490          # 0x5d2
YEAR_OFF_GLOBAL = 0x5205F0
GAME_YEAR_BASE = 1560     # 0x618
_b1 = open(B1, "rb").read()


# ------------------------------------------------------------ 核心公式
def birth_year_from_field(field_byte):
    """生年 = 1490 + (field & 0x7f)。field = BSDATA @39 或 实体 +0x1b。"""
    return BASE_YEAR + (field_byte & 0x7F)


def field_from_birth_year(year):
    return (year - BASE_YEAR) & 0x7F


def age(year_offset, field_byte):
    """数え年 = (year_offset + 1560) − 生年 + 1。EXE 0x49a5c0。"""
    return (year_offset + GAME_YEAR_BASE) - birth_year_from_field(field_byte) + 1


def set_age(year_offset, old_field, new_age):
    """EXE 0x49a5e0: 按新年龄反设生年字段, 保留 bit7。返回 (new_field, written)。"""
    eax = year_offset - new_age
    eax = (eax + 0x619) & 0xFFFF
    if eax < 0x5D2:
        return old_field, False
    eax = (eax + 0x2E) & 0xFFFFFFFF
    x = ((eax & 0xFF) ^ old_field) & 0x7F
    return old_field ^ x, True


def set_age_simple(year_offset, old_field, new_age):
    """化简版 (与 set_age 等价): new_low7 = (Y - age + 71) & 0x7f"""
    return (old_field & 0x80) | ((year_offset - new_age + 71) & 0x7F)


# ------------------------------------------------------------ 数据访问
def bsd_name(rec):
    o = REC * rec
    return (_b1[o:o + 7].split(b"\x00")[0].decode("gbk", "replace") +
            _b1[o + 7:o + 13].split(b"\x00")[0].decode("gbk", "replace"))


def bsd_f(rec, off):
    return _b1[REC * rec + off]


_idx = {bsd_name(i): i for i in range(NREC)}


def rec_of(name):
    return _idx.get(name)


# 史实锚点（旧历/日本史通行生年）
ANCHORS = [
    ("织田信长", 1534), ("武田信玄", 1521), ("上杉谦信", 1530), ("德川家康", 1542),
    ("毛利元就", 1497), ("明智光秀", 1528), ("服部半藏", 1542), ("伊达政宗", 1567),
    ("真田幸村", 1567), ("石田三成", 1560), ("柴田胜家", 1521), ("丹羽长秀", 1535),
    ("前田利家", 1538), ("蜂须贺小六", 1526), ("今川氏真", 1538), ("武田胜赖", 1546),
    ("北条氏政", 1538), ("上杉景胜", 1555), ("黑田官兵卫", 1546), ("竹中半兵卫", 1544),
    ("浅井长政", 1545),
]


# ============================================================ 自检
def _run_tests():
    ok = tot = 0

    def check(name, cond):
        nonlocal ok, tot
        tot += 1
        if not cond:
            print(f"  [FAIL] {name}")
        else:
            ok += 1

    # --- 1. 编解码 round-trip
    for v in range(128):
        check(f"编解码 {v}", field_from_birth_year(BASE_YEAR + v) == v)
    check("生年上下界", birth_year_from_field(0) == 1490 and
          birth_year_from_field(0x7F) == 1617)
    check("bit7 被抹除", birth_year_from_field(0x80) == birth_year_from_field(0x00))

    # --- 2. 年龄公式与 getter 一致
    # year_offset=0 → 今年 1560；生年字段 70 → 生年 1560 → 数え年 1
    check("age(Y=0, field=70) == 1", age(0, 70) == 1)
    check("age(Y=10, field=70) == 11", age(10, 70) == 11)
    check("age 与数え年定义自洽",
          age(0, field_from_birth_year(1534)) == 1560 - 1534 + 1)

    # --- 3. setter 与 getter 互逆（保留 bit7）
    for yo in (0, 5, 20, 40):
        for ag in (1, 15, 30, 50, 70):
            for bit7 in (0x00, 0x80):
                nf, w = set_age(yo, bit7, ag)
                if w:
                    check(f"setter/getter 互逆 Y={yo} age={ag} b7={bit7:#04x}",
                          age(yo, nf) == ag and (nf & 0x80) == bit7)
    # 化简版等价
    for yo in (0, 7, 33):
        for ag in (1, 20, 44, 60):
            nf, w = set_age(yo, 0x80, ag)
            if w:
                check(f"化简版等价 Y={yo} age={ag}", set_age_simple(yo, 0x80, ag) == nf)

    # --- 4. setter 守卫: (Y - age + 1561) < 1490 → 不写入
    check("守卫: Y=0 age=100 不写入", set_age(0, 0x00, 100)[1] is False)
    check("守卫: Y=40 age=10 写入", set_age(40, 0x00, 10)[1] is True)

    # --- 5. 史实锚点 21 条（数据侧）
    hit = 0
    for nm, by in ANCHORS:
        r = rec_of(nm)
        if r is None:
            print(f"  [WARN] 未找到 {nm}")
            continue
        hit += 1
        check(f"{nm} 生年={by}", birth_year_from_field(bsd_f(r, 39)) == by)
    check("锚点全部命中 21 条", hit == 21)

    # --- 6. 全 700 条: 生年落在合理区间
    years = [birth_year_from_field(bsd_f(i, 39)) for i in range(NREC)]
    check("生年范围 1493..1582", min(years) == 1493 and max(years) == 1582)
    check("生年全部落在 1490..1617", all(1490 <= y <= 1617 for y in years))
    check("生年取值数 82", len(set(years)) == 82)

    # --- 7. bit7 flag 统计
    b7 = sum(1 for i in range(NREC) if (bsd_f(i, 39) >> 7) & 1)
    check("@39 bit7 置位 232/700", b7 == 232)

    # --- 8. 负结果断言: @43 / @58 不是生年的函数
    from collections import defaultdict
    for off, mn in ((43, 71), (58, 64)):
        m = defaultdict(set)
        for i in range(NREC):
            m[years[i]].add(bsd_f(i, off))
        multi = sum(1 for v in m.values() if len(v) > 1)
        check(f"@{off} 非生年函数 (多值生年={multi})", multi == mn)

    # --- 9. @40 = 32*A + B 分解
    v40 = [bsd_f(i, 40) for i in range(NREC)]
    check("@40 范围 2..251", min(v40) == 2 and max(v40) == 251)
    check("@40 高位 A∈0..7", all(0 <= (v >> 5) <= 7 for v in v40))
    check("@40 低位 B∈0..31", all(0 <= (v & 31) <= 31 for v in v40))
    check("@40 B=0 者 492 条", sum(1 for v in v40 if (v & 31) == 0) == 492)

    # --- 10. @41 哨兵
    check("@41 =255 者 544 条", sum(1 for i in range(NREC) if bsd_f(i, 41) == 255) == 544)

    print(f"\nRESULT: {ok}/{tot} checks passed")
    return ok == tot


if __name__ == "__main__":
    print("=== 生年/年齢 编码（续131）===")
    print(f"  生年 = {BASE_YEAR} + (BSDATA @39 & 0x7f)      [EXE 0x49a5c0: add ecx,0x5d2]")
    print(f"  年齢 = (byte[0x5205f0] + {GAME_YEAR_BASE}) - 生年 + 1   (数え年)")
    print(f"  BSDATA @39 (off 0x27)  →  运行时实体 +0x1b  （偏移重映射）\n")
    for nm, by in ANCHORS[:6]:
        r = rec_of(nm)
        if r is not None:
            f39 = bsd_f(r, 39)
            print(f"  {nm:<8} @39={f39:#04x} (bit7={f39 >> 7}) → 生年 {birth_year_from_field(f39)}"
                  f"  史実 {by}   {'OK' if birth_year_from_field(f39) == by else 'DIFF'}")
    print()
    _run_tests()
