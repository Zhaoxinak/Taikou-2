# -*- coding: utf8 -*-
"""dis_exe.py —— 直接从一个 exe 映像反汇编 VA 区间 (自动做 RVA->文件偏移)
用法: python dis_exe.py <exe> <start_va> <end_va> [--bytes N]
"""
import sys, struct, capstone


def sections(data):
    pe = struct.unpack_from('<I', data, 0x3C)[0]
    nsec = struct.unpack_from('<H', data, pe + 6)[0]
    opt = pe + 24
    sizeopt = struct.unpack_from('<H', data, pe + 20)[0]
    sect = opt + sizeopt
    out = []
    for i in range(nsec):
        o = sect + i * 40
        name = data[o:o + 8].rstrip(b'\0').decode('latin1')
        vsize, vaddr, rsize, raddr = struct.unpack_from('<IIII', data, o + 8)
        out.append((name, vaddr, vsize, raddr, rsize))
    return out


def main():
    exe = sys.argv[1]
    s = int(sys.argv[2], 16)
    e = int(sys.argv[3], 16)
    data = open(exe, 'rb').read()
    secs = sections(data)
    ib = struct.unpack_from('<I', data, struct.unpack_from('<I', data, 0x3C)[0] + 24 + 28)[0]

    def rva2off(rva):
        for name, vaddr, vsize, raddr, rsize in secs:
            if vaddr <= rva < vaddr + max(vsize, rsize):
                return raddr + (rva - vaddr)
        return None

    off = rva2off(s - ib)
    n = e - s
    md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)
    md.detail = True
    print('# imagebase=0x%X  file_off=0x%X  len=%d' % (ib, off, n))
    print('# raw: ' + data[off:off + n].hex())
    for ins in md.disasm(data[off:off + n], s):
        print('  %08X  %-22s %s %s' % (ins.address, ins.bytes.hex(), ins.mnemonic, ins.op_str))


if __name__ == '__main__':
    main()
