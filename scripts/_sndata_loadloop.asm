0047ff00  ret 
0047ff01  push 0x10
0047ff03  lea ecx, [esp + 4]
0047ff07  push 0x4fc228
0047ff0c  push ecx
0047ff0d  call 0x492850
0047ff12  add esp, 0xc
0047ff15  test ax, ax
0047ff18  jne 0x47ff2b
0047ff1a  mov eax, 1
0047ff1f  mov dword ptr [0x520628], eax
0047ff24  add esp, 0x9c
0047ff2a  ret 
0047ff2b  push 0x509620
0047ff30  call 0x47ae80
0047ff35  add esp, 4
0047ff38  xor eax, eax
0047ff3a  add esp, 0x9c
0047ff40  ret 
0047ff41  nop 
0047ff42  nop 
0047ff43  nop 
0047ff44  nop 
0047ff45  nop 
0047ff46  nop 
0047ff47  nop 
0047ff48  nop 
0047ff49  nop 
0047ff4a  nop 
0047ff4b  nop 
0047ff4c  nop 
0047ff4d  nop 
0047ff4e  nop 
0047ff4f  nop 
0047ff50  sub esp, 0x5c
0047ff53  lea eax, [esp]
0047ff57  lea ecx, [esp + 0x60]
0047ff5b  lea edx, [esp + 4]
0047ff5f  push esi
0047ff60  push eax
0047ff61  mov eax, dword ptr [esp + 0x68]
0047ff65  push ecx
0047ff66  push edx
0047ff67  push eax
0047ff68  call 0x47fc60
0047ff6d  mov eax, dword ptr [esp + 0x18]
0047ff71  add esp, 0x10
0047ff74  test ax, ax
0047ff77  jne 0x47ffa0
0047ff79  cmp word ptr [esp + 0x64], ax
0047ff7e  jne 0x47ffa0
0047ff80  cmp word ptr [esp + 4], ax
0047ff85  jne 0x47ffa0
0047ff87  mov ecx, dword ptr [0x509648]
0047ff8d  mov edx, dword ptr [esp + 0x68]
0047ff91  push ecx
0047ff92  push edx
0047ff93  call 0x4ebfe0
0047ff98  add esp, 8
0047ff9b  pop esi
0047ff9c  add esp, 0x5c
0047ff9f  ret 
0047ffa0  lea ecx, [esp + 0xc]
0047ffa4  push 0xa
0047ffa6  push ecx
0047ffa7  push eax
0047ffa8  call 0x4ebe60
0047ffad  mov esi, dword ptr [esp + 0x74]
0047ffb1  add esp, 0xc
0047ffb4  push eax
0047ffb5  push esi
0047ffb6  call 0x4ebfe0
0047ffbb  add esp, 8
0047ffbe  push 0x509744
0047ffc3  push esi
0047ffc4  call 0x4ec010
0047ffc9  mov edx, dword ptr [esp + 0x6c]
0047ffcd  add esp, 8
0047ffd0  push edx
0047ffd1  call 0x49f120
0047ffd6  add esp, 4
0047ffd9  cmp ax, 2
0047ffdd  jge 0x47ffed
0047ffdf  push 0x5038d0
0047ffe4  push esi
0047ffe5  call 0x4ec010
0047ffea  add esp, 8
0047ffed  mov ecx, dword ptr [esp + 0x64]
0047fff1  lea eax, [esp + 0xc]
0047fff5  push 0xa
0047fff7  push eax
0047fff8  push ecx
0047fff9  call 0x4ebe60
0047fffe  add esp, 0xc
00480001  push eax
00480002  push esi
00480003  call 0x4ec010
00480008  add esp, 8
0048000b  push 0x509740
00480010  push esi
00480011  call 0x4ec010
00480016  mov edx, dword ptr [esp + 0xc]
0048001a  add esp, 8
0048001d  push edx
0048001e  call 0x49f120
00480023  add esp, 4
00480026  cmp ax, 2
0048002a  jge 0x48003a
0048002c  push 0x5038d0
00480031  push esi
00480032  call 0x4ec010
00480037  add esp, 8
0048003a  mov ecx, dword ptr [esp + 4]
0048003e  lea eax, [esp + 0xc]
00480042  push 0xa
00480044  push eax
00480045  push ecx
00480046  call 0x4ebe60
0048004b  add esp, 0xc
0048004e  push eax
0048004f  push esi
00480050  call 0x4ec010
00480055  add esp, 8
00480058  push 0x50973c
0048005d  push esi
0048005e  call 0x4ec010
00480063  add esp, 8
00480066  lea edx, [esp + 0xc]
0048006a  push 0x522c88
0048006f  push edx
00480070  call 0x4ebfe0
00480075  add esp, 8
00480078  lea eax, [esp + 0xc]
0048007c  push eax
0048007d  call 0x4ebfc0
00480082  mov ecx, 0xe
00480087  add esp, 4
0048008a  sub ecx, eax
0048008c  push ecx
0048008d  push esi
0048008e  call 0x49f0b0
00480093  add esp, 8
00480096  lea edx, [esp + 0xc]
0048009a  push edx
0048009b  push esi
0048009c  call 0x4ec010
004800a1  add esp, 8
004800a4  lea eax, [esp + 0xc]
004800a8  push 0x522c70
004800ad  push eax
004800ae  call 0x4ebfe0
004800b3  add esp, 8
004800b6  lea ecx, [esp + 0xc]
004800ba  push ecx
004800bb  call 0x4ebfc0
004800c0  mov edx, 0x12
004800c5  add esp, 4
004800c8  sub edx, eax
004800ca  push edx
004800cb  push esi
004800cc  call 0x49f0b0
004800d1  add esp, 8
004800d4  lea eax, [esp + 0xc]
004800d8  push eax
004800d9  push esi
004800da  call 0x4ec010
004800df  add esp, 8
004800e2  lea ecx, [esp + 0xc]
004800e6  push 0x509738
004800eb  push ecx
004800ec  call 0x4ebfe0
004800f1  add esp, 8
004800f4  lea edx, [esp + 0xc]
004800f8  push 0x522c60
004800fd  push edx
004800fe  call 0x4ec010
00480103  add esp, 8
00480106  lea eax, [esp + 0xc]
0048010a  push eax
0048010b  call 0x4ebfc0
00480110  mov ecx, 0x12
00480115  add esp, 4
00480118  sub ecx, eax
0048011a  push ecx
0048011b  push esi
0048011c  call 0x49f0b0
00480121  add esp, 8
00480124  lea edx, [esp + 0xc]
00480128  push edx
00480129  push esi
0048012a  call 0x4ec010
0048012f  add esp, 8
00480132  pop esi
00480133  add esp, 0x5c
00480136  ret 
00480137  nop 
00480138  nop 
00480139  nop 
0048013a  nop 
0048013b  nop 
0048013c  nop 
0048013d  nop 
0048013e  nop 
0048013f  nop 
00480140  sub esp, 0x8c
00480146  push ebx
00480147  push esi
00480148  push edi
00480149  lea eax, [esp + 0xc]
0048014d  push 3
0048014f  push eax
00480150  mov dword ptr [esp + 0x14], 0
00480158  call 0x47d780
0048015d  add esp, 8
00480160  cmp eax, 1
00480163  jne 0x4801ee
00480169  mov ecx, 0x526c50
0048016e  mov ebx, eax
00480170  call 0x4edfa0
00480175  mov eax, dword ptr [0x520628]
0048017a  test eax, eax
0048017c  mov eax, 0x4fc228
00480181  jne 0x480188
00480183  mov eax, 0x4fc210
00480188  push 0x10
0048018a  push eax
0048018b  lea ecx, [esp + 0x14]
0048018f  call 0x4411d0
00480194  push 0x2000
00480199  push 0
0048019b  push 0
0048019d  mov ecx, 0x524978
004801a2  call 0x4eb5c0
004801a7  push eax
004801a8  call 0x492820
004801ad  add esp, 0xc
004801b0  mov edi, 0x50188
004801b5  cmp edi, 0x2000
004801bb  mov esi, 0x2000
004801c0  jg 0x4801c4
004801c2  mov esi, edi
004801c4  push esi
004801c5  push 0
004801c7  mov ecx, 0x524978
004801cc  call 0x4eb5c0
004801d1  push eax
004801d2  lea ecx, [esp + 0x14]
004801d6  call 0x4411d0
004801db  cmp si, ax
004801de  jne 0x4801ee
004801e0  and esi, 0xffff
004801e6  sub edi, esi
004801e8  test edi, edi
004801ea  jg 0x4801b5
004801ec  jmp 0x4801f0
004801ee  xor ebx, ebx
004801f0  mov ecx, dword ptr [esp + 0xc]
004801f4  push ecx
004801f5  call dword ptr [0x4fb09c]
004801fb  mov ecx, 0x526c50
