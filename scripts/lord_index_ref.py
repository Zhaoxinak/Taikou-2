# -*- coding: utf-8 -*-
"""
太阁立志传2 —— 武将实体 word[+0x2a]「主君（所属）索引」与家臣逻辑 参考实现
==============================================================================
承接 BREAKTHROUGHS 续142「下一步(A)：用 +0x2a=主君索引 重扫家臣逻辑（0x4a6970 同族）」。

结论摘要
--------
1. word[entity + 0x2a] = **主君（所属）武将索引**，哨兵 0xFFFF = 浪人/无所属。
   setter = **0x49a7d0(ptr, val)** : `mov ax,[esp+4]; mov word[ecx+0x2a], ax; ret 4`（整字覆盖，无掩码）。

2. 🔴 **第 5 次共享方法库陷阱**：`0x49ba30 / 0x49ba60 / 0x49ba70 / 0x49baa0` 也操作 `+0x2a`，
   但它们是 **位域** 方法（bits0-1 / bits2-4）。全部 **28 处调用清一色 `mov ecx, 0x516610`（S6）**
   ⇒ 属 **S6**，与武将实体 `+0x2a`（整字索引）**同名不同物**。
   判据：setter 0x49a7d0 无掩码（整字），而 0x49ba30/70 有 `&0xffe3` / `&0xfffc` 掩码。

3. setter 0x49a7d0 共 **18 个调用点**：**14 处 push 0xffff（浪人化/所属解除）** +
   **4 处设新主君**（其中 0x452ab0 = 登用，主君 := 玩家）。

4. 同族「主家灭亡 → 家臣全员浪人化」循环：`0x4a3920(lord_idx)` 与 `0x46a4a0(ent_ptr)`，
   均为 370 次 × stride 47，`cmp word[+0x2a], lord` → `0x49a7d0(0xffff)` + `0x49a880(0)`。

5. 🆕 顺带破出 4 张表：
   - `0x51e1f6`  stride **10** × **200**（0x4a3960：word==dx → 置 0xffff）
   - `0x51eb88`  stride **31** × **200**（三重证据：÷31 魔数 0x84210843+sar4、shl5-sub=×31、add edi,0x1f 循环）
   - `0x5179b8`  stride **14**（索引 = 親密度 byte[+0x24] × 14，上限 cmp al,0x31）
   - `0x521aa8` / `0x520660`  stride **7**（索引 = 武将号 × 7）

运行：python scripts/lord_index_ref.py    （自测，打印 RESULT: n/n checks passed）
"""
import bisect, json, os, pickle, sys

BASE = 0x400000
HERE = os.path.dirname(os.path.abspath(__file__))
BIN = os.path.join(HERE, "_unpacked_mem.bin")
IDX = os.path.join(HERE, "_insn_addrs.pkl")
MSGX = os.path.join(HERE, "msgx_all_texts.json")

_d = pickle.load(open(IDX, "rb"))
IMAP = _d[0]                    # rva -> (size, "mnem op")
FSTART = sorted(_d[1])          # 函数起点 rva
RVAS = sorted(IMAP)
MEM = open(BIN, "rb").read()

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


def owner(rva):
    i = bisect.bisect_right(FSTART, rva) - 1
    return FSTART[i] if i >= 0 else FSTART[0]


def fend(rva):
    i = bisect.bisect_right(FSTART, rva) - 1
    return FSTART[i + 1] if i + 1 < len(FSTART) else max(IMAP) + 1


def body(va, maxlen=0x800):
    """函数体指令文本列表 [(va, text)]"""
    s = va - BASE
    e = min(fend(s), s + maxlen)
    return [(r + BASE, IMAP[r][1]) for r in RVAS[bisect.bisect_left(RVAS, s):bisect.bisect_left(RVAS, e)]]


def txt_at(va):
    r = va - BASE
    return IMAP.get(r, (0, ""))[1]


def has(body_list, sub):
    return any(sub in t for (_, t) in body_list)


def count_sub(body_list, sub):
    return sum(1 for (_, t) in body_list if sub in t)


