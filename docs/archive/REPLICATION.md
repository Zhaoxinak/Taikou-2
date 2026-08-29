> ⚠️ **已归档（2026-08-29）**：本文档不再是权威入口。请改读仓库根目录 `README.md`。
> 归档说明见 `docs/archive/README.md`。
# 太阁立志传2 —— Godot 4.7.1 复刻 / 迁移文档

> 本文档为**接手者（人或 AI）**准备，目标：在 Cursor 等环境里继续本项目时，
> 不重复我们已经踩过的坑、直接复用已逆向出的格式与数据。
> 最后更新：**2026-08-24**（交接版）。  
> **诚实进度**：数据逆向 ~70% · 可玩 Demo ~60% · 对标原版完整玩法 ~15–25% · **完美复刻远未完成**。  
> 接手者请先读 **`HANDOFF.md`**（交接总入口），再读 **§11 接手清单** 和 **§6 死路警告**。  
> **逆向/脱壳专项**见 **`REVERSE_ENGINEERING.md`**；**EXE 引擎规范**见 **`ENGINE_SPEC.md`**（含字体系统 §7）。

---

## 0. 项目模式与法律边界（务必先读）

- **模式 = 源码移植（引擎重实现）**：我们写 Godot 引擎，游戏数据来自用户**自己合法拥有**的太阁2拷贝。
- **仓库不提交任何原版素材/创意内容**（立绘、音乐、原版台词等）。运行时从用户目录（见 §2）现场读取。
- 用户已确认：自有合法拷贝、仅本地单机玩。
- ⚠️ **关键事实**：你手里的 `TAIK2W95.exe` 是 **【中文汉化版】**，文本直接用 **GBK** 编码。**不是**日文原版，也**不是**光荣私有乱码页。

---

## 1. 环境与运行方式

### 1.1 Godot 二进制路径（容易踩的坑）

实际 exe 路径里，**`.exe` 文件名本身是一层目录，里面才是真 exe**：

```
F:/Games/New-Life/Godot_v4.7.1-stable_win64.exe/Godot_v4.7.1-stable_win64.exe
                                    ^^^^^^^^^^^ 这一层是目录名，不是后缀
```

### 1.2 无头运行前置

- 首次运行须先 `--import` 注册 `class_name`（否则报 "not declared"）：
  ```bash
  GODOT="F:/Games/New-Life/Godot_v4.7.1-stable_win64.exe/Godot_v4.7.1-stable_win64.exe"
  cd "F:/Games/Taikou 2"
  "$GODOT" --headless --import --path "F:/Games/Taikou 2"
  ```
- `project.godot`：`config_version=5`、`run/main_scene=res://scenes/Main.tscn`、`autoload GameState=res://scripts/GameState.gd`。窗口 1024×640。

### 1.3 验证脚本（都放 `scripts/` 下，直接用）

```bash
"$GODOT" --headless --script scripts/_verify_text.gd   --path "F:/Games/Taikou 2"   # 对话文本解码
"$GODOT" --headless --script scripts/_verify_db.gd     --path "F:/Games/Taikou 2"   # 700武将入库
"$GODOT" --headless --script scripts/_verify_wiring.gd --path "F:/Games/Taikou 2"   # 真实数据接入原型(WIRING_OK)
"$GODOT" --headless --script scripts/_verify_chip.gd   --path "F:/Games/Taikou 2"   # CHIP/CHAR 图形解码(STAGE_CHIP_OK)
"$GODOT" --headless --script scripts/_verify_towns.gd  --path "F:/Games/Taikou 2"   # 城镇表加载(STAGE_TOWNS_OK)
"$GODOT" --headless --script scripts/_verify_faces.gd  --path "F:/Games/Taikou 2"   # FACE 肖像 NPK(STAGE_FACE_OK)
"$GODOT" --headless --script scripts/_verify_kos.gd    --path "F:/Games/Taikou 2"   # KOS 音效解码(STAGE_KOS_OK)
"$GODOT" --headless --script scripts/_verify_battle.gd --path "F:/Games/Taikou 2"   # 战斗卡组(STAGE_BATTLE_OK)
"$GODOT" --headless --script scripts/_verify_sndata.gd --path "F:/Games/Taikou 2"   # SNDATA 头(STAGE_SNDATA_OK)
"$GODOT" --headless --script scripts/_verify_scenario.gd --path "F:/Games/Taikou 2" # SNDATA 标志(STAGE_SCENARIO_OK)
"$GODOT" --headless --script scripts/_verify_messages.gd --path "F:/Games/Taikou 2" # KOS台词映射(STAGE_MESSAGES_OK)
```

> 注：`--script` 模式下 **autoload 不会自动注册**，验证脚本里都是用 `preload(...)` 或手动 `new()` 来拿对象。  
> 有 stdout 时用 **console 版**：`Godot_v4.7.1-stable_win64_console.exe`（同目录）。

### 1.4 如何游玩（当前 Demo）

1. Godot 打开 `F:/Games/Taikou 2`，按 **F5** 运行（主场景 `res://scenes/Main.tscn`）。
2. 主菜单：**继续游戏** / **新游戏（选 3 槽位之一）** / 读取存档预览。
3. 典型通关线：清洲（修行/打工）→ 岐阜 ⚔ 斋藤 → 小谷 ⚔ 浅井 → 二条 ⚔ 信长 → 通关画面。
4. 默认玩家：**木下藤吉郎 #16**，居城 **0x42 清洲**。

### 1.5 验证脚本全表（52 个，`_verify_*.gd`）

PowerShell 示例（换路径时改 `$G` 与 `--path`）：

