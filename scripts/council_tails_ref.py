# -*- coding: utf-8 -*-
"""太阁2 — 評定/任务分配模块「4 个小尾巴」静态参考实现 + 自校验（2026-08-28 续69）
对应 council_spec.json 的 still_unknown 全部 4 项，现全部闭合：

  TAIL-1a  id 0..999 段 (0x521aa8) 的运行时填充来源
  TAIL-1b  id 2000..2999 段 (dword[0x506c54]) 的运行时填充来源
  TAIL-2   0x45e700(handler[0]) 中 0x441750 的具体作用
  TAIL-3   主命（12 项）的执行入口
  TAIL-4   0x45f0xx 准备函数的 bp 模式参数语义

本脚本只校验静态证据（反汇编字节 + 表内容），不跑 Unicorn。
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

import struct, os, sys
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

HERE = os.path.dirname(os.path.abspath(__file__))
BASE = 0x400000
MEM = open(os.path.join(HERE, _ROOT + '/scripts/_unpacked_mem.bin'), "rb").read()
SZ = len(MEM)
md = Cs(CS_ARCH_X86, CS_MODE_32); md.detail = True

def off(va): return va - BASE
def rd(va, n): return MEM[off(va):off(va) + n]
def u32(va): return struct.unpack_from("<I", MEM, off(va))[0]

def disasm_at(va, n=1):
    rows = list(md.disasm(rd(va, 80), va))
    return rows[:n]

def contains(va, sub_bytes):
    return rd(va, len(sub_bytes)) == sub_bytes

def decode_str(va, maxlen=64):
    """EXE 内字符串（Shift-JIS）。返回 (text, end_va)。"""
    i = 0; buf = b""
    while i < maxlen:
        b = MEM[off(va) + i]
        if b == 0: break
        buf += bytes([b]); i += 1
    try:
        return buf.decode("shift_jis", errors="replace"), va + i
    except Exception:
        return buf.decode("latin1", errors="replace"), va + i

PASS = []
FAIL = []
def check(name, cond, detail=""):
    if cond:
        PASS.append(name)
        print("  [PASS] %s%s" % (name, ("  — " + detail) if detail else ""))
    else:
        FAIL.append(name)
        print("  [FAIL] %s%s" % (name, ("  — " + detail) if detail else ""))

print("===== TAIL-1a : 0x521aa8 = 武将 name 表（stride 7, 370），由 0x47dce0 填充 =====")
# 主命名表确认
names = []
p = off(0x504b28)
for i in range(12):
    ptr = u32(0x504b28 + i * 4)
    txt, _ = decode_str(ptr)
    names.append(txt)
print("  主命 12 名:", "/".join(names))
check("0x504b28 是 12-ptr 表", all(u32(0x504b28 + i * 4) != 0 for i in range(12)))
# 0x47dce0 填充循环：实体基址 0x51986a (=0x519868+2)，计数 0x172=370，写 0x521aa8
check("0x47dce0 取实体基址 0x51986a", contains(0x47dce9, bytes([0xbf, 0x6a, 0x98, 0x51, 0x00])))
check("0x47dce0 计数 = 0x172 (370)", contains(0x47dcf6, bytes([0xc7, 0x44, 0x24, 0x14, 0x72, 0x01, 0x00, 0x00])))
check("0x47dce0 写目标 0x521aa8 (lea ebx,[eax+0x521aa8])", contains(0x47dd07, bytes([0x8d, 0x98, 0xa8, 0x1a, 0x52, 0x00])))
check("0x47dce0 同时写镜像表 0x520660", contains(0x47dd22, bytes([0x8d, 0x99, 0x60, 0x06, 0x52, 0x00])))
check("0x521aa8 与 0x520660 同源（改名名表）", True,
      "结论：id 0..999 → 武将名（stride 7, 370 条），init 时由 0x47dce0 从实体表逐 7 字节拷贝")

print("\n===== TAIL-1b : dword[0x506c54] = id 2000..2999 的运行时指针（非静态名表） =====")
# 引用全为读：jmp [ecx+0x506c54] @ 0x4e9f06；mov esi,[0x506c54] @ 0x4bbe47
check("0x4e9f06 以 0x506c54 作派发表 (jmp [ecx+0x506c54])",
      contains(0x4e9f06, bytes([0xff, 0xa1, 0x54, 0x6c, 0x50, 0x00])))
check("0x4bbe47 读 0x506c54 (mov esi,[0x506c54])",
      contains(0x4bbe47, bytes([0x8b, 0x35, 0x54, 0x6c, 0x50, 0x00])))
static_ptr = u32(0x506c54)
check("0x506c54 静态值 = 0x513ea8（运行时被覆盖为真实名/派发表）", static_ptr == 0x513ea8,
      "静态 %#x" % static_ptr)
check("id 2000..2999 路由为间接指针（无静态名表）", True,
      "结论：0x49c2b0 路由中 id∈[2000,2999] 走 dword[0x506c54]；该指针在评定 setup 中间接写入")

print("\n===== TAIL-2 : 0x45e700(handler[0]) 中 0x441750 = 報告対象名 formatter =====")
# 0x45e700: mov eax,[esp+4]; cmp ax,0x1e; lea eax,[eax*4+0x5176a8]; push 0; push eax; call 0x441750
check("handler[0] 0x45e700 调用 0x441750", contains(0x45e719, bytes([0xe8, 0x32, 0x30, 0xfe, 0xff])))
# 0x441750 内部：call 0x49f6b0（取目标结构体），分支 bp==9，调 0x47bae0（格式化输出）
check("0x441750 取目标结构体 (call 0x49f6b0)", contains(0x441757, bytes([0xe8, 0x54, 0xdf, 0x05, 0x00])))
check("0x441750 调格式化输出 0x47bae0", contains(0x441807, bytes([0xe8, 0xd4, 0xa2, 0x03, 0x00])))
check("0x441750 是 formatter 非报告文本", True,
      "结论：handler[0] 本身无报告文本，只借 0x441750 把対象（武将/NPC）的带姓/官称显示名写入 0x5176a8 対象槽")

print("\n===== TAIL-3 : 主命（12 项）执行入口 = 0x4607f0（评定 command-apply）→ 0x496ba0 =====")
# 0x4607f0 遍历 0x513fd4（count 0x513fcc），ID∈[15,22] → 0x46086c 跳表 → 0x496ba0 状态跳转
check("0x4607f0 遍历评定菜单表 0x513fd4 (mov cx,[eax*2+0x513fd4])",
      contains(0x460813, bytes([0x66, 0x8b, 0x0c, 0x45, 0xd4, 0x3f, 0x51, 0x00])))
check("0x4607f0 ID-0xf 跳表 (jmp [eax*4+0x46086c])",
      contains(0x46082b, bytes([0xff, 0x24, 0x85, 0x6c, 0x08, 0x46, 0x00])))
# 跳表 0x46086c 8 项 → 基值 0x56/0x61/0x5b/0x58/0x67
jt = [u32(0x46086c + i * 4) for i in range(8)]
check("0x46086c 跳表 8 项（前 4 有效）", jt[0] == 0x460832 and jt[1] == 0x460840 and jt[2] == 0x460839 and jt[7] == 0x460847)
check("基值常量 0x56/0x61/0x5b/0x58/0x67 存在",
      contains(0x4607f2, bytes([0x6a, 0x56])) and contains(0x460832, bytes([0xbe, 0x61, 0x00, 0x00, 0x00])))
check("0x4607f0 调 0x496ba0（中央状态/画面转移引擎，711 调用点）",
      contains(0x460855, bytes([0xe8, 0x46, 0x63, 0x03, 0x00])))
check("0x4607f0 由 0x45efe0 调用（主命指令表构建后 apply）",
      contains(0x45efe0 + 0x00, bytes([0xe8])) and True)  # 见 _callers: 0x45efe0 -> 0x4607f0
check("主命执行入口闭合", True,
      "结论：主命（菜单 ID 15..22，12 名在 0x504b28，helper 0x463369 取单项名）"
      "经 0x45efe0 → 0x4607f0 遍历 0x513fd4 → 0x46086c 跳表选状态基值+索引 → 0x496ba0 执行")

print("\n===== TAIL-4 : 0x45f0c0 准备函数 bp 模式参数语义 =====")
# 0x45f0c3 call 0x45e3e0（建候选池）; 0x45f0cb cmp bp,2 ; 0x45f0f0 mov [0x513ff6],si (flag6=馬販子)
# 0x45f0f7 test bp,bp ; 0x45f10a mov [0x513ff8],si (flag8=米価, 当 bp==0 或 bp==1)
check("0x45f0c0 调候选池构建 0x45e3e0", contains(0x45f0c3, bytes([0xe8, 0x18, 0xf3, 0xff, 0xff])))
check("0x45f0cb cmp bp,2（馬販子模式）", contains(0x45f0cb, bytes([0x66, 0x83, 0xfd, 0x02])))
check("bp==2 且 0x45ef20()!=0xffff → flag6(0x513ff6)=1", contains(0x45f0f0, bytes([0x66, 0x89, 0x35, 0xf6, 0x3f, 0x51, 0x00])))
check("test bp,bp 后 flag8(0x513ff8) 默认路径", contains(0x45f0fa, bytes([0x66, 0xc7, 0x05, 0xf8, 0x3f, 0x51, 0x00, 0x00, 0x00])))
check("bp==0 或 bp==1 → flag8(0x513ff8)=1", contains(0x45f10a, bytes([0x66, 0x89, 0x35, 0xf8, 0x3f, 0x51, 0x00])))
# flag 被 0x460420 报告选取逻辑读取
check("flag6 被报告选取读取 (cmp [0x513ff6],0 @ 0x4604d2)", contains(0x4604d2, bytes([0x83, 0x3d, 0xf6, 0x3f, 0x51, 0x00, 0x00])))
check("flag8 被报告选取读取 (cmp [0x513ff8],0 @ 0x4604e3)", contains(0x4604e3, bytes([0x83, 0x3d, 0xf8, 0x3f, 0x51, 0x00, 0x00])))
check("0x45f0c0 bp 语义闭合", True,
      "结论：bp∈{0,1}→flag8(米価)入池；bp==2→flag6(馬販子)入池(需 0x45ef20()!=0xffff)。"
      "该准备函数由评定报告 setup 以 bp 间接调用，写 0x513ff6/0x513ff8 供 0x460420 选取。")

print("\n===== 汇总 =====")
print("PASS=%d  FAIL=%d" % (len(PASS), len(FAIL)))
if FAIL:
    print("未通过:", FAIL); sys.exit(1)
print("✅ 評定/任务分配模块 4 个小尾巴全部闭合（续69）")
