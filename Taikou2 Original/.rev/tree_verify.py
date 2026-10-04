"""tree_verify.py — 校验 .fdata 节里的树形渲染机器码(清单驱动, 由 build 导出的 tree_blobs.json 描述)

检查:
  1) 每个 blob 能连续反汇编, 字节数吻合, 结尾是 ret 或 jmp(尾调用/内部收敛)
  2) 所有 `call dword ptr [0x1360xx]` 都落在 GDI_TAB(20 槽)或 IAT(GetModuleHandleA/GetProcAddress)
  3) 所有 call/jmp/jcc 的相对目标都落在本节代码区内
  4) FAM_DIR / NODE_TAB 数据自洽(坐标、状态、父索引、本人标记、串偏移)
     FAM_DIR 每条 24B, NODE_TAB 每条 10B, 串池为 [u8 len][bytes][NUL]
"""
import json
import struct
import sys

sys.stdout.reconfigure(encoding='utf-8')
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

M = json.load(open('tree_blobs.json'))
EXE = sys.argv[1] if len(sys.argv) > 1 else \
    r'F:\Games\Taikou 2\Taikou2 Original\TAIK2W95_family.exe'
SEC_VA, SEC_PTR, SEC_SZ = M['sec_va'], M['sec_ptr'], M['sec_sz']
IMAGE_BASE = 0x400000
SIZE_OF_IMAGE = (SEC_VA - IMAGE_BASE) + SEC_SZ   # 随节大小自动跟涨(v8: 0x5400)
IMG_LO, IMG_HI = IMAGE_BASE, IMAGE_BASE + SIZE_OF_IMAGE
O_CODE = M['o_code']
CODE_VA, CODE_LO, CODE_HI = SEC_VA + O_CODE, SEC_VA + O_CODE, SEC_VA + SEC_SZ
GDI_TAB_VA, N_API = M['gdi_tab'], M['n_api']
IAT = (0x4FB138, 0x4FB0E0)
# 本节的机器码允许跳去的"外部"目标 —— 白名单式, 写死在这里,
# 任何不在名单里的外部 call/jmp 仍然算错(防止误跳)。
CAVE_LO, CAVE_HI = 0x535000, 0x536000     # 旧代码洞: ft_kbd/ft_click/nav_click/修复跳板…
EXT_OK = {
    0x4EEFA0: '游戏: 模态等待泵(入口)',
    0x4EEFA5: '游戏: 模态等待泵(入口+5, 跳板返回点)',
    0x4EE0D0: '游戏: 事件队列查询(入口)',
    0x4EE0D7: '游戏: 事件队列查询(入口+7, 跳板返回点)',
    0x4989F2: '游戏: 卡片等待循环(4989E3)的泵返回点',
    0x4BA0EC: '游戏: 卡片等待循环(4BA0DD)的泵返回点',
}

buf = open(EXE, 'rb').read()
assert len(buf) == SEC_PTR + SEC_SZ, '文件尾与新节 raw 不吻合 %d vs %d' % (len(buf), SEC_PTR + SEC_SZ)
sec = buf[SEC_PTR:SEC_PTR + SEC_SZ]

md = Cs(CS_ARCH_X86, CS_MODE_32); md.detail = True
rc = 0
tot = 0
JCC = ('je', 'jne', 'jb', 'jae', 'jz', 'jnz', 'jbe', 'ja', 'jg', 'jl', 'jge', 'jle', 'js', 'jns')
# 手写汇编最容易踩的坑: 把 "0F E9" 当成无条件相对跳转。
# x86 里 0F E9 实为 MMX 指令 psubsw, 一旦生成就会读野地址 -> 崩溃。
SIMD_HINT = ('psub', 'padd', 'pand', 'por', 'pxor', 'pmul', 'pavg', 'pmin',
             'pmax', 'pcmpgt', 'movq', 'movd', 'punpck', 'packss', 'packus')
for b in M['blobs']:
    name, off, size = b['name'], b['off'], b['size']
    va = SEC_VA + O_CODE + off
    data = sec[O_CODE + off: O_CODE + off + size]
    ins = list(md.disasm(data, va))
    nb = sum(len(i.bytes) for i in ins)
    last = ins[-1].mnemonic if ins else '(空)'
    ok = (nb == size) and last in ('ret', 'jmp')
    print('%-12s %4dB  %3d 指令  %s' % (name, size, len(ins), 'OK' if ok else '!! 尾部=%s 覆盖=%d/%d' % (last, nb, size)))
    if not ok:
        rc = 1
    tot += size
    for i in ins:
        mn, t = i.mnemonic, i.op_str
        if mn.startswith(SIMD_HINT):
            print('   !! 出现 SIMD 指令 @0x%06X: %s %s  (多半是 0F Ex 被误当跳转)'
                  % (i.address, mn, t)); rc = 1
        if mn == 'call' and t.startswith('dword ptr ['):
            a = int(t[t.index('[') + 1:-1], 16)
            if a in IAT:
                continue
            if not (GDI_TAB_VA <= a < GDI_TAB_VA + N_API * 4):
                print('   !! call %s 不在 GDI_TAB' % t); rc = 1
        elif (mn in ('call', 'jmp') or mn in JCC) and t.startswith('0x'):
            a = int(t, 16)
            if not (CODE_LO <= a < CODE_HI) and not (CAVE_LO <= a < CAVE_HI) \
                    and a not in EXT_OK:
                print('   !! %s %s 跳出代码区' % (mn, t)); rc = 1
        # ★ 绝对地址必须落在 PE 映像内 —— 挡住 "把节 RVA 当成 VA" 这类错误。
        #   映像区间: ImageBase 0x400000 + SizeOfImage 0x139000 = [0x400000, 0x539000)
        for op in i.operands:
            if op.type == 2 and op.mem and op.mem.base == 0 and op.mem.index == 0 \
                    and op.mem.disp and not any(s in t for s in ('[', ':')):
                d = op.mem.disp
                if not (IMG_LO <= d < IMG_HI) and d not in IAT \
                        and not (GDI_TAB_VA <= d < GDI_TAB_VA + N_API * 4):
                    print('   !! 绝对地址 0x%08X 落在映像外 @0x%06X: %s %s'
                          % (d, i.address, mn, t)); rc = 1
