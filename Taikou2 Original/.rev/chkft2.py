import struct, capstone
f=open(r'F:\Games\Taikou 2\Taikou2 Original\TAIK2W95_ft2.exe','rb').read()
def rd(va,n): o=va-0x400000-0xC00; return f[o:o+n]
md=capstone.Cs(capstone.CS_ARCH_X86,capstone.CS_MODE_32)
def full(va,length):
    blob=rd(va,length); got=bytearray(); c=0
    for ins in md.disasm(blob,va):
        got.extend(ins.bytes); c+=1
    assert bytes(got)==blob, "MISMATCH %06X got %d/%d"%(va,len(got),len(blob))
    print("OK %06X: %d 指令 完全解码, %d 字节"%(va,c,len(blob)))
full(0x535200,104)   # ft_kbd
full(0x5352C0,32)    # nav_kbd
print("user32 str:", rd(0x535270,7))
print("GetAsync str:", rd(0x535280,17))
