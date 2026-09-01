#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
sndata_payload_consumer_ref.py -- 续205：P0 49B payload「哪些字节被谁读」运行时映射
========================================================================================
复用 emu_sndata_read.py 已验证可驱动 0x47fc60 的 I/O 桩 + on_code 管线（Test B 实跑通过），
仅追加：
  - UC_HOOK_MEM_READ 钩住 4 个 payload 缓冲（局部 0x63df2c / 0x522c88 / 0x522c60 / 0x522c70），
    把任一读地址映射回 rec 偏移，按记录 type(rec[0]) 聚合。
  - 对 idx 0..832 各驱动一次 0x47fc60(idx, IDW, SUBW, FL)，汇总 type→{rec_offset:read_count}。

type = rec[0]&0xff。
输出：scripts/sndata_payload_consumer.json
"""
import os, struct, json
from unicorn import Uc, UC_ARCH_X86, UC_MODE_32, UC_HOOK_CODE, UC_HOOK_MEM_READ
from unicorn.x86_const import (UC_X86_REG_ESP, UC_X86_REG_EIP, UC_X86_REG_EAX)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BIN  = os.path.join(ROOT, "scripts/_unpacked_mem.bin")
SND_PATH = os.path.join(ROOT, "Taikou2 Original/SNDATA1.TR2")
BASE = 0x400000

# payload 缓冲：(base_va, length, rec_base_offset)
BUFS = [
    (0x63df2c, 49, 0),
    (0x522c88, 43, 6),
    (0x522c60, 30, 19),
    (0x522c70, 17, 32),
]
def buf_for(va):
    for b, n, rb in BUFS:
        if b <= va < b + n:
            return rb + (va - b)
    return None

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
    assert len(SND) >= 16 + 833*49, f"SNDATA 长度异常: {len(SND)}"
    e = Emu()
    BUF = e.alloc(len(SND)); e.write(BUF, SND)
    # 复用 emu_sndata_read 的桩布局（STUB 同址）
    STUB_LSEEK, STUB_READ, STUB_FLUSH = 0x900000, 0x900010, 0x900020
    e.mem_map(0x900000, 0x1000); e.write(0x900000, b"\xc3" * 0x1000)
    e.write(0x4fb0a8, struct.pack("<I", STUB_LSEEK))
    e.write(0x4fb0a0, struct.pack("<I", STUB_READ))
    e.write(0x4fb09c, struct.pack("<I", STUB_FLUSH))

    FS = e.alloc(16); e.write(FS, b"\x00" * 16)
    MYDST = e.alloc(64)
    BUF_BASE = 0x63df2c
    pos = [0]; copies = []
    def on_code(mu, address, size, ud):
        sp = mu.reg_read(UC_X86_REG_ESP)
        if address == STUB_LSEEK:
            off = struct.unpack("<I", mu.mem_read(sp + 8, 4))[0]; pos[0] = off
            ret = struct.unpack("<I", mu.mem_read(sp, 4))[0]
            mu.reg_write(UC_X86_REG_EAX, off & 0xffffffff)
            mu.reg_write(UC_X86_REG_ESP, sp + 16)
            mu.reg_write(UC_X86_REG_EIP, ret)
        elif address == STUB_READ:
            dst = struct.unpack("<I", mu.mem_read(sp + 8, 4))[0]
            cnt = struct.unpack("<I", mu.mem_read(sp + 0xc, 4))[0]
            n = min(cnt, len(SND) - pos[0]); n = max(0, n)
            mu.mem_write(dst, SND[pos[0]:pos[0] + n]); pos[0] += n
            ret = struct.unpack("<I", mu.mem_read(sp, 4))[0]
            mu.reg_write(UC_X86_REG_EAX, n & 0xffffffff)
            mu.reg_write(UC_X86_REG_ESP, sp + 16)
            mu.reg_write(UC_X86_REG_EIP, ret)
        elif address == STUB_FLUSH:
            ret = struct.unpack("<I", mu.mem_read(sp, 4))[0]
            mu.reg_write(UC_X86_REG_EAX, 0)
            mu.reg_write(UC_X86_REG_ESP, sp + 8)
            mu.reg_write(UC_X86_REG_EIP, ret)
        elif address == 0x47d720:
            ret = struct.unpack("<I", mu.mem_read(sp, 4))[0]
            mu.reg_write(UC_X86_REG_EAX, 1)
            mu.reg_write(UC_X86_REG_ESP, sp + 8)
            mu.reg_write(UC_X86_REG_EIP, ret)
        elif address == 0x4ebfe0:
            d = struct.unpack("<I", mu.mem_read(sp + 4, 4))[0]
            s = struct.unpack("<I", mu.mem_read(sp + 8, 4))[0]
            copies.append((d, s)
        elif address == 0x47fc7b:  # 读 idx 前：dump 帧找 idx 槽
            if sum(crashes.values()) <= 8:
                probe = []
                for off in (-4, 0, 0x4, 0xd0, 0xd4, 0xd8, 0xdc, 0xe0, 0xe4):
                    probe.append(f"{off:+#x}=0x{struct.unpack('<I', mu.mem_read(sp+off,4))[0]:08x}")
                print(f"   [idx@0x47fc7b] esp=0x{sp:08x} want_idx={current_type[0]} " + " ".join(probe))
    e.mu.hook_add(UC_HOOK_CODE, on_code)

    # ---- consumer MEM_READ 钩 ----
    reads = {}
    crashes = {}
    current_type = [0]
    def on_mem(mu, access, address, size, value, ud):
        ro = buf_for(address)
        if ro is None: return
        t = current_type[0]
        d = reads.setdefault(t, {})
        d[ro] = d.get(ro, 0) + 1
    hm = e.mu.hook_add(UC_HOOK_MEM_READ, on_mem)

    IDW, SUBW, FL = e.alloc(8), e.alloc(8), e.alloc(8)
    n_done = 0
    for idx in range(833):
        rec = SND[16 + idx*49: 16 + idx*49 + 49]
        t = rec[0] & 0xff
        current_type[0] = t
        e.write(IDW, b"\x00"*8); e.write(SUBW, b"\x00"*8); e.write(FL, b"\x00"*8)
        e.write(0x522c88, b"\x00"*64); e.write(0x522c60, b"\x00"*48); e.write(0x522c70, b"\x00"*32)
        e.write(0x63d000, b"\x00"*0x1000)
        pos[0] = 0; copies.clear()
        try:
            e.call(0x47fc60, args=[idx, IDW, SUBW, FL])
            n_done += 1
        except Exception as ex:
            crashes[t] = crashes.get(t, 0) + 1
            if len(crashes) <= 5 and sum(crashes.values()) <= 5:
                print(f"  ** crash idx={idx} type=0x{t:02x} last=0x{e.last[0]:06x}: {ex}")
    e.mu.hook_del(hm)

    # 校验：抽样比对 idw/subw/fl 与静态
    okchk = 0; bad = 0
    samp = [0,1,2,3,100,400,832]
    for idx in samp:
        if idx in (None,): continue
        rec = SND[16+idx*49:16+idx*49+49]
        eidw, esubw, efl = struct.unpack_from("<HHH", rec, 0)
        idw = struct.unpack_from("<H", e.read(IDW,2),0)[0]
        subw = struct.unpack_from("<H", e.read(SUBW,2),0)[0]
        fl = struct.unpack_from("<H", e.read(FL,2),0)[0]
        if (idw,subw,fl)==(eidw,esubw,efl): okchk += 1
        else:
            bad += 1
            print(f"  [chk] idx={idx}: emu=({idw:04x},{subw:04x},{fl:04x}) stat=({eidw:04x},{esubw:04x},{efl:04x})")

    summary = {}
    for t, d in reads.items():
        offsets = sorted(d.keys())
        summary[f"0x{t:02x}"] = {
            "types_read_bytes": len(offsets),
            "read_offsets": offsets,
            "read_count": {str(o): d[o] for o in offsets},
        }
    out = {
        "total_types": len(summary),
        "records_processed_no_crash": n_done,
        "crash_by_type": crashes,
        "header_check": {"sampled": len(samp), "ok": okchk, "bad": bad},
        "by_type": summary,
    }
    with open(os.path.join(ROOT, "scripts/sndata_payload_consumer.json"), "w") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    print(f"type 数={len(summary)}  无崩溃记录={n_done}/833  崩溃type数={len(crashes)}  头部校验 ok/bad={okchk}/{bad}")
    top = sorted(summary.items(), key=lambda kv: -kv[1]["types_read_bytes"])[:15]
    for k, v in top:
        print(f"  {k}: 读 {v['types_read_bytes']} 字节 offsets={v['read_offsets'][:24]}")
    print("产物: scripts/sndata_payload_consumer.json")

if __name__ == "__main__":
    main()
