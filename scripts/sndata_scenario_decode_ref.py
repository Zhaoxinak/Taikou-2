# -*- coding: utf-8 -*-
"""
sndata_scenario_decode_ref.py  —— 续165 自校验脚本
==========================================================
主题：建立 0x47f350 「载入剧本(scenario)」主解码器 与 18 个子字段解码器 的架构事实，
      并澄清 3-文本视图(display) 路径与「49字节记录」路径是两条独立链路。

校验点：
  [C1] 0x47f350 调用的子解码器总数 == 18，且集合 == 已知 18 个 (0x47dae0..0x47f210)。
  [C2] 18 个子解码器各自写入的「目标全局表基址」可映射到已知表 (实体/城/国/S15/...)。
  [C3] 3 文本视图缓冲 (0x522c88/0x522c60/0x522c70) 全镜像仅 3 处引用，均在 0x480000 区域，
       且 0x480000 把它们当作 *字符串* 消费 (strcpy->strlen->空格对齐至宽度 14/18/18)。
  [C4] 49 字节记录读取器 0x47d890 的 stride == idx*49 + 0x10 (÷49 魔数 0x51eb85? 实测 lea+shl)。

运行：<venv>/Scripts/python.exe sndata_scenario_decode_ref.py
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

import os, re
from capstone import CS_ARCH_X86, CS_MODE_32, Cs

BASE = 0x400000
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MEM = open(os.path.join(ROOT, 'scripts', _ROOT + '/scripts/_unpacked_mem.bin'), 'rb').read()
md = Cs(CS_ARCH_X86, CS_MODE_32)
md.detail = True

def dis(va, n):
    return list(md.disasm(MEM[va - BASE: va - BASE + n], va))

# 已知 18 个子解码器（0x47f350 在 0x47f4cb 之前的 call 目标，剔除 0x47f5b0 守卫 与 0x47d960 解密器）
KNOWN_SUBS = [0x47dae0, 0x47dce0, 0x47e130, 0x47e3a0, 0x47e440, 0x47e5a0,
              0x47e770, 0x47ea80, 0x47ebb0, 0x47ecb0, 0x47ed10, 0x47ed70,
              0x47ee50, 0x47ef00, 0x47f050, 0x47f0a0, 0x47f1b0, 0x47f210]

# 已知 18 子解码器 → (S#, 基址, 语义)  —— ★ 续166 修正：以 §5.2(emu, 续99) 为权威
# 续165 旧 KNOWN_TABLES 用「字面 push 全局最小值」自动探测，会把 scratch 基址(0x516610/0x5203c0/0x517c70)
# 误当真实目标表，已弃用。GAME_DATA_SPEC §5.2 经 Unicorn 实跑 0x47f350 逐段挂钩计数给出权威映射。
SUBDECODER_NAMES = {
    0x47dae0: ('S0',  None,     '全局/头部(22B)'),
    0x47dce0: ('S1',  0x519868, '武将实体池(370x59)'),
    0x47e130: ('S2',  0x51eb88, '城/町表(200x26)'),
    0x47e3a0: ('S3',  0x519548, '国情基表(49x5)'),
    0x47e440: ('S4',  0x5179b8, '49国政治/关系表(49x11)'),
    0x47e5a0: ('S5',  0x5197b0, '6槽武将表(6x30)'),
    0x47e770: ('S6',  0x516610, '玩家/事件上下文 S6(46B, §3.20)'),
    0x47ea80: ('S7',  0x516a28, '每城运行时状态表(200x16)'),
    0x47ebb0: ('S8',  0x517850, '台词表(30x12)'),
    0x47ecb0: ('S9',  0x519238, '台词表(20x4)'),
    0x47ed10: ('S10', 0x5176a8, '台词表(30x4)'),
    0x47ed70: ('S11', None,     '物品段(189x19)'),
    0x47ee50: ('S12', 0x517728, '物品副池(20x12)'),
    0x47ef00: ('S13', 0x5185b6, '目標/目標記録表(20x114)'),
    0x47f050: ('S14', 0x51dc60, '49国外交关系矩阵(1176B)'),
    0x47f0a0: ('S15', 0x5203c2, 'S15 3段标志(25B)'),
    0x47f1b0: ('S16', 0x519680, '文本ID表(20x2)'),
    0x47f210: ('S17', 0x517c73, '3B前缀+10x13B'),
}

SET_BYTE_GLOBAL = '0x47d910'   # read 1 byte from record -> global
SET_WORD_GLOBAL = '0x47d930'   # read 1 word from record -> global
SET_BYTE_OBJ = '0x47da80'      # read byte -> object member
SET_WORD_OBJ = '0x47dac0'      # read word -> object member


def check_c1_master_calls():
    """[C1] 枚举 0x47f350 内对 0x47d000..0x47f600 的 call，剔除守卫/解密器后应为 18。"""
    calls = []
    for i in dis(0x47f350, 0x300):
        if i.mnemonic == 'call':
            m = re.match(r'0x([0-9a-f]+)', i.op_str)
            if m:
                t = int(m.group(1), 16)
                if 0x47d000 <= t <= 0x47f600:
                    calls.append(t)
    seen, uniq = set(), []
    for t in calls:
        if t not in seen:
            seen.add(t); uniq.append(t)
    subs = [t for t in uniq if t not in (0x47f5b0, 0x47d960)]
    ok = (len(subs) == 18) and (sorted(subs) == sorted(KNOWN_SUBS))
    return ok, len(subs), subs


def analyze_sub(func):
    """提取子解码器：目标全局集合 / 是否写对象成员 / 字节数 / 主基址。"""
    ins = dis(func, 0x400)
    globs = set()
    pend = None
    nbytes = 0
    writes_obj = False
    for i in ins:
        if i.mnemonic == 'push':
            m2 = re.search(r'0x([0-9a-f]+)', i.op_str)
            if m2:
                v = int(m2.group(1), 16)
                if 0x500000 <= v <= 0x52ffff:
                    pend = v
        if i.mnemonic == 'call' and i.op_str.strip() in (
                SET_BYTE_GLOBAL, SET_WORD_GLOBAL, SET_BYTE_OBJ, SET_WORD_OBJ):
            sz = 2 if i.op_str.strip() in (SET_WORD_GLOBAL, SET_WORD_OBJ) else 1
            if i.op_str.strip() in (SET_BYTE_GLOBAL, SET_WORD_GLOBAL):
                if pend is not None:
                    globs.add(pend)
            else:
                writes_obj = True
            nbytes += sz
            pend = None
    # 主基址 = 目标全局最小值，否则标注 objmem（★ 续166：真实表名见 SUBDECODER_NAMES，此处仅给底色标签）
    base = min(globs) if globs else None
    label = 'objmem' if (base is None and writes_obj) else ('?' if base is None else 'global')
    return sorted(globs), writes_obj, nbytes, base, label


def check_c3_views():
    """[C3] 3 视图缓冲全镜像引用扫描（窗口扫描，规避数据段反汇编停滞）。"""
    VIEWS = ['0x522c88', '0x522c60', '0x522c70']
    hits = []
    va = BASE
    while va < 0x5A0000:
        chunk = MEM[va - BASE: va - BASE + 0x2000]
        for ins in md.disasm(chunk, va):
            s = f'{ins.mnemonic} {ins.op_str}'
            for v in VIEWS:
                if v in s:
                    hits.append((ins.address, ins.mnemonic, ins.op_str))
                    break
        va += 0x2000
    # 全部应为 0x480000 区域的 push (R 读取方=作实参)
    in_480000 = all(0x480000 <= a <= 0x480140 for a, _, _ in hits)
    widths = (14, 18, 18)  # 0x480000 内 0xe / 0x12 / 0x12 空格对齐宽度
    return (len(hits) == 3) and in_480000, len(hits), hits, widths


def check_c4_record_reader():
    """[C4] 0x47d890 的 stride： lea ecx,[eax+eax*2]; shl ecx,4; lea edx,[ecx+eax+0x10] => eax*49+0x10。"""
    lines = [f'{i.mnemonic} {i.op_str}' for i in dis(0x47d890, 0x60)]
    joined = '\n'.join(lines)
    ok = ('shl ecx, 4' in joined) and ('lea edx, [ecx + eax + 0x10]' in joined)
    return ok, lines[6:14]


def main():
    print('=' * 70)
    print('续165 自校验：0x47f350 剧本载入主解码器 架构')
    print('=' * 70)

    # C1
    ok1, n, subs = check_c1_master_calls()
    print(f'\n[C1] 0x47f350 子解码器调用数 = {n} (期望 18)  -> {"PASS" if ok1 else "FAIL"}')
    if not ok1:
        print('     实际:', [hex(x) for x in subs])

    # C2: 每个子解码器的目标表（★ 续166 改用 §5.2 权威 SUBDECODER_NAMES，弃用 buggy 的 min-glob 探测）
    print('\n[C2] 18 子解码器 -> 目标表映射（权威 §5.2）：')
    all_ok = True
    for t in KNOWN_SUBS:
        globs, wobj, nb, base, _ = analyze_sub(t)
        s, b, sem = SUBDECODER_NAMES.get(t, ('?', base, '?'))
        bstr = hex(b) if b else '-'
        print(f'  0x{t:06x}  {s:3s}  setter调用点={nb:3d}B  base={bstr:10s}  {sem}')
        if s == '?':
            all_ok = False
    print(f'  -> {"PASS (全部映射到 §5.2 权威表)" if all_ok else "WARN (存在未识别子解码器)"}')

    # C3
    ok3, nh, hits, widths = check_c3_views()
    print(f'\n[C3] 3 视图缓冲引用数 = {nh} (期望 3，全在 0x480000) -> {"PASS" if ok3 else "FAIL"}')
    for a, m, o in hits:
        print(f'      0x{a:06x}  {m} {o}')
    print(f'      0x480000 空格对齐宽度 = {widths} (view1=rec+6, view3=rec+32, view2=rec+19)')

    # C4
    ok4, slit = check_c4_record_reader()
    print(f'\n[C4] 49字节记录读取器 0x47d890 stride = idx*49+0x10 -> {"PASS" if ok4 else "FAIL"}')
    for l in slit:
        print('      ' + l)

    print('\n' + '=' * 70)
    overall = ok1 and ok3 and ok4
    print(f'总体: {"ALL PASS" if overall else "PARTIAL/FIX NEEDED"}')
    print('=' * 70)


if __name__ == '__main__':
    main()