```powershell
$G = 'F:\Games\New-Life\Godot_v4.7.1-stable_win64.exe\Godot_v4.7.1-stable_win64_console.exe'
$P = 'F:\Games\Taikou 2'
& $G --headless --script "$P\scripts\_verify_story.gd" --path $P
```

| 类别 | 脚本 | 验证内容 |
|---|---|---|
| 数据层 | `_verify_text` `_verify_db` `_verify_bsdata` `_verify_sndata` `_verify_scenario` `_verify_messages` | GBK 文本、700 武将、BSDATA 字段、SNDATA 头、剧本标志、KOS→MESSAGE |
| 图形 | `_verify_chip` `_verify_grp` `_verify_faces` `_verify_assets` `_verify_end` `_verify_smode` `_verify_smode_hotspots` | CHIP/CHAR、GRP、FACE 肖像、场景资源、END/SMODE 变体 |
| 接线 | `_verify_wiring` `_verify_towns` `_verify_town` | 真实数据接入、城镇表、城内场景 |
| 战斗 | `_verify_battle` `_verify_retainer_battle` | 卡组构建、家臣参战 |
| KOS | `_verify_kos` `_verify_kos_vm` `_verify_kos_script` `_verify_kos_ops` `_verify_kos_branch` `_verify_kos_linear` `_verify_kos_effects` `_verify_kos_flag` `_verify_kos_path_score` `_verify_kos_flag_threshold` | 解密、VM、分支、flag 阈值、路径分 |
| 剧情 | `_verify_story` `_verify_feast` `_verify_feast_event` `_verify_feast_deep_event` `_verify_feast_flag_gate` | 主线进度、宴请 flag、宴后 KOS 事件 |
| 地图 | `_verify_travel` `_verify_travel_cost` | 行军天数/金钱/体力消耗 |
| 城内 | `_verify_town_work` | 城下打工三种（筑城/算用/军学） |
| 外交 | `_verify_diplomacy` `_verify_diplo_spread` `_verify_diplo_events` `_verify_diplomacy_weight` | 送礼宴请、友好度传播、事件权重 |
| 家臣 | `_verify_retainers` `_verify_retainer_pick` `_verify_retainer_rotate` | 招募、挑选、轮换 |
| 存档 | `_verify_save` `_verify_save_slots` `_verify_save_meta` `_verify_save_timestamp` `_verify_save_sorted` `_verify_save_delete` `_verify_new_game_slot` `_verify_new_game_autosave` | 3 槽位读写、元数据、排序、删除、新游戏 |
| 音频 | `_verify_audio` | 原版 WAV/MID 读取 |

批量跑（PowerShell）：

```powershell
Get-ChildItem "$P\scripts\_verify_*.gd" | ForEach-Object {
  Write-Host "=== $($_.Name) ==="
  & $G --headless --script $_.FullName --path $P
}
```

---

## 2. 目录结构（两个目录！路径大小写/空格不同）

| 路径 | 含义 | 备注 |
|---|---|---|
| `F:/Games/Taikou 2` | **Godot 工程目录**（带空格） | 我们写的引擎代码在这里 |
| `F:/Games/Taikou2` | **原版游戏数据目录**（无空格） | = `DataLoader.DATA_ROOT`，用户自有拷贝 |

`DataLoader.gd` 里写死：`const DATA_ROOT := "F:/Games/Taikou2"`。
换机器/换目录时改这一处即可。

---

## 3. 已逆向的文件格式（核心财富，务必复用）

### 3.1 LS11 压缩（全部 33 个 `.LZW` 已 100% 验证可解压）

光荣自研 **LZ77 变体 + 256 字节频率字典**。

文件头结构：
```
0x000  "LS11" + 12×0x00          (16B 头)
0x010  256 字节字典 (index→实际字节，按出现频率排序)
0x110  压缩数据长度  (4B, 大端)
0x114  解压后长度    (4B, 大端)
0x118  数据区起始偏移(4B, 大端, 通常 0x120)
0x120  压缩数据 (MSB-first 位流)
```

位流解码（一元前缀，曾错，现已对）：
1. **段1** = 连续读 `1` 直到遇 `0`（**含该 0**）。
2. **段2** = 紧跟段1长度的那么多位。
3. `索引值 = (2^段1长度 − 2) + 段2值`。
4. 索引 `< 256` → 输出 `dictionary[索引]`；
   索引 `≥ 256` → 回退引用：`offset = 索引−256`，`length = 下一索引 + 3`。

GDScript 实现（已验证）：`scripts/TaikouLZW.gd::decompress()`。

### 3.2 MSGX 文本容器（`MESSAGE1~4.LZW` 解压后的结构）

```
0x00  ASCII "MSGX"
0x04  uint16 LE  消息条数 N  (MESSAGE1 = 0x06C7 = 1735)
0x06  N × uint32 LE  指针表，指向各消息起始偏移
       (自洽: 6 + N*4 = 第一个指针值)
之后   消息字节流，由指针表界定边界
```

- 各消息**长度奇偶不一**（内嵌 ASCII 时可能为偶数），**不能**靠 `00 00` 判定边界，必须按指针表切分。
- 解析器：`scripts/TaikouMessage.gd::parse_bytes()` → 返回 `Array[PackedByteArray]`（每条消息的原始字节）。

### 3.3 文本字符编码 = **GBK 混合编码**（⚠️ 最重要的纠偏）

之前数轮误判为「KOEI 私有置换码 / 日文乱码页」，全是死路。实测：

