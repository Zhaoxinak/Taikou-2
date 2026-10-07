# -*- coding: utf8 -*-
"""
tree_dyn.py —— v13 动态族谱的**运行时点亮桩** (x86-32, keystone 装配 + capstone 回读自检)

谁调用它: tree_render.tree_entry 在 [FAMP] 落定后 `call dword[DYN_FN]`(先判空, 所以
  没有 .edata 的 family.exe 完全不受影响)。它在开树的一瞬间做三件事:
    1) FAM_DIR.count 复位成 static_n(+21 那份只读真值) —— 否则上一次开树抬高的计数会残留;
    2) 扫实体池, 把「父链 +0x1d == 本人 oid」的人认作子嗣, 逐个把姓名写进串池**池首可变区**
       (每条 [u8 len][GBK<=14B][NUL], 槽位 j 复用), 已在本家族静态节点里出现过的 oid 跳过;
    3) count = static_n + 点亮数 —— 渲染层每帧重读 count, 于是多出来的框就有了名字和连线。
  几何(NODE_TAB 坐标/亲缘线)全是构建期烘死的, 桩里一条算术都没有: 手写 x86 少一处几何
  就少一处崩。

两条分支由 FAM_DIR+22 区分:
  0        史实家族(27 条 FAM_DIR): 「本人」= OIDTAB[start*2+subject] 那个 oid
                                   (+8 的 start 是 /2 编码的, 渲染层也是先 add eax,eax)
  GEN_FLAG 通用块(第 28 条):        「本人」= tree_entry 存进 DYN_SLOT 的这张武将卡的人,
                                   额外把他的姓名和「X氏」标题也写进池首 —— 这就是
                                   「审查所有人的族谱」: 27 家之外的人不再回落柴田树。

在岗判据为什么是**三条**而不是「(状态 & 0x8080) == 0x8080」一条: 0x8080 那条只认原生
  在岗成人。孩子(生出来的、也包含扩展槽预载的史实儿童)的状态字刻意带 bit4=1 且 bit15=0,
  实测值 0x001B / 家督国主 0x081B —— 用一条 0x8080 去筛会把孩子全部否掉, 于是
  「生了两个孩子, 族谱里还是没有」(实机 pid=13468: 木下太郎 slot477 oid694 +0x1d=16
  状态=0x001B, 丰臣氏 OIDTAB[64*2+2]=16, DYN_CALL=2 而 DYN_LIT=0)。所以门写成
  0x8080 在岗 / 0x879F==0x001B 儿童 / 0x879F==0x010F 元服后 三选一。
  注意 +0x1d 不是「史实儿童恒为 0xFFFF」: INST 会把 BSDATA 的父链抄进实体池, 预载儿童
  同样带真父亲(武田胜赖 463→199, 织田信忠 471→13), 因此他们出现在自己父亲的树上正是
  该要的行为, 不需要 CHILD_BM 再去排除。oid 未分配(0xFFFF)的本人仍然直接放弃整棵树,
  顺带把池首那两条记录清零, 免得留下上一个人的名字。
"""
import struct

GEN_FLAG = 1                  # 与 tree_data.GEN_FLAG 同步(build_big 两侧都断言)
LOCALS = 0x20                 # 桩自己的栈帧(pushad 之后)
# 帧内槽位(只列 SRC 真正用到的, 偏移改动要同步改 SRC)
L_DIR, L_SUBOID, L_FSTART, L_LIT, L_CHOID = 0x00, 0x04, 0x08, 0x0C, 0x14
assert max(L_DIR, L_SUBOID, L_FSTART, L_LIT, L_CHOID) + 2 <= LOCALS

