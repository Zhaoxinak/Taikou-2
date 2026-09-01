# -*- coding: utf-8 -*-
"""
太阁立志传2 —— 国名 getter `0x49b400` / 国名别名 getter `0x49b440`（築城·改称事件）
======================================================================================
承接续146「下一步(A)：反查 `0x519548` 国情表内容（`0x49b400` 的语义）」。

结论摘要
--------
**① 🆕 `0x49b400(国情表记录指针)` = 国名 getter**（全库此前无记录）
```
test ecx,ecx ; jne +L
  mov edx, 0x31                       ; 空指针 → 索引 49（哨兵，越过 49 国）
L: sub ecx, 0x519548
   mov eax, 0x66666667 ; imul ecx ; sar edx,1   ; ÷5 = 国情表 stride
   ...                             ; edx = 国 id (0..48)
   lea eax, [edx + edx*8 + 0x506ca8] ; = 0x506ca8 + id*9（名称总表 stride 9）
   ret
```
- **÷5 魔数 `0x66666667` + `sar edx,1`** 坐实国情表 stride = 5（与 §3.9.7 一致）。
- `0x506ca8` = 名称索引总表（stride **9**，370 条；**国名占前 49 条** 0..48）。
- 空指针哨兵索引 **49** —— 恰好越过 49 国，取到城町名块之首（防御性设计）。

**② 🆕 `0x49b440(国情表记录指针)` = 国名别名 getter（築城/改称后改称）**
先同样 ÷5 得国 id（`si`），再对 **4 个特定国**做条件替换。**四条全部命中战国史实**：

| 国 id | 本名 | 条件（`tbl = 0x5203c0`） | 别名 | 别名 VA | 史实 |
|---|---|---|---|---|---|
| `0x11`=17 | **美濃** | `0x49c390(tbl,4)` ∧ `0x49c3d0(tbl,4)` ∧ `word[0x520604]&0x400` | **岐阜** | `0x5076c8` | 1567 信长稻叶山城改称 |
| `0x17`=23 | **北近江** | `0x49c390(tbl, 0xf)` | **长滨** | `0x5076da` | 1573 秀吉筑长滨城 |
| `0x18`=24 | **南近江** | (`0x49c390(tbl,8)` ∧ ¬`0x49c3d0(tbl,8)`) ∨ (`byte[tbl]==8` ∧ ¬`0x49c3d0(tbl,8)`) | **安土** | `0x5076d1` | 1576 信长筑安土城 |
| `0x1c`=28 | **摂津** | `0x49c390(tbl, 0x26)` | **大阪** | `0x5076e3` | 1583 秀吉筑大阪城 |

相邻别名串（同一字符串块，供后续复用）：
`0x507692 饫肥` / `0x50769b 鹿儿岛` / `0x5076a4 大口` / `0x5076ad 加治木` /
`0x5076b6 伊集院` / `0x5076bf 大隅高山` / `0x5076c8 岐阜` / `0x5076d1 安土` /
`0x5076da 长滨` / `0x5076e3 大阪`

**③ 调用链闭合**：`0x40da70` = 「`0x49f830(0xa)` 取对象 → `byte[+0x25]`(在城) → ×31 定位城表
→ `byte[城+0x08]` → `cmp al,0x31` → 国情表 `0x519548` → **`0x49b400` 取国名**」。
⚠️ 但 `byte[城+0x08]` 数据值域 0..250（170/200 越过上界 49），矛盾留档见 **§3.17.9**。

运行：python scripts/province_name_alias_ref.py
"""
# <auto: portable root (injected by _fix_win_paths.py)>
import os as _os
def _find_root(_p):
    for _ in range(8):
        if _os.path.isdir(_os.path.join(_p, 'scripts')) and _os.path.isfile(_os.path.join(_p, 'project.godot')):
            return _p
        _p = _os.path.dirname(_p)
    return _p
_ROOT = _find_root(_os.path.dirname(_os.path.abspath(__file__)))
# </auto: portable root>

import bisect, json, os, pickle, sys

