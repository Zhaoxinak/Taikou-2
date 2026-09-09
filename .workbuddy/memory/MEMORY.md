# 太阁立志传2 — 项目记忆（索引）

> 只留**跨会话必需**的边界/防重踩坑/当前状态；数值细节查权威文档。
> 文档链：`README.md`→`docs/INDEX.md`→`docs/specs/GAME_DATA_SPEC.md`(数据权威)+`docs/re/BREAKTHROUGHS.md`+`docs/replication/`(★施工图/进度表)。
> ⚠️ `scripts/` 不移动（180 个 `*_ref.py` 非递归 glob）。

## 边界与当前阶段
- Godot 4.7.1 自写复刻；原版 `<工程>/Taikou2 Original/`（149 文件，不打包）。画面 **HD-2D**（3D+高清像素+后处理；像素破解豁免）。
- 非图像逆向 100% 收口。Godot **M0–M5 完成**（M5=職位晋升）+ **12 主命精确 delta（续254）**+ **M6/HD-5 自绘 UI 完成**（标题/主角选择/状态画面全改自绘，0 处硬编码字号、0 原生 Button/Label）+ **音效 39 已接入**（`AudioManager.play_sfx(id)` 对齐原版数字 id，`UiButton` 点击联动）+ **M7 事件链(S15) 已收口** + **M7 单挑(duel) 已收口**（`DuelSim`+`GameState.run_duel`+`_test_duel` 全过）+ **M7 事件文本渲染(event_text) 已收口**（`src/core/event_text.gd` 10 bit MSGX 叙事 + `%s`→主角名 + `GameState.render_event_text/render_resolved_events` + `_test_event_text` 全过）+ **M7 店铺/商业核心(shop) 已收口**（`src/core/shop.gd` 30 记录 + 入店分发 + favor 饱和 + 买药÷50；设施内交互流程与闇商人事件流留待后续）+ **M7 外交(diplomacy) 已收口**（`src/core/diplomacy.gd` 1176B 国関係マトリクス + 外交/主从位域 + 有向 2↔3 镜像 + 筛选/变更点 + 使者功勋；AI 主动外交与 UI 层留待后续）。+ **HD-3 光照+天气联动已接线完成**（新增 `src/render/WeatherFX.gd` 雨/雪 `GPUParticles3D`，分 CPU 安全层 `needs_particles/build_material/build_draw_mesh` 与运行时 `make_particles`；`battle_screen.gd` 加 `@export weather` + `_setup_environment`/`_apply_weather_now`/`set_weather`，4K 自动 `downgrade_for_4k`；`tools/_test_hd3.gd` 43 项**待实跑**）。下阶段：M7 余下（HD-6 视觉回归+4K 基准）、SHOP 设施内交互流程、AI 主动外交(续104)、MSGX 事件解释器、BGM、素材规格。git push 走 `127.0.0.1:7890` 代理可用（9120 已死）。

## 🔴 高频纠偏（别再踩）
| 旧记 | 正确 |
|---|---|
| `bsdata.json` 的 `fields` 直接用 | ❌ 续200：用 `export_for_godot.py` |
| 技能名 算用/军学 | 实为 **算术/兵法** |
| 城表 92 条 | **200 条** 0..199 |
| 職位名 足轻组头… | ❌ 续63：正版=浪人/步兵头/队长/侍大将/部将/家老/宿老/大名/城主（`Consts.RANK_NAMES`） |
| 城主(8)是職位字段 | ❌ 城主=城表派生 `word[城表+0x0a]`（`f0a`）；3-bit職位仅0..7 |
| 贩卖/购买军粮 handler 直写軍糧/米 | ❌ 续254：只算仕事成果値 `byte[ent+0x17]`，转移走纳结算 `0x4a5fc0` |
| 外交目标国筛选按「外交関係」 | ❌ 续95：0x4c4270 按**主从関係**过滤 |
| `mission_level` 除数 10 | ❌ 实为 **20**（magic `0x66666667`+sar3） |
| 盲信 `diplomacy_spec.json` 的 asm 三角索引 | ❌ 该句有误（max 1222 溢出 1176）；正解 `i*49-i*(i+1)/2+(j-i-1)` |
| 地形材质 11 种（Terrain3DBuilder 旧表） | ❌ 全 38 战实测 **16 种**；漏 `?8/?9/?A/?B/?C` 会让 4234 格变默认灰。?8~?C 名称 EXE 内搜不到（`sectA2_spec.json` 证据：地形中文名是 JSON 侧硬编码），现按邻接统计**推定**为河原/砂州/湿地/葦原/城濠 |

