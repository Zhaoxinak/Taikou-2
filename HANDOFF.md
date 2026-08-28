# HANDOFF.md — 太阁立志传2 Godot 复刻 · 交接文档

> **接手者请先读此文档**，再读 `REPLICATION.md`（Godot Demo 状态）和 `REVERSE_ENGINEERING.md`（数据破解全表）和 `ENGINE_SPEC.md`（EXE 引擎逆向）。
> **突破增量日志（每次破解的 chronological 记录，跨 AI 接手必看）**：→ `BREAKTHROUGHS.md`
> 最后更新：**2026-08-26**（建立突破日志制度 + 策略纠偏）。
> **诚实进度**：数据格式 ~85% · 引擎逻辑 ~10% · 可玩 Demo ~60% · 完美复刻 ~15-25%。
>
> ⚠️ **2026-08-25 策略变更**：停止 UI / 像素渲染 / 字体位图提取，转向 **数值 + 玩法** 抽取（单一文档 `GAME_DATA_SPEC.md`）。复刻方接数据用 JSON（`bsdata.json`/`towns.json`），文本走 MSGX+GBK，美术另配。**当前核心任务见 `BREAKTHROUGHS.md` 任务清单（#35–#42）**。

---

## 0. 一句话状态

数据格式层大部分已破（LS11 解压 100%、GBK 文本 100%、BSDATA 武将名、TOWNPOS 城镇坐标、NPKDATA/GRPDATA/HGRP 图形容器、KOS 音效、SMODE 界面）。

**当前方向（2026-08-25 起）= 数值 + 玩法 抽取**，不再做画面 / 字体 / 像素逆向。优先破解清单见 `BREAKTHROUGHS.md`（Task #35–#42）。**已破**：合战数据表(#35)、**per-tick 伤害公式(#36，见 §2.9)**、名称索引表(#40)、SNDATA 记录分类(#39)。**待破**：兵种/阵形/计略中文名(#37)、地形数值(#38)、事件系统(#41)、技能·授艺·经济公式(#42)、SNDATA 数据块字段语义。

**已降级 / 作废的旧假设**（勿被误导）：①「SNDATA 字符串解码 = 核心阻塞」——SNDATA 是结构化二进制，但用户已暂停画面方向，文本解码降级；②「字体系统逆向 = 核心路径」——真实 CJK 渲染是 Win32 GDI + 系统字体（`msyh.ttc`/Noto），所有 `*CHAR.LZW` 是角色精灵非字体，无需位图提取。

---

## 1. 双目录结构（最重要的前提）

| 路径 | 用途 |
|------|------|
| `F:/Games/Taikou 2` | **Godot 工程目录**（带空格）。所有脚本、场景、文档在这里。 |
| `F:/Games/Taikou2` | **原版游戏数据目录**（无空格）。97 个原版文件。`DataLoader.DATA_ROOT` 指向这里。 |

> 用户已确认：自有合法拷贝、仅本地单机玩、不传播。工程不打包原版素材，运行时从用户目录读取。

---

## 2. 已破解的数据格式（可直接用）

### 2.1 LS11 解压算法（100% 验证，32/32 文件）
- 光荣私有 LZ77 变体 + 256 字节频率字典。
- 文件结构：`0x00` "LS11"+12 零 → `0x10` 字典 256B → `0x110` 压缩长度(BE) → `0x114` 解压长度(BE) → `0x118` 数据偏移(BE, 通常 0x120)。
- **位流解码（关键，曾错）**：段1=连续'1'直到遇'0'（含该0）；段2=紧接着段1长度的位；索引=`(1<<段1长度)-2 + 段2值`。
- 索引<256 → 输出 `dictionary[索引]`；≥256 → 回退：`offset=索引-256`, `length=下一索引+3`。
- 实现：Python `scripts/real_assets.py`（`ls11_decompress`）；Godot `scripts/TaikouLZW.gd`。

### 2.2 对话文本 = 明文 GBK（2026-08-23 破解，99.998% 覆盖）
- `MESSAGE1-4.LZW` + `HEXMES.LZW`（共 5 个 MSGX 容器）经 LS11 解压后：
  - `0x00` "MSGX" → `0x04` uint16 LE 消息条数 N → `0x06` N×uint32 LE 指针表。
  - 消息靠指针表界定边界，`0x00` 为终止符。
