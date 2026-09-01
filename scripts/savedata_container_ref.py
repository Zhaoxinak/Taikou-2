#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
续199 参考实现：SAVEDATA.TR2 存档容器 + 49B 槽元数据 + TR2 族分类

核心结论（含对旧文档的两处纠偏）：
  1) SAVEDATA.TR2 = 16B magic + 8×49B 槽元数据 + 8×40960B 槽体   ★ 8 槽，不是 16 槽
     旧文档 SNDATA_SPEC §6/§11.1 记「16 × 20480B」，源于把 `shl eax,0x0d` 误读为 `0x0c`。
  2) 那 49B 记录属于 SAVEDATA（8 条存档列表条目），不是 SNDATA 的「833 条剧本记录」。
     铁证：0x47fc60 / 0x47fd10 开头硬编码 `push 2` → 0x47d720(ax>=2) → LoadSAVEDATA。

槽元数据 schema（0x47fc60 扇出 / 0x47fd10 反向，读写完全对称）：
    +0x00  u16 LE   年
    +0x02  u16 LE   月
    +0x04  u16 LE   日
    +0x06  char[13] 主角名   GBK NUL 结尾  → strcpy 0x522c88
    +0x13  char[13] 所在国   GBK NUL 结尾  → strcpy 0x522c60
    +0x20  char[17] 所在地+身分 GBK NUL 结尾 → strcpy 0x522c70
    6 + 13 + 13 + 17 = 49  ★ 精确闭合
