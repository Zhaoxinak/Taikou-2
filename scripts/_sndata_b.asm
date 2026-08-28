==== scene-block decoder 0x47f350 / reader 0x47f5c0 (0x47f340-0x47f740) ====
0047f340  and       al, 0x10
0047f342  jne       0x47f2f5
0047f344  pop       edi
0047f345  pop       esi
0047f346  pop       ebp
0047f347  pop       ebx
0047f348  pop       ecx
0047f349  ret       
0047f34a  nop       
0047f34b  nop       
0047f34c  nop       
0047f34d  nop       
0047f34e  nop       
0047f34f  nop       
0047f350  sub       esp, 0x18
0047f353  push      ebx
0047f354  mov       bx, word ptr [0x520604]
0047f35b  xor       eax, eax
0047f35d  push      ebp
0047f35e  push      esi
0047f35f  mov       ax, bx
0047f362  push      edi
0047f363  mov       edi, eax
0047f365  mov       ebp, eax
0047f367  push      0x10
0047f369  shr       eax, 1
0047f36b  and       eax, 1
0047f36e  mov       esi, ecx
0047f370  mov       dword ptr [esp + 0x18], eax
0047f374  lea       eax, [esp + 0x1c]
0047f378  shr       edi, 2
0047f37b  shr       ebx, 6
0047f37e  push      eax
0047f37f  and       edi, 1
0047f382  and       ebp, 1
0047f385  and       ebx, 0xf
0047f388  call      0x4411b0
0047f38d  push      0x10
0047f38f  lea       ecx, [esp + 0x1c]
0047f393  push      0x4fc240
0047f398  push      ecx
0047f399  call      0x492850
0047f39e  add       esp, 0xc
0047f3a1  test      ax, ax
0047f3a4  je        0x47f3b7
0047f3a6  call      0x47f5b0
0047f3ab  xor       eax, eax
0047f3ad  pop       edi
0047f3ae  pop       esi
0047f3af  pop       ebp
0047f3b0  pop       ebx
0047f3b1  add       esp, 0x18
0047f3b4  ret       4
0047f3b7  lea       eax, [esi + 0x90]
0047f3bd  push      2
0047f3bf  push      eax
0047f3c0  mov       ecx, esi
0047f3c2  call      0x4411b0
0047f3c7  lea       eax, [esi + 0x94]
0047f3cd  push      2
0047f3cf  push      eax
0047f3d0  mov       ecx, esi
0047f3d2  call      0x4411b0
0047f3d7  mov       ax, word ptr [esi + 0x94]
0047f3de  xor       edx, edx
0047f3e0  mov       dl, ah
0047f3e2  and       eax, 0xff
0047f3e7  xor       edx, eax
0047f3e9  push      0x2bc
0047f3ee  push      0x519288
0047f3f3  mov       ecx, esi
0047f3f5  mov       word ptr [esi + 0x94], dx
0047f3fc  call      0x4411b0
0047f401  push      0
0047f403  mov       ecx, 0x524978
0047f408  call      0x4eb5c0
0047f40d  push      0x2bc
0047f412  push      eax
0047f413  mov       ecx, esi
0047f415  mov       dword ptr [esp + 0x18], eax
0047f419  call      0x4411b0
0047f41e  mov       eax, dword ptr [esp + 0x10]
0047f422  cmp       byte ptr [eax], 0x39
0047f425  jne       0x47f438
0047f427  inc       eax
0047f428  push      0x31
0047f42a  push      eax
0047f42b  push      0x519640
0047f430  call      0x492800
0047f435  add       esp, 0xc
0047f438  mov       ecx, esi
0047f43a  call      0x47d960
0047f43f  mov       ecx, 0x526c50
0047f444  call      0x4edfa0
0047f449  mov       ecx, esi
0047f44b  mov       word ptr [esi + 0x92], 0
0047f454  call      0x47dae0
0047f459  mov       ecx, esi
0047f45b  call      0x47dce0
0047f460  mov       ecx, esi
0047f462  call      0x47e130
0047f467  mov       ecx, esi
0047f469  call      0x47e3a0
0047f46e  mov       ecx, esi
0047f470  call      0x47e440
0047f475  mov       ecx, esi
0047f477  call      0x47e5a0
0047f47c  mov       ecx, esi
0047f47e  call      0x47e770
0047f483  mov       ecx, esi
0047f485  call      0x47ea80
0047f48a  mov       ecx, esi
0047f48c  call      0x47ebb0
0047f491  mov       ecx, esi
0047f493  call      0x47ecb0
0047f498  mov       ecx, esi
0047f49a  call      0x47ed10
0047f49f  mov       ecx, esi
0047f4a1  call      0x47ed70
0047f4a6  mov       ecx, esi
0047f4a8  call      0x47ee50
0047f4ad  mov       ecx, esi
0047f4af  call      0x47ef00
0047f4b4  mov       ecx, esi
0047f4b6  call      0x47f050
0047f4bb  mov       ecx, esi
0047f4bd  call      0x47f0a0
0047f4c2  mov       ecx, esi
0047f4c4  call      0x47f1b0
0047f4c9  mov       ecx, esi
0047f4cb  call      0x47f210
0047f4d0  mov       ecx, 0x526c50
0047f4d5  call      0x4edf70
0047f4da  mov       ax, word ptr [esi + 0x92]
0047f4e1  cmp       ax, word ptr [esi + 0x90]
0047f4e8  je        0x47f4fb
0047f4ea  call      0x47f5b0
0047f4ef  xor       eax, eax
0047f4f1  pop       edi
0047f4f2  pop       esi
0047f4f3  pop       ebp
0047f4f4  pop       ebx
0047f4f5  add       esp, 0x18
0047f4f8  ret       4
0047f4fb  mov       ecx, dword ptr [esi + 0x96]
0047f501  mov       edx, dword ptr [esi]
0047f503  add       ecx, 0x9ffa
0047f509  push      0
0047f50b  push      ecx
0047f50c  push      edx
0047f50d  call      dword ptr [0x4fb0a8]
0047f513  push      2
0047f515  push      0x5261ac
0047f51a  mov       ecx, esi
0047f51c  call      0x4411b0
0047f521  push      2
0047f523  push      0x5261b0
0047f528  mov       ecx, esi
0047f52a  call      0x4411b0
0047f52f  push      2
0047f531  push      0x5261a4
0047f536  mov       ecx, esi
0047f538  call      0x4411b0
0047f53d  mov       eax, dword ptr [esp + 0x2c]
0047f541  test      eax, eax
0047f543  jne       0x47f56d
0047f545  mov       bx, word ptr [0x520604]
0047f54c  xor       eax, eax
0047f54e  mov       ax, bx
0047f551  mov       edi, eax
0047f553  mov       ebp, eax
0047f555  shr       eax, 1
0047f557  shr       edi, 2
0047f55a  and       eax, 1
0047f55d  and       edi, 1
0047f560  shr       ebx, 6
0047f563  and       ebp, 1
0047f566  mov       esi, eax
0047f568  and       ebx, 0xf
0047f56b  jmp       0x47f571
0047f56d  mov       esi, dword ptr [esp + 0x14]
0047f571  push      edi
0047f572  mov       ecx, 0x5205f0
0047f577  call      0x49a210
0047f57c  push      ebp
0047f57d  mov       ecx, 0x5205f0
0047f582  call      0x49a1c0
0047f587  push      esi
0047f588  mov       ecx, 0x5205f0
0047f58d  call      0x49a1f0
0047f592  push      ebx
0047f593  mov       ecx, 0x5205f0
0047f598  call      0x49a250
0047f59d  pop       edi
0047f59e  pop       esi
0047f59f  pop       ebp
0047f5a0  mov       eax, 1
0047f5a5  pop       ebx
0047f5a6  add       esp, 0x18
0047f5a9  ret       4
0047f5ac  nop       
0047f5ad  nop       
0047f5ae  nop       
0047f5af  nop       
0047f5b0  push      0x509608
0047f5b5  call      0x47ae80
0047f5ba  add       esp, 4
0047f5bd  ret       
0047f5be  nop       
0047f5bf  nop       
0047f5c0  push      ebx
0047f5c1  push      ebp
0047f5c2  push      esi
0047f5c3  mov       esi, ecx
0047f5c5  push      edi
0047f5c6  mov       ecx, 0x526c50
0047f5cb  call      0x4edfa0
0047f5d0  lea       ebx, [esi + 0x92]
0047f5d6  push      0x100
0047f5db  lea       edi, [esi + 0x94]
0047f5e1  mov       word ptr [ebx], 0
0047f5e6  call      0x4ebd60
0047f5eb  add       esp, 4
0047f5ee  mov       bp, ax
0047f5f1  push      0x100
0047f5f6  call      0x4ebd60
0047f5fb  add       esp, 4
0047f5fe  mov       ecx, esi
0047f600  shl       eax, 8
0047f603  add       ebp, eax
0047f605  push      0x10
0047f607  push      0x4fc240
0047f60c  mov       word ptr [edi], bp
0047f60f  call      0x4411d0
0047f614  push      2
0047f616  push      ebx
0047f617  mov       ecx, esi
0047f619  call      0x4411d0
0047f61e  push      2
0047f620  push      edi
0047f621  mov       ecx, esi
0047f623  call      0x4411d0
0047f628  mov       ax, word ptr [edi]
0047f62b  xor       ecx, ecx
0047f62d  mov       cl, ah
0047f62f  and       eax, 0xff
0047f634  xor       ecx, eax
0047f636  push      0x2bc
0047f63b  mov       word ptr [edi], cx
0047f63e  push      0x519288
0047f643  mov       ecx, esi
0047f645  call      0x4411d0
0047f64a  push      0
0047f64c  mov       ecx, 0x524978
0047f651  call      0x4eb5c0
0047f656  mov       edi, eax
0047f658  push      0x2bc
0047f65d  push      0
0047f65f  push      edi
0047f660  call      0x492820
0047f665  add       esp, 0xc
0047f668  lea       edx, [edi + 1]
0047f66b  mov       byte ptr [edi], 0x39
0047f66e  push      0x31
0047f670  push      0x519640
0047f675  push      edx
0047f676  call      0x492800
0047f67b  add       esp, 0xc
0047f67e  mov       ecx, esi
0047f680  push      0x2bc
0047f685  push      edi
0047f686  call      0x4411d0
0047f68b  push      0
0047f68d  mov       ecx, 0x524978
0047f692  mov       word ptr [esi + 0x8e], 0
0047f69b  call      0x4eb5c0
0047f6a0  mov       ecx, esi
0047f6a2  mov       dword ptr [esi + 0x9a], eax
0047f6a8  call      0x47dba0
0047f6ad  mov       ecx, esi
0047f6af  call      0x47df00
0047f6b4  mov       ecx, esi
0047f6b6  call      0x47e260
0047f6bb  mov       ecx, esi
0047f6bd  call      0x47e3f0
0047f6c2  mov       ecx, esi
0047f6c4  call      0x47e4e0
0047f6c9  mov       ecx, esi
0047f6cb  call      0x47e680
0047f6d0  mov       ecx, esi
0047f6d2  call      0x47e8a0
0047f6d7  mov       ecx, esi
0047f6d9  call      0x47eb10
0047f6de  mov       ecx, esi
0047f6e0  call      0x47ec30
0047f6e5  mov       ecx, esi
0047f6e7  call      0x47ece0
0047f6ec  mov       ecx, esi
0047f6ee  call      0x47ed40
0047f6f3  mov       ecx, esi
0047f6f5  call      0x47ede0
0047f6fa  mov       ecx, esi
0047f6fc  call      0x47eea0
0047f701  mov       ecx, esi
0047f703  call      0x47efa0
0047f708  mov       ecx, esi
0047f70a  call      0x47f070
0047f70f  mov       ecx, esi
0047f711  call      0x47f110
0047f716  mov       ecx, esi
0047f718  call      0x47f1e0
0047f71d  mov       ecx, esi
0047f71f  call      0x47f2a0
0047f724  cmp       word ptr [esi + 0x8e], 0
0047f72c  je        0x47f735
0047f72e  mov       ecx, esi
0047f730  call      0x47d9b0
0047f735  mov       eax, dword ptr [esi + 0x96]
0047f73b  mov       ecx, dword ptr [esi]
==== main record loop 0x47ff68 (0x47ff50-0x480100) ====
0047ff50  sub       esp, 0x5c
0047ff53  lea       eax, [esp]
0047ff57  lea       ecx, [esp + 0x60]
0047ff5b  lea       edx, [esp + 4]
0047ff5f  push      esi
0047ff60  push      eax
0047ff61  mov       eax, dword ptr [esp + 0x68]
0047ff65  push      ecx
0047ff66  push      edx
0047ff67  push      eax
0047ff68  call      0x47fc60
0047ff6d  mov       eax, dword ptr [esp + 0x18]
0047ff71  add       esp, 0x10
0047ff74  test      ax, ax
0047ff77  jne       0x47ffa0
0047ff79  cmp       word ptr [esp + 0x64], ax
0047ff7e  jne       0x47ffa0
0047ff80  cmp       word ptr [esp + 4], ax
0047ff85  jne       0x47ffa0
0047ff87  mov       ecx, dword ptr [0x509648]
0047ff8d  mov       edx, dword ptr [esp + 0x68]
0047ff91  push      ecx
0047ff92  push      edx
0047ff93  call      0x4ebfe0
0047ff98  add       esp, 8
0047ff9b  pop       esi
0047ff9c  add       esp, 0x5c
0047ff9f  ret       
0047ffa0  lea       ecx, [esp + 0xc]
0047ffa4  push      0xa
0047ffa6  push      ecx
0047ffa7  push      eax
0047ffa8  call      0x4ebe60
0047ffad  mov       esi, dword ptr [esp + 0x74]
0047ffb1  add       esp, 0xc
0047ffb4  push      eax
0047ffb5  push      esi
0047ffb6  call      0x4ebfe0
0047ffbb  add       esp, 8
0047ffbe  push      0x509744
0047ffc3  push      esi
0047ffc4  call      0x4ec010
0047ffc9  mov       edx, dword ptr [esp + 0x6c]
0047ffcd  add       esp, 8
0047ffd0  push      edx
0047ffd1  call      0x49f120
0047ffd6  add       esp, 4
0047ffd9  cmp       ax, 2
0047ffdd  jge       0x47ffed
0047ffdf  push      0x5038d0
0047ffe4  push      esi
0047ffe5  call      0x4ec010
0047ffea  add       esp, 8
0047ffed  mov       ecx, dword ptr [esp + 0x64]
0047fff1  lea       eax, [esp + 0xc]
0047fff5  push      0xa
0047fff7  push      eax
0047fff8  push      ecx
0047fff9  call      0x4ebe60
0047fffe  add       esp, 0xc
00480001  push      eax
00480002  push      esi
00480003  call      0x4ec010
00480008  add       esp, 8
0048000b  push      0x509740
00480010  push      esi
00480011  call      0x4ec010
00480016  mov       edx, dword ptr [esp + 0xc]
0048001a  add       esp, 8
0048001d  push      edx
0048001e  call      0x49f120
00480023  add       esp, 4
00480026  cmp       ax, 2
0048002a  jge       0x48003a
0048002c  push      0x5038d0
00480031  push      esi
00480032  call      0x4ec010
00480037  add       esp, 8
0048003a  mov       ecx, dword ptr [esp + 4]
0048003e  lea       eax, [esp + 0xc]
00480042  push      0xa
00480044  push      eax
00480045  push      ecx
00480046  call      0x4ebe60
0048004b  add       esp, 0xc
0048004e  push      eax
0048004f  push      esi
00480050  call      0x4ec010
00480055  add       esp, 8
00480058  push      0x50973c
0048005d  push      esi
0048005e  call      0x4ec010
00480063  add       esp, 8
00480066  lea       edx, [esp + 0xc]
0048006a  push      0x522c88
0048006f  push      edx
00480070  call      0x4ebfe0
00480075  add       esp, 8
00480078  lea       eax, [esp + 0xc]
0048007c  push      eax
0048007d  call      0x4ebfc0
00480082  mov       ecx, 0xe
00480087  add       esp, 4
0048008a  sub       ecx, eax
0048008c  push      ecx
0048008d  push      esi
0048008e  call      0x49f0b0
00480093  add       esp, 8
00480096  lea       edx, [esp + 0xc]
0048009a  push      edx
0048009b  push      esi
0048009c  call      0x4ec010
004800a1  add       esp, 8
004800a4  lea       eax, [esp + 0xc]
004800a8  push      0x522c70
004800ad  push      eax
004800ae  call      0x4ebfe0
004800b3  add       esp, 8
004800b6  lea       ecx, [esp + 0xc]
004800ba  push      ecx
004800bb  call      0x4ebfc0
004800c0  mov       edx, 0x12
004800c5  add       esp, 4
004800c8  sub       edx, eax
004800ca  push      edx
004800cb  push      esi
004800cc  call      0x49f0b0
004800d1  add       esp, 8
004800d4  lea       eax, [esp + 0xc]
004800d8  push      eax
004800d9  push      esi
004800da  call      0x4ec010
004800df  add       esp, 8
004800e2  lea       ecx, [esp + 0xc]
004800e6  push      0x509738
004800eb  push      ecx
004800ec  call      0x4ebfe0
004800f1  add       esp, 8
004800f4  lea       edx, [esp + 0xc]
004800f8  push      0x522c60
004800fd  push      edx