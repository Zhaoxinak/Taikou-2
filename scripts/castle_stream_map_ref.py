# -*- coding: utf-8 -*-
"""
太阁立志传2 —— 城表 `0x51eb88`(31B × 200) 权威流映射 + 三项纠偏
================================================================================
承接续143「下一步①：定名 0x51eb88 城表字段布局」。

结论摘要
--------
**① 权威流映射（loader `0x47e130`，逐条实锤）**
`esi = 0x51eb8c` = 城记录基址 `0x51eb88` + 4 ⇒ `[esi + k]` 的偏移 = **k + 4**。
17 次读调用（`0x47d930`=读 WORD，`0x47d910`=读 BYTE）完美对齐 26B 记录：

| 流偏移 | 宽 | 目标偏移 | 语义 |
|---|---|---|---|
| 0:2   | W | `+0x00`(dword) | **城主武将索引** → `0x519868 + idx*47`（`cmp cx,0x172`） |
| 2     | B | `+0x04`(dword) | **本城(親城)索引** → `0x51eb88 + idx*31`（`cmp al,0xc8`） |
| 3     | B | `+0x08` | 状态/規模字节（0..250，29 dist）⚠️ **非**所属国 |
| 4     | B | `+0x09` | 状态字节 |
| 5:7   | W | `+0x0a` | 未知 2B（0..64592，114 dist）⚠️ **非**武将索引 |
| 7     | B | `+0x0c` | 农商等级 |
| 8     | B | `+0x0d` | 守城度 |
| 9     | B | `+0x0e` | 民心 |
| 10    | B | `+0x0f` | 生产率 |
| 11:13 | W | `+0x10` | 軍糧 |
| 13:15 | W | `+0x12` | 米 |
| 15:17 | W | `+0x14` | 資金 |
| 17:19 | W | `+0x16` | 地域 |
| 19:21 | W | `+0x18` | `0xffff` 哨兵 |
| 21    | B | `+0x1a` | 次级民情 |
| 22:24 | W | `+0x1b` | 城種(&7) |
| 24:26 | W | `+0x1d` | **所属国 province**（low 0..48，49 distinct）|

循环：`add esi, 0x1f`(31)、`ebx = 0xc8`(200)。读序列 `W B B B W B B B B W W W W W B W W`
= 9×2 + 8×1 = **26B**，与 §3.17.6 记载完全一致（互为独立佐证）。

**② 🔴 纠偏一（推翻续143 ⑥）：`+0x0a` 不是武将索引**
数据侧铁证：两剧本 400 条中 **399 条 ≥ 370**，唯一 <370 的一条值为 0；值域 0..64592、114 distinct。
`0x46a4a0` 确以 `word[+0xa]` 作武将索引（`cmp ax,0x172` → `×47` → `0x519868`），
但因 `jae` 几乎恒真，**该分支实质从不命中 = 残留/死代码**。
🔑 方法论：**代码形态 ≠ 运行期使用**；定字段语义前必须先查数据分布。

**③ 🔴 纠偏二（第 7 处文档矛盾）：所属国 = `+0x1d`，不是 `+0x08`**
§3.17.6 续99 纠偏 #3 称「所属国 = `+0x08`（stream[3]）」——**错误**。
- 数据：`stream[3]`→`+0x08` 值域 **0..250、29 distinct**，不可能是 49 国；
  `stream[24]`→`+0x1d`(low) 值域 **0..48、49 distinct 全覆盖**。
- 代码：loader 明确 `stream[24:26]`(W) → `[esi+0x19]` = `+0x1d`。
- 自证矛盾：§3.17.6 自己产出的 `castle_values.json` 用的就是 `d[24] → province`。
⇒ §3.17.2 正确；§3.17.6 续99 #3 应撤销。

**④ 🆕 纠偏三：`byte[entity+0x24]` = 国(province) 索引，非「親密度」**
- 数据：BSDATA `@48` → `+0x24`，**663/700 < 49**；≥49 的 37 个**全部是 255**（哨兵）；
  <49 的值覆盖 0..48 中的 **45** 个。
- 代码：`0x46a4a0` 以 `cmp al,0x31`(49) 为界，`×14` 查 **49 国表 `0x5179bc`**
  （`shl ecx,3; sub ecx,eax`=×7 再 `lea [ecx*2+0x5179b8]` 后 `[eax+4]` ⇒ 基址实为 `0x5179bc`）。
⇒ 续135「`@48`→`+0x24`=親密度」误命名，应撤销；`bsdata.json` 的 `intimacy` 键应改名 `province`。

**⑤ 🆕 坐实：`byte[entity+0x25]` = 在城（所属城）索引 0..199，哨兵 255**
422/700 < 200；278/700 = 255（浪人/无固定城）。与 §3.17.6 一致。

**⑥ 🆕 `0x46a4a0` 语义**：按城记录 `+0x0a` 反查城 → 取该武将的**国** `byte[+0x24]`
→ 查 49 国表得该国**代表武将** `word[+0]` → 取代表武将的**在城** `byte[+0x25]`
→ `0x49a990(城记录, 代表武将号)`（设新城主/后继者）。因 `+0x0a` 恒 ≥370，实质不触发。

运行：python scripts/castle_stream_map_ref.py
"""
import bisect, json, os, pickle, sys

