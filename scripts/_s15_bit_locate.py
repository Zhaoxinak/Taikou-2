# -*- coding: utf-8 -*-
"""
定位 S15 每个 bit 的置位函数：扫 set_a(0x49c460)/set_b(0x49c4b0) 全部调用点，
提取 (bit, val, caller_fn)，按 bit 聚类；对未定名 bit 反汇编置位函数找 MSGX 锚点。
"""
import os, bisect, pickle, sys, json, collections
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

HERE = os.path.dirname(os.path.abspath(__file__))
BASE = 0x400000
MEM = open(os.path.join(HERE, "_unpacked_mem.bin"), "rb").read()
md = Cs(CS_ARCH_X86, CS_MODE_32)
md.detail = False

_d = pickle.load(open(os.path.join(HERE, "_insn_addrs.pkl"), "rb"))
FSTART = sorted(_d[1])               # 文件偏移
FSTART_VA = [x + BASE for x in FSTART]

MSGMAP = json.load(open(os.path.join(HERE, "msgx_id_map.json"), encoding="utf-8"))
TXT = json.load(open(os.path.join(HERE, "msgx_all_texts.json"), encoding="utf-8"))["texts"]
BYFUNC = collections.defaultdict(list)
for s in MSGMAP["sites"]:
    f = s["func"]
    f = f if isinstance(f, int) else int(f, 16)
    BYFUNC[f].append(s)


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


def push_imm_before(call_va, n=2, span=0x30):
    """返回 call 前最近的 n 个 push 立即数（地址降序收集后反转）。"""
    off = call_va - BASE - span
    off = max(off, 0)
    ins = list(md.disasm(MEM[off:off + span + 0x8], BASE + off))
    pushes = []
    for it in ins:
        if it.address >= call_va:
            break
        if it.mnemonic == "push":
            try:
                v = int(it.op_str, 16) if it.op_str.startswith("0x") else int(it.op_str)
                pushes.append((it.address, v))
            except ValueError:
                pushes.append((it.address, None))  # 寄存器/内存 push
    # 取最靠近 call 的两个
    last = [p for p in pushes if p[0] < call_va][-n:]
    return list(reversed(last))


def main():
    setters = {0x49c460: "set_a", 0x49c4b0: "set_b"}
    # 扫全镜像 call 目标
    rows = []  # (setter, bit, val, call_va, fn)
    i = 0
    while True:
        i = MEM.find(b"\xe8", i)
        if i < 0:
            break
        rel = int.from_bytes(MEM[i + 1:i + 5], "little", signed=True)
        va = BASE + i
        tgt = va + 5 + rel
        if tgt in setters:
            bit_val = push_imm_before(va, n=2)
            bit = bit_val[0][1] if len(bit_val) >= 2 else None
            val = bit_val[1][1] if len(bit_val) >= 2 else None
            fn = fn_of(va)
            rows.append((setters[tgt], bit, val, va, fn))
        i += 1

    # 按 bit 聚类
    bybit = collections.defaultdict(list)
    for setter, bit, val, call_va, fn in rows:
        if bit is None:
            continue
        bybit[bit].append((setter, val, call_va, fn))

    print("== set_a/set_b 调用点按 bit 聚类（未定名 bit 高亮）==")
    UNNAMED = {1, 3, 5, 6, 7, 11}
    for bit in sorted(bybit):
        fns = sorted(set(r[3] for r in bybit[bit]))
        mark = "  <<< 未定名" if bit in UNNAMED else ""
        print("\nbit %2d%s  (%d 处, %d 个函数)" % (bit, mark, len(bybit[bit]), len(fns)))
        for setter, val, call_va, fn in bybit[bit]:
            print("   %-5s val=%-4s call@0x%06x  fn=0x%06x" % (setter, str(val), call_va, fn))

    return bybit


if __name__ == "__main__":
    bybit = main()
    # 对未定名 bit，dump 置位函数的 MSGX
    UNNAMED = {1, 3, 5, 6, 7, 11}
    print("\n\n############ 未定名 bit 的置位函数 MSGX 锚点 ############")
    for bit in sorted(UNNAMED):
        if bit not in bybit:
            print("\n[bit %d] 无 set_a/set_b 命中（可能走段C或其它路径）" % bit)
            continue
        fns = sorted(set(r[3] for r in bybit[bit]))
        print("\n===== bit %d : %d 个置位函数 =====" % (bit, len(fns)))
        for fn in fns:
            own = BYFUNC.get(fn, [])
            print("\n  -- fn 0x%06x  本体MSGX(%d) --" % (fn, len(own)))
            for s in own:
                for ii in s["ids"]:
                    if isinstance(ii, int):
                        print("     @0x%06x  0x%x [%d] %s" % (hx(s["at"]), ii, ii, txt(ii)))