SRC = """
  pushad
  sub esp, %(locals)s
  mov esi, dword ptr [%(famp)s]
  test esi, esi
  je td_ret
  mov dword ptr [esp + 0x0], esi
  movzx eax, byte ptr [esi + 0x15]
  mov byte ptr [esi + 0x9], al
  inc dword ptr [%(calls)s]
  cmp byte ptr [esi + 0x16], %(genflag)s
  je td_gen
  movzx eax, byte ptr [esi + 0x8]
  add eax, eax
  movzx ecx, byte ptr [esi + 0x14]
  add eax, ecx
  mov dword ptr [esp + 0x8], eax
  movzx edx, word ptr [eax * 2 + %(oidtab)s]
  cmp edx, 0xFFFF
  je td_nosub
  mov dword ptr [esp + 0x4], edx
  jmp td_scan
td_nosub:
  inc dword ptr [%(nosub)s]
  jmp td_ret
td_gen:
  mov byte ptr [%(gname)s], 0
  mov byte ptr [%(gtitle)s], 0
  movzx ebp, word ptr [%(slot)s]
  lea eax, [ebp + ebp * 2]
  shl eax, 4
  sub eax, ebp
  add eax, %(pool)s
  movzx edx, word ptr [eax + 0x2]
  cmp edx, 0xFFFF
  je td_ret
  mov dword ptr [esp + 0x4], edx
  mov dword ptr [esp + 0x8], %(gstart)s
  mov ebx, ebp
  mov esi, %(gname)s
  call td_putname
  mov ebx, ebp
  mov esi, %(gtitle)s
  call td_title
  jmp td_scan
td_scan:
  xor ebp, ebp
  mov word ptr [esp + 0xC], 0
ts_loop:
  cmp ebp, %(cap)s
  jae ts_end
  lea eax, [ebp + ebp * 2]
  shl eax, 4
  sub eax, ebp
  add eax, %(pool)s
  movzx ecx, word ptr [eax + 0x2C]
  mov edx, ecx
  and ecx, 0x8080
  cmp ecx, 0x8080
  je ts_live
  and edx, 0x879F
  cmp edx, 0x001B
  je ts_live
  cmp edx, 0x010F
  jne ts_next
ts_live:
  movzx ecx, word ptr [eax + 0x1D]
  cmp cx, word ptr [esp + 0x4]
  jne ts_next
  movzx ecx, word ptr [eax + 0x2]
  cmp cx, 0xFFFF
  je ts_next
  mov word ptr [esp + 0x14], cx
  mov esi, dword ptr [esp + 0x0]
  movzx edx, byte ptr [esi + 0x15]
  mov edi, dword ptr [esp + 0x8]
  xor eax, eax
ts_dup:
  cmp al, dl
  jae ts_light
  lea ecx, [edi + eax]
  movzx ecx, word ptr [ecx * 2 + %(oidtab)s]
  cmp cx, word ptr [esp + 0x14]
  je ts_next
  inc eax
  jmp ts_dup
ts_light:
  movzx eax, word ptr [esp + 0xC]
  cmp eax, %(slots)s
  jae ts_end
  shl eax, 4
  add eax, %(dynpool)s
  mov esi, eax
  mov ebx, ebp
  call td_putname
  movzx eax, word ptr [esp + 0xC]
  inc eax
  mov word ptr [esp + 0xC], ax
ts_next:
  inc ebp
  jmp ts_loop
ts_end:
  mov esi, dword ptr [esp + 0x0]
  movzx eax, byte ptr [esi + 0x15]
  movzx ecx, word ptr [esp + 0xC]
  add eax, ecx
  mov byte ptr [esi + 0x9], al
  mov dword ptr [%(lit)s], ecx
td_ret:
  add esp, %(locals)s
  popad
  ret
td_putname:
  lea edi, [esi + 0x1]
  xor ecx, ecx
  lea eax, [ebx * 8]
  sub eax, ebx
  add eax, %(giv)s
tp_s:
  mov dl, byte ptr [eax]
  test dl, dl
  je tp_g
  cmp ecx, 0x6
  jae tp_g
  mov byte ptr [edi], dl
  inc eax
  inc edi
  inc ecx
  jmp tp_s
tp_g:
  lea eax, [ebx * 8]
  sub eax, ebx
  add eax, %(sur)s
tp_c:
  mov dl, byte ptr [eax]
  test dl, dl
  je tp_end
  cmp ecx, 0xE
  jae tp_end
  mov byte ptr [edi], dl
  inc eax
  inc edi
  inc ecx
  jmp tp_c
tp_end:
  mov byte ptr [edi], 0
  mov byte ptr [esi], cl
  ret
td_title:
  lea edi, [esi + 0x1]
  xor ecx, ecx
  lea eax, [ebx * 8]
  sub eax, ebx
  add eax, %(giv)s
tt_s:
  mov dl, byte ptr [eax]
  test dl, dl
  je tt_chk
  mov byte ptr [edi], dl
  inc eax
  inc edi
  inc ecx
  cmp ecx, 0x6
  jb tt_s
tt_chk:
  test ecx, ecx
  jnz tt_app
  xor ecx, ecx
  lea edi, [esi + 0x1]
  lea eax, [ebx * 8]
  sub eax, ebx
  add eax, %(sur)s
tt_g:
  mov dl, byte ptr [eax]
  test dl, dl
  je tt_app
  mov byte ptr [edi], dl
  inc eax
  inc edi
  inc ecx
  cmp ecx, 0x6
  jb tt_g
tt_app:
  mov word ptr [edi], %(suffix)s
  add ecx, 0x2
  mov byte ptr [edi + 0x2], 0
  mov byte ptr [esi], cl
  ret
"""


