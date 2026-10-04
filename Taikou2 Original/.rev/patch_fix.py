"""
把 HD 版的"现代系统兼容补丁"移植到纯净脱壳版，但保留原始 640x480 分辨率。

HD 版之所以能在现代 Windows 上跑起来，靠的是把几个初始化函数改成"直接返回成功"，
从而绕开会让进程 fail-fast 崩溃的多媒体初始化。但 HD 版同时把分辨率写死成
1600x1000，导致鼠标坐标与按钮判定不匹配（点不动）。本脚本只取前者。

clean.exe 节表映射： 文件偏移 = RVA - 0xC00
"""
import shutil, struct, sys

SRC = r'F:\Games\Taikou 2\Taikou2 Original\TAIK2W95_clean.exe'
DST = r'F:\Games\Taikou 2\Taikou2 Original\TAIK2W95_fix.exe'
DELTA = 0xC00          # 文件偏移 = RVA - DELTA

RET1 = b'\xb8\x01\x00\x00\x00\xc3'      # mov eax,1; ret
NOP2 = b'\x90\x90'
RET2E = b'\xb0\x2e\xc3'                 # mov al,0x2E; ret

# (RVA, 新字节, 说明)
PATCHES = [
    (0x6e950, RET1,  '函数A -> 返回 1（原: mov eax,[0x514AB4] 后做检查）'),
    (0x6e9ac, NOP2,  'call ebx 后的 jne 判空 -> NOP（不再因失败而跳过）'),
    (0x6ea60, RET1,  '函数B -> 返回 1'),
    (0x6ec00, RET2E, '函数C -> 返回 0x2E（原: call 内部函数后判断 ax>=0）'),
    (0x6f5ae, NOP2,  'mov si,[0x514ABC] 的操作数 -> NOP'),
    (0x98f30, RET1,  '函数D -> 返回 1（原: push 0x27/push 0x22 的多媒体初始化）'),
]

SEL = sys.argv[1:] if len(sys.argv) > 1 else None   # 可指定只打某几项，如 1 3 6


def main():
    shutil.copyfile(SRC, DST)
    d = bytearray(open(DST, 'rb').read())
    print('基准 %s -> %s' % (SRC, DST))
    for i, (rva, new, desc) in enumerate(PATCHES, 1):
        if SEL and str(i) not in SEL:
            print('  [跳过] #%d @RVA 0x%X  %s' % (i, rva, desc))
            continue
        off = rva - DELTA
        old = bytes(d[off:off + len(new)])
        d[off:off + len(new)] = new
        print('  #%d  RVA 0x%06X  file 0x%06X  %s' % (i, rva, off, desc))
        print('        %s  ->  %s' % (old.hex(' '), new.hex(' ')))
    open(DST, 'wb').write(bytes(d))
    print('\n已生成 %s (%d 字节)' % (DST, len(d)))


if __name__ == '__main__':
    main()