- **编码 = 标准大端 GBK**：字节<0x80 → ASCII；字节≥0x80 → 2 字节大端 GBK 双字节汉字。
- 交付物：`scripts/gbk_table.json`（21,791 条码→汉字）；`scripts/TaikouTextDecoder.gd`（Godot 内验证通过）。
- 样例：`武将的军饷。每月从城池的收入中，按俸禄支付给武将。`

### 2.3 武将数据 BSDATA1/2.TR2
- 41300B = 700 条 × 59 字节/条（两文件完全相同 = 副本）。
- **名字在每条记录前 13 字节（明文 GBK）**：姓[0:4]+`00 00 00`+名[7:13]。
- 其余 46 字节为属性/标志（数值字段语义未完全映射）。

### 2.4 城镇数据
- `TOWNPOS.DAT`：92 城坐标，uint8(x,y) 格式，48×37 网格。
- `TOWNTBL.DAT`：城镇索引表。
- `towns.json`：已提取的城镇列表，`map_x∈[2,47]` / `map_y∈[1,36]`。
- **关键规则**：归一化必须用 `TOWN_GRID_W=48.0` / `TOWN_GRID_H=37.0`，**不能除以 MAP_W=256 / MAP_H=88**（会把 92 城挤到左上 4%）。

### 2.5 KOS 音效 = WAV（2026-08-24 破解，推翻"事件脚本"假设）
- 39 个 .KOS 全是 KOEI 音效 = RIFF/WAVE（mono 22050Hz 8-bit PCM）。
- 布局：`byte[0]=0xAE` 标记 + `byte[1:]` 逐字节 XOR `0xAE` = 完整个合法 RIFF/WAVE。
- 文件名语义：CANCEL/CLICK/KOUGEKI1·2(攻击)/SEIKOU(成功)/SHIPPAI(失败)/KAMINARI(雷)/KEMURI(烟)/NINJA/IKARI(怒)…
- 交付物：`scripts/_decode_kos_wav.py` → `scripts/kos_wav/*.wav`（39 个可播放音效）。
- **重要**：`KosVm.gd`/`kos_opcodes.json`/`kos_message_map.json` 等全部基于错误前提，已作废。

### 2.6 图形格式
| 文件 | 格式 | 状态 |
|------|------|------|
| `KOEILOGO/ACERTWP/PRESS.GRP` | 6B 头 + RGB565 (320×200) | ✅ 已解 |
| `NPKDATA.IDX` | 23 条图像，全 4bpp，16 色 LE RGB444 调色板 + kaodata 控制位流 | ✅ 完全破解（见 `NPK_SPEC.md`） |
| `GRPDATA.LZW` / `HGRP.LZW` | IDX 容器：139/126 条目，3bpp(8色) MSB-first | ✅ 已破解（真调色板未得） |
| `SMODE.GRP` | 6B 头 + 640×200 8bpp 索引 + 5531B 尾（调色板在 tail[0:512] 256 RGB565 LE 自包含） | ✅ 已解 |
| `TOWNCHIP.LZW` | KOEI 4bpp 位平面交错，16×16×341 瓦片 | ✅ 已解 |
| `HBCHAR.LZW` | EGA 4 平面位图，16×16×384 精灵 | ✅ 已解（1536 字形） |
| `TOWNMAP.LZW` | 48×32 城镇场景瓦片索引图 | ✅ 已解 |
| `SHOPMAP.LZW` | 32×32 商店室内布局 | ✅ 已解 |
| `ANMSEQ.LZW` | 动画帧索引表 | ✅ 已解 |
| `MAPCHIP.LZW` | 88 张 16×16 裸 RGB565 地形 | ⚠️ 解压成功但视觉验证为噪点 |

### 2.7 EXE 脱壳
- 用 Unicorn 引擎静态脱壳成功（无需 x32dbg/Windows）。
- OEP = VA `0x4f44b0`（MSVC CRT 启动帧）。
- Dump：`scripts/_unpacked_mem.bin`（2MB，基址 0x400000）。
- 解压后暴露：9218 ASCII 串、完整文件清单 89 个、真实导入表（MP3.DLL 等）。

