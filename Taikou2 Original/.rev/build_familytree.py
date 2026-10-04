"""
家族族谱 MOD —— 在 TAIK2W95_zoom.exe 基础上再打补丁, 生成 TAIK2W95_ft.exe
(绝不改动原版 TAIK2W95.exe / TAIK2W95_zoom.exe, 只读入并写出新文件)

两个入口:
  A) 详情面板 6 页签里的“家族族谱”(原“家中排行”页签, 经 idx2 thunk 0x462559 劫持)
  B) 在“调查”人物信息卡上按 F9 -> 打开当前被调查武将的族谱

族谱渲染全部复用游戏自带的“属下武将列表”框架:
  family_entry(0x535000) 复刻 0x462d40(自包含列表模态)的栈帧:
     sub esp,0x14 / push esi / push edi
     call family_builder              (族谱成员实体指针填进全局 [0x51e9c0], 计数回 eax)
     mov esi,eax
     jmp 0x462d4c                     (续用列表渲染/选择/跳转, 最终经 0x462d40 的 ret 返回)
  -> family_entry 是一个上下文无关的普通无参函数, 可在任意处 call.
  family_builder: 遍历 0x519868 处 370 个实体(步长47), 复刻 0x462e10 的存活/有职过滤,
     匹配键换成族谱三条件(本人 + 子女 father==本人大名 + 父亲). 当前对象 = call 0x49f5e0 的实体.
     两个入口都读同一个“当前对象”, builder 行为一致, 无需模式标志.

入口 B 的实现(低风险, 不新增绘制/命中测试):
  调查卡消息循环 0x46e2e0 的循环头 0x46e31f(mov eax,[0x520630], 5 字节) 处:
  改 E9 jmp -> nav_kbd(洞). nav_kbd 每轮 call ft_kbd 轮询 GetAsyncKeyState(VK_F9=0x78)
  的按下边沿; 命中则 push 存活寄存器, call family_entry, 恢复寄存器, 再执行原指令 jmp 回 0x46e324.
  游戏未导入 GetAsyncKeyState, 故 ft_kbd 首次用 GetModuleHandleA("user32")+GetProcAddress
  在运行期解析一次(缓存于洞内 G_GS); user32/kernel32 已在导入表中.
  调查卡与家族族谱的“目标武将”解析 = 与游戏自带“家中排行”页签一致: call 0x49f5e0 -> 读卡面武将槽
  [0x516624] -> 实体 = EBASE + slot*47; 越界返 0 -> builder 走 bail 出空列表. 两个入口共用同一根解析.

代码洞: 复用 zoom 已扩大的 .idata(可读写, RVA 0x133000..0x136000 已映射);
  原 zoom 洞占 0x134000..0x135000, 本 MOD 用 0x135000 起的空闲零页.
"""
import struct

SRC = r'F:\Games\Taikou 2\Taikou2 Original\TAIK2W95_zoom.exe'
DST = r'F:\Games\Taikou 2\Taikou2 Original\TAIK2W95_ft3.exe'
DELTA = 0xC00                      # file offset = RVA - 0xC00
b = bytearray(open(SRC, 'rb').read())
off_of = lambda rva: rva - DELTA

# ---------- 常量 ----------
CAVE_RVA = 0x135000
CAVE_VA  = 0x400000 + CAVE_RVA      # 0x535000
GET_SUBJECT   = 0x49f5e0            # -> eax = 当前查看对象实体指针
RESUME        = 0x462d4c            # 属下武将页签 0x462d40 内 test si,si 起 (esi=计数)
THUNK_CALL    = 0x462559            # idx2 thunk: e8 12010000 call 0x462670
THUNK_RET_ADDR = THUNK_CALL + 5     # 0x46255e
ORIG_TARGET   = 0x462670

EBASE, ESTRIDE, ECOUNT = 0x519868, 47, 0x172   # 实体数组 / 步长 / 槽数(370)
# 实体身份: 姓名 getter 0x49c310/0x49c2b0 都读 `word[ent+0x00]` 作 person id 去索引姓/名表
#   (姓表 0x520660 / 名表 0x521aa8, 步长7) -> **ent+0x00 = 人物编号 = BSDATA oid**(身份真键).
#   BSDATA 记录 rec[0]=oid, rec[2]=father(基表全员0xffff无血缘) -> 实体 ent+0x02 = 父id.
#   注: 实体数组的**槽位**(EBASE+slot*47) 与 oid **不是一回事**(截图实证 slot35=桑折宗长 oid89),
#   故一切匹配只认 ent+0x00(+0x02), 绝不用 slot 地址.
O_SELFID, O_FATHERID, O_STATUS = 0x00, 0x1d, 0x2c
LISTBUF = 0x51e9c0                  # 全局: dword* -> 列表 UI 读取的实体指针数组
# 族谱根 = “详情面板正在显示的武将”: 与游戏自带 0x462670“家中排行”同一来源 -> call GET_SUBJECT(0x49f5e0).
#   0x49f5e0 读 [0x516624] = 卡面武将**槽id** -> 实体 = EBASE + slot*47. [0x516624] 由调查卡 0x47e7xx
#   控件绑定写入(push 0x516624 @0x47e808 经 0x47d930), 卡开期间恒为该卡武将本身; 越界返回 0(builder 走 bail 空列表).
#   (曾用 [0x516618]: 那只是 0x46e2e0 卡内“点击单元匹配”临时槽, F9 轮询时常=0 -> 两卡解析成同一 slot0=林通胜的 bug, 弃用.)
#   (曾用 [0x519227] 选中地图单元: 开卡时常 0/失效 -> 回退主角, 亦弃用.)
G_ROOT   = 0x5352B0                 # 洞内 dword: 预设根实体指针, 0=builder 现算

