# 太阁立志传2 — 项目记忆（索引）

> 只留**跨会话必需**的边界/防重踩坑/当前状态；数值细节查权威文档。
> 文档链：`README.md`→`docs/INDEX.md`→`docs/specs/GAME_DATA_SPEC.md`(数据权威)+`docs/re/BREAKTHROUGHS.md`+`docs/replication/`(★施工图/进度表)。
> ⚠️ `scripts/` 不移动（180 个 `*_ref.py` 非递归 glob）。

## 边界与当前阶段
- Godot 4.7.1 自写复刻；原版 `<工程>/Taikou2 Original/`（149 文件，不打包）。画面 **HD-2D**（3D+高清像素+后处理；像素破解豁免）。
- 非图像逆向 100% 收口。Godot **M0–M5 完成**（M5=職位晋升）+ **12 主命精确 delta（续254）**+ **M6/HD-5 自绘 UI 完成**（标题/主角选择/状态画面全改自绘，0 处硬编码字号、0 原生 Button/Label）+ **音效 39 已接入**（`AudioManager.play_sfx(id)` 对齐原版数字 id，`UiButton` 点击联动）+ **M7 事件链(S15) 已收口** + **M7 单挑(duel) 已收口**（`DuelSim`+`GameState.run_duel`+`_test_duel` 全过）+ **M7 事件文本渲染(event_text) 已收口**（`src/core/event_text.gd` 10 bit MSGX 叙事 + `%s`→主角名 + `GameState.render_event_text/render_resolved_events` + `_test_event_text` 全过）+ **M7 店铺/商业核心(shop) 已收口**（`src/core/shop.gd` 30 记录 + 入店分发 + favor 饱和 + 买药÷50；设施内交互流程与闇商人事件流留待后续）+ **M7 外交(diplomacy) 已收口**（`src/core/diplomacy.gd` 1176B 国関係マトリクス + 外交/主从位域 + 有向 2↔3 镜像 + 筛选/变更点 + 使者功勋；AI 主动外交与 UI 层留待后续）。+ **HD-3 光照+天气联动已接线完成**（新增 `src/render/WeatherFX.gd` 雨/雪 `GPUParticles3D`，分 CPU 安全层 `needs_particles/build_material/build_draw_mesh` 与运行时 `make_particles`；`battle_screen.gd` 加 `@export weather` + `_setup_environment`/`_apply_weather_now`/`set_weather`，4K 自动 `downgrade_for_4k`；`tools/_test_hd3.gd` 43 项**待实跑**）。下阶段：HD-6 视觉回归+4K 基准（卡真实美术）、BGM（卡 MIDI/CD 素材）、SHOP 剩余设施（闇商人事件流 0x460890 + 品茶/铁炮打工/试合/忍里修业/30日修行/学做生意，**无逆向证据**）。**已完成**：事件解释器纯逻辑核心(`src/core/event_sys.gd`：派发注册表18id→49handler + 条件求值0x4e82c0/0x4e7e10 + 每tick状态机0x44d950；效果handler主体/完整vtable/NPC名表 待接线，类比SHOP设施)。**已完成**：经济/物价纯逻辑核心(`src/core/economy.gd`：1:1 移植 `economy_ref.py` 49/49 —— 月度城产0x4a5aa0/农商/商店买价×1.5/茶具/宝物/米市；填补 GameState 交易经济占位；0x513ea8 店面改价与 0x51e1f0 物品池种子已证伪非本模块职责)。**已完成**：大地图最小可玩空壳（方案B：`scenes/screens/world_screen.tscn`+`src/ui/world_screen.gd`+`src/core/world_map.gd`，状态画面「外出」→大地图，方向键/WASD 移动、Enter 进城、城下町占位 overlay；坐标 `scripts/gen_castle_map.py` 按国聚类生成 `data/castle_map.json` **非原版固定坐标（诚实未接）**；HD-2D 美术/城下町设施/主命/剧情 待 HD-6 与后续）。**已完成**：AI 主动外交(续104)、素材规格、HD-3、SHOP 四设施流程(续243：画师/医师/教会/南蛮)、**天气/季节判定逻辑**（`src/core/weather.gd` WeatherState 1:1 移植 weather_ref：0晴/1曇/2雨/3雪+wet、season_of=(月//3)&3、tick_simple/region、4 概率表对映像自校验、gun 降水惩罚×2/3；GameState `weather` 每月 7 tick + `get_weather_state()`；`_test_weather.gd` 51 项期望值 Python 镜像推导。⚠️雪国地域走 tick_region 需国表气候字节 0x519548+国*5+1 未导出→暂简版；battle_sim 无兵种 kind 概念 gun 惩罚未接）。git push 走 `127.0.0.1:7890` 代理可用（9120 已死）。

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
| 手动 position + Container 混用（status_screen 旧版） | ❌ 会导致子控件尺寸/位置冲突，按钮被挤出可视区或接收不到点击 → 改为**单一 VBoxContainer 主布局** + `custom_minimum_size`/`size_flags_*`，避免手动 position 与 Container 布局混用 |
| Python 式 `d.get(x) or 默认` | ❌ GDScript `or` 返回 **bool**：`"三户" or ""` = true → `str()` 后成 "true"。判空用显式 `var v: Variant = d.get(x); str(v) if v != null else ""` |
| JSON 直方图字段当 Array | ❌ `battles.json` 的 `unit_nibble_hist`/`terrain_type_hist` 是 **dict**；模型声明错类型会在 load_from_dict 中断、后续字段全空 |
| `env.tonemapper = TONE_MAPPER_*` | ❌ Godot 4.x 属性名 **`tonemap_mode`**；`glow_mipmap_bias` 4.7 已移除（赋值抛错→整个 build_environment 返回 Nil） |

## GDScript / 无头坑（每次写 GDScript 前看）
- `JSON.parse_string` 数字全 float→建 id 索引须 `int(rec["id"])`；改 GameData 缓存 Array/Dict 须 `.duplicate()`；除法 `//`。
- 无头 `--script`：autoload 未进树→`process_frame.connect(_run, CONNECT_ONE_SHOT)`；末尾 `quit(0)`（否则 rc=1 噪声）。**不建全局类缓存→禁用 `class_name`，跨文件一律 `preload`**（也勿 `class_name GameState`，与 autoload 冲突）。
- 🔴 **本机 Godot 二进制**：`/Users/ts/Downloads/Taikou 2/Godot/Godot.app/Contents/MacOS/Godot`（4.7.1.stable，与项目同版；另有 `Godot_mono.app`）。macOS **无 `timeout` 命令**→用 Bash 工具 timeout 参数。
- ✅ **2026-09-09 更正：`--headless --script` 其实可用**（旧记「主循环失效/恒卡死」是**误判**）。真因是两条：① 测试脚本自身有 Parse/Compile Error 时 Godot **静默回退去跑主场景**→主循环永不退出，看起来就是「卡死」；② 测试脚本漏写 `process_frame.connect(_run)` 触发→SceneTree 空转。⇒ **实跑 `_test_*.gd` 才是首选验证**，不要只信 Python 镜像（本次靠实跑抓出 `economy.gd` 的 `_imul_sar` 掩码 bug，Python 镜像 49/49 却完全没发现）。启动期 13 条 `Unexpected NUL character` 为干扰项（实测文件 0 NUL；zsh 下 `grep $'\x00'` 是**假阳性**）。
- 🔴 **`--check-only` 有盲区**：只解析被场景/autoload 引用到的脚本。仅被测试引用的模块（如 `council.gd`）有语法错误时，项目级 `--check-only` 照样报「零错误」。⇒ 用 `tools/_test_all_compile.gd`（递归 preload `res://src` 全部 .gd）补盲区，44/44 通过才算干净。
- ⚠️ **`TaskStop` 杀不掉 Godot 真进程**→必须 `pkill -f "Godot.app/Contents/MacOS/Godot"` 并用 `pgrep` 复核；残留进程会占锁拖慢/卡死后续运行。
- ⚠️ **新增带 `class_name` 的文件不会自动进全局类缓存**→其他脚本直接写 `X.Y` 会 Parse Error "Identifier not declared"。**跨文件引用新文件一律 `const X = preload("res://...")`，别依赖 class_name 全局缓存**。
- ℹ️ **`--script` 卡死前仍会打印 Parse Error** → 即使跑不完 `_run`，也可用它验证「新脚本是否编译通过」（看有无 Parse Error / Compile Error 即可）。
- 🔧 **反汇编**：本机无 capstone 时装的隔离 venv `/Users/ts/.workbuddy/binaries/python/envs/default/bin/pip install capstone`（5.0.7）。用法 `Cs(CS_ARCH_X86,CS_MODE_32).disasm(data[va-0x400000:], va)`，`_unpacked_mem.bin`（2MB，**gitignored 无生成器**，换机器需手工拷）。
- ⚠️ **魔数除法别混**：`0x51eb851f`+sar3 = **/25**（sar4 = /50）；`0x66666667`+sar3 = **/20**（mission_level 也用它，除数 20 非 10）。
- ✅ **验证优先级（2026-09-09 订正）**：① 实跑 `--headless --script`（最可信）→ ② `tools/_test_all_compile.gd`（补 `--check-only` 盲区）→ ③ Python 镜像（**仅当①②不可用时**，它与 GDScript 并非同源，会漏掉语言差异类 bug）。批量跑批用 `zsh tools/run_all_tests.sh`（每测试 15s 上限，汇总到 `tests_report.txt`）。
- ⚠️ **GDScript 整数/语法坑（本次实跑逐个踩到）**：① `1 << 64` 移位量按 6 位取模变成 `1 << 0 = 1`，写 64 位掩码会退化成 0 —— GDScript int 本就 64 位有符号且乘法天然回绕，**不要再手动掩码**；② **无 `for...else`**（Python 遗留）；③ 函数内**不能嵌套 `func`**，且 lambda 捕获局部变量**按值**（计数须用成员/Array）；④ `var X := PreloadedScript` 无法推断类型 → 写 `var X = PreloadedScript`；⑤ `while true` 不被认定为「所有路径返回」，需补不可达 `return`；⑥ 不支持命名参数 `f(c=10)`；⑦ Array 不可 `* int`；⑧ `Dictionary.get()` 返回 Variant，`var s: String = d.get(...)` 会报 Nil→String，须 `str(...)` 包裹；⑨ RefCounted 对象做的 `Callable` 若无人持有会被释放 → 报 `null::pull`，须缓存实例。
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