### 2.8 名称索引总表 `0x506ca8`（2026-08-26 全破译，stride=9）
- **四块布局（纠正旧「变长/null/stride14」误解码）**：0–48 国(49) / 49–87 附加地名(39,flag前缀) / **88–291 城·町(204，城 id c → 槽 88+c)** / 292–369 职种·角色·特殊NPC(78,flag前缀)。
- **城名权威**：`castle_names_exe.json` 是 EXE 内部真名（与社区 `castle_names.json` 88/92 一致，4 处异字：泷山/泷川·兴津/兴泽·二俣/二俁·长筱/长篠）。⚠️ 旧 `towns.json` 用了社区后期名（岐阜→稻叶山、大阪→本愿寺等），复刻以 EXE 名为准。
- **职种/师匠名（292–369）** 已解出（大名/宿老/队长/大将/步兵/枪铸造/大师/画匠/僧侣/南蛮商人/秘商人/国友(鉄砲)/山科言継/百地(忍者)/施药院/快川/近卫/伊达/阿尔梅(Almeida)/…），即「修行师父/町角色」名称池 → 服务技能→师父授艺表。
- 产物：`name_table.json`（四块全量）、`castle_names_exe.json`（92 城权威名 + is_alt）。

### 2.9 合战 per-tick 兵力消耗公式（2026-08-26 晚 全破 + 深夜 Unicorn 实跑验证，主函数 `0x42d270`）
- **公式链**：`0x42d270`(一回合结算，写回兵力) → `0x42d5d0`(阵营战力汇总) → `0x42d730`/`0x42d5a0`(阵营修正) → `0x43a9c0`(攻击除数表 `0x503770`) / `0x43cd10`(兵力递减曲线) / `0x439050`·`0x4390c0`(section A) / `0x4ebc50`·`0x4ebcd0`(muldiv/饱和减法)。
- **单位槽**：15 槽 @ `0x513910`，**stride 24 B**（`+0x0c`兵力w / `+0x11`士气 / `+0x12`士气损失 / `+0x13`状态[低2位=兵种类别,高4位≠0=退场] / `+0x15` bit2=阵营）。
- **核心式**：`战力=(atk+装备加成)×(100+净士气//10)//100`（下限10）`×troop_scale(兵力)//23`；`E=本方战力//对方存活数×2`；`base=14*(E方总战力//对方存活数)//攻击除数`（`base_vs_side0` 用 side1 总战力，`base_vs_side1` 用 side0 总战力）；`dmg=base//(防御//4+50)+1`（`side==1且mode_m1`→0）；`兵力=max(0,兵力-dmg)`。
- **阵营修正（⚠️ 已纠偏）**：side0 恒 `×4/5`，两将同类(kind)再 `×4/5`；side1 仅当 `mode_m1` 且 `parity&1` 时 `>>3`。**`0x42d730` 全程不读 flags 位**（旧「`flags&0x10→÷2`」「`battle_type==0 额外÷2`」均已证伪）。
- **section A 真实数值用途**：低4位=**攻击除数表索引**；高4位=双方除数 ±1 对冲（静态恒0）。⚠️ **纠偏**：旧说「section A=交战判定比较矩阵(`0x423a9d`)」已证伪——`0x423910` 是 UI 属性条显示例程，只写 `0x511358`。
- **✅ Unicorn 隔离仿真验证（2026-08-26 深夜）**：`scripts/_emu_battle.py` 实跑真实二进制 `0x42d270`，3 场景（4+4 / 7+7 / 2退场+flags+同类）**逐单位兵力 bit-for-bit 吻合**，公式现为「反汇编 + 真二进制仿真」双实证。
- **文档/产物**：`BATTLE_SPEC.md §9`（完整，含 §9.10 验证报告）、`GAME_DATA_SPEC.md §4.5.1`（复刻用摘要+验证印章）、**`scripts/battle_formula_ref.py`**（可执行参考实现，自检通过）、`scripts/_emu_battle.py`（仿真验证）。
- **方法论（接手必读）**：本脱壳镜像**几乎无标准栈帧序言**（全 2MB 仅 80 处 `push ebp;mov ebp,esp`）→ 函数边界必须用「所有 `call rel32` 目标」推导；线性反汇编需逐 4KB 块 + `va+=1` 重同步。工具：`scripts/_fdis.py`（带符号标注反汇编）、`scripts/_profile_all_funcs.py`（4212 函数算术密度画像，正是它定位到 `0x42d270`）。

