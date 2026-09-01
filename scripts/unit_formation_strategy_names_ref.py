#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
#19 兵种/阵形/计略 中文名 —— 静态定位最终实证 (续211 配套)

结论：
  兵种名  : 静态定长名表 @0x50bfe8, stride 5, 3 个有名类别
            cls0=步兵(b2 bd b1 f8) / cls1=骑兵(c6 ef b1 f8) / cls2=洋枪(d1 f3 c7 b9)
            cls3=城守备 (category map 0x50bfd0 实证, 但其名表槽 @0x50bff7 首字节为 0x00 → 无显示名)
            访问器 0x43e150 : lea eax,[eax+eax*4+0x50bfe8]  (cls&3 → 名指针)
  计略名  : 静态定长名表 @0x5032d8, 每目 7B (2汉字 + 全角空格 A1A1 + 2汉字 + 0x00), 共 11 目
            鼓舞/伏兵/伪兵/谣言/火计/开城/挑衅/落石/牵制/修复/填埋
            handler 指针表 @0x503328, 11×4B → 0x435530..0x437c90
            访问器 0x42f428 : 循环 name=0x5032d8+idx*7, handler=0x503328+idx*4
  阵形名  : 结论性缺失 —— 全镜像 串扫描(concatenated GBK / 全角空格 interleaved / UTF-16LE) 与
            已解码 MSGX(MESSAGE1-4.LZW + HEXMES.LZW) 文本表 均 0 命中日式/中式的 9 阵形名
            (鹤翼/鱼鳞/锋矢/偃月/方圆/雁行/长蛇/衡轭/磐石 及日文变体)。
            Taikou2 合战无玩家可见阵形名；byte[p+4](0..3) 是内部布阵编号，
            经相克矩阵 0x5031d0 产布阵变体 fi=[1,3,0,2][(B-A)mod4] (见 GAME_DATA_SPEC §3.10.2/§3.11.3)。

