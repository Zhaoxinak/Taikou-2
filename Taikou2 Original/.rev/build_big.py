# -*- coding: utf-8 -*-
"""
build_big.py —— P1「实体池搬家」: 从 TAIK2W95_family.exe 派生 TAIK2W95_big.exe
  * 新增 RW 节 .edata @RVA 0x13C000 (VA 0x53C000, 32KB): 实体池新家 (容纳 512×47, P2 用)
  * 把代码/静态表中所有指向旧池 [0x519868,0x51DC56) 的 4 字节 LE 字段(imm32/disp32)
    重定位到 0x53C000+同偏移; 0x51DC56(池尾界) → 0x53C000+47*370
  * 370 边界常数(0x172)一律不动 —— 本步纯搬家, 行为应逐位相同
  * 防误伤: 只改「白名单访存指令的完整 4 字节操作数字段」; j*/call 的 rel32 自动排除
  验证: 重建后全节复扫, 旧池区间字段引用应为 0; 逐点清单 -> _big_reloc.json
"""
import struct, json, os, sys, time
import pefile
from capstone import Cs, CS_ARCH_X86, CS_MODE_32
from capstone.x86 import X86_OP_IMM, X86_OP_MEM

# 控制台默认 GBK, 打印里的 ✓/中文会触发 UnicodeEncodeError -> 在写盘前崩, big.exe 不更新。
try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

SRC = r'F:\Games\Taikou 2\Taikou2 Original\TAIK2W95_family.exe'
DST = r'F:\Games\Taikou 2\Taikou2 Original\TAIK2W95_big.exe'

IMAGE_BASE = 0x400000
LO, STRIDE, N0 = 0x519868, 47, 370
HI = LO + STRIDE * N0                 # 0x51DC56 = 旧池尾/旧界
NEW = 0x53C000                        # 新池基址 (RVA 0x13C000)
NEW_RVA, NEW_PTR, NEW_SZ = 0x13C000, None, 0x8000
NEW_HI = NEW + STRIDE * N0            # 新池尾(P1 期等效旧 HI)

MEM_MNEMS = {
    'mov', 'lea', 'cmp', 'push', 'add', 'sub', 'and', 'or', 'xor', 'test',
    'xchg', 'adc', 'sbb', 'movzx', 'movsx', 'inc', 'dec', 'neg', 'not',
    'cmpxchg', 'movbe', 'xadd', 'bt',
}

def reloc_val(v):
    """旧池地址(含池尾界) -> 新地址; 不命中返回 None"""
    if LO <= v < HI:
        return NEW + (v - LO)
    if v == HI:
        return NEW_HI
    return None

def sweep(data, va):
    """线性反汇编+失步重同步, 返回 {addr: Insn}"""
    md = Cs(CS_ARCH_X86, CS_MODE_32)
    md.detail = True
    out = {}
    pos, end = 0, len(data)
    while pos < end:
        prog = False
        for ins in md.disasm(data[pos:end], va + pos):
            prog = True
            pos = ins.address - va + len(ins.bytes)
            out[ins.address] = ins
        if not prog:
            pos += 1
    return out

def sweep_iter(data, va):
    """同 sweep, 但按序 yield(省内存)"""
    md = Cs(CS_ARCH_X86, CS_MODE_32)
    md.detail = True
    pos, end = 0, len(data)
    while pos < end:
        prog = False
        for ins in md.disasm(data[pos:end], va + pos):
            prog = True
            pos = ins.address - va + len(ins.bytes)
            yield ins
        if not prog:
            pos += 1

