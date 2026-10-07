# -*- coding: utf8 -*-
"""
child_stub.py —— M2 儿童预载桩 + M3a 随父居住 + M3b-2 五维起步 (x86 32 位, keystone 装配 + capstone 回读自检)

配方唯一来源: .rev/CHILD_STATE_RECIPE.md §2。本文件只把配方翻译成机器码, 不做判断。
表项数据(fslot/国/城)唯一来源: .rev/_kin.json (gen_kin.py) —— 换批次不改本文件。
成长常量(年龄/写手/BSDATA 镜像/档位)唯一来源: .rev/child_growth.py —— 两边共用, 不各写一份。

入口 (一块代码, 两个钩子):
  child_pass —— 幂等主循环, 逐条读排程表 (oid, slot, fslot, 国, 城):
      * 位图未记账 且 槽是空槽(bit15|bit7 双置, 即 0x808F 家族) ⇒ 实例化 + 落儿童态 + 记账
      * 位图已记账 且 槽 bit15=1(不在场) ⇒ 重新实例化 (剧本/池被重置的情形)
      * 位图已记账 且 槽 bit15=0(在岗)  ⇒ 复臂 (nibble=0xb + bit4=1)
      * 位图已记账 且 在岗 且 nibble 已经 ==0xf ⇒ **一个字节都不碰** (M4: 这是刚元服的孩子,
        复臂/重实例化都会把他拉回 0xb 儿童态, 于是每月再元服一次、FREEZE != CHILD_GENPUKU)
      * 位图未记账 且 槽被人占着        ⇒ 一个字节都不碰
    三条干活的路径末尾都调 place_child(随父居住), 所以孩子换城既发生在首次入场也发生在每月复臂。
    make_child 里 INST 之后调 init_stats: 五维 = (史实成年值+1)//2, 下限 5 (M3b-2 的 50% 起步)。
  month_hook —— 顶替 0x4A4CC5 `call 0x4a5370` (在 0x4a4d10 登场例程返回之后)
      M3b-2 起这一段是 **两个 call**: 先 child_pass(在场/复臂/搬家), 再 child_growth_pass(成长结算)
      ⇒ 成长只由"过了一月"驱动; load_hook 那一路不调成长 ⇒ 存/读一次不会把成长多算一跳。
  load_hook —— 顶替 0x47F71F `call 0x47f2a0`
              ★方向定论 2026-10: 0x47F71F 在 0x47F5C0 里, 而 0x47F5C0 只被保存派发器 0x47FC10
              (调用点 0x47FC40) 调用, 且它内部 0x47F6AF 调的是**写**链 0x47DF00 —— 所以这个钩子
              跑在**保存侧**, 不是载入侧(名字沿用历史, 别照着名字改行为)。
              child_pass 幂等(在岗只复臂+搬家, 不重跑 init_stats), 保存时多跑一趟无害;
              真正的"读档后重臂"现在由 M6 影子档回填(状态整体还原) + 月钩兜底(MISS/REJECT 归零后
              下一月按 位图未记账 + 空槽 重新实例化)。载入派发器 0x47FB80 的链尾 0x47FBEE 已被 M6 用掉。
              两个钩子体都是 `pushad → call… → popad → jmp 原callee`
              (pushad/popad 连 esp 一起还原 ⇒ 站点原有的 push 参数与 ecx(this) 逐位不受影响)

调用约定 (逐条实测, 见 CHILD_STATE_RECIPE.md §2 表格):
  0x47F7B0(slot, oid)  cdecl + `ret 8`(被调清栈), 首尾 push/pop ebx,ebp,esi,edi ⇒ 指针可跨调用保留
  状态访问器           `ecx = 实体; push arg; call`, 被调 `ret 4`, 只用 eax/ecx/edx
  归属原语(M4 用, 在 child_growth.py) 0x4A5100(本人, 主人) / 0x4A5290(本人) 都是 cdecl, **调用方清栈**
  (`add esp,8` / `add esp,4`) —— 证据是引擎自己调用点 0x4A525A/0x4A52E3/0x4A4FFD 后面就是这两条
"""
import struct

