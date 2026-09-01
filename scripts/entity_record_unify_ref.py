#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
entity_record_unify_ref.py -- 续201 参考实现/自测：**59B 武将流记录 ↔ 47B 实体结构** 统一映射，
                              以及 **BSDATA(模板) → SNDATA S1(剧本实例) → 城武将链表** 三层架构闭合。
=====================================================================================
承接续200（BSDATA = 700×59B 明文主表）与续199 下一步 (A)「重定 SNDATA 加密流实体 stride」。

本条的核心结论
--------------
1. **加密流起点是 0x58C，不是文档写的 0x598**（0x14 + 700 + 700 = 0x58C 算术闭合；
   用 0x598 解 S1 得 GBK 可解 0/370，用 0x58C 得 352/354）。
2. **59B 流记录 ↔ 47B 实体结构的完整双向映射**（两个解码器独立给出同一映射）：
       stream 0x00..0x06 -> 姓表 0x521aa8 + 7*id      (7B)
       stream 0x07..0x0d -> 名表 0x520660 + 7*id      (7B)
       stream 0x0e..0x0f -> entity +0x00 (word)        ← 槽自身索引；BSDATA 丢弃
       stream 0x10..0x11 -> entity +0x02 (word)        ← 武将ID（指回 BSDATA 700 主表）
       stream 0x12..0x13 -> entity +0x04 (DWORD 指针)  ← 同城武将链 next；BSDATA 硬置 0
       stream 0x14..0x15 -> entity +0x08 (word)        ← 相性（对上 setter 0x49a5a0 ecx=base+8）
       stream 0x16..0x3a -> entity +0x0a..+0x2e        ← **entity_off = stream_off - 0x0c**
   ⇒ 59 = 7 + 7 + 2 + 2 + 2 + 2 + 37，实体 47 字节被恰好覆盖一次（无空洞无重叠）。
3. **BSDATA 是 SNDATA S1 的模板源**：按武将ID 对齐后 **52/59 偏移逐字节全等**，
   仅 7 个偏移有差异（0x0e/0x0f 槽索引、0x12/0x13 链指针、0x1f、0x36/0x37 主君）。
   姓名段 S1[i] == BSDATA[w10[i]] 达 354/354(剧本1) 与 356/356(剧本2)。
4. **entity +0x04 = 同城武将单向链表 next 指针**（推翻「关系记录指针」的模糊说法，给出精确语义）：
   目标全互异、无自环；走链得 46/44 条链，**链内国/城 100% 唯一（0 反例）**、链→城一一对应；
   **S2 城表 stream word@0x00 命中链头 46/46 与 44/44**，且城结构 +0x00 就是由该 2B 索引 ×47
   构造出的实体指针（解码器 0x47e130 实证）；链头全是大名（武田信玄/上杉谦信/岛津贵久/织田信长）。
5. **城结构 +0x04 = 城链 next 指针**（1B 城索引 ×31 构造）⇒ 引擎是「城链 + 城内武将链」双层链表。
6. 明文段A(file 0x14, 700B) `==1` 的武将数 **精确等于 S1 有效槽数**（354/356）⇒ 段A = 本剧本登场标志。

⚠️ 复刻要点：S1 的 国@0x30 / 城@0x31 与 BSDATA 模板**完全一致（0 差异）**，即剧本没有覆写这两个字段；
   真正的「实际驻留」由城链表达。**不在任何城链上的登场武将（67/60 条）其国/城是模板残值，不代表驻留**。