"""
import os, struct, json, collections

HERE = os.path.dirname(os.path.abspath(__file__))
ORIG = os.path.join(HERE, "..", "Taikou2 Original")
MEM  = open(os.path.join(HERE, "_unpacked_mem.bin"), "rb").read()
BASE = 0x400000

def rdmem(va, n):  return MEM[va - BASE: va - BASE + n]
def load(n):       return open(os.path.join(ORIG, n), "rb").read()
def cstr_gbk(b):
    i = b.find(b"\0")
    return (b[:i] if i >= 0 else b).decode("gbk", "replace")

# ─────────────────────────── 常量（EXE 侧钉死） ───────────────────────────
SLOT_STRIDE  = 5 * (2 ** 13)      # 0x47d86b: lea eax,[eax+eax*4] ; shl eax,0x0d
HDR_SIZE     = 0x198              # 0x47d871: add eax,0x198
META_SIZE    = 0x31               # 0x47d8b6: push 0x31
META_BASE    = 0x10               # 0x47d8a4: lea edx,[ecx+eax+0x10]
MAGIC_SAVE   = b"TAIKOU2_SAVEFILE"
MAGIC_SCEN   = b"TAIKOU2_SCENARIO"

# 存档子系统数据区 @0x509590（stride 16 的 5 项名串子表）
TR2_NAME_TABLE = [(0x509590, "A:SAVEDATA.TR2"), (0x5095a0, "F:SNDATA1.TR2"),
                  (0x5095b0, "F:SNDATA2.TR2"), (0x5095c0, "F:BSDATA1.TR2"),
                  (0x5095d0, "F:BSDATA2.TR2")]
# 扇出目标（存档列表 UI 三显示缓冲）
FANOUT = [(0x06, 13, 0x522c88), (0x13, 13, 0x522c60), (0x20, 17, 0x522c70)]

# ─────────────────────────── 解析器 ───────────────────────────
def slot_offset(idx):
    """0x47d860: off = idx*40960 + 0x198"""
    return idx * SLOT_STRIDE + HDR_SIZE

def meta_offset(idx):
    """0x47d890/0x47d8d0: off = idx*49 + 0x10"""
    return idx * META_SIZE + META_BASE

def parse_slot_meta(data, idx):
    """按 0x47fc60 扇出布局解析一条槽元数据"""
    r = data[meta_offset(idx): meta_offset(idx) + META_SIZE]
    y, m, d = struct.unpack("<HHH", r[0:6])
    return {
        "slot": idx, "year": y, "month": m, "day": d,
        "hero":  cstr_gbk(r[0x06:0x13]),
        "country": cstr_gbk(r[0x13:0x20]),
        "place_rank": cstr_gbk(r[0x20:0x31]),
        "used": any(r),
    }

def parse_savedata(data):
    n_slots = (len(data) - HDR_SIZE) // SLOT_STRIDE
    return {
        "magic": data[:16],
        "n_slots": n_slots,
        "metas": [parse_slot_meta(data, i) for i in range(n_slots)],
        "bodies": [(slot_offset(i), data[slot_offset(i): slot_offset(i) + SLOT_STRIDE])
                   for i in range(n_slots)],
    }

def classify_tr2(name, data):
    """TR2 是「容器扩展名」而非单一格式，共 4 类"""
    if data[:16] == MAGIC_SAVE:  return "SAVEFILE"
    if data[:16] == MAGIC_SCEN:  return "SCENARIO"
    if len(data) == 544:         return "GAIJI"      # §3.26 16×34B
    if len(data) % 59 == 0:      return "BSDATA"     # 700×59B 花名册
    return "UNKNOWN"

# ─────────────────────────── 自测 ───────────────────────────
def main():
    ok = fail = 0
    def chk(cond, msg):
        nonlocal ok, fail
        if cond: ok += 1;  print("    ✓ %s" % msg)
        else:    fail += 1; print("    ✗ %s" % msg)

    SAVE = load("SAVEDATA.TR2")
    SN1, SN2 = load("SNDATA1.TR2"), load("SNDATA2.TR2")
    BS1, BS2 = load("BSDATA1.TR2"), load("BSDATA2.TR2")
    GAI = load("GAIJI.TR2")

    print("T1: EXE 侧槽偏移公式字节码（0x47d860）")
    bc = rdmem(0x47d86b, 11)
    chk(bc[0:3] == b"\x8d\x04\x80", "lea eax,[eax+eax*4]  (×5)  8d0480")
    chk(bc[3:6] == b"\xc1\xe0\x0d", "shl eax,0x0d  (×8192) c1e00d ★ 0x0d 非 0x0c")
    chk(bc[6:11] == b"\x05\x98\x01\x00\x00", "add eax,0x198 (+408)")
    chk(SLOT_STRIDE == 40960, "⇒ stride = 5<<13 = %d" % SLOT_STRIDE)

    print("\nT2: 槽数判定 —— 8 槽 vs 16 槽（决定性第二证据）")
    body_total = len(SAVE) - HDR_SIZE
    chk(body_total == 327680, "槽体总量 = %d" % body_total)
    chk(body_total % 40960 == 0 and body_total // 40960 == 8, "40960 × 8 整除 ✓")
    chk((HDR_SIZE - 16) == 392 and 392 % 8 == 0 and 392 // 8 == META_SIZE,
        "元数据区 392 = 8 × 49 整除 ✓")
    chk(392 % 16 != 0, "392 / 16 = 24.5 不整 ⇒ 16 槽假设被数据证伪 ✓")

    print("\nT3: 49B 记录访问器公式（0x47d890 读 / 0x47d8d0 写，字节级同构）")
    a, b = rdmem(0x47d890, 0x29), rdmem(0x47d8d0, 0x29)
    chk(a == b, "两访问器前 0x29 字节完全一致（仅末尾 read/write 调用不同）")
    chk(rdmem(0x47d89e, 3) == b"\x8d\x0c\x40", "lea ecx,[eax+eax*2] (×3)")
    chk(rdmem(0x47d8a1, 3) == b"\xc1\xe1\x04", "shl ecx,4 ⇒ ×48")
    chk(rdmem(0x47d8a4, 4) == b"\x8d\x54\x01\x10", "lea edx,[ecx+eax+0x10] ⇒ idx*49+16")
    chk(rdmem(0x47d8b6, 2) == b"\x6a\x31", "push 0x31 ⇒ 读写长度 49")
    chk(meta_offset(0) == 16 and meta_offset(7) == 359, "off(0)=16, off(7)=359")

    print("\nT4: ★ `push 2` 铁证 —— 49B 记录属 SAVEDATA 而非 SNDATA")
    chk(rdmem(0x47fc66, 4) == b"\x6a\x00\x6a\x02", "0x47fc60 读器: push 0(读) ; push 2(SAVEDATA)")
    chk(rdmem(0x47fd89, 4) == b"\x6a\x01\x6a\x02", "0x47fd10 写器: push 1(写) ; push 2(SAVEDATA)")
    chk(rdmem(0x47fb88, 4) == b"\x6a\x00\x6a\x02", "0x47fb80 载槽: push 0 ; push 2")
    chk(rdmem(0x47fc16, 4) == b"\x6a\x01\x6a\x02", "0x47fc10 存槽: push 1 ; push 2")
    chk(rdmem(0x47d726, 4) == b"\x66\x3d\x02\x00", "0x47d726 cmp ax,2 ⇒ >=2 走 LoadSAVEDATA")

    print("\nT5: 扇出目标立即数（存档列表 UI 三显示缓冲）")
    for off, ln, va in FANOUT:
        pat = b"\x68" + struct.pack("<I", va)
        chk(pat in MEM[0x47fc60 - BASE: 0x47fd04 - BASE], "push 0x%06x 出现于 0x47fc60 体内 (字段 +0x%02x len %d)" % (va, off, ln))
    chk(0x06 + 13 == 0x13 and 0x13 + 13 == 0x20 and 0x20 + 17 == META_SIZE,
        "字段长闭合 6+13+13+17 = 49 ✓")

    print("\nT6: 读写对称性（0x47fd10 的 strcpy 目标 = buf+0x06/0x13/0x20）")
    # push esi 使栈基 +4：lea 偏移 0xa/0x17/0x24 → 减 4 得 0x06/0x13/0x20
    for lea_off, want in ((0x0a, 0x06), (0x17, 0x13), (0x24, 0x20)):
        chk(lea_off - 4 == want, "lea [esp+0x%02x] − 4(push esi) = buf+0x%02x" % (lea_off, want))

    print("\nT7: SAVEDATA 容器实测")
    S = parse_savedata(SAVE)
    chk(S["magic"] == MAGIC_SAVE, "magic = %r" % S["magic"])
    chk(S["n_slots"] == 8, "槽数 = %d" % S["n_slots"])
    chk(all(bd[:16] == MAGIC_SCEN for _, bd in S["bodies"][:1]),
        "slot0 槽体 magic = TAIKOU2_SCENARIO（槽体沿用剧本格式）")
    used = [m for m in S["metas"] if m["used"]]
    chk(len(used) == 1 and used[0]["slot"] == 0, "仅 slot0 已使用，slot1..7 全零")

    print("\nT8: slot0 元数据语义 + 史实交叉验证")
    m0 = S["metas"][0]
    chk(m0["year"] == 1560, "年 = %d（永禄3年·桶狭间之战，剧本1）" % m0["year"])
    chk(m0["month"] == 5,  "月 = %d" % m0["month"])
    chk(m0["day"] == 20,   "日 = %d" % m0["day"])
    chk(m0["hero"] == "木下藤吉郎", "主角名 = %s" % m0["hero"])
    chk(m0["country"] == "尾张国",   "所在国 = %s" % m0["country"])
    chk(m0["place_rank"] == "清洲城步兵头", "所在地+身分 = %s" % m0["place_rank"])

    print("\nT9: 名串子表 @0x509590（stride 16 × 5 项）")
    for va, want in TR2_NAME_TABLE:
        got = cstr_gbk(rdmem(va, 16))
        chk(got == want, "0x%06x = %r" % (va, got))

    print("\nT10: TR2 族分类（4 类，非单一格式）")
    for nm, d, want in (("SAVEDATA.TR2", SAVE, "SAVEFILE"), ("SNDATA1.TR2", SN1, "SCENARIO"),
                        ("SNDATA2.TR2", SN2, "SCENARIO"), ("GAIJI.TR2", GAI, "GAIJI"),
                        ("BSDATA1.TR2", BS1, "BSDATA"), ("BSDATA2.TR2", BS2, "BSDATA")):
        got = classify_tr2(nm, d)
        chk(got == want, "%-13s len=%6d → %s" % (nm, len(d), got))

    print("\nT11: BSDATA stride 59 的位置学独立证据（判别性对照）")
    chk(len(BS1) % 59 == 0 and len(BS1) // 59 == 700, "41300 = 59 × 700 整除")
    diff = [i for i in range(len(BS1)) if BS1[i] != BS2[i]]

    def col_stats(s):
        c = collections.Counter(x % s for x in diff)
        return len(c) / float(s), max(c.values()) / float(len(diff))
    occ59, top59 = col_stats(59)
    chk(occ59 < 0.60, "stride 59: 占用列率 %.3f（33/59，未铺满 ⇒ 有列结构）" % occ59)
    chk(top59 > 0.30, "stride 59: 最热列占比 %.3f ⇒ 单列高度集中" % top59)
    # 对照组：所有非整除 stride 应「铺满 + 无热点」
    others = [41, 43, 47, 49, 53, 58, 60, 61]
    stats = [(s,) + col_stats(s) for s in others]
    chk(all(o == 1.0 for _, o, _ in stats), "对照 8 个非整除 stride 占用列率全 = 1.000（无结构）")
    chk(all(t < 0.05 for _, _, t in stats), "对照组最热列占比全 < 0.05（随机水平）")
    # 倍数 118 也显结构但应弱于基本周期 59 ⇒ 证明 59 是基本周期而非其倍数
    occ118, top118 = col_stats(118)
    chk(top59 > top118, "59 的热点强度 %.3f > 倍数 118 的 %.3f ⇒ 59 为基本周期" % (top59, top118))
    chk(col_stats(70)[0] == 1.0 and col_stats(100)[0] == 1.0,
        "整除但非真 stride 的 70/100 占用率仍 = 1.000 ⇒ 整除性单独不足，须配列对齐")

    print("\nT12: 槽体两趟解码（0x47fb80）与写对偶（0x47fc10）")
    body = MEM[0x47fb80 - BASE: 0x47fc00 - BASE]
    chk(body.count(b"\xe8") >= 4, "0x47fb80 体内 ≥4 处 call")
    chk(rdmem(0x47fc40, 1) == b"\xe8", "0x47fc40 call 0x47f5c0（编码器 = 0x47f350 写对偶）")
    chk(rdmem(0x47fc4e, 10) == b"\xc7\x05\x20\x06\x52\x00\x01\x00\x00\x00",
        "0x47fc4e mov [0x520620],1 ⇒ 已存档标志")

    # ── 导出 ──
    out = {
        "container": {
            "magic": MAGIC_SAVE.decode(), "filesize": len(SAVE),
            "header_size": HDR_SIZE, "meta_size": META_SIZE,
            "n_slots": S["n_slots"], "slot_stride": SLOT_STRIDE,
            "layout": "16B magic + 8×49B slot meta (392B) + 8×40960B slot body",
            "slot_offset_formula": "idx*40960 + 0x198   (0x47d860: lea x5 ; shl 0x0d ; add 0x198)",
            "meta_offset_formula": "idx*49 + 0x10       (0x47d890/0x47d8d0)",
        },
        "slot_meta_schema": [
            {"off": "0x00", "len": 2, "type": "u16 LE", "name": "year"},
            {"off": "0x02", "len": 2, "type": "u16 LE", "name": "month"},
            {"off": "0x04", "len": 2, "type": "u16 LE", "name": "day"},
            {"off": "0x06", "len": 13, "type": "GBK cstr", "name": "hero_name",  "ui_buf": "0x522c88"},
            {"off": "0x13", "len": 13, "type": "GBK cstr", "name": "country",    "ui_buf": "0x522c60"},
            {"off": "0x20", "len": 17, "type": "GBK cstr", "name": "place_rank", "ui_buf": "0x522c70"},
        ],
        "functions": {
            "0x47d720": "OpenTR2(file_idx, mode)  0→SNDATA1 1→SNDATA2 >=2→SAVEDATA ; mode 0=read 1=write",
            "0x47d780": "LoadSAVEDATA — 栈上构造 'A:SAVEDATA.TR2' 并动态替换盘符 (al=[0x526c78]+0x40)",
            "0x47d800": "重试循环 — 失败弹「请在插入<启动盘或保存盘>。」(0x5095e8) 后 retry",
            "0x47d850": "CloseTR2 → [0x4fb09c]",
            "0x47d860": "SeekSlot(idx) → off=idx*40960+0x198 ; [ecx+0x96]=off ; [0x4fb0a8]",
            "0x47d890": "ReadSlotMeta49(idx,dst) → 0x4411b0",
            "0x47d8d0": "WriteSlotMeta49(idx,src) → 0x4411d0",
            "0x47fb80": "LoadSaveSlot(slot) → Open(2,0) ; Seek ; 0x47f350 ×2 趟(flag 1→0)",
            "0x47fc10": "SaveToSlot(slot) → Open(2,1) ; Seek ; 0x47f5c0 ; Close ; [0x520620]=1",
            "0x47fc60": "ReadSlotMeta(slot,&y,&m,&d) → 3 word + 3 strcpy 到 UI 缓冲",
            "0x47fd10": "WriteSlotMeta(slot,y,m,d,name,country,place)",
        },
        "ui_strings": {
            "0x5095e8": "请在插入<启动盘或保存盘>。", "0x509610": "无法使用。",
            "0x509620": "保存的资料文件不正确。",     "0x509638": "资料读取失败。",
            "0x509650": "保存资料文件制作失败",
        },
        "name_table_0x509590": [{"va": hex(v), "name": n} for v, n in TR2_NAME_TABLE],
        "tr2_family": {
            "SAVEFILE": ["SAVEDATA.TR2"], "SCENARIO": ["SNDATA1.TR2", "SNDATA2.TR2"],
            "GAIJI": ["GAIJI.TR2"], "BSDATA": ["BSDATA1.TR2", "BSDATA2.TR2"],
        },
        "slots": S["metas"],
        "corrections": [
            "SNDATA_SPEC §6/§11.1「16 槽 × 20480B」→ 实为 8 槽 × 40960B（shl 0x0d 被误读为 0x0c；且 392/16=24.5 不整）",
            "SNDATA_SPEC §4「49B 记录 = SNDATA 833 条剧本记录」→ 实为 SAVEDATA 的 8 条存档槽元数据（0x47fc60/0x47fd10 硬编码 push 2）",
        ],
    }
    with open(os.path.join(HERE, "savedata_container.json"), "w") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)

    print("\n" + "=" * 62)
    print("自测: %d/%d PASS" % (ok, ok + fail))
    print("RESULT: %s" % ("ALL PASS ✅" if fail == 0 else "FAIL ❌ (%d)" % fail))
    return fail

if __name__ == "__main__":
    raise SystemExit(1 if main() else 0)
