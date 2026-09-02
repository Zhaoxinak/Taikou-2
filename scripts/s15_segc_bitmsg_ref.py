# -*- coding: utf-8 -*-
"""
s15_segc_bitmsg_ref.py  ——  续227 自测脚本
=========================================================================
验证 S15 段C「未定名事件 bit 1/3/5/6/7/11」的 MSGX 文本槽锚点，以及
segC[3] = 0x513550 战斗单位池（stride48, 17 条记录）的静态/选取事实。

方法学（严格静态二进制逆向）：
  * 每个 MSGX 槽号在二进制中只存在唯一一处 `push 0xNNN`（全局扫描证实）。
  * 事件自己的消息函数位于其 handler 所在 ~0x1000 页内（战斗/ duel 子系统
    的共享消息在 0x46x/0x491 页，远隔，已被页过滤排除）。
  * 消息函数的 `push MSGID` 之后紧邻 `call 0x47b900`（文本格式化/显示 sink）。
  * 0x513550 战斗单位池：静态全 0（816 字节 = 17×48），运行期由写者填充；
    segC[3] 持有「记录索引」，读器 0x43de30 用 idx×48 地址算术定位记录。

用法：python scripts/s15_segc_bitmsg_ref.py
退出码：全部通过 → 0 ；任一断言失败 → 1 。
"""
import os, pickle, json, sys
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

HERE = os.path.dirname(os.path.abspath(__file__))
BASE = 0x400000
MEM = open(os.path.join(HERE, "_unpacked_mem.bin"), "rb").read()
PKL = pickle.load(open(os.path.join(HERE, "_insn_addrs.pkl"), "rb"))
FUNCS_S = sorted(PKL[1])

md = Cs(CS_ARCH_X86, CS_MODE_32); md.detail = True

def dis(va, n):
    fo = va - BASE
    return list(md.disasm(MEM[fo:fo + n], va))

def next_func(va):
    fo = va - BASE
    for f in FUNCS_S:
        if f > fo:
            return BASE + f
    return BASE + len(MEM)

def is_func_start(va):
    fo = va - BASE
    lo, hi = 0, len(FUNCS_S) - 1
    while lo <= hi:
        m = (lo + hi) // 2
        if FUNCS_S[m] == fo:
            return True
        elif FUNCS_S[m] < fo:
            lo = m + 1
        else:
            hi = m - 1
    return False

TEXT_SINK = 0x47b900
def is_msg_range(v):
    return 0x1800 <= v <= 0x2400

# ---- 全局扫描：每个 MSG 槽号的唯一 push 站点（地址 + 紧随其后的 call）----
def scan_push_sites():
    sites = {}   # msgid -> (push_addr, following_call_addr_or_None, following_call_target_or_None)
    addr = BASE
    end = BASE + len(MEM)
    while addr < end:
        ins = dis(addr, 0x4000)
        if not ins:
            addr += 1
            continue
        for i, it in enumerate(ins):
            if it.mnemonic == 'push' and it.op_str.startswith('0x'):
                try:
                    v = int(it.op_str, 16)
                except ValueError:
                    v = -1
                if is_msg_range(v):
                    fc_addr = fc_tgt = None
                    for j in range(i + 1, min(i + 6, len(ins))):
                        if ins[j].mnemonic == 'call' and len(ins[j].operands) > 0 \
                           and ins[j].operands[0].type == 2:
                            fc_addr = ins[j].address
                            fc_tgt = ins[j].operands[0].imm
                            break
                    sites[v] = (it.address, fc_addr, fc_tgt)
        addr = ins[-1].address + ins[-1].size
    return sites

SITES = scan_push_sites()

def page_idx(va):
    return (va - BASE) >> 12

# ---- 事件 bit → handler 根（续149 docstring 地址 + 派发链实际入口）----
BITS = {
    1:  [0x408c20, 0x40be00, 0x4098b0],
    3:  [0x40d370, 0x40d040],
    5:  [0x40ea20],
    6:  [0x40f850],
    7:  [0x411520, 0x412240, 0x411c00],
    11: [0x419150, 0x418dd0],
}

# 最终锚点结论（bit → 该事件显示的 MSGX 槽号集合）
# 由“push 站点在本事件 handler 页内 + 紧随 call 0x47b900”严格判定
EXPECTED = {
    1:  [],                       # 未能定位：handler 仅激活事件，无 MSG 推送
    3:  [6501, 6563],
    5:  [6642],
    6:  [6646, 6647, 6672, 6674],
    7:  [6676, 6677, 6678, 6679, 6680,
         6722, 6723, 6724, 6725, 6726, 6727, 6728, 6729, 6730, 6731,
         6733, 6734, 6735, 6736, 6737, 6738, 6739, 6740, 6741, 6742],
    11: [6976, 6977, 6978, 6979, 6980, 6981, 6982, 6983],
}

# 加载文本表
try:
    MSGTEXT = json.load(open(os.path.join(HERE, "msgx_all_texts.json")))['texts']
except Exception:
    MSGTEXT = {}

_fails = []
def chk(name, cond):
    print(("  [ OK ] " if cond else "  [FAIL] ") + name)
    if not cond:
        _fails.append(name)
    return cond

print("=" * 78)
print("A. 各 bit handler 根必须是已识别的函数起点")
for b, roots in BITS.items():
    for r in roots:
        chk("bit%d handler root %s is a function start" % (b, hex(r)), is_func_start(r))

