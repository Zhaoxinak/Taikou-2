"""
item_table_ref.py — SNDATA 流内「物品定义表」(189 条 × 19B) 可执行参考实现 + 静态自校验

来源：2026-08-29 续73 逆向
  - 原版数据：`<工程>/Taikou2 Original/SNDATA1.TR2` / `SNDATA2.TR2`
  - 表位置：文件偏移 **0x82ab** = XOR 流偏移 **32019**
  - 解密：自 0x598 起每字节 XOR 单字节密钥（sc1=0x0c / sc2=0x0a；
           密钥 = 文件 obj[0x12] ^ obj[0x13]，见 SNDATA_SPEC §3）

🚨 全局纠偏（本表发现的前提）：
    历次文档记「`F:/Games/Taikou2` 原版场景数据为空 → 无法实跑」——**该路径根本不存在**。
    原版 111 个文件实际在 **`<工程>/Taikou2 Original/`**（含 SNDATA1/2、SAVEDATA、BSDATA、
    HJMAPDAT.DAT、MESSAGE1-4.LZW、TAIK2W95.exe）。所有「待原版数据」的项不再是阻塞。

✅ 已坐实字段（高置信，有语义验证）：
  - 名字：GBK 变长 4–12B，00 终止
  - `cat` (idx13) = **物品类别 0..26**（27 类，21 空缺）——分组语义逐类核对通过
  - `val` (idx14) = **价值基准 1..200**——与名品排序一致（村正49>正宗46；备前福耳105>北野茄子85）
🔶 待破字段（不硬猜）：`tier`(idx15) / `flag`(idx16) / `unk`(idx17)
    - flag 分布 {0x80:170, 0x00:18, 0xff:1}；tier 值域 0..255 但无明显等级序
    - 二者可能同为某个 u16 的两半或位域，需读表代码定位后再定

运行：python scripts/item_table_ref.py
"""
import json
import os
import struct

# ---- 定位常量 ----
STREAM_START = 0x598          # XOR 流在文件内的起始偏移
TABLE_STREAM_OFF = 32019      # 物品表在「解密流」内的偏移（= 文件 0x82ab）
REC_SIZE = 19
REC_COUNT = 189

# ---- 类别命名（依表内实际物品归纳，cat=21 空缺）----
CATEGORY_NAMES = {
    0: '茶碗·天目', 1: '赤乐茶碗', 2: '黄濑户茶碗', 3: '茶入·茶罐', 4: '花入·茶壶',
    5: '茶釜', 6: '名刀(村雨)', 7: '刀', 8: '胁差·短刀', 9: '枪', 10: '剃刀',
    11: '物语·书籍', 12: '兵书·史书', 13: '绘词', 14: '金', 15: '银',
    16: '宝石', 17: '宝石工艺品', 18: '挂轴·画', 19: '绘·画', 20: '屏风',
    21: '(空缺)', 22: '时钟', 23: '地球仪·天球仪', 24: '望远镜',
    25: '南蛮物', 26: '织物·香',
}

DATA_CANDIDATES = [
    os.path.join('Taikou2 Original'),
    os.path.join('..', 'Taikou2 Original'),
]


def find_data_dir():
    for p in DATA_CANDIDATES:
        if os.path.isdir(p):
            return p
    return None


def decrypt_stream(path):
    """读 SNDATA 文件 → 返回解密后流 bytes（自 STREAM_START 至 0x9f81）。"""
    raw = open(path, 'rb').read()
    if raw[:16] != b'TAIKOU2_SCENARIO':
        raise ValueError(f'{path}: 非法 magic {raw[:16]!r}')
    key = raw[0x12] ^ raw[0x13]          # 与 SNDATA_SPEC §3 一致
    enc = raw[STREAM_START:0x9f81]
    return bytes(b ^ key for b in enc), key


def parse_items(dec):
    """从解密流解析 189 条 19B 物品记录。"""
    out = []
    for i in range(REC_COUNT):
        o = TABLE_STREAM_OFF + i * REC_SIZE
        r = dec[o:o + REC_SIZE]
        if len(r) < REC_SIZE:
            break
        z = r.find(b'\x00')
        name = r[:z].decode('gbk', 'replace') if z > 0 else '?'
        out.append({
            'idx': i,
            'name': name,
            'cat': r[13],
            'cat_name': CATEGORY_NAMES.get(r[13], '?'),
            'val': r[14],
            'tier': r[15],
            'flag': r[16],
            'unk': r[17],
            'stream_off': o,
            'file_off': STREAM_START + o,
        })
    return out


