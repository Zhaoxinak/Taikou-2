# -*- coding: utf-8 -*-
"""太閤立志伝2 —— SNDATA payload 解析引擎（0x4802e0/0x492800/0x4ec8c0/0x4f40b0）参考实现（续162）

承接续161「下一步(A) 追 payload 解析引擎逐字段偏移」。

🔑 核心结论（2026-08-31 续162）：所谓「payload 解析引擎」实为**资源加载管线**，
   不是「43B 字节 → 游戏表字段」的扁平映射器。结构：

   ① `0x4f40b0` = **memmove**（重叠感知：先 `cmp edi,esi`/`cmp edi,eax(=esi+ecx)`
      做边界判定，再 `rep movsd`）。
   ② `0x492800` = 3 参转发到 `0x4f40b0`（`memmove(dst, src, n)` 实参重排）。
   ③ `0x4802e0(this=句柄, 资源表)` = `memmove(0x522ca0, 资源表, 0x20)`（把类别资源表
       前 2 项拷入缓冲 0x522ca0）+ `0x4ec8c0(this, 0x522ca0)` 注册资源选择器；返回 eax=句柄有效性。
   ④ `0x4ec8c0(this, buf)` = **资源选择器构造器**：`strcpy(局部, buf+2)`（剥 `X:` 盘符前缀）
      读资源名；`al &= 0xfb` 取类型字节；`cmp eax,3; ja` 4 路 switch（跳表 0x4ec948）
      → 尺寸 `0/1/2/0x1000` → `call dword ptr [0x4fb07c]`（注册式加载器回调，运行期填入）。
   ⑤ 类别 = 一组资源加载器：**每个簇 handler 引用资源表的不同条目**（0x492e20→0x506b20、
      0x493140→0x506b30、0x492f80→0x506b40 …），即 6 资源（MAPCHIP/MAPCHAR/SHOP_BG/
      SHOP_OBJ/SHOP_MSK/ANMSEQ）各一 handler；handler 经 `0x441330`/`0x441360`（`call dword
      ptr [0x4fb0a8]` 同 read_record 的 lseek/read 派发 + `call 0x441170` 读）把资源文件内容
      写入游戏表 `0x524978`（主）/`0x524918`（副）。
   ⑥ 失败路径 `0x47bde0`：资源未加载 → `push 0x5094d0; call 0x47ae80` 记错误日志，返回 1（no-op）。

⇒ **续161「类别作用域资源表」模型精修**：类别 handler 簇不是「读 49B 记录的字段」，
   而是「按记录给出的**资源表偏移 + 类型字节**加载对应资源文件，资源文件解析内容填游戏表」。
   故资源支撑类别的「逐字段偏移」不在 49B 记录内，而在**被加载的资源文件**（LZW/PK8）里——
   这正是续156 已破的 HEXMES.LZW/MSGX 解包路径的同类工作。要拿到真实 byte→field，
   须解包资源文件（下一步 B）。

⚠️ 仍未知：① 每记录的「资源表偏移」具体取自 payload 哪一段（0x4802e0 读 `[esp+0x18]` 来自
   调用方帧，须追 0x492e20 如何由 record 算出该偏移）；② `[0x4fb07c]` 真实加载器（静态镜像
   此处为 0x3000，运行期由初始化写入）；③ 资源文件（如 MAPCHIP.LZW）解析后如何映射到
   0x524978 的逐字段（须解包资源文件，续156 同类）。
"""
import os, struct, re
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


def rd(va, n):
    return MEM[va - BASE: va - BASE + n]


def mainloop_txt():
    # 0x4e8625 主循环（续160 已坐实），确认它最终落到本引擎的 handler 簇
    return txts(0x4E8625, 0x80)


