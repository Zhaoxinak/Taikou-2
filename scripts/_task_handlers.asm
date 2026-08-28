

########## handler[0]  0x45e700  (144 B) ##########
0x45e700  8b442404             mov      eax, dword ptr [esp + 4]
0x45e704  663d1e00             cmp      ax, 0x1e
0x45e708  7318                 jae      0x45e722
0x45e70a  25ffff0000           and      eax, 0xffff
0x45e70f  6a00                 push     0
0x45e711  8d0485a8765100       lea      eax, [eax*4 + 0x5176a8]
0x45e718  50                   push     eax
0x45e719  e83230feff           call     0x441750   ; call
0x45e71e  83c408               add      esp, 8
0x45e721  c3                   ret      
0x45e722  33c0                 xor      eax, eax
0x45e724  50                   push     eax
0x45e725  50                   push     eax
0x45e726  e82530feff           call     0x441750   ; call
0x45e72b  83c408               add      esp, 8
0x45e72e  c3                   ret      
0x45e72f  90                   nop      
0x45e730  53                   push     ebx
0x45e731  55                   push     ebp
0x45e732  56                   push     esi
0x45e733  57                   push     edi
0x45e734  33ff                 xor      edi, edi
0x45e736  be88eb5100           mov      esi, 0x51eb88
0x45e73b  bbc8000000           mov      ebx, 0xc8
0x45e740  bdffff0000           mov      ebp, 0xffff
0x45e745  66396e0a             cmp      word ptr [esi + 0xa], bp
0x45e749  7422                 je       0x45e76d
0x45e74b  56                   push     esi
0x45e74c  e8df0c0400           call     0x49f430   ; call
0x45e751  660fb6c0             movzx    ax, al
0x45e755  83c404               add      esp, 4
0x45e758  663b442414           cmp      ax, word ptr [esp + 0x14]
0x45e75d  750e                 jne      0x45e76d
0x45e75f  8b1580855100         mov      edx, dword ptr [0x518580]
0x45e765  8bcf                 mov      ecx, edi
0x45e767  23cd                 and      ecx, ebp
0x45e769  47                   inc      edi
0x45e76a  89348a               mov      dword ptr [edx + ecx*4], esi
0x45e76d  83c61f               add      esi, 0x1f
0x45e770  4b                   dec      ebx
0x45e771  75d2                 jne      0x45e745
0x45e773  57                   push     edi
0x45e774  e8e7d50800           call     0x4ebd60   ; call
0x45e779  8b0d80855100         mov      ecx, dword ptr [0x518580]
0x45e77f  83c404               add      esp, 4
0x45e782  23c5                 and      eax, ebp
0x45e784  5f                   pop      edi
0x45e785  5e                   pop      esi
0x45e786  8b0481               mov      eax, dword ptr [ecx + eax*4]
0x45e789  5d                   pop      ebp
0x45e78a  5b                   pop      ebx
0x45e78b  c3                   ret      
0x45e78c  90                   nop      
0x45e78d  90                   nop      
0x45e78e  90                   nop      
0x45e78f  90                   nop      


########## handler[1]  0x45e790  (224 B) ##########
0x45e790  51                   push     ecx
0x45e791  56                   push     esi
0x45e792  57                   push     edi
0x45e793  e8180f0400           call     0x49f6b0   ; call
0x45e798  66833809             cmp      word ptr [eax], 9
0x45e79c  668b7008             mov      si, word ptr [eax + 8]
0x45e7a0  751c                 jne      0x45e7be
0x45e7a2  6a03                 push     3
0x45e7a4  e8b7d50800           call     0x4ebd60   ; call
0x45e7a9  83c404               add      esp, 4
0x45e7ac  6685c0               test     ax, ax
0x45e7af  750d                 jne      0x45e7be
0x45e7b1  56                   push     esi
0x45e7b2  e879ffffff           call     0x45e730   ; call
0x45e7b7  83c404               add      esp, 4
0x45e7ba  8bf0                 mov      esi, eax
0x45e7bc  eb2f                 jmp      0x45e7ed
0x45e7be  68c8000000           push     0xc8
0x45e7c3  e898d50800           call     0x4ebd60   ; call
0x45e7c8  83c404               add      esp, 4
0x45e7cb  3cc8                 cmp      al, 0xc8
0x45e7cd  88442408             mov      byte ptr [esp + 8], al
0x45e7d1  7318                 jae      0x45e7eb
0x45e7d3  8b442408             mov      eax, dword ptr [esp + 8]
0x45e7d7  25ff000000           and      eax, 0xff
0x45e7dc  8bf0                 mov      esi, eax
0x45e7de  c1e605               shl      esi, 5
0x45e7e1  2bf0                 sub      esi, eax
0x45e7e3  81c688eb5100         add      esi, 0x51eb88
0x45e7e9  eb02                 jmp      0x45e7ed
0x45e7eb  33f6                 xor      esi, esi
0x45e7ed  8b442410             mov      eax, dword ptr [esp + 0x10]
0x45e7f1  663d1e00             cmp      ax, 0x1e
0x45e7f5  730e                 jae      0x45e805
0x45e7f7  25ffff0000           and      eax, 0xffff
0x45e7fc  8d3c85a8765100       lea      edi, [eax*4 + 0x5176a8]
0x45e803  eb02                 jmp      0x45e807
0x45e805  33ff                 xor      edi, edi
0x45e807  8bce                 mov      ecx, esi
0x45e809  e832c90300           call     0x49b140   ; call
0x45e80e  50                   push     eax
0x45e80f  6802120000           push     0x1202
0x45e814  57                   push     edi
0x45e815  e8e6d00100           call     0x47b900   ; call
0x45e81a  83c40c               add      esp, 0xc
0x45e81d  85f6                 test     esi, esi
0x45e81f  7518                 jne      0x45e839
0x45e821  bac8000000           mov      edx, 0xc8
0x45e826  6633c9               xor      cx, cx
0x45e829  8aca                 mov      cl, dl
0x45e82b  56                   push     esi
0x45e82c  51                   push     ecx
0x45e82d  e82e1a0100           call     0x470260   ; call
0x45e832  83c408               add      esp, 8
0x45e835  5f                   pop      edi
0x45e836  5e                   pop      esi
0x45e837  59                   pop      ecx
0x45e838  c3                   ret      
0x45e839  81ee88eb5100         sub      esi, 0x51eb88
0x45e83f  b843082184           mov      eax, 0x84210843
0x45e844  f7ee                 imul     esi
0x45e846  03d6                 add      edx, esi
0x45e848  6633c9               xor      cx, cx
0x45e84b  c1fa04               sar      edx, 4
0x45e84e  8bc2                 mov      eax, edx
0x45e850  6a00                 push     0
0x45e852  c1e81f               shr      eax, 0x1f
0x45e855  03d0                 add      edx, eax
0x45e857  8aca                 mov      cl, dl
0x45e859  51                   push     ecx
0x45e85a  e8011a0100           call     0x470260   ; call
0x45e85f  83c408               add      esp, 8
0x45e862  5f                   pop      edi
0x45e863  5e                   pop      esi
0x45e864  59                   pop      ecx
0x45e865  c3                   ret      
0x45e866  90                   nop      
0x45e867  90                   nop      
0x45e868  90                   nop      
0x45e869  90                   nop      
0x45e86a  90                   nop      
0x45e86b  90                   nop      
0x45e86c  90                   nop      
0x45e86d  90                   nop      
0x45e86e  90                   nop      
0x45e86f  90                   nop      


