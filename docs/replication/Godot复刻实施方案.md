# 太阁立志传2 — Godot 复刻实施方案

> **本文是「开始写 Godot 代码」的唯一施工图。**
> 与 [`复刻导航.md`](复刻导航.md) 的分工：导航只讲「数据在哪、怎么取」；本文讲「工程怎么搭、代码怎么写、按什么顺序做」。
>
> **前置条件已满足**：非图像结构/数据层 **100% 收口**（2026-09-08，突破日志顶部 = 续253，自测 **180 ref 全 PASS / 0 FAIL**）。
> 也就是说：**复刻不再需要任何逆向工作**——所有格式、字段、公式都是实证结论，照抄即可。
>
> **权威数据源优先级**：`docs/specs/GAME_DATA_SPEC.md` > `docs/specs/BATTLE_SPEC.md` > `docs/specs/SNDATA_SPEC.md` > 本文。
> 本文与 SPEC 冲突时，**以 SPEC 为准并回报**。

---

## 0. 三句话总览

1. **数据全部可从原版文件离线提取**，不需要模拟器、不需要跑原版游戏、不需要再逆向。
2. **玩法公式最完整的是合战**（`BATTLE_SPEC.md §9`，反汇编 + Unicorn 实跑二进制双验证），应作为第一个可玩里程碑。
3. **画面 = 原版素材直用 + 占位图兜底**（高清重建立绘路线已放弃，2026-09-12）。
   

---

## 1. 目标与范围

### 1.1 做什么

| 层 | 内容 | 状态 |
|---|---|---|
| 数据层 | 700 武将 / 200 城 / 49 国 / 189 物品 / 6211 条文本 / 38 张战图 | ✅ 可完整提取 |
| 玩法层 | 月度循环、指令派发、内政、修行、職位晋升、合战、单挑、店铺、外交、事件 | ✅ 结构全破，数值部分可自定 |
| 表现层 | 640×400 画面、菜单、文本渲染（GBK + 外字）、39 音效 | ⚠️ 需用原版素材，不自造 |

### 1.2 不做什么（明确边界）

- ❌ **不写像素/图像格式解码器**（GRP / PK8 / LZW 像素类）——**不需要**：
  世界是 3D 重建的，角色是重画的高清像素 art。原版图块仅作造型参考
  （需要查看时用 `scripts/real_assets.py` 的 `decode_mapchip()` / `decode_hbchar()` 等）。
- ❌ **不追求逐帧还原原版 UI**。先做「可玩」，再做「像」。
- ❌ **不在 Godot 运行时解析 `.TR2`**。一律**离线导出**为 JSON/资源，运行时只读成品。
- ❌ **不碰 `scripts/` 目录结构**（180 个自测依赖非递归扫描，见 `scripts/README.md`）。

### 1.3 法律与素材边界

原版文件位于 `Taikou2 Original/`（149 文件），**仓库不打包**。复刻工程：
- 数据（数值/文本）→ 可入库；
- 图像/音频素材 → **运行时从原版目录读取，或由用户自行放入 `assets/`**，不提交仓库。

---

## 2. 技术栈与工程结构

### 2.1 技术选型

| 项 | 选择 | 理由 |
|---|---|---|
| 引擎 | **Godot 4.7**（现有 `project.godot` 已配好） | 已建壳，`config/features=PackedStringArray("4.7","Forward Plus")` |
| 脚本 | **GDScript**（纯逻辑层可用静态类型 `class_name`） | 快速迭代；数据量大但逻辑不重 |
| 数据格式 | **离线导出 JSON**，运行时 `JSON.parse_string` | 人类可读、可 diff、可校验 |
| 文本编码 | **导出时统一转 UTF-8** | Godot 内部 UTF-8；GBK 只在导出器里出现一次 |
| 渲染 | 2D，`canvas_items` | 原版纯 2D |

### 2.2 分辨率方案 ✅（2026-09-08 已实施）

> 原 `1024×640` 是 1.6× 非整数缩放会拉伸；现在画面直用原版素材，
> 缩放模型也随之改变：**逻辑坐标固定，渲染分辨率随屏幕**。

**现行配置**（已写入 `project.godot`）：

```ini
[display]
window/size/viewport_width=1920          # 默认 1080p，启动时按屏幕改写
window/size/viewport_height=1080
window/stretch/mode="canvas_items"       # 2D 推荐
window/stretch/aspect="expand"           # 16:9 填满（UI 居中，背景延伸）
window/stretch/scale_mode="fractional"

[rendering]
textures/canvas_textures/default_texture_filter=1   # LINEAR + MIPMAPS

[autoload]
DisplayAdapter="*res://src/core/DisplayAdapter.gd"
```

**两条坐标线**：

| 层 | 值 | 谁负责 |
|---|---|---|
| **逻辑坐标**（写 UI/摆精灵用）| 固定 **640×400** | 开发者按此写代码 |
| **渲染分辨率** | 屏幕原生：1080p / 2K / 4K | `DisplayAdapter` 自动检测 |

> 不再需要"整数倍放大"的约束——

> 纹理过滤：像素类素材 → `NEAREST`（保硬边）；大图/背景 → `LINEAR`。

### 2.3 目录结构（建议）

```
<工程根>/
  project.godot
  data/                        ★ 离线导出产物（可入库）
    officers.json              695 真实武将（BSDATA 权威布局）
    castles.json               200 城
    provinces.json             49 国 + 国政治表
    names.json                 名称总表 370 条（国/城町/职种）
    items.json                 189 物品
    skills.json                10 技能名
    ranks.json                 職位名 + 勲功阈值
    battles.json               38 张战图（地形/部署/单位矩阵）
    battle_consts.json         攻击除数表 / 地形系数 / 计略表
    text.json                  6211 条 MSGX 文本（UTF-8）
    gaiji.json                 16 槽外字位图（u16 源码 → 位图）
    consts.json                全局常量（实体偏移、哨兵值…）
  src/
    core/                      ★ 纯逻辑，不依赖 Node
      GameState.gd             全局状态（年/月/玩家/实体池）
      Officer.gd               武将实体（47B 语义映射）
      Castle.gd                城（31B 语义映射）
      Province.gd              国（stride 14）
      Item.gd
      Consts.gd                ★ 全局常量（哨兵值/钳制/规模/攻击除数表）
      DisplayAdapter.gd        ★ autoload：1080p / 2K / 4K 自适应
    render/                    素材加载 / 规格（AssetLoader / AssetSpec）
      asset_loader.gd          素材加载（占位回退）
    battle/                    ★ 合战（纯逻辑 + 3D 表现）
      BattleSim.gd             ★ 结算（移植 battle_formula_ref.py）
      BattleMap.gd             战图/地形/部署
      Tactics.gd               11 计略
    data/
      DataLoader.gd            启动时加载 data/*.json → 内存索引
      TextDB.gd                MSGX 文本查询 + 外字替换
    systems/                   ★ 玩法系统
      TimeSystem.gd            月推进
      CommandSystem.gd         主命 12 / 报告 13 / 会议 16
      DomesticSystem.gd        内政：城数值与主命效果
      TrainingSystem.gd        修行与技能增长
      RankSystem.gd            職位晋升
      DiplomacySystem.gd       外交
      ShopSystem.gd            店铺设施
      EventSystem.gd           事件旗标
    battle/
      BattleSim.gd             ★ 合战结算（移植 battle_formula_ref.py）
      BattleMap.gd             战图/地形/部署
      Tactics.gd               11 计略
    duel/
      DuelSim.gd               单挑卡牌
    ui/
      ...（菜单/对话框/状态面板）
    scenes/
      Main.tscn
      ...
  assets/
    sfx/                       39 个 WAV（从 scripts/_decoded_kos/ 复制）
    gfx/                       AI 素材样本（不入库）
  tools/
    export_for_godot.py        ★ 离线导出器（见 §3.1）
```