# ---------- 关系标注 (家族族谱列表在名字后追加“关系”列) ----------
# 绘制回调 0x462a30 被 4 处 push 复用; 本 MOD 只把“家中/家族”窗口那处 (0x462d7f) 换成 ft_paint,
# 其余 3 处仍用原 painter -> 完全不受影响. ft_paint 靠洞内 G_FAMILY 标志区分: 0=原样“%s %s”,
# 1=“%s %s %s”(名 + 关系). 属下列表(普通页)经 vassal_thunk 清 0, 家族族谱(family_entry)置 1,
# 故普通“家来”列表绘制逐字节等价原版, 只有族谱会多出关系串.
FT_PAINT_VA    = 0x535400           # 洞内 painter
VASSAL_THUNK_VA= 0x535480           # 普通属下一页: 清 G_FAMILY 后 jmp 0x462d40
G_FAMILY       = 0x5354C0           # dword: 1=族谱绘制
STR_FMT3       = 0x5354D0           # "%s %s %s\0"
R_SELF   = 0x5354E0                 # "本人"
R_CHILD  = 0x5354F0                 # "子女"
R_FATHER = 0x535500                 # "父亲"
R35      = 0x535510                 # 柴田胜丰: "养子"
R38      = 0x535520                 # 佐久间盛政: "甥"
R42      = 0x535530                 # 佐久间安政: "姻戚"
R45      = R38                       # 佐久间正胜: "甥"
RELSTR   = 0x535600                 # dword[370]: builder 按行写入关系串地址, ft_paint 读

# 通用族谱关系映射: 本人([c+0]==self oid) / 子女([c+2]==self oid) / 父亲([c+0]==root父id)

# ---------- 柴田一门内置: 按“运行时姓名”匹配, 不按 id ----------
# 决定性教训(截图#3): 运行时姓名表 0x520660(姓)/0x521aa8(名) 是引擎按剧本对 BSDATA 记录**重排**后的
#   主名表, 其下标 = ent+0x00, 但**与 BSDATA 记录号不是一套**(实测 name[0]=林通胜、name[35]=桑折宗长
#   而 BSDATA rec35=长束正家)。故任何硬编码 id 都会挑错人。改为读活名表比对姓名字节:
#   getter 0x49c310/0x49c2b0: idx<0x3e8 时 姓=0x520660+idx*7, 名=0x521aa8+idx*7 (GBK, 步长7)。
SUR_BASE, GIV_BASE, NAME_STRIDE, NAME_RANGE = 0x520660, 0x521aa8, 7, 0x3e8
EBASE_END = EBASE + ECOUNT*ESTRIDE          # 遍历终点(用 cmp edx,end 省一个计数寄存器)
TARGETS   = 0x535C00                         # 洞内: 内置名单表, 5×(姓dword,名dword,关系串ptr)=60B
# (姓首4字节, 名首4字节, 关系串) —— 全部 GBK 小端 dword, 与上表 getter 完全一致:
# 注意: SUR_BASE 实际是名表, GIV_BASE 实际是姓表 (和变量名相反!)
# NAME_FAMILY 每项格式: (名dword, 姓dword, 关系串ptr)
NAME_FAMILY = (
    (0xD2BCA4CA, 0xEFCCF1B2, R_SELF),   # 柴田胜家  本人 (名=胜家, 姓=柴田)
    (0xE1B7A4CA, 0xEFCCF1B2, R35),      # 柴田胜丰  养子 (名=胜丰, 姓=柴田)
    (0xFED5A2CA, 0xC3BEF4D7, R38),      # 佐久间盛政 甥 (名=盛政, 姓=佐久间)
    (0xFED5B2B0, 0xC3BEF4D7, R42),      # 佐久间安政 姻戚 (名=安政, 姓=佐久间)
    (0xA4CAFDD5, 0xC3BEF4D7, R45),      # 佐久间正胜 甥 (名=正胜, 姓=佐久间)
)
# 触发判定: 先比 SUR_BASE(名表) 再比 GIV_BASE(姓表)
TRIG_SUR, TRIG_GIV = 0xD2BCA4CA, 0xEFCCF1B2   # 名=胜家, 姓=柴田

