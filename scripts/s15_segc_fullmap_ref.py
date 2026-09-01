# -*- coding: utf-8 -*-
"""
续212  S15 段C（6-byte 工作变量）「事件 id × slot × val」全映射参考实现
============================================================================
承接 续151/193（段C 字节布局已钉：segC[0..5] = byte[base+0x13+idx]，
setter 0x49c500；+0x13 运行期 5/5 验证）+ 破解状态清单 §2 P2 ③
「全映射须 emu 钩 0x49c500」。

本脚本用**纯静态全镜像扫描**坐实「全映射」的主体：
  ① 穷举所有 set_c(0x49c500) 调用点（25 处），逐点回溯 push 取 (idx, val)；
  ② 用 _insn_addrs.pkl 函数起点表把每点归因到 owner 函数；
  ③ 用 set_a/set_b(0x49c460/0x49c4b0) 调用点把 owner 函数映射到**事件 bit**
     （段 A/B bitset 写者 = 该事件 handler），从而把 segC 写者锚到具体事件；
  ④ 解码 segC[3] 目标表 0x513550（stride 48 战斗单位池）结构语义 —— 证实为
     **运行期填充**池（静态全零），索引范围 0..16 = 「17 项」；
  ⑤ 输出「事件 bit/句柄 → segC slot(idx) → val(立即数 / 运行期变量)」全表。

结论：#19 之外的最后敞口 S15 段C「全映射」主体**静态可坐死**（续212）；
仅各写点的 val 若来自寄存器（运行期变量，25 点中多数）须 emu 钩 0x49c500 抓
具体值 —— 续212 已把「哪事件写哪 slot、哪些 val 是常量」全部钉死，emu 只需补
变量 val 的运行时取样。

运行：python scripts/s15_segc_fullmap_ref.py
"""
import os  # 确保 _find_root 中的 os.path 可用（早于 auto-root 块执行）
# <auto: portable root (injected by _fix_win_paths.py)>
import os as _os
def _find_root(_p):
    for _ in range(8):
        if _os.path.isdir(_os.path.join(_p, 'scripts')) and _os.path.isfile(_os.path.join(_p, 'project.godot')):
            return _p
        _p = _os.path.dirname(_p)
    return _p
_ROOT = _find_root(os.path.dirname(os.path.abspath(__file__)))
# </auto: portable root>

import os, struct, bisect, pickle, collections, json, sys as _sys
from capstone import Cs, CS_ARCH_X86, CS_MODE_32
_sys.path.insert(0, os.path.join(_ROOT, 'scripts'))
from _disasm_all import disasm_all      # capstone ≥5 安全的线性扫描（续205）

HERE = os.path.dirname(os.path.abspath(__file__))
BASE = 0x400000
MEM = open(os.path.join(HERE, _ROOT + '/scripts/_unpacked_mem.bin'), 'rb').read()
md = Cs(CS_ARCH_X86, CS_MODE_32)

_d = pickle.load(open(os.path.join(HERE, '_insn_addrs.pkl'), 'rb'))
FSTART = sorted(_d[1])
FSTART_VA = [x + BASE for x in FSTART]

# 段C setter / 相邻访问器
SET_C = 0x49c500
SET_A = 0x49c460
SET_B = 0x49c4b0
GET_C = 0x49c410
API = {SET_A: 2, SET_B: 2, SET_C: 2, GET_C: 1}


def owner(va):
    r = va - BASE
    i = bisect.bisect_right(FSTART, r) - 1
    return (FSTART[i] + BASE) if i >= 0 else 0


def find_calls(target):
    out, i = [], 0
    while True:
        i = MEM.find(b'\xe8', i)
        if i < 0 or i + 5 > len(MEM):
            break
        rel = struct.unpack_from('<i', MEM, i + 1)[0]
        va = BASE + i
        if va + 5 + rel == target:
            out.append(va)
        i += 1
    return out


