import sys,os,struct
ROOT=os.path.dirname(os.path.abspath(__file__)); BASE=0x400000
data=open(os.path.join(ROOT,"_unpacked_mem.bin"),"rb").read()
def xrefs(target):
    out={"direct_call":[],"direct_jmp":[],"ptr_literal":[]}
    for i in range(len(data)-5):
        b=data[i]
        if b in (0xe8,0xe9):
            rel=struct.unpack_from("<i",data,i+1)[0]
            if BASE+i+5+rel==target:
                out["direct_call" if b==0xe8 else "direct_jmp"].append(BASE+i)
    tb=struct.pack("<I",target)
    s=0
    while True:
        j=data.find(tb,s)
        if j<0: break
        out["ptr_literal"].append(BASE+j); s=j+1
    return out
for t in (0x40c4d0,0x40a620,0x40ad60,0x40c350,0x40a4f0,0x40ad10):
    r=xrefs(t)
    print(f"target 0x{t:x}: call={[hex(x) for x in r['direct_call']]} jmp={[hex(x) for x in r['direct_jmp']]} ptr={[hex(x) for x in r['ptr_literal']]}")
