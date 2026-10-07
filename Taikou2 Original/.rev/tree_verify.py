"""tree_verify.py — 校验 .fdata 节里的树形渲染机器码(清单驱动, 由 build 导出的 tree_blobs.json 描述)

检查:
  1) 每个 blob 能连续反汇编, 字节数吻合, 结尾是 ret 或 jmp(尾调用/内部收敛)
  2) 所有 `call dword ptr [0x1360xx]` 都落在 GDI_TAB(20 槽)或 IAT(GetModuleHandleA/GetProcAddress)
  3) 所有 call/jmp/jcc 的相对目标都落在本节代码区内
  4) FAM_DIR / NODE_TAB 数据自洽(坐标、状态、父索引、本人标记、串偏移)
     FAM_DIR 每条 24B, NODE_TAB 每条 10B, 串池为 [u8 len][bytes][NUL]
"""
import json
import os
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
# 族谱节必须完整落到文件尾方向; big.exe 在 .fdata 之后还挂 .edata(实体池), 故允许尾部更大。
assert len(buf) >= SEC_PTR + SEC_SZ, '文件尾缺 .fdata raw %d < %d' % (len(buf), SEC_PTR + SEC_SZ)
if len(buf) != SEC_PTR + SEC_SZ:
    print('注: 文件尾另有 %d B (big.exe 的 .edata 实体池节), 跳过精确等长校验'
          % (len(buf) - SEC_PTR - SEC_SZ))
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
O_OID = M['oidtab'] - SEC_VA
O_DET = M['detailtab'] - SEC_VA
DIR_SZ, NODE_SZ = 24, 10
ND = M['ndir']
NN = M['nnode']
SLOTS = M['dyn_slots']
DSZ = M['dyn_str_sz']
GEN_FLAG = M['gen_flag']
GEN_START = (M['gen_nodes_va'] - M['nodes']) // NODE_SZ   # 清单给的是字节差, 换成节点序号
# ★ v13: FAM_DIR+8 的 start 是 **/2 编码**(渲染层 START_MUL = 2*NODE_SZ = 20), 先还原成节点序号。
#   真实节点总数仍用 build 导出的 nnode(v8 起多条别名触发共享同一区间, 不能对 cnt 求和)。
dirs = []
for k in range(ND):
    e = sec[O_FAMDIR + k * DIR_SZ: O_FAMDIR + (k + 1) * DIR_SZ]
    nm, su, st2, cnt, to = struct.unpack('<IIBBH', e[:12])
    cx0, cy0, cx1, cy1 = struct.unpack('<hhhh', e[12:20])
    subj, sn, flag, pad = struct.unpack('<BBBB', e[20:24])
    st = st2 * 2
    assert 0 <= st < NN and 0 < cnt <= NN, (k, st, cnt)
    assert flag in (0, GEN_FLAG), ('+22 只能是 0 或通用标记', k, flag)
    assert pad == 0, ('+23 保留字节被写了', k, pad)
    assert cnt == sn, ('构建期 count(+9) 必须等于 static_n(+21)', k, cnt, sn)
    assert 0 <= subj < cnt, ('本人索引越界', k, subj, cnt)
    assert cx0 < cx1 and cy0 < cy1, ('内容框无效', k, cx0, cy0, cx1, cy1)
    dirs.append(dict(st=st, cnt=cnt, bbox=(cx0, cy0, cx1, cy1), subj=subj, to=to,
                     sn=sn, flag=flag, nm=nm, su=su, k=k))


def pool_str(o):
    o = O_POOL + o
    n = sec[o]
    return sec[o + 1:o + 1 + n].decode('gbk')


# ---- 家族块边界: NODE_TAB 里各块连续排布, 块尾 = 下一个唯一 start ----
_starts = sorted({d['st'] for d in dirs})
_blk = {s: (_starts[i + 1] if i + 1 < len(_starts) else NN) for i, s in enumerate(_starts)}
owner_of = [None] * NN
for _s in _starts:
    for _k in range(_s, _blk[_s]):
        owner_of[_k] = _s
by_start = {}
for d in dirs:
    by_start.setdefault(d['st'], []).append(d)

