# 太阁立志传2 — 项目记忆（索引）

> 只留**跨会话必需**的边界/防重踩坑/当前状态；数值细节查权威文档。
> 文档链：`README.md`→`docs/INDEX.md`→`docs/specs/GAME_DATA_SPEC.md`(数据权威)+`docs/re/BREAKTHROUGHS.md`+`docs/replication/`(★施工图/进度表)。
> ⚠️ `scripts/` 不移动（180 个 `*_ref.py` 非递归 glob）。

## 边界与当前阶段
- Godot 4.7.1 自写复刻；原版 `<工程>/Taikou2 Original/`（149 文件，不打包）。画面 **HD-2D**（3D+高清像素+后处理；像素破解豁免）。
- 非图像逆向 100% 收口。Godot **M0–M5 完成**（M5=職位晋升）+ **12 主命精确 delta（续254）**+ **M6/HD-5 自绘 UI 完成**（标题/主角选择/状态画面全改自绘，0 处硬编码字号、0 原生 Button/Label）+ **音效 39 已接入**（`AudioManager.play_sfx(id)` 对齐原版数字 id，`UiButton` 点击联动）。下阶段：BGM / 素材规格 / HD-6·M7。git push 仍卡凭据。

## 🔴 高频纠偏（别再踩）
| 旧记 | 正确 |
|---|---|
| `bsdata.json` 的 `fields` 直接用 | ❌ 续200：用 `export_for_godot.py` |
| 技能名 算用/军学 | 实为 **算术/兵法** |
| 城表 92 条 | **200 条** 0..199 |
| 職位名 足轻组头… | ❌ 续63：正版=浪人/步兵头/队长/侍大将/部将/家老/宿老/大名/城主（`Consts.RANK_NAMES`） |
| 城主(8)是職位字段 | ❌ 城主=城表派生 `word[城表+0x0a]`（`f0a`）；3-bit職位仅0..7 |
| 贩卖/购买军粮 handler 直写軍糧/米 | ❌ 续254：只算仕事成果値 `byte[ent+0x17]`，转移走纳结算 `0x4a5fc0` |

## GDScript / 无头坑（每次写 GDScript 前看）
- `JSON.parse_string` 数字全 float→建 id 索引须 `int(rec["id"])`；改 GameData 缓存 Array/Dict 须 `.duplicate()`；除法 `//`。
- 无头 `--script`：autoload 未进树→`process_frame.connect(_run, CONNECT_ONE_SHOT)`；末尾 `quit(0)`（否则 rc=1 噪声）。**不建全局类缓存→禁用 `class_name`，跨文件一律 `preload`**（也勿 `class_name GameState`，与 autoload 冲突）。
- lambda 捕获局部变量**按值**→计数/累加须用 Array/Dict，否则永远读到 0。
- 载 TTF 用 `FontFile.load_dynamic_font(ProjectSettings.globalize_path(res://...))`；**不可用 `ResourceLoader.load`**（依赖 .import 缓存，会静默回退无 CJK 字体→中文变方框）。
- UI 布局勿硬编码字号/像素（`canvas_items` 会缩放，设计空间 1920×1080）。

## 约定 / 环境
- 工程根=`project.godot`；四目录 `src/`·`scenes/`·`assets/`·`scripts/`。autoload=DisplayAdapter+GameData+GameState。覆盖层存 `GameState` 运行期变更，不回写 data/。
- 无头测试：`Godot_v4.7.1-stable_win64_console.exe --headless --script res://tools/_test_mX.gd`。反汇编用系统 Python3.12（capstone 5.0.7；托管 3.13 无）。
- **git push 卡凭据**（GCM 无凭据，待 PAT）：`remote=https://github.com/Zhaoxinak/Taikou-2`。
- 突破插 BREAKTHROUGHS 倒序（四段），续编号取 `grep -o '上一条（续[0-9]*）'` max+1。

## 数据细节指针（勿抄进本文件）
- 武将/城字段 → `GAME_DATA_SPEC.md` §1.2/§3.17（城表 `0x51eb88` 31B×200）。
- 晋升阈值 / 12 主命公式 → `src/core/game_state.gd`；自绘 UI 度量 → `src/ui/UiTheme.gd`。
