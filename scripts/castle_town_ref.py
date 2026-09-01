
# <auto: portable root (injected by _fix_win_paths.py)>
import os as _os
def _find_root(_p):
    for _ in range(8):
        if _os.path.isdir(_os.path.join(_p, 'scripts')) and _os.path.isfile(_os.path.join(_p, 'project.godot')):
            return _p
        _p = _os.path.dirname(_p)
    return _p
_ROOT = _find_root(_os.path.dirname(_os.path.abspath(__file__)))
# </auto: portable root>
import os
_HERE = os.path.dirname(os.path.abspath(__file__))
"""
castle_town_ref.py — 城/町表数据层：SNDATA XOR 流 21852（200 × 26B → `0x51eb88` stride 31）

来源：2026-08-29 续77 逆向
  - 流：偏移 **21852**，长 **5200B = 200 × 26B**（对应 §5.1 第 3 段 `0x47e130`）
  - 目标：`0x51eb88`，stride 31，200 条 = **92 城 + 108 町**
  - 解密：key = 文件[0x12]^[0x13]（sc1=0x0c / sc2=0x0a）

## ✅ 已坐实字段（真实数据验证）
| rec | 语义 | 验证 |
|---|---|---|
| `byte17` | **所属国索引 0..48** | 按值分组，城名地理完全吻合：踯躅崎→甲斐(10)、春日山→越后(12)、骏府→骏河(13)、滨松→远江(14)、冈崎→三河(15)、清洲→尾张(16)、稻叶山→美浓(17)、金泽→加贺(21)、一乘谷→越前若狭(22) |
| `byte19` | **城主武将号** | 三户→前田利家、登米→浅野长政、鹤冈→藤堂高秀、二本松→织田信忠、须贺川→中野义时（BSDATA 查名，均真实武将）|
| `byte14` | **在城武将号**（255 = 不在城） | 106/200 与 byte19 相同，95/200 为 255；同国内不同城可有不同值 |
| `byte12..13` | 恒 `0xff 0xff`（哨兵/未使用） | 200/200 |
| `byte16` | 另一武将编号（语义待定） | 值域 2..255，154 个不同值，46 条为 255；含织田信长(13)、木下藤吉郎(16) |
| `byte22/23/24` | 0..250 / 0..200 / 0..100（疑农商/生产率/民心） | byte24 值域 0..100 且 top=90/80/70，形态最像百分比 |

## ✅ 完整字段映射（续78 终解，由 `0x47e130` 反汇编 + 数据双重确认）
`0x47e130`：`esi` 起始 **`0x51eb8c` = `0x51eb88 + 4`**，`ebx=0xc8`(200)，`add esi,0x1f`(stride 31)。
**17 次读取 = 26B/条**（初数 16 次得 25B 是漏了 `0x47e1a4 → [esi+4]`，续78 已补正）。
宽度实证：`0x47d910`→`0x47da10` 读 1B；`0x47d930`→`0x47da50` 读 2B。

| 流字节 | 宽 | 记录偏移 | 语义 |
|---|---|---|---|
| `[0..1]` | 2 | `+0x00` | 武将号 → 查 `0x519868`(×47) 存**指针** |
| `[2]` | 1 | `+0x04` | 城索引 → 查 `0x51eb88`(×31) 存**指针** |
| `[3]` | 1 | `+0x08` | 未知 |
| `[4]` | 1 | `+0x09` | 未知 |
| `[5..6]` | 2 | `+0x0a` | 仅 19 个不同武将名、多重复 ⇒ **非城主**，待定 |
| `[7]` | 1 | `+0x0c` | 农商系 |
| `[8]` | 1 | `+0x0d` | 次级 |
| `[9]` | 1 | `+0x0e` | **民心**（0..200）|
| `[10]` | 1 | `+0x0f` | 生产率 |
| `[11..12]` | 2 | `+0x10` | 军粮——剧本内恒 `0xFF05` **未设置** |
| `[13..14]` | 2 | `+0x12` | 米 |
| `[15..16]` | 2 | `+0x14` | 资金 |
| `[17..18]` | 2 | `+0x16` | **所属国索引**（本文件 `province` = 流[17]，低字节）|
| `[19..20]` | 2 | `+0x18` | **城主武将号**（本文件 `lord` = 流[19]，低字节）|
| `[21]` | 1 | `+0x1a` | 次级民情 |
| `[22..23]` | 2 | `+0x1b` | 城种（&7）|
| `[24..25]` | 2 | `+0x1d` | 未知 |

## 🔴 对续70 的纠偏
续70 由任命代码 `0x49a990` 推「`word[城+0x0a]` = 城主」。实测：
`+0x0a` 191/200 <370 但**仅 19 个不同武将名**（大量「林通胜」）；
**`+0x18` 199/200 <370、105 个不同武将名**且逐个合理。
⇒ **真正城主在 `+0x18`**；`0x49a990` 写的 `+0x0a` 是另一语义，待核。
（另一佐证：`+0x10` 军粮在剧本内恒 `0xFF05` 未设置 ⇒ 军粮/米/资金本就不由剧本初始化。）

运行：python scripts/castle_town_ref.py
"""
import json
import os
import struct

