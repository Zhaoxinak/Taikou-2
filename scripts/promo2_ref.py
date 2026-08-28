# -*- coding: utf-8 -*-
"""太阁立志传2 — 職位晋升公式 参考实现 + 二进制自校验（2026-08-28 续63·晋升篇）

已确认链路（全为实证）：
  職位名表      0x50d850  9 项指针表
  職位阈值表    0x50bf88  6 条 × 8B = {dword rank, word 勲功阈值, word 俸禄}
  set_rank      0x49a7e0  (word[+0x2c] & 0xF8FF) | (rank<<8)
  threshold(r)  0x49fc30  查表 -> 勲功阈值；未命中返回 -1
  stipend(r)    0x49fc90  查表 -> 俸禄
  merit->rank   0x49fc60  自条目 5 递减，首个 阈值<=勲功 者；兜底 1
  晋升主逻辑    0x4ab1d0（城内自动晋升）/ 0x4b9ae0（評定晋升，同构）
  城表          0x51eb88  ×31B，+0x0a = 城主武将编号
  武将实体      0x519868  ×47B

晋升判据（两处主逻辑一致）：
  new_rank = 当前職位 + 1
  必须  new_rank < 主君職位            （不得达到/超过主君）
  必须  word[+0x26](勲功) >= 阈值表[new_rank].勲功阈值
  通过则 set_rank(new_rank)，并 byte[+0x28] = 阈值表[new_rank].俸禄
"""
import struct, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
BASE = 0x400000
MEM = open(os.path.join(HERE, "_unpacked_mem.bin"), "rb").read()

# ---------------------------------------------------------------- 常量
RANK_NAME_TABLE   = 0x50D850
RANK_COUNT        = 9
THRESHOLD_TABLE   = 0x50BF88
THRESHOLD_ENTRIES = 6          # 0x49fc30 扫 0..5
ENTITY_BASE       = 0x519868
ENTITY_SIZE       = 47         # 0x2f
CITY_TABLE        = 0x51EB88
CITY_STRIDE       = 31
MERIT_MAX         = 60000      # 0xea60，setter 0x49a770 上限
MAX_GENERAL       = 370        # 0x172
NO_CITY           = 200        # 0xc8

SET_RANK          = 0x49A7E0
THRESHOLD_FN      = 0x49FC30
STIPEND_FN        = 0x49FC90
MERIT_TO_RANK_FN  = 0x49FC60
PROMOTE_MAIN      = 0x4AB1D0
PROMOTE_COUNCIL   = 0x4B9AE0

def _u32(va):
    return struct.unpack_from("<I", MEM, va - BASE)[0]
def _u16(va):
    return struct.unpack_from("<H", MEM, va - BASE)[0]

def cstr(va, maxn=48):
    o = va - BASE
    e = MEM.find(b"\x00", o, o + maxn)
    if e < 0:
        e = o + maxn
    return MEM[o:e].decode("gbk", "replace")

# ---------------------------------------------------------------- 表读取
def rank_names():
    return [cstr(_u32(RANK_NAME_TABLE + 4 * i), 16) for i in range(RANK_COUNT)]

def merit_table():
    """[(rank, 勲功阈值, 俸禄)] × 6"""
    out = []
    for i in range(THRESHOLD_ENTRIES):
        r, m, s = struct.unpack_from("<IHH", MEM, THRESHOLD_TABLE - BASE + i * 8)
        out.append((r, m, s))
    return out

def threshold_of(rank):
    """0x49fc30：查表得勲功阈值；未命中 -1"""
    for (r, m, s) in merit_table():
        if r == rank:
            return m
    return -1

def stipend_of(rank):
    """0x49fc90：查表得俸禄；未命中 -1"""
    for (r, m, s) in merit_table():
        if r == rank:
            return s
    return -1

def rank_from_merit(merit):
    """0x49fc60：勲功 -> 職位（自高到低首个阈值<=勲功），兜底 1"""
    for i in range(THRESHOLD_ENTRIES - 1, -1, -1):
        (r, m, s) = struct.unpack_from("<IHH", MEM, THRESHOLD_TABLE - BASE + i * 8)
        if merit >= m:
            return r
    return 1

