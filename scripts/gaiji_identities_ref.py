#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GAIJI.TR2 外字身份表 —— 自校验参考实现

═══════════════════════════════════════════════════════════════════════
结论：15 个实字形身份全部定死；其中 5 槽被 BSDATA 姓名引用，其余 10 槽
      字形可认但中文版文本/姓名未引用（日版遗留外字集）。第 16 槽终止空位。

  A140 堯     新认·未用   位图≈堯（三土+兀）；MSGX/BSDATA 0 引用
  A141 長*    已认·在用   長宗我部 48×16 切格 #0（*非独立整字）
  A142 香*    已认·在用   香宗我部 切格 #0
  A143 宗我*  已认·在用   長/香宗我部 切格 #1（跨「宗」「我」）
  A144 部*    已认·在用   長/香宗我部 切格 #2
  A145 籠     新认·未用   竹冠+龍；位图着墨最高之一
  A146 頸     新认·未用   左巠右頁
  A147 垪     已认·在用   #182 垪和氏续
  A148 惣     新认·未用   上「物」略形 + 下心
  A149 揆     新认·未用   扌+癸（一揆用字）
  A14A 梟     新认·未用   上鳥略形 + 下木
  A14B 瓊     新认·未用   王+夐
  A14C 絆     新认·未用   糸+半
  A14D 渚     新认·未用   氵+者
  A14E 戌     新认·未用   戈类地支「戌」（非成/戍：中腹封闭 #.####）
  A14F —     终止空位    源码 0x7721、位图全 0

引用扫描（本续）：
  · BSDATA1/2：仅 A141..A144、A147（5 条武将姓）
  · MSGX 正文（MESSAGE1-4 + HEXMES，按指针表取串）：外字码位 0 命中
  · 解压后 LZW 里偶发 A14x 字节落在偏移表，非文本
