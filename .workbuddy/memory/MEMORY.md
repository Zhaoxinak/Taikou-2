# 太阁立志传2 — 项目记忆（索引）
> 只留跨会话必需的边界/防重踩坑/当前状态；数值细节查权威文档。
> 链：README→docs/INDEX→GAME_DATA_SPEC(数据权威)+BREAKTHROUGHS+docs/replication/(进度表).
> ⚠️ scripts/ 不移动（180 个 *_ref.py 非递归 glob）。

## 边界与阶段
- Godot 4.7.1 自写复刻；原版 Taikou2 Original/ 已入版本库（data/ 唯一来源）。画面走原版素材+占位图（单位 spriteD 已放弃）。
- 已完成（Godot）：M0–M5(職位晋升) + 12 主命精确 delta + M6/自绘 UI(0 硬编码字号) + 音效39 + M7事件链S15 + M7单挑duel + M7事件文本event_text + M7店铺shop + M7外交diplomacy + 光照天气光照天气 + 天气/季节判定(weather 51项) + 经济economy(49/49) + 大地图world_map空壳 + AI主动外交 + **NPC名表导出(data/npc_names.json → GameData.get_npc_name，special 1000..1339 / generic 3000..3278)** + 全量GDScript测试实跑**30/30 套件 0 失败**(_test_all_compile 45/0)。
- 事件解释器：纯逻辑核心(派发/条件求值/每tick状态机) + **效果执行层 event_effects.gd**（7 真实事件 id=0,1,9,10,13,14,15 的 MSGX 叙事发射 + 月度 poll_events 接线 advance_month + 状态画面事件流弹窗）已实跑通过(_test_event_effects 23/23；_test_m3_ui 23/23)。**诚实未接**：id0/1 概率分支+RNG、id13/14 触发后叙事文本、id9 条件全局 0x49f430、0x4d0ca0 月度 applier 自动触发(仅 force_event 显式驱动)、完整 C++ vtable 仅 18 id 静态自断言（~~NPC 名表未导出~~ ✅已闭合）。
- 遗留(卡外因)：视觉回归 仅剩像素级截图比对+GPU FPS 基准(须 GUI 实跑；无头可测部分已 21/21)；BGM 已接入 34 首 MP3（**未逆**：场景→BGM 槽位调度表走虚表，需 emu 钩 CdPlay@0x401310 的 caller）；SHOP剩余设施(闇商人/品茶/铁炮打工/试合/忍里修业/30日修行/学做生意,无逆向证据)。
- **BGM 权威（续255）**：入口 = `CdPlay` **@0x401310**（4 参 track/flag/from/to，`add esp,0x10`）；旧记「CdPlayTrack 0x4013b0」是其**内部 MCI 指令块**（全镜像 0 调用点）。轨 0/越界⇒停止；同轨重播跳过；当前轨 = `byte[0x501294]`；槽位→轨号 **+2**(0x498eb8)；门控 `word[0x50b8f0]==4`。**轨数 34 权威证据** = `0x498f45 push 0x22` + `ecx=0x5256c4`(BGM 对象)（紧邻 `push 0x27`+`ecx=0x5256c8`=音效）。MP3 无 ID3，走 `FileAccess`→`AudioStreamMP3.data`（绕 .import）。

## 高频纠偏（别再踩）
| 旧记 | 正确 |
|---|---|
| bsdata.json 的 fields 直接用 | ❌ 用 export_for_godot.py |
| 技能名 算用/军学 | 实为 算术/兵法 |
| 城表 92 条 | 200 条 0..199 |
| 職位名 足轻组头… | 正版=浪人/步兵头/队长/侍大将/部将/家老/宿老/大名/城主 |
| 城主(8)是職位字段 | 城主=城表派生 word[+0x0a]；3-bit職位仅0..7 |
| 贩卖/购买军粮 handler 直写軍糧/米 | 只算仕事成果値 byte[ent+0x17]，转移走纳结算 |
| 外交目标国筛选按外交関係 | 按主从関係(0x4c4270) |
| mission_level 除数 10 | 实为 20 |
| 盲信 diplomacy_spec.json 的 asm 三角索引 | 正解 i*49-i*(i+1)/2+(j-i-1) |
| 地形材质 11 种 | 全 38 战实测 16 种（?8~?C 名称 JSON 侧硬编码，推定 河原/砂州/湿地/葦原/城濠）|
| 手动 position + Container 混用 | 单一 VBoxContainer 主布局 + custom_minimum_size/size_flags_* |
| Python 式 d.get(x) or 默认 | GDScript or 返回 bool；显式判 null |
| JSON 直方图字段当 Array | battles.json 的 unit_nibble_hist/terrain_type_hist 是 dict |
| env.tonemapper | Godot 4.x = tonemap_mode；dof_* 全部不存在（4.7.1 移除）|
| 二进制名表只查「长度+无\ufffd」 | ❌ 名表后紧接**其它数据结构**（调色板/查找表/指针区），其字节在 gb18030 下**恰好解码成伪名**（踗/挢/䎬/吏/E/>H/浇B）。必须三层过滤见下 |