# ---- 引擎侧原语 (clean_dump 语义 VA; 均不在旧池区间 [0x519868,0x51DC56), 故 P1 不重定位) ----
INST = 0x47F7B0          # 实例化(槽, oid): BSDATA→47B 实体 + 姓/名表[slot*7]
A_BIT15 = 0x49A860       # (0) 清 bit15 → 在场/存活   [0x49A86F: and word[+0x2c],0x7fff; ret 4]
A_NIBSET = 0x49A6B0      # (v) 写状态字低 4 位 (xor 技巧, 只动 bits0..3)
A_BIT4 = 0x49A6D0        # (1) 置 bit4 排除 / (0) 清
A_BIT7CLR = 0x49A73F     # 清 bit7「无效」(参数不用但须配 ret 4 的栈) ⇒ 孩子不隐身 (§4)
A_RANK = 0x49A7E0        # (code) 写身分码 bits8..10 (`and 0xf8ff; or code<<8`)

NIBBLE_CHILD = 0xb       # 非 0xff ⇒ 免疫 0x4A4740 死亡抽签 + 0x4A4910 bit4 随机解禁 (§1.2)
EMPTY_MASK = 0x8080      # 空槽特征位 (bit15 不在场 + bit7 无效)
FLAGTAB = 0x519288       # 登场标志表 [oid]: 全镜像 4 个引用点, 代码从不清零, 且被原生存档序列化

MONTH_SITE, MONTH_JMP = 0x4A4CC5, 0x4A5370     # 月钩: 登场例程返回后下一条
LOAD_SITE, LOAD_JMP = 0x47F71F, 0x47F2A0       # ★名字沿用历史: 该站点在**保存**驱动 0x47F5C0 里 (见上面 load_hook)
SITE_ORIG = {MONTH_SITE: b'\xE8\xA6\x06\x00\x00', LOAD_SITE: b'\xE8\x7C\xFB\xFF\xFF'}

TERM = 0xFFFF
PUSHAD_MN = ('pushad', 'pushal')   # capstone 用 AT&T 名 pushal, keystone 源用 pushad —— 两边都认

# 排程表条目布局 (M3a 起 8 字节; 条目大小必须与 SRC 里的 `add ebx, ESZ` 同步)
#   +0 word oid      BSDATA 身份键
#   +2 word slot     池槽
#   +4 word fslot    父的池槽, 0xffff = 父不在原生池 (随父居住退用静态城)
#   +6 byte 国       静态兜底 (父的 S1/BSDATA 国)
#   +7 byte 城       静态兜底 (父的 S1/BSDATA 城)
ESZ = 8

# ---- M3a place_child: 随父居住 (见 SRC 里的 place_child 段) ----
#   原生 ent+0x24=国 / +0x25=城 (probe_keyspace 352/352)，相邻 ⇒ 一次 word 搬运。
#   动态优先: fslot 有效且父亲 bit15=0(在场) ⇒ 直接读父亲实体的 +0x24 ⇒ 父亲换城, 孩子下月跟着换;
#   否则退用表项 +6/+7 的静态城 (父亲的 S1 值; 父亲不在原生池时取他的 BSDATA 值)。
#   调用点两处: make_child 末尾(首次实例化) 与 rearm(每月自愈一次)。

