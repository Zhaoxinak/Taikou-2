# -*- coding: utf-8 -*-
r"""
entity_fields_ref.py — 武将实体表字段图 + 「指针→下标」除法魔数总表（续114）

============================================================================
1. 🔑 方法论：定表 stride 的 4 条互补证据链（本项目已全部用过）
============================================================================
| # | 手段 | 实例 | 出处 |
|---|------|------|------|
| 1 | `lea` 系数（`lea r,[r+r*S+G]` = ×(S+1)） | 国情表 ×5 | 续107 |
| 2 | 完整乘减序列（`lea ×3 → shl4 → sub → add G` = ×47） | 武将实体表 ×47 | 续110/111 |
| 3 | **序列化器 `add reg, N`** | 物品表 ×10（`add edi,0xa`） | 续111 |
| 4 | **除法魔数反推** | ÷10 / ÷14 / ÷31 | 续109/111/114 |

**除法魔数有两种 MSVC 变体**（务必分清，否则算错）：

    变体 A（正魔数 M < 2^31）：
        mov eax, M; imul ecx; sar edx, s
        mov eax, edx; shr eax, 0x1f; add edx, eax
        ⇒ result = ((M*n >> 32) >> s) + sign_bit
    变体 B（负魔数 M >= 2^31）：
        mov eax, M; imul ecx; add edx, ecx; sar edx, s
        ⇒ result = ((M*n >> 32) + n) >> s

已确认的三组（本文件 self-test 对 0..9999 逐一验证）：

| 除数 | 魔数 M | sar | 变体 | 对应表 | 基址 | 发现处 |
|------|--------|-----|------|--------|------|--------|
| 10 | `0x66666667` | 2 | **A** | 物品表 | `0x51e1f0` | `0x49c030` / `0x44afb0` |
| 14 | `0x92492493` | 3 | **B** | 49国政治/关系表 | `0x5179b8` | `0x4c2d5b` |
| 31 | `0x84210843` | 4 | **B** | 城/町表 | `0x51eb88` | `0x49af00` |

（47 用第 2 类乘减序列，无除法魔数：`lea ×3 → shl 4 → sub → add 0x519868`。）

**NULL 指针哨兵**：三个「指针→下标」函数对 NULL 都返回 **表条目数**：
物品 200（`0xc8`）、城 200（`0xc8`）。

============================================================================
2. 🆕 `0x49af00` = 城指针 → 城索引（÷31），并查 stride-3 城属性表
============================================================================
```asm
test ecx, ecx
jne  short 0x49af19
mov  edx, 0xc8                              ; NULL ⇒ 索引哨兵 200
and  edx, 0xff
movzx ax, byte [edx + edx*2 + 0x508d98]     ; 0x508d98 + 3*200 = 0x508ff0
ret
0x49af19:
sub  ecx, 0x51eb88      ; ptr - 城表基址
mov  eax, 0x84210843    ; ★ ÷31
imul ecx
add  edx, ecx
sar  edx, 4
...  and edx, 0xff
```
⇒ **城索引 = (ptr − 0x51eb88) / 31**；随后查 **`0x508d98`（stride 3，200 条，
`0x508d98..0x508ff0`）**。

`0x49af50` / `0x49afa0` 是间距 0x50 的两个同构兄弟，分别读 3 字节记录的
**偏移 +1 / +2**（与 `0x49af00` 的 +0 并列）⇒ `0x508d98` 是 **200×3B 城属性表**，
三个字节各由一个 getter 暴露。

✨ **一致性佐证**：NULL 哨兵 200 落到 `0x508d98 + 3*200 = **0x508ff0**`，
正是 id15 效果器 `0x4b3ac0` 分支中 `mov bl, byte[edx + 0x508ff0]` 所用的查表基址
（续82 记「0x4b3b84: 查 `byte[edx + 0x508ff0]`」）—— 两处完全自洽。

============================================================================
3. 🆕 武将实体表（0x519868, stride 47, 370 条）字段图
============================================================================
由 `scripts/_field_map.py 0x519868` 自动生成（**497 个函数**引用该表）。
字段范围 +0x02 .. +0x2e，**恰好落在 stride 47 内**：

| 偏移 | 宽 | 读/写 | 语义（本轮定名） |
|------|----|-------|-----------------|
| `+0x00..+0x0d` | 14B | — | **GBK 姓名**（姓 7B + 名 7B，续103 已破） |
| `+0x02` | word | 读 2 | （与姓名区重叠，实为姓名第 3 字起） |
| `+0x08` | word | 读 2 | — |
| `+0x0b` | byte | 读 1 | — |
| `+0x12` | byte | 写 2 | **= 城属性表[3*城 + 0]**（`0x49af00` 结果） |
| `+0x13` | byte | 写 4 | **= 实体[+0x25]**（基础值副本） |
| `+0x14` | byte | 写 2 | **= 城属性表[3*城 + 1]**（`0x49af50`） |
| `+0x15` | byte | 写 2 | **= 城属性表[3*城 + 2]**（`0x49afa0`） |
| `+0x16` | byte | 写 4 | **= 1**（存活 / 有效标记，init 置 1） |
| `+0x18` | word | 读1写1 | **= 实体[+0x25]**（零扩展为 word） |
| `+0x21` | byte | 读 1 | — |
| `+0x22` | byte | 读 1 | — |
| `+0x24` | byte | **读 9** | **搜索匹配 ID**（见下） |
| `+0x25` | byte | **读 18** | **基础值**（被复制到 `+0x13` / `+0x18`） |
| `+0x26` | word | 读 3 | — |
| `+0x29` | byte | 读 2 | 概率判定输入（`0x4a3df3` 用它做 RNG 判定） |
| `+0x2a` | word | 读 7 | — |
| `+0x2c` | word | 读 13 | **状态字**（低/高字节 bit7 均作屏蔽） |
| `+0x2d` | byte | 读 11 | **bit7 = 无效 / 已故 / 除籍**（`test byte[+0x2d],0x80`） |
| `+0x2e` | byte | 读 2 | bit2 标志（`test byte[+0x2e],4`） |

**初始化 / 重算函数 `0x409340`**（关键，字段语义由此坐实）：
```asm
lea esi, [eax + eax*2]; shl esi, 4; sub esi, eax; add esi, 0x519868  ; ×47
mov  byte [esi + 0x16], 1            ; 有效标记
movzx cx, byte [esi + 0x25]
mov  word [esi + 0x18], cx           ; +0x18 = +0x25 (零扩展)
mov  dl, byte [esi + 0x25]
mov  byte [esi + 0x13], dl           ; +0x13 = +0x25
mov  ecx, 0x51f45f; call 0x49af00; mov byte [esi + 0x12], al
mov  ecx, 0x51f45f; call 0x49af50; mov byte [esi + 0x14], al
mov  ecx, 0x51f45f; call 0x49afa0; mov byte [esi + 0x15], al
```

**全实体搜索循环 `0x413720`**（`+0x24` / `+0x2c` 语义由此坐实）：
```asm
mov  cx, word [eax + 0x2c]
test cl, 0x80 ; jne skip        ; +0x2c 低字节 bit7 → 跳过
test ch, 0x80 ; jne skip        ; +0x2d      bit7 → 跳过（无效/已故）
cmp  byte [eax + 0x24], bl ; je FOUND   ; +0x24 为被匹配的目标 ID
skip: inc edx; add eax, esi; cmp dx, 0x172; jb loop   ; 遍历 370 实体
```

============================================================================
4. 待继续（字段语义未全定）
============================================================================
* `+0x08` / `+0x0b` / `+0x21` / `+0x22` / `+0x26` / `+0x2a` 语义未定
* `+0x25` 究竟是哪种能力（体力？武力？）—— 需结合 MSGX 能力说明表定位
* `+0x2e` bit2 的具体含义
"""
import sys