STREAM_START = 0x598
CASTLE_OFF = 21852
CASTLE_COUNT = 200
CASTLE_REC = 26
N_CASTLE = 92          # 0..91 城，92..199 町
NAME_TBL = 0x506CA8
NAME_STRIDE = 9
BASE = 0x400000
BSDATA_STRIDE = 59


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


def load_names(img=_ROOT + '/scripts/_unpacked_mem.bin'):
    mem = open(img, 'rb').read()
    out = []
    for i in range(300):
        b = mem[NAME_TBL + i * NAME_STRIDE - BASE:
                NAME_TBL + i * NAME_STRIDE + NAME_STRIDE - BASE]
        s = b.split(b'\x00')[0]
        out.append(s.decode('gbk', 'replace').strip() if s else '')
    return out


def load_generals(d, fname='BSDATA1.TR2'):
    bs = open(os.path.join(d, fname), 'rb').read()
    out = {}
    for i in range(len(bs) // BSDATA_STRIDE):
        r = bs[i * BSDATA_STRIDE:(i + 1) * BSDATA_STRIDE]
        out[i] = (r[0:4].split(b'\x00')[0] + r[7:13].split(b'\x00')[0]).decode('gbk', 'replace')
    return out


def parse(dec, names, gens):
    out = []
    for i in range(CASTLE_COUNT):
        r = dec[CASTLE_OFF + i * CASTLE_REC: CASTLE_OFF + (i + 1) * CASTLE_REC]
        if len(r) < CASTLE_REC:
            break
        kind = '城' if i < N_CASTLE else '町'
        nm = names[88 + i] if 88 + i < len(names) else ''
        def g(v):
            return None if v == 255 else (gens.get(v) if v < 700 else None)
        out.append({
            'idx': i, 'kind': kind, 'name': nm,
            'province': r[17],
            'lord': r[19], 'lord_name': g(r[19]),
            'resident': None if r[14] == 255 else r[14],
            'resident_name': g(r[14]),
            'general2': None if r[16] == 255 else r[16],
            'general2_name': g(r[16]),
            'b18': r[18], 'b21': r[21],
            'b22': r[22], 'b23': r[23], 'b24': r[24], 'b25': r[25],
        })
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
    dec, key = decrypt_stream(os.path.join(d, 'SNDATA1.TR2'))
    names = load_names()
    gens = load_generals(d)
    chk('密钥 sc1=0x0c', key == 0x0c, f"0x{key:02x}")
    rows = parse(dec, names, gens)
    chk('解析 200 条', len(rows) == CASTLE_COUNT, f"n={len(rows)}")
    chk('92 城 + 108 町', sum(1 for r in rows if r['kind'] == '城') == 92)

    recs = [dec[CASTLE_OFF + i * CASTLE_REC: CASTLE_OFF + (i + 1) * CASTLE_REC]
            for i in range(CASTLE_COUNT)]
    chk('byte12..13 恒 0xff',
        all(r[12] == 255 and r[13] == 255 for r in recs))
    chk('byte17 ∈ 0..48 且 49 个不同值',
        all(0 <= r[17] <= 48 for r in recs) and len(set(r[17] for r in recs)) == 49,
        f"distinct={len(set(r[17] for r in recs))}")
    chk('byte19 城主可解析为名 (>=190 条)',
        sum(1 for r in rows if r['lord_name']) >= 190,
        f"{sum(1 for r in rows if r['lord_name'])}/200")
    chk('byte14 在城标记：存在 255',
        any(r[14] == 255 for r in recs),
        f"{sum(1 for r in recs if r[14] == 255)} 条为 255")
    chk('byte14 与 byte19 一致 >=100 条',
        sum(1 for r in recs if r[14] == r[19]) >= 100,
        f"{sum(1 for r in recs if r[14] == r[19])}/200")

    # 地理抽查
    by = {r['name']: r for r in rows}
    for cname, prov in (('踯躅崎', 10), ('春日山', 12), ('骏府', 13),
                        ('滨松', 14), ('冈崎', 15), ('清洲', 16),
                        ('稻叶山', 17), ('金泽', 21)):
        got = by.get(cname)
        chk(f'{cname} 所属国 == {prov}', got is not None and got['province'] == prov,
            f"got={got['province'] if got else '?'}")

    json.dump(rows, open(os.path.join(_HERE, r'castle_town.json'), 'w', encoding='utf-8'),
              ensure_ascii=False, indent=1)
    print("  -> 已写 scripts/castle_town.json")
    print(f"\n自校验结果: {ok} OK, {fail} FAIL")
    return fail == 0


if __name__ == '__main__':
    print("=" * 70)
    print("城/町表 (流 21852, 200 × 26B → 0x51eb88 stride 31)")
    print("=" * 70)
    d = find_data_dir()
    if d:
        dec, key = decrypt_stream(os.path.join(d, 'SNDATA1.TR2'))
        names = load_names()
        gens = load_generals(d)
        rows = parse(dec, names, gens)
        print(f"\nkey=0x{key:02x}  共 {len(rows)} 条\n")
        print("   idx 种  名称      国  城主           在城")
        for r in rows[:22]:
            print(f"  {r['idx']:4d} {r['kind']}  {r['name']:8s} {r['province']:2d}  "
                  f"{str(r['lord_name']):14s} {str(r['resident_name'])}")
    print()
    raise SystemExit(0 if self_check() else 1)