SRC = """
child_pass:
  push ebx
  push esi
  push edi
  push ebp
  inc dword ptr [%(scan)s]
  ; 埋点: child_pass 开始 (0x41 = 'A')
  push 0x41
  call debug_log
  mov ebx, %(sched)s
next_entry:
  movzx eax, word ptr [ebx]
  cmp ax, 0xffff
  je done
  movzx edi, word ptr [ebx + 2]
  lea esi, [edi + edi * 2]
  shl esi, 4
  sub esi, edi
  add esi, %(pool)s
  movzx edx, word ptr [ebx + 2]
  bt dword ptr [%(bm)s], edx
  jc ours
  mov dx, word ptr [esi + 0x2c]
  and dx, 0x8080
  cmp dx, 0x8080
  jne foreign_skip
  call make_child
  inc dword ptr [%(preload)s]
  jmp after
ours:
  mov dx, word ptr [esi + 0x2c]
  movzx ax, dl
  and al, 0x0f
  cmp al, 0xf
  je after
  test dh, 0x80
  jz rearm
  call make_child
  inc dword ptr [%(preload)s]
  jmp after
rearm:
  mov ecx, esi
  push 0xb
  call %(a_nib)s
  mov ecx, esi
  push 1
  call %(a_bit4)s
  call place_child
  inc dword ptr [%(rearm)s]
  jmp after
foreign_skip:
  inc dword ptr [%(skip)s]
after:
  add ebx, %(esz)s
  jmp next_entry

make_child:
  movzx eax, word ptr [ebx]
  movzx edi, word ptr [ebx + 2]
  push eax
  push edi
  call %(inst)s
  call init_stats
  movzx eax, word ptr [ebx]
  mov ecx, esi
  push 0
  call %(a_bit15)s
  mov ecx, esi
  push 0
  call %(a_bit7)s
  mov ecx, esi
  push 0xb
  call %(a_nib)s
  mov ecx, esi
  push 1
  call %(a_bit4)s
  mov ecx, esi
  push 0
  call %(a_rank)s
  mov word ptr [esi + 0x2a], 0xffff
  ; ★ 标志表按 oid 索引，而五个状态原语都会改写 eax（A_RANK 返回的是状态字），
  ;   所以写表前必须从表项 +0 重新取 oid。
  movzx eax, word ptr [ebx]
  mov byte ptr [eax + %(flagtab)s], 1
  call place_child
  movzx edx, word ptr [ebx + 2]
  bts dword ptr [%(bm)s], edx
  ret

place_child:
  movzx ecx, word ptr [ebx + 4]
  cmp cx, 0xffff
  je pc_static
  lea eax, [ecx + ecx * 2]
  shl eax, 4
  sub eax, ecx
  add eax, %(pool)s
  mov dx, word ptr [eax + 0x2c]
  test dh, 0x80
  jnz pc_static
  mov dx, word ptr [eax + 0x24]
  mov word ptr [esi + 0x24], dx
  inc dword ptr [%(place)s]
  ret
pc_static:
  movzx eax, word ptr [ebx + 6]
  mov word ptr [esi + 0x24], ax
  inc dword ptr [%(place)s]
  ret

init_stats:
  movzx eax, word ptr [ebx]
  imul eax, eax, 0x3b
  add eax, %(bsd_dim0)s
  lea edx, [esi + 0x0a]
  mov edi, 5
is_dim:
  movzx ecx, byte ptr [eax]
  inc ecx
  shr ecx, 1
  cmp ecx, 5
  jae is_floor_ok
  mov ecx, 5
is_floor_ok:
  mov byte ptr [edx], cl
  inc eax
  inc edx
  dec edi
  jnz is_dim
  inc dword ptr [%(init5)s]
  ret

done:
  ; 埋点: child_pass 完成 (0x42 = 'B')
  push 0x42
  call debug_log
  pop ebp
  pop edi
  pop esi
  pop ebx
  ret

debug_log:
  push ebp
  mov ebp, esp
  sub esp, 0xA0
  push ebx
  push esi
  push edi
  ; 路径 "C:\taikou_debug.log\0" 放在 [ebp-0x14]..[ebp-0x04] (不覆盖保存的ebp)
  mov dword ptr [ebp - 0x14], 0x745C3A43
  mov dword ptr [ebp - 0x10], 0x6F6B6961
  mov dword ptr [ebp - 0x0C], 0x65645F75
  mov dword ptr [ebp - 0x08], 0x2E677562
  mov dword ptr [ebp - 0x04], 0x00676F6C
  ; OFSTRUCT (136字节) 放在 [ebp-0xA0] (有160字节空间, 足够)
  mov byte ptr [ebp - 0xA0], 0x9C
  mov byte ptr [ebp - 0x9F], 0
  push 0x1000
  lea eax, [ebp - 0xA0]
  push eax
  lea eax, [ebp - 0x14]
  push eax
  call dword ptr [0x4FB07C]
  ; ★ OpenFile 是 stdcall, 不清栈
  mov edi, eax
  cmp edi, -1
  je debug_log_end
  push 1
  lea eax, [ebp + 0x08]
  push eax
  push edi
  call dword ptr [0x4FB090]
  ; ★ _lwrite 是 stdcall, 不清栈
  push edi
  call dword ptr [0x4FB09C]
  ; ★ _lclose 是 stdcall, 不清栈
debug_log_end:
  pop edi
  pop esi
  pop ebx
  mov esp, ebp
  pop ebp
  ret 4

month_hook:
  pushad
  call %(pass)s
  call %(growth)s
  popad
  jmp %(month_jmp)s

load_hook:
  pushad
  call %(pass)s
  popad
  jmp %(load_jmp)s
"""


