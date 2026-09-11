
=== callers of 0x0045d300 : 2 ===
  funcs: 0x45d0b0 0x45d480

########## caller 0x0045d0b0 (206 条) ##########
     0x0045d0b0  53                 push     ebx
     0x0045d0b1  55                 push     ebp
     0x0045d0b2  56                 push     esi
     0x0045d0b3  57                 push     edi
     0x0045d0b4  8b7c241c           mov      edi, dword ptr [esp + 0x1c]
     0x0045d0b8  57                 push     edi
     0x0045d0b9  e8722b0100         call     0x46fc30
     0x0045d0be  8b6c242c           mov      ebp, dword ptr [esp + 0x2c]
     0x0045d0c2  8bf0               mov      esi, eax
     0x0045d0c4  8bc5               mov      eax, ebp
     0x0045d0c6  83c404             add      esp, 4
     0x0045d0c9  25ffff0000         and      eax, 0xffff
     0x0045d0ce  668b0c4580475000   mov      cx, word ptr [eax*2 + 0x504780]
     0x0045d0d6  51                 push     ecx
     0x0045d0d7  e884ec0800         call     0x4ebd60
     0x0045d0dc  83c404             add      esp, 4
     0x0045d0df  6685c0             test     ax, ax
     0x0045d0e2  0f850b020000       jne      0x45d2f3
     0x0045d0e8  6a46               push     0x46
     0x0045d0ea  6a01               push     1
     0x0045d0ec  57                 push     edi
     0x0045d0ed  e82e880300         call     0x495920
     0x0045d0f2  8b442438           mov      eax, dword ptr [esp + 0x38]
     0x0045d0f6  83c40c             add      esp, 0xc
     0x0045d0f9  85c0               test     eax, eax
     0x0045d0fb  744a               je       0x45d147
     0x0045d0fd  e8ae250400         call     0x49f6b0
     0x0045d102  8b5c2414           mov      ebx, dword ptr [esp + 0x14]
     0x0045d106  668b7002           mov      si, word ptr [eax + 2]
     0x0045d10a  53                 push     ebx
     0x0045d10b  e8c0270100         call     0x46f8d0
     0x0045d110  8d1480             lea      edx, [eax + eax*4]
     0x0045d113  b832000000         mov      eax, 0x32
     0x0045d118  83c404             add      esp, 4
     0x0045d11b  2bc2               sub      eax, edx
     0x0045d11d  50                 push     eax
     0x0045d11e  e83dec0800         call     0x4ebd60
     0x0045d123  83c404             add      esp, 4
     0x0045d126  663bf0             cmp      si, ax
     0x0045d129  0f86c4010000       jbe      0x45d2f3
     0x0045d12f  8b4c2418           mov      ecx, dword ptr [esp + 0x18]
     0x0045d133  6a01               push     1
     0x0045d135  57                 push     edi
     0x0045d136  51                 push     ecx
     0x0045d137  53                 push     ebx
  >> 0x0045d138  e8c3010000         call     0x45d300
     0x0045d13d  83c410             add      esp, 0x10
     0x0045d140  33c0               xor      eax, eax
     0x0045d142  5f                 pop      edi
     0x0045d143  5e                 pop      esi
     0x0045d144  5d                 pop      ebp
     0x0045d145  5b                 pop      ebx
     0x0045d146  c3                 ret      
     0x0045d147  6a28               push     0x28
     0x0045d149  c705c03f510001000000 mov      dword ptr [0x513fc0], 1
     0x0045d153  e8489a0300         call     0x496ba0
     0x0045d158  83c404             add      esp, 4
     0x0045d15b  e840260400         call     0x49f7a0
     0x0045d160  f7d8               neg      eax
     0x0045d162  1bc0               sbb      eax, eax
     0x0045d164  f7d8               neg      eax
     0x0045d166  83c023             add      eax, 0x23
     0x0045d169  50                 push     eax
     0x0045d16a  e8319a0300         call     0x496ba0
     0x0045d16f  83c404             add      esp, 4
     0x0045d172  6a1f               push     0x1f
     0x0045d174  e8279a0300         call     0x496ba0
     0x0045d179  8b5c2418           mov      ebx, dword ptr [esp + 0x18]
     0x0045d17d  83c404             add      esp, 4
     0x0045d180  8bcb               mov      ecx, ebx
     0x0045d182  e889f10300         call     0x49c310
     0x0045d187  8bd6               mov      edx, esi
     0x0045d189  50                 push     eax
     0x0045d18a  f7da               neg      edx
     0x0045d18c  1bd2               sbb      edx, edx
     0x0045d18e  83e2e3             and      edx, 0xffffffe3
     0x0045d191  81c24b030000       add      edx, 0x34b
     0x0045d197  52                 push     edx
     0x0045d198  57                 push     edi
     0x0045d199  e862e70100         call     0x47b900
     0x0045d19e  83c40c             add      esp, 0xc
     0x0045d1a1  6a05               push     5
     0x0045d1a3  e8f8990300         call     0x496ba0
     0x0045d1a8  83c404             add      esp, 4
     0x0045d1ab  6a11               push     0x11
     0x0045d1ad  e8ee990300         call     0x496ba0
     0x0045d1b2  83c404             add      esp, 4
     0x0045d1b5  e836e40100         call     0x47b5f0
     0x0045d1ba  8bcf               mov      ecx, edi
     0x0045d1bc  e84ff10300         call     0x49c310
     0x0045d1c1  50                 push     eax
     0x0045d1c2  8bc6               mov      eax, esi
     0x0045d1c4  f7d8               neg      eax
     0x0045d1c6  1bc0               sbb      eax, eax
     0x0045d1c8  83e01d             and      eax, 0x1d
     0x0045d1cb  052f030000         add      eax, 0x32f
     0x0045d1d0  50                 push     eax
     0x0045d1d1  53                 push     ebx
     0x0045d1d2  e829e70100         call     0x47b900
     0x0045d1d7  8bce               mov      ecx, esi
     0x0045d1d9  83c40c             add      esp, 0xc
     0x0045d1dc  f7d9               neg      ecx
     0x0045d1de  1bc9               sbb      ecx, ecx
     0x0045d1e0  83e1e3             and      ecx, 0xffffffe3
     0x0045d1e3  81c14d030000       add      ecx, 0x34d
     0x0045d1e9  51                 push     ecx
     0x0045d1ea  57                 push     edi
     0x0045d1eb  e810e70100         call     0x47b900
     0x0045d1f0  83c408             add      esp, 8
     0x0045d1f3  6831030000         push     0x331
     0x0045d1f8  53                 push     ebx
     0x0045d1f9  e802e70100         call     0x47b900
     0x0045d1fe  83c408             add      esp, 8
     0x0045d201  57                 push     edi
     0x0045d202  e8490fffff         call     0x44e150
     0x0045d207  83c404             add      esp, 4
     0x0045d20a  f7de               neg      esi
     0x0045d20c  1bf6               sbb      esi, esi
     0x0045d20e  50                 push     eax
     0x0045d20f  83e6e4             and      esi, 0xffffffe4
     0x0045d212  81c64e030000       add      esi, 0x34e
     0x0045d218  56                 push     esi
     0x0045d219  57                 push     edi
     0x0045d21a  e8e1e60100         call     0x47b900
     0x0045d21f  83c40c             add      esp, 0xc
     0x0045d222  e8d9e30100         call     0x47b600
     0x0045d227  6a29               push     0x29
     0x0045d229  e872990300         call     0x496ba0
     0x0045d22e  83c404             add      esp, 4
     0x0045d231  6833030000         push     0x333
     0x0045d236  53                 push     ebx
     0x0045d237  e8c4e60100         call     0x47b900
     0x0045d23c  8b74242c           mov      esi, dword ptr [esp + 0x2c]
     0x0045d240  83c408             add      esp, 8
     0x0045d243  f6460c02           test     byte ptr [esi + 0xc], 2
     0x0045d247  7536               jne      0x45d27f
     0x0045d249  6a01               push     1
     0x0045d24b  8bce               mov      ecx, esi
     0x0045d24d  e80ee60300         call     0x49b860
     0x0045d252  8d542d0a           lea      edx, [ebp + ebp + 0xa]
     0x0045d256  52                 push     edx
     0x0045d257  e804eb0800         call     0x4ebd60
     0x0045d25c  83c032             add      eax, 0x32
     0x0045d25f  83c404             add      esp, 4
     0x0045d262  66894606           mov      word ptr [esi + 6], ax
     0x0045d266  b80a000000         mov      eax, 0xa
     0x0045d26b  2bc5               sub      eax, ebp
     0x0045d26d  50                 push     eax
     0x0045d26e  e8edea0800         call     0x4ebd60
     0x0045d273  83c404             add      esp, 4
     0x0045d276  6685c0             test     ax, ax
     0x0045d279  7541               jne      0x45d2bc
     0x0045d27b  6a01               push     1
     0x0045d27d  eb36               jmp      0x45d2b5
     0x0045d27f  668b7e06           mov      di, word ptr [esi + 6]
     0x0045d283  8d4d01             lea      ecx, [ebp + 1]
     0x0045d286  51                 push     ecx
     0x0045d287  e8d4ea0800         call     0x4ebd60
     0x0045d28c  ba14000000         mov      edx, 0x14
     0x0045d291  83c404             add      esp, 4
     0x0045d294  2bd5               sub      edx, ebp
     0x0045d296  8d44470a           lea      eax, [edi + eax*2 + 0xa]
     0x0045d29a  52                 push     edx
     0x0045d29b  66894606           mov      word ptr [esi + 6], ax
     0x0045d29f  e8bcea0800         call     0x4ebd60
     0x0045d2a4  83c404             add      esp, 4
     0x0045d2a7  6685c0             test     ax, ax
     0x0045d2aa  7407               je       0x45d2b3
     0x0045d2ac  66837e0678         cmp      word ptr [esi + 6], 0x78
     0x0045d2b1  7609               jbe      0x45d2bc
     0x0045d2b3  6a00               push     0
     0x0045d2b5  8bce               mov      ecx, esi
     0x0045d2b7  e864e60300         call     0x49b920
     0x0045d2bc  8b7c2420           mov      edi, dword ptr [esp + 0x20]
     0x0045d2c0  6a0a               push     0xa
     0x0045d2c2  668b7703           mov      si, word ptr [edi + 3]
     0x0045d2c6  c1ee07             shr      esi, 7
     0x0045d2c9  83e61f             and      esi, 0x1f
     0x0045d2cc  e88fea0800         call     0x4ebd60
     0x0045d2d1  83c404             add      esp, 4
     0x0045d2d4  83c01b             add      eax, 0x1b
     0x0045d2d7  50                 push     eax
     0x0045d2d8  56                 push     esi
     0x0045d2d9  e8f2e90800         call     0x4ebcd0
     0x0045d2de  83c408             add      esp, 8
     0x0045d2e1  8bcf               mov      ecx, edi
     0x0045d2e3  50                 push     eax
     0x0045d2e4  e8c7df0300         call     0x49b2b0
     0x0045d2e9  b801000000         mov      eax, 1
     0x0045d2ee  5f                 pop      edi
     0x0045d2ef  5e                 pop      esi
     0x0045d2f0  5d                 pop      ebp
     0x0045d2f1  5b                 pop      ebx
     0x0045d2f2  c3                 ret      
     0x0045d2f3  5f                 pop      edi
     0x0045d2f4  5e                 pop      esi
     0x0045d2f5  5d                 pop      ebp
     0x0045d2f6  33c0               xor      eax, eax
     0x0045d2f8  5b                 pop      ebx
     0x0045d2f9  c3                 ret      
     0x0045d2fa  90                 nop      
     0x0045d2fb  90                 nop      
     0x0045d2fc  90                 nop      
     0x0045d2fd  90                 nop      
     0x0045d2fe  90                 nop      
     0x0045d2ff  90                 nop      