---

## 3. 当前核心阻塞：SNDATA 字符串解码

### 3.1 SNDATA 结构（已破，✅）
- `SNDATA1.TR2` / `SNDATA2.TR2`：均 40856B（两文件结构相同、数据不同）。
- 布局：`[0:16]` ASCII `"TAIKOU2_SCENARIO"` 签名 → `[16:]` **833 条 × 49 字节记录** → `[40833:40856]` 23B 尾（场景1=全 `0x0C` / 场景2=全 `0x0A`）。
- 校验 `16 + 833×49 + 23 = 40856` ✅。
- 记录尺寸 49 由反汇编确认（访问器 `0x47d890`：`lea edx,[ecx+eax+0x10]` + `push 0x31`=49）。
- **⚠️ 不要用自相关定记录尺寸**：SNDATA 内容以 `0x01/0x00` 为主（低熵），自相关在 S=59 给出假峰。真值来自反汇编。

### 3.2 SNDATA 记录类型（2026-08-24 修正）

**重大纠正**：833 条记录**非同质**，且记录 23–830 **不是纯文本字符串表**，而是**结构化二进制记录**（固定布局 structs）。

| 类别 | 记录范围 | 条数 | 内容 |
|------|----------|------|------|
| 头部 | 0 | 1 | 4B 场景 ID + 45 位标志位域 |
| 标志位域 | 1–22 | 22 | 纯 `0x00/0x01`（场景状态布尔开关） |
| **结构化二进制** | 23–830（含填充槽） | ~690 | 每条 49B 内含多个二进制字段，以 `0x0C`/`0xF3` 为字段分隔符 |
| 填充槽 | 24–27 / 602–665 / 759–804 / 831–832 | ~120 | 整条单值（`0xFF`/`0x0C`/`0xF3`），随场景变 → 未使用空位 |

**为什么之前误判为"字符串表"**：
- 用 GBK 强制解码时，有些字节对恰好构成合法 GBK（如 `c1 a4`=沥、`c6 a8`=屁、`cd da`=挖）。
- 但同一"汉字"在不同记录的固定偏移反复出现（`篌`/`驨`/`岓` 几乎每条都有），这不是真实文本的模式。
- 聚合统计显示 HH/(HH+HL)≈65% → 看似 GBK 双字节签名，**但这恰好是随机二进制数据的自然比率**（GBK trail 字节 ≥0x80 的概率约 65%）。
- 严格 GBK 解码 4477 个文本 run 中 **37.8% 直接报错**（如 `c4 3d` 的 trail `0x3d` < 0x40 非法）。
- XOR/ADD 穷举各 0–255 最高仅 70.6%（XOR 83），无峰 → 排除"GBK + 固定变换"。

**结论**：SNDATA 文本字段用的是 **EXE 内部计算的编码**（GBK 码 → 字形索引 → 字体位图），不是标准 GBK，也不是简单的单字节变换。解码需要逆向 EXE 字体加载器的 GBK→字形映射逻辑（见 §4）。

### 3.3 跨场景差异
- 833 条中 805 条差异 >20B → 绝大多数为**场景状态**（非静态主数据）。
- 仅 14 条两场景完全相同。

---

## 4. 字体系统逆向（2026-08-24 定位；⚠️ 2026-08-25 起已降级，非当前方向）

> ⚠️ **本节约为历史定位记录，非当前阻塞**：2026-08-25 策略变更后，字体 / 像素方向已暂停。真实 CJK 渲染 = Win32 GDI + 系统字体，无需位图提取。下方内容保留供参考。

### 4.1 rmKOEI.bin = 卸载程序 DLL（不是字体渲染器）

**重大纠正**：MEMORY.md 旧笔记记 rmKOEI.bin 为"位图字体渲染 DLL"，**实测为误**。

