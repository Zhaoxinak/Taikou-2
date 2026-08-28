=== 晋升相关消息 ===
  0x033e  None
  0x033f  None
  0x0340  None
  0x0341  None
  0x0342  None

########## 晋升播报 0x45d300  0x0045d300  func=0x0045d300 (109 条) ##########
0x0045d300  53                 push     ebx
0x0045d301  55                 push     ebp
0x0045d302  8b6c240c           mov      ebp, dword ptr [esp + 0xc]
0x0045d306  56                 push     esi
0x0045d307  8b74241c           mov      esi, dword ptr [esp + 0x1c]
0x0045d30b  57                 push     edi
0x0045d30c  8b7c241c           mov      edi, dword ptr [esp + 0x1c]
0x0045d310  c705c03f510001000000 mov      dword ptr [0x513fc0], 1
0x0045d31a  85f6               test     esi, esi
0x0045d31c  7426               je       0x45d344
0x0045d31e  e8cde20100         call     0x47b5f0
0x0045d323  683d030000         push     0x33d
0x0045d328  57                 push     edi
0x0045d329  e8d2e50100         call     0x47b900
0x0045d32e  83c408             add      esp, 8
0x0045d331  683e030000         push     0x33e
0x0045d336  55                 push     ebp
0x0045d337  e8c4e50100         call     0x47b900
0x0045d33c  83c408             add      esp, 8
0x0045d33f  e8bce20100         call     0x47b600
0x0045d344  6a2a               push     0x2a
0x0045d346  e855980300         call     0x496ba0
0x0045d34b  83c404             add      esp, 4
0x0045d34e  e89de20100         call     0x47b5f0
0x0045d353  8bc6               mov      eax, esi
0x0045d355  f7d8               neg      eax
0x0045d357  1bc0               sbb      eax, eax
0x0045d359  24f8               and      al, 0xf8
0x0045d35b  0547030000         add      eax, 0x347
0x0045d360  50                 push     eax
0x0045d361  57                 push     edi
0x0045d362  e899e50100         call     0x47b900
0x0045d367  83c408             add      esp, 8
0x0045d36a  57                 push     edi
0x0045d36b  e8c0280100         call     0x46fc30
0x0045d370  83c404             add      esp, 4
0x0045d373  f7d8               neg      eax
0x0045d375  1bc0               sbb      eax, eax
0x0045d377  83e013             and      eax, 0x13
0x0045d37a  0540030000         add      eax, 0x340
0x0045d37f  50                 push     eax
0x0045d380  55                 push     ebp
0x0045d381  e87ae50100         call     0x47b900
0x0045d386  83c408             add      esp, 8
0x0045d389  85f6               test     esi, esi
0x0045d38b  750e               jne      0x45d39b
0x0045d38d  683f030000         push     0x33f
0x0045d392  57                 push     edi
0x0045d393  e868e50100         call     0x47b900
0x0045d398  83c408             add      esp, 8
0x0045d39b  6841030000         push     0x341
0x0045d3a0  68b0765100         push     0x5176b0
0x0045d3a5  e856e50100         call     0x47b900
0x0045d3aa  83c408             add      esp, 8
0x0045d3ad  6842030000         push     0x342
0x0045d3b2  57                 push     edi
0x0045d3b3  e848e50100         call     0x47b900
0x0045d3b8  8b5c2420           mov      ebx, dword ptr [esp + 0x20]
0x0045d3bc  83c408             add      esp, 8
0x0045d3bf  85db               test     ebx, ebx
0x0045d3c1  8bc3               mov      eax, ebx
0x0045d3c3  7502               jne      0x45d3c7
0x0045d3c5  8bc5               mov      eax, ebp
0x0045d3c7  6843030000         push     0x343
0x0045d3cc  50                 push     eax
0x0045d3cd  e82ee50100         call     0x47b900
0x0045d3d2  83c408             add      esp, 8
0x0045d3d5  f7de               neg      esi
0x0045d3d7  1bf6               sbb      esi, esi
0x0045d3d9  83e6fe             and      esi, 0xfffffffe
0x0045d3dc  81c646030000       add      esi, 0x346
0x0045d3e2  56                 push     esi
0x0045d3e3  57                 push     edi
0x0045d3e4  e817e50100         call     0x47b900
0x0045d3e9  83c408             add      esp, 8
0x0045d3ec  e80fe20100         call     0x47b600
0x0045d3f1  6a2b               push     0x2b
0x0045d3f3  e8a8970300         call     0x496ba0
0x0045d3f8  83c404             add      esp, 4
0x0045d3fb  b8f8475000         mov      eax, 0x5047f8
0x0045d400  85db               test     ebx, ebx
0x0045d402  7505               jne      0x45d409
0x0045d404  b8f4475000         mov      eax, 0x5047f4
0x0045d409  85db               test     ebx, ebx
0x0045d40b  7502               jne      0x45d40f
0x0045d40d  8bdd               mov      ebx, ebp
0x0045d40f  50                 push     eax
0x0045d410  6845030000         push     0x345
0x0045d415  53                 push     ebx
0x0045d416  e8e5e40100         call     0x47b900
0x0045d41b  83c40c             add      esp, 0xc
0x0045d41e  5f                 pop      edi
0x0045d41f  5e                 pop      esi
0x0045d420  5d                 pop      ebp
0x0045d421  5b                 pop      ebx
0x0045d422  c3                 ret      
0x0045d423  90                 nop      
0x0045d424  90                 nop      
0x0045d425  90                 nop      
0x0045d426  90                 nop      
0x0045d427  90                 nop      
0x0045d428  90                 nop      
0x0045d429  90                 nop      
0x0045d42a  90                 nop      
0x0045d42b  90                 nop      
0x0045d42c  90                 nop      
0x0045d42d  90                 nop      
0x0045d42e  90                 nop      
0x0045d42f  90                 nop      

