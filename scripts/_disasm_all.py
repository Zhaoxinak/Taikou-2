# -*- coding: utf-8 -*-
r"""
_disasm_all.py -- 全镜像线性扫描反汇编（修 capstone 5 的 skipdata 静默截断）
=====================================================================================
🚨 **背景（续205 工程卫生·影响面极大）**

本工程大量脚本用「全镜像反汇编 + 字符串匹配」做字节级 xref（找 call 目标、找立即数
引用、统计调用点数量）。历史环境用 `md.skipdata = True` 让 capstone 遇到非法字节时
跳过 1 字节继续；但 **capstone 5.0.1 起该行为变了——遇到非法字节直接停止迭代**，
既不抛异常也不跳过。

实测（本工程映像 `_unpacked_mem.bin`，从 0x401000 起扫）：
  - 旧写法 `md.skipdata=True; md.disasm(data, va)` → **仅 11836 条，止于 0x409117**
    （≈全镜像的 1.3%），call 目标命中 **0** ⇒ 所有"全镜像扫描"结论静默变成空集。
  - 本模块 `disasm_all(...)` → **895208 条**，call `0x49c390`/`0x49c3d0` 命中 **50 处**
    （= 段A 27 + 段B 23，与 `province_name_alias_ref.py` 文档值精确吻合）。

⚠️ 因此：**任何"全镜像 N 处引用"的扫描，未经本模块复跑的结论都不可信**（尤其
   "0 调用方 / 静态 0 命中"这类负结论，可能只是扫描被截断了）。

用法：
    from _disasm_all import disasm_all, insn_index, load_image
    md = Cs(CS_ARCH_X86, CS_MODE_32)
    for ins in disasm_all(md, data, va):        # 生成器，边扫边 yielded
        ...
    # 或一次性取列表（2MB 映像约 3 秒 / 89.5 万条，内存约 300MB，慎用）
    insns = list(disasm_all(md, data, va))
"""
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

BASE = 0x400000


def disasm_all(md, data, va):
    """线性扫描 + 遇非法字节前进 1 字节重启（capstone 5 安全）。

    注意：md 不要开 detail（会慢很多）；需要操作数细节时另行对单函数再 disasm。
    """
    pos, n = 0, len(data)
    while pos < n:
        got = 0
        for ins in md.disasm(data[pos:], va + pos):
            yield ins
            pos = ins.address - va + ins.size
            got += 1
        if got == 0:            # 当前字节不可解码 → 跳过 1 字节
            pos += 1


def disasm_all_list(md, data, va):
    return list(disasm_all(md, data, va))


def new_md(detail=False):
    md = Cs(CS_ARCH_X86, CS_MODE_32)
    md.detail = detail
    return md


def load_image(path=None):
    import os
    if path is None:
        path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            "_unpacked_mem.bin")
    with open(path, "rb") as f:
        return f.read()


def _selftest():
    md = new_md()
    data = load_image()
    insns = disasm_all_list(md, data[0x1000:], 0x401000)
    assert len(insns) > 800000, f"指令数异常({len(insns)}) —— skipdata 截断复发？"
    hits = [i for i in insns if i.mnemonic == "call"
            and i.op_str in ("0x49c390", "0x49c3d0")]
    assert len(hits) == 50, f"段A/B 调用点应为 50，实测 {len(hits)}"
    print(f"_disasm_all selftest: {len(insns)} 条指令, 段A/B 调用点 {len(hits)}/50 => PASS ✅")


if __name__ == "__main__":
    _selftest()
