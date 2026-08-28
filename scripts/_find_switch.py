# -*- coding: utf-8 -*-
"""穷举找 switch 语句: jmp dword ptr [reg*4 + imm32] (FF 24 xx) / FF A4 (jmp [reg*4+disp32])。
输出跳表基址 + 表长(自动探测) + 所在函数。"""
import struct, sys, json
from capstone import *
BASE=0x400000
mem=open('_unpacked_mem.bin','rb').read()
md=Cs(CS_ARCH_X86,CS_MODE_32); md.detail=True
TLO,THI=0x401000,0x4f4000

# 建立 call-target 函数头集合 用于归属
targets=set()
i=0
while True:
    i=mem.find(b'\xe8',i)
    if i<0: break
    rel=struct.unpack_from('<i',mem,i+1)[0]
    t=(i+BASE)+5+rel
    if TLO<=t<THI: targets.add(t)
    i+=1
funcs=sorted(targets)
import bisect
def host(va):
    k=bisect.bisect_right(funcs,va)-1
    return funcs[k] if k>=0 else 0

res=[]
# 线性扫描 .text 找 FF 24 / FF A4
for off in range(0, min(len(mem), (0x4f4000-BASE))):
    b=mem[off]
    if b!=0xff: continue
    b1=mem[off+1] if off+1<len(mem) else 0
    if b1 in (0x24,0xa4,0x64,0xe4):   # jmp [..*4 + disp]
        modrm=b1
        # 尝试从 off 起反汇编一条
        for ins in md.disasm(mem[off:off+8], BASE+off):
            if ins.mnemonic=='jmp' and '*4' in ins.op_str and '0x' in ins.op_str:
                try:
                    tbl=int(ins.op_str.split('+')[1].strip().rstrip(']'),16)
                except Exception:
                    break
                if not (0x4f0000<=tbl<0x530000): break
                # 探测表长：连续 dword 落在 text
                n=0
                while True:
                    v=struct.unpack_from('<I',mem,tbl-BASE+4*n)[0]
                    if TLO<=v<THI: n+=1
                    else: break
                    if n>400: break
                if n>=8:
                    res.append((BASE+off, tbl, n, host(BASE+off)))
            break
res.sort(key=lambda r:-r[2])
print(f'switch 语句 {len(res)} 处')
for site,tbl,n,fn in res[:40]:
    print(f'  switch@{site:#x} (func {fn:#x})  table={tbl:#x}  n={n}')
json.dump([{'site':hex(a),'table':hex(t),'n':n,'func':hex(f)} for a,t,n,f in res],
          open('_switches.json','w',encoding='utf-8'),indent=1)
