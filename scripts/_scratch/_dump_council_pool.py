MEM = open('scripts/_unpacked_mem.bin','rb').read()
cur = 0x50c7c0
labels = ['出兵','结束会议','高压外交','友好外交','谋略','卖出军粮','购入军粮','购入军马','购入洋枪','开垦农田','训练','修复','筑城','朝廷工作','收集情报','移动居城','武者修行','茶会','任命','其他武将','取消']
for i, expected in enumerate(labels):
    chunk = MEM[cur-0x400000:cur-0x400000+14]
    end = chunk.find(b'\x00')
    if end < 0: end = 14
    s = chunk[:end].decode('gbk', errors='replace')
    mark = 'Y' if s.strip() == expected else 'N'
    print(f'[{i:2d}] 0x{cur:08x} {mark} {repr(s)} exp={expected!r}')
    cur += 14