def build(pass_va, L):
    """装配整块桩代码。L 需含 pool/sched/bm/preload/rearm/skip/place/growth/init5 的 VA;
    pass_va = child_pass 落点。返回 (code, va, src, disasm_ins)"""
    from keystone import Ks, KS_ARCH_X86, KS_MODE_32, KS_OPT_SYNTAX_INTEL
    import child_growth as CG
    ks = Ks(KS_ARCH_X86, KS_MODE_32)
    ks.syntax = KS_OPT_SYNTAX_INTEL
    src = SRC % {k: v for k, v in
                 {'pool': '0x%X' % L['pool'], 'sched': '0x%X' % L['sched'], 'bm': '0x%X' % L['bm'],
                  'preload': '0x%X' % L['preload'], 'rearm': '0x%X' % L['rearm'],
                  'scan': '0x%X' % L['scan'], 'skip': '0x%X' % L['skip'],
                  'place': '0x%X' % L['place'], 'init5': '0x%X' % L['init5'],
                  'inst': '0x%X' % INST, 'growth': '0x%X' % L['growth'],
                  'bsd_dim0': '0x%X' % (CG.BSD_BASE + CG.BSD_DIM0),
                  'a_bit15': '0x%X' % A_BIT15, 'a_bit7': '0x%X' % A_BIT7CLR,
                  'a_nib': '0x%X' % A_NIBSET, 'a_bit4': '0x%X' % A_BIT4,
                  'a_rank': '0x%X' % A_RANK, 'flagtab': '0x%X' % FLAGTAB,
                  'month_jmp': '0x%X' % MONTH_JMP, 'load_jmp': '0x%X' % LOAD_JMP,
                  'pass': '0x%X' % pass_va, 'esz': '0x%X' % ESZ}.items()}
    CG.lint_src(src)
    # keystone 不支持 ; 注释(尤其含非 ASCII), 装配前剥掉
    import re as _re
    src_clean = _re.sub(r';[^\n]*', '', src)
    code = bytes(ks.asm(src_clean, pass_va)[0])
    va = entry_vas(code, pass_va)
    ins = selfcheck(code, pass_va, va, L)
    return code, va, src, ins


def entry_vas(code, origin):
    """按指令语义定位入口与钩子 (不写死偏移, 汇编长度变化也不会错位)。"""
    from capstone import Cs, CS_ARCH_X86, CS_MODE_32
    md = Cs(CS_ARCH_X86, CS_MODE_32)
    ins = list(md.disasm(code, origin))
    assert ins and ins[0].mnemonic == 'push' and ins[0].op_str == 'ebx', ins[:1]
    pads = [i for i in ins if i.mnemonic in PUSHAD_MN]
    assert len(pads) == 2, ('pushad 站点应为 2', [hex(p.address) for p in pads])
    mh = pads[0]
    before = [i for i in ins if i.address < mh.address]
    assert before and before[-1].mnemonic == 'ret', ('month_hook 前应是 done 的 ret', before[-2:])
    jmps = [i for i in ins if i.mnemonic == 'jmp' and i.op_str == '0x%x' % MONTH_JMP]
    assert len(jmps) == 1, jmps
    lh = [i for i in pads if i.address > jmps[0].address]
    assert len(lh) == 1, ('load_hook 定位失败', [hex(p.address) for p in pads], hex(jmps[0].address))
    assert lh[0].address == jmps[0].address + jmps[0].size, '两钩子之间不应有空隙'
    debug_log_va = None
    for i in ins:
        if i.mnemonic == 'call' and i.op_str.startswith('0x'):
            debug_log_va = int(i.op_str, 16)
            break
    assert debug_log_va is not None, '找不到 debug_log call 目标'

    def _head(op, nxt):
        """按 (首条指令, 第二条指令) 定位内部标签入口: 桩内代码增删后不用再手改地址。"""
        got = [i for k, i in enumerate(ins)
               if k + 1 < len(ins) and i.mnemonic == 'movzx' and i.op_str == op
               and ins[k + 1].op_str == nxt]
        assert len(got) == 1, ('标签定位 %s / %s 命中 %d 处' % (op, nxt, len(got)))
        return got[0].address

    _mk = _head('eax, word ptr [ebx]', 'edi, word ptr [ebx + 2]')      # make_child
    _ini = _head('eax, word ptr [ebx]', 'eax, eax, 0x3b')                # init_stats
    _pl = [i for i in ins if i.mnemonic == 'movzx' and i.op_str == 'ecx, word ptr [ebx + 4]']
    assert len(_pl) == 1, ('place_child 定位命中 %d 处' % len(_pl))
    return {'child_pass': origin, 'month_hook': mh.address, 'load_hook': lh[0].address,
            'debug_log': debug_log_va,
            'make_child': _mk, 'place_child': _pl[0].address, 'init_stats': _ini,
            'month_hook_sz': lh[0].address - mh.address,
            'load_hook_sz': 12,                       # pushad(1) call rel32(5) popad(1) jmp rel32(5)
            'stub_end': lh[0].address + 12}