def title_suffix_word(suffix):
    """「氏」的 GBK 双字节按小端拼成一个 word(桩里一次 mov word 写进去)"""
    b = suffix.encode('gbk')
    assert len(b) == 2, '标题后缀必须是单个 GBK 双字节汉字: %r' % suffix
    return struct.unpack('<H', b)[0]


def cap_op(v):
    """capstone 把**位移**和立即数用同一套口径渲染: <10 打十进制, >=0x10 打十六进制并补前导零到偶数位:
        [esi + 9] / [esp + 4] / [eax + 0x1d] / [eax + 0x2c]
    回读断言按同一套渲染比, 否则 '0x9' 永远匹配不到 '[esi + 9]'。"""
    return '%d' % v if v < 10 else '0x%x' % v


def _hexsubs(d):
    return {k: ('0x%X' % v if isinstance(v, int) else v) for k, v in d.items()}


def build(va, L):
    """L: famp oidtab pool cap giv sur dynpool gname gtitle gstart slots suffix
          slot lit calls nosub genflag locals
       -> (code, src)"""
    from keystone import Ks, KS_ARCH_X86, KS_MODE_32, KS_OPT_SYNTAX_INTEL
    import child_menu as CM
    subs = _hexsubs(L)
    src = SRC % subs
    CM.lint_src(src)
    ks = Ks(KS_ARCH_X86, KS_MODE_32)
    ks.syntax = KS_OPT_SYNTAX_INTEL
    code = bytes(ks.asm(src, va)[0])
    return code, src