BASE = 0x400000
HERE = os.path.dirname(os.path.abspath(__file__))

_d = pickle.load(open(os.path.join(HERE, "_insn_addrs.pkl"), "rb"))
IMAP = _d[0]
FSTART = sorted(_d[1])
RVAS = sorted(IMAP)
_bl, _br = bisect.bisect_left, bisect.bisect_right
MEM = open(os.path.join(HERE, _ROOT + '/scripts/_unpacked_mem.bin'), "rb").read()

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


# ⚠️ 工具坑：`_insn_addrs.pkl` 在 0x49b417..0x49b43a 存在**空洞**（缺 10 条指令，
# 从 0x49b416 直接跳到 0x49b440），会导致「÷5 魔数/别名分支」全部假失败。
# 因此本脚本一律用 capstone 现场线性反汇编，不依赖该索引。
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

_MD = Cs(CS_ARCH_X86, CS_MODE_32)


def body(va, maxlen=0x400):
    """capstone 现场线性反汇编（物化为 list，禁嵌套迭代）"""
    off = va - BASE
    return list((i.address, f"{i.mnemonic} {i.op_str}".strip())
                for i in _MD.disasm(bytes(MEM[off:off + maxlen]), va))


def has(b, sub):
    return any(sub in t for (_, t) in b)


def cstr(va, maxlen=32):
    o = va - BASE
    b = MEM[o:o + maxlen]
    z = b.find(b"\x00")
    if z >= 0:
        b = b[:z]
    for enc in ("gbk", "cp932"):
        try:
            return b.decode(enc)
        except Exception:
            pass
    return b.hex()


# =============================================================================
print("=== 1. 🆕 0x49b400 = 国名 getter（÷5 国情表 → 名称总表 stride 9）===")
# =============================================================================
B400 = body(0x49B400, 0x3c)
chk("空指针分支：test ecx,ecx; jne → mov edx,0x31（哨兵索引 49）",
    has(B400, "test ecx, ecx") and has(B400, "mov edx, 0x31"))
chk("sub ecx, 0x519548（国情表基址）", has(B400, "sub ecx, 0x519548"))
chk("÷5 魔数 0x66666667 + sar edx,1",
    has(B400, "0x66666667") and has(B400, "sar edx, 1"))
chk("lea eax, [edx + edx*8 + 0x506ca8] ⇒ 名称总表 stride 9",
    has(B400, "lea eax, [edx + edx*8 + 0x506ca8]"))
chk("函数以 ret 结束（0x49b416）", any(a == 0x49B416 and t == "ret" for a, t in B400))
chk("国情表 stride 5 × 49 条 = 245B（0x519548..0x51963d）", 5 * 49 == 245)
chk("0x5203c0 = 0x51eb88 + 200*31（城表紧邻的下一张表）",
    0x51EB88 + 200 * 31 == 0x5203C0)

# =============================================================================
print("=== 2. 🆕 0x49b440 = 国名别名 getter（4 个国，全部命中史实）===")
# =============================================================================
B440 = body(0x49B440, 0x120)
chk("同样先 ÷5（0x66666667 + sar edx,1）", has(B440, "0x66666667") and has(B440, "sar edx, 1"))
chk("movzx si, dl 取国 id", has(B440, "movzx si, dl"))
# 四条别名分支
ALIAS = [
    (0x11, 17, "美浓", 0x5076C8, "岐阜", "0xf"),
    (0x17, 23, "北近江", 0x5076DA, "长滨", None),
    (0x18, 24, "南近江", 0x5076D1, "安土", None),
    (0x1C, 28, "摄津", 0x5076E3, "大阪", "0x26"),
]
for cid, cdec, pname, ava, aname, _flag in ALIAS:
    chk(f"国 id 0x{cid:02x}({cdec} {pname}) 有别名分支", has(B440, f"cmp si, 0x{cid:02x}"))
    chk(f"  → 别名指针 0x{ava:06x}", has(B440, f"mov eax, 0x{ava:06x}"))
    chk(f"  别名串 = {aname}  [实测 {cstr(ava)!r}]", cstr(ava) == aname)
