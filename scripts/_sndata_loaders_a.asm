========== LoadSNDATA @0x47d720  (0x47d720 - 0x47d860) ==========
0047d720  mov        ax, word ptr [esp + 4]
0047d725  push       esi
0047d726  cmp        ax, 2
0047d72a  jae        0x47d759
0047d72c  test       ax, ax
0047d72f  mov        esi, 0x5095b0
0047d734  jne        0x47d73b
0047d736  mov        esi, 0x5095a0
0047d73b  mov        eax, dword ptr [esp + 0xc]
0047d73f  push       eax
0047d740  push       esi
0047d741  call       0x4802e0
0047d746  test       eax, eax
0047d748  jne        0x47d76f
0047d74a  push       esi
0047d74b  call       0x47bde0
0047d750  add        esp, 4
0047d753  xor        eax, eax
0047d755  pop        esi
0047d756  ret        8
0047d759  mov        edx, dword ptr [esp + 0xc]
0047d75d  push       edx
0047d75e  push       ecx
0047d75f  call       0x47d780
0047d764  add        esp, 8
0047d767  test       eax, eax
0047d769  jne        0x47d76f
0047d76b  pop        esi
0047d76c  ret        8
0047d76f  mov        eax, 1
0047d774  pop        esi
0047d775  ret        8
0047d778  nop        
0047d779  nop        
0047d77a  nop        
0047d77b  nop        
0047d77c  nop        
0047d77d  nop        
0047d77e  nop        
0047d77f  nop        
0047d780  sub        esp, 0x20
0047d783  lea        eax, [esp]
0047d787  push       0x509590
0047d78c  push       eax
0047d78d  call       0x4ebfe0
0047d792  mov        ecx, dword ptr [0x5095e0]
0047d798  add        esp, 8
0047d79b  test       ecx, ecx
0047d79d  je         0x47d7ac
0047d79f  call       0x4ef690
0047d7a4  mov        ecx, dword ptr [0x5095e0]
0047d7aa  jmp        0x47d7b1
0047d7ac  mov        eax, dword ptr [0x526c78]
0047d7b1  add        al, 0x40
0047d7b3  mov        edx, dword ptr [esp + 0x28]
0047d7b7  mov        byte ptr [esp], al
0047d7bb  mov        eax, ecx
0047d7bd  neg        eax
0047d7bf  sbb        eax, eax
0047d7c1  and        eax, 4
0047d7c4  or         eax, edx
0047d7c6  test       ecx, ecx
0047d7c8  je         0x47d7dd
0047d7ca  lea        ecx, [esp]
0047d7ce  push       eax
0047d7cf  push       ecx
0047d7d0  mov        ecx, dword ptr [esp + 0x2c]
0047d7d4  call       0x4802e0
0047d7d9  add        esp, 0x20
0047d7dc  ret        
0047d7dd  mov        ecx, dword ptr [esp + 0x24]
0047d7e1  lea        eax, [esp]
0047d7e5  push       eax
0047d7e6  push       edx
0047d7e7  push       ecx
0047d7e8  call       0x47d800
0047d7ed  add        esp, 0xc
0047d7f0  add        esp, 0x20
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
0047d800  push       ebx
0047d801  mov        ebx, dword ptr [esp + 0xc]
0047d805  push       esi
0047d806  mov        esi, dword ptr [esp + 0x14]
0047d80a  push       edi
0047d80b  mov        edi, dword ptr [esp + 0x10]
0047d80f  push       0
0047d811  call       0x4ef720
0047d816  add        esp, 4
0047d819  test       eax, eax
0047d81b  je         0x47d82a
0047d81d  push       ebx
0047d81e  push       esi
0047d81f  mov        ecx, edi
0047d821  call       0x4802e0
0047d826  test       eax, eax
0047d828  jne        0x47d83d
0047d82a  push       0x5095e8
0047d82f  call       0x47af50
0047d834  add        esp, 4
0047d837  test       eax, eax
0047d839  je         0x47d846
0047d83b  jmp        0x47d80f
0047d83d  mov        eax, 1
0047d842  pop        edi
0047d843  pop        esi
0047d844  pop        ebx
0047d845  ret        
0047d846  pop        edi
0047d847  pop        esi
0047d848  xor        eax, eax
0047d84a  pop        ebx
0047d84b  ret        
0047d84c  nop        
0047d84d  nop        
0047d84e  nop        
0047d84f  nop        
0047d850  mov        eax, dword ptr [ecx]
0047d852  push       eax
0047d853  call       dword ptr [0x4fb09c]
0047d859  ret        
0047d85a  nop        
0047d85b  nop        
0047d85c  nop        
0047d85d  nop        
0047d85e  nop        
0047d85f  nop        
========== 40960-block accessor @0x47d860  (0x47d860 - 0x47de00) ==========
0047d860  mov        eax, dword ptr [esp + 4]
0047d864  push       0
0047d866  and        eax, 0xffff
0047d86b  lea        eax, [eax + eax*4]
0047d86e  shl        eax, 0xd
0047d871  add        eax, 0x198
0047d876  mov        dword ptr [ecx + 0x96], eax
0047d87c  mov        ecx, dword ptr [ecx]
0047d87e  push       eax
0047d87f  push       ecx
0047d880  call       dword ptr [0x4fb0a8]
0047d886  ret        4
0047d889  nop        
0047d88a  nop        
0047d88b  nop        
0047d88c  nop        
0047d88d  nop        
0047d88e  nop        
0047d88f  nop        
0047d890  mov        eax, dword ptr [esp + 4]
0047d894  push       esi
0047d895  and        eax, 0xffff
0047d89a  mov        esi, ecx
0047d89c  push       0
0047d89e  lea        ecx, [eax + eax*2]
0047d8a1  shl        ecx, 4
0047d8a4  lea        edx, [ecx + eax + 0x10]
0047d8a8  mov        eax, dword ptr [esi]
0047d8aa  push       edx
0047d8ab  push       eax
0047d8ac  call       dword ptr [0x4fb0a8]
0047d8b2  mov        ecx, dword ptr [esp + 0xc]
0047d8b6  push       0x31
0047d8b8  push       ecx
0047d8b9  mov        ecx, esi
0047d8bb  call       0x4411b0
0047d8c0  pop        esi
0047d8c1  ret        8
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
0047d8d0  mov        eax, dword ptr [esp + 4]
0047d8d4  push       esi
0047d8d5  and        eax, 0xffff
0047d8da  mov        esi, ecx
0047d8dc  push       0
0047d8de  lea        ecx, [eax + eax*2]
0047d8e1  shl        ecx, 4
0047d8e4  lea        edx, [ecx + eax + 0x10]
0047d8e8  mov        eax, dword ptr [esi]
0047d8ea  push       edx
0047d8eb  push       eax
0047d8ec  call       dword ptr [0x4fb0a8]
0047d8f2  mov        ecx, dword ptr [esp + 0xc]
0047d8f6  push       0x31
0047d8f8  push       ecx
0047d8f9  mov        ecx, esi
0047d8fb  call       0x4411d0
0047d900  pop        esi
0047d901  ret        8
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
0047d910  cmp        word ptr [ecx + 0x8c], 0
0047d918  je         0x47d922
0047d91a  call       0x47da10
0047d91f  ret        4
0047d922  call       0x47da10
0047d927  mov        ecx, dword ptr [esp + 4]
0047d92b  mov        byte ptr [ecx], al
0047d92d  ret        4
0047d930  cmp        word ptr [ecx + 0x8c], 0
0047d938  je         0x47d942
0047d93a  call       0x47da50
0047d93f  ret        4
0047d942  call       0x47da50
0047d947  mov        ecx, dword ptr [esp + 4]
0047d94b  mov        word ptr [ecx], ax
0047d94e  ret        4
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
0047d960  push       ebx
0047d961  push       esi
0047d962  mov        esi, ecx
0047d964  push       0
0047d966  mov        ecx, 0x524978
0047d96b  call       0x4eb5c0
0047d970  push       0x2000
0047d975  push       eax
0047d976  mov        ecx, esi
0047d978  mov        dword ptr [esi + 0x9a], eax
0047d97e  call       0x4411b0
0047d983  mov        eax, dword ptr [esi + 0x9a]
0047d989  mov        ecx, 0x2000
0047d98e  mov        dl, byte ptr [esi + 0x94]
0047d994  mov        bl, byte ptr [eax]
0047d996  xor        bl, dl
0047d998  mov        byte ptr [eax], bl
0047d99a  inc        eax
0047d99b  dec        ecx
0047d99c  jne        0x47d98e
0047d99e  mov        word ptr [esi + 0x8e], 0
0047d9a7  pop        esi
0047d9a8  pop        ebx
0047d9a9  ret        
0047d9aa  nop        
0047d9ab  nop        
0047d9ac  nop        
0047d9ad  nop        
0047d9ae  nop        
0047d9af  nop        
0047d9b0  push       esi
0047d9b1  mov        esi, ecx
0047d9b3  push       edi
0047d9b4  push       0
0047d9b6  mov        di, word ptr [esi + 0x8e]
0047d9bd  mov        ecx, 0x524978
0047d9c2  call       0x4eb5c0
0047d9c7  test       di, di
0047d9ca  mov        dword ptr [esi + 0x9a], eax
0047d9d0  je         0x47d9e8
0047d9d2  and        edi, 0xffff
0047d9d8  mov        cl, byte ptr [esi + 0x94]
0047d9de  mov        dl, byte ptr [eax]
0047d9e0  xor        dl, cl
0047d9e2  mov        byte ptr [eax], dl
0047d9e4  inc        eax
0047d9e5  dec        edi
0047d9e6  jne        0x47d9d8
0047d9e8  mov        dx, word ptr [esi + 0x8e]
0047d9ef  mov        eax, dword ptr [esi + 0x9a]
0047d9f5  push       edx
0047d9f6  push       eax
0047d9f7  mov        ecx, esi
0047d9f9  call       0x4411d0
0047d9fe  mov        word ptr [esi + 0x8e], 0
0047da07  pop        edi
0047da08  pop        esi
0047da09  ret        
0047da0a  nop        
0047da0b  nop        
0047da0c  nop        
0047da0d  nop        
0047da0e  nop        
0047da0f  nop        
0047da10  push       esi
0047da11  mov        esi, ecx
0047da13  cmp        word ptr [esi + 0x8e], 0x2000
0047da1c  jne        0x47da23
0047da1e  call       0x47d960
0047da23  mov        ecx, dword ptr [esi + 0x9a]
0047da29  inc        word ptr [esi + 0x8e]
0047da30  mov        al, byte ptr [ecx]
0047da32  inc        ecx
0047da33  mov        dword ptr [esi + 0x9a], ecx
0047da39  xor        cx, cx
0047da3c  mov        cl, al
0047da3e  add        word ptr [esi + 0x92], cx
0047da45  pop        esi
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
0047da50  push       esi
0047da51  push       edi
0047da52  mov        esi, ecx
0047da54  call       0x47da10
0047da59  mov        ecx, esi
0047da5b  movzx      di, al
0047da5f  call       0x47da10
0047da64  and        eax, 0xff
0047da69  shl        eax, 8
0047da6c  add        eax, edi
0047da6e  pop        edi
0047da6f  pop        esi
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
0047da80  mov        edx, dword ptr [ecx + 0x9a]
0047da86  mov        al, byte ptr [esp + 4]
0047da8a  inc        word ptr [ecx + 0x8e]
0047da91  mov        byte ptr [edx], al
0047da93  mov        edx, dword ptr [ecx + 0x9a]
0047da99  movzx      ax, al
0047da9d  add        word ptr [ecx + 0x92], ax
0047daa4  inc        edx
0047daa5  cmp        word ptr [ecx + 0x8e], 0x2000
0047daae  mov        dword ptr [ecx + 0x9a], edx
0047dab4  jne        0x47dabb
0047dab6  call       0x47d9b0
0047dabb  ret        4
0047dabe  nop        
0047dabf  nop        
0047dac0  push       ebx
0047dac1  mov        ebx, dword ptr [esp + 8]
0047dac5  push       esi
0047dac6  mov        esi, ecx
0047dac8  push       ebx
0047dac9  call       0x47da80
0047dace  xor        eax, eax
0047dad0  mov        ecx, esi
0047dad2  mov        al, bh
0047dad4  push       eax
0047dad5  call       0x47da80
0047dada  pop        esi
0047dadb  pop        ebx
0047dadc  ret        4
0047dadf  nop        
0047dae0  push       esi
0047dae1  mov        esi, ecx
0047dae3  push       0x5205f0
0047dae8  call       0x47d910
0047daed  push       0x5205f1
0047daf2  mov        ecx, esi
0047daf4  call       0x47d910
0047daf9  push       0x5205f2
0047dafe  mov        ecx, esi
0047db00  call       0x47d910
0047db05  push       0x5205f3
0047db0a  mov        ecx, esi
0047db0c  call       0x47d910
0047db11  push       0x5205f4
0047db16  mov        ecx, esi
0047db18  call       0x47d910
0047db1d  push       0x5205f5
0047db22  mov        ecx, esi
0047db24  call       0x47d910
0047db29  push       0x5205f6
0047db2e  mov        ecx, esi
0047db30  call       0x47d930
0047db35  push       0x5205f8
0047db3a  mov        ecx, esi
0047db3c  call       0x47d930
0047db41  push       0x5205fa
0047db46  mov        ecx, esi
0047db48  call       0x47d930
0047db4d  push       0x5205fc
0047db52  mov        ecx, esi
0047db54  call       0x47d930
0047db59  push       0x5205fe
0047db5e  mov        ecx, esi
0047db60  call       0x47d930
0047db65  push       0x520600
0047db6a  mov        ecx, esi
0047db6c  call       0x47d930
0047db71  push       0x520602
0047db76  mov        ecx, esi
0047db78  call       0x47d910
0047db7d  push       0x520603
0047db82  mov        ecx, esi
0047db84  call       0x47d910
0047db89  push       0x520604
0047db8e  mov        ecx, esi
0047db90  call       0x47d930
0047db95  pop        esi
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
0047dba0  push       ecx
0047dba1  mov        al, byte ptr [0x5205f0]
0047dba6  push       esi
0047dba7  mov        esi, ecx
0047dba9  mov        byte ptr [esp + 4], al
0047dbad  mov        ecx, dword ptr [esp + 4]
0047dbb1  push       ecx
0047dbb2  mov        ecx, esi
0047dbb4  call       0x47da80
0047dbb9  mov        dl, byte ptr [0x5205f1]
0047dbbf  mov        ecx, esi
0047dbc1  mov        byte ptr [esp + 4], dl
0047dbc5  mov        eax, dword ptr [esp + 4]
0047dbc9  push       eax
0047dbca  call       0x47da80
0047dbcf  mov        cl, byte ptr [0x5205f2]
0047dbd5  mov        byte ptr [esp + 4], cl
0047dbd9  mov        ecx, esi
0047dbdb  mov        edx, dword ptr [esp + 4]
0047dbdf  push       edx
0047dbe0  call       0x47da80
0047dbe5  mov        al, byte ptr [0x5205f3]
0047dbea  mov        byte ptr [esp + 4], al
0047dbee  mov        ecx, dword ptr [esp + 4]
0047dbf2  push       ecx
0047dbf3  mov        ecx, esi
0047dbf5  call       0x47da80
0047dbfa  mov        dl, byte ptr [0x5205f4]
0047dc00  mov        ecx, esi
0047dc02  mov        byte ptr [esp + 4], dl
0047dc06  mov        eax, dword ptr [esp + 4]
0047dc0a  push       eax
0047dc0b  call       0x47da80
0047dc10  mov        cl, byte ptr [0x5205f5]
0047dc16  mov        byte ptr [esp + 4], cl
0047dc1a  mov        ecx, esi
0047dc1c  mov        edx, dword ptr [esp + 4]
0047dc20  push       edx
0047dc21  call       0x47da80
0047dc26  mov        ax, word ptr [0x5205f6]
0047dc2c  mov        word ptr [esp + 4], ax
0047dc31  mov        ecx, dword ptr [esp + 4]
0047dc35  push       ecx
0047dc36  mov        ecx, esi
0047dc38  call       0x47dac0
0047dc3d  mov        eax, dword ptr [0x5205f8]
0047dc42  mov        ecx, esi
0047dc44  push       eax
0047dc45  call       0x47dac0
0047dc4a  mov        dx, word ptr [0x5205fa]
0047dc51  mov        ecx, esi
0047dc53  mov        word ptr [esp + 4], dx
0047dc58  mov        eax, dword ptr [esp + 4]
0047dc5c  push       eax
0047dc5d  call       0x47dac0
0047dc62  mov        eax, dword ptr [0x5205fc]
0047dc67  mov        ecx, esi
0047dc69  push       eax
0047dc6a  call       0x47dac0
0047dc6f  mov        cx, word ptr [0x5205fe]
0047dc76  mov        word ptr [esp + 4], cx
0047dc7b  mov        ecx, esi
0047dc7d  mov        edx, dword ptr [esp + 4]
0047dc81  push       edx
0047dc82  call       0x47dac0
0047dc87  mov        eax, dword ptr [0x520600]
0047dc8c  mov        ecx, esi
0047dc8e  push       eax
0047dc8f  call       0x47dac0
0047dc94  mov        al, byte ptr [0x520602]
0047dc99  mov        byte ptr [esp + 4], al
0047dc9d  mov        ecx, dword ptr [esp + 4]
0047dca1  push       ecx
0047dca2  mov        ecx, esi
0047dca4  call       0x47da80
0047dca9  mov        dl, byte ptr [0x520603]
0047dcaf  mov        ecx, esi
0047dcb1  mov        byte ptr [esp + 4], dl
0047dcb5  mov        eax, dword ptr [esp + 4]
0047dcb9  push       eax
0047dcba  call       0x47da80
0047dcbf  mov        cx, word ptr [0x520604]
0047dcc6  mov        word ptr [esp + 4], cx
0047dccb  mov        ecx, esi
0047dccd  mov        edx, dword ptr [esp + 4]
0047dcd1  push       edx
0047dcd2  call       0x47dac0
0047dcd7  pop        esi
0047dcd8  pop        ecx
0047dcd9  ret        
0047dcda  nop        
0047dcdb  nop        
0047dcdc  nop        
0047dcdd  nop        
0047dcde  nop        
0047dcdf  nop        
0047dce0  sub        esp, 0xc
0047dce3  push       ebx
0047dce4  push       ebp
0047dce5  push       esi
0047dce6  push       edi
0047dce7  mov        esi, ecx
0047dce9  mov        edi, 0x51986a
0047dcee  mov        dword ptr [esp + 0x10], 0
0047dcf6  mov        dword ptr [esp + 0x14], 0x172
0047dcfe  mov        eax, dword ptr [esp + 0x10]
0047dd02  mov        ebp, 7
0047dd07  lea        ebx, [eax + 0x521aa8]
0047dd0d  push       ebx
0047dd0e  mov        ecx, esi
0047dd10  call       0x47d910
0047dd15  inc        ebx
0047dd16  dec        ebp
0047dd17  jne        0x47dd0d
0047dd19  mov        ecx, dword ptr [esp + 0x10]
0047dd1d  mov        ebp, 7
0047dd22  lea        ebx, [ecx + 0x520660]
0047dd28  push       ebx
0047dd29  mov        ecx, esi
0047dd2b  call       0x47d910
0047dd30  inc        ebx
0047dd31  dec        ebp
0047dd32  jne        0x47dd28
0047dd34  lea        edx, [edi - 2]
0047dd37  mov        ecx, esi
0047dd39  push       edx
0047dd3a  call       0x47d930
0047dd3f  push       edi
0047dd40  mov        ecx, esi
0047dd42  call       0x47d930
0047dd47  lea        eax, [esp + 0x18]
0047dd4b  mov        ecx, esi
0047dd4d  push       eax
0047dd4e  call       0x47d930
0047dd53  mov        ecx, dword ptr [esp + 0x18]
0047dd57  cmp        cx, 0x172
0047dd5c  jae        0x47dd73
0047dd5e  and        ecx, 0xffff
0047dd64  lea        eax, [ecx + ecx*2]
0047dd67  shl        eax, 4
0047dd6a  sub        eax, ecx
0047dd6c  add        eax, 0x519868
0047dd71  jmp        0x47dd75
0047dd73  xor        eax, eax
0047dd75  lea        ecx, [edi + 6]
0047dd78  mov        dword ptr [edi + 2], eax
0047dd7b  push       ecx
0047dd7c  mov        ecx, esi
0047dd7e  call       0x47d930
0047dd83  lea        edx, [edi + 8]
0047dd86  mov        ecx, esi
0047dd88  push       edx
0047dd89  call       0x47d910
0047dd8e  lea        eax, [edi + 9]
0047dd91  mov        ecx, esi
0047dd93  push       eax
0047dd94  call       0x47d910
0047dd99  lea        ecx, [edi + 0xa]
0047dd9c  push       ecx
0047dd9d  mov        ecx, esi
0047dd9f  call       0x47d910
0047dda4  lea        edx, [edi + 0xb]
0047dda7  mov        ecx, esi
0047dda9  push       edx
0047ddaa  call       0x47d910
0047ddaf  lea        eax, [edi + 0xc]
0047ddb2  mov        ecx, esi
0047ddb4  push       eax
0047ddb5  call       0x47d910
0047ddba  lea        ecx, [edi + 0xd]
0047ddbd  push       ecx
0047ddbe  mov        ecx, esi
0047ddc0  call       0x47d910
0047ddc5  lea        edx, [edi + 0xe]
0047ddc8  mov        ecx, esi
0047ddca  push       edx
0047ddcb  call       0x47d910
0047ddd0  lea        eax, [edi + 0xf]
0047ddd3  mov        ecx, esi
0047ddd5  push       eax
0047ddd6  call       0x47d910
0047dddb  lea        ecx, [edi + 0x10]
0047ddde  push       ecx
0047dddf  mov        ecx, esi
0047dde1  call       0x47d910
0047dde6  lea        edx, [edi + 0x11]
0047dde9  mov        ecx, esi
0047ddeb  push       edx
0047ddec  call       0x47d910
0047ddf1  lea        eax, [edi + 0x12]
0047ddf4  mov        ecx, esi
0047ddf6  push       eax
0047ddf7  call       0x47d910
0047ddfc  lea        ecx, [edi + 0x13]
0047ddff  push       ecx