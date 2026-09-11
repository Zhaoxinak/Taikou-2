# -*- coding: utf-8 -*-
PROVINCE_NAMES = [
    "北陆奥", "陆奥", "出羽", "南陆奥", "上野", "下野", "常陆", "房总", "武藏", "相模伊豆",
    "甲斐", "信浓", "越后", "骏河", "远江", "三河", "尾张", "美浓", "伊势", "越中",
    "能登", "加贺", "越前若狭", "北近江", "南近江", "大和伊贺", "山城", "丹波丹后", "摄津",
    "河内和泉", "纪伊", "播磨但马", "因幡伯耆", "出云石见", "备前美作", "备中备后", "安艺",
    "周防长门", "阿波", "赞岐", "伊予", "土佐", "丰前", "筑前筑后", "肥前", "丰后",
    "肥后", "日向", "萨摩大隅",
]
mem = open("scripts/_unpacked_mem.bin", "rb").read()
raw = mem[0x50bf48 - 0x400000:0x50bf48 - 0x400000 + 63]
bs = open("Taikou2 Original/BSDATA1.TR2", "rb").read()
STRIDE = 59

def name(i):
    r = bs[i * STRIDE:(i + 1) * STRIDE]
    return (
        r[0:7].split(b"\x00")[0].decode("gbk", "replace")
        + r[7:14].split(b"\x00")[0].decode("gbk", "replace")
    )

lines = []
for i in [13, 19, 199, 257, 304, 112, 500, 1, 100, 364, 230]:
    r = bs[i * STRIDE:(i + 1) * STRIDE]
    idx = r[0x2b]
    prov = raw[idx]
    pf = r[0x30]
    pfn = PROVINCE_NAMES[pf] if pf < 49 else str(pf)
    lines.append(f"{name(i)}: 1f={idx} ->{PROVINCE_NAMES[prov]}({prov}) field国={pfn}")

clans = {}
for i in range(700):
    r = bs[i * STRIDE:(i + 1) * STRIDE]
    sur = r[0:7].split(b"\x00")[0].decode("gbk", "replace")
    if sur.startswith("姓"):
        continue
    idx = r[0x2b]
    prov = raw[idx]
    clans.setdefault(sur, set()).add((idx, PROVINCE_NAMES[prov]))

for sur in ["织田", "武田", "德川", "上杉", "毛利", "岛津", "北条", "伊达", "朝仓", "三好", "真田"]:
    if sur in clans:
        lines.append(f"{sur}: {sorted(clans[sur])}")

text = "\n".join(lines)
open("scripts/_scratch/_1f_geo.txt", "w", encoding="utf-8").write(text)
print(text)
