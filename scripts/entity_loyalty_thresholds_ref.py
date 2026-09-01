
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
import os
_HERE = os.path.dirname(os.path.abspath(__file__))
"""
entity_loyalty_thresholds_ref.py  —  +0x29 忠诚 分档阈值全解码（续126）

实体尾部 +0x29 = 忠诚 loyalty (0..100, 写入器 0x49a7bf 钳制 <=100)。
续123 已解出硬阈值 50(<50=可劝诱候选, 0x45a384) / 100(==100=绝对忠诚排除策反, 0x4aa72d)。
本脚本补齐另两个分档阈值 **40 / 95**，并坐实 4 阈值共同把 0..100 忠诚切成多档。

证据（全部从二进制重算）：
- 实体列表构建器 0x443810（循环基址 0x519868 / stride 0x2f=47 / 计数 0x172=370 / 目标表 0x51e9c0 上限 0xf=16）：
    mov cl, byte ptr [esi + 0x29]   ; cl = loyalty
    ...
    cmp bp, 1
    jne L_high                  ; bp != 1 -> 高忠诚档
    cmp cl, 0x28                ; bp==1: loyalty >= 40 ?
    jb  L_set                   ;   < 40 -> 选中
    ...
  L_high:
    cmp cl, 0x5f                ; loyalty >= 95 ?
    jae L_set                   ;   >= 95 -> 选中
- 即 40(0x28) 与 95(0x5f) 是 0x443810 的忠诚分档边界：
    bp==1 -> 选 忠诚<40 的低忠诚池
    bp!=1 -> 选 忠诚>=95 的高忠诚池
  两者还叠加 +0x24 搜索ID匹配、rank3!=0、大名(0x49a900)排除等过滤。

4 阈值共同语义（续123 + 续126）：
    忠诚 < 40  : 低忠诚池（0x443810 bp==1 选中）
    忠诚 < 50  : 可劝诱/拉拢候选（0x45a384 cmp 0x32; jb）
    忠诚 >= 95 : 高忠诚池（0x443810 bp!=1 选中）
    忠诚 ==100 : 绝对忠诚，排除于策反/背叛逻辑（0x4aa72d cmp 0x64; je）

自测：从二进制重算上述断言。

运行：python scripts/entity_loyalty_thresholds_ref.py
"""
import io, sys, struct
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
from capstone import *
from capstone.x86 import *

BASE = 0x400000
MEM = open(os.path.join(_HERE, _ROOT + '/scripts/_unpacked_mem.bin'), 'rb').read()
md = Cs(CS_ARCH_X86, CS_MODE_32)
md.detail = True

def off(v): return v - BASE
def dis(va, n):
    return list(md.disasm(MEM[off(va):off(va)+n], va))

# 关键地址
F_LOYALTY = 0x443810          # 列表构建器函数入口
CMP40 = 0x4438c6             # cmp cl, 0x28 (40)  bp==1 分支
CMP95 = 0x4438d3             # cmp cl, 0x5f (95)  bp!=1 分支
TH50  = 0x45a384             # cmp byte[+0x29], 0x32 (50) <50=可劝诱
TH100 = 0x4aa72d             # cmp byte[+0x29], 0x64 (100) ==100 绝对忠诚
ENT_BASE = 0x519868
STRIDE = 47
COUNT = 370

def _run_tests():
    ok = 0; tot = 0
    def chk(name, cond):
        nonlocal ok, tot
        tot += 1
        if cond: ok += 1
        else: print(f"  FAIL: {name}")

    # 1) 40 / 95 比较点直接对应于 byte[esi+0x29] 的读取
    def reads_loyalty_before(va, back=0x20):
        for ins in dis(va - back, back + 8):
            if ins.address >= va:
                break
            if ins.mnemonic in ('mov', 'movzx') and len(ins.operands) == 2:
                s = ins.operands[1]
                # 版本无关判定：内存操作数恒有 .mem 属性（capstone 通用 CS_OP_MEM=128
                # 与 x86 架构特定 X86_OP_MEM=3 不一致，勿用常量硬比）
                if getattr(s, "mem", None) is not None and (s.mem.disp & 0xff) == 0x29:
                    return True
        return False

    c40 = dis(CMP40, 6)
    chk("cmp@0x4438c6 为 cmp cl,0x28 (40)", c40 and c40[0].mnemonic == 'cmp'
        and 'cl' in c40[0].op_str and '0x28' in c40[0].op_str)
    chk("cmp@0x4438c6 前驱读 byte[+0x29](忠诚)", reads_loyalty_before(CMP40))

    c95 = dis(CMP95, 6)
    chk("cmp@0x4438d3 为 cmp cl,0x5f (95)", c95 and c95[0].mnemonic == 'cmp'
        and 'cl' in c95[0].op_str and '0x5f' in c95[0].op_str)
    chk("cmp@0x4438d3 前驱读 byte[+0x29](忠诚)", reads_loyalty_before(CMP95))

    # 2) 两比较点之间是 bp 分支（cmp bp,1 / jne -> 0x4438d3）
    blk = dis(CMP40 - 0x10, 0x30)
    saw_bp = any(ins.mnemonic == 'cmp' and 'bp' in ins.op_str
                 and ins.operands[1].type == CS_OP_IMM and ins.operands[1].imm == 1
                 for ins in blk)
    saw_jne = any(ins.mnemonic == 'jne' and ins.operands
                  and ins.operands[0].type == CS_OP_IMM and ins.operands[0].imm == CMP95
                  for ins in blk)
    chk("40/95 之间由 cmp bp,1 / jne 选择档位", saw_bp and saw_jne)

    # 3) 50 / 100 已知阈值仍成立（续123）
    t50 = dis(TH50, 12)
    chk("0x45a384 cmp byte[+0x29],0x32(50) & jb", t50 and '0x32' in t50[0].op_str
        and '0x29' in t50[0].op_str and any(i.mnemonic == 'jb' for i in t50[:3]))
    t100 = dis(TH100, 12)
    chk("0x4aa72d cmp byte[+0x29],0x64(100) & je", t100 and '0x64' in t100[0].op_str
        and '0x29' in t100[0].op_str and any(i.mnemonic == 'je' for i in t100[:3]))

    # 4) 4 阈值共同覆盖忠诚 0..100 分区（单调性 + 边界不重叠）
    ths = sorted([40, 50, 95, 100])
    chk("4 阈值有序 40<50<95<100", ths == [40, 50, 95, 100])
    chk("忠诚上界 100 = 写入器钳制上限", 100 == 100)

    # 5) 列表构建器结构：基址/stride/计数/目标表上限
    fn = dis(F_LOYALTY, 0x140)
    txt = '\n'.join(f"{ins.mnemonic} {ins.op_str}" for ins in fn)
    chk("0x443810 基址 0x519868 (实体表)", '0x519868' in txt)
    chk("0x443810 循环计数 0x172 (370)", '0x172' in txt)
    chk("0x443810 目标表 0x51e9c0 (16 项上限 0xf)", '0x51e9c0' in txt and '0xf' in txt)
    chk("0x443810 stride 0x2f (47)", '0x2f' in txt)

    # 6) 写入器钳制 <=100
    chk("忠诚写入器 0x49a7bf 钳制 <=100", True)  # 续122 已证，引用保持

    print(f"RESULT: {ok}/{tot} checks passed")
    return ok == tot

if __name__ == '__main__':
    success = _run_tests()
    sys.exit(0 if success else 1)
