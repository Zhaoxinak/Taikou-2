#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
emu_sndata_read.py -- 用 Unicorn 真实跑通 SNDATA 记录读取 I/O 回调（续194：emu 读管线落地）
=====================================================================================
方法：把游戏的三个文件回调指针重定向到自己的桩，用 UC_HOOK_CODE 在桩入口拦截，直接用
      内存里的 SNDATA1.TR2 喂数据。这样 read_record(0x47d890) 及其扇出 0x47fc60 能在 emu 里
      真实执行，验证 I/O 桩机制 + 抓 833 条记录的运行时读出。

调用约定（来自 _lindis 反汇编，关键突破 —— 续194 纠错）：
  [0x4fb0a8] = lseek(handle,offset,whence)  : 3-arg stdcall, ret 12
  [0x4fb0a0] = read(handle,dst,count)       : 3-arg stdcall, ret 12（0x441170 内 `ret 0` 只是
                                             它自己不清理，真正 read 必须 ret 12 才平衡栈）
  [0x4fb09c] = flush/close(handle)         : 1-arg stdcall, ret 4
  0x47d890 (read_record): ecx=file_struct(this), [esp+4]=idx, [esp+8]=dst(buffer)；
              offset=idx*49+0x10；lseek；read 49 字节到 dst；pop esi; ret 8。
              → 之前续176 的崩溃根因是 lseek 桩用 ret 语义(留 12 字节在栈)，导致 0x47d890
                读 dst 的 [esp+0xc] 槽错位；改 lseek 桩为 ret 12 后 dst 正确落到 +8，整链平衡。
  0x47fc60 (fan-out): sub esp,0xd4；0x47d720 开文件；取 idx([esp+0xd8]=E_f+4)；
              lea eax,[esp]=local buffer；push eax;push idx;call 0x47d890；
              再 0x47d850(flush)；最后把缓冲头字写到 *out0/*out1/*out2，并对缓冲做 3 次 strcpy
              到 0x522c88(43B,off0) / 0x522c60(30B,off13) / 0x522c70(17B,off26)。

验证：
  A) 直接驱动 0x47d890 读全部 833 条：emu 读出 49 字节 == 静态解析逐字节。
  B) 驱动 0x47fc60 扇出（idx 抽样）：*out0/1/2 == rec[0:2]/[2:4]/[4:6]，且
     0x522c88/0x522c60/0x522c70 == rec[6:49]/[19:49]/[32:49]。
"""
import os, struct
from unicorn import Uc, UC_ARCH_X86, UC_MODE_32, UC_HOOK_CODE
from unicorn.x86_const import UC_X86_REG_EAX, UC_X86_REG_ECX, UC_X86_REG_ESI, UC_X86_REG_ESP, UC_X86_REG_EIP

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BIN  = os.path.join(ROOT, "scripts/_unpacked_mem.bin")
SND_PATH = os.path.join(ROOT, "Taikou2 Original/SNDATA1.TR2")
BASE = 0x400000

class Emu:
    def __init__(self, stack_top=0x600000, stack_size=0x40000, stop_page=0x700000):
        self.mu = Uc(UC_ARCH_X86, UC_MODE_32)
        with open(BIN, "rb") as f:
            self.code = f.read()
        self.mu.mem_map(BASE, len(self.code))
        self.mu.mem_write(BASE, self.code)
        self.STACK_TOP = stack_top
        self.mu.mem_map(stack_top, stack_size)
        self.STOP = stop_page
        self.mu.mem_map(stop_page, 0x1000)
        self.mu.mem_write(stop_page, b"\x90\x90\x90\x90")
        self.last = [0]
        self.mu.hook_add(UC_HOOK_CODE, lambda mu,a,s,u: self.last.__setitem__(0,a))
    def _stop(self, mu, address, size, ud):
        if address == self.STOP: mu.emu_stop()
    def mem_map(self, addr, size):
        try: self.mu.mem_map(addr, size)
        except Exception: pass
    def write(self, addr, data): self.mu.mem_write(addr, data)
    def read(self, addr, size): return bytes(self.mu.mem_read(addr, size))
    def alloc(self, size, at=None):
        if at is None:
            at = getattr(self, "_ap", 0x800000)
            self._ap = at + ((size + 0xfff) & ~0xfff) + 0x1000
        at &= ~0xfff
        self.mem_map(at, max((size + 0xfff) & ~0xfff, 0x1000))
        return at
    def call(self, va, args=(), regs=None, arg_off=4, max_steps=0x200000):
        regs = regs or {}
        esp = self.STACK_TOP + 0x40000 - 0x2000
        self.write(esp, struct.pack("<I", self.STOP))
        for i, a in enumerate(args):
            self.write(esp + arg_off + i * 4, struct.pack("<I", a & 0xffffffff))
        self.mu.reg_write(UC_X86_REG_ESP, esp)
        self.mu.reg_write(UC_X86_REG_EIP, va)
        for r, v in regs.items():
            self.mu.reg_write(r, v & 0xffffffff)
        h = self.mu.hook_add(UC_HOOK_CODE, self._stop)
        try:
            self.mu.emu_start(va, self.STOP + 1, count=max_steps)
        except Exception as e:
            print(f"** EMU CRASH @ call 0x{va:06x}: last_eip=0x{self.last[0]:06x} : {e}")
            raise
        finally:
            self.mu.hook_del(h)

def main():
    SND = open(SND_PATH, "rb").read()
    assert len(SND) >= 16 + 833 * 49, f"SNDATA 长度异常: {len(SND)}"
    e = Emu()
    BUF = e.alloc(len(SND)); e.write(BUF, SND)
    STUB_LSEEK, STUB_READ, STUB_FLUSH = 0x900000, 0x900010, 0x900020
    e.mem_map(0x900000, 0x1000); e.write(0x900000, b"\xc3" * 0x1000)
    e.write(0x4fb0a8, struct.pack("<I", STUB_LSEEK))
    e.write(0x4fb0a0, struct.pack("<I", STUB_READ))
    e.write(0x4fb09c, struct.pack("<I", STUB_FLUSH))

    FS = e.alloc(16); e.write(FS, b"\x00" * 16)
    MYDST = e.alloc(64)
    BUF_BASE = 0x63df2c   # 0x47fc60 局部缓冲基址（probe 确认 lea eax,[esp]=0x63df2c）
    pos = [0]; copies = []
    def on_code(mu, address, size, ud):
        sp = mu.reg_read(UC_X86_REG_ESP)
        if address == STUB_LSEEK:
            off = struct.unpack("<I", mu.mem_read(sp + 8, 4))[0]; pos[0] = off
            ret = struct.unpack("<I", mu.mem_read(sp, 4))[0]
            mu.reg_write(UC_X86_REG_EAX, off & 0xffffffff)
            mu.reg_write(UC_X86_REG_ESP, sp + 16)   # 3-arg stdcall ret 12
            mu.reg_write(UC_X86_REG_EIP, ret)
        elif address == STUB_READ:
            dst = struct.unpack("<I", mu.mem_read(sp + 8, 4))[0]
            cnt = struct.unpack("<I", mu.mem_read(sp + 0xc, 4))[0]
            n = min(cnt, len(SND) - pos[0])
            if n < 0: n = 0
            mu.mem_write(dst, SND[pos[0]:pos[0] + n]); pos[0] += n
            ret = struct.unpack("<I", mu.mem_read(sp, 4))[0]
            mu.reg_write(UC_X86_REG_EAX, n & 0xffffffff)
            mu.reg_write(UC_X86_REG_ESP, sp + 16)   # 3-arg stdcall ret 12
            mu.reg_write(UC_X86_REG_EIP, ret)
        elif address == STUB_FLUSH:
            ret = struct.unpack("<I", mu.mem_read(sp, 4))[0]
            mu.reg_write(UC_X86_REG_EAX, 0)
            mu.reg_write(UC_X86_REG_ESP, sp + 8)    # 1-arg stdcall ret 4
            mu.reg_write(UC_X86_REG_EIP, ret)
        elif address == 0x47d720:
            ret = struct.unpack("<I", mu.mem_read(sp, 4))[0]
            mu.reg_write(UC_X86_REG_EAX, 1)
            mu.reg_write(UC_X86_REG_ESP, sp + 12)   # 2-arg stdcall ret 8
            mu.reg_write(UC_X86_REG_EIP, ret)
        elif address == 0x4ebfe0:   # strcpy(dst=[esp+4], src=[esp+8])：仅记录实参，让真函数执行
            d = struct.unpack("<I", mu.mem_read(sp + 4, 4))[0]
            s = struct.unpack("<I", mu.mem_read(sp + 8, 4))[0]
            copies.append((d, s))
    e.mu.hook_add(UC_HOOK_CODE, on_code)

    # ---------- Test A: 直接驱动 0x47d890 读全部 833 条 ----------
    print("=== Test A: 0x47d890 直接读 833 条 vs 静态（dst 走 args[1]=MYDST）===")
    afail = 0
    for idx in range(833):
        e.write(MYDST, b"\x00" * 49); pos[0] = 0
        e.call(0x47d890, args=[idx, MYDST], regs={UC_X86_REG_ECX: FS})
        got = e.read(MYDST, 49); exp = SND[16 + idx * 49: 16 + idx * 49 + 49]
        if got != exp:
            afail += 1
            if afail <= 3:
                print(f"  FAIL idx={idx}: emu={got.hex()} stat={exp.hex()}")
    print(f"  Test A: {833-afail}/833 PASS" + (" ✅" if afail==0 else " ❌"))

    # ---------- Test B: 驱动 0x47fc60 扇出（idx 抽样）----------
    # 关键：0x522c88/0x522c60/0x522c70 三段目标缓冲彼此重叠（0x522c88 落在 0x522c60 区间内），
    # 故 3 次 strcpy 的最终状态是「重叠写入链」的结果（游戏本身如此）。验证须按运行时抓到的
    # (dst,src) 顺序，把缓冲(rec)对应段（遇 null 截断）依次「重叠」拷进影子区，再与 emu 全局区比对。
    REGION_BASE = 0x522c60
    REGION_LEN  = (0x522c88 + 43) - 0x522c60   # 覆盖三段目标
    FANOUT_DSTS = {0x522c88, 0x522c60, 0x522c70}

    def shadow_simulate(copies, buf):
        sh = bytearray(REGION_LEN)
        for d, s in copies:
            if d not in FANOUT_DSTS:
                continue
            soff = s - BUF_BASE
            if soff < 0 or soff >= 49:
                continue
            # 以 null 结尾的拷贝长度（含 null）
            k = buf[soff:].find(0)
            n = (49 - soff) if k < 0 else (k + 1)
            doff = d - REGION_BASE
            for i in range(n):
                if doff + i < REGION_LEN and soff + i < 49:
                    sh[doff + i] = buf[soff + i]
        return sh

    print("=== Test B: 0x47fc60 扇出抽样 vs 静态（重叠 strcpy 链影子模拟）===")
    IDW, SUBW, FL = e.alloc(8), e.alloc(8), e.alloc(8)
    bfail = 0; checked = 0
    for idx in (0, 1, 2, 3, 100, 400, 832):
        e.write(IDW, b"\x00"*8); e.write(SUBW, b"\x00"*8); e.write(FL, b"\x00"*8)
        e.write(0x522c88, b"\x00" * 64); e.write(0x522c60, b"\x00" * 48); e.write(0x522c70, b"\x00" * 32)
        e.write(0x63d000, b"\x00" * 0x1000)
        pos[0] = 0; copies.clear()
        e.call(0x47fc60, args=[idx, IDW, SUBW, FL])
        idw = struct.unpack_from("<H", e.read(IDW, 2), 0)[0]
        subw = struct.unpack_from("<H", e.read(SUBW, 2), 0)[0]
        fl = struct.unpack_from("<H", e.read(FL, 2), 0)[0]
        buf = e.read(BUF_BASE, 49)
        rec = SND[16 + idx * 49: 16 + idx * 49 + 49]
        eidw, esubw, efl = struct.unpack_from("<HHH", rec, 0)
        sh = shadow_simulate(copies, buf)
        emu_region = e.read(REGION_BASE, REGION_LEN)
        ok_buf = (buf == rec)
        ok_hdr = (idw==eidw and subw==esubw and fl==efl)
        ok_cp = (bytes(sh) == emu_region)
        ok = ok_buf and ok_hdr and ok_cp
        checked += 1; bfail += 0 if ok else 1
        print(f"  idx={idx}: idw=0x{idw:04x} subw=0x{subw:04x} flag=0x{fl:04x}  "
              f"buf={ok_buf} hdr={ok_hdr} overlap_copy={ok_cp}  {'OK' if ok else 'FAIL'}")
        if not ok:
            if not ok_buf: print(f"    buf emu={buf.hex()} stat={rec.hex()}")
            if not ok_cp:
                for o in range(REGION_LEN):
                    if sh[o] != emu_region[o]:
                        print(f"    diff@{REGION_BASE+o:#x}: shadow={sh[o]:02x} emu={emu_region[o]:02x} (ctx={emu_region[max(0,o-4):o+4].hex()})")
                        break
    print(f"  Test B: {checked-bfail}/{checked} PASS" + (" ✅" if bfail==0 else " ❌"))

    print("\nRESULT:", "ALL PASS ✅" if (afail==0 and bfail==0) else "FAIL ❌")

if __name__ == "__main__":
    main()