★ 推翻旧假设：兵种/阵形名「运行期从已解码数据表构造、须 emu 抓渲染路径」(旧 #19 待办表述) 不成立 ——
  兵种名是纯静态字串表；阵形名是压根不存在(非运行期构造)。

运行: python3 unit_formation_strategy_names_ref.py
依赖: scripts/_unpacked_mem.bin (2MB 解包映像, base 0x400000)
"""
import struct, sys

BASE = 0x400000
IMG  = "scripts/_unpacked_mem.bin"

UNIT_BASE   = 0x50bfe8   # 兵种名表基址, stride 5
UNIT_STRIDE = 5
UNIT_NAMES  = {0: "步兵", 1: "骑兵", 2: "洋枪"}   # cls&3 → 显示名 (cls3 城守备 无显示名)
UNIT_BYTES  = {0: b"\xb2\xbd\xb1\xf8", 1: b"\xc6\xef\xb1\xf8", 2: b"\xd1\xf3\xc7\xb9"}
CATMAP      = 0x50bfd0   # 24B 兵种类别映射表, 值 0..3

STRAT_BASE  = 0x5032d8   # 计略名表基址, stride 7 (interleaved: 字+ A1A1 + 字 + 0x00)
STRAT_STRIDE= 7
STRAT_NAMES = ["鼓舞","伏兵","伪兵","谣言","火计","开城","挑衅","落石","牵制","修复","填埋"]
STRAT_HANDLERS = 0x503328  # 11×4B handler 指针表

FORMATION_NAMES = ["鹤翼","鱼鳞","锋矢","偃月","方圆","雁行","长蛇","衡轭","磐石",
                   "鶴翼","魚鱗","鋒矢","方円","長蛇","衡軛"]

def load():
    with open(IMG, "rb") as f:
        return f.read()

def decode_gbk(raw):
    try:
        return raw.decode("gbk")
    except Exception:
        return raw.hex()

def test_unit_names(data):
    ok = True
    for cls, name in UNIT_NAMES.items():
        va = UNIT_BASE + cls * UNIT_STRIDE
        raw = data[va-BASE : va-BASE+4]
        got = decode_gbk(raw)
        exp = UNIT_BYTES[cls]
        cond = (raw == exp) and (data[va+4-BASE] == 0)
        print("[兵种] cls%d @%06x 期望=%s 实读=%s(%s) %s" % (
            cls, va, name, got, raw.hex(), "OK" if cond else "FAIL"))
        ok = ok and cond
    # cls3 名表槽首字节须为 0x00 (无显示名) —— 与 category map 的 cls3 存在性对照
    va3 = UNIT_BASE + 3 * UNIT_STRIDE
    cls3_empty = (data[va3-BASE] == 0x00)
    print("[兵种] cls3(城守备) 名表槽 @%06x 首字节=0x%02x %s" % (
        va3, data[va3-BASE], "OK(空名/无显示)" if cls3_empty else "FAIL"))
    ok = ok and cls3_empty
    # category map 0x50bfd0 : 4 类 (0=步兵,1=骑兵,2=洋枪,3=城守备)
    cat = data[CATMAP-BASE : CATMAP-BASE+24]
    expect_cat = [3,3,3,3, 0,0,0,0, 1,1,1,1,1,1,1,1, 2,2,2,2, 3,3,3,3]
    cat_ok = (list(cat) == expect_cat)
    print("[兵种] 类别映射表 @%s %s" % (hex(CATMAP), "OK" if cat_ok else "FAIL"))
    ok = ok and cat_ok
    # accessor 0x43e150 引用基址 0x50bfe8
    ref = struct.pack("<I", UNIT_BASE)
    found = data.find(ref)
    acc_ok = (found >= 0)
    print("[兵种] 基址 0x50bfe8 被引用 @%06x %s" % (BASE+found if found>=0 else 0, "OK" if acc_ok else "FAIL"))
    ok = ok and acc_ok
    return ok

def test_strat_names(data):
    ok = True
    for idx, name in enumerate(STRAT_NAMES):
        va = STRAT_BASE + idx * STRAT_STRIDE
        raw = data[va-BASE : va-BASE+7]
        # interleaved: c1(2B) A1 A1 c2(2B) 00
        cond = (raw[2]==0xa1 and raw[3]==0xa1 and raw[6]==0 and
                decode_gbk(raw[:2])+decode_gbk(raw[4:6]) == name)
        print("[计略] [%d] @%06x 期望=%s 实读=%s %s" % (
            idx, va, name, decode_gbk(raw[:2])+decode_gbk(raw[4:6]), "OK" if cond else "FAIL"))
        ok = ok and cond
    # handler 指针表 11×4B, 全部落在代码段 0x43xxxx/0x4x 范围
    n = len(STRAT_NAMES)
    hptr = data[STRAT_HANDLERS-BASE : STRAT_HANDLERS-BASE + n*4]
    handlers = [struct.unpack_from("<I", hptr, i*4)[0] for i in range(n)]
    h_ok = all(0x400000 <= h < 0x500000 for h in handlers)
    print("[计略] handler 表 @%s 11 项 全部代码段 %s : %s" % (
        hex(STRAT_HANDLERS), "OK" if h_ok else "FAIL",
        " ".join("%06x"%h for h in handlers[:4])+" .."))
    ok = ok and h_ok
    # 名表基址 0x5032d8 被访问器 0x42f428 引用
    ref = struct.pack("<I", STRAT_BASE)
    found = data.find(ref)
    acc_ok = (found >= 0)
    print("[计略] 名表基址 0x5032d8 被引用 @%06x %s" % (BASE+found if found>=0 else 0, "OK" if acc_ok else "FAIL"))
    ok = ok and acc_ok
    return ok

def test_formation_absent(data):
    """阵形名在全镜像 0 命中 (结论性缺失)"""
    hits = 0
    for fn in FORMATION_NAMES:
        try:
            b = fn.encode("gbk")
        except Exception:
            continue
        if data.find(b) >= 0:
            hits += 1
            print("[阵形] 命中 %s (不应出现)" % fn)
    # interleaved 全角空格形式也须 0 命中
    import re
    pat = re.compile(rb'([\x81-\xfe][\x40-\xfe])\xa1\xa1([\x81-\xfe][\x40-\xfe])\x00')
    inter = set()
    for m in pat.finditer(data):
        try:
            inter.add(m.group(1).decode("gbk")+m.group(2).decode("gbk"))
        except Exception:
            pass
    inter_hit = any(f in inter for f in FORMATION_NAMES)
    ok = (hits == 0) and (not inter_hit)
    print("[阵形] 9 阵形名 concatenated GBK 命中=%d, interleaved 命中=%s → %s" % (
        hits, inter_hit, "OK(结论性缺失)" if ok else "FAIL(找到则改写)"))
    return ok

def main():
    data = load()
    print("=== #19 兵种/阵形/计略 中文名 静态实证 ===\n")
    r1 = test_unit_names(data)
    print()
    r2 = test_strat_names(data)
    print()
    r3 = test_formation_absent(data)
    print()
    allok = r1 and r2 and r3
    print("RESULT: %s" % ("ALL PASS ✅" if allok else "FAIL ❌"))
    sys.exit(0 if allok else 1)

if __name__ == "__main__":
    main()
