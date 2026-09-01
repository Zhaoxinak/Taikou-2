#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
savedata_loadflow_ref.py -- 续208：P0「49B 记录 43B payload」= 张冠李戴，实为 SAVEDATA 槽元数据
================================================================================
🔴 重大改判（推翻续158→续189 一整条 P0 支线的前提）

长期挂在 P0 的最大敞口是「SNDATA 833×49B 记录的 43B payload 逐字段语义」。本轮证明：
**那条支线的对象根本不存在**——`0x47d890`(`offset = idx*49 + 0x10`) 访问的不是 SNDATA 的
833 条剧本记录，而是 **SAVEDATA.TR2 的 8 条存档槽元数据**；`0x4e8600` 主循环不是「记录
分派管线」，而是**「读取进度」存档槽 UI 流程**。

--------------------------------------------------------------------------------
【铁证 1】入口错位 —— 续206 崩溃的真因
    0x4e8600  sub esp,0xc                 ← 真·函数入口
    0x4e8603  push esi
    0x4e8604  call 0x480240               ← 取槽号 → esi
    0x4e860b  cmp si,-1  ; je 0x4e8774    ← -1 = 用户取消
    0x4e8615..0x4e8624  lea/push ×4       ← 备 4 个实参
    0x4e8625  call 0x47fc60               ← ⚠️ 这是一条 call 指令，不是函数入口！
  续206 与本轮之前的 boot 全部从 `0x4e8625` 起跑 ⇒ 带着垃圾 esi/垃圾栈参进扇出，
  于是 `0x47fcad  mov word ptr [edx], ax`（edx=[esp+0xdc]=arg2）写垃圾指针 → 未映射写。
  ⇒ 旧诊断「因游戏表未初始化」**错**；真因是**起跑地址取在循环体中段**。

【铁证 2】读的是 SAVEDATA，不是 SNDATA
    0x47fc60: push 0 ; push 2 ; lea ecx,[esp+0x3c] ; call 0x47d720
    0x47d720(mode=word[esp+4], arg): mode>=2 → 0x47d780
                                     mode==0 → esi=0x5095a0  'F:SNDATA1.TR2'
                                     mode!=0 → esi=0x5095b0  'F:SNDATA2.TR2'
    0x47d780: strcpy(local, 0x509590)   ; 0x509590 = 'A:SAVEDATA.TR2'
  扇出用 **mode=2** ⇒ 走 0x47d780 ⇒ 目标文件 = **A:SAVEDATA.TR2**。

【铁证 3】几何精确闭合
    0x47d890: off = idx*49 + 0x10 ; read 0x31(49)
    SAVEDATA.TR2: 328088 B = 0x198 + 8 × 40960   (整除 8.0000)
    槽元数据区 = 0x10 .. 0x197，恰 8 × 49 = 392 = 0x188，末端 0x10+392 = 0x198
  ⇒ **0x198 正是续199 的「场景块起点」**；两套几何在同一字节上对接，无缝。

【铁证 4】字段语义 = 续199 已定名的槽元数据（本轮由代码路径独立坐实）
    *arg2 = word[rec+0x00]  → 年
    *arg3 = word[rec+0x02]  → 月
    *arg4 = word[rec+0x04]  → 日
    strcpy(0x522c88, rec+0x06)  13B → 主角名
    strcpy(0x522c60, rec+0x13)  13B → 所在国
    strcpy(0x522c70, rec+0x20)  17B → 所在地+身分
    6 + 13 + 13 + 17 = 49  ← 完美平铺
  实测 slot0 = 1560年5月20日 / 木下藤吉郎 / 尾张国 / 清洲城步兵头（与续199 交叉验证一致）。
  ⇒ 续164「3 重叠视图长 43/30/17」的「重叠」是**payload 无 NUL 时的溢读假象**；真实是
    3 个定长串槽（13/13/17），空槽全 0 时长度为 0。

