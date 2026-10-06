# -*- coding: utf8 -*-
"""
child_save.py —— M6 sidecar 影子存档 TKMODSAVE_<槽>.DAT (x86 32 位, keystone 装配 + capstone 回读自检)

要解决的问题: 原生存档序列化器 0x47DCE0(读)/0x47DF00(写) 的循环界是 **0x172=370 槽**(4 处 0x172
保留不动 = 文件格式锚), 所以扩展槽 370..CAP-1 里的人、以及 KID_TAB/CMD_RING/儿童位图这些 MOD 私有
状态, 在 SAVEDATA.TR2 里根本没有位置 —— 读档即消失。本模块用一份**旁路文件**把它们整体带走。

★ 方向定论(2026-10-05 复测, 五条独立证据; 老文档里"0x47F5C0=存档/剧本载入函数"的说法是错的):
    0x47F350 = **载入**驱动 —— 调用者 0x47FB80 用 `push 2; push 0` 走 0x47D720 => OpenFile 码 0=OF_READ,
               并且带 [obj+0x8c]=1 的**预校验遍** + =0 的**真读遍**两次调用同一个驱动;
    0x47F5C0 = **保存**驱动 —— 调用者 0x47FC10 用 `push 2; push 1` => OF_WRITE, 只跑一遍;
    0x47D910/0x47D930(读原语) 在 [obj+0x8c]!=0 时"读了但不写内存" => 只可能出现在载入链;
    0x47DA80/0x47DAC0(写原语) 把值写进缓冲区 => 只可能出现在保存链;
    0x47DCE0(链成员) 37 次取**地址**调用读原语, 0x47DF00 同序 37 次取值调用写原语 —— 逐字段互逆。
  ⇒ 顺带纠正: child_stub 的 LOAD_SITE 0x47F71F 在 0x47F5C0 里, 那是**保存侧**钩子(不是载入钩)。

钩点选择(两个派发器的"链跑完、原生句柄还没关"那一发 `call 0x47D850`, 位置完全对称):
    保存 SITE_SAVE 0x47FC49  0x47FC10 派发器: call 0x47F5C0 之后 -> call 0x47D850  原字节 E8 02 DC FF FF
    载入 SITE_LOAD 0x47FBEE  0x47FB80 派发器: 真读遍之后       -> call 0x47D850  原字节 E8 5D DC FF FF
  好处: 每方向**只触发一次**(不会撞上预校验遍), 原生池已被整体恢复/尚未被后续环节改动, 摘要对得上;
        载入侧若预校验失败(走 je 0x47FBEA 落点, [obj+0x8c] 仍是 1) => 桩一个字节都不碰(SIDECAR_GATE)。

文件(每槽一份, 与 SAVEDATA.TR2 同目录同名规则 —— 引擎自己也是 OpenFile 前砍掉 "X:" 走相对路径,
     见 0x4EC8C0 `add eax,2`; Win16 OpenFile 的 OF_CREATE 会截断, 所以多槽不能挤在一个文件里):
    TKMODSAVE_0.DAT .. TKMODSAVE_7.DAT   (槽号取自 [obj+0x96] = slot*0xA000+0x198, 最多 8 槽)
    布局 = 0x30 头 + 6 段连续数据(唯一真源 BLOCKS(), 保存写什么、载入就读什么):
      扩展槽实体 [N0..CAP) 47B/槽 | 姓表行 7B/槽 | 名表行 7B/槽 | 儿童位图 CAP/8 | KID_TAB CAP*12 | CMD_RING 0x220
    全 16 位计数安全(最大一段 30738 < 0xFFFF), 一次 _lwrite/_lread 走完一段 => 每方向 ~9 次系统调用。

完整性分层(不依赖 _lread/_lwrite 返回值宽度的细节, 也不探测文件位置):
    **每一段都必须读/写满请求字节数** —— 头 0x30 + 六段的满额检查本身就是截断/半截写入的闸门,
      所以不用 `_llseek(h,0,2)` 探长度(探完位置就跑到档尾, 后面什么也读不到; 引擎自己也不看它的返回值);
    头里 magic/ver/cap/slot/n0/payload/commit 逐字段比; 实体+姓名表都是按槽定序, 顺序错不得;
    再拿"原生池摘要"当**配对键**: 保存时算 NEW..NEW+47*370, 载入时重算比对 —— 不同剧本/不同存档
      的原生池必然不同, 于是绝不会把 A 档的影子贴到 B 档上; 对不上 => sc_reset(扩展槽回空槽态)。
    载入方向还先看引擎的预校验门 [obj+0x8c](派发器给校验遍置 1、真读遍置 0; 校验失败就直接跳到
      链尾关闭, 那个 1 会留着) —— 门开着才动, 坏档一个字节都不碰, 计入 SIDECAR_GATE。
    摘要刻意跳过每条记录的 +4..+7: 那是引擎的池内指针, 存的是"槽号"、载入时用 `idx*47+池基` 重算
      (0x47DD64), 且 idx>=370 会被判 0 => 它是**派生字段**, 进摘要会造成假 REJECT。
"""
import struct

# ---------------- 引擎侧地址 (clean_dump 语义 VA; 见上面的方向定论) ----------------
CLOSE_FN = 0x47D850             # (ecx=存档流对象) _lclose([obj]) —— 两个派发器链尾都在调它, 我们顶替它
SITE_SAVE, ORIG_SAVE = 0x47FC49, b'\xE8\x02\xDC\xFF\xFF'    # 0x47FC10: call 0x47D850 (保存链之后)
SITE_LOAD, ORIG_LOAD = 0x47FBEE, b'\xE8\x5D\xDC\xFF\xFF'    # 0x47FB80: call 0x47D850 (载入真读遍之后)
BACK_SAVE, BACK_LOAD = SITE_SAVE + 5, SITE_LOAD + 5