```
字节 < 0x80           → 单字节 ASCII 原文 (数字/字母/符号/控制码)
字节 ≥ 0x80           → 2 字节【大端】GBK 双字节汉字 (高字节在前)
单个 0x00 字节         → 消息终止符
```

验证：`CE E4 BD AB B5 C4 …` 直接按 GBK 解 = **「武将的军饷……」**。
4 个 MESSAGE 文件共 104,911 字，**仅 2 个 GB18030 私有区冷僻字（AEBA / AFD2）未含**，覆盖率 99.998%。

- 码表：`scripts/gbk_table.json`（21,791 条 `"CEE4":"武"`），由 `scripts/TaikouTextDecoder.gd` 加载。
- 解码器接口：`TaikouTextDecoder.decode_bytes(raw_bytes: PackedByteArray) -> String`。

### 3.4 BSDATA 武将记录（已 100% 破解）

`BSDATA1.TR2` / `BSDATA2.TR2` 内容**完全相同**（副本），大小 **41,300 B = 700 条 × 59 字节/条**。

**记录内字节布局（中文汉化版 59 字节）**：

| 偏移 | 长度 | 字段 | 说明 |
|---|---|---|---|
| 0–3 | 4B | 姓（GBK） | 多为 2 汉字（如 `织田`），不足则后接分隔 |
| 4–6 | 3B | `00 00 00` 分隔 | **姓与名之间夹 3 个零字节** |
| 7–12 | 6B | 名（GBK） | 如 `信长`；遇 0 终止 |
| 13 | 1B | `00` 终止符 | |
| 16 | 1B | **脸谱编号** | 织田信长=13、木下藤吉郎=16、前田庆次=27 |
| 20 | 1B | **相性** | |
| 22–26 | 5B | **5 项能力** | 统率/武力/内政/外交/魅力（值=字节本身，0–100） |
| 27–29 | 3B | **10 项技能** | 见下方解码规则 |
| 43 | 1B | **年龄编码** | 游戏内部值（非常数岁数；常见成人=17） |
| 45 | 1B | 体力(最大) | |
| 46 | 1B | 体力(当前) | |
| 47 | 1B | **野心** | 常见默认 50 |
| 48 | 1B | **亲密** | |
| 49 | 1B | **居城编号** | 织田一门=66（0x42 清洲） |
| 50–51 | 2B | **信赖** | uint16 LE |
| 52 | 1B | **俸禄** | |
| 56 | 1B | **忠诚** | 常见 47(0x2F) |
| 57 | 1B | **身份编号** | 信长=7→大名；其余家臣序列 |
| 58 | 1B | **寿命** | 信长=112 |

**技能 10 项解码（偏移 27/28/29）**：
- 取 5 个半字节：`b27_hi, b27_lo, b28_hi, b28_lo, b29_lo`。
- 每个半字节 `v` 给出**一对技能**等级：`甲 = v & 3`（前一技能），`乙 = v >> 2`（后一技能）。
- 技能顺序：`[算用, 剑术, 口才, 马术, 洋枪, 筑城, 忍术, 军学, 礼法, 茶道]`。
- 校验锚点：前田庆次文档值 `CC 15 0A` → 算用0/剑术3/口才0/马术3/洋枪1/筑城0/忍术1/军学1/礼法2/茶道2（逐位吻合）。

**名字提取（Python 参考）**：
```python
def name_of(rec_bytes):
    return gbk(rec_bytes[0:4]) + gbk(rec_bytes[7:13])   # gbk 遇 0 终止
```

**数值校验**：700 条能力值**全部 0–100 无越界**；#13 织田信长 统96/武85/内92/交99/魅90；#16 木下藤吉郎 武42（史实低武力）/魅97；#27 前田庆次 武98/内12。

### 3.5 GRP 画面格式（已验证：RGB565 直接像素）

KOEI 的 `.GRP` 文件是**直接像素画面**（非索引+调色板），用于标题/版权/logo 等全屏画面。

**文件头结构（6 字节）**：
```
0x00  04 00          → 格式标记 / 版本
0x02  XX XX (LE)     → 2 × 实际宽度   (如 0x0280=640 → 宽=320)
0x04  YY YY (LE)     → 2 × 实际高度   (如 0x0190=400 → 高=200)
```

**像素区**：从偏移 6 开始，**RGB565（小端）** 像素，每像素 2 字节：
- R = `(pixel >> 11) & 0x1f` → `* 255 // 31`
- G = `(pixel >> 5) & 0x3f` → `* 255 // 63`
- B = `pixel & 0x1f`         → `* 255 // 31`

**已验证文件**（三者均为 **320×200**，128,006 B = 6B 头 + 128,000B 像素）：

| 文件 | 内容 | 渲染确认 |
|---|---|---|
| `KOEILOGO.GRP` | KOEI logo（白底黑字 "KOEI" + 蓝点装饰） | ✅ 清晰 |
| `ACERTWP.GRP` | 认证/版权页（黄底蓝框 "第3弹" 等） | ✅ 清晰 |
| `PRESS.GRP` | 按键提示页（黑底彩色文字） | ✅ 清晰 |

### 3.6 CHIP / CHAR 像素格式（2026-08-23 第三轮突破）

**关键纠偏**：CHIP/CHAR 并非统一的「8bpp 索引 + 外部 256 色调色板」。实测至少存在 **三种** 编码：

