#!/usr/bin/env python3
"""从社区城名表生成 scripts/castle_names.json（居城代码 = 单字节 0x00–0xC7）。"""
import json
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "scripts", "castle_names.json")

# 来源：jcku.com / 星虎论坛 居城参数一览（太阁立志传2）
CASTLE_RAW = (
    "00三户01八户02弘前03米泽04岩出山05登米06白石07桑折08山形09横手"
    "0A鲑延0B鹤冈0C黑川0D二本松0E须贺川0F厩桥10沼田11箕轮12松井田13馆林"
    "14宇都宫15唐泽山16小山17太田18水户19小田1A国府台1B结1C久留里1D稻村"
    "1E河越1F忍20钵形21江户22泷川23小田原24玉绳25津久井26三浦27韭山"
    "28踯躅崎29下山2A岩殿2B韭崎2C海津2D饭山2E小诸2F木曾福岛30高远"
    "31饭田32春日山33本庄34新发田35枥尾36骏府37深泽38兴泽39花泽3A滨松"
    "3B二俁3C挂川3D高天神3E冈崎3F长篠40野田41吉田42清洲43鸣海44小牧山"
    "45犬山46守山47那古野48稻叶山49墨俣4A大垣4B曾根4C岩村4D北方4E安浓津"
    "4F长岛50桑名51伊势龟山52大河内53鸟羽54富山55鱼津56七尾57金泽"
    "58小松59大圣寺5A一乘谷5B北之庄5C大野5D府中5E金崎5F小滨60小谷"
    "61横山62大沟63佐和山64今滨65观音寺66目加田/安土67长光寺68日野"
    "69坂本6A大和郡山6B信贵山6C多闻6D伊贺上野6E高取6F二条70朽木谷"
    "71槙岛72胜龙寺73八上74宫津75园部76福知山77丹波龟山78芥川79高槻"
    "7A茨木7B伊丹7C本愿寺/大阪7D尼崎7E花隗7F饭盛80高屋81岸和田"
    "82杂贺83根来84三木85出石86竹田87御着88姬路89鱼住8A上月8B鸟取"
    "8C羽衣石8D月山富田8E三刀屋8F温汤90津和野91冈山92三星93砥石山"
    "94沼95备中高松96甲山97松山98神边99吉田郡山9A安艺高山9B银山"
    "9C樱尾9D山口9E岩国9F胜山A0胜瑞A1抚养A2十河A3多度津A4汤筑"
    "A5高冈A6大洲A7冈丰A8安艺A9浦户AA中村AB小仓AC中津AD秋月"
    "AE宗像AF立花B0久留米B1柳川B2佐嘉B3势福寺B4大村B5平户B6府内"
    "B7高田B8冈B9佐伯BA丹生岛BB人吉BC永野BD隗府BE八代BF都于郡"
    "C0县C1高C2沃肥C3鹿儿岛C4大口C5加治木C6伊集院C7大隅高山"
)


def parse_castles() -> dict[int, str]:
    names: dict[int, str] = {}
    for m in re.finditer(r"([0-9A-F]{2})([^0-9A-F/]+(?:/[^0-9A-F]+)?)", CASTLE_RAW):
        names[int(m.group(1), 16)] = m.group(2)
    return names


def display_name(base: str) -> str:
    if "/" in base:
        base = base.split("/")[-1]
    if base.endswith("城"):
        return base
    return base + "城"


def main() -> None:
    names = parse_castles()
    castles = []
    for code in range(0xC8):
        base = names.get(code, f"城{code}")
        castles.append({
            "id": code,
            "hex": f"{code:02X}",
            "name": base,
            "display": display_name(base),
        })
    out = {
        "source": "community castle table (jcku / 星虎论坛)",
        "count": len(castles),
        "castles": castles,
    }
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print(f"OK {len(castles)} castles -> {OUT}")


if __name__ == "__main__":
    main()