########## 候选A 0x49ca90  0x0049ca90  func=0x0049ca90 (94 条) ##########
0x0049ca90  81ecac080000       sub      esp, 0x8ac
0x0049ca96  53                 push     ebx
0x0049ca97  55                 push     ebp
0x0049ca98  8bac24b8080000     mov      ebp, dword ptr [esp + 0x8b8]
0x0049ca9f  56                 push     esi
0x0049caa0  57                 push     edi
0x0049caa1  6a05               push     5
0x0049caa3  668b4510           mov      ax, word ptr [ebp + 0x10]
0x0049caa7  668b7514           mov      si, word ptr [ebp + 0x14]
0x0049caab  6a03               push     3
0x0049caad  50                 push     eax
0x0049caae  e89df10400         call     0x4ebc50
0x0049cab3  25ffff0000         and      eax, 0xffff
0x0049cab8  81e6ffff0000       and      esi, 0xffff
0x0049cabe  052c010000         add      eax, 0x12c
0x0049cac3  83c40c             add      esp, 0xc
0x0049cac6  3bf0               cmp      esi, eax
0x0049cac8  0f8cce000000       jl       0x49cb9c
0x0049cace  66817d12204e       cmp      word ptr [ebp + 0x12], 0x4e20
0x0049cad4  0f87c2000000       ja       0x49cb9c
0x0049cada  8b9c24c4080000     mov      ebx, dword ptr [esp + 0x8c4]
0x0049cae1  33d2               xor      edx, edx
0x0049cae3  33f6               xor      esi, esi
0x0049cae5  81e3ffff0000       and      ebx, 0xffff
0x0049caeb  7e30               jle      0x49cb1d
0x0049caed  8b3dc0e95100       mov      edi, dword ptr [0x51e9c0]
0x0049caf3  33c9               xor      ecx, ecx
0x0049caf5  8b8424c8080000     mov      eax, dword ptr [esp + 0x8c8]
0x0049cafc  803c0800           cmp      byte ptr [eax + ecx], 0
0x0049cb00  7513               jne      0x49cb15
0x0049cb02  8b0c8f             mov      ecx, dword ptr [edi + ecx*4]
0x0049cb05  0fbfc2             movsx    eax, dx
0x0049cb08  42                 inc      edx
0x0049cb09  898c84f4020000     mov      dword ptr [esp + eax*4 + 0x2f4], ecx
0x0049cb10  6689744410         mov      word ptr [esp + eax*2 + 0x10], si
0x0049cb15  46                 inc      esi
0x0049cb16  0fbfce             movsx    ecx, si
0x0049cb19  3bcb               cmp      ecx, ebx
0x0049cb1b  7cd8               jl       0x49caf5
0x0049cb1d  6685d2             test     dx, dx
0x0049cb20  7e7a               jle      0x49cb9c
0x0049cb22  8bbc24f4020000     mov      edi, dword ptr [esp + 0x2f4]
0x0049cb29  8b5c2410           mov      ebx, dword ptr [esp + 0x10]
0x0049cb2d  6683fa01           cmp      dx, 1
0x0049cb31  7e30               jle      0x49cb63
0x0049cb33  0fbfd2             movsx    edx, dx
0x0049cb36  8d4c2412           lea      ecx, [esp + 0x12]
0x0049cb3a  8db424f8020000     lea      esi, [esp + 0x2f8]
0x0049cb41  4a                 dec      edx
0x0049cb42  8b06               mov      eax, dword ptr [esi]
0x0049cb44  668b6f26           mov      bp, word ptr [edi + 0x26]
0x0049cb48  663b6826           cmp      bp, word ptr [eax + 0x26]
0x0049cb4c  7605               jbe      0x49cb53
0x0049cb4e  668b19             mov      bx, word ptr [ecx]
0x0049cb51  8bf8               mov      edi, eax
0x0049cb53  83c604             add      esi, 4
0x0049cb56  83c102             add      ecx, 2
0x0049cb59  4a                 dec      edx
0x0049cb5a  75e6               jne      0x49cb42
0x0049cb5c  8bac24c0080000     mov      ebp, dword ptr [esp + 0x8c0]
0x0049cb63  55                 push     ebp
0x0049cb64  e8470b0000         call     0x49d6b0
0x0049cb69  6633d2             xor      dx, dx
0x0049cb6c  83c404             add      esp, 4
0x0049cb6f  8ad0               mov      dl, al
0x0049cb71  52                 push     edx
0x0049cb72  6a02               push     2
0x0049cb74  57                 push     edi
0x0049cb75  55                 push     ebp
0x0049cb76  e825f60000         call     0x4ac1a0
0x0049cb7b  83c410             add      esp, 0x10
0x0049cb7e  85c0               test     eax, eax
0x0049cb80  741a               je       0x49cb9c
0x0049cb82  682c010000         push     0x12c
0x0049cb87  8bcd               mov      ecx, ebp
0x0049cb89  e8e2680000         call     0x4a3470
0x0049cb8e  8b8c24c8080000     mov      ecx, dword ptr [esp + 0x8c8]
0x0049cb95  0fbfc3             movsx    eax, bx
0x0049cb98  c6040101           mov      byte ptr [ecx + eax], 1
0x0049cb9c  5f                 pop      edi
0x0049cb9d  5e                 pop      esi
0x0049cb9e  5d                 pop      ebp
0x0049cb9f  5b                 pop      ebx
0x0049cba0  81c4ac080000       add      esp, 0x8ac
0x0049cba6  c3                 ret      
0x0049cba7  90                 nop      
0x0049cba8  90                 nop      
0x0049cba9  90                 nop      
0x0049cbaa  90                 nop      
0x0049cbab  90                 nop      
0x0049cbac  90                 nop      
0x0049cbad  90                 nop      
0x0049cbae  90                 nop      
0x0049cbaf  90                 nop      