def selfcheck(code, origin, va, L):
    """回读核对: 原语调用齐、儿童态常量齐、相对跳转不越界、钩子跳回原 callee。"""
    from capstone import Cs, CS_ARCH_X86, CS_MODE_32
    md = Cs(CS_ARCH_X86, CS_MODE_32)
    ins = list(md.disasm(code, origin))
    assert ins and sum(len(i.bytes) for i in ins) == len(code), '反汇编未覆盖全部字节'
    calls = {}
    for i in ins:
        if i.mnemonic == 'call' and i.op_str.startswith('0x'):
            t = int(i.op_str, 16)
            calls[t] = calls.get(t, 0) + 1
    must = {INST: 1, A_BIT15: 1, A_BIT7CLR: 1, A_RANK: 1,
            A_NIBSET: 2, A_BIT4: 2, va['child_pass']: 2}
    for k, n in must.items():
        assert calls.get(k) == n, ('调用次数不符 %08X 期望 %d 实得 %s / 全表 %s'
                                  % (k, n, calls.get(k), {hex(a): c for a, c in calls.items()}))
    internal = [a for a in calls if origin <= a < origin + len(code) and a != L['growth']]
    assert sum(calls[a] for a in internal) == 9 and len(internal) == 5, \
        ('桩内调用应为 make_child x2 + place_child x2 + init_stats x1 + child_pass x2 + debug_log x2: %s'
         % {hex(a): calls[a] for a in internal})
    assert calls.get(L['growth']) == 1, ('month_hook 应恰有一次调成长桩, 实得 %s' % calls.get(L['growth']))
    assert va['month_hook_sz'] == 17 and va['load_hook_sz'] == 12, \
        ('月钩 1 pushad+2 call+1 popad+1 jmp = 17B, 保存侧钩(历史名 load_hook)仍 12B: %d/%d'
         % (va['month_hook_sz'], va['load_hook_sz']))
    for i in ins:
        if i.mnemonic.startswith('j') and i.op_str.startswith('0x'):
            t = int(i.op_str, 16)
            assert origin <= t < origin + len(code) or t in (MONTH_JMP, LOAD_JMP), \
                ('跳转目标异常 %08X -> %08X' % (i.address, t))

    def need(mn, pat, n=1):
        got = [i for i in ins if i.mnemonic == mn and all(p in i.op_str for p in pat)]
        assert len(got) == n, ('缺少指令 %s %s (命中 %d, 期望 %d)' % (mn, pat, len(got), n))

    need('mov', ['word ptr [esi + 0x2a]', '0xffff'])
    _ft = [i for i in ins if i.mnemonic == 'mov' and 'byte ptr [eax + 0x519288]' in i.op_str]
    assert len(_ft) == 1, ('登场标志写应恰好 1 处, 实得 %d' % len(_ft))
    _prev = ins[ins.index(_ft[0]) - 1]
    assert (_prev.mnemonic, _prev.op_str) == ('movzx', 'eax, word ptr [ebx]'), \
        ('★标志表按 oid 索引: 写表前一条必须重新取表项 +0 的 oid (状态原语全都会改写 eax), 实得 %s %s'
         % (_prev.mnemonic, _prev.op_str))
    need('bt', ['0x%x' % L['bm']])
    need('bts', ['0x%x' % L['bm']])
    for key, n in (('scan', 1), ('preload', 2), ('rearm', 1), ('skip', 1), ('place', 2), ('init5', 1)):
        need('inc', ['dword ptr [0x%x]' % L[key]], n)
    need('cmp', ['0x8080'])
    need('cmp', ['ax', '-1'])      # 哨兵: keystone 把 0xffff 编成 imm16 = -1
    need('test', ['dh, 0x80'], 2)  # ours 分支查孩子 bit15 + place_child 查父亲 bit15
    need('and', ['dx, 0x8080'])
    # ★ 排程表游标必须前进: 漏了 `add ebx, ESZ` 就是"载入即死循环"(M2 曾踩过, 见 verify_children C13)
    need('add', ['ebx, %d' % ESZ], 1)
    need('mov', ['word ptr [esi + 0x24], dx'])     # 动态: 父之城
    need('mov', ['word ptr [esi + 0x24], ax'])     # 静态兜底
    need('movzx', ['word ptr [ebx + 4]'])          # fslot
    need('movzx', ['word ptr [ebx + 6]'])          # 兜底 国|城<<8
    # ---- M3b-2 init_stats: 五维 50% 起步 (成年值 -> (v+1)//2, 下限 5) ----
    need('imul', ['eax, eax, 0x3b'])                # oid × sizeof(BSDATA 记录) = oid*59
    need('add', ['eax, 0x%x' % (0x524A20 + 0x16)])  # 指向该 oid 的成年五维首字节
    need('shr', ['ecx, 1'])                        # 折半(round-half-up 由前面的 inc 完成)
    need('cmp', ['ecx, 5'])                        # 下限 5
    need('mov', ['byte ptr [edx], cl'])            # 写实体五维
    need('mov', ['edi, 5'])                        # 5 维循环
    assert any(i.mnemonic == 'jmp' and i.op_str == '0x%x' % LOAD_JMP for i in ins), \
        '钩子未跳回原 callee'
    # 前进指令必须排在**所有**分支汇合之后, 且**回到循环头的那条边就是它** ——
    # 任何"分支直接 jmp 循环头"的写法都会让游标不前进 = 载入即死循环 (M2 踩过, 见 verify_children C13)。
    _adv = [i for i in ins if i.mnemonic == 'add' and i.op_str == 'ebx, %d' % ESZ][0]
    _head = [i for i in ins if i.mnemonic == 'movzx' and i.op_str.endswith('[ebx]')][0].address
    _back = [i for i in ins if i.mnemonic == 'jmp' and i.op_str == '0x%x' % _head]
    assert len(_back) == 1 and _back[0].address > _adv.address and _back[0].address == _adv.address + _adv.size, \
        ('回边不唯一或不接在游标前进之后: %s' % [hex(b.address) for b in _back])
    return ins