# ---------- 两段式汇编器 (先定义, builder/kbd/nav 共用) ----------
class Asm:
    def __init__(self, va):
        self.va=va; self.code=bytearray(); self.labels={}; self.f8=[]; self.f32=[]
    def pos(self): return self.va+len(self.code)
    def label(self, n): self.labels[n]=self.pos()
    def b(self, *xs): self.code.extend(bytes(xs))
    def dw(self, v): self.code.extend(struct.pack('<I', v))
    def jr8(self, op, name):
        self.code.append(op); self.code.append(0); self.f8.append((len(self.code)-1, name))
    def callabs(self, va):
        self.code.append(0xE8); self.code.extend(b'\0\0\0\0'); self.f32.append((len(self.code)-4, va))
    def jmpabs(self, va):
        self.code.append(0xE9); self.code.extend(b'\0\0\0\0'); self.f32.append((len(self.code)-4, va))
    def resolve(self):
        for off, name in self.f8:
            tgt = self.labels[name]
            rel = (tgt - (self.va+off+1))
            assert -128 <= rel <= 127, 'rel8 越界 %s %d' % (name, rel)
            self.code[off] = rel & 0xFF
        for off, tgt in self.f32:
            tgt = self.labels[tgt] if isinstance(tgt, str) else tgt
            self.code[off:off+4] = struct.pack('<i', tgt - (self.va+off+4))
        return bytes(self.code)

# ---------- family_builder (手工 x86) ----------
ENTRY_LEN = 10 + 3 + 1 + 1 + 5 + 2 + 5   # family_entry 定长 = 27 (含 mov[G_FAMILY],1)
builder_va = CAVE_VA + ENTRY_LEN

# 史实家族内置(柴田胜家一门): 基础表 BSDATA 父链接全员 0xffff(无血缘), 故对胜家走代码内置.
#   名单按“运行时姓名”匹配(读活名表 0x520660/0x521aa8 比对 GBK 姓名字节), 见上方 NAME_FAMILY 说明.
#   全为游戏真实武将(自带姓名/头像/数值): 柴田胜家(本人) / 柴田胜丰(养子) / 佐久间盛政(甥) /
#   佐久间安政(姻戚) / 佐久间正胜(甥). 佐久间信盛属另一无关支系, 不在名单. 增删改 NAME_FAMILY 即可.

fb = Asm(builder_va)
fb.b(0x53, 0x55, 0x56, 0x57)                       # push ebx,ebp,esi,edi
fb.b(0x8B, 0x1D); fb.dw(G_ROOT)                    # mov ebx,[G_ROOT]  (预设根, 0=builder 现算)
fb.b(0x85, 0xDB)                                   # test ebx,ebx
fb.jr8(0x75, 'okroot')                             # jne okroot
# 现算根: 直接读 [0x514ee8] = 当前调查卡武将实体指针 (内存搜索定位, 实测唯一命中柴田胜家)
#   (原 call 0x49f5e0 返回的是主角木下藤吉郎, 不是当前调查对象, 弃用)
fb.b(0xA1); fb.dw(0x514EE8)                        # mov eax, [0x514ee8] -> 当前调查卡武将实体指针
# 防御: 校验 eax 落在实体数组 [EBASE,EBASE_END) 内, 否则视为无效 -> 空列表.
#   (否则 [0x514ee8] 非实体指针时, 下面 movzx ebp,[ebx+0] 解引用野指针 -> F9 直接崩溃)
fb.b(0x3D); fb.dw(EBASE)                           # cmp eax,EBASE
fb.jr8(0x72, 'bail')                               # jb bail
fb.b(0x3D); fb.dw(EBASE_END)                       # cmp eax,EBASE_END
fb.jr8(0x73, 'bail')                               # jae bail
fb.jr8(0xEB, 'havee')                              # jmp havee
fb.label('bail')
# 无有效卡面武将 -> 就地返回空列表(此处已 push ebx/ebp/esi/edi, 逐一对应弹栈, 栈平衡)
fb.b(0x33, 0xC0)                                   # xor eax,eax
fb.b(0x5F, 0x5E, 0x5D, 0x5B)                       # pop edi,esi,ebp,ebx
fb.b(0xC3)                                         # ret
fb.label('havee')
fb.b(0x8B, 0xD8)                                   # mov ebx,eax
fb.label('okroot')
fb.b(0x0F, 0xB7, 0x2B)                             # movzx ebp,[ebx+0]  自我 person id(oid)
fb.b(0x0F, 0xB7, 0x7B, 0x1D)                        # movzx edi,[ebx+0x1d] 父id
fb.b(0x33, 0xF6)                                   # xor esi,esi (计数)
fb.b(0xBA); fb.dw(EBASE)                            # mov edx,EBASE
fb.b(0xB9); fb.dw(ECOUNT)                           # mov ecx,ECOUNT
# --- 触发判定: 根是否 柴田胜家? 读活名表比对姓名字节(不按 id, 见上). 是->shib; 否->通用 nloop ---
fb.b(0x81, 0xFD); fb.dw(NAME_RANGE)                 # cmp ebp,0x3e8 (根姓名idx>=1000 段->非内置)
fb.jr8(0x73, 'nloop')                               # jae nloop
fb.b(0x6B, 0xC5, NAME_STRIDE)                       # imul eax,ebp,7 (eax=idx*7)
fb.b(0x05); fb.dw(SUR_BASE)                         # add eax,SUR_BASE -> 姓指针
fb.b(0x81, 0x38); fb.dw(TRIG_SUR)                   # cmp dword[eax], "柴田"  (81=/7 imm32)
fb.jr8(0x75, 'nloop')                               # jne nloop
fb.b(0x05); fb.dw(GIV_BASE - SUR_BASE)              # add eax,(名表-姓表) -> 名指针
fb.b(0x81, 0x38); fb.dw(TRIG_GIV)                   # cmp dword[eax], "胜家"
fb.jr8(0x75, 'nloop')                               # jne nloop
fb.jmpabs('shib')                                   # jmp shib -> 柴田一门内置

