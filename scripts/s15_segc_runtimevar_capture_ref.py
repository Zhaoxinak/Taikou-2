#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
S15 段C 16 处 runtime-var val 运行期取样（续218）
==================================================================
基于 续217 静态定位的 16 处 runtime-var set_c 写者（call_va + owner_fn + segC_idx + 7 语义类），
用 emu_harness.Emu 钩 set_c(0x49c500) 字节级（thiscall, ecx=0x5203c0, byte[ecx+0x13+idx]=val, ret 8），
对 16 个 owner 事件 handler 逐一尝试运行期取样，捕获具体 (idx,val) 配对；崩溃/超时站记录阻塞 VA。

方法：
- 每个 owner 用两种寄存器预置各跑一次，取首个成功捕获 (idx,val) 者：
    preload A「zero」：regs={}（全零，栈全零）
    preload B「ecx=BUF」：regs={ecx=0x5203c0}（set_c 自身用 0x5203c0 作段C 缓冲基，
                      事件 handler 多半是段C 上下文的 thiscall 方法，故以此提升可达性）
- IAT 0x3000 整页 ret 兜底（续209 通则）：所有 `call [0x4fb0xx]` → no-op，避免 Win32 API 崩溃。
- set_c 钩：从 [esp+4] 取 idx(&0xff)、[esp+8] 取 val(1B)，记录 (call_va, idx, val)，抓到首个即 emu_stop 省步数。
- 崩溃：UC_HOOK_CODE 记录 last_eip，异常时取崩溃 VA；步数上限 0x80000 防死循环。

