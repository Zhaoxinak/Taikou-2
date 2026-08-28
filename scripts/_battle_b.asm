0x00439000  push esi
0x00439001  mov esi, dword ptr [esp + 8]
0x00439005  push edi
0x00439006  mov ecx, esi
0x00439008  mov al, byte ptr [esi + 0x2c]
0x0043900b  and al, 8
0x0043900d  neg al
0x0043900f  sbb eax, eax
0x00439011  and eax, 0xffffd000
0x00439016  add eax, 0x3000
0x0043901b  mov edi, eax
0x0043901d  call 0x43d680
0x00439022  cmp ax, 0xbb8
0x00439026  jb 0x43902c
0x00439028  xor eax, eax
0x0043902a  jmp 0x439038
0x0043902c  cmp ax, 0x1f4
0x00439030  sbb eax, eax
0x00439032  and eax, 4
0x00439035  add eax, 4
0x00439038  movzx cx, byte ptr [esi + 4]
0x0043903d  movzx dx, byte ptr [esi + 0x2e]
0x00439042  add ecx, eax
0x00439044  lea eax, [edx + ecx*2]
0x00439047  shl eax, 9
0x0043904a  add eax, edi
0x0043904c  pop edi
0x0043904d  pop esi
0x0043904e  ret 
0x0043904f  nop 
0x00439050  mov eax, dword ptr [esp + 8]
0x00439054  mov ecx, dword ptr [esp + 4]
0x00439058  and eax, 0xff
0x0043905d  and ecx, 0xff
0x00439063  lea eax, [eax + eax*4]
0x00439066  mov al, byte ptr [ecx + eax*4 + 0x512e58]
0x0043906d  and eax, 0xf
0x00439070  ret 
0x00439071  nop 
0x00439072  nop 
0x00439073  nop 
0x00439074  nop 
0x00439075  nop 
0x00439076  nop 
0x00439077  nop 
0x00439078  nop 
0x00439079  nop 
0x0043907a  nop 
0x0043907b  nop 
0x0043907c  nop 
0x0043907d  nop 
0x0043907e  nop 
0x0043907f  nop 
0x00439080  mov eax, dword ptr [esp + 8]
0x00439084  mov ecx, dword ptr [esp + 4]
0x00439088  and eax, 0xff
0x0043908d  and ecx, 0xff
0x00439093  lea eax, [eax + eax*4]
0x00439096  mov dl, byte ptr [ecx + eax*4 + 0x512e58]
0x0043909d  lea eax, [ecx + eax*4 + 0x512e58]
0x004390a4  mov cl, byte ptr [esp + 0xc]
0x004390a8  xor dl, cl
0x004390aa  mov cl, byte ptr [eax]
0x004390ac  and dl, 0xf
0x004390af  xor cl, dl
0x004390b1  mov byte ptr [eax], cl
0x004390b3  ret 
0x004390b4  nop 
0x004390b5  nop 
0x004390b6  nop 
0x004390b7  nop 
0x004390b8  nop 
0x004390b9  nop 
0x004390ba  nop 
0x004390bb  nop 
0x004390bc  nop 
0x004390bd  nop 
0x004390be  nop 
0x004390bf  nop 
0x004390c0  mov eax, dword ptr [esp + 8]
0x004390c4  mov ecx, dword ptr [esp + 4]
0x004390c8  and eax, 0xff
0x004390cd  and ecx, 0xff
0x004390d3  xor edx, edx
0x004390d5  lea eax, [eax + eax*4]
0x004390d8  mov dl, byte ptr [ecx + eax*4 + 0x512e58]
0x004390df  mov eax, edx
0x004390e1  shr eax, 4
0x004390e4  ret 
0x004390e5  nop 
0x004390e6  nop 
0x004390e7  nop 
0x004390e8  nop 
0x004390e9  nop 
0x004390ea  nop 
0x004390eb  nop 
0x004390ec  nop 
0x004390ed  nop 
0x004390ee  nop 
0x004390ef  nop 
0x004390f0  movsx eax, word ptr [esp + 4]
0x004390f5  mov edx, dword ptr [esp + 8]
0x004390f9  shl eax, 1
0x004390fb  mov cl, byte ptr [eax + 0x512f10]
0x00439101  mov byte ptr [edx], cl
0x00439103  mov ecx, dword ptr [esp + 0xc]
0x00439107  mov al, byte ptr [eax + 0x512f11]
0x0043910d  mov byte ptr [ecx], al
0x0043910f  ret 
0x00439110  mov eax, dword ptr [esp + 8]
0x00439114  mov ecx, dword ptr [esp + 4]
0x00439118  push eax
0x00439119  push ecx
0x0043911a  call 0x439050
0x0043911f  mov dl, 2
0x00439121  add esp, 8
0x00439124  cmp dl, al
0x00439126  sbb eax, eax
0x00439128  neg eax
0x0043912a  ret 
0x0043912b  nop 
0x0043912c  nop 
0x0043912d  nop 
0x0043912e  nop 
0x0043912f  nop 
0x00439130  mov eax, dword ptr [esp + 8]
0x00439134  mov ecx, dword ptr [esp + 4]
0x00439138  and eax, 0xff
0x0043913d  and ecx, 0xff
0x00439143  lea eax, [eax + eax*4]
0x00439146  mov al, byte ptr [ecx + eax*8 + 0x512b60]
0x0043914d  ret 
0x0043914e  nop 
0x0043914f  nop 
0x00439150  mov eax, dword ptr [esp + 8]
0x00439154  mov ecx, dword ptr [esp + 4]
0x00439158  mov dl, byte ptr [esp + 0xc]
0x0043915c  and eax, 0xff
0x00439161  and ecx, 0xff
0x00439167  lea eax, [eax + eax*4]
0x0043916a  mov byte ptr [ecx + eax*8 + 0x512b60], dl
0x00439171  ret 
0x00439172  nop 
0x00439173  nop 
0x00439174  nop 
0x00439175  nop 
0x00439176  nop 
0x00439177  nop 
0x00439178  nop 
0x00439179  nop 
0x0043917a  nop 
0x0043917b  nop 
0x0043917c  nop 
0x0043917d  nop 
0x0043917e  nop 
0x0043917f  nop 
0x00439180  mov eax, dword ptr [ecx + 0x18]
0x00439183  push eax
0x00439184  call 0x439190
0x00439189  add esp, 4
0x0043918c  ret 
0x0043918d  nop 
0x0043918e  nop 
0x0043918f  nop 
0x00439190  sub esp, 0x580
0x00439196  push ebx
0x00439197  push ebp
0x00439198  push esi
0x00439199  push edi
0x0043919a  call 0x43ca10
0x0043919f  test al, al
0x004391a1  jne 0x4392aa
0x004391a7  xor ebp, ebp
0x004391a9  push ebp
0x004391aa  call 0x43e820
0x004391af  mov esi, eax
0x004391b1  add esp, 4
0x004391b4  cmp byte ptr [esi], 4
0x004391b7  jne 0x43929f
0x004391bd  mov ecx, esi
0x004391bf  call 0x43e7a0
0x004391c4  test al, al
0x004391c6  je 0x43929f
0x004391cc  mov al, byte ptr [esi + 2]
0x004391cf  xor bx, bx
0x004391d2  mov bl, al
0x004391d4  and eax, 0xff
0x004391d9  cdq 
0x004391da  movzx cx, byte ptr [esi + 3]
0x004391df  xor eax, edx
0x004391e1  sub eax, edx
0x004391e3  and eax, 1
0x004391e6  xor eax, edx
0x004391e8  sub eax, edx
0x004391ea  xor eax, 1
0x004391ed  shl ebx, 1
0x004391ef  lea eax, [eax + ecx*2]
0x004391f2  push eax
0x004391f3  push ebx
0x004391f4  mov dword ptr [esp + 0x18], eax
0x004391f8  call 0x439130
0x004391fd  add esp, 8
0x00439200  cmp al, 0x2f
0x00439202  jne 0x43929f
0x00439208  movzx dx, byte ptr [esi + 3]
0x0043920d  movzx ax, byte ptr [esi + 2]
0x00439212  push edx
0x00439213  push eax
0x00439214  call 0x43e070
0x00439219  add esp, 8
0x0043921c  test eax, eax
0x0043921e  jne 0x43929f
