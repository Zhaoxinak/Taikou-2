# -*- coding: utf-8 -*-
"""
Emulate the per-type decoder 0x47ff68 for a given record type T, with ALL
sub-calls stubbed. Each stubbed callee is "returned" precisely by emulating its
real epilogue (ret N where N is the function's own cleanup size), so the caller's
stack stays balanced regardless of cdecl/stdcall. The memcpy/strcpy-family calls
(0x4ebfe0/0x4ec010/0x4ebe60/0x49f120/0x49f0b0/0x4ebfc0) are intercepted and their
args recorded (dst, src, len, + call-site) so we can reconstruct, per type,
which payload offset (0x522c88 / 0x522c60 / 0x522c70) is copied into which
scenario buffer (0x509xxx).

The record is NOT read from disk; we pre-fill the payload scratch
0x522c88 / 0x522c60 / 0x522c70 (a ramp of distinct bytes) and stub 0x47fc60
(the fan-out) as a no-op, so the decoder reads the payload we control. We set
[esp+0x18] = T on the decoder's frame, matching the real calling convention.
"""
import os, sys, struct
from capstone import Cs, CS_ARCH_X86, CS_MODE_32
from unicorn import Uc, UC_ARCH_X86, UC_MODE_32, UC_HOOK_CODE, UcError
import unicorn.x86_const as X

HERE = os.path.dirname(os.path.abspath(__file__))
IMG = open(os.path.join(HERE, "_unpacked_mem.bin"), "rb").read()
BASE = 0x400000
DISP = 0x47ff68

# memcpy / strcpy / itoa / classify / pad / strlen helpers we want to trace.
TRACE_TARGETS = {0x4ebfe0, 0x4ec010, 0x4ebe60, 0x49f120, 0x49f0b0, 0x4ebfc0}

# Where each traced helper reads its SRC (the pointer that may be a payload
# base). dst is always at [esp+4]; src offset varies.
SRC_OFF = {0x4ebfe0: 0x0c, 0x4ec010: 0x08, 0x4ebe60: 0x0c,
           0x49f120: 0x04, 0x49f0b0: 0x04, 0x4ebfc0: 0x04}

PAYLOAD_BASE = 0x522c88
PAYLOAD_END = 0x522c88 + 0x2b          # 43 bytes
B1 = 0x522c60                          # record[0x13]
B2 = 0x522c70                          # record[0x20]

mdh = Cs(CS_ARCH_X86, CS_MODE_32)
mdh.detail = False

def capstone_at(va):
    code = IMG[va - BASE: va - BASE + 16]
    out = list(mdh.disasm(code, va))
    return out[0] if out else None

def payload_off(src):
    if PAYLOAD_BASE <= src < PAYLOAD_END:
        return src - PAYLOAD_BASE
    if src == B1:
        return 0x13
    if src == B2:
        return 0x20
    return None

def ret_size(addr):
    """Return the cleanup size of a function's epilogue (0 for cdecl ret,
    N for stdcall ret N). Linear-scan for the first ret / ret imm16."""
    code = IMG[addr - BASE: addr - BASE + 256]
    for i in mdh.disasm(code, addr):
        if i.mnemonic == 'ret':
            if i.bytes[:1] == b'\xc2':  # ret imm16
                return int.from_bytes(i.bytes[1:3], 'little')
            return 0
    return 0

