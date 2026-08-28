from capstone import Cs, CS_ARCH_X86, CS_MODE_32
mem=open("_unpacked_mem.bin","rb").read(); base=0x400000
md=Cs(CS_ARCH_X86, CS_MODE_32)

funcs=[0x47dae0,0x47dce0,0x47e130,0x47e3a0,0x47e440,0x47e5a0,0x47e770,0x47ea80,
       0x47ebb0,0x47ecb0,0x47ed10,0x47ed70,0x47ee50,0x47ef00,0x47f050,0x47f0a0,0x47f1b0]

READERS={'0x47da10':'r1B','0x47da50':'r2B','0x47da80':'w1B','0x47dac0':'w2B'}
def disasm_fn(start, maxlen=0x480):
    code=mem[start-base:start-base+maxlen]
    out=[]
    for ins in md.disasm(code,start):
        out.append(ins)
    return out

for f in funcs:
    insns=disasm_fn(f)
    r1=r2=w1=w2=0
    loops=[]
    # find loop counters: mov ecx, imm  (where imm in interesting set) preceding a call to reader inside jne loop
    for i,ins in enumerate(insns):
        if ins.mnemonic=='call' and ins.op_str in READERS:
            if READERS[ins.op_str]=='r1B': r1+=1
            elif READERS[ins.op_str]=='r2B': r2+=1
            elif READERS[ins.op_str]=='w1B': w1+=1
            elif READERS[ins.op_str]=='w2B': w2+=1
        # detect loop counter assignments
        if ins.mnemonic=='mov' and 'ecx' in ins.op_str:
            parts=[p.strip() for p in ins.op_str.split(',')]
            if len(parts)==2 and parts[0]=='ecx' and parts[1].startswith('0x'):
                try: v=int(parts[1],16)
                except: v=-1
                if v in (0x5c,0x2bc,0x5a,0xb4,0x10,0x2c,0x60,0x5b,0x58,0x54,0x48):
                    # check if a reader call appears within next ~30 insns
                    window=insns[i+1:i+30]
                    hasloop=any(x.mnemonic=='call' and x.op_str in READERS for x in window)
                    loops.append((hex(ins.address),'ecx=%d'%v,'reader_in_loop' if hasloop else '-'))
    print("0x%05x | r1B=%2d r2B=%2d w1B=%2d w2B=%2d | loops:%s"%(f,r1,r2,w1,w2,loops[:6]))
