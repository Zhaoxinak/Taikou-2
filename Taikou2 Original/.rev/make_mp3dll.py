"""
太阁立志传2 —— 现代 Windows 兼容 MP3.DLL 替代品
================================================

背景
----
原版 mp3.dll 播放 BGM 时走 MCI -> mciqtz32 -> quartz(DirectShow) -> devenum，
枚举解码器 filter 时会加载 Windows 自带的 msmpeg2ac3dec.dll，
该 DLL 在 WOW64 下以 0xC0000602 (FAIL_FAST) 主动自杀，整个进程被杀。

对策
----
用自写的 mp3.dll 顶替，导出同名函数 mp3play / mp3seek / mp3stop，
内部改用 WINMM!PlaySoundA 播放 WAV —— 只走 waveOut/ACM，完全不碰 DirectShow。

调用约定（由游戏代码 RVA 0x12D200 反推）:
    int __stdcall mp3play(const char* path);   // path = ".\\MP3\\01.MP3"
    int __stdcall mp3stop(void);
    mp3seek 在 exe 中从未被调用（ff 55 24 出现 0 次），仅保留导出。

本 DLL 把 path 末尾扩展名替换成 .WAV 再交给 PlaySoundA，
所以需先用 ffmpeg 把 MP3/*.mp3 转成 MP3/*.wav（pcm_s16le）。

本机没有 C 编译器 —— 整个 PE 头和 x86 机器码由本脚本直接拼装。
"""
import os
import struct
import shutil

IMAGEBASE = 0x0F000000        # 挑一个不容易与其他 DLL 冲突的基址
OUT = r'F:\Games\Taikou 2\Taikou2 Original\mp3.dll'

PATHBUF = IMAGEBASE + 0x3000          # .data 起始：路径缓冲（260 字节）
CNT     = PATHBUF + 0x100             # +256: mp3play 调用次数
RETVAL  = PATHBUF + 0x104             # +260: PlaySoundA 返回值
LASTFLG = PATHBUF + 0x108             # +264: 实际传入的 fdwSound
LASTPTR = PATHBUF + 0x10C             # +268: 实际传入的 pszSound 指针
IAT_ADDR = IMAGEBASE + 0x2000 + 0x30  # .rdata + 0x30：IAT 第一项

FILE_ALIGN = 0x200
SECT_ALIGN = 0x1000
HDR_SIZE = 0x200


# ---------------------------------------------------------------- 机器码
def emit_play():
    """int __stdcall mp3play(const char* path) -> 复制路径并把扩展名换成 .WAV"""
    c = bytearray()
    c += bytes([0x55, 0x8B, 0xEC,              # push ebp / mov ebp,esp
                0x56, 0x57, 0x53,              # push esi/edi/ebx
                0x8B, 0x75, 0x08])             # mov esi,[ebp+8]
    i_movedi = len(c) + 1                      # mov edi, imm32 的 imm 偏移
    c += bytes([0xBF, 0, 0, 0, 0])
    c += bytes([0x33, 0xC9, 0x33, 0xD2])       # xor ecx,ecx / xor edx,edx
    L = len(c)
    c += bytes([0x8A, 0x04, 0x0E,              # L+0  mov al,[esi+ecx]
                0x88, 0x04, 0x0F,              # L+3  mov [edi+ecx],al
                0x84, 0xC0,                    # L+6  test al,al
                0x74, 0x0D,                    # L+8  jz  done
                0x3C, 0x2E,                    # L+10 cmp al,'.'
                0x75, 0x03,                    # L+12 jne nod
                0x8D, 0x14, 0x0F,              # L+14 lea edx,[edi+ecx]
                0x41,                          # L+17 nod: inc ecx
                0x83, 0xF9, 0xFA,              # L+18 cmp ecx,250
                0x72, 0xE9])                   # L+21 jb  L
    assert len(c) - L == 23
    c += bytes([0xC6, 0x04, 0x0F, 0x00])       # done: mov byte [edi+ecx],0
    c += bytes([0x85, 0xD2, 0x74, 0x07])       # test edx,edx / jz noext
    # 保留 '.'，从其后开始写 "WAV\0"：  "xx.MP3" -> "xx.WAV"
    c += bytes([0xC7, 0x42, 0x01, 0x57, 0x41, 0x56, 0x00])
    # --- 诊断计数器 ---
    i_cnt = len(c) + 2
    c += bytes([0xFF, 0x05, 0, 0, 0, 0])       # noext: inc dword [CNT]
    # --- PlaySoundA(pszSound, hmod, fdwSound)：stdcall 从右往左压栈 ---
    c += bytes([0x68, 0x09, 0x00, 0x02, 0x00])  # push fdwSound = FILENAME|ASYNC|LOOP
    c += bytes([0x6A, 0x00])                    # push hmod = 0
    i_push = len(c) + 1
    c += bytes([0x68, 0, 0, 0, 0])              # push pszSound = PATHBUF
    i_call = len(c) + 2
    c += bytes([0xFF, 0x15, 0, 0, 0, 0])        # call dword [IAT]
    i_sret = len(c) + 1
    c += bytes([0xA3, 0, 0, 0, 0])              # mov [RETVAL],eax
    # C7 05 <abs32> <imm32>：abs 在 +2，imm 在 +6
    i_sflg = len(c) + 2
    c += bytes([0xC7, 0x05, 0, 0, 0, 0, 0x09, 0x00, 0x02, 0x00])  # mov [LASTFLG],flags
    i_sptr = len(c) + 2
    c += bytes([0xC7, 0x05, 0, 0, 0, 0, 0, 0, 0, 0])              # mov [LASTPTR],PATHBUF
    c += bytes([0xB8, 0x01, 0x00, 0x00, 0x00,  # mov eax,1
                0x5B, 0x5F, 0x5E, 0x5D,        # pop ebx/edi/esi/ebp
                0xC2, 0x04, 0x00])             # ret 4
    assert c[i_movedi - 1] == 0xBF and c[i_push - 1] == 0x68 and c[i_call - 1] == 0x15
    return c, i_movedi, i_push, i_call, i_cnt, i_sret, i_sflg, i_sptr