class Harness:
    def __init__(self):
        self.uc = Uc(UC_ARCH_X86, UC_MODE_32)
        self.uc.mem_map(BASE, len(IMG), 7)
        self.uc.mem_write(BASE, IMG)
        self.STACK = 0x700000
        self.uc.mem_map(self.STACK, 0x20000, 7)
        self.STOP = 0x610000
        self.uc.mem_map(self.STOP, 0x1000, 7)
        self.uc.mem_write(self.STOP, b'\xc3')  # ret (stop)
        self.trace = []
        self.pending = set()
        self.retn = {}
        self.eip_hist = []

    def _get_retn(self, addr):
        if addr not in self.retn:
            self.retn[addr] = ret_size(addr)
        return self.retn[addr]

    def run(self, T):
        uc = self.uc
        self.trace = []
        self.pending = set()
        self.eip_hist = []
        # distinct-byte ramp so each payload byte is identifiable
        payload = bytes((i * 7 + 3) & 0xff for i in range(0x2b))
        uc.mem_write(PAYLOAD_BASE, payload)
        uc.mem_write(B1, b'\xff')          # record[0x13] sentinel
        uc.mem_write(B2, b'\xfe')          # record[0x20] sentinel
        FRAME = self.STACK + 0x10000
        uc.reg_write(X.UC_X86_REG_ESP, FRAME)
        uc.mem_write(FRAME, struct.pack('<I', self.STOP))   # fake return addr
        uc.mem_write(FRAME + 0x18, struct.pack('<H', T & 0xffff))  # type
        uc.mem_write(FRAME + 0x1c, b'\x00' * 0x400)

        def hook(uc, address, size, user_data):
            self.eip_hist.append(address)
            if len(self.eip_hist) > 64:
                self.eip_hist.pop(0)
            if address == self.STOP:
                uc.emu_stop()
                return
            if address in self.pending:
                self.pending.discard(address)
                esp = uc.reg_read(X.UC_X86_REG_ESP)
                ret_addr = struct.unpack('<I', uc.mem_read(esp, 4))[0]
                a1 = struct.unpack('<I', uc.mem_read(esp + 4, 4))[0]
                a2 = struct.unpack('<I', uc.mem_read(esp + 8, 4))[0]
                a3 = struct.unpack('<I', uc.mem_read(esp + 0xc, 4))[0]
                if address in TRACE_TARGETS and address != 0x47fc60:
                    self.trace.append((hex(address), hex(ret_addr),
                                       hex(a1), hex(a2), hex(a3)))
                # emulate the callee's real return (pop ret addr + its cleanup)
                n = self._get_retn(address)
                esp_new = esp + 4 + n
                uc.reg_write(X.UC_X86_REG_ESP, esp_new)
                uc.reg_write(X.UC_X86_REG_EIP, ret_addr)
                return
            ins = capstone_at(address)
            if ins is not None and ins.mnemonic == 'call':
                op = ins.op_str.strip().lower()
                if op.startswith('0x'):
                    self.pending.add(int(op, 16))
                else:
                    reg_map = {'eax': X.UC_X86_REG_EAX, 'ecx': X.UC_X86_REG_ECX,
                               'edx': X.UC_X86_REG_EDX, 'ebx': X.UC_X86_REG_EBX,
                               'esi': X.UC_X86_REG_ESI, 'edi': X.UC_X86_REG_EDI}
                    rn = (op.replace('dword ptr ', '').replace('[', '')
                             .replace(']', '').split('+')[0].strip())
                    if rn in reg_map:
                        self.pending.add(uc.reg_read(reg_map[rn]))

        uc.hook_add(UC_HOOK_CODE, hook)
        uc.emu_start(0x47ff68, BASE + len(IMG), timeout=15_000_000)
        return self.trace


def main():
    types = [0x00, 0x01, 0x08, 0x0d, 0x3e, 0x8c]
    for T in types:
        h = Harness()
        try:
            tr = h.run(T)
        except UcError as e:
            eip = h.uc.reg_read(X.UC_X86_REG_EIP)
            esp = h.uc.reg_read(X.UC_X86_REG_ESP)
            print("type 0x%02x EMU ERROR EIP=0x%06x ESP=0x%06x: %s" % (T, eip, esp, e))
            print("  last EIPs: " + " ".join(hex(x) for x in h.eip_hist[-8:]))
            print("  trace so far (%d):" % len(h.trace))
            for (fn, ret, a1, a2, a3) in h.trace[-12:]:
                print("    %s ret=%s a1=%s a2=%s a3=%s" % (fn, ret, a1, a2, a3))
            continue
        print("\n===== TYPE 0x%02x : %d traced calls =====" % (T, len(tr)))
        for (fn, ret, a1, a2, a3) in tr[:60]:
            soff = SRC_OFF.get(int(fn, 16), 8)
            # pick the source slot that is a payload/base pointer
            src = int(a2, 16) if soff == 8 else int(a3, 16)
            po = payload_off(src)
            tag = ("payload+0x%02x" % po) if po is not None else (
                  "buf/tmp 0x%05x" % src if 0x509000 <= src < 0x520000 or 0x710000 <= src < 0x720000 else "0x%05x" % src)
            print("  %s  dst=%s  src=%s (%s)  ret=%s" % (fn, a1, hex(src), tag, ret))


if __name__ == "__main__":
    main()
