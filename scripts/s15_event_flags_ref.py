# -*- coding: utf-8 -*-
"""
太阁立志传2 —— S15「劇本/築城イベント旗幟塊」`0x5203c0` 完整结构（续149）
==========================================================================
承接续148「下一步(A)：穷举段 A/B/C 的 bit 语义；(B) 找段 C 的测试器」。

结论摘要
--------
**① 🆕 S15 权威布局由 SAVE `0x47f0a0` / LOAD `0x47f110` 逐字节坐实 = 25B**

| 偏移 | 长 | 类型 | 语义 |
|---|---|---|---|
| `+0x00` | 1 | byte | **イベント進行 ID**（= bit 号；`0xff` = 無/終了） |
| `+0x01` | 1 | byte | **進捗**：低 5 bit = 進行段階(0..30)，高 3 bit = フェーズ(0..7) |
| `+0x02..+0x09` | 8 | bitset | **段 A** = 「已発生/已完了」旗幟（bit 0..63） |
| `+0x0a..+0x11` | 8 | bitset | **段 B** = 「已失敗/已喪失」旗幟（bit 0..63） |
| `+0x12` | 1 | byte | **実行済みマーカー**（0 = 未実行；非 0 = 実行済み） |
| `+0x13..+0x18` | 6 | **byte 配列** | **段 C** = イベント作業変数（**不是 bitset**） |

**② 🔴 纠正续148**：段 B 是 **8B**（非 9B）；`0x5203d2` 是**独立标量**（非段 B 末字节）；
段 C 是 **6B 的 byte 数组**（非 8B bitset）。25B 总数不变。

**③ 🆕 S15 访问器类 `0x49c390..0x49c520`（9 个方法，全表）**

| VA | 签名 | 语义 |
|---|---|---|
| `0x49c390` | `get_a(base, idx)` | 段 A 读 bit：`byte[base + (idx>>3) + 2] & (1<<(idx&7))` |
| `0x49c3d0` | `get_b(base, idx)` | 段 B 读 bit：`byte[base + (idx>>3) + 0xa] & (1<<(idx&7))` |
| `0x49c410` | `get_c(base, idx)` | 段 C **读字节**：`byte[base + idx + 0x13]` |
| `0x49c420` | `set_prog(base, v)` | `byte[base+1] = (b & 0xe0) \| (v & 0x1f)`（低 5 位） |
| `0x49c440` | `set_hi3(base, v)` | `byte[base+1] = ((v << 5)) \| (b & 0x1f)`（高 3 位） |
| `0x49c460` | `set_a(base, idx, val)` | 段 A 写 bit（val 非 0 置位 / 0 清位） |
| `0x49c4b0` | `set_b(base, idx, val)` | 段 B 写 bit |
| `0x49c500` | `set_c(base, idx, val)` | 段 C **写字节** |
| `0x49c520` | `get_a24_26(base)` | `byte[base+5] & 7` = 段 A 的 bit 24..26 |

调用点计数：get_a 27 / get_b 23 / get_c 29 / set_prog 55 / set_hi3 21 /
set_a 31 / set_b 37 / set_c 25 / get_a24_26 4。

**④ 🆕 14 个 bit 的语义**（`A` = 已発生、`B` = 已喪失/已失敗）

| bit | 事件（证据） | A 置位者 | B 置位者 |
|---|---|---|---|
| 1 | 【未定名】ハンドラ `0x408c20`；完了点 `0x4098b0`/`0x40be00` | `0x4098b0`,`0x40be00` | `0x4098b0` |
| 2 | **将軍（足利家）暗殺/追放** — MSG 6492「什么，将军┅┅？虽然是乱世，暗杀这手段也太卑鄙了」/6498「旧足利领地的各地相继被%s掌握。」 | `0x40c350` | — |
| 3 | 【未定名】`0x40d370`；`0x488030` 预置 B3 | `0x40d370` | `0x40d370`,`0x488030` |
| 4 | **美濃 → 岐阜 改称**（别名 getter `0x49b440`/城名 getter `0x49b140` 条件 A4 ∧ ¬B4） | `0x40e1f0`,`0x488030` | `0x40e1f0`(0) |
| 5 | 【未定名】ハンドラ `0x40ea20`（城マーカー 61） | `0x40f100`,`0x40f640`,`0x471d70`,`0x488030` | `0x40ec60`,`0x488030` |
| 6 | 【未定名】ハンドラ `0x40f850`（**`0x41a400` 首个检查项**，在身分闸门之前） | `0x40fc00`,`0x4100f0` | `0x4100f0`,`0x488030` |
| 7 | 【未定名】`0x411520`/`0x412240` | `0x411520`,`0x412240`,`0x488030` | `0x412240`,`0x488030` |
| 8 | **安土城築城** — MSG 6787「这就是新城，取名安土城」/6792「主公，这次安土城落成，真是可喜可贺」/6802「以后安土城就是天下的中心！」 | `0x412970`,`0x413050` | `0x412860`,`0x4129d0` |
| 9 | **本能寺の変 → 山崎合戦** — MSG 6881「我%s杀死了叛臣明智光秀！」/6883「应该由我胜家继承主公的遗志」/6894「太好了，大获全勝！！回城吧！」 | `0x414160`,`0x4143e0`,`0x416500`,`0x488030` | `0x414160`,`0x4143e0`,`0x488030` |
| 10 | **光秀討伐/安土城召還** — MSG 6952「谋杀主公的叛徒，我要与你决一死战！」/6810「要我去安土城」/6912「进攻%s还顺利吧」 | `0x414fa0`,`0x415fb0`,`0x416400`,`0x417a30`,`0x488030` | `0x414fa0`,`0x488030` |
| 11 | 【未定名】`0x419150` | `0x419150` | `0x419150`(0) |
| 14 | **将軍家（足利義昭）断交** — MSG 6959「会议结束前，有件事告诉大家」/6974「这种旧势力已经不行了，把这个腐朽的将军赶走吧。」 | `0x4c75f0` | `0x4c75f0` |
| 15 | **今滨 → 長浜 改称** — MSG 7025「不过，"今滨"听起来总是别扭。」 | `0x4a9920`,`0x4c0130`,`0x4e3ec0` | — |
| 38 | **摂津 → 大阪（大阪城築城）**（别名 getter 条件 A38，无 ¬B ⇒ 不可破却） | `0x4b3c10` | — |

**⑤ 🆕 `0x488030` = 主人公依存の歴史フラグ初期化**（`0x487f9a` 于开局调用一次）
```
id = 0x49f8f0(0x49f5e0())        ; プレイヤー武将番号（÷47 魔数 0xae4c415d）
if id == 8:                       ; 武将 8
    for b in 1..3: set_b(b, 1)    ; B1=B2=B3=1
    set_b(7,1); set_b(9,1); set_a(4,1); set_a(5,1)
else:
    set_b(5,1); set_b(6,1); set_b(7,1); set_a(0xa,1); set_b(0xa,1)
    if id != 0: set_b(3,1)
```

**⑥ 🆕 事件派发链**：`0x41a400`（bit 6 → 1 → 2 → 3 → 5 → 9 → 10）与
`0x41a660`（bit 4 → 7 → 11）是两条「if (A_i || B_i) 跳过；否则调ハンドラ，
ハンドラ返回非 0 则整链终止」的一次性事件派发器。

运行：python scripts/s15_event_flags_ref.py
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

import bisect, os, pickle, struct, collections

HERE = os.path.dirname(os.path.abspath(__file__))
BASE = 0x400000
MEM = open(os.path.join(HERE, _ROOT + '/scripts/_unpacked_mem.bin'), "rb").read()
_d = pickle.load(open(os.path.join(HERE, "_insn_addrs.pkl"), "rb"))
IMAP = _d[0]
FSTART = sorted(_d[1])

_fail = []
_n = 0


def chk(name, cond):
    global _n
    _n += 1
    print(("  [ OK ] " if cond else "  [FAIL] ") + name)
    if not cond:
        _fail.append(name)


def u8(va):
    return MEM[va - BASE]


def u32(va):
    return struct.unpack_from("<I", MEM, va - BASE)[0]


def dis(va, nb):
    """capstone 现场线性反汇编（不依赖有空洞的 _insn_addrs.pkl 索引）"""
    from capstone import Cs, CS_ARCH_X86, CS_MODE_32
    md = Cs(CS_ARCH_X86, CS_MODE_32)
    return list(md.disasm(MEM[va - BASE:va - BASE + nb], va))


def ops_at(va, nb):
    return [(i.address, i.mnemonic, i.op_str) for i in dis(va, nb)]


def find_calls(target):
    out, i = [], 0
    while True:
        i = MEM.find(b"\xe8", i)
        if i < 0 or i + 5 > len(MEM):
            break
        rel = struct.unpack_from("<i", MEM, i + 1)[0]
        va = BASE + i
        if va + 5 + rel == target:
            out.append(va)
        i += 1
    return out


S15 = 0x5203C0
print("=" * 78)
print("S15 (0x5203c0) 劇本/築城イベント旗幟塊 —— 参考实现自校验")
print("=" * 78)

# ---------------------------------------------------------------- ① 布局
print("\n[1] S15 权威布局（SAVE 0x47f0a0 / LOAD 0x47f110）")
save = ops_at(0x47F0A0, 0x72)
save_txt = "\n".join("%s %s" % (m, o) for _, m, o in save)
chk("SAVE 首段 push 0x5203c0（進行 ID）", "push 0x5203c0" in save_txt)
chk("SAVE 次段 push 0x5203c1（進捗）", "push 0x5203c1" in save_txt)
chk("SAVE 段A edi=0x5203c2 计数 8", "mov edi, 0x5203c2" in save_txt and "mov ebx, 8" in save_txt)
chk("SAVE 段B edi=0x5203ca 计数 8", "mov edi, 0x5203ca" in save_txt)
chk("SAVE 标量 push 0x5203d2", "push 0x5203d2" in save_txt)
chk("SAVE 段C edi=0x5203d3 计数 **6**（非 8）",
    "mov edi, 0x5203d3" in save_txt and save_txt.count("mov ebx, 6") >= 1)

load = ops_at(0x47F110, 0x90)
load_txt = "\n".join("%s %s" % (m, o) for _, m, o in load)
for frag in ("0x5203c0", "0x5203c1", "0x5203c2", "0x5203ca", "0x5203d2", "0x5203d3"):
    chk("LOAD 覆盖 " + frag, frag in load_txt)

LAYOUT = [(0x00, 1, "event_id"), (0x01, 1, "progress"),
          (0x02, 8, "segA_bitset"), (0x0A, 8, "segB_bitset"),
          (0x12, 1, "done_marker"), (0x13, 6, "segC_bytes")]
chk("布局总长 = 1+1+8+8+1+6 = 25B", sum(n for _, n, _ in LAYOUT) == 25)
chk("末字节 = 0x5203d8（0x5203c0+24）", S15 + 25 - 1 == 0x5203D8)

# ---------------------------------------------------------------- ② 访问器
print("\n[2] S15 访问器类 0x49c390..0x49c520")
# ⚠️ capstone 对小立即数省略 0x 前缀（如 `+2`、`and al, 0xe0` 中的 0xe0 保留），
#    断言必须用实际渲染串，不能凭印象写。
API = {
    0x49C390: ("get_a", 1, ["byte ptr [esi + edi + 2]"], 27),
    0x49C3D0: ("get_b", 1, ["byte ptr [esi + edi + 0xa]"], 23),
    0x49C410: ("get_c(byte)", 1, ["byte ptr [ecx + eax + 0x13]"], 29),
    0x49C420: ("set_prog(low5)", 1, ["byte ptr [ecx + 1]", "and al, 0xe0"], 55),
    0x49C440: ("set_hi3(high3)", 1, ["byte ptr [ecx + 1]", "shl al, 5", "and dl, 0x1f"], 21),
    0x49C460: ("set_a", 2, ["byte ptr [esi + edi + 2]"], 31),
    0x49C4B0: ("set_b", 2, ["byte ptr [esi + edi + 0xa]"], 37),
    0x49C500: ("set_c(byte)", 2, ["byte ptr [eax + ecx + 0x13]"], 25),
    0x49C520: ("get_a24_26", 0, ["byte ptr [ecx + 5]", "and eax, 7"], 4),
}
for va, (name, nargs, frags, expect_n) in sorted(API.items()):
    body = "\n".join("%s %s" % (m, o) for _, m, o in ops_at(va, 0x40))
    for frag in frags:
        chk("0x%06x %s 含 %s" % (va, name, frag), frag in body)
    got = len(find_calls(va))
    chk("0x%06x %s 调用点 = %d" % (va, name, expect_n), got == expect_n)

# 段 C 是 byte 数组而非 bitset（关键纠偏）
c_body = "\n".join("%s %s" % (m, o) for _, m, o in ops_at(0x49C410, 0x12))
chk("get_c 是 mov al, byte[ecx+eax+0x13]（byte 非 bit）",
    "byte ptr [ecx + eax + 0x13]" in c_body)
chk("get_c 无移位运算（故为 byte 数组而非 bitset）", "shl" not in c_body and "shr" not in c_body)
cw = "\n".join("%s %s" % (m, o) for _, m, o in ops_at(0x49C500, 0x14))
chk("set_c 是 mov byte[eax+ecx+0x13], dl（byte 非 bit）",
    "byte ptr [eax + ecx + 0x13], dl" in cw)

# ---------------------------------------------------------------- ③ 调用点
print("\n[3] 全镜像 bitset 调用点穷举")
from capstone import Cs, CS_ARCH_X86, CS_MODE_32  # noqa: E402

_md = Cs(CS_ARCH_X86, CS_MODE_32)


def back_args(callva, nargs, back=96):
    ins = list(_md.disasm(MEM[callva - BASE - back:callva - BASE], callva - back))
    args = []
    for k in range(len(ins) - 1, -1, -1):
        it = ins[k]
        if it.mnemonic == "push":
            o = it.op_str
            v = None
            if o.startswith("0x"):
                try:
                    v = int(o, 16)
                except ValueError:
                    pass
            if v is None:
                try:
                    v = int(o)
                except ValueError:
                    v = o
            args.append(v)
            if len(args) == nargs:
                break
        elif it.mnemonic in ("ret", "jmp"):
            break
        elif it.mnemonic == "add" and it.op_str.startswith("esp"):
            break
    return args


rows = []
for va, (name, nargs, _, _) in API.items():
    for cva in find_calls(va):
        rows.append((va, name, cva, back_args(cva, nargs) if nargs else []))

GETA = collections.Counter(a[0] for va, nm, _, a in rows if va == 0x49C390 and a and isinstance(a[0], int))
GETB = collections.Counter(a[0] for va, nm, _, a in rows if va == 0x49C3D0 and a and isinstance(a[0], int))
SETA = collections.defaultdict(list)
SETB = collections.defaultdict(list)
for va, nm, cva, a in rows:
    if va == 0x49C460 and len(a) == 2 and isinstance(a[0], int):
        SETA[a[0]].append((cva, a[1]))
    if va == 0x49C4B0 and len(a) == 2 and isinstance(a[0], int):
        SETB[a[0]].append((cva, a[1]))

BITS = sorted(set(GETA) | set(GETB) | set(SETA) | set(SETB))
chk("已用 bit 集合 = {1..11, 14, 15, 38}",
    BITS == [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 14, 15, 38])
chk("bit 数 = 14", len(BITS) == 14)
chk("全部 bit < 64（段 A/B 各 64 bit 足够）", max(BITS) < 64)

# ---------------------------------------------------------------- ④ 事件语义
print("\n[4] 事件语义锚点（MSG 铁证）")
TEXT = None
try:
    import json
    TEXT = json.load(open(os.path.join(HERE, "msgx_all_texts.json"), encoding="utf-8"))["texts"]
except Exception:
    pass

if TEXT:
    def t(i):
        for k in (str(i), "0x%x" % i):
            if k in TEXT:
                return TEXT[k]
        return ""
    chk("bit8 安土城：MSG 6787 含「取名安土城」", "取名安土城" in t(6787))
    chk("bit8 安土城：MSG 6802 含「安土城就是天下的中心」", "安土城就是天下的中心" in t(6802))
    chk("bit14 将軍家断交：MSG 6974 含「把这个腐朽的将军赶走」", "把这个腐朽的将军赶走" in t(6974))
    chk("bit15 今滨改称：MSG 7025 含「今滨」", "今滨" in t(7025))
    chk("bit2 将軍暗殺：MSG 6492 含「将军」且含「暗杀」", "将军" in t(6492) and "暗杀" in t(6492))
    chk("bit9 山崎合戦：MSG 6881 含「杀死了叛臣明智光秀」", "杀死了叛臣明智光秀" in t(6881))
    chk("bit10 光秀討伐：MSG 6952 含「谋杀主公的叛徒」", "谋杀主公的叛徒" in t(6952))
else:
    print("  [SKIP] msgx_all_texts.json 不可用")

print("\n[5] 派发器与初始化")
chk("0x41a400 首项检查 bit 6（push 6; call 0x49c390）",
    "push 6" in "\n".join("%s %s" % (m, o) for _, m, o in ops_at(0x41A400, 0x10)))
chk("0x41a660 首项检查 bit 4", "push 4" in "\n".join("%s %s" % (m, o) for _, m, o in ops_at(0x41A660, 0x10)))
init = "\n".join("%s %s" % (m, o) for _, m, o in ops_at(0x488030, 0x80))
chk("0x488030 以 0x49f8f0(0x49f5e0()) 取武将番号", "call 0x49f5e0" in init and "call 0x49f8f0" in init)
chk("0x488030 分支 cmp si, 8", "cmp si, 8" in init)
chk("0x488030 由 0x487f9a 调用一次", find_calls(0x488030) == [0x487F9A])
chk("0x49f8f0 用 ÷47 魔数 0xae4c415d",
    "0xae4c415d" in "\n".join("%s %s" % (m, o) for _, m, o in ops_at(0x49F8F0, 0x20)))

print("\n[6] 0x5203d2 语义（布尔マーカー，非城 ID）")
for rd in (0x40D351, 0x412078):
    b = "\n".join("%s %s" % (m, o) for _, m, o in ops_at(rd, 0x10))
    chk("0x%06x 读法 = mov al,byte[0x5203d2]; test al,al" % rd,
        "byte ptr [0x5203d2]" in b and "test al, al" in b)

# ---------------------------------------------------------------- 参考实现
print("\n[7] 参考实现 round-trip")


class S15(object):
    SIZE = 25

    def __init__(self, buf=None):
        self.b = bytearray(buf) if buf is not None else bytearray(self.SIZE)

    # --- 段 A / B ---
    def _get(self, seg, idx):
        return (self.b[seg + (idx >> 3)] >> (idx & 7)) & 1

    def _set(self, seg, idx, val):
        p = seg + (idx >> 3)
        if val:
            self.b[p] |= 1 << (idx & 7)
        else:
            self.b[p] &= ~(1 << (idx & 7)) & 0xFF

    def get_a(self, i):
        return self._get(2, i)

    def get_b(self, i):
        return self._get(0xA, i)

    def set_a(self, i, v):
        self._set(2, i, v)

    def set_b(self, i, v):
        self._set(0xA, i, v)

    # --- 段 C（byte 数组） ---
    def get_c(self, i):
        return self.b[0x13 + i]

    def set_c(self, i, v):
        self.b[0x13 + i] = v & 0xFF

    # --- スカラー ---
    @property
    def event_id(self):
        return self.b[0]

    @event_id.setter
    def event_id(self, v):
        self.b[0] = v & 0xFF

    @property
    def progress(self):
        return self.b[1] & 0x1F

    @progress.setter
    def progress(self, v):
        self.b[1] = (self.b[1] & 0xE0) | (v & 0x1F)

    @property
    def phase(self):
        return (self.b[1] >> 5) & 7

    @phase.setter
    def phase(self, v):
        self.b[1] = ((v & 7) << 5) | (self.b[1] & 0x1F)

    @property
    def done(self):
        return self.b[0x12] != 0

    def get_a24_26(self):
        return self.b[5] & 7


s = S15()
ok = True
for i in BITS:
    s.set_a(i, 1)
    ok &= (s.get_a(i) == 1) and (s.get_b(i) == 0)
    s.set_b(i, 1)
    ok &= (s.get_b(i) == 1) and (s.get_a(i) == 1)
    s.set_a(i, 0)
    ok &= (s.get_a(i) == 0) and (s.get_b(i) == 1)
    s.set_b(i, 0)
    ok &= (s.get_b(i) == 0)
chk("段 A/B 全 14 bit set/clear/独立 round-trip", ok)

s2 = S15()
s2.event_id = 8
s2.progress = 1
s2.phase = 0
s2.set_b(8, 0)
s2.b[0x12] = 110
chk("安土城築城開始（0x412d90）复现：id=8,prog=1,phase=0,¬B8,done=110",
    s2.event_id == 8 and s2.progress == 1 and s2.phase == 0
    and s2.get_b(8) == 0 and s2.b[0x12] == 110)

s3 = S15()
s3.progress = 0x1E  # 30 → &0x1f
chk("progress 钳到 5 bit（0x1e 保持，0x3f→0x1f）",
    s3.progress == 30 and (lambda x: (setattr(x, 'progress', 0x3F), x.progress)[1])(s3) == 0x1F)
s3.phase = 5
chk("phase 写入高 3 bit 不破坏低 5 bit", s3.phase == 5 and s3.progress == 0x1F)
s3.set_c(0, 0x1E)
s3.set_c(1, 200)
chk("段 C byte 数组读写（0..5）", s3.get_c(0) == 0x1E and s3.get_c(1) == 200 and len(s3.b) == 25)

s4 = S15()
s4.set_a(24, 1); s4.set_a(25, 1); s4.set_a(26, 0)
chk("get_a24_26 = byte[+5]&7 = A24..A26", s4.get_a24_26() == 0b011)

print("\n" + "=" * 78)
print("结果：%d/%d 通过" % (_n - len(_fail), _n))
if _fail:
    print("失败项：")
    for f in _fail:
        print("   - " + f)
print("=" * 78)