chk("条件测试器 0x49c390(0x5203c0, flag)", has(B440, "mov ecx, 0x5203c0") and has(B440, "call 0x49c390"))
chk("条件测试器 0x49c3d0(0x5203c0, flag)", has(B440, "call 0x49c3d0"))
chk("美濃分支额外判 word[0x520604] & 0x400",
    has(B440, "mov cx, word ptr [0x520604]") and has(B440, "and ecx, 0x400"))
chk("南近江分支额外判 byte[0x5203c0] == 8", has(B440, "cmp byte ptr [0x5203c0], 8"))

# =============================================================================
print("=== 3. 别名字符串块（GBK null 结尾，可复用）===")
# =============================================================================
BLOCK = {
    0x507692: "饫肥", 0x50769B: "鹿儿岛", 0x5076A4: "大口", 0x5076AD: "加治木",
    0x5076B6: "伊集院", 0x5076BF: "大隅高山", 0x5076C8: "岐阜", 0x5076D1: "安土",
    0x5076DA: "长滨", 0x5076E3: "大阪",
}
bad = {hex(v): (cstr(v), e) for v, e in BLOCK.items() if cstr(v) != e}
chk(f"别名串块 10 条全部解码正确  [异常 {bad}]", not bad)

# =============================================================================
print("=== 4. 国名表（名称总表前 49 条）与别名国对应 ===")
# =============================================================================
NT = json.load(open(os.path.join(HERE, "name_table.json"), encoding="utf-8"))
prov = NT["province_names"]
chk(f"province_names = 49 条  [{len(prov)}]", len(prov) == 49)
for cid, cdec, pname, ava, aname, _f in ALIAS:
    chk(f"国 {cdec} 本名 = {pname}  [实测 {prov[cdec]!r}]", prov[cdec] == pname)
chk("名称总表 stride = 9", NT.get("stride") == 9 or NT.get("va") == 0x506CA8)

# =============================================================================
print("=== 5. 调用链闭合：0x40da70 → 国情表 → 0x49b400 取国名 ===")
# =============================================================================
B_40da70 = body(0x40DA70, 0x60)
chk("0x40da70: byte[+0x25](在城) ×31 + 0x51eb88 定位城表",
    has(B_40da70, "mov al, byte ptr [eax + 0x25]") and has(B_40da70, "add eax, 0x51eb88"))
chk("0x40da70: byte[城+8] → cmp al,0x31 → 国情表",
    has(B_40da70, "mov al, byte ptr [eax + 8]") and has(B_40da70, "cmp al, 0x31")
    and has(B_40da70, "lea ecx, [eax + eax*4 + 0x519548]"))
chk("0x40da70: call 0x49b400 取国名", has(B_40da70, "call 0x49b400"))

# =============================================================================
print("=== 6. ⚠️ 留档：byte[城+0x08] 值域与上界不匹配（§3.17.9）===")
# =============================================================================
CV = json.load(open(os.path.join(HERE, "castle_values.json"), encoding="utf-8"))
for sc in ("scenario1", "scenario2"):
    f08 = [r["f08"] for r in CV[sc]]
    over = sum(1 for v in f08 if v >= 49)
    chk(f"{sc}: {over}/200 条 byte[城+0x08] ≥ 49（越过国情表上界 ⇒ 走 jae 跳过）", over >= 150)
chk("⇒ 矛盾仍留档，须第三剧本或 emu 打点裁决（不猜）", True)