########## handler[2]  0x45e870  (112 B) ##########
0x45e870  53                   push     ebx
0x45e871  56                   push     esi
0x45e872  57                   push     edi
0x45e873  e858feffff           call     0x45e6d0   ; call
0x45e878  8bf0                 mov      esi, eax
0x45e87a  56                   push     esi
0x45e87b  e8200d0400           call     0x49f5a0   ; call
0x45e880  8bf8                 mov      edi, eax
0x45e882  8b442414             mov      eax, dword ptr [esp + 0x14]
0x45e886  83c404               add      esp, 4
0x45e889  663d1e00             cmp      ax, 0x1e
0x45e88d  730e                 jae      0x45e89d
0x45e88f  25ffff0000           and      eax, 0xffff
0x45e894  8d1c85a8765100       lea      ebx, [eax*4 + 0x5176a8]
0x45e89b  eb02                 jmp      0x45e89f
0x45e89d  33db                 xor      ebx, ebx
0x45e89f  8bce                 mov      ecx, esi
0x45e8a1  e8aacc0300           call     0x49b550   ; call
0x45e8a6  660fb6c0             movzx    ax, al
0x45e8aa  50                   push     eax
0x45e8ab  e850bc0100           call     0x47a500   ; call
0x45e8b0  83c404               add      esp, 4
0x45e8b3  50                   push     eax
0x45e8b4  57                   push     edi
0x45e8b5  e866f6feff           call     0x44df20   ; call
0x45e8ba  83c404               add      esp, 4
0x45e8bd  50                   push     eax
0x45e8be  6803120000           push     0x1203
0x45e8c3  53                   push     ebx
0x45e8c4  e837d00100           call     0x47b900   ; call
0x45e8c9  83c410               add      esp, 0x10
0x45e8cc  6a01                 push     1
0x45e8ce  57                   push     edi
0x45e8cf  e82c3a0000           call     0x462300   ; call
0x45e8d4  83c408               add      esp, 8
0x45e8d7  5f                   pop      edi
0x45e8d8  5e                   pop      esi
0x45e8d9  5b                   pop      ebx
0x45e8da  c3                   ret      
0x45e8db  90                   nop      
0x45e8dc  90                   nop      
0x45e8dd  90                   nop      
0x45e8de  90                   nop      
0x45e8df  90                   nop      


########## handler[3]  0x45e8e0  (144 B) ##########
0x45e8e0  56                   push     esi
0x45e8e1  57                   push     edi
0x45e8e2  6a03                 push     3
0x45e8e4  6a01                 push     1
0x45e8e6  e8f5faffff           call     0x45e3e0   ; call
0x45e8eb  83c408               add      esp, 8
0x45e8ee  50                   push     eax
0x45e8ef  e86cd40800           call     0x4ebd60   ; call
0x45e8f4  8b0dc0e95100         mov      ecx, dword ptr [0x51e9c0]
0x45e8fa  25ffff0000           and      eax, 0xffff
0x45e8ff  83c404               add      esp, 4
0x45e902  8b3481               mov      esi, dword ptr [ecx + eax*4]
0x45e905  8b44240c             mov      eax, dword ptr [esp + 0xc]
0x45e909  663d1e00             cmp      ax, 0x1e
0x45e90d  730e                 jae      0x45e91d
0x45e90f  25ffff0000           and      eax, 0xffff
0x45e914  8d3c85a8765100       lea      edi, [eax*4 + 0x5176a8]
0x45e91b  eb02                 jmp      0x45e91f
0x45e91d  33ff                 xor      edi, edi
0x45e91f  a1d03f5100           mov      eax, dword ptr [0x513fd0]
0x45e924  25ff000000           and      eax, 0xff
0x45e929  8bd0                 mov      edx, eax
0x45e92b  c1e203               shl      edx, 3
0x45e92e  2bd0                 sub      edx, eax
0x45e930  81c2c07f5000         add      edx, 0x507fc0
0x45e936  52                   push     edx
0x45e937  56                   push     esi
0x45e938  e8e3f5feff           call     0x44df20   ; call
0x45e93d  83c404               add      esp, 4
0x45e940  50                   push     eax
0x45e941  56                   push     esi
0x45e942  e8b9fafeff           call     0x44e400   ; call
0x45e947  83c404               add      esp, 4
0x45e94a  50                   push     eax
0x45e94b  6804120000           push     0x1204
0x45e950  57                   push     edi
0x45e951  e8aacf0100           call     0x47b900   ; call
0x45e956  83c414               add      esp, 0x14
0x45e959  56                   push     esi
0x45e95a  e8c1e8feff           call     0x44d220   ; call
0x45e95f  83c404               add      esp, 4
0x45e962  5f                   pop      edi
0x45e963  5e                   pop      esi
0x45e964  c3                   ret      
0x45e965  90                   nop      
0x45e966  90                   nop      
0x45e967  90                   nop      
0x45e968  90                   nop      
0x45e969  90                   nop      
0x45e96a  90                   nop      
0x45e96b  90                   nop      
0x45e96c  90                   nop      
0x45e96d  90                   nop      
0x45e96e  90                   nop      
0x45e96f  90                   nop      


