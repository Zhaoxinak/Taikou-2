# -*- coding: utf-8 -*-
"""sndata_payload_consumers_ref.py — 续194 破解 P0：SNDATA 49B payload「消费者地图」

承接续189「type=0x01 = 43 独立布尔开关，须 emu 追运行时消费者」+ 续193「emu 骨架落地」。
本续在**静态**层先把「哪条 record 缓冲区字节被哪个分发 handler 读/写」钉成可复核地图，
作为后续 emu 驱动 / 字段命名的基座（静态先到极限再 emu，方法论一致）。

🔑 核心结论（续194）：
  扇出 `0x47fc60` 把记录三视图落到全局缓冲：
    payload[6:49](43B) -> 0x522c88[0..42]
    [0x13](1B)        -> 0x522c60
    [0x20](1B)        -> 0x522c70
  本脚本全镜像扫描这三个缓冲的字面引用，按「函数地图」(E8 rel32 call 目标 + 已知入口) 归属到
  函数，产出：
    (a) 每缓冲每字节的消费者集合（func_va 列表）；
    (b) 每个 handler 函数读/写了哪些缓冲字节；
    (c) 指令形态(mov/test/cmp/lea) 抽样（区分「按位读」vs「按位写」vs「作索引基址」）。

⇒ 把续189 的「171 型字段指纹」从黑箱推进到「字节偏移 → 消费者函数」的可操作地图，
  字段名须由消费者语义(emu/对照游戏)赋予——本续提供精确坐标。

仍未知（续194 下一步）：① 每个消费者函数对字节的具体操作语义（test bit? cmp 值? 作索引?）
  须 emu 钩 MEM_READ 抓运行期使用；② 消费者函数多数在分发簇(0x492e20/0x492ed0/...)
  内，须 emu 驱动这些 handler 以 payload 钩子落「type→字节→字段名」。

用法：python sndata_payload_consumers_ref.py   （脚本目录 scripts/ 下运行）
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

import os, struct, sys
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
BASE = 0x400000
MEM = open(os.path.join(HERE, _ROOT + '/scripts/_unpacked_mem.bin'), "rb").read()
IMG_LEN = len(MEM)

# 三个目标缓冲
PAYLOAD_BASE = 0x522c88          # 43 字节 payload[6:49]
PAYLOAD_END  = PAYLOAD_BASE + 43 # 0x522cb3 (exclusive)
ONE_A_BASE   = 0x522c60          # rec[0x13] 单字节
ONE_B_BASE   = 0x522c70          # rec[0x20] 单字节

# 已知入口（保证进入函数地图，即使无静态 call）
KNOWN_ENTRIES = [
    0x47fc60, 0x4e8604, 0x4e8625, 0x47b390, 0x47fb80, 0x4802e0, 0x492800, 0x4ec8c0, 0x4f40b0,
    0x480000, 0x47d890, 0x47f350, 0x47ff68, 0x47b160, 0x47b2e0, 0x47ae80,
    # 分发簇（续160 cluster0/1/else）
    0x492e20, 0x493140, 0x48cc20, 0x48d350, 0x48e690, 0x4a0b20,
    0x492ed0, 0x4931f0, 0x4ac9c0, 0x4ae380, 0x4a0b70,
    0x491e70, 0x4873b0, 0x491f90, 0x492050, 0x499050, 0x524740,
]


def build_function_map():
    """全镜像扫描 E8 rel32 call 目标 + 已知入口，建函数起始集合。"""
    funcs = set(KNOWN_ENTRIES)
    n = IMG_LEN
    i = 0
    while i < n - 5:
        if MEM[i] == 0xE8:
            try:
                rel = struct.unpack_from("<i", MEM, i + 1)[0]
            except struct.error:
                i += 1
                continue
            va_site = BASE + i
            tgt = va_site + 5 + rel
            # 仅收映像代码范围内目标
            if BASE <= tgt < BASE + n - 5:
                funcs.add(tgt)
        i += 1
    return sorted(funcs)


def enclosing_func(funcs_sorted, va):
    """返回 <= va 的最大函数起始（归属最近函数）。"""
    lo, hi = 0, len(funcs_sorted)
    import bisect
    idx = bisect.bisect_right(funcs_sorted, va) - 1
    if idx < 0:
        return None
    return funcs_sorted[idx]


def scan_buffer_refs(funcs_sorted):
    """扫描全镜像对 0x522cxx 的字面引用，归属函数，分类到三缓冲。"""
    md = Cs(CS_ARCH_X86, CS_MODE_32)
    md.detail = False
    refs = []  # dict(va, func, buf, off, mnem)
    n = IMG_LEN
    # 地址 0x522cXX 的小端字节序 = XX 2c 52 00；匹配 3 字节后缀 2c 52 00，前 1 字节为 low byte。
    i = 0
    while i < n - 4:
        if MEM[i+1] == 0x2c and MEM[i+2] == 0x52 and MEM[i+3] == 0x00:
            lb = MEM[i]
            addr = 0x00522c00 | lb
            # 分类
            if PAYLOAD_BASE <= addr < PAYLOAD_END:
                buf, off = "payload", addr - PAYLOAD_BASE
            elif addr == ONE_A_BASE:
                buf, off = "oneA[0x13]", 0
            elif addr == ONE_B_BASE:
                buf, off = "oneB[0x20]", 0
            else:
                i += 1
                continue
            ref_va = BASE + i
            func = enclosing_func(funcs_sorted, ref_va)
            # 反汇编该 ref 所在指令（向前 0x10 字节窗口）
            woff = max(0, i - 0x10)
            insns = list(md.disasm(MEM[woff: woff + 0x30], BASE + woff))
            mnem = "?"
            for ins in insns:
                if ins.address <= ref_va < ins.address + ins.size:
                    mnem = f"{ins.mnemonic} {ins.op_str}"
                    break
            refs.append(dict(va=ref_va, func=func, buf=buf, off=off, mnem=mnem))
        i += 1
    return refs


def _selftest():
    funcs = build_function_map()
    print(f"[*] 函数地图规模: {len(funcs)} 个函数起始")
    refs = scan_buffer_refs(funcs)
    print(f"[*] 缓冲字面引用总数: {len(refs)}")

    # 分类统计
    payload_refs = [r for r in refs if r["buf"] == "payload"]
    oneA = [r for r in refs if r["buf"] == "oneA[0x13]"]
    oneB = [r for r in refs if r["buf"] == "oneB[0x20]"]
    print(f"    payload(0x522c88[0..42]) 引用: {len(payload_refs)}")
    print(f"    oneA 0x522c60 引用: {len(oneA)}")
    print(f"    oneB 0x522c70 引用: {len(oneB)}")

    # 每字节消费者集合
    byte_consumers = {}
    for r in payload_refs:
        byte_consumers.setdefault(r["off"], set()).add(r["func"])
    distinct_offs = sorted(byte_consumers.keys())
    print(f"    payload 中被引用的不同字节偏移数: {len(distinct_offs)} / 43")
    print(f"    被引用字节: {distinct_offs}")

    # 每个消费者函数读/写的字节
    func_bytes = {}
    for r in payload_refs:
        func_bytes.setdefault(r["func"], set()).add(r["off"])

    ok = []
    def chk(name, cond, extra=""):
        ok.append(bool(cond))
        print(f"  [{'OK' if cond else 'FAIL'}] {name}{(' — ' + extra) if extra else ''}")

    print("--- T1 payload 缓冲被稀疏引用（续163/164：簇 handler 不直读记录缓冲，payload 经 fan-out + 资源管线整体消费，仅 3 字节偏移被消费）---")
    expected_offs = {0, 16, 24}
    chk("payload 被引用字节偏移 == 已验证稀疏集{0,16,24}", set(distinct_offs) == expected_offs,
        f"实测 {distinct_offs}")

    print("--- T2 无分发簇 handler 直读 payload（续163 0/44 验证：资源身份由记录类型固定，payload 不参与资源选择）---")
    cluster = {0x492e20, 0x492ed0, 0x493140, 0x4931f0, 0x48cc20, 0x48d350,
               0x48e690, 0x4a0b20, 0x4ac9c0, 0x4ae380, 0x4a0b70,
               0x491e70, 0x4873b0, 0x491f90, 0x492050, 0x499050, 0x524740}
    hit_cluster = sorted(set(func_bytes.keys()) & cluster)
    chk("簇 handler 不出现为 payload 直读消费者", len(hit_cluster) == 0,
        f"{len(hit_cluster)} 个: " + (", ".join(f"0x{h:06x}" for h in hit_cluster[:6]) or "无(符合续163)"))

    print("--- T3 单字节缓冲 0x522c60 / 0x522c70 均被引用 ---")
    chk("0x522c60([0x13]) 被引用", len(oneA) >= 1, f"{len(oneA)} 处")
    chk("0x522c70([0x20]) 被引用", len(oneB) >= 1, f"{len(oneB)} 处")

    print("--- T4 所有引用归属到合法函数（func 非 None 且 >= BASE）---")
    none_cnt = sum(1 for r in refs if r["func"] is None)
    chk("无 func==None 的引用(全可归属)", none_cnt == 0, f"{none_cnt} 处无归属")

    print("--- T5 不同消费者函数数 >= 5（地图非平凡）---")
    nfuncs = len(set(r["func"] for r in refs))
    chk("不同消费者函数 >= 5", nfuncs >= 5, f"{nfuncs} 个函数")

    # 抽样打印 top 消费者（按引用字节数）
    print("\n=== 消费者函数 top（按读取的不同 payload 字节数）===")
    top = sorted(func_bytes.items(), key=lambda kv: -len(kv[1]))[:12]
    for f, offs in top:
        mn = sorted(offs)
        print(f"  0x{f:06x}: 读 {len(offs)} 字节, 偏移={mn[:20]}{'...' if len(mn)>20 else ''}")

    print("\n=== 引用形态抽样（前 12 条）===")
    for r in (payload_refs + oneA + oneB)[:12]:
        print(f"  0x{r['va']:06x} [{r['buf']}{('+'+str(r['off'])) if r['buf']=='payload' else ''}] "
              f"in 0x{r['func']:06x}: {r['mnem']}")

    n = sum(ok)
    print(f"\nRESULT: {n}/{len(ok)} checks passed")
    return n == len(ok), byte_consumers, func_bytes


if __name__ == "__main__":
    ok, bc, fb = _selftest()
    sys.exit(0 if ok else 1)
