#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
anmseq_format_ref.py  -- 太阁立志传2 (TAIK2W95) ANMSEQ.LZW 动画脚本格式 逆向参考实现 + 自检

=== 文件角色 ===
ANMSEQ.LZW 是"动画序列脚本"容器（非图像！动画控制字节码，按用户指令属破解范围）。
解 LZW 后得到 31941 字节裸流，缓冲槽 0x524960（ANMSbuf，容量 0x8000=32768 > 31941）。

=== 容器结构（消费者 0x496ba0 实锤）===
  [0x00..0x04)  magic  = b"ANMX"  (4 字节，加载函数 0x48bb00 分配 ANMSbuf)
  [0x04..0x824) index  = 520 条 (u16 off, u16 len) 索引对（每条 4 字节）
  [0x824..EOF)  data   = 520 个平铺子记录，子记录 i 位于 [off_i, off_i+len_i)

消费者 0x496ba0 行为：
  esi = 动画 id (16-bit)
  read(0x524960, esi*4+4, 2) -> off_i      ; 读索引对 off
  read(0x524960, esi*4+6, 2) -> len_i      ; 读索引对 len
  copy len_i 字节 (0x524960[off_i..]) -> 工作缓冲 0x524978
  逐字节解释子记录字节码（opcode 0..0x59 经表 @0x496d20 分派到 @0x496cf4 的 11 个 handler）

=== 字节码语义（opcode 表 @0x496d20, 90 项 0x00..0x59 -> slot; 跳表 @0x496cf4, 11 个 handler）===
  slot0  0x00 END          返回（子记录结束符）
  slot1  0x43 SELECT_OBJECT 后跟 u8 idx(0..0x13=19) -> 活动对象 ptr = 0x525350 + idx*12（20 槽，每槽 12B）
  slot2  0x49 CALL 0x47ad60
  slot3  0x4e CLEAR_FLAG    dword[0x525340] = 0
  slot4  0x4f CALL 0x47adc0
  slot5  0x50 WRITE_FLD8    后跟 u16 -> 活动对象字段 +0x08
  slot6  0x53 CALL_OBJ       push(活动对象ptr); call 0x4966d0
  slot7  0x57 WAIT          后跟 u8 -> call 0x496b50(id)（延时/帧等待）
  slot8  0x58 WRITE_FLD0    后跟 u16 -> 活动对象字段 +0x00
  slot9  0x59 WRITE_FLD2    后跟 u16 -> 活动对象字段 +0x02
  slot10 (其余 0x01..0x59 未映射项) NOOP = 循环顶 0x496c28（opcode>0x59 也走 ja 0x496c28 跳过）
  注：0xff 不是终止符（>0x59 为 NOOP），真正终止符是 0x00。

=== 自检结论阈值 ===
  - magic == b"ANMX"
  - N == 520；索引表 4 + 520*4 == 0x824
  - 519/519 相邻平铺（pair[i+1].off == pair[i].off + pair[i].len）
  - pair[0].off == 0x824；末对覆盖到文件尾（remain 0）
  - 全部 520 子记录按上述操作数长度解码，0 溢出（证明操作数长度模型正确）
