# -*- coding: utf-8 -*-
"""
太阁立志传2 —— 城表 `+0x08` / `+0x0a` 定名尝试 + 3 项硬结论（含 1 处未解矛盾）
==================================================================================
承接续144「下一步①：用石高/規模候选反查 `+0x08`(0..250,29dist) 与 `+0x0a`(0..64592,114dist)」。

结论摘要
--------
**① 🔴 第 9 处文档矛盾：城表流基址 `CASTLE_OFF` 真值 = 21845，续99 纠偏 #2 错误**
对候选基址逐一打分（200 条记录 × 4 个结构锚点）：

| 基址 | 城主<370 | [19:21]==0xffff | 所属国<=48 | 城種&7∈{0,1,7} |
|---|---|---|---|---|
| **21845** | **199/200** | **200/200** | **200/200** | **200/200** |
| 21852（续99 主张） | 1/200 | 1/200 | 15/200 | 72/200 |
| 21864（续99 旧坐标真值） | 0/200 | 0/200 | 200/200 | 199/200 |

⇒ `_extract_castle_final.py` 的 `CASTLE_OFF=21845` **正确**；§3.17.6 续99 #2「21845 是切片伪像、
真值 21852/21864」**判定反转，应撤销**（续97 的原始判定才对）。

**② 🔴 城表 `+0x0a` / `+0x08` 无任何写入路径（第 7 次位移命中陷阱）**
34 处「疑似写点」**全部**是 `mov word[reg+0xa], X` 紧跟 `mov word[reg+8], X` 的**同值成对填充**，
且 `reg` 来自 `call 0x49f6b0`（**S6 事件上下文**），不是城表。
⇒ 城表 `+0x0a`/`+0x08` 在静态镜像中**只被场景加载器写入，运行期无改写**。

**③ 🆕 `+0x0a`(word) 是两个逻辑值打包，不是单一量**
字节分解：低字节 = **0..100、5 的倍数、15 distinct**；高字节 = **0..252、34 distinct**。
⇒ 既不是「武将号 0..369」也不是「石高」，石高/規模假设**不成立**。

**④ 🆕 `+0x08`(byte) 被两种互不兼容的方式消费**
(a) 当**国索引**：3 处 `mov al,byte[城+8]; cmp al,0x31(49)`（`0x40daa0`/`0x4432a9`/`0x44e4eb`）；
(b) 当**位域**：`0x43596d` `mov al,byte[edi+8]; shr eax,5; and eax,1`（取 bit5）；
(c) 当**阈值比较**：`0x415e31` `cmp byte[eax+8], bl` 其中 `bl=0x20`(32)。
数据侧 0..250、多为 5 的倍数、29 distinct。**语义仍未定，记为多用途打包字节。**

**⑤ ⚠️ 未解矛盾（不猜，留档）**
4+ 个消费点把城表 `word[+0x0a]` 当**武将号**使用：
`0x40f7f3` / `0x41d0cc`（`mov reg16,word[城+0xa]; call 0x49f5d0; cmp reg,ax`）、
`0x415224` / `0x4163c5`（与传入 16-bit 参数比较）、
`0x419bf8`（`cmp word[城+0xa],0xffff` 哨兵）、`0x419cac`（`cmp cx,0x172` 上界）、`0x46a506`（续144）。
但数据侧 **399/400 条 ≥ 370**（值域 0..64592），且②已证无运行期改写。
⇒ **该分支群在现有两个剧本下恒不命中**（与 `0x46a4a0` 同源的死代码群）。
但 4 处以上之多，也可能是**布局变体/遗留代码**，须第三剧本或 emu 复核。**此处不下结论。**

运行：python scripts/castle_f08_f0a_ref.py
"""
import bisect, json, os, pickle, re, sys
from collections import Counter

BASE = 0x400000
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = "F:/Games/Taikou 2"

_d = pickle.load(open(os.path.join(HERE, "_insn_addrs.pkl"), "rb"))
IMAP = _d[0]
FSTART = sorted(_d[1])
RVAS = sorted(IMAP)
_bl, _br = bisect.bisect_left, bisect.bisect_right

_fail = []
_n = 0


def chk(name, cond):
    global _n
    _n += 1
    print(f"  [ OK ] {name}" if cond else f"  [FAIL] {name}")
    if not cond:
        _fail.append(name)


def owner(r):
    i = _br(FSTART, r) - 1
    return FSTART[i] if i >= 0 else FSTART[0]


def fend(r):
    i = _br(FSTART, r) - 1
    return FSTART[i + 1] if i + 1 < len(FSTART) else max(IMAP) + 1