# 每条记录覆盖 [start, block) = 静态人数 + 烘死的隐藏子嗣槽(+ 凑偶填充 1 个)
for d in dirs:
    bl = _blk[d['st']] - d['st']
    assert bl % 2 == 0, ('块长未凑偶, start/2 会错', d['k'], bl)
    if d['flag']:
        assert d['st'] == GEN_START and bl == M['gen_static_n'] + SLOTS + 1, \
            ('通用块形状变了', d['k'], d['st'], bl)
        assert d['nm'] == 0 and d['su'] == 0, '通用块触发键必须全 0(不参与姓名扫描)'
        assert d['st'] == (_starts[-1]), '通用块必须是最后一条 FAM_DIR'
    else:
        assert SLOTS <= bl - d['sn'] <= SLOTS + 1, ('静态段之外的节点数不对', d['k'], d['sn'], bl)
        assert d['st'] != GEN_START, '史实家族占到了通用块的节点区'
assert len(_starts) == len(by_start) and _blk[_starts[-1]] == NN
print('OK  FAM_DIR %d 条 / %d 个家族块 (start 按 /2 编码), count==static_n, 隐藏子嗣槽 %d~%d 个'
      % (ND, len(_starts), SLOTS, SLOTS + 1))

nn = 0
for k in range(NN):
    n = sec[O_NODES + k * NODE_SZ: O_NODES + (k + 1) * NODE_SZ]
    cx, cy, no, ro, par, fl = struct.unpack('<hhHHBB', n)
    st = owner_of[k]
    assert st is not None, ('节点无所属家族', k)
    d0 = by_start[st][0]
    cx0, cy0, cx1, cy1 = d0['bbox']
    assert cx0 <= cx <= cx1 and cy0 <= cy <= cy1, ('节点超出内容框', k, cx, cy)
    assert fl & 3 <= 2, (k, fl)
    bl = _blk[st] - st
    assert par == 0xFF or par < bl, ('父索引越界(族内)', k, par, bl)
    if fl & 8:                                    # F_SPOUSE: 渲染层要解引用丈夫节点
        assert par != 0xFF, ('配偶节点无 parent', k)
        pfl = struct.unpack_from('<B', sec, O_NODES + (st + par) * NODE_SZ + 9)[0]
        assert not pfl & 8, ('丈夫节点也标了配偶(链式?)', k)
    for o in (no, ro):
        assert o < O_CODE - O_POOL, (k, o)
        pool_str(o)
    if st + d0['sn'] <= k < bl + st:              # 隐藏子嗣槽 / 凑偶填充
        if fl & 0x10:                             # F_DYN: 名字运行时才写进池首 => 构建期必空
            assert no // DSZ < SLOTS and no % DSZ == 0, ('动态槽名字不指池首可变区', k, no)
            assert pool_str(no) == '' and pool_str(ro) == '子', (k, pool_str(no), pool_str(ro))
            assert par == d0['subj'], ('动态槽不挂在本人下', k, par, d0['subj'])
        else:
            assert fl == 0 and par == 0xFF, ('填充节点标志不对', k, fl, par)
            assert pool_str(no) == ' ' == pool_str(ro), (k, pool_str(no), pool_str(ro))
    elif fl & 0x10:
        raise AssertionError('F_DYN 落在了静态段里: 节点 %d' % k)
    nn += 1
print('OK  NODE_TAB 有效节点 %d 个, 坐标/状态/父索引/串偏移 + 动态槽形状均合法' % nn)

# ---- OIDTAB / DETAILTAB: 桩的身份表与详情表, 每个节点一条 ----
assert sec[O_OID + NN * 2: O_OID + NN * 2 + 2] == b'\x00\x00', 'OIDTAB 后面应有空隙'
noid = 0
for k in range(NN):
    oid = struct.unpack_from('<H', sec, O_OID + k * 2)[0]
    assert oid == 0xFFFF or oid < 0x700, ('oid 越出 BSDATA 700 条档案', k, oid)
    if oid != 0xFFFF:
        noid += 1
    doff = struct.unpack_from('<H', sec, O_DET + k * 2)[0]
    assert doff < O_CODE - O_POOL, ('详情偏移越界', k, doff)
    l1 = sec[O_POOL + doff]
    assert l1 > 0 and l1 < 256, ('详情主行长度非法', k, l1)
print('OK  OIDTAB/DETAILTAB 各 %d 条; 有名有姓(oid 已分配)的节点 %d 个' % (NN, noid))

