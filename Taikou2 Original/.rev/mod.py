"""
太阁立志传2 —— 现代 Windows 兼容补丁生成脚本（可迭代追加补丁）

基于纯净脱壳版 TAIK2W95_clean.exe，逐个打上绕过崩溃的补丁。
文件偏移 = RVA - 0xC00   （clean.exe 的 .text/.data 都是这个映射）

用法:
    python .rev/mod.py          生成 TAIK2W95_mod.exe
"""
import shutil

BASE = r'F:\Games\Taikou 2\Taikou2 Original\TAIK2W95_clean.exe'
OUT = r'F:\Games\Taikou 2\Taikou2 Original\TAIK2W95_mod.exe'
DELTA = 0xC00

RET1 = b'\xb8\x01\x00\x00\x00\xc3'        # mov eax,1 ; ret
NOP2 = b'\x90\x90'
NOP3 = b'\x90\x90\x90'
RET2E = b'\xb0\x2e\xc3'                   # mov al,0x2E ; ret

RET0 = b'\x33\xc0\xc3'                    # xor eax,eax ; ret

# (RVA, 原字节(用于校验), 新字节, 说明)
PATCHES = [
    # --- 崩溃点 1：调用 mp3.dll 的 mp3play，在 DirectShow/AC3 解码器里 fail-fast ---
    (0x12D342, b'\xff\x55\x20', NOP3,
     '禁用 call [ebp+0x20] (=mp3play)，BGM 不再播放'),

    # --- 崩溃点 2：音乐播放函数内部调用野指针 (EIP=7) ---
    (0x98F80, b'\x56\x8b\x74', RET0,
     '音乐播放函数(参数=曲目号) -> 直接返回 0，不再播放'),
]


def main():
    shutil.copyfile(BASE, OUT)
    b = bytearray(open(OUT, 'rb').read())
    print('基准: %s' % BASE)
    ok = 0
    for rva, expect, new, desc in PATCHES:
        off = rva - DELTA
        cur = bytes(b[off:off + len(new)])
        flag = 'OK ' if cur == expect[:len(new)] else '!! '
        if cur != expect[:len(new)]:
            flag = '!! '
        else:
            ok += 1
        b[off:off + len(new)] = new
        print('  %s RVA 0x%06X file 0x%06X  %s' % (flag, rva, off, desc))
        print('       %s -> %s   (期望原值 %s)'
              % (cur.hex(' '), new.hex(' '), expect[:len(new)].hex(' ')))
    open(OUT, 'wb').write(bytes(b))
    print('\n%d/%d 处补丁字节校验通过 -> %s' % (ok, len(PATCHES), OUT))


if __name__ == '__main__':
    main()
