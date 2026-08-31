# 太阁立志传2 — 逆向 / 数值破解工程

> **模式**：源码级引擎重实现（Godot 复刻）所需的数据与玩法规格抽取。  
> **法律边界**：用户自有合法拷贝、仅本地单机；仓库**不打包**原版素材。原版文件在 `Taikou2 Original/`。  
> **当前策略（2026-08-25 起）**：停 UI / 像素 / 字体；只做 **数值 + 玩法** → 写入规格文档。

---

## 文档怎么读（权威链）

| 顺序 | 文件 | 用途 |
|------|------|------|
| 1 | **本 README** | 入口、目录约定、待破速查 |
| 2 | [`BREAKTHROUGHS.md`](BREAKTHROUGHS.md) | 突破时间线（倒序）；新结论先写这里 |
| 3 | [`GAME_DATA_SPEC.md`](GAME_DATA_SPEC.md) | **数值/玩法权威规格**（复刻用） |
| 4 | [`BATTLE_SPEC.md`](BATTLE_SPEC.md) | 合战专篇（HJMAPDAT / per-tick 伤害） |
| 5 | [`SNDATA_SPEC.md`](SNDATA_SPEC.md) | SNDATA / SAVEDATA 容器与 XOR 流 |
| 6 | [`NPK_SPEC.md`](NPK_SPEC.md) | NPK 图像格式（UI 暂停，格式已闭） |

会话索引 / 方法论硬规则：`.workbuddy/memory/MEMORY.md`  
历史过时文档：[`docs/archive/`](docs/archive/README.md)（勿当权威）

---

## 目录约定

| 路径 | 用途 |
|------|------|
| `Taikou2 Original/` | 原版 111 文件（含 `TAIK2W95.exe`、SNDATA、BSDATA…） |
| `scripts/` | **现行**工具、`*_ref.py` 自检、JSON 产物、`_unpacked_mem.bin` |
| `scripts/_scratch/` | 一次性探针/旧实验脚本（可删可复跑，非接口） |
| `scripts/_probe/` 等 | 解码输出目录（gitignore，可再生） |
| `docs/archive/` | 归档旧文档 |
| `scenes/` / `project.godot` | Godot 壳（UI 工作暂停） |

---

## 逆向硬规则（摘要）

- 映像：`scripts/_unpacked_mem.bin`（2MB，base `0x400000`，平坦映射 `off = va - 0x400000`）
- **禁止猜表形状，必须穷举**；数据验证须读原始 DAT（勿只信 JSON 转储）
- 断言「静态不可见」前先做字节级 xref 找 WRITE 点
- 字段扫描必用 `scripts/_ins_index.py`（jmp 续体 / call 后 caller-saved 失效）
- 突破即：插 `BREAKTHROUGHS.md` dated 条目（四段）+ 同步 `GAME_DATA_SPEC.md` + 打勾

---

## 已破 / 待破（速查）

细节与地址以 `GAME_DATA_SPEC.md` + `BREAKTHROUGHS.md` 为准。摘要见 `MEMORY.md`。

**已破大块**：LS11/MSGX/GRP/IDX/KOS/BSDATA/城表/49 国政治表/物品表/合战公式/单挑/官位/会议任务/事件 id 派发/外交 handler 跳表…

**当前优先待破**：

1. 外交关系值变更公式 / 成功率（`0x525ea4` 下游、`0x5179b8+0x0b..0x0d`）
2. 事件系统剩余 handler 语义 + CONDITION 谓词表
3. 物品池绑定 / 流尾 3791B / 评价词 8↔10（需 emu）
4. section A 命名；单挑体力初值；时间月日定序

---

## 常用命令

```powershell
# —— 工程健康检查（续94 新增，先跑这两个）——
cd "F:\Games\Taikou 2\scripts"
python _run_all_selfchecks.py    # 批量跑全部 31 个 *_ref.py → 应 31/31 PASS
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
