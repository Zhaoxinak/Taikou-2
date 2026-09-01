# -*- coding: utf-8 -*-
"""
Reusable annotated function disassembler for the unpacked TAIK2W95 image.

Usage:  _fdis.py 0x423910 [0x427830 ...]  [--len N]

Stops at the next known function start (derived from global call targets) or
after a terminal `ret` at depth 0. Annotates known symbols.
"""
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

import sys, io, struct, bisect, collections
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
from capstone import *

BASE = 0x400000
MEM = open(_ROOT + '/scripts/_unpacked_mem.bin', 'rb').read()
TEXT_START, TEXT_END = 0x401000, 0x4d0000
md = Cs(CS_ARCH_X86, CS_MODE_32)

SYM = {
    0x439050: 'getLo(col,row) ; SECT_A[col + 20*row]&0xF  (col 0..19, row 0..8)',
    0x4390c0: 'getHi(col,row) ; SECT_A[col + 20*row]>>4',
    0x439080: 'setLo(col,row,v) ; SECT_A[col+20*row] low nibble = v&0xF (hi nibble preserved)',
    0x439110: 'sectA_lo_eq2(col,row) ; (getLo(col,row)==2)?1:0',
    0x438b80: 'sectA_getLo_bounded(col,row) ; bounds-checked getLo (col<20,row<9)',
    0x439130: 'depGet(col,row) ; DEPLOY[0x512b60][col + 40*row]  (NOT sectA!)',
    0x439150: 'depSet(col,row,v) ; DEPLOY[0x512b60][col + 40*row]=v  (NOT sectA!)',
    0x43e820: 'facilitySlot(i) ; &0x513a78[i*5]  (NOT terrain attr!)',
    0x43e8b0: 'facilityScan',
    0x4ebd30: 'rand()',
    0x4ebd60: 'rand()%n',
    0x43a460: 'pickBattleVariant',
    0x433780: 'loadLZW',
    0x4ec040: 'memcpy',
    0x4f40b0: 'memcpy2',
    0x42d270: 'battleTick(pA,pB)  ; per-tick troop loss',
    0x43a9c0: 'atkDivisor  ; 0x503770[battleType+k]',
    0x43cd10: 'troopDecayCurve',
    0x43cfc0: 'weatherTickSimple',
    0x43d060: 'weatherTransition(thr,mode)',
    0x43d0e0: 'weatherTickRegional',
    0x43e4a0: 'unitSlot(i) ; &0x513910[i*24]',
    # --- 2026-08-27 续5：布陣/計略 ---
    0x42c740: 'deployUnits(pA,pB) ; initial battle deployment (15 slots)',
    0x42c550: 'battleInit -> deployUnits',
    0x423010: 'isOccupied(x,y)',
    0x435370: 'tacticKobu ; morale boost formula',
    0x437400: 'tacticPinRoute ; msgs 0x105-0x109 -> 0x437590',
    0x437590: 'tacticPinMutator ; threshold>=contest, lock unit 0xfa',
    0x43db50: 'getMorale ; byte[corps+0x23]',
    0x43db60: 'addMorale ; min(cur+v, 200)',
    0x43db80: 'subMorale ; saturating',
    0x43dba0: 'addField25 ; min(cur+v, 100)',
    0x4ebcf0: 'clampMin(cur,v,cap)=min(cur+v,cap)',
    0x4ebd10: 'satSub(cur,v)=max(cur-v,0)',
    # --- 2026-08-27 续6：名表访问器 ---
    0x43e140: 'unitTypeCls(u) ; byte[u+0x13]&3  (0=步兵 1=骑兵 2=洋枪)',
    0x43e150: 'unitTypeName(u) ; &0x50bfe8[cls*5]',
    0x43e170: 'unitDisplayName(u) ; side(bit3 of +0x15) + typeName',
    0x4a0b00: 'unitTypeMapLookup(i) ; 0x50bfd0[i]',
    0x4a0fa0: 'unitTypeName2 ; cls from 0x4a0f80',
    0x47ca70: 'drawCastlePanel ; fields 0x50953c + rating words',
}
DSYM = {
    0x503138: 'LUT_A', 0x503140: 'LUT_B', 0x503710: 'DIR8',
    0x503740: 'TIER_THR', 0x503750: 'TIER_BASE', 0x503760: 'TIER_RND',
    0x503770: 'ATK_DIVISOR[20]',
    0x503794: 'WEATHER_KEEP_SIMPLE[12]',
    0x5037b8: 'WEATHER_KEEP_SEASON[15]  (NOT terrain matrix!)',
    0x5037c8: 'WEATHER_WINTER_SNOWREG[3]', 0x5037cb: 'WEATHER_WINTER_NORMAL[3]',
    0x512868: 'TERRAIN_MAP(40x19 nibble)', 0x512b60: 'UNIT_ARR/DEPLOY', 0x512e58: 'SECT_A(20col*9row=180B; lo nibble=moveclass idx, hi nibble=combmod)', 0x503712: 'SPAWN_TYPE_TBL[?*4] (0x43a440 lookup)',
    0x512f10: 'SPRITE_TAB',
    0x513910: 'UNIT_SLOTS[15*24]', 0x513a78: 'FACILITY_SLOTS[16*5] (runtime)',
    0x51352c: 'WEATHER_WET_FLAG', 0x513548: 'BATTLE_TYPE',
    0x506ca8: 'NAME_TABLE', 0x519868: 'ENTITY_TAB', 0x522ce4: 'CITY_OWNER',
    0x519288: 'GEN_APPEAR_FLAGS', 0x519548: 'PROVINCE_STATE[49*5]',
    0x5205f1: 'CUR_MONTH', 0x524866: 'CUR_PROVINCE',
    # --- 2026-08-27 续5：布陣/計略静态表 ---
    0x5031d0: 'FORMATION_MATCHUP[4*4] ; fi=[1,3,0,2][(B-A)%4]',
    0x5031e0: 'DEPLOY_LEFT[4][5][2]', 0x503208: 'FACING_LEFT[4]',
    0x503210: 'DEPLOY_RIGHT[4][5][2]', 0x503238: 'FACING_RIGHT[4]',
    0x503240: 'FLANK_A[5][2]', 0x503258: 'FACING_FLANK_A[5]',
    0x50324a: 'FLANK_B[5][2]', 0x503260: 'FACING_FLANK_B[5]',
    0x503268: 'OPP6[6] ; opp(i)=(i+3)%6',
    0x5032d8: 'TACTIC_NAMES[11*7]', 0x503328: 'TACTIC_HANDLERS[11]',
    # --- 2026-08-27 续6：中文名表 ---
    0x5037e0: 'CORPS_SLOT_NAMES[5*7] ; 总大将/第二~第五军',
    0x503808: 'SIDE_NAMES[2*8] ; 敌人/盟军',
    0x503818: 'FACILITY_NAMES[5*7] ; 本城/米仓/了望台/哨所/城门',
    0x50bfe8: 'UNIT_TYPE_NAMES[3*5] ; 步兵/骑兵/洋枪',
    0x50bff8: 'STR_城守备',
    0x50bfd0: 'UNIT_TYPE_MAP[24] ; id -> cls',
    0x50bfb8: 'MONEY_LADDER[10]', 0x50bfa0: 'PURCHASE_TIERS[3] (id,金额,数量)',
    0x509a48: 'UNIT_TYPE_MENU[3*16]',
    0x5099d8: 'CORPS_ATTRS_A[4*5]', 0x509a78: 'CORPS_ATTRS_B[5*5]',
    0x50953c: 'CASTLE_FIELD_NAMES[10*8]',
    0x50b6ba: 'RATING_WORDS[8][3]*9 ; low/mid/high',
    0x502858: 'PERSUADE_METHODS[6*16]',
}