用法： python3 scripts/entity_record_unify_ref.py
"""
import os
import json
import struct
import collections

from capstone import Cs, CS_ARCH_X86, CS_MODE_32

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BIN = os.path.join(ROOT, "scripts", "_unpacked_mem.bin")
ORIG = os.path.join(ROOT, "Taikou2 Original")
BASE = 0x400000

# ---- 关键常量（本条钉死） ----
S1_DECODER = 0x47DCE0        # SNDATA S1 段解码器（流式）
BS_DECODER = 0x47F7B0        # BSDATA 记录解码器（缓冲式）
S2_DECODER = 0x47E130        # SNDATA S2 城表解码器
READ1_S1, READ2_S1 = 0x47D910, 0x47D930   # 流读 1/2 字节（S1/S2 用）
READ1_BS, READ2_BS = 0x47FA40, 0x47FA60   # 缓冲读 1/2 字节（BSDATA 用）
ENT_BASE, ENT_STRIDE, ENT_N = 0x519868, 47, 370
SUR_TBL, GIV_TBL, NAME_W = 0x521AA8, 0x520660, 7
CITY_BASE, CITY_STRIDE, CITY_N = 0x51EB88, 31, 200
STREAM_BASE = 0x58C          # ★ 纠偏：不是 0x598
S1_STREAM_OFF, S2_STREAM_OFF = 22, 21852
STRIDE, NBS = 59, 700
FLAG_A_OFF, FLAG_B_OFF, FLAG_N = 0x14, 0x2D0, 700

RESULTS = []


def ck(name, cond, detail=""):
    RESULTS.append((name, bool(cond), detail))
    print("  [%s] %-52s %s" % ("PASS" if cond else "FAIL", name, detail))
    return bool(cond)


# ============================ 载入 ============================
IMG = open(BIN, "rb").read()


def rd(va, n):
    return IMG[va - BASE: va - BASE + n]


def load_orig(n):
    return open(os.path.join(ORIG, n), "rb").read()


def decrypt(raw):
    """SNDATA 单字节 XOR：密钥 = raw[0x12] ^ raw[0x13]"""
    k = raw[0x12] ^ raw[0x13]
    return k, bytes(b ^ k for b in raw)


def gbk7(b):
    b = b.split(b"\x00")[0]
    if not b:
        return None
    try:
        return b.decode("gbk")
    except Exception:
        return None


# ============ A. 静态：S1 解码器游标图（capstone 抽取） ============
def extract_stream_map(start_va, read1, read2, limit=0x260):
    """线性抽取「流游标 -> 目标」序列。

    ⚠️ 方法论：本函数只在「除 3 个内层短循环外全为直线代码」的解码器上成立。
    做法 = 跟踪 `lea reg,[base+disp]` 的符号值，`push reg` 记为待定目标，
    遇 read1/read2 消费一个目标并推进游标；识别 `inc r; dec r2; jne back`
    形式的 7 次字节循环并展开。
    """
    md = Cs(CS_ARCH_X86, CS_MODE_32)
    md.detail = True
    code = IMG[start_va - BASE: start_va - BASE + limit]
    insns = list(md.disasm(code, start_va))   # 先物化，禁嵌套 disasm
    lea = {}          # reg -> (base_str, disp)
    pending = None
    cursor = 0
    out = []          # (stream_off, size, target_str)
    i = 0
    loop_start_idx = {}
    while i < len(insns):
        ins = insns[i]
        m, op = ins.mnemonic, ins.op_str
        if m == "lea" and "[" in op:
            dst = op.split(",")[0].strip()
            lea[dst] = op[op.index("[") + 1: op.rindex("]")].strip()
        elif m == "mov" and op.count(",") == 1 and op.split(",")[1].strip().startswith("0x"):
            dst = op.split(",")[0].strip()
            if dst in ("edi", "esi"):
                lea[dst] = dst          # 记成符号寄存器，使后续 push edi 能正确归位到 edi
        elif m == "push":
            pending = lea.get(op.strip(), op.strip())
        elif m == "call":
            tgt = int(op, 16) if op.startswith("0x") else None
            if tgt in (read1, read2):
                sz = 1 if tgt == read1 else 2
                out.append((cursor, sz, pending))
                cursor += sz
                loop_start_idx[i] = (len(out) - 1, cursor)
                pending = None
        elif m == "jne":
            back = int(op, 16)
            # 7 次内层循环：向后跳且区间内只有一次 read → 展开 6 次
            body = [k for k in range(len(insns)) if back <= insns[k].address < ins.address]
            reads = [k for k in body if insns[k].mnemonic == "call"
                     and insns[k].op_str.startswith("0x")
                     and int(insns[k].op_str, 16) in (read1, read2)]
            if len(reads) == 1 and out:
                so, sz, tg = out[-1]
                for _ in range(6):
                    out.append((cursor, sz, tg + "+n"))
                    cursor += sz
        elif m == "ret":
            break
        i += 1
    return out, cursor


print("=" * 78)
print("A. 静态：S1 解码器 0x47dce0 —— 流游标图 / 实体几何")
S1MAP, S1_TOTAL = extract_stream_map(S1_DECODER, READ1_S1, READ2_S1)
ck("A1 S1 解码器实体基址 mov edi,0x51986a",
   rd(0x47DCE9, 5) == bytes.fromhex("bf6a985100"),
   "= ENT_BASE+2 = 0x%06x" % (ENT_BASE + 2))
ck("A2 记录数立即数 = 0x172 (=370)",
   rd(0x47DCF6, 8) == bytes.fromhex("c744241472010000") and 0x172 == ENT_N,
   "mov [esp+0x14],0x172")
ck("A3 循环尾 add edi,0x2f (=47) ⇒ 实体 stride 47",
   rd(0x47DEE3, 3) == bytes.fromhex("83c72f") and 0x2f == ENT_STRIDE)
ck("A4 姓表/名表基址立即数出现在解码器内",
   rd(0x47DD07, 6) == bytes.fromhex("8d98a81a5200") and rd(0x47DD22, 6) == bytes.fromhex("8d9960065200"),
   "lea ebx,[eax+0x521aa8] / lea ebx,[ecx+0x520660]")
ck("A5 流消费总量 == 59", S1_TOTAL == STRIDE, "实测 %d" % S1_TOTAL)

# 实体覆盖：把 edi 相对目标折算成实体偏移
ent_hits = collections.Counter()
stream2ent = {}
for so, sz, tg in S1MAP:
    if tg is None:
        continue
    t = tg.replace("+n", "")
    if t.startswith("edi"):
        d = 0 if t == "edi" else int(t.split("+")[1], 16) if "+" in t else -int(t.split("-")[1], 16)
        eo = d + 2                      # edi = ENT_BASE + 2
        for k in range(sz):
            ent_hits[eo + k] += 1
        stream2ent[so] = eo
ck("A7 read2→edi-2 = entity+0x00（stream 0x0e）", stream2ent.get(0x0E) == 0x00)
ck("A8 read2→edi = entity+0x02（stream 0x10 = 武将ID）", stream2ent.get(0x10) == 0x02)
ck("A9 read2→edi+6 = entity+0x08（stream 0x14 = 相性）", stream2ent.get(0x14) == 0x08)
ck("A10 stream 0x16.. → entity_off = stream_off - 0x0c",
   all(stream2ent[s] == s - 0x0C for s in stream2ent if s >= 0x16),
   "样本 0x16→0x%02x, 0x30→0x%02x, 0x36→0x%02x"
   % (stream2ent.get(0x16, -1), stream2ent.get(0x30, -1), stream2ent.get(0x36, -1)))

# A6：实体字段读的「字节覆盖区间」完整（read2 双字节调用只产生一个流起始键，
# 故第二字节不单独出现在 stream2ent；0x12/0x13 是局部指针索引读，不归实体字段）
_cover = set()
for so, sz, tg in S1MAP:
    if tg and tg.replace("+n", "").startswith("edi"):
        _cover |= set(range(so, so + sz))
EXPECT_COVER = {0x0E, 0x0F, 0x10, 0x11} | set(range(0x14, 0x3B))
ck("A6 实体字段读字节覆盖 == {0x0e,0x0f,0x10,0x11} ∪ [0x14..0x3a]（0x12/0x13 为局部读）",
   _cover == EXPECT_COVER, "覆盖 %d 字节" % len(_cover))

print("-" * 78)
print("A'. S1 解码器里的实体指针构造（entity+0x04）")
ck("A11 cmp cx,0x172 边界检查", rd(0x47DD57, 5) == bytes.fromhex("6681f97201"))
ck("A12 idx*47 (lea+shl4+sub) + 0x519868",
   rd(0x47DD64, 3) == bytes.fromhex("8d0449") and rd(0x47DD67, 3) == bytes.fromhex("c1e004")
   and rd(0x47DD6A, 2) == bytes.fromhex("2bc1") and rd(0x47DD6C, 5) == bytes.fromhex("0568985100"))
ck("A13 越界写 0（xor eax,eax）", rd(0x47DD73, 2) == bytes.fromhex("33c0"))
ck("A14 落点 mov [edi+2],eax ⇒ entity+0x04 是 DWORD 实体指针",
   rd(0x47DD78, 3) == bytes.fromhex("894702"))

# ============ B. 静态：BSDATA 解码器 0x47f7b0 ============
print("=" * 78)
print("B. 静态：BSDATA 解码器 0x47f7b0 —— 独立复现 stride 59 / 丢弃两个剧本态字段")
ck("B1 记录偏移 = 59*idx（shl3-sub / lea*4 / lea*2 链）",
   rd(0x47F7BE, 3) == bytes.fromhex("c1e103") and rd(0x47F7C1, 2) == bytes.fromhex("2bc8")
   and rd(0x47F7C4, 3) == bytes.fromhex("8d1488") and rd(0x47F7CC, 3) == bytes.fromhex("8d0450"),
   "7x → 29x → 59x")
ck("B2 BSDATA 缓冲基址 ecx=0x524a20", rd(0x47F7C7, 5) == bytes.fromhex("b9204a5200"))
ck("B3 实体 stride 47（lea edi+edi*2; shl 4; sub edi）",
   rd(0x47F827, 3) == bytes.fromhex("8d347f") and rd(0x47F82D, 3) == bytes.fromhex("c1e604")
   and rd(0x47F830, 2) == bytes.fromhex("2bf7"))
ck("B4 姓表/名表 7B 循环基址一致",
   rd(0x47F7F2, 6) == bytes.fromhex("8d9ea81a5200") and rd(0x47F805, 6) == bytes.fromhex("8db660065200"))
ck("B5 ★ entity+0x04 被硬置 0（mov dword [esi+0x51986c],0）",
   rd(0x47F854, 10) == bytes.fromhex("c7866c98510000000000"),
   "⇒ BSDATA 无链指针")
ck("B6 ★ stream 0x0e / 0x12 两处 read2 目标是栈局部 [esp+0x18]（读后丢弃）",
   rd(0x47F81D, 4) == bytes.fromhex("8d4c2418") and rd(0x47F841, 4) == bytes.fromhex("8d442418"),
   "两次复用同一局部 ⇒ 首值被覆盖")
ck("B7 entity+0x02 / +0x08 落点与 S1 一致",
   rd(0x47F832, 6) == bytes.fromhex("8d966a985100") and rd(0x47F84E, 6) == bytes.fromhex("8d8e70985100"),
   "0x51986a=+0x02 / 0x519870=+0x08")

# ============ C. 已知实体偏移的交叉验证 ============
print("=" * 78)
print("C. 交叉验证：本映射 vs 此前独立破解的实体偏移")
KNOWN = {0x14: (0x08, "相性 setter 0x49a5a0 ecx=base+8"),
         0x16: (0x0A, "五维起点"), 0x1A: (0x0E, "五维终点"),
         0x1B: (0x0F, "技能起点"), 0x1D: (0x11, "技能终点"),
         0x30: (0x24, "国索引"), 0x31: (0x25, "在城"), 0x36: (0x2A, "主君 word")}
allok = True
for so, (eo, why) in sorted(KNOWN.items()):
    got = stream2ent.get(so)
    ok = (got == eo)
    allok &= ok
    print("      stream 0x%02x → entity +0x%02x  期望 +0x%02x  %s  (%s)"
          % (so, got if got is not None else -1, eo, "OK" if ok else "MISMATCH", why))
ck("C1 8 个独立来源的实体偏移全部命中", allok)
ck("C2 相性 setter 0x49a5a0 取 ecx=base+8（读 word[ecx] 改写 bit11-14 写回）",
   rd(0x49A5A0 + 0x0A, 8) == bytes.fromhex("668b1181e2ff8700")
   and rd(0x49A5A0 + 0x18, 3) == bytes.fromhex("668911"),
   "mov dx,[ecx]; and edx,0x87ff; ...; mov [ecx],dx（相性居 bit11-14）")

# ============ D. 数据：加密流起点纠偏 ============
print("=" * 78)
print("D. 数据：加密流起点 = 0x58C（纠正 SNDATA_SPEC §2 的 0x598）")
ck("D1 算术闭合 0x14 + 700 + 700 == 0x58C",
   FLAG_A_OFF + FLAG_N + FLAG_N == STREAM_BASE,
   "0x%x + 700 + 700 = 0x%x" % (FLAG_A_OFF, STREAM_BASE))
ck("D2 段B 起点 = 0x2D0（旧文档写 0x2d4，差 4）", FLAG_A_OFF + FLAG_N == FLAG_B_OFF)

SC = {}
for scen in (1, 2):
    raw = load_orig("SNDATA%d.TR2" % scen)
    key, dec = decrypt(raw)
    s1o = STREAM_BASE + S1_STREAM_OFF
    s2o = STREAM_BASE + S2_STREAM_OFF
    SC[scen] = dict(
        raw=raw, key=key, dec=dec,
        s1=[dec[s1o + i * STRIDE: s1o + (i + 1) * STRIDE] for i in range(ENT_N)],
        s2=[dec[s2o + i * 26: s2o + (i + 1) * 26] for i in range(CITY_N)],
        bs=[load_orig("BSDATA%d.TR2" % scen)[i * STRIDE:(i + 1) * STRIDE] for i in range(NBS)],
    )
ck("D3 密钥 = raw[0x12]^raw[0x13] = 0x0c / 0x0a",
   SC[1]["key"] == 0x0C and SC[2]["key"] == 0x0A)
for scen in (1, 2):
    ok58c = sum(1 for r in SC[scen]["s1"] if gbk7(r[0:7]) and gbk7(r[7:14]))
    bad = STREAM_BASE + 12 + S1_STREAM_OFF     # 若按旧 0x598
    d = SC[scen]["dec"]
    ok598 = sum(1 for i in range(ENT_N)
                if gbk7(d[bad + i * STRIDE: bad + i * STRIDE + 7])
                and gbk7(d[bad + i * STRIDE + 7: bad + i * STRIDE + 14]))
    ck("D4.%d 0x58C 起 S1 姓名可解 >=350 而 0x598 起 == 0" % scen,
       ok58c >= 350 and ok598 == 0, "0x58C:%d/370  0x598:%d/370" % (ok58c, ok598))

# ============ E. 数据：S1 ↔ BSDATA 模板对齐 ============
print("=" * 78)
print("E. 数据：BSDATA(模板) → S1(剧本实例) 按武将ID 对齐")
EXPECT_DIFF = {0x0E, 0x0F, 0x12, 0x13, 0x1F, 0x36, 0x37}
for scen in (1, 2):
    s1, bs = SC[scen]["s1"], SC[scen]["bs"]
    w0e = [struct.unpack_from("<H", r, 0x0E)[0] for r in s1]
    w10 = [struct.unpack_from("<H", r, 0x10)[0] for r in s1]
    live = [i for i in range(ENT_N) if w10[i] != 0xFFFF]
    ck("E1.%d stream 0x0e == 槽自身索引（全 370 条）" % scen,
       all(w0e[i] == i for i in range(ENT_N)))
    ck("E2.%d 武将ID 全 <700 且互异，空槽 0xffff" % scen,
       all(w10[i] < NBS for i in live) and len(set(w10[i] for i in live)) == len(live),
       "有效槽=%d" % len(live))
    nm = sum(1 for i in live if s1[i][0:14] == bs[w10[i]][0:14])
    ck("E3.%d ★ 姓名段 S1[i] == BSDATA[w10[i]] 全等" % scen,
       nm == len(live), "%d/%d" % (nm, len(live)))
    diff = set(o for o in range(STRIDE) if any(s1[i][o] != bs[w10[i]][o] for i in live))
    ck("E4.%d ★ 差异偏移集合 == {0x0e,0x0f,0x12,0x13,0x1f,0x36,0x37}（52/59 全等）" % scen,
       diff == EXPECT_DIFF, "实测 %s" % sorted(hex(o) for o in diff))
    ck("E5.%d 国@0x30 / 城@0x31 未被剧本覆写（差异集合不含）" % scen,
       0x30 not in diff and 0x31 not in diff)
    flagA = SC[scen]["raw"][FLAG_A_OFF:FLAG_A_OFF + FLAG_N]
    ck("E6.%d 段A(0x14)==1 的武将数 == S1 有效槽数" % scen,
       sum(1 for v in flagA if v == 1) == len(live),
       "%d == %d" % (sum(1 for v in flagA if v == 1), len(live)))
    ck("E7.%d 段A 值域 {0,1}；有效槽的武将 段A 恒 1" % scen,
       set(flagA) == {0, 1} and all(flagA[w10[i]] == 1 for i in live))
    SC[scen]["w10"], SC[scen]["live"] = w10, live

# ============ F. 数据：城武将链表 ============
print("=" * 78)
print("F. 数据：entity+0x04 = 同城武将链 next 指针")
EXPECT_CHAINS = {1: 46, 2: 44}
CHAIN_OUT = {}
for scen in (1, 2):
    s1, s2 = SC[scen]["s1"], SC[scen]["s2"]
    w12 = [struct.unpack_from("<H", r, 0x12)[0] for r in s1]
    kok = [r[0x30] for r in s1]
    joe = [r[0x31] for r in s1]
    tv = [v for v in w12 if v < ENT_N]
    ck("F1.%d 链指针目标全互异 + 无自环 + 越界值恒 0xffff" % scen,
       len(set(tv)) == len(tv) and all(w12[i] != i for i in range(ENT_N))
       and all(v == 0xFFFF for v in w12 if v >= ENT_N),
       "有效目标=%d 空=%d" % (len(tv), sum(1 for v in w12 if v == 0xFFFF)))
    targets = set(tv)
    heads = [i for i in range(ENT_N) if i not in targets and w12[i] < ENT_N]
    chains, seen = [], set()
    for h in heads:
        ch, cur, g = [], h, 0
        while cur < ENT_N and cur not in seen and g < ENT_N + 4:
            seen.add(cur); ch.append(cur); cur = w12[cur]; g += 1
        chains.append(ch)
    ck("F2.%d 链数 == %d，且走链不成环（全部自然终止）" % (scen, EXPECT_CHAINS[scen]),
       len(chains) == EXPECT_CHAINS[scen] and len(seen) == sum(len(c) for c in chains),
       "链数=%d 覆盖槽=%d" % (len(chains), len(seen)))
    ck("F3.%d ★ 链内 国/城 100%% 唯一（0 反例）" % scen,
       all(len(set(joe[i] for i in c)) == 1 for c in chains)
       and all(len(set(kok[i] for i in c)) == 1 for c in chains))
    cities = [joe[c[0]] for c in chains]
    ck("F4.%d ★ 链 → 城 一一对应（每城至多一条链）" % scen,
       len(set(cities)) == len(chains))
    hit = sum(1 for c in chains
              if joe[c[0]] < CITY_N and struct.unpack_from("<H", s2[joe[c[0]]], 0)[0] == c[0])
    ck("F5.%d ★ S2 城表 stream word@0x00 命中链头" % scen,
       hit == len(chains), "%d/%d" % (hit, len(chains)))
    nohead = [c for c in range(CITY_N) if struct.unpack_from("<H", s2[c], 0)[0] >= ENT_N]
    ck("F6.%d 无链城的 word@0x00 恒 0xffff（NULL）" % scen,
       all(struct.unpack_from("<H", s2[c], 0)[0] == 0xFFFF for c in nohead),
       "无链城=%d" % len(nohead))
    flagA = SC[scen]["raw"][FLAG_A_OFF:FLAG_A_OFF + FLAG_N]
    iso = [i for i in SC[scen]["live"] if i not in seen]
    ck("F7.%d 孤立槽（登场但不在任何城链上）段A 恒 1" % scen,
       all(flagA[SC[scen]["w10"][i]] == 1 for i in iso), "孤立=%d" % len(iso))
    # 链头 = 大名（史实抽样）
    named = {}
    for c in chains:
        nmz = (gbk7(s1[c[0]][0:7]) or "") + (gbk7(s1[c[0]][7:14]) or "")
        named[joe[c[0]]] = nmz
    SAMPLE = {1: {40: "武田信玄", 50: "上杉谦信", 195: "岛津贵久"},
              2: {72: "织田信长", 40: "武田信玄", 195: "岛津义久"}}[scen]
    ck("F8.%d ★ 链头 = 各家大名（史实抽样）" % scen,
       all(named.get(c) == n for c, n in SAMPLE.items()),
       ", ".join("城%d=%s" % (c, named.get(c)) for c in SAMPLE))
    CHAIN_OUT[scen] = dict(
        n_chains=len(chains), covered=len(seen), isolated=len(iso),
        chains=[dict(city=joe[c[0]], kuni=kok[c[0]], slots=c,
                     names=[(gbk7(s1[i][0:7]) or "") + (gbk7(s1[i][7:14]) or "") for i in c])
                for c in sorted(chains, key=lambda x: -len(x))])

# ============ G. 静态：S2 城表解码器双指针 ============
print("=" * 78)
print("G. 静态：S2 城表解码器 0x47e130 —— 城结构双指针")
ck("G1 城基址 mov esi,0x51eb8c（= CITY_BASE+4）",
   rd(0x47E138, 5) == bytes.fromhex("be8ceb5100"))
ck("G2 城数立即数 0xc8 (=200)", rd(0x47E13D, 5) == bytes.fromhex("bbc8000000") and 0xC8 == CITY_N)
ck("G3 ★ 城+0x00 = 实体指针（2B 槽索引 → 边界370 → ×47 → +0x519868 → mov [esi-4],eax）",
   rd(0x47E152, 5) == bytes.fromhex("6681f97201") and rd(0x47E167, 5) == bytes.fromhex("0568985100")
   and rd(0x47E174, 3) == bytes.fromhex("8946fc"))
ck("G4 ★ 城+0x04 = 城链 next 指针（1B 城索引 → 边界200 → ×31 → +0x51eb88 → mov [esi],eax）",
   rd(0x47E183, 2) == bytes.fromhex("3cc8") and rd(0x47E18E, 3) == bytes.fromhex("c1e005")
   and rd(0x47E191, 2) == bytes.fromhex("2bc1") and rd(0x47E193, 5) == bytes.fromhex("0588eb5100")
   and rd(0x47E1A2, 2) == bytes.fromhex("8906"))
ck("G5 城 stride 31 由 shl5-sub 复现", (1 << 5) - 1 == CITY_STRIDE)
ck("G6 S2 流 stride 26 与城结构 31B 的差 = 两个指针各多 3/2 字节",
   26 + (4 - 2) + (4 - 1) == CITY_STRIDE, "26 + 2 + 3 = 31")

# ============ 落盘 ============
OUT = {
    "breakthrough": "续201",
    "title": "59B 流记录 ↔ 47B 实体结构统一映射 + BSDATA→S1→城武将链三层架构",
    "corrections": [
        {"what": "SNDATA 加密流起点", "old": "0x598", "new": "0x58C",
         "why": "0x14 + 700 + 700 = 0x58C；用 0x598 解 S1 姓名 0/370，用 0x58C 得 352/354"},
        {"what": "明文段B 起点", "old": "0x2d4", "new": "0x2d0", "why": "0x14 + 700 = 0x2d0"},
        {"what": "续199 下一步(A)「SNDATA 实体 stride 待重测」", "old": "未知",
         "new": "= 59（与 BSDATA 同格式）",
         "why": "S1 解码器 0x47dce0 游标反算 59B/记录；与 BSDATA 解码器 0x47f7b0 的 59*idx 独立互证"},
        {"what": "entity+0x04 语义", "old": "续200 记为「+0x12 未定」",
         "new": "同城武将链 next 指针（2B 槽索引 ×47 构造）",
         "why": "目标全互异、链内城唯一 0 反例、S2 城表 word@0x00 命中链头 46/46 与 44/44"},
        {"what": "entity+0x00 语义", "old": "续200 记为「+0x0e 未定」",
         "new": "槽自身索引（BSDATA 中恒 0xffff 且被解码器丢弃）",
         "why": "S1 中 w0e[i]==i 全 370 条成立"},
    ],
    "stream_to_entity": {
        "rule_ge_0x16": "entity_off = stream_off - 0x0c",
        "map": {("0x%02x" % s): ("+0x%02x" % e) for s, e in sorted(stream2ent.items())},
        "names": {"surname": {"stream": "0x00..0x06", "table": hex(SUR_TBL), "width": NAME_W},
                  "given": {"stream": "0x07..0x0d", "table": hex(GIV_TBL), "width": NAME_W}},
        "stride_stream": STRIDE, "stride_entity": ENT_STRIDE, "records": ENT_N,
    },
    "decoders": {
        "s1_stream": hex(S1_DECODER), "bsdata_buffer": hex(BS_DECODER), "s2_city": hex(S2_DECODER),
        "read1_stream": hex(READ1_S1), "read2_stream": hex(READ2_S1),
        "read1_buffer": hex(READ1_BS), "read2_buffer": hex(READ2_BS),
    },
    "architecture": {
        "layer1_template": "BSDATA1/2.TR2 = 700×59B 明文武将模板库",
        "layer2_instance": "SNDATA S1 = 370×59B 剧本槽；stream 0x10 = 武将ID 指回模板",
        "layer3_topology": "城结构+0x00 → 链头槽；实体+0x04 → 同城下一武将；城结构+0x04 → 下一城",
        "template_copy_fidelity": "按武将ID 对齐后 52/59 偏移逐字节全等",
        "scenario_overrides": ["0x0e/0x0f 槽索引", "0x12/0x13 链指针", "0x1f", "0x36/0x37 主君"],
    },
    "chains": CHAIN_OUT,
    "godot_notes": [
        "S1 的 国@0x30/城@0x31 与 BSDATA 模板 0 差异 ⇒ 剧本未覆写；实际驻留必须按城链判定。",
        "不在任何城链上的登场武将（剧本1:67 / 剧本2:60）其国/城为模板残值，不代表驻留。",
        "复刻数据层建议：BSDATA 读模板 + SNDATA S1 读槽映射与城链，两者分离。",
    ],
}
outp = os.path.join(ROOT, "scripts", "entity_record_unify.json")
with open(outp, "w", encoding="utf-8") as f:
    json.dump(OUT, f, ensure_ascii=False, indent=1)

print("=" * 78)
npass = sum(1 for _, ok, _ in RESULTS if ok)
print("落盘: %s" % outp)
print("RESULT: %d/%d %s" % (npass, len(RESULTS), "ALL PASS ✅" if npass == len(RESULTS) else "FAIL ❌"))
if npass != len(RESULTS):
    for n, ok, d in RESULTS:
        if not ok:
            print("   ❌ %s  %s" % (n, d))
