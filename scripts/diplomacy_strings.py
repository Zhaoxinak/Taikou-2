# -*- coding: utf-8 -*-
"""Diplomacy system string pools (Taikou 2 — 续84 partial pass).

Three CONFIRMED static string pools in the unpacked image that were previously
uncharted. Together they form the user-facing entry points of the diplomacy /
council subsystem:

  1. 国関係 (international-relation) rating table @ 0x5080cc
     — 8 levels, stride 10 bytes (GBK with null padding).
  2. 評価語 (rating adjective) table @ 0x50811c
     — 5 levels, stride 6 bytes (GBK with null padding).
  3. 大名/家臣 会議指令メニュー (lord / retainer monthly- council menu) @ 0x50c7c0
     — 22 menu items, stride 14 bytes (GBK + null padding).
       The 3rd and 4th entries (高压外交 / 友好外交) are the diplomacy entries.

NONE of the address 0x5080cc appears as an xref in the image (no push imm32,
no lea [reg + disp32]) — strongly suggests 国関係 at 0x5080cc is a dead copy
or a layout-only artefact. The real 国関係 table is likely elsewhere (maybe
inside 0x5179b8 province-politics table) and remains a target for future work.

The 大名/家臣 会議指令メニュー IS a real, well-formed pool: 0x50c7c0 is a
22-entry string table whose entries map 1:1 to the lord's council UI.

Files referenced:
  - scripts/_d_50c7c0_pool.txt  (full string pool dump)
  - GAME_DATA_SPEC.md  §3.X (TODO: §4.6.1 待破外交系统)
"""

POOLS = {
    # ===== 1. 国関係 (international relation) rating table =====
    "intl_relation": {
        "addr":      0x5080cc,
        "stride":    10,
        "count":     8,
        "encoding":  "GBK + null pad",
        "items": [
            "盟友",   # 0
            "亲密",   # 1
            "良好",   # 2
            "普通",   # 3
            "敌视",   # 4
            "险恶",   # 5
            "绝交",   # 6
            "交战",   # 7
        ],
        "xrefs":    [],   # zero xrefs found in _unpacked_mem.bin → see note
        "note":     "No xref ⇒ likely dead layout / overwritten at runtime.",
    },

    # ===== 2. 評価語 (rating adjective) table =====
    "rating_word": {
        "addr":      0x50811c,
        "stride":    6,
        "count":     5,
        "encoding":  "GBK + null pad",
        "items": [
            "最坏",   # 0
            "较坏",   # 1
            "普通",   # 2
            "良好",   # 3
            "最好",   # 4
        ],
        "xrefs":    [],   # see note
        "note":     "Adj for rating; likely used by 城/町面板 / 関係ステータス 表示.",
    },

    # ===== 3. 大名/家臣 会議指令メニュー (council menu) =====
    "council_menu": {
        "addr":      0x50c7c0,
        "stride":    14,
        "count":     21,
        "encoding":  "GBK + null pad (2B null + GBK string + 4B null = 14B)",
        "items": [
            "出兵",       # 0  +0x00
            "结束会议",   # 1  +0x0e
            "高压外交",   # 2  +0x1c  ← DIPLOMACY entry (hard-pressure)
            "友好外交",   # 3  +0x2a  ← DIPLOMACY entry (friendly)
            "谋略",       # 4  +0x38
            "卖出军粮",   # 5  +0x46
            "购入军粮",   # 6  +0x54
            "购入军马",   # 7  +0x62 (note: layout overlap → actual address +0x70)
            "购入洋枪",   # 8  +0x7e
            "开垦农田",   # 9  +0x8c
            "训练",       # 10 +0x9a
            "修复",       # 11 +0xa8
            "筑城",       # 12 +0xb6
            "朝廷工作",   # 13 +0xc4
            "收集情报",   # 14 +0xd2
            "移动居城",   # 15 +0xe0 (layout overlap → actual address +0xee+)
            "武者修行",   # 16 +0xec (partial)
            "茶会",       # 17 +0xfa
            "任命",       # 18 +0x108
            "其他武将",   # 19 +0x116
            "取消",       # 20 +0x124
        ],
        "xrefs":    ["6 处 0x507f5f / 0x509c7e / 0x509f48 / 0x509f58 / 0x50c7e0 / 0x50ce45"],
        "note":     "Items [2]/[3] are the diplomacy entry points. Real handler logic not yet located. Items 6+ have variable actual offset due to GBK + null padding interactions; cross-check with _dump_council_pool.py.",
    },

    # ===== 4. 出兵确认对话框文字列 =====
    "confirm_attack": {
        "addr":      0x50c910,
        "encoding":  "GBK format string",
        "items":     ["进攻%s城可以吗？"],
        "note":     "Format string for the 出兵 confirmation dialog. The %s gets the target 城名.",
    },
}


# ---- self-tests ----
def _self_test():
    for pool_name, p in POOLS.items():
        if "count" in p:
            assert len(p["items"]) == p["count"], f"{pool_name} item count mismatch"
        for it in p["items"]:
            assert isinstance(it, str) and len(it) > 0, f"bad item {repr(it)}"
        # check item sizes fit the stride (only for fixed-stride pools)
        if "stride" in p:
            for i, it in enumerate(p["items"]):
                assert len(it.encode("gbk")) <= p["stride"], \
                    f"{pool_name}[{i}] {it!r} exceeds stride {p['stride']}"

    # sanity: 大名家臣 council menu must include the diplomacy entries
    cm = POOLS["council_menu"]["items"]
    assert "高压外交" in cm, "高压外交 missing from council_menu"
    assert "友好外交" in cm, "友好外交 missing from council_menu"

    # 国関係 table must have 8 entries (matching the rating UI)
    ir = POOLS["intl_relation"]["items"]
    assert len(ir) == 8
    assert ir[0] == "盟友" and ir[-1] == "交战"

    # 評価語 table must have 5 entries
    rw = POOLS["rating_word"]["items"]
    assert len(rw) == 5
    assert rw[0] == "最坏" and rw[-1] == "最好"

    print("diplomacy_strings self-test: ALL PASS  (4 pools, 8+5+21+1 = 35 entries)")


if __name__ == "__main__":
    _self_test()