# kernel32 的 Win16 兼容导出 (IAT 在 .data; 全是 stdcall —— 0x4EC91F/0x441185/0x47D880/0x47D853
# 四处 call 之后调用者都**不**清栈, 只有 0x47D860 那种 ret 4 是引擎自己的包装)
TH_OPENFILE = 0x4FB07C          # OpenFile(path, OFSTRUCT*, code) -> HFILE, -1=失败 (0x4EC91F 实测)
TH_LWRITE = 0x4FB090            # _lwrite(h, buf, cnt) -> 写入字节数
TH_LCLOSE = 0x4FB09C            # _lclose(h)
TH_LREAD = 0x4FB0A0             # _lread(h, buf, cnt) -> 读出字节数
TH_LLSEEK = 0x4FB0A8            # _llseek(h, off, from) -> 新位置 (from 0=BEGIN 1=CUR 2=END)
#   ★ M6 桩不用它: 截断由"每段读满额"把关; 而 seek 到档尾会把读位置一起带走(踩过这个坑)。
OF_READ = 0x0000                # 引擎载入用 0 (0x4EC8F3)
OF_CREATE = 0x1000              # 引擎新建用 0x1000 (0x4EC911); 会截断既有文件
OF_RW = 0x0002
OPEN_SAVE = OF_RW | OF_CREATE   # 0x1002
OPEN_LOAD = OF_READ             # 0
FROM_END = 2

# 存档流对象字段 (esi/ecx 在两驱动里都是它; 布局由 0x47D860/0x47D910/0x47F724/0x47F430 反证)
OBJ_GATE = 0x8c                 # word: !=0 => 读原语"只校验不落内存"(引擎预校验遍/原生校验失败)
OBJ_RECBASE = 0x96              # dword: 本槽记录基址 = slot*0xA000 + 0x198 (0x47D860 写它)
REC_HDR, REC_SIZE, SLOT_MAX = 0x198, 0xA000, 8      # 408 头 + 8 槽 x 40960 = SAVEDATA.TR2

# ---------------- 影子存档格式 ----------------
MAGIC = 0x44534B54              # 'TKSD'
COMMIT = 0x3144534B             # 'KSD1'
VER = 1
HDR_SZ = 0x30
HD_MAGIC, HD_VER, HD_CAP, HD_SLOT, HD_N0, HD_PAYLOAD, HD_DIGEST, HD_COMMIT, HD_RECN = (
    0x00, 0x04, 0x06, 0x08, 0x0A, 0x0C, 0x10, 0x14, 0x18)
BLK_ENT_SZ, BLK_SRC, BLK_LEN = 8, 0, 4
PATH_TMPL = 'TKMODSAVE_0.DAT'
PATH_DIGIT = 10                 # 槽号数字所在字节 (TKMODSAVE_ 之后第 1 个)
PATH_SZ = 16
OFS_SZ = 0x88                   # Win32 OFSTRUCT = 136B (OpenFile 会往里写 szPathName[128])

# SC_DATA 内字段偏移 (桩与构建共用, 别两边各写一份)
D_PATH, D_HDR, D_BLK, D_HND, D_SLOT, D_DIG, D_CUR, D_TMPL, D_OFS = (
    0x000, 0x010, 0x040, 0x078, 0x07C, 0x080, 0x084, 0x088, 0x0B8)
SC_DATA_SZ = 0x140              # D_OFS + OFS_SZ = 0x0B8+0x88 = 0x140
RING_SZ = 0x220                 # CMD_RING: 头 8B + 64 条 x 8B (child_growth RING_* 口径)
VACANT_STATE = 0x808F           # 空槽状态字 (模板自带, 见 build_big 4c)
ENT_SZ = 47                     # sizeof(实体)

# 埋点顺序 = GROWTH_CTRS 追加顺序 (verify/tkwatch 按下标取, 加一项 append 一项, 别插中间)
SC_CTRS = ['SIDECAR_SAVE',      # 保存方向: 槽号合法, 准备写影子档
           'SIDECAR_SAVED',     # 保存方向: 头+6 段全部写完并关闭 => = 你按保存的次数
           'SIDECAR_WERR',      # 保存方向: OpenFile 失败 或 写不满 => 影子档没落地
           'SIDECAR_SLOT',      # [obj+0x96] 解析不出 0..7 槽 (应恒 0; 涨了=钩点上下文变了)
           'SIDECAR_LOAD',      # 载入方向: 影子档已打开
           'SIDECAR_RESTORE',   # 载入方向: 长度+头+摘要全过, 6 段已回填 => 孩子保住了
           'SIDECAR_MISS',      # 载入方向: 该槽没有影子档(老存档/换机) => 扩展槽归零
           'SIDECAR_REJECT',    # 载入方向: 有文件但校验不过(半截写/贴错档/剧本不符) => 归零
           'SIDECAR_GATE']      # 原生预校验失败([obj+0x8c]!=0) => 桩不碰扩展槽 (应 = 坏档次数)


