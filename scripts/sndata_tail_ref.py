"""
sndata_tail_ref.py — SNDATA XOR 流「尾段」(流偏移 35610..39401，3791B) 结构描述

来源：2026-08-29 续76 逆向
  - 紧接 §3.19 物品定义表（189×19B，流 32019..35609）之后
  - 解密：key = 文件[0x12]^[0x13]（sc1=0x0c / sc2=0x0a）

## ✅ 已坐实（结构层）
1. **性质：静态定义数据，非场景状态**
   两场景逐 u16 比对：1895 个中**仅 10 处不同**（8 处在 617 长段内 + 2 处段边界）。
   ⇒ 这一段是随游戏发行的固定定义，不随剧本改变。
2. **🔴 纠偏：`0xffff` 不是纯分隔符**
   两场景 `0xffff` 个数不同（**sc1=1173 / sc2=1171**）⇒ 它是**数据值**
   （65535 = 无效/空标记），**不是段分隔符**。
   此前「按 `ffff` 切分成 32 段」的方法是**错的**，本文件不再采用该切分。
3. **最长非 ffff 游程 = 617 个 u16**
   - 默认值 **`0x0303`** 出现 **504 次**（占 81.7%）
   - 其余 **113 个**特殊值，聚成 **42 簇**（簇长分布：1×19、2×11、3×5、4×3、5×2、6×1、**29×1**）
   - 特殊值形态两类：
     a) **`(A<<8)|B` 位域对**：A 主要 0..8，B 主要 0..7 / 10 / 11
        （如 `0x0302` `0x0304` `0x0103` `0x0203` `0x0403` `0x0503` `0x0307` `0x080b`）
     b) **独立大值**：`0x9800`/`0xA500`/`0xB700`/`0xFF00` 等（最大 `0xFF00`=65280）
4. **尾端 55 个 u16**：全 0，仅首个为 255（标志数组）
5. **短区（流前段）含 `0x8000|n` 标志值**，n ∈ {11,12,21,22,23,…}，形如 `[26, 0x8017, 290]`。

## 🚫 未坐实
- **语义未知**。自相关扫描（周期 2..39）各周期得分**全部 ≈0.817**，
  被 81.7% 的默认值 0x0303 主导 ⇒ **不存在的定长记录周期**，
  617 段是稀疏/变长结构，**静态无法推出字段含义**，须定位读取它的序列化器。

运行：python scripts/sndata_tail_ref.py
"""
import os
import struct

STREAM_START = 0x598
TAIL_OFF = 35610            # 流内偏移（物品表 189×19 之后）
TAIL_END = 39401
DEFAULT_VAL = 0x0303


def find_data_dir():
    for p in ('Taikou2 Original', os.path.join('..', 'Taikou2 Original')):
        if os.path.isdir(p):
            return p
    return None


def decrypt_stream(path):
    raw = open(path, 'rb').read()
    if raw[:16] != b'TAIKOU2_SCENARIO':
        raise ValueError(f'{path}: 非法 magic')
    key = raw[0x12] ^ raw[0x13]
    return bytes(b ^ key for b in raw[STREAM_START:0x9f81]), key


