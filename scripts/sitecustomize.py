# -*- coding: utf-8 -*-
r"""
sitecustomize.py -- 全局打上 capstone 5 的 skipdata 回归补丁（本工程专用）
=====================================================================================
🚨 **为什么需要它（续205）**

capstone ≥5 改变了 `Cs.disasm()` 的 skipdata 行为：遇到不可解码字节时**直接停止迭代**，
既不抛异常、也不像 capstone 4 那样「跳 1 字节继续」。后果是全镜像扫描被**静默截断**：

    实测（本工程 2MB 映像，从 0x401000 起）：
      md.skipdata = True; md.disasm(data, va)  →  仅 11836 条（≈1.3%），call 目标命中 0
      本补丁后的 disasm()                      →  895208 条，call 0x49c390/0x49c3d0 命中 50

本工程 **288 个脚本** 依赖「全镜像反汇编 + 字符串匹配」做字节级 xref。若不打补丁，
所有"全镜像 N 处引用"扫描（以及由此得出的「0 调用方」「静态 0 命中」负结论）
在 capstone 5 环境下全部不可信。

**方案**：monkeypatch `capstone.Cs.disasm`，使其在迭代意外结束时从「最后一条有效指令
末尾」重启；若重启后仍一条都解不出，则前进 1 字节。这样保持原有 API 完全兼容。

⚠️ 只在 `sys.path` 含本目录（即直接运行 `scripts/` 下的脚本）时生效，不影响其它工程。
   需要显式使用安全扫描器时，请 `from _disasm_all import disasm_all`。
"""
try:
    import capstone
    from capstone import Cs as _Cs

    if getattr(_Cs, "_taikou_skip_patched", False):
        raise RuntimeError  # 已打过补丁，跳过

    _orig_disasm = _Cs.disasm

    def _safe_disasm(self, code, addr, count=0):
        """capstone 4 语义：遇非法字节跳 1 字节继续（capstone 5 不再具备）。"""
        pos, n = 0, len(code)
        while pos < n:
            got = 0
            for insn in _orig_disasm(self, code[pos:], addr + pos, count):
                yield insn
                pos = insn.address - addr + insn.size
                got += 1
                if count and got >= count:
                    return
            if got == 0:
                pos += 1

    _Cs.disasm = _safe_disasm
    _Cs._taikou_skip_patched = True
except Exception:  # pragma: no cover
    pass
