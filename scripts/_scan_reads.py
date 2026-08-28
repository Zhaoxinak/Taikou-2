from capstone import Cs, CS_ARCH_X86, CS_MODE_32
mem=open("_unpacked_mem.bin","rb").read(); base=0x400000
md=Cs(CS_ARCH_X86, CS_MODE_32)

START,END=0x47d960,0x47f200
lines=[]
for ins in md.disasm(mem[START-base:END-base],START):
    if ins.address>END: break
    lines.append((ins.address, ins.mnemonic, ins.op_str))

# scan for push size; push dest; call 0x4411b0 / 0x4411d0
out=[]
i=0
cur_func=None
# track function boundaries by 'ret' or call patterns; simpler: just scan triples
n=len(lines)
for i in range(n-2):
    a=lines[i]; b=lines[i+1]; c=lines[i+2]
    # pattern: push imm ; push imm/reg ; call 0x4411b0 or 0x4411d0
    if a[1]=='push' and b[1]=='push' and c[1]=='call' and c[2] in ('0x4411b0','0x4411d0'):
        sz=a[2]; dest=b[2]
        # only keep reads that look like "load N bytes into a global" (size>4 and dest is a global 0x5xxxxx or [esi+..])
        try:
            szv=int(sz,16) if sz.startswith('0x') else int(sz)
        except:
            szv=-1
        if szv>=8 or '0x5' in dest:
            out.append("%08x  READ size=%s -> %s   [%s]"%(a[0],sz,dest, 'read' if c[2]=='0x4411b0' else 'write?'))

# also catch lea ecx,[esi+..]; push size; call
open("_sndata_reads.txt","w").write("\n".join(out))
print("found %d read-like ops"%len(out))
for o in out[:80]:
    print(o)