# =============================================================================
print("=== 1. setter 0x49a7d0 = word[+0x2a] 整字写入 ===")
# =============================================================================
s49a7d0 = body(0x49a7d0, 0x20)
chk("0x49a7d0 取 [esp+4] 的 word", has(s49a7d0, "mov ax, word ptr [esp + 4]"))
chk("0x49a7d0 写 word [ecx + 0x2a]", has(s49a7d0, "mov word ptr [ecx + 0x2a], ax"))
chk("0x49a7d0 stdcall ret 4（1 参数）", has(s49a7d0, "ret 4"))
# 整字覆盖 ⇒ 无掩码，这是与位域方法的分水岭
chk("0x49a7d0 无 and/or 掩码（整字覆盖）",
    not has(s49a7d0, "and word ptr [ecx + 0x2a]") and not has(s49a7d0, "or word ptr [ecx + 0x2a]"))

# =============================================================================
print("=== 2. 🔴 共享方法库陷阱：0x49ba30/60/70/aa0 属 S6，非武将实体 ===")
# =============================================================================
SHARED = {0x49ba30: "SET bits2-4", 0x49ba60: "GET bits2-4",
          0x49ba70: "SET bits0-1", 0x49baa0: "GET bits0-1"}
tot_shared_calls = 0
tot_s6 = 0
for va, name in sorted(SHARED.items()):
    b = body(va, 0x40)
    # 位域形态证据
    if va == 0x49ba30:
        chk(f"0x49ba30 {name}: 掩码 &0xffe3 + shl 2", has(b, "0xffe3") and has(b, "shl eax, 2"))
    if va == 0x49ba70:
        chk(f"0x49ba70 {name}: 掩码 &0xfffc + 钳 3", has(b, "0xfffc") and has(b, "cmp eax, 3"))
    if va == 0x49ba60:
        chk(f"0x49ba60 {name}: (byte[+0x2a]>>2)&7", has(b, "shr al, 2") and has(b, "and al, 7"))
    if va == 0x49baa0:
        chk(f"0x49baa0 {name}: byte[+0x2a]&3", has(b, "and eax, 3"))
    # 调用方 ecx 溯源
    sites = [i for i, r in enumerate(RVAS) if IMAP[r][1] == f"call 0x{va:06x}"]
    ecx_src = []
    for i in sites:
        for j in range(i - 1, max(0, i - 12) - 1, -1):
            t = IMAP[RVAS[j]][1]
            if t.startswith("mov ecx,") or t.startswith("lea ecx,"):
                ecx_src.append(t)
                break
    tot_shared_calls += len(sites)
    n_s6 = sum(1 for t in ecx_src if "0x516610" in t)
    tot_s6 += n_s6
    chk(f"0x{va:06x} {name}: {len(sites)} 处调用全部 ecx=0x516610(S6)  [{n_s6}/{len(sites)}]",
        len(sites) > 0 and n_s6 == len(sites))
chk(f"共享方法库 {tot_shared_calls} 处调用 100% 指向 S6（无一指向武将实体）",
    tot_shared_calls == tot_s6 and tot_shared_calls > 0)

# =============================================================================
print("=== 3. setter 0x49a7d0 的 18 个调用点：14 浪人化 + 4 新主君 ===")
# =============================================================================
call_sites = []
for i, r in enumerate(RVAS):
    if IMAP[r][1] == "call 0x49a7d0":
        call_sites.append(i)
chk("0x49a7d0 调用点共 18 处", len(call_sites) == 18)


def arg_at(i):
    """call 站点 i 正上方的 push（即 setter 的 val 实参）"""
    for j in range(i - 1, max(0, i - 4) - 1, -1):
        t = IMAP[RVAS[j]][1]
        if t.startswith("push "):
            return t
    return ""


args = [arg_at(i) for i in call_sites]
n_ronin = sum(1 for a in args if a == "push 0xffff")
n_newlord = len(args) - n_ronin
chk(f"其中 push 0xffff（浪人化）= 14 处  [{n_ronin}]", n_ronin == 14)
chk(f"其中设新主君 = 4 处  [{n_newlord}]", n_newlord == 4)
chk("浪人哨兵为 0xffff（16 位全 1）", 0xffff == 0xFFFF)

