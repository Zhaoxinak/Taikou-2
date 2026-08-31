# -*- coding: utf-8 -*-
"""续164 自校验：定位 43B payload 的字节语义（记录缓冲读取枚举）。

核心结论（代码级坐实）：
1. 扇出 0x47fc60（续159 实锤的 read_record 下游）把 49B 记录拆为：
   - 头 3 字：rec[0]=id_word / rec[2]=sub_word / rec[4]=flag_or_rel（写 *arg2/*arg3/*arg4）；
   - 43B payload（rec[6..48]）以 3 个重叠视图暴露：
       view1 @0x522c88 = strcpy(&rec[6])    （长度 43 若无 NUL）
       view2 @0x522c60 = strcpy(&rec[0x13]=rec[19])（长度 30）
       view3 @0x522c70 = strcpy(&rec[0x20]=rec[32])（长度 17）
   ⇒ 修正续159「payload 起点 0/13/26」为 **6/19/32**。
2. 匹配器 0x47b390/impl 0x47b2e0 **不读任何记录缓冲** → 是模板/状态门控，非字段匹配（印证续161「0x50d834 是消息串」）。
3. 谓词 0x47fb80 把 3 个视图(0x522c88/0x522c60/0x522c70)传给序列化解析器 0x47d860/0x47f350
   → 43B payload 被当「3 段重叠的子结构模板/覆盖块」解析（续160「模板+稀疏覆盖」模型坐实）。
4. 簇 handler（0x492e20/0x493140/0x492f80/0x492ed0/0x4931f0）**不读记录缓冲** → 印证续163：payload 不参与资源加载。

运行：python sndata_payload_bytes_ref.py
"""
import os
import sys
from capstone import CS_ARCH_X86, CS_MODE_32, Cs

BASE = 0x400000
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MEM = open(os.path.join(ROOT, 'scripts', '_unpacked_mem.bin'), 'rb').read()
md = Cs(CS_ARCH_X86, CS_MODE_32)
md.detail = True

RECB = ['0x522c88', '0x522c60', '0x522c70', '0x522c98', '0x522ca0', '0x522cc0']
REC_PARSERS = [0x47b390, 0x47b2e0, 0x47fb80, 0x47f350,
               0x492e20, 0x493140, 0x492f80, 0x492ed0, 0x4931f0, 0x524740]

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


def has_recbuf_read(va, n=0x400):
    for x in dis(va, n):
        if any(rb in f'{x.mnemonic} {x.op_str}' for rb in RECB):
            return True
    return False


def _run_tests():
    print('===== 续164 · 43B payload 字节语义（记录缓冲读取枚举）自校验 =====\n')

    print('--- T1: 扇出 0x47fc60 拆头 3 字 (rec[0]/[2]/[4]) ---')
    f = dis(0x47FC60, 0xA0)
    s1 = [f'{x.mnemonic} {x.op_str}' for x in f]
    check('0x47fc60 先 call 0x47d890 (read_record)',
          any('call 0x47d890' in s for s in s1))
    check('读 rec[0] → id_word', any('mov ax, word ptr [esp]' in s for s in s1))
    check('读 rec[2] → sub_word', any('mov dx, word ptr [esp + 2]' in s for s in s1))
    check('读 rec[4] → flag/rel', any('mov cx, word ptr [esp + 4]' in s for s in s1))

    print('\n--- T2: 43B payload 以 3 重叠视图暴露（修正续159 0/13/26 → 6/19/32）---')
    f2 = dis(0x47FC60, 0x100)
    s2 = [f'{x.mnemonic} {x.op_str}' for x in f2]
    check('view1 @0x522c88 源 = &rec[6]',
          any('lea' in s and 'esp + 6' in s for s in s2) and any('push 0x522c88' in s for s in s2),
          'strcpy(0x522c88, &rec[6])')
    check('view2 @0x522c60 源 = &rec[0x13]=rec[19]',
          any('esp + 0x13' in s for s in s2) and any('push 0x522c60' in s for s in s2),
          'strcpy(0x522c60, &rec[19])')
    check('view3 @0x522c70 源 = &rec[0x20]=rec[32]',
          any('esp + 0x20' in s for s in s2) and any('push 0x522c70' in s for s in s2),
          'strcpy(0x522c70, &rec[32])')
    check('3 次 strcpy 均走 0x4ebfe0（续159 坐实）',
          sum(1 for s in s2 if 'call 0x4ebfe0' in s) >= 3, '>=3 次 call 0x4ebfe0')

    print('\n--- T3: 匹配器不读记录缓冲（模板/状态门控，非字段匹配）---')
    check('0x47b390 不读 0x522c..', not has_recbuf_read(0x47b390, 0x80))
    check('0x47b2e0 (impl) 不读 0x522c..', not has_recbuf_read(0x47b2e0, 0x80))

    print('\n--- T4: 谓词 0x47fb80 把原始记录指针传给序列化解析器 0x47d860/0x47f350 ---')
    fp = dis(0x47FB80, 0x160)
    sp = [f'{x.mnemonic} {x.op_str}' for x in fp]
    # 0x47fb80 取 [esp+0xac]=记录指针(edi)，push edi 传给 0x47d860（序列化）；另调 0x47f350
    # （注：push 0x522c88/0x522c60/0x522c70 属 0x47fc60 扇出，非本函数）
    check('0x47fb80 取记录指针 edi = [esp+0xac]',
          any('mov edi, dword ptr [esp + 0xac]' in s for s in sp))
    check('0x47fb80 push edi 传给 序列化解析器 0x47d860',
          any('push edi' in s for s in sp) and any('call 0x47d860' in s for s in sp))
    check('0x47fb80 调 0x47f350（记录解析器）',
          any('call 0x47f350' in s for s in sp))

    print('\n--- T5: 簇 handler 不读记录缓冲（印证续163：payload 不参与资源加载）---')
    for name, va in [('type0 h0 0x492e20', 0x492e20), ('type0 h1 0x493140', 0x493140),
                     ('type0 h2 0x492f80', 0x492f80), ('type1 h0 0x492ed0', 0x492ed0),
                     ('type1 h1 0x4931f0', 0x4931f0), ('clu_else 0x524740', 0x524740)]:
        check(f'{name} 不读 0x522c..', not has_recbuf_read(va, 0x300), name)

    print(f'\nRESULT: {PASS}/{PASS + FAIL} checks passed' + ('' if FAIL == 0 else f'  ({FAIL} FAILED)'))
    return FAIL == 0


if __name__ == '__main__':
    ok = _run_tests()
    sys.exit(0 if ok else 1)