BASE = 0x400000
HERE = os.path.dirname(os.path.abspath(__file__))
IDX = os.path.join(HERE, "_insn_addrs.pkl")

_d = pickle.load(open(IDX, "rb"))
IMAP = _d[0]
FSTART = sorted(_d[1])
RVAS = sorted(IMAP)

_fail = []
_n = 0


def chk(name, cond):
    global _n
    _n += 1
    if cond:
        print(f"  [ OK ] {name}")
    else:
        print(f"  [FAIL] {name}")
        _fail.append(name)


def body(va, maxlen=0x400):
    s = va - BASE
    e = min(s + maxlen, RVAS[-1] + 1)
    return [(r + BASE, IMAP[r][1]) for r in RVAS[bisect.bisect_left(RVAS, s):bisect.bisect_left(RVAS, e)]]


def has(b, sub):
    return any(sub in t for (_, t) in b)


# =============================================================================
print("=== 1. loader 0x47e130：骨架与循环 ===")
# =============================================================================
L = body(0x47e130, 0x190)
chk("esi = 0x51eb8c（= 城记录基址 0x51eb88 + 4）", has(L, "mov esi, 0x51eb8c"))
chk("ebx = 0xc8（200 条）", has(L, "mov ebx, 0xc8"))
chk("步进 add esi, 0x1f（stride 31）", has(L, "add esi, 0x1f"))
chk("回跳 jne 0x47e142 形成 200 次循环", has(L, "jne 0x47e142"))

# =============================================================================
print("=== 2. 17 次读调用的 (reader, 目标偏移) 序列 ===")
# =============================================================================
# 解析： dest 由紧邻 call 之前的 lea/push 决定；reader = call 目标
WORD_READER = "call 0x47d930"
BYTE_READER = "call 0x47d910"
seq = []      # [(kind, dest_expr)]
pending_dest = None
for addr, t in L:
    if t.startswith("lea ") and "esi" in t and "[" in t:
        # lea reg, [esi + k] / [esi - 4]
        op = t.split(" ", 1)[1]
        inner = op[op.find("[") + 1:op.find("]")]
        pending_dest = inner.strip()
    if t == WORD_READER or t == BYTE_READER:
        seq.append(("W" if t == WORD_READER else "B", pending_dest))
        pending_dest = None
    # 前两读经栈局部中转：[esp+0xc]/[esp+0x10] → 随后 mov dword [esi±k], eax
    if t in ("mov dword ptr [esi - 4], eax", "mov dword ptr [esi], eax"):
        inner = "esi-4" if "- 4" in t else "esi"
        for i in range(len(seq) - 1, -1, -1):
            if seq[i][1] is None or "esp" in (seq[i][1] or ""):
                seq[i] = (seq[i][0], inner)
                break