def _run_tests():
    ok = []
    def chk(name, cond, extra=''):
        ok.append(bool(cond))
        print(f'  [{"OK" if cond else "FAIL"}] {name}{(" — " + extra) if extra else ""}')

    print('--- T1 0x4f40b0 = memmove（重叠感知 + rep movsd）---')
    t = txts(0x4F40B0, 0x80)
    full = '\n'.join(t)
    chk('rep movsd 存在', 'movsd' in full, 'memcpy/memmove 核心')
    chk('边界判定 cmp edi, esi', 'cmp edi, esi' in full)
    chk('重叠判定 cmp edi, eax(=esi+ecx)', 'cmp edi, eax' in full)
    chk('短转移 jbe/jb（重叠分支）',
        any('jbe' in s for s in t) and any('jb ' in s for s in t))

    print('--- T2 0x492800 = 转发到 memmove 0x4f40b0 ---')
    t = txts(0x492800, 0x30)
    chk('call 0x4f40b0', 'call 0x4f40b0' in t)

    print('--- T3 0x4802e0 = memmove(0x522ca0, 资源表, 0x20) + 调 0x4ec8c0 ---')
    t = txts(0x4802E0, 0x40)
    full = '\n'.join(t)
    chk('push 0x20（n）', 'push 0x20' in t)
    chk('push 0x522ca0（dst）', 'push 0x522ca0' in t)
    chk('call 0x492800（memmove 转发）', 'call 0x492800' in t)
    chk('push 0x522ca0 后 call 0x4ec8c0（注册选择器）',
        ('push 0x522ca0' in t) and ('call 0x4ec8c0' in t))
    chk('读选择器字 movsx ecx, word ptr [esp+0x18]',
        'movsx ecx, word ptr [esp + 0x18]' in t or 'movsx ecx, word ptr [esp+0x18]' in t)

    print('--- T4 0x4ec8c0 = 资源选择器构造器（strcpy 剥盘符 + &0xfb + 4 路 switch + 注册）---')
    t = txts(0x4EC8C0, 0x80)
    full = '\n'.join(t)
    chk('strcpy(local, arg1+2) 剥 X: 盘符', 'call 0x4ebfe0' in t)
    chk('and al, 0xfb（类型字节掩码）', 'and al, 0xfb' in t)
    chk('cmp eax, 3 + ja（4 路 switch）', 'cmp eax, 3' in t and ('ja' in full))
    chk('jmp dword ptr [eax*4+0x4ec948]（跳表）', 'jmp dword ptr [eax*4 + 0x4ec948]' in t)
    chk('尺寸三态 push 0 / 1 / 2 / 0x1000',
        'push 0' in t and 'push 1' in t and 'push 2' in t and 'push 0x1000' in t)
    chk('call dword ptr [0x4fb07c]（注册加载器回调）', 'call dword ptr [0x4fb07c]' in t)

    print('--- T5 跳表 0x4ec948：4 项 → 4 个尺寸 push 现场 ---')
    tbl = rd(0x4EC948, 16)
    targets = [struct.unpack_from('<I', tbl, k * 4)[0] for k in range(4)]
    chk('4 项全落在 0x4ec8c0 函数内', all(0x4EC8C0 <= tg < 0x4EC8C0 + 0x80 for tg in targets),
        str([f'0x{tg:06x}' for tg in targets]))
    # 尺寸 push 现场：0x4ec8f3→push0 / 0x4ec8f7→push1 / 0x4ec8f2→push2 / 0x4ec911→push0x1000
    site0 = txts(targets[0], 6)
    site1 = txts(targets[1], 6)
    site2 = txts(targets[2], 6)
    site3 = txts(targets[3], 6)
    chk('case0 → push 0', 'push 0' in '\n'.join(site0), str(site0))
    chk('case1 → push 1', 'push 1' in '\n'.join(site1), str(site1))
    chk('case2 → push 2', 'push 2' in '\n'.join(site2), str(site2))
    chk('case3 → push 0x1000', 'push 0x1000' in '\n'.join(site3), str(site3))

    print('--- T6 类别 = 6 资源加载器：每个簇 handler 引用资源表不同条目 ---')
    t0 = txts(0x492E20, 0x90)
    t1 = txts(0x493140, 0x90)
    t2 = txts(0x492F80, 0x90)
    chk('0x492e20 push 0x506b20（entry0 MAPCHIP）', 'push 0x506b20' in t0)
    chk('0x493140 push 0x506b30（entry1 MAPCHAR）', 'push 0x506b30' in t1)
    chk('0x492f80 push 0x506b40（entry2 SHOP_BG）', 'push 0x506b40' in t2)
    # 这些 handler 后续写游戏表 0x524978 / 0x524918（引用在 0x492e57 / 0x492e94，须拉长反汇编）
    chk('0x492e20 写游戏表 0x524978', '0x524978' in '\n'.join(t0))
    chk('0x492e20 写游戏表 0x524918', '0x524918' in '\n'.join(t0))

    print('--- T7 资源读取走文件 I/O（0x4fb0a8 同 read_record 派发 + 0x441170 读）---')
    tA = txts(0x441330, 0x40)
    tB = txts(0x441360, 0x90)
    chk('0x441330 call dword ptr [0x4fb0a8]（lseek/read 派发）', 'call dword ptr [0x4fb0a8]' in tA)
    chk('0x441330 call 0x441170（读原语）', 'call 0x441170' in tA)
    chk('0x441360 经 edi 调 [0x4fb0a8]（mov edi,[0x4fb0a8]; call edi）',
        'mov edi, dword ptr [0x4fb0a8]' in tB and 'call edi' in tB)
    chk('0x441360 call 0x441170', 'call 0x441170' in tB)

    print('--- T8 失败路径 0x47bde0 = 记资源未找到日志（0x5094d0 + 0x47ae80）---')
    t = txts(0x47BDE0, 0x18)
    chk('push 0x5094d0（错误消息串）', 'push 0x5094d0' in t)
    chk('call 0x47ae80（日志/报错）', 'call 0x47ae80' in t)

    print('--- T9 [0x4fb07c] = 运行期填入的加载器回调槽（静态非代码地址）---')
    fp = struct.unpack_from('<I', rd(0x4FB07C, 4), 0)[0]
    chk('[0x4fb07c] 静态 < 0x400000（非本映像代码，运行期写入）',
        fp < BASE, f'0x{fp:06x}')

    n = sum(ok)
    print(f'\nRESULT: {n}/{len(ok)} checks passed')
    return n == len(ok)


if __name__ == '__main__':
    import sys
    sys.exit(0 if _run_tests() else 1)