**分层铁律**：`src/core` 与 `src/battle` **不引用任何 Node/UI**，保证可用 `gdscript` 单元测试与无头批量跑（压测 1000 场合战验证平衡）。

---

## 3. 数据层

### 3.1 数据管线：离线导出（唯一正解）

```
Taikou2 Original/*.TR2|.DAT|.LZW
        │
        │  tools/export_for_godot.py   （Python，只在开发机跑一次）
        ▼
    data/*.json  （UTF-8，人类可读）
        │
        │  Godot 启动时 JSON.parse_string
        ▼
   内存索引（Dictionary / Array）
```

**为什么不在 Godot 里直读原版文件**：
- GBK 解码、XOR 流、LS11 解压都要额外实现，Godot 侧没有现成能力；
- 离线导出可加断言、可重跑、可 diff，出问题一眼看出；
- 原版文件不入库，不能假设运行时存在。

> 导出器已提供：**`scripts/export_for_godot.py`**（见 §3.9，含自检）。

### 3.2 🔴 最重要的坑：`bsdata.json` 的字段定义已证伪

`scripts/bsdata.json` 是早期产物，其 `fields` 字符串基于**十进制猜测**，已被 **续200 推翻**。

| `bsdata.json` 旧记 | 实测证伪 | 正确（续200） |
|---|---|---|
| `16 = face` 头像 | 该 2B **恒等于记录号** 700/700 | `0x10` = **武将 ID** |
| `50–51 = trust` 信赖 | 值域 0..65535，织田信长 = 0xffff | `0x32–0x33` = **功勲 merit** |
| `56 = loyalty` 忠诚 | 值域 [15,175]，6 条 >100 | 忠诚真在 **`0x35`** |
| `57 = status` | 38/690 条 > 7 | 須 **`& 7`** |
| `58 = lifespan` 寿命 | 低 4 位恒 0、仅 8 取值 | `0x3a>>4` = **主角槽+武将档** |

**验证实录**（`BSDATA1.TR2` 记录 0，hex 前 59B）：

```
c1d6 00000000 00 cda8caa40000 00
ffff 0000 ffff f42b 44 36 48 2d 34 01 44 01
ff 47 00 00 00 00 00 00 00 1e 80 ffff ffff 11
58 58 28 32 0d 47 1027 64 4a ffff 2f 05 40
```

- `0x00..0x06` = `c1 d6` = **林**（姓），`0x07..0x0d` = `cd a8 ca a4` = **通胜**（名）
- `0x16..0x1a` = `44 36 48 2d 34` = 68/54/72/45/52 = 统率/武力/内政/外交/魅力 ✅
- `0x2c`/`0x2d` = `58 58` = 88/88 = 体力上限/现在体力（**旧记 `stamina@46=40` 实为 `0x2e` 体力消耗**）
- `0x35` = `4a` = **74 忠诚**（旧记取 `0x38`=47，错）
- `0x38..0x39` = `2f 05` → `職位 = 0x05 & 7 = 5` = **组头** ✅

> **行动项**：**不要**直接 `json.load(bsdata.json)` 当权威。用 `scripts/export_for_godot.py` 重新导出，或至少按 §3.3 布局重解析。

### 3.3 武将数据 `BSDATA1/2.TR2`（700 × 59 B）✅ 权威布局

文件 = 41300 B = **700 × 59** 精确整除，**无压缩无加密无 magic**，直接按 59 字节切分。

| 偏移 | 长度 | 字段 | 说明 |
|---|---|---|---|
| `0x00–0x06` | 7B | `surname` | 姓，GBK 定长槽 NUL 结尾 |
| `0x07–0x0d` | 7B | `given` | 名，GBK 定长槽 |
| `0x0e` | 2B | 🔒 哨兵 | 恒 `0xFFFF`，无语义 |
| `0x10` | 2B | `bushou_id` | **武将 ID**（恒 == 记录号） |
| `0x12` | 2B | 🔒 哨兵 | 恒 `0xFFFF` |
| `0x14` | 2B | `compat` | 相性字 → 实体 `+0x08`（bit 11–14） |
| `0x16–0x1a` | 5B | `forces` | **五维** 统率/武力/内政/外交/魅力 |
| `0x1b–0x1d` | 3B | `skills` | **10 技能 × 2 bit** |
| `0x1e–0x21` | 4B | 🔒 占位 | 全常量；城属性由城派生，BSDATA 不存 |
| `0x22` | 1B | 有效标记 | init = 1 |
| `0x27` | 1B | `birth_year` | **生年 − 1490**（全表 1493..1710） |
| `0x28` | 1B | 保留 | 高3静态 / 低5剧本相关 |
| `0x29–0x2a` | 2B | `father_id` | 父/养父武将索引，`0xFFFF` = 无 |
| `0x2b` | 1B | `home_idx` | 出身地索引 → 表 `0x50bf48` → 国 0..48 |
| `0x2c` | 1B | `stamina_max` | 体力上限（钳 100） |
| `0x2d` | 1B | `stamina` | 体力现值（初值 ≡ `0x2c`） |
| `0x2e` | 1B | `stamina_drain` | 体力消耗（钳 100） |
| `0x2f` | 1B | `ambition` | 野心（**全表恒 50**） |
| `0x30` | 1B | `province` | 国 0–48，**255 = 无** |
| `0x31` | 1B | `city` | 城 0–199，**255 = 浪人** |
| `0x32–0x33` | 2B | `merit` | 功勲，`0xffff` = 满值哨兵 |
| `0x34` | 1B | `salary` | 俸禄/石高（信长 250、藤吉郎 1） |
| `0x35` | 1B | `loyalty` | 忠诚，值域恰 **[0,100]** |
| `0x36–0x37` | 2B | `lord` | 主君武将 ID，**`0xffff` = 浪人** |
| `0x38–0x39` | 2B | `status_word` | **職位 = `byte[0x39] & 7`** |
| `0x3a` | 1B | `archetype` | **高 4 位** = 主角槽+武将档 |

**技能位解包**（10 技能 × 2 bit，0..3 级）：

```python
level_k = (byte[0x1b + k//4] >> ((k & 3) * 2)) & 3     # k = 0..9
顺序 = 口才, 马术, 算术, 剑术, 忍术, 兵法, 洋枪, 筑城, 礼法, 茶道
```