def s32(v):
    return v - (1 << 32) if v >= (1 << 31) else v


def magic_div_varA(n, M, s):
    """MSVC 正魔数变体: imul; sar edx,s; mov eax,edx; shr eax,0x1f; add edx,eax"""
    hi = (s32(M) * n) >> 32
    r = hi >> s
    return r + ((r >> 31) & 1)


def magic_div_varB(n, M, s):
    """MSVC 负魔数变体: imul; add edx,ecx; sar edx,s"""
    hi = (s32(M) * n) >> 32
    hi = s32((hi + n) & 0xFFFFFFFF)
    return hi >> s


def trunc_div(n, d):
    q = abs(n) // d
    return -q if n < 0 else q


# (除数, 魔数, sar, 变体, 表基址, 发现处)
STRIDE_MAGICS = [
    (10, 0x66666667, 2, 'A', 0x51E1F0, '0x49c030 / 0x44afb0'),
    (14, 0x92492493, 3, 'B', 0x5179B8, '0x4c2d5b'),
    (31, 0x84210843, 4, 'B', 0x51EB88, '0x49af00'),
]

# 无除法魔数、用 lea/shl/sub 乘减序列的表
MULSEQ_STRIDES = [
    (47, 0x519868, 'lea ×3 → shl 4 → sub → add 0x519868', '0x40936b / 0x4da191 / 0x4daf41'),
]

ENTITY = dict(base=0x519868, stride=47, count=370, name_len=14)

# 城属性表（stride 3，200 条）；三个 getter 分别取 +0/+1/+2
CASTLE_ATTR = dict(base=0x508D98, stride=3, count=200,
                   getters=[(0x49AF00, 0), (0x49AF50, 1), (0x49AFA0, 2)],
                   sentinel_addr=0x508FF0)