########## handler[4]  0x45e970  (128 B) ##########
0x45e970  56                   push     esi
0x45e971  57                   push     edi
0x45e972  6a04                 push     4
0x45e974  6a01                 push     1
0x45e976  e865faffff           call     0x45e3e0   ; call
0x45e97b  83c408               add      esp, 8
0x45e97e  50                   push     eax
0x45e97f  e8dcd30800           call     0x4ebd60   ; call
0x45e984  8b0dc0e95100         mov      ecx, dword ptr [0x51e9c0]
0x45e98a  25ffff0000           and      eax, 0xffff
0x45e98f  83c404               add      esp, 4
0x45e992  8b3481               mov      esi, dword ptr [ecx + eax*4]
0x45e995  8b44240c             mov      eax, dword ptr [esp + 0xc]
0x45e999  663d1e00             cmp      ax, 0x1e
0x45e99d  730e                 jae      0x45e9ad
0x45e99f  25ffff0000           and      eax, 0xffff
0x45e9a4  8d3c85a8765100       lea      edi, [eax*4 + 0x5176a8]
0x45e9ab  eb02                 jmp      0x45e9af
0x45e9ad  33ff                 xor      edi, edi
0x45e9af  a1c83f5100           mov      eax, dword ptr [0x513fc8]
0x45e9b4  25ff000000           and      eax, 0xff
0x45e9b9  8d9480587b5000       lea      edx, [eax + eax*4 + 0x507b58]
0x45e9c0  52                   push     edx
0x45e9c1  56                   push     esi
0x45e9c2  e859f5feff           call     0x44df20   ; call
0x45e9c7  83c404               add      esp, 4
0x45e9ca  50                   push     eax
0x45e9cb  56                   push     esi
0x45e9cc  e82ffafeff           call     0x44e400   ; call
0x45e9d1  83c404               add      esp, 4
0x45e9d4  50                   push     eax
0x45e9d5  6805120000           push     0x1205
0x45e9da  57                   push     edi
0x45e9db  e820cf0100           call     0x47b900   ; call
0x45e9e0  83c414               add      esp, 0x14
0x45e9e3  56                   push     esi
0x45e9e4  e837e8feff           call     0x44d220   ; call
0x45e9e9  83c404               add      esp, 4
0x45e9ec  5f                   pop      edi
0x45e9ed  5e                   pop      esi
0x45e9ee  c3                   ret      
0x45e9ef  90                   nop      


########## handler[5]  0x45e9f0  (160 B) ##########
0x45e9f0  53                   push     ebx
0x45e9f1  55                   push     ebp
0x45e9f2  56                   push     esi
0x45e9f3  57                   push     edi
0x45e9f4  6a05                 push     5
0x45e9f6  6a01                 push     1
0x45e9f8  e8e3f9ffff           call     0x45e3e0   ; call
0x45e9fd  83c408               add      esp, 8
0x45ea00  50                   push     eax
0x45ea01  e85ad30800           call     0x4ebd60   ; call
0x45ea06  8b0dc0e95100         mov      ecx, dword ptr [0x51e9c0]
0x45ea0c  25ffff0000           and      eax, 0xffff
0x45ea11  83c404               add      esp, 4
0x45ea14  8b3481               mov      esi, dword ptr [ecx + eax*4]
0x45ea17  56                   push     esi
0x45ea18  e8f3fafeff           call     0x44e510   ; call
0x45ea1d  83c404               add      esp, 4
0x45ea20  8be8                 mov      ebp, eax
0x45ea22  e8b90b0400           call     0x49f5e0   ; call
0x45ea27  8bf8                 mov      edi, eax
0x45ea29  8b442414             mov      eax, dword ptr [esp + 0x14]
0x45ea2d  663d1e00             cmp      ax, 0x1e
0x45ea31  730e                 jae      0x45ea41
0x45ea33  25ffff0000           and      eax, 0xffff
0x45ea38  8d1c85a8765100       lea      ebx, [eax*4 + 0x5176a8]
0x45ea3f  eb02                 jmp      0x45ea43
0x45ea41  33db                 xor      ebx, ebx
0x45ea43  56                   push     esi
0x45ea44  e8d7f4feff           call     0x44df20   ; call
0x45ea49  83c404               add      esp, 4
0x45ea4c  50                   push     eax
0x45ea4d  55                   push     ebp
0x45ea4e  e8edf4feff           call     0x44df40   ; call
0x45ea53  83c404               add      esp, 4
0x45ea56  50                   push     eax
0x45ea57  6806120000           push     0x1206
0x45ea5c  53                   push     ebx
0x45ea5d  e89ece0100           call     0x47b900   ; call
0x45ea62  83c410               add      esp, 0x10
0x45ea65  56                   push     esi
0x45ea66  e8b5e7feff           call     0x44d220   ; call
0x45ea6b  83c404               add      esp, 4
0x45ea6e  3bf7                 cmp      esi, edi
0x45ea70  750e                 jne      0x45ea80
0x45ea72  680d120000           push     0x120d
0x45ea77  57                   push     edi
0x45ea78  e883ce0100           call     0x47b900   ; call
0x45ea7d  83c408               add      esp, 8
0x45ea80  5f                   pop      edi
0x45ea81  5e                   pop      esi
0x45ea82  5d                   pop      ebp
0x45ea83  5b                   pop      ebx
0x45ea84  c3                   ret      
0x45ea85  90                   nop      
0x45ea86  90                   nop      
0x45ea87  90                   nop      
0x45ea88  90                   nop      
0x45ea89  90                   nop      
0x45ea8a  90                   nop      
0x45ea8b  90                   nop      
0x45ea8c  90                   nop      
0x45ea8d  90                   nop      
0x45ea8e  90                   nop      
0x45ea8f  90                   nop      