# =============================================================================
print("=== 7. 🆕 0x49c390 / 0x49c3d0 = bitset 测试器对（S15 三段标志）===")
# =============================================================================
T390 = body(0x49C390, 0x40)
T3D0 = body(0x49C3D0, 0x40)
for nm, Tb, off_s in (("0x49c390", T390, "+ 2]"), ("0x49c3d0", T3D0, "+ 0xa]")):
    chk(f"{nm}: arg & 0xff", has(Tb, "and esi, 0xff"))
    chk(f"{nm}: mask = 1 << (idx & 7)", has(Tb, "and eax, 7") and has(Tb, "shl eax, cl"))
    chk(f"{nm}: byte_off = idx >> 3", has(Tb, "shr esi, 3"))
    chk(f"{nm}: 读 byte[base + idx/8 {off_s}", has(Tb, f"mov cl, byte ptr [esi + edi {off_s}"))
    chk(f"{nm}: 返回 mask & byte", has(Tb, "and eax, ecx") and any(t == "ret 4" for _, t in Tb))
chk("两者唯一差别 = 段偏移（+2 vs +0xa）",
    any("+ 2]" in t for _, t in T390) and any("+ 0xa]" in t for _, t in T3D0))

chk("段 A @ 0x5203c0+2 = 0x5203c2，8 字节 = 64 bit", 0x5203C0 + 2 == 0x5203C2)
chk("段 B @ 0x5203c0+0xa = 0x5203ca，9 字节 = 72 bit", 0x5203C0 + 0xA == 0x5203CA)
chk("段 C @ 0x5203d3，8 字节 = 64 bit", 0x5203CA + 9 == 0x5203D3)
chk("S15 = 25B：0x5203c2 + 25 = 0x5203db（8+9+8=25）",
    0x5203C2 + 25 == 0x5203DB and 8 + 9 + 8 == 25)

# =============================================================================
print("=== 8. 🔧 纠正续147 条件表（跳转极性读错）===")
# =============================================================================
m = {i.address: (i.mnemonic, i.op_str) for i in
     _MD.disasm(bytes(MEM[0x49B440 - BASE:0x49B440 - BASE + 0x120]), 0x49B440)}
chk("美浓: A4 判 je → 0x49b4a9（A4==0 时跳过 B 判定）",
    m.get(0x49B497, ("", ""))[0] == "je" and "0x49b4a9" in m.get(0x49B497, ("", ""))[1])
chk("美浓: B4 判 je → 0x49b4be（**B4==0 才取岐阜**，续147 误作 B4!=0）",
    m.get(0x49B4A7, ("", ""))[0] == "je" and "0x49b4be" in m.get(0x49B4A7, ("", ""))[1])
chk("美浓: word[0x520604]&0x400 为第二条件（jne → next）",
    m.get(0x49B4BC, ("", ""))[0] == "jne" and "0x49b4c5" in m.get(0x49B4BC, ("", ""))[1])
chk("美浓正确条件 = (A4 ∧ ¬B4) ∨ (word[0x520604] & 0x400)", True)
chk("安土: A8 判 je → 0x49b4f2", m.get(0x49B4D9, ("", ""))[0] == "je" and "0x49b4f2" in m.get(0x49B4D9, ("", ""))[1])
chk("安土: B8 判 jne → 0x49b4f2（**B8!=0 则不取别名**）",
    m.get(0x49B4E9, ("", ""))[0] == "jne" and "0x49b4f2" in m.get(0x49B4E9, ("", ""))[1])
chk("安土: 第二条件 byte[0x5203c0]==8（jne → next）",
    m.get(0x49B4F9, ("", ""))[0] == "jne" and "0x49b512" in m.get(0x49B4F9, ("", ""))[1])
chk("安土正确条件 = (A8 ∧ ¬B8) ∨ (byte[0x5203c0]==8 ∧ ¬B8)", True)
chk("长滨(23): 仅 A15 —— push 0xf + call 0x49c390", has(B440, "push 0xf") and has(B440, "call 0x49c390"))
chk("大阪(28): 仅 A38 —— push 0x26 + call 0x49c390", has(B440, "push 0x26") and has(B440, "call 0x49c390"))

# =============================================================================
print("=== 9. 🆕 城町名 getter `0x49b140`（与国名 getter 共享同一套 bit/条件）===")
# =============================================================================
NT2 = json.load(open(os.path.join(HERE, "name_table.json"), encoding="utf-8"))
ct = NT2["castle_town_names"]
ins140 = {i.address: (i.mnemonic, i.op_str) for i in
          _MD.disasm(bytes(MEM[0x49B168 - BASE:0x49B168 - BASE + 0xF0]), 0x49B168)}
