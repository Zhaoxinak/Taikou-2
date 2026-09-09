# _test_castle_town_mirror.py — 城下町经济/背包逻辑 Python 等价镜像
# 本机 Godot --script 主循环失效，故用此镜像复跑同一套断言验证逻辑与期望值。
# 对应 GDScript（待实跑）：src/core/economy.gd(item_value/item_buy_price/item_sell_value)
#                          src/core/game_state.gd(spend_money/gain_money/shop_buy/shop_sell/buy_medicine)
#                          src/core/shop.gd(medicine_doses/medicine_cost)
import json, os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ITEMS = json.load(open(os.path.join(ROOT, "data", "items.json")))


# ============================================================ 复制 economy.gd 纯逻辑
ITEM_CAT8 = {"茶具": 7, "美术品": 6, "南蛮物": 5, "书籍": 1, "道具": 2, "武器": 4, "财宝": 3}


def treasure_value(level, sub, category):
    lvl = level & 0xFF
    s = sub & 0xFF
    cat = category & 7
    if cat == 0:
        return max(1, min(lvl, 250))
    if cat == 1:
        return max(10, min((lvl + s * 10) * 10, 6500))
    if cat == 2:
        return max(20, min(lvl * 20, 5000))
    if cat == 3:
        return max(100, min((lvl + s * 50) * 10, 32496))
    if cat == 4:
        return max(200, min((lvl + max(s - 5, 0) * 5) * 200, 60000))
    return max(200, min((lvl * (s + 5)) << 2, 50000))


def item_value(item):
    cat = ITEM_CAT8.get(item.get("cat_name", ""), 0)
    return treasure_value(item.get("val", 1), item.get("tier", 0), cat)


def item_buy_price(item):
    return (item_value(item) * 3) // 2


def item_sell_value(item):
    return item_value(item) // 2


def medicine_doses(gold):
    g = int(gold)
    if g >= 0:
        return g // 50
    return -((-g + 49) // 50)


def medicine_cost(d):
    return d * 50


# ============================================================ 复制 game_state.gd 经济/背包逻辑
class MiniState:
    def __init__(self, money=1000):
        self.money = money
        self.inv = {}
        self.med = 0

    def spend_money(self, c):
        if c <= 0:
            return True
        if self.money < c:
            return False
        self.money -= c
        return True

    def gain_money(self, n):
        self.money = max(0, self.money + n)

    def add_item(self, i, q=1):
        self.inv[i] = self.inv.get(i, 0) + q

    def count_item(self, i):
        return self.inv.get(i, 0)

    def spend_item(self, i, q=1):
        if self.count_item(i) < q:
            return False
        self.inv[i] -= q
        return True

    def shop_buy(self, i):
        res = {"ok": False, "reason": "", "cost": 0, "name": ""}
        item = next((x for x in ITEMS if x["id"] == i), None)
        if item is None:
            res["reason"] = "no_item"
            return res
        price = item_buy_price(item)
        if self.money < price:
            res["reason"] = "no_money"
            return res
        self.spend_money(price)
        self.add_item(i, 1)
        res["ok"] = True
        res["cost"] = price
        res["name"] = item["name"]
        return res

    def shop_sell(self, i, q=1):
        res = {"ok": False, "reason": "", "gain": 0, "name": ""}
        if q <= 0:
            res["reason"] = "bad_qty"
            return res
        if self.count_item(i) < q:
            res["reason"] = "no_item"
            return res
        item = next((x for x in ITEMS if x["id"] == i), None)
        if item is None:
            res["reason"] = "no_item"
            return res
        unit = item_sell_value(item)
        gain = unit * q
        self.spend_item(i, q)
        self.gain_money(gain)
        res["ok"] = True
        res["gain"] = gain
        res["name"] = item["name"]
        return res

    def buy_medicine(self, d):
        res = {"ok": False, "reason": "", "cost": 0, "doses": 0}
        if d <= 0:
            res["reason"] = "bad_doses"
            return res
        cost = medicine_cost(d)
        if self.money < cost:
            res["reason"] = "no_money"
            return res
        self.spend_money(cost)
        self.med += d
        res["ok"] = True
        res["cost"] = cost
        res["doses"] = d
        return res


# ============================================================ 断言
_pass = 0
_fail = 0


def chk(name, cond, detail=""):
    global _pass, _fail
    if cond:
        _pass += 1
    else:
        _fail += 1
        print("  FAIL  %s%s" % (name, ("  (%s)" % detail) if detail != "" else ""))


print("=== item_value 模型（全物品）===")
vals = [(it["id"], item_value(it)) for it in ITEMS]
vmin = min(v for _, v in vals)
vmax = max(v for _, v in vals)
chk("全部物品价值 > 0", vmin > 0)
chk("最高价值 >= 1000（名物应有高价）", vmax >= 1000, "max=%d" % vmax)
# 买价 = 1.5× 价值
it0 = ITEMS[0]
chk("item_buy_price = value*3/2", item_buy_price(it0) == item_value(it0) * 3 // 2)
chk("item_sell_value = value/2", item_sell_value(it0) == item_value(it0) // 2)
chk("买价 > 卖价（含加价）", item_buy_price(it0) > item_sell_value(it0))

print("=== 买不起（初始 1000 金）===")
hi = max(ITEMS, key=item_buy_price)
hi_id, hi_price = hi["id"], item_buy_price(hi)
chk("存在 >1000 金物品", hi_price > 1000, "hi_price=%d" % hi_price)
st = MiniState(1000)
r = st.shop_buy(hi_id)
chk("金不足 → 失败 no_money", (not r["ok"]) and r["reason"] == "no_money")
chk("金不变", st.money == 1000)
chk("背包为空", st.count_item(hi_id) == 0)

print("=== 买得起（注入资金）===")
st.gain_money(200000)
before = st.money
r = st.shop_buy(hi_id)
chk("购买成功", r["ok"])
chk("扣钱正确", st.money == before - hi_price, "%d vs %d" % (st.money, before - hi_price))
chk("入库 1 件", st.count_item(hi_id) == 1)

print("=== 卖出回笼 ===")
before2 = st.money
r = st.shop_sell(hi_id, 1)
chk("卖出成功", r["ok"])
chk("加钱 = 卖价", st.money == before2 + r["gain"], "%d vs %d" % (st.money, before2 + r["gain"]))
chk("背包清空", st.count_item(hi_id) == 0)

print("=== 买薬 ===")
st.gain_money(100000)
md = medicine_doses(st.money)
chk("medicine_doses = gold//50", md == st.money // 50)
before_med = st.money
r = st.buy_medicine(md)
chk("买薬成功", r["ok"])
chk("薬数 = 服数", st.med == md)
chk("扣金 = 服数×50", st.money == before_med - md * 50)

print("=== 边界 ===")
chk("买薬 0 服 → bad_doses", not st.buy_medicine(0)["ok"])
chk("空背包卖出 → no_item", not st.shop_sell(99999, 1)["ok"])
chk("不存在物品购买 → no_item", not st.shop_buy(99999)["ok"])

print("\n%d PASS / %d FAIL" % (_pass, _fail))
import sys
sys.exit(1 if _fail else 0)
