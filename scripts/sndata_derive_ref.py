# -*- coding: utf-8 -*-
"""
SNDATA §11 归属派生规则 —— 验证参考实现 + 自校验（2026-08-31 续157 · P2 静态）

验证目标（对应 SNDATA_SPEC.md §11 / 破解状态清单 Task #16）：
  (A) §11 派生规则本体：BSDATA 每武将 home_city@49 + status@57 → 谁拥哪城 / 谁效忠谁。
      规则：每城（按 home_city 归组）城主 = 该组 status==7(大名) 者，否则最高 status；
            某武将「主君」= 其 home_city 组的城主。
  (B) 49B 记录 → 三缓冲扇出映射（§4 表，由 0x47fc60 反汇编实锤）：
      record[6:49]  → 0x522c88  (43B 主体 payload，经 0x4ebfe0 块拷贝)
      record[0x13]   → 0x522c60
      record[0x20]   → 0x522c70
  (C) 诚实标注：三缓冲在脱壳镜像中静态全 0（runtime only），是「剧本脚本化初始态」路径，
      与 (A) 的「花名册派生基线」是两条独立数据通路，不可混为一谈。

修复旧 _derive_ownership.py 的两处错误：
  - 旧脚本硬编码 Windows 路径 F:/Games/Taikou2/SAVEDATA.TR2（本机不存在）→ 改用本地 bsdata.json。
  - 旧脚本名表用 stride 14（错）→ 实锤 stride=9（省块 49/49 干净；城堡块 >8B 名溢出污染）。

无外部依赖（仅读 scripts/_unpacked_mem.bin + scripts/bsdata.json）。
"""

import json
import os
import struct

_HERE = os.path.dirname(os.path.abspath(__file__))
BIN = os.path.join(_HERE, "_unpacked_mem.bin")
BASE = 0x400000

# ---------------------------------------------------------------------------
# 1. BSDATA 字段偏移（来自 bsdata.json 的 fields schema，实锤）
#    "home_city@49 ... status@57 ..."  —— 与 §11.4 声称一致
# ---------------------------------------------------------------------------
BSDATA_FIELDS = json.load(open(os.path.join(_HERE, "bsdata.json")))["fields"]

# ---------------------------------------------------------------------------
# 2. EXE 名表 @0x506ca8 —— 定宽 stride 9（省块干净；城堡块 >8B 名溢出）
# ---------------------------------------------------------------------------
def load_name_table(stride=9):
    mem = open(BIN, "rb").read()
    base = 0x506ca8 - BASE
    names = []
    for i in range(370):
        chunk = mem[base + i * stride: base + i * stride + stride + 2]
        s = chunk.split(b"\x00", 1)[0]
        try:
            names.append(s.decode("gbk", "replace").strip())
        except Exception:
            names.append("")
    return names

# ---------------------------------------------------------------------------
# 3. §11 派生规则
# ---------------------------------------------------------------------------
STATUS_NAMES = {0: "无", 1: "足轻组头", 2: "足轻工头", 3: "足轻头",
                4: "家老", 5: "部将", 6: "军师", 7: "大名"}

def owner_of(occupants):
    daim = [g for g in occupants if g["status"] == 7]
    if daim:
        return max(daim, key=lambda g: g.get("loyalty", 0))
    if occupants:
        return max(occupants, key=lambda g: (g["status"], g.get("loyalty", 0)))
    return None

def derive(bsdata_chars, names):
    """返回 (castle_tbl, gen_tbl, stats)。home_city 255 = 未登场，不入城池分组。"""
    # 按 home_city 归组（仅 present? 这里用全花名册基线；bsdata 已是史实登场集）
    castle_occ = {}
    for g in bsdata_chars:
        hc = g.get("home_city")
        if hc is None or hc == 255:
            continue
        castle_occ.setdefault(hc, []).append(g)

    castle_tbl = {}
    for c, occ in castle_occ.items():
        ow = owner_of(occ)
        nm = names[c] if 0 <= c < len(names) else ""
        castle_tbl[c] = {
            "place_name": nm,
            "owner_id": ow["id"] if ow else None,
            "owner_name": ow["name"] if ow else None,
            "occupant_ids": [g["id"] for g in occ],
            "occupant_count": len(occ),
        }
    gen_tbl = {}
    for g in bsdata_chars:
        c = g.get("home_city")
        if c is None or c == 255:
            continue
        occ = castle_occ.get(c, [])
        ow = owner_of(occ)
        gen_tbl[g["id"]] = {
            "name": g["name"],
            "home_city": c,
            "place_name": names[c] if 0 <= c < len(names) else "",
            "status": g["status"],
            "lord_id": ow["id"] if (ow and ow["id"] != g["id"]) else None,
            "lord_name": ow["name"] if (ow and ow["id"] != g["id"]) else None,
        }
    stats = {
        "n_home_city_buckets": len(castle_occ),
        "n_with_owner": sum(1 for v in castle_tbl.values() if v["owner_id"] is not None),
        "n_placed_generals": len(gen_tbl),
    }
    return castle_tbl, gen_tbl, stats

# ---------------------------------------------------------------------------
# 4. 三缓冲扇出映射（0x47fc60 内 3 处 push 立即数，静态可验）
# ---------------------------------------------------------------------------
def verify_buffer_fanout():
    mem = open(BIN, "rb").read()
    # 0x47fc60 .. 0x47fd85 区间
    lo, hi = 0x47fc60 - BASE, 0x47fd86 - BASE
    seg = mem[lo:hi]
    found = {}
    for va, label in [(0x522c88, "[6:49]->0x522c88"),
                      (0x522c60, "[0x13]->0x522c60"),
                      (0x522c70, "[0x20]->0x522c70")]:
        imm = struct.pack("<I", va)
        pat = b"\x68" + imm  # push imm32
        found[label] = (pat in seg)
    return found