########## handler[6]  0x45ea90  (240 B) ##########
0x45ea90  51                   push     ecx
0x45ea91  53                   push     ebx
0x45ea92  56                   push     esi
0x45ea93  57                   push     edi
0x45ea94  6a01                 push     1
0x45ea96  e895000000           call     0x45eb30   ; call
0x45ea9b  83c404               add      esp, 4
0x45ea9e  50                   push     eax
0x45ea9f  e8bcd20800           call     0x4ebd60   ; call
0x45eaa4  8b0d80eb5100         mov      ecx, dword ptr [0x51eb80]
0x45eaaa  25ffff0000           and      eax, 0xffff
0x45eaaf  83c404               add      esp, 4
0x45eab2  8b3c81               mov      edi, dword ptr [ecx + eax*4]
0x45eab5  8a4705               mov      al, byte ptr [edi + 5]
0x45eab8  3c31                 cmp      al, 0x31
0x45eaba  8844240c             mov      byte ptr [esp + 0xc], al
0x45eabe  7312                 jae      0x45ead2
0x45eac0  8b44240c             mov      eax, dword ptr [esp + 0xc]
0x45eac4  25ff000000           and      eax, 0xff
0x45eac9  8d8c8048955100       lea      ecx, [eax + eax*4 + 0x519548]
0x45ead0  eb02                 jmp      0x45ead4
0x45ead2  33c9                 xor      ecx, ecx
0x45ead4  8b442414             mov      eax, dword ptr [esp + 0x14]
0x45ead8  33d2                 xor      edx, edx
0x45eada  8a5704               mov      dl, byte ptr [edi + 4]
0x45eadd  663d1e00             cmp      ax, 0x1e
0x45eae1  8bf2                 mov      esi, edx
0x45eae3  730e                 jae      0x45eaf3
0x45eae5  25ffff0000           and      eax, 0xffff
0x45eaea  8d1c85a8765100       lea      ebx, [eax*4 + 0x5176a8]
0x45eaf1  eb02                 jmp      0x45eaf5
0x45eaf3  33db                 xor      ebx, ebx
0x45eaf5  e846c90300           call     0x49b440   ; call
0x45eafa  50                   push     eax
0x45eafb  8d04b6               lea      eax, [esi + esi*4]
0x45eafe  8d8c46f0765000       lea      ecx, [esi + eax*2 + 0x5076f0]
0x45eb05  51                   push     ecx
0x45eb06  57                   push     edi
0x45eb07  e814f4feff           call     0x44df20   ; call
0x45eb0c  83c404               add      esp, 4
0x45eb0f  50                   push     eax
0x45eb10  6807120000           push     0x1207
0x45eb15  53                   push     ebx
0x45eb16  e8e5cd0100           call     0x47b900   ; call
0x45eb1b  83c414               add      esp, 0x14
0x45eb1e  5f                   pop      edi
0x45eb1f  5e                   pop      esi
0x45eb20  5b                   pop      ebx
0x45eb21  59                   pop      ecx
0x45eb22  c3                   ret      
0x45eb23  90                   nop      
0x45eb24  90                   nop      
0x45eb25  90                   nop      
0x45eb26  90                   nop      
0x45eb27  90                   nop      
0x45eb28  90                   nop      
0x45eb29  90                   nop      
0x45eb2a  90                   nop      
0x45eb2b  90                   nop      
0x45eb2c  90                   nop      
0x45eb2d  90                   nop      
0x45eb2e  90                   nop      
0x45eb2f  90                   nop      
0x45eb30  53                   push     ebx
0x45eb31  55                   push     ebp
0x45eb32  56                   push     esi
0x45eb33  8b742410             mov      esi, dword ptr [esp + 0x10]
0x45eb37  33c0                 xor      eax, eax
0x45eb39  57                   push     edi
0x45eb3a  33d2                 xor      edx, edx
0x45eb3c  b954785100           mov      ecx, 0x517854
0x45eb41  8079030a             cmp      byte ptr [ecx + 3], 0xa
0x45eb45  731f                 jae      0x45eb66
0x45eb47  80390b               cmp      byte ptr [ecx], 0xb
0x45eb4a  741a                 je       0x45eb66
0x45eb4c  8b2d80eb5100         mov      ebp, dword ptr [0x51eb80]
0x45eb52  8bd8                 mov      ebx, eax
0x45eb54  81e3ffff0000         and      ebx, 0xffff
0x45eb5a  8d79fc               lea      edi, [ecx - 4]
0x45eb5d  40                   inc      eax
0x45eb5e  85f6                 test     esi, esi
0x45eb60  897c9d00             mov      dword ptr [ebp + ebx*4], edi
0x45eb64  740a                 je       0x45eb70
0x45eb66  42                   inc      edx
0x45eb67  83c10c               add      ecx, 0xc
0x45eb6a  6683fa1e             cmp      dx, 0x1e
0x45eb6e  72d1                 jb       0x45eb41
0x45eb70  5f                   pop      edi
0x45eb71  5e                   pop      esi
0x45eb72  5d                   pop      ebp
0x45eb73  5b                   pop      ebx
0x45eb74  c3                   ret      
0x45eb75  90                   nop      
0x45eb76  90                   nop      
0x45eb77  90                   nop      
0x45eb78  90                   nop      
0x45eb79  90                   nop      
0x45eb7a  90                   nop      
0x45eb7b  90                   nop      
0x45eb7c  90                   nop      
0x45eb7d  90                   nop      
0x45eb7e  90                   nop      
0x45eb7f  90                   nop      


