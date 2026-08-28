0x004e87e0  83ec40             sub      esp, 0x40
0x004e87e3  53                 push     ebx
0x004e87e4  55                 push     ebp
0x004e87e5  56                 push     esi
0x004e87e6  57                 push     edi
0x004e87e7  e8f475f9ff         call     0x47fde0
0x004e87ec  663dffff           cmp      ax, 0xffff
0x004e87f0  89442418           mov      dword ptr [esp + 0x18], eax
0x004e87f4  0f84f5010000       je       0x4e89ef
0x004e87fa  68c0d85000         push     0x50d8c0
0x004e87ff  e88c2bf9ff         call     0x47b390
0x004e8804  83c404             add      esp, 4
0x004e8807  85c0               test     eax, eax
0x004e8809  0f84e0010000       je       0x4e89ef
0x004e880f  660fb61df0055200   movzx    bx, byte ptr [0x5205f0]
0x004e8817  660fb605f2055200   movzx    ax, byte ptr [0x5205f2]
0x004e881f  660fb62df1055200   movzx    bp, byte ptr [0x5205f1]
0x004e8827  81c318060000       add      ebx, 0x618
0x004e882d  6689442414         mov      word ptr [esp + 0x14], ax
0x004e8832  e8a96dfbff         call     0x49f5e0
0x004e8837  8bf0               mov      esi, eax
0x004e8839  33c9               xor      ecx, ecx
0x004e883b  8a4e2d             mov      cl, byte ptr [esi + 0x2d]
0x004e883e  83e107             and      ecx, 7
0x004e8841  8bf9               mov      edi, ecx
0x004e8843  6683ff07           cmp      di, 7
0x004e8847  740e               je       0x4e8857
0x004e8849  f6053866510004     test     byte ptr [0x516638], 4
0x004e8850  7405               je       0x4e8857
0x004e8852  bf08000000         mov      edi, 8
0x004e8857  6685ff             test     di, di
0x004e885a  c644243c00         mov      byte ptr [esp + 0x3c], 0
0x004e885f  744a               je       0x4e88ab
0x004e8861  8a4625             mov      al, byte ptr [esi + 0x25]
0x004e8864  3cc8               cmp      al, 0xc8
0x004e8866  88442410           mov      byte ptr [esp + 0x10], al
0x004e886a  7318               jae      0x4e8884
0x004e886c  8b442410           mov      eax, dword ptr [esp + 0x10]
0x004e8870  25ff000000         and      eax, 0xff
0x004e8875  8bc8               mov      ecx, eax
0x004e8877  c1e105             shl      ecx, 5
0x004e887a  2bc8               sub      ecx, eax
0x004e887c  81c188eb5100       add      ecx, 0x51eb88
0x004e8882  eb02               jmp      0x4e8886
0x004e8884  33c9               xor      ecx, ecx
0x004e8886  e8b528fbff         call     0x49b140
0x004e888b  8d54243c           lea      edx, [esp + 0x3c]
0x004e888f  50                 push     eax
0x004e8890  52                 push     edx
0x004e8891  e87a370000         call     0x4ec010
0x004e8896  83c408             add      esp, 8
0x004e8899  8d44243c           lea      eax, [esp + 0x3c]
0x004e889d  68b8295000         push     0x5029b8
0x004e88a2  50                 push     eax
0x004e88a3  e868370000         call     0x4ec010
0x004e88a8  83c408             add      esp, 8
0x004e88ab  81e7ffff0000       and      edi, 0xffff
0x004e88b1  8d54243c           lea      edx, [esp + 0x3c]
0x004e88b5  8b0cbd50d85000     mov      ecx, dword ptr [edi*4 + 0x50d850]
0x004e88bc  51                 push     ecx
0x004e88bd  52                 push     edx
0x004e88be  e84d370000         call     0x4ec010
0x004e88c3  66a1fe055200       mov      ax, word ptr [0x5205fe]
0x004e88c9  83c408             add      esp, 8
0x004e88cc  6689442410         mov      word ptr [esp + 0x10], ax
0x004e88d1  8b442410           mov      eax, dword ptr [esp + 0x10]
0x004e88d5  25ffff0000         and      eax, 0xffff
0x004e88da  83e800             sub      eax, 0
0x004e88dd  7462               je       0x4e8941
0x004e88df  48                 dec      eax
0x004e88e0  0f85b0000000       jne      0x4e8996
0x004e88e6  c64612ff           mov      byte ptr [esi + 0x12], 0xff
0x004e88ea  a003065200         mov      al, byte ptr [0x520603]
0x004e88ef  2c38               sub      al, 0x38
0x004e88f1  884613             mov      byte ptr [esi + 0x13], al
0x004e88f4  a108e15100         mov      eax, dword ptr [0x51e108]
0x004e88f9  668b0d0ae15100     mov      cx, word ptr [0x51e10a]
0x004e8900  884614             mov      byte ptr [esi + 0x14], al
0x004e8903  884e15             mov      byte ptr [esi + 0x15], cl
0x004e8906  a003065200         mov      al, byte ptr [0x520603]
0x004e890b  3c31               cmp      al, 0x31
0x004e890d  88442410           mov      byte ptr [esp + 0x10], al
0x004e8911  7312               jae      0x4e8925
0x004e8913  8b442410           mov      eax, dword ptr [esp + 0x10]
0x004e8917  25ff000000         and      eax, 0xff
0x004e891c  8d8c8048955100     lea      ecx, [eax + eax*4 + 0x519548]
0x004e8923  eb02               jmp      0x4e8927
0x004e8925  33c9               xor      ecx, ecx
0x004e8927  e8142bfbff         call     0x49b440
0x004e892c  8d4c241c           lea      ecx, [esp + 0x1c]
0x004e8930  50                 push     eax
0x004e8931  51                 push     ecx
0x004e8932  e8a9360000         call     0x4ebfe0
0x004e8937  83c408             add      esp, 8
0x004e893a  68bcd85000         push     0x50d8bc
0x004e893f  eb48               jmp      0x4e8989
0x004e8941  6a00               push     0
0x004e8943  e8e856faff         call     0x48e030
0x004e8948  66a166485200       mov      ax, word ptr [0x524866]
0x004e894e  83c404             add      esp, 4
0x004e8951  6689442410         mov      word ptr [esp + 0x10], ax
0x004e8956  807c241031         cmp      byte ptr [esp + 0x10], 0x31
0x004e895b  7312               jae      0x4e896f
0x004e895d  8b442410           mov      eax, dword ptr [esp + 0x10]
0x004e8961  25ff000000         and      eax, 0xff
0x004e8966  8d8c8048955100     lea      ecx, [eax + eax*4 + 0x519548]
0x004e896d  eb02               jmp      0x4e8971
0x004e896f  33c9               xor      ecx, ecx
0x004e8971  e88a2afbff         call     0x49b400
0x004e8976  8d4c241c           lea      ecx, [esp + 0x1c]
0x004e897a  50                 push     eax
0x004e897b  51                 push     ecx
0x004e897c  e85f360000         call     0x4ebfe0
0x004e8981  83c408             add      esp, 8
0x004e8984  68b8d85000         push     0x50d8b8
0x004e8989  8d542420           lea      edx, [esp + 0x20]
0x004e898d  52                 push     edx
0x004e898e  e87d360000         call     0x4ec010
0x004e8993  83c408             add      esp, 8
0x004e8996  8d44242c           lea      eax, [esp + 0x2c]
0x004e899a  56                 push     esi
0x004e899b  50                 push     eax
0x004e899c  e8af67fbff         call     0x49f150
0x004e89a1  a128065200         mov      eax, dword ptr [0x520628]
0x004e89a6  83c408             add      esp, 8
0x004e89a9  85c0               test     eax, eax
0x004e89ab  7405               je       0x4e89b2
0x004e89ad  e8ae78f9ff         call     0x480260
0x004e89b2  8b742418           mov      esi, dword ptr [esp + 0x18]
0x004e89b6  8d4c243c           lea      ecx, [esp + 0x3c]
0x004e89ba  8d54241c           lea      edx, [esp + 0x1c]
0x004e89be  51                 push     ecx
0x004e89bf  8b4c2418           mov      ecx, dword ptr [esp + 0x18]
0x004e89c3  8d442430           lea      eax, [esp + 0x30]
0x004e89c7  52                 push     edx
0x004e89c8  50                 push     eax
0x004e89c9  51                 push     ecx
0x004e89ca  55                 push     ebp
0x004e89cb  53                 push     ebx
0x004e89cc  56                 push     esi
0x004e89cd  e83e73f9ff         call     0x47fd10
0x004e89d2  83c41c             add      esp, 0x1c
0x004e89d5  85c0               test     eax, eax
0x004e89d7  7416               je       0x4e89ef
0x004e89d9  56                 push     esi
0x004e89da  e83172f9ff         call     0x47fc10
0x004e89df  83c404             add      esp, 4
0x004e89e2  68acd85000         push     0x50d8ac
0x004e89e7  e87428f9ff         call     0x47b260
0x004e89ec  83c404             add      esp, 4
0x004e89ef  5f                 pop      edi
0x004e89f0  5e                 pop      esi
0x004e89f1  5d                 pop      ebp
0x004e89f2  5b                 pop      ebx
0x004e89f3  83c440             add      esp, 0x40
0x004e89f6  c3                 ret      
0x004e89f7  90                 nop      
0x004e89f8  90                 nop      
0x004e89f9  90                 nop      
0x004e89fa  90                 nop      
0x004e89fb  90                 nop      
0x004e89fc  90                 nop      
0x004e89fd  90                 nop      
0x004e89fe  90                 nop      
0x004e89ff  90                 nop      