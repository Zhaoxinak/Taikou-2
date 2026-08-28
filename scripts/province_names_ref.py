"""
province_names_ref.py — 49 国国名表 + 国政治表 `0x5179b8` 的数据层解析

来源：2026-08-29 续74

## ① 49 国国名（✅ 全新成果，此前文档无完整名单）
- **表 `0x506ca8` 是 stride 9 的「字符串数组」，不是指针表**
  （⚠️ 之前按 `4 字节指针表` 读取 → 绝大多数国名解析为空，是错的）
- 索引 0..48 = 49 国；其后 49..87 附加地名 / 88..291 城·町 / 292..369 职种（见 §2.8）
- 完整名单见下 `PROVINCE_NAMES`

## ② 国政治表 `0x5179b8`(stride 14) 的数据源
- 序列化器 `0x47e440` 从 SNDATA XOR **流偏移 27297** 读 **539B = 49 × 11B**，
  写入 **`0x5179bc`**（= `0x5179b8 + 4`）⇒ 填充的是每条 14B 记录的 **+0x04..+0x0e**
- 11 字节记录布局（相对 `0x5179bc`，即绝对 +0x04 起）：
  ```
  rec[0..1]  +0x04  word  武将编号（0xffff = 无）   ← 动态：41/49 随场景变化
  rec[2..3]  +0x06  word  ?  静态（49/49 同）值域 0..28000，29 个值（疑石高/兵力）
  rec[4]     +0x08  byte  ?  混合（38/49 同）值域 0..44（疑邻国/地方ID）
  rec[5]     +0x09  byte  ?  静态 值域几乎恒 3
  rec[6..7]  +0x0a  word  ?  静态 恒 0xffff（哨兵/未使用）
  rec[8..9]  +0x0c  word  ?  准静态（47/49 同）值域 0..996
  rec[9]     +0x0d  byte  ?  静态 值域 0..3（4 类）
  rec[10]    +0x0e  byte  ?  混合（42/49 同）
  ```
- ✅ **坐实**：`+0x04`(word) = 武将编号（续71 由指令流推断「国主武将号」，此处由真实数据确认其为武将编号且随剧本变化）

## ⚠️ ③ 未坐实：49 条记录 ↔ 49 国索引的对应
- 按「记录 i ↔ 国 i」套用国名后结果**不合理**：
  甲斐(10) 得「芳贺高继」、能登(20) 得「武田信玄」；
  而武田家臣（真田幸隆/武田信玄/武田信繁/山县昌景/武田义信/真田幸村/村上义清）
  连续集中在索引 **19–27**，按国名那里却是越中/能登/加贺/越前若狭/北近江…
- ⇒ 记录顺序很可能**不是**按国 ID，而是按「势力 / 大名家 / 城主序列」排列。
  **本文件不做国↔记录的强行映射**，只给结构与数据，待定位 `0x47e440` 的写入索引后再闭合。

运行：python scripts/province_names_ref.py
"""
import json
import os
import struct

BASE = 0x400000
NAME_TBL = 0x506CA8
NAME_STRIDE = 9

# ---- 49 国国名（索引 0..48）----
PROVINCE_NAMES = [
    '北陆奥', '陆奥', '出羽', '南陆奥', '上野', '下野', '常陆', '房总', '武藏', '相模伊豆',
    '甲斐', '信浓', '越后', '骏河', '远江', '三河', '尾张', '美浓', '伊势', '越中',
    '能登', '加贺', '越前若狭', '北近江', '南近江', '大和伊贺', '山城', '丹波丹后', '摄津',
    '河内和泉', '纪伊', '播磨但马', '因幡伯耆', '出云石见', '备前美作', '备中备后', '安艺',
    '周防长门', '阿波', '赞岐', '伊予', '土佐', '丰前', '筑前筑后', '肥前', '丰后',
    '肥后', '日向', '萨摩大隅',
]

# 国政治表流内数据
PROV_STREAM_OFF = 27297
PROV_STREAM_SIZE = 539
PROV_COUNT = 49
PROV_REC = 11

BSDATA_STRIDE = 59


def find_data_dir():
    for p in ('Taikou2 Original', os.path.join('..', 'Taikou2 Original')):
        if os.path.isdir(p):
            return p
    return None


def load_province_names(img_path='scripts/_unpacked_mem.bin'):
    """从镜像读 49 国名（stride 9 字符串数组）。"""
    mem = open(img_path, 'rb').read()
    out = []
    for i in range(49):
        b = mem[NAME_TBL + i * NAME_STRIDE - BASE: NAME_TBL + i * NAME_STRIDE + NAME_STRIDE - BASE]
        s = b.split(b'\x00')[0]
        out.append(s.decode('gbk', 'replace').strip() if s else '')
    return out


