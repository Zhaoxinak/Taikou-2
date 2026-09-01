# -*- coding: utf-8 -*-

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
# 太阁立志传2 — 大名/城主 任命·继承路径 参考实现
# 反汇编证据：
#   領地->大名: 0x4c2b80(主) -> 0x4c2c30(find_daimyo) -> 0x4c2c50(setup_daimyo, set_rank(7)+0xea60)
#   家督继承:   0x4a3f80(遍历 0x51e9c0 链表) -> 0x4a40c0 -> 0x4a4030(set_rank(7)+0xea60)
#   场景初始化: 0x40fedf (set_rank(7)+0xea60)
#   城主显示:   渲染器 0x4e87e0 (rank!=7 且 0x516638 bit2 -> 显示 城主(8))
#
# 说明：領地表 0x5179b8 是「运行时表」(开局填充)，静态 dump 全 0，阈值常量取自代码。
import sys

# ---- 常量（来自反汇编） ----
ENTITY_BASE   = 0x519868
ENTITY_SIZE   = 0x2f          # 47B / 武将
TERR_BASE     = 0x5179b8      # 領地表（运行时）
TERR_STRIDE   = 0xe           # 14B / 家族
TERR_FAMILIES = 0x31          # 49 个家族
TERR_FIELD    = 4             # entry[+4] 是比较字段
DAIMYO_THRESH = 0x172         # 370 = 武将总数；entry[+4] >= 此值 -> 够格升大名
RANK_DAIMYO   = 7
RANK_CASTLE   = 8
MERIT_CAP     = 0xea60        # 60000 勲功上限
FLAG_CLLORD   = 0x516638      # 全局「当前上下文」字节，bit2 = 显示城主

class Entity:
    """最小武将实体模型（仅含本模块关心的字段）"""
    def __init__(self, rank=0, merit=0, flags2c=0, city=0xff):
        self.rank = rank          # byte[+0x2d] & 7
        self.merit = merit        # word[+0x26] 勲功
        self.flags2c = flags2c    # word[+0x2c]（bit8..10 = rank）
        self.city = city          # byte[+0x25] 城/城下町索引
    def set_rank(self, r):
        # set_rank 0x49a7e0: and eax,0xF8FF ; or eax, r<<8 ; 回写 word[+0x2c]
        self.flags2c = (self.flags2c & 0xF8FF) | ((r & 7) << 8)
        self.rank = r & 7
    def rank_field(self):
        return self.flags2c & 0x700 >> 8  # bit8..10

# ---- 領地->大名 资格判定 ----
def find_daimyo(terr_table):
    """复刻 0x4c2c30：遍历 49 家族，返回第一个 entry[+4] >= 370 的家族下标；无则 -1。
    terr_table: list of 49 entries, 每项是 dict，含 field4 (int)。"""
    for i in range(TERR_FAMILIES):
        if terr_table[i].get("field4", 0) >= DAIMYO_THRESH:
            return i
    return -1

def setup_daimyo(char, family_idx):
    """复刻 0x4c2c50：把该家族主君设为大名(7)，勲功上限 60000，初始化字段。"""
    char.set_rank(RANK_DAIMYO)
    char.merit = min(char.merit, MERIT_CAP)
    return char

# ---- 家督继承 ----
def succeed_lord(heir, old_lord):
    """复刻 0x4a4030：清空字段后升大名(7)，勲功上限 60000。"""
    # 0x49b580/0x49b5b0/0x49b5d0 传 0 = 清字段
    heir.set_rank(RANK_DAIMYO)
    heir.merit = min(heir.merit, MERIT_CAP)
    return heir

# ---- 城主 显示态 ----
def is_castle_lord_display(char, flag_byte):
    """复刻 0x4e87e0：rank(=byte[+0x2d]&7) != 7 且 全局 0x516638 bit2 -> 显示 城主(8)。"""
    r = char.rank & 7
    if r == RANK_DAIMYO:
        return False
    return bool(flag_byte & 0x04)

