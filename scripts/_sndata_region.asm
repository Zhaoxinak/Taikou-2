0047d720  mov ax, word ptr [esp + 4]
0047d725  push esi
0047d726  cmp ax, 2
0047d72a  jae 0x47d759
0047d72c  test ax, ax
0047d72f  mov esi, 0x5095b0
0047d734  jne 0x47d73b
0047d736  mov esi, 0x5095a0
0047d73b  mov eax, dword ptr [esp + 0xc]
0047d73f  push eax
0047d740  push esi
0047d741  call 0x4802e0
0047d746  test eax, eax
0047d748  jne 0x47d76f
0047d74a  push esi
0047d74b  call 0x47bde0
0047d750  add esp, 4
0047d753  xor eax, eax
0047d755  pop esi
0047d756  ret 8
0047d759  mov edx, dword ptr [esp + 0xc]
0047d75d  push edx
0047d75e  push ecx
0047d75f  call 0x47d780
0047d764  add esp, 8
0047d767  test eax, eax
0047d769  jne 0x47d76f
0047d76b  pop esi
0047d76c  ret 8
0047d76f  mov eax, 1
0047d774  pop esi
0047d775  ret 8
0047d778  nop 
0047d779  nop 
0047d77a  nop 
0047d77b  nop 
0047d77c  nop 
0047d77d  nop 
0047d77e  nop 
0047d77f  nop 
0047d780  sub esp, 0x20
0047d783  lea eax, [esp]
0047d787  push 0x509590
0047d78c  push eax
0047d78d  call 0x4ebfe0
0047d792  mov ecx, dword ptr [0x5095e0]
0047d798  add esp, 8
0047d79b  test ecx, ecx
0047d79d  je 0x47d7ac
0047d79f  call 0x4ef690
0047d7a4  mov ecx, dword ptr [0x5095e0]
0047d7aa  jmp 0x47d7b1
0047d7ac  mov eax, dword ptr [0x526c78]
0047d7b1  add al, 0x40
0047d7b3  mov edx, dword ptr [esp + 0x28]
0047d7b7  mov byte ptr [esp], al
0047d7bb  mov eax, ecx
0047d7bd  neg eax
0047d7bf  sbb eax, eax
0047d7c1  and eax, 4
0047d7c4  or eax, edx
0047d7c6  test ecx, ecx
0047d7c8  je 0x47d7dd
0047d7ca  lea ecx, [esp]
0047d7ce  push eax
0047d7cf  push ecx
0047d7d0  mov ecx, dword ptr [esp + 0x2c]
0047d7d4  call 0x4802e0
0047d7d9  add esp, 0x20
0047d7dc  ret 
0047d7dd  mov ecx, dword ptr [esp + 0x24]
0047d7e1  lea eax, [esp]
0047d7e5  push eax
0047d7e6  push edx
0047d7e7  push ecx
0047d7e8  call 0x47d800
0047d7ed  add esp, 0xc
0047d7f0  add esp, 0x20
0047d7f3  ret 
0047d7f4  nop 
0047d7f5  nop 
0047d7f6  nop 
0047d7f7  nop 
0047d7f8  nop 
0047d7f9  nop 
0047d7fa  nop 
0047d7fb  nop 
0047d7fc  nop 
0047d7fd  nop 
0047d7fe  nop 
0047d7ff  nop 
0047d800  push ebx
0047d801  mov ebx, dword ptr [esp + 0xc]
0047d805  push esi
0047d806  mov esi, dword ptr [esp + 0x14]
0047d80a  push edi
0047d80b  mov edi, dword ptr [esp + 0x10]
0047d80f  push 0
0047d811  call 0x4ef720
0047d816  add esp, 4
0047d819  test eax, eax
0047d81b  je 0x47d82a
0047d81d  push ebx
0047d81e  push esi
0047d81f  mov ecx, edi
0047d821  call 0x4802e0
0047d826  test eax, eax
0047d828  jne 0x47d83d
0047d82a  push 0x5095e8
0047d82f  call 0x47af50
0047d834  add esp, 4
0047d837  test eax, eax
0047d839  je 0x47d846
0047d83b  jmp 0x47d80f
0047d83d  mov eax, 1
0047d842  pop edi
0047d843  pop esi
0047d844  pop ebx
0047d845  ret 
0047d846  pop edi
0047d847  pop esi
0047d848  xor eax, eax
0047d84a  pop ebx
0047d84b  ret 
0047d84c  nop 
0047d84d  nop 
0047d84e  nop 
0047d84f  nop 
0047d850  mov eax, dword ptr [ecx]
0047d852  push eax
0047d853  call dword ptr [0x4fb09c]
0047d859  ret 
0047d85a  nop 
0047d85b  nop 
0047d85c  nop 
0047d85d  nop 
0047d85e  nop 
0047d85f  nop 
0047d860  mov eax, dword ptr [esp + 4]
0047d864  push 0
0047d866  and eax, 0xffff
0047d86b  lea eax, [eax + eax*4]
0047d86e  shl eax, 0xd
0047d871  add eax, 0x198
0047d876  mov dword ptr [ecx + 0x96], eax
0047d87c  mov ecx, dword ptr [ecx]
0047d87e  push eax
0047d87f  push ecx
0047d880  call dword ptr [0x4fb0a8]
0047d886  ret 4
0047d889  nop 
0047d88a  nop 
0047d88b  nop 
0047d88c  nop 
0047d88d  nop 
0047d88e  nop 
0047d88f  nop 
0047d890  mov eax, dword ptr [esp + 4]
0047d894  push esi
0047d895  and eax, 0xffff
0047d89a  mov esi, ecx
0047d89c  push 0
0047d89e  lea ecx, [eax + eax*2]
0047d8a1  shl ecx, 4
0047d8a4  lea edx, [ecx + eax + 0x10]
0047d8a8  mov eax, dword ptr [esi]
0047d8aa  push edx
0047d8ab  push eax
0047d8ac  call dword ptr [0x4fb0a8]
0047d8b2  mov ecx, dword ptr [esp + 0xc]
0047d8b6  push 0x31
0047d8b8  push ecx
0047d8b9  mov ecx, esi
0047d8bb  call 0x4411b0
0047d8c0  pop esi
0047d8c1  ret 8
0047d8c4  nop 
0047d8c5  nop 
0047d8c6  nop 
0047d8c7  nop 
0047d8c8  nop 
0047d8c9  nop 
0047d8ca  nop 
0047d8cb  nop 
0047d8cc  nop 
0047d8cd  nop 
0047d8ce  nop 
0047d8cf  nop 
0047d8d0  mov eax, dword ptr [esp + 4]
0047d8d4  push esi
0047d8d5  and eax, 0xffff
0047d8da  mov esi, ecx
0047d8dc  push 0
0047d8de  lea ecx, [eax + eax*2]
0047d8e1  shl ecx, 4
0047d8e4  lea edx, [ecx + eax + 0x10]
0047d8e8  mov eax, dword ptr [esi]
0047d8ea  push edx
0047d8eb  push eax
0047d8ec  call dword ptr [0x4fb0a8]
0047d8f2  mov ecx, dword ptr [esp + 0xc]
0047d8f6  push 0x31
0047d8f8  push ecx
0047d8f9  mov ecx, esi
0047d8fb  call 0x4411d0
0047d900  pop esi
0047d901  ret 8
0047d904  nop 
0047d905  nop 
0047d906  nop 
0047d907  nop 
0047d908  nop 
0047d909  nop 
0047d90a  nop 
0047d90b  nop 
0047d90c  nop 
0047d90d  nop 
0047d90e  nop 
0047d90f  nop 
0047d910  cmp word ptr [ecx + 0x8c], 0
0047d918  je 0x47d922
0047d91a  call 0x47da10
0047d91f  ret 4
0047d922  call 0x47da10
0047d927  mov ecx, dword ptr [esp + 4]
0047d92b  mov byte ptr [ecx], al
0047d92d  ret 4
0047d930  cmp word ptr [ecx + 0x8c], 0
0047d938  je 0x47d942
0047d93a  call 0x47da50
0047d93f  ret 4
0047d942  call 0x47da50
0047d947  mov ecx, dword ptr [esp + 4]
0047d94b  mov word ptr [ecx], ax
0047d94e  ret 4
0047d951  nop 
0047d952  nop 
0047d953  nop 
0047d954  nop 
0047d955  nop 
0047d956  nop 
0047d957  nop 
0047d958  nop 
0047d959  nop 
0047d95a  nop 
0047d95b  nop 
0047d95c  nop 
0047d95d  nop 
0047d95e  nop 
0047d95f  nop 
0047d960  push ebx
0047d961  push esi
0047d962  mov esi, ecx
0047d964  push 0
0047d966  mov ecx, 0x524978
0047d96b  call 0x4eb5c0
0047d970  push 0x2000
0047d975  push eax
0047d976  mov ecx, esi
0047d978  mov dword ptr [esi + 0x9a], eax
0047d97e  call 0x4411b0
0047d983  mov eax, dword ptr [esi + 0x9a]
0047d989  mov ecx, 0x2000
0047d98e  mov dl, byte ptr [esi + 0x94]
0047d994  mov bl, byte ptr [eax]
0047d996  xor bl, dl
0047d998  mov byte ptr [eax], bl
0047d99a  inc eax
0047d99b  dec ecx
0047d99c  jne 0x47d98e
0047d99e  mov word ptr [esi + 0x8e], 0
0047d9a7  pop esi
0047d9a8  pop ebx
0047d9a9  ret 
0047d9aa  nop 
0047d9ab  nop 
0047d9ac  nop 
0047d9ad  nop 
0047d9ae  nop 
0047d9af  nop 
0047d9b0  push esi
0047d9b1  mov esi, ecx
0047d9b3  push edi
0047d9b4  push 0
0047d9b6  mov di, word ptr [esi + 0x8e]
0047d9bd  mov ecx, 0x524978
0047d9c2  call 0x4eb5c0
0047d9c7  test di, di
0047d9ca  mov dword ptr [esi + 0x9a], eax
0047d9d0  je 0x47d9e8
0047d9d2  and edi, 0xffff
0047d9d8  mov cl, byte ptr [esi + 0x94]
0047d9de  mov dl, byte ptr [eax]
0047d9e0  xor dl, cl
0047d9e2  mov byte ptr [eax], dl
0047d9e4  inc eax
0047d9e5  dec edi
0047d9e6  jne 0x47d9d8
0047d9e8  mov dx, word ptr [esi + 0x8e]
0047d9ef  mov eax, dword ptr [esi + 0x9a]
0047d9f5  push edx
0047d9f6  push eax
0047d9f7  mov ecx, esi
0047d9f9  call 0x4411d0
0047d9fe  mov word ptr [esi + 0x8e], 0
0047da07  pop edi
0047da08  pop esi
0047da09  ret 
0047da0a  nop 
0047da0b  nop 
0047da0c  nop 
0047da0d  nop 
0047da0e  nop 
0047da0f  nop 
0047da10  push esi
0047da11  mov esi, ecx
0047da13  cmp word ptr [esi + 0x8e], 0x2000
0047da1c  jne 0x47da23
0047da1e  call 0x47d960
0047da23  mov ecx, dword ptr [esi + 0x9a]
0047da29  inc word ptr [esi + 0x8e]
0047da30  mov al, byte ptr [ecx]
0047da32  inc ecx
0047da33  mov dword ptr [esi + 0x9a], ecx
0047da39  xor cx, cx
0047da3c  mov cl, al
0047da3e  add word ptr [esi + 0x92], cx
0047da45  pop esi
0047da46  ret 
0047da47  nop 
0047da48  nop 
0047da49  nop 
0047da4a  nop 
0047da4b  nop 
0047da4c  nop 
0047da4d  nop 
0047da4e  nop 
0047da4f  nop 
0047da50  push esi
0047da51  push edi
0047da52  mov esi, ecx
0047da54  call 0x47da10
0047da59  mov ecx, esi
0047da5b  movzx di, al
0047da5f  call 0x47da10
0047da64  and eax, 0xff
0047da69  shl eax, 8
0047da6c  add eax, edi
0047da6e  pop edi
0047da6f  pop esi
0047da70  ret 
0047da71  nop 
0047da72  nop 
0047da73  nop 
0047da74  nop 
0047da75  nop 
0047da76  nop 
0047da77  nop 
0047da78  nop 
0047da79  nop 
0047da7a  nop 
0047da7b  nop 
0047da7c  nop 
0047da7d  nop 
0047da7e  nop 
0047da7f  nop 
0047da80  mov edx, dword ptr [ecx + 0x9a]
0047da86  mov al, byte ptr [esp + 4]
0047da8a  inc word ptr [ecx + 0x8e]
0047da91  mov byte ptr [edx], al
0047da93  mov edx, dword ptr [ecx + 0x9a]
0047da99  movzx ax, al
0047da9d  add word ptr [ecx + 0x92], ax
0047daa4  inc edx
0047daa5  cmp word ptr [ecx + 0x8e], 0x2000
0047daae  mov dword ptr [ecx + 0x9a], edx
0047dab4  jne 0x47dabb
0047dab6  call 0x47d9b0
0047dabb  ret 4
0047dabe  nop 
0047dabf  nop 
0047dac0  push ebx
0047dac1  mov ebx, dword ptr [esp + 8]
0047dac5  push esi
0047dac6  mov esi, ecx
0047dac8  push ebx
0047dac9  call 0x47da80
0047dace  xor eax, eax
0047dad0  mov ecx, esi
0047dad2  mov al, bh
0047dad4  push eax
0047dad5  call 0x47da80
0047dada  pop esi
0047dadb  pop ebx
0047dadc  ret 4
0047dadf  nop 
0047dae0  push esi
0047dae1  mov esi, ecx
0047dae3  push 0x5205f0
0047dae8  call 0x47d910
0047daed  push 0x5205f1
0047daf2  mov ecx, esi
0047daf4  call 0x47d910
0047daf9  push 0x5205f2
0047dafe  mov ecx, esi
0047db00  call 0x47d910
0047db05  push 0x5205f3
0047db0a  mov ecx, esi
0047db0c  call 0x47d910
0047db11  push 0x5205f4
0047db16  mov ecx, esi
0047db18  call 0x47d910
0047db1d  push 0x5205f5
0047db22  mov ecx, esi
0047db24  call 0x47d910
0047db29  push 0x5205f6
0047db2e  mov ecx, esi
0047db30  call 0x47d930
0047db35  push 0x5205f8
0047db3a  mov ecx, esi
0047db3c  call 0x47d930
0047db41  push 0x5205fa
0047db46  mov ecx, esi
0047db48  call 0x47d930
0047db4d  push 0x5205fc
0047db52  mov ecx, esi
0047db54  call 0x47d930
0047db59  push 0x5205fe
0047db5e  mov ecx, esi
0047db60  call 0x47d930
0047db65  push 0x520600
0047db6a  mov ecx, esi
0047db6c  call 0x47d930
0047db71  push 0x520602
0047db76  mov ecx, esi
0047db78  call 0x47d910
0047db7d  push 0x520603
0047db82  mov ecx, esi
0047db84  call 0x47d910
0047db89  push 0x520604
0047db8e  mov ecx, esi
0047db90  call 0x47d930
0047db95  pop esi
0047db96  ret 
0047db97  nop 
0047db98  nop 
0047db99  nop 
0047db9a  nop 
0047db9b  nop 
0047db9c  nop 
0047db9d  nop 
0047db9e  nop 
0047db9f  nop 
0047dba0  push ecx
0047dba1  mov al, byte ptr [0x5205f0]
0047dba6  push esi
0047dba7  mov esi, ecx
0047dba9  mov byte ptr [esp + 4], al
0047dbad  mov ecx, dword ptr [esp + 4]
0047dbb1  push ecx
0047dbb2  mov ecx, esi
0047dbb4  call 0x47da80
0047dbb9  mov dl, byte ptr [0x5205f1]
0047dbbf  mov ecx, esi
0047dbc1  mov byte ptr [esp + 4], dl
0047dbc5  mov eax, dword ptr [esp + 4]
0047dbc9  push eax
0047dbca  call 0x47da80
0047dbcf  mov cl, byte ptr [0x5205f2]
0047dbd5  mov byte ptr [esp + 4], cl
0047dbd9  mov ecx, esi
0047dbdb  mov edx, dword ptr [esp + 4]
0047dbdf  push edx
0047dbe0  call 0x47da80
0047dbe5  mov al, byte ptr [0x5205f3]
0047dbea  mov byte ptr [esp + 4], al
0047dbee  mov ecx, dword ptr [esp + 4]
0047dbf2  push ecx
0047dbf3  mov ecx, esi
0047dbf5  call 0x47da80
0047dbfa  mov dl, byte ptr [0x5205f4]
0047dc00  mov ecx, esi
0047dc02  mov byte ptr [esp + 4], dl
0047dc06  mov eax, dword ptr [esp + 4]
0047dc0a  push eax
0047dc0b  call 0x47da80
0047dc10  mov cl, byte ptr [0x5205f5]
0047dc16  mov byte ptr [esp + 4], cl
0047dc1a  mov ecx, esi
0047dc1c  mov edx, dword ptr [esp + 4]
0047dc20  push edx
0047dc21  call 0x47da80
0047dc26  mov ax, word ptr [0x5205f6]
0047dc2c  mov word ptr [esp + 4], ax
0047dc31  mov ecx, dword ptr [esp + 4]
0047dc35  push ecx
0047dc36  mov ecx, esi
0047dc38  call 0x47dac0
0047dc3d  mov eax, dword ptr [0x5205f8]
0047dc42  mov ecx, esi
0047dc44  push eax
0047dc45  call 0x47dac0
0047dc4a  mov dx, word ptr [0x5205fa]
0047dc51  mov ecx, esi
0047dc53  mov word ptr [esp + 4], dx
0047dc58  mov eax, dword ptr [esp + 4]
0047dc5c  push eax
0047dc5d  call 0x47dac0
0047dc62  mov eax, dword ptr [0x5205fc]
0047dc67  mov ecx, esi
0047dc69  push eax
0047dc6a  call 0x47dac0
0047dc6f  mov cx, word ptr [0x5205fe]
0047dc76  mov word ptr [esp + 4], cx
0047dc7b  mov ecx, esi
0047dc7d  mov edx, dword ptr [esp + 4]
0047dc81  push edx
0047dc82  call 0x47dac0
0047dc87  mov eax, dword ptr [0x520600]
0047dc8c  mov ecx, esi
0047dc8e  push eax
0047dc8f  call 0x47dac0
0047dc94  mov al, byte ptr [0x520602]
0047dc99  mov byte ptr [esp + 4], al
0047dc9d  mov ecx, dword ptr [esp + 4]
0047dca1  push ecx
0047dca2  mov ecx, esi
0047dca4  call 0x47da80
0047dca9  mov dl, byte ptr [0x520603]
0047dcaf  mov ecx, esi
0047dcb1  mov byte ptr [esp + 4], dl
0047dcb5  mov eax, dword ptr [esp + 4]
0047dcb9  push eax
0047dcba  call 0x47da80
0047dcbf  mov cx, word ptr [0x520604]
0047dcc6  mov word ptr [esp + 4], cx
0047dccb  mov ecx, esi
0047dccd  mov edx, dword ptr [esp + 4]
0047dcd1  push edx
0047dcd2  call 0x47dac0
0047dcd7  pop esi
0047dcd8  pop ecx
0047dcd9  ret 
0047dcda  nop 
0047dcdb  nop 
0047dcdc  nop 
0047dcdd  nop 
0047dcde  nop 
0047dcdf  nop 
0047dce0  sub esp, 0xc
0047dce3  push ebx
0047dce4  push ebp
0047dce5  push esi
0047dce6  push edi
0047dce7  mov esi, ecx
0047dce9  mov edi, 0x51986a
0047dcee  mov dword ptr [esp + 0x10], 0
0047dcf6  mov dword ptr [esp + 0x14], 0x172
0047dcfe  mov eax, dword ptr [esp + 0x10]
0047dd02  mov ebp, 7
0047dd07  lea ebx, [eax + 0x521aa8]
0047dd0d  push ebx
0047dd0e  mov ecx, esi
0047dd10  call 0x47d910
0047dd15  inc ebx
0047dd16  dec ebp
0047dd17  jne 0x47dd0d
0047dd19  mov ecx, dword ptr [esp + 0x10]
0047dd1d  mov ebp, 7
0047dd22  lea ebx, [ecx + 0x520660]
0047dd28  push ebx
0047dd29  mov ecx, esi
0047dd2b  call 0x47d910
0047dd30  inc ebx
0047dd31  dec ebp
0047dd32  jne 0x47dd28
0047dd34  lea edx, [edi - 2]
0047dd37  mov ecx, esi
0047dd39  push edx
0047dd3a  call 0x47d930
0047dd3f  push edi
0047dd40  mov ecx, esi
0047dd42  call 0x47d930
0047dd47  lea eax, [esp + 0x18]
0047dd4b  mov ecx, esi
0047dd4d  push eax
0047dd4e  call 0x47d930
0047dd53  mov ecx, dword ptr [esp + 0x18]
0047dd57  cmp cx, 0x172
0047dd5c  jae 0x47dd73
0047dd5e  and ecx, 0xffff
0047dd64  lea eax, [ecx + ecx*2]
0047dd67  shl eax, 4
0047dd6a  sub eax, ecx
0047dd6c  add eax, 0x519868
0047dd71  jmp 0x47dd75
0047dd73  xor eax, eax
0047dd75  lea ecx, [edi + 6]
0047dd78  mov dword ptr [edi + 2], eax
0047dd7b  push ecx
0047dd7c  mov ecx, esi
0047dd7e  call 0x47d930
0047dd83  lea edx, [edi + 8]
0047dd86  mov ecx, esi
0047dd88  push edx
0047dd89  call 0x47d910
0047dd8e  lea eax, [edi + 9]
0047dd91  mov ecx, esi
0047dd93  push eax
0047dd94  call 0x47d910
0047dd99  lea ecx, [edi + 0xa]
0047dd9c  push ecx
0047dd9d  mov ecx, esi
0047dd9f  call 0x47d910
0047dda4  lea edx, [edi + 0xb]
0047dda7  mov ecx, esi
0047dda9  push edx
0047ddaa  call 0x47d910
0047ddaf  lea eax, [edi + 0xc]
0047ddb2  mov ecx, esi
0047ddb4  push eax
0047ddb5  call 0x47d910
0047ddba  lea ecx, [edi + 0xd]
0047ddbd  push ecx
0047ddbe  mov ecx, esi
0047ddc0  call 0x47d910
0047ddc5  lea edx, [edi + 0xe]
0047ddc8  mov ecx, esi
0047ddca  push edx
0047ddcb  call 0x47d910
0047ddd0  lea eax, [edi + 0xf]
0047ddd3  mov ecx, esi
0047ddd5  push eax
0047ddd6  call 0x47d910
0047dddb  lea ecx, [edi + 0x10]
0047ddde  push ecx
0047dddf  mov ecx, esi
0047dde1  call 0x47d910
0047dde6  lea edx, [edi + 0x11]
0047dde9  mov ecx, esi
0047ddeb  push edx
0047ddec  call 0x47d910
0047ddf1  lea eax, [edi + 0x12]
0047ddf4  mov ecx, esi
0047ddf6  push eax
0047ddf7  call 0x47d910
0047ddfc  lea ecx, [edi + 0x13]
0047ddff  push ecx
0047de00  mov ecx, esi
0047de02  call 0x47d910
0047de07  lea edx, [edi + 0x14]
0047de0a  mov ecx, esi
0047de0c  push edx
0047de0d  call 0x47d910
0047de12  lea eax, [edi + 0x15]
0047de15  mov ecx, esi
0047de17  push eax
0047de18  call 0x47d910
0047de1d  lea ecx, [edi + 0x16]
0047de20  push ecx
0047de21  mov ecx, esi
0047de23  call 0x47d930
0047de28  lea edx, [edi + 0x18]
0047de2b  mov ecx, esi
0047de2d  push edx
0047de2e  call 0x47d910
0047de33  lea eax, [edi + 0x19]
0047de36  mov ecx, esi
0047de38  push eax
0047de39  call 0x47d930
0047de3e  lea ecx, [edi + 0x1b]
0047de41  push ecx
0047de42  mov ecx, esi
0047de44  call 0x47d930
0047de49  lea edx, [edi + 0x1d]
0047de4c  mov ecx, esi
0047de4e  push edx
0047de4f  call 0x47d910
0047de54  lea eax, [edi + 0x1e]
0047de57  mov ecx, esi
0047de59  push eax
0047de5a  call 0x47d910
0047de5f  lea ecx, [edi + 0x1f]
0047de62  push ecx
0047de63  mov ecx, esi
0047de65  call 0x47d910
0047de6a  lea edx, [edi + 0x20]
0047de6d  mov ecx, esi
0047de6f  push edx
0047de70  call 0x47d910
0047de75  lea eax, [edi + 0x21]
0047de78  mov ecx, esi
0047de7a  push eax
0047de7b  call 0x47d910
0047de80  lea ecx, [edi + 0x22]
0047de83  push ecx
0047de84  mov ecx, esi
0047de86  call 0x47d910
0047de8b  lea edx, [edi + 0x23]
0047de8e  mov ecx, esi
0047de90  push edx
0047de91  call 0x47d910
0047de96  lea eax, [edi + 0x24]
0047de99  mov ecx, esi
0047de9b  push eax
0047de9c  call 0x47d930
0047dea1  lea ecx, [edi + 0x26]
0047dea4  push ecx
0047dea5  mov ecx, esi
0047dea7  call 0x47d910
0047deac  lea edx, [edi + 0x27]
0047deaf  mov ecx, esi
0047deb1  push edx
0047deb2  call 0x47d910
0047deb7  lea eax, [edi + 0x28]
0047deba  mov ecx, esi
0047debc  push eax
0047debd  call 0x47d930
0047dec2  lea ecx, [edi + 0x2a]
0047dec5  push ecx
0047dec6  mov ecx, esi
0047dec8  call 0x47d930
0047decd  lea edx, [edi + 0x2c]
0047ded0  mov ecx, esi
0047ded2  push edx
0047ded3  call 0x47d910
0047ded8  mov edx, dword ptr [esp + 0x10]
0047dedc  mov eax, dword ptr [esp + 0x14]
0047dee0  add edx, 7
0047dee3  add edi, 0x2f
0047dee6  dec eax
0047dee7  mov dword ptr [esp + 0x10], edx
0047deeb  mov dword ptr [esp + 0x14], eax
0047deef  jne 0x47dcfe
0047def5  pop edi
0047def6  pop esi
0047def7  pop ebp
0047def8  pop ebx
0047def9  add esp, 0xc
0047defc  ret 
0047defd  nop 
0047defe  nop 
0047deff  nop 
0047df00  sub esp, 8
0047df03  push ebx
0047df04  push ebp
0047df05  push esi
0047df06  push edi
0047df07  mov esi, ecx
0047df09  mov edi, 0x51986a
0047df0e  mov dword ptr [esp + 0x10], 0
0047df16  mov dword ptr [esp + 0x14], 0x172
0047df1e  mov eax, dword ptr [esp + 0x10]
0047df22  mov ebp, 7
0047df27  lea ebx, [eax + 0x521aa8]
0047df2d  mov cl, byte ptr [ebx]
0047df2f  push ecx
0047df30  mov ecx, esi
0047df32  call 0x47da80
0047df37  inc ebx
0047df38  dec ebp
0047df39  jne 0x47df2d
0047df3b  mov edx, dword ptr [esp + 0x10]
0047df3f  mov ebp, 7
0047df44  lea ebx, [edx + 0x520660]
0047df4a  mov al, byte ptr [ebx]
0047df4c  mov ecx, esi
0047df4e  push eax
0047df4f  call 0x47da80
0047df54  inc ebx
0047df55  dec ebp
0047df56  jne 0x47df4a
0047df58  mov cx, word ptr [edi - 2]
0047df5c  push ecx
0047df5d  mov ecx, esi
0047df5f  call 0x47dac0
0047df64  mov dx, word ptr [edi]
0047df67  mov ecx, esi
0047df69  push edx
0047df6a  call 0x47dac0
0047df6f  mov eax, dword ptr [edi + 2]
0047df72  test eax, eax
0047df74  jne 0x47df7d
0047df76  mov edx, 0x172
0047df7b  jmp 0x47df97
0047df7d  sub eax, 0x519868
0047df82  mov ecx, eax
0047df84  mov eax, 0xae4c415d
0047df89  imul ecx
0047df8b  add edx, ecx
0047df8d  sar edx, 5
0047df90  mov eax, edx
0047df92  shr eax, 0x1f
0047df95  add edx, eax
0047df97  push edx
0047df98  mov ecx, esi
0047df9a  call 0x47dac0
0047df9f  mov cx, word ptr [edi + 6]
0047dfa3  push ecx
0047dfa4  mov ecx, esi
0047dfa6  call 0x47dac0
0047dfab  mov dl, byte ptr [edi + 8]
0047dfae  mov ecx, esi
0047dfb0  push edx
0047dfb1  call 0x47da80
0047dfb6  mov al, byte ptr [edi + 9]
0047dfb9  mov ecx, esi
0047dfbb  push eax
0047dfbc  call 0x47da80
0047dfc1  mov cl, byte ptr [edi + 0xa]
0047dfc4  push ecx
0047dfc5  mov ecx, esi
0047dfc7  call 0x47da80
0047dfcc  mov dl, byte ptr [edi + 0xb]
0047dfcf  mov ecx, esi
0047dfd1  push edx
0047dfd2  call 0x47da80
0047dfd7  mov al, byte ptr [edi + 0xc]
0047dfda  mov ecx, esi
0047dfdc  push eax
0047dfdd  call 0x47da80
0047dfe2  mov cl, byte ptr [edi + 0xd]
0047dfe5  push ecx
0047dfe6  mov ecx, esi
0047dfe8  call 0x47da80
0047dfed  mov dl, byte ptr [edi + 0xe]
0047dff0  mov ecx, esi
0047dff2  push edx
0047dff3  call 0x47da80
0047dff8  mov al, byte ptr [edi + 0xf]
0047dffb  mov ecx, esi
0047dffd  push eax
0047dffe  call 0x47da80
0047e003  mov cl, byte ptr [edi + 0x10]
0047e006  push ecx
0047e007  mov ecx, esi
0047e009  call 0x47da80
0047e00e  mov dl, byte ptr [edi + 0x11]
0047e011  mov ecx, esi
0047e013  push edx
0047e014  call 0x47da80
0047e019  mov al, byte ptr [edi + 0x12]
0047e01c  mov ecx, esi
0047e01e  push eax
0047e01f  call 0x47da80
0047e024  mov cl, byte ptr [edi + 0x13]
0047e027  push ecx
0047e028  mov ecx, esi
0047e02a  call 0x47da80
0047e02f  mov dl, byte ptr [edi + 0x14]
0047e032  mov ecx, esi
0047e034  push edx
0047e035  call 0x47da80
0047e03a  mov al, byte ptr [edi + 0x15]
0047e03d  mov ecx, esi
0047e03f  push eax
0047e040  call 0x47da80
0047e045  mov cx, word ptr [edi + 0x16]
0047e049  push ecx
0047e04a  mov ecx, esi
0047e04c  call 0x47dac0
0047e051  mov dl, byte ptr [edi + 0x18]
0047e054  mov ecx, esi
0047e056  push edx
0047e057  call 0x47da80
0047e05c  mov ax, word ptr [edi + 0x19]
0047e060  mov ecx, esi
0047e062  push eax
0047e063  call 0x47dac0
0047e068  mov cx, word ptr [edi + 0x1b]
0047e06c  push ecx
0047e06d  mov ecx, esi
0047e06f  call 0x47dac0
0047e074  mov dl, byte ptr [edi + 0x1d]
0047e077  push edx
0047e078  mov ecx, esi
0047e07a  call 0x47da80
0047e07f  mov al, byte ptr [edi + 0x1e]
0047e082  mov ecx, esi
0047e084  push eax
0047e085  call 0x47da80
0047e08a  mov cl, byte ptr [edi + 0x1f]
0047e08d  push ecx
0047e08e  mov ecx, esi
0047e090  call 0x47da80
0047e095  mov dl, byte ptr [edi + 0x20]
0047e098  mov ecx, esi
0047e09a  push edx
0047e09b  call 0x47da80
0047e0a0  mov al, byte ptr [edi + 0x21]
0047e0a3  mov ecx, esi
0047e0a5  push eax
0047e0a6  call 0x47da80
0047e0ab  mov cl, byte ptr [edi + 0x22]
0047e0ae  push ecx
0047e0af  mov ecx, esi
0047e0b1  call 0x47da80
0047e0b6  mov dl, byte ptr [edi + 0x23]
0047e0b9  mov ecx, esi
0047e0bb  push edx
0047e0bc  call 0x47da80
0047e0c1  mov ax, word ptr [edi + 0x24]
0047e0c5  mov ecx, esi
0047e0c7  push eax
0047e0c8  call 0x47dac0
0047e0cd  mov cl, byte ptr [edi + 0x26]
0047e0d0  push ecx
0047e0d1  mov ecx, esi
0047e0d3  call 0x47da80
0047e0d8  mov dl, byte ptr [edi + 0x27]
0047e0db  mov ecx, esi
0047e0dd  push edx
0047e0de  call 0x47da80
0047e0e3  mov ax, word ptr [edi + 0x28]
0047e0e7  mov ecx, esi
0047e0e9  push eax
0047e0ea  call 0x47dac0
0047e0ef  mov cx, word ptr [edi + 0x2a]
0047e0f3  push ecx
0047e0f4  mov ecx, esi
0047e0f6  call 0x47dac0
0047e0fb  mov dl, byte ptr [edi + 0x2c]
0047e0fe  mov ecx, esi
0047e100  push edx
0047e101  call 0x47da80
0047e106  mov edx, dword ptr [esp + 0x10]
0047e10a  mov eax, dword ptr [esp + 0x14]
0047e10e  add edx, 7
0047e111  add edi, 0x2f
0047e114  dec eax
0047e115  mov dword ptr [esp + 0x10], edx
0047e119  mov dword ptr [esp + 0x14], eax
0047e11d  jne 0x47df1e
0047e123  pop edi
0047e124  pop esi
0047e125  pop ebp
0047e126  pop ebx
0047e127  add esp, 8
0047e12a  ret 
0047e12b  nop 
0047e12c  nop 
0047e12d  nop 
0047e12e  nop 
0047e12f  nop 
0047e130  sub esp, 8
0047e133  push ebx
0047e134  push esi
0047e135  push edi
0047e136  mov edi, ecx
0047e138  mov esi, 0x51eb8c
0047e13d  mov ebx, 0xc8
0047e142  lea eax, [esp + 0xc]
0047e146  mov ecx, edi
0047e148  push eax
0047e149  call 0x47d930
0047e14e  mov ecx, dword ptr [esp + 0xc]
0047e152  cmp cx, 0x172
0047e157  jae 0x47e16e
0047e159  and ecx, 0xffff
0047e15f  lea eax, [ecx + ecx*2]
0047e162  shl eax, 4
0047e165  sub eax, ecx
0047e167  add eax, 0x519868
0047e16c  jmp 0x47e170
0047e16e  xor eax, eax
0047e170  lea ecx, [esp + 0x10]
0047e174  mov dword ptr [esi - 4], eax
0047e177  push ecx
0047e178  mov ecx, edi
0047e17a  call 0x47d910
0047e17f  mov eax, dword ptr [esp + 0x10]
0047e183  cmp al, 0xc8
0047e185  jae 0x47e19a
0047e187  and eax, 0xff
0047e18c  mov ecx, eax
0047e18e  shl eax, 5
0047e191  sub eax, ecx
0047e193  add eax, 0x51eb88
0047e198  jmp 0x47e19c
0047e19a  xor eax, eax
0047e19c  lea edx, [esi + 4]
0047e19f  mov ecx, edi
0047e1a1  push edx
0047e1a2  mov dword ptr [esi], eax
0047e1a4  call 0x47d910
0047e1a9  lea eax, [esi + 5]
0047e1ac  mov ecx, edi
0047e1ae  push eax
0047e1af  call 0x47d910
0047e1b4  lea ecx, [esi + 6]
0047e1b7  push ecx
0047e1b8  mov ecx, edi
0047e1ba  call 0x47d930
0047e1bf  lea edx, [esi + 8]
0047e1c2  mov ecx, edi
0047e1c4  push edx
0047e1c5  call 0x47d910
0047e1ca  lea eax, [esi + 9]
0047e1cd  mov ecx, edi
0047e1cf  push eax
0047e1d0  call 0x47d910
0047e1d5  lea ecx, [esi + 0xa]
0047e1d8  push ecx
0047e1d9  mov ecx, edi
0047e1db  call 0x47d910
0047e1e0  lea edx, [esi + 0xb]
0047e1e3  mov ecx, edi
0047e1e5  push edx
0047e1e6  call 0x47d910
0047e1eb  lea eax, [esi + 0xc]
0047e1ee  mov ecx, edi
0047e1f0  push eax
0047e1f1  call 0x47d930
0047e1f6  lea ecx, [esi + 0xe]
0047e1f9  push ecx
0047e1fa  mov ecx, edi
0047e1fc  call 0x47d930
0047e201  lea edx, [esi + 0x10]
0047e204  mov ecx, edi
0047e206  push edx
0047e207  call 0x47d930
0047e20c  lea eax, [esi + 0x12]
0047e20f  mov ecx, edi
0047e211  push eax
0047e212  call 0x47d930
0047e217  lea ecx, [esi + 0x14]
0047e21a  push ecx
0047e21b  mov ecx, edi
0047e21d  call 0x47d930
0047e222  lea edx, [esi + 0x16]
0047e225  mov ecx, edi
0047e227  push edx
0047e228  call 0x47d910
0047e22d  lea eax, [esi + 0x17]
0047e230  mov ecx, edi
0047e232  push eax
0047e233  call 0x47d930
0047e238  lea ecx, [esi + 0x19]
0047e23b  push ecx
0047e23c  mov ecx, edi
0047e23e  call 0x47d930
0047e243  add esi, 0x1f
0047e246  dec ebx
0047e247  jne 0x47e142
0047e24d  pop edi
0047e24e  pop esi
0047e24f  pop ebx
0047e250  add esp, 8
0047e253  ret 
0047e254  nop 
0047e255  nop 
0047e256  nop 
0047e257  nop 
0047e258  nop 
0047e259  nop 
0047e25a  nop 
0047e25b  nop 
0047e25c  nop 
0047e25d  nop 
0047e25e  nop 
0047e25f  nop 
0047e260  push ecx
0047e261  push ebx
0047e262  push ebp
0047e263  push esi
0047e264  mov ebx, 0xc8
0047e269  push edi
0047e26a  mov edi, ecx
0047e26c  mov esi, 0x51eb8c
0047e271  mov ebp, ebx
0047e273  mov eax, dword ptr [esi - 4]
0047e276  test eax, eax
0047e278  jne 0x47e281
0047e27a  mov edx, 0x172
0047e27f  jmp 0x47e29b
0047e281  sub eax, 0x519868
0047e286  mov ecx, eax
0047e288  mov eax, 0xae4c415d
0047e28d  imul ecx
0047e28f  add edx, ecx
0047e291  sar edx, 5
0047e294  mov eax, edx
0047e296  shr eax, 0x1f
0047e299  add edx, eax
0047e29b  push edx
0047e29c  mov ecx, edi
0047e29e  call 0x47dac0
0047e2a3  mov eax, dword ptr [esi]
0047e2a5  test eax, eax
0047e2a7  jne 0x47e2af
0047e2a9  mov byte ptr [esp + 0x10], bl
0047e2ad  jmp 0x47e2cd
0047e2af  sub eax, 0x51eb88
0047e2b4  mov ecx, eax
0047e2b6  mov eax, 0x84210843
0047e2bb  imul ecx
0047e2bd  add edx, ecx
0047e2bf  sar edx, 4
0047e2c2  mov ecx, edx
0047e2c4  shr ecx, 0x1f
0047e2c7  add edx, ecx
0047e2c9  mov byte ptr [esp + 0x10], dl
0047e2cd  mov edx, dword ptr [esp + 0x10]
0047e2d1  mov ecx, edi
0047e2d3  push edx
0047e2d4  call 0x47da80
0047e2d9  mov al, byte ptr [esi + 4]
0047e2dc  mov ecx, edi
0047e2de  push eax
0047e2df  call 0x47da80
0047e2e4  mov cl, byte ptr [esi + 5]
0047e2e7  push ecx
0047e2e8  mov ecx, edi
0047e2ea  call 0x47da80
0047e2ef  mov dx, word ptr [esi + 6]
0047e2f3  mov ecx, edi
0047e2f5  push edx
0047e2f6  call 0x47dac0
0047e2fb  mov al, byte ptr [esi + 8]
0047e2fe  mov ecx, edi
0047e300  push eax
0047e301  call 0x47da80
0047e306  mov cl, byte ptr [esi + 9]
0047e309  push ecx
0047e30a  mov ecx, edi
0047e30c  call 0x47da80
0047e311  mov dl, byte ptr [esi + 0xa]
0047e314  mov ecx, edi
0047e316  push edx
0047e317  call 0x47da80
0047e31c  mov al, byte ptr [esi + 0xb]
0047e31f  mov ecx, edi
0047e321  push eax
0047e322  call 0x47da80
0047e327  mov cx, word ptr [esi + 0xc]
0047e32b  push ecx
0047e32c  mov ecx, edi
0047e32e  call 0x47dac0
0047e333  mov dx, word ptr [esi + 0xe]
0047e337  mov ecx, edi
0047e339  push edx
0047e33a  call 0x47dac0
0047e33f  mov ax, word ptr [esi + 0x10]
0047e343  mov ecx, edi
0047e345  push eax
0047e346  call 0x47dac0
0047e34b  mov cx, word ptr [esi + 0x12]
0047e34f  push ecx
0047e350  mov ecx, edi
0047e352  call 0x47dac0
0047e357  mov dx, word ptr [esi + 0x14]
0047e35b  mov ecx, edi
0047e35d  push edx
0047e35e  call 0x47dac0
0047e363  mov al, byte ptr [esi + 0x16]
0047e366  mov ecx, edi
0047e368  push eax
0047e369  call 0x47da80
0047e36e  mov cx, word ptr [esi + 0x17]
0047e372  push ecx
0047e373  mov ecx, edi
0047e375  call 0x47dac0
0047e37a  mov dx, word ptr [esi + 0x19]
0047e37e  mov ecx, edi
0047e380  push edx
0047e381  call 0x47dac0
0047e386  add esi, 0x1f
0047e389  dec ebp
0047e38a  jne 0x47e273
0047e390  pop edi
0047e391  pop esi
0047e392  pop ebp
0047e393  pop ebx
0047e394  pop ecx
0047e395  ret 
0047e396  nop 
0047e397  nop 
0047e398  nop 
0047e399  nop 
0047e39a  nop 
0047e39b  nop 
0047e39c  nop 
0047e39d  nop 
0047e39e  nop 
0047e39f  nop 
0047e3a0  push ebx
0047e3a1  push esi
0047e3a2  push edi
0047e3a3  mov edi, ecx
0047e3a5  mov esi, 0x519549
0047e3aa  mov ebx, 0x31
0047e3af  lea eax, [esi - 1]
0047e3b2  mov ecx, edi
0047e3b4  push eax
0047e3b5  call 0x47d910
0047e3ba  push esi
0047e3bb  mov ecx, edi
0047e3bd  call 0x47d910
0047e3c2  lea ecx, [esi + 1]
0047e3c5  push ecx
0047e3c6  mov ecx, edi
0047e3c8  call 0x47d910
0047e3cd  lea edx, [esi + 2]
0047e3d0  mov ecx, edi
0047e3d2  push edx
0047e3d3  call 0x47d930
0047e3d8  add esi, 5
0047e3db  dec ebx
0047e3dc  jne 0x47e3af
0047e3de  pop edi
0047e3df  pop esi
0047e3e0  pop ebx
0047e3e1  ret 
0047e3e2  nop 
0047e3e3  nop 
0047e3e4  nop 
0047e3e5  nop 
0047e3e6  nop 
0047e3e7  nop 
0047e3e8  nop 
0047e3e9  nop 
0047e3ea  nop 
0047e3eb  nop 
0047e3ec  nop 
0047e3ed  nop 
0047e3ee  nop 
0047e3ef  nop 
0047e3f0  push ebx
0047e3f1  push esi
0047e3f2  push edi
0047e3f3  mov edi, ecx
0047e3f5  mov esi, 0x519549
0047e3fa  mov ebx, 0x31
0047e3ff  mov al, byte ptr [esi - 1]
0047e402  mov ecx, edi
0047e404  push eax
0047e405  call 0x47da80
0047e40a  mov cl, byte ptr [esi]
0047e40c  push ecx
0047e40d  mov ecx, edi
0047e40f  call 0x47da80
0047e414  mov dl, byte ptr [esi + 1]
0047e417  mov ecx, edi
0047e419  push edx
0047e41a  call 0x47da80
0047e41f  mov ax, word ptr [esi + 2]
0047e423  mov ecx, edi
0047e425  push eax
0047e426  call 0x47dac0
0047e42b  add esi, 5
0047e42e  dec ebx
0047e42f  jne 0x47e3ff
0047e431  pop edi
0047e432  pop esi
0047e433  pop ebx
0047e434  ret 
0047e435  nop 
0047e436  nop 
0047e437  nop 
0047e438  nop 
0047e439  nop 
0047e43a  nop 
0047e43b  nop 
0047e43c  nop 
0047e43d  nop 
0047e43e  nop 
0047e43f  nop 
0047e440  push ecx
0047e441  push ebx
0047e442  push esi
0047e443  push edi
0047e444  mov edi, ecx
0047e446  mov esi, 0x5179bc
0047e44b  mov ebx, 0x31
0047e450  lea eax, [esp + 0xc]
0047e454  mov ecx, edi
0047e456  push eax
0047e457  call 0x47d910
0047e45c  mov eax, dword ptr [esp + 0xc]
0047e460  cmp al, 0xc8
0047e462  jae 0x47e477
0047e464  and eax, 0xff
0047e469  mov ecx, eax
0047e46b  shl eax, 5
0047e46e  sub eax, ecx
0047e470  add eax, 0x51eb88
0047e475  jmp 0x47e479
0047e477  xor eax, eax
0047e479  push esi
0047e47a  mov ecx, edi
0047e47c  mov dword ptr [esi - 4], eax
0047e47f  call 0x47d930
0047e484  lea ecx, [esi + 2]
0047e487  push ecx
0047e488  mov ecx, edi
0047e48a  call 0x47d930
0047e48f  lea edx, [esi + 4]
0047e492  mov ecx, edi
0047e494  push edx
0047e495  call 0x47d910
0047e49a  lea eax, [esi + 5]
0047e49d  mov ecx, edi
0047e49f  push eax
0047e4a0  call 0x47d910
0047e4a5  lea ecx, [esi + 6]
0047e4a8  push ecx
0047e4a9  mov ecx, edi
0047e4ab  call 0x47d910
0047e4b0  lea edx, [esi + 7]
0047e4b3  mov ecx, edi
0047e4b5  push edx
0047e4b6  call 0x47d910
0047e4bb  lea eax, [esi + 8]
0047e4be  mov ecx, edi
0047e4c0  push eax
0047e4c1  call 0x47d910
0047e4c6  lea ecx, [esi + 9]
0047e4c9  push ecx
0047e4ca  mov ecx, edi
0047e4cc  call 0x47d910
0047e4d1  add esi, 0xe
0047e4d4  dec ebx
0047e4d5  jne 0x47e450
0047e4db  pop edi
0047e4dc  pop esi
0047e4dd  pop ebx
0047e4de  pop ecx
0047e4df  ret 
0047e4e0  push ecx
0047e4e1  push ebx
0047e4e2  push ebp
0047e4e3  push esi
0047e4e4  push edi
0047e4e5  mov edi, ecx
0047e4e7  mov esi, 0x5179bc
0047e4ec  mov ebp, 0x31
0047e4f1  mov bl, 0xc8
0047e4f3  mov eax, dword ptr [esi - 4]
0047e4f6  test eax, eax
0047e4f8  jne 0x47e500
0047e4fa  mov byte ptr [esp + 0x10], bl
0047e4fe  jmp 0x47e51e
0047e500  sub eax, 0x51eb88
0047e505  mov ecx, eax
0047e507  mov eax, 0x84210843
0047e50c  imul ecx
0047e50e  add edx, ecx
0047e510  sar edx, 4
0047e513  mov eax, edx
0047e515  shr eax, 0x1f
0047e518  add edx, eax
0047e51a  mov byte ptr [esp + 0x10], dl
0047e51e  mov ecx, dword ptr [esp + 0x10]
0047e522  push ecx
0047e523  mov ecx, edi
0047e525  call 0x47da80
0047e52a  mov dx, word ptr [esi]
0047e52d  mov ecx, edi
0047e52f  push edx
0047e530  call 0x47dac0
0047e535  mov ax, word ptr [esi + 2]
0047e539  mov ecx, edi
0047e53b  push eax
0047e53c  call 0x47dac0
0047e541  mov cl, byte ptr [esi + 4]
0047e544  push ecx
0047e545  mov ecx, edi
0047e547  call 0x47da80
0047e54c  mov dl, byte ptr [esi + 5]
0047e54f  mov ecx, edi
0047e551  push edx
0047e552  call 0x47da80
0047e557  mov al, byte ptr [esi + 6]
0047e55a  mov ecx, edi
0047e55c  push eax
0047e55d  call 0x47da80
0047e562  mov cl, byte ptr [esi + 7]
0047e565  push ecx
0047e566  mov ecx, edi
0047e568  call 0x47da80
0047e56d  mov dl, byte ptr [esi + 8]
0047e570  mov ecx, edi
0047e572  push edx
0047e573  call 0x47da80
0047e578  mov al, byte ptr [esi + 9]
0047e57b  mov ecx, edi
0047e57d  push eax
0047e57e  call 0x47da80
0047e583  add esi, 0xe
0047e586  dec ebp
0047e587  jne 0x47e4f3
0047e58d  pop edi
0047e58e  pop esi
0047e58f  pop ebp
0047e590  pop ebx
0047e591  pop ecx
0047e592  ret 
0047e593  nop 
0047e594  nop 
0047e595  nop 
0047e596  nop 
0047e597  nop 
0047e598  nop 
0047e599  nop 
0047e59a  nop 
0047e59b  nop 
0047e59c  nop 
0047e59d  nop 
0047e59e  nop 
0047e59f  nop 
0047e5a0  push ebx
0047e5a1  push esi
0047e5a2  push edi
0047e5a3  mov edi, ecx
0047e5a5  mov esi, 0x5197b2
0047e5aa  mov ebx, 6
0047e5af  lea eax, [esi - 2]
0047e5b2  mov ecx, edi
0047e5b4  push eax
0047e5b5  call 0x47d930
0047e5ba  push esi
0047e5bb  mov ecx, edi
0047e5bd  call 0x47d930
0047e5c2  lea ecx, [esi + 2]
0047e5c5  push ecx
0047e5c6  mov ecx, edi
0047e5c8  call 0x47d930
0047e5cd  lea edx, [esi + 4]
0047e5d0  mov ecx, edi
0047e5d2  push edx
0047e5d3  call 0x47d930
0047e5d8  lea eax, [esi + 6]
0047e5db  mov ecx, edi
0047e5dd  push eax
0047e5de  call 0x47d930
0047e5e3  lea ecx, [esi + 8]
0047e5e6  push ecx
0047e5e7  mov ecx, edi
0047e5e9  call 0x47d930
0047e5ee  lea edx, [esi + 0xa]
0047e5f1  mov ecx, edi
0047e5f3  push edx
0047e5f4  call 0x47d930
0047e5f9  lea eax, [esi + 0xc]
0047e5fc  mov ecx, edi
0047e5fe  push eax
0047e5ff  call 0x47d910
0047e604  lea ecx, [esi + 0xd]
0047e607  push ecx
0047e608  mov ecx, edi
0047e60a  call 0x47d910
0047e60f  lea edx, [esi + 0xe]
0047e612  mov ecx, edi
0047e614  push edx
0047e615  call 0x47d930
0047e61a  lea eax, [esi + 0x10]
0047e61d  mov ecx, edi
0047e61f  push eax
0047e620  call 0x47d910
0047e625  lea ecx, [esi + 0x11]
0047e628  push ecx
0047e629  mov ecx, edi
0047e62b  call 0x47d910
0047e630  lea edx, [esi + 0x12]
0047e633  mov ecx, edi
0047e635  push edx
0047e636  call 0x47d930
0047e63b  lea eax, [esi + 0x14]
0047e63e  mov ecx, edi
0047e640  push eax
0047e641  call 0x47d930
0047e646  lea ecx, [esi + 0x16]
0047e649  push ecx
0047e64a  mov ecx, edi
0047e64c  call 0x47d930
0047e651  lea edx, [esi + 0x18]
0047e654  mov ecx, edi
0047e656  push edx
0047e657  call 0x47d930
0047e65c  lea eax, [esi + 0x1a]
0047e65f  mov ecx, edi
0047e661  push eax
0047e662  call 0x47d930
0047e667  add esi, 0x1e
0047e66a  dec ebx
0047e66b  jne 0x47e5af
0047e671  pop edi
0047e672  pop esi
0047e673  pop ebx
0047e674  ret 
0047e675  nop 
0047e676  nop 
0047e677  nop 
0047e678  nop 
0047e679  nop 
0047e67a  nop 
0047e67b  nop 
0047e67c  nop 
0047e67d  nop 
0047e67e  nop 
0047e67f  nop 
0047e680  push ebx
0047e681  push esi
0047e682  push edi
0047e683  mov edi, ecx
0047e685  mov esi, 0x5197b2
0047e68a  mov ebx, 6
0047e68f  mov ax, word ptr [esi - 2]
0047e693  mov ecx, edi
0047e695  push eax
0047e696  call 0x47dac0
0047e69b  mov cx, word ptr [esi]
0047e69e  push ecx
0047e69f  mov ecx, edi
0047e6a1  call 0x47dac0
0047e6a6  mov dx, word ptr [esi + 2]
0047e6aa  mov ecx, edi
0047e6ac  push edx
0047e6ad  call 0x47dac0
0047e6b2  mov ax, word ptr [esi + 4]
0047e6b6  mov ecx, edi
0047e6b8  push eax
0047e6b9  call 0x47dac0
0047e6be  mov cx, word ptr [esi + 6]
0047e6c2  push ecx
0047e6c3  mov ecx, edi
0047e6c5  call 0x47dac0
0047e6ca  mov dx, word ptr [esi + 8]
0047e6ce  mov ecx, edi
0047e6d0  push edx
0047e6d1  call 0x47dac0
0047e6d6  mov ax, word ptr [esi + 0xa]
0047e6da  mov ecx, edi
0047e6dc  push eax
0047e6dd  call 0x47dac0
0047e6e2  mov cl, byte ptr [esi + 0xc]
0047e6e5  push ecx
0047e6e6  mov ecx, edi
0047e6e8  call 0x47da80
0047e6ed  mov dl, byte ptr [esi + 0xd]
0047e6f0  mov ecx, edi
0047e6f2  push edx
0047e6f3  call 0x47da80
0047e6f8  mov ax, word ptr [esi + 0xe]
0047e6fc  mov ecx, edi
0047e6fe  push eax
0047e6ff  call 0x47dac0
0047e704  mov cl, byte ptr [esi + 0x10]
0047e707  push ecx
0047e708  mov ecx, edi
0047e70a  call 0x47da80
0047e70f  mov dl, byte ptr [esi + 0x11]
0047e712  mov ecx, edi
0047e714  push edx
0047e715  call 0x47da80
0047e71a  mov ax, word ptr [esi + 0x12]
0047e71e  mov ecx, edi
0047e720  push eax
0047e721  call 0x47dac0
0047e726  mov cx, word ptr [esi + 0x14]
0047e72a  push ecx
0047e72b  mov ecx, edi
0047e72d  call 0x47dac0
0047e732  mov dx, word ptr [esi + 0x16]
0047e736  mov ecx, edi
0047e738  push edx
0047e739  call 0x47dac0
0047e73e  mov ax, word ptr [esi + 0x18]
0047e742  mov ecx, edi
0047e744  push eax
0047e745  call 0x47dac0
0047e74a  mov cx, word ptr [esi + 0x1a]
0047e74e  push ecx
0047e74f  mov ecx, edi
0047e751  call 0x47dac0
0047e756  add esi, 0x1e
0047e759  dec ebx
0047e75a  jne 0x47e68f
0047e760  pop edi
0047e761  pop esi
0047e762  pop ebx
0047e763  ret 
0047e764  nop 
0047e765  nop 
0047e766  nop 
0047e767  nop 
0047e768  nop 
0047e769  nop 
0047e76a  nop 
0047e76b  nop 
0047e76c  nop 
0047e76d  nop 
0047e76e  nop 
0047e76f  nop 
0047e770  push esi
0047e771  mov esi, ecx
0047e773  push 0x516610
0047e778  call 0x47d930
0047e77d  push 0x516612
0047e782  mov ecx, esi
0047e784  call 0x47d930
0047e789  push 0x516614
0047e78e  mov ecx, esi
0047e790  call 0x47d930
0047e795  push 0x516616
0047e79a  mov ecx, esi
0047e79c  call 0x47d930
0047e7a1  push 0x516618
0047e7a6  mov ecx, esi
0047e7a8  call 0x47d930
0047e7ad  push 0x51661a
0047e7b2  mov ecx, esi
0047e7b4  call 0x47d930
0047e7b9  push 0x51661c
0047e7be  mov ecx, esi
0047e7c0  call 0x47d930
0047e7c5  push 0x51661e
0047e7ca  mov ecx, esi
0047e7cc  call 0x47d910
0047e7d1  push 0x51661f
0047e7d6  mov ecx, esi
0047e7d8  call 0x47d910
0047e7dd  push 0x516620
0047e7e2  mov ecx, esi
0047e7e4  call 0x47d930
0047e7e9  push 0x516622
0047e7ee  mov ecx, esi
0047e7f0  call 0x47d910
0047e7f5  push 0x516623
0047e7fa  mov ecx, esi
0047e7fc  call 0x47d910
0047e801  push 0x516624
0047e806  mov ecx, esi
0047e808  call 0x47d930
0047e80d  push 0x516626
0047e812  mov ecx, esi
0047e814  call 0x47d930
0047e819  push 0x516628
0047e81e  mov ecx, esi
0047e820  call 0x47d930
0047e825  push 0x51662a
0047e82a  mov ecx, esi
0047e82c  call 0x47d930
0047e831  push 0x51662c
0047e836  mov ecx, esi
0047e838  call 0x47d930
0047e83d  push 0x51662e
0047e842  mov ecx, esi
0047e844  call 0x47d930
0047e849  push 0x516630
0047e84e  mov ecx, esi
0047e850  call 0x47d930
0047e855  push 0x516632
0047e85a  mov ecx, esi
0047e85c  call 0x47d930
0047e861  push 0x516634
0047e866  mov ecx, esi
0047e868  call 0x47d930
0047e86d  push 0x516636
0047e872  mov ecx, esi
0047e874  call 0x47d930
0047e879  push 0x516638
0047e87e  mov ecx, esi
0047e880  call 0x47d930
0047e885  push 0x51663a
0047e88a  mov ecx, esi
0047e88c  call 0x47d930
0047e891  push 0x51663c
0047e896  mov ecx, esi
0047e898  call 0x47d930
0047e89d  pop esi
0047e89e  ret 
0047e89f  nop 
0047e8a0  push ecx
0047e8a1  mov eax, dword ptr [0x516610]
0047e8a6  push esi
0047e8a7  mov esi, ecx
0047e8a9  push eax
0047e8aa  call 0x47dac0
0047e8af  mov ax, word ptr [0x516612]
0047e8b5  mov word ptr [esp + 4], ax
0047e8ba  mov ecx, dword ptr [esp + 4]
0047e8be  push ecx
0047e8bf  mov ecx, esi
0047e8c1  call 0x47dac0
0047e8c6  mov eax, dword ptr [0x516614]
0047e8cb  mov ecx, esi
0047e8cd  push eax
0047e8ce  call 0x47dac0
0047e8d3  mov dx, word ptr [0x516616]
0047e8da  mov ecx, esi
0047e8dc  mov word ptr [esp + 4], dx
0047e8e1  mov eax, dword ptr [esp + 4]
0047e8e5  push eax
0047e8e6  call 0x47dac0
0047e8eb  mov eax, dword ptr [0x516618]
0047e8f0  mov ecx, esi
0047e8f2  push eax
0047e8f3  call 0x47dac0
0047e8f8  mov cx, word ptr [0x51661a]
0047e8ff  mov word ptr [esp + 4], cx
0047e904  mov ecx, esi
0047e906  mov edx, dword ptr [esp + 4]
0047e90a  push edx
0047e90b  call 0x47dac0
0047e910  mov eax, dword ptr [0x51661c]
0047e915  mov ecx, esi
0047e917  push eax
0047e918  call 0x47dac0
0047e91d  mov al, byte ptr [0x51661e]
0047e922  mov byte ptr [esp + 4], al
0047e926  mov ecx, dword ptr [esp + 4]
0047e92a  push ecx
0047e92b  mov ecx, esi
0047e92d  call 0x47da80
0047e932  mov dl, byte ptr [0x51661f]
0047e938  mov ecx, esi
0047e93a  mov byte ptr [esp + 4], dl
0047e93e  mov eax, dword ptr [esp + 4]
0047e942  push eax
0047e943  call 0x47da80
0047e948  mov eax, dword ptr [0x516620]
0047e94d  mov ecx, esi
0047e94f  push eax
0047e950  call 0x47dac0
0047e955  mov cl, byte ptr [0x516622]
0047e95b  mov byte ptr [esp + 4], cl
0047e95f  mov ecx, esi
0047e961  mov edx, dword ptr [esp + 4]
0047e965  push edx
0047e966  call 0x47da80
0047e96b  mov al, byte ptr [0x516623]
0047e970  mov byte ptr [esp + 4], al
0047e974  mov ecx, dword ptr [esp + 4]
0047e978  push ecx
0047e979  mov ecx, esi
0047e97b  call 0x47da80
0047e980  mov eax, dword ptr [0x516624]
0047e985  mov ecx, esi
0047e987  push eax
0047e988  call 0x47dac0
0047e98d  mov dx, word ptr [0x516626]
0047e994  mov ecx, esi
0047e996  mov word ptr [esp + 4], dx
0047e99b  mov eax, dword ptr [esp + 4]
0047e99f  push eax
0047e9a0  call 0x47dac0
0047e9a5  mov eax, dword ptr [0x516628]
0047e9aa  mov ecx, esi
0047e9ac  push eax
0047e9ad  call 0x47dac0
0047e9b2  mov cx, word ptr [0x51662a]
0047e9b9  mov word ptr [esp + 4], cx
0047e9be  mov edx, dword ptr [esp + 4]
0047e9c2  push edx
0047e9c3  mov ecx, esi
0047e9c5  call 0x47dac0
0047e9ca  mov eax, dword ptr [0x51662c]
0047e9cf  mov ecx, esi
0047e9d1  push eax
0047e9d2  call 0x47dac0
0047e9d7  mov ax, word ptr [0x51662e]
0047e9dd  mov word ptr [esp + 4], ax
0047e9e2  mov ecx, dword ptr [esp + 4]
0047e9e6  push ecx
0047e9e7  mov ecx, esi
0047e9e9  call 0x47dac0
0047e9ee  mov eax, dword ptr [0x516630]
0047e9f3  mov ecx, esi
0047e9f5  push eax
0047e9f6  call 0x47dac0
0047e9fb  mov dx, word ptr [0x516632]
0047ea02  mov ecx, esi
0047ea04  mov word ptr [esp + 4], dx
0047ea09  mov eax, dword ptr [esp + 4]
0047ea0d  push eax
0047ea0e  call 0x47dac0
0047ea13  mov eax, dword ptr [0x516634]
0047ea18  mov ecx, esi
0047ea1a  push eax
0047ea1b  call 0x47dac0
0047ea20  mov cx, word ptr [0x516636]
0047ea27  mov word ptr [esp + 4], cx
0047ea2c  mov ecx, esi
0047ea2e  mov edx, dword ptr [esp + 4]
0047ea32  push edx
0047ea33  call 0x47dac0
0047ea38  mov eax, dword ptr [0x516638]
0047ea3d  mov ecx, esi
0047ea3f  push eax
0047ea40  call 0x47dac0
0047ea45  mov ax, word ptr [0x51663a]
0047ea4b  mov word ptr [esp + 4], ax
0047ea50  mov ecx, dword ptr [esp + 4]
0047ea54  push ecx
0047ea55  mov ecx, esi
0047ea57  call 0x47dac0
0047ea5c  mov dx, word ptr [0x51663c]
0047ea63  mov ecx, esi
0047ea65  mov word ptr [esp + 4], dx
0047ea6a  mov eax, dword ptr [esp + 4]
0047ea6e  push eax
0047ea6f  call 0x47dac0
0047ea74  pop esi
0047ea75  pop ecx
0047ea76  ret 
0047ea77  nop 
0047ea78  nop 
0047ea79  nop 
0047ea7a  nop 
0047ea7b  nop 
0047ea7c  nop 
0047ea7d  nop 
0047ea7e  nop 
0047ea7f  nop 
0047ea80  push ebx
0047ea81  push esi
0047ea82  push edi
0047ea83  mov edi, ecx
0047ea85  mov esi, 0x516a29
0047ea8a  mov ebx, 0xc8
0047ea8f  lea eax, [esi - 1]
0047ea92  mov ecx, edi
0047ea94  push eax
0047ea95  call 0x47d910
0047ea9a  push esi
0047ea9b  mov ecx, edi
0047ea9d  call 0x47d910
0047eaa2  lea ecx, [esi + 1]
0047eaa5  push ecx
0047eaa6  mov ecx, edi
0047eaa8  call 0x47d930
0047eaad  lea edx, [esi + 3]
0047eab0  mov ecx, edi
0047eab2  push edx
0047eab3  call 0x47d930
0047eab8  lea eax, [esi + 5]
0047eabb  mov ecx, edi
0047eabd  push eax
0047eabe  call 0x47d930
0047eac3  lea ecx, [esi + 7]
0047eac6  push ecx
0047eac7  mov ecx, edi
0047eac9  call 0x47d930
0047eace  lea edx, [esi + 9]
0047ead1  mov ecx, edi
0047ead3  push edx
0047ead4  call 0x47d930
0047ead9  lea eax, [esi + 0xb]
0047eadc  mov ecx, edi
0047eade  push eax
0047eadf  call 0x47d910
0047eae4  lea ecx, [esi + 0xc]
0047eae7  push ecx
0047eae8  mov ecx, edi
0047eaea  call 0x47d910
0047eaef  lea edx, [esi + 0xd]
0047eaf2  mov ecx, edi
0047eaf4  push edx
0047eaf5  call 0x47d910
0047eafa  lea eax, [esi + 0xe]
0047eafd  mov ecx, edi
0047eaff  push eax
0047eb00  call 0x47d910
0047eb05  add esi, 0x10
0047eb08  dec ebx
0047eb09  jne 0x47ea8f
0047eb0b  pop edi
0047eb0c  pop esi
0047eb0d  pop ebx
0047eb0e  ret 
0047eb0f  nop 
0047eb10  push ebx
0047eb11  push esi
0047eb12  push edi
0047eb13  mov edi, ecx
0047eb15  mov esi, 0x516a29
0047eb1a  mov ebx, 0xc8
0047eb1f  mov al, byte ptr [esi - 1]
0047eb22  mov ecx, edi
0047eb24  push eax
0047eb25  call 0x47da80
0047eb2a  mov cl, byte ptr [esi]
0047eb2c  push ecx
0047eb2d  mov ecx, edi
0047eb2f  call 0x47da80
0047eb34  mov dx, word ptr [esi + 1]
0047eb38  mov ecx, edi
0047eb3a  push edx
0047eb3b  call 0x47dac0
0047eb40  mov ax, word ptr [esi + 3]
0047eb44  mov ecx, edi
0047eb46  push eax
0047eb47  call 0x47dac0
0047eb4c  mov cx, word ptr [esi + 5]
0047eb50  push ecx
0047eb51  mov ecx, edi
0047eb53  call 0x47dac0
0047eb58  mov dx, word ptr [esi + 7]
0047eb5c  mov ecx, edi
0047eb5e  push edx
0047eb5f  call 0x47dac0
0047eb64  mov ax, word ptr [esi + 9]
0047eb68  mov ecx, edi
0047eb6a  push eax
0047eb6b  call 0x47dac0
0047eb70  mov cl, byte ptr [esi + 0xb]
0047eb73  push ecx
0047eb74  mov ecx, edi
0047eb76  call 0x47da80
0047eb7b  mov dl, byte ptr [esi + 0xc]
0047eb7e  mov ecx, edi
0047eb80  push edx
0047eb81  call 0x47da80
0047eb86  mov al, byte ptr [esi + 0xd]
0047eb89  mov ecx, edi
0047eb8b  push eax
0047eb8c  call 0x47da80
0047eb91  mov cl, byte ptr [esi + 0xe]
0047eb94  push ecx
0047eb95  mov ecx, edi
0047eb97  call 0x47da80
0047eb9c  add esi, 0x10
0047eb9f  dec ebx
0047eba0  jne 0x47eb1f
0047eba6  pop edi
0047eba7  pop esi
0047eba8  pop ebx
0047eba9  ret 
0047ebaa  nop 
0047ebab  nop 
0047ebac  nop 
0047ebad  nop 
0047ebae  nop 
0047ebaf  nop 
0047ebb0  push ebx
0047ebb1  push esi
0047ebb2  push edi
0047ebb3  mov edi, ecx
0047ebb5  mov esi, 0x517852
0047ebba  mov ebx, 0x1e
0047ebbf  lea eax, [esi - 2]
0047ebc2  mov ecx, edi
0047ebc4  push eax
0047ebc5  call 0x47d930
0047ebca  push esi
0047ebcb  mov ecx, edi
0047ebcd  call 0x47d930
0047ebd2  lea ecx, [esi + 2]
0047ebd5  push ecx
0047ebd6  mov ecx, edi
0047ebd8  call 0x47d910
0047ebdd  lea edx, [esi + 3]
0047ebe0  mov ecx, edi
0047ebe2  push edx
0047ebe3  call 0x47d910
0047ebe8  lea eax, [esi + 4]
0047ebeb  mov ecx, edi
0047ebed  push eax
0047ebee  call 0x47d910
0047ebf3  lea ecx, [esi + 5]
0047ebf6  push ecx
0047ebf7  mov ecx, edi
0047ebf9  call 0x47d910
0047ebfe  lea edx, [esi + 6]
0047ec01  mov ecx, edi
0047ec03  push edx
0047ec04  call 0x47d930
0047ec09  lea eax, [esi + 8]
0047ec0c  mov ecx, edi
0047ec0e  push eax
0047ec0f  call 0x47d910
0047ec14  lea ecx, [esi + 9]
0047ec17  push ecx
0047ec18  mov ecx, edi
0047ec1a  call 0x47d910
0047ec1f  add esi, 0xc
0047ec22  dec ebx
0047ec23  jne 0x47ebbf
0047ec25  pop edi
0047ec26  pop esi
0047ec27  pop ebx
0047ec28  ret 
0047ec29  nop 
0047ec2a  nop 
0047ec2b  nop 
0047ec2c  nop 
0047ec2d  nop 
0047ec2e  nop 
0047ec2f  nop 
0047ec30  push ebx
0047ec31  push esi
0047ec32  push edi
0047ec33  mov edi, ecx
0047ec35  mov esi, 0x517852
0047ec3a  mov ebx, 0x1e
0047ec3f  mov ax, word ptr [esi - 2]
0047ec43  mov ecx, edi
0047ec45  push eax
0047ec46  call 0x47dac0
0047ec4b  mov cx, word ptr [esi]
0047ec4e  push ecx
0047ec4f  mov ecx, edi
0047ec51  call 0x47dac0
0047ec56  mov dl, byte ptr [esi + 2]
0047ec59  mov ecx, edi
0047ec5b  push edx
0047ec5c  call 0x47da80
0047ec61  mov al, byte ptr [esi + 3]
0047ec64  mov ecx, edi
0047ec66  push eax
0047ec67  call 0x47da80
0047ec6c  mov cl, byte ptr [esi + 4]
0047ec6f  push ecx
0047ec70  mov ecx, edi
0047ec72  call 0x47da80
0047ec77  mov dl, byte ptr [esi + 5]
0047ec7a  mov ecx, edi
0047ec7c  push edx
0047ec7d  call 0x47da80
0047ec82  mov ax, word ptr [esi + 6]
0047ec86  mov ecx, edi
0047ec88  push eax
0047ec89  call 0x47dac0
0047ec8e  mov cl, byte ptr [esi + 8]
0047ec91  push ecx
0047ec92  mov ecx, edi
0047ec94  call 0x47da80
0047ec99  mov dl, byte ptr [esi + 9]
0047ec9c  mov ecx, edi
0047ec9e  push edx
0047ec9f  call 0x47da80
0047eca4  add esi, 0xc
0047eca7  dec ebx
0047eca8  jne 0x47ec3f
0047ecaa  pop edi
0047ecab  pop esi
0047ecac  pop ebx
0047ecad  ret 
0047ecae  nop 
0047ecaf  nop 
0047ecb0  push ebx
0047ecb1  push esi
0047ecb2  push edi
0047ecb3  mov edi, ecx
0047ecb5  mov esi, 0x51923a
0047ecba  mov ebx, 0x14
0047ecbf  lea eax, [esi - 2]
0047ecc2  mov ecx, edi
0047ecc4  push eax
0047ecc5  call 0x47d930
0047ecca  push esi
0047eccb  mov ecx, edi
0047eccd  call 0x47d930
0047ecd2  add esi, 4
0047ecd5  dec ebx
0047ecd6  jne 0x47ecbf
0047ecd8  pop edi
0047ecd9  pop esi
0047ecda  pop ebx
0047ecdb  ret 
0047ecdc  nop 
0047ecdd  nop 
0047ecde  nop 
0047ecdf  nop 
0047ece0  push ebx
0047ece1  push esi
0047ece2  push edi
0047ece3  mov edi, ecx
0047ece5  mov esi, 0x51923a
0047ecea  mov ebx, 0x14
0047ecef  mov ax, word ptr [esi - 2]
0047ecf3  mov ecx, edi
0047ecf5  push eax
0047ecf6  call 0x47dac0
0047ecfb  mov cx, word ptr [esi]
0047ecfe  push ecx
0047ecff  mov ecx, edi
0047ed01  call 0x47dac0
0047ed06  add esi, 4
0047ed09  dec ebx
0047ed0a  jne 0x47ecef
0047ed0c  pop edi
0047ed0d  pop esi
0047ed0e  pop ebx
0047ed0f  ret 
0047ed10  push ebx
0047ed11  push esi
0047ed12  push edi
0047ed13  mov edi, ecx
0047ed15  mov esi, 0x5176aa
0047ed1a  mov ebx, 0x1e
0047ed1f  lea eax, [esi - 2]
0047ed22  mov ecx, edi
0047ed24  push eax
0047ed25  call 0x47d930
0047ed2a  push esi
0047ed2b  mov ecx, edi
0047ed2d  call 0x47d930
0047ed32  add esi, 4
0047ed35  dec ebx
0047ed36  jne 0x47ed1f
0047ed38  pop edi
0047ed39  pop esi
0047ed3a  pop ebx
0047ed3b  ret 
0047ed3c  nop 
0047ed3d  nop 
0047ed3e  nop 
0047ed3f  nop 
0047ed40  push ebx
0047ed41  push esi
0047ed42  push edi
0047ed43  mov edi, ecx
0047ed45  mov esi, 0x5176aa
0047ed4a  mov ebx, 0x1e
0047ed4f  mov ax, word ptr [esi - 2]
0047ed53  mov ecx, edi
0047ed55  push eax
0047ed56  call 0x47dac0
0047ed5b  mov cx, word ptr [esi]
0047ed5e  push ecx
0047ed5f  mov ecx, edi
0047ed61  call 0x47dac0
0047ed66  add esi, 4
0047ed69  dec ebx
0047ed6a  jne 0x47ed4f
0047ed6c  pop edi
0047ed6d  pop esi
0047ed6e  pop ebx
0047ed6f  ret 
0047ed70  push ecx
0047ed71  push ebx
0047ed72  push ebp
0047ed73  push esi
0047ed74  push edi
0047ed75  mov esi, ecx
0047ed77  mov edi, 0x51e1f5
0047ed7c  mov ebx, 0x521080
0047ed81  mov dword ptr [esp + 0x10], 0xc8
0047ed89  mov ebp, 0xd
0047ed8e  push ebx
0047ed8f  mov ecx, esi
0047ed91  call 0x47d910
0047ed96  inc ebx
0047ed97  dec ebp
0047ed98  jne 0x47ed8e
0047ed9a  lea eax, [edi - 1]
0047ed9d  mov ecx, esi
0047ed9f  push eax
0047eda0  call 0x47d910
0047eda5  push edi
0047eda6  mov ecx, esi
0047eda8  call 0x47d910
0047edad  lea ecx, [edi + 1]
0047edb0  push ecx
0047edb1  mov ecx, esi
0047edb3  call 0x47d930
0047edb8  lea edx, [edi + 3]
0047edbb  mov ecx, esi
0047edbd  push edx
0047edbe  call 0x47d930
0047edc3  mov eax, dword ptr [esp + 0x10]
0047edc7  add edi, 0xa
0047edca  dec eax
0047edcb  mov dword ptr [esp + 0x10], eax
0047edcf  jne 0x47ed89
0047edd1  pop edi
0047edd2  pop esi
0047edd3  pop ebp
0047edd4  pop ebx
0047edd5  pop ecx
0047edd6  ret 
0047edd7  nop 
0047edd8  nop 
0047edd9  nop 
0047edda  nop 
0047eddb  nop 
0047eddc  nop 
0047eddd  nop 
0047edde  nop 
0047eddf  nop 
0047ede0  push ecx
0047ede1  push ebx
0047ede2  push ebp
0047ede3  push esi
0047ede4  push edi
0047ede5  mov esi, ecx
0047ede7  mov edi, 0x51e1f5
0047edec  mov ebx, 0x521080
0047edf1  mov dword ptr [esp + 0x10], 0xc8
0047edf9  mov ebp, 0xd
0047edfe  mov al, byte ptr [ebx]
0047ee00  mov ecx, esi
0047ee02  push eax
0047ee03  call 0x47da80
0047ee08  inc ebx
0047ee09  dec ebp
0047ee0a  jne 0x47edfe
0047ee0c  mov cl, byte ptr [edi - 1]
0047ee0f  push ecx
0047ee10  mov ecx, esi
0047ee12  call 0x47da80
0047ee17  mov dl, byte ptr [edi]
0047ee19  mov ecx, esi
0047ee1b  push edx
0047ee1c  call 0x47da80
0047ee21  mov ax, word ptr [edi + 1]
0047ee25  mov ecx, esi
0047ee27  push eax
0047ee28  call 0x47dac0
0047ee2d  mov cx, word ptr [edi + 3]
0047ee31  push ecx
0047ee32  mov ecx, esi
0047ee34  call 0x47dac0
0047ee39  mov eax, dword ptr [esp + 0x10]
0047ee3d  add edi, 0xa
0047ee40  dec eax
0047ee41  mov dword ptr [esp + 0x10], eax
0047ee45  jne 0x47edf9
0047ee47  pop edi
0047ee48  pop esi
0047ee49  pop ebp
0047ee4a  pop ebx
0047ee4b  pop ecx
0047ee4c  ret 
0047ee4d  nop 
0047ee4e  nop 
0047ee4f  nop 
0047ee50  push ebx
0047ee51  push esi
0047ee52  push edi
0047ee53  mov edi, ecx
0047ee55  mov esi, 0x51772d
0047ee5a  mov ebx, 0x14
0047ee5f  lea eax, [esi - 1]
0047ee62  mov ecx, edi
0047ee64  push eax
0047ee65  call 0x47d910
0047ee6a  push esi
0047ee6b  mov ecx, edi
0047ee6d  call 0x47d910
0047ee72  lea ecx, [esi + 1]
0047ee75  push ecx
0047ee76  mov ecx, edi
0047ee78  call 0x47d930
0047ee7d  lea edx, [esi + 3]
0047ee80  mov ecx, edi
0047ee82  push edx
0047ee83  call 0x47d930
0047ee88  lea eax, [esi + 5]
0047ee8b  mov ecx, edi
0047ee8d  push eax
0047ee8e  call 0x47d930
0047ee93  add esi, 0xc
0047ee96  dec ebx
0047ee97  jne 0x47ee5f
0047ee99  pop edi
0047ee9a  pop esi
0047ee9b  pop ebx
0047ee9c  ret 
0047ee9d  nop 
0047ee9e  nop 
0047ee9f  nop 
0047eea0  push ebx
0047eea1  push esi
0047eea2  push edi
0047eea3  mov edi, ecx
0047eea5  mov esi, 0x51772d
0047eeaa  mov ebx, 0x14
0047eeaf  mov al, byte ptr [esi - 1]
0047eeb2  mov ecx, edi
0047eeb4  push eax
0047eeb5  call 0x47da80
0047eeba  mov cl, byte ptr [esi]
0047eebc  push ecx
0047eebd  mov ecx, edi
0047eebf  call 0x47da80
0047eec4  mov dx, word ptr [esi + 1]
0047eec8  mov ecx, edi
0047eeca  push edx
0047eecb  call 0x47dac0
0047eed0  mov ax, word ptr [esi + 3]
0047eed4  mov ecx, edi
0047eed6  push eax
0047eed7  call 0x47dac0
0047eedc  mov cx, word ptr [esi + 5]
0047eee0  push ecx
0047eee1  mov ecx, edi
0047eee3  call 0x47dac0
0047eee8  add esi, 0xc
0047eeeb  dec ebx
0047eeec  jne 0x47eeaf
0047eeee  pop edi
0047eeef  pop esi
0047eef0  pop ebx
0047eef1  ret 
0047eef2  nop 
0047eef3  nop 
0047eef4  nop 
0047eef5  nop 
0047eef6  nop 
0047eef7  nop 
0047eef8  nop 
0047eef9  nop 
0047eefa  nop 
0047eefb  nop 
0047eefc  nop 
0047eefd  nop 
0047eefe  nop 
0047eeff  nop 
0047ef00  push ecx
0047ef01  push ebx
0047ef02  push ebp
0047ef03  push esi
0047ef04  push edi
0047ef05  mov esi, ecx
0047ef07  mov edi, 0x5185ba
0047ef0c  mov dword ptr [esp + 0x10], 0x14
0047ef14  lea ebx, [edi - 0x32]
0047ef17  mov ebp, 0x19
0047ef1c  push ebx
0047ef1d  mov ecx, esi
0047ef1f  call 0x47d930
0047ef24  add ebx, 2
0047ef27  dec ebp
0047ef28  jne 0x47ef1c
0047ef2a  mov ebx, edi
0047ef2c  mov ebp, 0x19
0047ef31  push ebx
0047ef32  mov ecx, esi
0047ef34  call 0x47d930
0047ef39  add ebx, 2
0047ef3c  dec ebp
0047ef3d  jne 0x47ef31
0047ef3f  lea ebx, [edi + 0x32]
0047ef42  mov ebp, 5
0047ef47  push ebx
0047ef48  mov ecx, esi
0047ef4a  call 0x47d930
0047ef4f  add ebx, 2
0047ef52  dec ebp
0047ef53  jne 0x47ef47
0047ef55  lea eax, [edi + 0x3c]
0047ef58  mov ecx, esi
0047ef5a  push eax
0047ef5b  call 0x47d910
0047ef60  lea ecx, [edi + 0x3d]
0047ef63  push ecx
0047ef64  mov ecx, esi
0047ef66  call 0x47d910
0047ef6b  lea edx, [edi + 0x3e]
0047ef6e  mov ecx, esi
0047ef70  push edx
0047ef71  call 0x47d910
0047ef76  lea eax, [edi + 0x3f]
0047ef79  mov ecx, esi
0047ef7b  push eax
0047ef7c  call 0x47d910
0047ef81  mov eax, dword ptr [esp + 0x10]
0047ef85  add edi, 0x8b
0047ef8b  dec eax
0047ef8c  mov dword ptr [esp + 0x10], eax
0047ef90  jne 0x47ef14
0047ef92  pop edi
0047ef93  pop esi
0047ef94  pop ebp
0047ef95  pop ebx
0047ef96  pop ecx
0047ef97  ret 
0047ef98  nop 
0047ef99  nop 
0047ef9a  nop 
0047ef9b  nop 
0047ef9c  nop 
0047ef9d  nop 
0047ef9e  nop 
0047ef9f  nop 
0047efa0  push ecx
0047efa1  push ebx
0047efa2  push ebp
0047efa3  push esi
0047efa4  push edi
0047efa5  mov esi, ecx
0047efa7  mov edi, 0x5185ba
0047efac  mov dword ptr [esp + 0x10], 0x14
0047efb4  lea ebx, [edi - 0x32]
0047efb7  mov ebp, 0x19
0047efbc  mov ax, word ptr [ebx]
0047efbf  mov ecx, esi
0047efc1  push eax
0047efc2  call 0x47dac0
0047efc7  add ebx, 2
0047efca  dec ebp
0047efcb  jne 0x47efbc
0047efcd  mov ebx, edi
0047efcf  mov ebp, 0x19
0047efd4  mov cx, word ptr [ebx]
0047efd7  push ecx
0047efd8  mov ecx, esi
0047efda  call 0x47dac0
0047efdf  add ebx, 2
0047efe2  dec ebp
0047efe3  jne 0x47efd4
0047efe5  lea ebx, [edi + 0x32]
0047efe8  mov ebp, 5
0047efed  mov dx, word ptr [ebx]
0047eff0  mov ecx, esi
0047eff2  push edx
0047eff3  call 0x47dac0
0047eff8  add ebx, 2
0047effb  dec ebp
0047effc  jne 0x47efed
0047effe  mov al, byte ptr [edi + 0x3c]
0047f001  mov ecx, esi
0047f003  push eax
0047f004  call 0x47da80
0047f009  mov cl, byte ptr [edi + 0x3d]
0047f00c  push ecx
0047f00d  mov ecx, esi
0047f00f  call 0x47da80
0047f014  mov dl, byte ptr [edi + 0x3e]
0047f017  mov ecx, esi
0047f019  push edx
0047f01a  call 0x47da80
0047f01f  mov al, byte ptr [edi + 0x3f]
0047f022  mov ecx, esi
0047f024  push eax
0047f025  call 0x47da80
0047f02a  mov eax, dword ptr [esp + 0x10]
0047f02e  add edi, 0x8b
0047f034  dec eax
0047f035  mov dword ptr [esp + 0x10], eax
0047f039  jne 0x47efb4
0047f03f  pop edi
0047f040  pop esi
0047f041  pop ebp
0047f042  pop ebx
0047f043  pop ecx
0047f044  ret 
0047f045  nop 
0047f046  nop 
0047f047  nop 
0047f048  nop 
0047f049  nop 
0047f04a  nop 
0047f04b  nop 
0047f04c  nop 
0047f04d  nop 
0047f04e  nop 
0047f04f  nop 
0047f050  push ebx
0047f051  push esi
0047f052  push edi
0047f053  mov ebx, ecx
0047f055  mov esi, 0x51dc60
0047f05a  mov edi, 0x498
0047f05f  push esi
0047f060  mov ecx, ebx
0047f062  call 0x47d910
0047f067  inc esi
0047f068  dec edi
0047f069  jne 0x47f05f
0047f06b  pop edi
0047f06c  pop esi
0047f06d  pop ebx
0047f06e  ret 
0047f06f  nop 
0047f070  push ebx
0047f071  push esi
0047f072  push edi
0047f073  mov ebx, ecx
0047f075  mov esi, 0x51dc60
0047f07a  mov edi, 0x498
0047f07f  mov al, byte ptr [esi]
0047f081  mov ecx, ebx
0047f083  push eax
0047f084  call 0x47da80
0047f089  inc esi
0047f08a  dec edi
0047f08b  jne 0x47f07f
0047f08d  pop edi
0047f08e  pop esi
0047f08f  pop ebx
0047f090  ret 
0047f091  nop 
0047f092  nop 
0047f093  nop 
0047f094  nop 
0047f095  nop 
0047f096  nop 
0047f097  nop 
0047f098  nop 
0047f099  nop 
0047f09a  nop 
0047f09b  nop 
0047f09c  nop 
0047f09d  nop 
0047f09e  nop 
0047f09f  nop 
0047f0a0  push ebx
0047f0a1  push esi
0047f0a2  push edi
0047f0a3  mov esi, ecx
0047f0a5  push 0x5203c0
0047f0aa  call 0x47d910
0047f0af  push 0x5203c1
0047f0b4  mov ecx, esi
0047f0b6  call 0x47d910
0047f0bb  mov edi, 0x5203c2
0047f0c0  mov ebx, 8
0047f0c5  push edi
0047f0c6  mov ecx, esi
0047f0c8  call 0x47d910
0047f0cd  inc edi
0047f0ce  dec ebx
0047f0cf  jne 0x47f0c5
0047f0d1  mov edi, 0x5203ca
0047f0d6  mov ebx, 8
0047f0db  push edi
0047f0dc  mov ecx, esi
0047f0de  call 0x47d910
0047f0e3  inc edi
0047f0e4  dec ebx
0047f0e5  jne 0x47f0db
0047f0e7  push 0x5203d2
0047f0ec  mov ecx, esi
0047f0ee  call 0x47d910
0047f0f3  mov edi, 0x5203d3
0047f0f8  mov ebx, 6
0047f0fd  push edi
0047f0fe  mov ecx, esi
0047f100  call 0x47d910
0047f105  inc edi
0047f106  dec ebx
0047f107  jne 0x47f0fd
0047f109  pop edi
0047f10a  pop esi
0047f10b  pop ebx
0047f10c  ret 
0047f10d  nop 
0047f10e  nop 
0047f10f  nop 
0047f110  push ecx
0047f111  mov al, byte ptr [0x5203c0]
0047f116  push ebx
0047f117  push esi
0047f118  mov esi, ecx
0047f11a  mov byte ptr [esp + 8], al
0047f11e  push edi
0047f11f  mov ecx, dword ptr [esp + 0xc]
0047f123  push ecx
0047f124  mov ecx, esi
0047f126  call 0x47da80
0047f12b  mov dl, byte ptr [0x5203c1]
0047f131  mov ecx, esi
0047f133  mov byte ptr [esp + 0xc], dl
0047f137  mov eax, dword ptr [esp + 0xc]
0047f13b  push eax
0047f13c  call 0x47da80
0047f141  mov edi, 0x5203c2
0047f146  mov ebx, 8
0047f14b  mov cl, byte ptr [edi]
0047f14d  push ecx
0047f14e  mov ecx, esi
0047f150  call 0x47da80
0047f155  inc edi
0047f156  dec ebx
0047f157  jne 0x47f14b
0047f159  mov edi, 0x5203ca
0047f15e  mov ebx, 8
0047f163  mov dl, byte ptr [edi]
0047f165  mov ecx, esi
0047f167  push edx
0047f168  call 0x47da80
0047f16d  inc edi
0047f16e  dec ebx
0047f16f  jne 0x47f163
0047f171  mov al, byte ptr [0x5203d2]
0047f176  mov byte ptr [esp + 0xc], al
0047f17a  mov ecx, dword ptr [esp + 0xc]
0047f17e  push ecx
0047f17f  mov ecx, esi
0047f181  call 0x47da80
0047f186  mov edi, 0x5203d3
0047f18b  mov ebx, 6
0047f190  mov dl, byte ptr [edi]
0047f192  mov ecx, esi
0047f194  push edx
0047f195  call 0x47da80
0047f19a  inc edi
0047f19b  dec ebx
0047f19c  jne 0x47f190
0047f19e  pop edi
0047f19f  pop esi
0047f1a0  pop ebx
0047f1a1  pop ecx
0047f1a2  ret 
0047f1a3  nop 
0047f1a4  nop 
0047f1a5  nop 
0047f1a6  nop 
0047f1a7  nop 
0047f1a8  nop 
0047f1a9  nop 
0047f1aa  nop 
0047f1ab  nop 
0047f1ac  nop 
0047f1ad  nop 
0047f1ae  nop 
0047f1af  nop 
0047f1b0  push ebx
0047f1b1  push esi
0047f1b2  push edi
0047f1b3  mov ebx, ecx
0047f1b5  mov esi, 0x519680
0047f1ba  mov edi, 0x14
0047f1bf  push esi
0047f1c0  mov ecx, ebx
0047f1c2  call 0x47d930
0047f1c7  add esi, 2
0047f1ca  dec edi
0047f1cb  jne 0x47f1bf
0047f1cd  pop edi
0047f1ce  pop esi
0047f1cf  pop ebx
0047f1d0  ret 
0047f1d1  nop 
0047f1d2  nop 
0047f1d3  nop 
0047f1d4  nop 
0047f1d5  nop 
0047f1d6  nop 
0047f1d7  nop 
0047f1d8  nop 
0047f1d9  nop 
0047f1da  nop 
0047f1db  nop 
0047f1dc  nop 
0047f1dd  nop 
0047f1de  nop 
0047f1df  nop 
0047f1e0  push ebx
0047f1e1  push esi
0047f1e2  push edi
0047f1e3  mov ebx, ecx
0047f1e5  mov esi, 0x519680
0047f1ea  mov edi, 0x14
0047f1ef  mov ax, word ptr [esi]
0047f1f2  mov ecx, ebx
0047f1f4  push eax
0047f1f5  call 0x47dac0
0047f1fa  add esi, 2
0047f1fd  dec edi
0047f1fe  jne 0x47f1ef
0047f200  pop edi
0047f201  pop esi
0047f202  pop ebx
0047f203  ret 
0047f204  nop 
0047f205  nop 
0047f206  nop 
0047f207  nop 
0047f208  nop 
0047f209  nop 
0047f20a  nop 
0047f20b  nop 
0047f20c  nop 
0047f20d  nop 
0047f20e  nop 
0047f20f  nop 
0047f210  push ecx
0047f211  push ebx
0047f212  push ebp
0047f213  push esi
0047f214  push edi
0047f215  mov esi, ecx
0047f217  push 0x517c70
0047f21c  call 0x47d910
0047f221  push 0x517c71
0047f226  mov ecx, esi
0047f228  call 0x47d910
0047f22d  push 0x517c72
0047f232  mov ecx, esi
0047f234  call 0x47d910
0047f239  mov edi, 0x517c74
0047f23e  mov dword ptr [esp + 0x10], 0xa
0047f246  lea eax, [edi - 1]
0047f249  mov ecx, esi
0047f24b  push eax
0047f24c  call 0x47d910
0047f251  push edi
0047f252  mov ecx, esi
0047f254  call 0x47d910
0047f259  lea ecx, [edi + 1]
0047f25c  push ecx
0047f25d  mov ecx, esi
0047f25f  call 0x47d910
0047f264  lea edx, [edi + 2]
0047f267  mov ecx, esi
0047f269  push edx
0047f26a  call 0x47d910
0047f26f  lea ebx, [edi + 3]
0047f272  mov ebp, 9
0047f277  push ebx
0047f278  mov ecx, esi
0047f27a  call 0x47d910
0047f27f  inc ebx
0047f280  dec ebp
0047f281  jne 0x47f277
0047f283  mov eax, dword ptr [esp + 0x10]
0047f287  add edi, 0xd
0047f28a  dec eax
0047f28b  mov dword ptr [esp + 0x10], eax
0047f28f  jne 0x47f246
0047f291  pop edi
0047f292  pop esi
0047f293  pop ebp
0047f294  pop ebx
0047f295  pop ecx
0047f296  ret 
0047f297  nop 
0047f298  nop 
0047f299  nop 
0047f29a  nop 
0047f29b  nop 
0047f29c  nop 
0047f29d  nop 
0047f29e  nop 
0047f29f  nop 
0047f2a0  push ecx
0047f2a1  mov al, byte ptr [0x517c70]
0047f2a6  push ebx
0047f2a7  push ebp
0047f2a8  push esi
0047f2a9  mov esi, ecx
0047f2ab  mov byte ptr [esp + 0xc], al
0047f2af  mov ecx, dword ptr [esp + 0xc]
0047f2b3  push edi
0047f2b4  push ecx
0047f2b5  mov ecx, esi
0047f2b7  call 0x47da80
0047f2bc  mov dl, byte ptr [0x517c71]
0047f2c2  mov ecx, esi
0047f2c4  mov byte ptr [esp + 0x10], dl
0047f2c8  mov eax, dword ptr [esp + 0x10]
0047f2cc  push eax
0047f2cd  call 0x47da80
0047f2d2  mov cl, byte ptr [0x517c72]
0047f2d8  mov byte ptr [esp + 0x10], cl
0047f2dc  mov ecx, esi
0047f2de  mov edx, dword ptr [esp + 0x10]
0047f2e2  push edx
0047f2e3  call 0x47da80
0047f2e8  mov edi, 0x517c74
0047f2ed  mov dword ptr [esp + 0x10], 0xa
0047f2f5  mov al, byte ptr [edi - 1]
0047f2f8  mov ecx, esi
0047f2fa  push eax
0047f2fb  call 0x47da80
0047f300  mov cl, byte ptr [edi]
0047f302  push ecx
0047f303  mov ecx, esi
0047f305  call 0x47da80
0047f30a  mov dl, byte ptr [edi + 1]
0047f30d  mov ecx, esi
0047f30f  push edx
0047f310  call 0x47da80
0047f315  mov al, byte ptr [edi + 2]
0047f318  mov ecx, esi
0047f31a  push eax
0047f31b  call 0x47da80
0047f320  lea ebx, [edi + 3]
0047f323  mov ebp, 9
0047f328  mov cl, byte ptr [ebx]
0047f32a  push ecx
0047f32b  mov ecx, esi
0047f32d  call 0x47da80
0047f332  inc ebx
0047f333  dec ebp
0047f334  jne 0x47f328
0047f336  mov eax, dword ptr [esp + 0x10]
0047f33a  add edi, 0xd
0047f33d  dec eax
0047f33e  mov dword ptr [esp + 0x10], eax
0047f342  jne 0x47f2f5
0047f344  pop edi
0047f345  pop esi
0047f346  pop ebp
0047f347  pop ebx
0047f348  pop ecx
0047f349  ret 
0047f34a  nop 
0047f34b  nop 
0047f34c  nop 
0047f34d  nop 
0047f34e  nop 
0047f34f  nop 
0047f350  sub esp, 0x18
0047f353  push ebx
0047f354  mov bx, word ptr [0x520604]
0047f35b  xor eax, eax
0047f35d  push ebp
0047f35e  push esi
0047f35f  mov ax, bx
0047f362  push edi
0047f363  mov edi, eax
0047f365  mov ebp, eax
0047f367  push 0x10
0047f369  shr eax, 1
0047f36b  and eax, 1
0047f36e  mov esi, ecx
0047f370  mov dword ptr [esp + 0x18], eax
0047f374  lea eax, [esp + 0x1c]
0047f378  shr edi, 2
0047f37b  shr ebx, 6
0047f37e  push eax
0047f37f  and edi, 1
0047f382  and ebp, 1
0047f385  and ebx, 0xf
0047f388  call 0x4411b0
0047f38d  push 0x10
0047f38f  lea ecx, [esp + 0x1c]
0047f393  push 0x4fc240
0047f398  push ecx
0047f399  call 0x492850
0047f39e  add esp, 0xc
0047f3a1  test ax, ax
0047f3a4  je 0x47f3b7
0047f3a6  call 0x47f5b0
0047f3ab  xor eax, eax
0047f3ad  pop edi
0047f3ae  pop esi
0047f3af  pop ebp
0047f3b0  pop ebx
0047f3b1  add esp, 0x18
0047f3b4  ret 4
0047f3b7  lea eax, [esi + 0x90]
0047f3bd  push 2
0047f3bf  push eax
0047f3c0  mov ecx, esi
0047f3c2  call 0x4411b0
0047f3c7  lea eax, [esi + 0x94]
0047f3cd  push 2
0047f3cf  push eax
0047f3d0  mov ecx, esi
0047f3d2  call 0x4411b0
0047f3d7  mov ax, word ptr [esi + 0x94]
0047f3de  xor edx, edx
0047f3e0  mov dl, ah
0047f3e2  and eax, 0xff
0047f3e7  xor edx, eax
0047f3e9  push 0x2bc
0047f3ee  push 0x519288
0047f3f3  mov ecx, esi
0047f3f5  mov word ptr [esi + 0x94], dx
0047f3fc  call 0x4411b0
0047f401  push 0
0047f403  mov ecx, 0x524978
0047f408  call 0x4eb5c0
0047f40d  push 0x2bc
0047f412  push eax
0047f413  mov ecx, esi
0047f415  mov dword ptr [esp + 0x18], eax
0047f419  call 0x4411b0
0047f41e  mov eax, dword ptr [esp + 0x10]
0047f422  cmp byte ptr [eax], 0x39
0047f425  jne 0x47f438
0047f427  inc eax
0047f428  push 0x31
0047f42a  push eax
0047f42b  push 0x519640
0047f430  call 0x492800
0047f435  add esp, 0xc
0047f438  mov ecx, esi
0047f43a  call 0x47d960
0047f43f  mov ecx, 0x526c50
0047f444  call 0x4edfa0
0047f449  mov ecx, esi
0047f44b  mov word ptr [esi + 0x92], 0
0047f454  call 0x47dae0
0047f459  mov ecx, esi
0047f45b  call 0x47dce0
0047f460  mov ecx, esi
0047f462  call 0x47e130
0047f467  mov ecx, esi
0047f469  call 0x47e3a0
0047f46e  mov ecx, esi
0047f470  call 0x47e440
0047f475  mov ecx, esi
0047f477  call 0x47e5a0
0047f47c  mov ecx, esi
0047f47e  call 0x47e770
0047f483  mov ecx, esi
0047f485  call 0x47ea80
0047f48a  mov ecx, esi
0047f48c  call 0x47ebb0
0047f491  mov ecx, esi
0047f493  call 0x47ecb0
0047f498  mov ecx, esi
0047f49a  call 0x47ed10
0047f49f  mov ecx, esi
0047f4a1  call 0x47ed70
0047f4a6  mov ecx, esi
0047f4a8  call 0x47ee50
0047f4ad  mov ecx, esi
0047f4af  call 0x47ef00
0047f4b4  mov ecx, esi
0047f4b6  call 0x47f050
0047f4bb  mov ecx, esi
0047f4bd  call 0x47f0a0
0047f4c2  mov ecx, esi
0047f4c4  call 0x47f1b0
0047f4c9  mov ecx, esi
0047f4cb  call 0x47f210
0047f4d0  mov ecx, 0x526c50
0047f4d5  call 0x4edf70
0047f4da  mov ax, word ptr [esi + 0x92]
0047f4e1  cmp ax, word ptr [esi + 0x90]
0047f4e8  je 0x47f4fb
0047f4ea  call 0x47f5b0
0047f4ef  xor eax, eax
0047f4f1  pop edi
0047f4f2  pop esi
0047f4f3  pop ebp
0047f4f4  pop ebx
0047f4f5  add esp, 0x18
0047f4f8  ret 4
0047f4fb  mov ecx, dword ptr [esi + 0x96]
0047f501  mov edx, dword ptr [esi]
0047f503  add ecx, 0x9ffa
0047f509  push 0
0047f50b  push ecx
0047f50c  push edx
0047f50d  call dword ptr [0x4fb0a8]
0047f513  push 2
0047f515  push 0x5261ac
0047f51a  mov ecx, esi
0047f51c  call 0x4411b0
0047f521  push 2
0047f523  push 0x5261b0
0047f528  mov ecx, esi
0047f52a  call 0x4411b0
0047f52f  push 2
0047f531  push 0x5261a4
0047f536  mov ecx, esi
0047f538  call 0x4411b0
0047f53d  mov eax, dword ptr [esp + 0x2c]
0047f541  test eax, eax
0047f543  jne 0x47f56d
0047f545  mov bx, word ptr [0x520604]
0047f54c  xor eax, eax
0047f54e  mov ax, bx
0047f551  mov edi, eax
0047f553  mov ebp, eax
0047f555  shr eax, 1
0047f557  shr edi, 2
0047f55a  and eax, 1
0047f55d  and edi, 1
0047f560  shr ebx, 6
0047f563  and ebp, 1
0047f566  mov esi, eax
0047f568  and ebx, 0xf
0047f56b  jmp 0x47f571
0047f56d  mov esi, dword ptr [esp + 0x14]
0047f571  push edi
0047f572  mov ecx, 0x5205f0
0047f577  call 0x49a210
0047f57c  push ebp
0047f57d  mov ecx, 0x5205f0
0047f582  call 0x49a1c0
0047f587  push esi
0047f588  mov ecx, 0x5205f0
0047f58d  call 0x49a1f0
0047f592  push ebx
0047f593  mov ecx, 0x5205f0
0047f598  call 0x49a250
0047f59d  pop edi
0047f59e  pop esi
0047f59f  pop ebp
0047f5a0  mov eax, 1
0047f5a5  pop ebx
0047f5a6  add esp, 0x18
0047f5a9  ret 4
0047f5ac  nop 
0047f5ad  nop 
0047f5ae  nop 
0047f5af  nop 
0047f5b0  push 0x509608
0047f5b5  call 0x47ae80
0047f5ba  add esp, 4
0047f5bd  ret 
0047f5be  nop 
0047f5bf  nop 
0047f5c0  push ebx
0047f5c1  push ebp
0047f5c2  push esi
0047f5c3  mov esi, ecx
0047f5c5  push edi
0047f5c6  mov ecx, 0x526c50
0047f5cb  call 0x4edfa0
0047f5d0  lea ebx, [esi + 0x92]
0047f5d6  push 0x100
0047f5db  lea edi, [esi + 0x94]
0047f5e1  mov word ptr [ebx], 0
0047f5e6  call 0x4ebd60
0047f5eb  add esp, 4
0047f5ee  mov bp, ax
0047f5f1  push 0x100
0047f5f6  call 0x4ebd60
0047f5fb  add esp, 4
0047f5fe  mov ecx, esi
0047f600  shl eax, 8
0047f603  add ebp, eax
0047f605  push 0x10
0047f607  push 0x4fc240
0047f60c  mov word ptr [edi], bp
0047f60f  call 0x4411d0
0047f614  push 2
0047f616  push ebx
0047f617  mov ecx, esi
0047f619  call 0x4411d0
0047f61e  push 2
0047f620  push edi
0047f621  mov ecx, esi
0047f623  call 0x4411d0
0047f628  mov ax, word ptr [edi]
0047f62b  xor ecx, ecx
0047f62d  mov cl, ah
0047f62f  and eax, 0xff
0047f634  xor ecx, eax
0047f636  push 0x2bc
0047f63b  mov word ptr [edi], cx
0047f63e  push 0x519288
0047f643  mov ecx, esi
0047f645  call 0x4411d0
0047f64a  push 0
0047f64c  mov ecx, 0x524978
0047f651  call 0x4eb5c0
0047f656  mov edi, eax
0047f658  push 0x2bc
0047f65d  push 0
0047f65f  push edi
0047f660  call 0x492820
0047f665  add esp, 0xc
0047f668  lea edx, [edi + 1]
0047f66b  mov byte ptr [edi], 0x39
0047f66e  push 0x31
0047f670  push 0x519640
0047f675  push edx
0047f676  call 0x492800
0047f67b  add esp, 0xc
0047f67e  mov ecx, esi
0047f680  push 0x2bc
0047f685  push edi
0047f686  call 0x4411d0
0047f68b  push 0
0047f68d  mov ecx, 0x524978
0047f692  mov word ptr [esi + 0x8e], 0
0047f69b  call 0x4eb5c0
0047f6a0  mov ecx, esi
0047f6a2  mov dword ptr [esi + 0x9a], eax
0047f6a8  call 0x47dba0
0047f6ad  mov ecx, esi
0047f6af  call 0x47df00
0047f6b4  mov ecx, esi
0047f6b6  call 0x47e260
0047f6bb  mov ecx, esi
0047f6bd  call 0x47e3f0
0047f6c2  mov ecx, esi
0047f6c4  call 0x47e4e0
0047f6c9  mov ecx, esi
0047f6cb  call 0x47e680
0047f6d0  mov ecx, esi
0047f6d2  call 0x47e8a0
0047f6d7  mov ecx, esi
0047f6d9  call 0x47eb10
0047f6de  mov ecx, esi
0047f6e0  call 0x47ec30
0047f6e5  mov ecx, esi
0047f6e7  call 0x47ece0
0047f6ec  mov ecx, esi
0047f6ee  call 0x47ed40
0047f6f3  mov ecx, esi
0047f6f5  call 0x47ede0
0047f6fa  mov ecx, esi
0047f6fc  call 0x47eea0
0047f701  mov ecx, esi
0047f703  call 0x47efa0
0047f708  mov ecx, esi
0047f70a  call 0x47f070
0047f70f  mov ecx, esi
0047f711  call 0x47f110
0047f716  mov ecx, esi
0047f718  call 0x47f1e0
0047f71d  mov ecx, esi
0047f71f  call 0x47f2a0
0047f724  cmp word ptr [esi + 0x8e], 0
0047f72c  je 0x47f735
0047f72e  mov ecx, esi
0047f730  call 0x47d9b0
0047f735  mov eax, dword ptr [esi + 0x96]
0047f73b  mov ecx, dword ptr [esi]
0047f73d  mov edi, dword ptr [0x4fb0a8]
0047f743  add eax, 0x10
0047f746  push 0
0047f748  push eax
0047f749  push ecx
0047f74a  call edi
0047f74c  push 2
0047f74e  push ebx
0047f74f  mov ecx, esi
0047f751  call 0x4411d0
0047f756  mov edx, dword ptr [esi + 0x96]
0047f75c  mov eax, dword ptr [esi]
0047f75e  add edx, 0x9ffa
0047f764  push 0
0047f766  push edx
0047f767  push eax
0047f768  call edi
0047f76a  push 2
0047f76c  push 0x5261ac
0047f771  mov ecx, esi
0047f773  call 0x4411d0
0047f778  push 2
0047f77a  push 0x5261b0
0047f77f  mov ecx, esi
0047f781  call 0x4411d0
0047f786  push 2
0047f788  push 0x5261a4
0047f78d  mov ecx, esi
0047f78f  call 0x4411d0
0047f794  mov ecx, 0x526c50
0047f799  call 0x4edf70
0047f79e  pop edi
0047f79f  pop esi
0047f7a0  pop ebp
0047f7a1  pop ebx
0047f7a2  ret 
0047f7a3  nop 
0047f7a4  nop 
0047f7a5  nop 
0047f7a6  nop 
0047f7a7  nop 
0047f7a8  nop 
0047f7a9  nop 
0047f7aa  nop 
0047f7ab  nop 
0047f7ac  nop 
0047f7ad  nop 
0047f7ae  nop 
0047f7af  nop 
0047f7b0  mov eax, dword ptr [esp + 8]
0047f7b4  push ebx
0047f7b5  and eax, 0xffff
0047f7ba  push ebp
0047f7bb  mov ecx, eax
0047f7bd  push esi
0047f7be  shl ecx, 3
0047f7c1  sub ecx, eax
0047f7c3  push edi
0047f7c4  lea edx, [eax + ecx*4]
0047f7c7  mov ecx, 0x524a20
0047f7cc  lea eax, [eax + edx*2]
0047f7cf  push eax
0047f7d0  call 0x4eb5c0
0047f7d5  mov edi, dword ptr [esp + 0x14]
0047f7d9  mov dword ptr [0x522c98], eax
0047f7de  and edi, 0xffff
0047f7e4  mov ebp, 7
0047f7e9  lea esi, [edi*8]
0047f7f0  sub esi, edi
0047f7f2  lea ebx, [esi + 0x521aa8]
0047f7f8  push ebx
0047f7f9  call 0x47fa40
0047f7fe  add esp, 4
0047f801  inc ebx
0047f802  dec ebp
0047f803  jne 0x47f7f8
0047f805  lea esi, [esi + 0x520660]
0047f80b  mov ebx, 7
0047f810  push esi
0047f811  call 0x47fa40
0047f816  add esp, 4
0047f819  inc esi
0047f81a  dec ebx
0047f81b  jne 0x47f810
0047f81d  lea ecx, [esp + 0x18]
0047f821  push ecx
0047f822  call 0x47fa60
0047f827  lea esi, [edi + edi*2]
0047f82a  add esp, 4
0047f82d  shl esi, 4
0047f830  sub esi, edi
0047f832  lea edx, [esi + 0x51986a]
0047f838  push edx
0047f839  call 0x47fa60
0047f83e  add esp, 4
0047f841  lea eax, [esp + 0x18]
0047f845  push eax
0047f846  call 0x47fa60
0047f84b  add esp, 4
0047f84e  lea ecx, [esi + 0x519870]
0047f854  mov dword ptr [esi + 0x51986c], 0
0047f85e  push ecx
0047f85f  call 0x47fa60
0047f864  add esp, 4
0047f867  lea edx, [esi + 0x519872]
0047f86d  push edx
0047f86e  call 0x47fa40
0047f873  add esp, 4
0047f876  lea eax, [esi + 0x519873]
0047f87c  push eax
0047f87d  call 0x47fa40
0047f882  add esp, 4
0047f885  lea ecx, [esi + 0x519874]
0047f88b  push ecx
0047f88c  call 0x47fa40
0047f891  add esp, 4
0047f894  lea edx, [esi + 0x519875]
0047f89a  push edx
0047f89b  call 0x47fa40
0047f8a0  add esp, 4
0047f8a3  lea eax, [esi + 0x519876]
0047f8a9  push eax
0047f8aa  call 0x47fa40
0047f8af  add esp, 4
0047f8b2  lea ecx, [esi + 0x519877]
0047f8b8  push ecx
0047f8b9  call 0x47fa40
0047f8be  add esp, 4
0047f8c1  lea edx, [esi + 0x519878]
0047f8c7  push edx
0047f8c8  call 0x47fa40
0047f8cd  add esp, 4
0047f8d0  lea eax, [esi + 0x519879]
0047f8d6  push eax
0047f8d7  call 0x47fa40
0047f8dc  add esp, 4
0047f8df  lea ecx, [esi + 0x51987a]
0047f8e5  push ecx
0047f8e6  call 0x47fa40
0047f8eb  add esp, 4
0047f8ee  lea edx, [esi + 0x51987b]
0047f8f4  push edx
0047f8f5  call 0x47fa40
0047f8fa  add esp, 4
0047f8fd  lea eax, [esi + 0x51987c]
0047f903  push eax
0047f904  call 0x47fa40
0047f909  add esp, 4
0047f90c  lea ecx, [esi + 0x51987d]
0047f912  push ecx
0047f913  call 0x47fa40
0047f918  add esp, 4
0047f91b  lea edx, [esi + 0x51987e]
0047f921  push edx
0047f922  call 0x47fa40
0047f927  add esp, 4
0047f92a  lea eax, [esi + 0x51987f]
0047f930  push eax
0047f931  call 0x47fa40
0047f936  add esp, 4
0047f939  lea ecx, [esi + 0x519880]
0047f93f  push ecx
0047f940  call 0x47fa60
0047f945  add esp, 4
0047f948  lea edx, [esi + 0x519882]
0047f94e  push edx
0047f94f  call 0x47fa40
0047f954  add esp, 4
0047f957  lea eax, [esi + 0x519883]
0047f95d  push eax
0047f95e  call 0x47fa60
0047f963  add esp, 4
0047f966  lea ecx, [esi + 0x519885]
0047f96c  push ecx
0047f96d  call 0x47fa60
0047f972  add esp, 4
0047f975  lea edx, [esi + 0x519887]
0047f97b  push edx
0047f97c  call 0x47fa40
0047f981  add esp, 4
0047f984  lea eax, [esi + 0x519888]
0047f98a  push eax
0047f98b  call 0x47fa40
0047f990  add esp, 4
0047f993  lea ecx, [esi + 0x519889]
0047f999  push ecx
0047f99a  call 0x47fa40
0047f99f  add esp, 4
0047f9a2  lea edx, [esi + 0x51988a]
0047f9a8  push edx
0047f9a9  call 0x47fa40
0047f9ae  add esp, 4
0047f9b1  lea eax, [esi + 0x51988b]
0047f9b7  push eax
0047f9b8  call 0x47fa40
0047f9bd  add esp, 4
0047f9c0  lea ecx, [esi + 0x51988c]
0047f9c6  push ecx
0047f9c7  call 0x47fa40
0047f9cc  add esp, 4
0047f9cf  lea edx, [esi + 0x51988d]
0047f9d5  push edx
0047f9d6  call 0x47fa40
0047f9db  add esp, 4
0047f9de  lea eax, [esi + 0x51988e]
0047f9e4  push eax
0047f9e5  call 0x47fa60
0047f9ea  add esp, 4
0047f9ed  lea ecx, [esi + 0x519890]
0047f9f3  push ecx
0047f9f4  call 0x47fa40
0047f9f9  add esp, 4
0047f9fc  lea edx, [esi + 0x519891]
0047fa02  push edx
0047fa03  call 0x47fa40
0047fa08  add esp, 4
0047fa0b  lea eax, [esi + 0x519892]
0047fa11  push eax
0047fa12  call 0x47fa60
0047fa17  add esp, 4
0047fa1a  lea ecx, [esi + 0x519894]
0047fa20  push ecx
0047fa21  call 0x47fa60
0047fa26  add esp, 4
0047fa29  lea edx, [esi + 0x519896]
0047fa2f  push edx
0047fa30  call 0x47fa40
0047fa35  add esp, 4
0047fa38  pop edi
0047fa39  pop esi
0047fa3a  pop ebp
0047fa3b  pop ebx
0047fa3c  ret 8
0047fa3f  nop 
0047fa40  mov eax, dword ptr [0x522c98]
0047fa45  mov edx, dword ptr [esp + 4]
0047fa49  mov cl, byte ptr [eax]
0047fa4b  mov byte ptr [edx], cl
0047fa4d  mov eax, dword ptr [0x522c98]
0047fa52  inc eax
0047fa53  mov dword ptr [0x522c98], eax
0047fa58  ret 
0047fa59  nop 
0047fa5a  nop 
0047fa5b  nop 
0047fa5c  nop 
0047fa5d  nop 
0047fa5e  nop 
0047fa5f  nop 
0047fa60  mov eax, dword ptr [0x522c98]
0047fa65  movzx cx, byte ptr [eax]
0047fa69  inc eax
0047fa6a  mov dword ptr [0x522c98], eax
0047fa6f  movzx dx, byte ptr [eax]
0047fa73  inc eax
0047fa74  mov dword ptr [0x522c98], eax
0047fa79  xor eax, eax
0047fa7b  mov ah, dl
0047fa7d  or eax, ecx
0047fa7f  mov ecx, dword ptr [esp + 4]
0047fa83  mov word ptr [ecx], ax
0047fa86  ret 
0047fa87  nop 
0047fa88  nop 
0047fa89  nop 
0047fa8a  nop 
0047fa8b  nop 
0047fa8c  nop 
0047fa8d  nop 
0047fa8e  nop 
0047fa8f  nop 
0047fa90  sub esp, 0x8c
0047fa96  mov eax, dword ptr [0x520604]
0047fa9b  mov dword ptr [esp], 0
0047faa3  test ah, 4
0047faa6  mov eax, 0x5095d0
0047faab  jne 0x47fab2
0047faad  mov eax, 0x5095c0
0047fab2  push 4
0047fab4  push eax
0047fab5  lea ecx, [esp + 8]
0047fab9  call 0x4802e0
0047fabe  test eax, eax
0047fac0  je 0x47fafe
0047fac2  push 0xa154
0047fac7  push 0
0047fac9  mov ecx, 0x524a20
0047face  call 0x4eb5c0
0047fad3  push eax
0047fad4  lea ecx, [esp + 8]
0047fad8  call 0x4411b0
0047fadd  mov eax, dword ptr [esp]
0047fae1  push eax
0047fae2  call dword ptr [0x4fb09c]
0047fae8  mov ecx, 0x524a20
0047faed  call 0x4eb730
0047faf2  mov eax, 1
0047faf7  add esp, 0x8c
0047fafd  ret 
0047fafe  xor eax, eax
0047fb00  add esp, 0x8c
0047fb06  ret 
0047fb07  nop 
0047fb08  nop 
0047fb09  nop 
0047fb0a  nop 
0047fb0b  nop 
0047fb0c  nop 
0047fb0d  nop 
0047fb0e  nop 
0047fb0f  nop 
0047fb10  sub esp, 0xa0
0047fb16  mov eax, dword ptr [esp + 0xa4]
0047fb1d  push esi
0047fb1e  cmp ax, 2
0047fb22  mov dword ptr [esp + 4], 0
0047fb2a  jae 0x47fb71
0047fb2c  push 4
0047fb2e  push eax
0047fb2f  lea ecx, [esp + 0xc]
0047fb33  call 0x47d720
0047fb38  test eax, eax
0047fb3a  je 0x47fb71
0047fb3c  push 1
0047fb3e  lea ecx, [esp + 8]
0047fb42  mov word ptr [esp + 0x94], 0
0047fb4c  call 0x47f350
0047fb51  lea ecx, [esp + 4]
0047fb55  mov esi, eax
0047fb57  call 0x47d850
0047fb5c  test esi, esi
0047fb5e  je 0x47fb67
0047fb60  call 0x47fa90
0047fb65  mov esi, eax
0047fb67  mov eax, esi
0047fb69  pop esi
0047fb6a  add esp, 0xa0
0047fb70  ret 
0047fb71  xor eax, eax
0047fb73  pop esi
0047fb74  add esp, 0xa0
0047fb7a  ret 
0047fb7b  nop 
0047fb7c  nop 
0047fb7d  nop 
0047fb7e  nop 
0047fb7f  nop 
0047fb80  sub esp, 0xa0
0047fb86  push esi
0047fb87  push edi
0047fb88  push 0
0047fb8a  push 2
0047fb8c  lea ecx, [esp + 0x10]
0047fb90  mov dword ptr [esp + 0x10], 0
0047fb98  call 0x47d720
0047fb9d  mov edi, dword ptr [esp + 0xac]
0047fba4  lea ecx, [esp + 8]
0047fba8  push edi
0047fba9  mov word ptr [esp + 0x98], 1
0047fbb3  call 0x47d860
0047fbb8  push 0
0047fbba  lea ecx, [esp + 0xc]
0047fbbe  call 0x47f350
0047fbc3  mov esi, eax
0047fbc5  test esi, esi
0047fbc7  je 0x47fbea
0047fbc9  push edi
0047fbca  lea ecx, [esp + 0xc]
0047fbce  mov word ptr [esp + 0x98], 0
0047fbd8  call 0x47d860
0047fbdd  push 0
0047fbdf  lea ecx, [esp + 0xc]
0047fbe3  call 0x47f350
0047fbe8  mov esi, eax
0047fbea  lea ecx, [esp + 8]
0047fbee  call 0x47d850
0047fbf3  test esi, esi
0047fbf5  je 0x47fbfc
0047fbf7  call 0x47fa90
0047fbfc  mov eax, esi
0047fbfe  pop edi
0047fbff  pop esi
0047fc00  add esp, 0xa0
0047fc06  ret 
0047fc07  nop 
0047fc08  nop 
0047fc09  nop 
0047fc0a  nop 
0047fc0b  nop 
0047fc0c  nop 
0047fc0d  nop 
0047fc0e  nop 
0047fc0f  nop 
0047fc10  sub esp, 0xa0
0047fc16  push 1
0047fc18  push 2
0047fc1a  lea ecx, [esp + 8]
0047fc1e  mov dword ptr [esp + 8], 0
0047fc26  call 0x47d720
0047fc2b  mov eax, dword ptr [esp + 0xa4]
0047fc32  lea ecx, [esp]
0047fc36  push eax
0047fc37  call 0x47d860
0047fc3c  lea ecx, [esp]
0047fc40  call 0x47f5c0
0047fc45  lea ecx, [esp]
0047fc49  call 0x47d850
0047fc4e  mov dword ptr [0x520620], 1
0047fc58  add esp, 0xa0
0047fc5e  ret 
0047fc5f  nop 
0047fc60  sub esp, 0xd4
0047fc66  push 0
0047fc68  push 2
0047fc6a  lea ecx, [esp + 0x3c]
0047fc6e  mov dword ptr [esp + 0x3c], 0
0047fc76  call 0x47d720
0047fc7b  mov ecx, dword ptr [esp + 0xd8]
0047fc82  lea eax, [esp]
0047fc86  push eax
0047fc87  push ecx
0047fc88  lea ecx, [esp + 0x3c]
0047fc8c  call 0x47d890
0047fc91  lea ecx, [esp + 0x34]
0047fc95  call 0x47d850
0047fc9a  mov edx, dword ptr [esp + 0xdc]
0047fca1  mov ax, word ptr [esp]
0047fca6  mov ecx, dword ptr [esp + 0xe0]
0047fcad  mov word ptr [edx], ax
0047fcb0  mov dx, word ptr [esp + 2]
0047fcb5  mov eax, dword ptr [esp + 0xe4]
0047fcbc  mov word ptr [ecx], dx
0047fcbf  mov cx, word ptr [esp + 4]
0047fcc4  lea edx, [esp + 6]
0047fcc8  push edx
0047fcc9  push 0x522c88
0047fcce  mov word ptr [eax], cx
0047fcd1  call 0x4ebfe0
0047fcd6  add esp, 8
0047fcd9  lea eax, [esp + 0x13]
0047fcdd  push eax
0047fcde  push 0x522c60
0047fce3  call 0x4ebfe0
0047fce8  add esp, 8
0047fceb  lea ecx, [esp + 0x20]
0047fcef  push ecx
0047fcf0  push 0x522c70
0047fcf5  call 0x4ebfe0
0047fcfa  add esp, 8
0047fcfd  add esp, 0xd4
0047fd03  ret 
0047fd04  nop 
0047fd05  nop 
0047fd06  nop 
0047fd07  nop 
0047fd08  nop 
0047fd09  nop 
0047fd0a  nop 
0047fd0b  nop 
0047fd0c  nop 
0047fd0d  nop 
0047fd0e  nop 
0047fd0f  nop 
0047fd10  sub esp, 0xd4
0047fd16  mov ax, word ptr [esp + 0xdc]
0047fd1e  mov cx, word ptr [esp + 0xe0]
0047fd26  mov dx, word ptr [esp + 0xe4]
0047fd2e  mov word ptr [esp], ax
0047fd33  mov eax, dword ptr [esp + 0xe8]
0047fd3a  mov word ptr [esp + 2], cx
0047fd3f  push esi
0047fd40  lea ecx, [esp + 0xa]
0047fd44  push eax
0047fd45  push ecx
0047fd46  mov dword ptr [esp + 0x40], 0
0047fd4e  mov word ptr [esp + 0x10], dx
0047fd53  call 0x4ebfe0
0047fd58  mov edx, dword ptr [esp + 0xf8]
0047fd5f  add esp, 8
0047fd62  lea eax, [esp + 0x17]
0047fd66  push edx
0047fd67  push eax
0047fd68  call 0x4ebfe0
0047fd6d  mov ecx, dword ptr [esp + 0xfc]
0047fd74  add esp, 8
0047fd77  lea edx, [esp + 0x24]
0047fd7b  push ecx
0047fd7c  push edx
0047fd7d  call 0x4ebfe0
0047fd82  add esp, 8
0047fd85  lea ecx, [esp + 0x38]
0047fd89  push 1
0047fd8b  push 2
0047fd8d  call 0x47d720
0047fd92  mov ecx, dword ptr [esp + 0xdc]
0047fd99  lea eax, [esp + 4]
0047fd9d  push eax
0047fd9e  push ecx
0047fd9f  lea ecx, [esp + 0x40]
0047fda3  mov esi, 1
0047fda8  call 0x47d8d0
0047fdad  test ax, ax
0047fdb0  jne 0x47fdc1
0047fdb2  push 0x509638
0047fdb7  call 0x47ae80
0047fdbc  add esp, 4
0047fdbf  xor esi, esi
0047fdc1  lea ecx, [esp + 0x38]
0047fdc5  call 0x47d850
0047fdca  mov eax, esi
0047fdcc  pop esi
0047fdcd  add esp, 0xd4
0047fdd3  ret 
0047fdd4  nop 
0047fdd5  nop 
0047fdd6  nop 
0047fdd7  nop 
0047fdd8  nop 
0047fdd9  nop 
0047fdda  nop 
0047fddb  nop 
0047fddc  nop 
0047fddd  nop 
0047fdde  nop 
0047fddf  nop 
0047fde0  mov eax, dword ptr [0x509680]
0047fde5  push 1
0047fde7  push eax
0047fde8  call 0x47fe00
0047fded  add esp, 8
0047fdf0  ret 
0047fdf1  nop 
0047fdf2  nop 
0047fdf3  nop 
0047fdf4  nop 
0047fdf5  nop 
0047fdf6  nop 
0047fdf7  nop 
0047fdf8  nop 
0047fdf9  nop 
0047fdfa  nop 
0047fdfb  nop 
0047fdfc  nop 
0047fdfd  nop 
0047fdfe  nop 
0047fdff  nop 
0047fe00  mov eax, dword ptr [0x5095e0]
0047fe05  sub esp, 0x2a8
0047fe0b  test eax, eax
0047fe0d  push ebx
0047fe0e  push ebp
0047fe0f  push esi
0047fe10  push edi
0047fe11  je 0x47fe25
0047fe13  call 0x47fea0
0047fe18  test eax, eax
0047fe1a  jne 0x47fe25
0047fe1c  call 0x480140
0047fe21  test eax, eax
0047fe23  je 0x47fe85
0047fe25  call 0x47fea0
0047fe2a  test eax, eax
0047fe2c  je 0x47fe7b
0047fe2e  mov ebp, dword ptr [esp + 0x2bc]
0047fe35  xor esi, esi
0047fe37  lea ebx, [esp + 0x10]
0047fe3b  lea edi, [esp + 0x30]
0047fe3f  push edi
0047fe40  push esi
0047fe41  call 0x47ff50
0047fe46  add esp, 8
0047fe49  mov dword ptr [ebx], edi
0047fe4b  inc esi
0047fe4c  add edi, 0x51
0047fe4f  add ebx, 4
0047fe52  cmp si, 8
0047fe56  jb 0x47fe3f
0047fe58  push 0
0047fe5a  push ebp
0047fe5b  lea eax, [esp + 0x18]
0047fe5f  push 0
0047fe61  push eax
0047fe62  push 8
0047fe64  call 0x47be00
0047fe69  add esp, 0x14
0047fe6c  cmp ax, 8
0047fe70  jne 0x47fe89
0047fe72  call 0x47fea0
0047fe77  test eax, eax
0047fe79  jne 0x47fe35
0047fe7b  mov dword ptr [0x5095e0], 1
0047fe85  or ax, 0xffff
0047fe89  pop edi
0047fe8a  pop esi
0047fe8b  pop ebp
0047fe8c  pop ebx
0047fe8d  add esp, 0x2a8
0047fe93  ret 
0047fe94  nop 
0047fe95  nop 
0047fe96  nop 
0047fe97  nop 
0047fe98  nop 
0047fe99  nop 
0047fe9a  nop 
0047fe9b  nop 
0047fe9c  nop 
0047fe9d  nop 
0047fe9e  nop 
0047fe9f  nop 
0047fea0  sub esp, 0x9c
0047fea6  lea eax, [esp + 0x10]
0047feaa  push 0
0047feac  push eax
0047fead  mov dword ptr [esp + 0x18], 0
0047feb5  call 0x47d780
0047feba  add esp, 8
0047febd  test eax, eax
0047febf  je 0x47ff38
0047fec1  lea ecx, [esp]
0047fec5  push 0x10
0047fec7  push ecx
0047fec8  lea ecx, [esp + 0x18]
0047fecc  call 0x4411b0
0047fed1  mov edx, dword ptr [esp + 0x10]
0047fed5  push edx
0047fed6  call dword ptr [0x4fb09c]
0047fedc  push 0x10
0047fede  lea eax, [esp + 4]
0047fee2  push 0x4fc210
0047fee7  push eax
0047fee8  call 0x492850
0047feed  add esp, 0xc
0047fef0  test ax, ax
0047fef3  jne 0x47ff01
0047fef5  mov eax, 1
0047fefa  add esp, 0x9c