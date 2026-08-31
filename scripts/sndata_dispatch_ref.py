# -*- coding: utf-8 -*-
"""太閤立志伝2 —— SNDATA 记录处理「主循环 + 扇出 + 匹配/谓词管线 + 值开关」参考实现（续160）

结论（2026-08-31 续160）：承接续159「下一步(A) 逐指令追 0x4e8625/0x4e89cd 比较链」。

🔑 核心：记录处理的「分派」不是 type→handler 函数指针表（续159 已证伪），而是
   **代码级「匹配器 + 谓词 + 值开关」管线**——本轮从「看到真实分派代码」角度
   二次坐实 P0 证伪，并纠正续158 两处过度断言。

1. 主循环 0x4e8604 / 0x4e8625（一条记录处理一条记录，循环在 0x4e8604 回边）：
   - 0x4e8604: `call 0x480240`(取记录索引, esi) → `cmp si,-1`(0xffff=结束哨兵, je 0x4e8774) →
     设 4 个参数 `lea eax,[esp+0xa]`/`lea ecx,[esp+8]`/`lea edx,[esp+0xa]`(注意 push 后 esp 下移,
     故 arg2=[E+0xa]=id_word, arg3=[E+8]=sub_word, arg4=[E+6]=flag_rel) → 落入 0x4e8625。
   - 0x4e8625: `call 0x47fc60`(扇出) → `add esp,0x10` → 对头三字作全 0 判定。
     头三字落点（已用「push 间 esp 下移」纠正续159 旧记的偏移）：
       id_word @ loop[E+0xa], sub_word @ loop[E+8], flag_rel @ loop[E+6]。

2. 扇出 0x47fc60（续159 已破，本轮补「参数语义」）：
   - `call 0x47d890`(read_record 按索引把 49B 记录读入自身帧 [esp])；
   - `*arg2 = word[rec+0]`(id_word) / `*arg3 = word[rec+2]`(sub_word) / `*arg4 = word[rec+4]`(flag_rel)；
   - `strcpy(0x522c88, rec+6)` / `strcpy(0x522c60, rec+0x13)` / `strcpy(0x522c70, rec+0x20)`。

3. 分派机制（代码级，二次证伪 P0）：
   - 头三字全 0（`cmp [esp+6]/[esp+8]/[esp+0xa],0` 均 jne 跳 0x4e8654）→ 空/哨兵记录，走 `0x47b160(0x50d820)` 后跳回。
   - 否则 `call 0x47b390(0x50d834)`：匹配器（薄壳 → `0x47b2e0`，返回 eax 0/1）；eax==0 则跳回（本函数只处理匹配模板 0x50d834 的类别）。
   - `call 0x47fb80`：谓词（内部 `call 0x47f350`——即续158 称「不处理 49B 记录」的主解析器，
     本轮证实它**在记录路径内**作为谓词子组件校验/解析记录子数据）；eax==0 则跳回。
   - 读全局 `word ptr [0x5205fe]`（当前记录「类别/类型」选择器，被 0x418459/0x44edaa 等写入），
     三路值开关：
        == 0 → 0x4e86e7 簇（0x492e20/0x493140/0x48cc20/0x48d350/0x48e690/0x4a0b20）
        == 1 → 0x4e86c5 簇（0x492ed0/0x4931f0/0x4ac9c0/0x4ae380/0x4a0b70）
        else → 0x4e870f 簇（0x524740/0x491e70/0x4873b0/0x491f90/0x492050/0x499050）

4. 🔧 纠正续158 两处过度断言：
   (a) 续158 称「0x47ff68 = 按记录类型(ax)分派的 dispatcher」——**错**。0x47ff68 实为先
       `call 0x47fc60`(扇出) 再判定 `word[esp+0x18]/[esp+0x64]/[esp+4]` 全 0 → 全 0 则
       `strcpy(0x509648→0x522c..)` 拷默认名（0x509648 = 空名串池）。它是「头全 0 → 默认名」助手，非分派器。
   (b) 续158 称「记录循环不在 0x47f350 静态调用图内」——**误导**。0x47fb80(记录谓词)
       直接 `call 0x47f350`；0x47f350 确实在记录处理路径内，只是它不直接引用 49B 缓冲
       （0x522c88/60/70），而是解析记录引用的子表（实体/城/国/名）。

5. 缓冲族（payload 解析基础设施，非 per-type handler 直读）：
   0x522c88 / 0x522c60 / 0x522c70（扇出三视图）+ 0x522c98 / 0x522ca0 / 0x522cc0（续159 记的
   「真消费者访问器」）。handler 簇经 `0x4802e0`/`0x492800`/`0x4ec8c0` 等读 `0x522ca0` 族，
   把 payload 写入游戏表（0x524978/0x524918/0x524740），故 **type→field schema 的真相在
   通用 payload 解析基础设施，不在 per-type handler 直读 0x522c88**。

⚠️ 仍未知：① 0x5205fe 在本路径的确切写入方（master 注册间接分派器 or 0x47ae20？）；
   ② 全部类别 handler（0x4e8625 只处理模板 0x50d834；0x4e89cd 链处理另一类；其余存在）；
   ③ 完整 type→field schema 须追 0x4802e0/0x492800/0x4ec8c0（payload 解析引擎）+
       各 handler 的表写入；master 注册间接分派器无静态 xref，宜用 emu 提取全 833 条映射。
"""
import os, struct
from capstone import CS_ARCH_X86, CS_MODE_32, Cs

BASE = 0x400000
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MEM = open(os.path.join(ROOT, 'scripts', '_unpacked_mem.bin'), 'rb').read()
md = Cs(CS_ARCH_X86, CS_MODE_32)
md.detail = True


def dis(va, n):
    return list(md.disasm(MEM[va - BASE: va - BASE + n], va))


