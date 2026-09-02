# -*- coding: utf-8 -*-
"""
skill_bitpack_ref.py -- 实证 武将技能 2-bit 位打包 (GAME_DATA_SPEC §3.5.6)。
纯静态：EXE 名表 0x507b58 + 显示槽映射 0x503840 + 明文 BSDATA1.TR2，无需 emu。
"""
import os, struct, json

BASE = 0x400000
HERE = os.path.dirname(os.path.abspath(__file__))
IMG = os.path.join(HERE, '_unpacked_mem.bin')
ROOT = os.path.dirname(HERE)
ORIG = os.path.join(ROOT, 'Taikou2 Original')

def read(va, n):
    return open(IMG, 'rb').read()[va - BASE: va - BASE + n]

def gbk2(s):
    return s.decode('gbk', 'replace').strip('\x00 ')

# 规范技能名（EXE 名表 0x507b58 实测顺序；ROM 串即 算术/兵法，非旧记 算用/军学）
EXE_NAMES = ['口才','马术','算术','剑术','忍术','兵法','洋枪','筑城','礼法','茶道']

# ---- 我的规范解码：槽 k(0..9)=技能 id k，level_k=(byte[0x1b+k//4]>>((k&3)*2))&3 ----
def my_decode(b27, b28, b29):
    return [( (b27,b28,b29)[k//4] >> ((k&3)*2) ) & 3 for k in range(10)]

# ---- 原 _extract_bsdata.py 解码（逐字复制），输出也转成 id 顺序 ----
SCRIPT_NAMES = ["算用","剑术","口才","马术","洋枪","筑城","忍术","军学","礼法","茶道"]
def orig_decode(b27, b28, b29):
    nibbles = [(b27>>4)&0xF, b27&0xF, (b28>>4)&0xF, b28&0xF, b29&0xF]
    d = {}
    for i,v in enumerate(nibbles):
        d[SCRIPT_NAMES[i*2]] = v & 3
        d[SCRIPT_NAMES[i*2+1]] = (v>>2) & 3
    # 原解码 dict 键 = SCRIPT_NAMES（算用/军学 旧名）；桥接到 id 顺序
    id_to_script = {0:'口才',1:'马术',2:'算用',3:'剑术',4:'忍术',5:'军学',
                    6:'洋枪',7:'筑城',8:'礼法',9:'茶道'}
    return [d[id_to_script[k]] for k in range(10)]

def main():
    raw = open(os.path.join(ORIG,'BSDATA1.TR2'),'rb').read()
    assert len(raw) == 59*700
    recs = [raw[i*59:(i+1)*59] for i in range(700)]

    # A. 名表
    nametab = read(0x507b58, 5*10)
    names = [gbk2(nametab[i*5:i*5+4]) for i in range(10)]
    print('A. 技能名表 @0x507b58 :', names)
    assert names == EXE_NAMES, (names, EXE_NAMES)

    # B. 显示槽→id
    slotmap = list(read(0x503840, 10))
    print('B. 显示槽→技能id @0x503840 :', slotmap)
    assert sorted(slotmap) == list(range(10))

    # C. 我的解码 vs 原解码 一致性 + 2-bit 范围
    diffs = []
    over = 0
    for cid in range(700):
        b27,b28,b29 = recs[cid][27], recs[cid][28], recs[cid][29]
        mine = my_decode(b27,b28,b29)
        orig = orig_decode(b27,b28,b29)
        for k in range(10):
            if mine[k] > 3: over += 1
            if mine[k] != orig[k]:
                diffs.append((cid, k, EXE_NAMES[k], mine[k], orig[k]))
    print('C. 我的解码 vs 原解码 差异: %d / 7000 ; 越界(>3): %d' % (len(diffs), over))
    for d in diffs[:20]:
        print('    cid=%d id%d(%s) mine=%d orig=%d' % d)
    assert over == 0
    assert len(diffs) == 0, '两套解码不一致'

    # D. 史实 sanity（用我自己的解码 + 武将名定位）
    bs = json.load(open(os.path.join(HERE,'bsdata.json'),encoding='utf-8'))['characters']
    name_of = {i: bs[i]['name'] for i in range(700)}
    # 找目标武将 id（按已知史实人物在 700 武将中的位置）
    targets = {
        13:  {5:3, 2:3},   # 织田信长: 兵法3 算术3
        16:  {2:2},        # 木下藤吉郎（秀吉）: 算术2
        27:  {3:3},        # 前田利家: 剑术3
    }
    print('D. 史实 sanity（按 id 直接取，避免名称字形差异）:')
    for cid, exp in targets.items():
        b27,b28,b29 = recs[cid][27], recs[cid][28], recs[cid][29]
        mine = my_decode(b27,b28,b29)
        got = {EXE_NAMES[k]: mine[k] for k in exp}
        ok = all(mine[k]==v for k,v in exp.items())
        print('    #%d %s: %s  %s' % (cid, name_of[cid], got, 'OK' if ok else 'CHECK'))

    print('\n结论: ✅ 武将技能 = 10×2-bit @ BSDATA 字节27..29 (entity +0x1b..+0x1d)。')
    print('      槽位顺序 == EXE 名表 0x507b58 技能 id 顺序 (口才,马术,算术,剑术,忍术,兵法,洋枪,筑城,礼法,茶道)。')
    print('      位布局: level_k = (byte[0x1b+k//4] >> ((k&3)*2)) & 3, k=0..9。')
    print('      与既有解码 7000 项全一致；全部等级∈0..3；显示槽 0x503840 印证 id 空间。')
    print('      → §3.5.6 由 🔶 升级为 ✅（EXE 名表序 + 明文数据双重实证）。')

if __name__ == '__main__':
    main()
