#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
解析 SNDATA1/2.TR2 (正确结构, 2026-08-24 经反汇编确认):
  [0:16]  "TAIKOU2_SCENARIO" 签名
  [16:]   833 条 x 49 字节 记录 (记录 i 在 offset 16 + i*49, 由 0x47d890/0x47d8d0 的
          `lea edx,[ecx+eax+0x10]` + `push 0x31`(=49) 读 49 字节 确认)
  [16+833*49 = 40833 : 40856]  23 字节尾部 (场景1=全 0x0C, 场景2=全 0x0A)
校验: 16 + 833*49 + 23 = 40856 精确.
注意: 自相关法在 0x01/0x00 低密度数据上会假阳性(曾误报 59B), 必须信反汇编 stride.
"""
import struct

def summarize(fn):
    sd = open(f"F:/Games/Taikou2/{fn}","rb").read()
    assert sd[:16] == b"TAIKOU2_SCENARIO", f"{fn} sig mismatch"
    n = len(sd)
    rec = 49
    start = 16
    nrec = (40833 - 16) // rec   # = 833
    tail = sd[40833:40856]
    magic0 = sd[16:20].hex()      # 记录0 前 4 字节 (每场景不同)
    print(f"{fn}: size={n}  sig=OK")
    print(f"  records: start={start} size={rec} count={nrec}  -> {start}+{nrec}*{rec}={start+nrec*rec}")
    print(f"  tail[40833:40856] = {tail.hex()}  (uniform={len(set(tail))==1}, val=0x{tail[0]:02x})")
    print(f"  rec0 前 12B = {sd[16:28].hex()}   (4B头={magic0} + 8B 旗帜)")
    # 验证每条记录首字节分布 (抽样)
    heads = [sd[start + i*rec] for i in range(nrec)]
    from collections import Counter
    print(f"  记录首字节分布(top5): {Counter(heads).most_common(5)}")
    # 记录1 是否全 0 (内存笔记说 rec1 @65 = 全 0)
    print(f"  rec1 @65 前 12B = {sd[65:77].hex()}")
    return sd

if __name__ == "__main__":
    for fn in ["SNDATA1.TR2","SNDATA2.TR2"]:
        summarize(fn)
        print()
    # 一致性校验
    s1=open(r"F:/Games/Taikou2/SNDATA1.TR2","rb").read()
    s2=open(r"F:/Games/Taikou2/SNDATA2.TR2","rb").read()
    same=sum(1 for i in range(16,40833) if s1[i]==s2[i])
    print(f"两场景 [16:40833] 相同字节: {same}/{40833-16} = {same/(40833-16)*100:.1f}%  差异主要在旗帜阵列")
    print("DONE")
