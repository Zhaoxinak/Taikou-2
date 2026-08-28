004e85e0  push      esi
004e85e1  call      0x4e8150
004e85e6  mov       eax, dword ptr [esp + 0x28]
004e85ea  add       esp, 0xc
004e85ed  add       edi, 4
004e85f0  dec       eax
004e85f1  mov       dword ptr [esp + 0x1c], eax
004e85f5  jne       0x4e85bb
004e85f7  pop       edi
004e85f8  pop       esi
004e85f9  pop       ebp
004e85fa  pop       ebx
004e85fb  pop       ecx
004e85fc  ret       
004e85fd  nop       
004e85fe  nop       
004e85ff  nop       
004e8600  sub       esp, 0xc
004e8603  push      esi
004e8604  call      0x480240
004e8609  mov       esi, eax
004e860b  cmp       si, -1
004e860f  je        0x4e8774
004e8615  lea       eax, [esp + 0xa]
004e8619  lea       ecx, [esp + 8]
004e861d  push      eax
004e861e  lea       edx, [esp + 0xa]
004e8622  push      ecx
004e8623  push      edx
004e8624  push      esi
004e8625  call      0x47fc60
004e862a  add       esp, 0x10
004e862d  cmp       word ptr [esp + 6], 0
004e8633  jne       0x4e8654
004e8635  cmp       word ptr [esp + 8], 0
004e863b  jne       0x4e8654
004e863d  cmp       word ptr [esp + 0xa], 0
004e8643  jne       0x4e8654
004e8645  push      0x50d820
004e864a  call      0x47b160
004e864f  add       esp, 4
004e8652  jmp       0x4e8604
004e8654  push      0x50d834
004e8659  call      0x47b390
004e865e  add       esp, 4
004e8661  test      eax, eax
004e8663  je        0x4e8604
004e8665  push      esi
004e8666  call      0x47fb80
004e866b  add       esp, 4
004e866e  test      eax, eax
004e8670  je        0x4e8604
004e8672  mov       ecx, 0x526c50
004e8677  call      0x4edfa0
004e867c  call      0x47adc0
004e8681  mov       ecx, 0x5239f0
004e8686  call      0x4ee340
004e868b  mov       ecx, 0x523ae0
004e8690  call      0x4ee340
004e8695  mov       ecx, 0x523748
004e869a  call      0x4ee340
004e869f  mov       ecx, 0x523748
004e86a4  call      0x4b0ad0
004e86a9  mov       ax, word ptr [0x5205fe]
004e86af  mov       word ptr [esp + 0xc], ax
004e86b4  mov       eax, dword ptr [esp + 0xc]
004e86b8  and       eax, 0xffff
004e86bd  sub       eax, 0
004e86c0  je        0x4e86e7
004e86c2  dec       eax
004e86c3  jne       0x4e870f
004e86c5  call      0x492ed0
004e86ca  call      0x4931f0
004e86cf  call      0x4ac9c0
004e86d4  push      1
004e86d6  call      0x4ae380
004e86db  add       esp, 4
004e86de  push      0
004e86e0  call      0x4a0b70
004e86e5  jmp       0x4e870c
004e86e7  call      0x492e20
004e86ec  call      0x493140
004e86f1  push      0
004e86f3  call      0x48cc20
004e86f8  add       esp, 4
004e86fb  call      0x48d350
004e8700  call      0x48e690
004e8705  push      0
004e8707  call      0x4a0b20
004e870c  add       esp, 4
004e870f  mov       ecx, 0x524740
004e8714  call      0x491e70
004e8719  mov       ecx, 0x524740
004e871e  call      0x4873b0
004e8723  mov       ecx, 0x524740
004e8728  call      0x491f90
004e872d  mov       ecx, 0x524740
004e8732  call      0x492050
004e8737  call      0x499050
004e873c  mov       al, 0xff
004e873e  mov       word ptr [0x506c4c], 0xffff
004e8747  mov       dword ptr [0x51e0f8], 0
004e8751  mov       dword ptr [0x520614], 0
004e875b  mov       byte ptr [0x506c5c], al
004e8760  mov       byte ptr [0x506c60], al
004e8765  call      0x47ad60
004e876a  mov       ecx, 0x526c50
004e876f  call      0x4edf70
004e8774  pop       esi
004e8775  add       esp, 0xc
004e8778  ret       
004e8779  nop       
004e877a  nop       
004e877b  nop       
004e877c  nop       
004e877d  nop       
004e877e  nop       
004e877f  nop       
004e8780  push      0
004e8782  mov       ecx, 0x515ad0
004e8787  call      0x479d70
004e878c  push      0
004e878e  mov       ecx, 0x5159a8
004e8793  call      0x479f10
004e8798  mov       eax, dword ptr [esp + 4]
004e879c  mov       eax, dword ptr [eax + 4]
004e879f  sub       eax, 0x7de
004e87a4  je        0x4e87ba
004e87a6  dec       eax
004e87a7  je        0x4e87b3
004e87a9  dec       eax
004e87aa  jne       0x4e87bf
004e87ac  call      0x4e8ac0
004e87b1  jmp       0x4e87bf
004e87b3  call      0x4e8600
004e87b8  jmp       0x4e87bf
004e87ba  call      0x4e87e0
004e87bf  push      1
004e87c1  mov       ecx, 0x515ad0
004e87c6  call      0x479d70
004e87cb  push      1
004e87cd  mov       ecx, 0x5159a8
004e87d2  call      0x479f10
004e87d7  ret       
004e87d8  nop       
004e87d9  nop       
004e87da  nop       
004e87db  nop       
004e87dc  nop       
004e87dd  nop       
004e87de  nop       
004e87df  nop       
004e87e0  sub       esp, 0x40
004e87e3  push      ebx
004e87e4  push      ebp
004e87e5  push      esi
004e87e6  push      edi
004e87e7  call      0x47fde0
004e87ec  cmp       ax, 0xffff
004e87f0  mov       dword ptr [esp + 0x18], eax
004e87f4  je        0x4e89ef
004e87fa  push      0x50d8c0
004e87ff  call      0x47b390
004e8804  add       esp, 4
004e8807  test      eax, eax
004e8809  je        0x4e89ef
004e880f  movzx     bx, byte ptr [0x5205f0]
004e8817  movzx     ax, byte ptr [0x5205f2]
004e881f  movzx     bp, byte ptr [0x5205f1]
004e8827  add       ebx, 0x618
004e882d  mov       word ptr [esp + 0x14], ax
004e8832  call      0x49f5e0
004e8837  mov       esi, eax
004e8839  xor       ecx, ecx
004e883b  mov       cl, byte ptr [esi + 0x2d]
004e883e  and       ecx, 7
004e8841  mov       edi, ecx
004e8843  cmp       di, 7
004e8847  je        0x4e8857
004e8849  test      byte ptr [0x516638], 4
004e8850  je        0x4e8857
004e8852  mov       edi, 8
004e8857  test      di, di
004e885a  mov       byte ptr [esp + 0x3c], 0
004e885f  je        0x4e88ab
004e8861  mov       al, byte ptr [esi + 0x25]
004e8864  cmp       al, 0xc8
004e8866  mov       byte ptr [esp + 0x10], al
004e886a  jae       0x4e8884
004e886c  mov       eax, dword ptr [esp + 0x10]
004e8870  and       eax, 0xff
004e8875  mov       ecx, eax
004e8877  shl       ecx, 5
004e887a  sub       ecx, eax
004e887c  add       ecx, 0x51eb88
004e8882  jmp       0x4e8886
004e8884  xor       ecx, ecx
004e8886  call      0x49b140
004e888b  lea       edx, [esp + 0x3c]
004e888f  push      eax
004e8890  push      edx
004e8891  call      0x4ec010
004e8896  add       esp, 8
004e8899  lea       eax, [esp + 0x3c]
004e889d  push      0x5029b8
004e88a2  push      eax
004e88a3  call      0x4ec010
004e88a8  add       esp, 8
004e88ab  and       edi, 0xffff
004e88b1  lea       edx, [esp + 0x3c]
004e88b5  mov       ecx, dword ptr [edi*4 + 0x50d850]
004e88bc  push      ecx
004e88bd  push      edx
004e88be  call      0x4ec010
004e88c3  mov       ax, word ptr [0x5205fe]
004e88c9  add       esp, 8
004e88cc  mov       word ptr [esp + 0x10], ax
004e88d1  mov       eax, dword ptr [esp + 0x10]
004e88d5  and       eax, 0xffff
004e88da  sub       eax, 0
004e88dd  je        0x4e8941
004e88df  dec       eax
004e88e0  jne       0x4e8996
004e88e6  mov       byte ptr [esi + 0x12], 0xff
004e88ea  mov       al, byte ptr [0x520603]
004e88ef  sub       al, 0x38
004e88f1  mov       byte ptr [esi + 0x13], al
004e88f4  mov       eax, dword ptr [0x51e108]
004e88f9  mov       cx, word ptr [0x51e10a]
004e8900  mov       byte ptr [esi + 0x14], al
004e8903  mov       byte ptr [esi + 0x15], cl
004e8906  mov       al, byte ptr [0x520603]
004e890b  cmp       al, 0x31
004e890d  mov       byte ptr [esp + 0x10], al
004e8911  jae       0x4e8925
004e8913  mov       eax, dword ptr [esp + 0x10]
004e8917  and       eax, 0xff
004e891c  lea       ecx, [eax + eax*4 + 0x519548]
004e8923  jmp       0x4e8927
004e8925  xor       ecx, ecx
004e8927  call      0x49b440
004e892c  lea       ecx, [esp + 0x1c]
004e8930  push      eax
004e8931  push      ecx
004e8932  call      0x4ebfe0
004e8937  add       esp, 8
004e893a  push      0x50d8bc
004e893f  jmp       0x4e8989
004e8941  push      0
004e8943  call      0x48e030
004e8948  mov       ax, word ptr [0x524866]
004e894e  add       esp, 4
004e8951  mov       word ptr [esp + 0x10], ax
004e8956  cmp       byte ptr [esp + 0x10], 0x31
004e895b  jae       0x4e896f
004e895d  mov       eax, dword ptr [esp + 0x10]
004e8961  and       eax, 0xff
004e8966  lea       ecx, [eax + eax*4 + 0x519548]
004e896d  jmp       0x4e8971
004e896f  xor       ecx, ecx
004e8971  call      0x49b400
004e8976  lea       ecx, [esp + 0x1c]
004e897a  push      eax
004e897b  push      ecx
004e897c  call      0x4ebfe0
004e8981  add       esp, 8
004e8984  push      0x50d8b8
004e8989  lea       edx, [esp + 0x20]
004e898d  push      edx
004e898e  call      0x4ec010
004e8993  add       esp, 8
004e8996  lea       eax, [esp + 0x2c]
004e899a  push      esi
004e899b  push      eax
004e899c  call      0x49f150
004e89a1  mov       eax, dword ptr [0x520628]
004e89a6  add       esp, 8
004e89a9  test      eax, eax
004e89ab  je        0x4e89b2
004e89ad  call      0x480260
004e89b2  mov       esi, dword ptr [esp + 0x18]
004e89b6  lea       ecx, [esp + 0x3c]
004e89ba  lea       edx, [esp + 0x1c]
004e89be  push      ecx
004e89bf  mov       ecx, dword ptr [esp + 0x18]
004e89c3  lea       eax, [esp + 0x30]
004e89c7  push      edx
004e89c8  push      eax
004e89c9  push      ecx
004e89ca  push      ebp
004e89cb  push      ebx
004e89cc  push      esi
004e89cd  call      0x47fd10
004e89d2  add       esp, 0x1c
004e89d5  test      eax, eax
004e89d7  je        0x4e89ef
004e89d9  push      esi
004e89da  call      0x47fc10
004e89df  add       esp, 4
004e89e2  push      0x50d8ac
004e89e7  call      0x47b260
004e89ec  add       esp, 4
004e89ef  pop       edi
004e89f0  pop       esi
004e89f1  pop       ebp
004e89f2  pop       ebx
004e89f3  add       esp, 0x40
004e89f6  ret       
004e89f7  nop       
004e89f8  nop       
004e89f9  nop       
004e89fa  nop       
004e89fb  nop       
004e89fc  nop       
004e89fd  nop       
004e89fe  nop       
004e89ff  nop       
004e8a00  cmp       word ptr [0x5205fe], 1
004e8a08  push      ebx
004e8a09  push      esi
004e8a0a  jne       0x4e8a11
004e8a0c  call      0x48f8e0
004e8a11  mov       esi, dword ptr [esp + 0xc]
004e8a15  test      esi, esi
004e8a17  jne       0x4e8a20
004e8a19  mov       ebx, 0xc8
004e8a1e  jmp       0x4e8a3d
004e8a20  mov       ecx, esi
004e8a22  mov       eax, 0x84210843
004e8a27  sub       ecx, 0x51eb88
004e8a2d  imul      ecx
004e8a2f  add       edx, ecx
004e8a31  sar       edx, 4
004e8a34  mov       eax, edx
004e8a36  shr       eax, 0x1f
004e8a39  add       edx, eax
004e8a3b  mov       ebx, edx
004e8a3d  call      0x49f5e0
004e8a42  add       eax, 0x12
004e8a45  mov       byte ptr [eax + 1], bl
004e8a48  call      0x4a2e70
004e8a4d  mov       dword ptr [0x519227], esi
004e8a53  pop       esi
004e8a54  pop       ebx
004e8a55  ret       
004e8a56  nop       
004e8a57  nop       
004e8a58  nop       
004e8a59  nop       
004e8a5a  nop       
004e8a5b  nop       
004e8a5c  nop       
004e8a5d  nop       
004e8a5e  nop       
004e8a5f  nop       
004e8a60  cmp       word ptr [0x5205fe], 1
004e8a68  push      ebx
004e8a69  push      esi
004e8a6a  jne       0x4e8a71
004e8a6c  call      0x48f8e0
004e8a71  mov       esi, dword ptr [esp + 0xc]
004e8a75  test      esi, esi
004e8a77  jne       0x4e8a80
004e8a79  mov       ebx, 0x31
004e8a7e  jmp       0x4e8a9a
004e8a80  mov       ecx, esi
004e8a82  mov       eax, 0x66666667
004e8a87  sub       ecx, 0x519548
004e8a8d  imul      ecx
004e8a8f  sar       edx, 1
004e8a91  mov       eax, edx
004e8a93  shr       eax, 0x1f
004e8a96  add       edx, eax
004e8a98  mov       ebx, edx
004e8a9a  call      0x49f5e0
004e8a9f  add       eax, 0x12
004e8aa2  sub       bl, 0x38
004e8aa5  mov       byte ptr [eax + 1], bl
004e8aa8  call      0x4a2e70
004e8aad  mov       dword ptr [0x51922b], esi
004e8ab3  pop       esi
004e8ab4  pop       ebx
004e8ab5  ret       
004e8ab6  nop       
004e8ab7  nop       
004e8ab8  nop       
004e8ab9  nop       
004e8aba  nop       
004e8abb  nop       
004e8abc  nop       
004e8abd  nop       
004e8abe  nop       
004e8abf  nop       
004e8ac0  sub       esp, 0x14
004e8ac3  push      esi
004e8ac4  mov       dword ptr [esp + 8], 0x50d938
004e8acc  mov       dword ptr [esp + 0xc], 0x50d948
004e8ad4  mov       dword ptr [esp + 0x10], 0x50d958
004e8adc  mov       dword ptr [esp + 0x14], 0x50d968
004e8ae4  call      0x49f5e0
004e8ae9  mov       ax, word ptr [eax + 0x2c]
004e8aed  mov       ecx, 0
004e8af2  shr       eax, 8
004e8af5  and       eax, 7
004e8af8  setne     cl
004e8afb  add       ecx, 3