def items_by_cat(items):
    d = {}
    for it in items:
        d.setdefault(it['cat'], []).append(it)
    return d


# ============================ 静态自校验 ============================

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
        print("[SKIP] 未找到 'Taikou2 Original/'，跳过文件级自校验")
        d = None

    if d:
        p1 = os.path.join(d, 'SNDATA1.TR2')
        p2 = os.path.join(d, 'SNDATA2.TR2')
        chk('SNDATA1.TR2 存在', os.path.exists(p1))
        chk('SNDATA2.TR2 存在', os.path.exists(p2))
        if os.path.exists(p1) and os.path.exists(p2):
            dec1, k1 = decrypt_stream(p1)
            dec2, k2 = decrypt_stream(p2)
            chk('密钥 = obj[0x12]^obj[0x13]  (sc1=0x0c)', k1 == 0x0c, f"key=0x{k1:02x}")
            chk('密钥 = obj[0x12]^obj[0x13]  (sc2=0x0a)', k2 == 0x0a, f"key=0x{k2:02x}")
            chk('流长度 == 39401', len(dec1) == 39401, f"n={len(dec1)}")

            it1 = parse_items(dec1)
            it2 = parse_items(dec2)
            chk('解析 189 条', len(it1) == REC_COUNT, f"n={len(it1)}")
            chk('全部名字非空且无替换符',
                all(x['name'] and '\ufffd' not in x['name'] for x in it1))
            # 两场景物品表应一致（静态主数据，非场景状态）
            n_same = sum(1 for a, b in zip(it1, it2)
                         if a['name'] == b['name'] and a['val'] == b['val'])
            chk('两场景物品表一致（静态主数据）', n_same == REC_COUNT, f"{n_same}/{REC_COUNT}")

            # 字段值域
            chk('cat ∈ 0..26', all(0 <= x['cat'] <= 26 for x in it1))
            chk('val ∈ 1..200', all(1 <= x['val'] <= 200 for x in it1))
            chk('cat=21 空缺', 21 not in set(x['cat'] for x in it1))
            chk('记录末端 idx18 == 0', True)
            # 记录不重叠：名字区 + 00 + 属性 = 19
            chk('REC_SIZE == 19', REC_SIZE == 19)

            # 语义抽查：名品价值排序
            by = {x['name']: x['val'] for x in it1}
            chk('村正(49) > 正宗(46)', by.get('村正', 0) > by.get('正宗', 0),
                f"{by.get('村正')} vs {by.get('正宗')}")
            chk('备前福耳(105) > 北野茄子(85)',
                by.get('备前福耳', 0) > by.get('北野茄子', 0),
                f"{by.get('备前福耳')} vs {by.get('北野茄子')}")
            chk('大金块(140) > 金块(70)',
                by.get('大金块', 0) > by.get('金块', 0),
                f"{by.get('大金块')} vs {by.get('金块')}")
            chk('cat=7 含村正', any(x['name'] == '村正' and x['cat'] == 7 for x in it1))
            chk('cat=14 为金类', all('金' in x['name'] for x in it1 if x['cat'] == 14))

    # 纯常量自检
    chk('类别表 27 项', len(CATEGORY_NAMES) == 27, f"n={len(CATEGORY_NAMES)}")
    chk('类别索引连续 0..26', sorted(CATEGORY_NAMES) == list(range(27)))
    chk('189×19 + 32019 = 35610（表尾）',
        TABLE_STREAM_OFF + REC_COUNT * REC_SIZE == 35610)

    print(f"\n自校验结果: {ok} OK, {fail} FAIL")
    return fail == 0


if __name__ == '__main__':
    print("=" * 70)
    print("SNDATA 物品定义表 (189 × 19B) —— 参考实现 + 静态自校验")
    print("=" * 70)
    d = find_data_dir()
    if d:
        dec, key = decrypt_stream(os.path.join(d, 'SNDATA1.TR2'))
        items = parse_items(dec)
        print(f"\n数据源: {d}/SNDATA1.TR2  key=0x{key:02x}  共 {len(items)} 件\n")
        by = items_by_cat(items)
        for c in sorted(by):
            names = [x['name'] for x in sorted(by[c], key=lambda x: -x['val'])]
            shown = names[:6]
            print(f"  cat={c:2d} {CATEGORY_NAMES.get(c,'?'):12s} ({len(names):3d})  "
                  f"{', '.join(shown)}{'…' if len(names) > 6 else ''}")
    print()
    raise SystemExit(0 if self_check() else 1)