def selfcheck(code, origin, L):
    """回读断言: 只查"这串机器码里确实有这几条关键指令"(次数按 SRC 实际出现数写死)。
    ★ 渲染口径全部走 cap_op/cap_imm: 位移/立即数 < 10 时 capstone 打**十进制**
      ('[esi + 9]' / 'cmp ..., 1'), 十六进制的写法一条都匹配不到。
      另外 capstone 把 pushad/popad 打成 **pushal/popal** (32 位默认操作数大小)。"""
    import child_menu as CM
    ins = CM._dis(code, origin)
    one, cnt, cntx = CM._mk(ins)
    co = cap_op
    # 1) count(+9) 只被写两次且形态相同: 开头复位成 static_n(+21), 末尾抬成 static_n+点亮数
    assert cnt('mov', 'byte ptr [esi + %s], al' % co(9)) == 2, '复位/抬高各一次'
    assert cnt('movzx', 'eax, byte ptr [esi + %s]' % co(0x15)) == 2, 'static_n 读两次(复位/抬高)'
    # 2) 分支门: FAM_DIR+22 判通用块
    one('cmp', 'byte ptr [esi + %s], %s' % (co(0x16), co(L['genflag'])))
    # 3) 史实分支的本人 oid 一定走 OIDTAB[start*2+subject] (start 是 /2 编码 => add eax,eax)
    one('add', 'eax, eax')
    one('movzx', 'edx, word ptr [eax*2 + 0x%x]' % L['oidtab'])
    # 4) 通用分支先清池首两条记录, 再写姓名/标题 (清了才不会有上一个人的残留)
    one('mov', 'byte ptr [0x%x], %s' % (L['gname'], co(0)))
    one('mov', 'byte ptr [0x%x], %s' % (L['gtitle'], co(0)))
    # 5) 亲子判据 = 父链 +0x1d 对本人 oid; 在岗判据 = **三条**都认:
    #    正常在场 (v&0x8080)==0x8080 / 儿童态签名 (v&0x879F)==0x001B / 元服后 (v&0x879F)==0x010F
    #    (★2026-10-07 实机: 只留第一条时 DYN_LIT 恒 0 —— 我们的孩子 bit15=0, 天生不过那条门)
    one('and', 'ecx, 0x8080')
    one('and', 'edx, ' + co(0x879F))
    one('cmp', 'edx, ' + co(0x1B))
    one('cmp', 'edx, ' + co(0x10F))
    one('movzx', 'ecx, word ptr [eax + %s]' % co(0x2c))
    one('mov', 'edx, ecx')
    one('cmp', 'cx, word ptr [esp + %s]' % co(0x4))
    one('movzx', 'ecx, word ptr [eax + %s]' % co(0x1d))
    # 6) 去重: 家族静态节点的 oid 命中就跳过 (对掉谱里已有的人)
    one('movzx', 'ecx, word ptr [ecx*2 + 0x%x]' % L['oidtab'])
    one('cmp', 'cx, word ptr [esp + %s]' % co(0x14))
    # 7) 姓行(GIV)/名行(SUR) 各被拼两处: putname + title
    assert cnt('lea', '[ebx*8]') == 4, '行址计算应是 putname 2 次 + title 2 次'
    assert cnt('add', 'eax, 0x%x' % L['giv']) == 2, '姓表应有 2 处(孩子/本人 + 标题)'
    assert cnt('add', 'eax, 0x%x' % L['sur']) == 2, '名表应有 2 处(孩子/本人 + 标题回落)'
    # 8) 长度前缀最后写: [rec] = cl  (putname/title 各一次)
    assert cnt('mov', 'byte ptr [esi], cl') == 2, '长度前缀应各写一次'
    # 9) 标题后缀一个 word 写进去
    one('mov', 'word ptr [edi], 0x%x' % L['suffix'])
    # 10) 抬 count = static_n + 点亮数, 并把点亮数落埋点
    assert cnt('add', 'eax, ecx') == 2, '一处是 start+subject, 一处是 static_n+lit'
    one('mov', 'dword ptr [0x%x], ecx' % L['lit'])
    # 11) 栈平衡: pushal/popal 各 1, 局部帧 sub/add 同值
    assert cntx('pushal', '') == 1 and cntx('popal', '') == 1, 'pushal/popal 必须各 1 条'
    one('sub', 'esp, 0x%x' % L['locals'])
    one('add', 'esp, 0x%x' % L['locals'])
    # 12) 槽上限(不越写池首) + 池槽遍历上限都要在
    one('cmp', 'eax, %s' % co(L['slots']))
    one('cmp', 'ebp, 0x%x' % L['cap'])
    # 13) call 全部落在本桩之内(不能调到桩外); 且三个写姓名的 call 前都必须先摆好 ebx/esi
    n = 0
    for i in ins:
        if i.mnemonic == 'call':
            tgt = int(i.op_str, 16)
            assert origin <= tgt < origin + len(code), ('call 越出桩体', i.ins_str)
            n += 1
    assert n == 3, '应当恰有 3 个 call: 本人姓名 / 本人标题 / 子嗣姓名 (现在 %d)' % n
    return ins