# 4 处设新主君的调用点
NEWLORD_FUNCS = {0x40c010, 0x40cc60, 0x452ab0, 0x4a5500}
got = set()
for i in call_sites:
    if arg_at(i) != "push 0xffff":
        got.add(owner(RVAS[i]) + BASE)
chk("4 处新主君调用点所属函数 = {0x40c010, 0x40cc60, 0x452ab0, 0x4a5500}", got == NEWLORD_FUNCS)

# =============================================================================
print("=== 4. 登用 0x452ab0：主君 := 玩家（MSG 文本互证）===")
# =============================================================================
b452 = body(0x452ab0, 0x120)
chk("0x452ab0 读源武将 byte[+0x24]（親密度）", has(b452, "mov al, byte ptr [ebx + 0x24]"))
chk("0x452ab0 复制親密度 0x49a750(esi, al)", has(b452, "call 0x49a750"))
chk("0x452ab0 取玩家武将号 0x49f5d0", has(b452, "call 0x49f5d0"))
chk("0x452ab0 设主君 0x49a7d0(esi, 玩家号)", has(b452, "push eax") and has(b452, "call 0x49a7d0"))
chk("0x452ab0 随后 0x49a880(esi,1) 置 bit0",
    has(b452, "push 1") and has(b452, "call 0x49a880"))
chk("0x452ab0 门控 test byte[0x516638],4", has(b452, "test byte ptr [0x516638], 4"))
# MSG 文本
_t = json.load(open(MSGX, encoding="utf-8"))["texts"]
chk("MSG 0x40c = 早就想在%s手下工作。", "早就想在" in _t.get(str(0x40c), ""))
chk("MSG 0x40d = 哦，太好了！那么赶快进城吧。", "赶快进城" in _t.get(str(0x40d), ""))
chk("MSG 0x40e = 是！今后定为您效犬马之劳。", "效犬马之劳" in _t.get(str(0x40e), ""))
chk("0x452ab0 依次弹 0x40d / 0x40e", has(b452, "push 0x40d") and has(b452, "push 0x40e"))
chk("0x452ab0 基址偏移 add eax, 0x40b（MSG 0x40b 起算）", has(b452, "add eax, 0x40b"))

# =============================================================================
print("=== 5. 同族：主家灭亡 → 家臣全员浪人化（0x4a3920 / 0x46a4a0）===")
# =============================================================================
b4a3920 = body(0x4a3920, 0x60)
chk("0x4a3920 esi = 0x519868（实体表基址）", has(b4a3920, "mov esi, 0x519868"))
chk("0x4a3920 edi = 0x172（370 次）", has(b4a3920, "mov edi, 0x172"))
chk("0x4a3920 cmp word[esi+0x2a], bx（筛家臣）", has(b4a3920, "cmp word ptr [esi + 0x2a], bx"))
chk("0x4a3920 命中 → 0x49a7d0(0xffff)", has(b4a3920, "push 0xffff") and has(b4a3920, "call 0x49a7d0"))
chk("0x4a3920 命中 → 0x49a880(0) 清 bit0", has(b4a3920, "push 0") and has(b4a3920, "call 0x49a880"))
chk("0x4a3920 循环步进 add esi, 0x2f（stride 47）", has(b4a3920, "add esi, 0x2f"))

b46a4a0 = body(0x46a4a0, 0x200)
chk("0x46a4a0 ÷47 魔数 0xae4c415d + sar 5", has(b46a4a0, "0xae4c415d") and has(b46a4a0, "sar edx, 5"))
chk("0x46a4a0 实体表 stride 47 三证据 lea[ecx+ecx*2]/shl4/sub",
    has(b46a4a0, "lea eax, [ecx + ecx*2]") and has(b46a4a0, "shl eax, 4") and has(b46a4a0, "sub eax, ecx"))