| 文件 | 解压大小 | 格式 | 布局 | 验证 |
|---|---|---|---|---|
| `MAPCHIP.LZW` | 45,056 B | **裸 RGB565**（无头） | 256×88 px（= 88 块 16×16 地图块） | ✅ 地形块清晰 |
| `TOWNCHIP.LZW` | 43,648 B | **KOEI 4bpp 位平面交错** | 16×16 瓦片 × **341** 块 | ✅ 建筑/町块清晰 |
| `HBCHAR.LZW` | 49,152 B | **EGA 4 平面位图** | 16×16 精灵 × **384** 块（64 脸谱×6 帧） | ✅ 红蓝武士精灵清晰 |
| `FACE.LZW` | 1,093,638 B（压缩） | **NPK016 肖像** + 元数据表 | 64×80 × 134+ 张；解压头 1621B | ✅ 战斗肖像已接入 |
| `TOWNCHAR.LZW` | 27,136 B | KOEI 4bpp（同 TOWNCHIP） | 16×16 × 212 块 | 🟡 结构对，调色板待调 |
| `HJCHAR` / `HKCHAR` | — | EGA 4 平面（同 HBCHAR） | 16×16 | 🟡 待目视确认 |

### 3.7 IDX 图形容器（GRPDATA / HGRP）— ✅ 已破解（2026-08-24）

- 文件 `GRPDATA.LZW`（LS11 解压 40322B，**139 条目**）、`HGRP.LZW`（解压 37912B，**126 条目**）。
- **容器头**：`"IDX"`(3B) + `u8` 条目数（GRPDATA=`0x8b`=139 / HGRP=`0x7e`=126）+ `u32 LE` 偏移表（条目数个，单调递增，遇 0 或非递增终止）。
- **每条目**：`u16 LE type`(=3 → 3bpp/8 色) + `u16 LE width` + `u16 LE height` + **3bpp 索引像素（MSB-first，每 3 bit = 调色板索引 0..7）**。
- **验证（非图片）**：139/139、126/126 条目字节充足（avail ≥ `ceil(w*h*3/8)`）；ASCII 灰度预览显示真实字形/图标轮廓（非噪声）。解码器 `scripts/_decode_grp_container.py`，验证 `scripts/_verify_idx.py`。
- **真实调色板**：尚未获得（3bpp 仅 8 色，真值需代码驱动发现）。
- **纠正旧假设**：`GRPDATA2.LZW` / `KOSENGRP.LZW` 经 LS11 解压为 `0xFF` 垃圾，**不是** IDX 容器。

**KOEI 4bpp 位平面交错**（TOWNCHIP，与 kaodata `to_4bpp_indexes` 一致）：
- 每 16×16 瓦片占 **128 字节**（4 个位平面 × 32 字节，每字节 8 像素）。
- 每 4 字节为一组，MSB-first 逐位展开为 8 个像素索引（0–15）。

**EGA 4 平面位图**（HBCHAR，IBM PC EGA 标准布局）：
- 每 16×16 精灵占 **128 字节**（4 平面 × 32 字节）。
- 像素索引 = plane0_bit | (plane1_bit<<1) | (plane2_bit<<2) | (plane3_bit<<3)。

**FACE 肖像 NPK**（2026-08-23 第六轮）：
- `FACE.LZW` LS11 解压后 1621B：`uint16 64×80` 头 + 12B×脸谱索引。
- 每条脸谱在 12B 记录的 **3 个 uint32 槽** 之一存 `uint32(offset | size<<16)`（按序尝试首个有效 NPK 块）；仅 ~35/134 条有像素，高编号脸谱回退 HBCHAR。
- `TaikouImage.unpack_npk()` + `face8` 调色板 → 64×80 肖像；`GameAssets.get_face_texture()`。

**调色板**：
- EGA 精灵用 **16 色 EGA 标准盘**（`chip_palettes.json` → `ega16`），结构正确。
- TOWNCHIP 用 **KOEI 4bpp 默认 16 色**（`koei4bpp`），结构正确但色相偏霓虹（真盘可能在 exe 运行时设置，待精调）。
- ⚠️ 标准 VGA 256 色 **不适用**于 TOWNCHIP/HBCHAR（旧假设已证伪）。

### 3.7 TOWNPOS 城镇坐标（2026-08-23 第四轮破解）

`TOWNPOS.DAT`：**153 行 × 16 字节/行**，有效城池 **92 座**（其余行无合法坐标）。

**格式**（纠偏：不是 uint16 LE，而是连续 **uint8 (x,y)** 对）：
- 每行 16 字节 = 最多 8 组 `(uint8 x, uint8 y)`。
- 有效坐标：`0 < x < 180` 且 `0 < y < 88`（对应 MAPCHIP 256×88 像素地图）。
- `x ≥ 180` 的字节为链接/标记，跳过；多组有效坐标时取 **y 最小**（最北）的点作为主坐标。
- 行号 = **居城代码**（单字节 `0x00`–`0xC7`，与 bsdata `home_city` 一致）。例：#0x42(66)=清洲 `(9,15)`；#0x47(71)=那古野 `(47,29)`。

**城名表**（2026-08-23 第五轮）：
- `scripts/castle_names.json`：200 座居城真名（社区代码表 jcku / 星虎论坛，非 SNDATA 明文）。
- `scripts/_build_castle_names.py` 生成；`_extract_towns.py` 合并 TOWNPOS + 城名表。

**交付物**：
- `scripts/towns.json`（92 城：id/code_hex/name/map_x/map_y/x/y/enemy/desc）
- `scripts/_extract_towns.py`（可重跑生成）
- `Database.get_towns()` / `get_town_by_id()` / `get_castle_name()`
- 剧情锚点（居城代码）：`0x42` 清洲(起点) / `0x48` 岐阜·稻叶山(saito) / `0x60` 小谷(asai) / `0x70` 二条(nobunaga，朽木谷坐标代用；`0x6F` 二条无 TOWNPOS)

