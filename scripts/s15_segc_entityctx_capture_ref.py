#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
S15 段C runtime-var val：注入实体上下文取样（续219）
==================================================================
续218 实证 6 个 owner 崩溃于 `mov al/bl,[entity_ptr+0x25]`（实体指针零态为 null）。
本批注入**真实实体上下文**使 handler 跑通、钩 set_c 抓到真实运行期 (idx,val)：

  - 映射 0 页为 `entity[entity_idx]` 的 0x47B 拷贝（统一化解 null 实体 deref；
    entity 表 @0x519868 stride 0x47B，370 条，静态映像已初始化）。
  - ecx = 0x5203c0（段C this），ebx = 实体指针（覆盖 0x413d10 经 ebx 传实体）。
  - args[4] = 实体指针（覆盖 0x4113a0 读 [esp+0x14] 传实体）。
  - 对 0x4110d0 在 0x4110e3/0x4110e8 强制 edi/esi = 实体指针（其经 0x49f830 返回实体，
    零态返回 0；强制后读取合法）。
  - IAT 0x3000 整页 ret 兜底（续209 通则）。

对 16 个 runtime-var owner 各扫 entity[0,100,369]，报告可达/崩溃/超时 + 捕获 (idx,val)。
自测：RESULT 形式。
"""
import os, json, sys
from unicorn import Uc, UC_ARCH_X86, UC_MODE_32, UC_HOOK_CODE
from unicorn.x86_const import UC_X86_REG_ESP, UC_X86_REG_ECX, UC_X86_REG_EBX, \
    UC_X86_REG_ESI, UC_X86_REG_EDI
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from emu_harness import Emu

BASE = 0x400000
SET_C = 0x49c500
BUF = 0x5203c0
ENT_BASE = 0x519868          # 实体表基址（续：370×0x47B）
ENT_STRIDE = 0x47b
HERE = os.path.dirname(os.path.abspath(__file__))


def make_emu():
    e = Emu()
    try:
        e.mu.mem_map(0x3000, 0x1000)
        e.mu.mem_write(0x3000, b"\xc3" * 0x1000)
    except Exception:
        pass
    return e


def run_ctx(owner_fn, entity_idx):
    e = make_emu()
    ent = ENT_BASE + entity_idx * ENT_STRIDE
    # 映射 0 页为 entity[entity_idx] 拷贝（null 实体 deref 不再崩溃）
    try:
        e.mu.mem_map(0, 0x1000)
        data = bytes(e.mu.mem_read(ENT_BASE + entity_idx * ENT_STRIDE, ENT_STRIDE))
        e.mu.mem_write(0, data + b"\x00" * (0x1000 - ENT_STRIDE))
    except Exception:
        pass
    cap = []
    last = [0]
    def hk(mu, ad, sz, ud):
        last[0] = ad
        if ad == 0x4110e3:
            mu.reg_write(UC_X86_REG_EDI, ent)      # 0x4110d0: 强制 edi=实体
        elif ad == 0x4110e8:
            mu.reg_write(UC_X86_REG_ESI, ent)      # 0x4110d0: 强制 esi=实体
        elif ad == 0x413db7:
            mu.reg_write(UC_X86_REG_ESI, ent)      # 0x413d10→sub 0x413db0: 强制 esi=实体(经 [esp+0xc] 传入)
        elif ad == SET_C:
            esp = mu.reg_read(UC_X86_REG_ESP)
            idx = int.from_bytes(mu.mem_read(esp + 4, 4), 'little') & 0xff
            val = int.from_bytes(mu.mem_read(esp + 8, 1), 'little')
            cap.append((idx, val))
            mu.emu_stop()
    hh = e.mu.hook_add(UC_HOOK_CODE, hk)
    crashed = False
    try:
        e.call(owner_fn, [0, 0, 0, 0, ent],
               regs={UC_X86_REG_ECX: BUF, UC_X86_REG_EBX: ent}, max_steps=0x80000)
    except Exception:
        crashed = True
    e.mu.hook_del(hh)
    return cap, crashed, last[0]


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
    ok(len(rt) == 16, "runtime-var 写者 == 16")
    SWEEP = [0, 100, 369]

    print("=== T1: 注入实体上下文(0 页=entity 拷贝) 跑 16 owner × entity[0,100,369] ===")
    table = {}
    for en in rt:
        ofn = int(en['owner_fn'], 16)
        per = {}
        for ei in SWEEP:
            cap, crashed, cr = run_ctx(ofn, ei)
            per[ei] = {"captures": cap, "crashed": crashed, "crash_va": cr}
        table[en['set_c_call']] = {"owner_fn": en['owner_fn'], "per_entity": per}
        reach = any(len(v['captures']) > 0 for v in per.values())
        cr_any = any(v['crashed'] for v in per.values())
        tag = "reach" if reach else ("crash" if cr_any else "timeout")
        c0 = per[0]['captures']; c100 = per[100]['captures']; c369 = per[369]['captures']
        print(f"  {en['set_c_call']} owner={en['owner_fn']} segC[{en.get('segC_idx')}] -> {tag} "
              f"e0={c0} e100={c100} e369={c369}")
    nreach = sum(1 for t in table.values()
                if any(len(v['captures']) > 0 for v in t['per_entity'].values()))
    ncrash = sum(1 for t in table.values()
                if any(v['crashed'] for v in t['per_entity'].values())
                and not any(len(v['captures']) > 0 for v in t['per_entity'].values()))
    nto = 16 - nreach - ncrash
    print(f"\n  可达 {nreach} / 崩溃 {ncrash} / 超时 {nto}（续218 零态: 7/6/3）")
    ok(nreach >= 13, "注入实体上下文后可达 >=13（续218 仅 7 可达 → 证明 null 实体=根因）")
    ok(ncrash <= 3, "崩溃降至 <=3（原 6）")

    print("\n=== T2: 续218 崩溃站注入实体后产生真实 (idx,val) ===")
    # 续218 中崩溃的站（全在 [entity+0x25] 缺实体）：0x413d4f/0x413d80/0x413d9c/0x413d65(owner 0x413d10)、
    # 0x41112f(owner 0x4110d0)、0x41144a(owner 0x4113a0)。注入后须可达且给出具体值。
    crash_sites_218 = {"0x413d4f", "0x413d80", "0x413d9c", "0x413d65",
                       "0x41112f", "0x41144a"}
    newly = 0
    for cva in crash_sites_218:
        t = table.get(cva)
        if t is None:
            continue
        caps = [c for ei in SWEEP for c in t['per_entity'][ei]['captures']]
        if caps:
            newly += 1
            print(f"  {cva} 注入后可达，捕获 (idx,val)={caps}")
        else:
            print(f"  {cva} 注入后仍无捕获")
    ok(newly >= 5, f"续218 崩溃站注入实体后 >=5 站可达并给值（实得 {newly}/6）")
    # 具体真实值断言：segC[3] 写者 0x41112f 须 idx==3（槽 3）；0x41144a 须捕获 idx∈[0,5]
    cva = "0x41112f"; t = table.get(cva)
    cap311 = [c for ei in SWEEP for c in t['per_entity'][ei]['captures']] if t else []
    ok(any(idx == 3 for (idx, val) in cap311), f"0x41112f(segC[3]) 捕获 idx==3（实得 {cap311}）")
    cva = "0x41144a"; t = table.get(cva)
    cap144 = [c for ei in SWEEP for c in t['per_entity'][ei]['captures']] if t else []
    ok(len(cap144) > 0 and all(0 <= idx <= 5 for (idx, val) in cap144),
       f"0x41144a(segC[edx]) 捕获 idx∈[0,5]（实得 {cap144}）")

    print("\n=== T3: 捕获 idx 有效性（段C 索引域 [0,5]）===")
    bad = 0
    for t in table.values():
        for ei in SWEEP:
            for (idx, val) in t['per_entity'][ei]['captures']:
                if not (0 <= idx <= 5):
                    bad += 1
    ok(bad == 0, f"全部捕获 idx ∈ [0,5]（非法 {bad}）")

    json.dump(table, open(os.path.join(HERE, 's15_segc_entityctx_capture.json'), 'w'), indent=2)
    print(f"\n  写出 s15_segc_entityctx_capture.json")
    print(f"\nRESULT: {checks - fails}/{checks} PASS" + ("" if fails == 0 else f" ({fails} FAIL)"))
    if fails == 0:
        print("ALL PASS ✅")
    else:
        print("NOT ALL PASS ❌")
    return fails == 0


if __name__ == '__main__':
    sys.exit(0 if main() else 1)
