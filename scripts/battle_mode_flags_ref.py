# -*- coding: utf-8 -*-
"""
battle_mode_flags_ref.py  —  合战全局模式标志 setter/getter 几何 + 值语义自测
================================================================================
承接清单 P1「模式标志玩法含义（mode_m1/m2/parity/battle_type/handle_stat，
5 全局标志已定位 BATTLE_SPEC §9.9）→ emu 观察置位时机」。

本脚本用 Unicorn 2.1.4 实跑 5 个全局标志的 setter，验证：
  (A) 每个 setter 把值写到正确的全局地址（setter→全局 几何）；
  (B) 值语义：
        mode_m1      = 写入 arg0（dword，典型 0/1 布尔）
        mode_m2_a    = 写入 arg0（dword，典型 0/1 布尔）
        mode_m2_b    = 在随机条件下「翻转」0x51352c 的 bit0（xor [addr],1）
        parity_a     = min(arg0, X)，X = 0x43ca30() 返回的阈值
        parity_b     = 若 cur < X 则 cur+1，否则不变（X = 0x43ca30()）
        battle_type  = 写入 arg0（byte，典型 0 / 3 / 变量）
        handle_stat  = 写入 arg0（dword，变量）
  (C) 静态断言：3 个有 getter 的标志（mode_m1/mode_m2/parity）的 getter 读取
      地址与 setter 写入地址一致（round-trip 闭合）。

外部依赖（0x43ca30 / 0x43cad0 / 0x4ebd60）用定点 hook 强制返回值，使
「clamp / toggle」分支可达并被断言。

运行：从本文件所在目录（scripts/）执行：
    python battle_mode_flags_ref.py
"""
import os, struct
from unicorn import Uc, UC_ARCH_X86, UC_MODE_32, UC_HOOK_CODE
from unicorn.x86_const import UC_X86_REG_ESP, UC_X86_REG_EIP, UC_X86_REG_EAX

HERE = os.path.dirname(os.path.abspath(__file__))
BIN = os.path.join(HERE, "_unpacked_mem.bin")
BASE = 0x400000
code = open(BIN, "rb").read()

# setter VA -> (flag_addr, width, label)
SETTERS = {
    0x42c140: (0x511bf8, 4, "mode_m1"),
    0x43cb20: (0x51352c, 4, "mode_m2_a"),
    0x43cfc0: (0x51352c, 4, "mode_m2_b(toggle)"),
    0x43ca70: (0x513540, 1, "parity_a"),
    0x43ca90: (0x513540, 1, "parity_b"),
    0x43ca20: (0x513548, 1, "battle_type"),
    0x43cb70: (0x513534, 4, "handle_stat"),
}
# getter VA -> flag_addr（静态断言用）
GETTERS = {
    0x42c151: 0x511bf8,   # mode_m1 getter
    0x43cb11: 0x51352c,   # mode_m2 getter
    0x43cab1: 0x513540,   # parity getter
}

class Emu:
    def __init__(self, force=None):
        self.mu = Uc(UC_ARCH_X86, UC_MODE_32)
        self.mu.mem_map(BASE, 0x200000)
        self.mu.mem_write(BASE, code)
        self.mu.mem_map(0x800000, 0x10000)
        self.mu.mem_map(0x900000, 0x1000)
        self.RET = 0x900000
        self.force = force or {}
        self.mu.hook_add(UC_HOOK_CODE, self._hook)

    def _hook(self, mu, ad, sz, ud):
        if ad == self.RET:
            mu.emu_stop()
            return
        if ad in self.force:
            esp = mu.reg_read(UC_X86_REG_ESP)
            ret = struct.unpack_from("<I", mu.mem_read(esp, 4))[0]
            mu.reg_write(UC_X86_REG_EAX, self.force[ad] & 0xffffffff)
            mu.reg_write(UC_X86_REG_ESP, esp + 4)
            mu.reg_write(UC_X86_REG_EIP, ret)

    def call(self, func, arg=0, pre_set=None):
        for a, v in (pre_set or {}).items():
            w = 1 if v <= 0xff else 4
            self.mu.mem_write(a, struct.pack("<I", v & 0xffffffff)[:w])
        ESP = 0x808000
        self.mu.mem_write(ESP, struct.pack("<II", self.RET, arg & 0xffffffff))
        self.mu.reg_write(UC_X86_REG_ESP, ESP)
        self.mu.reg_write(UC_X86_REG_EIP, func)
        self.mu.emu_start(func, func + 0x300)
        fa, w, _ = SETTERS[func]
        raw = self.mu.mem_read(fa, 4)
        return raw[0] if w == 1 else struct.unpack_from("<I", bytes(raw))[0]


