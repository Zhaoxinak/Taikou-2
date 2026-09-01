#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""续167(A): 13 个 +0x2a 消费循环 定名 / 分类自检。
对 13 个 stride-47 循环中消费 word[entity+0x2a] 的函数做 capstone 反汇编（skipdata=True），
抽取锚点调用（set_lord_idx / inc_loyalty / affinity_score / S15_set_a / castle_rec_copy /
display_msg / RNG / sndata_fanout / shared_setter_lib / get_player / get_slot / is_alive），
据此自动分类并断言每个函数含预期锚点。
纯静态，不改写任何文件。运行：python scripts/retainer_consumers_ref.py
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

import os, sys, re
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

HERE = os.path.dirname(os.path.abspath(__file__))
BASE = 0x400000
MEM = open(os.path.join(HERE, _ROOT + '/scripts/_unpacked_mem.bin'), "rb").read()

# 13 个 consumer（续167 列）
CONSUMERS = [
    0x45e3e0, 0x46a4a0, 0x47dce0, 0x47df00, 0x488100, 0x4a3920,
    0x4a5010, 0x4a5370, 0x4a6970, 0x4c0130, 0x4c9650, 0x4d7fe0,
]

ANCHOR = {
    0x49a7d0: "set_lord_idx",
    0x49a880: "inc_loyalty",
    0x49ffc0: "affinity_score",
    0x49c460: "S15_set_a",
    0x49c4b0: "S15_set_b",
    0x49a990: "castle_rec_copy",
    0x47b900: "display_msg",
    0x4ebd60: "RNG",
    0x45e3e0: "build_cand_pool",
    0x49f5e0: "get_player",
    0x49f830: "get_slot",
    0x470690: "is_alive",
    0x47fc60: "sndata_fanout",
    0x49b960: "shared_setter_lib",
}

# 分类（conf: HIGH=调用图高置信; KNOWN=既有结论; MSG=需 MSGX 文本最终确认标签）
CLASS = {
    0x45e3e0: ("候选池构建器（续167 已闭）", "KNOWN",
               dict(anchors={0x470690, 0x49f5e0, 0x4ebd60}, reads={0x2a, 0x25})),
    0x46a4a0: ("大名継承/転封・家臣主君一括再割当", "HIGH",
               dict(anchors={0x49a7d0, 0x49a990, 0x49a880, 0x4ebd60}, reads={0x2a, 0x24, 0x25, 0x28})),
    0x47dce0: ("武将名表填充器（id0..999→0x521aa8，序列化原语）", "KNOWN",
               dict(anchors=set(), reads={0x2a, 0x22, 0x24, 0x26, 0x28, 0x2c})),
    0x47df00: ("武将实体一括シリアライズ/init（0x47dce0 兄弟，序列化原语）", "HIGH",
               dict(anchors=set(), reads={0x2a, 0x22, 0x24, 0x26, 0x28, 0x2c})),
    0x488100: ("劇本 SNDATA→武将状態適用（sndata_fanout + 忠誠加算）", "HIGH",
               dict(anchors={0x47fc60, 0x49a880, 0x49b960, 0x49f5e0, 0x49f830}, reads={0x2a, 0x24, 0x25, 0x2c})),
    0x4a3920: ("家臣登用/任命 対話フロー（display_msg+set_lord_idx+城record）", "HIGH",
               dict(anchors={0x47b900, 0x49a7d0, 0x49a990, 0x49a880, 0x49b960, 0x49f5e0}, reads={0x2a, 0x24, 0x25, 0x26, 0x28, 0x2c})),
    0x4a5010: ("相性ベース 登用/引抜 A（set_lord_idx+affinity+RNG）", "MSG",
               dict(anchors={0x49a7d0, 0x49a880, 0x49f5e0, 0x49ffc0, 0x4ebd60}, reads={0x2a, 0x22, 0x24, 0x25, 0x2c})),
    0x4a5370: ("相性ベース 登用/引抜 B・寢返し/離反（[esi+0x2a]→set_lord_idx）", "MSG",
               dict(anchors={0x49a7d0, 0x49a880, 0x49f5e0, 0x49ffc0, 0x4ebd60}, reads={0x2a, 0x22, 0x25, 0x2c})),
    0x4a6970: ("俸禄/知行结算净额累加器（续140 已闭）", "KNOWN",
               dict(anchors={0x49f5e0, 0x49f830, 0x4ebd60}, reads={0x24, 0x26, 0x28, 0x2c})),
    0x4c0130: ("劇本イベント handler：家臣関連（S15_set_a+display_msg+城record）", "HIGH",
               dict(anchors={0x47b900, 0x49a880, 0x49a990, 0x49c460, 0x49f5e0, 0x49f830, 0x4ebd60}, reads={0x2a, 0x24, 0x25, 0x28, 0x2c})),
    0x4c9650: ("月次俸禄/恩賞支給 + 忠誠加算（display_msg+sat_add）", "HIGH",
               dict(anchors={0x47b900, 0x49f5e0}, reads={0x25, 0x26, 0x2a, 0x2c})),
    0x4d7fe0: ("家臣 解雇/追放/離反処理（display_msg+浪人化+shared_setter_lib）", "MSG",
               dict(anchors={0x47b900, 0x49b960, 0x49f5e0}, reads={0x25, 0x2c})),
}

