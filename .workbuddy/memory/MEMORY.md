# 太阁立志传2 Godot 复刻 - 项目记忆（索引）

> 细节在仓库文档；本文件只留跨会话必需的边界/方法论/当前状态。
> 文档链：README.md → BREAKTHROUGHS.md → GAME_DATA_SPEC.md → BATTLE_SPEC.md → SNDATA_SPEC.md。旧文档 → docs/archive/。
> ⚠️ BREAKTHROUGHS.md 倒序：新条目以 `> 上一条（续N）：…` 插在文件最顶部（续130 起改此格式）。

## 边界
- Godot 4.7.1 自写；原版在 `<工程>/Taikou2 Original/`。仓库不打包素材。
- 2026-08-25 起：停 UI/像素/字体，只做数值+玩法 → 汇总进 GAME_DATA_SPEC.md。
- **硬性要求**：突破/推翻旧假设即插 BREAKTHROUGHS.md dated 条目（四段：突破/证据/仍未知/下一步）+ 打勾，倒序（新在上）。

## 逆向方法论（必守·核心坑）
- 映像 `scripts/_unpacked_mem.bin`(2MB, base 0x400000, OEP 0x4f44b0, off=va-0x400000)。反汇编用 `/Library/Frameworks/Python.framework/Versions/3.7/bin/python3`（capstone 5.0.1，通用 `python3` 无 capstone）；emu 用 Unicorn 2.1.4。函数边界=「所有 call rel32 目标」。
- ⚠️ **`_insn_addrs.pkl` 有空洞**（`0x49b417..0x49b43a` 缺10条）⇒ 基于它的断言静默假失败。关键处用 `scripts/_lindis.py` 现场反汇编核对。
- ⚠️ **`_insn_addrs.pkl` 的 `_d[0]`(IMAP)/`_d[1]`(FSTART) 存文件偏移非 VA**：按 VA `bisect` 会静默错（首跑 fn=0x588bf3 越界）。**先 `+BASE` 再比较**。
- ⚠️ `find_calls` 须写 `dst == tgt`；写成 `dst in TARGETS` 会把调用点重复计入每目标。
- ⚠️ capstone 共享 `Cs` 禁止嵌套 `disasm()` 迭代（破坏状态→静默0命中），须先物化 list。
- ⚠️ 断言须容忍渲染差异：小立即数省 `0x`（写 `+2` 非 `+0x2`）；钳制常写 `cmp ax,cap+1; jae`。
- 🔑 **bitset 定语义必须扫 setter**（续149）；找 setter：看 getter 邻近地址同形态写族。
- 🔑 禁止猜表形状，必须穷举（串池扫描）；数据须读原始 DAT（JSON 转储丢信息）。
- 🔑 定 stride 三证据：① lea 系数 ② 乘减序列 ③ 除法魔数（÷10=`0x66666667`+sar2、÷12=`0x2aaaaaab`+sar1、÷14=`0x92492493`+sar3、÷31=`0x84210843`+sar4、÷47=`0xae4c415d`）。
- 🔑 先查文档再动手（续144 教训：重复推导浪费半轮）；先查数据分布再定语义（代码形态 ≠ 运行期使用）。
- 🔑 整字覆盖 vs 带掩码 = 位域/标量分水岭；结构填充成对指纹（`mov word[+a],X` 紧跟 `mov word[+8],X`=批量初始化非字段写）。
- 🔑 表基址用「N 条×多锚点」打分裁决一次终结争议。
- 🔴 **「静态抓不到写入」≠ 须 emu**：常因 setter 按 `ecx=base+N` 参数化传入。排查：① 字面 `mov ecx,<base>` ② 沿 call 下探一层找「取实参作 this」(`push <base>; call helper`, helper 内 `esi=[esp+0xc]`) ③ 才下结论。
- 🔴 **「位移命中」≠「字段命中」**（多 struct 陷阱 6+ 次）：判定写点必须溯源基址寄存器。
- 🔴 **「函数内含某表基址」≠「该访问属于那张表」**：`sub eax,0x51eb88`+÷31 可能只是「城指针→城索引」换算。
- 🔴 **共享方法库陷阱**（5 次）：`0x49b960..0x49bda8` 通用 setter 库；某偏移出现在该区 ≠ 属于某 struct；须以绝对 xref 为准 + 确认真实 this + 读/写方向。
- 🔴 **写「A∧B」条件表前须逐条确认 `je`/`jne` 目标地址**（续148 自纠跳极性读反）。
- 🆕 **事件文本「第二来源」= HEXMES.LZW（续156 修正续150 旧注）**：旧记「XOR 加密资源 / 双轨制 / 经 0x49fe40 解析」**已推翻**——`0x49fe40`=`set_diplomacy`、`0x49fd80`=`rel_lookup`，均与文本无关（张冠李戴）。真相：事件/战斗文本的真正「第二来源」是 **HEXMES.LZW**，一个与 MESSAGE1~4 同构的**第 5 个 MSGX 文本容器**（283 条，静态 `ls11_decompress` 即可解）。旧分析因 `msgx_all_texts.json` 仅含 4 文件（6211 条）而查不到 HEXMES 锚点，才误判「无 MSGX 锚点 / XOR 资源」。交付：`scripts/event_text_xor_ref.py`(6/6) + `scripts/hexmes_texts.json`。
- 🆕 **MSGX 解析器结构（续156）**：全镜像仅 1 处 `mov eax,0x10624dd3`（÷2000 魔数）= 唯一解析器 `0x493500`，`cmp edx,3; ja` 只服务 slot0..3（MESSAGE1~4，句柄 `0x5249d8/0x524a08/0x524a50/0x524870`）；HEXMES 不在该 4-slot 数组，由独立路径服务（句柄运行时填充）。
- 🆕 **`0x4a3240` = sat_sub 包装器**（续150）：内部 `word[esi+0x26]`，`push 0x12c` 是减量非 MSG id。
- 🆕 **`val=0` 的 setter 调用 = 清除/撤销，非置位**（续150）：扫 setter 时须区分置 1 vs 清 0。