- PE DLL（24,576B），3 节：`.text`(0x2b46) / `.rdata`(0xa00) / `.data`(0x2600)。
- `.rdata` 含 MSVC 运行时错误字符串 + API 导入表：`MessageBoxA`、`DeleteFileA`、`RemoveDirectoryA`、`SetCurrentDirectoryA`、`GetWindowsDirectoryA`、`SHChangeNotify`、`lstrcpyA`。
- `.data` 含**明文 GBK 卸载程序字符串**：`光荣卸载程序`、`指令行不正确`、`无法删除卸载程序`、`卸载完毕。`、`为了删除卸载程序使用的临时文件，请重新启动电脑。`、`无法移动到Windows文件夹。`、`检查Windows文件夹失败。`
- 源文件标记：`$Id: textsub.cpp 1.2 1996/01/17 02:44:02 Ashihara Exp Ashihara $`
- **没有任何字体/GDI API 导入**（无 `CreateDIBitmap`/`SelectObject`/`TextOut`）。
- **结论**：rmKOEI.bin 是 KOEI **卸载程序 DLL**（textsub.cpp, 1996, Ashihara），与文字解码完全无关。

> 这与 2026-08-23 的结论"对话文本和武将名是明文 GBK，不需要 rmKOEI"一致——结论正确，但旧文档对 rmKOEI 性质的描述是错的。

### 4.2 字体加载器在主 EXE 内（已定位）

脱壳后 EXE（`_unpacked_mem.bin`，基址 0x400000）内找到字体文件名字符串：

| 字符串 | VA |
|--------|----|
| `C:HBCHAR.LZW` | `0x5030e8` |
| `C:HBCHAR2.LZW` | `0x5030f8` |
| `C:HJCHAR.LZW` | `0x5034d0` |
| `C:HKCHAR.LZW` | `0x5034f0` |
| `C:TOWNCHAR.LZW` | `0x506bb0` |

**字体加载器** `0x424120`（通过 xref `C:HBCHAR.LZW` 字符串定位）：
1. 读取 `C:HBCHAR.LZW` → 调用 `0x441330`/`0x441360`（LS11 解压）
2. `0x424320` 按字形索引 blit 位图到全局字形缓冲区：`stride = esi*5<<6` = 320 字节/字形
3. 字形缓冲区地址：`0x524a38` / `0x524918`

**关键认知**：字形→字符的映射由**字体文件内字形的排列顺序**决定（加载器把字形 k blit 到 slot k），不是查表。

### 4.3 运行时字形表 0x519868（核心数据结构）

- 位于 EXE 数据段，**370 条目 × 47 字节（stride 0x2f）**。
- **加载时全为零**——由字体加载器在运行时填充。
- 全镜像中有 **588 处引用** `0x519868` → 它是**中央运行时字形表**，每次文本绘制都会访问。
- `0x443810` 是字形缓存构建器：扫描此表，读 `byte[0x24]`（页选择器），检查 `0x2d`/`0x29` 标志位，计算 `shl ecx,3`(×8) 偏移。

### 4.4 字体文件字形统计（经 LS11 解压后）

| 文件 | 解压大小 | 字形数 | 用途 |
|------|----------|--------|------|
| `HBCHAR.LZW` | 49152B | 1536 | 战斗精灵（16×16 1bpp EGA） |
| `TOWNCHAR.LZW` | 27136B | 848 | 城镇角色 |
| `HJCHAR.LZW` | 38464B | 1202 | 合战角色 |
| `HKCHAR.LZW` | 42560B | 1330 | 角色精灵 |

- 各字体文件的字形集**不同**（不是同一套字符的子集），说明不同场景用不同字符集。
- 字体文件内**没有内嵌字符码表**——纯位图数据。

### 4.5 无显式 glyph→GBK 查找表

- 扫描整个 `_unpacked_mem.bin`：最长连续"合法 GBK LE u16"run 仅 57 条（需要 ≥200 才算表）→ **EXE 中没有静态 glyph→GBK 查找表**。
- "LS11" 魔术字符串在 EXE 中不存在（解压算法内联在代码中，不用字符串标记）。

