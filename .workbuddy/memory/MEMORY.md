# 太阁立志传2 Godot 复刻 - 项目记忆（索引）

> 细节在仓库文档；本文件只留跨会话必需的边界/方法论/待破清单。
> 文档链：README.md → BREAKTHROUGHS.md → GAME_DATA_SPEC.md → BATTLE_SPEC.md → SNDATA_SPEC.md
> 旧 HANDOFF / REPLICATION / REVERSE_ENGINEERING / ENGINE_SPEC / HJMAPDAT_SPEC → `docs/archive/`

## 边界
- Godot 4.7.1 代码自写；原版 111 文件在 `<工程>/Taikou2 Original/`（`F:/Games/Taikou2` 路径不存在，勿写「数据为空」）。仓库不打包素材。
- 2026-08-25 起：停 UI/像素/字体，只做数值+玩法→汇总进 GAME_DATA_SPEC.md，美术用户自配。
- **硬性要求**：突破/推翻旧假设即插 BREAKTHROUGHS.md dated 条目(四段)+打勾，倒序(新在上)。

## 逆向方法论（必守）
- 映像 `scripts/_unpacked_mem.bin`(2MB,base 0x400000,OEP 0x4f44b0)；全镜像仅80栈帧序言→函数边界由「所有 call rel32 目标」推导；线性反汇编逐4KB+`va+=1`重同步。
- 工具：`_fdis.py`(只吃 call-target 函数头)·`_lindis.py`·`_string_pool_scan.py`·`_xref_reads.py`·`_emu_*.py`(Unicorn 2.1.4)；capstone 需 `from capstone.x86 import *`。
- **🔑 禁止猜表形状，必须穷举**（串池扫描推翻「兵种名不在EXE」）。**数据验证须读原始 DAT**（勿用 JSON 转储，字节经 Unicode 解码变 0xfffd 丢信息）。
- **🔑 断言「静态不可见」前先做字节级 xref 找 WRITE 点**（续89 推翻续84：填表代码就在同函数簇）。
- **🔑 字段扫描必用 `scripts/_ins_index.py`**（续71 固化）：① 索引在 `jmp` 处截断→MSVC `lea;jmp<cont>` 三元续体丢失；② `call` 后未失效 eax/ecx/edx→假字段。立即数 xref 落指令中间须按「包含」匹配。
- 教训：切片伪像造假表；xref 只抓绝对立即数；已四次误判「唯一 xref 静态表」语义→先确认引用函数真起点。两场景差分=判定「静态 vs 场景状态」最快手段；自相关须先剔除默认值。

