#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
_unpack_exe.py — 用 Unicorn 引擎原生执行 TAIK2W95.exe 的脱壳 stub, 静态脱壳。
原理: 把 PE 按 VA 映射到 0x400000, hook 掉 stub 的 4 个 API 调用(返回桩值),
      让真正的自解压代码在内存里把游戏解压出来, 到 OEP(0x4f44b0)停下并 dump 内存。
      无需调试器 / 无需 Windows API 真身 -> 完全静态脱壳。
依赖: unicorn (managed venv)
产物: scripts/_unpacked_mem.bin (原始内存映像 0x400000..) + 控制台验证
"""
import struct
import math
from collections import Counter
from unicorn import *
from unicorn.x86_const import *
from capstone import *

EXE = r"F:/Games/Taikou2/TAIK2W95.exe"
BASE = 0x400000
ENTRY = BASE + 0x1311A0      # 入口 VA
OEP   = BASE + 0xF44B0       # 尾跳转目标 VA (RVA 0xf44b0 + ImageBase)
MEM_END = 0x600000           # 映射 2MB

# API 桩地址 (写入 import 槽, 触发我们的 hook)
H_LOADLIB = 0x590000
H_GETPROC = 0x590004
H_VIRTPROT = 0x590008
H_SLOT3 = 0x59000C

STOP = {"hit_oep": False, "count": 0}

def read_file_sections():
    b = open(EXE, "rb").read()
    # section 1 raw @ 0x400, size 447488 -> VA 0x4c4000
    sec1_off, sec1_size = 0x400, 447488
    # .rsrc raw @ 0x6d800, size 3072 -> VA 0x532000
    rsrc_off, rsrc_size = 0x6d800, 3072
    return b, sec1_off, sec1_size, rsrc_off, rsrc_size

def api_hook_factory(nargs, retval):
    def hook(uc, address, size, user_data):
        esp = uc.reg_read(UC_X86_REG_ESP)
        ret = struct.unpack_from("<I", uc.mem_read(esp, 4))[0]
        uc.reg_write(UC_X86_REG_EAX, retval)
        # stdcall: callee 清理 ret(4) + nargs*4
        uc.reg_write(UC_X86_REG_ESP, esp + 4 + nargs * 4)
        uc.reg_write(UC_X86_REG_EIP, ret)
    return hook

def main():
    b, s1o, s1s, ro, rs = read_file_sections()
    mu = Uc(UC_ARCH_X86, UC_MODE_32)
    mu.mem_map(BASE, MEM_END - BASE, UC_PROT_ALL)

    # 1) PE 头 (file 0..0x400 -> VA BASE)
    mu.mem_write(BASE, b[0:0x400])
    # 2) 节区1 (压缩体)
    mu.mem_write(BASE + 0xC4000, b[s1o:s1o + s1s])
    # 3) .rsrc
    mu.mem_write(BASE + 0x132000, b[ro:ro + rs])

    # 4) 把 4 个 API 桩地址写入 import 槽 (VA = 0x401000 + 0x131a28..)
    BASE_SLOT = 0x401000
    slots = {
        BASE_SLOT + 0x131a28: H_LOADLIB,
        BASE_SLOT + 0x131a2c: H_GETPROC,
        BASE_SLOT + 0x131a30: H_VIRTPROT,
        BASE_SLOT + 0x131a3c: H_SLOT3,
    }
    for va, target in slots.items():
        mu.mem_write(va, struct.pack("<I", target))

    # hook: API 桩
    mu.hook_add(UC_HOOK_CODE, api_hook_factory(1, 0x2000), begin=H_LOADLIB, end=H_LOADLIB)   # LoadLibraryA -> HMODULE
    mu.hook_add(UC_HOOK_CODE, api_hook_factory(2, 0x3000), begin=H_GETPROC, end=H_GETPROC)   # GetProcAddress -> ptr
    mu.hook_add(UC_HOOK_CODE, api_hook_factory(5, 1), begin=H_VIRTPROT, end=H_VIRTPROT)      # VirtualProtect -> 1
    mu.hook_add(UC_HOOK_CODE, api_hook_factory(0, 1), begin=H_SLOT3, end=H_SLOT3)             # 收尾

    # 初始化栈指针 (OS loader 会设好; 这里给合法栈顶, 向下生长)
    mu.reg_write(UC_X86_REG_ESP, 0x5F0000)

    # hook: OEP 停下
    def oep_hook(uc, address, size, user_data):
        STOP["hit_oep"] = True
        uc.emu_stop()
    mu.hook_add(UC_HOOK_CODE, oep_hook, begin=OEP, end=OEP)

    # hook: 指令数上限, 防死循环
    def count_hook(uc, address, size, user_data):
        STOP["count"] += 1
        if STOP["count"] > 30_000_000:
            uc.emu_stop()
    mu.hook_add(UC_HOOK_CODE, count_hook)

    print(f"入口 VA={ENTRY:#x}  OEP VA={OEP:#x}  开始原生执行 stub ...")
    try:
        mu.emu_start(ENTRY, 0)
    except UcError as e:
        print(f"[!] Unicorn 错误: {e}  (已执行 {STOP['count']:,} 条)")

    print(f"执行指令数: {STOP['count']:,}  OEP 命中: {STOP['hit_oep']}")

    if STOP["hit_oep"]:
        # dump 内存映像
        mem = mu.mem_read(BASE, MEM_END - BASE)
        out = r"F:/Games/Taikou 2/scripts/_unpacked_mem.bin"
        with open(out, "wb") as f:
            f.write(bytes(mem))
        print(f"已 dump 内存映像 -> {out}  ({len(mem):,} B)")
        # 简易验证: OEP 处反汇编 + 字符串统计
        md = Cs(CS_ARCH_X86, CS_MODE_32)
        # OEP 处取 32 字节反汇编
        opcodes = bytes(mu.mem_read(OEP, 32))
        print(f"\nOEP ({OEP:#x}) 反汇编前几条:")
        for ins in md.disasm(opcodes, OEP):
            print(f"  {ins.address:#010x}  {ins.mnemonic} {ins.op_str}")
            if ins.address - OEP > 24:
                break
        # 字符串统计: 整个 dump 里 ASCII>=4 的数量
        ascii_runs = 0
        ascii_bytes = 0
        i = 0
        run = 0
        while i < len(mem):
            c = mem[i]
            if 0x20 <= c <= 0x7E:
                run += 1
            else:
                if run >= 4:
                    ascii_runs += 1
                    ascii_bytes += run
                run = 0
            i += 1
        if run >= 4:
            ascii_runs += 1; ascii_bytes += run
        # 熵: OEP 附近 64KB
        chunk = bytes(mu.mem_read(OEP, 65536))
        cnt = Counter(chunk)
        ent = -sum((v/len(chunk))*math.log2(v/len(chunk)) for v in cnt.values())
        print(f"\n验证: 全 dump ASCII 串(>=4)={ascii_runs:,}  字节={ascii_bytes:,}")
        print(f"      OEP 后 64KB 熵={ent:.3f} (>6 说明仍是代码/已解压)")
    else:
        print("[!] 未命中 OEP, 脱壳未完成 (检查 hook / 映射)")

if __name__ == "__main__":
    main()
