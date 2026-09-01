"""
_ins_index.py — 全镜像可靠指令索引（供字段扫描 / xref 分析复用）

为什么需要它（踩过的坑，勿重复）：
  1. 本脱壳镜像几乎无标准栈帧序言（全 2MB 仅 80 处 push ebp;mov ebp,esp），
     函数边界必须用「所有 call rel32 目标」推导。
  2. 线性反汇编若从任意字节开始，指令边界会错位 —— 之前的字段扫描
     因此只抓到 1 条命中。必须从真实函数起点开始。
  3. MSVC 常用 `lea reg,[..]; jmp <cont>` 三元表达式编译模式，
     若在 jmp 处停止索引，续体代码会整个丢失。
     => 用队列把 jmp/条件跳转的目标也当作新起点继续反汇编，迭代到收敛。

用法：
    from _ins_index import build_index
    idx = build_index()                 # ~几秒，返回 InsIndex
    ins = idx.ins_containing(0x40c41a)  # 按「包含」匹配（立即数落在指令中间）
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

import struct
import capstone

BASE = 0x400000
TEXT_LO, TEXT_HI = 0x401000, 0x4f0000


class InsIndex:
    def __init__(self, ins_at):
        self.ins_at = ins_at

    def __len__(self):
        return len(self.ins_at)

    def ins_at_addr(self, va):
        return self.ins_at.get(va)

    def ins_containing(self, va, max_back=10):
        """返回「字节地址 va 落在其中间」的指令（用于立即数 xref 匹配）。"""
        for back in range(0, max_back):
            a = va - back
            ins = self.ins_at.get(a)
            if ins and ins.address <= va < ins.address + len(ins.bytes):
                return ins
        return None

    def next_addr(self, ins):
        return ins.address + len(ins.bytes)


def _md():
    md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)
    md.detail = True
    return md


def build_index(img_path=_ROOT + '/scripts/_unpacked_mem.bin', verbose=True):
    MEM = open(img_path, 'rb').read()
    md = _md()

    # 1) 种子：所有 call rel32 目标
    seeds = set()
    for i in range(0, len(MEM) - 5):
        if MEM[i] == 0xE8:
            rel = struct.unpack('<i', MEM[i + 1:i + 5])[0]
            t = BASE + i + 5 + rel
            if TEXT_LO <= t < TEXT_HI:
                seeds.add(t)

    ins_at = {}
    queue = sorted(seeds)
    seen_starts = set()

    while queue:
        start = queue.pop(0)
        if start in seen_starts:
            continue
        seen_starts.add(start)
        if not (TEXT_LO <= start < TEXT_HI):
            continue
        off = start - BASE
        for ins in md.disasm(MEM[off:off + 0x4000], start):
            if ins.address in ins_at:
                break                      # 已被其它流覆盖 → 边界一致，停
            ins_at[ins.address] = ins
            if ins.mnemonic == 'ret':
                break
            # jmp / jcc 的目标作为新起点
            if ins.mnemonic == 'jmp' and ins.operands and \
               ins.operands[0].type == capstone.x86.X86_OP_IMM:
                queue.append(ins.operands[0].imm)
                break
            if ins.mnemonic.startswith('j') and ins.operands and \
               ins.operands[0].type == capstone.x86.X86_OP_IMM:
                queue.append(ins.operands[0].imm)
                continue
            if ins.mnemonic in ('ud2', 'hlt'):
                break

    if verbose:
        print(f"[ins_index] {len(ins_at)} instructions, {len(seen_starts)} starts")
    return InsIndex(ins_at)


if __name__ == '__main__':
    idx = build_index()
    print(f"total instructions: {len(idx)}")