## 已破速查（细节见文档）
- 格式 LS11/MSGX/GRP/IDX/SMODE/TOWNCHIP/KOS；BSDATA 700×59B·TOWNPOS 92城·SNDATA XOR流·SAVEDATA 16×20480B。
- 名表 `0x506ca8` stride9×370（**非指针表**）；`HJMAPDAT.DAT` 38×1700B；per-tick伤害 `0x42d270`；天气/季节 §3.9；49国国情 §3.10/§3.13；合戦布陣+計略 §3.10；地形系数 §3.12；技能/官位/授艺·经济 §3.x。
- **武将实体表 `0x519868` stride47×370**（多次实锤）；MSGX 全局 id↔文本 `msgx_id_map.json`/`msgx_all_texts.json`(6211条)。
- **单挑（续66）**：无「一击必杀」；伤害仅1处恒0..4；`0x4684c0`跳表5分支=`duel2_ref.py` 38/38。🔴`0x466e40`返回**体力**非武力。
- **大名/城主任命·继承（续65/70/78）**：城主(8)是**城表派生态**(`word[城+0x18]==武将号`)。**城/町表 `0x51eb88` stride31·200条·26B/条(~95%)**：`+0x00`武将指针/`+0x02`城指针/`+0x07`农商/`+0x08`次级/`+0x09`民心/`+0x0a`生产率/`+0x10`军粮/`+0x12`米/`+0x14`资金/**`+0x16`所属国**/**`+0x18`城主**/`+0x1a`次级民情/`+0x1b`城种(&7)/`+0x1d`。序列化器 `0x47e130`。
- **49国政治/关系表 `0x5179b8` stride14·49条（续71/79/81）**：`+0x00`城/町指针/`+0x04`=2B packed(flag|国主武将号0..369)/`+0x06`=`(关连国idx<<8)|attr`(hi<49)/`+0x08`=0x03常量(表内关联索引,续81 纠偏:非运行时覆盖)/`+0x09+0x0a`=0xff/**`+0x0b..+0x0d`关系属性(外交目标,续89 待追)**。⚠️ 与国情表 `0x519548`(stride5)是两张表。49条顺序按势力非国ID。`province_politics_ref.py` 15/15。
- **事件系统（续72/81/82）**：派发=[ctx+0]事件类型id(0..~60)双表——CONDITION(`[ctx+8]`=arg 比较后 `call 0x49b860`)/EFFECT(直接执行)并行，同 id 可兼有(id9:`0x4b4b20`+`0x44ca90`)。已破：`0x4e82c0`(13/14)·`0x4e7e10`(10)·`0x4b4b20`(9)·`0x44ca90`(9)·`0x4b3ac0`(15)·`0x4499f0`+`0x490c0`(0/1)。⚠️ 底层事件 id ≠ §3.7 分类表 `0x50da40`(27类)。`event_id_dispatch_ref.py`/`event_cond_ref.py` ALL PASS。`_evt_enum3.py`(liveness修正)。
- **🎯 外交系统 handler 级实锤（续89）**：主会议4项跳表 `jmp [eax*4+0x4c1668]`（听取意见`0x4c1830`/分派工作`0x4c1ef0`/出兵`0x4c2590`/结束会议）；**16项工作类型执行跳表 `jmp [eax*4+0x50c950`**（名表 `0x50c7e0` stride16B·参数表 `0x50c990` 3B/项）含**高压外交`0x4c41e0`/友好外交`0x4c4320`**；流程 `0x4c4270`选国→`0x4c4300`选使者→`0x519868+id*47`→MSGX `0x875`→存 `dword[0x525ea4]`。`diplomacy_ref.py` ALL PASS。
- **物品定义表(SNDATA流 32019, 189×19B, 续73/80)**：`名|0|cat(0..26)|val|tier[15]|flag[16]|grp[17]|0`；`idx15`等级评分/`idx16`稀有度档位/`idx17`系列(同号=同流派)。`item_table_ref.py` 21/21。
- 阵形名不在EXE(`byte[p+4]`仅内部编号)；SNDATA流尾3791B(续76)；时间全局 `byte[0x5205f0]`=1560起年偏移(续75)；§4.3 城内指令/城表/事件/单挑/任命 均已文档闭。

## 仍待破（按完成度低→高）
1. **外交数值核心（续89 延伸·本次目标）**：使者抵达后**关系值变更公式/成功率**——追 `0x525ea4` 下游消费 + `0x5179b8` 的 `+0x0b..+0x0d` 关系属性写入；`0x50c990` 3字节参数语义(`255`=不需要?)；`0x5080cc`八级国关系表无xref之谜；AI主动外交决策。
2. **事件系统 id 全映射**：剩余 17 候选(`_evt_enum3.py` opcodes=[])未读 id；id 2..8/11/12/16+ handler 未定位；CONDITION handler 抽「arg↔运行时值」谓词表。
3. **物品表↔物品池(stride12/10)绑定**；idx15公式；流尾3791B语义；商品基价`0x513ea8`；评价词8↔10绑定。
4. **section A 命名/抽样意图/值中文名**（结构+8类地形系数已闭,续67/68）。
5. 单挑体力初值赋值；AI选牌；城策略`0x4ac690`；绝嗣`0x4a4410`；实体`+0x25/26/2c`；国情`+0`低4位/`+2`/`0x47e440`。
6. 时间月/日定序（`0x5205f1/f2`）；其余史实事件 handler（按 MSGX 文本反查 push id，本能寺已验证）。

## Godot 侧约定
预渲染画作 LINEAR+MIPMAPS；像素艺术 NEAREST+STRETCH_KEEP；mipmap 只在 Image 上生成；CJK 走系统字体（**所有 `*CHAR.LZW` 是角色精灵非字体**）。