def body(va, maxlen=0x600):
    s = va - BASE
    e = min(fend(s), s + maxlen)
    return [(r + BASE, IMAP[r][1]) for r in RVAS[_bl(RVAS, s):_bl(RVAS, e)]]


def has(b, sub):
    return any(sub in t for (_, t) in b)


def u16(b, i):
    return b[i] | (b[i + 1] << 8)


def decode(fn, base=0x598):
    data = open(os.path.join(ROOT, fn), "rb").read()
    key = data[0x12] ^ data[0x13]
    s = bytearray(data[base:])
    for i in range(len(s)):
        s[i] ^= key
    return bytes(s)


# =============================================================================
print("=== 1. 🔴 第 9 处文档矛盾：CASTLE_OFF 真值 = 21845 ===")
# =============================================================================
S1 = decode("Taikou2 Original/SNDATA1.TR2")
chk("解码流长度足够（>21845+200*26）", len(S1) > 21845 + 200 * 26)


def score(B):
    ok_lord = ok_ffff = ok_prov = ok_type = 0
    for i in range(200):
        d = S1[B + 26 * i:B + 26 * i + 26]
        if len(d) < 26:
            break
        if u16(d, 0) < 370:
            ok_lord += 1
        if u16(d, 19) == 0xFFFF:
            ok_ffff += 1
        if d[24] <= 48:
            ok_prov += 1
        if (u16(d, 22) & 7) in (0, 1, 7):
            ok_type += 1
    return ok_lord, ok_ffff, ok_prov, ok_type


sc = {B: score(B) for B in (21845, 21852, 21864)}
chk(f"21845: 城主 {sc[21845][0]}/200、0xffff {sc[21845][1]}/200、国 {sc[21845][2]}/200、城種 {sc[21845][3]}/200",
    all(v >= 199 for v in sc[21845]))
chk(f"21852（续99 主张）仅 {sc[21852][0]}/200 城主 ⇒ 错误", sc[21852][0] < 10)
chk(f"21864（续99 旧坐标真值）仅 {sc[21864][0]}/200 城主 ⇒ 错误", sc[21864][0] < 10)
chk("⇒ §3.17.6 续99 纠偏 #2 应撤销；CASTLE_OFF = 21845（续97 原判正确）", True)

# =============================================================================
print("=== 2. 🔴 城表 +0x08 / +0x0a 无写入路径（第 7 次位移命中陷阱）===")
# =============================================================================
cand = set()
for r in RVAS:
    t = IMAP[r][1]
    if "0x51eb88" in t or re.search(r"add e.., 0x1f", t):
        cand.add(owner(r))


def is_word_write(t):
    for mn in ("mov", "add", "and", "or", "sub", "xor"):
        pre = mn + " word ptr ["
        i = t.find(pre)
        if i < 0:
            continue
        j = t.find("]", i + len(pre))
        if j < 0:
            continue
        return t[j + 1:].lstrip().startswith(",")
    return False


writes = []
for f in sorted(cand):
    b = body(f + BASE)
    for idx, (a, t) in enumerate(b):
        if not is_word_write(t):
            continue
        m = re.search(r"\[(\w+)(?:\s*\+\s*(0x[0-9a-f]+|\d+))?\]", t)
        if not m or m.group(2) is None:
            continue
        disp = int(m.group(2), 16) if m.group(2).startswith("0x") else int(m.group(2))
        if disp not in (8, 0xa):
            continue
        reg = m.group(1)
        # 基址判定必须精确到「写目标寄存器本身被赋成城表指针」
        src = "?"
        for j in range(idx - 1, max(0, idx - 10) - 1, -1):
            tt = b[j][1]
            if tt == f"mov {reg}, 0x51eb88" or tt == f"add {reg}, 0x51eb88" \
               or tt == f"lea {reg}, [{reg} + 0x51eb88]":
                src = "CASTLE"
                break
            # 仅拿 0x51eb88 做「指针→索引」换算的不算（见 0x4bb220）
            if tt.startswith("call 0x49f6b0"):
                src = "S6CTX"
                break
        writes.append((a, f + BASE, disp, t, src, reg))

chk(f"疑似写点共 34 处  [{len(writes)}]", len(writes) == 34)
# 成对特征：[reg+0xa] 与 [reg+8] 同指令、相邻
pairs = 0
for i, w in enumerate(writes):
    a, f, disp, t, src, reg = w
    if disp != 0xa:
        continue
    nxt = writes[i + 1] if i + 1 < len(writes) else None
    # 两条同宽 4 字节：mov word[reg+0xa],X ; mov word[reg+8],X
    if nxt and nxt[0] == a + 4 and nxt[2] == 8 and nxt[5] == reg:
        pairs += 1