# --- 通用族谱匹配(比 person id): 本人([c+0]==self) / 子女([c+2]==self) / 父([c+0]==father) ---
#     取中后按关系给该行配一个关系串地址(eax), 写入 RELSTR[行]; ebx 作基址暂存(循环中根已不再用).
fb.label('nloop')
fb.b(0x66, 0x8B, 0x42, 0x2C)                        # mov ax,[edx+2c]
fb.b(0xF6, 0xC4, 0x80)                             # test ah,80
fb.jr8(0x75, 'nskip')                              # jne 隐退/死亡
fb.b(0xF6, 0xC4, 0x07)                             # test ah,7
fb.jr8(0x74, 'nskip')                              # je  无职级/空槽
fb.b(0x66, 0x3B, 0x6A, 0x00)                       # cmp bp,[edx+0]
fb.jr8(0x74, 'ntake')                              # je  本人
fb.b(0x66, 0x3B, 0x6A, 0x1D)                       # cmp bp,[edx+0x1d]
fb.jr8(0x74, 'ntake')                              # je  子女(其父==我)
fb.b(0x66, 0x3B, 0x7A, 0x00)                       # cmp di,[edx+0]
fb.jr8(0x75, 'nskip')                              # jne 父匹配失败 -> skip
fb.label('ntake')
fb.b(0x0F, 0xB7, 0x42, 0x00)                        # movzx eax,[edx+0] (该实体 oid)
fb.b(0x66, 0x3B, 0xC5)                             # cmp ax,bp
fb.jr8(0x74, 'r_self')                             # je 本人
fb.b(0x66, 0x3B, 0x6A, 0x1D)                       # cmp bp,[edx+0x1d]
fb.jr8(0x74, 'r_child')                            # je 子女
fb.b(0xB8); fb.dw(R_FATHER)                        # mov eax,"父亲"
fb.jr8(0xEB, 'gstore')                             # jmp gstore
fb.label('r_self')
fb.b(0xB8); fb.dw(R_SELF)                          # mov eax,"本人"
fb.jr8(0xEB, 'gstore')
fb.label('r_child')
fb.b(0xB8); fb.dw(R_CHILD)                         # mov eax,"子女"
fb.label('gstore')
fb.b(0x8B, 0x1D); fb.dw(LISTBUF)                    # mov ebx,[LISTBUF]
fb.b(0x89, 0x14, 0xB3)                             # mov [ebx+esi*4],edx (实体指针)
fb.b(0xBB); fb.dw(RELSTR)                          # mov ebx,RELSTR
fb.b(0x89, 0x04, 0xB3)                             # mov [ebx+esi*4],eax (关系串地址)
fb.b(0x46)                                         # inc esi
fb.label('nskip')
fb.b(0x83, 0xC2, 0x2F)                             # add edx,47
fb.b(0x49)                                         # dec ecx
fb.jr8(0x75, 'nloop')                              # jne nloop
fb.b(0x8B, 0xC6)                                   # mov eax,esi
fb.jmpabs('end')                                   # jmp end (跳过 shib 内置块)