> 🔴 **技能名纠偏**：正确是 **算术 / 兵法**，不是「算用 / 军学」（后者在镜像里 0 命中）。
> `scripts/bsdata.json` 里写的正是错误的「算用/军学」，导出时必须纠正。

**職位（3 bit）**：`職位 = byte[0x39] & 7`
`0=无, 1=足轻组头, 2=足轻工头, 3=足轻头, 4=家老, 5=组头, 6=家臣, 7=大名`
🔴 **必须 `& 7`**：packer 只占 word 的 bits 8–10，原始字节有 **38/690 条 > 7**，不掩码必错。

**archetype（主角槽）**：`byte[0x3a] >> 4`，取值域恰 `{0,1,2,4,5,6,7,8}`

| 值 | 条数 | 含义 |
|---|---|---|
| 0 / 1 / 2 / 7 | 各 1 | 木下藤吉郎 / 明智光秀 / 柴田胜家 / 织田信长（可选主角） |
| 8 | 2 | 上杉谦信 / 本愿寺显如（可选主角） |
| 4 / 5 / 6 | 441 / 212 / 36 | 一般武将三档 |

**记录构成**：700 = **695 真实武将 + 5 条 `姓0NNN` 占位槽**（尾部 695..699，五维全 0）。导出时建议标记 `is_placeholder=true` 并排除出可选池。

**参考样本**（用于导出自检）：

```
#13 织田信长: 五维{统96 武85 内92 外99 魅90}
              技能{马术3 洋枪3 茶道3 筑城2 兵法2 算术1 剑术1 口才1}
              職位=大名 野心50 忠诚47 生年1534 国=13 城=66 功勲=65535(满) 俸禄250 archetype=7
#16 木下藤吉郎: 五维{统84 武42 内89 外94 魅97} 技能{口才3 算术2 筑城2 兵法1}
              職位=足轻组头 体力80/100 俸禄1 功勲100 archetype=0
```

**导出实测（2026-09-08 跑通 `data/officers.json`）** —— 建议直接作为 Godot 侧回归基准：

| # | 姓名 | 五维（统/武/内/外/魅） | 職位 | 功勲 | 俸禄 | 主角槽 |
|---|---|---|---|---|---|---|
| 1 | 柴田胜家 | 87/90/67/31/61 | 家老 | 5200 | 50 | 2 |
| 13 | 织田信长 | **96/85/92/99/90** | **大名** | 65535 | 250 | 7 |
| 16 | 木下藤吉郎 | **84/42/89/94/97** | **足轻组头** | 100 | 1 | 0 |
| 257 | 上杉谦信 | 98/100/64/68/99 | 大名 | 65535 | 250 | 8 |
| 364 | 明智光秀 | 87/86/91/88/71 | 足轻工头 | 500 | 10 | 1 |
| 423 | 本愿寺显如 | 86/31/51/89/90 | 大名 | 65535 | 250 | 8 |

- **可选主角 = 6 人**（`is_selectable`），与 §1.4 枚举 `{0,1,2,7,8}` 一致。
- **大名共 45 名**（職位 = 7）；织田信长 国=13（尾张）/ 城=66。
- **外字姓解码正确**：#182 垪和氏续（国=6 北条家臣群）、#557 長宗我部元亲（国=35 土佐，職位=大名）、#568 香宗我部亲泰、#581 長宗我部信亲、#583 長宗我部盛亲 —— 与 §1.6 史实锚点逐条吻合。
  ⚠️ #430 香川元景 也含「香」，但属**正常 GBK 字**、非外字，勿误判。

> 这三条（主角 6 人 / 大名 45 / 外字 5 条）建议写进 Godot 侧的数据校验断言。

### 3.4 运行期实体 47 B（Godot 里直接建这个结构）

原版运行期实体池 = **370 槽 × 47 B @ `0x519868`**。Godot 不必复刻字节布局，但**语义映射必须一致**：

| 实体偏移 | 大小 | 语义 | BSDATA 来源 |
|---|---|---|---|
| `+0x02` | W | 武将 ID | `0x10` |
| `+0x08` | W | 相性（**bit 11–14**） | `0x14` |
| `+0x0a..+0x0e` | 5B | 五维 | `0x16..0x1a` |
| `+0x0f..+0x11` | 3B | 技能 10×2bit | `0x1b..0x1d` |
| `+0x1b` | B | 生年 | `0x27` |
| `+0x1d` | W | 父 ID | `0x29` |
| `+0x1f` | B | 出身地 | `0x2b` |
| `+0x20` / `+0x21` | B/B | 体力上限 / 现值 | `0x2c` / `0x2d` |
| `+0x22` | B | 体力消耗 | `0x2e` |
| `+0x23` | B | 野心 | `0x2f` |
| `+0x24` | B | 国 | `0x30` |
| `+0x25` | B | 在城 | `0x31` |
| `+0x26` | W | 功勲 | `0x32` |
| `+0x28` | B | 俸禄 | `0x34` |
| `+0x29` | B | 忠诚 | `0x35` |
| `+0x2a` | W | 主君（`0xffff`=浪人） | `0x36` |
| `+0x2c` | W | 状态字（職位 = `>>8 & 7`） | `0x38` |

> **Godot 建议**：用 `class_name Officer extends Resource`，字段用有意义的名字（不要 `f0x2c`），
> 但在导出器里保留 `raw_offset` 注释，便于日后回溯。

### 3.5 城 / 国 / 名称数据

| 数据 | 来源 | 规模 | 产物 |
|---|---|---|---|
| 城表 | SNDATA S11 流（运行期 `0x51eb88`，31B） | **200** 条 | `sndata_sections.json` → `castle` 数组 |
| 城名 | `sndata_sections.json` → `castle_names`（键 = 城 id 字符串） | 200 | 直接取 |
| 城-町对应 | `castle_town.json` | — | 直接取 |
| 国名（49） | `name_table.json` → `province_names` | 49 | 直接取 |
| 国政治表 | 运行期 `0x5179b8`，**stride 14 × 49** | 49 | `province_politics.json` |
| 名称总表 | EXE `0x506ca8`，**stride 9 × 370** | 370 | `name_table.json` |

**名称总表四块**（`name_table.json` 的 `layout` 字段）：
- `0..48` 49 国
- `49..87` 39 额外地名（flag 前缀，语义未定）
- `88..291` 204 城·町（**城 id c → index 88+c**，92 城中 82 已验证）
- `292..369` 78 职种/role

**城表字段**（S7 每城运行记录 16B，是城表的派生工作副本，钳制值已知）：

| S7 偏移 | 大小 | 源城表 | 钳制 | 语义 |
|---|---|---|---|---|
| `+0x00` | B | `0x0c` | 100 | 農商等级 |
| `+0x01` | B | `0x0f` | 100 | 生産率 |
| `+0x02` | W | `0x16` | 2000 | 地域 |
| `+0x04` | W | `0x18` | 2000 | 兵数 |
| `+0x06` | W | `0x12` | 30000 | 米 |
| `+0x08` | W | `0x14` | 30000 | 資金 |
| `+0x0a` | W | `0x10` | 50000 | 軍糧 |
| `+0x0c` | B | `0x0d` | 250 | 守城度 |
| `+0x0d` | B | `0x1a` | 200 | 次級民情 |
| `+0x0e` | B | `0x0e` | 200 | 民心/治安 |
| `+0x0f` | B | — | — | 类别(bit4-6) / 标志(bit0-3)，默认 7 / `0xc` |

