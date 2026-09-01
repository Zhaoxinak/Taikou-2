# -*- coding: utf-8 -*-
"""
Unicorn 校准：实跑 0x438c60 的「真实落地写块」(0x438cd6..0x438d4f)，
验证 谣言/共享「部署格编辑」原语的精确写入量 = ±4，并验证两道门控：
  (1) section A getLo(a,c) == 0xb (11)
  (2) DEPLOY 部署字符类：arg5==0 时须 ∈ {'/','1','7','9'}(左军)；arg5!=0 时须 ∈ {'+','-','3','5'}(右军)
写入目标：DEPLOY[index]、DEPLOY[index+1]、UNITBUF_A[index](0x512b88)、UNITBUF_B[index](0x512b89) 各 ±4。
其中 index = (B3<<1) + 40*((B3&1)^1) + 80*B4   （B3=arg3=byte[corps+0], B4=arg4=byte[corps+2]）

我们只 emu 真实的写块指令（跳过前导坐标计算与后续的 C++ 字符串构造/报告），
hook 0x438d51 即停。这等价于在真实二进制上实测落地数值，且不受字符串/虚表机制干扰。
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

import struct, sys
from unicorn import Uc, UC_ARCH_X86, UC_MODE_32, UC_HOOK_CODE, UC_HOOK_MEM_UNMAPPED, UC_MEM_FETCH_UNMAPPED
from unicorn.x86_const import (
    UC_X86_REG_ESP, UC_X86_REG_EIP, UC_X86_REG_ESI, UC_X86_REG_EAX, UC_X86_REG_EDX,
    UC_X86_REG_ECX, UC_X86_REG_EBX)

BASE = 0x400000
IMG = open(_ROOT + '/scripts/_unpacked_mem.bin', 'rb').read()
assert len(IMG) == 0x200000, len(IMG)

STACK = 0x600000
SENTINEL = 0x610000
SCRATCH = 0x708000          # arg2 (corps ptr) 指向的可读缓冲
EDIT_START = 0x438cd6       # 真实写块入口
EDIT_END = 0x438d51         # 0x438d4f(add [eax],cl) 紧后一条指令，即停（写块为 0x438cd6..0x438d4f）

DEPLOY = 0x512b60          # ASCII 部署图
UBUF_A = 0x512b88          # 数值单位缓冲 A
UBUF_B = 0x512b89          # 数值单位缓冲 B
GETLO = 0x439050           # getLo(a,c) ; 桩返回可控值

# 左军 / 右军 字符类（与 0x438fa0/0x438fc0 + BATTLE_SPEC.md:130 一致）
# 两类的 ASCII 码相距正好 4：左 -4 → 右，右 +4 → 左（互为镜像）。
LEFT = {'/': 0x2f, '1': 0x31, '7': 0x37, '9': 0x39}
RIGHT = {'+': 0x2b, '-': 0x2d, '3': 0x33, '5': 0x35}

def index_of(B3, B4):
    return ((B3 << 1) + 40 * ((B3 & 1) ^ 1) + 80 * B4) & 0xffff

def patch(mu, va, code):
    mu.mem_write(va, bytes(code))

def build(getlo_ret):
    mu = Uc(UC_ARCH_X86, UC_MODE_32)
    mu.mem_map(BASE, 0x200000)
    mu.mem_write(BASE, IMG)
    mu.mem_map(STACK, 0x10000)
    mu.mem_map(SCRATCH, 0x1000)
    # 部署 + 单位缓冲 + 地形区域均位于 BASE 映像内，无需单独映射
    mu.mem_map(SENTINEL, 0x1000)
    mu.mem_write(SENTINEL, b'\xc3')
    # DEPLOY / 单位缓冲就在 BASE 映像内 (0x512b60..)，清零初始态
    mu.mem_write(DEPLOY, b'\x00' * 0x400)
    mu.mem_write(UBUF_A, b'\x00' * 0x400)
    mu.mem_write(UBUF_B, b'\x00' * 0x400)
    # getLo 桩：mov al,getlo_ret ; ret
    patch(mu, GETLO, b'\xb0' + bytes([getlo_ret & 0xff]) + b'\xc3')
    # 0x43ca10 parity 桩（写块之前调用，返回 0=不跳过）
    patch(mu, 0x43ca10, b'\x33\xc0\xc3')
    return mu

def run_case(B3, B4, cell_char, arg5, getlo_ret, label):
    mu = build(getlo_ret)
    esi = index_of(B3, B4)
    # 预置部署格（测试格 + 右邻）为指定字符；单位缓冲预置为 0
    mu.mem_write(DEPLOY + esi, bytes([cell_char]))
    mu.mem_write(DEPLOY + esi + 1, bytes([cell_char]))
    # 构造写块入口所需的栈帧：
    #   [esp+0x10] = 0x512b89 + esi  (0x438cc9 在真实流程里设置)
    #   [esp+0x428] = arg3 = B3
    #   [esp+0x42c] = arg4 = B4
    #   [esp+0x430] = arg5
    sp = STACK + 0x800
    frame = bytearray(0x440)
    struct.pack_into('<I', frame, 0x10, UBUF_B + esi)   # 0x512b89 + esi
    struct.pack_into('<I', frame, 0x428, B3 & 0xff)
    struct.pack_into('<I', frame, 0x42c, B4 & 0xff)
    struct.pack_into('<I', frame, 0x430, arg5 & 0xff)
    # 写块前还读到 arg2(=0x524... 指针) 与 arg1(0x5133d0) 仅用于后续报告块，写块本身不依赖；
    # 但 0x438c92 读 [esp+0x42c]=B4、0x438c78 此前已读 [esp+0x428]=B3，写块入口 0x438cd6 重读二者。
    mu.mem_write(sp, bytes(frame))
    mu.reg_write(UC_X86_REG_ESP, sp)
    mu.reg_write(UC_X86_REG_ESI, esi)
    mu.reg_write(UC_X86_REG_EBX, UBUF_A + esi)   # 0x438cc3 `lea ebx,[esi+0x512b88]` 在写块之前，mq
    mu.reg_write(UC_X86_REG_EIP, EDIT_START)

    stopped = [False]
    def hook_code(mu, address, size, data):
        if address == EDIT_END:
            stopped[0] = True
            mu.emu_stop()
    mu.hook_add(UC_HOOK_CODE, hook_code)

    def hook_mem(mu, access, address, size, value, data):
        if access == UC_MEM_FETCH_UNMAPPED:
            mu.mem_map(address & ~0xfff, 0x1000)
            return True
        mu.mem_map(address & ~0xfff, 0x1000)
        return True
    mu.hook_add(UC_HOOK_MEM_UNMAPPED, hook_mem)

    try:
        mu.emu_start(EDIT_START, EDIT_END)
    except Exception as e:
        print('  [EXC %s] %s' % (e, label), file=sys.stderr)

    dep0 = mu.mem_read(DEPLOY + esi, 1)[0]
    dep1 = mu.mem_read(DEPLOY + esi + 1, 1)[0]
    ua = mu.mem_read(UBUF_A + esi, 1)[0]
    ub = mu.mem_read(UBUF_B + esi, 1)[0]
    return {'esi': esi, 'dep0': dep0, 'dep1': dep1, 'ua': ua, 'ub': ub}

def main():
    print('coord formula check: index_of(0,0)=%d  index_of(1,0)=%d  index_of(0,1)=%d'
          % (index_of(0,0), index_of(1,0), index_of(0,1)))
    print('%-10s %-4s %-4s %-4s %-4s %-10s %-10s %-10s %-10s %-8s' %
          ('case', 'B3', 'B4', 'char', 'arg5', 'DEPLOY[i]', 'DEPLOY[i+1]', 'UBUF_A', 'UBUF_B', 'result'))
    print('-' * 86)

    # 用例1：左军字符 + arg5=0 + getLo=11  -> 应 -4 (0x39 '9' -> 0x35 '5')；单位缓冲 0 -> 0xfc
    r = run_case(0, 0, LEFT['9'], 0, 11, 'left-arg5=0')
    ok1 = r['dep0'] == 0x35 and r['dep1'] == 0x35 and r['ua'] == 0xfc and r['ub'] == 0xfc
    print('%-10s %-4d %-4d %-4s %-4d %-10s %-10s %-10s %-10s %-8s' %
          ('left-4', 0, 0, "'9'", 0, '%#x' % r['dep0'], '%#x' % r['dep1'], '%#x' % r['ua'], '%#x' % r['ub'], 'PASS' if ok1 else 'FAIL'))

    # 用例2：右军字符 + arg5=0 + getLo=11 -> 0x438fa0 类检查失败 -> 不写
    r = run_case(0, 0, RIGHT['+'], 0, 11, 'right-arg5=0-skip')
    ok2 = r['dep0'] == RIGHT['+'] and r['ua'] == 0 and r['ub'] == 0
    print('%-10s %-4d %-4d %-4s %-4d %-10s %-10s %-10s %-10s %-8s' %
          ('skip-char', 0, 0, "'+'", 0, '%#x' % r['dep0'], '%#x' % r['dep1'], '%#x' % r['ua'], '%#x' % r['ub'], 'PASS' if ok2 else 'FAIL'))

    # 用例3：右军字符 + arg5!=0 + getLo=11 -> +4 (0x2b '+' -> 0x2f '/')；单位缓冲 0 -> 0x04
    r = run_case(0, 0, RIGHT['+'], 1, 11, 'right-arg5=1')
    ok3 = r['dep0'] == 0x2f and r['dep1'] == 0x2f and r['ua'] == 0x04 and r['ub'] == 0x04
    print('%-10s %-4d %-4d %-4s %-4d %-10s %-10s %-10s %-10s %-8s' %
          ('right+4', 0, 0, "'+'", 1, '%#x' % r['dep0'], '%#x' % r['dep1'], '%#x' % r['ua'], '%#x' % r['ub'], 'PASS' if ok3 else 'FAIL'))

    # 用例4：左军字符 + arg5=0 + getLo=5(≠11) -> section A 门控失败 -> 不写
    r = run_case(0, 0, LEFT['9'], 0, 5, 'getLo!=11-skip')
    ok4 = r['dep0'] == LEFT['9'] and r['ua'] == 0 and r['ub'] == 0
    print('%-10s %-4d %-4d %-4s %-4d %-10s %-10s %-10s %-10s %-8s' %
          ('gate-A', 0, 0, "'9'", 0, '%#x' % r['dep0'], '%#x' % r['dep1'], '%#x' % r['ua'], '%#x' % r['ub'], 'PASS' if ok4 else 'FAIL'))

    print('-' * 86)
    allok = ok1 and ok2 and ok3 and ok4
    print('ALL PASS' if allok else 'SOME FAILED')
    return 0 if allok else 1

if __name__ == '__main__':
    sys.exit(main())
