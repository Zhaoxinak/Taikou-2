"""mk_fix3.py — fix2 + 修掉「培养孩子面板姓名渲染写空指针」= TAIK2W95_big_fix3.exe

★ 本次根因（崩溃现场 + 源码对照坐实）
点「培养孩子」→ 崩在我们的回家菜单桩 MENU_SCR(入口 0x550F00, 由 0x4CD563 jmp 进来):

    异常地址 0x005510CE  [MOD+0x5ACE]  mov byte ptr [edi], al
    EAX=0x100 EBX=0 ECX=7 EDX=0x550CE0 ESI=0x54A4B7 EDI=0  ← 往地址 0 写

child_menu.py 的 cm_same 块里 edi **一身兼两职**, 冲突了:

    mov edi, [esp+0x0C]              ; edi = row  行号 (0..page_max-1)
    lea edx, [edi + edi*2]
    shl edx, 3
    add edx, name_buf                ; edx = name_buf + row*24   ← 本行姓名缓冲
    mov [edi*4 + sub_ptr], edx       ; edi 当**索引**  ✓
    mov [edi*2 + slot_arr], ax       ; edi 当**索引**  ✓
    mov esi, eax / shl esi,3 / sub esi,eax / add esi, giv
    mov ecx, 7
  cm_cp_surname:
    mov al, [esi]
    mov byte ptr [edi], al           ; edi 当**写指针** ✗ row=0 时写地址 0 → AV

edx 已经算好了本行缓冲指针却没人拿它当写游标。row=0 ⇒ edi=0 ⇒ 写 0 地址 ⇒ 崩。

★ 修复（等长替换, 不移动任何后续代码）
  mov esi, eax        (89 C6)      -> mov edi, edx      (89 D7)   写游标 = 本行缓冲
  shl esi, 3          (C1 E6 03)   -> imul esi, eax, 7  (6B F0 07)  一次算出 *7
  sub esi, eax        (29 C6)      -> nop nop           (90 90)    已由 imul 完成

原 shl 3 + sub = eax*8 - eax = eax*7, 与 imul esi,eax,7 完全等价。
edi 在 273/275 行当索引用完之后才被改成 edx, 顺序安全;
后面 291/300/308/322 那些 mov byte ptr [edi] 全部跟着变成写本行缓冲。

同时保留 fix1(A:摘5个诊断trampoline, B:2处栈数组memset 1024->370)
与 fix2(C:3处日志桩后多余的 add esp,4)。

用法: python mk_fix3.py [输出文件名]
"""
import hashlib, os, struct, sys

sys.stdout.reconfigure(encoding='utf-8')

SRC = r'F:\Games\Taikou 2\Taikou2 Original\TAIK2W95_big.exe'
DST = os.path.join(os.path.dirname(SRC), sys.argv[1] if len(sys.argv) > 1
                   else 'TAIK2W95_big_fix3.exe')
IMAGE_BASE = 0x400000
OLD_N, NEW_N = 0x172, 0x400
LOGGER_VA = 0x54C988


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

    print('源档: %s (%d B, sha %s)'
          % (SRC, len(d), hashlib.sha256(bytes(d)).hexdigest()[:16]))

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
    print('\n[B] 修栈数组 memset 长度 (1024 -> 370):')
    for va in (0x49C5E5, 0x49CD3D):
        o = off(va)
        old = bytes(d[o:o + 5])
        assert old == b'\x68\x00\x04\x00\x00', '0x%06X 不是 push 0x400: %s' % (va, old.hex(' '))
        d[o:o + 5] = b'\x68' + struct.pack('<I', OLD_N)
        print('   0x%06X %s -> %s' % (va, old.hex(' '), bytes(d[o:o + 5]).hex(' ')))

    # ---- C) 日志桩(ret 4)调用点后多余的 add esp,4 ----
    print('\n[C] 日志桩 0x%06X `ret 4` 的调用点, 清理多余的 add esp,4:' % LOGGER_VA)
    nfix = 0
    for nm, va, vs, ra in secs:
        base = IMAGE_BASE + va
        blob = bytes(d[ra:ra + vs])
        for k in range(len(blob) - 5):
            if blob[k] != 0xE8:
                continue
            rel, = struct.unpack_from('<i', blob, k + 1)
            site = base + k
            if site + 5 + rel != LOGGER_VA:
                continue
            nxt = blob[k + 5:k + 8]
            if nxt == b'\x83\xC4\x04':
                d[ra + k + 5:ra + k + 8] = b'\x90\x90\x90'
                nfix += 1
                print('   %s@0x%08X  add esp,4 -> nop nop nop   ✗已修' % (nm, site))
            else:
                print('   %s@0x%08X  后接 %s -> 保留' % (nm, site, nxt.hex(' ')))
    assert nfix == 3, '多余 add esp,4 应为 3 处, 实得 %d' % nfix

    # ---- D) 姓名渲染写游标: edi 应取 edx(本行缓冲), 不是 row ----
    D = [
        (0x5510BA, b'\x89\xC6', b'\x89\xD7',
         'mov esi,eax     -> mov edi,edx      (写游标 = 本行姓名缓冲)'),
        (0x5510BC, b'\xC1\xE6\x03', b'\x6B\xF0\x07',
         'shl esi,3       -> imul esi,eax,7   (一次算出 *7, 腾出 2B)'),
        (0x5510BF, b'\x29\xC6', b'\x90\x90',
         'sub esi,eax     -> nop nop          (*7 已由 imul 完成)'),
    ]
    print('\n[D] 修姓名渲染写空指针 (edi 误用 row 当写指针):')
    for va, old, new, desc in D:
        o = off(va)
        got = bytes(d[o:o + len(old)])
        assert got == old, '0x%06X 实际 %s != 预期 %s' % (va, got.hex(' '), old.hex(' '))
        assert len(old) == len(new), '0x%06X 长度不等, 会移位' % va
        d[o:o + len(new)] = new
        print('   0x%06X  %s' % (va, desc))
        print('             %s -> %s' % (old.hex(' '), new.hex(' ')))

    open(DST, 'wb').write(bytes(d))
    print('\n产出: %s (%d B, sha %s)'
          % (DST, len(d), hashlib.sha256(bytes(d)).hexdigest()[:16]))
    print('试跑: StartTaikou2_fix3.bat')


if __name__ == '__main__':
    main()