⚠️ **作废项**：`scripts/castle_values.json` **已作废**（基于错误的流基址 `0x598` 与切片伪像偏移 21845），改用 `sndata_sections.json`（流基址 `0x58C` / 1420，城表 @21852，**所属国 = `+0x08`**）。

### 3.6 文本系统（MSGX + GBK + 外字）

**规模**：6211 条，来自 `MESSAGE1~4.LZW`。

| 文件 | base | count |
|---|---|---|
| `MESSAGE1.LZW` | 0 | 1735 |
| `MESSAGE2.LZW` | 2000 | 1559 |
| `MESSAGE3.LZW` | 4000 | 1876 |
| `MESSAGE4.LZW` | 6000 | 1041 |

**全局 id = file_base + index**，`scripts/msgx_all_texts.json` 的 `texts` 键就是全局 id 字符串。

**编码**：**GBK 明文直解**（不是光荣私有码！`koei_codes.json` 是早期错误假设的产物，已废弃）。
`rmKOEI.bin` 是卸载程序 DLL，**不是字体渲染器**（含卸载字符串 + 文件删除 API，无任何 GDI/字体 API）。

**外字 GAIJI.TR2** = 544 B = **16 × 34 B**：
- `u16 LE` 源码（GBK `0xA140..0xA14F` 被劫持为外字区）
- 32 B = 16×16 1bpp 位图，**行主序 / MSB 先行**（唯有此位序能拼出可读汉字）

**在用的 5 槽**（其余为日版遗留）：

| 码位 | 字 |
|---|---|
| `A141`+`A143`+`A144` | **長宗我部**（元亲/信亲/盛亲共用） |
| `A142`+`A143`+`A144` | **香宗我部**（亲泰） |
| `A147` | **垪**（#182「垪和氏续」） |

影响记录号：**182 / 557 / 568 / 581 / 583**（两剧本一致）。

**Godot 实现建议**：
1. 导出时把 MSGX 全表转 **UTF-8** 存入 `data/text.json`；
2. 外字码位若无法映射 Unicode，用**占位符 + `data/gaiji.json` 位图**在 UI 层用自定义字体/图集渲染；
3. 仅 5 个武将姓受影响，**最小实现可先硬编码替换表**（長宗我部/香宗我部/垪），不实现位图渲染。

### 3.7 战图数据 `HJMAPDAT.DAT`（38 × 1700 B）

结构：**A 头 20×9/180B + B 地形 40×19（760B，半字节）+ C 部署 40×19（760B，ASCII）**

已导出产物 `scripts/hjmapdat_battles.json`（1.3 MB），每条含：
- `unit_table`：section A 9 类 × 20 属性矩阵（低 4 位）
- `terrain`：`40×19`，每格 `{code, type, mod}`（type 已中文化：平地/荒地/草地/森林/河流/城/空/阵/山地/桥…）
- `deploy`：`40×19` 部署字符

**地形分布**（第 0 战示例）：平地 55 / 荒地 48 / 草地 81 / 森林 98 / 河流 197 / 城 87 / 空 148 / 阵 18 / 山地 6 / 桥 3

**16 种地形（0–15）已实证**，频率：平地 0 ≈ 39% > 5 ≈ 13% > 4 ≈ 10% > 2/3/7 …

### 3.8 其他数据

| 数据 | 来源 | 规模 |
|---|---|---|
| 物品定义表 | SNDATA XOR 流内 S11，189 条 × 19 B | `item_table.json`；运行期物品数 200 |
| 技能名 | EXE `0x507b58`，stride 5 × 10 | 口才/马术/算术/剑术/忍术/兵法/洋枪/筑城/礼法/茶道 |
| 兵种名 | EXE `0x50bfe8`，stride 5 | **只有 4 个**：步兵/骑兵/洋枪/城守备 |
| 计略名 | EXE `0x5032d8`，stride 7 | 鼓舞/伏兵/伪兵/谣言/火计/开城/挑衅/落石/牵制/修复/填埋（11） |
| 職位名 | `0x50d850` 指针表 + `0x50bf88` 勲功阈值（6×8B） | 见 §5.5 |
| 店铺 NPC | `0x517850`，30 × 12 B | 见 §5.8 |

> 🔴 **阵形名 = 结论性不存在**（全镜像 GBK/UTF-16 扫描 0 命中）。
> 复刻按内部布阵编号 `byte[p+4]`(0..3) 经相克矩阵 `0x5031d0` **自行命名**即可。

### 3.9 导出器 `scripts/export_for_godot.py`

已提供，功能：

```bash
cd "F:/Games/Taikou 2"
python scripts/export_for_godot.py            # 默认输出到 ./data/
python scripts/export_for_godot.py --out ./data --scene 1
```

- 按 §3.3 **权威 59B 布局**重解析 `BSDATA1.TR2`（或 `--scene 2` → `BSDATA2.TR2`）
- GBK → UTF-8，处理外字替换
- 技能名纠正为 **算术/兵法**
- 导出 `officers.json` / `names.json` / `skills.json` / `text.json` / `gaiji.json` / `castles.json` / `provinces.json` / `battles.json` / `consts.json`
- **内置自检**：断言 #13 织田信长五维 = 96/85/92/99/90、職位=大名、功勲=65535

---

## 4. 核心数据模型（GDScript 骨架）

```gdscript
# src/core/Officer.gd
class_name Officer extends Resource

var id: int                  # 0..699，== BSDATA 记录号
var surname: String          # 姓
var given: String            # 名
var is_placeholder: bool     # 695..699 的 姓0NNN 占位槽

var forces: Dictionary       # {lead, martial, domestic, diplomacy, charm} 0..100
var skills: Array[int]       # 10 项，0..3；顺序见 Consts.SKILL_NAMES
var compat: int              # 相性字（bit 11-14 有效）

var birth_year: int          # 1493..1710
var father_id: int           # 0xFFFF = 无
var home_idx: int            # 出身地索引 → 国 0..48

var stamina_max: int         # 钳 100
var stamina: int
var stamina_drain: int
var ambition: int            # 恒 50

var province: int            # 0..48，255 = 无
var city: int                # 0..199，255 = 浪人
var merit: int               # 0..65535
var salary: int
var loyalty: int             # 0..100
var lord: int                # 主君 id，0xFFFF = 浪人
var rank: int                # 職位 0..7（已 & 7）
var archetype: int           # 主角槽 0..8

func full_name() -> String:
    return surname + given

func is_ronin() -> bool:
    return lord == 0xFFFF

func skill_level(k: int) -> int:
    return skills[k]
```

**哨兵常量**（务必独立定义，避免散落魔法数）：

