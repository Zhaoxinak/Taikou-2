"""fam_sim.py — 用 Unicorn 仿真 family_builder, 验证族谱展开逻辑(无需开游戏)
验的是"点开某武将 -> 列表里出现完整家族树"这条链路的纯计算部分:
  builder(实体指针) -> eax=行数, LISTBUF[i]=表项地址, RELSTR[i]=关系串
"""
import struct, sys
sys.stdout.reconfigure(encoding='utf-8')
from unicorn import Uc, UC_ARCH_X86, UC_MODE_32, UC_HOOK_CODE
from unicorn.x86_const import *

EXE = r'F:\Games\Taikou 2\Taikou2 Original\TAIK2W95_family.exe'
MEM = r'F:\Games\Taikou 2\scripts\_unpacked_mem.bin'
CAVE_RVA, CAVE_VA = 0x135000, 0x535000
BASE = 0x400000

# ---- 常量(与 build_fam_btn2.py 保持一致) ----
G_ROOT   = 0x5352B0
G_FAMSEL = 0x5355D8
ENTRY_VA = CAVE_VA                       # family_entry
BUILDER_VA = CAVE_VA + 27                # 0x53501B
LISTBUF  = 0x51E9C0
RELSTR   = 0x535600
RELSTR_N = 32
SUR_BASE, GIV_BASE, STRIDE = 0x520660, 0x521aa8, 7
FAM_DIR_VA = 0x535680
NDIR = 13
FAM_ENTRY = 12
FAM_ROWS = FAM_DIR_VA + NDIR * FAM_ENTRY
CUR_CARD = 0x514EE8                      # 当前信息卡武将实体指针

d = open(EXE, 'rb').read()
pe = struct.unpack_from('<I', d, 0x3c)[0]
nsec = struct.unpack_from('<H', d, pe + 6)[0]
opt = struct.unpack_from('<H', d, pe + 20)[0]
secs = []
for i in range(nsec):
    o = pe + 24 + opt + i * 40
    vs, va, rs, ptr = struct.unpack_from('<IIII', d, o + 8)
    secs.append((va, vs, rs, ptr))

def r2o(rva):
    for va, vs, rs, ptr in secs:
        if va <= rva < va + max(vs, rs):
            return ptr + (rva - va)
    raise ValueError('RVA 0x%X' % rva)

cave = d[r2o(CAVE_RVA):r2o(CAVE_RVA) + 0x1000]
img = bytearray(open(MEM, 'rb').read())          # 2MB 覆盖 0x400000..0x600000

def run_case(title, slot, giv, sur, father=0xFFFF, root_ptr=None):
    """在镜像上铺好输入, 跑 builder, 返回 (行数, [(姓,名,关系)])"""
    mu = bytearray(img)
    # 洞字节(必须在镜像之后写入, 覆盖同名区域)
    mu[CAVE_VA - BASE: CAVE_VA - BASE + 0x1000] = cave
    # 假实体
    eva = BASE + 0x119868 + 5 * 47           # EBASE+5*47, 安全位置
    struct.pack_into('<H', mu, eva - BASE + 0x00, slot)      # [0]=S1槽位
    struct.pack_into('<H', mu, eva - BASE + 0x1D, father)    # [+0x1d]=父id
    struct.pack_into('<H', mu, eva - BASE + 0x2C, 0x0100)    # [+0x2c]status: 须 (ah&7)!=0 才被通用路径收录
    # 姓名表 (7B 槽: 前几字节为 GBK, 尾部补 0 —— 与 BSDATA 固定长字段一致)
    for base_va, txt in ((SUR_BASE, giv), (GIV_BASE, sur)):
        off = base_va - BASE + slot * STRIDE
        mu[off:off + 7] = b'\0' * 7
        tb = txt.encode('gbk')
        mu[off:off + len(tb)] = tb
    # LISTBUF 指向的数组
    lb = 0x600000
    mu[LISTBUF - BASE:LISTBUF - BASE + 4] = struct.pack('<I', lb)
    # 清零 RELSTR / G_FAMSEL
    mu[RELSTR - BASE:RELSTR - BASE + RELSTR_N * 4] = b'\0' * (RELSTR_N * 4)
    mu[G_FAMSEL - BASE:G_FAMSEL - BASE + 4] = b'\0' * 4
    struct.pack_into('<I', mu, G_ROOT - BASE, root_ptr if root_ptr else eva)

    uc = Uc(UC_ARCH_X86, UC_MODE_32)
    uc.mem_map(0x400000, 0x200000)
    uc.mem_map(0x600000, 0x2000)
    uc.mem_write(0x400000, bytes(mu))
    uc.mem_write(0x600000, b'\0' * 0x2000)
    uc.mem_map(0x6FF000, 0x2000)
    uc.mem_write(0x6FF000, b'\0' * 0x2000)
    uc.reg_write(UC_X86_REG_ESP, 0x701000)
    # 跑 builder: 遇 ret 即停(避免 ret 后跳到未映射)
    def on_code(uc_, addr, size, ud):
        if size == 1 and uc_.mem_read(addr, 1) == b'\xc3':
            uc_.emu_stop()
    uc.hook_add(UC_HOOK_CODE, on_code)
    uc.emu_start(BUILDER_VA, BUILDER_VA + 400)
    eax = uc.reg_read(UC_X86_REG_EAX)
    lbd = uc.mem_read(lb, 64 * 4)
    reld = uc.mem_read(RELSTR, RELSTR_N * 4)
    rows = []
    for i in range(min(eax, 32)):
        ent = struct.unpack_from('<I', lbd, i * 4)[0]
        if not (FAM_ROWS <= ent < FAM_ROWS + 57 * FAM_ENTRY):
            rows.append(('<哨兵异常 0x%06X>' % ent, '', ''))
            continue
        ps, pg, pr = struct.unpack_from('<III', uc.mem_read(ent, 12), 0)
        def cs(va):
            b = uc.mem_read(va, 24).split(b'\x00')[0]
            try:
                return b.decode('gbk')
            except Exception:
                return '<%s>' % b.hex()
        rel = struct.unpack_from('<I', reld, i * 4)[0]
        rows.append((cs(ps), cs(pg), cs(pr) if rel == pr else cs(rel) + '?'))
    print('\n【%s】  slot=%d  -> eax=%d 行' % (title, slot, eax))
    for s, g, r in rows:
        print('    %-12s %-6s %s' % (repr(s), g, r))
    return eax, rows

print('=' * 70)
print('family_builder 仿真 (纯逻辑, 不依赖 UI/姓名表填充状态)')
print('=' * 70)
ok = True
for i, (tsur, tgiv, mem) in enumerate([
        ('柴田', '胜家', 2), ('织田', '信长', 4), ('毛利', '元就', 5),
        ('北条', '氏康', 6), ('岛津', '贵久', 5), ('武田', '信玄', 4),
        ('德川', '家康', 4), ('真田', '幸隆', 4), ('伊达', '晴宗', 4),
        ('大友', '宗麟', 4), ('森', '可成', 3), ('最上', '义守', 3),
        ('吉川', '元春', 4)]):
    n, rows = run_case(tsur + tgiv, 100 + i, tgiv, tsur)
    if n != mem:
        ok = False
        print('   !! 期望 %d 行' % mem)

# 非内置家族 -> 通用路径(只列在场亲属)
n, rows = run_case('未知武将(通用路径)', 200, '某某', '某某')
print('    通用路径返回 %d 行 (期望 >=1, 即本人)' % n)
if n < 1:
    ok = False

print('\n' + ('=' * 70))
print('结果: %s' % ('全部通过 ✔' if ok else '存在失败 ✘'))