def display_rank(char, flag_byte):
    r = char.rank & 7
    if r != RANK_DAIMYO and (flag_byte & 0x04):
        return RANK_CASTLE  # 城主(8)
    return r


# =================== 自校验 ===================
def self_test():
    import io
    buf = io.StringIO()
    ok = 0; total = 0
    def check(name, got, exp):
        nonlocal ok, total
        total += 1
        if got == exp:
            ok += 1
            buf.write("[OK  ] %s: got=%s\n" % (name, got))
        else:
            buf.write("[FAIL] %s: got=%s exp=%s\n" % (name, got, exp))

    # 1) find_daimyo：无够格 -> -1
    t0 = [{"field4": 0} for _ in range(TERR_FAMILIES)]
    check("no-qualified", find_daimyo(t0), -1)
    # 2) find_daimyo：第 5 个够格
    t1 = [{"field4": 0} for _ in range(TERR_FAMILIES)]
    t1[5]["field4"] = 370
    check("qualified-idx", find_daimyo(t1), 5)
    # 3) find_daimyo：取第一个（第2、9都够格 -> 返回2）
    t2 = [{"field4": 0} for _ in range(TERR_FAMILIES)]
    t2[2]["field4"] = 999; t2[9]["field4"] = 999
    check("first-match", find_daimyo(t2), 2)
    # 4) 阈值边界：369 不够，370 够
    t3 = [{"field4": 369} for _ in range(TERR_FAMILIES)]
    check("boundary-369", find_daimyo(t3), -1)
    t4 = [{"field4": 370} for _ in range(TERR_FAMILIES)]
    check("boundary-370", find_daimyo(t4), 0)
    # 5) setup_daimyo：rank->7, 勲功被钳到 60000
    c = Entity(rank=3, merit=99999)
    setup_daimyo(c, 0)
    check("daimyo-rank", c.rank, 7)
    check("daimyo-merit-cap", c.merit, 60000)
    check("daimyo-bit", (c.flags2c >> 8) & 7, 7)
    # 6) succeed_lord：清字段后 rank->7
    h = Entity(rank=2, merit=50000)
    succeed_lord(h, None)
    check("succ-rank", h.rank, 7)
    check("succ-merit-cap", h.merit, 50000)  # 未超上限，保持
    # 7) 城主显示：rank!=7 + flag bit2 -> True
    c2 = Entity(rank=1, flags2c=0)
    check("castle-display-on", is_castle_lord_display(c2, 0x04), True)
    # 8) 城主显示：rank==7(大名) 即使 flag 也不显示城主
    c3 = Entity(rank=7, flags2c=(7<<8))
    check("castle-display-daimyo", is_castle_lord_display(c3, 0x04), False)
    # 9) 城主显示：flag 未置 -> False
    check("castle-display-noflag", is_castle_lord_display(c2, 0x00), False)
    # 10) display_rank：rank0 + flag -> 8(城主)
    check("display-castle", display_rank(c2, 0x04), 8)
    # 11) display_rank：rank7 + flag -> 7(大名)
    check("display-daimyo", display_rank(c3, 0x04), 7)
    # 12) display_rank：rank5 + noflag -> 5
    c4 = Entity(rank=5, flags2c=(5<<8))
    check("display-normal", display_rank(c4, 0x00), 5)

    buf.write("\nself_test: %d/%d %s\n" % (ok, total, "ALL PASS" if ok==total else "FAILED"))
    out = buf.getvalue()
    with open(_ROOT + '/scripts/_promo3_selftest.txt', "w", encoding="utf-8") as f:
        f.write(out)
    print(out)
    return ok == total

if __name__ == "__main__":
    if "--dump" in sys.argv:
        print("promo3_ref loaded; TERR_STRIDE=%d FAMILIES=%d THRESH=%d MERIT_CAP=%d"
              % (TERR_STRIDE, TERR_FAMILIES, DAIMYO_THRESH, MERIT_CAP))
    else:
        sys.exit(0 if self_test() else 1)