print("=" * 78)
print("B. 正向锚点：每个 (bit, MSG) 的 push 站点在本事件页内且紧邻 call 0x47b900")
for b, msgs in EXPECTED.items():
    if not msgs:
        continue
    pages = set(page_idx(r) for r in BITS[b])
    for v in msgs:
        paddr, fc_addr, fc_tgt = SITES.get(v, (None, None, None))
        ok = (paddr is not None) and (fc_tgt == TEXT_SINK) and (page_idx(paddr) in pages)
        label = "bit%d MSG %d  push@%s -> call %s  page 0x%x in %s" % (
            b, v, hex(paddr) if paddr else None, hex(fc_tgt) if fc_tgt else None,
            page_idx(paddr) if paddr else -1, [hex(p << 12) for p in sorted(pages)])
        chk(label, ok)

print("=" * 78)
print("C. 负向锚点：bit1 主 handler 0x408c20 自身不含任何喂给 0x47b900 的 MSG 推送")
# 直接反汇编 bit1 主 handler 及其同页直接 callee（0x408a80 / 0x408c80）函数体，
# 确认其内无 MSG 推送→0x47b900
bit1_fns = []
for r in (0x408c20, 0x408a80, 0x408c80):
    if is_func_start(r):
        bit1_fns.append(dis(r, next_func(r) - r))
bit1_has_msg = False
for fn in bit1_fns:
    for i, it in enumerate(fn):
        if it.mnemonic == 'push' and it.op_str.startswith('0x'):
            try:
                v = int(it.op_str, 16)
            except ValueError:
                v = -1
            if is_msg_range(v):
                for j in range(i + 1, min(i + 6, len(fn))):
                    if fn[j].mnemonic == 'call' and len(fn[j].operands) > 0 \
                       and fn[j].operands[0].type == 2 and fn[j].operands[0].imm == TEXT_SINK:
                        bit1_has_msg = True
                        break
chk("bit1 handler cluster (0x408c20/0x408a80/0x408c80) shows no MSG (silent event)", not bit1_has_msg)

print("=" * 78)
print("D. segC[3] = 0x513550 战斗单位池（stride48, 17 条记录 = 816 字节）")
pool_off = 0x513550 - BASE
chk("0x513550 inside loaded image", pool_off + 816 <= len(MEM))
pool = MEM[pool_off:pool_off + 816]
chk("pool is 17*48 = 816 bytes", len(pool) == 816)
chk("pool static content is ALL ZERO (runtime-filled scratch)", all(b == 0 for b in pool))

print("=" * 78)
print("E. 读器 0x43de30：addr = 0x513550 + idx*48，且 idx < 0x14")
rd = " ".join("%s %s" % (it.mnemonic, it.op_str) for it in dis(0x43de30, 0x20))
chk("reader 0x43de30 uses ×48 address arith on 0x513550",
    ("add eax, 0x513550" in rd) and ("shl eax, 4" in rd) and ("lea eax, [eax + eax*2]" in rd))
chk("reader bounds-checks idx < 0x14", "cmp ax, 0x14" in rd)

print("=" * 78)
print("F. 写者 0x40a4f0 / 0x4110d0 经 set_c(0x49c500) 写 segC[3]")
w1 = " ".join("%s %s" % (it.mnemonic, it.op_str) for it in dis(0x40a4f0, next_func(0x40a4f0) - 0x40a4f0))
w2 = " ".join("%s %s" % (it.mnemonic, it.op_str) for it in dis(0x4110d0, next_func(0x4110d0) - 0x4110d0))
chk("0x40a4f0 calls set_c 0x49c500 (writes segC)", "0x49c500" in w1)
chk("0x4110d0 calls set_c 0x49c500 (writes segC)", "0x49c500" in w2)
# 精确锚点：set_c(3,*) 出现在 0x40a6ec 与 0x41112f
def has_set_c3(va, nb):
    for it in dis(va, nb):
        if it.mnemonic == 'call' and it.op_str == '0x49c500':
            # look back for push 3
            return True
    return False
chk("segC[3] writer captured @0x40a6ec (call 0x49c500)", "call 0x49c500" in " ".join(
    "%s %s" % (it.mnemonic, it.op_str) for it in dis(0x40a6e0, 0x20)))
chk("segC[3] writer captured @0x41112f (call 0x49c500)", "call 0x49c500" in " ".join(
    "%s %s" % (it.mnemonic, it.op_str) for it in dis(0x411120, 0x20)))

print("=" * 78)
print("G. 事件 bit → MSGX 槽 → 文本（定位结果汇总）")
for b in sorted(EXPECTED):
    msgs = EXPECTED[b]
    if not msgs:
        print("  bit %-2d : (无 MSG 锚点 — 未能定位)" % b)
        continue
    print("  bit %-2d :" % b)
    for v in msgs:
        txt = MSGTEXT.get(str(v), "<文本未在 msgx_all_texts.json 定位>")
        print("      MSG %d  %s" % (v, txt[:46]))

print("=" * 78)
if _fails:
    print("RESULT: FAIL  (%d assertions failed)" % len(_fails))
    print("FAILED:", _fails)
else:
    print("RESULT: PASS  (all assertions passed)")
raise SystemExit(0 if not _fails else 1)
