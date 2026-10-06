"""mk_fix1.py — 在 big.exe 上修掉已坐实的两处「栈缓冲区溢出」, 产出 TAIK2W95_big_fix1.exe。

★ 根因
build_big.py 的 P2 阶段把 .text 里所有 0x172(370) 常量按 CAP 放大到 0x400(1024)。
其中两处是 **栈上局部数组** 的 memset 长度, 而栈数组本身只有 370B(编译器定的, 不会跟着放大):

  0x49C5E5   lea eax,[esp+0xc] / push 0x400 / push 0 / push eax / call 0x492820(memset)
  0x49CD3D   同上形态

=> memset 写 1024B 进 370B 的栈数组 -> 踩穿返回地址 -> EIP=0(大地图崩)
   -> 后续 ntdll 里 call ecx(ecx=0) 反复异常处理递归 -> 0xC00000FD STACK_OVERFLOW

原版实测: 0x49C5E6 / 0x49CD3E 处立即数 = 370 (0x172)。

★ 为什么只改这两处
5 处 push 370 里, 其余 3 处(0x471219 / 0x476E7C / 0x4B48EC)的目标是全局/堆数组,
那些数组在 P3 阶段已随 CAP 一起放大(池 0x53C000 CAP*47、姓名两表 CAP*7), 缩放是对的。
判据: 目标是不是 `lea r,[esp+n]` —— 是栈就绝不能放大。

★ 同时保留 mk_nodbg 的 5 个调试 trampoline 还原(那 5 个已证实会让大地图入口必崩)。

用法: python mk_fix1.py [输出文件名]
"""
import hashlib, os, struct, sys

sys.stdout.reconfigure(encoding='utf-8')
SRC = r'F:\Games\Taikou 2\Taikou2 Original\TAIK2W95_big.exe'
DST = os.path.join(os.path.dirname(SRC), sys.argv[1] if len(sys.argv) > 1
                   else 'TAIK2W95_big_fix1.exe')
IMAGE_BASE = 0x400000
OLD_N, NEW_N = 0x172, 0x400


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
    return struct.pack('<i', to - (frm + 5))


def main():
    d = bytearray(open(SRC, 'rb').read())
    secs = sec_map(d)

    def off(va):
        return r2o(secs, va - IMAGE_BASE)

    print('源档: %s (%d B, sha %s)' % (SRC, len(d), hashlib.sha256(bytes(d)).hexdigest()[:16]))

    # ---- A) 还原 5 个纯诊断 trampoline ----
    A = [
        (0x4A0D50, 0xE9, b'\x83\xEC\x08\x53\x55', 'ENTRY(E) 日推进外层入口'),
        (0x4F44B0, 0xE9, b'\x55\x8B\xEC\x6A\xFF', 'BOOT(F) 游戏入口'),
        (0x4A0E47, 0xE8, b'\xE8' + rel32(0x4A0E47, 0x4A0B00), 'DAILY(D) call 0x4A0B00'),
        (0x4A0E41, 0xE8, b'\xE8' + rel32(0x4A0E41, 0x49A1A0), 'EARLY(G) call 0x49A1A0'),
        (0x4A0DED, 0xE8, b'\xE8' + rel32(0x4A0DED, 0x4A4C60), 'MONTH(H) call 0x4A4C60'),
    ]
    print('\n[A] 还原 5 个诊断 trampoline:')
    for va, want, new, desc in A:
        o = off(va)
        old = bytes(d[o:o + 5])
        assert old[0] == want, '0x%06X 首字节 0x%02X != 预期 0x%02X' % (va, old[0], want)
        d[o:o + 5] = new
        print('   0x%06X %-26s %s -> %s' % (va, desc, old.hex(' '), new.hex(' ')))

    # ---- B) 修栈缓冲区溢出: memset 长度 1024 -> 370 ----
    # 指令是 `68 00 04 00 00` (push imm32), 立即数在 +1 起 4 字节
    B = [0x49C5E5, 0x49CD3D]
    print('\n[B] 修栈数组 memset 长度 (1024 -> 370):')
    for va in B:
        o = off(va)
        old = bytes(d[o:o + 5])
        assert old == b'\x68\x00\x04\x00\x00', '0x%06X 不是 push 0x400: %s' % (va, old.hex(' '))
        d[o:o + 5] = b'\x68' + struct.pack('<I', OLD_N)
        print('   0x%06X %s -> %s   (栈上 370B 局部数组)' % (va, old.hex(' '), bytes(d[o:o + 5]).hex(' ')))

    open(DST, 'wb').write(bytes(d))
    print('\n产出: %s (%d B, sha %s)' % (DST, len(d), hashlib.sha256(bytes(d)).hexdigest()[:16]))
    print('试跑: StartTaikou2.bat %s' % os.path.basename(DST))


if __name__ == '__main__':
    main()
