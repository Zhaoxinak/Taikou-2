"""verify_fam.py — 静态校验 TAIK2W95_family.exe 的族谱补丁
1) 回读洞内 FAM_DIR / FAM_ROWS / 串池, 打印每棵家族树
2) capstone 反汇编 builder 的 触发段 + shib 段, 确认指令正确
"""
import struct, sys
sys.stdout.reconfigure(encoding='utf-8')

EXE = r'F:\Games\Taikou 2\Taikou2 Original\TAIK2W95_family.exe'
CAVE_RVA = 0x135000
CAVE_VA = 0x535000

d = open(EXE, 'rb').read()
pe = struct.unpack_from('<I', d, 0x3c)[0]
nsec = struct.unpack_from('<H', d, pe + 6)[0]
opt = struct.unpack_from('<H', d, pe + 20)[0]
secs = []
for i in range(nsec):
    o = pe + 24 + opt + i * 40
    nm = d[o:o + 8].rstrip(b'\x00').decode()
    vs, va, rs, ptr = struct.unpack_from('<IIII', d, o + 8)
    secs.append((nm, va, vs, rs, ptr))

def r2o(rva):
    for nm, va, vs, rs, ptr in secs:
        if va <= rva < va + max(vs, rs):
            return ptr + (rva - va)
    raise ValueError('RVA 0x%X' % rva)

fo = r2o(CAVE_RVA)
cave = d[fo:fo + 0x1000]

def rd(va, n):
    return cave[va - CAVE_VA: va - CAVE_VA + n]

def cstr(va):
    b = cave[va - CAVE_VA:]
    s = b.split(b'\x00')[0]
    try:
        return s.decode('gbk')
    except Exception:
        return '<%s>' % s.hex()

FAM_DIR_VA = 0x535680
ND = 13
DIR_ENTRY = 12
FAM_ROWS = FAM_DIR_VA + ND * DIR_ENTRY
FAM_ENTRY = 12

print('=' * 74)
print('族谱数据回读 (FAM_DIR=0x%06X, %d 家族)' % (FAM_DIR_VA, ND))
print('=' * 74)
nrow_total = 0
for i in range(ND):
    o = FAM_DIR_VA + i * DIR_ENTRY
    gdw, sdw, sel = struct.unpack('<III', rd(o, 12))
    giv = struct.pack('<I', gdw).split(b'\x00')[0].decode('gbk')
    sur = struct.pack('<I', sdw).split(b'\x00')[0].decode('gbk')
    start, n = sel >> 8, sel & 0xFF
    nrow_total += n
    print('\n【%s%s】 start=%d n=%d' % (sur, giv, start, n))
    for k in range(n):
        rp = FAM_ROWS + (start + k) * FAM_ENTRY
        ps, pg, pr = struct.unpack('<III', rd(rp, 12))
        s, g, r = cstr(ps), cstr(pg), cstr(pr)
        indent = (len(s) - len(s.lstrip(' '))) // 2
        print('   %s%-*s %-4s  %s' % ('│  ' * 0, 10, s.strip(), g, r))
        _ = indent
print('\n总行数 %d' % nrow_total)

# ---------- 反汇编 ----------
try:
    from capstone import Cs, CS_ARCH_X86, CS_MODE_32
    md = Cs(CS_ARCH_X86, CS_MODE_32)
    md.detail = False
except Exception as e:
    print('\n[!] capstone 不可用:', e)
    md = None

if md:
    print('\n' + '=' * 74)
    print('builder 触发段 (FAM_DIR 匹配)')
    print('=' * 74)
    # builder VA 0x53501B, 找到 dloop: 从 mov edx,FAM_DIR_VA 开始 (BA 80 56 53 00)
    blob = rd(0x53501B, 292)
    off = blob.find(bytes([0xBA]) + struct.pack('<I', FAM_DIR_VA))
    print('  偏移 0x%X 处找到 mov edx,FAM_DIR_VA' % off)
    for ins in md.disasm(blob[off:off + 60], 0x53501B + off):
        print('  %08X  %-24s %s %s' % (ins.address, ins.bytes.hex(), ins.mnemonic, ins.op_str))
        if ins.mnemonic == 'jmp' or (ins.mnemonic == 'jne' and ins.address > 0x53501B + off + 30):
            break

    print('\n' + '=' * 74)
    print('builder shib 段 (展开家族表)')
    print('=' * 74)
    off2 = blob.find(bytes([0x8B, 0x0D]) + struct.pack('<I', 0x51E9C0))
    for ins in md.disasm(blob[off2:off2 + 60], 0x53501B + off2):
        print('  %08X  %-24s %s %s' % (ins.address, ins.bytes.hex(), ins.mnemonic, ins.op_str))
        if ins.mnemonic == 'ret':
            break

    print('\n' + '=' * 74)
    print('painter override 判定段 (0x535400 起, 检查 cmp esi,FAM_ROWS)')
    print('=' * 74)
    paint = rd(0x535400, 169)
    for ins in md.disasm(paint, 0x535400):
        if ins.address >= 0x535430:
            break
        print('  %08X  %-24s %s %s' % (ins.address, ins.bytes.hex(), ins.mnemonic, ins.op_str))