########## handler[7]  0x45eb80  (144 B) ##########
0x45eb80  51                   push     ecx
0x45eb81  56                   push     esi
0x45eb82  57                   push     edi
0x45eb83  6a07                 push     7
0x45eb85  6a01                 push     1
0x45eb87  e854f8ffff           call     0x45e3e0   ; call
0x45eb8c  83c408               add      esp, 8
0x45eb8f  50                   push     eax
0x45eb90  e8cbd10800           call     0x4ebd60   ; call
0x45eb95  8b0dc0e95100         mov      ecx, dword ptr [0x51e9c0]
0x45eb9b  25ffff0000           and      eax, 0xffff
0x45eba0  83c404               add      esp, 4
0x45eba3  8b3481               mov      esi, dword ptr [ecx + eax*4]
0x45eba6  8a4625               mov      al, byte ptr [esi + 0x25]
0x45eba9  3c31                 cmp      al, 0x31
0x45ebab  88442408             mov      byte ptr [esp + 8], al
0x45ebaf  7312                 jae      0x45ebc3
0x45ebb1  8b442408             mov      eax, dword ptr [esp + 8]
0x45ebb5  25ff000000           and      eax, 0xff
0x45ebba  8d8c8048955100       lea      ecx, [eax + eax*4 + 0x519548]
0x45ebc1  eb02                 jmp      0x45ebc5
0x45ebc3  33c9                 xor      ecx, ecx
0x45ebc5  8b442410             mov      eax, dword ptr [esp + 0x10]
0x45ebc9  663d1e00             cmp      ax, 0x1e
0x45ebcd  730e                 jae      0x45ebdd
0x45ebcf  25ffff0000           and      eax, 0xffff
0x45ebd4  8d3c85a8765100       lea      edi, [eax*4 + 0x5176a8]
0x45ebdb  eb02                 jmp      0x45ebdf
0x45ebdd  33ff                 xor      edi, edi
0x45ebdf  e85cc80300           call     0x49b440   ; call
0x45ebe4  50                   push     eax
0x45ebe5  56                   push     esi
0x45ebe6  e835f3feff           call     0x44df20   ; call
0x45ebeb  83c404               add      esp, 4
0x45ebee  50                   push     eax
0x45ebef  6808120000           push     0x1208
0x45ebf4  57                   push     edi
0x45ebf5  e806cd0100           call     0x47b900   ; call
0x45ebfa  83c410               add      esp, 0x10
0x45ebfd  56                   push     esi
0x45ebfe  e81de6feff           call     0x44d220   ; call
0x45ec03  83c404               add      esp, 4
0x45ec06  5f                   pop      edi
0x45ec07  5e                   pop      esi
0x45ec08  59                   pop      ecx
0x45ec09  c3                   ret      
0x45ec0a  90                   nop      
0x45ec0b  90                   nop      
0x45ec0c  90                   nop      
0x45ec0d  90                   nop      
0x45ec0e  90                   nop      
0x45ec0f  90                   nop      


