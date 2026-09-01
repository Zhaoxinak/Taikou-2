#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""事件 id2 尾跳目标 `0x461510` 的供给者 —— ✅ 纯静态闭合（续136）

旧判「须 emu」系误判（与其三项子问题在续129 被静态推翻同源）。

链路（全部反汇编实证）：
  0x4619ec  mov ecx,[0x52063c]        ; 当前武将
  0x4619f2  cmp byte[ecx+7], 2
  0x4619f6  jb  → 0x461b00            ; 下位（byte[+7] < 2）
  0x4619fd  call 0x461a30             ; 上位（byte[+7] >= 2）
  0x461a15  mov ecx,[esp+4]           ; 取回产出
  0x461a19  push ecx
  0x461a1a  call 0x461510             ; id2 thunk，参数 = 数量选择结果
  0x461a1f  add esp,4
  0x461a22  call 0x461490

两个供给者结构完全对称，差别只在阈值与上限：
  0x461a30(上位): edx = word[0x51662e]/10 + word[ctx+4];  cmp edx, 0x0f; jge → call 0x461660(15,30,0,1)
  0x461b00(下位): edx = word[0x51662e]/10 + word[ctx+4];  cmp edx, 0x0a; jge → call 0x461660(10,100,0,0)
  （/10 由魔法数 0x66666667 + sar edx,2 实现；0x51662e 落在 S6 事件 ctx 内）
  0x461660 返回所选数量；== 0x7fffffff 视为取消（弹 0xfb0 后返回 0）。

玩法（MSGX 反查坐实）= **铁炮（洋枪）购入**：
  0xfda 商人兜售 / 0xfdc「10支洋枪15贯钱，最多可以卖到300支」(15,30: 30批×10支=300)
       / 0xfde「10支洋枪10贯钱，可以卖到1000枝」(10,100: 100批×10支=1000)
       / 0xfcf 钱不够 / 0xfdf 带不到10贯很难买东西 / 0xfb0 取消
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

import json, os, struct

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
IMG = open(os.path.join(ROOT, _ROOT + '/scripts/_unpacked_mem.bin'), 'rb').read()
BASE = 0x400000

# (地址, 期望字节) —— 关键指令锚点，防回归
ANCHORS = [
    (0x4619ec, 'mov ecx, dword ptr [0x52063c]'),
    (0x4619f2, 'cmp byte ptr [ecx + 7], 2'),
    (0x4619f6, 'jb 0x461a04'),
    (0x4619fd, 'call 0x461a30'),
    (0x461a09, 'call 0x461b00'),
    (0x461a19, 'push ecx'),
    (0x461a1a, 'call 0x461510'),
    (0x461a22, 'call 0x461490'),
]
SUPPLIERS = {
    '0x461a30': {'branch': 'byte[cur+7] >= 2 (上位)', 'threshold': 0x0f,
                 'args': (0x0f, 0x1e, 0, 1), 'msg': 0xfdc, 'unit': 10, 'max': 300},
    '0x461b00': {'branch': 'byte[cur+7] < 2 (下位)', 'threshold': 0x0a,
                 'args': (0x0a, 0x64, 0, 0), 'msg': 0xfde, 'unit': 10, 'max': 1000},
}
MSGX = {0xfda: '商人兜售上等洋枪', 0xfdb: '精挑细选的洋枪，性能有保证',
        0xfdc: '10支洋枪15贯钱，最多可以卖到300支', 0xfde: '10支洋枪10贯钱，可以卖到1000枝',
        0xfcf: '糟糕，钱不够了', 0xfd0: '只有这么点钱，武士大人真是辛苦啊',
        0xfdf: '身上带不到10贯钱，不管要买什么都很困难', 0xfb0: '如果您改变主意的话，请再来找我'}


def dis_one(va):
    from capstone import Cs, CS_ARCH_X86, CS_MODE_32
    md = Cs(CS_ARCH_X86, CS_MODE_32); md.detail = True
    off = va - BASE
    for ins in md.disasm(IMG[off:off + 16], va):
        return f'{ins.mnemonic} {ins.op_str}'
    return ''


def main():
    ok = fail = 0
    def chk(l, cond):
        nonlocal ok, fail
        if cond: ok += 1; print(f'  [PASS] {l}')
        else:    fail += 1; print(f'  [FAIL] {l}')

    print('=== 事件 id2 尾跳目标供给者（续136） ===')
    for va, want in ANCHORS:
        got = dis_one(va)
        chk(f'0x{va:x}: {want}', got == want)

    # 两个供给者的阈值/参数（线性反汇编，勿逐字节扫——会错位解码）
    def dis_body(va, nbytes=0xA0):
        from capstone import Cs, CS_ARCH_X86, CS_MODE_32
        md = Cs(CS_ARCH_X86, CS_MODE_32); md.detail = True
        off = va - BASE
        out = []
        for ins in md.disasm(IMG[off:off + nbytes], va):
            out.append(f'{ins.mnemonic} {ins.op_str}')
            if ins.mnemonic in ('ret', 'retn'):
                break
        return ' '.join(out)

    for name, s in SUPPLIERS.items():
        va = int(name, 16)
        body = dis_body(va)
        want_cmp = f'cmp edx, 0x{s["threshold"]:x}'     # capstone 渲染为十六进制，勿用十进制
        chk(f'{name} 含阈值 {want_cmp}', want_cmp in body)
        chk(f'{name} 调用 0x461660(数量选择)',
            'call 0x461660' in body)
        chk(f'{name} 读取 word[0x51662e]（S6 事件 ctx）',
            'word ptr [0x51662e]' in body)
        # 上限自洽：批次 × 每批10支 = 上限
        per, batches = s['args'][0], s['args'][1]
        chk(f'{name} 上限自洽 {batches}批 × {s["unit"]}支 = {s["max"]}',
            batches * s['unit'] == s['max'])

    # MSGX 文本交叉验证
    T = json.load(open(os.path.join(ROOT, _ROOT + '/scripts/msgx_all_texts.json'),
                       encoding='utf-8'))['texts']
    g = lambda i: T.get(str(i), T.get(i))
    for i, kw in ((0xfda, '洋枪'), (0xfdc, '300支'), (0xfde, '1000')):
        t = g(i)
        chk(f'MSGX {i:#x} 含「{kw}」', t is not None and kw in t)

    out = {'结论': '0x461510(id2 thunk) 的尾跳目标 = 0x461660(数量选择例程) 的返回值',
           '调用链': {'选择器': 'byte[当前武将+7] 与 2 比较',
                      '上位 0x461a30': '阈值15 → 0x461660(15,30,0,1) → 上限300支',
                      '下位 0x461b00': '阈值10 → 0x461660(10,100,0,0) → 上限1000支'},
           '前置门槛': 'word[0x51662e]/10 + word[ctx+4] >= 阈值（不足则弹 0xfcf/0xfdf）',
           '取消': '0x461660 返回 0x7fffffff → 弹 0xfb0 后返回 0',
           '玩法': '铁炮（洋枪）购入', 'MSGX': {hex(k): v for k, v in MSGX.items()}}
    json.dump(out, open(os.path.join(ROOT, _ROOT + '/scripts/evt_id2_teppo.json'), 'w',
                        encoding='utf-8'), ensure_ascii=False, indent=1)
    print(f'\n==== {ok} PASS / {fail} FAIL ====')
    print('saved scripts/evt_id2_teppo.json')
    return 0 if fail == 0 else 1


if __name__ == '__main__':
    raise SystemExit(main())
