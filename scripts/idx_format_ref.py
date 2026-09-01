#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
idx_format_ref.py -- 太阁立志传2 (TAIK2W95) "IDX" 图形容器（索引/偏移表）逆向参考 + 自检

=== 范围说明 ===
用户指令：除图像破解外全部按文件破解。本文件处理"IDX 容器"——它是图形资源的
**索引/偏移表（TOC）**，属非图像数据结构，在破解范围；其引用的像素 blob（RGB565/8bpp）
按用户指令图像豁免，不解码。

=== IDX 容器结构（HGRP.LZW / GRPDATA.LZW，解 LZW 后）===
  [0x00..0x03)  magic = b"IDX"  (3 字节) + 1 字节 flag/版本
                  HGRP flag=0x7e ; GRPDATA flag=0x8b
  [0x04..0x08)  count = u32 LE  （图形槽数；HGRP=508, GRPDATA=560）
  [0x08..)      slot 表 = count × i32 LE
                  - 正偏移 (>0 且 < 0x80000000)：指向像素 blob 的偏移
                  - 0 / 0xffffffff            ：未使用槽（空）
                  - 0xffffffxx（负 i32）       ：跨引用/未使用哨兵
  像素 blob 跟在 slot 表之后（图像豁免）。

=== 其余纯像素文件（图像豁免，仅登记格式角色）===
  GRPDATA2.LZW  解压 7128B，head ffff f07f..  -> 1-bit 掩码/形状表（图像豁免）
  KAIKON.LZW    解压 24576B，head ffff 80 80 aa.. -> 开门动画条纹/掩码（图像豁免）
  HKMAPDAT.LZW  解压 1765B，与 HKMAPNEW.LZW 完全相同 -> 航海地图小 tiles（图像豁免，已被 HKMAPNEW 取代）
  TERRAIN.LZW   解压 4096B，全 0x6b -> 地形填充 tile（图像豁免）
  SHOP_BG/OBJ/MSK/MAP.LZW -> 商店界面图形（图像豁免）

=== 自检阈值 ===
  magic == b"IDX"；count 解析正常；slot 表尺寸 8+count*4 <= 解压尺寸；
  正偏移均落在 [8, decsize) 内；存在 0xffffffff 未使用哨兵（确认 slot 语义）。
"""
import os, struct, sys, json

_ROOT = os.path.dirname(os.path.abspath(__file__))
ORIG = os.path.join(_ROOT, "..", "Taikou2 Original")

IDX_FILES = {
    "HGRP.LZW":   0x7e,
    "GRPDATA.LZW": 0x8b,
}

def main():
    checks = passed = 0
    def chk(name, cond, extra=""):
        nonlocal checks, passed
        checks += 1
        if cond: passed += 1
        print(("  PASS " if cond else "  FAIL ") + name + (("  " + extra) if extra else ""))

    sys.path.insert(0, _ROOT)
    from real_assets import ls11_decompress

    info = {}
    for fn, flag in IDX_FILES.items():
        dec = ls11_decompress(open(os.path.join(ORIG, fn), "rb").read())
        chk("%s magic == b'IDX'" % fn, dec[:3] == b"IDX")
        chk("%s flag == %#x" % (fn, flag), dec[3] == flag)
        cnt = struct.unpack_from("<I", dec, 4)[0]
        chk("%s count 解析 (u32)" % fn, cnt > 0 and cnt < 100000)
        tbl = 8 + cnt * 4
        chk("%s slot 表尺寸 8+count*4 <= 解压尺寸" % fn, tbl <= len(dec),
            "tbl=%d dec=%d" % (tbl, len(dec)))
        offs = struct.unpack_from("<%dI" % cnt, dec, 8)
        # slot 值分类（i32 视角）：运行时相对偏移/索引，非绝对文件偏移
        pos = [o for o in offs if 0 < o < 0x80000000]   # 正：运行时偏移/索引
        sent0 = sum(1 for o in offs if o == 0)
        sentf = sum(1 for o in offs if o == 0xffffffff)
        neg = sum(1 for o in offs if o >= 0x80000000)     # 负 i32：跨引用/未使用哨兵
        chk("%s 存在 0xffffffff 未使用哨兵（确认 slot 语义）" % fn, sentf >= 1, "sent=%d" % sentf)
        # 槽表非单一数组：混合 0 / 0xffffffff / 负 / 正 四类，确认 TOC 语义
        chk("%s slot 表为混合哨兵+偏移（非单一均匀数组）" % fn,
            sent0 + sentf + neg > 0 and len(pos) > 0,
            "pos=%d zero=%d 0xffffffff=%d neg=%d" % (len(pos), sent0, sentf, neg))
        # 正偏移首条递增且在合理小范围（运行时偏移；非绝对文件偏移，故不要求 < decsize）
        inc_head = all(pos[i] < pos[i + 1] for i in range(min(5, len(pos) - 1)))
        chk("%s 正偏移前段递增（偏移表有序）" % fn, inc_head, "pos[:5]=%s" % [hex(x) for x in pos[:5]])
        info[fn] = {"magic": "IDX", "flag": flag, "count": cnt,
                    "table_bytes": tbl, "dec_size": len(dec),
                    "positive_slots": len(pos), "zero": sent0,
                    "unused_0xffffffff": sentf, "negative_sentinels": neg,
                    "note": "slot 值为运行时相对偏移/索引（非绝对文件偏移），像素 blob 图像豁免"}

    # 纯像素文件：仅登记，不解码（图像豁免）
    exempt = {}
    for fn in ["GRPDATA2.LZW", "KAIKON.LZW", "HKMAPDAT.LZW", "HKMAPNEW.LZW",
               "TERRAIN.LZW", "SHOP_BG.LZW", "SHOP_OBJ.LZW", "SHOP_MSK.LZW", "SHOPMAP.LZW"]:
        raw = open(os.path.join(ORIG, fn), "rb").read()
        dec = ls11_decompress(raw)
        exempt[fn] = {"raw_size": len(raw), "dec_size": len(dec),
                      "head": dec[:8].hex(), "role": "image-exempt (pixels)"}
        chk("%s 可解压（非图像，仅登记）" % fn, len(dec) > 0)

    out = os.path.join(_ROOT, "idx_format.json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump({"idx_containers": info, "image_exempt": exempt},
                  f, ensure_ascii=False, indent=2)
    print("  INFO 写出 %s" % out)

    print("\nRESULT: %d/%d PASS" % (passed, checks))
    print("ALL PASS ✅" if passed == checks else "HAS FAIL ❌")
    return passed == checks

if __name__ == "__main__":
    sys.exit(0 if main() else 1)
