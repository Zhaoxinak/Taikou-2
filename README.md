# 太阁立志传2 — 逆向 / 数值破解工程

> **📂 文档已分类整理到 [`docs/INDEX.md`](docs/INDEX.md)**（总索引：规格 / 逆向留档 / 复刻入口）。本文件是仓库大门；详细数据契约在 `docs/specs/`，脚本导航在 [`scripts/README.md`](scripts/README.md)。

> **🤖 新 AI 接手？先读 [`docs/re/HANDOFF.md`](docs/re/HANDOFF.md)** —— 自包含交接文档（项目定性 / 当前状态 / 方法论 / 残留敞口 / 环境坑 / 接手 SOP），读完即可独立上手。
>
> **🔨 要开始写复刻代码？读 [`docs/replication/复刻导航.md`](docs/replication/复刻导航.md)** —— 数据资产地图 / 原版文件格式 / 关键几何 / 字段速查 / 避坑清单，只讲「数据在哪、怎么取」。

> **模式**：源码级引擎重实现（Godot 复刻）所需的数据与玩法规格抽取。  
> **法律边界**：用户自有合法拷贝、仅本地单机；仓库**不打包**原版素材。原版文件在 `Taikou2 Original/`。  
> **当前策略（2026-08-25 起）**：停 UI / 像素 / 字体；只做 **数值 + 玩法** → 写入规格文档。

---

## 文档怎么读（权威链）

| 顺序 | 文件 | 用途 |
|------|------|------|
| 1 | **本 README** | 入口、目录约定、待破速查 |
| 2 | [`docs/re/BREAKTHROUGHS.md`](docs/re/BREAKTHROUGHS.md) | 突破时间线（倒序）；新结论先写这里 |
| 3 | [`docs/specs/GAME_DATA_SPEC.md`](docs/specs/GAME_DATA_SPEC.md) | **数值/玩法权威规格**（复刻用） |
| 4 | [`docs/specs/BATTLE_SPEC.md`](docs/specs/BATTLE_SPEC.md) | 合战专篇（HJMAPDAT / per-tick 伤害） |
| 5 | [`docs/specs/SNDATA_SPEC.md`](docs/specs/SNDATA_SPEC.md) | SNDATA / SAVEDATA 容器与 XOR 流 |
| 6 | [`docs/specs/NPK_SPEC.md`](docs/specs/NPK_SPEC.md) | NPK 图像格式（UI 暂停，格式已闭） |
| — | [`docs/replication/复刻导航.md`](docs/replication/复刻导航.md) | **复刻专用入口**（数据在哪 / 字段速查 / 避坑） |

会话索引 / 方法论硬规则：`.workbuddy/memory/MEMORY.md`  

---

## 目录约定

| 路径 | 用途 |
|------|------|
| `docs/` | **文档分类根**：`INDEX.md`(总索引) / `specs/`(数据契约) / `re/`(逆向留档) / `replication/`(复刻入口) |
| `docs/specs/` | ★ 复刻核心：`GAME_DATA_SPEC` `BATTLE_SPEC` `SNDATA_SPEC` `NPK_SPEC` `破解状态清单` |
| `docs/re/` | 逆向留档：`BREAKTHROUGHS`(突破时间线) `HANDOFF`(交接) `_x92` |
| `docs/replication/` | `复刻导航.md`：数据资产地图 / 原版格式 / 关键几何 / 字段速查 |
| `Taikou2 Original/` | 原版 149 文件（含 `TAIK2W95.exe`、SNDATA、BSDATA…），**仓库不打包** |
| `scripts/` | **现行**工具、180 个 `*_ref.py` 自检、JSON 产物、`_unpacked_mem.bin`（分类见 `scripts/README.md`） |
| `scripts/_scratch/` | 一次性探针/旧实验脚本（283 项，gitignore，非接口） |
| `scripts/_草稿/` | 早期草稿脚本（21 项） |
| `scripts/_decoded_kos/` | 39 个已解码音效 WAV（**权威**） |
| `scripts/_decoded_grp/` | 31 个 GRP 解码 PNG（图像豁免，但产物可直接用） |
| `project.godot` + `fonts/` | Godot 4.7.1 复刻工程（已暂停，留作下次复刻壳；见 MEMORY 边界节） |

