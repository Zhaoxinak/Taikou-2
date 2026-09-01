# -*- coding: utf-8 -*-
"""
S15 剧本事件 flag（14 个 bit）语义定名参考实现 + 自校验。
锚点来源：
- 派发器 A(0x41a400)/B(0x41a660) 提取 bit->handler 映射（_s15_dispatcher.py）
- 各 handler / set 子函数的 MSGX 文本铁证 或 硬常量锚点
- 国名表 0x506ca8 stride 9（国 id=索引）第 13 条 = 駿河
- 武将名表 entity_names_sc1.json[217] = 下间赖照（石山本願寺僧官）
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

import os, bisect, pickle, json, sys
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

HERE = os.path.dirname(os.path.abspath(__file__))
BASE = 0x400000
MEM = open(os.path.join(HERE, _ROOT + '/scripts/_unpacked_mem.bin'), "rb").read()
md = Cs(CS_ARCH_X86, CS_MODE_32)
md.detail = False

_d = pickle.load(open(os.path.join(HERE, "_insn_addrs.pkl"), "rb"))
FSTART = sorted(_d[1])
FSTART_VA = [x + BASE for x in FSTART]

MSGMAP = json.load(open(os.path.join(HERE, "msgx_id_map.json"), encoding="utf-8"))
TXT = json.load(open(os.path.join(HERE, "msgx_all_texts.json"), encoding="utf-8"))["texts"]


def hx(v):
    return v if isinstance(v, int) else int(v, 16)


def txt(i):
    for k in (str(i), "0x%x" % i):
        if k in TXT:
            return TXT[k]
    return "?"


def fn_of(va):
    i = bisect.bisect_right(FSTART_VA, va) - 1
    return FSTART_VA[i] if i >= 0 else None


def body(va, length=0x300):
    i = bisect.bisect_right(FSTART_VA, va) - 1
    end = FSTART_VA[i + 1] if i + 1 < len(FSTART_VA) else BASE + len(MEM)
    return list(md.disasm(MEM[va - BASE:min(end, va + length) - BASE], va))


def ops_at(va, length=0x200):
    return [(it.mnemonic, it.op_str) for it in body(va, length)]


# ---- 已定名 bit 表 ----
# (bit, 事件, 置信, 锚点类型, 锚点值)
BITS = {
    1:  ("桶狭间之战 (1560)", "高", "const", ("0x408a80", "cmp al, 0xd")),   # 玩家国==13(駿河)
    2:  ("将军暗杀/追放 (1573)", "铁", "msg", ("0x40c350", [0x195c, 0x1962])),  # MSG 6492/6498
    3:  ("石山本愿寺之战/一向一揆", "中(推断)", "const", ("0x40d410", "byte ptr [esi + 0x13], 0xd9")),  # 下间赖照(217)
    4:  ("岐阜筑城 (1567)", "铁", "ref", ("续148", None)),
    5:  ("义昭上洛/将军奉戴 (1568)", "铁", "msg", ("0x40ec60", [0x19f2, 0x19f0])),  # MSG 6642/6640
    6:  ("二条城筑城/足利义昭 征夷大将军宣下 (1568)", "铁", "msg", ("0x40f9d0", [0x19f7, 0x1a12])),  # MSG 6647/6674
    7:  ("金崎撤退 (1570)", "铁", "msg", ("0x411870", [0x1a42, 0x1a46])),  # MSG 6722/6726
    8:  ("安土城筑城 (1576)", "铁", "msg", ("0x413050", [0x1a83, 0x1a86])),  # MSG 6787/6790
    9:  ("本能寺之变→山崎合战 (1582)", "铁", "msg", ("0x416500", [0x1ad1, 0x1ad3])),  # MSG 6881/6883
    10: ("光秀讨伐/山崎 (1582)", "铁", "msg", ("0x414fa0", [0x1b28, 0x1a9a])),  # MSG 6952/6810
    11: ("长篠合战 (1575)", "铁", "msg", ("0x418e10", [0x1b40, 0x1b41])),  # MSG 6976/6977
    14: ("将军家(足利)断交", "铁", "msg", ("0x4c75f0", [0x1b2f, 0x1b4e])),  # MSG 6959/6974
    15: ("今滨→长滨 改名 (1573)", "铁", "msg", ("0x4e3ec0", [0x1b71])),  # MSG 7025
    38: ("大阪(石山本愿寺)落城 (1580)", "铁", "ref", ("续147/148", None)),
}

# 派发器提取的 bit->handler（真实运行期）
DISPATCH = {
    6: 0x40f850, 1: 0x408c20, 2: 0x40c350, 3: 0x40d040, 5: 0x40ea20,
    9: 0x413bd0, 4: 0x40e120, 7: 0x411c00, 11: 0x418dd0,
}

passed = 0
failed = 0


def chk(name, cond):
    global passed, failed
    if cond:
        passed += 1
        print("  [OK]  %s" % name)
    else:
        failed += 1
        print("  [FAIL] %s" % name)


print("== A. 派发器 bit->handler 锚点 ==")
for bit, handler in sorted(DISPATCH.items()):
    ops = ["%s %s" % (m, o) for m, o in ops_at(handler, 0x40)]
    # 该 handler 应属于其函数（离散反汇编即可，证明地址可定位）
    chk("bit %2d 的 handler 0x%06x 可反汇编" % (bit, handler), len(ops) > 0)

print("\n== B. 各 bit 关键锚点 ==")
# bit 1: 0x408a80 含 cmp al, 0xd (駿河)
b1 = "\n".join("%s %s" % (m, o) for m, o in ops_at(0x408a80, 0x80))
chk("bit 1 駿河锚点(0x408a80 含 'cmp al, 0xd')", "cmp al, 0xd" in b1)

# bit 3: 0x40d410 含 'byte ptr [esi + 0x13], 0xd9'
b3 = "\n".join("%s %s" % (m, o) for m, o in ops_at(0x40d410, 0x70))
chk("bit 3 下间赖照锚点(0x40d410 含 'byte ptr [esi + 0x13], 0xd9')", "byte ptr [esi + 0x13], 0xd9" in b3)

# bit 5/6/7/11 的 MSGX 铁证（本体或 callee 文本存在）
checks = {
    5:  (0x19f2, "义昭公上京都"),
    6:  (0x19f7, "征夷大将军"),
    7:  (0x1a42, "你没事真是太好了"),
    11: (0x1b40, "在长筱交战"),
    2:  (0x195c, "将军"),
    8:  (0x1a83, "安土城"),
    9:  (0x1ad1, "明智光秀"),
    10: (0x1b28, "叛徒"),
    14: (0x1b2f, "会议结束前"),
    15: (0x1b71, "今滨"),
}
for bit, (mid, kw) in checks.items():
    t = txt(mid)
    chk("bit %2d MSGX 0x%x 含'%s' -> %s" % (bit, mid, kw, t[:24]), kw in t)

print("\n== C. 国名表/武将名 锚点 ==")
# 国 13 = 駿河
def gname(i):
    off = 0x506ca8 - BASE + i * 9
    end = MEM.find(b"\x00", off)
    return MEM[off:end].decode("gbk", "replace")
chk("国 13 = 駿河（bit 1 锚点）", gname(13) == "骏河")
n = json.load(open(os.path.join(HERE, "entity_names_sc1.json"), encoding="utf-8"))
chk("武将 217 = 下间赖照（bit 3 锚点）", n[217] == "下间赖照")

print("\n== 结果：%d OK / %d FAIL ==" % (passed, failed))
print("\n== S15 14 bit 语义总表 ==")
for bit in sorted(BITS):
    name, conf, _, _ = BITS[bit]
    print("  bit %2d | %-40s | %s" % (bit, name, conf))
sys.exit(1 if failed else 0)