def blocks(L):
    """唯一真源: 影子档里的 6 段连续数据 [(VA, 字节数)], 顺序 = 文件顺序。
    L 需含 pool/stride/n0/cap/giv/sur/bm/kid_tab/kid_esz/sect_va/sect_sz。"""
    n = L['cap'] - L['n0']
    bl = [(L['pool'] + L['stride'] * L['n0'], L['stride'] * n, '扩展槽实体'),
          (L['giv'], 7 * n, '姓表行', ),
          (L['sur'], 7 * n, '名表行'),
          (L['bm'], L['cap'] // 8, '儿童位图'),
          (L['kid_tab'], L['cap'] * L['kid_esz'], 'KID_TAB'),
          (L['ring'], RING_SZ, 'CMD_RING')]
    out = []
    for e in bl:
        va, sz = e[0], e[1]
        assert sz > 0 and sz <= 0xFFFF, ('单段长度必须能塞进 16 位计数', e)
        assert L['sect_va'] <= va and va + sz <= L['sect_va'] + L['sect_sz'], ('段越出 .edata', e)
        out.append((va, sz))
    for i, (a, sa) in enumerate(out):
        for j, (b2, sb) in enumerate(out):
            if i < j:
                assert not (a < b2 + sb and b2 < a + sa), ('影子档两段重叠', out[i], out[j])
    return out


def block_pairs(L):
    return [(va, sz) for va, sz in blocks(L)]


def payload_len(L):
    return sum(sz for _, sz in blocks(L))


def file_len(L):
    return HDR_SZ + payload_len(L)


def blktab_bytes(L):
    """6 条描述符 + 终止条目(len=0) 落进 SC_DATA+D_BLK (桩两个方向都只认这张表)"""
    out = bytearray()
    for va, sz in blocks(L):
        out += struct.pack('<II', va, sz)
    out += struct.pack('<II', 0, 0)
    assert len(out) == BLK_ENT_SZ * (len(L and blocks(L)) + 1) == 0x38, len(out)
    return bytes(out)


def path_bytes():
    b = PATH_TMPL.encode('ascii') + b'\x00'
    assert len(b) <= PATH_SZ and b[PATH_DIGIT:PATH_DIGIT + 1] == b'0', b
    return b.ljust(PATH_SZ, b'\x00')


def header_bytes(L, slot, digest):
    """Python 参考实现(与桩写的字段逐位同规格; 也给人拿 hexdump 对)"""
    h = bytearray(HDR_SZ)
    struct.pack_into('<I', h, HD_MAGIC, MAGIC)
    struct.pack_into('<H', h, HD_VER, VER)
    struct.pack_into('<H', h, HD_CAP, L['cap'])
    struct.pack_into('<H', h, HD_SLOT, slot)
    struct.pack_into('<H', h, HD_N0, L['n0'])
    struct.pack_into('<I', h, HD_PAYLOAD, payload_len(L))
    struct.pack_into('<I', h, HD_DIGEST, digest)
    struct.pack_into('<I', h, HD_COMMIT, COMMIT)
    struct.pack_into('<I', h, HD_RECN, L['cap'] - L['n0'])
    return bytes(h)


def parse_header(h):
    assert len(h) == HDR_SZ, len(h)
    d = dict(magic=u(h, HD_MAGIC), ver=u16(h, HD_VER), cap=u16(h, HD_CAP), slot=u16(h, HD_SLOT),
             n0=u16(h, HD_N0), payload=u(h, HD_PAYLOAD), digest=u(h, HD_DIGEST),
             commit=u(h, HD_COMMIT), recn=u(h, HD_RECN))
    return d


def accept_header(L, h):
    """Python 侧同一条判定链(载入桩逐字段的镜像), 给参考实现/自检用"""
    d = parse_header(h)
    return (d['magic'] == MAGIC and d['ver'] == VER and d['cap'] == L['cap']
            and d['n0'] == L['n0'] and d['payload'] == payload_len(L)
            and d['commit'] == COMMIT and d['slot'] == L['_slot'])


def digest_ref(pool_bytes, stride=ENT_SZ, n0=None):
    """参考摘要: 逐条记录取 +0..+3 双字、跳过 +4..+7 派生指针、+8..+43 九个双字、+44 字、+46 字节;
    每取一次 `add edx, v; rol edx, 3`。桩里就是这段语义, 两边同一组常量。"""
    m = 0xFFFFFFFF
    if n0 is None:
        n0 = len(pool_bytes) // stride
    acc = 0
    for i in range(n0):
        r = pool_bytes[i * stride:(i + 1) * stride]
        assert len(r) == stride, (i, len(r))
        vals = [struct.unpack_from('<I', r, 0)[0]]
        vals += [struct.unpack_from('<I', r, o)[0] for o in range(8, 44, 4)]
        vals += [struct.unpack_from('<H', r, 44)[0], r[46]]
        for v in vals:
            acc = _rotl((acc + v) & m, 3)
    return acc


def _rotl(v, n):
    m = 0xFFFFFFFF
    return ((v << n) | (v >> (32 - n))) & m


def u(b, o):
    return struct.unpack_from('<I', b, o)[0]


def u16(b, o):
    return struct.unpack_from('<H', b, o)[0]


# ---------------- 桩源码 ----------------
# 内部函数一律 `ret`(参数走寄存器, 不靠栈), 只有对 Win16 兼容导出 call 之后不清栈(它们是 stdcall)。
# trampoline 用 pushad/popad 包住, 所以桩内 eax..edi 可随便用; esi 进来时已被搬成 ecx(存档流对象)。
SC_SRC = """
  pushad
  mov esi, ecx
  call sc_save
  popad
  call %(close)s
  jmp %(back_save)s
  pushad
  mov esi, ecx
  call sc_load
  popad
  call %(close)s
  jmp %(back_load)s

sc_save:
  cld
  mov eax, dword ptr [esi + %(o_recbase)s]
  call sc_slotpath
  test eax, eax
  jz ssv_slot
  inc dword ptr [%(c_save)s]
  call sc_digest
  mov dword ptr [%(dig)s], eax
  mov dword ptr [%(f_dig)s], eax
  mov dword ptr [%(f_mag)s], %(magic)s
  mov word ptr [%(f_ver)s], %(ver)s
  mov word ptr [%(f_cap)s], %(cap)s
  mov word ptr [%(f_n0)s], %(n0)s
  mov dword ptr [%(f_pay)s], %(payload)s
  mov dword ptr [%(f_com)s], %(commit)s
  mov dword ptr [%(f_recn)s], %(extn)s
  mov eax, dword ptr [%(slot)s]
  mov word ptr [%(f_slot)s], ax
  mov edx, %(open_save)s
  call sc_open
  cmp eax, %(neg1)s
  je ssv_werr
  mov dword ptr [%(hnd)s], eax
  mov edx, %(hdr)s
  mov ecx, %(hdr_sz)s
  call sc_w
  cmp eax, ecx
  jne ssv_err
  call sc_blocks_w
  test eax, eax
  jnz ssv_err
  call sc_close
  inc dword ptr [%(c_saved)s]
  ret
ssv_err:
  call sc_close
  inc dword ptr [%(c_werr)s]
  ret
ssv_werr:
  inc dword ptr [%(c_werr)s]
  ret
ssv_slot:
  inc dword ptr [%(c_slot)s]
  ret

sc_load:
  cld
  cmp word ptr [esi + %(o_gate)s], 0
  jne sld_gate
  mov eax, dword ptr [esi + %(o_recbase)s]
  call sc_slotpath
  test eax, eax
  jz sld_slot
  xor edx, edx
  call sc_open
  cmp eax, %(neg1)s
  jne sld_open
  inc dword ptr [%(c_miss)s]
  jmp sc_reset
sld_open:
  mov dword ptr [%(hnd)s], eax
  inc dword ptr [%(c_load)s]
  mov edx, %(hdr)s
  mov ecx, %(hdr_sz)s
  call sc_r
  cmp eax, ecx
  jne sld_rej
  cmp dword ptr [%(f_mag)s], %(magic)s
  jne sld_rej
  cmp word ptr [%(f_ver)s], %(ver)s
  jne sld_rej
  cmp word ptr [%(f_cap)s], %(cap)s
  jne sld_rej
  cmp word ptr [%(f_n0)s], %(n0)s
  jne sld_rej
  cmp dword ptr [%(f_pay)s], %(payload)s
  jne sld_rej
  cmp dword ptr [%(f_com)s], %(commit)s
  jne sld_rej
  movzx eax, word ptr [%(f_slot)s]
  cmp eax, dword ptr [%(slot)s]
  jne sld_rej
  call sc_digest
  mov dword ptr [%(dig)s], eax          # 现场重算值留档(头部那份是**文件里**的值, REJECT 时两者可对照)
  cmp eax, dword ptr [%(f_dig)s]
  jne sld_rej
  call sc_blocks_r
  test eax, eax
  jnz sld_rej
  call sc_close
  inc dword ptr [%(c_restore)s]
  ret
sld_gate:
  inc dword ptr [%(c_gate)s]
  ret
sld_slot:
  inc dword ptr [%(c_slot)s]
  ret
sld_rej:
  call sc_close
  inc dword ptr [%(c_reject)s]
  jmp sc_reset

# ---- 归零: 扩展槽回"尾空槽"原貌(模板 47B + id word=槽号), 姓名表行与三块私有区清零 ----
#   与 build_big 4c 的静态初始化同一份模板、同一步 sub; 7B 行只用 rep stosb 逐字节清(绝不用 qword)。
sc_reset:
  cld
  xor ebx, ebx
ssr_rec:
  imul edi, ebx, %(ent_sz)s
  add edi, %(ext_pool)s
  lea edx, [ebx + %(n0)s]
  push edi
  mov esi, %(tmpl)s
  mov ecx, %(ent_sz)s
  rep movsb
  pop edi
  mov word ptr [edi], dx
  imul eax, ebx, 7
  lea edi, [%(ext_giv)s + eax]
  xor eax, eax
  mov ecx, 7
  rep stosb
  lea edi, [%(ext_sur)s + eax]
  mov ecx, 7
  rep stosb
  inc ebx
  cmp ebx, %(extn)s
  jb ssr_rec
  mov edi, %(bm)s
  xor eax, eax
  mov ecx, %(bm_sz)s
  rep stosb
  mov edi, %(kid)s
  mov ecx, %(kid_sz)s
  rep stosb
  mov edi, %(ring)s
  mov ecx, %(ring_sz)s
  rep stosb
  ret

# ---- 槽号: [obj+0x96] = slot*0xA000 + 0x198 (由 0x47D860 写: `and 0xffff / *5 / shl 0xd / +0x198`) ----
#   减法循环取槽号(最多 8 槽), 顺手把槽号写进文件名里那一位。
#   返回值 = slot+1 (0 = 非法), 免得拿 -1 当哨兵; 槽号另存 [slot] 给头部字段用。
sc_slotpath:
  cmp eax, %(rec_hdr)s
  jb sp_bad
  sub eax, %(rec_hdr)s
  mov ecx, %(rec_size)s
  xor edx, edx
sp_loop:
  sub eax, ecx                      # 减不动即借位 => 已减到不足一个槽宽, edx 就是槽号
  jb sp_hit                         # (这里刻意不用 cmp eax,ecx —— 那对寄存器留给"读写满额"闸门, 自检按它计数)
  inc edx
  cmp edx, %(slot_max)s
  jb sp_loop
sp_bad:
  xor eax, eax
  ret
sp_hit:
  mov dword ptr [%(slot)s], edx
  or dl, 0x30
  mov byte ptr [%(f_pathdig)s], dl
  lea eax, [edx + 1]
  ret

# ---- 配对键: 原生池 NEW..NEW+47*370 逐条哈希(跳过 +4..+7 的派生指针) ----
sc_digest:
  mov edi, %(pool)s
  mov ebp, %(n0)s
  xor ebx, ebx
sdg_rec:
  mov eax, dword ptr [edi]
  add ebx, eax
  rol ebx, 3
  add edi, 8
  mov ecx, 9
sdg_q:
  mov eax, dword ptr [edi]
  add ebx, eax
  rol ebx, 3
  add edi, 4
  dec ecx
  jnz sdg_q
  movzx eax, word ptr [edi]
  add ebx, eax
  rol ebx, 3
  movzx eax, byte ptr [edi + 2]
  add ebx, eax
  rol ebx, 3
  add edi, 3
  dec ebp
  jnz sdg_rec
  mov eax, ebx
  ret

# ---- 六段循环: 保存写 / 载入读, 同一张描述符表, 游标放内存(stdcall 可能毁寄存器) ----
sc_blocks_w:
  mov eax, %(blk)s
  mov dword ptr [%(cur)s], eax
sbw_loop:
  mov eax, dword ptr [%(cur)s]
  mov ecx, dword ptr [eax + %(blk_len)s]
  test ecx, ecx
  jz sbw_done
  push ecx
  mov edx, dword ptr [eax + %(blk_src)s]
  call sc_w
  pop ecx
  cmp eax, ecx
  jne sbw_fail
  add dword ptr [%(cur)s], %(blk_ent)s
  jmp sbw_loop
sbw_done:
  xor eax, eax
  ret
sbw_fail:
  mov eax, %(neg1)s
  ret

sc_blocks_r:
  mov eax, %(blk)s
  mov dword ptr [%(cur)s], eax
sbr_loop:
  mov eax, dword ptr [%(cur)s]
  mov ecx, dword ptr [eax + %(blk_len)s]
  test ecx, ecx
  jz sbr_done
  push ecx
  mov edx, dword ptr [eax + %(blk_src)s]
  call sc_r
  pop ecx
  cmp eax, ecx
  jne sbr_fail
  add dword ptr [%(cur)s], %(blk_ent)s
  jmp sbr_loop
sbr_done:
  xor eax, eax
  ret
sbr_fail:
  mov eax, %(neg1)s
  ret

# ---- Win16 兼容 API 薄包装: 参数全走寄存器, call 后不清栈(stdcall) ----
sc_open:
  push edx
  push %(ofs)s
  push %(path)s
  call dword ptr [%(th_open)s]
  ret

sc_w:
  push ecx
  push edx
  push dword ptr [%(hnd)s]
  call dword ptr [%(th_write)s]
  ret

sc_r:
  push ecx
  push edx
  push dword ptr [%(hnd)s]
  call dword ptr [%(th_read)s]
  ret

sc_close:
  push dword ptr [%(hnd)s]
  call dword ptr [%(th_close)s]
  ret
"""


CTR_PH = ['c_save', 'c_saved', 'c_werr', 'c_slot', 'c_load', 'c_restore',
          'c_miss', 'c_reject', 'c_gate']        # 与 SC_CTRS 一一对应, 顺序即埋点顺序
assert len(CTR_PH) == len(SC_CTRS), '埋点占位符与 SC_CTRS 不一致'

# 头部九字段: 桩里只用**折好的绝对地址** —— keystone 原样保留 `[base + disp]` 写法,
#   capstone 回读却可能折叠成单个 disp32, 两边口径不一致会让自检的子串匹配飘掉。
HD_FIELDS = {'mag': HD_MAGIC, 'ver': HD_VER, 'cap': HD_CAP, 'slot': HD_SLOT, 'n0': HD_N0,
             'pay': HD_PAYLOAD, 'dig': HD_DIGEST, 'com': HD_COMMIT, 'recn': HD_RECN}


def _subs(code_va, L):
    """★ 立即数一律 0x 前缀(keystone 把裸多位十进制当十六进制吃, 见 child_growth.lint_src)。
    L 需含 pool/stride/n0/cap/giv/sur/bm/kid_tab/kid_esz/ring + data_delta(= SC_DATA - SC_CODE)
    + ctr{埋点名: VA}。"""
    pay = sum(sz for _, sz in blocks(L))
    X = lambda v: '0x%X' % v
    h = lambda k: X(code_va + L['data_delta'] + k)
    d = {'close': X(CLOSE_FN), 'back_save': X(BACK_SAVE), 'back_load': X(BACK_LOAD),
         'o_gate': X(OBJ_GATE), 'o_recbase': X(OBJ_RECBASE),
         'rec_hdr': X(REC_HDR), 'rec_size': X(REC_SIZE), 'slot_max': X(SLOT_MAX),
         'th_open': X(TH_OPENFILE), 'th_write': X(TH_LWRITE), 'th_read': X(TH_LREAD),
         'th_seek': X(TH_LLSEEK), 'th_close': X(TH_LCLOSE),
         'open_save': X(OPEN_SAVE), 'from_end': X(FROM_END), 'neg1': X(0xFFFFFFFF),
         'magic': X(MAGIC), 'commit': X(COMMIT), 'ver': X(VER),
         'cap': X(L['cap']), 'n0': X(L['n0']), 'extn': X(L['cap'] - L['n0']),
         'payload': X(pay), 'total': X(HDR_SZ + pay), 'hdr_sz': X(HDR_SZ),
         'path': h(D_PATH), 'hdr': h(D_HDR), 'blk': h(D_BLK),
         'hnd': h(D_HND), 'slot': h(D_SLOT), 'dig': h(D_DIG), 'cur': h(D_CUR),
         'tmpl': h(D_TMPL), 'ofs': h(D_OFS),
         'blk_ent': X(BLK_ENT_SZ), 'blk_src': X(BLK_SRC), 'blk_len': X(BLK_LEN),
         'pool': X(L['pool']), 'stride': X(L['stride']), 'ent_sz': X(ENT_SZ),
         'ext_pool': X(L['pool'] + L['stride'] * L['n0']),
         'ext_giv': X(L['giv'] + 7 * L['n0']), 'ext_sur': X(L['sur'] + 7 * L['n0']),
         'bm': X(L['bm']), 'bm_sz': X(L['cap'] // 8),
         'kid': X(L['kid_tab']), 'kid_sz': X(L['cap'] * L['kid_esz']),
         'ring': X(L['ring']), 'ring_sz': X(RING_SZ)}
    for k, off in HD_FIELDS.items():
        d['f_' + k] = h(D_HDR + off)
    d['f_pathdig'] = h(D_PATH + PATH_DIGIT)
    for nm, ph in zip(SC_CTRS, CTR_PH):
        d[ph] = X(L['ctr'][nm])
    return d


def strip_comments(src):
    """SC_SRC 里的 `#` 注释是给人看的, 装配前先砍掉: lint_src 是纯正则扫文本,
    留着注释里的"47B / 370 / 16"这类说明数字会被它当成裸十进制立即数炸掉。"""
    return '\n'.join(l.split('#')[0] for l in src.splitlines())


def build(code_va, L):
    """装配 M6 桩。返回 (code, va, src, ins); va 含两个 trampoline 与 sc_save/sc_load。"""
    from keystone import Ks, KS_ARCH_X86, KS_MODE_32, KS_OPT_SYNTAX_INTEL
    import child_growth as CG
    ks = Ks(KS_ARCH_X86, KS_MODE_32)
    ks.syntax = KS_OPT_SYNTAX_INTEL
    asm_src = strip_comments(SC_SRC % _subs(code_va, L))
    CG.lint_src(asm_src)
    code = bytes(ks.asm(asm_src, code_va)[0])
    va = entry_vas(code, code_va)
    ins = selfcheck(code, code_va, va, L)
    return code, va, asm_src, ins


PUSHAD_MN = ('pushad', 'pushal')


def entry_vas(code, origin):
    """块首两个 trampoline: pushad / mov esi,ecx / call sc_x / popad / call 原生 close / jmp 回跳。
    按 pushad 次序定位, 不写死偏移(改源码长度也不会错位)。"""
    from capstone import Cs, CS_ARCH_X86, CS_MODE_32
    md = Cs(CS_ARCH_X86, CS_MODE_32)
    ins = list(md.disasm(code, origin))
    assert ins and sum(len(i.bytes) for i in ins) == len(code), '反汇编未覆盖全部字节'
    pads = [k for k, i in enumerate(ins) if i.mnemonic in PUSHAD_MN]
    assert len(pads) == 2, ('pushad 应恰 2 个', [hex(ins[k].address) for k in pads])
    assert pads[0] == 0, 'tramp_save 必须在块首'
    ent, ends = {}, []
    for k, tag in zip(pads, ('sc_save', 'sc_load')):
        seq = ins[k:k + 6]
        assert seq[0].mnemonic in PUSHAD_MN, ('入口应是 pushad', tag, seq[0])
        assert seq[1].mnemonic == 'mov' and seq[1].op_str == 'esi, ecx', \
            ('pushad 后应立刻 mov esi,ecx', tag, seq[1])
        assert seq[2].mnemonic == 'call' and seq[2].op_str.startswith('0x'), \
            ('第三拍应是本方向入口', tag, seq[2])
        assert seq[3].mnemonic in ('popad', 'popal'), \
            ('第四拍应是 popad', tag, seq[3])
        assert seq[4].mnemonic == 'call' and int(seq[4].op_str, 16) == CLOSE_FN, \
            ('第五拍应重放 call 0x47D850', tag, seq[4])
        assert seq[5].mnemonic == 'jmp', ('第六拍应跳回原 site+5', tag, seq[5])
        ent[tag] = int(seq[2].op_str, 16)
        ends.append(seq[5].address + seq[5].size)
    assert ent['sc_save'] != ent['sc_load'], '两方向入口不得相同'
    jmps = [i for i in ins if i.mnemonic == 'jmp'
            and i.op_str in ('0x%x' % BACK_SAVE, '0x%x' % BACK_LOAD)]
    assert len(jmps) == 2, ('回跳 jmp 应恰 2 条', [hex(j.address) for j in jmps])
    return {'tramp_save': origin, 'tramp_load': ins[pads[1]].address,
            'tramp_end': ends[1], 'code_end': origin + len(code), 'size': len(code), **ent}


def selfcheck(code, origin, va, L):
    """回读核对: 系统调用只用那 5 个导出、两个方向共用一张表、摘要范围与偏移、归零只用字节串操作。"""
    from capstone import Cs, CS_ARCH_X86, CS_MODE_32
    md = Cs(CS_ARCH_X86, CS_MODE_32)
    ins = list(md.disasm(code, origin))
    assert ins and sum(len(i.bytes) for i in ins) == len(code), '反汇编未覆盖全部字节'
    D = lambda k: origin + L['data_delta'] + k

    def txt(i):
        return '%s %s' % (i.mnemonic, i.op_str)

    def one(mn, *pats, **kw):
        n = kw.get('n', 1)
        got = [i for i in ins if i.mnemonic == mn and all(p in i.op_str for p in pats)]
        assert len(got) == n, ('缺/多指令 %s %s (命中 %d, 期望 %d)' % (mn, pats, len(got), n))
        return got[0] if n == 1 else got

    # 1) 外部调用: 只允许 4 个 Win16 兼容导出(不探测文件位置) + 存档链尾的原生 call
    mem_calls = [i for i in ins if i.mnemonic == 'call' and i.op_str.startswith('dword ptr')]
    got = {}
    for i in mem_calls:
        t = int(i.op_str.split('[')[1].rstrip(']'), 16)
        got[t] = got.get(t, 0) + 1
    assert set(got) == {TH_OPENFILE, TH_LWRITE, TH_LREAD, TH_LCLOSE}, \
        ('系统调用集合不符', {hex(x): c for x, c in got.items()})
    for t in (TH_OPENFILE, TH_LWRITE, TH_LREAD, TH_LCLOSE):
        assert got[t] == 1, ('%s 应恰 1 处包装, 实得 %d' % (hex(t), got[t]))
    # 2) 两个 trampoline: pushad / mov esi,ecx / call sc_x / popad / call 原生 close / jmp 回跳
    for tag, site, back in (('sc_save', SITE_SAVE, BACK_SAVE), ('sc_load', SITE_LOAD, BACK_LOAD)):
        e = [i for i in ins if i.mnemonic in PUSHAD_MN][0 if tag == 'sc_save' else 1]
        seq = [txt(i) for i in ins if e.address <= i.address < e.address + 16][:6]
        assert e.mnemonic in PUSHAD_MN, seq
        calls = [i for i in ins if i.address > e.address and i.mnemonic == 'call'][:2]
        jmps = [i for i in ins if i.address > calls[1].address and i.mnemonic == 'jmp'][:1]
        assert int(calls[0].op_str, 16) == va[tag], ('%s 没调本方向入口' % tag, calls[0])
        assert int(calls[1].op_str, 16) == CLOSE_FN, ('重放的不是 0x47D850', calls[1])
        assert int(jmps[0].op_str, 16) == back, ('回跳不是 site+5=0x%08X' % back, jmps[0])
        assert len([i for i in ins if i.mnemonic in PUSHAD_MN]) == 2, 'pushad 总数'
    # 3) 打开标志与文件名: 保存 0x1002 / 载入 0 (xor edx,edx), 槽号写进路径第 10 字节
    one('mov', 'edx, 0x1002')
    assert [i for i in ins if txt(i) == 'mov edx, 0x1002'] and \
        [i for i in ins if txt(i) == 'xor edx, edx'], '两方向的 OpenFile code 应一存一读'
    one('mov', 'byte ptr [0x%x], dl' % (D(D_PATH) + PATH_DIGIT))
    # 4) 长度闸门 = "头 + 六段每次都读/写满额"(不 seek: seek 到档尾会把读位置也带走);
    #    文件总长只作为头里的 payload 字段参与比较, 头部字段读写偏移两边同一套
    pay, tot = payload_len(L), HDR_SZ + payload_len(L)
    one('mov', 'dword ptr [0x%x], 0x%x' % (D(D_HDR) + HD_PAYLOAD, pay))
    for off, nm in ((HD_MAGIC, 'magic'), (HD_COMMIT, 'commit'), (HD_DIGEST, 'digest'),
                    (HD_PAYLOAD, 'payload'), (HD_CAP, 'cap'), (HD_N0, 'n0'), (HD_VER, 'ver'),
                    (HD_SLOT, 'slot'), (HD_RECN, 'recn')):
        w_ = [i for i in ins if nm != 'digest' and i.mnemonic == 'mov' and ('[0x%x' % (D(D_HDR) + off)) in i.op_str]
        if nm in ('magic', 'commit', 'payload', 'recn', 'cap', 'n0', 'ver', 'slot'):
            assert w_, ('头部字段 %s 没被写' % nm)
    # 5) 两方向共用一张描述符表: 游标读/写 + 前进 8 + 全量比对 各恰 2 处(写方向/读方向)
    for pat in ('dword ptr [0x%x]' % D(D_CUR),):
        assert len([i for i in ins if i.mnemonic == 'mov' and pat in i.op_str
                    and i.op_str.startswith('dword ptr')]) == 2, '游标装载'
        assert len([i for i in ins if i.mnemonic == 'add' and pat in i.op_str]) == 2, '游标前进'
    # 头部 1 处 + 六段循环各 1 处 = 4 次"实读写 == 请求数"闸门
    assert len([i for i in ins if i.mnemonic == 'cmp' and i.op_str == 'eax, ecx']) == 4, \
        '保存/载入两方向都必须"读/写字节数 == 请求数"才算过'
    assert len([i for i in ins if i.mnemonic == 'mov'
                and i.op_str.startswith('edx, dword ptr [eax')]) == 2, '缓冲区取自表项'
    # 6) 摘要范围: 基址=池, 条数=N0, 每条 12 次 add+rol(1 双字 + 9 双字 + 1 字 + 1 字节), 跳过 +4..+7
    assert one('mov', 'edi, 0x%x' % L['pool']), '摘要基址不是池'
    assert one('mov', 'ebp, 0x%x' % L['n0']), '摘要条数不是 N0'
    # 文本里 4 处 rol = 首双字 + 循环体内双字(跑 9 次) + 字 + 字节 => 运行时每条记录 12 步混合
    assert len([i for i in ins if i.mnemonic == 'rol' and i.op_str == 'ebx, 3']) == 4, '摘要混合步应是 4 处文本'
    one('add', 'edi, 8')                      # 跳过派生指针 +4..+7
    one('add', 'edi, 3')                      # 字/字节尾巴 -> 正好前进 47B
    one('mov', 'ecx, 9')                      # 中间九个双字
    # 7) 归零与静态初始化同构: 47B 模板 + id word, 7B 行只用 rep stosb(禁 qword), 私有区整块清
    #    ★ capstone 5 把重复前缀折进助记符: mnemonic 就是 'rep movsb' / 'rep stosb'
    one('imul', 'edi, ebx, 0x2f')
    one('rep movsb', 'byte ptr es:[edi], byte ptr [esi]')
    assert len([i for i in ins if i.mnemonic == 'rep stosb']) == 5, \
        '姓行/名行/位图/KID_TAB/CMD_RING 五处清零'
    assert not [i for i in ins if 'qword' in i.op_str], '不许用 qword 写 7B 行(会踩到隔壁表)'
    assert len([i for i in ins if i.mnemonic == 'mov' and i.op_str == 'ecx, 7']) == 2, '两张姓名表各 7B'
    one('mov', 'word ptr [edi], dx')
    for sz in (L['cap'] // 8, L['cap'] * L['kid_esz'], RING_SZ):
        one('mov', 'ecx, 0x%x' % sz)
    # 8) 载入方向必须先看引擎的"预校验门"; 每方向入口恰一次 cld
    one('cmp', 'word ptr [esi + 0x%x], 0' % OBJ_GATE)
    assert len([i for i in ins if i.mnemonic == 'cld']) == 3, 'sc_save/sc_load/sc_reset 各一次 cld'
    # 9) 槽号解析: 减 0x198、每次减 0xA000、上界 8
    one('cmp', 'eax, 0x198')
    one('sub', 'eax, 0x198')
    one('mov', 'ecx, 0xa000')
    one('sub', 'eax, ecx')
    one('cmp', 'edx, 8')
    # 10) 内部 call 的目标全在块内, 跳转目标合法
    for i in ins:
        if i.mnemonic == 'call' and not i.op_str.startswith('dword ptr'):
            t = int(i.op_str, 16)
            assert t == CLOSE_FN or origin <= t < va['code_end'], ('外部 call %08X' % t, i)
        if i.mnemonic.startswith('j') and i.op_str.startswith('0x'):
            t = int(i.op_str, 16)
            assert origin <= t < va['code_end'] or t in (BACK_SAVE, BACK_LOAD), \
                ('跳转越界 %08X -> %08X' % (i.address, t))
    return ins


if __name__ == '__main__':
    import json, os, sys
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass
    REV = os.path.dirname(os.path.abspath(__file__))
    lay = json.load(open(os.path.join(REV, '_big_layout.json'), encoding='utf-8'))
    ctr = lay['growth_ctrs']                   # 埋点表唯一真源(build_big 落盘, 含 SIDECAR_* 九项)
    missing = [nm for nm in SC_CTRS if nm not in ctr]
    assert not missing, '布局里还没有 M6 埋点(先跑带 M6 的 build_big): %s' % missing
    L = {'pool': lay['pool_va'], 'stride': lay['stride'], 'n0': lay['n0'], 'cap': lay['cap'],
         'giv': lay['surname_tab_va'], 'sur': lay['given_tab_va'],
         'bm': lay['v']['CHILD_BM'], 'kid_tab': lay['v']['KID_TAB'], 'kid_esz': lay['kid_esz'],
         'ring': lay['v']['CMD_RING'], 'sect_va': lay['section_va'], 'sect_sz': lay['section_sz'],
         'data_delta': lay['sc']['data_va'] - lay['sc']['code_va'], '_slot': 3,
         'ctr': {nm: ctr[nm] for nm in SC_CTRS}}
    code_va, data_va = lay['sc']['code_va'], lay['sc']['data_va']
    code, va, src, ins = build(code_va, L)
    print('SC_CODE 0x%06X..0x%06X (%dB) ; SC_DATA 0x%06X..0x%06X (%dB)'
          % (code_va, va['code_end'], va['size'], data_va, data_va + SC_DATA_SZ, SC_DATA_SZ))
    print('tramp_save @0x%06X -> 0x%08X | tramp_load @0x%06X -> 0x%08X'
          % (va['tramp_save'], SITE_SAVE, va['tramp_load'], SITE_LOAD))
    print('影子档 %dB = 头 0x%X + ' % (file_len(L), HDR_SZ) + ' + '.join(str(s) for _, s in blocks(L)))
    print('埋点 %s' % ', '.join('%s@0x%06X' % (nm, L['ctr'][nm]) for nm in SC_CTRS))
    for i in ins:
        print('  %08X  %-24s %s %s' % (i.address, i.bytes.hex(), i.mnemonic, i.op_str))