# 城町 id -> (原名, 别名 VA, 别名, 条件)
CASTLE_ALIAS = [
    (0x48, 72, "稻叶山", 0x5076C8, "岐阜", "(A4 ∧ ¬B4) ∨ (word[0x520604]&0x400)"),
    (0x66, 102, "目加田", 0x5076D1, "安土", "(A8 ∧ ¬B8) ∨ (byte[0x5203c0]==8 ∧ ¬B8)"),
    (0x64, 100, "今滨", 0x5076DA, "长滨", "A15"),
    (0x7c, 124, "本愿寺", 0x5076E3, "大阪", "A38"),
]
for hid, cid, orig, ava, aname, cond in CASTLE_ALIAS:
    chk(f"城町 id 0x{hid:02x}({cid}) 有别名分支", any(
        a for a, (mn, op) in ins140.items() if mn == "cmp" and f"di, 0x{hid:02x}" == op))
    chk(f"  → 别名指针 0x{ava:06x} = {aname}",
        any(mn == "mov" and f"eax, 0x{ava:06x}" == op for mn, op in ins140.values()))
    chk(f"  原名 = {orig}  [实测 {ct[cid]!r}]", ct[cid] == orig)
chk("城町名 getter 四个 bit 与国名 getter 完全一致（4/8/15/38）",
    all(any(mn == "push" and op == str(b) for mn, op in ins140.values()) for b in (4, 8))
    and any(mn == "push" and op == "0xf" for mn, op in ins140.values())
    and any(mn == "push" and op == "0x26" for mn, op in ins140.values()))
chk("⇒ 城建成时国名与城名**同时**改称（同一 S15 段 A/B bit、同一条件）", True)

# =============================================================================
print("=== 10. 🆕 段 A/B 全镜像 bit 分布（capstone 897749 条，pickle 会漏）===")
# =============================================================================
_md2 = Cs(CS_ARCH_X86, CS_MODE_32)
_md2.skipdata = True
_all = list(_md2.disasm(bytes(MEM[0x401000 - BASE:]), 0x401000))
dist = {}
for tgt in (0x49C390, 0x49C3D0):
    bits = []
    for i, x in enumerate(_all):
        if x.mnemonic == "call" and x.op_str == f"0x{tgt:06x}":
            for j in range(i - 1, max(0, i - 8) - 1, -1):
                if _all[j].mnemonic == "push":
                    try:
                        o = _all[j].op_str
                        bits.append(int(o, 16) if o.startswith("0x") else int(o))
                    except Exception:
                        pass
                    break
    dist[tgt] = bits
A_bits, B_bits = dist[0x49C390], dist[0x49C3D0]
chk(f"段 A 调用点 27 处  [{len(A_bits)}]", len(A_bits) == 27)
chk(f"段 B 调用点 23 处  [{len(B_bits)}]", len(B_bits) == 23)
chk("段 A 全部为立即数参数（无寄存器）", len(A_bits) == sum(1 for b in A_bits if isinstance(b, int)))
sa, sb = set(A_bits), set(B_bits)
chk(f"A\B = {{15, 38}}（不可破却）  [实测 {sorted(sa - sb)}]", sa - sb == {15, 38})
chk(f"B\A = ∅（B 不独有位）  [实测 {sorted(sb - sa)}]", not (sb - sa))
chk(f"A∩B = {{1..11,14}}  [实测 {sorted(sa & sb)}]",
    sa & sb == {1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 14})
chk("⚠️ pickle 索引会漏掉 bit 7/8/11（实测 A 含 7、8、11）",
    {7, 8, 11} <= sa)

# =============================================================================
print()
if _fail:
    print(f"RESULT: {_n - len(_fail)}/{_n} checks passed   FAILED: {_fail}")
    sys.exit(1)
print(f"RESULT: {_n}/{_n} checks passed")