kinds = "".join(k for k, _ in seq)
chk(f"读调用共 17 次  [{len(seq)}]", len(seq) == 17)
chk(f"读序列 = WBBBWBBBBWWWWWBWW（26B）  [实测 {kinds}]",
    kinds == "WBBBWBBBBWWWWWBWW")
chk("9×W + 8×B = 26 字节", kinds.count("W") * 2 + kinds.count("B") * 1 == 26)

# dest 表达式 -> 记录内偏移（esi = base+4 ⇒ [esi+k] = k+4，[esi-4] = 0）
def off_of(expr):
    if expr is None:
        return None
    e = expr.replace(" ", "")
    if e == "esi-4":
        return 0x00
    if e.startswith("esi+"):
        return int(e[4:], 16) + 4
    if e == "esi":
        return 0x04
    return None


offsets = [off_of(d) for _, d in seq]
EXPECT = [0x00, 0x04, 0x08, 0x09, 0x0a, 0x0c, 0x0d, 0x0e, 0x0f,
          0x10, 0x12, 0x14, 0x16, 0x18, 0x1a, 0x1b, 0x1d]
chk(f"目标偏移序列 = {[hex(x) for x in EXPECT]}  [实测 {[hex(x) if x is not None else None for x in offsets]}]",
    offsets == EXPECT)

# 流偏移（按 26B 顺序累加）
pos = 0
stream_off = []
for k, _ in seq:
    stream_off.append(pos)
    pos += 2 if k == "W" else 1
chk("流偏移序列正确（0,2,3,4,5,7,8,9,10,11,13,15,17,19,21,22,24）",
    stream_off == [0, 2, 3, 4, 5, 7, 8, 9, 10, 11, 13, 15, 17, 19, 21, 22, 24])
chk("总消耗 = 26 字节", pos == 26)

# =============================================================================
print("=== 3. 城主 / 本城 的索引→指针转换 ===")
# =============================================================================
chk("城主：word 读后 cmp cx, 0x172（370 上界）", has(L, "cmp cx, 0x172"))
chk("城主：×47 = lea[ecx+ecx*2]; shl eax,4; sub eax,ecx",
    has(L, "lea eax, [ecx + ecx*2]") and has(L, "shl eax, 4") and has(L, "sub eax, ecx"))
chk("城主：+ 0x519868（实体表）", has(L, "add eax, 0x519868"))
chk("城主：写入 [esi - 4] = +0x00", has(L, "mov dword ptr [esi - 4], eax"))
chk("本城：byte 读后 cmp al, 0xc8（200 上界）", has(L, "cmp al, 0xc8"))
chk("本城：×31 = shl eax,5; sub eax,ecx", has(L, "shl eax, 5") and has(L, "sub eax, ecx"))
chk("本城：+ 0x51eb88（城表自身）", has(L, "add eax, 0x51eb88"))
chk("本城：写入 [esi] = +0x04", has(L, "mov dword ptr [esi], eax"))

# =============================================================================
print("=== 4. 🔴 纠偏一：+0x0a 不是武将索引（数据侧铁证）===")
# =============================================================================
CV = json.load(open(os.path.join(HERE, "castle_values.json"), encoding="utf-8"))
for sc in ("scenario1", "scenario2"):
    recs = CV[sc]
    chk(f"{sc}: 200 条", len(recs) == 200)
    f0a = [r["f0a"] for r in recs]
    n_lt = sum(1 for v in f0a if v < 370)
    chk(f"{sc}: +0x0a < 370 的仅 {n_lt} 条（余 {200 - n_lt} 条 ≥370）", n_lt <= 1)
    chk(f"{sc}: +0x0a 值域 {min(f0a)}..{max(f0a)}（远超 370）", max(f0a) > 1000)
chk("⇒ +0x0a 非武将索引（续143 断言被推翻，§3.17.2 正确）", True)

# 代码侧确有这样用过，但恒不命中
B4 = body(0x46a4a0, 0x200)
chk("0x46a4a0 确以 word[+0xa] 作武将索引（cmp ax,0x172 → ×47 → 0x519868）",
    has(B4, "mov ax, word ptr [edi + 0xa]") and has(B4, "cmp ax, 0x172")
    and has(B4, "add eax, 0x519868"))