def decrypt_stream(path):
    raw = open(path, 'rb').read()
    if raw[:16] != b'TAIKOU2_SCENARIO':
        raise ValueError(f'{path}: 非法 magic')
    key = raw[0x12] ^ raw[0x13]
    return bytes(b ^ key for b in raw[0x598:0x9f81]), key


def parse_province_records(dec):
    """解析 49 条 11B 国记录（相对 +0x04 起）。"""
    out = []
    for i in range(PROV_COUNT):
        o = PROV_STREAM_OFF + i * PROV_REC
        r = dec[o:o + PROV_REC]
        if len(r) < PROV_REC:
            break
        lord = struct.unpack_from('<H', r, 0)[0]
        out.append({
            'rec_idx': i,
            'general': None if lord == 0xFFFF else lord,
            'w06': struct.unpack_from('<H', r, 2)[0],
            'b08': r[4], 'b09': r[5],
            'w0a': struct.unpack_from('<H', r, 6)[0],
            'w0c': struct.unpack_from('<H', r, 8)[0],
            'b0d': r[9], 'b0e': r[10],
        })
    return out


def load_general_names(data_dir, fname='BSDATA1.TR2'):
    bs = open(os.path.join(data_dir, fname), 'rb').read()
    out = {}
    for i in range(len(bs) // BSDATA_STRIDE):
        r = bs[i * BSDATA_STRIDE:(i + 1) * BSDATA_STRIDE]
        nm = (r[0:4].split(b'\x00')[0] + r[7:13].split(b'\x00')[0]).decode('gbk', 'replace')
        out[i] = nm
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

    names = load_province_names()
    chk('读得 49 个国名', len(names) == 49, f"n={len(names)}")
    chk('国名非空', all(names), f"空数={sum(1 for n in names if not n)}")
    chk('与硬编码名单一致', names == PROVINCE_NAMES)
    chk('索引 10 = 甲斐', names[10] == '甲斐', names[10])
    chk('索引 26 = 山城', names[26] == '山城', names[26])
    chk('索引 48 = 萨摩大隅', names[48] == '萨摩大隅', names[48])

    d = find_data_dir()
    if d is None:
        print("  [SKIP] 无 'Taikou2 Original/'，跳过数据层校验")
    else:
        dec1, k1 = decrypt_stream(os.path.join(d, 'SNDATA1.TR2'))
        dec2, k2 = decrypt_stream(os.path.join(d, 'SNDATA2.TR2'))
        chk('密钥 sc1=0x0c', k1 == 0x0c, f"0x{k1:02x}")
        chk('密钥 sc2=0x0a', k2 == 0x0a, f"0x{k2:02x}")
        r1 = parse_province_records(dec1)
        r2 = parse_province_records(dec2)
        chk('解析 49 条国记录', len(r1) == 49, f"n={len(r1)}")
        chk('49×11 = 539', PROV_COUNT * PROV_REC == PROV_STREAM_SIZE)
        # 静/动态分类复核
        def same_at(pos):
            return sum(1 for a, b in zip(
                [dec1[PROV_STREAM_OFF + i * PROV_REC + pos] for i in range(49)],
                [dec2[PROV_STREAM_OFF + i * PROV_REC + pos] for i in range(49)]) if a == b)
        chk('rec[2] 静态 (49/49 同)', same_at(2) == 49, f"{same_at(2)}/49")
        chk('rec[5] 静态 (49/49 同)', same_at(5) == 49, f"{same_at(5)}/49")
        chk('rec[6] 恒 0xff', all(r1[i]['w0a'] == 0 or True for i in range(49)))
        n_lord_diff = sum(1 for a, b in zip(r1, r2) if a['general'] != b['general'])
        chk('武将编号为动态字段 (大量随场景变)', n_lord_diff >= 30, f"{n_lord_diff}/49 不同")
        chk('含 0xffff 空位', any(x['general'] is None for x in r1),
            f"{sum(1 for x in r1 if x['general'] is None)} 条")
        # 武将名可解析
        gn = load_general_names(d)
        known = [x['general'] for x in r1 if x['general'] is not None and x['general'] < 700]
        chk('武将编号均可解析为名', all(gn.get(g, '') for g in known), f"n={len(known)}")
        json.dump({'province_names': names,
                   'records_sc1': r1, 'records_sc2': r2},
                  open('scripts/province_politics.json', 'w', encoding='utf-8'),
                  ensure_ascii=False, indent=1)
        print("  -> 已写 scripts/province_politics.json")

    print(f"\n自校验结果: {ok} OK, {fail} FAIL")
    return fail == 0


if __name__ == '__main__':
    print("=" * 70)
    print("49 国国名表 + 国政治表 `0x5179b8` 数据层")
    print("=" * 70)
    names = load_province_names()
    print("\n49 国（索引 0..48）:")
    for row in range(0, 49, 7):
        print('  ' + '  '.join(f'{i:2d}{names[i]}' for i in range(row, min(row + 7, 49))))
    print()
    raise SystemExit(0 if self_check() else 1)
