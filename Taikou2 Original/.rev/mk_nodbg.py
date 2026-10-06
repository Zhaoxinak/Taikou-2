"""mk_nodbg.py — 从 TAIK2W95_big.exe 摘掉「纯诊断用」的 5 个调试 trampoline, 产出对照档。

目的: 大地图必崩(EIP=0)。这 5 个钩子是 2026-10-06 深夜为了定位才加进 build_big.py 的,
     本身不实现任何玩法。先做一个「除它们之外完全一样」的对照档做二分,
     若不再崩 => 真凶就是这 5 个钩子(或其 trampoline), 直接删掉即可收工。

被还原的 5 处(全部按 trampoline 里保存的原指令重建, 逐字节核对):
  0x4A0D50  E9 -> 83 EC 08 53 55              sub esp,8 / push ebx / push ebp
  0x4F44B0  E9 -> 55 8B EC 6A FF              push ebp / mov ebp,esp / push -1
  0x4A0E47  E8 -> E8 rel32(0x4A0B00)          call 0x4A0B00
  0x4A0E41  E8 -> E8 rel32(0x49A1A0)          call 0x49A1A0
  0x4A0DED  E8 -> E8 rel32(0x4A4C60)          call 0x4A4C60

不动: MCI-STUB / BGM-STUB / 儿童预载 / 成长桩 / 影子档 / 菜单钩子 等一切功能性补丁。
用法: python mk_nodbg.py [输出文件名]
"""
import hashlib, os, struct, sys

sys.stdout.reconfigure(encoding='utf-8')
SRC = r'F:\Games\Taikou 2\Taikou2 Original\TAIK2W95_big.exe'
DST = os.path.join(os.path.dirname(SRC), sys.argv[1] if len(sys.argv) > 1
                   else 'TAIK2W95_big_nodbg.exe')

IMAGE_BASE = 0x400000


def sec_map(d):
    e_lfanew = struct.unpack_from('<I', d, 0x3C)[0]
    opt = e_lfanew + 24
    nsec, = struct.unpack_from('<H', d, e_lfanew + 6)
    opt_size, = struct.unpack_from('<H', d, e_lfanew + 20)
    so = opt + opt_size
    secs = []
    for i in range(nsec):
        o = so + i * 40
        nm = d[o:o + 8].rstrip(b'\0').decode('latin1')
        vs, va, rs, ra = struct.unpack_from('<IIII', d, o + 8)
        secs.append((nm, va, max(vs, rs), ra))
    return secs


def r2o(secs, rva):
    for nm, va, vs, ra in secs:
        if va <= rva < va + vs:
            return ra + (rva - va)
    raise KeyError('RVA 0x%X 不在任何段内' % rva)


def rel32(frm, to):
    """E8/E9 的相对位移: 以指令后一条为基准。"""
    return struct.pack('<i', to - (frm + 5))


def main():
    d = bytearray(open(SRC, 'rb').read())
    secs = sec_map(d)

    def off(va):
        return r2o(secs, va - IMAGE_BASE)

    # (地址, 期望的现行首字节, 还原后的 5 字节, 说明)
    FIX = [
        (0x4A0D50, 0xE9, b'\x83\xEC\x08\x53\x55', 'ENTRY(E) 日推进外层入口'),
        (0x4F44B0, 0xE9, b'\x55\x8B\xEC\x6A\xFF', 'BOOT(F) 游戏入口'),
        (0x4A0E47, 0xE8, b'\xE8' + rel32(0x4A0E47, 0x4A0B00), 'DAILY(D) call 0x4A0B00'),
        (0x4A0E41, 0xE8, b'\xE8' + rel32(0x4A0E41, 0x49A1A0), 'EARLY(G) call 0x49A1A0'),
        (0x4A0DED, 0xE8, b'\xE8' + rel32(0x4A0DED, 0x4A4C60), 'MONTH(H) call 0x4A4C60'),
    ]
    print('源档: %s  (%d B, sha %s)' % (SRC, len(d), hashlib.sha256(bytes(d)).hexdigest()[:16]))
    for va, want, new, desc in FIX:
        o = off(va)
        old = bytes(d[o:o + 5])
        assert old[0] == want, '0x%06X 首字节是 0x%02X, 不是预期的 0x%02X —— 补丁布局变了, 别盲改' % (
            va, old[0], want)
        d[o:o + 5] = new
        print('  0x%06X  %s  %s -> %s' % (va, desc, old.hex(' '), new.hex(' ')))
    open(DST, 'wb').write(bytes(d))
    print('产出: %s  (%d B, sha %s)' % (DST, len(d), hashlib.sha256(bytes(d)).hexdigest()[:16]))
    print('两档除这 5 处外逐字节相同; 请用 StartTaikou2.bat %s 试跑对照。' % os.path.basename(DST))


if __name__ == '__main__':
    main()