【铁证 5】UI 语义（推翻续160 的「匹配器/谓词」标签）
    dword[0x509684] = 0x5096d0 ⇒ **不是 16-bit 游标**，是槽选择 UI 的字符串表指针
      0x5096d0 = '读取哪个进度？' / '保存在哪个进度？' / '----年--月--日  ----------'
    0x480240 = 0x47fe00(dword[0x509684], 0)  → 槽选择器，返回槽号 或 -1(取消)
    头三字全 0 → 0x47b160(0x50d820) '这个进度无法使用。'   ← 空槽提示（实测 slot1..7 全 0）
    否则       → 0x47b390(0x50d834) '读取游戏进度，\\n可以吗？' ← 是/否确认框（非「类型匹配器」）
    → 0x47fb80(slot) 真正读档（内部 call 0x47f350 剧本解码器）
    → 读 0x5205fe 画面模式 → 3 路载入对应资源簇（读档后重建画面）
  ⇒ 续160「匹配器+谓词+值开关分派 833 条记录」应改述为
    **「空槽判定 + 读档确认框 + 读档 + 按画面模式重载资源」**（续161 已预警此标签待审，此处结案）。

【铁证 6】「833 条 payload 是二进制填充」= 在读 XOR 加密的 0x00/0xFF
    40856 = 16 + 833×49 + 23 的整除只是**数字巧合**。用 SNDATA 自身密钥
    key = byte[0x12] ^ byte[0x13]（续202）：sc1 key=0x0c、sc2 key=0x0a。
    续189 报的「TOP 型 0x0c×249 / 0xf3×111 填充」与本轮实测 word TOP 值
      sc1: 0x0C0C(=3084) / 0xF3F3(=62451)      ← 0x0c = 0x00^0x0c, 0xf3 = 0xff^0x0c
      sc2: 0x0A0A(=2570) / 0xF5F5(=62965)      ← 0x0a = 0x00^0x0a, 0xf5 = 0xff^0x0a
    **完全等于「明文 0x00 / 0xFF 经单字节 XOR」**。
  ⇒ 续176/188/189 的「171 型字段指纹 / type=0x01 的 43 布尔 / benum 索引」全部建立在
    加密字节上，**不是游戏数据**。SNDATA 的真实剧本数据是 0x598 起的解密流，由
    `0x47f350` 的 18 个子解码器写入 S0..S17 游戏表（续165/续202 已破）。

--------------------------------------------------------------------------------
⇒ **P0 结论：该敞口应关闭为「证伪/改判」，而非继续追字段名。**
   ① 49B 结构真身 = SAVEDATA 8 槽元数据，字段已全部定名（本轮 + 续199 双证）；
   ② SNDATA 剧本数据入口 = 0x598 解密流 → 0x47f350 → S0..S17（已破）；
   ③ 「全 833 条 idx→资源表」这一待办**目标不成立**：资源不按记录选，而是读档后
      按全局画面模式 0x5205fe 三路重载（续161/163/178 已破的 3 层资源表即全部答案）。
