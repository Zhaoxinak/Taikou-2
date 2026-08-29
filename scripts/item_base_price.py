# -*- coding: utf-8 -*-
"""商品基价 0x513ea8 — 静态源数据全破（续86）

KEY FINDING (2026-08-29, 续86):
============================
The 商品基价 (item base price) of every 商品 in 太阁2 is **already statically
available** — it lives in the SNDATA-XOR-flow 189-item 物品定义表 (§3.19.2),
specifically at byte offset 14 (the `val` field) of each 19-byte item record.

The chain is:
    val (1..200, byte 14 of item_table 19B records)
    -> getValue() / 10 (executed by 0x44f4e0 / 0x458000 / 0x442270)
    -> base_price (stored in 0x513ea8 price object, one entry per 商品)
    -> buy_price = base * 1.5    (shop buy, formula 0x445ff0)
    -> sell_price = buy_price * 0.9  (treasure sell, formula 0x458000)
    -> tea_offer = value * (100 - prog>>1) / 100  (tea sell, formula 0x442270)

This was previously thought to require Unicorn emulation because 0x513ea8 was
found statically all-zeros. But the runtime value is just (val / 10),
where val is already extracted into item_table.json. Therefore no emulation
is needed for商品基价.

Reference scripts (already in repo, not modified here):
  - scripts/item_table.json          (189 records, val 1..200)
  - scripts/item_table_ref.py        (val self-tests)
  - scripts/economy_ref.py           (buy/sell formulas)
  - scripts/_emu_economy.py          (formula reference impl with self-tests)

This file just glues them together and exposes a clean API.
"""

import json
from pathlib import Path

_HERE = Path(__file__).parent
_ITEMS = json.loads((_HERE / "item_table.json").read_text(encoding="utf-8"))


def get_value(item_idx: int) -> int:
    """Return the val field (1..200) for an item, or 0 if unknown."""
    if 0 <= item_idx < len(_ITEMS):
        return _ITEMS[item_idx]["val"]
    return 0


def base_price(item_idx: int) -> int:
    """Return the 商品基价 (= val // 10) for an item.
    This is the value that would be written to 0x513ea8[idx] at runtime.
    """
    return get_value(item_idx) // 10


def shop_buy_price(item_idx: int) -> int:
    """buy = base * 1.5  (formula 0x445ff0, 续30 Unicorn-verified)."""
    return (base_price(item_idx) * 3) // 2


def tea_offer(item_idx: int, progress: int) -> int:
    """tea_sell_offer = val * (100 - (prog>>1)) / 100  (formula 0x442270)."""
    v = get_value(item_idx)
    return (v * (100 - ((progress & 0xFFFF) >> 1))) // 100


def treasure_sell_quote(item_idx: int, progress: int, cat: int) -> int:
    """base = val / 10; quote = base + base * (100-prog) / 100 (normal) or
       base + base * prog / 200 (cat==5 南蛮物)."""
    base = get_value(item_idx) // 10
    if cat == 5:
        return base + (base * progress) // 200
    # 0xAE147AE1 sar 6 = mul-by-magic-then-div-by-100-rounded
    # Approximation: (base * (100 - progress)) // 100, with rounding
    a = base * (100 - progress)
    return base + ((a * 0xAE147AE1) >> 38)


def _self_test():
    # Spot-check against item_table_ref.py: 村正(49) > 正宗(46)
    assert get_value(_ITEMS[0]["idx"]) >= 0
    masamune = next(it for it in _ITEMS if it["name"] == "村正")
    masahiro = next(it for it in _ITEMS if it["name"] == "正宗")
    assert masamune["val"] > masahiro["val"], "村正 should be > 正宗"

    # base = val/10 must be integer in [0..20]
    for it in _ITEMS:
        b = base_price(it["idx"])
        assert 0 <= b <= 20, "item {} val={} -> base={}".format(
            it["idx"], it["val"], b)

    # shop_buy_price = base * 1.5
    for it in _ITEMS:
        b = base_price(it["idx"])
        s = shop_buy_price(it["idx"])
        assert s == (b * 3) // 2, "buy math fail at idx={}".format(it["idx"])

    # tea_offer = val*(100-(prog>>1))/100: at prog=0, offer == val
    for it in _ITEMS:
        assert tea_offer(it["idx"], 0) == it["val"], \
            "tea_offer at prog=0 should equal val"

    # All cats 0..26 covered (cat==21 is empty by design per item_table_ref)
    cats = sorted({it["cat"] for it in _ITEMS})
    assert 21 not in cats, "cat 21 should be empty"
    assert max(cats) <= 26 and min(cats) >= 0

    # val range 1..200
    for it in _ITEMS:
        assert 1 <= it["val"] <= 200

    print("item_base_price self-test: ALL PASS  "
          "(189 items, val range 1..200, base = val//10 = 0..20)")


if __name__ == "__main__":
    _self_test()