# ---------------------------------------------------------------- 实体字段
def rank_of(ent):
    """word[+0x2c] bit8..10 == byte[+0x2d] & 7"""
    return (struct.unpack_from("<H", ent, 0x2C)[0] >> 8) & 7

def set_rank(ent, rank):
    """复刻 0x49a7e0：清 bit8..10 后写入 rank，其余标志位保持"""
    w = struct.unpack_from("<H", ent, 0x2C)[0]
    w = (w & 0xF8FF) | ((rank & 7) << 8)
    struct.pack_into("<H", ent, 0x2C, w)
    return ent

def merit_of(ent):
    return struct.unpack_from("<H", ent, 0x26)[0]

def set_merit(ent, v):
    struct.pack_into("<H", ent, 0x26, min(v, MERIT_MAX))
    return ent

def city_of(ent):
    return ent[0x25]

def stipend_field(ent):
    return ent[0x28]

# ---------------------------------------------------------------- 晋升
def entity_ptr(idx):
    return ENTITY_BASE + idx * ENTITY_SIZE

def lord_index_of_city(city, mem=None):
    """城表 +0x0a = 城主武将编号；返回 None 表示无城主"""
    src = mem if mem is not None else MEM
    if city >= NO_CITY:
        return None
    off = CITY_TABLE - BASE + city * CITY_STRIDE
    idx = struct.unpack_from("<H", src, off + 0x0A)[0]
    return idx if idx < MAX_GENERAL else None

def try_promote(target, self_ent=None, lord=None):
    """复刻 0x4ab1d0。
    target/self_ent/lord 均为 47 字节实体。
    self_ent 为「玩家武将」（可为 None 表示浪人视角）。
    返回 (是否晋升, 新職位)。"""
    # ① 同城规避：若"我"非浪人且与 target 同城 -> 不晋升
    if self_ent is not None and rank_of(self_ent) != 0:
        if city_of(target) == city_of(self_ent):
            return False, rank_of(target)
    # ② 取主君（城主）
    if lord is None:
        li = lord_index_of_city(city_of(target))
        lord = None if li is None else None   # 需真实内存；此处交由调用方传入
    # ③ 逐级只升 1 级，且须严格小于主君職位
    cur = rank_of(target)
    new_rank = cur + 1
    lord_rank = rank_of(lord) if lord is not None else 0
    if new_rank >= lord_rank:
        return False, cur
    # ④ 勲功达标判定
    th = threshold_of(new_rank)
    if th < 0 or merit_of(target) < th:
        return False, cur
    # ⑤ 生效
    set_rank(target, new_rank)
    sp = stipend_of(new_rank)
    if sp >= 0:
        target[0x28] = sp & 0xFF      # 0x49a790: byte[+0x28] = 俸禄（上限 200 由 setter 钳制）
    return True, new_rank

# ---------------------------------------------------------------- 自检
REPORT = []
def _ok(cond, msg):
    line = "  [%s] %s" % ("OK  " if cond else "FAIL", msg)
    REPORT.append(line)
    print(line)
    return bool(cond)

