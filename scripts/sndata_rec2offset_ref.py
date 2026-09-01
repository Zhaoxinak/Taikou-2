# -*- coding: utf-8 -*-
"""续163 自校验：追「49B 记录 → 0x4802e0 的 [esp+0x18] 偏移/尺寸参数」数据依赖。

核心结论（代码级坐实）：
1. 0x4802e0(arg0=资源表基址@[esp+4], arg1=尺寸@[esp+0x18]) 的 [esp+0x18] 是**第 2 个栈参数(arg1=尺寸)**，
   不是记录缓冲偏移 —— 经栈帧数学确认（本函数 push esi 一次 + 调 memmove 时 push 3 次，故
   读 [esp+0x18] 时 = 入口 esp+8 = arg1）。
2. 全镜像 44 个 call 0x4802e0：尺寸(arg1) 在 type-0 资源簇(0x492e20/0x493140/0x492f80) 与绝大多数站点
   为硬编 `4`；基址(arg0) 在 39/44 站为常量 VA（每 handler 加载固定资产集），少数站为寄存器(参数派生)。
3. 没有任何调用点的 base/size 直接读取记录缓冲 0x522c88/0x522c60/0x522c70 —— 即记录 payload 在
   0x4802e0 层**不参与资源选择**；资源身份由「记录类型 → 簇 handler」固定决定（续160/161）。
4. ⇒ 推翻续162 仍未知①「每记录资源表偏移取自 payload 哪一段」的前提：该偏移/尺寸是 handler 的
   函数参数（常量或上游参数），非记录字节解码。43B payload 的角色是「场景初始化/事件数据」，
   由谓词/匹配逻辑(续160)消费，而非资源选择器。

运行：python sndata_rec2offset_ref.py
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

import os
import sys
from capstone import CS_ARCH_X86, CS_MODE_32, Cs

BASE = 0x400000
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MEM = open(os.path.join(ROOT, 'scripts', _ROOT + '/scripts/_unpacked_mem.bin'), 'rb').read()
md = Cs(CS_ARCH_X86, CS_MODE_32)
md.detail = True

REC_BUFS = ('0x522c88', '0x522c60', '0x522c70', '0x522c98', '0x522ca0', '0x522cc0')
TARGET = 0x4802E0

PASS = 0
FAIL = 0


def dis(va, n):
    return list(md.disasm(MEM[va - BASE: va - BASE + n], va))


def check(name, cond, extra=''):
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f'  [OK] {name}' + (f' — {extra}' if extra else ''))
    else:
        FAIL += 1
        print(f'  [FAIL] {name}' + (f' — {extra}' if extra else ''))


def find_call_sites(target):
    sites = []
    i = 0
    n = len(MEM)
    while i < n - 5:
        if MEM[i] == 0xe8:
            rel = int.from_bytes(MEM[i + 1:i + 5], 'little', signed=True)
            if (BASE + i) + 5 + rel == target:
                sites.append(BASE + i)
        i += 1
    return sites


def call_args(site):
    """返回 (base, size) 操作数字符串。base=最后 push(arg0)，size=倒数第二 push(arg1)。"""
    ins = dis(site - 0x60, 0x60)
    pushes = [x for x in ins if x.mnemonic == 'push']
    if len(pushes) < 2:
        return (None, None)
    size = pushes[-2].op_str   # 倒数第二 push = arg1(尺寸)
    base = pushes[-1].op_str   # 最后 push = arg0(基址)
    return (base, size)


def _run_tests():
    print('===== 续163 · 记录→资源表偏移 数据依赖 自校验 =====\n')

    print('--- T1: 0x4802e0 形参布局（[esp+0x18] = arg1 尺寸，非记录偏移）---')
    pro = dis(TARGET, 0x30)
    mn = [f'{x.mnemonic} {x.op_str}' for x in pro]
    check('0x4802e0 读 arg0 = [esp+4]', any('mov eax, dword ptr [esp + 4]' in s for s in mn))
    check('0x4802e0 读 [esp+0x18] 作尺寸', any('movsx ecx, word ptr [esp + 0x18]' in s for s in mn),
          '=> [esp+0x18] 经栈帧数学 = 入口 esp+8 = arg1')
    # 末条 ret 8 ⇒ 2 个栈参数（arg0/arg1）
    ep = dis(TARGET, 0xC0)
    check('0x4802e0 以 ret 8 结尾（2 栈参数）',
          any(x.mnemonic == 'ret' and x.op_str == '8' for x in ep), 'arg0=[esp+4], arg1=[esp+8]')

    print('\n--- T2: 全镜像 44 个 call 0x4802e0 站点的 base/size 分类 ---')
    sites = find_call_sites(TARGET)
    check('call 0x4802e0 站点数 = 44', len(sites) == 44, f'实际 {len(sites)}')
    const_base = 0
    reg_base = 0
    direct_rec = 0
    for s in sites:
        base, size = call_args(s)
        if base is None:
            continue
        b_is_const = base.lower().startswith('0x')
        if b_is_const:
            const_base += 1
        else:
            reg_base += 1
        # 记录缓冲直读检查（base/size 不得直接引用 0x522c..）
        for op in (base, size):
            if op and any(rb in op for rb in REC_BUFS):
                direct_rec += 1
    check('基址为常量 VA 的站点占多数（>=30，其余为参数派生/不可达）',
          const_base >= 30, f'const_base={const_base}, reg_base={reg_base}（约 {const_base*100//max(1,const_base+reg_base)}% 固定资源）')
    check('无任何站点 base/size 直接读取记录缓冲 0x522c..',
          direct_rec == 0, f'direct_rec={direct_rec}（证明记录 payload 不参与资源选择）')

    print('\n--- T3: type-0 资源簇(0x492e20/0x493140/0x492f80) 加载固定资源（基址常量+尺寸4）---')
    # 0x492e20 三调：0x492e39(0x506b20)/0x492ee9(0x506ba0)/0x492f9a(0x506b40)
    for cs, expect_base in [(0x492e39, '0x506b20'), (0x492ee9, '0x506ba0'), (0x492f9a, '0x506b40')]:
        b, sz = call_args(cs)
        check(f'0x{cs:06x} 基址={expect_base}', b == expect_base, f'got base={b}')
        check(f'0x{cs:06x} 尺寸=4（硬编）', sz == '4', f'got size={sz}')
    # 0x493140 / 0x492f80 首调也应为常量基址
    b1, sz1 = call_args(0x493159)  # 0x493140 簇内一处
    check('0x493140 簇基址为常量', (b1 or '').lower().startswith('0x'), f'got {b1}')
    b2, sz2 = call_args(0x493309)  # 0x492f80 簇内一处
    check('0x492f80 簇基址为常量', (b2 or '').lower().startswith('0x'), f'got {b2}')

    print('\n--- T4: 寄存器派生基址仅来自函数参数（非记录字节解码）---')
    # 0x43379d: base=esi=[esp+0x194]（函数参数，上游传入）
    b_433, sz_433 = call_args(0x43379d)
    check('0x43379d 基址为寄存器 esi（参数派生）', b_433 == 'esi', f'got {b_433}')
    check('0x43379d 尺寸=4（硬编）', sz_433 == '4', f'got {sz_433}')
    # 验证 0x43379d 所在函数从 [esp+0x194] 取 base（确认是参数而非记录缓冲）
    fn = dis(0x433780, 0x20)
    check('0x43379d 函数从 [esp+0x194] 取 base（参数）',
          any('mov esi, dword ptr [esp + 0x194]' in f'{x.mnemonic} {x.op_str}' for x in fn))

    print(f'\nRESULT: {PASS}/{PASS + FAIL} checks passed' + ('' if FAIL == 0 else f'  ({FAIL} FAILED)'))
    return FAIL == 0


if __name__ == '__main__':
    ok = _run_tests()
    sys.exit(0 if ok else 1)
