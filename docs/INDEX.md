# 文档总索引（太阁立志传2 逆向 / 复刻工程）

> 本仓库所有**文档**已分类到 `docs/` 下。本文件是**唯一地图**：下次接手或复刻，先看这里。
> 根目录 [`README.md`](../README.md) 是仓库大门（项目定性 / 命令速查）；**脚本**导航见 [`scripts/README.md`](../scripts/README.md)（脚本**不移动**，移动会破坏 180 个自测，详见该文）。

## 📁 目录结构

```
docs/
  INDEX.md            ← 本文件（总索引）
  specs/              ★ 复刻核心交付物：数据/玩法契约（权威）
    GAME_DATA_SPEC.md   数值/玩法权威规格（复刻照此实现）
    BATTLE_SPEC.md      合战专篇（HJMAPDAT / per-tick 伤害 / 计略）
    SNDATA_SPEC.md      SNDATA/SAVEDATA 容器与 XOR 流 / 段地图
    NPK_SPEC.md         NPK 图像格式（UI 暂停，格式已闭）
    破解状态清单.md     逐文件/逐块破解状态矩阵 + 审计 SOP
  re/                逆向过程留档（参考，非必需）
    BREAKTHROUGHS.md    突破时间线（倒序，新在上）；每个新结论先写这里
    HANDOFF.md          自包含交接文档（状态/方法论/环境坑/接手 SOP）
    _x92.md             续92 零散突破笔记
  replication/        怎么把规格变成 Godot
    复刻导航.md         数据资产地图 / 原版文件格式 / 关键几何 / 字段速查 / 避坑
```

## 🧭 按目标选读

| 你想做什么 | 读 |
|---|---|
| 整体了解 / 接手项目 | [`README.md`](../README.md) → [`re/HANDOFF.md`](re/HANDOFF.md) |
| 查某个数值/玩法的权威定义 | [`specs/GAME_DATA_SPEC.md`](specs/GAME_DATA_SPEC.md) |
| 查合战（伤害/地形/计略） | [`specs/BATTLE_SPEC.md`](specs/BATTLE_SPEC.md) |
| 查剧本/存档容器与 XOR 流 | [`specs/SNDATA_SPEC.md`](specs/SNDATA_SPEC.md) |
| 查图像格式（NPK/LZW） | [`specs/NPK_SPEC.md`](specs/NPK_SPEC.md) |
| 查「某块破没破」 | [`specs/破解状态清单.md`](specs/破解状态清单.md) |
| 看突破历史/时间线 | [`re/BREAKTHROUGHS.md`](re/BREAKTHROUGHS.md) |
| **开始写复刻代码** | [`replication/复刻导航.md`](replication/复刻导航.md) |
| 找某个逆向脚本/自测 | [`scripts/README.md`](../scripts/README.md) |

## 🔑 硬规则速记
- 新结论 → 先插 `re/BREAKTHROUGHS.md` 倒序条目（四段），再同步 `specs/GAME_DATA_SPEC.md`。
- 数据取值以 `specs/` 为准；仍在 `❓/🔶` 者均为 emu 运行期语义增强，**非结构敞口、不阻塞复刻**。
- 非图像已 100% 收口（2026-09-08 续253 结案）；图像按用户明令豁免（GRP/PK8/纯像素 LZW）。

## 📂 工程根其余关键项
- `scripts/`：现行工具 + 180 个 `*_ref.py` 自测 + 解码产物（详见 `scripts/README.md`）。
- `project.godot` + `fonts/`：Godot 4.7 复刻工程（已暂停，留作下次复刻壳）。
- `Taikou2 Original/`：原版 149 文件，**仓库不打包**。
- `.workbuddy/memory/`：会话索引与每日日志（方法论硬规则在 `MEMORY.md`）。
