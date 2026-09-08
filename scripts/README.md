# scripts/ — 脚本导航（分类地图）

> **⚠️ 本目录文件位置刻意不移动。** 180 个 `*_ref.py` 自测由 `scripts/_run_all_selfchecks.py` 用 **非递归** `glob("*_ref.py")` 扫顶层；`emu_harness` / `real_assets` 等被大量 ref 直接 `import`。物理移动会破坏自测套件。分类靠**本地图**，不动文件。

## 一、自测 / 验收（复刻验证依据）★`*_ref.py`
- 数量：**180** 个，全在 `scripts/` 顶层。
- 作用：每个逆向结论都有对应 `*_ref.py` 自测，**全 PASS = 数据层正确**，复刻前先跑 `_run_all_selfchecks.py`（约 12 分钟，macOS 无 `timeout` 勿加前缀）。
- 例：`diplomacy_ref.py` `battle_formula_ref.py` `s15_table_ref.py` `bsdata_format_ref.py` `kos_format_ref.py`。

## 二、框架（被 ref 依赖，勿改接口）
| 文件 | 角色 |
|---|---|
| `_unpack_exe.py` | 解包 EXE → `_unpacked_mem.bin`（2MB，base 0x400000） |
| `emu_harness.py` | Unicorn 2.1.4 单函数仿真桩 |
| `real_assets.py` | **资源/音效解码**（含 LS11 / KOS / MSGX / GRP 等真实解码器） |
| `emu_sndata_read.py` | SNDATA 容器读取 |
| `_lindis.py` | 现场反汇编核对（`<va> <nbytes>`） |
| `_ins_index.py` | 指令索引（字段扫描必用，避免 jmp 续体误判） |
| `_audit_progress.py` | 扫 `*_spec.json` 的 still_unknown → 未破清单 |
| `_run_all_selfchecks.py` | 批量跑全部 `*_ref.py` |

## 二之二、Godot 复刻导出器 ★
| 文件 | 角色 |
|---|---|
| `export_for_godot.py` | **原版数据 → `data/*.json`**（按续200 权威 59B 布局重解析 BSDATA，GBK→UTF-8 + 外字，内置自检）。工程根运行：`python scripts/export_for_godot.py [--scene 1\|2] [--out ./data]` |

> 🔴 它存在的理由：`scripts/bsdata.json` 的 `fields` 已被续200 证伪，不能直接当权威数据源。详见 `docs/replication/Godot复刻实施方案.md §3.2`。

## 三、逆向推导脚本（过程留档，非接口）
- 顶层其余 `_*.py`（约 460 个，如 `_fdis.py` `_dumpfn.py` `_emu_*`）：一次性探针/推导过程，**勿在新代码里 import**，随时可被 `_scratch/` 化。
- 顶层独立 `*.py`（非 ref 非框架）：杂项工具。

## 四、子目录
| 目录 | 内容 | 状态 |
|---|---|---|
| `_scratch/` | 一次性探针/旧实验脚本（**283** 个，gitignore，非接口） | 勿依赖 |
| `_草稿/` | 早期草稿脚本（**21** 个） | 勿依赖 |
| `_decoded_kos/` | **39** 个已解码音效 WAV（**权威**，原 `kos_wav/` 已删） | 产物可用 |
| `_decoded_grp/` | **13** 个 GRP 解码 PNG（2026-09-08 实测；图像豁免，产物可直接用） | 产物可用 |

## 五、根目录其它产物（勿手改）
- `scripts/*.txt`（**91** 个）：探测输出（可再生，gitignore 部分）。
- `*.json`（如 `bsdata_format.json` `battle_units_spec.json` `msgx_all_texts.json`）：ref 生成的产物，`_run_all_selfchecks.py` 跑完会再生，`git checkout --` 还原即可。
- `_unpacked_mem.bin`：解包映像（large，gitignore）。

## 六、常用命令
```powershell
cd "工程根"
python scripts/_run_all_selfchecks.py     # 180 自测 → 应 180 PASS / 0 FAIL
python scripts/_audit_progress.py          # 未破项清单
cd scripts
python _fdis.py 0x4c41e0                   # 反汇编单函数
python _lindis.py 0x4c41e0 0xc0            # 现场反汇编核对
```
