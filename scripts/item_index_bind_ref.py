# -*- coding: utf-8 -*-
"""
item_index_bind_ref.py — 物品表运行期基址/stride + 物品名数组 + 实例级绑定（续111）

回答了续98 遗留的核心问题：「名物身份存于另一结构（未找到）」。
答案：**物品的 identity 就是它在表中的槽号 0..199**，名称与定义是与之平行的数组。

============================================================================
1. 运行期布局（静态反汇编 + 真值数据双证）
============================================================================
    物品表   ITEM_TABLE = 0x51e1f0   stride 10   200 槽   (0x51e1f0..0x51E9C0)
    物品名   ITEM_NAMES = 0x521080   stride 13   200 条   (0x521080..0x521AA8)

两者**平行索引**：第 i 件物品 = 表 0x51e1f0 + 10*i，名 = 0x521080 + 13*i。

静态镜像中这两块**全为 0x00**（BSS 式缓冲），运行期由 SNDATA 序列化器填充 ——
已用 `scripts/_item_name_arr.py` 核实。

----------------------------------------------------------------------------
证据 A：序列化器 0x47ed70（S11 load）/ 0x47ede0（S11 save）
----------------------------------------------------------------------------
    mov  edi, 0x51e1f5        ; 记录游标 = 表基址 0x51e1f0 + 4（跳过 4B vptr）
    mov  ebx, 0x521080        ; 名字数组游标（全程只初始化一次！）
    mov  [esp+0x10], 0xc8     ; 200 次
  loop:
    mov  ebp, 0xd             ; 13
  nl: push ebx; call 0x47d910 ; BYTE 读入 *ebx
    inc  ebx; dec ebp; jne nl ; ⇒ 每轮向 0x521080 写 13 字节名字
    BYTE -> [edi-1] = 0x51e1f4   ; 表 +4
    BYTE -> [edi]   = 0x51e1f5   ; 表 +5
    WORD -> [edi+1] = 0x51e1f6   ; 表 +6
    WORD -> [edi+3] = 0x51e1f8   ; 表 +8
    add  edi, 0xa                ; ★ STRIDE = 10
    dec  count; jne loop
每轮消耗 13+1+1+2+2 = 19 字节 ⇒ 与 SNDATA S11 的 19B/条 记录完全吻合
（200 × 19 = 3800B，流偏移 31810..35610）。

----------------------------------------------------------------------------
证据 B：物品自己的 getItemIndex —— MSVC 除法魔数 ÷10（第三条独立证据）
----------------------------------------------------------------------------
0x49c030（物品 vtable 方法）：
    test ecx, ecx
    jne  short 0x49c043
    mov  edx, 0xc8            ; 指针为 NULL ⇒ 索引哨兵 200
    push edx; call 0x47a530; ret
0x49c043:
    sub  ecx, 0x51e1f0        ; ptr - base
    mov  eax, 0x66666667      ; ★ MSVC 有符号除法魔数 = ÷10
    imul ecx
    sar  edx, 2
    mov  eax, edx; shr eax, 0x1f; add edx, eax
    push edx; call 0x47a530   ; getItemName(index)
    ret
0x44afb0 是同一逻辑的另一实现（`sub eax,0x51e1f0` + `0x66666667` + `sar 2`，
NULL ⇒ 0xc8），说明「取物品索引」是常用操作。

----------------------------------------------------------------------------
证据 C：getItemName = 0x47a530
----------------------------------------------------------------------------
0x47a53e: lea edx, [eax + ecx*4 + 0x521080]
（eax 为 index 的 9 倍时：9i + 4i = 13i ⇒ 0x521080 + 13*index）
两个序列化器 0x47ed70 / 0x47ede0 均直接 `mov ebx, 0x521080`。

============================================================================
2. 🔴 纠偏：物品数是 200，不是 189
============================================================================
续73/80 记「物品定义表 = S11[209:], 189×19B」。实测 **S11 从流偏移 31810 起
共 200 条 ×19B**（= 3800B，止于 35610）；续80 从 32019（= 槽 11）起只取到 189 条，
**漏掉槽 0..10 共 11 件名物**，其中包括茶道最著名的几件：

    slot 0  松本茶碗      slot 1  九十九茄子      slot 2  古天明平蜘蛛
    slot 3  珠光小茄子    slot 4  三日月茶壶      slot 5  松屋茶罐
    slot 6  初花茶罐      slot 7  楢柴茶罐        slot 8  新田茶罐
    slot 9  山井茶罐      slot 10 道成寺茶碗

⇒ **全部 200 个槽都是有名字的实体物品**；不存在「前 11 槽为通用品/保留槽」。

============================================================================
3. 实例级绑定（本文件结论）
============================================================================
    item_index (0..199)  ──┬──> 0x51e1f0 + 10*i   : 数据（cat/val/tier/flag/grp…）
                           └──> 0x521080 + 13*i   : 名称（GBK，12 字符 + NUL）

即：**物品身份 = 槽号**，与续98 所述「名物身份存于角色/存档库存（非本池）」不同 ——
槽号本身就是定义表索引，不需要额外的 def-index 字段。
续98 观察到的 `+6 OWNER_KEY` / `+8 FLAGS(CAT/SUB/owned)` 是**实例化之后**被写入
的运行时语义（与定义载入共用同一 10B 结构，载入的定义值随后被实例值覆盖）。

    流记录(19B) → 运行期写入：
      name[0..12]  -> 0x521080 + 13*i
      byte[13] cat -> 表 +4
      byte[14] val -> 表 +5
      byte[15] tier, byte[16] flag -> 表 +6 (word)
      byte[17] grp, byte[18] pad   -> 表 +8 (word)

============================================================================
4. 与既有产物的关系
============================================================================
* `item_table_ref.py` 的 189 条是 200 条的子集（缺槽 0..10），字段解析（cat/val/
  tier/flag/grp）仍然正确，仅**起点偏移与条数需更正**（31810 / 200）。
* `item_pool_bind_ref.py`（续98）的 27→8 类目归并、getValue 公式、副池(0x517728)
  结论不受影响；但「物品池 = 0x51e1f0」应理解为 **= 物品定义表本身**。
"""
import os
import struct