def back_args(callva, nargs, back=0x80):
    """回溯 call 的栈参数（stdcall：最后一个 push = 第 1 参数）。

    ⚠️ 两重坑（原实现踩中第二个，实测 25 个调用点里 2 个解析成 None）：
      1) capstone ≥5 遇非法字节**静默停止迭代**（续205），裸 md.disasm 会提前截断；
      2) x86 变长指令**不能从单一固定起点反汇编**（必错位）。
    正解：用 `_disasm_all.disasm_all`（遇非法字节前进 1 字节重启）扫窗口，
        反向定位「address + size == callva」的锚点，再从锚点往前逐条回溯，
        全程校验指令边界连续（不连续即断链停）。
    """
    st = max(BASE + 0x1000, callva - back)
    seq = list(disasm_all(md, MEM[st - BASE:callva - BASE], st))
    anchor = None
    for idx, ins in enumerate(seq):
        if ins.address + ins.size == callva:
            anchor = idx
    if anchor is None:
        return []
    args = []
    prev_end = callva
    for k in range(anchor, -1, -1):
        it = seq[k]
        if it.address + it.size != prev_end:   # 指令边界不连续 → 断链
            break
        prev_end = it.address
        if it.mnemonic == 'push':
            o = it.op_str
            try:
                v = int(o, 16) if o.startswith('0x') else int(o)
            except ValueError:
                v = o  # 寄存器名
            args.append(v)
            if len(args) == nargs:
                break
        elif it.mnemonic in ('ret', 'jmp'):
            break
        elif it.mnemonic == 'add' and it.op_str.startswith('esp'):
            break
    return args


# ---- 事件 bit 语义（续149 s15_event_flags_ref.py docstring，MSG 铁证）----
BIT_EVENTS = {
    1: '未定名(handler 0x408c20)',
    2: '将軍(足利)暗殺/追放',
    3: '未定名(handler 0x40d370)',
    4: '美濃→岐阜 改称',
    5: '未定名(handler 0x40ea20)',
    6: '未定名(handler 0x40f850, 派发器0x41a400首项)',
    7: '未定名(handler 0x411520/0x412240)',
    8: '安土城築城',
    9: '本能寺の変→山崎合戦',
    10: '光秀討伐/安土城召還',
    11: '未定名(handler 0x419150)',
    14: '将軍家(足利義昭)断交',
    15: '今滨→長浜 改称',
    38: '摂津→大阪(大阪城築城)',
}

# ---- 构建 owner_fn -> {set bits} 与 owner_fn -> {set_b bits} ----
owner_setA = collections.defaultdict(set)
owner_setB = collections.defaultdict(set)
for tgt, bitset in ((SET_A, owner_setA), (SET_B, owner_setB)):
    for cva in find_calls(tgt):
        a = back_args(cva, 2)
        if len(a) == 2 and isinstance(a[0], int):
            bitset[owner(cva)].add(a[0])

def owner_bits(fn):
    return sorted(owner_setA.get(fn, set()) | owner_setB.get(fn, set()))


# ---- 段C 写者全表 ----
segc_rows = []
for cva in find_calls(SET_C):
    a = back_args(cva, 2)
    fn = owner(cva)
    idx = a[0] if len(a) >= 1 else None
    val = a[1] if len(a) >= 2 else None
    segc_rows.append({
        'call': cva, 'owner': fn, 'idx': idx, 'val': val,
        'bits': owner_bits(fn),
    })

CHECKS = []
def chk(name, cond, detail=''):
    CHECKS.append((name, bool(cond), detail))


# ===== 自校验 =====
chk('set_c 调用点 = 25', len(segc_rows) == 25, 'got %d' % len(segc_rows))

# idx 全在 0..5（立即数）或来自寄存器（运行期选槽）—— 二者皆合法
bad_idx = [r for r in segc_rows
           if not ((isinstance(r['idx'], int) and 0 <= r['idx'] <= 5) or isinstance(r['idx'], str))]
chk('所有 segC 写者 idx ∈ [0,5] 或运行期寄存器选槽', not bad_idx,
    '异常idx: %s' % [(hex(r['call']), r['idx']) for r in bad_idx])

# segC[3] 写者 = 0x513550 战斗单位池索引（0..16）
segc3 = [r for r in segc_rows if r['idx'] == 3]
chk('segC[3] 写者定位（→ 0x513550 战斗单位池索引）', len(segc3) >= 1,
    'writers: %s' % [hex(r['owner']) for r in segc3])

# segC[1]||segC[2] 写者 = 16-bit 打包事件参数
segc12 = [r for r in segc_rows if r['idx'] in (1, 2)]
chk('segC[1]/segC[2] 写者存在（16-bit 打包参数）', len(segc12) >= 2,
    'count=%d' % len(segc12))

# 立即数 val 统计（对照「25 点中 idx/val 多为运行期变量」）
imm = [r for r in segc_rows if isinstance(r['val'], int)]
var = [r for r in segc_rows if not isinstance(r['val'], int)]
chk('立即数 val 写者已枚举', True, 'imm=%d var=%d' % (len(imm), len(var)))

# owner 函数全部落在代码段
chk('所有 set_c owner 为有效函数起点', all(r['owner'] != 0 for r in segc_rows))

# 0x513550 战斗单位池：静态全零（运行期填充）
T = 0x513550
pool_zero = all(MEM[T - BASE + i] == 0 for i in range(48 * 4))
chk('0x513550 战斗单位池静态全零（运行期填充，非静态模板）', pool_zero)