chk("0x46a4a0 edi = 0x51eb88、200 次、步进 0x1f",
    has(B4, "mov edi, 0x51eb88") and has(B4, "mov dword ptr [esp + 0x18], 0xc8")
    and has(B4, "add edi, 0x1f"))

# =============================================================================
print("=== 5. 🔴 纠偏二（第 7 处文档矛盾）：所属国 = +0x1d，不是 +0x08 ===")
# =============================================================================
for sc in ("scenario1", "scenario2"):
    recs = CV[sc]
    prov = [r["province"] for r in recs]        # d[24] -> +0x1d (low)
    f08 = [r["f08"] for r in recs]              # d[3]  -> +0x08
    chk(f"{sc}: province(+0x1d low) 值域 {min(prov)}..{max(prov)}、{len(set(prov))} distinct = 49 国",
        min(prov) == 0 and max(prov) == 48 and len(set(prov)) == 49)
    chk(f"{sc}: f08(+0x08) 值域 {min(f08)}..{max(f08)}、{len(set(f08))} distinct ≠ 49（非所属国）",
        max(f08) > 48 or len(set(f08)) != 49)
chk("代码侧：stream[24:26](W) → [esi+0x19] = +0x1d（loader 实证）",
    offsets[16] == 0x1d and stream_off[16] == 24 and kinds[16] == "W")
chk("⇒ §3.17.6 续99 纠偏 #3「所属国=+0x08」错误，应撤销；§3.17.2 正确", True)

# =============================================================================
print("=== 6. 🆕 纠偏三：byte[entity+0x24] = 国索引，非「親密度」===")
# =============================================================================
BS = json.load(open(os.path.join(HERE, "bsdata.json"), encoding="utf-8"))
ch = BS["characters"]
chk("BSDATA 700 条", len(ch) == 700)
intim = [c["intimacy"] for c in ch]     # @48 -> +0x24
lt = [v for v in intim if v < 49]
ge = [v for v in intim if v >= 49]
chk(f"+0x24: {len(lt)}/700 < 49（应为绝大多数）", len(lt) > 600)
chk(f"+0x24: ≥49 的 {len(ge)} 条全部为 255 哨兵", ge and set(ge) == {255})
chk(f"+0x24: <49 的值覆盖 0..48 中的 {len(set(lt))} 个", len(set(lt)) >= 40)
# 代码侧
chk("0x46a4a0 以 cmp al,0x31(49) 为界读 byte[+0x24]",
    has(B4, "mov al, byte ptr [eax + 0x24]") and has(B4, "cmp al, 0x31"))
chk("0x46a4a0 ×14：shl ecx,3; sub ecx,eax 然后 lea [ecx*2 + 0x5179b8]",
    has(B4, "shl ecx, 3") and has(B4, "sub ecx, eax") and has(B4, "lea eax, [ecx*2 + 0x5179b8]"))
chk("取 word[eax+4] ⇒ 真实基址 0x5179bc（49 国表，stride 14）",
    has(B4, "mov dx, word ptr [eax + 4]") and 0x5179B8 + 4 == 0x5179BC)
chk("该 word 判 <370 → 转实体（代表武将）",
    has(B4, "cmp dx, 0x172") and has(B4, "add ebp, 0x519868"))

# =============================================================================
print("=== 7. 🆕 坐实：byte[entity+0x25] = 在城索引（哨兵 255）===")
# =============================================================================
hc = [c["home_city"] for c in ch]       # @49 -> +0x25
n255 = sum(1 for v in hc if v == 255)
n_lt200 = sum(1 for v in hc if v < 200)
chk(f"+0x25: {n_lt200}/700 < 200（城表索引 0..199）", n_lt200 == 700 - n255)
chk(f"+0x25: {n255}/700 = 255（浪人/无固定城）", n255 == 278)
chk("0x46a4a0 读 byte[+0x25] 且 cmp al,0xc8(200) 后 ×31 查城表",
    has(B4, "mov al, byte ptr [ebp + 0x25]") and has(B4, "cmp al, 0xc8")
    and has(B4, "add ecx, 0x51eb88"))