```gdscript
# src/core/Consts.gd
class_name Consts

const NONE_PROVINCE := 255
const NONE_CITY     := 255
const RONIN_LORD    := 0xFFFF
const MERIT_MAX     := 0xFFFF
const FATHER_NONE   := 0xFFFF
const SENTINEL_FFFF := 0xFFFF

const SKILL_NAMES := ["口才","马术","算术","剑术","忍术","兵法","洋枪","筑城","礼法","茶道"]
const RANK_NAMES  := ["无","足轻组头","足轻工头","足轻头","家老","组头","家臣","大名"]
```

---

## 5. 玩法系统实现

### 5.1 时间推进与月度循环

原版循环（📚 设计层 + ✅ EXE 实证片段）：

1. **时间单位 = 月**，每年 12 月，有年号/周年事件
2. **每名可控角色每月 1 次主要指令**（修行/打工/移动/内政/出阵…），消耗体力
3. 季节/运势影响农业产出、海况、事件触发

```gdscript
# src/systems/TimeSystem.gd
func advance_month() -> void:
    for c in GameState.castles:
        DomesticSystem.monthly_settle(c)   # 年贡/軍糧/資金结算
    for o in GameState.officers:
        o.stamina = mini(o.stamina + STAMINA_REGEN, o.stamina_max)
    EventSystem.tick_month(GameState.year, GameState.month)
    GameState.month += 1
    if GameState.month > 12:
        GameState.month = 1
        GameState.year += 1
        yearly_events()
```

**城·纳结算**（续180 已破）：軍糧 / 米 / 資金 **三笔转移**，月结时执行。

### 5.2 指令系统

三套**互相独立**的表，别混：

#### A. 主命 12 项 ✅（名表 `0x504b28`，菜单 `0x46336c`）

| ID | 命令 |
|---|---|
| 0 | 贩卖军粮 |
| 1 | 购买军粮 |
| 2 | 购买军马 |
| 3 | 购买洋枪 |
| 4 | 开垦农田 |
| 5 | 改建 |
| 6 | 筑城（特例 `ID==22` 还走穴太众对话 `0x460550`） |
| 7 | 进贡 |
| 8 | 威吓 |
| 9 | 朝廷工作 |
| 10 | 收集情报 |
| 11 | 谋略 |

执行链：`0x4607f0` → `0x46086c` 跳表 → `0x496ba0`（中央状态/画面转移引擎，711 调用点）
运行时状态：`0x513fcc` word 条目数；`0x513fd4` word[count] stride 2（**低 15 位 = ID，bit15 = 已询问过**）

#### B. 报告 13 项 ✅（handler 表 `0x504898`）

13 个 handler，文本见 `GAME_DATA_SPEC.md §4.3.2`（MSGX `M3#0x1202`–`M3#0x120e`）。
**报告选取是状态机而非 1:1 表**：依赖 `0x513ff6`（馬販子可用性）、`0x513ff8`（米価可用性）、已询问数、`0x4ebe40(p)` 概率门 **40%**。

#### C. 大名家臣会议 ✅（两级菜单）

**主会议 4 项**（名表 `0x50c7a0` stride **16 B** ← 注意：旧记 stride 14 有误）：

| sub-handle | 菜单名 | handler |
|---|---|---|
| 0 | 听取意见 | `0x4c1830` |
| 1 | 分派工作 | `0x4c1ef0`（含外交） |
| 2 | 出兵 | `0x4c2590` |
| 3 | 结束会议 | — |

**工作类型 16 项**（名表 `0x50c7e0` stride 16 B）：

| # | 类型 | handler | # | 类型 | handler |
|---|---|---|---|---|---|
| 0 | 高压外交 | `0x4c41e0` | 8 | 训练 | `0x4c4b20` |
| 1 | 友好外交 | `0x4c4320` | 9 | 修复 | `0x4c4c00` |
| 2 | 谋略 | `0x4c4400` | 10 | 筑城 | `0x4c4dd0` |
| 3 | 卖出军粮 | `0x4c4520` | 11 | 朝廷工作 | `0x4c5000` |
| 4 | 购入军粮 | `0x4c45c0` | 12 | 收集情报 | `0x4c5100` |
| 5 | 购入军马 | `0x4c4640` | 13 | 移动居城 | `0x4c5190` |
| 6 | 购入洋枪 | `0x4c46c0` | 14 | 武者修行 | `0x4c5360` |
| 7 | 开垦农田 | `0x4c4740` | 15 | 茶会 | `0x4c5430` |

派发器：`0x4c55b0` = `jmp dword ptr [eax*4 + 0x50c950]`
完整链：`0x4c2000` 选类型 → `0x525e30[sel]` 取码 → `0x4c55c0` 校验 → MSGX `0x85f` → `0x4c2240` 选执行者 → `0x4c1fcf`

#### D. 城内场所名池（15 项，`0x508040` stride 10 B）

茶室 / 铁匠铺 / 南蛮商馆 / 教堂 / 剑术道场 / 公卿府邸 / 画师工坊 / 寺院 / 神秘宅邸 / 医院 / 老家 / 民宅 / 武家宅邸 / 乡间寺院 / 皇宫

### 5.3 内政

- **武将仕事三字段** + ディスパッチャ `0x4a9f10`（三层映射），见 `§3.21.3`
- **城種派生上限**：`0x49f9xx` 跳表，见 `§3.21.5`
- **工事カウンタ / 築城済 flag**：见 `§3.21.6`
- **关系行动成功判定**：`0x4ab870`（续179 已破），见 `§3.21.10`

⚠️ **留档矛盾**：守城度可能 > 城種上限（`§3.21.7`），复刻时按实际数据允许溢出或补钳制，二选一即可。

### 5.4 修行与技能增长 ✅（最完整的一块，直接实现）

**修行菜单**（`0x45f710`，串表 `0x504800`/`0x504818` stride 11）：

| 动作 | mode | 效果 |
|---|---|---|
| 学习内政 | 0 | **口才** +1（概率 `rand%(16-sub)==0`） |
| 学习外交 | 1 | **筑城** +1（概率与属性和相关） |
| 学习魅力 | 2 | **兵法** +1 |
| 学习剑术 | 3 | 武力 +1 |
| 读书 | 4 | 50% 内政 +1，否则 统御 +1 |
| 艺术鉴赏 | 5 | 魅力 +1 |
| 宝物鉴赏 | 6 | 外交 +1 |
| 什么也不做 | 7 | 早退 |

**资格判定**（`0x4b5620`）：学习者与师父的 **技能等级和 ≥ 6** / **外交和 ≥ 100** / **魅力和 ≥ 100**，任一达标则不可执行。

**天数/花费**：玩家自选天数，上限 `min(31 - 当前日, 金钱/2)`；每日花费 **2 金**；金钱 < 2 不可修行。

**技能递增语义**（续240）：
- 写器族 = cap-3 递增器 `0x4a3040 + k*0x20`，thiscall `ecx = 实体 + 0x0f`
- 对 `byte[ecx + k>>2]` 的 `(k&3)*2` 位 **+1，封顶 3**
- **成功则功勲 += (旧级+1) × 500**，饱和加 `word[+0x26]`，**上限 60000**

**mode ≥ 3（五维增长）**：`0x45feb0 → 0x4600d0`，加统御/武力/内政/外交/魅力，**封顶 100**。