**调色板精调**：`chip_palettes.json` → `koei4bpp` 换为 san4 大地色系，TOWNCHIP 建筑色已目视确认改善。

**验证**：`scripts/_verify_chip.gd` → `STAGE_CHIP_OK`。
**探测工具**：`_graph_probe.py --mode mapchip|townchip|ega`。

- `END.GRP`（733,380 B）：**非标准 GRP**——头部不同、像素区不匹配任何标准分辨率。可能是多帧打包或 RLE 压缩变体。待逆向。
- `SMODE.GRP`（133,537 B）：同上，不同子格式。

**工具**：`scripts/_graph_probe.py --mode grp <FILE> --out out.png` 可直接渲染已验证的 GRP。

> 直接产物：`_probe/koeilogo_grp.png` / `acertwp_grp.png` / `press_grp.png`（已渲染验证）。

> 直接产物：`scripts/bsdata.json`（700 人，结构见 §5）。**不要再手写解析 BSDATA 的 GDScript 去跑**——见 §6 死路警告 #4。

---

## 4. 已构建的引擎模块（`scripts/` 清单与职责）

### 4.1 数据与解码层

| 文件 | 职责 | 状态 |
|---|---|---|
| `TaikouLZW.gd` | LS11 解压（§3.1） | ✅ |
| `TaikouMessage.gd` | MSGX 解析（§3.2） | ✅ |
| `TaikouTextDecoder.gd` | GBK 解码，加载 `gbk_table.json` | ✅ |
| `TaikouImage.gd` | GRP/CHIP/CHAR 图像解码 | ✅ |
| `TaikouKos.gd` | ~~KOS XOR 0xAE 解密 + data 容器~~ **已废**：KOS=音效(见 REVERSE §6.1)，"data 容器"是 RIFF 的 data 块误读 | ❌ |
| `TaikouParser.gd` | SNDATA 头、KOS 解密；`parse_bsdata` 为桩 | ⚠️ |
| `DataLoader.gd` | 从 `DATA_ROOT` 读原版文件 | ⚠️ 换机改 `DATA_ROOT` |
| `MessageIndex.gd` | MESSAGE*.LZW 全局惰性索引 | ✅ |
| `ScenarioData.gd` | SNDATA 剧本标志 `get_scenario`/`flag_at` | ✅ |
| `KosFlagMap.gd` | SNDATA 标志 → 语义名映射 | 🟡 部分 |
| `Database.gd` | 武将/城镇/敌人/卡组；`get_enemy_def` 为 **static** | ✅ |
| `bsdata.json` / `_extract_bsdata.py` | 700 武将离线产物 | ✅ |
| `towns.json` / `castle_names.json` | 92 城坐标 + 200 居城名 | ✅ |
| `kos_message_map.json` | ~~39 KOS 中 37 条 MESSAGE 映射~~ **已废**：KOS 无台词，台词在 MESSAGE*.LZW | ❌ |
| `chip_palettes.json` | EGA16 / koei4bpp 调色板 | 🟡 近似 |

### 4.2 游戏系统层

| 文件 | 职责 | 状态 |
|---|---|---|
| `GameState.gd` | autoload：玩家、天数、居城、剧情、外交、行军缓存 | ✅ |
| `GameSave.gd` | 3 槽位 JSON 存档（`user://taikou2_save_1~3.json`） | ✅ |
| `SaveLoadMenu.gd` | 读档排序、保存覆盖确认、删除确认 | ✅ |
| `StoryProgress.gd` | Boss 击败标记、通关 `story_cleared` | ✅ |
| `MapTravel.gd` | 行军 1–7 天；每天 2 贯 + 5 体力 | ✅ |
| `Diplomacy.gd` | 送礼/宴请；`spread_relation` 最近 5 城 +1 友好 | ✅ |
| `KosVm.gd` | ~~KOS 运行时 VM~~ **已废**：KOS=音效，不存在事件 VM（REVERSE §6.1） | ❌ |
| `KosEvents.gd` | 城内随机事件 + 宴后/深谈 KOS 台词 | ✅ |
| `RetainerData.gd` | 家臣数据与招募 | 🟡 基础 |
| `TaikouAudio.gd` | 原版音频读取 | 🟡 基础 |
| `BattleFlow.gd` | 战斗入口与流程编排 | ✅ |
| `EndCinematic.gd` / `SmodeHotspots.gd` | 通关/SMODE 探测 | 🟡 探测阶段 |

### 4.3 场景与 UI 控制器

| 文件 | 职责 | 状态 |
|---|---|---|
| `Main.gd` | 根场景切换；HUD 含槽位编号 | ✅ |
| `MainMenu.gd` | 继续/新游戏/槽位预览/新游戏自动初始存档 | ✅ |
| `WorldMap.gd` | MAPCHIP 地图；◎ 当前位置；行军预览；回居城 | ✅ |
| `Town.gd` | 城内：修行/宿泊/漫步/外交/宴后事件 | ✅ |
| `TownWork.gd` | 城下打工（筑城/算用/军学 → 对应 KOS） | ✅ |
| `BattlePrep.gd` | 战前准备；槽位与自动存档提示 | ✅ |
| `Battle.gd` | 卡片决斗；距离/姿态/马术；Boss 胜自动存档 | ✅ |
| `GameAssets.gd` | 运行时图形缓存 | ✅ |
| `Character.gd` / `Card.gd` | 角色与卡牌模型 | ✅ |

### 4.4 工具与验证

