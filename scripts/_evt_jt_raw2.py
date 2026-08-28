# -*- coding: utf-8 -*-
"""Raw-byte scan for BOTH jmp[reg*4+disp] (FF 24 8x) and call[reg*4+disp] (FF 14 8x)
dispatch tables. For each table, resolve entries (abs / rel-tbl / rel-jmp) and report
any entry matching one of the HANDLER set. This reveals the opcode -> handler map."""
import io, sys, struct
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

BASE = 0x400000
MEM = open('scripts/_unpacked_mem.bin', 'rb').read()
CODE_LO, CODE_HI = 0x400000, 0x600000
SIBS = [0x85,0x8D,0x95,0x9D,0xA5,0xAD,0xB5,0xBD]
# handler set (from _evt_enum): functions calling both 0x49f6b0 and 0x49b860
HANDLERS = set()
i=0;n=len(MEM)-5
while i<n:
    if MEM[i]==0xE8:
        rel=struct.unpack('<i',MEM[i+1:i+5])[0]
        tgt=(BASE+i+5+rel)&0xffffffff
        if tgt==0x49f6b0 or tgt==0x49b860:
            # record fn-start = nearest preceding call-target; approximate: scan back to prologue
            pass
    i+=1
# simpler: reuse the known handler list
HANDLERS = {
0x443fe0,0x446bd0,0x446d00,0x490c0,0x499f0,0x4b7c0,0x4ca90,0x4f740,0x5d0b0,0x5df50,
0x609e0,0x61490,0x6e4b0,0x9d3e0,0xb3ac0,0xb4b20,0xb54b0,0xb5fa0,0xc91e0,0xca8e0,
0xd0ca0,0xd6ff0,0x4e7e10,0x4e82c0}

def find_tables():
    tabs=[]
    i=0;n=len(MEM)-7
    while i<n:
        b0=MEM[i]; b1=MEM[i+1]; b2=MEM[i+2]
        if (b0==0xFF and b1 in (0x14,0x24) and b2 in SIBS):
            disp=struct.unpack('<I',MEM[i+3:i+7])[0]
            va=BASE+i
            tabs.append((va, disp&0xffffffff, b1))
            i+=7
        else:
            i+=1
    return tabs

tabs=find_tables()
print(f"found {len(tabs)} dispatch tables (call+jmp)")

def entries_at(tbl):
    if not (CODE_LO<=tbl<len(MEM)-1024): return None
    return struct.unpack('<256I', MEM[tbl-BASE:tbl-BASE+1024])

for jmp_va,tbl,kind in tabs:
    en=entries_at(tbl)
    if en is None: continue
    hits=[]
    for idx,v in enumerate(en):
        for mode,base in (('abs',None),('reltbl',tbl),('reljmp',jmp_va+6)):
            rv=v&0xffffffff
            if rv&0x80000000: rv-=0x100000000
            t = v if mode=='abs' else ((base+rv)&0xffffffff)
            if CODE_LO<=t<CODE_HI and t in HANDLERS:
                hits.append((idx,t,mode))
    if hits:
        print(f"\n*** TABLE @jmp/call {jmp_va:#010x} tbl={tbl:#010x} kind={'call' if kind==0x14 else 'jmp'}")
        for idx,t,mode in hits:
            print(f"    entry[{idx}] -> handler {t:#010x} ({mode})")
    # also report tables with many valid absolute code ptrs (real dispatch tables)
    va=sum(1 for v in en[:80] if CODE_LO<=v<CODE_HI)
    if va>8:
        print(f"  big table jmp/call@{jmp_va:#010x} tbl={tbl:#010x} absptr(80)={va}")
