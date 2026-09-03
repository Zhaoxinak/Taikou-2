# 续242 recon3: all accesses to byte[[0x52063c]+7] with proximity to the pointer load
import os
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

MEM = open(os.path.join(_ROOT, 'scripts', '_unpacked_mem.bin'), 'rb').read()
BASE = 0x400000
md = Cs(CS_ARCH_X86, CS_MODE_32)
md.skipdata = True

ins_list = []
for ins in md.disasm(MEM, BASE):
    ins_list.append(ins)

# map: address of +7 access preceded (within 0x30 bytes) by load/store of [0x52063c]
ptr_addrs = [i.address for i in ins_list if '0x52063c' in (i.op_str or '') and i.bytes.hex().endswith('3c065200')]
ptr_set = set(ptr_addrs)

out = []
for idx, ins in enumerate(ins_list):
    op = ins.op_str or ''
    if ins.mnemonic in ('mov', 'movzx', 'cmp', 'test', 'add', 'sub') and 'byte ptr [' in op:
        # forms: [ecx + 7], [eax + 7], [reg + 7]
        if op.split('[')[1].split(']')[0].strip() in ('ecx + 7', 'eax + 7', 'edx + 7', 'esi + 7', 'edi + 7', 'ebx + 7', 'ebp + 7'):
            # look back for pointer load within 0x40 bytes
            near = any(0 <= ins.address - a <= 0x40 for a in ptr_addrs)
            if near:
                out.append((ins.address, ins.mnemonic, op))

print(f"+7 accesses near [0x52063c] load: {len(out)}")
prev_func = None
for a, m, o in out:
    print(f"0x{a:06x}  {m:<6s} {o}")