# global call targets => function starts
_starts = None
def starts():
    global _starts
    if _starts is None:
        s = set()
        i = 0
        while True:
            i = MEM.find(b'\xe8', i, TEXT_END - BASE)
            if i < 0:
                break
            rel = struct.unpack_from('<i', MEM, i + 1)[0]
            t = (i + BASE) + 5 + rel
            if TEXT_START <= t < TEXT_END:
                s.add(t)
            i += 1
        _starts = sorted(s)
    return _starts

def next_start(va):
    st = starts()
    k = bisect.bisect_right(st, va)
    return st[k] if k < len(st) else TEXT_END

def annotate(ins):
    notes = []
    op = ins.op_str
    if ins.mnemonic in ('call', 'jmp') and op.startswith('0x'):
        try:
            t = int(op, 16)
            if t in SYM:
                notes.append('-> ' + SYM[t])
        except ValueError:
            pass
    for a, nm in DSYM.items():
        if f'{a:#x}' in op:
            notes.append(nm)
    return '   ; ' + ' | '.join(notes) if notes else ''

def dis_func(va, maxlen=None):
    stop = next_start(va) if maxlen is None else va + maxlen
    print(f'\n===== func {va:#x}  (until {stop:#x}, {stop-va} bytes) =====')
    cur = va
    while cur < stop:
        chunk = MEM[cur - BASE: stop - BASE]
        n = 0
        for ins in md.disasm(chunk, cur):
            print(f'{ins.address:#08x}  {ins.bytes.hex():<20s} {ins.mnemonic:<8s} {ins.op_str}{annotate(ins)}')
            cur = ins.address + ins.size
            n += 1
            if cur >= stop:
                break
        if n == 0:
            print(f'{cur:#08x}  {MEM[cur-BASE]:02x}                   (bad)')
            cur += 1

if __name__ == '__main__':
    args = [a for a in sys.argv[1:]]
    ml = None
    if '--len' in args:
        k = args.index('--len')
        ml = int(args[k + 1], 0)
        args = args[:k] + args[k + 2:]
    for a in args:
        dis_func(int(a, 0), ml)
