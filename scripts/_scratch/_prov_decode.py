#!/usr/bin/env python3
# 解码国政治表真实流（解码后 XOR 流 偏移 27297, 49*11=539B），验证 +0x00=城/町idx, +0x04=国主, 并破解 +0x06。
import struct, json

DEC = "F:/Games/Taikou 2/scripts/_dec_SNDATA1.TR2.bin"
data = open(DEC, "rb").read()
STREAM_OFF = 27297
N = 49
REC = 11

print(f"decoded bin size = {len(data)}")
blk = data[STREAM_OFF:STREAM_OFF + N*REC]
print(f"block size = {len(blk)}")

def u16(b, o): return b[o] | (b[o+1] << 8)

recs = []
castle_idxs = []
lord_ids = []
w06 = []
b08_0d = []
for i in range(N):
    r = blk[i*REC:(i+1)*REC]
    cidx = r[0]
    lord = u16(r, 1)
    w = u16(r, 3)
    rest = list(r[5:11])
    recs.append((i, cidx, lord, w, rest))
    castle_idxs.append(cidx)
    lord_ids.append(lord)
    w06.append(w)
    b08_0d.append(rest)

print("\n== b0 (castle idx) range / valid (0..199) ==")
print("min", min(castle_idxs), "max", max(castle_idxs), "distinct", len(set(castle_idxs)))
print("all <200:", all(0 <= c < 200 for c in castle_idxs))
print("\n== +0x04 (lord) ==")
print("distinct", len(set(lord_ids)), "vals sample", sorted(set(lord_ids))[:20])
print("0xffff count:", sum(1 for x in lord_ids if x == 0xffff))
print("\n== +0x06 (w06) ==")
print("min", min(w06), "max", max(w06), "distinct", len(set(w06)))
print("sample:", w06[:20])

# 打印全部记录
print("\n== full records (idx | castleIdx | lord(+0x04) | w06(+0x06) | +0x08..+0x0d) ==")
for i, cidx, lord, w, rest in recs:
    print(f"{i:2d} | c={cidx:3d} | lord={lord:#06x}({lord:5d}) | w06={w:#06x}({w:5d}) | {rest}")

# 试着把 +0x06 当作"关联国索引"(0..48) 检验
print("\n== 假设 +0x06 低位=关联国(0..48) ==")
print("w06 < 0x100 计数:", sum(1 for x in w06 if x < 0x100), "/", N)
print("w06 & 0xff < 49 计数:", sum(1 for x in w06 if (x & 0xff) < 49), "/", N)
print("w06 >> 8 < 49 计数:", sum(1 for x in w06 if (x>>8) < 49), "/", N)

# 把所有记录存盘便于后续交叉验证
out = [{"rec":i,"castle_idx":c,"lord":lord,"w06":w,"b08_0d":rest} for i,c,lord,w,rest in recs]
json.dump(out, open("F:/Games/Taikou 2/scripts/prov_politics_decoded.json","w"), ensure_ascii=False, indent=1)
print("\nsaved prov_politics_decoded.json")