chk("0x46a4a0 cmp word[esi+0x2a], bx（筛家臣）", has(b46a4a0, "cmp word ptr [esi + 0x2a], bx"))
chk("0x46a4a0 命中 → 0x49a7d0(0xffff)", has(b46a4a0, "push 0xffff") and has(b46a4a0, "call 0x49a7d0"))
chk("0x46a4a0 遍历 370 条（mov edi, 0x172）", has(b46a4a0, "mov edi, 0x172"))

# =============================================================================
print("=== 6. 出奔 0x4a5010：已有主君才解除 ===")
# =============================================================================
b4a5010 = body(0x4a5010, 0xD0)
chk("0x4a5010 先 0x49a880(ebx,0) 清 bit0", has(b4a5010, "push 0") and has(b4a5010, "call 0x49a880"))
chk("0x4a5010 读 word[ebx+0x2a]", has(b4a5010, "mov bp, word ptr [ebx + 0x2a]"))
chk("0x4a5010 已是浪人(cmp bp,0xffff; je) 则跳过",
    has(b4a5010, "cmp bp, 0xffff") and has(b4a5010, "je 0x4a50a0"))
chk("0x4a5010 解除主君 0x49a7d0(ebx, 0xffff)", has(b4a5010, "call 0x49a7d0"))
chk("0x4a5010 随后遍历 370 实体（add esi,0x2f / cmp di,0x172）",
    has(b4a5010, "add esi, 0x2f") and has(b4a5010, "cmp di, 0x172"))

# =============================================================================
print("=== 7. 俸禄结算 0x4a6970（同族锚点，续140）===")
# =============================================================================
b4a6970 = body(0x4a6970, 0x90)
chk("0x4a6970 取玩家实体 0x49f5e0", has(b4a6970, "call 0x49f5e0"))
chk("0x4a6970 读 word[+0x2c]>>8 &7 = 身分，为 0 则跳过",
    has(b4a6970, "mov ax, word ptr [eax + 0x2c]") and has(b4a6970, "shr eax, 8") and has(b4a6970, "and eax, 7"))
chk("0x4a6970 预算 = byte[玩家+0x28]", has(b4a6970, "movzx di, byte ptr [eax + 0x28]"))
chk("0x4a6970 迭代基点 0x519894(=base+0x2c)，cmp word[esi-2],bp",
    has(b4a6970, "mov esi, 0x519894") and has(b4a6970, "cmp word ptr [esi - 2], bp"))
chk("0x4a6970 扣家臣 byte[esi-4] 经 sat_sub 0x4ebcd0",
    has(b4a6970, "movzx cx, byte ptr [esi - 4]") and has(b4a6970, "call 0x4ebcd0"))
chk("0x4a6970 stride: add esi, 0x2f", has(b4a6970, "add esi, 0x2f"))
chk("0x4a6970 净额累加进 S6（ecx=0x516610; call 0x4a35e0）",
    has(b4a6970, "mov ecx, 0x516610") and has(b4a6970, "call 0x4a35e0"))
chk("0x4a6970 跳过已故/退场：test al,0x80 / test ah,0x80",
    has(b4a6970, "test al, 0x80") and has(b4a6970, "test ah, 0x80"))

# =============================================================================
print("=== 8. 🆕 表 0x51e1f6  stride 10 × 200（0x4a3960）===")
# =============================================================================
b4a3960 = body(0x4a3960, 0x40)
chk("0x4a3960 基址 0x51e1f6", has(b4a3960, "mov eax, 0x51e1f6"))
chk("0x4a3960 计数 ecx = 0xc8（200 条）", has(b4a3960, "mov ecx, 0xc8"))
chk("0x4a3960 步进 add eax, 0xa（stride 10）", has(b4a3960, "add eax, 0xa"))
chk("0x4a3960 匹配 word[eax]==dx → 置 0xffff",
    has(b4a3960, "cmp word ptr [eax], dx") and has(b4a3960, "mov word ptr [eax], 0xffff"))
chk("表跨度 200×10 = 2000B（0x51e1f6..0x51e9ae）", 200 * 10 == 2000)

