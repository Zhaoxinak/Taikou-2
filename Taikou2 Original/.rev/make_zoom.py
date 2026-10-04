"""
TAIK2W95_zoom.exe —— 内容真 2x 放大版
原理:
  - 画布(8bpp DIB)与分辨率数组保持 640x400, 游戏逻辑/绘制完全不变
  - 窗口客户区开到 1280x800 (两处 clamp 改为 x2)
  - 贴图出口 0xEFA93 的 1:1 BitBlt 改为 StretchBlt 整幅拉伸到客户区
    (StretchBlt 用 LoadLibraryA+GetProcAddress 动态解析, 存于 g_pSB)
  - 鼠标坐标 ScreenToClient 后 sar 1 (÷2) 映射回 640x400 画布坐标
代码洞: .idata 节扩容到 0x3000, 代码放 RVA 0x134000
"""
import struct

SRC = r'F:\Games\Taikou 2\Taikou2 Original\TAIK2W95_clean.exe'
DST = r'F:\Games\Taikou 2\Taikou2 Original\TAIK2W95_zoom.exe'

DELTA = 0xC00          # clean.exe: file = RVA - 0xC00 (四个节统一)

b = bytearray(open(SRC, 'rb').read())

def rva_off(rva):
    return rva - DELTA

def patch(rva, old, new, desc):
    off = rva_off(rva)
    cur = bytes(b[off:off+len(old)])
    assert cur == old, 'RVA 0x%06X 不匹配:\n  实际 %s\n  期望 %s' % (rva, cur.hex(' '), old.hex(' '))
    assert len(new) == len(old), '长度不等: %s' % desc
    b[off:off+len(new)] = new
    print('OK  RVA 0x%06X  %s' % (rva, desc))

# ---------- A/B. 收敛目标改为常量 1280x800 ----------
# 0xF214C 内的循环把窗口收敛到 [0x526CF0]x[0x529958] (逻辑尺寸=640x400)。
# 把两处加载改成常量, 循环自动把客户区收敛到 1280x800。
patch(0xF220C,
      bytes.fromhex('a1f06c5200'),
      bytes.fromhex('b800050000'),
      '收敛目标宽: mov eax,[0x526CF0] -> mov eax,1280')
patch(0xF2211,
      bytes.fromhex('8b0d58995200'),
      bytes.fromhex('b92003000090'),
      '收敛目标高: mov ecx,[0x529958] -> mov ecx,800')

# ---------- C. 贴图出口: BitBlt 1:1 -> call 拉伸洞 ----------
CAVE = 0x134080
rel = CAVE - (0xEFA94 + 5)
patch(0xEFA94,
      bytes.fromhex('ff7510ff750cffb680905200ff7518ff7514ff7510ff750c57'
                    'e8332e000057ffb6b8b55200ff1568b14f005f5e5bc9c3'),
      b'\xe9' + struct.pack('<i', rel) + b'\x90'*43,
      'present: 1:1 BitBlt -> jmp 拉伸洞 (洞尾 ret 返回原调用者)')

# ---------- D. 鼠标: 整块挪进代码洞 (保持 eax=outx指针/edx=outy指针 契约) ----------
CAVE2 = 0x134180
rel2 = CAVE2 - (0xF1FF6 + 5)
patch(0xF1FF6,
      bytes.fromhex('8b45088b4df88b550c33f689088b4dfc890a3930'
                    '7d0889308935f09a5200'),
      b'\xe8' + struct.pack('<i', rel2) + b'\x90'*25,
      '鼠标: call 坐标换算洞 (原语义)')

# ---------- E. 组装代码洞 ----------
data = bytearray()

def emit(*chunks):
    for c in chunks:
        data.extend(c)

IAT = lambda r: struct.pack('<I', 0x400000 + r)

# --- 页头: 数据 ---
# 0x134000 g_pSB (拉伸函数指针, 运行时解析)
# 0x134010 RECT (16 字节)
# 0x134020 "StretchBlt"
# 0x134030 "GDI32.dll"
# 0x134080 代码
page = bytearray(0x1000)
struct.pack_into('<I', page, 0x000, 0)                    # g_pSB = 0
page[0x020:0x020+11] = b'StretchBlt\x00'
page[0x030:0x030+10] = b'GDI32.dll\x00'