# ---- 池首可变区(桩的写入目标)构建期必须全 0 ----
_head = M['gen_recs'] * DSZ
assert sec[O_POOL:O_POOL + _head] == b'\x00' * _head, '串池池首可变区非空'
print('OK  池首可变区 %d 条 x %dB 全零(开树时由桩填)' % (M['gen_recs'], DSZ))

# ---- 控制块: 构建期只允许 DYN_FN 有值(big 产物), 其余埋点必须为 0 ----
_ctl = M['dyn_fn'] - SEC_VA
_dfn = struct.unpack_from('<I', sec, _ctl)[0]
for _nm, _o in (('lit', 'dyn_lit'), ('call', 'dyn_call'), ('nosub', 'dyn_nosub'),
                ('slot', 'dyn_slot')):
    v = struct.unpack_from('<I', sec, M[_o] - SEC_VA)[0]
    assert v == 0, ('%s 构建期应为 0 (现在 0x%08X)' % (_nm, v))
print('OK  动态族谱控制块: DYN_FN 0x%06X -> %s ; lit/call/nosub/slot 均 0'
      % (M['dyn_fn'], '0x%06X(点亮桩)' % _dfn if _dfn else '0(纯静态产物)'))

# 每族「本人」标记恰好一个, 且只数静态段(动态槽永不带 F_SUBJECT)
no_sub_oid = []
for d in dirs:
    sub = [i for i in range(d['st'], d['st'] + d['sn'])
           if struct.unpack_from('<BB', sec, O_NODES + i * NODE_SZ + 8)[1] & 4]
    assert sub == [d['st'] + d['subj']], ('本人标记不唯一/不符', d['k'], sub, d['st'], d['subj'])
    if not d['flag']:
        oid = struct.unpack_from('<H', sec, O_OID + (d['st'] + d['subj']) * 2)[0]
        if oid == 0xFFFF:
            no_sub_oid.append(pool_str(d['to']))
print('OK  每族「本人」标记唯一, 且与 subject 索引一致')
if no_sub_oid:
    # 不是构建错误: 这家人只是 BSDATA 里查不到本人 oid, 桩点不亮他的孩子(计 nosub)。
    print('注  本人无 oid(其子嗣点不亮)的家族: %s' % ' / '.join(no_sub_oid))

names = ['[通用块]' if d['flag'] else pool_str(d['to']) for d in dirs]
print('OK  家族标题: %s' % ' / '.join(names))


hint = '点人物=详情      方向键/拖拽=移动      ESC/点空白=关闭\x00'.encode('gbk')
assert hint in sec, '底部提示串缺失'
print('OK  提示串存在: %s' % hint.decode('gbk').rstrip('\x00'))

# ================= v13: 点亮桩本体(逐字节复算, 只在带 .edata 的 big 产物上做) =================
_REV = os.path.dirname(os.path.abspath(__file__))
_LYP = os.path.join(_REV, '_big_layout.json')
if _dfn == 0:
    print('OK  纯静态产物: DYN_FN=0 => tree_entry 判空后不 call, 老产物行为逐位不变')
elif not os.path.exists(_LYP):
    print('!!  DYN_FN 非零但没有 _big_layout.json, 无法复算点亮桩'); rc = 1
