# -*- coding: utf-8 -*-
"""全局 MSGX id → 文本 映射 + 反查 EXE 中所有消息显示点。
用法: python _msgx_map.py [--battle]
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

import os, re, struct, json, bisect, sys
from capstone import *
BASE = 0x400000
HERE = os.path.dirname(os.path.abspath(__file__))
mem = open(os.path.join(HERE, _ROOT + '/scripts/_unpacked_mem.bin'), 'rb').read()

# ---------- 1) 载入 4 个文件全部文本 ----------
FILES = ['MESSAGE1.LZW', 'MESSAGE2.LZW', 'MESSAGE3.LZW', 'MESSAGE4.LZW']
counts = {}
texts = {}          # id -> text
for fi, fn in enumerate(FILES):
    lst = []
    for line in open(os.path.join(HERE, '_probe', 'msgx', 'all_messages.txt'), encoding='utf-8'):
        m = re.match(r'^\[' + re.escape(fn) + r'#(\d+)\] (.*)$', line.rstrip('\n'))
        if m:
            lst.append((int(m.group(1)), m.group(2)))
    lst.sort()
    counts[fn] = len(lst)
    for i, t in lst:
        texts[fi * 2000 + i] = t
print('文本载入:', counts, '总计', len(texts))

def resolve(mid):
    return texts.get(mid & 0xffff)

# ---------- 2) 反查 EXE 消息显示点 ----------
MSG_FUNCS = {0x47ba40, 0x47b180, 0x47b210, 0x47b900, 0x47b660, 0x49f190, 0x493500}
TLO, THI = 0x401000, 0x4f4000
# call-target 函数头
targets = set()
i = 0
while True:
    i = mem.find(b'\xe8', i)
    if i < 0: break
    rel = struct.unpack_from('<i', mem, i + 1)[0]
    t = (i + BASE) + 5 + rel
    if TLO <= t < THI: targets.add(t)
    i += 1
funcs = sorted(targets)
def host(va):
    k = bisect.bisect_right(funcs, va) - 1
    return funcs[k] if k >= 0 else 0

md = Cs(CS_ARCH_X86, CS_MODE_32); md.detail = False
sites = []
for off in range(0, min(len(mem), THI - BASE)):
    if mem[off] != 0xe8: continue
    rel = struct.unpack_from('<i', mem, off + 1)[0]
    tgt = (off + BASE) + 5 + rel
    if tgt not in MSG_FUNCS: continue
    site = BASE + off
    # 回溯最多 10 条指令，收集 push imm
    lo = max(0, off - 40)
    seq = list(md.disasm(mem[lo:off], BASE + lo))
    ids, args = [], []
    for ins in reversed(seq[-10:]):
        if ins.mnemonic == 'push':
            m = re.match(r'^0x([0-9a-f]+)$', ins.op_str.strip())
            if m:
                v = int(m.group(1), 16)
                args.append(v)
                if 0 < v < 0x2000 and v in texts:
                    ids.append(v)
        elif ins.mnemonic in ('call', 'ret', 'jmp'):
            break
    if ids:
        sites.append({'at': hex(site), 'callee': hex(tgt), 'func': hex(host(site)),
                      'ids': ids, 'texts': [texts[i] for i in ids],
                      'raw_args': args})
print(f'\n消息显示点 {len(sites)} 处\n')

json.dump({'counts': counts, 'total': len(texts),
           'sites': sites}, open(os.path.join(HERE, 'msgx_id_map.json'), 'w', encoding='utf-8'),
          ensure_ascii=False, indent=1)

# ---------- 3) 按宿主函数聚合 ----------
if '--battle' in sys.argv:
    print('=== 使用 MESSAGE4(6000+) 战斗文本的函数 ===')
    byf = {}
    for s in sites:
        for i in s['ids']:
            if i >= 6000:
                byf.setdefault(s['func'], []).append((i, texts[i]))
    for f, lst in sorted(byf.items(), key=lambda kv: -len(kv[1]))[:30]:
        print(f'\nfunc {f}  ({len(lst)} 处)')
        for i, t in lst[:8]:
            print(f'   id=0x{i:04x} {t}')