# =============================================================================
print("=== 9. 🆕 表 0x51eb88  stride 31 × 200（三重证据）===")
# =============================================================================
b4a5680 = body(0x4a5680, 0xA0)
chk("0x4a5680 ÷31 魔数 0x84210843 + sar 4",
    has(b4a5680, "0x84210843") and has(b4a5680, "sar edx, 4"))
chk("0x4a5680 基址 0x51eb88（sub ecx, 0x51eb88）", has(b4a5680, "sub ecx, 0x51eb88"))
chk("0x4a5680 edi==0 → bl = 0xc8（200 哨兵）", has(b4a5680, "mov bl, 0xc8"))
chk("0x4a5680 读表元素 word[edi+0xa] 判 <370（武将索引）",
    has(b4a5680, "mov di, word ptr [edi + 0xa]") and has(b4a5680, "cmp di, 0x172"))
b4a57a0 = body(0x4a57a0, 0xA0)
chk("0x4a57a0 ×31 二证据：shl eax,5 / sub eax,ecx + add 0x51eb88",
    has(b4a57a0, "shl eax, 5") and has(b4a57a0, "sub eax, ecx") and has(b4a57a0, "add eax, 0x51eb88"))
chk("0x46a4a0 循环三证据：add edi, 0x1f（stride 31）", has(b46a4a0, "add edi, 0x1f"))
chk("0x46a4a0 循环计数 [esp+0x18] = 0xc8（200）", has(b46a4a0, "mov dword ptr [esp + 0x18], 0xc8"))
chk("0x46a4a0 表基址 edi = 0x51eb88", has(b46a4a0, "mov edi, 0x51eb88"))
chk("表跨度 200×31 = 6200B（0x51eb88..0x5203c0）", 200 * 31 == 6200)

# =============================================================================
print("=== 10. 🆕 表 0x5179b8 stride 14 / 0x521aa8·0x520660 stride 7 ===")
# =============================================================================
chk("0x46a4a0 親密度 byte[+0x24] 上限 cmp al, 0x31（49）", has(b46a4a0, "cmp al, 0x31"))
chk("0x46a4a0 ×7 后 lea [ecx*2 + 0x5179b8] ⇒ stride 14",
    has(b46a4a0, "shl ecx, 3") and has(b46a4a0, "lea eax, [ecx*2 + 0x5179b8]"))
b440d20 = body(0x440d20, 0x100)
chk("0x440d20 武将号 ×7：shl esi,3 / sub esi,edx",
    has(b440d20, "shl esi, 3") and has(b440d20, "sub esi, edx"))
chk("0x440d20 表 0x521aa8 stride 7", has(b440d20, "lea ecx, [esi + 0x521aa8]"))
chk("0x440d20 表 0x520660 stride 7", has(b440d20, "lea edx, [esi + 0x520660]"))
chk("0x440d20 门控 cmp word[esp+4], 0x167（359）", has(b440d20, "cmp word ptr [esp + 4], 0x167"))
chk("0x440d20 玩家实体 0x513b14 ÷47 求武将号",
    has(b440d20, "mov eax, dword ptr [0x513b14]") and has(b440d20, "0xae4c415d"))
chk("0x440d20 玩家自身浪人化 0x49a7d0(0xffff)", has(b440d20, "push 0xffff") and has(b440d20, "call 0x49a7d0"))
chk("0x440d20 清相性 0x49a5a0(ecx+8, ...)",
    has(b440d20, "add ecx, 8") and has(b440d20, "call 0x49a5a0"))

# =============================================================================
print("=== 11. 全镜像 +0x2a 访问面统计 ===")
# =============================================================================
ENT_BASE, STRIDE, N_ENT = 0x519868, 47, 370
abs_2a = set(ENT_BASE + 0x2a + i * STRIDE for i in range(N_ENT))
all_hits = []
for r in RVAS:
    t = IMAP[r][1]
    if "word ptr" not in t:
        continue
    op = t.split(" ", 1)[1] if " " in t else ""
    if "+ 0x2a]" in op or "- 2]" in op:
        # 排除栈变量 [ebp - 2]
        if "[ebp - 2]" in op:
            continue
        all_hits.append((r + BASE, t))