# 实体字段图（_field_map.py 自动产出）
ENTITY_FIELDS = {
    0x02: ('word', 2, 0, ''),
    0x08: ('word', 2, 0, ''),
    0x0B: ('byte', 1, 0, ''),
    0x12: ('byte', 2, 0, '城属性表[3*城+0]（0x49af00）'),
    0x13: ('byte', 2, 4, '= 实体[+0x25] 副本'),
    0x14: ('byte', 0, 2, '城属性表[3*城+1]（0x49af50）'),
    0x15: ('byte', 0, 2, '城属性表[3*城+2]（0x49afa0）'),
    0x16: ('byte', 0, 4, '=1 有效/存活标记'),
    0x18: ('word', 1, 1, '= 实体[+0x25] 零扩展'),
    0x21: ('byte', 1, 0, ''),
    0x22: ('byte', 1, 0, ''),
    0x24: ('byte', 9, 0, '搜索匹配 ID'),
    0x25: ('byte', 18, 0, '基础值（复制到 +0x13/+0x18）'),
    0x26: ('word', 3, 0, ''),
    0x29: ('byte', 2, 0, '概率判定输入（0x4a3df3）'),
    0x2A: ('word', 7, 0, ''),
    0x2C: ('word', 13, 0, '状态字（低/高字节 bit7 屏蔽）'),
    0x2D: ('byte', 11, 0, 'bit7 = 无效/已故/除籍'),
    0x2E: ('byte', 2, 0, 'bit2 标志'),
}


def _self_test():
    ok = fail = 0

    def chk(name, cond, extra=''):
        nonlocal ok, fail
        if cond:
            ok += 1
        else:
            fail += 1
            print(f"  [FAIL] {name} {extra}")

    # --- 三个除法魔数逐一验证（0..9999）---
    for d, M, s, variant, base, where in STRIDE_MAGICS:
        f = magic_div_varA if variant == 'A' else magic_div_varB
        bad = [n for n in range(10000) if f(n, M, s) != trunc_div(n, d)]
        chk(f'÷{d} 魔数 {M:#x} sar {s} 变体{variant}', not bad, f'错 {len(bad)} 个 e.g. {bad[:5]}')
        chk(f'÷{d} 变体标注正确', (M < (1 << 31)) == (variant == 'A'),
            f'M={M:#x} 与变体{variant}不符')

    # --- 表常量 ---
    for d, M, s, v, base, where in STRIDE_MAGICS:
        chk(f'÷{d} 表基址 {base:#x} 合法', 0x4F0000 <= base < 0x540000)
    chk('实体表 stride 47 / 370 条', ENTITY['stride'] == 47 and ENTITY['count'] == 370)
    # 0x519868 + 47*370 = 0x51DC56 —— 距已知的外交关系矩阵 0x51dc60 仅差 10B，
    # 两者紧邻（中间 10 字节对齐填充），是实体表规模 370×47 的强力旁证。
    chk('实体表末址 = 0x51DC56', ENTITY['base'] + 47 * 370 == 0x51DC56)
    chk('实体表紧邻外交矩阵 0x51dc60（差 10B）', 0x51DC60 - (ENTITY['base'] + 47 * 370) == 10)
    chk('实体姓名 14B', ENTITY['name_len'] == 14)

    # --- 城属性表 ---
    ca = CASTLE_ATTR
    chk('城属性表 stride 3 / 200 条', ca['stride'] == 3 and ca['count'] == 200)
    chk('城属性表末址', ca['base'] + 3 * 200 == 0x508FF0)
    chk('NULL 哨兵落在 0x508ff0', ca['sentinel_addr'] == 0x508FF0)
    chk('三个 getter 偏移 0/1/2', [g[1] for g in ca['getters']] == [0, 1, 2])
    chk('getter 间距 0x50',
        ca['getters'][1][0] - ca['getters'][0][0] == 0x50 and
        ca['getters'][2][0] - ca['getters'][1][0] == 0x50)

    # --- 字段图 ---
    chk('字段图非空', len(ENTITY_FIELDS) >= 15)
    for disp, (w, r, wr, desc) in ENTITY_FIELDS.items():
        chk(f'字段 +{disp:#x} 在 stride 47 内', 0 <= disp < 47, f'disp={disp}')
        chk(f'字段 +{disp:#x} 宽度合法', w in ('byte', 'word'), f'w={w}')
    chk('+0x25 读次数最多(18)', ENTITY_FIELDS[0x25][1] == 18)
    chk('+0x16 只写不读(有效标记)', ENTITY_FIELDS[0x16][1] == 0 and ENTITY_FIELDS[0x16][2] > 0)
    chk('+0x2d bit7 有注释', '无效' in ENTITY_FIELDS[0x2D][3])

    print(f"\nentity_fields_ref self-test: {ok} OK, {fail} FAIL")
    return 1 if fail else 0


if __name__ == '__main__':
    raise SystemExit(_self_test())