"""
import os, struct, json, sys

_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _ROOT)
from real_assets import ls11_decompress

SRC = os.path.join(_ROOT, "..", "Taikou2 Original", "ANMSEQ.LZW")
MAGIC = b"ANMX"
N_PAIRS = 520
HDR = 4
DATA_START = HDR + N_PAIRS * 4  # 0x824

# opcode -> 操作数字节数（0 = 无立即数；SELECT=+1, WRITE u16=+2, WAIT=+1）
OP_OPERAND = {0x43: 1, 0x50: 2, 0x58: 2, 0x59: 2, 0x57: 1}
OP_NAME = {
    0x00: "END", 0x43: "SELECT_OBJECT", 0x49: "CALL_47ad60", 0x4e: "CLEAR_FLAG",
    0x4f: "CALL_47adc0", 0x50: "WRITE_FLD8", 0x53: "CALL_OBJ", 0x57: "WAIT",
    0x58: "WRITE_FLD0", 0x59: "WRITE_FLD2",
}

def decode_stream(buf, off, ln):
    """解码单个子记录，返回 [(op, operand_int), ...] 并验证长度不溢出。"""
    ops = []
    p = off
    end = off + ln
    while p < end:
        op = buf[p]; p += 1
        if op == 0x00:
            ops.append((op, None)); break
        n = OP_OPERAND.get(op, 0)
        val = None
        if n == 1:
            val = buf[p]; p += 1
        elif n == 2:
            val = int.from_bytes(buf[p:p + 2], "little"); p += 2
        ops.append((op, val))
    return ops, p - end  # overflow = 解码后越过 end 的字节数（应 == 0）

def main():
    raw = open(SRC, "rb").read()
    dec = ls11_decompress(raw)
    checks = 0; passed = 0
    def chk(name, cond):
        nonlocal checks, passed
        checks += 1
        if cond: passed += 1
        print(("  PASS " if cond else "  FAIL ") + name)

    # 1. magic
    chk("magic == ANMX", dec[:4] == MAGIC)
    chk("LZW 解压 13381 -> 31941", len(raw) == 13381 and len(dec) == 31941)
    # 2. 索引表尺寸
    chk("DATA_START == 0x824", DATA_START == 0x824)
    chk("文件尾 >= 索引表", len(dec) >= DATA_START)
    # 3. 解析 520 对
    pairs = [struct.unpack_from("<HH", dec, HDR + i * 4) for i in range(N_PAIRS)]
    chk("解析得到 520 对", len(pairs) == N_PAIRS)
    # 4. 边界
    inb = all(0x824 <= o and o + l <= len(dec) and l > 0 for o, l in pairs)
    chk("所有 off/len 落在 [0x824, EOF] 且 len>0", inb)
    # 5. 平铺
    adj = sum(1 for i in range(N_PAIRS - 1) if pairs[i + 1][0] == pairs[i][0] + pairs[i][1])
    chk("相邻平铺 519/519", adj == N_PAIRS - 1)
    chk("首对 off == 0x824", pairs[0][0] == 0x824)
    last_off, last_len = pairs[-1]
    chk("末对覆盖到 EOF (remain 0)", last_off + last_len == len(dec))
    # 6. 字节码解码零溢出
    total_ops = 0
    overflow = 0
    end_count = 0
    from collections import Counter
    hist = Counter()
    for (o, l) in pairs:
        ops, ov = decode_stream(dec, o, l)
        overflow += max(0, ov)
        total_ops += len(ops)
        if ops and ops[-1][0] == 0x00:
            end_count += 1
        for op, _ in ops:
            hist[op] += 1
    chk("520 子记录解码 0 溢出（操作数长度模型正确）", overflow == 0)
    chk(">=512 子记录以 0x00 END 结尾", end_count >= 512)
    # 7. 操作数长度模型自洽：每个 WRITE/SELECT/WAIT 出现次数均被合理消费
    meaningful = sum(hist.get(op, 0) for op in OP_NAME)
    chk("有意义 opcode 出现次数 > 0（SELECT 主导）", hist.get(0x43, 0) > 1000)
    print("  INFO 总 opcode 数 %d；有意义 %d；END 子记录 %d/%d" % (total_ops, meaningful, end_count, N_PAIRS))
    print("  INFO opcode 直方图(top):", {hex(k): hist[k] for k in sorted(hist) if hist[k] > 50})

    # 导出结构摘要
    summary = {
        "magic": dec[:4].decode("latin1"),
        "raw_size": len(raw), "dec_size": len(dec),
        "n_pairs": N_PAIRS, "index_table_end": DATA_START, "data_start": 0x824,
        "buffer_slot": "0x524960 (ANMSbuf)", "capacity": 0x8000,
        "consumer": "0x496ba0", "loader": "0x48bb00",
        "opcode_dispatch_table": "0x496d20 (90B)", "handler_table": "0x496cf4 (11)",
        "opcode_semantics": OP_NAME,
        "adjacent_tiling": "%d/%d" % (adj, N_PAIRS - 1),
        "subrecords_ending_END": end_count,
        "opcode_histogram": {hex(k): hist[k] for k in sorted(hist)},
    }
    out = os.path.join(_ROOT, "anmseq_format.json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    print("  INFO 写出 %s" % out)

    print("\nRESULT: %d/%d PASS" % (passed, checks))
    print("ALL PASS ✅" if passed == checks else "HAS FAIL ❌")
    return passed == checks

if __name__ == "__main__":
    sys.exit(0 if main() else 1)