########## handler[8]  0x45ec10  (368 B) ##########
0x45ec10  53                   push     ebx
0x45ec11  56                   push     esi
0x45ec12  57                   push     edi
0x45ec13  6a01                 push     1
0x45ec15  e8a6000000           call     0x45ecc0   ; call
0x45ec1a  83c404               add      esp, 4
0x45ec1d  50                   push     eax
0x45ec1e  e83dd10800           call     0x4ebd60   ; call
0x45ec23  8b0d38785100         mov      ecx, dword ptr [0x517838]
0x45ec29  25ffff0000           and      eax, 0xffff
0x45ec2e  83c404               add      esp, 4
0x45ec31  8b3481               mov      esi, dword ptr [ecx + eax*4]
0x45ec34  668b4606             mov      ax, word ptr [esi + 6]
0x45ec38  3c1e                 cmp      al, 0x1e
0x45ec3a  7311                 jae      0x45ec4d
0x45ec3c  25ff000000           and      eax, 0xff
0x45ec41  8d1440               lea      edx, [eax + eax*2]
0x45ec44  8d1c9550785100       lea      ebx, [edx*4 + 0x517850]
0x45ec4b  eb02                 jmp      0x45ec4f
0x45ec4d  33db                 xor      ebx, ebx
0x45ec4f  8b442410             mov      eax, dword ptr [esp + 0x10]
0x45ec53  663d1e00             cmp      ax, 0x1e
0x45ec57  730e                 jae      0x45ec67
0x45ec59  25ffff0000           and      eax, 0xffff
0x45ec5e  8d3c85a8765100       lea      edi, [eax*4 + 0x5176a8]
0x45ec65  eb02                 jmp      0x45ec69
0x45ec67  33ff                 xor      edi, edi
0x45ec69  8b06                 mov      eax, dword ptr [esi]
0x45ec6b  8bce                 mov      ecx, esi
0x45ec6d  ff5004               call     dword ptr [eax + 4]
0x45ec70  8b16                 mov      edx, dword ptr [esi]
0x45ec72  50                   push     eax
0x45ec73  8bce                 mov      ecx, esi
0x45ec75  ff5208               call     dword ptr [edx + 8]
0x45ec78  50                   push     eax
0x45ec79  53                   push     ebx
0x45ec7a  e8a1f2feff           call     0x44df20   ; call
0x45ec7f  83c404               add      esp, 4
0x45ec82  50                   push     eax
0x45ec83  6809120000           push     0x1209
0x45ec88  57                   push     edi
0x45ec89  e872cc0100           call     0x47b900   ; call
0x45ec8e  8a4608               mov      al, byte ptr [esi + 8]
0x45ec91  83c414               add      esp, 0x14
0x45ec94  c1e807               shr      eax, 7
0x45ec97  83e001               and      eax, 1
0x45ec9a  8bf8                 mov      edi, eax
0x45ec9c  7509                 jne      0x45eca7
0x45ec9e  6a01                 push     1
0x45eca0  8bce                 mov      ecx, esi
0x45eca2  e849d30300           call     0x49bff0   ; call
0x45eca7  56                   push     esi
0x45eca8  e803eafeff           call     0x44d6b0   ; call
0x45ecad  83c404               add      esp, 4
0x45ecb0  85ff                 test     edi, edi
0x45ecb2  7508                 jne      0x45ecbc
0x45ecb4  57                   push     edi
0x45ecb5  8bce                 mov      ecx, esi
0x45ecb7  e834d30300           call     0x49bff0   ; call
0x45ecbc  5f                   pop      edi
0x45ecbd  5e                   pop      esi
0x45ecbe  5b                   pop      ebx
0x45ecbf  c3                   ret      
0x45ecc0  53                   push     ebx
0x45ecc1  55                   push     ebp
0x45ecc2  8b6c240c             mov      ebp, dword ptr [esp + 0xc]
0x45ecc6  56                   push     esi
0x45ecc7  57                   push     edi
0x45ecc8  33c0                 xor      eax, eax
0x45ecca  33ff                 xor      edi, edi
0x45eccc  bef6e15100           mov      esi, 0x51e1f6
0x45ecd1  668b0e               mov      cx, word ptr [esi]
0x45ecd4  6681f9ffff           cmp      cx, 0xffff
0x45ecd9  0f848b000000         je       0x45ed6a
0x45ecdf  f6c580               test     ch, 0x80
0x45ece2  0f8482000000         je       0x45ed6a
0x45ece8  81e1ff7f0000         and      ecx, 0x7fff
0x45ecee  80f91e               cmp      cl, 0x1e
0x45ecf1  7314                 jae      0x45ed07
0x45ecf3  8bd1                 mov      edx, ecx
0x45ecf5  81e2ff000000         and      edx, 0xff
0x45ecfb  8d1452               lea      edx, [edx + edx*2]
0x45ecfe  8d149550785100       lea      edx, [edx*4 + 0x517850]
0x45ed05  eb02                 jmp      0x45ed09
0x45ed07  33d2                 xor      edx, edx
0x45ed09  85d2                 test     edx, edx
0x45ed0b  745d                 je       0x45ed6a
0x45ed0d  80f91e               cmp      cl, 0x1e
0x45ed10  7312                 jae      0x45ed24
0x45ed12  81e1ff000000         and      ecx, 0xff
0x45ed18  8d0c49               lea      ecx, [ecx + ecx*2]
0x45ed1b  8d0c8d50785100       lea      ecx, [ecx*4 + 0x517850]
0x45ed22  eb02                 jmp      0x45ed26
0x45ed24  33c9                 xor      ecx, ecx
0x45ed26  33d2                 xor      edx, edx
0x45ed28  8a5104               mov      dl, byte ptr [ecx + 4]
0x45ed2b  8bca                 mov      ecx, edx
0x45ed2d  85c9                 test     ecx, ecx
0x45ed2f  7415                 je       0x45ed46
0x45ed31  83f903               cmp      ecx, 3
0x45ed34  7410                 je       0x45ed46
0x45ed36  83f901               cmp      ecx, 1
0x45ed39  752f                 jne      0x45ed6a
0x45ed3b  8a4e02               mov      cl, byte ptr [esi + 2]
0x45ed3e  80e107               and      cl, 7
0x45ed41  80f907               cmp      cl, 7
0x45ed44  7524                 jne      0x45ed6a
0x45ed46  8a5602               mov      dl, byte ptr [esi + 2]
0x45ed49  80e278               and      dl, 0x78
0x45ed4c  80fa40               cmp      dl, 0x40
0x45ed4f  7219                 jb       0x45ed6a
0x45ed51  8b1d38785100         mov      ebx, dword ptr [0x517838]
0x45ed57  8bd0                 mov      edx, eax
0x45ed59  81e2ffff0000         and      edx, 0xffff
0x45ed5f  8d4efa               lea      ecx, [esi - 6]
0x45ed62  40                   inc      eax
0x45ed63  85ed                 test     ebp, ebp
0x45ed65  890c93               mov      dword ptr [ebx + edx*4], ecx
0x45ed68  740f                 je       0x45ed79
0x45ed6a  47                   inc      edi
0x45ed6b  83c60a               add      esi, 0xa
0x45ed6e  6681ffc800           cmp      di, 0xc8
0x45ed73  0f8258ffffff         jb       0x45ecd1
0x45ed79  5f                   pop      edi
0x45ed7a  5e                   pop      esi
0x45ed7b  5d                   pop      ebp
0x45ed7c  5b                   pop      ebx
0x45ed7d  c3                   ret      
0x45ed7e  90                   nop      
0x45ed7f  90                   nop      