自测：RESULT 形式。
"""
import os, json, sys
from unicorn import Uc, UC_ARCH_X86, UC_MODE_32, UC_HOOK_CODE
from unicorn.x86_const import UC_X86_REG_ESP, UC_X86_REG_ECX
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from emu_harness import Emu

BASE = 0x400000
SET_C = 0x49c500
BUF = 0x5203c0
HERE = os.path.dirname(os.path.abspath(__file__))


def make_emu():
    e = Emu()
    try:
        e.mu.mem_map(0x3000, 0x1000)
        e.mu.mem_write(0x3000, b"\xc3" * 0x1000)
    except Exception:
        pass
    return e


def capture_owner(owner_fn):
    """尝试两种预置跑 owner，返回首个 (idx,val,preload) 或 (None,None,preload,crash_va,crashed)。"""
    preloads = [
        ("zero", {}),
        ("ecx=BUF", {UC_X86_REG_ECX: BUF}),
    ]
    for pname, regs in preloads:
        e = make_emu()
        cap = []
        last = [0]
        def hk(mu, ad, sz, ud):
            last[0] = ad
            if ad == SET_C:
                esp = mu.reg_read(UC_X86_REG_ESP)
                idx = int.from_bytes(mu.mem_read(esp + 4, 4), 'little') & 0xff
                val = int.from_bytes(mu.mem_read(esp + 8, 1), 'little')
                cap.append((idx, val))
                mu.emu_stop()
        hh = e.mu.hook_add(UC_HOOK_CODE, hk)
        crashed = False
        try:
            e.call(owner_fn, [], regs=regs, max_steps=0x80000)
        except Exception:
            crashed = True
        e.mu.hook_del(hh)
        if cap:
            return (cap[0][0], cap[0][1], pname, None, False)
        if crashed:
            return (None, None, pname, last[0], True)
    return (None, None, "all", None, True)


def main():
    checks = 0
    fails = 0
    def ok(c, m):
        nonlocal checks, fails
        checks += 1
        if not c:
            fails += 1
            print(f"  [FAIL] {m}")
        else:
            print(f"  [ ok ] {m}")

    d = json.load(open(os.path.join(HERE, 's15_segc_fullmap.json')))
    rt = [e for e in d['mapping'] if e['val_kind'] == 'runtime-var']
    ok(len(rt) == 16, f"runtime-var 写者 == 16（实得 {len(rt)}）")

    print("=== T1: set_c 钩字节级契约（合成调用）===")
    e = make_emu()
    syn = []
    def hk(mu, ad, sz, ud):
        if ad == SET_C:
            esp = mu.reg_read(UC_X86_REG_ESP)
            syn.append((int.from_bytes(mu.mem_read(esp + 4, 4), 'little') & 0xff,
                        int.from_bytes(mu.mem_read(esp + 8, 1), 'little')))
    hh = e.mu.hook_add(UC_HOOK_CODE, hk)
    for idx in range(6):
        e.call(SET_C, [idx, (idx * 7) & 0xff], regs={UC_X86_REG_ECX: BUF})
    e.mu.hook_del(hh)
    ok(len(syn) == 6, f"set_c 钩捕获 6 次合成调用（实得 {len(syn)}）")
    ok(all(syn[i][0] == i for i in range(6)), "合成 idx 与传入一致")

    print(f"\n=== T2: 16 owner 运行期取样（钩 set_c 抓 (idx,val)）===")
    results = []
    for en in rt:
        cva = en['set_c_call']
        ofn = int(en['owner_fn'], 16)
        ei = en.get('segC_idx')
        r = capture_owner(ofn)
        results.append((cva, en['owner_fn'], r))
        if r[0] is not None:
            tag = f"reach(zero):idx={r[0]},val={r[1]},preload={r[2]}"
        elif r[3] is not None:
            tag = f"crash@{r[3]:#08x}({r[2]})"
        else:
            tag = f"timeout({r[2]})"
        print(f"  {cva} owner={en['owner_fn']} segC[{ei}] -> {tag}")

    ncap = sum(1 for x in results if x[2][0] is not None)
    ncrash = sum(1 for x in results if x[2][0] is None and x[2][3] is not None)
    nto = sum(1 for x in results if x[2][0] is None and x[2][3] is None)
    print(f"\n  可达(零态产物) {ncap} / 崩溃 6 注={ncrash} / 超时 {nto}")
    print("  （注：零态下可达的 (idx,val) 是 handler 在无游戏态时的产物，val 多为 0/30，")
    print("   非真实事件值；真实值须 boot 事件解释器或构造每 handler 的事件上下文。）")
    ok(ncap + ncrash + nto == 16, "16 站全部分类（可达/崩溃/超时）")

    print("\n=== T3: 可达站捕获 idx 有效性（段C 索引域 [0,5]）+ 与 fullmap 一致性(信息) ===")
    valid = 0
    for cva, ofn, (idx, val, pre, crash, crashed) in results:
        if idx is None:
            continue
        in_range = 0 <= idx <= 5
        if in_range:
            valid += 1
        en = [x for x in rt if x['set_c_call'] == cva][0]
        ei = int(en['segC_idx'])
        m = "==" if idx == ei else "!="
        print(f"  {cva} 捕获 idx={idx}(域{'OK' if in_range else 'BAD'}) "
              f"fullmap segC_idx={ei} {m} val={val}(零态产物)")
        ok(in_range, f"{cva} 捕获 idx={idx} 属有效段C 索引 [0,5]")
    ok(valid == ncap, f"全部 {ncap} 个可达 idx 均有效（范围 [0,5]）")

    out = {
        "reached_zero_state": [{"call_va": cva, "owner_fn": ofn, "idx": r[0], "val": r[1],
                                "preload": r[2], "note": "零态产物·非真实游戏值"}
                               for cva, ofn, r in results if r[0] is not None],
        "crashed": [{"call_va": cva, "owner_fn": ofn, "crash_va": r[3], "preload": r[2]}
                    for cva, ofn, r in results if r[0] is None and r[3] is not None],
        "timeout": [{"call_va": cva, "owner_fn": ofn, "preload": r[2]}
                    for cva, ofn, r in results if r[0] is None and r[3] is None],
        "note": "孤立跑 owner 无法取得可信运行期值；0/16 可信。真实值须 boot 事件解释器或构造事件上下文。",
    }
    json.dump(out, open(os.path.join(HERE, 's15_segc_runtimevar_capture.json'), 'w'), indent=2)
    print(f"\n  写出 s15_segc_runtimevar_capture.json：reached(零态)={len(out['reached_zero_state'])} "
          f"crashed={len(out['crashed'])} timeout={len(out['timeout'])}")

    print(f"\nRESULT: {checks - fails}/{checks} PASS" + ("" if fails == 0 else f" ({fails} FAIL)"))
    if fails == 0:
        print("ALL PASS ✅")
    else:
        print("NOT ALL PASS ❌")
    return fails == 0


if __name__ == '__main__':
    sys.exit(0 if main() else 1)
