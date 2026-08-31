# -*- coding: utf-8 -*-
"""
扫描 set_c(0x49c500) 全部调用点，提取 (idx=[esp+4], val=[esp+8])，按 idx(0..5) 归类，
统计每段C字节的取值分布，并 dump 调用函数的 MSGX 锚点，用于定语义。
"""
import os, bisect, pickle, sys, json, collections
import importlib.util

HERE = os.path.dirname(os.path.abspath(__file__))
# 复用 _s15_bit_locate 的工具（MEM/md/FSTART_VA/fn_of/BYFUNC/txt）
spec = importlib.util.spec_from_file_location("bl", os.path.join(HERE, "_s15_bit_locate.py"))
bl = importlib.util.module_from_spec(spec)
# 避免触发 bl.main()
spec.loader.exec_module(bl)

MEM = bl.MEM
md = bl.md
BASE = bl.BASE
FSTART_VA = bl.FSTART_VA
fn_of = bl.fn_of
BYFUNC = bl.BYFUNC
txt = bl.txt
hx = bl.hx

SET_C = 0x49c500


def resolve_reg_val(reg, stop_addr, ins_list):
    """在 ins_list 中、地址 < stop_addr 范围内，找最近一次 `mov <reg>, imm`。"""
    for it in reversed(ins_list):
        if it.address >= stop_addr:
            continue
        if it.mnemonic == "mov" and it.op_str.startswith(reg + ","):
            rhs = it.op_str.split(",", 1)[1].strip()
            try:
                return int(rhs, 16) if rhs.startswith("0x") else int(rhs)
            except ValueError:
                return None
    return None


def push_args_before(call_va, span=0x60):
    off = call_va - BASE - span
    off = max(off, 0)
    ins = list(md.disasm(MEM[off:off + span + 0x10], BASE + off))
    pushes = []  # (addr, op_str)
    for it in ins:
        if it.address >= call_va:
            break
        if it.mnemonic == "push":
            pushes.append((it.address, it.op_str))
    last2 = pushes[-2:]
    args = []
    for addr, op in last2:
        op = op.strip()
        if op.startswith("0x"):
            args.append(("imm", int(op, 16)))
        else:
            try:
                args.append(("imm", int(op)))
            except ValueError:
                v = resolve_reg_val(op, addr, ins)
                args.append(("reg", op, v))
    # 顺序：last2[0]=较早push(val), last2[1]=较晚push(idx) -> 返回 (idx, val)
    # 但可能只有1个push，做容错
    if len(args) == 2:
        idx, val = args[1], args[0]
    elif len(args) == 1:
        idx, val = args[0], None
    else:
        idx, val = None, None
    return idx, val, pushes


def main():
    rows = []  # (idx, val, call_va, fn)
    i = 0
    while True:
        i = MEM.find(b"\xe8", i)
        if i < 0:
            break
        rel = int.from_bytes(MEM[i + 1:i + 5], "little", signed=True)
        va = BASE + i
        tgt = va + 5 + rel
        if tgt == SET_C:
            idx, val, pushes = push_args_before(va)
            fn = fn_of(va)
            rows.append((idx, val, va, fn, pushes))
        i += 1

    print("== set_c(0x49c500) 调用点 %d 处 ==" % len(rows))
    byidx = collections.defaultdict(list)
    for idx, val, call_va, fn, pushes in rows:
        key = idx[1] if (idx and idx[0] == "imm") else (("reg:%s" % idx[1]) if idx else "??")
        byidx[key].append((val, call_va, fn, pushes))

    for key in sorted(byidx, key=lambda k: (str(k) == "??", str(k))):
        items = byidx[key]
        print("\n########## 段C 索引 %s  : %d 处写入 ##########" % (key, len(items)))
        valdist = collections.Counter()
        for val, call_va, fn, pushes in items:
            vstr = val[1] if (val and val[0] == "imm") else (("reg:%s" % val[1]) if val else "??")
            if val and val[0] == "imm":
                valdist[val[1]] += 1
            pctx = " | ".join("%s %s" % (a, o) for a, o in pushes[-3:])
            print("   val=%-8s call@0x%06x fn=0x%06x  ctx: %s" % (vstr, call_va, fn, pctx))
        if valdist:
            print("   -> val 分布:", dict(sorted(valdist.items())))

    # 每个 idx 的调用函数 MSGX 锚点
    print("\n\n############ 各段C索引写入函数的 MSGX 锚点 ############")
    for key in sorted(byidx, key=lambda k: (str(k) == "??", str(k))):
        fns = sorted(set(r[2] for r in byidx[key]))
        print("\n===== 段C idx %s : %d 个写入函数 =====" % (key, len(fns)))
        for fn in fns:
            own = BYFUNC.get(fn, [])
            print("  -- fn 0x%06x  本体MSGX(%d) --" % (fn, len(own)))
            for s in own:
                for ii in s["ids"]:
                    if isinstance(ii, int):
                        print("     0x%x [%d] %s" % (ii, ii, txt(ii)))
    return byidx


if __name__ == "__main__":
    main()