## GDScript / 无头坑（每次写 GDScript 前看）
- `JSON.parse_string` 数字全 float→建 id 索引须 `int(rec["id"])`；改 GameData 缓存 Array/Dict 须 `.duplicate()`；除法 `//`。
- 无头 `--script`：autoload 未进树→`process_frame.connect(_run, CONNECT_ONE_SHOT)`；末尾 `quit(0)`（否则 rc=1 噪声）。**不建全局类缓存→禁用 `class_name`，跨文件一律 `preload`**（也勿 `class_name GameState`，与 autoload 冲突）。
- 🔴 **本机 Godot 二进制**：`/Users/ts/Downloads/Taikou 2/Godot/Godot.app/Contents/MacOS/Godot`（4.7.1.stable，与项目同版；另有 `Godot_mono.app`）。macOS **无 `timeout` 命令**→用 Bash 工具 timeout 参数。
- 🔴 **2026-09-09 起 `--script` 主循环失效**：`--headless --script` 恒卡死、`_run()` 从不执行（**裸工程同样卡死→环境问题非代码问题**）；已排除 .godot 缓存/残留进程/渲染驱动(dummy·vulkan·metal·opengl3)/音频/沙箱/文件 NUL。⇒ 暂**勿依赖跑 `_test_*.gd` 验证**，改 `--check-only`（不同代码路径）或人工走查。启动期 13 条 `Unexpected NUL character` 为干扰项（实测文件 0 NUL；zsh 下 `grep $'\x00'` 是**假阳性**，须用 Python 数 `b"\x00"` 复核）。
- ⚠️ **`TaskStop` 杀不掉 Godot 真进程**→必须 `pkill -f "Godot.app/Contents/MacOS/Godot"` 并用 `pgrep` 复核；残留进程会占锁拖慢/卡死后续运行。
- ⚠️ **新增带 `class_name` 的文件不会自动进全局类缓存**→其他脚本直接写 `X.Y` 会 Parse Error "Identifier not declared"。**跨文件引用新文件一律 `const X = preload("res://...")`，别依赖 class_name 全局缓存**。
- ℹ️ **`--script` 卡死前仍会打印 Parse Error** → 即使跑不完 `_run`，也可用它验证「新脚本是否编译通过」（看有无 Parse Error / Compile Error 即可）。
- 🔧 **反汇编**：本机无 capstone 时装的隔离 venv `/Users/ts/.workbuddy/binaries/python/envs/default/bin/pip install capstone`（5.0.7）。用法 `Cs(CS_ARCH_X86,CS_MODE_32).disasm(data[va-0x400000:], va)`，`_unpacked_mem.bin`（2MB，**gitignored 无生成器**，换机器需手工拷）。
- ⚠️ **魔数除法别混**：`0x51eb851f`+sar3 = **/25**（sar4 = /50）；`0x66666667`+sar3 = **/20**（mission_level 也用它，除数 20 非 10）。
- ✅ **`--script` 跑不动时的替代验证链路**：① Godot 跑一遍查 Parse Error（验证编译）；② 用 **Python 等价实现复跑同一套断言**（验证逻辑与预期值）。两者结合可行。
- ⚠️ **非 autoload 脚本取 GameData**：本构建 `Engine.get_singleton("GameData")` 返回 **null**（autoload 仅挂树 `/root/GameData`，未注册 Engine 单例）；编译期也**无法解析 `GameData` 全局名**（仅 autoload 脚本因编译序可）。正确做法：依赖注入——autoload 侧 `event_text._data = GameData`（在 `_ready` 注入，GameData 注册序在前），或在测试里 `et._data = root.get_node("/root/GameData")`。事件文本 `render_event` 调 `_resolve_text` 走 `_data.get_text(mid)`。
- lambda 捕获局部变量**按值**→计数/累加须用 Array/Dict，否则永远读到 0。
- 载 TTF 用 `FontFile.load_dynamic_font(ProjectSettings.globalize_path(res://...))`；**不可用 `ResourceLoader.load`**（依赖 .import 缓存，会静默回退无 CJK 字体→中文变方框）。
- UI 布局勿硬编码字号/像素（`canvas_items` 会缩放，设计空间 1920×1080）。
- ⚠️ `const X : PackedByteArray = PackedByteArray([...])` 无法被外部脚本 `preload` 引用 `.X` 解析（"Could not resolve external class member"）；改用 `const X : Array = [...]` 字面量（Dictionary/Array 字面量 const 可正常外部访问）。
- ℹ️ **`/data/` 已于 2026-09-09 取消忽略、随仓库提交**（旧记「被 gitignore 需先 bootstrap」已过时，clone 即可跑）：但仍是 `export_for_godot.py` 导出产物 —— **改生成器或原版解析后须重跑 `python scripts/bootstrap.py` 并把 data/ 一起提交**，否则数据漂移。新增数据文件仍须配套生成器脚本（`export_shops_json.py`）。
- ⚠️ **`scripts/_unpacked_mem.bin`（2MB 脱壳映像）也被 gitignore（:26）且没有生成器**：180 个 `*_ref.py` 全依赖它，换机器需手工拷贝，否则反向脚本全跑不了。另 `Godot_v4.7.1/`（:5）需自行下载。
- ℹ️ `Taikou2 Original/`（原版 245 条目）**已入版本库**，是 `data/` 唯一生成来源（README 旧记「仓库不打包」已过时）。

## 约定 / 环境
- 工程根=`project.godot`；四目录 `src/`·`scenes/`·`assets/`·`scripts/`。autoload=DisplayAdapter+GameData+GameState。覆盖层存 `GameState` 运行期变更，不回写 data/。
- 无头测试：`Godot_v4.7.1-stable_win64_console.exe --headless --script res://tools/_test_mX.gd`。反汇编用系统 Python3.12（capstone 5.0.7；托管 3.13 无）。
- ⚠️ **git 联网必须显式走代理**：本机（macOS）`git fetch/pull/push origin` 若不加代理会被透明拦截代理 `198.19.2.122:443` 掐断（"Connection closed"），即使 `HTTP_PROXY` 环境变量已设也读不到。可靠姿势：`git -c http.proxy=http://127.0.0.1:56509 <fetch|pull|push> origin`（端口随会话变，当前 56509；旧 Windows 环境曾用 7890/9120）。remote=`https://github.com/Zhaoxinak/Taikou-2`。
- 突破插 BREAKTHROUGHS 倒序（四段），续编号取 `grep -o '上一条（续[0-9]*）'` max+1。

## 数据细节指针（勿抄进本文件）
- 武将/城字段 → `GAME_DATA_SPEC.md` §1.2/§3.17（城表 `0x51eb88` 31B×200）。
- 晋升阈值 / 12 主命公式 → `src/core/game_state.gd`；自绘 UI 度量 → `src/ui/UiTheme.gd`。
