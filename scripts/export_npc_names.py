#!/usr/bin/env python3
# export_npc_names.py — 导出《太阁立志传2》评定対象名表（NPC 名表）
#
# 权威来源：scripts/council_ref.py（0x49c2b0 対象ID→名称 四段路由，stride 7）
#   特殊 NPC (id 1000..1999) -> 0x5077B0 + (id-1000)*7
#   一般 NPC (id 3000+)       -> 0x507978 + (id-3000)*7
#   （id 2000..2999 为运行时指针 dword[0x506c54]，无静态名表 → 不导出）
# 每条目 7 字节，内联以 \x00 结尾的 C 字符串；编码经实测为 GBK/gb18030
#   （cp932 解码为半角片假名乱码，已排除）。
#
# 导出纯净度（本脚本核心难点）：
#   名表为「评定対象名」连续数组，前缀为密集的真实名（历史人物/职业/信件/宝物/
#   官位/建筑/关系），其后紧接的是**其它数据结构**（调色板/查找表/指针区），
#   这些字节在 gb18030 下恰好能解码成零散汉字/符号（如 踗/挢/䎬/吏/E/>H/浇B），
#   并非真实名。三层过滤确保只导出真实名：
#     ① 必须是 7 字节单元内含 0x00 终止符（真正的 C 字符串单元）；
#     ② is_name：去空白后 1..6 字，无控制符/PUA(U+E000~U+F8FF)/\ufffd，
#        禁止任何 Latin 字母（原版名表纯 CJK/假名/全角，绝无拉丁字母），
#        且至少含 1 个 CJK 统一表意/扩展A/假名/全角字符；
#     ③ 孤立滤除：候选须在 [id-5, id+5] 窗口内 ≥3 个有效邻居（否则为
#        真实名块之外的零散伪名，如孤立的 踗/挢/E/>H），密度保证只保留真名块。
#   调用方对缺失/未导出的 id 回退 "NPC{id}"（与原版空槽行为一致）。
#
# 用法：python scripts/export_npc_names.py  → 写 data/npc_names.json

import json
import os

BASE = 0x400000
HERE = os.path.dirname(os.path.abspath(__file__))
MEM_PATH = os.path.join(HERE, "_unpacked_mem.bin")
OUT_PATH = os.path.join(HERE, "..", "data", "npc_names.json")

MEM = open(MEM_PATH, "rb").read()
SZ = len(MEM)

NAME_TAB_MID = 0x5077B0   # id 1000..1999
NAME_TAB_HI = 0x507978    # id 3000+
NAME_STRIDE = 7

MID_LO, MID_HI = 1000, 1999
GEN_LO, GEN_HI = 3000, 3999

WIN = 5          # 孤立滤除窗口半径
WIN_MIN = 3      # 窗口内最少有效邻居数（含自身）


def rec_bytes(va: int) -> bytes:
    o = va - BASE
    if o < 0 or o + NAME_STRIDE > SZ:
        return b""
    return MEM[o:o + NAME_STRIDE]


def cstr(b: bytes):
    """仅当 7 字节单元内含 0x00 终止符时返回解码串，否则 None（非 C 字符串单元）。"""
    i = b.find(0)
    if i < 0:
        return None
    return b[:i].decode("gb18030", "replace")


def is_name(nm: str) -> bool:
    if not nm:
        return False
    nm = nm.strip()
    if not nm or len(nm) > 6:        # stride 7 内联，最多 6 字符 + \0
        return False
    if "\ufffd" in nm:               # 残留非文本字节
        return False
    has_cjk = False
    for ch in nm:
        o = ord(ch)
        if o < 0x20 or o == 0x7F:    # 控制字符
            return False
        if 0xE000 <= o <= 0xF8FF:    # 私有区（PUA）伪名
            return False
        if (0x41 <= o <= 0x5A) or (0x61 <= o <= 0x7A):  # Latin 字母（原版名表无）
            return False
        if 0x4E00 <= o <= 0x9FFF:    # CJK 统一表意
            has_cjk = True
        elif 0x3400 <= o <= 0x4DBF:  # CJK 扩展 A
            has_cjk = True
        elif 0x30A0 <= o <= 0x30FF:  # 片假名
            has_cjk = True
        elif 0x3040 <= o <= 0x309F:  # 平假名
            has_cjk = True
        elif 0xFF00 <= o <= 0xFFEF:  # 全角形式
            has_cjk = True
    return has_cjk


def collect(base: int, lo: int, hi: int) -> dict:
    # 第一遍：候选（含终止符且 is_name 通过）
    cand = {}
    for i in range(lo, hi + 1):
        b = rec_bytes(base + (i - lo) * NAME_STRIDE)
        nm = cstr(b)
        if nm is not None and is_name(nm):
            cand[i] = nm
    # 第二遍：孤立滤除（窗口内有效邻居不足则丢弃）
    out = {}
    for i in cand:
        cnt = sum(1 for j in range(i - WIN, i + WIN + 1) if j in cand)
        if cnt >= WIN_MIN:
            out[i] = cand[i]
    return out


def main() -> None:
    special = collect(NAME_TAB_MID, MID_LO, MID_HI)
    generic = collect(NAME_TAB_HI, GEN_LO, GEN_HI)
    mids = sorted(special)
    gens = sorted(generic)
    mspan = "%d..%d" % (mids[0], mids[-1]) if mids else "-"
    gspan = "%d..%d" % (gens[0], gens[-1]) if gens else "-"
    out = {
        "meta": {
            "source": "太阁立志传2 (TAIK2W95) 脱壳映像 scripts/_unpacked_mem.bin",
            "encoding": "gb18030",
            "router": "0x49c2b0 対象ID→名称 四段路由（council_ref.py）",
            "special_base": NAME_TAB_MID,
            "special_stride": NAME_STRIDE,
            "special_range": "id 1000..1999（特殊NPC/历史人物/南蛮传教士/信件物品等）",
            "generic_base": NAME_TAB_HI,
            "generic_stride": NAME_STRIDE,
            "generic_range": "id 3000..3999（一般NPC/职业/信件/宝物/官位/建筑/关系等；2000..2999 为运行时指针无静态名）",
            "filters": "7字节内含0x00终止符 + is_name(纯CJK/假名/全角,禁Latin/PUA/ufffd/控制符) + 孤立滤除(±5窗口≥3邻居)",
            "note": "1:1 复刻原版 target_name 真实名块；空/残留/数据区伪名不导出，调用方对缺失 id 回退 'NPC{id}'",
            "special_span": mspan,
            "generic_span": gspan,
        },
        "special": {str(k): v for k, v in sorted(special.items())},
        "generic": {str(k): v for k, v in sorted(generic.items())},
    }
    os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=0)
    print("导出完成：special=%d(%s) generic=%d(%s) → %s"
          % (len(special), mspan, len(generic), gspan, OUT_PATH))


if __name__ == "__main__":
    main()