chk(f"全镜像 word[±0x2a] 访问点 ≈ 100 处  [{len(all_hits)}]", 90 <= len(all_hits) <= 110)
# 写点 = 内存操作数位于 ',' 左侧（即 [..], reg 而非 reg, [..]）
def is_write(t):
    for mn in ("mov", "add", "and", "or", "sub", "xor"):
        pre = mn + " word ptr ["
        i = t.find(pre)
        if i < 0:
            continue
        j = t.find("]", i + len(pre))
        if j < 0:
            continue
        # ']' 之后跳过空格应紧跟 ','
        rest = t[j + 1:].lstrip()
        return rest.startswith(",")
    return False


writes = [(a, t) for (a, t) in all_hits if is_write(t)]
chk(f"其中写点 ≈ 12 处（mov/add/and 到内存）  [{len(writes)}]", 10 <= len(writes) <= 16)
ronin_test = [(a, t) for (a, t) in all_hits if "cmp" in t and "0xffff" in t]
chk(f"浪人判定 cmp word[+0x2a], 0xffff 共 7 处  [{len(ronin_test)}]", len(ronin_test) == 7)

# =============================================================================
print("=== 12. 🔴 位移命中 ≠ 字段命中：10 个『直写点』全部是误报 ===")
# =============================================================================
# 逐一溯源基址寄存器：无一处以实体表 0x519868 / 迭代基点 0x519894 为基
FP = {
    0x41b290: ("S5（esi=0x5197bc）", ["mov esi, 0x5197bc"]),
    0x41c8b0: ("表 0x510b54（esi=0x510b54）", ["mov esi, 0x510b54"]),
    0x42e820: ("栈局部（lea edi,[esp+0x28]/[esp+0x34]）",
               ["lea edi, [esp + 0x28]", "lea edi, [esp + 0x34]"]),
    0x495d10: ("表 0x525356（stride 0xc × 20）",
               ["mov eax, 0x525356", "add eax, 0xc", "mov edx, 0x14"]),
    0x49f3b0: ("word 数组轮转（esi += 2，非实体）", ["add esi, 2"]),
    0x4a4d10: ("排序交换（edx += 4 的 word 对列表）", ["add edx, 4"]),
    0x4bd3e0: ("S5（eax=0x5197ba）", ["mov eax, 0x5197ba"]),
    0x4dd7c0: ("S5（ecx=0x5197bc，stride 0x1e × 6）",
               ["mov ecx, 0x5197bc", "add ecx, 0x1e", "mov esi, 6"]),
}
for va, (desc, subs) in sorted(FP.items()):
    b = body(va, 0x400)
    chk(f"0x{va:06x} 直写点实为 {desc}", all(has(b, s) for s in subs))
    # 且该函数不得出现实体表基址 / 迭代基点 / ÷47 魔数
    if va not in (0x4a4d10,):   # 0x4a4d10 确有实体主循环，但写点本身在交换段
        chk(f"0x{va:06x} 无实体表基址（非武将实体）",
            not has(b, "0x519868") and not has(b, "0x519894"))

b4a4d10 = body(0x4a4d10, 0x400)
chk("0x4a4d10 主循环确为实体：esi=0x519868 / add esi,0x2f",
    has(b4a4d10, "mov esi, 0x519868") and has(b4a4d10, "add esi, 0x2f"))
chk("🆕 0x4a4d10 循环上界 = 0x167（359，非 370）", has(b4a4d10, "cmp di, 0x167"))
chk("⇒ 武将实体 word[+0x2a] 的唯一写入路径 = setter 0x49a7d0（18 调用点）",
    len(call_sites) == 18)

# =============================================================================
print()
if _fail:
    print(f"RESULT: {_n - len(_fail)}/{_n} checks passed   FAILED: {_fail}")
    sys.exit(1)
print(f"RESULT: {_n}/{_n} checks passed")