| 文件 | 职责 | 状态 |
|---|---|---|
| `_graph_probe.py` | LS11/GRP/tile 探测渲染 | ✅ |
| `_extract_towns.py` / `_build_castle_names.py` | 城镇表生成 | ✅ |
| `_verify_*.gd` | **52** 个 headless 验证脚本（见 §1.5） | ✅ |

---

## 5. 数据产物（`scripts/` 下）

- **`bsdata.json`**（265 KB）：顶级键 `record_size=59, count=700, fields, status_note, characters[]`。
  每个 `characters[i]`：`id, name, forces{统率,武力,内政,外交,魅力}, skills{10项}, face, compat, stamina, stamina_max, home_city, status, status_name, raw(59字节hex)`。
- **`gbk_table.json`**（327 KB）：顶级键 `encoding, note, entries{ "CEE4":"武", … }`。
- **`koei_codes.json`**（163 KB）：⚠️ **已废弃/死路产物**，请勿使用（详见 §6 #1）。保留仅供对照。

---

## 6. ⚠️ 死路警告（务必先看，避免重复浪费数轮）

1. **`koei_codes.json` 是死路**。它源于早期「KOEI 私有置换码」错误假设。真实文本是 **GBK**，用 `gbk_table.json`。看到 KOEI 字样一律当成过时结论。

2. **`rmKOEI.bin` 是卸载程序 DLL，不是字体渲染器**（2026-08-24 修正）。它实为 KOEI **卸载程序 DLL**（`textsub.cpp`, 1996, Ashihara）——含明文 GBK 卸载字符串（`光荣卸载程序`/`无法删除卸载程序`/`请重新启动电脑` 等）+ 文件操作 API（`DeleteFileA`/`RemoveDirectoryA`/`GetWindowsDirectoryA`）。**无任何 GDI/字体 API**。对话文本(MESSAGE)与武将名(BSDATA)都是**明文 GBK**，全部直解。真正的字体系统在主 EXE 内（`ENGINE_SPEC.md` §7）。

3. **`TAIK2W95.exe` 已脱壳**（Unicorn 静态，OEP `0x4f44b0`，dump `_unpacked_mem.bin`）。MESSAGE/BSDATA 文本是 GBK 直解。但 **SNDATA 记录中的字段用的是 EXE 内部码**（GBK→字形索引→字体位图），需逆向字体加载器 `0x424120`（见 `ENGINE_SPEC.md` §7），不是简单查表。

4. **`TaikouParser.parse_bsdata()` 是个错误占位桩**（它假设 100 字节/条记录，实际 59 字节，且没解任何字段）。**真实的 BSDATA 解码是 Python 离线脚本完成的**，产物即 `bsdata.json`，由 `Database.load_characters()` 直接加载。**不要再改 `parse_bsdata` 去跑**——要么复用 `bsdata.json`，要么重写 Python 离线提取器（推荐，因为可重跑、可校验）。

5. **搜武将全名（如「织田信长」）会搜不到**——因为姓和名之间夹了 `00 00 00` 三个零字节，字节不连续。要搜就分开搜「织田」「信长」，或按记录逐条用 GBK 解码。

6. **KOS 音效**：`byte[0]=0xAE` + 其余 XOR `0xAE` = RIFF/WAVE（mono 22050Hz 8-bit PCM），已 39/39 解码到 `scripts/kos_wav/`。**KOS 无台词**：台词来自 `MESSAGE*.LZW`（GBK，已破解）；旧 `kos_message_map.json` 系误读 PCM，已废。

7. **CHIP/CHAR 不是统一的 8bpp 索引格式**——实测 MAPCHIP=裸 RGB565、TOWNCHIP=KOEI 4bpp 位平面交错、HBCHAR=EGA 4 平面位图。标准 VGA 256 色调色板不适用。当前 `chip_palettes.json` 为近似盘，结构已验证、色相待从 exe 精调。

---

## 7. 当前可玩 Demo 已接入功能

### 7.1 主流程

- **主菜单**：3 存档槽；继续游戏；新游戏选槽 + 覆盖确认；槽位预览可点击加载；新游戏后**自动写初始存档**。
- **世界地图**：92 城 MAPCHIP；◎ 标记当前位置；悬停行军路线；行军消耗预览（天数 1–7，每天 2 贯 + 5 体力）；**回居城**按钮。
- **城内**：十技能修行（5 体力/次）；宿泊回满体力；漫步随机 KOS 事件；城下打工 3 种；外交送礼/宴请。
- **战斗**：BSDATA 技能驱动卡组；距离/姿态/马术先手；战败可再战或休养 1 天；Boss 击败**自动存档**。
- **通关**：击败信长 → 通关画面 → 主菜单/返回地图。

### 7.2 剧情锚点（`towns.json` / `StoryProgress.gd`）

| 居城 code | 城名 | enemy key | 说明 |
|---|---|---|---|
| `0x42` | 清洲 | — | 起点/居城 |
| `0x48` | 岐阜 | `saito` | 斋藤龙兴 #335 |
| `0x60` | 小谷 | `asai` | 浅井长政 #384 |
| `0x70` | 二条 | `nobunaga` | 织田信长 #13（final） |

### 7.3 外交与 KOS 事件

- 宴请设 flag **Lv2**（`Diplomacy.FEAST_FLAG_DEPTH`）；宴后/深谈事件**播放 `KAKEI.KOS` 等音效**（KOS=SFX，非台词；台词来自 MESSAGE*.LZW）。
- `KosVm.story_flag_value` = `max(SNDATA 基准, 运行时数值)`；`dialogue_path_index` 为 flag 数值之和。
- 宴请后 `spread_relation`：按地图距离取**最近 5 城**友好度 +1（上限 4）。

### 7.4 存档字段（`GameSave.gd`）

