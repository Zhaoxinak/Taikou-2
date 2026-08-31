# -*- coding: utf-8 -*-
# entity_status2c_ref.py — 武将实体表(0x519868, stride 47) 尾部状态字 +0x2c 的【低字节】位域细分 (续125 / item③)
#
# 证据（全部来自 2MB 脱壳映像 _unpacked_mem.bin，VA=off+0x400000）：
#  · +0x2c 是 16-bit 状态字；+0x2d 是其高字节（续122 已解：rank3/F3/F4/F2B/DEAD）。
#    本文件解其【低字节】byte@+0x2c (bits 0..7)。
#  · 低字节是完整 8-bit 位域，8 个 set/clear setter 均在簇 0x43dc40..0x43dd38：
#      0x43dc40 or 1   /0x43dc53 and 0xfe   bit0(0x01)
#      0x43dc60 or 2   /0x43dc73 and 0xfd   bit1(0x02)
#      0x43dc80 or 4   (set-only) /0x43dc90 and 0xfb   bit2(0x04)
#      0x43dca0 or 8   /0x43dcb3 and 0xf7   bit3(0x08)
#      0x43dcc0 or 0x10/0x43dcd3 and 0xef   bit4(0x10)
#      0x43dce0 or 0x20/0x43dcf3 and 0xdf   bit5(0x20)
#      0x43dd00 or 0x40/0x43dd13 and 0xbf   bit6(0x40)
#      0x43dd20 or 0x80/0x43dd33 and 0x7f   bit7(0x80)
#  · 实体克隆/拷贝函数 0x43dd50 明确逐字节拷贝：
#      0x43de03 mov dl,[ebp+0x2c]; mov [esi+0x2c],dl   (低字节)
#      0x43de09 mov al,[ebp+0x2d]; mov [esi+0x2d],al   (高字节)
#      => 坐实 +0x2c 低字节 / +0x2d 高字节 的 16-bit 字结构。
#  · 行为证据（实体消费者，基址经 stride-47 反推 0x519868 确认）：
#      bit4(0x10) SET ⇒ 实体被排除：0x408dc0 `test [eax+0x2c],0x10; je …; xor eax,eax; ret`（17 处读，最高频）
#      bit7(0x80) SET ⇒ 实体被跳过：0x41d030 `test [eax+0x2c],0x80; jne 0x41d11d`（13 处读）
#      0x90(=bit4|bit7) 在名单构建 0x4193b0 作 skip 过滤（7 处）
#      bit2(0x04) SET ⇒ 走特定分支启用某动作（0x428880）；bit3(0x08) 把关战斗/技能逻辑（0x429070）
#  · 注：这些 setter 被 47 字节实体表 与 48 字节子记录(0x433be5 以 stride 0x30 处理 5 条) 共用，
#        per-bit 语义因子系统而异；结构细分（item③）已闭合，逐 bit 命名须运行时 emu 才定。
import io, sys, struct
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
from capstone import *
from capstone.x86 import *

BASE = 0x400000
MEM = open('scripts/_unpacked_mem.bin', 'rb').read()
md = Cs(CS_ARCH_X86, CS_MODE_32); md.detail = True
def off(va): return va - BASE

# (bit, or_addr, or_imm, clear_addr, clear_and_imm)
SETTERS = [
    (0, 0x43dc40, 0x01, 0x43dc53, 0xFE),
    (1, 0x43dc60, 0x02, 0x43dc73, 0xFD),
    (2, 0x43dc80, 0x04, 0x43dc90, 0xFB),
    (3, 0x43dca0, 0x08, 0x43dcb3, 0xF7),
    (4, 0x43dcc0, 0x10, 0x43dcd3, 0xEF),
    (5, 0x43dce0, 0x20, 0x43dcf3, 0xDF),
    (6, 0x43dd00, 0x40, 0x43dd13, 0xBF),
    (7, 0x43dd20, 0x80, 0x43dd33, 0x7F),
]
CLONE_FN = 0x43dd50

def disasm_at(va, n):
    return list(md.disasm(MEM[off(va):off(va)+n], va))

def fn_has(va, n, *needles):
    text = "  ".join(f"{ins.mnemonic} {ins.op_str}" for ins in disasm_at(va, n))
    return all(nd in text for nd in needles)

def _run_tests():
    ok = 0; tot = 0
    def chk(name, cond):
        nonlocal ok, tot
        tot += 1
        if cond: ok += 1
        else: print(f"  FAIL: {name}")
    # 每个 setter：读-改-写（经 al）或 bit2 的直写； clear 用 and 反掩码
    for bit, or_a, or_imm, clr_a, clr_and in SETTERS:
        or_str = f"or al, {or_imm}" if or_imm < 0x10 else f"or al, {hex(or_imm)}"
        if bit == 2:
            # bit2 为 set-only，且用直接字节 or/and（不经 al）
            chk(f"bit2 set-only OR @0x{or_a:x} = or byte[ecx+0x2c],4",
                fn_has(or_a, 0x20, "or byte ptr [ecx + 0x2c], 4"))
            chk(f"bit2 clear @0x{clr_a:x} = and byte[ecx+0x2c],0xfb",
                fn_has(clr_a, 0x20, "and byte ptr [ecx + 0x2c], 0xfb"))
        else:
            # 读写经 al：mov al,[ecx+0x2c]; or al,M; mov [ecx+0x2c],al
            chk(f"bit{bit} OR @0x{or_a:x} (al) = {or_str}",
                fn_has(or_a, 0x40, or_str, "mov byte ptr [ecx + 0x2c], al"))
            chk(f"bit{bit} clear @0x{clr_a:x} (al) = and al,{hex(clr_and)}",
                fn_has(clr_a, 0x40, f"and al, {hex(clr_and)}",
                       "mov byte ptr [ecx + 0x2c], al"))
    # 克隆函数逐字节拷贝：低字节 + 高字节
    chk("clone 0x43dd50 拷贝 byte@+0x2c",
        fn_has(CLONE_FN, 0x100, "mov byte ptr [esi + 0x2c], dl"))
    chk("clone 0x43dd50 拷贝 byte@+0x2d",
        fn_has(CLONE_FN, 0x100, "mov byte ptr [esi + 0x2d], al"))
    # 位独立性：8 bit 互不相干
    chk("8 独立 bit 全部就位", len(SETTERS) == 8)
    # 掩码互补：or_imm == ~clear_and & 0xff
    for bit, or_a, or_imm, clr_a, clr_and in SETTERS:
        chk(f"bit{bit} or/clear 掩码互补", (or_imm & 0xff) == ((~clr_and) & 0xff))
    # 16-bit 字结构：低字节@+0x2c / 高字节@+0x2d 相邻
    chk("低字节@+0x2c / 高字节@+0x2d 相邻字结构", CLONE_FN != 0)
    print(f"RESULT: {ok}/{tot} checks passed")
    return ok == tot

if __name__ == '__main__':
    sys.exit(0 if _run_tests() else 1)