########## 候选B 0x49cbb0  0x0049cbb0  func=0x0049cbb0 (76 条) ##########
0x0049cbb0  81ecb0080000       sub      esp, 0x8b0
0x0049cbb6  8b8424b4080000     mov      eax, dword ptr [esp + 0x8b4]
0x0049cbbd  53                 push     ebx
0x0049cbbe  55                 push     ebp
0x0049cbbf  56                 push     esi
0x0049cbc0  57                 push     edi
0x0049cbc1  50                 push     eax
0x0049cbc2  e8b9280000         call     0x49f480
0x0049cbc7  8b9c24cc080000     mov      ebx, dword ptr [esp + 0x8cc]
0x0049cbce  83c404             add      esp, 4
0x0049cbd1  33ff               xor      edi, edi
0x0049cbd3  33f6               xor      esi, esi
0x0049cbd5  81e3ffff0000       and      ebx, 0xffff
0x0049cbdb  89442410           mov      dword ptr [esp + 0x10], eax
0x0049cbdf  7e2f               jle      0x49cc10
0x0049cbe1  a1c0e95100         mov      eax, dword ptr [0x51e9c0]
0x0049cbe6  33d2               xor      edx, edx
0x0049cbe8  8b8c24cc080000     mov      ecx, dword ptr [esp + 0x8cc]
0x0049cbef  803c1100           cmp      byte ptr [ecx + edx], 0
0x0049cbf3  7513               jne      0x49cc08
0x0049cbf5  8b1490             mov      edx, dword ptr [eax + edx*4]
0x0049cbf8  0fbfcf             movsx    ecx, di
0x0049cbfb  47                 inc      edi
0x0049cbfc  89948cf8020000     mov      dword ptr [esp + ecx*4 + 0x2f8], edx
0x0049cc03  6689744c14         mov      word ptr [esp + ecx*2 + 0x14], si
0x0049cc08  46                 inc      esi
0x0049cc09  0fbfd6             movsx    edx, si
0x0049cc0c  3bd3               cmp      edx, ebx
0x0049cc0e  7cd8               jl       0x49cbe8
0x0049cc10  6685ff             test     di, di
0x0049cc13  7e69               jle      0x49cc7e
0x0049cc15  8b9c24f8020000     mov      ebx, dword ptr [esp + 0x2f8]
0x0049cc1c  8b6c2414           mov      ebp, dword ptr [esp + 0x14]
0x0049cc20  6683ff01           cmp      di, 1
0x0049cc24  7e29               jle      0x49cc4f
0x0049cc26  0fbfff             movsx    edi, di
0x0049cc29  8d542416           lea      edx, [esp + 0x16]
0x0049cc2d  8db424fc020000     lea      esi, [esp + 0x2fc]
0x0049cc34  4f                 dec      edi
0x0049cc35  8b0e               mov      ecx, dword ptr [esi]
0x0049cc37  668b4326           mov      ax, word ptr [ebx + 0x26]
0x0049cc3b  663b4126           cmp      ax, word ptr [ecx + 0x26]
0x0049cc3f  7605               jbe      0x49cc46
0x0049cc41  668b2a             mov      bp, word ptr [edx]
0x0049cc44  8bd9               mov      ebx, ecx
0x0049cc46  83c604             add      esi, 4
0x0049cc49  83c202             add      edx, 2
0x0049cc4c  4f                 dec      edi
0x0049cc4d  75e6               jne      0x49cc35
0x0049cc4f  8b4c2410           mov      ecx, dword ptr [esp + 0x10]
0x0049cc53  8b8424c4080000     mov      eax, dword ptr [esp + 0x8c4]
0x0049cc5a  660fb65108         movzx    dx, byte ptr [ecx + 8]
0x0049cc5f  52                 push     edx
0x0049cc60  6a0c               push     0xc
0x0049cc62  53                 push     ebx
0x0049cc63  50                 push     eax
0x0049cc64  e837f50000         call     0x4ac1a0
0x0049cc69  83c410             add      esp, 0x10
0x0049cc6c  85c0               test     eax, eax
0x0049cc6e  740e               je       0x49cc7e
0x0049cc70  8b9424cc080000     mov      edx, dword ptr [esp + 0x8cc]
0x0049cc77  0fbfcd             movsx    ecx, bp
0x0049cc7a  c6040a01           mov      byte ptr [edx + ecx], 1
0x0049cc7e  5f                 pop      edi
0x0049cc7f  5e                 pop      esi
0x0049cc80  5d                 pop      ebp
0x0049cc81  5b                 pop      ebx
0x0049cc82  81c4b0080000       add      esp, 0x8b0
0x0049cc88  c3                 ret      
0x0049cc89  90                 nop      
0x0049cc8a  90                 nop      
0x0049cc8b  90                 nop      
0x0049cc8c  90                 nop      
0x0049cc8d  90                 nop      
0x0049cc8e  90                 nop      
0x0049cc8f  90                 nop      