def verify_buffers_static_zero():
    mem = open(BIN, "rb").read()
    out = {}
    for va, nm in [(0x522c60, "0x522c60"), (0x522c70, "0x522c70"), (0x522c88, "0x522c88")]:
        off = va - BASE
        out[nm] = all(b == 0 for b in mem[off:off + 0x80])
    return out

# ===========================================================================
# 自校验
# ===========================================================================
def self_test():
    problems = []

    # --- A1: 字段偏移实锤 ---
    fstr = BSDATA_FIELDS
    if "home_city@49" not in fstr:
        problems.append("bsdata.json fields 缺 home_city@49")
    if "status@57" not in fstr:
        problems.append("bsdata.json fields 缺 status@57")

    # --- A2: 派生规则历史锚点 ---
    cs = json.load(open(os.path.join(_HERE, "bsdata.json")))["characters"]
    by_id = {c["id"]: c for c in cs}
    # 织田信长 #13
    nob = by_id.get(13)
    if not (nob and nob["home_city"] == 66 and nob["status"] == 7):
        problems.append("锚点失败: 信长#13 应 home_city=66 & status=7(大名)")
    # 同组: 柴田#1/森#2/藤吉郎#16 同 home_city=66
    grp66 = [c for c in cs if c.get("home_city") == 66]
    ids66 = {c["id"] for c in grp66}
    if not ({1, 2, 16} <= ids66):
        problems.append("锚点失败: 柴田#1/森#2/藤吉郎#16 应同属 home_city=66")
    # 前田庆次 #27 未登场
    keiji = by_id.get(27)
    if not (keiji and keiji["home_city"] == 255):
        problems.append("锚点失败: 前田庆次#27 应 home_city=255(未登场)")
    # 组内城主 = 信长
    ow = owner_of(grp66)
    if not (ow and ow["id"] == 13):
        problems.append("派生失败: home_city=66 组城主应=信长#13(status7)")
    # home_city 值域
    hc_vals = [c["home_city"] for c in cs if c.get("home_city") is not None]
    if max(hc_vals) > 291 and max(hc_vals) != 255:
        problems.append("home_city 值域异常: max=%d" % max(hc_vals))
    if 255 not in hc_vals:
        problems.append("home_city 应含 255(未登场哨兵)")

    # --- A3: 全量派生 stats ---
    names = load_name_table(9)
    # 省块干净性（0-48 应全非空）
    prov_clean = sum(1 for i in range(49) if names[i]) == 49
    if not prov_clean:
        problems.append("名表省块(0-48)未按 stride9 干净解码")
    castle_tbl, gen_tbl, stats = derive(cs, names)
    if stats["n_home_city_buckets"] != 92:
        # 史实 92 城；若花名册 home_city 仅覆盖部分则 <92，记录而非硬失败
        print(f"  [info] home_city 分组数 = {stats['n_home_city_buckets']}（史实 92 城，花名册可能未覆盖全部）")
    if stats["n_with_owner"] <= 0:
        problems.append("派生失败: 无任何城池分到城主")
    if stats["n_placed_generals"] <= 0:
        problems.append("派生失败: 无武将归入城池")

    # --- B: 三缓冲扇出映射 ---
    fanout = verify_buffer_fanout()
    for label, ok in fanout.items():
        if not ok:
            problems.append("扇出映射缺失立即数: " + label)

    # --- C: 三缓冲静态全 0 ---
    zero = verify_buffers_static_zero()
    for nm, ok in zero.items():
        if not ok:
            problems.append("缓冲 %s 静态非 0（应 runtime-only 全 0）" % nm)

    # 输出摘要
    print("== §11 派生规则验证 ==")
    print("  字段 home_city@49 / status@57 :", "OK" if ("home_city@49" in fstr and "status@57" in fstr) else "FAIL")
    print("  历史锚点 (信长组/庆次未登场/组内城主) :", "OK" if not problems else "FAIL")
    print(f"  全量派生: {stats['n_home_city_buckets']} 城分组 / {stats['n_with_owner']} 有主 / {stats['n_placed_generals']} 武将归城")
    print("  三缓冲扇出映射:", {k: ("✓" if v else "✗") for k, v in fanout.items()})
    print("  三缓冲静态全0 (runtime-only):", {k: ("✓" if v else "✗") for k, v in zero.items()})
    print("  名表 stride9 省块干净:", prov_clean)

    if problems:
        print("\n❌ 自校验未通过:")
        for p in problems:
            print("   -", p)
        raise SystemExit(1)
    print("\n✅ 自校验全部通过：§11 派生规则 + 三缓冲扇出映射 一致")

    # 产物
    out = {
        "method": "BSDATA home_city@49 + status@57 派生（§11 规则）；名表 stride9（省块干净/城堡块>8B溢出）",
        "caveat": "0x522c60/0x522c70/0x522c88 为 runtime-only 全0缓冲，是剧本脚本化初始态，独立于本花名册派生基线",
        "stats": stats,
        "castle_table": castle_tbl,
        "general_table": gen_tbl,
    }
    json.dump(out, open(os.path.join(_HERE, "ownership_derived.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    print("wrote ownership_derived.json")
    return stats

if __name__ == "__main__":
    self_test()