def self_test():
    global REPORT
    REPORT = []
    n = p = 0
    try:
        names = rank_names()
        n += 1; p += _ok(names == ["浪人", "步兵头", "队长", "侍大将", "部将", "家老", "宿老", "大名", "城主"],
                         "職位名表 0x50d850 = " + "/".join(names))
        tbl = merit_table()
        n += 1; p += _ok([t[0] for t in tbl] == [1, 2, 3, 4, 5, 6],
                         "阈值表 rank 列 = " + str([t[0] for t in tbl]))
        n += 1; p += _ok([t[1] for t in tbl] == [100, 500, 1500, 5000, 10000, 30000],
                         "勲功阈值 = " + str([t[1] for t in tbl]))
        n += 1; p += _ok([t[2] for t in tbl] == [1, 10, 30, 50, 100, 200],
                         "俸禄 = " + str([t[2] for t in tbl]))
        n += 1; p += _ok(threshold_of(0) == -1 and threshold_of(7) == -1,
                         "浪人(0)/大名(7) 不在阈值表（返回 -1）")
        # rank_from_merit 边界
        n += 1; p += _ok(rank_from_merit(99) == 1 and rank_from_merit(100) == 1,
                         "勲功 99/100 -> 職位 1（兜底）")
        n += 1; p += _ok(rank_from_merit(499) == 1 and rank_from_merit(500) == 2,
                         "勲功 499->1, 500->2（边界）")
        n += 1; p += _ok(rank_from_merit(29999) == 5 and rank_from_merit(30000) == 6,
                         "勲功 29999->5(家老), 30000->6(宿老)")
        # set_rank 位操作
        ent = bytearray(ENTITY_SIZE)
        struct.pack_into("<H", ent, 0x2C, 0x0800)      # 预置死亡标志 bit15? -> 0x8000
        struct.pack_into("<H", ent, 0x2C, 0x8800)      # bit15(死亡) + bit11(标志A)
        set_rank(ent, 3)
        w = struct.unpack_from("<H", ent, 0x2C)[0]
        n += 1; p += _ok(rank_of(ent) == 3 and (w & 0x8800) == 0x8800,
                         "set_rank(3) 写入 bit8..10 且保留 bit11/bit15 (w=0x%04x)" % w)
        set_rank(ent, 6)
        n += 1; p += _ok(rank_of(ent) == 6 and (w & 0x8800) == (struct.unpack_from("<H", ent, 0x2C)[0] & 0x8800),
                         "set_rank(6) 覆盖旧值不残留")
        # 晋升：勲功不足
        t = bytearray(ENTITY_SIZE); set_rank(t, 2); set_merit(t, 499)
        lord = bytearray(ENTITY_SIZE); set_rank(lord, 7)
        ok, r = try_promote(t, None, lord)
        n += 1; p += _ok((not ok) and r == 2, "勲功 499 < 1500 -> 不晋升（職位仍 2）")
        # 晋升：达标
        set_merit(t, 1500)
        ok, r = try_promote(t, None, lord)
        n += 1; p += _ok(ok and r == 3 and rank_of(t) == 3, "勲功 1500 >= 1500 -> 晋升侍大将(3)")
        n += 1; p += _ok(stipend_field(t) == 30, "俸禄随職位更新 = %d（表值 30）" % stipend_field(t))
        # 晋升：不得达到主君職位（主君 家老=5，我 部将=4 -> new 5，不 < 5）
        t2 = bytearray(ENTITY_SIZE); set_rank(t2, 4); set_merit(t2, 99999)
        lord2 = bytearray(ENTITY_SIZE); set_rank(lord2, 5)
        ok, r = try_promote(t2, None, lord2)
        n += 1; p += _ok((not ok) and r == 4, "主君家老(5)：部将(4)->5 不允许（须严格小于主君）")
        # 主君 宿老(6)，部将(4) -> 5 允许
        lord3 = bytearray(ENTITY_SIZE); set_rank(lord3, 6)
        ok, r = try_promote(t2, None, lord3)
        n += 1; p += _ok(ok and r == 5, "主君宿老(6)：部将(4)->5(家老) 允许")
        # 同城规避
        t3 = bytearray(ENTITY_SIZE); set_rank(t3, 2); set_merit(t3, 60000); t3[0x25] = 7
        me = bytearray(ENTITY_SIZE); set_rank(me, 3); me[0x25] = 7
        ok, r = try_promote(t3, me, lord3)
        n += 1; p += _ok((not ok) and r == 2, "同城且我非浪人 -> 跳过晋升")
        me[0x25] = 9
        ok, r = try_promote(t3, me, lord3)
        n += 1; p += _ok(ok and r == 3, "不同城 -> 正常晋升")
        # 勲功上限
        t4 = bytearray(ENTITY_SIZE); set_merit(t4, 999999)
        n += 1; p += _ok(merit_of(t4) == MERIT_MAX, "勲功上限钳制 60000 (0xea60)")
    except Exception:
        import traceback
        REPORT.append("ERROR:\n" + traceback.format_exc())
    summary = "self_test: %d/%d %s" % (p, n, "ALL PASS" if p == n else "FAIL")
    REPORT.append(summary)
    open(os.path.join(HERE, "_promo2_selftest.txt"), "w", encoding="utf-8").write("\n".join(REPORT))
    return p == n

if __name__ == "__main__":
    ok = self_test()
    if "--dump" in sys.argv:
        print("")
        print("職位      勲功阈值   俸禄")
        for (r, m, s) in merit_table():
            print("  %-8s %-9d %d" % (rank_names()[r], m, s))
    sys.exit(0 if ok else 1)