########## 候选C 0x49d810  0x0049d810  func=0x0049d810 (92 条) ##########
0x0049d810  81ecac080000       sub      esp, 0x8ac
0x0049d816  53                 push     ebx
0x0049d817  55                 push     ebp
0x0049d818  56                 push     esi
0x0049d819  57                 push     edi
0x0049d81a  8bbc24c0080000     mov      edi, dword ptr [esp + 0x8c0]
0x0049d821  6a05               push     5
0x0049d823  6a03               push     3
0x0049d825  668b4710           mov      ax, word ptr [edi + 0x10]
0x0049d829  668b7714           mov      si, word ptr [edi + 0x14]
0x0049d82d  50                 push     eax
0x0049d82e  e81de40400         call     0x4ebc50
0x0049d833  83c40c             add      esp, 0xc
0x0049d836  663bf0             cmp      si, ax
0x0049d839  0f87cc000000       ja       0x49d90b
0x0049d83f  66837f1264         cmp      word ptr [edi + 0x12], 0x64
0x0049d844  0f82c1000000       jb       0x49d90b
0x0049d84a  8b9c24c4080000     mov      ebx, dword ptr [esp + 0x8c4]
0x0049d851  8bac24c8080000     mov      ebp, dword ptr [esp + 0x8c8]
0x0049d858  33f6               xor      esi, esi
0x0049d85a  33d2               xor      edx, edx
0x0049d85c  81e3ffff0000       and      ebx, 0xffff
0x0049d862  7e2a               jle      0x49d88e
0x0049d864  8b3dc0e95100       mov      edi, dword ptr [0x51e9c0]
0x0049d86a  33c9               xor      ecx, ecx
0x0049d86c  807c0d0000         cmp      byte ptr [ebp + ecx], 0
0x0049d871  7513               jne      0x49d886
0x0049d873  8b0c8f             mov      ecx, dword ptr [edi + ecx*4]
0x0049d876  0fbfc6             movsx    eax, si
0x0049d879  46                 inc      esi
0x0049d87a  898c84f4020000     mov      dword ptr [esp + eax*4 + 0x2f4], ecx
0x0049d881  6689544410         mov      word ptr [esp + eax*2 + 0x10], dx
0x0049d886  42                 inc      edx
0x0049d887  0fbfca             movsx    ecx, dx
0x0049d88a  3bcb               cmp      ecx, ebx
0x0049d88c  7cde               jl       0x49d86c
0x0049d88e  6685f6             test     si, si
0x0049d891  7e78               jle      0x49d90b
0x0049d893  8bbc24f4020000     mov      edi, dword ptr [esp + 0x2f4]
0x0049d89a  8b5c2410           mov      ebx, dword ptr [esp + 0x10]
0x0049d89e  6683fe01           cmp      si, 1
0x0049d8a2  7e30               jle      0x49d8d4
0x0049d8a4  0fbff6             movsx    esi, si
0x0049d8a7  8d4c2412           lea      ecx, [esp + 0x12]
0x0049d8ab  8d9424f8020000     lea      edx, [esp + 0x2f8]
0x0049d8b2  4e                 dec      esi
0x0049d8b3  8b02               mov      eax, dword ptr [edx]
0x0049d8b5  668b6f26           mov      bp, word ptr [edi + 0x26]
0x0049d8b9  663b6826           cmp      bp, word ptr [eax + 0x26]
0x0049d8bd  7605               jbe      0x49d8c4
0x0049d8bf  668b19             mov      bx, word ptr [ecx]
0x0049d8c2  8bf8               mov      edi, eax
0x0049d8c4  83c204             add      edx, 4
0x0049d8c7  83c102             add      ecx, 2
0x0049d8ca  4e                 dec      esi
0x0049d8cb  75e6               jne      0x49d8b3
0x0049d8cd  8bac24c8080000     mov      ebp, dword ptr [esp + 0x8c8]
0x0049d8d4  8bb424c0080000     mov      esi, dword ptr [esp + 0x8c0]
0x0049d8db  56                 push     esi
0x0049d8dc  e8cffdffff         call     0x49d6b0
0x0049d8e1  6633d2             xor      dx, dx
0x0049d8e4  83c404             add      esp, 4
0x0049d8e7  8ad0               mov      dl, al
0x0049d8e9  52                 push     edx
0x0049d8ea  6a03               push     3
0x0049d8ec  57                 push     edi
0x0049d8ed  56                 push     esi
0x0049d8ee  e8ade80000         call     0x4ac1a0
0x0049d8f3  83c410             add      esp, 0x10
0x0049d8f6  85c0               test     eax, eax
0x0049d8f8  7411               je       0x49d90b
0x0049d8fa  6a64               push     0x64
0x0049d8fc  8bce               mov      ecx, esi
0x0049d8fe  e81d5b0000         call     0x4a3420
0x0049d903  0fbfc3             movsx    eax, bx
0x0049d906  c644050001         mov      byte ptr [ebp + eax], 1
0x0049d90b  5f                 pop      edi
0x0049d90c  5e                 pop      esi
0x0049d90d  5d                 pop      ebp
0x0049d90e  5b                 pop      ebx
0x0049d90f  81c4ac080000       add      esp, 0x8ac
0x0049d915  c3                 ret      
0x0049d916  90                 nop      
0x0049d917  90                 nop      
0x0049d918  90                 nop      
0x0049d919  90                 nop      
0x0049d91a  90                 nop      
0x0049d91b  90                 nop      
0x0049d91c  90                 nop      
0x0049d91d  90                 nop      
0x0049d91e  90                 nop      
0x0049d91f  90                 nop      