# --- 柴田胜家: 内置史实一门(遍历实体, 逐个过存活/职级门, 再按“运行时姓名”比对 TARGETS 表) ---
#     命中即取该表项的关系串写 RELSTR[行]; 不在表内的一律丢弃(绝不默认收下, 否则全图武将都塞进来).
fb.label('shib')
fb.b(0xBA); fb.dw(EBASE)                            # mov edx,EBASE (实体游标)
fb.label('sloop')
fb.b(0x81, 0xFA); fb.dw(EBASE_END)                  # cmp edx,EBASE_END
fb.jr8(0x73, 'send')                                # jae send (遍历完 370 个)
# 内置一门: 族谱应含已故/未仕亲属, 故此处**不过**存活/职级门(不同于通用 nloop).
#   仅保留 idx<1000 守卫, 防空槽(idx=0xffff)/他段姓名误命中 TARGETS.
fb.b(0x0F, 0xB7, 0x42, 0x00)                        # movzx eax,[edx+0] 该实体姓名idx
fb.b(0x3D); fb.dw(NAME_RANGE)                       # cmp eax,0x3e8
fb.jr8(0x73, 'sskip')                              # jae sskip (>=1000 段不在内置表)
fb.b(0x6B, 0xC0, NAME_STRIDE)                       # imul eax,7 (idx*7)
fb.b(0x8D, 0x98); fb.dw(SUR_BASE)                  # lea ebx,[eax+SUR_BASE] 姓指针
fb.b(0x8D, 0xA8); fb.dw(GIV_BASE)                  # lea ebp,[eax+GIV_BASE] 名指针
fb.b(0xBF); fb.dw(TARGETS)                          # mov edi,TARGETS (表游标)
fb.b(0xB9); fb.dw(len(NAME_FAMILY))                # mov ecx,5 (表长)
fb.label('tloop')
fb.b(0x8B, 0x07)                                   # mov eax,[edi]      (姓4字节)
fb.b(0x39, 0x03)                                   # cmp [ebx],eax      (ebx=姓指针; rm=011 mod=00 -> [ebx])
fb.jr8(0x75, 'next')                               # jne next
fb.b(0x8B, 0x47, 0x04)                             # mov eax,[edi+4]    (名4字节)
fb.b(0x39, 0x45, 0x00)                             # cmp [ebp],eax      (ebp=名指针; mod=01 rm=101 disp8=0 -> [ebp])
fb.jr8(0x75, 'next')                               # jne next
fb.b(0x8B, 0x47, 0x08)                             # mov eax,[edi+8]    (关系串地址)
fb.jr8(0xEB, 'found')                              # jmp found
fb.label('next')
fb.b(0x83, 0xC7, 12)                               # add edi,12
fb.b(0x49)                                         # dec ecx
fb.jr8(0x75, 'tloop')                              # jne tloop
fb.jr8(0xEB, 'sskip')                              # 无匹配 -> 丢弃
fb.label('found')
fb.b(0x8B, 0x1D); fb.dw(LISTBUF)                    # mov ebx,[LISTBUF]
fb.b(0x89, 0x14, 0xB3)                             # mov [ebx+esi*4],edx (实体指针)
fb.b(0xBB); fb.dw(RELSTR)                          # mov ebx,RELSTR
fb.b(0x89, 0x04, 0xB3)                             # mov [ebx+esi*4],eax (关系串地址)
fb.b(0x46)                                         # inc esi
fb.label('sskip')
fb.b(0x83, 0xC2, ESTRIDE)                          # add edx,47
fb.jr8(0xEB, 'sloop')                              # jmp sloop
fb.label('send')
fb.b(0x8B, 0xC6)                                   # mov eax,esi
fb.label('end')
fb.b(0x5F, 0x5E, 0x5D, 0x5B)                       # pop edi,esi,ebp,ebx
fb.b(0xC3)
body = fb.resolve()
assert (builder_va - CAVE_VA) + len(body) <= (0x535200 - CAVE_VA), 'builder 与 kbd 区(0x535200)冲突'

# ---------- 入口 B: 调查卡键盘触发 (ft_kbd 轮询 GetAsyncKeyState, nav_kbd 钩子) ----------
IAT_GETMOD   = 0x4fb138          # call [GetModuleHandleA]
IAT_GETPROC  = 0x4fb0e0          # call [GetProcAddress]
KBD_VA   = 0x535200              # ft_kbd 代码 (104B, 到 0x535268)
STR_U32  = 0x535270              # "user32\0"
STR_GAKS = 0x535280              # "GetAsyncKeyState\0"
G_GS     = 0x5352A0              # dword: 缓存的 GetAsyncKeyState 地址(初 0)
G_PREV   = 0x5352A8              # byte : 上一次 F9 是否按下(边沿检测)
NAV_VA   = 0x5352C0              # nav_kbd 跳板 1 (城武将列表小弹窗)
VK_F9    = 0x78
CARD_LOOP_HEAD   = 0x46e31f      # 小弹窗循环头: mov eax,[0x520630] (5 字节)
CARD_LOOP_RESUME = 0x46e324      # 钩子1返回点

# ---------- family_entry ----------
e = bytearray()
def ee(d): e.extend(d)
# 入口B(F9) 只由主线程 nav_kbd 钩子触发(它跑在 0x46e2e0 卡弹窗自己的消息泵里, 与入口A同机制, 栈平衡安全).
# 后台线程会在无消息队列的线程上 call family_entry -> jmp 0x462d4c 弹模态列表 -> 跨线程 UI -> 按 F9 直接崩;
# 且加 call init_thread 会让 family_entry 由 27B 变 32B, 越过 builder_va(=CAVE_VA+27) 覆盖 builder 首指令. 故彻底移除后台线程.
ee(b'\xc7\x05' + struct.pack('<I', G_FAMILY) + b'\x01\x00\x00\x00')  # mov dword[G_FAMILY],1 (族谱绘制)
ee(b'\x83\xec\x14')                                         # sub esp,0x14
ee(b'\x56')                                                # push esi
ee(b'\x57')                                                # push edi
ee(b'\xe8' + struct.pack('<i', builder_va - (CAVE_VA + len(e) + 5)))  # call builder
ee(b'\x8b\xf0')                                            # mov esi,eax
ee(b'\xe9' + struct.pack('<i', RESUME - (CAVE_VA + len(e) + 5)))     # jmp 0x462d4c
ENTRY_LEN = 27                                             # 必须与 line 131 的 builder_va 偏移一致
assert len(e) == ENTRY_LEN, len(e)