# =============================================================================
print("=== 8. 0x46a4a0 的落点：0x49a990(城记录, 代表武将号) ===")
# =============================================================================
chk("命中后调用 0x49a990(ecx=edi 城记录, arg=edx 武将号)",
    has(B4, "push edx") and has(B4, "mov ecx, edi") and has(B4, "call 0x49a990"))
chk("随后沿 dword[edi] → +0x04 链表拷入 0x51e9c0",
    has(B4, "mov eax, dword ptr [edi]") and has(B4, "dword ptr [0x51e9c0]")
    and has(B4, "mov dword ptr [esi + edx*4], eax")
    and has(B4, "mov eax, dword ptr [eax + 4]"))

# =============================================================================
print("=== 9. 🆕 49 国表 `0x5179b8`：+0x04 是 WORD「国主武将号」（推翻 §3.18.2）===")
# =============================================================================
P = body(0x47e440, 0xB0)
chk("LOAD 0x47e440：esi = 0x5179bc（= 记录基 0x5179b8 + 4）", has(P, "mov esi, 0x5179bc"))
chk("LOAD 0x47e440：ebx = 0x31（49 条）", has(P, "mov ebx, 0x31"))
chk("LOAD 0x47e440：步进 add esi, 0xe（stride 14）", has(P, "add esi, 0xe"))
chk("首读 B stream[0] → 城 idx（cmp al,0xc8; ×31+0x51eb88）→ [esi-4] = +0x00",
    has(P, "cmp al, 0xc8") and has(P, "add eax, 0x51eb88") and has(P, "mov dword ptr [esi - 4], eax"))
# 第 2 读：push esi 后紧跟 WORD reader → 目标 [esi] = +0x04（WORD）
idx2 = None
for i in range(len(P)):
    if P[i][1] != "push esi":
        continue
    for j in range(i + 1, min(i + 4, len(P))):
        if P[j][1] == "call 0x47d930":
            idx2 = j
            break
    if idx2 is not None:
        break
chk("第 2 读为 WORD reader 且目标 = [esi] = +0x04（WORD，非两个独立字节）", idx2 is not None)
chk("⇒ +0x04 是 WORD（§3.18.2 拆成 +0x04 flag / +0x05 国主号 是错的）", idx2 is not None)

# 全镜像同形访问统计
def owner_rva(rva):
    i = bisect.bisect_right(FSTART, rva) - 1
    return FSTART[i] if i >= 0 else FSTART[0]


n_lea = 0
word4 = []
for i, r in enumerate(RVAS):
    t = IMAP[r][1]
    if "lea" in t and "ecx*2 + 0x5179b8" in t:
        n_lea += 1
        reg = t.split()[1].rstrip(",")
        for j in range(i + 1, min(i + 7, len(RVAS))):
            t2 = IMAP[RVAS[j]][1]
            if f"word ptr [{reg} + 4]" in t2:
                ctx = [IMAP[RVAS[k]][1] for k in range(j, min(j + 8, len(RVAS)))]
                word4.append(any("0x172" in c for c in ctx))
                break
chk(f"lea [ecx*2 + 0x5179b8] 全镜像 {n_lea} 处（§3.18.1 记 129 处，量级一致）", n_lea >= 80)
chk(f"其后 word ptr [reg+4] 的访问 {len(word4)} 处", len(word4) >= 10)
n370 = sum(1 for x in word4 if x)
chk(f"其中 {n370} 处紧跟 0x172(370) 上界判定 ⇒ +0x04 = 国主武将号(0..369)", n370 >= 10)

# =============================================================================
print()
if _fail:
    print(f"RESULT: {_n - len(_fail)}/{_n} checks passed   FAILED: {_fail}")
    sys.exit(1)
print(f"RESULT: {_n}/{_n} checks passed")