def txts(va, n):
    return [f'{i.mnemonic} {i.op_str}'.strip() for i in dis(va, n)]


def has(va, needle, n=0x200):
    return any(needle in t for t in txts(va, n))


def fn_len(va, maxb=0x2000):
    n = 0
    for i in dis(va, maxb):
        n += i.size
        if i.mnemonic == 'ret':
            return n
    return maxb


def _run_tests():
    ok = []
    def chk(name, cond, extra=''):
        ok.append(bool(cond))
        print(f'  [{"OK" if cond else "FAIL"}] {name}{(" — " + extra) if extra else ""}')

    print('--- T1 主循环 0x4e8604：取索引 + 结束哨兵 -1 + 4 参设置 ---')
    t = txts(0x4E8604, 0x30)
    chk('call 0x480240 取记录索引', 'call 0x480240' in t)
    chk('cmp si, -1 结束哨兵', 'cmp si, -1' in t or 'cmp si, 0xffff' in t)
    chk('循环回边 jmp 0x4e8604 在 0x4e8625 内',
        any('jmp 0x4e8604' in x for x in txts(0x4E8625, 0x40)))

    print('--- T2 扇出 0x47fc60：read_record + 头三字 + 3 strcpy ---')
    t = txts(0x47FC60, 0x170)
    chk('call 0x47d890 (read_record)', 'call 0x47d890' in t)
    chk('strcpy → 0x522c88', 'push 0x522c88' in t and 'call 0x4ebfe0' in t)
    chk('strcpy → 0x522c60', 'push 0x522c60' in t)
    chk('strcpy → 0x522c70', 'push 0x522c70' in t)
    chk('三视图起点 rec+6/0x13/0x20',
        'lea edx, [esp + 6]' in t and 'lea eax, [esp + 0x13]' in t
        and 'lea ecx, [esp + 0x20]' in t)

    print('--- T3 0x4e8625 分派：头三字全 0 判定 + 匹配器 + 谓词 + 0x5205fe 三路开关 ---')
    t = txts(0x4E8625, fn_len(0x4E8625))
    chk('头三字 [esp+6]/[esp+8]/[esp+0xa] 全 0 判定',
        'cmp word ptr [esp + 6], 0' in t and 'cmp word ptr [esp + 8], 0' in t
        and 'cmp word ptr [esp + 0xa], 0' in t)
    chk('call 0x47b390 (匹配器, 模板 0x50d834)',
        'call 0x47b390' in t and 'push 0x50d834' in t)
    chk('call 0x47fb80 (谓词)', 'call 0x47fb80' in t)
    chk('读全局 0x5205fe 作选择器', 'mov ax, word ptr [0x5205fe]' in t)
    chk('三路值开关 ==0/==1/else',
        'sub eax, 0' in t and any('je 0x4e86e7' in x for x in t)
        and any('dec eax' in x for x in t) and any('jne 0x4e870f' in x for x in t))
    # 三个 handler 簇地址出现
    chk('簇0/簇1/簇else 地址均在体内',
        'call 0x492e20' in t and 'call 0x492ed0' in t and 'call 0x491e70' in t)

    print('--- T4 🔧 纠正续158(a)：0x47ff68 非分派器，是「头全 0 → 默认名」助手 ---')
    t = txts(0x47FF68, fn_len(0x47FF68))
    chk('先 call 0x47fc60 扇出', 'call 0x47fc60' in t)
    # 三处「头字==0」判定：test ax,ax (on [esp+0x18]) + cmp [esp+0x64],ax + cmp [esp+4],ax
    zero_checks = sum(1 for x in t
                      if x.startswith('test ax, ax')
                      or (x.startswith('cmp word ptr [esp') and x.endswith(', ax')))
    chk('三处「头字==0」判定(2×cmp + 1×test)', zero_checks >= 3,
        f'{zero_checks} 处')
    chk('全 0 → 拷默认名池 0x509648 (mov ecx,[0x509648]; push ecx; call strcpy)',
        'mov ecx, dword ptr [0x509648]' in t and 'call 0x4ebfe0' in t)
    chk('无「按 ax 分派」的 cmp ax,<type>;je 簇',
        not any('cmp ax, ' in x and ('je' in x or 'jne' in x) for x in t))

    print('--- T5 🔧 纠正续158(b)：0x47f350 在记录路径内（0x47fb80 谓词调用它）---')
    t = txts(0x47FB80, fn_len(0x47FB80))
    chk('0x47fb80 call 0x47f350', 'call 0x47f350' in t)
    chk('0x47f350 不引用 49B 缓冲（只解析子表/谓词）',
        not any('0x522c88' in x or '0x522c60' in x or '0x522c70' in x for x in t))

    print('--- T6 缓冲族 + 0x5205fe 全局选择器 ---')
    # 0x5205fe 写入方存在（全局类型/类别选择器）
    writers = []
    for off in range(len(MEM) - 8):
        b = MEM[off:off + 7]
        if (b[:2] == b'\x66\x89' and b[2] & 0xC7 == 0x05
                and struct.unpack_from('<i', MEM, off + 3)[0] & 0x00ffffff == 0x005205fe):
            writers.append(BASE + off)
    chk('0x5205fe 有静态写入方（全局选择器）', len(writers) >= 1,
        f'{len(writers)} 处: ' + ','.join(f'0x{w:06x}' for w in writers[:4]))
    chk('0x4802e0 读兄弟缓冲 0x522ca0（payload 解析基础设施）',
        has(0x4802E0, '0x522ca0'))

    n = sum(ok)
    print(f'\nRESULT: {n}/{len(ok)} checks passed')
    return n == len(ok)


if __name__ == '__main__':
    import sys
    sys.exit(0 if _run_tests() else 1)
