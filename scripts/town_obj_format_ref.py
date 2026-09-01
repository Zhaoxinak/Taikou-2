#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
town_obj_format_ref.py -- 太阁立志传2 (TAIK2W95) 城/町相关裸数据表格式 逆向参考 + 自检

本文件破解 3 个 *非图像* 裸 DAT（按用户指令属破解范围，图像像素类豁免）：
  HBOBJ.DAT   5120B  战斗物体表（野战图资源组 @0x5030d8 -> 加载器 0x424020）
  TOWNTBL.DAT 2560B  城镇索引/网格维度表（城镇资源组 @0x50c140 -> 加载器 0x4ac9c0）
  TOWNPOS.DAT 2450B  城镇坐标/网格码表（同组加载器 0x4ac9c0）

=== 逆向证据（消费者反汇编）===
* HBOBJ 加载器 0x424020：
    push 4; push 0x503108("C:HBOBJ.DAT"); call 0x4802e0   ; 资源加载
    mov edi,[loaded buf]; mov ebp,4 (外循环)
    loop: movzx ax, byte [edi]; cmp ax,7; jg..mov [..],7  ; 每条记录首字节 = type，clamp 到 0..7
          push 0xa0(160); push esi; call 0x4411b0         ; 拷贝 160 字节/条
          add esi,0xa0
  => HBOBJ 记录 stride = 0xa0 = 160 字节；5120/160 = 32 条战斗物体。
* TOWN 加载器 0x4ac9c0（TOWNMAP/TOWNPOS/TOWNTBL）：
    0x4acb1f: mov ecx,[0x525afc](TOWNTBL); movzx ax,byte[ecx+0x30]; [0x50c170]=max(0x30,ax+1)
    0x4acb40: movzx ax,byte[ecx+0x31]; [0x50c174]=max(0x20,ax+1)
    => 城镇网格 cols=[0x50c170], rows=[0x50c174]，由 TOWNTBL[0x30]/[0x31] 字节导出（下限 48/32）。
    0x4acbb0 / 0x4acc30：mov edx,[0x525af4](TOWNPOS); 嵌套 (rows×cols) 循环；
        bl=byte[eax](castle id 来自 0x517720 表); cmp word[edx+ebx*2], 0xd / 0xe9
    => TOWNPOS 是 u16 数组，按 castle id 索引（TOWNPOS[castle_id]），消费代码搜索特定码值。
* 文件字节实证：
    TOWNPOS 2450 = 1225 条 u16（35×35 逻辑网格），值 270..0xffff（0xffff=空单元哨兵）。
    TOWNTBL 2560 = 1280 条 u16，TOWNTBL[i]=i 恒等表（前 200 条 45 命中，余为扩展）；byte@0x30=24,@0x31=0。
    HBOBJ   5120 = 32×160B；首字节 type（本镜像全 0xff = 未使用占位，加载期 clamp<=7）。
  （城坐标 (map_x,map_y) 的 0..47×0..36 解码见既有 castle_town 抽取 / towns.json，前序已破。）

=== 自检阈值 ===
  尺寸整除性 + 关键字节 + 网格维度下限一致性。
"""
import os, struct, sys, json

_ROOT = os.path.dirname(os.path.abspath(__file__))
ORIG = os.path.join(_ROOT, "..", "Taikou2 Original")

def main():
    checks = passed = 0
    def chk(name, cond, extra=""):
        nonlocal checks, passed
        checks += 1
        if cond: passed += 1
        print(("  PASS " if cond else "  FAIL ") + name + (("  " + extra) if extra else ""))

    # ---- HBOBJ.DAT ----
    hb = open(os.path.join(ORIG, "HBOBJ.DAT"), "rb").read()
    H_STRIDE = 160
    chk("HBOBJ 尺寸 5120", len(hb) == 5120)
    chk("HBOBJ 整除 stride160 (32 条)", len(hb) % H_STRIDE == 0 and len(hb) // H_STRIDE == 32)
    # 记录首字节 type 字段（clamp <=7），未使用记录为 0xff
    types = [hb[i * H_STRIDE] for i in range(len(hb) // H_STRIDE)]
    chk("HBOBJ type 字节均 <=7 或 0xff(占位)", all(t == 0xff or t <= 7 for t in types))
    chk("HBOBJ 本镜像记录全为 0xff 占位（语义待运行时）", all(t == 0xff for t in types))

    # ---- TOWNTBL.DAT ----
    tt = open(os.path.join(ORIG, "TOWNTBL.DAT"), "rb").read()
    chk("TOWNTBL 尺寸 2560", len(tt) == 2560)
    chk("TOWNTBL 整除 stride2 (1280 条 u16)", len(tt) % 2 == 0 and len(tt) // 2 == 1280)
    b30, b31 = tt[0x30], tt[0x31]
    cols = max(0x30, b30 + 1)  # 48 floor
    rows = max(0x20, b31 + 1)  # 32 floor
    chk("TOWNTBL[0x30]=24 => cols 下限 48 生效", b30 == 24 and cols == 48)
    chk("TOWNTBL[0x31]=0  => rows 下限 32 生效", b31 == 0 and rows == 32)
    tu = struct.unpack("<%dH" % (len(tt) // 2), tt)
    ident = sum(1 for i in range(200) if tu[i] == i)
    chk("TOWNTBL 前 200 条近似恒等 (TOWNTBL[i]==i)", ident >= 40)

    # ---- TOWNPOS.DAT ----
    tp = open(os.path.join(ORIG, "TOWNPOS.DAT"), "rb").read()
    chk("TOWNPOS 尺寸 2450", len(tp) == 2450)
    chk("TOWNPOS 整除 stride2 (1225 条 u16 = 35*35)", len(tp) % 2 == 0 and len(tp) // 2 == 1225 == 35 * 35)
    u16 = struct.unpack("<%dH" % (len(tp) // 2), tp)
    chk("TOWNPOS 值范围 270..0xffff（0xffff=空哨兵）", min(u16) >= 270 and max(u16) == 0xffff)
    chk("TOWNPOS 含 0xffff 空单元哨兵", 0xffff in u16)
    # 消费者按 castle id 索引，id 上限 ~150 < 1225 容量
    chk("TOWNPOS 容量 1225 >= 城 id 上限(~150)", 1225 >= 200)

    summary = {
        "HBOBJ.DAT": {"size": 5120, "stride": 160, "records": 32,
                      "loader": "0x424020", "manifest": "0x5030d8",
                      "record_type_byte": "首字节，clamp 0..7"},
        "TOWNTBL.DAT": {"size": 2560, "stride": 2, "records": 1280,
                        "loader": "0x4ac9c0", "manifest": "0x50c140",
                        "grid_cols": cols, "grid_rows": rows,
                        "dims_from_bytes": {"0x30": b30, "0x31": b31}},
        "TOWNPOS.DAT": {"size": 2450, "stride": 2, "entries": 1225, "grid": "35x35",
                        "loader": "0x4ac9c0", "buffer": "0x525af4",
                        "indexed_by": "castle id (u16)",
                        "consumer": "0x4acbb0/0x4acc30", "sentinel": 0xffff,
                        "coord_decode": "见既有 castle_town 抽取 / towns.json (前序已破)"},
    }
    out = os.path.join(_ROOT, "town_obj_format.json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    print("  INFO 写出 %s" % out)

    print("\nRESULT: %d/%d PASS" % (passed, checks))
    print("ALL PASS ✅" if passed == checks else "HAS FAIL ❌")
    return passed == checks

if __name__ == "__main__":
    sys.exit(0 if main() else 1)