########## handler[9]  0x45ed80  (112 B) ##########
0x45ed80  56                   push     esi
0x45ed81  57                   push     edi
0x45ed82  6a09                 push     9
0x45ed84  6a01                 push     1
0x45ed86  e855f6ffff           call     0x45e3e0   ; call
0x45ed8b  83c408               add      esp, 8
0x45ed8e  50                   push     eax
0x45ed8f  e8cccf0800           call     0x4ebd60   ; call
0x45ed94  8b0dc0e95100         mov      ecx, dword ptr [0x51e9c0]
0x45ed9a  25ffff0000           and      eax, 0xffff
0x45ed9f  83c404               add      esp, 4
0x45eda2  8b3c81               mov      edi, dword ptr [ecx + eax*4]
0x45eda5  8b44240c             mov      eax, dword ptr [esp + 0xc]
0x45eda9  663d1e00             cmp      ax, 0x1e
0x45edad  730e                 jae      0x45edbd
0x45edaf  25ffff0000           and      eax, 0xffff
0x45edb4  8d3485a8765100       lea      esi, [eax*4 + 0x5176a8]
0x45edbb  eb02                 jmp      0x45edbf
0x45edbd  33f6                 xor      esi, esi
0x45edbf  57                   push     edi
0x45edc0  e85bf1feff           call     0x44df20   ; call
0x45edc5  83c404               add      esp, 4
0x45edc8  50                   push     eax
0x45edc9  57                   push     edi
0x45edca  e831f6feff           call     0x44e400   ; call
0x45edcf  83c404               add      esp, 4
0x45edd2  50                   push     eax
0x45edd3  680a120000           push     0x120a
0x45edd8  56                   push     esi
0x45edd9  e822cb0100           call     0x47b900   ; call
0x45edde  83c410               add      esp, 0x10
0x45ede1  5f                   pop      edi
0x45ede2  5e                   pop      esi
0x45ede3  c3                   ret      
0x45ede4  90                   nop      
0x45ede5  90                   nop      
0x45ede6  90                   nop      
0x45ede7  90                   nop      
0x45ede8  90                   nop      
0x45ede9  90                   nop      
0x45edea  90                   nop      
0x45edeb  90                   nop      
0x45edec  90                   nop      
0x45eded  90                   nop      
0x45edee  90                   nop      
0x45edef  90                   nop      


########## handler[10]  0x45edf0  (208 B) ##########
0x45edf0  83ec10               sub      esp, 0x10
0x45edf3  53                   push     ebx
0x45edf4  56                   push     esi
0x45edf5  57                   push     edi
0x45edf6  6a0a                 push     0xa
0x45edf8  6a01                 push     1
0x45edfa  e8e1f5ffff           call     0x45e3e0   ; call
0x45edff  83c408               add      esp, 8
0x45ee02  50                   push     eax
0x45ee03  e858cf0800           call     0x4ebd60   ; call
0x45ee08  8b0dc0e95100         mov      ecx, dword ptr [0x51e9c0]
0x45ee0e  25ffff0000           and      eax, 0xffff
0x45ee13  83c404               add      esp, 4
0x45ee16  8b3c81               mov      edi, dword ptr [ecx + eax*4]
0x45ee19  668b472a             mov      ax, word ptr [edi + 0x2a]
0x45ee1d  663d7201             cmp      ax, 0x172
0x45ee21  7315                 jae      0x45ee38
0x45ee23  25ffff0000           and      eax, 0xffff
0x45ee28  8d3440               lea      esi, [eax + eax*2]
0x45ee2b  c1e604               shl      esi, 4
0x45ee2e  2bf0                 sub      esi, eax
0x45ee30  81c668985100         add      esi, 0x519868
0x45ee36  eb02                 jmp      0x45ee3a
0x45ee38  33f6                 xor      esi, esi
0x45ee3a  8b442420             mov      eax, dword ptr [esp + 0x20]
0x45ee3e  663d1e00             cmp      ax, 0x1e
0x45ee42  730e                 jae      0x45ee52
0x45ee44  25ffff0000           and      eax, 0xffff
0x45ee49  8d1c85a8765100       lea      ebx, [eax*4 + 0x5176a8]
0x45ee50  eb02                 jmp      0x45ee54
0x45ee52  33db                 xor      ebx, ebx
0x45ee54  57                   push     edi
0x45ee55  e8c6f0feff           call     0x44df20   ; call
0x45ee5a  83c404               add      esp, 4
0x45ee5d  8d54240c             lea      edx, [esp + 0xc]
0x45ee61  50                   push     eax
0x45ee62  56                   push     esi
0x45ee63  52                   push     edx
0x45ee64  e8e7020400           call     0x49f150   ; call
0x45ee69  83c408               add      esp, 8
0x45ee6c  50                   push     eax
0x45ee6d  56                   push     esi
0x45ee6e  e88df5feff           call     0x44e400   ; call
0x45ee73  83c404               add      esp, 4
0x45ee76  50                   push     eax
0x45ee77  680b120000           push     0x120b
0x45ee7c  53                   push     ebx
0x45ee7d  e87eca0100           call     0x47b900   ; call
0x45ee82  83c414               add      esp, 0x14
0x45ee85  e886070400           call     0x49f610   ; call
0x45ee8a  3bf8                 cmp      edi, eax
0x45ee8c  7513                 jne      0x45eea1
0x45ee8e  680d120000           push     0x120d
0x45ee93  e878070400           call     0x49f610   ; call
0x45ee98  50                   push     eax
0x45ee99  e862ca0100           call     0x47b900   ; call
0x45ee9e  83c408               add      esp, 8
0x45eea1  57                   push     edi
0x45eea2  56                   push     esi
0x45eea3  e8a8e2feff           call     0x44d150   ; call
0x45eea8  83c408               add      esp, 8
0x45eeab  5f                   pop      edi
0x45eeac  5e                   pop      esi
0x45eead  5b                   pop      ebx
0x45eeae  83c410               add      esp, 0x10
0x45eeb1  c3                   ret      
0x45eeb2  90                   nop      
0x45eeb3  90                   nop      
0x45eeb4  90                   nop      
0x45eeb5  90                   nop      
0x45eeb6  90                   nop      
0x45eeb7  90                   nop      
0x45eeb8  90                   nop      
0x45eeb9  90                   nop      
0x45eeba  90                   nop      
0x45eebb  90                   nop      
0x45eebc  90                   nop      
0x45eebd  90                   nop      
0x45eebe  90                   nop      
0x45eebf  90                   nop      