c = bytearray()
c += b'\xff\x05' + struct.pack('<I', 0x534040)   # inc dword [0x534040] 调用计数
# GetClientRect([esi+0x52B5B8], 0x534010)
c += b'\x68' + struct.pack('<I', 0x534010)          # push 0x534010
c += b'\xff\xb6\xb8\xb5\x52\x00'                    # push [esi+0x52B5B8]
c += b'\xff\x15' + IAT(0xFB158)                     # call GetClientRect
# SetStretchBltMode(edi, COLORONCOLOR)
c += b'\x6a\x03'                                    # push 3
c += b'\x57'                                        # push edi
c += b'\xff\x15' + IAT(0xFB04C)                     # call SetStretchBltMode
# if (!g_pSB) g_pSB = GetProcAddress(LoadLibraryA("GDI32.dll"), "StretchBlt")
c += b'\x83\x3d' + struct.pack('<I', 0x534000) + b'\x00'   # cmp [g_pSB],0
jne_at = len(c); c += b'\x75\x00'                          # jne have (回填)
c += b'\x68' + struct.pack('<I', 0x534030)          # push "GDI32.dll"
c += b'\xff\x15' + IAT(0xFB0AC)                     # call LoadLibraryA
c += b'\x68' + struct.pack('<I', 0x534020)          # push "StretchBlt"
c += b'\x50'                                        # push eax
c += b'\xff\x15' + IAT(0xFB0E0)                     # call GetProcAddress
c += b'\xa3' + struct.pack('<I', 0x534000)          # mov [g_pSB],eax
have_at = len(c)
c[jne_at+1] = have_at - (jne_at + 2)                       # 回填 jne
# StretchBlt(hdcDst,0,0,cliW,cliH, hdcSrc,0,0,cw,ch, SRCCOPY)
c += b'\x68\x20\x00\xcc\x00'                        # push SRCCOPY
c += b'\xff\xb6\x18\x92\x52\x00'                    # push [esi+0x529218]  ch
c += b'\xff\xb6\x58\x89\x52\x00'                    # push [esi+0x528958]  cw
c += b'\x6a\x00'                                    # push 0 ySrc
c += b'\x6a\x00'                                    # push 0 xSrc
c += b'\xff\xb6\x80\x90\x52\x00'                    # push [esi+0x529080]  hdcSrc
# 注意: GetClientRect 的 RECT 在 0x534010, right=0x534018, bottom=0x53401C
# (0x534008/0x53400C 从未被写入, 恒为 0 -> StretchBlt 宽高 0 -> 什么都不画!)
c += b'\xff\x35' + struct.pack('<I', 0x53401C)      # push clientH (RECT.bottom)
c += b'\xff\x35' + struct.pack('<I', 0x534018)      # push clientW (RECT.right)
c += b'\x6a\x00'                                    # push 0 yDst
c += b'\x6a\x00'                                    # push 0 xDst
c += b'\x57'                                        # push edi hdcDst
c += b'\xff\x15' + struct.pack('<I', 0x534000)      # call [g_pSB]
c += b'\xa3' + struct.pack('<I', 0x534044)          # mov [0x534044],eax 返回值
# ReleaseDC(hwnd, edi) + 原函数收尾
c += b'\x57'                                        # push edi
c += b'\xff\xb6\xb8\xb5\x52\x00'                    # push [esi+0x52B5B8]
c += b'\xff\x15' + IAT(0xFB168)                     # call ReleaseDC
c += b'\x5f\x5e\x5b\xc9\xc3'                        # pop edi/esi/ebx; leave; ret
assert len(c) <= 0x1000 - 0x80, '代码洞溢出: %d' % len(c)
page[0x080:0x080+len(c)] = c
print('代码洞 %d 字节 @ RVA 0x134080' % len(c))

# --- 坐标换算洞 @ 0x134180: 复刻原 30 字节的完整语义 (含 ÷2) ---
m = bytearray()
m += b'\xd1\x7d\xf8'                    # sar dword [ebp-8],1    pt.x /= 2
m += b'\xd1\x7d\xfc'                    # sar dword [ebp-4],1    pt.y /= 2
m += b'\x8b\x45\x08'                    # mov eax,[ebp+8]        eax = out x ptr
m += b'\x8b\x4d\xf8'                    # mov ecx,[ebp-8]
m += b'\x8b\x55\x0c'                    # mov edx,[ebp+0xc]      edx = out y ptr
m += b'\x33\xf6'                        # xor esi,esi
m += b'\x89\x08'                        # mov [eax],ecx
m += b'\x8b\x4d\xfc'                    # mov ecx,[ebp-4]
m += b'\x89\x0a'                        # mov [edx],ecx
m += b'\x39\x30'                        # cmp [eax],esi
m += b'\x7d\x08'                        # jge +8
m += b'\x89\x30'                        # mov [eax],esi
m += b'\x89\x35\xf0\x9a\x52\x00'        # mov [0x529AF0],esi
m += b'\xc3'                            # ret
page[0x180:0x180+len(m)] = m
print('坐标洞 %d 字节 @ RVA 0x134180' % len(m))

# ---------- F. 扩容 .idata 并写入 ----------
# 节表: opt=0xC8, so=0x1A8, .idata 是第 4 个节 @ 0x1A8+3*40 = 0x220
so_idata = 0x1A8 + 3*40
name = bytes(b[so_idata:so_idata+8])
assert name.rstrip(b'\0') == b'.idata', '第4节不是 .idata: %r' % name
vs, rva, rawsz, rawoff = struct.unpack_from('<IIII', b, so_idata+8)
print('.idata: VS=%X RVA=%X raw=%X @%X' % (vs, rva, rawsz, rawoff))

NEW_VS = 0x3000
idr = bytearray(b[rawoff:rawoff+rawsz])
idr += b'\x00' * (0x1000 - rawsz)      # 对齐到 0x134000
idr += page                            # 洞页 0x1000 (0x134000..0x135000)
idr += b'\x00' * (NEW_VS - len(idr))   # 补齐 VS
assert len(idr) == NEW_VS

out = bytearray(b[:rawoff]) + idr      # .idata 是最后一节, 直接截断重接
struct.pack_into('<I', out, so_idata+8, NEW_VS)     # VirtualSize
struct.pack_into('<I', out, so_idata+16, NEW_VS)    # SizeOfRawData
# SizeOfImage: 0x133000+0x3000 = 0x136000, 原值已够, 不改

open(DST, 'wb').write(bytes(out))
print('\n已生成:', DST, len(out), '字节')
print('  画布 640x400 (数组不变) | 窗口客户区 1280x800 | StretchBlt 2x | 鼠标 ÷2')