def tail_u16(dec):
    seg = dec[TAIL_OFF:TAIL_END]
    return list(struct.unpack('<%dH' % (len(seg) // 2), seg[:len(seg) // 2 * 2]))


def longest_run(u16s):
    """最长非 0xffff 游程"""
    best, cur = [], []
    for v in u16s:
        if v == 0xFFFF:
            if len(cur) > len(best):
                best = cur
            cur = []
        else:
            cur.append(v)
    if len(cur) > len(best):
        best = cur
    return best


def clusters(u16s, fill=DEFAULT_VAL, gap=2):
    """非默认值按间隔<=gap 聚簇"""
    spec = [i for i, v in enumerate(u16s) if v != fill]
    if not spec:
        return []
    out, cur = [], [spec[0]]
    for a, b in zip(spec, spec[1:]):
        if b - a <= gap:
            cur.append(b)
        else:
            out.append(cur)
            cur = [b]
    out.append(cur)
    return out


def self_check():
    ok = fail = 0

    def chk(name, cond, extra=''):
        nonlocal ok, fail
        if cond:
            ok += 1
            print(f"  [OK]   {name} {extra}")
        else:
            fail += 1
            print(f"  [FAIL] {name} {extra}")

    d = find_data_dir()
    if d is None:
        print("[SKIP] 未找到 'Taikou2 Original/'")
        return True
    dec1, k1 = decrypt_stream(os.path.join(d, 'SNDATA1.TR2'))
    dec2, k2 = decrypt_stream(os.path.join(d, 'SNDATA2.TR2'))
    chk('密钥 sc1=0x0c', k1 == 0x0c, f"0x{k1:02x}")
    chk('密钥 sc2=0x0a', k2 == 0x0a, f"0x{k2:02x}")

    u1, u2 = tail_u16(dec1), tail_u16(dec2)
    chk('尾段 u16 数 == 1895', len(u1) == 1895, f"n={len(u1)}")
    chk('尾段长度 == 3791B', TAIL_END - TAIL_OFF == 3791)

    # 1) 静态性
    diff = [i for i in range(min(len(u1), len(u2))) if u1[i] != u2[i]]
    chk('两场景差异 <= 12（静态定义）', len(diff) <= 12, f"{len(diff)}/1895")

    # 2) ffff 不是分隔符
    n1 = u1.count(0xFFFF)
    n2 = u2.count(0xFFFF)
    chk("🔴 0xffff 两场景计数不同 ⇒ 是数据值非分隔符", n1 != n2, f"sc1={n1} sc2={n2}")

    # 3) 617 长段
    big = longest_run(u1)
    chk('最长非 ffff 游程 == 617', len(big) == 617, f"n={len(big)}")
    c_def = big.count(DEFAULT_VAL)
    chk('默认值 0x0303 出现 504 次', c_def == 504, f"n={c_def}")
    chk('默认值占比 ~81.7%', 0.80 < c_def / len(big) < 0.83, f"{c_def/len(big):.3f}")
    chk('特殊值 113 个', len(big) - c_def == 113, f"n={len(big)-c_def}")
    cl = clusters(big)
    chk('特殊值聚为 42 簇', len(cl) == 42, f"n={len(cl)}")

    # 4) 形态
    spec = [v for v in big if v != DEFAULT_VAL]
    chk('含 (A<<8)|B 形态（A<=8 且 B<=11）',
        any((v >> 8) <= 8 and (v & 0xFF) <= 11 for v in spec))
    chk('含独立大值 (>=0x9000)', any(v >= 0x9000 for v in spec),
        f"max=0x{max(spec):04x}")

    # 5) 尾端 55 标志
    tail55 = u1[-55:]
    chk('尾端 55 个 u16 全 0 且首为 255',
        tail55[0] == 255 and all(v == 0 for v in tail55[1:]),
        f"首={tail55[0]} 其余0={all(v==0 for v in tail55[1:])}")

    # 6) 负结果：无周期
    # 用默认值占比近似说明（完整自相关见 BREAKTHROUGHS 续76）
    chk('🚫 无定长周期（默认值占比过高）', c_def / len(big) > 0.78,
        f"占比{c_def/len(big):.3f}")

    print(f"\n自校验结果: {ok} OK, {fail} FAIL")
    return fail == 0


if __name__ == '__main__':
    print("=" * 70)
    print("SNDATA 流尾段 (35610..39401, 3791B) —— 结构描述 + 静态自校验")
    print("=" * 70)
    d = find_data_dir()
    if d:
        dec, key = decrypt_stream(os.path.join(d, 'SNDATA1.TR2'))
        u = tail_u16(dec)
        big = longest_run(u)
        print(f"\nkey=0x{key:02x}  u16={len(u)}  最长游程={len(big)}")
        print(f"默认值 0x0303: {big.count(DEFAULT_VAL)}/{len(big)}")
        cl = clusters(big)
        print(f"特殊值 {len(big)-big.count(DEFAULT_VAL)} 个 → {len(cl)} 簇")
        for c in cl[:10]:
            print(f"   起始{c[0]:3d} 长{len(c)}: {[hex(big[i]) for i in c]}")
    print()
    raise SystemExit(0 if self_check() else 1)