=== callers of 0x0043dd50 : 4 ===
  funcs: 0x435570 0x435740 0x43a890 0x43bda0

########## caller 0x00435570 (158 条) ##########
     0x00435570  83ec3c             sub      esp, 0x3c
     0x00435573  53                 push     ebx
     0x00435574  55                 push     ebp
     0x00435575  8b6c2448           mov      ebp, dword ptr [esp + 0x48]
     0x00435579  56                 push     esi
     0x0043557a  57                 push     edi
     0x0043557b  6a00               push     0
     0x0043557d  8bcd               mov      ecx, ebp
     0x0043557f  e8ac800000         call     0x43d630
     0x00435584  8bcd               mov      ecx, ebp
     0x00435586  8bf8               mov      edi, eax
     0x00435588  e813830000         call     0x43d8a0
     0x0043558d  8bf0               mov      esi, eax
     0x0043558f  8a452c             mov      al, byte ptr [ebp + 0x2c]
     0x00435592  a801               test     al, 1
     0x00435594  89742418           mov      dword ptr [esp + 0x18], esi
     0x00435598  743a               je       0x4355d4
     0x0043559a  3bfe               cmp      edi, esi
     0x0043559c  7510               jne      0x4355ae
     0x0043559e  68c1000000         push     0xc1
     0x004355a3  56                 push     esi
     0x004355a4  e897640400         call     0x47ba40
     0x004355a9  83c408             add      esp, 8
     0x004355ac  eb45               jmp      0x4355f3
     0x004355ae  8bce               mov      ecx, esi
     0x004355b0  e85b6d0600         call     0x49c310
     0x004355b5  50                 push     eax
     0x004355b6  68c2000000         push     0xc2
     0x004355bb  57                 push     edi
     0x004355bc  e87f640400         call     0x47ba40
     0x004355c1  83c40c             add      esp, 0xc
     0x004355c4  68c3000000         push     0xc3
     0x004355c9  56                 push     esi
     0x004355ca  e871640400         call     0x47ba40
     0x004355cf  83c408             add      esp, 8
     0x004355d2  eb1f               jmp      0x4355f3
     0x004355d4  a808               test     al, 8
     0x004355d6  741b               je       0x4355f3
     0x004355d8  57                 push     edi
     0x004355d9  e8b29b0600         call     0x49f190
     0x004355de  83c404             add      esp, 4
     0x004355e1  50                 push     eax
     0x004355e2  68c5000000         push     0xc5
     0x004355e7  6a00               push     0
     0x004355e9  6a14               push     0x14
     0x004355eb  e8205c0400         call     0x47b210
     0x004355f0  83c410             add      esp, 0x10
     0x004355f3  e8e89f0600         call     0x49f5e0
     0x004355f8  3bf0               cmp      esi, eax
     0x004355fa  7558               jne      0x435654
     0x004355fc  55                 push     ebp
     0x004355fd  6a04               push     4
     0x004355ff  6a00               push     0
     0x00435601  68c4000000         push     0xc4
     0x00435606  e8f5de0500         call     0x493500
     0x0043560b  83c404             add      esp, 4
     0x0043560e  50                 push     eax
     0x0043560f  e8ecfaffff         call     0x435100
     0x00435614  83c410             add      esp, 0x10
     0x00435617  85c0               test     eax, eax
     0x00435619  0f8511010000       jne      0x435730
     0x0043561f  a071345100         mov      al, byte ptr [0x513471]
     0x00435624  8a0d70345100       mov      cl, byte ptr [0x513470]
     0x0043562a  88442450           mov      byte ptr [esp + 0x50], al
     0x0043562e  884c2410           mov      byte ptr [esp + 0x10], cl
     0x00435632  8b542450           mov      edx, dword ptr [esp + 0x50]
     0x00435636  8b442410           mov      eax, dword ptr [esp + 0x10]
     0x0043563a  52                 push     edx
     0x0043563b  50                 push     eax
     0x0043563c  55                 push     ebp
     0x0043563d  e8fe000000         call     0x435740
     0x00435642  83c40c             add      esp, 0xc
     0x00435645  b9d0335100         mov      ecx, 0x5133d0
     0x0043564a  e8218e0b00         call     0x4ee470
     0x0043564f  e9b9000000         jmp      0x43570d
     0x00435654  8d4c241c           lea      ecx, [esp + 0x1c]
     0x00435658  51                 push     ecx
     0x00435659  8bcd               mov      ecx, ebp
  >> 0x0043565b  e8f0860000         call     0x43dd50
     0x00435660  660fb67d00         movzx    di, byte ptr [ebp]
     0x00435665  660fb65502         movzx    dx, byte ptr [ebp + 2]
     0x0043566a  0fbfc7             movsx    eax, di
     0x0043566d  6689542410         mov      word ptr [esp + 0x10], dx
     0x00435672  c744245000000000   mov      dword ptr [esp + 0x50], 0
     0x0043567a  99                 cdq      
     0x0043567b  33c2               xor      eax, edx
     0x0043567d  2bc2               sub      eax, edx
     0x0043567f  83e001             and      eax, 1
     0x00435682  33c2               xor      eax, edx
     0x00435684  2bc2               sub      eax, edx
     0x00435686  8d3440             lea      esi, [eax + eax*2]
     0x00435689  d1e6               shl      esi, 1
     0x0043568b  56                 push     esi
     0x0043568c  e8af4d0000         call     0x43a440
     0x00435691  8b4c2414           mov      ecx, dword ptr [esp + 0x14]
     0x00435695  83c404             add      esp, 4
     0x00435698  668bd8             mov      bx, ax
     0x0043569b  56                 push     esi
     0x0043569c  03d9               add      ebx, ecx
     0x0043569e  e87d4d0000         call     0x43a420
     0x004356a3  8a4c2420           mov      cl, byte ptr [esp + 0x20]
     0x004356a7  8a542422           mov      dl, byte ptr [esp + 0x22]
     0x004356ab  83c404             add      esp, 4
     0x004356ae  884c241d           mov      byte ptr [esp + 0x1d], cl
     0x004356b2  8d4c241c           lea      ecx, [esp + 0x1c]
     0x004356b6  03c7               add      eax, edi
     0x004356b8  51                 push     ecx
     0x004356b9  53                 push     ebx
     0x004356ba  50                 push     eax
     0x004356bb  89442420           mov      dword ptr [esp + 0x20], eax
     0x004356bf  88442428           mov      byte ptr [esp + 0x28], al
     0x004356c3  8854242b           mov      byte ptr [esp + 0x2b], dl
     0x004356c7  885c242a           mov      byte ptr [esp + 0x2a], bl
     0x004356cb  e860510000         call     0x43a830
     0x004356d0  83c40c             add      esp, 0xc
     0x004356d3  85c0               test     eax, eax
     0x004356d5  7512               jne      0x4356e9
     0x004356d7  8b442450           mov      eax, dword ptr [esp + 0x50]
     0x004356db  40                 inc      eax
     0x004356dc  46                 inc      esi
     0x004356dd  663d0600           cmp      ax, 6
     0x004356e1  89442450           mov      dword ptr [esp + 0x50], eax
     0x004356e5  7ca4               jl       0x43568b
     0x004356e7  eb0f               jmp      0x4356f8
     0x004356e9  8b542414           mov      edx, dword ptr [esp + 0x14]
     0x004356ed  53                 push     ebx
     0x004356ee  52                 push     edx
     0x004356ef  55                 push     ebp
     0x004356f0  e84b000000         call     0x435740
     0x004356f5  83c40c             add      esp, 0xc
     0x004356f8  b9d0335100         mov      ecx, 0x5133d0
     0x004356fd  c6056e34510000     mov      byte ptr [0x51346e], 0
     0x00435704  e8678d0b00         call     0x4ee470
     0x00435709  8b742418           mov      esi, dword ptr [esp + 0x18]
     0x0043570d  6a0a               push     0xa
     0x0043570f  e8ac400600         call     0x4997c0
     0x00435714  83c404             add      esp, 4
     0x00435717  56                 push     esi
     0x00435718  55                 push     ebp
     0x00435719  e8a2000000         call     0x4357c0
     0x0043571e  83c408             add      esp, 8
     0x00435721  b9d0255100         mov      ecx, 0x5125d0
     0x00435726  e8f5270000         call     0x437f20
     0x0043572b  e8d0400600         call     0x499800
     0x00435730  5f                 pop      edi
     0x00435731  5e                 pop      esi
     0x00435732  5d                 pop      ebp
     0x00435733  5b                 pop      ebx
     0x00435734  83c43c             add      esp, 0x3c
     0x00435737  c3                 ret      
     0x00435738  90                 nop      
     0x00435739  90                 nop      
     0x0043573a  90                 nop      
     0x0043573b  90                 nop      
     0x0043573c  90                 nop      
     0x0043573d  90                 nop      
     0x0043573e  90                 nop      
     0x0043573f  90                 nop      