STREAM_START = 0x598
S11_STREAM_OFF = 31810          # 200 x 19B
S11_REC = 19
S11_COUNT = 200                 # ★ 不是 189

ITEM_TABLE = 0x51e1f0
ITEM_TABLE_STRIDE = 10
ITEM_NAMES = 0x521080
ITEM_NAME_STRIDE = 13
ITEM_INDEX_SENTINEL = 0xc8      # NULL 指针 -> 索引 200

# MSVC signed-division magic used by getItemIndex: 0x66666667 with `sar 2` == /10
DIV_MAGIC = 0x66666667
DIV_SHIFT = 2
DIV_BY = 10                     # == ITEM_TABLE_STRIDE

# 已知的 11 件「被续80 漏掉」的槽 0..10（实测值，用于自校验）
SLOTS_0_10 = [
    ('松本茶碗', 1, 100), ('九十九茄子', 3, 155), ('古天明平蜘蛛', 5, 105),
    ('珠光小茄子', 3, 100), ('三日月茶壶', 4, 95), ('松屋茶罐', 3, 105),
    ('初花茶罐', 3, 80), ('楢柴茶罐', 3, 85), ('新田茶罐', 3, 90),
    ('山井茶罐', 3, 100), ('道成寺茶碗', 0, 100),
]


def find_data_dir():
    for p in ('Taikou2 Original', os.path.join('..', 'Taikou2 Original')):
        if os.path.isdir(p):
            return p
    return None


def decrypt_stream(path):
    raw = open(path, 'rb').read()
    key = raw[0x12] ^ raw[0x13]
    return bytes(b ^ key for b in raw[STREAM_START:0x9f81])


