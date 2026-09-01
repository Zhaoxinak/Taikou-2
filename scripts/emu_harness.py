#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
emu_harness.py  --  可复用 Unicorn 2.1.4 仿真骨架（太阁立志传2 TAIK2W95 脱壳映像）
=====================================================================================
用途：在已脱壳的 2MB 映像(_unpacked_mem.bin, base 0x400000) 上，以受控参数调用任意
      **叶子/自包含函数**，捕获返回值与内存副作用。这是把静态逆向推进到「运行时验证」
      的基础设施（续192 后静态已到极限，P0 49B 字段命名 / #19 兵种名 / #89 门控 / S15 段C
      等均须 emu；本骨架是统一入口）。

能力：
  - 加载映像到 0x400000（code+data+rw）
  - call(va, args, regs={})：stdcall 调用，args 按 [esp+4],[esp+8]... 入栈，
     regs 预置寄存器（如 ecx=缓冲区基址），跑到 STOP 页自动停。
  - 返回寄存器快照 + 可随时 mu.mem_read 检查副作用。
  - 可选 hook_mem_read/write 回调（抓消费者/写者）。

坑（已处理，见 MEMORY 逆向方法论）：
  - Unicorn 2.x 用 mu.reg_read/write(UC_X86_REG_ESP) 而非 .reg_esp
  - stdcall 函数 ret N 自行平栈；本骨架用 STOP 页(until=STOP) 终止，不依赖 ret 值
  - 仅适用于叶子/自包含函数；调用 OS/未初始化内存的子函数会 UC_ERR_*
