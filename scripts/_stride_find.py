"""Detect the runtime stride used to index 0x51eb88 by finding
   imul reg,reg,K  followed by  add reg, 0x51eb88  (or lea reg,[reg*K+base])."""
from capstone import Cs, CS_ARCH_X86, CS_MODE_32
from capstone.x86 import (X86_REG_EAX, X86_REG_EBX, X86_REG_ECX, X86_REG_EDX,
                          X86_REG_ESI, X86_REG_EDI, X86_REG_EBP)
MEM = open('_unpacked_mem.bin','rb').read()
BASE=0x400000; SZ=len(MEM)
md = Cs(CS_ARCH_X86, CS_MODE_32); md.detail=True
TARGET=0x51eb88
REGN={X86_REG_EAX:'eax',X86_REG_EBX:'ebx',X86_REG_ECX:'ecx',X86_REG_EDX:'edx',
      X86_REG_ESI:'esi',X86_REG_EDI:'edi',X86_REG_EBP:'ebp'}
addr=BASE
found=set()
while addr < BASE+SZ:
    try: ins=next(md.disasm(MEM[addr-BASE:addr-BASE+16], addr))
    except Exception: addr+=1; continue
    s=ins.mnemonic+' '+ins.op_str
    # detect imul reg,reg,K
    if ins.mnemonic=='imul' and len(ins.operands)==3 and ins.operands[0].type==1 and ins.operands[1].type==1 and ins.operands[0].reg==ins.operands[1].reg and ins.operands[2].type==2:
        r=REGN.get(ins.operands[0].reg); K=ins.operands[2].imm & 0xffffffff
        if r is None: addr=ins.address+ins.size; continue
        if 8 <= K <= 256:
            # look ahead up to 6 instrs for add r,0x51eb88 or lea with base
            for j in range(1,7):
                a2=addr+ins.size
                try: nxt=next(md.disasm(MEM[a2-BASE:a2-BASE+16], a2))
                except: break
                s2=nxt.mnemonic+' '+nxt.op_str
                if ('0x%x'%TARGET in s2) and (nxt.mnemonic in ('add','lea')) :
                    # check same reg
                    if nxt.operands and nxt.operands[0].type==1 and REGN.get(nxt.operands[0].reg)==r:
                        found.add((K, addr, a2)); break
                if nxt.mnemonic in ('call','ret','jmp'): break
                addr2=a2  # continue loop via outer? no, just one step
                # we must advance manually; emulate small window
                # peek next already consumed; break out to outer loop to continue
                break
    addr=ins.address+ins.size
for K,va1,va2 in sorted(found):
    print("stride K=%d  @%08x imul ..  @%08x add/lea base" % (K,va1,va2))
print("unique strides:", sorted(set(k for k,_,_ in found)))
