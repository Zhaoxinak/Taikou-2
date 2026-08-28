from capstone import Cs, CS_ARCH_X86, CS_MODE_32
mem=open("_unpacked_mem.bin","rb").read(); base=0x400000
md=Cs(CS_ARCH_X86, CS_MODE_32)

funcs=[0x47dae0,0x47dce0,0x47e130,0x47e3a0,0x47e440,0x47e5a0,0x47e770,0x47ea80,
       0x47ebb0,0x47ecb0,0x47ed10,0x47ed70,0x47ee50,0x47ef00,0x47f050,0x47f0a0,0x47f1b0]

# disassemble each function body until a ret (top-level), collect calls to read fns
def disasm_fn(start, maxlen=0x500):
    code=mem[start-base:start-base+maxlen]
    calls=[]; looplevel=0; loopcounters=[]
    cur_ecx=None
    for ins in md.disasm(code,start):
        if ins.mnemonic=='ret': break
        if ins.mnemonic=='mov' and 'ecx' in ins.op_str and ',' in ins.op_str:
            parts=[p.strip() for p in ins.op_str.split(',')]
            if parts[0]=='ecx' and parts[1].startswith('0x'):
                try: cur_ecx=int(parts[1],16)
                except: cur_ecx=None
        if ins.mnemonic=='call':
            t=ins.op_str
            if t in ('0x47da10','0x47da50','0x47da80','0x47dac0','0x4411b0','0x4eb5c0'):
                calls.append((ins.address,t,cur_ecx))
    return calls

for f in funcs:
    calls=disasm_fn(f)
    c1=sum(1 for a,t,c in calls if t=='0x47da10')   # read 1B
    c2=sum(1 for a,t,c in calls if t=='0x47da50')   # read 2B
    cw=sum(1 for a,t,c in calls if t=='0x47da80')   # write 1B
    cww=sum(1 for a,t,c in calls if t=='0x47dac0')   # write 2B
    # detect loops: calls with non-trivial ecx counter
    loopcalls=[(hex(a),t,hex(c) if c else c) for a,t,c in calls if c and c>1]
    print("0x%05x  read1B=%2d read2B=%2d write1B=%2d write2B=%2d  looped-calls=%s"%(f,c1,c2,cw,cww,loopcalls[:8]))