def emit_stop():
    """int __stdcall mp3stop(void) -> PlaySoundA(NULL,NULL,0)"""
    c = bytearray([0x6A, 0x00, 0x6A, 0x00, 0x6A, 0x00])   # push 0 ×3
    i_call = len(c) + 2
    c += bytes([0xFF, 0x15, 0, 0, 0, 0])                   # call [IAT]
    c += bytes([0xB8, 0x01, 0x00, 0x00, 0x00, 0xC3])       # mov eax,1 / ret
    assert c[i_call - 1] == 0x15
    return c, i_call


CODE_SEEK = bytes([0xB8, 0x01, 0x00, 0x00, 0x00,   # mov eax,1
                   0xC2, 0x08, 0x00])               # ret 8


# ---------------------------------------------------------------- 组装
def build():
    play, p_movedi, p_push, p_call, p_cnt, p_sret, p_sflg, p_sptr = emit_play()
    text = bytearray(play)
    struct.pack_into('<I', text, p_movedi, PATHBUF)
    struct.pack_into('<I', text, p_push, PATHBUF)
    struct.pack_into('<I', text, p_call, IAT_ADDR)
    struct.pack_into('<I', text, p_cnt, CNT)
    struct.pack_into('<I', text, p_sret, RETVAL)
    struct.pack_into('<I', text, p_sflg, LASTFLG)
    struct.pack_into('<I', text, p_sptr, LASTPTR)
    struct.pack_into('<I', text, p_sflg + 4, 0x00020009)
    struct.pack_into('<I', text, p_sptr + 4, PATHBUF)

    off_seek = (len(text) + 3) & ~3
    text += b'\x90' * (off_seek - len(text))
    text += CODE_SEEK

    off_stop = off_seek + 8
    stop, s_call = emit_stop()
    struct.pack_into('<I', stop, s_call, IAT_ADDR)
    text += stop

    relocs = [0x1000 + p_movedi, 0x1000 + p_push, 0x1000 + p_call,
              0x1000 + p_cnt, 0x1000 + p_sret,
              0x1000 + p_sflg, 0x1000 + p_sptr,
              0x1000 + off_stop + s_call]

    # ---------------- .rdata ----------------
    rd = bytearray()
    rd += struct.pack('<IIIII', 0x2000 + 0x28, 0, 0, 0x2000 + 0x38,
                      0x2000 + 0x30)           # 导入描述符
    rd += b'\x00' * 20                         # 结束描述符
    assert len(rd) == 0x28
    rd += struct.pack('<II', 0x2000 + 0x44, 0)  # INT
    assert len(rd) == 0x30
    rd += struct.pack('<II', 0x2000 + 0x44, 0)  # IAT
    assert len(rd) == 0x38
    rd += b'WINMM.DLL\x00' + b'\x00\x00'       # 0x38..0x43（补齐到 0x44）
    assert len(rd) == 0x44
    rd += struct.pack('<H', 0) + b'PlaySoundA\x00'

    name_dll = len(rd)
    rd += b'MP3.DLL\x00'
    name_play = len(rd)
    rd += b'mp3play\x00'
    name_seek = len(rd)
    rd += b'mp3seek\x00'
    name_stop = len(rd)
    rd += b'mp3stop\x00'

    exp_off = len(rd)
    funcs = [(name_play, 0x1000 + 0x00),
             (name_seek, 0x1000 + off_seek),
             (name_stop, 0x1000 + off_stop)]
    eat = exp_off + 40
    enp = eat + 4 * len(funcs)
    eor = enp + 4 * len(funcs)
    # IMAGE_EXPORT_DIRECTORY = 40 字节（版本字段是 2 个 WORD）
    rd += struct.pack('<IIHHIIIIIII',
                      0,                  # Characteristics
                      0,                  # TimeDateStamp
                      0, 0,               # Major/MinorVersion (WORD)
                      0x2000 + name_dll,  # Name
                      1,                  # Base
                      len(funcs),         # NumberOfFunctions
                      len(funcs),         # NumberOfNames
                      0x2000 + eat,       # AddressOfFunctions
                      0x2000 + enp,       # AddressOfNames
                      0x2000 + eor)       # AddressOfNameOrdinals
    for _, fn in funcs:
        rd += struct.pack('<I', fn)
    for noff, _ in funcs:
        rd += struct.pack('<I', 0x2000 + noff)
    for i in range(len(funcs)):
        rd += struct.pack('<H', i)
    exp_size = len(rd) - exp_off

    rel_off = len(rd)
    rd += struct.pack('<II', 0x1000, 8 + 2 * len(relocs))
    for r in relocs:
        rd += struct.pack('<H', (3 << 12) | (r & 0xFFF))
    rel_size = len(rd) - rel_off

    # ---------------- .data ----------------
    data = bytearray(0x200)     # 路径缓冲 260B + 诊断计数器

    # ---------------- PE 头 ----------------
    secs = [(b'.text',  0x1000, len(text), 0x200, 0x60000020),
            (b'.rdata', 0x2000, len(rd),   0x400, 0xC0000040),
            (b'.data',  0x3000, len(data), 0x600, 0xC0000040)]

    dos = bytearray(0x40)
    dos[0:2] = b'MZ'
    struct.pack_into('<I', dos, 0x3C, 0x40)

    coff = struct.pack('<HHIIIHH', 0x014C, len(secs), 0, 0, 0, 0xE0, 0x2102)

    opt = bytearray(0xE0)
    struct.pack_into('<H', opt, 0, 0x10B)
    struct.pack_into('<I', opt, 4, len(text))
    struct.pack_into('<I', opt, 8, len(rd) + len(data))
    struct.pack_into('<I', opt, 16, 0)                 # 无入口点
    struct.pack_into('<I', opt, 20, 0x1000)
    struct.pack_into('<I', opt, 24, 0x2000)
    struct.pack_into('<I', opt, 28, IMAGEBASE)
    struct.pack_into('<I', opt, 32, SECT_ALIGN)
    struct.pack_into('<I', opt, 36, FILE_ALIGN)
    struct.pack_into('<HH', opt, 40, 6, 0)
    struct.pack_into('<HH', opt, 48, 6, 0)
    struct.pack_into('<I', opt, 56, 0x4000)            # SizeOfImage
    struct.pack_into('<I', opt, 60, HDR_SIZE)
    struct.pack_into('<H', opt, 68, 3)                 # Subsystem = CUI
    struct.pack_into('<I', opt, 72, 0x100000)
    struct.pack_into('<I', opt, 76, 0x1000)
    struct.pack_into('<I', opt, 80, 0x100000)
    struct.pack_into('<I', opt, 84, 0x1000)
    struct.pack_into('<I', opt, 92, 16)
    struct.pack_into('<II', opt, 96 + 0 * 8, 0x2000 + exp_off, exp_size)
    struct.pack_into('<II', opt, 96 + 1 * 8, 0x2000, 40)
    struct.pack_into('<II', opt, 96 + 5 * 8, 0x2000 + rel_off, rel_size)
    struct.pack_into('<II', opt, 96 + 12 * 8, 0x2000 + 0x30, 8)

    shdr = b''
    for name, rva, vsize, raw, ch in secs:
        rawsz = ((vsize + FILE_ALIGN - 1) // FILE_ALIGN) * FILE_ALIGN
        shdr += struct.pack('<8sIIIIIIHHI', name, rawsz, rva, rawsz, raw,
                            0, 0, 0, 0, ch)

    hdr = bytes(dos) + b'PE\x00\x00' + coff + bytes(opt) + shdr
    assert len(hdr) <= HDR_SIZE
    hdr += b'\x00' * (HDR_SIZE - len(hdr))

    out = bytearray(hdr)
    bodies = {b'.text': bytes(text), b'.rdata': bytes(rd), b'.data': bytes(data)}
    for name, rva, vsize, raw, ch in secs:
        rawsz = ((vsize + FILE_ALIGN - 1) // FILE_ALIGN) * FILE_ALIGN
        if len(out) < raw:
            out += b'\x00' * (raw - len(out))
        out[raw:raw + len(bodies[name])] = bodies[name]
        if len(out) < raw + rawsz:
            out += b'\x00' * (raw + rawsz - len(out))
    return bytes(out)


def main():
    if os.path.exists(OUT):
        bak = OUT + '.orig.bak'
        if not os.path.exists(bak):
            shutil.copyfile(OUT, bak)
            print('原 mp3.dll 已备份 -> %s' % bak)
    data = build()
    open(OUT, 'wb').write(data)
    print('已生成替代 mp3.dll（%d 字节）' % len(data))
    print('  导出: mp3play / mp3seek / mp3stop')
    print('  实现: WINMM!PlaySoundA 播放 .WAV（循环），不经过 DirectShow')


if __name__ == '__main__':
    main()