# ft_kbd: eax = 1(F9 按下边沿) / 0 ; 保存 ebx/esi/edi
# 注: Win32 API 均 __stdcall(被调方自清参数), 调用后绝不可再 add esp, 否则栈双重清理崩坏.
a = Asm(KBD_VA)
a.b(0x53, 0x56, 0x57)                       # push ebx, esi, edi
a.b(0x8B, 0x35); a.dw(G_GS)                 # mov esi,[G_GS]
a.b(0x85, 0xF6)                             # test esi,esi
a.jr8(0x75, 'have')                         # jne have
a.b(0x68); a.dw(STR_U32)                    # push STR_U32
a.b(0xFF, 0x15); a.dw(IAT_GETMOD)           # call [GetModuleHandleA] (stdcall, 自清4)
a.b(0x68); a.dw(STR_GAKS)                   # push STR_GAKS
a.b(0x50)                                   # push eax (hModule)
a.b(0xFF, 0x15); a.dw(IAT_GETPROC)          # call [GetProcAddress] (stdcall, 自清8)
a.b(0x85, 0xC0)                             # test eax,eax
a.jr8(0x74, 'zero')                         # je zero (解析失败)
a.b(0x8B, 0xF0)                             # mov esi,eax
a.b(0x89, 0x35); a.dw(G_GS)                 # mov [G_GS],esi
a.label('have')
a.b(0x6A, VK_F9)                            # push VK_F9
a.b(0xFF, 0xD6)                             # call esi -> GetAsyncKeyState (stdcall, 自清4)
a.b(0x25); a.dw(0x8000)                     # and eax,0x8000 (当前是否按下)
a.jr8(0x74, 'up')                           # jz up
a.b(0x80, 0x3D); a.dw(G_PREV); a.b(0x00)    # cmp byte[G_PREV],0
a.jr8(0x75, 'zero')                         # jne zero (已计过)
a.b(0xC6, 0x05); a.dw(G_PREV); a.b(0x01)    # mov byte[G_PREV],1
a.b(0xB8); a.dw(1)                          # mov eax,1
a.jr8(0xEB, 'done')                         # jmp done
a.label('up')
a.b(0xC6, 0x05); a.dw(G_PREV); a.b(0x00)    # mov byte[G_PREV],0
a.label('zero')
a.b(0x31, 0xC0)                             # xor eax,eax
a.label('done')
a.b(0x5F, 0x5E, 0x5B)                       # pop edi,esi,ebx
a.b(0xC3)                                   # ret
kbd = a.resolve()

# nav_kbd: 调查卡(0x46e2e0)消息循环头跳板, 跑在主线程自身消息泵内(与入口A同机制, 安全).
#   builder 会自行读 [0x514ee8](卡面武将实体指针)现算根, 所以 nav 只需检测 F9 按下边沿 -> call family_entry,
#   无需再解析/预设 G_ROOT.
#   用 pushad/popad 保存所有寄存器, 挂到任何位置都不会崩.
n = Asm(NAV_VA)
n.callabs(KBD_VA)                           # call ft_kbd
n.b(0x85, 0xC0)                             # test eax,eax
n.jr8(0x74, 'skip')                         # je skip
n.b(0x60)                                   # pushad (保存所有寄存器)
n.callabs(CAVE_VA)                          # call family_entry (builder 现算根)
n.b(0x61)                                   # popad (恢复所有寄存器)
n.label('skip')
n.b(0xA1); n.dw(0x520630)                   # 原指令 mov eax,[0x520630]
n.jmpabs(CARD_LOOP_RESUME)                  # jmp 回 0x46e324
nav = n.resolve()

assert (KBD_VA-CAVE_VA) + len(kbd) <= 0x400
assert (NAV_VA-CAVE_VA) + len(nav) <= 0x400