### 4.6 GBK 处理签名聚集区 0x443xxx

EXE 内 `cmp al,0x81`（GBK lead byte 检查）出现 14 次，`cmp al,0xa1` 出现 6 次，聚集于 `0x443xxx` 段——这是**真正的文本/字体模块**所在。

### 4.7 下一步（接手者应做的）

1. **反汇编 `0x424120`（字体加载器）完整逻辑**：看它如何从 LZW 解压数据中提取字形、如何分配字形索引、如何填充 `0x519868` 表的 47 字节条目。
2. **反汇编 `0x443xxx` 文本模块**：特别是 `cmp al,0x81`/`cmp al,0xa1` 所在的函数——这是 GBK 码→字形索引的转换逻辑。
3. **用 Unicorn 实跑字体加载**：模拟 `0x424120` 加载 HBCHAR.LZW，dump `0x519868` 表的填充结果，看每个字形条目的字符码字段。
4. **渲染字形位图为 ASCII-art**：把 HBCHAR 前 64 个字形渲染出来，看是否能识别出 ASCII 字符或常用汉字（字形排列可能是 ASCII 顺序或 GBK 区位码顺序）。
5. **对照 SNDATA 字段**：一旦知道字形索引→GBK 的映射，就能把 SNDATA 记录中的二进制字段解码为可读文本。

---

## 5. 关键教训 / 坑（勿重复）

1. **自相关定记录尺寸在低熵数据上会假阳性**：SNDATA 用自相关得 S=59 假峰，真值是 S=49（反汇编确认）。
2. **长度匹配 ≠ 格式正确**：MAPCHIP 解压 45056B = 256×88×2 看似匹配，但 RGB565 解码是噪点。
3. **"调色板在 EXE 0x100" 要验 ASCII**：EXE@0x100 实为 PE 资源表字符串 `BuckALI`/`rsrc`，不是调色板。
4. **必须把渲染结果给用户看**：不能凭"看起来有结构"就声称解码成功。
5. **KOS 不是脚本**：曾把 PCM 音频采样当字节码扫 uint16，完全是误读。
6. **rmKOEI 不是字体渲染器**：它是卸载程序 DLL（textsub.cpp），导入的全是文件操作 API。
7. **SNDATA 记录不是纯文本**：强制 GBK 解码出"汉字"是假象——同一字符在固定偏移反复出现 = 结构化二进制，不是文本。
8. **Godot 4 API**：`ImageTexture` 没有 `set_generate_mipmaps`，只在 `Image` 上调 mipmap → 建 texture 自动带上。
9. **Godot 渲染过滤器**：KOEI 预渲染画作 → `TEXTURE_FILTER_LINEAR_WITH_MIPMAPS`；像素艺术 → `TEXTURE_FILTER_NEAREST` + `STRETCH_KEEP`。错选 = "彩虹噪点"。

---

## 6. 关键文件索引

### 6.1 文档
| 文件 | 内容 |
|------|------|
| `HANDOFF.md`（本文档） | 交接总览 |
| `REPLICATION.md` | Godot Demo 状态 / 接手清单 / 52 个验证脚本 |
| `REVERSE_ENGINEERING.md` | 数据破解全表 / EXE 脱壳手册 / KOS 纠偏 |
| `ENGINE_SPEC.md` | EXE 引擎逆向规范（读原语 / SNDATA / IDX / 调色板 / 字体） |
| `NPK_SPEC.md` | NPKDATA.IDX 4bpp 图像格式规范 |