print('OK  渲染代码合计 %d B, 区域内 0x%06X-0x%06X' % (tot, CODE_LO, CODE_HI))

# ---- 数据区 ----
O_FAMDIR = M['famdir'] - SEC_VA
O_NODES = M['nodes'] - SEC_VA
O_POOL = M['pool'] - SEC_VA
DIR_SZ, NODE_SZ = 24, 10
ND = M['ndir']
# 真实节点总数: v8 起多个 FAM_DIR 条目(别名触发)会共享同一家族区间,
# 不能再对每条 cnt 求和(会重复计), 直接用 build 导出的 nnode。
NN = M['nnode']
dirs = []
for k in range(ND):
    e = sec[O_FAMDIR + k * DIR_SZ: O_FAMDIR + (k + 1) * DIR_SZ]
    nm, su, st, cnt, to = struct.unpack('<IIBBH', e[:12])
    cx0, cy0, cx1, cy1 = struct.unpack('<hhhh', e[12:20])
    subj, _p0, _p1 = struct.unpack('<BBH', e[20:24])
    assert 0 <= st < NN and 0 < cnt <= NN, (k, st, cnt)
    assert st + cnt <= NN, ('区间越界', k, st, cnt)
    assert 0 <= subj < cnt, ('本人索引越界', k, subj)
    assert cx0 < cx1 and cy0 < cy1, ('内容框无效', k, cx0, cy0, cx1, cy1)
    dirs.append((st, cnt, cx0, cy0, cx1, cy1, subj, to))

def pool_str(o):
    o = O_POOL + o
    n = sec[o]
    return sec[o + 1:o + 1 + n].decode('gbk')

print('OK  FAM_DIR %d 条, 区间/本人索引/内容框均合法' % ND)
nn = 0
bbox_ok = 0
for k in range(NN):
    n = sec[O_NODES + k * NODE_SZ: O_NODES + (k + 1) * NODE_SZ]
    cx, cy, no, ro, par, fl = struct.unpack('<hhHHBB', n)
    owner = [d for d in dirs if d[0] <= k < d[0] + d[1]]
    assert owner, ('节点无所属家族', k)
    st, cnt, cx0, cy0, cx1, cy1, subj, to = owner[0]
    assert cx0 <= cx <= cx1 and cy0 <= cy <= cy1, ('节点超出内容框', k, cx, cy)
    assert fl & 3 <= 2, (k, fl)
    assert par == 0xFF or par < cnt, ('父索引越界(族内)', k, par, cnt)
    if fl & 8:                                    # F_SPOUSE: 渲染层要解引用丈夫节点
        assert par != 0xFF, ('配偶节点无 parent', k)
        pfl = struct.unpack_from('<B', sec, O_NODES + (st + par) * NODE_SZ + 9)[0]
        assert not pfl & 8, ('丈夫节点也标了配偶(链式?)', k)
    for o in (no, ro):
        assert o < O_CODE - O_POOL, (k, o)
        pool_str(o)
    nn += 1
    bbox_ok += 1
print('OK  NODE_TAB 有效节点 %d 个, 坐标/状态/父索引/串偏移均合法' % nn)

# 每族「本人」标记恰好一个, 且拼出的姓名与 FAM_DIR 里的触发者一致
for k, (st, cnt, cx0, cy0, cx1, cy1, subj, to) in enumerate(dirs):
    sub = [i for i in range(st, st + cnt)
           if struct.unpack_from('<BB', sec, O_NODES + i * NODE_SZ + 8)[1] & 4]
    assert sub == [st + subj], ('本人标记不唯一/不符', k, sub, subj)
print('OK  每族「本人」标记唯一, 且与 subject 索引一致')

for bad in ('\x00\x00\x00\x00',):
    assert bad.encode() not in sec[O_POOL:O_POOL + 0x600][:4], '串池首条异常'
names = [pool_str(d[7]) for d in dirs]
print('OK  家族标题: %s' % ' / '.join(names))

hint = '点人物=详情      方向键/拖拽=移动      ESC/点空白=关闭\x00'.encode('gbk')
assert hint in sec, '底部提示串缺失'
print('OK  提示串存在: %s' % hint.decode('gbk').rstrip('\x00'))

print('\n结果:', 'PASS' if rc == 0 else 'FAIL')
sys.exit(rc)