## 二进制名表导出三层过滤（stride-N 内联 C 串，必用）
1. **记录内须含 `0x00`**（N 字节单元至少 1 个 0 才是真 C 串；全非零=溢出串/打包数据）。
2. **`is_name`**：1..N-1 字；禁控制符/**PUA(U+E000~U+F8FF)**/`\ufffd`；**禁 Latin 字母**（原版纯 CJK/假名/全角 → 杀 `浇B`/`>H`/`R`）；**须含 ≥1** CJK统一表意/扩展A/假名/全角（杀纯数字符号 `0014`/`2`）。
3. **孤立滤除**：`[id-5,id+5]` 窗口**≥3 有效邻居**（真名块密集，数据区仅零星伪名 → 孤立者丢）。⚠️ 窗口别太严：±2/阈值3 会误杀稀疏真名（如 `介绍信`±2 仅 2 个有效），±5/≥3 才保留。
宁可缺名（`NPC{id}` 回退）也不导入伪名。

## GDScript/无头坑
- JSON.parse_string 数字全 float→建 id 索引须 int(rec["id"])；改 GameData 缓存须 .duplicate()；除法 //。
- 无头 --script：autoload 未进树→process_frame.connect(_run, CONNECT_ONE_SHOT)；末尾 quit(0)。禁用 class_name，跨文件一律 preload。
- 🔴 --headless --script 实跑可用（旧记「主循环失效」是误判：真因①测试脚本 Parse/Compile Error→静默回退主场景卡死；②漏写 process_frame.connect）。实跑首选验证，Python 镜像仅补盲。
- 🔴 --check-only 有盲区（仅解析被场景/autoload 引用脚本）→ 用 tools/_test_all_compile.gd（递归 preload res://src 全部 .gd）补盲区。
- GDScript 整数坑：1<<64 移位量按 6 位取模退化；无 for...else；函数内不能嵌套 func；lambda 捕获按值；while true 需补不可达 return；Array 不可 *int；Dictionary.get() 返回 Variant 须 str() 包裹；RefCounted 的 Callable 须缓存实例防释放。
- 魔数除法：0x51eb851f+sar3=/25；0x66666667+sar3=/20(mission_level)。
- **子 CanvasItem 默认绘制在父 _draw() 之上**。若父 Control 的 _draw() 是主要可见内容（如 world_screen 画地图点/主角 marker），而 _ready() 里 add_child(全屏 ColorRect) 当背景 → bg 会**盖住**整个 _draw 输出，玩家看到全黑屏。修：bg.show_behind_parent = true（让 bg 绘在父 _draw 之下）。判定：UI 屏的可见内容是 child Controls（panel/label/button）且在 bg 之后 add_child 则天然安全（castle_town/status_screen）；唯一当父 _draw() 是主内容的屏才需注意。证据：world_screen bug d058ec0。
- 非 autoload 取 GameData：Engine.get_singleton 返回 null→依赖注入(autoload 侧 _ready 注入 或 测试 root.get_node("/root/GameData"))。
- 载 TTF：FontFile.load_dynamic_font(ProjectSettings.globalize_path(res://...))；不可用 ResourceLoader.load。
- const X: PackedByteArray=[...] 无法被外部 preload 引用 .X→用 const X: Array=[...]。
- data/ 已随仓库提交（export_for_godot.py 产物）；改生成器须重跑 python scripts/bootstrap.py 并提交 data/。
- scripts/_unpacked_mem.bin(2MB) 与 Godot_v4.7.1/ 被 gitignore，无生成器，换机器需手工拷。

## 约定/环境
- 工程根=project.godot；四目录 src/·scenes/·assets/·scripts/。autoload=DisplayAdapter+GameData+GameState。
- 无头测试：Godot_v4.7.1-stable_win64_console.exe --headless --script res://tools/_test_mX.gd（Windows；macOS 用 Godot.app）。反汇编用系统 Python3.12(capstone 5.0.7)。
- git 联网：remote = `git@github.com:Zhaoxinak/Taikou-2.git`（**SSH**，非 HTTPS）。认证走 `~/.ssh/id_ed25519_taikou` + `~/.ssh/config` 的 `ProxyCommand "connect.exe" -H 127.0.0.1:7890`，**push 已实测成功（2026-09-10，e57333e → origin/main）**。无需 GCM/HTTPS 凭据（旧记「GCM 无凭据」仅适用于 HTTPS remote，本工程 remote 是 SSH，不适用）。git config 另有 `http.proxy=https.proxy=http://127.0.0.1:7890`（仅影响 https 操作，SSH 走 ssh config 的 ProxyCommand）。
- 突破插 BREAKTHROUGHS 倒序；续编号取 grep '上一条（续[0-9]*）' max+1。