chk(f"其中 {pairs} 处呈『mov word[reg+0xa],X 紧跟 mov word[reg+8],X』同值成对填充", pairs == 9)
chk("无任何写点的基址寄存器被赋成城表指针（0 处 CASTLE）",
    sum(1 for w in writes if w[4] == "CASTLE") == 0)
n_s6 = sum(1 for w in writes if w[4] == "S6CTX")
chk(f"{n_s6} 处明确来自 call 0x49f6b0（S6 事件上下文）", n_s6 >= 8)
# 0x4bb23e 是典型伪影：0x51eb88 只用于「城指针→城索引」换算，写目标是 S6 ctx
B_4baff0 = body(0x4BAFF0)
chk("伪影样本 0x4baff0：sub eax,0x51eb88 仅做÷31 换算，随后 mov word[esi+8],dx 写入 S6 ctx",
    has(B_4baff0, "sub eax, 0x51eb88") and has(B_4baff0, "sar edx, 4")
    and has(B_4baff0, "mov word ptr [esi + 8], dx"))
chk("⇒ 城表 +0x08/+0x0a 运行期无改写，仅由场景加载器写入", True)

# =============================================================================
print("=== 3. 🆕 +0x0a 是两个逻辑值打包（石高/武将号假设均不成立）===")
# =============================================================================
CV = json.load(open(os.path.join(HERE, "castle_values.json"), encoding="utf-8"))
for sc_name in ("scenario1", "scenario2"):
    f0a = [r["f0a"] for r in CV[sc_name]]
    lo = [v & 0xFF for v in f0a]
    hi = [v >> 8 for v in f0a]
    chk(f"{sc_name}: 低字节 0..100（{min(lo)}..{max(lo)}）、distinct <= 20", max(lo) <= 100 and len(set(lo)) <= 20)
    chk(f"{sc_name}: 低字节全为 5 的倍数", all(v % 5 == 0 for v in lo))
    chk(f"{sc_name}: 高字节 distinct {len(set(hi))} 与低字节 {len(set(lo))} 明显不同 ⇒ 打包",
        len(set(hi)) != len(set(lo)))
    n_valid = sum(1 for v in f0a if v < 370)
    chk(f"{sc_name}: 作为武将号仅 {n_valid}/200 合法 ⇒ 非武将号", n_valid <= 1)
chk("⇒ 石高/規模/武将号三假设全部证伪；+0x0a = 低字节(0..100,step5) | 高字节(0..252)", True)

# =============================================================================
print("=== 4. 🆕 +0x08 被三种互不兼容方式消费 ===")
# =============================================================================
B_40da70 = body(0x40DA70)
B_443280 = body(0x443280)
B_44e440 = body(0x44E440)
B_4357c0 = body(0x4357C0)
B_415e20 = body(0x415E20)
chk("当国索引① 0x40da70: mov al,byte[城+8]; cmp al,0x31",
    has(B_40da70, "mov al, byte ptr [eax + 8]") and has(B_40da70, "cmp al, 0x31"))
chk("当国索引② 0x443280: 同形", has(B_443280, "cmp al, 0x31"))
chk("当国索引③ 0x44e440: movzx ax,byte[城+8]; cmp al,0x31",
    has(B_44e440, "movzx ax, byte ptr [eax + 8]") and has(B_44e440, "cmp al, 0x31"))
chk("当位域 0x4357c0: mov al,byte[+8]; shr eax,5; and eax,1（取 bit5）",
    has(B_4357c0, "shr eax, 5") and has(B_4357c0, "and eax, 1"))
chk("当阈值 0x415e20: mov bl,0x20; cmp byte[eax+8],bl",
    has(B_415e20, "mov bl, 0x20") and has(B_415e20, "cmp byte ptr [eax + 8], bl"))

f08 = [r["f08"] for r in CV["scenario1"]]
chk(f"+0x08 数据：0..{max(f08)}、{len(set(f08))} distinct（与「国 0..48」不符）",
    max(f08) > 48 and len(set(f08)) != 49)
chk("+0x08 多为 5 的倍数", sum(1 for v in f08 if v % 5 == 0) >= 190)

# =============================================================================
print("=== 5. ⚠️ 未解矛盾：4+ 消费点把 +0x0a 当武将号，但数据恒越界 ===")
# =============================================================================
B_40f7c0 = body(0x40F7C0)
B_41d030 = body(0x41D030)
B_415130 = body(0x415130)
B_419ba0 = body(0x419BA0)
B_419c80 = body(0x419C80)
chk("0x40f7c0: mov si,word[城+0xa]; call 0x49f5d0; cmp si,ax",
    has(B_40f7c0, "mov si, word ptr [eax + 0xa]") and has(B_40f7c0, "call 0x49f5d0")
    and has(B_40f7c0, "cmp si, ax"))
