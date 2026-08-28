import os
SRC="F:/Games/Taikou2"
def rd(n): return open(os.path.join(SRC,n),"rb").read()

def show(sc, skip):
    s=rd("SNDATA%d.TR2"%sc)
    key=s[0x12]^s[0x13]
    dec=bytes(x^key for x in s[0x598:])
    print("\n--- SNDATA%d skip=%d ---"%(sc,skip))
    for ri in range(5):
        o=skip+ri*49
        if o+6>len(dec): break
        rec=dec[o:o+49]
        w02=dec[o]|(dec[o+1]<<8)
        w24=dec[o+2]|(dec[o+3]<<8)
        w46=dec[o+4]|(dec[o+5]<<8)
        print(" rec%d @%d: [0:2]=%d [2:4]=%d [4:6]=%d | hex: %s"%(ri,o,w02,w24,w46,rec[:16].hex()))

for sc in (1,2):
    for sk in (0, 600, 608, 616):
        show(sc, sk)
