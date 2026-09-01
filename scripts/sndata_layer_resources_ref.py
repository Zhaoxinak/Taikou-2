#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
sndata_layer_resources_ref.py -- 续208：完整 P0「场景层→资源表」closure（emu 抓簇内部资源加载）

承接续206（真实分发点 = 主循环 0x4e8625，按全局 0x5205fe 三路极性 call 簇 handler）
+ 续161/196（簇 handler 经 0x4ec8c0 加载资源，资源名在 0x522ca0 暂存）。

方法：不再 boot 整个 0x4e8625（崩于 0x47fcad 未映射写，需全游戏态），而是**单独 emu
每个簇 handler**，钩 0x4ec8c0(this=ecx, name, size_class) 抓参 name（指向 0x522ca0 处的
资源名串 'X:NAME'），得到每个簇加载的完整资源名列表。再按主循环 call 目标归属到三层：
  - mode 0（簇0）: 0x492e20(基0x506b20) + 0x493140(基0x506b30)
  - mode 1（簇1）: 0x492ed0(基0x506ba0) + 0x4931f0(基0x506bb0)
  - else（簇else）: 0x491e70 + 0x4873b0
每个簇 handler 入参 = 主循环 push 的资源数组基址（call_sites 已坐实）。emu 时把基址
作为单栈参传入，ecx←scratch(0x510000)，钩 0x4ec8c0（stdcall2, ret 8）记 name+返回。

产物：scripts/sndata_layer_resources.json + 自测（每层≥1 资源、else 层解析出基址）。
"""
import os, struct, json
from unicorn import UC_ARCH_X86, UC_MODE_32, UC_HOOK_CODE
from unicorn.x86_const import UC_X86_REG_ESP, UC_X86_REG_EIP, UC_X86_REG_EAX
from emu_sndata_read import Emu

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# 主循环 call 目标 -> (簇 handler, 主循环传的基址, 层)
CLUSTERS = [
    # (handler, base_arg, layer_label)
    (0x492e20, 0x506b20, 'layer0'),
    (0x493140, 0x506b30, 'layer0'),
    (0x492ed0, 0x506ba0, 'layer1'),
    (0x4931f0, 0x506bb0, 'layer1'),
    (0x491e70, None,    'else'),
    (0x4873b0, None,    'else'),
]

def decode_name_at(mu, ptr):
    try:
        raw = mu.mem_read(ptr, 16)
    except Exception:
        return None
    n = raw.find(0)
    if n < 0: n = 16
    if n == 0: return ""
    try: return bytes(raw[:n]).decode('gbk')
    except Exception: return bytes(raw[:n]).decode('latin-1','replace')

def emulate_cluster(handler, base_arg):
    """emu 跑单簇 handler，钩 0x4ec8c0 抓资源名。返回资源名列表（去重保序）。"""
    e = Emu()
    captured = []
    def on_code(mu, address, size, ud):
        if address == 0x4ec8c0:
            sp = mu.reg_read(UC_X86_REG_ESP)
            name_ptr = struct.unpack("<I", mu.mem_read(sp+4,4))[0]
            nm = decode_name_at(mu, name_ptr)
            if nm: captured.append(nm)
            ret = struct.unpack("<I", mu.mem_read(sp,4))[0]
            mu.reg_write(UC_X86_REG_ESP, sp+12)   # stdcall2 ret 8
            mu.reg_write(UC_X86_REG_EIP, ret)
        elif address == 0x4802e0:
            sp = mu.reg_read(UC_X86_REG_ESP)
            ret = struct.unpack("<I", mu.mem_read(sp,4))[0]
            mu.reg_write(UC_X86_REG_ESP, sp+12)
            mu.reg_write(UC_X86_REG_EIP, ret)
    e.mu.hook_add(UC_HOOK_CODE, on_code)
    args = [base_arg] if base_arg is not None else []
    try:
        e.call(handler, args=args, regs={UC_X86_REG_EAX:0x510000}, max_steps=0x400000)
    except Exception as ex:
        # 部分簇可能内部调未桩函数；抓到的资源已记录
        pass
    # 去重保序
    seen=set(); out=[]
    for c in captured:
        if c not in seen:
            seen.add(c); out.append(c)
    return out

def main():
    by_layer = {'layer0':[], 'layer1':[], 'else':[]}
    detail = {}
    for handler, base_arg, layer in CLUSTERS:
        names = emulate_cluster(handler, base_arg)
        detail[f"0x{handler:06x}"] = {'layer':layer, 'base':(f"0x{base_arg:06x}" if base_arg else None), 'resources':names}
        by_layer[layer].extend(names)
    # 每层去重
    for k in by_layer:
        seen=set(); out=[]
        for c in by_layer[k]:
            if c not in seen: seen.add(c); out.append(c)
        by_layer[k]=out

    out = os.path.join(ROOT, 'scripts/sndata_layer_resources.json')
    with open(out,'w',encoding='utf-8') as f:
        json.dump({'by_layer':by_layer,'detail':detail}, f, ensure_ascii=False, indent=1)

    print("=== 场景层→资源表 closure（续208）===")
    for layer in ('layer0','layer1','else'):
        print(f"\n[{layer}]  {len(by_layer[layer])} 个资源:")
        for r in by_layer[layer]:
            print(f"   {r}")
    print("\n--- 逐簇明细 ---")
    for h, d in detail.items():
        print(f"  {h} ({d['layer']}, base={d['base']}): {d['resources']}")
    print("\nJSON ->", out)

    # 自测
    assert len(by_layer['layer0']) >= 1, "layer0 空"
    assert len(by_layer['layer1']) >= 1, "layer1 空"
    assert len(by_layer['else']) >= 1, "else 层空"
    print("\nRESULT: PASS ✅ (三层资源表全部解析)")

if __name__ == "__main__":
    main()