---

## 逆向硬规则（摘要）

- 映像：`scripts/_unpacked_mem.bin`（2MB，base `0x400000`，平坦映射 `off = va - 0x400000`）
- **禁止猜表形状，必须穷举**；数据验证须读原始 DAT（勿只信 JSON 转储）
- 断言「静态不可见」前先做字节级 xref 找 WRITE 点
- 字段扫描必用 `scripts/_ins_index.py`（jmp 续体 / call 后 caller-saved 失效）
- 突破即：插 `docs/re/BREAKTHROUGHS.md` dated 条目（四段）+ 同步 `docs/specs/GAME_DATA_SPEC.md` + 打勾

---

## 已破 / 待破（速查）

细节与地址以 `docs/specs/GAME_DATA_SPEC.md` + `docs/re/BREAKTHROUGHS.md` 为准。摘要见 `MEMORY.md`。

**已破大块**：LS11/MSGX/GRP/IDX/KOS/BSDATA/城表/49 国政治表/物品表/合战公式/单挑/官位/会议任务/事件 id 派发/外交 handler 跳表…

~~**当前优先待破**~~ → ✅ **全部已闭（2026-09-08，续253 结案）**：

1. ~~外交关系值变更公式 / 成功率~~ → 关系矩阵写点已破（续184/185 双写伴生）；剩余为**设计层参数**，复刻可自定
2. ~~事件系统剩余 handler 语义 + CONDITION 谓词表~~ → S15 段C「事件 id×slot×val」全映射（续212/220），MSGX 锚点全定位（续227）
3. ~~物品池绑定 / 流尾 3791B / 评价词 8↔10~~ → 流尾 = S12..S17 六段（续99）；**评价词档位阈值已闭**（续253：`val<lo→0 / lo≤val<hi→1 / val≥hi→2`）
4. ~~section A 命名；单挑体力初值~~ → section A **结论性负结果**（=空间网格，无日文主名表，续250）；实体 `+0x20/+0x21`=最大/现在体力（续241）

> **非图像已 100% 收口，零真敞口。** SPEC 文档内现存 🔶/❓ **全部**为「emu 运行期语义增强」（某 bit 玩法命名、delta 精确值），
> **非结构敞口、不阻塞复刻**——复刻按结构取字段、语义按设计自定即可。图像类按用户明令豁免。

---

## 常用命令

```powershell
# —— 工程健康检查（续94 新增，先跑这两个）——
cd "F:\Games\Taikou 2\scripts"
python _run_all_selfchecks.py    # 批量跑全部 180 个 *_ref.py → 应 180 PASS / 0 FAIL（约 12 分钟）
                                 # ⚠️ macOS 无 `timeout` 命令，勿加前缀（会直接空跑）
                                 # ⚠️ 跑完会再生 bsdata_format.json / bsdata_tail_fields.json → git checkout -- 还原
python _audit_progress.py        # 扫全部 *_spec.json 的 still_unknown → 未破项清单

# —— 单个参考实现 ——
# ⚠️ cwd 不统一：多数 ref 用 'scripts/_unpacked_mem.bin'（须 cwd=工程根），
#    少数用裸 '_unpacked_mem.bin'（须 cwd=scripts/）。跑单个若报
#    FileNotFoundError，换另一个目录重试即可（_run_all_selfchecks.py 已自动兜住）。
cd "F:\Games\Taikou 2"
python scripts\diplomacy_ref.py
python scripts\event_id_dispatch_ref.py
python scripts\item_table_ref.py

# —— 反汇编单函数 ——
cd "F:\Games\Taikou 2\scripts"
python _fdis.py 0x4c41e0
python _dumpfn.py 0x4c41e0
```

> **MSGX 文本查询**：权威索引是 `scripts/msgx_all_texts.json`（6211 条，键=全局 id
> `file_base + index`）。**勿用** `scripts/_probe/msgx/all_messages.txt` —— 它在可再生
> gitignore 目录内、常不存在，且仅覆盖 3091 条（续94 已把 `council_ref`/`duel_ref` 切到权威索引）。