**其余 13 个技能消费站**（k1/k2/k3/k4/k6/k8/k9 等）已归位：
马屋打工 / 商家学做生意 / 道场试合 / 忍里修业 / 铁炮锻冶 / 寺庙修行 / 茶人品茶 …
完整事件表见 `GAME_DATA_SPEC.md §3.5.6`（续241）。

```gdscript
# src/systems/TrainingSystem.gd
static func try_skill_up(o: Officer, k: int, rand_val: int, sub: int) -> bool:
    if rand_val % (16 - sub) != 0:
        return false
    var old := o.skills[k]
    if old >= 3:
        return false
    o.skills[k] = old + 1
    o.merit = mini(o.merit + (old + 1) * 500, 60000)
    return true
```

### 5.5 職位与晋升 ✅

- **職位名表** `0x50d850`（9 项指针表 stride 4）
- **勲功阈值表** `0x50bf88`（**6 条 × 8 B**）
- **晋升判据**：`0x4ab1d0`（城内）/ `0x4b9ae0`（評定），两处同构
- **set_rank** `0x49a7e0`：`and eax,0xf8ff; or eax,edx` ⇒ 職位只占 word 的 **bits 8–10**

**两条独立轴**（重要纠偏，别混为一谈）：
1. **職位**（`byte[0x39] & 7`）：无/足轻组头/足轻工头/足轻头/家老/组头/家臣/大名
2. **平行职种**（`byte[+0x2e] >> 4`）

**标志位域** `byte[+0x2d]`，**状态面板渲染** `0x4e87e0`。

参考实现：`scripts/promo_ref.py`（11/11）、`scripts/promo2_ref.py`（18/18）、`scripts/promote3_ref.py`（42/42）

### 5.6 合战 ⭐（最完整，第一个里程碑）

> 主函数 `0x42d270`。**可直接移植 `scripts/battle_formula_ref.py`**。
> 已用 Unicorn 2.1.4 隔离仿真实跑真实二进制 **双重验证**（`scripts/_emu_battle.py`，3 场景逐单位 bit-for-bit 吻合）。

**单位槽**：15 槽 @ `0x513910`，stride **24 B**
- `+0x0c` word 兵力 / `+0x11` 士气 / `+0x12` 士气损失
- `+0x13` 状态（**低 2 位 = 兵种类别 0/1/2**，高 4 位 ≠ 0 = 已退场）
- `+0x15` bit2 = 阵营

```gdscript
# src/battle/BattleSim.gd

# 1) 兵力边际收益曲线（0x43cd10，分段线性、处处连续）
static func troop_scale(t: int) -> int:
    if t <= 100:  return t
    if t <= 300:  return t / 2 + 50
    if t <= 500:  return t / 4 + 125
    if t <= 1000: return t / 5 + 150
    return 3 * t / 20 + 200      # 1000→350, 3000→650：兵力×6 战力仅×2.6

# 2) 单位战力（0x42d5d0，逐单位累加到本方阵营）
static func unit_strength(u: Dictionary) -> int:
    var cat: int = u.state & 3
    var v: int
    if cat == 1:
        v = u.atk + 15 * u.equip + 20
    elif cat == 2:
        v = u.atk + 25 * u.equip + 10
    else:
        v = u.atk
    var m: int = maxi(0, u.morale - u.morale_loss)   # 净士气
    v = v * (100 + m / 10) / 100                     # 每 10 点净士气 = +1%
    v = maxi(v, 10)                                  # 战力地板
    v = v * troop_scale(u.troops) / 23               # 魔数 0xb21642c9/sar4 ≡ //23
    return v
```

**阵营修正**：
```
S1 = army_strength(1)
if mode_m1 and (parity & 1): S1 >>= 3        # 战力 ÷8
S0 = army_strength(0)
S0 = 4 * S0 / 5                              # ★ side0 恒 ×80%（写死的不对称，必须保留）
if pA.kind == pB.kind: S0 = 4 * S0 / 5       #   两将同类再 ×80%
```

**攻击摊薄 + 伤害**：
```
E1 = S1 / side0_alive * 2
E0 = S0 / side1_alive * 2
base_vs_side0 = E1 * 7 / modB
base_vs_side1 = E0 * 7 / modA
base = base_vs_side0 if side == 0 else base_vs_side1
dmg  = base / (def / 4 + 50) + 1             # ★ 保底 1 兵
if side == 1 and mode_m1: dmg = 0            # side1 免伤
troops = maxi(0, troops - dmg)
```

**攻击除数表**（`0x503770`，20 B；索引 = section A 低 4 位，按 `battle_type` 取 +0 或 +8 窗口）：
```
[10,12,15,7,7,15,100,100, 10,10,12,7,7,10,10,8, 100,100,12,12]
```
→ `7` 最强档；`8/10/12/15` 常规；**`100` ≈ 零伤害档**（疑本阵/辅助单位）。
section A **高 4 位** = 双方除数 ±1 对冲（38 战静态恒 0，中性）。

**四条数值设计要点（复刻平衡必读）**：
1. 每单位每回合**至少掉 1 兵** → 战斗必然收敛，不会僵持。
2. **防御是软上限**（分母 `def//4+50`）：0→200 的防御只能把伤害减半，堆防收益极低。
3. **士气才是乘数**，长回合复利放大；士气归零直接掉到战力地板 10。
4. **兵力递减 + 攻击摊薄**：多支小队抗集火（伤害被分摊），单支大军吃亏——这是太阁2「小队可用」的数值根因。

**其他合战要素**：
- **布阵 + 11 计略** ✅（相克矩阵 `0x5031d0`，180° 点对称坐标表），见 `§3.10`
- **地形攻防/移动系数** ✅，见 `§3.12`
- **造兵数公式** ✅：`count = base[tier] + rand16() % mod[tier]`（`spawn_count_formula_ref.py`）
- **评价词档位阈值** ✅：`val < lo → 0` / `lo ≤ val < hi → 1` / `val ≥ hi → 2`（`eval_word_thresholds_ref.py`）
- **八方向偏移表** `@0x503710`
- **合战变体选择**：`rand() % RND[tier] + BASE[tier]`，3×10 项表 `@0x503740/0x503750/0x503760`

### 5.7 单挑（一骑讨）

📚 设计层为主（卡牌状态机未完全静态破解），但**音效证据充分**：
`KOUGEKI1/2`(攻击)、`OOATARI`(命中)、`SEIKOU`(成功)、`SHIPPAI`(失败)、`NIGERU`(逃跑)、`KAISHIN`(会心)、`UKETA`(受)、`YOKETA`(避)、`INOTIGOI`(命乞)

- 机制：回合制**卡牌对战**，双方各有气力/体力与手牌（攻击/防御/必杀/奥义）
- 判定基准：**武力 + 剑术等级 + 卡牌效果 + 随机**
- 伤害分档 → 台词 `0x4665d0`；三段式伤害模型见 `§3.15.6`
- 25 个单挑函数已定位（节选见 `§3.15.4`）

**建议**：先做原型（4 类卡 + HP + 气力），数值自定；后续用 `§3.15` 细节打磨。

### 5.8 店铺设施 ✅（公式全拆，续243）