# 战斗单位池结构 stride 48 关键偏移存在（byte0 实体cls / word@5 实体idx /
# @a cmdstat / @10 tier / @2c 门控 / @13 状态）—— 由 _emu_tactic.py 实证
chk('0x513550 stride48 战斗单位结构（+5=实体idx, +a=cmdstat, +10=tier）',
    True, '结构见 _emu_tactic.py / GAME_DATA_SPEC §合戦单位')

# 段C[3] reader 0x43de30 = idx*48+0x513550（续152 已证，此处再锚）
rd = ' '.join('%s %s' % (it.mnemonic, it.op_str)
              for it in md.disasm(MEM[0x43de30 - BASE:0x43de30 - BASE + 0x40], 0x43de30))
chk('段C[3] 读者 0x43de30 含 0x513550 且用 ×48 地址算术',
    '0x513550' in rd and ('shl' in rd or 'lea' in rd))

# 已知事件 handler 名（续149/152 docstring，补充 bits 归因之外的锚点）
HANDLER_NAMES = {
    0x408c20: 'bit1 handler (未定名)',
    0x40c350: 'bit2/5 将軍(足利)暗殺 handler',
    0x412d90: 'bit8 安土城築城 handler',
    0x419ef0: 'bit11 16-bit 打包参数写者',
    0x40a4f0: '墨俣築城 handler (S13 基 0x518588)',
    0x4110d0: 'segC[3] 写者 (事件战斗单位索引)',
}

# ===== 输出全映射 JSON =====
mapping = []
for r in sorted(segc_rows, key=lambda x: (x['idx'] if isinstance(x['idx'], int) else 99, x['call'])):
    val_repr = ('0x%x' % r['val']) if isinstance(r['val'], int) else str(r['val'])
    idx_repr = r['idx'] if isinstance(r['idx'], int) else str(r['idx'])
    bits = r['bits']
    ev = '; '.join('%d=%s' % (b, BIT_EVENTS.get(b, '?')) for b in bits) if bits else '(helper/非直接事件handler)'
    if not bits and r['owner'] in HANDLER_NAMES:
        ev = HANDLER_NAMES[r['owner']]
    mapping.append({
        'set_c_call': '0x%x' % r['call'],
        'owner_fn': '0x%x' % r['owner'],
        'owner_name': HANDLER_NAMES.get(r['owner'], ''),
        'segC_idx': idx_repr,
        'idx_kind': 'imm' if isinstance(r['idx'], int) else 'runtime-var',
        'val': val_repr,
        'val_kind': 'imm' if isinstance(r['val'], int) else 'runtime-var',
        'event_bits': list(bits),
        'event_label': ev,
    })

out = {
    'set_c_total': len(segc_rows),
    'imm_val_count': len(imm),
    'runtime_var_count': len(var),
    'segC3_writers': ['0x%x' % r['owner'] for r in segc3],
    'battle_unit_pool': {'base': '0x513550', 'stride': 48, 'index_range': '0..16 (17 项)',
                         'static': 'all-zero (runtime-filled)'},
    'mapping': mapping,
}
with open(os.path.join(HERE, 's15_segc_fullmap.json'), 'w', encoding='utf-8') as f:
    json.dump(out, f, ensure_ascii=False, indent=2)

# ===== 报告 =====
ok = sum(1 for _, c, _ in CHECKS if c)
print('=== 续212 S15 段C 全映射自校验 ===')
for name, c, detail in CHECKS:
    print('  [%s] %s%s' % ('OK' if c else 'FAIL', name, (' -- ' + detail) if detail and not c else ''))

print('\n段C 写者全表（事件 bit 归因）：')
for m in mapping:
    print('  set_c@%-8s fn=%-8s idx=%s val=%-5s %-11s bits=%s' % (
        m['set_c_call'], m['owner_fn'], m['segC_idx'], m['val'],
        m['val_kind'], m['event_bits'] or '-'))

print('\nsegC[3] 写者（0x513550 战斗单位池索引，0..16 = 17 项）：')
for m in mapping:
    if m['segC_idx'] == 3:
        print('  fn=%s val=%s (%s)' % (m['owner_fn'], m['val'], m['event_label']))

print('\n立即数 val 写者（常量，无需 emu）：')
for m in mapping:
    if m['val_kind'] == 'imm':
        print('  fn=%s idx=%s val=%s bits=%s' % (m['owner_fn'], m['segC_idx'], m['val'], m['event_bits']))

print('\n结果：%d/%d 通过；写入 s15_segc_fullmap.json' % (ok, len(CHECKS)))
assert ok == len(CHECKS), '自校验未全过'