def sched_bytes(entries):
    """排程表: ESZ 字节/条 (见上方 ESZ 注释的布局) + 0xFFFF 哨兵"""
    out = bytearray()
    for e in entries:
        out += struct.pack('<HHHBB', e['oid'], e['slot'], e.get('fslot', TERM),
                           e.get('pv', 0xFF), e.get('city', 0xFF))
    out += struct.pack('<HH', TERM, TERM)
    assert len(out) == ESZ * len(entries) + 4, (len(out), len(entries))
    return bytes(out)


if __name__ == '__main__':
    import json, sys, os
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass
    REV = os.path.dirname(os.path.abspath(__file__))
    lay = json.load(open(os.path.join(REV, '_big_layout.json'), encoding='utf-8'))
    M = lambda o: lay['mod_base'] + o
    L = {'pool': lay['pool_va'], 'sched': M(0x180), 'bm': M(0x100),
         'preload': M(0xC0), 'rearm': M(0xC4), 'scan': M(0xCC), 'skip': M(0xD0),
         'place': M(0xD4), 'init5': M(0xD8),      # 埋点紧跟 SKIP/PLACE 排; 0x100..0x17F 是儿童位图(CAP bit), 别放那
         'growth': lay['v']['CHILD_GROWTH']}      # 成长桩入口 (child_growth.py 装配落点)
    code, va, src, ins = build(M(0x1200), L)
    print('child_pass  %dB  @0x%06X  (month_hook %dB / load_hook %dB)'
          % (len(code), va['child_pass'], va['month_hook_sz'], va['load_hook_sz']))
    print('month_hook  @0x%06X   load_hook @0x%06X' % (va['month_hook'], va['load_hook']))
    for i in ins:
        print('  %08X  %-22s %s %s' % (i.address, i.bytes.hex(), i.mnemonic, i.op_str))
    ent = json.load(open(os.path.join(REV, '_child_preload.json'), encoding='utf-8'))['batches']['fam13']
    sb = sched_bytes(ent)
    print('排程表 %d 条 -> %dB, 放 0x%06X..0x%06X (区上界 0x%06X)'
          % (len(ent), len(sb), L['sched'], L['sched'] + len(sb), lay['section_va'] + lay['section_sz']))
    print('位图 %d bit 占 %dB @0x%06X (CAP=%d)' % (lay['cap'], lay['cap'] // 8, L['bm'], lay['cap']))