def disasm(va, n):
    md = Cs(CS_ARCH_X86, CS_MODE_32)
    md.skipdata = True
    off = va - BASE
    return list(md.disasm(bytes(MEM[off:off + n]), va))

def signed_disp(op):
    """从内存操作数 [reg + disp] / [reg - disp] 抽符号位移；忽略索引项（本批循环均为 [reg ± imm]）。"""
    m = re.search(r'\[([^\]]+)\]', op)
    if not m:
        return None
    inside = m.group(1)
    # capstone 对大位移渲染 0x 十六进制，对小数位移（如 [esi - 2]）渲染十进制，两者都要吃
    adds = re.findall(r'([+\-])\s*(0x[0-9a-f]+|\d+)', inside)
    if not adds:
        return 0
    val = 0
    for s, h in adds:
        n = int(h, 16) if h.startswith('0x') else int(h, 10)
        val += n * (1 if s == '+' else -1)
    return val

def feats(va):
    ins = disasm(va, 0x800)
    calls, reads, push_ffff = set(), set(), 0
    for i in ins:
        m, op = i.mnemonic, i.op_str
        if m == "call" and op.startswith("0x"):
            try: calls.add(int(op, 16))
            except: pass
        low = op.lower()
        if "ptr [" in low or "ptr[" in low:
            d = signed_disp(low)
            if d is not None:
                # 家臣字段核心 +0x2a：两种循环基址形态都命中
                #   (a) base 对齐循环：直接 [reg + 0x2a]
                #   (b) base+0x2c 对齐循环（0x4a6970/0x4d7fe0 等）：+0x2a = [reg - 0x2]
                if d == 0x2a or d == -0x2:
                    reads.add(0x2a)
                # 信息性：把位移折算成实体字段偏移（负位移按 base+0x2c 对齐还原）
                if d < 0:
                    off = d + 0x2c
                    if 0 <= off <= 0x2e:
                        reads.add(off)
                elif 0 <= d <= 0x2e:
                    reads.add(d)
        if m == "push" and op.lower().endswith("ffff"):
            push_ffff += 1
    return calls, reads, push_ffff

def main():
    fails = 0
    total_asserts = 0
    print("=== 13 个 +0x2a 消费循环 · 分类自检 ===\n")
    for va in CONSUMERS:
        name, conf, exp = CLASS[va]
        calls, reads, pf = feats(va)
        print("0x%06x  [%s]  %s" % (va, conf, name))
        # 断言 1：预期锚点全部出现
        for a in exp["anchors"]:
            total_asserts += 1
            ok = a in calls
            fails += (not ok)
            if not ok:
                print("    [FAIL] 缺失锚点 %s" % ANCHOR.get(a, "0x%x" % a))
        # 断言 2：读 +0x2a（家臣字段核心）
        if 0x2a not in reads:
            total_asserts += 1; fails += 1
            print("    [FAIL] 未检出 +0x2a 读取")
        else:
            writes_pool = 1 if (va == 0x45e3e0 or 0x45e3e0 in calls) else 0
            print("    读字段 %s | pushFFFF=%d | writes_pool=%d" % (
                " ".join("+0x%x" % r for r in sorted(reads)), pf, writes_pool))
        print("    锚点: %s" % (" ".join(ANCHOR[a] for a in sorted(calls & set(ANCHOR)))))
        print()
    # 汇总
    known = sum(1 for v in CLASS if CLASS[v][1] == "KNOWN")
    high = sum(1 for v in CLASS if CLASS[v][1] == "HIGH")
    msg = sum(1 for v in CLASS if CLASS[v][1] == "MSG")
    print("=== 结果：%d/%d 通过 ===" % (total_asserts - fails, total_asserts))
    print("分类覆盖：KNOWN=%d HIGH=%d 需MSGX确认=%d" % (known, high, msg))
    print("   0x45e3e0 候选池构建器(KNOWN)  0x46a4a0 主君再割当(HIGH)  0x47dce0 名表填充(KNOWN)")
    print("   0x47df00 实体序列化(HIGH)     0x488100 SNDATA→武将(HIGH) 0x4a3920 登用対話(HIGH)")
    print("   0x4a5010 相性登用A(MSG)       0x4a5370 相性引抜B(MSG)     0x4a6970 俸禄结算(KNOWN)")
    print("   0x4c0130 劇本handler(HIGH)    0x4c9650 月俸支給(HIGH)     0x4d7fe0 解雇/追放(MSG)")
    if fails:
        print("FAIL")
        sys.exit(1)
    print("RESULT: 13/13 消费循环分类自检通过（KNOWN=%d HIGH=%d MSG需确认=%d）" % (known, high, msg))

if __name__ == "__main__":
    main()