### 6.2 核心脚本（Python，逆向分析用）
| 脚本 | 用途 |
|------|------|
| `scripts/_unpack_exe.py` | Unicorn 静态脱壳 → `_unpacked_mem.bin` |
| `scripts/_probe_exe.py` | PE 静态分析基线 |
| `scripts/real_assets.py` | Python 解码库（LS11 + 位平面 + 调色板 + 精灵导出） |
| `scripts/_decode_npk.py` | NPKDATA.IDX 4bpp 解码器 |
| `scripts/_decode_grp_container.py` | IDX 容器（GRPDATA/HGRP）解码器 |
| `scripts/_decode_kos_wav.py` | KOS 音效 → WAV 解码器 |
| `scripts/_decode_fonts.py` | 字体容器 LS11 解压 + 字形统计 |
| `scripts/_sndata_encoding_probe.py` | SNDATA 编码探测（hex dump + GBK 验证） |
| `scripts/_sndata_text_vs_binary.py` | SNDATA 文本/二进制分类 |
| `scripts/_render_glyphs_ascii.py` | 字形位图 → ASCII-art 渲染（未完成，下一步） |
| `scripts/_disasm_glyph_lookup.py` | `0x443810` 字形查找函数反汇编 |
| `scripts/_disasm_textmod.py` | `0x443xxx` GBK 文本模块反汇编 |
| `scripts/_scan_glyph_table.py` | 扫描 EXE 中 glyph→GBK 查找表 |
| `scripts/_xref_fonttbl.py` | `0x519868` 字形表交叉引用 |
| `scripts/_emu_sndata_loader.py` | Unicorn 模拟 SNDATA 加载 |

### 6.3 Godot 脚本（游戏端）
| 脚本 | 用途 |
|------|------|
| `scripts/TaikouLZW.gd` | LS11 解压（Godot 端） |
| `scripts/TaikouTextDecoder.gd` | GBK 文本解码（加载 gbk_table.json） |
| `scripts/TaikouImage.gd` | 图形解码（GRP/SMODE/NPK 等） |
| `scripts/GameAssets.gd` | 资产管道 |
| `scripts/DataLoader.gd` | 数据加载（`DATA_ROOT = "F:/Games/Taikou2"`） |
| `scripts/Database.gd` | 武将/城镇数据库 |
| `scripts/KOEITheme.gd` | 全局 KOEI Win95 主题 |

### 6.4 已作废的脚本（勿用）
- `scripts/KosVm.gd` / `KosEvents.gd` / `KosFlagMap.gd` — 基于错误的"KOS=事件脚本"假设
- `scripts/_build_kos_opcodes.py` / `_build_kos_message_map.py` / `_build_kos_flag_map.py` — 同上
- `scripts/_verify_kos_*.gd`（16 个）— 同上

---

## 7. 接手者的工作优先级

> **当前权威优先级清单 = `BREAKTHROUGHS.md` 的「当前任务清单」（Task #35–#42，数值 / 玩法方向）。** 下方是 2026-08-24 的历史清单（字体 / SNDATA 方向），仅供参考，部分已降级。

<历史清单 2026-08-24，仅供参考>
```
1. 反汇编 0x424120 字体加载器 → GBK→字形索引映射（⚠️ 已降级，非当前方向）
2. 用字形映射解码 SNDATA 字段（⚠️ 已降级）
3. SNDATA 标志位语义（rec 1-22 的 0x00/0x01 位域）
4. 合战地图 HBMAP/HKMAP/HJMAPDAT.DAT 格式逆向
5. BSDATA 59B 记录 46B 属性字段语义
6. END.GRP / FACE.LZW / EXTFACE.PK8
7. GRPDATA/HGRP 3bpp 真调色板
8. Godot 玩法扩展（合战/多结局）—— 等数值/玩法表完成
```
</历史清单>

---

## 8. 环境

- **Python venv**：`C:/Users/Administrator/.workbuddy/binaries/python/envs/default/Scripts/python.exe`（已装 unicorn 2.1.4 + capstone 5.0.7）
- **Godot 4.7.1**：`F:/Games/New-Life/Godot_v4.7.1-stable_win64.exe/Godot_v4.7.1-stable_win64.exe`
- **Godot 工程**：`F:/Games/Taikou 2`（`project.godot`：viewport 1024×640，main_scene = `res://scenes/Main.tscn`）
- **首次运行**须先 `--import` 注册 class_name
- **原版数据**：`F:/Games/Taikou2`（`TAIK2W95.exe` + 97 文件）
- **脱壳后 EXE**：`F:/Games/Taikou 2/scripts/_unpacked_mem.bin`（2MB，基址 0x400000）

> 最后更新：2026-08-24。配套文档：`REPLICATION.md` / `REVERSE_ENGINEERING.md` / `ENGINE_SPEC.md` / `NPK_SPEC.md`。