def lit_scan(addr):
    lit = struct.pack("<I", addr)
    hits = []
    s = 0
    while True:
        i = code.find(lit, s)
        if i < 0:
            break
        hits.append(i + BASE)
        s = i + 1
    return hits


def main():
    results = []
    def check(name, got, exp):
        ok = got == exp
        results.append(ok)
        print(f"  [{'PASS' if ok else 'FAIL'}] {name}: got={exp.__class__.__name__ and hex(got) if isinstance(got,int) else got} exp={hex(exp) if isinstance(exp,int) else exp}")
        return ok

    # ---- (A) 简单写 arg0 的 setter ----
    print("== (A) write-arg0 setters ==")
    e = Emu()
    check("mode_m1  0x12345678", e.call(0x42c140, 0x12345678), 0x12345678)
    check("mode_m1  1          ", e.call(0x42c140, 1), 1)
    check("mode_m1  0          ", e.call(0x42c140, 0), 0)
    e = Emu()
    check("mode_m2_a 0x99      ", e.call(0x43cb20, 0x99), 0x99)
    check("mode_m2_a 1         ", e.call(0x43cb20, 1), 1)
    e = Emu()
    check("handle_stat 0xABCD  ", e.call(0x43cb70, 0xABCD), 0xABCD)
    check("handle_stat 7       ", e.call(0x43cb70, 7), 7)
    e = Emu()
    check("battle_type 3       ", e.call(0x43ca20, 3), 3)
    check("battle_type 0       ", e.call(0x43ca20, 0), 0)

    # ---- (B) parity clamp / increment (force 0x43ca30 -> 5) ----
    print("== (B) parity (force 0x43ca30->5) ==")
    e = Emu(force={0x43ca30: 5})
    check("parity_a 3 (<=5)    ", e.call(0x43ca70, 3), 3)
    check("parity_a 9 (>5->5)  ", e.call(0x43ca70, 9), 5)
    e = Emu(force={0x43ca30: 5})
    check("parity_b pre=2 ->3  ", e.call(0x43ca90, 0, pre_set={0x513540: 2}), 3)
    check("parity_b pre=5 ->5  ", e.call(0x43ca90, 0, pre_set={0x513540: 5}), 5)
    check("parity_b pre=7 ->7  ", e.call(0x43ca90, 0, pre_set={0x513540: 7}), 7)

    # ---- (B) mode_m2_b toggle (force 0x43cad0->3, 0x4ebd60->0) ----
    print("== (B) mode_m2_b toggle (force 0x43cad0->3, 0x4ebd60->0) ==")
    e = Emu(force={0x43cad0: 3, 0x4ebd60: 0})
    check("mode_m2_b pre=0 ->1  ", e.call(0x43cfc0, pre_set={0x51352c: 0}), 1)
    check("mode_m2_b pre=1 ->0  ", e.call(0x43cfc0, pre_set={0x51352c: 1}), 0)
    check("mode_m2_b pre=0x100->0x101 (bit0 flip, hi preserved)",
          e.call(0x43cfc0, pre_set={0x51352c: 0x100}), 0x101)

    # ---- (C) static: getter read-addr == setter write-addr ----
    print("== (C) getter round-trip ==")
    for gva, faddr in GETTERS.items():
        refs = lit_scan(faddr)
        # getter 函数体内应含该地址的读取引用
        in_getter = any(gva <= r <= gva + 0x20 for r in refs)
        ok = in_getter
        results.append(ok)
        print(f"  [{'PASS' if ok else 'FAIL'}] getter {gva:#08x} reads flag {faddr:#08x} (refs in getter body: {in_getter})")

    total = len(results)
    passed = sum(results)
    print(f"\n==== SUMMARY: {passed}/{total} PASS ====")
    return 0 if passed == total else 1


if __name__ == "__main__":
    import sys
    sys.exit(main())
