# -*- coding: utf-8 -*-
# 统计 4 个高字节 setter 的直接 E8 调用计数（确认 0x49a828 是否真无调用）
import io, sys, struct
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
BASE = 0x400000
MEM = open('scripts/_unpacked_mem.bin', 'rb').read()
SET = {0x49a808:'F3', 0x49a828:'F4', 0x49a840:'F2B', 0x49a868:'DEAD', 0x49a7e0:'PACK'}
cnt = {k:0 for k in SET}
i,n = 0, len(MEM)-5
while i<n:
    if MEM[i]==0xE8:
        rel=struct.unpack('<i',MEM[i+1:i+5])[0]
        t=(BASE+i+5+rel)&0xffffffff
        if t in SET: cnt[t]+=1
    i+=1
for k,v in SET.items():
    print("  0x%x (%s) : %d direct callers" % (k, v, cnt[k]))
