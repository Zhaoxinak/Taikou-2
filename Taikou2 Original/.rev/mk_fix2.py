"""mk_fix2.py — fix1 + 修掉「日志桩调用约定不一致(多清栈)」= TAIK2W95_big_fix2.exe

★ 本次根因（探针夹逼 + 字节级反汇编坐实）
日志桩 0x54C988 (写 C:\\taikou_debug.log) 结尾是 `ret 4` —— **stdcall, 自己清参数**。
但 child_growth_pass 里 4 个调用点中, 后 3 个在 call 之后又 `add esp,4` ⇒ **每次多弹 4 字节**:

  0x54CA2F  push 0x43 / call 0x54c988 → mov ebx        ✓ 正确
  0x54CA9B  push 0x44 / call 0x54c988 → add esp,4      ✗ 多清
  0x54CDB6  push 0x45 / call 0x54c988 → add esp,4      ✗ 多清
  0x54CE6C  push 0x46 / call 0x54c988 → add esp,4      ✗ 多清

后果: ESP 逐次抬高。0x54CAA0 那条每结算一个孩子走一次, 14 个孩子 ⇒ +56B;
实测崩溃时 ESP 比桩入口高 0x40=64B ⇒ 完全吻合。
ESP 漂到返回地址之外 -> 弹栈拿到垃圾(EBP=0x530006) -> 最终 `ret` 弹到 0 -> **EIP=0 执行空指针**。

★ 探针证据（tkmon --probe 0x54CA00,0x54CA05,0x54CA0A,0x4A4CC5）
  命中 0x4A4CC5 ✓  → 命中 0x54CA00 ✓ → 命中 0x54CA05 ✓ → **0x54CA0A(popal) 未命中**
  ⇒ 崩在 child_growth_pass(0x54CA20) 内部, 而该桩内**没有任何间接转移**
  ⇒ 只能是它调用的函数改了栈 ⇒ 定位到日志桩。

修复: 把 3 处多余的 `83 C4 04`(add esp,4) 换成 `90 90 90`(nop), 栈即恢复平衡。
同时保留 fix1 的两组修复(A: 摘 5 个诊断 trampoline; B: 2 处栈数组 memset 1024->370)。

用法: python mk_fix2.py [输出文件名]
"""
import hashlib, os, struct, sys

sys.stdout.reconfigure(encoding='utf-8')
SRC = r'F:\Games\Taikou 2\Taikou2 Original\TAIK2W95_big.exe'
DST = os.path.join(os.path.dirname(SRC), sys.argv[1] if len(sys.argv) > 1
                   else 'TAIK2W95_big_fix2.exe')
IMAGE_BASE = 0x400000
OLD_N, NEW_N = 0x172, 0x400
LOGGER_VA = 0x54C988          # 日志桩 (ret 4)


def sec_map(d):
    e = struct.unpack_from('<I', d, 0x3C)[0]
    opt = e + 24
    n, = struct.unpack_from('<H', d, e + 6)
    osz, = struct.unpack_from('<H', d, e + 20)
    so = opt + osz
    secs = []
    for i in range(n):
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

    # ---- B) 修栈数组 memset 溢出 (1024 -> 370) ----
    B = [0x49C5E5, 0x49CD3D]
    print('\n[B] 修栈数组 memset 长度 (1024 -> 370):')
    for va in B:
        o = off(va)
        old = bytes(d[o:o + 5])
        assert old == b'\x68\x00\x04\x00\x00', '0x%06X 不是 push 0x400: %s' % (va, old.hex(' '))
        d[o:o + 5] = b'\x68' + struct.pack('<I', OLD_N)
        print('   0x%06X %s -> %s' % (va, old.hex(' '), bytes(d[o:o + 5]).hex(' ')))

    # ---- C) 日志桩调用约定: 删掉多余 add esp,4 ----
    #    扫全镜像里所有 `call 0x54C988`(E8 rel32) 的站点, 看紧随其后是不是 `83 C4 04`
    print('\n[C] 日志桩 0x%06X `ret 4` 的调用点, 清理多余的 add esp,4:' % LOGGER_VA)
    nfix = 0
    for sec in secs:
        nm, va, vs, ra = sec
        base = IMAGE_BASE + va
        blob = d[ra:ra + vs]
        for k in range(len(blob) - 5):
            if blob[k] != 0xE8:
                continue
            rel, = struct.unpack_from('<i', blob, k + 1)
            site = base + k
            if site + 5 + rel != LOGGER_VA:
                continue
            nxt = bytes(blob[k + 5:k + 8])
            tag = '%s@0x%08X' % (nm, site)
            if nxt == b'\x83\xC4\x04':
                d[ra + k + 5:ra + k + 8] = b'\x90\x90\x90'
                nfix += 1
                print('   %s  后接 add esp,4  ->  nop nop nop   ✗已修' % tag)
            else:
                print('   %s  后接 %s  -> 保留(本来就没多清)' % (tag, nxt.hex(' ')))
    assert nfix == 3, '多余 add esp,4 应为 3 处, 实得 %d —— 补丁布局变了, 别盲改' % nfix

    open(DST, 'wb').write(bytes(d))
    print('\n产出: %s (%d B, sha %s)' % (DST, len(d), hashlib.sha256(bytes(d)).hexdigest()[:16]))
    print('试跑: StartTaikou2.bat %s' % os.path.basename(DST))


if __name__ == '__main__':
    main()