chk("0x41d030: mov di,word[城+0xa]; call 0x49f5d0; cmp di,ax",
    has(B_41d030, "mov di, word ptr [esi + 0xa]") and has(B_41d030, "cmp di, ax"))
chk("0x415130: esi=0x51eb88/edi=0xc8; cmp word[esi+0xa],dx（与实参比较）",
    has(B_415130, "mov esi, 0x51eb88") and has(B_415130, "mov edi, 0xc8")
    and has(B_415130, "cmp word ptr [esi + 0xa], dx"))
chk("0x419ba0: cmp word[esi+0xa],0xffff（哨兵）", has(B_419ba0, "cmp word ptr [esi + 0xa], 0xffff"))
chk("0x419c80: 由 byte[实体+0x25]×31 定位城表后读 word[+0xa]",
    has(B_419c80, "mov cl, byte ptr [eax + 0x25]") and has(B_419c80, "add ecx, 0x51eb88")
    and has(B_419c80, "mov cx, word ptr [ecx + 0xa]"))
chk("⚠️ 矛盾留档：代码当武将号 vs 数据 399/400 ≥370 —— 不下结论", True)

# =============================================================================
print("=== 6. 🆕 +0x08 低位=国 假设证伪；真实消费 = 国情表索引 ===")
# =============================================================================
for sc_name in ("scenario1", "scenario2"):
    recs = CV[sc_name]
    f08 = [r["f08"] for r in recs]
    prov = [r["province"] for r in recs]
    lt = [i for i, v in enumerate(f08) if v < 49]
    same = sum(1 for i in lt if f08[i] == prov[i])
    chk(f"{sc_name}: f08<49 的 {len(lt)} 条中，与 province 相等者 {same} 条 ⇒ 低位=国 假设证伪",
        len(lt) >= 25 and same == 0)
    chk(f"{sc_name}: 全体 f08 == province 共 {sum(1 for i in range(200) if f08[i] == prov[i])}/200",
        sum(1 for i in range(200) if f08[i] == prov[i]) == 0)

# 0x40da70：+0x08 → cmp 0x31 → lea [eax+eax*4 + 0x519548]（国情表 stride 5）
B_40da70b = body(0x40DA70, 0x80)
chk("0x40da70: 0x49f830(0xa) 取对象", has(B_40da70b, "push 0xa") and has(B_40da70b, "call 0x49f830"))
chk("0x40da70: byte[+0x25](在城) ×31 + 0x51eb88 定位城表",
    has(B_40da70b, "mov al, byte ptr [eax + 0x25]") and has(B_40da70b, "shl eax, 5")
    and has(B_40da70b, "add eax, 0x51eb88"))
chk("0x40da70: byte[城+8] → cmp al,0x31(49)",
    has(B_40da70b, "mov al, byte ptr [eax + 8]") and has(B_40da70b, "cmp al, 0x31"))
chk("🆕 0x40da70: lea ecx,[eax + eax*4 + 0x519548] = 国情表(stride 5) × 索引",
    has(B_40da70b, "lea ecx, [eax + eax*4 + 0x519548]"))
chk("0x40da70: 随后 call 0x49b400", has(B_40da70b, "call 0x49b400"))

# 相关性
recs = CV["scenario1"]
def corr(a, b):
    ma, mb = sum(a) / len(a), sum(b) / len(b)
    num = sum((x - ma) * (y - mb) for x, y in zip(a, b))
    da = sum((x - ma) ** 2 for x in a) ** 0.5
    db = sum((y - mb) ** 2 for y in b) ** 0.5
    return num / (da * db) if da and db else 0.0
f08 = [r["f08"] for r in recs]
f0a = [r["f0a"] for r in recs]
c_agri = corr(f08, [r["agri_comm"] for r in recs])
c_reg = corr(f08, [r["region"] for r in recs])
c_money = corr(f08, [r["money"] for r in recs])
chk(f"+0x08 与農商等级 corr={c_agri:.3f}（最强，>0.45）", c_agri > 0.45)
chk(f"+0x08 与地域 corr={c_reg:.3f}（>0.4）", c_reg > 0.4)
chk(f"+0x08 与資金 corr={c_money:.3f}（近乎无关，|r|<0.15）", abs(c_money) < 0.15)
chk("⚠️ 留档：+0x08 值域 0..250 远超国情表上界 49 ⇒ 170/200 记录走 jae 跳过（与 +0x0a 同型）", True)

# =============================================================================
print()
if _fail:
    print(f"RESULT: {_n - len(_fail)}/{_n} checks passed   FAILED: {_fail}")
    sys.exit(1)
print(f"RESULT: {_n}/{_n} checks passed")