═══════════════════════════════════════════════════════════════════════
"""
from __future__ import annotations

import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
ORIG = os.path.join(ROOT, "Taikou2 Original")

sys.path.insert(0, HERE)
from real_assets import ls11_decompress  # noqa: E402

PASS = 0
FAIL = 0


def check(name: str, cond: bool, extra: str = "") -> None:
    global PASS, FAIL
    if cond:
        PASS += 1
        print("  [OK]   %s" % name)
    else:
        FAIL += 1
        print("  [FAIL] %s   %s" % (name, extra))


# ── 身份权威表（本脚本对外契约）──────────────────────────────────────
# status: used = BSDATA 姓名引用；unused = 字形可认但中文数据未引用；
#         terminator = 第 16 槽空位
# role:   compound_slice = 四字姓横向连排切格；standalone = 独立汉字
IDENTITIES = {
    0xA140: dict(char="堯", status="unused", role="standalone",
                 note="新认；三土+兀，系统宋体 IoU 峰值"),
    0xA141: dict(char="長", status="used", role="compound_slice",
                 note="已认；長宗我部 切格0（右4列与 A142 相同=连排伪影）"),
    0xA142: dict(char="香", status="used", role="compound_slice",
                 note="已认；香宗我部 切格0"),
    0xA143: dict(char="宗我", status="used", role="compound_slice",
                 note="已认；切格1，横跨「宗」「我」约各半"),
    0xA144: dict(char="部", status="used", role="compound_slice",
                 note="已认；切格2"),
    0xA145: dict(char="籠", status="unused", role="standalone",
                 note="新认；竹冠+龍"),
    0xA146: dict(char="頸", status="unused", role="standalone",
                 note="新认；巠+頁"),
    0xA147: dict(char="垪", status="used", role="standalone",
                 note="已认；#182 垪和氏续（+GBK『和』）"),
    0xA148: dict(char="惣", status="unused", role="standalone",
                 note="新认；上物略形+下心"),
    0xA149: dict(char="揆", status="unused", role="standalone",
                 note="新认；扌+癸"),
    0xA14A: dict(char="梟", status="unused", role="standalone",
                 note="新认；鳥略形+木"),
    0xA14B: dict(char="瓊", status="unused", role="standalone",
                 note="新认；王+夐"),
    0xA14C: dict(char="絆", status="unused", role="standalone",
                 note="新认；糸+半"),
    0xA14D: dict(char="渚", status="unused", role="standalone",
                 note="新认；氵+者"),
    0xA14E: dict(char="戌", status="unused", role="standalone",
                 note="新认；地支戌（中腹封闭，别于成/戍）"),
    0xA14F: dict(char=None, status="terminator", role="empty",
                 note="终止记录：源码 0x7721、位图全 0"),
}


def load_gaiji():
    raw = open(os.path.join(ORIG, "GAIJI.TR2"), "rb").read()
    recs = []
    for i in range(16):
        off = i * 34
        code = struct.unpack_from("<H", raw, off)[0]
        bm = raw[off + 2:off + 34]
        recs.append(dict(idx=i, slot=0xA140 + i, src=code, bm=bm))
    return raw, recs


def rows(bm):
    return [(bm[2 * r] << 8) | bm[2 * r + 1] for r in range(16)]


def grid(bm):
    g = [[0] * 16 for _ in range(16)]
    for y, v in enumerate(rows(bm)):
        for x in range(16):
            g[y][x] = 1 if (v & (0x8000 >> x)) else 0
    return g


def ink(bm):
    return sum(bin(x).count("1") for x in bm)


def parse_msgx(dec):
    assert dec[:4] == b"MSGX"
    n = struct.unpack_from("<H", dec, 4)[0]
    ptrs = [struct.unpack_from("<I", dec, 6 + i * 4)[0] for i in range(n)]
    ptrs.append(len(dec))
    out = []
    for i in range(n):
        seg = dec[ptrs[i]:ptrs[i + 1]]
        z = seg.find(b"\x00")
        out.append(seg if z < 0 else seg[:z])
    return out


def seg_has_gaiji(seg):
    i = 0
    while i + 1 < len(seg):
        code = (seg[i] << 8) | seg[i + 1]
        if 0xA140 <= code <= 0xA14F:
            return True
        if 0x81 <= seg[i] <= 0xFE:
            i += 2
        else:
            i += 1
    return False


def bsdata_gaiji_usage(path):
    """Return {rec_idx: (surname_codes_tuple, given_gbk)} for records using gaiji."""
    data = open(path, "rb").read()
    stride = 59
    nrec = len(data) // stride
    out = {}
    for i in range(nrec):
        rec = data[i * stride:(i + 1) * stride]
        sur = rec[0:7].split(b"\x00")[0]
        codes = []
        for k in range(0, len(sur) - 1, 2):
            codes.append((sur[k] << 8) | sur[k + 1])
        if any(0xA140 <= c <= 0xA14F for c in codes):
            giv = rec[7:14].split(b"\x00")[0]
            try:
                gname = giv.decode("gbk")
            except Exception:
                gname = giv.hex()
            out[i] = (tuple(codes), gname)
    return out


# ══════════════════════════════════════════════════════════════════
print("\n[A] 身份表完整性")
check("A0 恰 16 个码位 A140..A14F",
      list(IDENTITIES.keys()) == list(range(0xA140, 0xA150)))
check("A1 15 实字 + 1 终止",
      sum(1 for v in IDENTITIES.values() if v["status"] != "terminator") == 15
      and IDENTITIES[0xA14F]["status"] == "terminator")
check("A2 已认在用恰 5 槽（A141-A144,A147）",
      sorted(c for c, v in IDENTITIES.items() if v["status"] == "used")
      == [0xA141, 0xA142, 0xA143, 0xA144, 0xA147])
check("A3 新认未用恰 10 槽",
      sorted(c for c, v in IDENTITIES.items() if v["status"] == "unused")
      == [0xA140, 0xA145, 0xA146, 0xA148, 0xA149, 0xA14A, 0xA14B, 0xA14C,
          0xA14D, 0xA14E])
check("A4 独立汉字身份均可 GBK 编码（证明劫持因字体/姓宽，非 GBK 缺码）",
      all(IDENTITIES[c]["char"].encode("gbk")
          for c in IDENTITIES
          if IDENTITIES[c]["role"] == "standalone" and IDENTITIES[c]["char"]))

# ══════════════════════════════════════════════════════════════════
print("\n[B] 文件几何 + 已知连排闭环（续200）")
raw, recs = load_gaiji()
check("B0 文件 544 B = 16×34", len(raw) == 544)
check("B1 前 15 源码 0x7670+i",
      [r["src"] for r in recs[:15]] == [0x7670 + i for i in range(15)])
check("B2 A14F 终止：源码 0x7721 且位图全 0",
      recs[15]["src"] == 0x7721 and recs[15]["bm"] == b"\x00" * 32)
check("B3 A141/A142 右 4 列逐行相同（连排伪影）",
      [v & 0xF for v in rows(recs[1]["bm"])]
      == [v & 0xF for v in rows(recs[2]["bm"])])
check("B4 A141/A142 左 12 列不同（長 vs 香）",
      [v >> 4 for v in rows(recs[1]["bm"])]
      != [v >> 4 for v in rows(recs[2]["bm"])])

# ══════════════════════════════════════════════════════════════════
print("\n[C] BSDATA 引用（唯五条）")
u1 = bsdata_gaiji_usage(os.path.join(ORIG, "BSDATA1.TR2"))
u2 = bsdata_gaiji_usage(os.path.join(ORIG, "BSDATA2.TR2"))
check("C1 两剧本外字记录集合一致且恰 5 条",
      u1 == u2 and set(u1) == {182, 557, 568, 581, 583},
      "u1=%s" % sorted(u1))
check("C2 557/581/583 = A141+A143+A144 + 元亲/信亲/盛亲",
      all(u1[i][0] == (0xA141, 0xA143, 0xA144) for i in (557, 581, 583))
      and [u1[i][1] for i in (557, 581, 583)] == ["元亲", "信亲", "盛亲"])
check("C3 568 = A142+A143+A144 + 亲泰",
      u1[568] == ((0xA142, 0xA143, 0xA144), "亲泰"))
check("C4 182 = A147 + GBK『和』 + 氏续",
      u1[182][0] == (0xA147, 0xBACD) and u1[182][1] == "氏续")
used_codes = set()
for codes, _ in u1.values():
    used_codes.update(c for c in codes if 0xA140 <= c <= 0xA14F)
check("C5 BSDATA 实际触碰码位 == {A141,A142,A143,A144,A147}",
      used_codes == {0xA141, 0xA142, 0xA143, 0xA144, 0xA147},
      str([hex(x) for x in sorted(used_codes)]))

# ══════════════════════════════════════════════════════════════════
print("\n[D] MSGX 正文零外字")
msg_hits = 0
msg_total = 0
for fn in ("MESSAGE1.LZW", "MESSAGE2.LZW", "MESSAGE3.LZW",
           "MESSAGE4.LZW", "HEXMES.LZW"):
    dec = ls11_decompress(open(os.path.join(ORIG, fn), "rb").read())
    for seg in parse_msgx(dec):
        msg_total += 1
        if seg_has_gaiji(seg):
            msg_hits += 1
check("D1 MESSAGE1-4+HEXMES 全部 %d 条正文不含 A140..A14F" % msg_total,
      msg_hits == 0 and msg_total == 1735 + 1559 + 1876 + 1041 + 283,
      "hits=%d total=%d" % (msg_hits, msg_total))

# ══════════════════════════════════════════════════════════════════
print("\n[E] 新认字形结构指纹（目视定死的可机检特征）")
g = {r["slot"]: grid(r["bm"]) for r in recs}
ink_map = {r["slot"]: ink(r["bm"]) for r in recs}

check("E0 15 实字着墨 ∈ [50,110]",
      all(50 <= ink_map[0xA140 + i] <= 110 for i in range(15)),
      str([ink_map[0xA140 + i] for i in range(15)]))

# A140 堯：顶部有孤立中轴竖 + 底部两撇腿（右下着墨）
check("E1 A140 堯：ink=89 且右 4 列着墨 ≥20（兀腿偏右）",
      ink_map[0xA140] == 89 and sum(g[0xA140][y][x] for y in range(16)
                                     for x in range(12, 16)) >= 20)

# A145 籠：着墨最密之一，顶行有双峰（竹冠）
top = g[0xA145][1]
check("E2 A145 籠：ink=104（15 槽最高）且第 2 行左右双峰",
      ink_map[0xA145] == 104
      and sum(top[:8]) >= 4 and sum(top[8:]) >= 4)

# A146 頸：右半有頁的三横箱
right_boxes = sum(g[0xA146][y][x] for y in range(4, 11) for x in range(8, 15))
check("E3 A146 頸：右半中段着墨 ≥20（頁）", right_boxes >= 20)

# A147 垪：左土右并 — 左列有竖笔
check("E4 A147 垪：ink=67 且左 4 列有竖画（土）",
      ink_map[0xA147] == 67
      and sum(g[0xA147][y][3] for y in range(16)) >= 8)

# A148 惣：底行居中 ##### = 心底
bot = "".join("#" if g[0xA148][15][x] else "." for x in range(16))
check("E5 A148 惣：底行含居中心底 '#####'",
      "#####" in bot and ink_map[0xA148] == 66, bot)

# A149 揆：左列 dense 扌竖
check("E6 A149 揆：列3 连续竖画 ≥10（扌）",
      sum(g[0xA149][y][3] for y in range(16)) >= 10)

# A14A 梟：底 4 行着墨高（木）+ 上部封闭三横
check("E7 A14A 梟：ink=93 且底 4 行着墨 ≥25（木）",
      ink_map[0xA14A] == 93
      and sum(g[0xA14A][y][x] for y in range(12, 16) for x in range(16)) >= 25)

# A14B 瓊：左王（列中段多横）+ 高着墨
check("E8 A14B 瓊：ink=97 且左 4 列着墨 ≥15（王旁）",
      ink_map[0xA14B] == 97
      and sum(g[0xA14B][y][x] for y in range(16) for x in range(4)) >= 15)

# A14C 絆：左糸 —— 中下有 ##### 横束
left_join = "".join("#" if g[0xA14C][8][x] else "." for x in range(6))
check("E9 A14C 絆：第 9 行左段含 '#####'（糸束）",
      "#####" in left_join or left_join.count("#") >= 5, left_join)

# A14D 渚：底 5 行三横箱 = 日
day = [sum(g[0xA14D][y]) for y in range(11, 16)]
check("E10 A14D 渚：底 5 行呈 日 箱（高/低/高/低/高）",
      day[0] >= 8 and day[1] <= 4 and day[2] >= 8
      and day[3] <= 4 and day[4] >= 8, str(day))

# A14E 戌：中腹封闭 ###### 段（别于成）
mid = "".join("#" if g[0xA14E][9][x] else "." for x in range(16))
check("E11 A14E 戌：第 10 行含 '####' 封闭腹（戌≠成）",
      "####" in mid and ink_map[0xA14E] == 59, mid)

# ══════════════════════════════════════════════════════════════════
print("\n[F] 契约：身份字符串")
expect = {
    0xA140: "堯", 0xA141: "長", 0xA142: "香", 0xA143: "宗我", 0xA144: "部",
    0xA145: "籠", 0xA146: "頸", 0xA147: "垪", 0xA148: "惣", 0xA149: "揆",
    0xA14A: "梟", 0xA14B: "瓊", 0xA14C: "絆", 0xA14D: "渚", 0xA14E: "戌",
    0xA14F: None,
}
check("F1 15+1 身份字符串与权威表一致",
      {c: IDENTITIES[c]["char"] for c in IDENTITIES} == expect)

# 落盘简表（供主 agent 回填，本脚本不改规格文档）
import json
out = {
    "slots": {
        hex(c): {
            "char": v["char"],
            "status": v["status"],
            "role": v["role"],
            "note": v["note"],
            "ink": ink_map.get(c, 0),
            "src_code": hex(recs[c - 0xA140]["src"]),
        }
        for c, v in IDENTITIES.items()
    },
    "bsdata_refs": {
        str(i): {"surname_codes": [hex(x) for x in codes], "given": name}
        for i, (codes, name) in sorted(u1.items())
    },
    "msgx_gaiji_hits": 0,
}
jsp = os.path.join(HERE, "gaiji_identities.json")
json.dump(out, open(jsp, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
check("F2 写出 scripts/gaiji_identities.json", os.path.exists(jsp))

print("\n" + "=" * 68)
print("RESULT: %d PASS / %d FAIL" % (PASS, FAIL))
print("=" * 68)
if FAIL:
    sys.exit(1)

# 人类可读摘要
print("\n码位身份一览：")
for c in range(0xA140, 0xA150):
    v = IDENTITIES[c]
    ch = v["char"] if v["char"] is not None else "—"
    print("  %04X  %-4s  %-11s  %s" % (c, ch, v["status"], v["note"]))