`user://taikou2_save_{1,2,3}.json`，含：`saved_at_unix`、`story_cleared`、Boss 进度、家臣数、`last_travel_days/money/stamina` 等 `GameState` 快照。

### 7.5 数据接线事实（仍有效）

- 玩家 = **木下藤吉郎**（统84/武42/内89/交94/魅97，脸谱16）。
- `Database.build_deck()` 按十技能生成卡；Lv 每级威+5，Lv3 气耗-1。
- `Database.get_enemy_def()` 必须是 **`static func`**（曾引发 Parser Error，已修）。

---

## 8. 完美复刻对照表（接手者路线图）

图例：**✅ 已有** · **🟡 部分/原型** · **❌ 未做**

### 8.1 数据逆向层

| 模块 | 状态 | 说明 |
|---|---|---|
| LS11 解压（33×.LZW） | ✅ | `TaikouLZW.gd`，100% 长度吻合 |
| MESSAGE / GBK 文本 | ✅ | MSGX + `gbk_table.json`，99.998% 覆盖 |
| BSDATA 700 武将 59B | ✅ | `bsdata.json` + `_extract_bsdata.py` |
| GRP 标准 320×200 RGB565 | ✅ | KOEILOGO/ACERTWP/PRESS |
| MAPCHIP / TOWNCHIP / HBCHAR | ✅ | 三种像素格式已破 |
| FACE 肖像 NPK | 🟡 | ~35/134 有像素，其余回退 HBCHAR |
| TOWNPOS 92 城 | ✅ | `towns.json` |
| KOS XOR 0xAE 解密 | ✅ | `TaikouKos.gd` |
| KOS 音效解码 | ✅ | 39 个 `.KOS` = RIFF/WAVE（XOR `0xAE`），`scripts/kos_wav/*.wav` |
| KOS→MESSAGE 自动映射 | 🟡 | 37/39；靠扫描非完整语义 |
| SNDATA 头部/标志区 | 🟡 | 可读；**事件语义未破** |
| END.GRP / SMODE.GRP | ❌ | 非标准 GRP，待逆向 |
| 原版音乐/音效全接入 | 🟡 | `TaikouAudio.gd` 基础读取 |
| rmKOEI | ✅ | **卸载程序 DLL**（textsub.cpp, 1996），非字体渲染器（旧定位已证伪，见 `ENGINE_SPEC.md` §7.1）|

### 8.2 玩法系统层

| 系统 | 状态 | 说明 |
|---|---|---|
| 主菜单 + 3 槽存档 | ✅ | `GameSave` / `MainMenu` / `SaveLoadMenu` |
| 世界地图行军 | 🟡 | 有消耗/预览；无原版势力占领逻辑 |
| 城内：修行/宿泊/漫步 | 🟡 | 十技能简化版 |
| 城内：打工 | 🟡 | 3 种 KOS 台词 |
| 外交：送礼/宴请 | 🟡 | 友好度 + 传播；无完整势力 AI |
| 卡片单挑 | 🟡 | 距离/姿态/马术；非原版阵型全规则 |
| 家臣系统 | 🟡 | 招募基础；无俸禄/忠诚循环 |
| 忍者/城内任务 | ❌ | |
| 合战（大军团战） | ❌ | **最大缺口** |
| 知行/内政 | ❌ | |
| 多结局/全剧本 | ❌ | 仅 Demo 单线三 Boss |
| UI/音画 1:1 | ❌ | 原型 UI + 部分原版素材 |

### 8.3 推荐实施阶段

> **2026-08-24 策略调整**：若感觉「问题很多」，建议 **暂停堆 Godot 玩法**，转做 `REVERSE_ENGINEERING.md` 阶段 0–2（数据文档 + EXE 脱壳 + EXE 引擎规范（ENGINE_SPEC.md）），再回来复刻。见该文档 §0.1。

**阶段 A（优先，约 1–2 周）**

1. **SNDATA 字段语义映射 + EXE 引擎（事件/合战/调色板）（见 `ENGINE_SPEC.md`）**（branch/flag/子例程，禁止靠 uint16 扫描猜）
2. **SNDATA 标志 → 事件语义**（驱动全城内事件，而非硬编码）
3. **全 MESSAGE 自动映射**（39 个 KOS 全覆盖）
4. 经济循环（旅店分级、买卖简化版）

**阶段 B（约 1–2 月）**

- 忍者/城内任务、家臣忠诚俸禄、单挑 AI 深化、势力地图与占领

**阶段 C（数月+）**

- **合战**、知行内政、全结局、UI/音画 1:1、END/SMODE GRP

**北极星验收**：KOS 音效可解码播放（XOR 0xAE → WAV）；SNDATA 驱动事件；单挑+合战；全城内菜单；多结局；UI 难与原版区分。

---

## 9. 社区资源 / 参考（已在探索中使用）

- **`tzengyuxio/kaodata`**（GitHub）：「Early KOEI Games Data Research」，明确支持 **TAIKOH2（太閤立志傳II 1995）**。其机制：`KOEI码 → 线性 order → CNS11643 → Unicode`（见 `dekoei/utils.py` 的 `order_of_koei_tw` / `cns_from_order`）。⚠️ 它是 **KOEI-台湾版**（武=`0x97BC`），我们的是 **KOEI-日本版/GBK**（武=`0xCEE4`），**码→order 的置换不同**，但 order→Unicode 后半段可借鉴。克隆过 `F:/Games/kaodata_tmp`（可作参考，非必须）。
- 中文游戏社区（游民星空 / emu618 / 游侠 / 轩辕春秋）已有 **BSDATA 47 字节原版布局**文档，是偏移锚定的依据。本中文汉化版扩为 59 字节、名字前置，需用已知人物数值做交叉校验。