########## handler[11]  0x45eec0  (128 B) ##########
0x45eec0  51                   push     ecx
0x45eec1  56                   push     esi
0x45eec2  e859000000           call     0x45ef20   ; call
0x45eec7  3c31                 cmp      al, 0x31
0x45eec9  88442404             mov      byte ptr [esp + 4], al
0x45eecd  7312                 jae      0x45eee1
0x45eecf  8b442404             mov      eax, dword ptr [esp + 4]
0x45eed3  25ff000000           and      eax, 0xff
0x45eed8  8d8c8048955100       lea      ecx, [eax + eax*4 + 0x519548]
0x45eedf  eb02                 jmp      0x45eee3
0x45eee1  33c9                 xor      ecx, ecx
0x45eee3  8b44240c             mov      eax, dword ptr [esp + 0xc]
0x45eee7  663d1e00             cmp      ax, 0x1e
0x45eeeb  730e                 jae      0x45eefb
0x45eeed  25ffff0000           and      eax, 0xffff
0x45eef2  8d3485a8765100       lea      esi, [eax*4 + 0x5176a8]
0x45eef9  eb02                 jmp      0x45eefd
0x45eefb  33f6                 xor      esi, esi
0x45eefd  e83ec50300           call     0x49b440   ; call
0x45ef02  50                   push     eax
0x45ef03  680c120000           push     0x120c
0x45ef08  56                   push     esi
0x45ef09  e8f2c90100           call     0x47b900   ; call
0x45ef0e  83c40c               add      esp, 0xc
0x45ef11  5e                   pop      esi
0x45ef12  59                   pop      ecx
0x45ef13  c3                   ret      
0x45ef14  90                   nop      
0x45ef15  90                   nop      
0x45ef16  90                   nop      
0x45ef17  90                   nop      
0x45ef18  90                   nop      
0x45ef19  90                   nop      
0x45ef1a  90                   nop      
0x45ef1b  90                   nop      
0x45ef1c  90                   nop      
0x45ef1d  90                   nop      
0x45ef1e  90                   nop      
0x45ef1f  90                   nop      
0x45ef20  33c0                 xor      eax, eax
0x45ef22  b94b955100           mov      ecx, 0x51954b
0x45ef27  f6410120             test     byte ptr [ecx + 1], 0x20
0x45ef2b  750e                 jne      0x45ef3b
0x45ef2d  40                   inc      eax
0x45ef2e  83c105               add      ecx, 5
0x45ef31  663d3100             cmp      ax, 0x31
0x45ef35  72f0                 jb       0x45ef27
0x45ef37  660dffff             or       ax, 0xffff
0x45ef3b  c3                   ret      
0x45ef3c  90                   nop      
0x45ef3d  90                   nop      
0x45ef3e  90                   nop      
0x45ef3f  90                   nop      


########## handler[12]  0x45ef40  (192 B) ##########
0x45ef40  53                   push     ebx
0x45ef41  56                   push     esi
0x45ef42  57                   push     edi
0x45ef43  6a09                 push     9
0x45ef45  e816ce0800           call     0x4ebd60   ; call
0x45ef4a  8bd8                 mov      ebx, eax
0x45ef4c  8b442414             mov      eax, dword ptr [esp + 0x14]
0x45ef50  83c404               add      esp, 4
0x45ef53  663d1e00             cmp      ax, 0x1e
0x45ef57  730e                 jae      0x45ef67
0x45ef59  25ffff0000           and      eax, 0xffff
0x45ef5e  8d0c85a8765100       lea      ecx, [eax*4 + 0x5176a8]
0x45ef65  eb02                 jmp      0x45ef69
0x45ef67  33c9                 xor      ecx, ecx
0x45ef69  8bc3                 mov      eax, ebx
0x45ef6b  25ffff0000           and      eax, 0xffff
0x45ef70  8bd0                 mov      edx, eax
0x45ef72  c1e203               shl      edx, 3
0x45ef75  2bd0                 sub      edx, eax
0x45ef77  81c2686c5000         add      edx, 0x506c68
0x45ef7d  52                   push     edx
0x45ef7e  680e120000           push     0x120e
0x45ef83  51                   push     ecx
0x45ef84  e877c90100           call     0x47b900   ; call
0x45ef89  83c40c               add      esp, 0xc
0x45ef8c  be48955100           mov      esi, 0x519548
0x45ef91  bf31000000           mov      edi, 0x31
0x45ef96  660fb64601           movzx    ax, byte ptr [esi + 1]
0x45ef9b  663bc3               cmp      ax, bx
0x45ef9e  7509                 jne      0x45efa9
0x45efa0  6a01                 push     1
0x45efa2  8bce                 mov      ecx, esi
0x45efa4  e837c30300           call     0x49b2e0   ; call
0x45efa9  83c605               add      esi, 5
0x45efac  4f                   dec      edi
0x45efad  75e7                 jne      0x45ef96
0x45efaf  6a00                 push     0
0x45efb1  6a00                 push     0
0x45efb3  e8182f0000           call     0x461ed0   ; call
0x45efb8  83c408               add      esp, 8
0x45efbb  5f                   pop      edi
0x45efbc  5e                   pop      esi
0x45efbd  5b                   pop      ebx
0x45efbe  c3                   ret      
0x45efbf  90                   nop      
0x45efc0  6a10                 push     0x10
0x45efc2  e8b99f0300           call     0x498f80   ; call
0x45efc7  83c404               add      esp, 4
0x45efca  e821170000           call     0x4606f0   ; call
0x45efcf  e84c000000           call     0x45f020   ; call
0x45efd4  6a03                 push     3
0x45efd6  6a2b                 push     0x2b
0x45efd8  e893760300           call     0x496670   ; call
0x45efdd  83c408               add      esp, 8
0x45efe0  e80b180000           call     0x4607f0   ; call
0x45efe5  e8b6070400           call     0x49f7a0   ; call
0x45efea  f7d8                 neg      eax
0x45efec  1bc0                 sbb      eax, eax
0x45efee  f7d8                 neg      eax
0x45eff0  83c069               add      eax, 0x69
0x45eff3  50                   push     eax
0x45eff4  e8a77b0300           call     0x496ba0   ; call
0x45eff9  83c404               add      esp, 4