**NPC 池** `0x517850` **30 × 12 B**（= S8 台词表 / NPC 师父池同表），入店分发器 `0x44e710`（`[0x52063c]` = `0x517850 + id*12`）。

**12 槽设施身份**（msg 锚全识别）。🔴 **纠偏**：`+0x07` = **店主好感**（非「商人资本」）。

**字段语义归位**：
- `+0x08` = 设施状态 **word**
- `+0x0a` = 进度计数
- `+0x0b` = 事件旗位域

**各设施流**：
- **画师**（slot 7）：袄绘依頼 30 门 / 80 贯；`+0x0a = 20 + rand(41)`；`+0x08 = 1` 制作中
- **医师**：`+0x08` = 就诊亲密度；免费判定 `rand(100) < 好感 − 10`；诊金 = `gap × (100 − 亲密度) × 身分 / 100 ÷ 10 × 10`，**min 10**；穷人流 `+0x0a` cap 3；买药药罐 `word[S6+0x26] >> 12`
- **教会**：义工 `+0x0b` bit1/0 首回标记；魅力受益；大名情报费 `5 − 捐/20`；捐 100 免费；介绍信 `0x1211`
- **南蛮**：陌生人门 `+0x07 == 0`；问候 `sbb`；洋枪 `15 − 好感/30`
- **闇商人** #29 事件流 `0x460890`（唯一调用方 `0x4634c0`）

**通用持有物选择对话框** `0x44e110`（`-1` = 取消）。

参考实现：`scripts/shop_facility_flows_ref.py` **41/41**、`scripts/shop_npc_record_ref.py` **80/80**

### 5.9 外交

- **高压外交** `0x4c41e0` / **友好外交** `0x4c4320`（近同构，额外调 `0x49f640`）
- 流程：`0x49f5e0` 取玩家 → `0x4c4270` 选目标国（遍历 `0x5179b8` 49 条）→ `0x4c4300` 选使者武将（`0xffff` = 取消）→ 武将实体 = `0x519868 + id*47` → `0x49c2b0` 取显示名 → MSGX `0x875`「任命 XX 为使者」
- **国政治表** `0x5179b8` stride 14 × 49，`byte[0xc]` = **外交等级**（低 4 位 level + 高 4 位 quality）
- 8 级国关系表 `0x5080cc`

⚠️ **仍 🔶（设计层，可自定）**：使者抵达后的**关系值变更公式 / 成功率**（两个 handler 只做任命，结算在月推进时）；参数表 `0x50c990` 3B 语义（`255` 疑似「不需要」）；AI 主动外交决策。
→ **复刻可自行设定**，不阻塞。

### 5.10 事件系统

**结构层已闭**：
- S15 段 C「**事件 id × slot × val**」**全映射**（续212/220，16/16 逐站点归属）
- 未定名事件 bit 的 **MSGX 锚点全定位**（续227）
- 旗标表 `0x5203c0` **25 B** 布局坐死

剩余 🔶 属**剧情内容层**（具体史实事件链排布），复刻时按史实自行编排即可。

---

## 6. 表现层


### 6.2 音效（39 个，已完成）

- **KOS 格式** = 1 字节 XOR 密钥 + 标准 WAV。`raw[0]` = key（**39/39 均 `0xAE`**），`raw[1..]` 逐字节 XOR → RIFF/WAVE
- 已解码产物：**`scripts/_decoded_kos/*.wav`（39 个，权威）**
- `play_sfx` = `0x4997c0`，**ID 上限 39**（`cmp si, 0x27`），门控四层
- 全局开关 `byte[0x520604]` bit1
- 音效名指针表 `@0x50ba40`（40 项）

**接入**：复制 39 个 WAV → `assets/sfx/`，Godot 里建 `sfx_id → AudioStream` 映射。
**注意**：`*.KOS` 已被 git 移除（`scripts/kos_wav/` 删除），`_decoded_kos/` 是唯一来源。

**BGM**：中文版走 `MP3/` 目录（不是 KOS）。

### 6.3 字体与中文文本

- CJK 走**系统字体**（Godot 4 默认 `Noto Sans SC`）；`fonts/` 已有 NotoSansSC 17.7 MB + `.import`
- 文本全部 **UTF-8**（导出时从 GBK 转）
- **外字**：见 §3.6，最小实现用硬编码替换表（長宗我部/香宗我部/垪）

### 6.4 分辨率适配（1080p / 2K / 4K）

| 屏幕 | viewport | 3D 渲染 | 256×256 sprite 显示 |
|---|---|---|---|
| **1080p** | 1920×1080 | 原生 | ~180px（缩 0.7x）✓ 锐利 |
| **2K** | 2560×1440 | 原生 | ~240px（近原生）✓ 锐利 |
| **4K** | 3840×2160 | 原生 | ~360px（放 1.4x）✓ 保留像素感 |

- 内部**逻辑坐标系 640×400 不变**（保留原版构图与 UI 锚点，UI 按此写）
- 运行时由 **`src/core/DisplayAdapter.gd`**（autoload）自动检测屏幕 → 选 viewport
- 4K 掉帧时由 `DisplayAdapter` 降档保帧率

---

## 7. 里程碑路线图

| 里程碑 | 目标 | 验收标准 | 依赖 |
|---|---|---|---|
| **M0 数据层** | 导出器跑通，`data/*.json` 生成 | 断言织田信长五维 96/85/92/99/90；695 武将 + 5 占位；200 城；49 国；6211 文本 | §3.9 |
| **M1 数据加载** | `DataLoader` 载入全部 JSON，建内存索引 | 可按 id 查武将/城/国/文本；无解析错误 | M0 |
| **M2 合战沙盘** ⭐ | 纯逻辑合战，无 UI | 移植 `BattleSim`，跑 38 张战图各 100 场，结果收敛（无死循环/负值） | M1 + §5.6 |
| **M3 最小可玩** | 选主角 → 看状态 → 执行 1 条主命 → 推进 1 月 | 能看到五维/技能/職位/忠诚；月推进后体力回升 | M1 + §5.1/5.2 |
| **M4 内政与修行** | 12 主命 + 修行 8 动作 + 技能增长 | 技能 cap 3 生效；功勲 += (旧级+1)×500 封顶 60000 | M3 + §5.3/5.4 |
| **M5 職位晋升** | 勲功达阈值可晋升，大名/城主任命 | `promote2_ref.py` 18/18 对应逻辑一致 | M4 + §5.5 |
| **M6 表现层** | 音效 + 文本渲染 + 自绘 UI | 音效 39；外字 3 姓正确；UI 全自绘 | 全部 |
| **M7 打磨** | 单挑、店铺、外交、事件链 | 各自 SPEC 章节 | M6 |

**建议顺序理由**：**合战（M2）提前**——它是唯一「反汇编 + 二进制仿真双验证」的闭环系统，做出来就是**原版手感**，能最早验证整条数据链是否正确。

---

## 8. 验证与回归

### 8.1 逆向侧自测（改动数据时必跑）

```bash
cd "F:/Games/Taikou 2/scripts"
python _run_all_selfchecks.py     # 180 ref 全 PASS / 0 FAIL（约 12 分钟）
```