## 当前状态（2026-08-31，续150 为止）
- **S15 `0x5203c0` 築城/劇本イベント旗幟塊 25B（权威规格 GAME_DATA_SPEC §3.9.9；`s15_event_flags_ref.py` 63/63 + `s15_event_bits_named.py` 23/23）**：`+0` イベント進行 ID（值=bit号,0xff=無）/ `+1` 進捗（低5bit段階+高3bitフェーズ）/ `+2..+9` 段A bitset 8B=已発生 / `+0xa..+0x11` 段B bitset 8B=已喪失 / `+0x12` 実行済みマーカー(bool) / `+0x13..+0x18` 段C 6B=byte数组。SAVE `0x47f0a0`/LOAD `0x47f110` 逐字节坐实。
  - 访问器类 9 方法 `0x49c390..0x49c540`：get_a(`0x49c390`)/get_b(`0x49c3d0`)/get_c(`0x49c410` 读字节)/set_prog(`0x49c420` 低5,&0xe0)/set_hi3(`0x49c440` <<5,&0x1f)/set_a(`0x49c460`)/set_b(`0x49c4b0`)/set_c(`0x49c500` idx=[esp+4] val=[esp+8])/`0x49c520`(=`byte[+5]&7`=A24..A26)/`0x49c530`(=`byte[+5]>>3&3`=A27,A28)。
  - **14 bit 全部定名（续150 闭合）**：
    - 段A 已発生：1=桶狭間の戦い(1560, anchor `0x408a80` `cmp al,0xd` 玩家国13=駿河)、2=将軍暗殺/追放(MSG6492/6498)、3=石山本願寺の戦い/一向一揆(anchor `byte[esi+0x13]=0xd9` 武将217=下间赖照)、5=足利義昭上洛/将軍奉戴(1568,MSG6640/6642)、6=二条城築城/征夷大将軍宣下(1568,MSG6647/6674)、7=金崎撤退(1570,MSG6722/6726/6741)、8=安土城築城(MSG6787/6792/6802)、9=本能寺→山崎合戦(MSG6881/6883/6894)、10=光秀討伐(MSG6952/6810/6912)。
    - 段B 已喪失：4=岐阜、11=長篠合戦(1575,MSG6976/6977)、14=将軍家断交(MSG6959/6974)、15=今滨→長浜(MSG7025)、38=大阪。
    - 派发器 `0x41a400`(bit6→1→2→3→5→9→10)/`0x41a660`(bit4→7→11)，形态 `if(A‖B) continue; if(handler()) return;`。
    - `0x488030`=主人公依存フラグ初期化（÷47 魔数 `0xae4c415d`）：id==8→B1,B2,B3,B7,B9,A4,A5；else→B5,B6,B7,A10,B10(+id!=0 时 B3)。
  - **仍待破（续150 下一步）**：① 段C 6 字节语义（扫 `0x49c500` 调用点按索引0..5归类 idx/val）；② `0x49c520`/`0x49c530` 的消费者（A24..A28 是 get_a 未覆盖的 segA 高位 bit 子域）。
- 实体(370×47B@`0x519868`)：五维`+0x0a..+0x0e`、技能`+0x0f..+0x11`、生年`+0x1b`、国索引`+0x24`(255)、在城索引`+0x25`(255)、功勲`+0x26`(cap60000)、主君索引`word+0x2a`(0xffff=浪人)、`word+0x08`=compat_a|compat_b<<8(bits11-14=相性,bit15=茶会フラグ)。
- 表几何：`0x51eb88`城表31B×200(CASTLE_OFF=21845)、`0x519548`国情表stride5×49(`+0x04`=WORD国主武将号)、`0x5179b8`国政治表stride14×49、`0x51e1f6`物品池10B×200、`0x506ca8`名称总表stride9、`0x5203c0`S15三段25B。
- 国名 getter `0x49b400`、别名 getter `0x49b440`（岐阜/长滨/安土/大阪）。
- 两档计数上界 370(0x172) vs 359(0x167)，含义待考。
- ⚠️ 留档矛盾（§3.17.9）：`byte[城+0x08]`(0..250,170/200越界) 与 `word[城+0x0a]`(0..64592,199/200越界) 同症；`+0x0a`=`低字节0..100(5倍数)+高字节0..252`打包。须第三剧本或 emu。

## Godot 侧约定
- 预渲染画作 LINEAR+MIPMAPS；像素艺术 NEAREST+STRETCH_KEEP；CJK 走系统字体。
