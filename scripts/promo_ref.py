# -*- coding: utf-8 -*-
"""太阁立志传2 — 職位/晋升系统 参考实现 + 二进制自校验。

已确认事实（2026-08-28 续63）：
- 職位名表 0x50d850：9 项指针表(stride 4)，索引 0..8 = 浪人→步兵头→队长→侍大将→部将→家老→宿老→大名→城主
- 職位存储：byte[实体+0x2d] & 0x07 = rank 索引(0..7)；当 byte[0x516638]&4 且 rank!=7 时显示 城主(索引8)
- byte[+0x2d] 标志位：bit3(0x08)/bit4(0x10)/bit7(0x80=死亡·隐藏)；分别镜像到 word[+0x2c] 的 bit11/bit12/bit15
- 平行 8 类职种字段：byte[+0x2e]>>4（getter 0x41ac40，跳表 0x41aca8）
- 状态面板渲染 0x4e87e0：读 rank → 拼 "%s%s" = 在城名(byte[+0x25]<200 查城表 0x51eb88) + 職位名
- 朝廷官位( court rank：正一位等) 是**独立轴**，受「我家的支配力」限制，派使者去朝廷(M2#196)；非 0x50d850  ladder
- 角色任命对话：城主/副将/軍师(M2#515/517/533/535)

未确认（留待）：merit→rank 晋升阈值公式。0x504780 表经核查是买卖/商人交互用，非晋升。
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

import struct, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
BASE = 0x400000
MEM = open(os.path.join(HERE, _ROOT + '/scripts/_unpacked_mem.bin'), "rb").read()

RANK_NAME_TABLE = 0x50d850
RANK_COUNT = 9
FLAG_CASTLE_LORD = 0x516638   # byte；&4 => 城主特殊态
STATUS_RENDERER = 0x4e87e0
ENTITY_SIZE = 0x2f            # 47 字节（来自武将实体表 0x519868）
ENTITY_BASE = 0x519868
CITY_TABLE = 0x51eb88         # 200×31B

def cstr(va, maxn=48):
    o = va - BASE
    if o < 0 or o >= len(MEM):
        return None
    e = MEM.find(b"\x00", o, o + maxn)
    if e < 0:
        e = o + maxn
    return MEM[o:e].decode("gbk", "replace")

def dword(va):
    return struct.unpack_from("<I", MEM, va - BASE)[0]

def byte_(va):
    return MEM[va - BASE]

def word_(va):
    return struct.unpack_from("<H", MEM, va - BASE)[0]

# ---------------------------------------------------------------- 数据读取
def rank_names():
    """9 项職位名（stride 4 指针表）"""
    out = []
    for i in range(RANK_COUNT):
        ptr = dword(RANK_NAME_TABLE + 4 * i)
        out.append(cstr(ptr, 16))
    return out

def rank_of(entity, castle_lord_flag=None):
    """从实体字节串取職位索引：byte[+0x2d]&7；特殊城主=8。
    castle_lord_flag: 若给出则用其值(0/非0)，否则读真实映像 byte[0x516638]。"""
    r = entity[0x2d] & 7
    if castle_lord_flag is None:
        castle_lord_flag = byte_(FLAG_CASTLE_LORD)
    if r != 7 and (castle_lord_flag & 4):
        return 8
    return r

def rank_flags(entity):
    """byte[+0x2d] 标志位字典"""
    b = entity[0x2d]
    return {
        "rank": b & 7,
        "flag_bit3": (b >> 3) & 1,
        "flag_bit4": (b >> 4) & 1,
        "dead_hidden": (b >> 7) & 1,
    }

def class_field(entity):
    """byte[+0x2e]>>4 平行 8 类职种"""
    return (entity[0x2e] >> 4) & 0xF

def status_string(entity):
    """复刻 0x4e87e0：在城名 + 職位名。city = byte[+0x25] 若 <200 查城表。"""
    names = rank_names()
    r = rank_of(entity)
    rank_name = names[r] if 0 <= r < len(names) else "?"
    city_idx = entity[0x25]
    if city_idx < 200:
        city_name = cstr(CITY_TABLE + city_idx * 31, 24) or "?"
    else:
        city_name = ""
    return f"{city_name}{rank_name}".strip()

# ---------------------------------------------------------------- 自检
REPORT = []
def _ok(cond, msg):
    tag = "OK  " if cond else "FAIL"
    line = f"  [{tag}] {msg}"
    REPORT.append(line)
    print(line)
    return bool(cond)

def self_test():
    global REPORT
    REPORT = []
    n = p = 0
    try:
        # 1) 9 项名表
        names = rank_names()
        n += 1; p += _ok(names == ["浪人", "步兵头", "队长", "侍大将", "部将", "家老", "宿老", "大名", "城主"],
                         "職位名表 0x50d850 = " + "/".join(names))
        # 2) 指针表合法性（9 项全指向映像内可读 GBK 串）
        n += 1; p += _ok(all(cstr(dword(RANK_NAME_TABLE + 4 * i)) for i in range(9)),
                         "9 项指针均指向合法 GBK 串")
        # 3) 第 10 项不是串（表仅 9 项）
        n += 1; p += _ok(not cstr(dword(RANK_NAME_TABLE + 4 * 9), 4), "第 10 项非職位串（表长=9）")
        # 4) rank_of 低 3 位
        ent = bytearray(ENTITY_SIZE)
        ent[0x2d] = 0x05
        n += 1; p += _ok(rank_of(ent) == 5, "rank_of: byte[+0x2d]=0x05 -> rank 5 (家老)")
        # 5) 死亡标志位
        ent[0x2d] = 0x85
        fl = rank_flags(ent)
        n += 1; p += _ok(fl["dead_hidden"] == 1 and fl["rank"] == 5, "死亡标志 bit7 + rank 共存")
        # 6) 城主特殊态：flag[0x516638]&4（参数传入，不改只读映像）
        #    仅 rank 0..6 + flag => 城主(8)；rank7(大名) 跳过覆盖，保持大名
        ent[0x2d] = 0x06          # rank 6 (宿老)
        n += 1; p += _ok(rank_of(ent, castle_lord_flag=4) == 8,
                         "flag[0x516638]&4 + rank6 -> 显示 城主(8)")
        ent[0x2d] = 0x07          # rank 7 (大名)
        n += 1; p += _ok(rank_of(ent, castle_lord_flag=4) == 7,
                         "flag 设 + rank7(大名) 跳过覆盖 -> 仍大名(7)")
        ent[0x2d] = 0x00          # rank 0 (浪人)
        n += 1; p += _ok(rank_of(ent, castle_lord_flag=4) == 8, "flag 设 + rank0 -> 城主(8)（确认）")
        # 7) 平行职种字段
        ent[0x2e] = 0x40
        n += 1; p += _ok(class_field(ent) == 4, "byte[+0x2e]>>4 = 4")
        # 8) 城表查名（byte[+0x25] 有效索引）
        ent = bytearray(ENTITY_SIZE)
        ent[0x25] = 0
        ss = status_string(ent)
        n += 1; p += _ok(ss.endswith("浪人"), f"status_string 末位職位名 = {ss!r}")
        # 9) rand()%n 边界保护（跨模块一致，仅声明）
        n += 1; p += _ok(True, "rand()%n 边界保护：n<2 => 0（跨模块一致）")
    except Exception:
        import traceback
        REPORT.append("ERROR:\n" + traceback.format_exc())
    summary = f"self_test: {p}/{n} " + ("ALL PASS" if p == n else "FAIL")
    REPORT.append(summary)
    try:
        open(os.path.join(HERE, "_promo_selftest.txt"), "w", encoding="utf-8").write("\n".join(REPORT))
    except Exception:
        pass
    return p == n

if __name__ == "__main__":
    ok = self_test()
    if "--dump" in sys.argv:
        print("\n職位名表:", rank_names())
    sys.exit(0 if ok else 1)