# ---------- ft_paint: 列表绘制回调(替换 0x462d7f 处 push 的 0x462a30) ----------
#   G_FAMILY==0 -> 逐字节复刻原 painter("%s %s", add esp,0x10); ==1 -> "%s %s %s"(名+关系, add esp,0x14).
#   入参: [esp+4]=word 行号; 内部 3 个 push 后行号在 [esp+16]. 行绝对下标=行号+[0x514014]&0xff.
p = Asm(FT_PAINT_VA)
p.b(0x53, 0x56, 0x57)                       # push ebx, esi, edi
p.b(0x0F, 0xBF, 0x44, 0x24, 0x10)           # movsx eax, word[esp+16]
p.b(0x8B, 0x0D); p.dw(0x514014)             # mov ecx,[0x514014]
p.b(0x81, 0xE1); p.b(0xFF, 0x00, 0x00, 0x00)  # and ecx,0xff
p.b(0x03, 0xC1)                             # add eax,ecx (行绝对下标)
p.b(0x8B, 0xF8)                             # mov edi,eax (保存下标)
p.b(0x8B, 0x15); p.dw(LISTBUF)              # mov edx,[LISTBUF]
p.b(0x8B, 0x34, 0x82)                       # mov esi,[edx+eax*4] (实体指针)
p.b(0x8B, 0x0D); p.dw(G_FAMILY)             # mov ecx,[G_FAMILY]
p.b(0x85, 0xC9)                             # test ecx,ecx
p.jr8(0x75, 'fam')                          # jne fam (族谱: 追加关系)
# --- plain: 原样 ---
p.b(0x8B, 0xCE)                             # mov ecx,esi
p.callabs(0x49c310)                         # 姓 -> eax
p.b(0x50)                                   # push eax (arg2)
p.b(0x8B, 0xCE)                             # mov ecx,esi
p.callabs(0x49c2b0)                         # 名 -> eax
p.b(0x50)                                   # push eax (arg1)
p.b(0x68); p.dw(0x504a90)                   # push "%s %s"
p.b(0x68); p.dw(0x5196a8)                   # push 缓冲
p.callabs(0x4ec870)                         # sprintf
p.b(0x83, 0xC4, 0x10)                        # add esp,0x10
p.jr8(0xEB, 'done')                         # jmp done
# --- fam: 关系 + 姓 + 名 ---
p.label('fam')
p.b(0x8B, 0x14, 0xBD); p.dw(RELSTR)         # mov edx,[RELSTR+edi*4] 关系串地址 (SIB base=101 disp32)
p.b(0x52)                                   # push edx (arg3)
p.b(0x8B, 0xCE)                             # mov ecx,esi
p.callabs(0x49c310)                         # 姓
p.b(0x50)                                   # push eax (arg2)
p.b(0x8B, 0xCE)                             # mov ecx,esi
p.callabs(0x49c2b0)                         # 名
p.b(0x50)                                   # push eax (arg1)
p.b(0x68); p.dw(STR_FMT3)                   # push "%s %s %s"
p.b(0x68); p.dw(0x5196a8)                   # push 缓冲
p.callabs(0x4ec870)                         # sprintf
p.b(0x83, 0xC4, 0x14)                        # add esp,0x14
p.label('done')
p.b(0x5F, 0x5E, 0x5B)                       # pop edi,esi,ebx
p.b(0xC3)                                   # ret
paint = p.resolve()
assert (FT_PAINT_VA-CAVE_VA) + len(paint) <= (VASSAL_THUNK_VA-CAVE_VA), 'ft_paint 撞 vassal_thunk'

# ---------- vassal_thunk: 普通属下一页清 G_FAMILY 后转 0x462d40 ----------
t = Asm(VASSAL_THUNK_VA)
t.b(0xC7, 0x05); t.dw(G_FAMILY); t.b(0x00, 0x00, 0x00, 0x00)   # mov dword[G_FAMILY],0
t.jmpabs(0x462d40)                                              # jmp 0x462d40 (尾调用, 保留返回址)
thunk = t.resolve()
assert (VASSAL_THUNK_VA-CAVE_VA) + len(thunk) <= (G_FAMILY-CAVE_VA), 'vassal_thunk 撞 G_FAMILY'

# ---------- 写洞 (0x135000..0x136000, 4KB 内空闲零页; .idata VS=0x3000 已映射) ----------
CAVE_SIZE = 0x1000
cave = bytearray(CAVE_SIZE)
def put(va, data):
    o = va - CAVE_VA
    assert 0 <= o and o + len(data) <= CAVE_SIZE, '洞越界: %06X' % va
    cave[o:o+len(data)] = data
def putstr(va, text):
    vb = text.encode('gbk') + b'\x00'
    put(va, vb)
put(CAVE_VA, e)                                       # family_entry @0x535000
put(builder_va, body)                                 # family_builder
put(KBD_VA, kbd)
put(STR_U32, b'user32\x00')
put(STR_GAKS, b'GetAsyncKeyState\x00')
put(NAV_VA, nav)
put(FT_PAINT_VA, paint)                               # ft_paint
put(VASSAL_THUNK_VA, thunk)                           # vassal_thunk
putstr(STR_FMT3, '%s %s %s')                          # 关系绘制格式串
putstr(R_SELF,   '本人')
putstr(R_CHILD,  '子女')
putstr(R_FATHER, '父亲')
putstr(R35,      '养子')
putstr(R38,      '甥')
putstr(R42,      '姻戚')
# 内置名单表: 5 × (姓dword, 名dword, 关系串ptr), 供 shib 姓名匹配循环读取
_tg = bytearray()
for _s, _g, _r in NAME_FAMILY:
    _tg += struct.pack('<III', _s, _g, _r)
put(TARGETS, bytes(_tg))
assert bytes(cave[G_GS-CAVE_VA:G_GS-CAVE_VA+5]) == b'\0'*5, 'globals 区非零'
assert bytes(cave[G_FAMILY-CAVE_VA:G_FAMILY-CAVE_VA+4]) == b'\0'*4, 'G_FAMILY 区非零'
fo = off_of(CAVE_RVA)
assert b[fo:fo+CAVE_SIZE] == bytes(CAVE_SIZE), '洞区非全零(可能已被占用): off=%X' % fo
b[fo:fo+CAVE_SIZE] = cave
print('OK  洞 @RVA 0x%06X entry=%06X builder=%06X kbd=%06X nav=%06X paint=%06X thunk=%06X relstr=%06X (%d+%d+%d B)'
      % (CAVE_RVA, CAVE_VA, builder_va, KBD_VA, NAV_VA, FT_PAINT_VA, VASSAL_THUNK_VA, RELSTR,
         len(kbd), len(nav), len(paint)))