def main():
    b = bytearray(open(SRC, 'rb').read())
    pe = pefile.PE(data=bytes(b))
    assert pe.OPTIONAL_HEADER.ImageBase == IMAGE_BASE
    secs = {}
    for s in pe.sections:
        secs[s.Name.rstrip(b'\0').decode()] = s
    assert len(secs) == 5, '族谱版应恰有 5 节'

    # ---------- 1) 新节 .edata ----------
    first_raw = min(s.PointerToRawData for s in pe.sections)
    e_lfanew = struct.unpack_from('<I', b, 0x3C)[0]
    coff = e_lfanew + 4
    nsec = struct.unpack_from('<H', b, coff + 2)[0]
    size_opt = struct.unpack_from('<H', b, coff + 16)[0]
    table = coff + 20 + size_opt
    assert nsec == 5
    assert table + 40 * 6 <= first_raw, '节表空隙不足'
    # .fdata 尾 = 其 ptr+size
    fd = secs['.fdata']
    want_ptr = fd.PointerToRawData + fd.SizeOfRawData
    assert want_ptr % 0x200 == 0
    NEW_PTR = want_ptr
    fsize = os.path.getsize(SRC)
    assert fsize == NEW_PTR, '族谱版文件尾应恰在 .fdata 后'
    # 追加节头
    name = b'.edata\x00\x00'
    hdr = struct.pack('<8sIIIIIIHHI', name, NEW_SZ, NEW_RVA, NEW_SZ, NEW_PTR,
                      0, 0, 0, 0, 0xE0000040)
    b[table + 40 * 5: table + 40 * 5 + 40] = hdr
    struct.pack_into('<H', b, coff + 2, 6)                    # NumberOfSections
    struct.pack_into('<I', b, e_lfanew + 24 + 56, NEW_RVA + NEW_SZ)  # SizeOfImage
    # 补零到新文件尾
    b.extend(b'\x00' * (NEW_PTR + NEW_SZ - len(b)))
    print('节 .edata: RVA 0x%06X VA 0x%06X raw 0x%X size 0x%X SizeOfImage=0x%X' %
          (NEW_RVA, NEW, NEW_PTR, NEW_SZ, NEW_RVA + NEW_SZ))

    # ---------- 2) 重定位所有旧池字段引用 ----------
    manifest, skipped = [], []
    for s in pe.sections:
        nm = s.Name.rstrip(b'\0').decode()
        if nm == '.rsrc':
            continue
        data = bytes(b[s.PointerToRawData:s.PointerToRawData + s.SizeOfRawData])
        s_va = IMAGE_BASE + s.VirtualAddress
        ins_map = sweep(data, s_va)
        for p in range(len(data) - 3):
            v = struct.unpack_from('<I', data, p)[0]
            nv = reloc_val(v)
            if nv is None:
                continue
            # 必须完整落在某条白名单指令的操作数字段上
            host = None
            for back in range(0, 14):
                it = ins_map.get(s_va + p - back)
                if it and it.address - s_va + len(it.bytes) >= p + 4:
                    host = it
                    break
            if host is None or host.mnemonic not in MEM_MNEMS:
                skipped.append((nm, p, v, host.mnemonic if host else 'no-insn'))
                continue
            # 字段匹配: 指令字节内 p-host.off 处须 == pack(v), 且是 imm/disp 值
            off = p - (host.address - s_va)
            if host.bytes[off:off + 4] != struct.pack('<I', v):
                skipped.append((nm, p, v, 'field-mismatch:' + host.mnemonic))
                continue
            ok_operand = False
            for op in host.operands:
                if op.type == X86_OP_IMM and (op.imm & 0xFFFFFFFF) == v:
                    ok_operand = True
                if op.type == X86_OP_MEM and (op.mem.disp & 0xFFFFFFFF) == v:
                    ok_operand = True
            if not ok_operand:
                skipped.append((nm, p, v, 'operand-mismatch'))
                continue
            abs_i = s.PointerToRawData + p
            struct.pack_into('<I', b, abs_i, nv)
            manifest.append({'sec': nm, 'off': p, 'va': s_va + p, 'old': v,
                             'new': nv, 'ins': '%s %s' % (host.mnemonic, host.op_str)})
    n_by_sec = {}
    for m in manifest:
        n_by_sec[m['sec']] = n_by_sec.get(m['sec'], 0) + 1
    print('重定位 %d 处: %s' % (len(manifest), n_by_sec))
    print('跳过(应为 j*/call/garbage 命中): %d' % len(skipped))
    for sk in skipped[:40]:
        print('   skip [%s+0x%X] 0x%08X  %s' % sk)

    # ---------- 3) 复扫验证: 旧池字段引用清零 ----------
    pe2 = pefile.PE(data=bytes(b))
    left = 0
    for s in pe2.sections:
        nm = s.Name.rstrip(b'\0').decode()
        if nm == '.rsrc':
            continue
        data = bytes(b[s.PointerToRawData:s.PointerToRawData + s.SizeOfRawData])
        s_va = IMAGE_BASE + s.VirtualAddress
        ins_map = sweep(data, s_va)
        for p in range(len(data) - 3):
            v = struct.unpack_from('<I', data, p)[0]
            if reloc_val(v) is not None:
                host = None
                for back in range(0, 14):
                    it = ins_map.get(s_va + p - back)
                    if it and it.address - s_va + len(it.bytes) >= p + 4:
                        host = it
                        break
                if not (host and host.mnemonic in MEM_MNEMS):
                    continue
                # 与打点通道同判据: 字段字节匹配 + 操作数值匹配
                off = p - (host.address - s_va)
                if host.bytes[off:off + 4] != struct.pack('<I', v):
                    continue
                if not any((op.type == X86_OP_IMM and (op.imm & 0xFFFFFFFF) == v) or
                           (op.type == X86_OP_MEM and (op.mem.disp & 0xFFFFFFFF) == v)
                           for op in host.operands):
                    continue
                left += 1
                print('   !! 残留 [%s+0x%X] 0x%08X `%s %s`' % (
                    nm, p, v, host.mnemonic, host.op_str))
    assert left == 0, '残留 %d 处' % left
    print('复扫: 白名单字段引用残留 0 ✓ (j*/call/数据噪声命中不算)')

    # ---------- 4) 关键锚点抽查 ----------
    def find4(v):
        return bytes(struct.pack('<I', v))
    assert bytes(b).count(find4(NEW)) >= 300, '新基址 imm 数量异常'
    json.dump(manifest, open('_big_reloc.json', 'w', encoding='utf-8'),
              ensure_ascii=False, indent=1)

    # ---------- 4b) P2-STAGE: 0x172(370) -> 0x200(512) ----------
    #   判据: 解码指令的 imm 操作数 == 0x172 且白名单指令(cmp/mov/push...)。
    #   23 处 "cmp 后置 mov 再 jcc" 的延迟界检同属 BOUND(cmp/mov 均不破坏标志) —— 一起改。
    #   序列化器 VA 区间 [0x47DA00,0x47F200) 的 4 处循环保留 370(文件格式锚)。
    #   清点应与 _sites_172.json 的 510 处一致: patched=506, kept=4。
    SER_LO_VA, SER_HI_VA = 0x47DA00, 0x47F200
    OLD_N, NEW_N = 0x172, 0x200
    tsec = secs['.text']
    patched172, kept_ser = [], []
    data = bytes(b[tsec.PointerToRawData:tsec.PointerToRawData + tsec.SizeOfRawData])
    s_va = IMAGE_BASE + tsec.VirtualAddress
    for ins in sweep_iter(data, s_va):
        hit = None
        for o in ins.operands:
            if o.type == X86_OP_IMM and (o.imm & 0xFFFFFFFF) == OLD_N and o.size in (2, 4):
                hit = o
                break
        if hit is None or ins.mnemonic not in MEM_MNEMS:
            continue
        if SER_LO_VA <= ins.address < SER_HI_VA:
            kept_ser.append((ins.address - s_va, '%s %s' % (ins.mnemonic, ins.op_str)))
            continue
        w = hit.size
        off = len(ins.bytes) - w          # 立即数在指令尾部
        if ins.bytes[off:off + 2] != struct.pack('<H', OLD_N) or \
           (w == 4 and ins.bytes[off + 2:off + 4] != b'\x00\x00'):
            kept_ser.append((ins.address - s_va, 'NOTAIL:' + ins.mnemonic))
            continue
        abs_i = tsec.PointerToRawData + (ins.address - s_va) + off
        struct.pack_into('<H', b, abs_i, NEW_N)
        if w == 4:
            struct.pack_into('<H', b, abs_i + 2, 0)
        patched172.append({'off': ins.address - s_va, 'va': ins.address, 'w': w,
                           'ins': '%s %s' % (ins.mnemonic, ins.op_str)})
    print('P2: 改界 %d 处 (0x172->0x200), 保留 %d 处' % (len(patched172), len(kept_ser)))
    for o, txt in kept_ser:
        print('   keep +%06X %s' % (o, txt))
    assert len(patched172) == 504 and len(kept_ser) == 6, 'P2 点数与清点清单不符(序列化器带2处cmp界)'

    # ---------- 4c) P2-STAGE: .edata 扩展槽静态初始化 (370..511) ----------
    #   模板 = 运行时池尾空槽 354 的 47B 原文(ents_dump.json), 仅 id word=槽号。
    #   尾槽 354..369 已证明该形态可安然走过游戏全周期; 槽 370 id=0x172 兼作哨兵假人。
    import json as _json
    dump = _json.load(open(r'F:\Games\Taikou 2\Taikou2 Original\.rev\ents_dump.json', encoding='utf-8'))
    tmpl = None
    for e in dump:
        if e['slot'] == 354:
            tmpl = bytes.fromhex(e['raw'])
    assert tmpl and len(tmpl) == 47, '槽354模板缺失'
    ed = [s for s in pe2.sections if s.Name.rstrip(b'\0') == b'.edata'][0]
    for i in range(N0, N0 + 142):        # 370..511
        rec = bytearray(tmpl)
        rec[0:2] = struct.pack('<H', i)  # id word = 槽号 (尾槽惯例)
        off = ed.PointerToRawData + i * STRIDE
        b[off:off + STRIDE] = rec
    print('扩展槽 370..511 静态初始化完成 (模板=尾空槽354, id=槽号)')

    # ---------- 4d) P2 复核: .text 内白名单操作数 0x172 应只剩序列化器 4 处 ----------
    data = bytes(b[tsec.PointerToRawData:tsec.PointerToRawData + tsec.SizeOfRawData])
    left172 = 0
    for ins in sweep_iter(data, s_va):
        if ins.mnemonic in MEM_MNEMS and any(
                o.type == X86_OP_IMM and (o.imm & 0xFFFFFFFF) == OLD_N
                for o in ins.operands):
            left172 += 1
            print('   余 %06X %s %s' % (ins.address - s_va, ins.mnemonic, ins.op_str))
    assert left172 == 6, 'P2 后残留 %d 处' % left172
    print('P2 复核: 0x172 仅序列化器 6 点保留 (4 mov + 2 cmp) ✓')

    # ---------- 4e) P3a-STAGE: 姓/名表搬家到 .edata, 容量 370->512 ----------
    #   姓表 0x520660 (370×7, 止 0x521076), 名表 0x521AA8 (370×7, 止 0x5224C2)。
    #   全部引用只有 4 个常量: base 与 base+6 (记录尾字节清零)。
    #   新家: SUR=0x541E00 (池尾 0x541DE0 对齐后), GIV=0x542C00; 各 512×7=0xE00,
    #   总止 0x543A00 < 节尾 0x544000。序列化器逐槽 370 条写文件 —— 搬家透明, 格式不变。
    SUR_NEW = NEW + 0x5E00          # 0x541E00
    GIV_NEW = NEW + 0x6C00          # 0x542C00
    assert SUR_NEW + 7 * 512 == GIV_NEW and GIV_NEW + 7 * 512 <= NEW + NEW_SZ
    TAB_MAP = {0x520660: SUR_NEW, 0x520666: SUR_NEW + 6,
               0x521AA8: GIV_NEW,  0x521AAE: GIV_NEW + 6}

    def tab_reloc(v):
        return TAB_MAP.get(v)

    def field_pass(relocate, collect=None, verbose_tag=''):
        """全节(除 .rsrc)窗口扫描: 白名单指令操作数字段命中 relocate(v) 则改写."""
        n_hit = n_skip = 0
        for s in pe2.sections:
            nm = s.Name.rstrip(b'\0').decode()
            if nm == '.rsrc':
                continue
            data = bytes(b[s.PointerToRawData:s.PointerToRawData + s.SizeOfRawData])
            s_va = IMAGE_BASE + s.VirtualAddress
            ins_map = sweep(data, s_va)
            for p in range(len(data) - 3):
                v = struct.unpack_from('<I', data, p)[0]
                nv = relocate(v)
                if nv is None:
                    continue
                host = None
                for back in range(0, 14):
                    it = ins_map.get(s_va + p - back)
                    if it and it.address - s_va + len(it.bytes) >= p + 4:
                        host = it
                        break
                if host is None or host.mnemonic not in MEM_MNEMS:
                    n_skip += 1
                    print('   %sskip [%s+0x%X] 0x%08X %s' % (
                        verbose_tag, nm, p, v, host.mnemonic if host else 'no-insn'))
                    continue
                off = p - (host.address - s_va)
                if host.bytes[off:off + 4] != struct.pack('<I', v):
                    n_skip += 1
                    print('   %sskip [%s+0x%X] field-mismatch' % (verbose_tag, nm, p))
                    continue
                if not any((op.type == X86_OP_IMM and (op.imm & 0xFFFFFFFF) == v) or
                           (op.type == X86_OP_MEM and (op.mem.disp & 0xFFFFFFFF) == v)
                           for op in host.operands):
                    n_skip += 1
                    print('   %sskip [%s+0x%X] 0x%08X operand-mismatch' % (
                        verbose_tag, nm, p, v))
                    continue
                if collect is not None:
                    abs_i = s.PointerToRawData + p
                    struct.pack_into('<I', b, abs_i, nv)
                    collect.append({'sec': nm, 'off': p, 'old': v, 'new': nv,
                                    'ins': '%s %s' % (host.mnemonic, host.op_str)})
                n_hit += 1
        return n_hit, n_skip

    tab_manifest = []
    n_hit, n_skip = field_pass(tab_reloc, tab_manifest, 'P3a ')
    print('P3a: 姓/名表引用重定位 %d 处, 噪声跳过 %d' % (n_hit, n_skip))
    for m in tab_manifest:
        print('   [%s+0x%X] 0x%08X -> 0x%08X  %s' % (m['sec'], m['off'], m['old'], m['new'], m['ins']))
    assert n_skip == 0 and len(tab_manifest) >= 26, 'P3a 站点异常, 需人工核对'

    # 复扫: 旧表常量残留应为 0 (噪声除外, 用同判据)
    left_tab, _ = field_pass(tab_reloc, None, 'P3a-rescan ')
    assert left_tab == 0, 'P3a 残留 %d 处' % left_tab
    print('P3a 复核: 旧姓/名表字段引用 0 ✓ (表容量 512, 序列化器条数仍 370)')

    # ---------- 4f) P3b-STAGE: 休眠人物姓名预填 (姓/名表槽 371..462) ----------
    #   数据源 _dormants.json (gen_dormants.py 从 tree_data 生成, 独名字已拆姓/名)。
    #   序列化器逐槽只写 0..369, 扩展条目在运行期永不被加载流程覆盖 -> 文件字节即终值。
    dorm = json.load(open(r'F:\Games\Taikou 2\Taikou2 Original\.rev\_dormants.json', encoding='utf-8'))
    ed2 = [s for s in pe2.sections if s.Name.rstrip(b'\0') == b'.edata'][0]
    for d in dorm:
        sl = d['slot']
        assert 371 <= sl <= 511
        for key, tbl in (('sur_hex', SUR_NEW), ('giv_hex', GIV_NEW)):
            nb = bytes.fromhex(d[key])
            assert len(nb) <= 6, (d, key)
            off = ed2.PointerToRawData + (tbl - NEW) + sl * 7
            b[off:off + len(nb)] = nb
            b[off + len(nb)] = 0
    print('P3b: 休眠人物 %d 名已预填 (槽 %d..%d)' % (
        len(dorm), dorm[0]['slot'], dorm[-1]['slot']))

    # ---------- 4g) MCI-STUB: 屏蔽 mciSendCommandA 的设备打开, 躲 Win11 24H2 msmpeg2ac3dec fastfail ----------
    #   根因(minidump 实证): 进大地图时游戏经 WINMM!mciSendCommandA 建 DirectShow 图播放 开场动画/BGM(=MP3),
    #   系统旧解码器 msmpeg2ac3dec.dll 自毁(0xC0000602 __fastfail)。属环境回归, 与族谱/池代码无关(family/big/zoom 同崩)。
    #   做法(不依赖被加载器覆写的 IAT): .text 里全部 `call/mov dword,[0x4FB1E8]`(__imp_mciSendCommandA) 的
    #   disp32 改指到 .edata 内私有槽 NEW_SLOT; 该槽存 stub VA, stub 对 MCI_OPEN(0x800) 返回错误码(令调用方跳过媒体),
    #   其余命令返回 0(空操作)。加载器不碰 .edata, 故改写持久; 设备永不打开 -> 解码器不加载 -> 不崩。
    #   代价: 开场/结局动画与背景音乐全静音(用户已确认接受)。还原=用未打此步的 big 或删节。
    MCI_SLOT_VA, NEW_SLOT_VA, STUB_VA = 0x4FB1E8, 0x543C00, 0x543C10
    ed3 = [s for s in pe2.sections if s.Name.rstrip(b'\0') == b'.edata'][0]
    def ed_off(va):
        assert NEW <= va < NEW + NEW_SZ, ('.edata 越界', hex(va))
        return ed3.PointerToRawData + (va - NEW)
    stub = bytearray()
    stub += b'\x8B\x44\x24\x08'              # mov eax,[esp+8]      msg
    stub += b'\x3D\x00\x08\x00\x00'          # cmp eax,0x800        MCI_OPEN
    stub += b'\x74\x05'                      # je  short .open      (-> 0x10)
    stub += b'\x33\xC0'                      # xor eax,eax          返回 0 (其它命令空操作)
    stub += b'\xC2\x10\x00'                  # ret 16               stdcall 清 4 参
    # .open:
    stub += b'\xB8\x00\x01\x00\x00'          # mov eax,0x100        MCIERR_BASE -> 调用方判失败, 跳过媒体
    stub += b'\xC2\x10\x00'                  # ret 16
    assert len(stub) <= 0x80, 'stub 过长'
    b[ed_off(STUB_VA):ed_off(STUB_VA) + len(stub)] = stub
    struct.pack_into('<I', b, ed_off(NEW_SLOT_VA), STUB_VA)   # 私有槽 = stub 代码 VA
    old4 = struct.pack('<I', MCI_SLOT_VA)
    new4 = struct.pack('<I', NEW_SLOT_VA)
    n_ref = b.count(old4)
    b = bytearray(bytes(b).replace(old4, new4))
    assert n_ref == 18, 'mciSendCommandA 引用点数量异常: %d (期望 18)' % n_ref
    assert b.count(old4) == 0 and b.count(new4) == n_ref
    print('MCI-STUB: stub @0x%06X (%dB), 私有槽 0x%06X 存 0x%06X, 改写 [0x4FB1E8] 引用 %d 处 -> 全指私有槽'
          % (STUB_VA, len(stub), NEW_SLOT_VA, STUB_VA, n_ref))

    # ---------- 4h) BGM-STUB: 屏蔽 mp3.dll 背景乐的 DirectShow 图, 才是进大地图仍崩的真凶 ----------
    #   MCI-STUB 只封了引擎内建 mciSendCommandA(开场/结局 AVI); 打完仍崩, minidump 显示 msmpeg2ac3dec 是经
    #   BGM 插件 mp3.dll -> mciSendStringA -> mciqtz32 -> DirectShow 图被加载的。该 DLL 由 .data 内一块保护壳代码驱动:
    #     0x52D100 LoadLibrary("MP3.DLL")+GetProcAddress -> mp3play@[ebp+0x20]/mp3seek@+0x24/mp3stop@+0x28;
    #     0x52D200 play 包装: 拼 ".\\MP3\\??.MP3" 文件名 -> push 文件名 -> 0x52D342 `call [ebp+0x20]`(mp3play, stdcall 1 参, 建图->崩)
    #                            -> 0x52D348 `mov [ebp+0x40],1`(置"正在播放"标志);
    #     0x52D390 stop 包装: 仅当标志!=0 才 `call [ebp+0x28]`(mp3stop) -> 拆图。
    #   全盘: mp3play 只在 0x52D342 调一次, mp3seek 无人调用, mp3stop 被标志门控。故只需断 play:
    #     (a) 三字节 call 换成 `add esp,4` —— 弹出已压入的文件名实参, 栈平衡, 不建图;
    #     (b) 七字节"置标志"换成 `inc dword[BGM_CNT]` + nop —— 标志恒 0 -> stop 亦永不触发 mp3stop; 该计数即埋点。
    #   代价: 背景音乐静音(动画已静音)。还原=删除本步。tkwatch 读 VA BGM_CNT 可确认"命中并抑制 N 次"。
    dsec = [s for s in pe2.sections if s.Name.rstrip(b'\0') == b'.data'][0]
    DVA = IMAGE_BASE + dsec.VirtualAddress
    DSZ = max(dsec.Misc_VirtualSize, dsec.SizeOfRawData)
    def data_off(va):
        assert DVA <= va < DVA + DSZ, ('.data 越界', hex(va))
        return dsec.PointerToRawData + (va - DVA)
    BGM_CNT_VA, PLAY_CALL_VA, FLAG_SET_VA = 0x543C40, 0x52D342, 0x52D348
    # 被替换区 = call[ebp+0x20](3) + 3 nop(3) + mov [ebp+0x40],1(7) = 13 字节, 到 0x52D34F 止
    assert bytes(b[data_off(PLAY_CALL_VA):data_off(PLAY_CALL_VA) + 3]) == b'\xFF\x55\x20', 'play call 站点漂移'
    assert bytes(b[data_off(FLAG_SET_VA):data_off(FLAG_SET_VA) + 7]) == b'\xC7\x45\x40\x01\x00\x00\x00', 'flag set 站点漂移'
    assert bytes(b[data_off(PLAY_CALL_VA):data_off(PLAY_CALL_VA) + 13]) == \
        b'\xFF\x55\x20\x90\x90\x90\xC7\x45\x40\x01\x00\x00\x00', 'play 包装区布局异常'
    # 下一原指令须是 mov word[0x501290],2 (66 c7 05 ..) -> 补丁须恰好填满 13 字节落到它, 不可留残字节(否则错位 AV)
    assert bytes(b[data_off(PLAY_CALL_VA + 13):data_off(PLAY_CALL_VA + 13) + 3]) == b'\x66\xC7\x05', '尾指令边界异常'
    patch = b'\x83\xC4\x04' + b'\xFF\x05' + struct.pack('<I', BGM_CNT_VA) + b'\x90\x90\x90\x90'  # add esp,4 | inc[BGM_CNT] | nop*4 = 13B
    assert len(patch) == 13
    b[data_off(PLAY_CALL_VA):data_off(PLAY_CALL_VA) + 13] = patch
    struct.pack_into('<I', b, ed_off(BGM_CNT_VA), 0)                                   # 埋点计数器初值 0
    assert bytes(b[data_off(PLAY_CALL_VA):data_off(PLAY_CALL_VA) + 13]) == patch
    print('BGM-STUB: 0x%06X call[mp3play]->add esp,4; 0x%06X 置标志->inc dword[0x%06X](埋点,恒不置位) ; stop 因标志恒0 不触发'
          % (PLAY_CALL_VA, FLAG_SET_VA, BGM_CNT_VA))

    # ---------- 5) 写盘(游戏占用防呆) ----------
    try:
        open(DST, 'wb').write(bytes(b))
        print('OK  %s  %d B  mtime=%s' % (DST, len(b), time.strftime('%H:%M:%S', time.localtime(os.path.getmtime(DST)))))
    except PermissionError:
        out = DST[:-4] + 'b.exe'
        open(out, 'wb').write(bytes(b))
        print('!! 警告: %s 被占用(游戏在跑?), 本次写到了 %s' % (DST, out))

if __name__ == '__main__':
    main()
