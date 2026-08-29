MEM = open('scripts/_unpacked_mem.bin','rb').read()
data = MEM[0x50c7c0-0x400000:0x50c7c0-0x400000+240]
print('raw bytes 0x50c7c0..+240:')
for i in range(0, 240, 14):
    chunk = data[i:i+14]
    h = chunk.hex()
    s = chunk.decode('gbk', errors='replace')
    print(f'+{i:#04x}: {h} | {s}')