def parse_items(dec):
    """Parse all 200 S11 records (NOT just the 189 that 续80 found)."""
    out = []
    for i in range(S11_COUNT):
        o = S11_STREAM_OFF + i * S11_REC
        r = dec[o:o + S11_REC]
        z = r.find(b'\x00')
        name = r[:z].decode('gbk', 'replace') if z > 0 else '?'
        out.append({'idx': i, 'name': name, 'cat': r[13], 'val': r[14],
                    'tier': r[15], 'flag': r[16], 'grp': r[17], 'pad': r[18]})
    return out


def name_addr(idx):
    return ITEM_NAMES + idx * ITEM_NAME_STRIDE


def table_addr(idx):
    return ITEM_TABLE + idx * ITEM_TABLE_STRIDE


def index_of_ptr(ptr):
    """Mirror of getItemIndex (0x49c030 / 0x44afb0)."""
    if ptr == 0:
        return ITEM_INDEX_SENTINEL
    return (ptr - ITEM_TABLE) // ITEM_TABLE_STRIDE


def _self_test():
    ok = fail = 0

    def chk(name, cond, extra=''):
        nonlocal ok, fail
        if cond:
            ok += 1
        else:
            fail += 1
            print(f"  [FAIL] {name} {extra}")

    # --- structural constants ---
    chk('表 stride == 除法除数', ITEM_TABLE_STRIDE == DIV_BY)
    chk('除法魔数为 MSVC ÷10', DIV_MAGIC == 0x66666667 and DIV_SHIFT == 2)
    chk('名 stride 13 (12 字符+NUL)', ITEM_NAME_STRIDE == 13)
    chk('槽数 200（非 189）', S11_COUNT == 200)
    chk('S11 字节数 = 200*19', S11_COUNT * S11_REC == 3800)
    chk('S11 流尾 = 35610', S11_STREAM_OFF + 3800 == 35610)
    chk('续80 起点 = 槽11', 32019 == S11_STREAM_OFF + 11 * S11_REC)

    # --- getItemIndex round-trip ---
    chk('index_of_ptr(0) == 哨兵 200', index_of_ptr(0) == 200)
    for i in (0, 1, 11, 100, 199):
        chk(f'index_of_ptr 往返 {i}', index_of_ptr(table_addr(i)) == i)
    chk('名表末地址', name_addr(199) + 13 == 0x521AA8)
    chk('表末地址', table_addr(199) + 10 == 0x51E9C0)

    # --- real data ---
    d = find_data_dir()
    if d is None:
        print("  [SKIP] 未找到 'Taikou2 Original/'，跳过真值校验")
    else:
        dec = decrypt_stream(os.path.join(d, 'SNDATA1.TR2'))
        items = parse_items(dec)
        chk('解析出 200 条', len(items) == 200, f'got {len(items)}')
        # 槽 0..10 必须是具名实体（续80 曾把它们当保留槽）
        for i, (nm, cat, val) in enumerate(SLOTS_0_10):
            it = items[i]
            chk(f'slot{i} 名 = {nm}', it['name'] == nm, f"got {it['name']!r}")
            chk(f'slot{i} cat/val', (it['cat'], it['val']) == (cat, val),
                f"got {(it['cat'], it['val'])}")
        # 全部 200 条都应有非空名字
        empty = [it['idx'] for it in items if not it['name'] or it['name'] == '?']
        chk('200 条全部具名', not empty, f'空名槽: {empty[:12]}')
        # cat 合法范围 0..26
        bad = [it['idx'] for it in items if not (0 <= it['cat'] <= 26)]
        chk('cat ∈ 0..26', not bad, f'越界: {bad[:12]}')
        print(f"  数据: 200 件，cat 覆盖 {sorted({it['cat'] for it in items})}")
        ex = ', '.join(f"{it['idx']}:{it['name']}" for it in items[:6])
        print(f"  前 6 件: {ex}")

    print(f"\nitem_index_bind_ref self-test: {ok} OK, {fail} FAIL")
    return 1 if fail else 0


if __name__ == '__main__':
    raise SystemExit(_self_test())
