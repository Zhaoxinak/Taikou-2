import os, json
SRC="F:/Games/Taikou2"
def rd(n):
    return open(os.path.join(SRC,n),"rb").read()

# 0x47f350 顺序布局:
# 0x00 16B 头, 0x10 2B, 0x12 2B, 0x14 700B(0x519288 武将状态), 0x2d4 700B(第二缓冲)
for sc in (1,2):
    s=rd("SNDATA%d.TR2"%sc)
    print("\n===== SNDATA%d (len=%d) ====="%(sc,len(s)))
    print("header:", s[:16])
    print("obj[0x90] @0x10:", s[0x10:0x12].hex())
    print("obj[0x94] @0x12:", s[0x12:0x14].hex(), "(校验 byte0^byte1 =", hex(s[0x12]^s[0x13]),")")
    wstate = s[0x14:0x14+700]          # -> 0x519288 武将状态
    wstate2 = s[0x2d4:0x2d4+700]       # 第二缓冲
    print("\n--- 0x519288 武将状态 (700B) ---")
    print("  bytes 0..39:", " ".join("%02x"%b for b in wstate[:40]))
    print("  value range: min=%d max=%d"%(min(wstate),max(wstate)))
    from collections import Counter
    c=Counter(wstate)
    print("  distinct values:", len(c))
    print("  top values:", c.most_common(15))
    print("\n--- 第二缓冲 (700B @0x2d4) ---")
    print("  bytes 0..39:", " ".join("%02x"%b for b in wstate2[:40]))
    print("  value range: min=%d max=%d"%(min(wstate2),max(wstate2)))
    c2=Counter(wstate2)
    print("  distinct:", len(c2), " top:", c2.most_common(15))
    # 检查 0x598 是否 0x39
    print("\n  @0x598 byte:", hex(s[0x598]), "(if 0x39 -> read 49B record into 0x519640)")
    print("  @0x598..0x5c9:", s[0x598:0x598+0x31].hex())

# 交叉验证: 读取 bsdata.json 武将名
try:
    b=json.load(open("bsdata.json",encoding="utf-8"))
    ch=b["characters"]
    print("\n=== 武将状态抽样 (SNDATA1) ===")
    for idx in [0,13,16,27,50,100,200,300,699]:
        if idx<len(ch):
            nm=ch[idx].get("name","?")
            print("  #%d %s  : state=0x%02x  state2=0x%02x"%(idx,nm,wstate[idx],wstate2[idx]))
except Exception as e:
    print("bsdata load fail:",e)