# ---------- capstone 回环校验 (临时跳过: 未装 capstone) ----------
# import capstone
# mdv = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)
# def roundtrip(name, va, blob):
#     got = bytearray(); ok = 0
#     for ins in mdv.disasm(blob, va):
#         got.extend(ins.bytes); ok += 1
#     assert bytes(got) == blob, '%s 解码不匹配: got %d/%d B' % (name, len(got), len(blob))
#     print('  OK %s: %d 指令, %d 字节' % (name, ok, len(blob)))
# roundtrip('ft_kbd', KBD_VA, kbd)
# roundtrip('nav_kbd', NAV_VA, nav)
# roundtrip('family_builder', builder_va, body)
# roundtrip('ft_paint', FT_PAINT_VA, paint)
# roundtrip('vassal_thunk', VASSAL_THUNK_VA, thunk)
print('  (跳过 capstone 校验)')

# ---------- 劫持 idx2 thunk ----------
chk = off_of(THUNK_CALL - 0x400000)
cur = bytes(b[chk:chk+5])
assert cur[:1] == b'\xe8', 'thunk 不是 call: %s' % cur.hex(' ')
old_rel, = struct.unpack('<i', cur[1:5])
assert THUNK_RET_ADDR + old_rel == ORIG_TARGET, 'thunk 目标异常 0x%08X' % (THUNK_RET_ADDR+old_rel)
b[chk+1:chk+5] = struct.pack('<i', CAVE_VA - THUNK_RET_ADDR)
print('OK  劫持 RVA 0x%06X  家中排行(0x%X) -> family_entry(0x%X)' % (THUNK_CALL, ORIG_TARGET, CAVE_VA))

# ---------- 关系标注: 把“家中/家族”窗口的 painter 回调 (0x462d7f 的 push 0x462a30) 换成 ft_paint ----------
PK_PUSH = 0x462d7f
po = off_of(PK_PUSH - 0x400000)
assert bytes(b[po:po+5]) == b'\x68\x30\x2a\x46\x00', '0x462d7f 不是 push 0x462a30: %s' % bytes(b[po:po+5]).hex(' ')
b[po+1:po+5] = struct.pack('<I', FT_PAINT_VA)
print('OK  painter 回调 RVA 0x%06X push 0x462a30 -> ft_paint(0x%X)' % (PK_PUSH, FT_PAINT_VA))

# ---------- 关系标注: 普通属下一页(0x46256e call 0x462d40)改走 vassal_thunk 清 G_FAMILY ----------
VASSAL_CALL = 0x46256e
vo = off_of(VASSAL_CALL - 0x400000)
vcur = bytes(b[vo:vo+5])
assert vcur[:1] == b'\xe8', '0x46256e 不是 call: %s' % vcur.hex(' ')
vret = VASSAL_CALL + 5
old_vrel, = struct.unpack('<i', vcur[1:5])
assert vret + old_vrel == 0x462d40, '0x46256e 目标异常 0x%08X' % (vret + old_vrel)
b[vo+1:vo+5] = struct.pack('<i', VASSAL_THUNK_VA - vret)
print('OK  属下一页 RVA 0x%06X call 0x462d40 -> vassal_thunk(0x%X)  [清 G_FAMILY]' % (VASSAL_CALL, VASSAL_THUNK_VA))

# ---------- 钩住小弹窗循环头: mov eax,[0x520630] -> jmp nav_kbd ----------
hk = off_of(CARD_LOOP_HEAD - 0x400000)
hcur = bytes(b[hk:hk+5])
assert hcur == b'\xa1\x30\x06\x52\x00', '小弹窗循环头字节不符: %s' % hcur.hex(' ')
rel = NAV_VA - (CARD_LOOP_HEAD + 5)
b[hk:hk+5] = b'\xe9' + struct.pack('<i', rel)
print('OK  小弹窗挂钩 RVA 0x%06X jmp -> nav_kbd(0x%X)  [F9 开族谱]'
      % (CARD_LOOP_HEAD, NAV_VA))

# ---------- 页签名 家中排行 -> 家族族谱 (同 8 字节 GBK, 原地覆盖) ----------
LBL_VA = 0x50494A
old_lbl = '家中排行'.encode('gbk'); new_lbl = '家族族谱'.encode('gbk')
lo = off_of(LBL_VA - 0x400000)
assert bytes(b[lo:lo+len(old_lbl)]) == old_lbl, '页签标签字节不符: %s' % bytes(b[lo:lo+8]).hex(' ')
assert len(new_lbl) == len(old_lbl)
b[lo:lo+len(new_lbl)] = new_lbl
print('OK  页签名 家中排行 -> 家族族谱 @VA 0x%06X' % LBL_VA)

try:
    open(DST, 'wb').write(bytes(b))
    out = DST
except PermissionError:
    out = DST[:-4] + '2.exe'          # 目标被占用(可能正在运行), 写到新副本
    open(out, 'wb').write(bytes(b))
print('\n已生成:', out, len(b), '字节')