"""
import os as _os
def _find_root(_p):
    for _ in range(8):
        if _os.path.isdir(_os.path.join(_p, 'scripts')) and _os.path.isfile(_os.path.join(_p, 'project.godot')):
            return _p
        _p = _os.path.dirname(_p)
    return _p
_ROOT = _find_root(_os.path.dirname(_os.path.abspath(__file__)))

import os, struct, json
from collections import Counter

BASE = 0x400000
BIN = os.path.join(_ROOT, 'scripts', '_unpacked_mem.bin')
ORIG = os.path.join(_ROOT, 'Taikou2 Original')

IMG = open(BIN, 'rb').read()


def rd(va, n):
    return IMG[va - BASE: va - BASE + n]


def rd32(va):
    return struct.unpack_from('<I', IMG, va - BASE)[0]


def cstr(va, n=32):
    b = rd(va, n)
    k = b.find(b'\x00')
    return b[:k if k >= 0 else n]


def gbk(va, n=64):
    b = cstr(va, n)
    try:
        return b.decode('gbk')
    except Exception:
        return b.decode('latin-1', 'replace')


# ---------------------------------------------------------------- 槽元数据布局
SLOT_META_BASE = 0x10
SLOT_META_SIZE = 49
SLOT_COUNT = 8
SLOT_DATA_BASE = 0x198
SLOT_DATA_SIZE = 40960

FIELDS = [
    ('年',           'word', 0x00, 2),
    ('月',           'word', 0x02, 2),
    ('日',           'word', 0x04, 2),
    ('主角名',       'str',  0x06, 13),
    ('所在国',       'str',  0x13, 13),
    ('所在地+身分',  'str',  0x20, 17),
]


def decode_slot(rec):
    out = {}
    for name, kind, off, ln in FIELDS:
        if kind == 'word':
            out[name] = struct.unpack_from('<H', rec, off)[0]
        else:
            b = rec[off:off + ln]
            k = b.find(b'\x00')
            body = b[:k if k >= 0 else ln]
            try:
                out[name] = body.decode('gbk')
            except Exception:
                out[name] = body.decode('latin-1', 'replace')
    return out


def main():
    tests = []

    def T(name, ok, detail=''):
        tests.append((name, bool(ok), detail))
        print('  %s %s%s' % ('PASS' if ok else 'FAIL', name, ('  — ' + detail) if detail else ''))

    print('=' * 78)
    print('A. 代码路径：入口错位 + 目标文件 = SAVEDATA')
    print('=' * 78)
    # A1 0x4e8600 真入口（sub esp,0xc）
    T('0x4e8600 = 函数入口 (sub esp,0xc)', rd(0x4e8600, 3) == b'\x83\xec\x0c',
      rd(0x4e8600, 3).hex())
    # A2 0x4e8604 call 0x480240
    b = rd(0x4e8604, 5)
    tgt = 0x4e8604 + 5 + struct.unpack('<i', b[1:5])[0]
    T('0x4e8604 = call 0x480240 (取槽号)', b[0] == 0xe8 and tgt == 0x480240, hex(tgt))
    # A3 cmp si,-1
    T('0x4e860b = cmp si,-1 (取消哨兵)', rd(0x4e860b, 4) == b'\x66\x83\xfe\xff',
      rd(0x4e860b, 4).hex())
    # A4 0x4e8625 是 call 指令而非入口 —— 续206 崩溃真因
    b = rd(0x4e8625, 5)
    tgt = 0x4e8625 + 5 + struct.unpack('<i', b[1:5])[0]
    T('0x4e8625 是 call 0x47fc60 指令(非函数入口) ⇒ 续206 起跑地址错',
      b[0] == 0xe8 and tgt == 0x47fc60, hex(tgt))
    # A5 0x47fc60 用 mode=2 调 0x47d720（push 0; push 2）
    T('0x47fc60 以 mode=2 调 0x47d720 (push 0; push 2)',
      rd(0x47fc66, 4) == b'\x6a\x00\x6a\x02', rd(0x47fc66, 4).hex())
    # A6 文件名串
    T("0x5095a0 == 'F:SNDATA1.TR2'", cstr(0x5095a0) == b'F:SNDATA1.TR2', repr(cstr(0x5095a0)))
    T("0x5095b0 == 'F:SNDATA2.TR2'", cstr(0x5095b0) == b'F:SNDATA2.TR2', repr(cstr(0x5095b0)))
    T("0x509590 == 'A:SAVEDATA.TR2' (mode>=2 目标)",
      cstr(0x509590) == b'A:SAVEDATA.TR2', repr(cstr(0x509590)))
    # A7 0x47d780 从 0x509590 取名
    T('0x47d780 strcpy(local, 0x509590)', rd(0x47d787, 5) == b'\x68\x90\x95\x50\x00',
      rd(0x47d787, 5).hex())
    # A8 0x47d890 偏移公式 idx*49+0x10 且读 0x31
    T('0x47d890: lea edx,[ecx+eax+0x10] (idx*49+0x10)',
      rd(0x47d8a4, 4) == b'\x8d\x54\x01\x10', rd(0x47d8a4, 4).hex())
    T('0x47d890: push 0x31 (读 49 字节)', rd(0x47d8b6, 2) == b'\x6a\x31', rd(0x47d8b6, 2).hex())

    print()
    print('=' * 78)
    print('B. UI 语义：0x509684 是字符串表指针，不是 16-bit 游标')
    print('=' * 78)
    p = rd32(0x509684)
    T('dword[0x509684] == 0x5096d0 (指针,非游标)', p == 0x5096d0, hex(p))
    s0 = gbk(0x5096d0)
    T('0x5096d0 = 槽选择提示串', '进度' in s0, s0)
    s1 = gbk(0x50d820)
    T("0x50d820 = '这个进度无法使用。' (空槽提示)", '无法使用' in s1, s1)
    s2 = gbk(0x50d834)
    T("0x50d834 = '读取游戏进度，可以吗？' (确认框, 非类型模板)", '读取游戏进度' in s2, repr(s2))

    print()
    print('=' * 78)
    print('C. SAVEDATA.TR2 几何 + 8 槽元数据字段解码')
    print('=' * 78)
    sp = os.path.join(ORIG, 'SAVEDATA.TR2')
    sav = open(sp, 'rb').read()
    T("magic == 'TAIKOU2_SAVEFILE'", sav[:16] == b'TAIKOU2_SAVEFILE', repr(sav[:16]))
    T('槽元数据区末端 0x10+8*49 == 0x198 (=续199 场景块起点)',
      SLOT_META_BASE + SLOT_COUNT * SLOT_META_SIZE == SLOT_DATA_BASE,
      hex(SLOT_META_BASE + SLOT_COUNT * SLOT_META_SIZE))
    T('size == 0x198 + 8*40960',
      len(sav) == SLOT_DATA_BASE + SLOT_COUNT * SLOT_DATA_SIZE,
      '%d vs %d' % (len(sav), SLOT_DATA_BASE + SLOT_COUNT * SLOT_DATA_SIZE))
    T('49B 字段平铺无空洞 (6+13+13+17)',
      sum(f[3] for f in FIELDS) == SLOT_META_SIZE, str(sum(f[3] for f in FIELDS)))

    slots = []
    for i in range(SLOT_COUNT):
        o = SLOT_META_BASE + i * SLOT_META_SIZE
        d = decode_slot(sav[o: o + SLOT_META_SIZE])
        d['slot'] = i
        d['offset'] = o
        slots.append(d)
        print('    slot%d @0x%04x  %s年%s月%s日 | %-12s | %-10s | %s'
              % (i, o, d['年'], d['月'], d['日'], d['主角名'], d['所在国'], d['所在地+身分']))

    s = slots[0]
    T('slot0 = 1560年5月20日 (续199 交叉验证)',
      (s['年'], s['月'], s['日']) == (1560, 5, 20), '%s/%s/%s' % (s['年'], s['月'], s['日']))
    T('slot0 主角名 == 木下藤吉郎', s['主角名'] == '木下藤吉郎', s['主角名'])
    T('slot0 所在国 == 尾张国', s['所在国'] == '尾张国', s['所在国'])
    T('slot0 所在地+身分 == 清洲城步兵头', s['所在地+身分'] == '清洲城步兵头', s['所在地+身分'])
    empt = [x['slot'] for x in slots[1:] if (x['年'], x['月'], x['日']) == (0, 0, 0)]
    T('slot1..7 头三字全 0 ⇒ 命中 0x4e862d 空槽分支', empt == [1, 2, 3, 4, 5, 6, 7], str(empt))

    print()
    print('=' * 78)
    print("D. 证伪「SNDATA 833×49B 记录」：那些 payload 字节 = XOR 加密的 0x00/0xFF")
    print('=' * 78)
    xor_report = {}
    for fn, tag in (('SNDATA1.TR2', 'sc1'), ('SNDATA2.TR2', 'sc2')):
        p2 = os.path.join(ORIG, fn)
        raw = open(p2, 'rb').read()
        key = raw[0x12] ^ raw[0x13]                     # 续202
        enc = raw[0x598:len(raw) - 23]                  # 加密流（尾 23B 除外）
        c = Counter(enc)
        top = c.most_common(3)
        # 833×49 伪切分下的 word 直方图 TOP（复现续189 的「填充型」）
        nrec = (len(raw) - 16 - 23) // 49
        wA = Counter(struct.unpack_from('<H', raw, 16 + i * 49)[0] for i in range(nrec))
        wtop = wA.most_common(2)
        exp1 = key | (key << 8)
        exp2 = (key ^ 0xff) | ((key ^ 0xff) << 8)
        print('  %s: key=0x%02x  加密流最常见字节 %s' %
              (fn, key, [('0x%02x' % b, n) for b, n in top]))
        print('        伪切分 833 条 wordA TOP2 = %s ；期望 0x%04x / 0x%04x' %
              ([hex(v) for v, _ in wtop], exp1, exp2))
        T('%s: 加密流最常见字节 == key(=明文0x00)' % tag, top[0][0] == key,
          '0x%02x' % top[0][0])
        T('%s: 次常见字节 == key^0xff(=明文0xFF)' % tag, top[1][0] == (key ^ 0xff),
          '0x%02x' % top[1][0])
        T('%s: 伪切分 wordA TOP1 == key|key<<8 (续189「填充型」真身)' % tag,
          wtop[0][0] == exp1, hex(wtop[0][0]))
        T('%s: 伪切分 wordA TOP2 == (key^0xff) 重复 (续189 第二填充型)' % tag,
          wtop[1][0] == exp2, hex(wtop[1][0]))
        xor_report[fn] = {
            'key': key, 'stream_top_bytes': [[b, n] for b, n in top],
            'pseudo_833_wordA_top2': [[v, n] for v, n in wtop],
            'expect_word_fill': [exp1, exp2],
        }
        # 数字巧合本身也记录下来
        T('%s: 40856 == 16 + 833*49 + 23 (整除巧合成立但非结构)' % tag,
          len(raw) == 16 + 833 * 49 + 23, str(len(raw)))

    print()
    out = os.path.join(_ROOT, 'scripts', 'savedata_loadflow.json')
    with open(out, 'w', encoding='utf-8') as f:
        json.dump({
            'verdict': 'P0「SNDATA 833×49B 记录 43B payload」= 张冠李戴；49B 真身 = SAVEDATA 8 槽元数据',
            'entry_point_correction': {
                'wrong': '0x4e8625 (实为 call 0x47fc60 指令)',
                'right': '0x4e8600 (sub esp,0xc)',
                'consequence': '续206 的 0x47fcad 未映射写 = 垃圾栈参，非游戏表未初始化',
            },
            'target_file': {'mode0': 'F:SNDATA1.TR2', 'mode1': 'F:SNDATA2.TR2',
                            'mode>=2 (扇出实际用)': 'A:SAVEDATA.TR2'},
            'savedata_geometry': {
                'magic': 'TAIKOU2_SAVEFILE', 'slot_meta_base': SLOT_META_BASE,
                'slot_meta_size': SLOT_META_SIZE, 'slot_count': SLOT_COUNT,
                'slot_data_base': SLOT_DATA_BASE, 'slot_data_size': SLOT_DATA_SIZE,
                'total': SLOT_DATA_BASE + SLOT_COUNT * SLOT_DATA_SIZE,
            },
            'slot_meta_fields': [{'name': n, 'kind': k, 'off': o, 'len': l} for n, k, o, l in FIELDS],
            'fanout_map': {
                'arg2 = word[rec+0x00]': '年', 'arg3 = word[rec+0x02]': '月',
                'arg4 = word[rec+0x04]': '日',
                '0x522c88 <- rec+0x06 (13B)': '主角名',
                '0x522c60 <- rec+0x13 (13B)': '所在国',
                '0x522c70 <- rec+0x20 (17B)': '所在地+身分',
            },
            'ui_strings': {'0x5096d0': gbk(0x5096d0), '0x50d820': gbk(0x50d820),
                           '0x50d834': gbk(0x50d834)},
            'slots': slots,
            'xor_disproof': xor_report,
        }, f, ensure_ascii=False, indent=1)
    print('JSON ->', out)

    npass = sum(1 for _, ok, _ in tests if ok)
    print('\nRESULT: %d/%d' % (npass, len(tests)))
    bad = [n for n, ok, _ in tests if not ok]
    assert not bad, '失败项: %s' % bad
    print('ALL PASS ✅  P0「43B payload 语义」敞口以「证伪/改判」结案')


if __name__ == '__main__':
    main()