else:
    import tree_dyn as TDYN
    LY = json.load(open(_LYP, encoding='utf-8'))
    TD = LY['tree_dyn']
    assert _dfn == TD['code_va'], ('DYN_FN 0x%06X 与 layout 0x%06X 不符 —— 清单不是这份 exe'
                                   % (_dfn, TD['code_va']))
    for _k, _m in (('dyn_fn', 'dyn_fn'), ('dyn_lit', 'dyn_lit'), ('dyn_call', 'dyn_call'),
                   ('dyn_nosub', 'dyn_nosub'), ('dyn_slot', 'dyn_slot'),
                   ('dyn_pool', 'dyn_pool'), ('oidtab', 'oidtab'), ('famdir', 'famdir'),
                   ('nodes', 'nodes'), ('pool', 'pool'), ('famp', 'famp'),
                   ('generic_dir', 'generic_dir'), ('ndir', 'ndir'), ('nnode', 'nnode')):
        assert TD[_k] == M[_m], ('两份清单(%s)不一致: %s' % (_k, TD[_k]))
    assert TD['gen_start'] == GEN_START and TD['scan_ndir'] == M['scan_ndir']
    # 段表定位: .edata 是最后一节, raw 与 virt 差 2 个扇区, 只能用表算 file offset
    pe = struct.unpack_from('<I', buf, 0x3C)[0]
    nsec = struct.unpack_from('<H', buf, pe + 6)[0]
    # COFF 头 20B: Machine@+4 / NSec@+6 / ... / SizeOfOptionalHeader@+20 (不是 +16)
    sh = pe + 24 + struct.unpack_from('<H', buf, pe + 20)[0]
    _t = None
    for i in range(nsec):
        s = buf[sh + i * 40: sh + (i + 1) * 40]
        name = s[:8].rstrip(b'\0').decode('latin1')
        vsize, rva, rawsz, rawptr = struct.unpack('<IIII', s[8:24])
        lo, hi = IMAGE_BASE + rva, IMAGE_BASE + rva + max(vsize, rawsz)
        if lo <= TD['code_va'] < hi:
            _t = (name, rawptr + (TD['code_va'] - lo), lo, hi)
            break
    assert _t and _t[0] == '.edata', '点亮桩不在 .edata 里(段表定位失败): %s' % (_t,)
    _off = _t[1]
    got = bytes(buf[_off:_off + TD['code_sz']])
    TL = {'famp': M['famp'], 'oidtab': M['oidtab'], 'pool': LY['pool_va'], 'cap': LY['cap'],
          'giv': LY['surname_tab_va'], 'sur': LY['given_tab_va'],
          'dynpool': M['dyn_pool'],
          'gname': TD['gen_name_rec'], 'gtitle': TD['gen_title_rec'],
          'gstart': TD['gen_start'], 'slots': M['dyn_slots'],
          'suffix': TDYN.title_suffix_word(M['gen_title_suffix']),
          'slot': M['dyn_slot'], 'lit': M['dyn_lit'],
          'calls': M['dyn_call'], 'nosub': M['dyn_nosub'],
          'genflag': M['gen_flag'], 'locals': TDYN.LOCALS}
    exp, _src = TDYN.build(TD['code_va'], TL)
    assert len(exp) == TD['code_sz'], ('桩长度与清单不符 %d != %d' % (len(exp), TD['code_sz']))
    assert got == exp, 'exe 里的点亮桩与 tree_dyn.build 不逐字节一致(第一个差异 @+0x%X)' \
        % next(i for i in range(len(exp)) if got[i] != exp[i])
    ins = TDYN.selfcheck(got, TD['code_va'], TL)
    assert TD['code_sz'] <= TD['win_sz'], '桩越出窗口'
    assert TD['code_va'] + TD['win_sz'] <= _t[3], \
        '桩窗口越出 .edata (窗口尾 0x%06X > 节尾 0x%06X)' % (TD['code_va'] + TD['win_sz'], _t[3])
    # 桩的控制块/数据引用必须只落在 .fdata(清单已核对)与本 exe 映像内
    _LO, _HI = TD['code_va'], TD['code_va'] + TD['win_sz']
    for i in md.disasm(got, TD['code_va']):   # ★ 用自带 detail 的 md: selfcheck 那份没有 operands
        if i.mnemonic in ('call', 'jmp') and i.op_str.startswith('0x'):
            a = int(i.op_str, 16)
            assert _LO <= a < _HI, ('桩跳转越出窗口: %s %s' % (i.mnemonic, i.op_str))
        for op in i.operands:
            if op.type == 2 and op.mem and op.mem.base == 0 and op.mem.index == 0 and op.mem.disp:
                d = op.mem.disp
                assert IMAGE_BASE <= d < SEC_VA + SEC_SZ + LY['section_sz'], \
                    ('桩引用了映像外的地址 0x%08X: %s %s' % (d, i.address, i.mnemonic))
    print('OK  点亮桩 %dB @0x%06X(.edata file 0x%X) 与 tree_dyn.build 逐字节一致, 形态自检通过'
          % (TD['code_sz'], TD['code_va'], _off))
    print('    窗口 0x%X ; 引用表: FAMP 0x%06X OIDTAB 0x%06X 实体池 0x%06X x%d 姓 0x%06X 名 0x%06X'
          % (TD['win_sz'], TL['famp'], TL['oidtab'], TL['pool'], TL['cap'], TL['giv'], TL['sur']))

print('\n结果:', 'PASS' if rc == 0 else 'FAIL')
sys.exit(rc)