"""
import os
import struct
from unicorn import Uc, UC_ARCH_X86, UC_MODE_32, UC_HOOK_CODE, UC_HOOK_MEM_READ, UC_HOOK_MEM_WRITE
from unicorn.x86_const import UC_X86_REG_EAX, UC_X86_REG_ECX, UC_X86_REG_EDX, UC_X86_REG_EBX, UC_X86_REG_ESP, \
    UC_X86_REG_EBP, UC_X86_REG_ESI, UC_X86_REG_EDI, UC_X86_REG_EFLAGS, UC_X86_REG_EIP

BASE = 0x400000
BIN  = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_unpacked_mem.bin")

REG_NAMES = {
    UC_X86_REG_EAX:"eax", UC_X86_REG_ECX:"ecx", UC_X86_REG_EDX:"edx", UC_X86_REG_EBX:"ebx",
    UC_X86_REG_ESP:"esp", UC_X86_REG_EBP:"ebp", UC_X86_REG_ESI:"esi", UC_X86_REG_EDI:"edi",
    UC_X86_REG_EFLAGS:"eflags", UC_X86_REG_EIP:"eip",
}

class Emu:
    def __init__(self, stack_top=0x600000, stack_size=0x20000, stop_page=0x700000):
        self.mu = Uc(UC_ARCH_X86, UC_MODE_32)
        with open(BIN, "rb") as f:
            self.code = f.read()
        # 映像本体（code+data+rw）
        self.mu.mem_map(BASE, len(self.code))
        self.mu.mem_write(BASE, self.code)
        # 栈
        self.STACK_TOP = stack_top
        self.mu.mem_map(stack_top, stack_size)
        # STOP 页（函数 ret 到此即停）
        self.STOP = stop_page
        self.mu.mem_map(stop_page, 0x1000)
        self.mu.mem_write(stop_page, b"\x90\x90\x90\x90")  # nop 占位；emu_start until=STOP 终止
        self._hooks = []
        self._mem_read_log = []
        self._mem_write_log = []

    def _stop_hook(self, mu, address, size, user_data):
        if address == self.STOP:
            mu.emu_stop()

    def call(self, va, args=(), regs=None, until=None, max_steps=0x100000):
        """调用函数 va(stdcall)。args=[a1,a2,...] 入栈 [esp+4..]；regs 预置寄存器。
        返回寄存器快照 dict。"""
        regs = regs or {}
        esp = self.STACK_TOP - 0x1000  # 留余量
        stop = until if until else self.STOP
        # ret 地址 @ [esp]
        self.mu.mem_write(esp, struct.pack("<I", stop))
        # 参数
        for i, a in enumerate(args):
            self.mu.mem_write(esp + 4 + i * 4, struct.pack("<I", a & 0xffffffff))
        # 预置寄存器
        self.mu.reg_write(UC_X86_REG_ESP, esp)
        self.mu.reg_write(UC_X86_REG_EIP, va)
        for r, v in regs.items():
            self.mu.reg_write(r, v & 0xffffffff)
        # 安装 stop hook（一次性）
        h = self.mu.hook_add(UC_HOOK_CODE, self._stop_hook)
        try:
            self.mu.emu_start(va, stop + 1, count=max_steps)
        finally:
            self.mu.hook_del(h)
        return self.regs()

    def regs(self):
        return {REG_NAMES[r]: self.mu.reg_read(r)
                for r in (UC_X86_REG_EAX, UC_X86_REG_ECX, UC_X86_REG_EDX, UC_X86_REG_EBX,
                          UC_X86_REG_ESP, UC_X86_REG_EBP, UC_X86_REG_ESI, UC_X86_REG_EDI,
                          UC_X86_REG_EFLAGS, UC_X86_REG_EIP)}

    def read(self, addr, size):
        return self.mu.mem_read(addr, size)

    def write(self, addr, data):
        self.mu.mem_write(addr, data)

    def alloc(self, size, at=None):
        """分配一块可读写内存，返回基址（页对齐）。"""
        if at is None:
            at = 0x800000 + (getattr(self, "_alloc_ptr", 0))
            self._alloc_ptr = (at - 0x800000) + ((size + 0xfff) & ~0xfff) + 0x1000
        at = at & ~0xfff  # 页对齐
        self.mu.mem_map(at, max((size + 0xfff) & ~0xfff, 0x1000))
        return at

    def hook_mem(self, read_cb=None, write_cb=None):
        """注册 MEM_READ/MEM_WRITE 回调：read_cb(access,addr,size,value)。"""
        if read_cb:
            def _r(mu, access, addr, size, value, ud):
                self._mem_read_log.append((addr, size, value)); read_cb(access, addr, size, value)
            self._hooks.append(self.mu.hook_add(UC_HOOK_MEM_READ, _r))
        if write_cb:
            def _w(mu, access, addr, size, value, ud):
                self._mem_write_log.append((addr, size, value)); write_cb(access, addr, size, value)
            self._hooks.append(self.mu.hook_add(UC_HOOK_MEM_WRITE, _w))


# ---- 自测（叶子函数）----
def _selftest():
    e = Emu()
    # ① sat_sub(0x4ebcd0)=(a>b)?a-b:0
    for a, b, exp in [(5, 3, 2), (3, 5, 0), (0, 0, 0), (10, 1, 9)]:
        r = e.call(0x4ebcd0, [a, b])
        assert r["eax"] == exp, f"sat_sub({a},{b})={r['eax']} != {exp}"
    # ② set_c(0x49c500): byte[ecx+0x13+idx]=val  (段C 6B 布局验证)
    buf = e.alloc(0x40)
    e.write(buf, b"\x00" * 0x40)
    for idx in range(6):
        val = (idx * 0x11) & 0xff
        e.call(0x49c500, [idx, val], regs={UC_X86_REG_ECX: buf})
        got = e.read(buf + 0x13 + idx, 1)[0]
        assert got == val, f"set_c idx={idx}: wrote {val:02x} got {got:02x}"
    print("emu_harness selftest: sat_sub OK (4/4), set_c byte[+0x13+idx] OK (6/6) => ALL PASS ✅")

if __name__ == "__main__":
    _selftest()