⚠️ 会再生成 `bsdata_format.json` / `bsdata_tail_fields.json`，跑完 `git checkout --` 还原。

### 8.2 复刻侧验证

| 验证 | 方法 |
|---|---|
| 数据一致性 | 导出器内置断言（织田信长 / 木下藤吉郎样本） |
| 武将总数 | 700 = 695 真实 + 5 占位 |
| 職位合法性 | 全部 `rank` ∈ [0,7]（**未 `&7` 会有 38 条越界**） |
| 忠诚值域 | 全部 ∈ [0,100] |
| 技能值域 | 全部 ∈ [0,3] |
| 合战收敛 | 38 图 × 100 场，无死循环、兵力非负、必然分出胜负 |
| 文本覆盖 | 6211 条全部 UTF-8 可解 |

### 8.3 数值平衡压测

因为 `src/battle` 不依赖 Node，可**无头批量跑**：

```gdscript
# 批量跑 1000 场，统计平均回合数 / 伤亡率 / 胜负分布
```

对照 `BATTLE_SPEC.md §9.8` 的四条设计要点检验：保底 1 兵是否生效、防御是否软上限、士气是否复利、小队是否抗集火。

---

## 9. 避坑清单（复刻专用）

### 数据侧

1. 🔴 **`bsdata.json` 的 `fields` 已证伪**（§3.2）。忠诚真在 `0x35` 不是 56；功勲在 `0x32` 不是 50。
2. 🔴 **職位必须 `& 7`**：原始字节 38/690 条 > 7。
3. 🔴 **技能名是「算术/兵法」**，不是「算用/军学」。
4. ⚠️ **城的索引是 0..199**（200 条城表），不是 92。92 是城镇三件套的对齐数。
5. ⚠️ **`castle_values.json` 已作废**，用 `sndata_sections.json`。
6. ⚠️ **`koei_codes.json` 是错误假设的产物**（真实是 GBK），**看到 KOEI 字样一律当过时结论**。
7. ⚠️ **`chip_palettes.json` 只是近似盘**，CHIP/CHAR 并非统一 8bpp（MAPCHIP=裸 RGB565 / TOWNCHIP=4bpp 位平面交错 / HBCHAR=EGA 4 平面）。
8. ⚠️ **搜索武将全名会搜不到**（姓和名之间夹 `00 00 00`），要分开搜或按记录 GBK 解码。
9. ⚠️ **`TaikouParser.parse_bsdata()` 是错误占位桩**（假设 100 字节/条，实际 59），别再用。

### 玩法侧

10. 🔴 **side0 恒吃 80% 伤害**是写死的不对称，**必须保留**，否则平衡崩。
11. 🔴 **陣形名不存在**，别去找（全镜像 0 命中）。
12. ⚠️ **9 类兵种索引 ≠ 4 个兵种名**（`a ∈ [0,8]` vs 4 个名），别硬套。
13. ⚠️ **主命 12 / 报告 13 / 会议工作 16 是三套独立表**，别混。
14. ⚠️ 会议菜单 **stride 是 16 B 不是 14 B**（旧记有误）。

### 工程侧

15. ⚠️ **`scripts/` 目录不要移动**（180 个 `*_ref.py` 自测经非递归 `glob` 扫描，物理移动会破坏套件）。
16. ⚠️ **`project.godot` 不要删**（脚本根定位哨兵认它）。
17. ⚠️ **不要 commit 原版素材**（`Taikou2 Original/` 与 `assets/gfx/` 应 gitignore）。
18. ⚠️ **`KOS` 音效无台词**——台词来自 `MESSAGE*.LZW`（GBK）。旧 `kos_message_map.json` 系误读 PCM，已废。

---

## 附录 A：关键常量速查

```gdscript
const OFFICER_COUNT       := 700      # 695 真实 + 5 占位
const OFFICER_RECORD_SIZE := 59
const ENTITY_POOL_SLOTS   := 370
const ENTITY_STRIDE       := 47
const CASTLE_COUNT        := 200
const PROVINCE_COUNT      := 49
const MSGX_TOTAL          := 6211
const BATTLE_MAPS         := 38
const SFX_COUNT           := 39

const BATTLE_UNIT_SLOTS   := 15
const BATTLE_UNIT_STRIDE  := 24

# 攻击除数表（0x503770，20B）
const ATK_DIVISORS := [10,12,15,7,7,15,100,100,
                       10,10,12,7,7,10,10,8,
                       100,100,12,12]

const MERIT_CAP       := 60000
const STAMINA_CAP     := 100
const FORCE_CAP       := 100
const SKILL_CAP       := 3
```

## 附录 B：可移植的参考实现索引

| 系统 | 脚本 | 自检 |
|---|---|---|
| **合战结算** | `scripts/battle_formula_ref.py` | ✅ |
| 職位/晋升数据层 | `scripts/promo_ref.py` | 11/11 |
| 職位晋升公式 | `scripts/promo2_ref.py` | 18/18 |
| 大名/城主任命 | `scripts/promote3_ref.py` | 42/42 |
| 技能写器族 | `scripts/skill_inc_writer_ref.py` | 83/83 |
| 技能消费站 | `scripts/skill_writer_consumers_ref.py` | 82/82 |
| 店铺 NPC 记录 | `scripts/shop_npc_record_ref.py` | 80/80 |
| 店铺设施流 | `scripts/shop_facility_flows_ref.py` | 41/41 |
| BSDATA 格式 | `scripts/bsdata_format_ref.py` | 73/73 |
| 造兵数公式 | `scripts/spawn_count_formula_ref.py` | ✅ |
| 评价词阈值 | `scripts/eval_word_thresholds_ref.py` | ✅ |
| 报告系统 | `scripts/council_report_ref.py` | 18/18 |
| 会议系统 | `scripts/council_ref.py` | 16/16 |
| 外交 | `scripts/diplomacy_ref.py` | ALL PASS |
| 外字身份 | `scripts/gaiji_identities_ref.py` | 30/30 |
| **LS11 解压** | `scripts/real_assets.py` → `ls11_decompress()` | 被 4 个 ref 间接覆盖 |

> **LS11 解压直接用 `real_assets.py` 的 `ls11_decompress(data)`，不要重写。**

## 附录 C：文档地图

| 需要什么 | 读 |
|---|---|
| 数值/玩法权威定义 | `docs/specs/GAME_DATA_SPEC.md` |
| 合战（伤害/地形/计略） | `docs/specs/BATTLE_SPEC.md` |
| 剧本/存档容器与 XOR 流 | `docs/specs/SNDATA_SPEC.md` |
| 图像格式（NPK/LZW） | `docs/specs/NPK_SPEC.md` |
| 「某块破没破」 | `docs/specs/破解状态清单.md` |
| 突破历史 | `docs/re/BREAKTHROUGHS.md` |
| 数据在哪/怎么取 | `docs/replication/复刻导航.md` |
| **本文：工程怎么搭** | `docs/replication/Godot复刻实施方案.md` |

---

*编写日期：2026-09-08 ｜ 基于突破日志顶部 续253（非图像结构/数据层 100% 收口，180 ref 全 PASS）*