---

## 10. 一句话交接

> **数据层**（GBK、BSDATA、CHIP/GRP、KOS 解密）大体可用；**Demo**（地图→城内→三 Boss 单挑→通关 + 存档/外交/行军）可玩。  
> **下一优先级：SNDATA 字段语义（Task #23）+ EXE 引擎（事件/合战/调色板）（见 `ENGINE_SPEC.md`）。KOS VM 已证伪（KOS=音效），勿再投入；IDX 容器(GRPDATA/HGRP)、SNDATA 结构已破解**（见 §8.3 阶段 A）。  
> 死路：KOEI 乱码页、rmKOEI 解文本/字体渲染、exe 抽表（已脱壳可用）、统一 8bpp+VGA256、手写 `parse_bsdata`——**别碰**（§6）。

---

## 11. 接手清单（换电脑 / 换 AI 必做）

> **第一步永远是读 `HANDOFF.md`** —— 它是 2026-08-24 的交接总入口，含已破格式、核心阻塞、字体系统、坑、文件索引、优先级。然后读本文件 §11 以下 + `ENGINE_SPEC.md` §7（字体系统）。

### 11.1 环境检查

- [ ] Godot **4.7.1** 已安装（路径见 §1.1；注意 `.exe` 是目录名）
- [ ] 原版数据在 `F:/Games/Taikou2`（或改 `DataLoader.gd` 的 `DATA_ROOT`）
- [ ] Godot 工程在 `F:/Games/Taikou 2`（路径含空格，引号包裹）
- [ ] 首次或新增 `class_name` 后执行 `--headless --import`（§1.2）

### 11.2 冒烟测试（建议顺序）

```powershell
$G = '...\Godot_v4.7.1-stable_win64_console.exe'
$P = 'F:\Games\Taikou 2'
& $G --headless --script "$P\scripts\_verify_wiring.gd" --path $P   # WIRING_OK
& $G --headless --script "$P\scripts\_verify_story.gd" --path $P     # 剧情链
& $G --headless --script "$P\scripts\_verify_save.gd" --path $P      # 存档
```

- [ ] 三项均 exit 0 / 打印 `*_OK`
- [ ] F5 能进主菜单 → 新游戏 → 清洲城内 → 地图行军

### 11.3 开发约定

- **不要** git commit，除非用户（XIN）明确要求。
- **不要**把原版素材提交进仓库；运行时从 `DATA_ROOT` 读取。
- 新功能优先加 `_verify_*.gd`，headless 可回归。
- `--script` 模式无 autoload：验证脚本用 `preload` 或 `KosVm.bind_game_state(gs)`。
- 改 `Database.get_enemy_def` 时保持 **`static func`**。

### 11.4 关键文件速查

| 区域 | 入口文件 |
|---|---|
| 场景根 | `scenes/Main.tscn` → `scripts/Main.gd` |
| 全局状态 | `scripts/GameState.gd`（autoload） |
| 存档 | `scripts/GameSave.gd` |
| 地图行军 | `scripts/WorldMap.gd` + `MapTravel.gd` |
| 城内 | `scripts/Town.gd` + `TownWork.gd` |
| 战斗 | `scripts/Battle.gd` + `BattleFlow.gd` |
| KOS | `scripts/KosVm.gd` + `KosEvents.gd` + `TaikouKos.gd` |
| 外交 | `scripts/Diplomacy.gd` |
| 剧情 | `scripts/StoryProgress.gd` |
| 数据 | `scripts/Database.gd` + `DataLoader.gd` |
| 进度文档 | **本文件** `REPLICATION.md` |

---

## 12. 已知 Bug 与修复记录（勿重蹈）

| 问题 | 修复 |
|---|---|
| `KosVm.gd` 重复定义 `_runtime_flag_set` | 删除重复定义 |
| flag 值 2 无法解锁深分支 | `story_flag_value = maxi(SNDATA, runtime)` |
| headless 读不到 runtime flag | `KosVm.bind_game_state(gs)` |
| `Database.get_enemy_def` Parser Error | 改为 `static func`，内部 `Database.new().build_character_enemy()` |
| `Battle.gd` `tip` 类型推断失败 | `var c: Card = card as Card`；`var tip: String` |
| `MapTravel.gd` `MINI_DAYS` 拼写 | 改为 `MIN_DAYS` |
| 外交传播范围过大 | 改为距离排序取最近 5 城 |

---

## 13. 近期会话变更摘要（2026-08-23 ~ 08-24）

- 存档：3 槽位 JSON；读档按时间排序；保存/删除确认；Boss 胜自动存档；新游戏自动初始存档。
- 地图：行军消耗（天/钱/体力）；路线预览；回居城；状态栏。
- 外交：宴请 flag Lv2；宴后/深谈 KOS；友好度向最近 5 城传播。
- 城内：城下打工 3 种；修行耗体力；宿泊回满。
- 战斗：战前槽位提示；战败再战/休养；通关返回主菜单。
- KOS：`dialogue_path_index`、`story_flag_meets`、阈值门控。
- 验证：新增 `_verify_save*`、`_verify_travel*`、`_verify_feast*`、`_verify_diplo*`、`_verify_town_work` 等。

完整对话记录：`C:\Users\Administrator\.cursor\projects\f-Games-Taikou-2\agent-transcripts\e41fbaf9-e69e-434b-8a1e-50813c25e37a\e41fbaf9-e69e-434b-8a1e-50813c25e37a.jsonl`

