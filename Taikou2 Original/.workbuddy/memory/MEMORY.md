# 项目长期笔记 — 太阁立志传2（Win95）逆向 / 重制

## 仓库布局（重要，先看这里）

工作区根目录 `F:\Games\Taikou 2\Taikou2 Original\` 只是**冰山一角**。
它外面还有一层真正的工程根 `F:\Games\Taikou 2\`：
Godot 4.7.1 复刻工程 + 已完成的逆向成果（`scripts/` 180 个 `*_ref.py` 自测、
`docs/specs/` 规格、`data/*.json` 导出产物）+
 `_unpacked_mem.bin`（2MB 脱壳映像，180 个 ref 全依赖它）。

**教训（2026-10-03 踩过）**：曾因为只在子目录 `Taikou2 Original/` 里翻，
得出"LS11 未破、资源层不能做 mod"的错误结论，
其实 `F:\Games\Taikou 2\scripts\real_assets.py` 里早就有全套解码器。
→ **动手前先读工程根 README.md 和 docs/INDEX.md，别在子目录里下全域结论。**

## 用户偏好

- 偏好**结构化表格**汇总变更，要求技术深度（十六进制地址、反汇编片段、明细表）
- 以「破」为单位推进：每轮必须闭合证据链 + 带 assertion 的参考实现 + 更新文档
- 范围明确：**只做数值 / 玩法 / 数据**，不做像素 / UI / 字体（2026-08-25 起）
- Git：AI 可执行 commit / pull / rebase，**push 前必须用户确认**

## Git 仓库约定（2026-10-07 用户拍板）

- 仓库根 `F:\Games\Taikou 2\`（**不是**子目录），远端 `git@github.com:Zhaoxinak/Taikou-2.git`，分支 `main`
- **入库**：`.rev/` 源码/文档/配置、`.workbuddy/memory/`、已跟踪的游戏数据改动（BSDATA/AVI/bat）、
  根目录 MOD exe 产物（`TAIK2W95_big*.exe` / `_clean` / `_family` / `_zoom`）
- **不入库**（已写进 `.gitignore`）：`MP3/` 34 个 BGM wav（约 400MB，版权+体积）、
  `taielizhit2.rar` + `taielizhit2/`（第三方修改器）、`*.bak` / `*.orig`、`OPENNING_long.bak`(36MB)、
  `.rev/_archive/` 历史 exe、`shots*` / `variants/` 截图、`crash_mem.bin` / `clean_dump.bin`、
  `WAVE.TMP`、`TKMODSAVE_*.DAT`、`370)`
- **push 前必做**：`git ls-files --others --exclude-standard -z` 递归统计真实体积再定范围 ——
  `git status --short | wc -l` 会把目录算成一行，严重低估（这次 152 行 → 实际 492MB）

## 已闭的关键结论

- 非图像部分 100% 收口（2026-09-08，续253 结案）
  BSDATA / 城表 / 49 国政治 / 物品 / 合战公式 / 单挑 / 官位 / 会议 / 事件派发 / 外交矩阵
- **LS11 资源容器已双向打通**（2026-10-03）→ 工具在 `modkit/`，详见 `modkit/README.md`
  - 规格：256B 字典 + Elias gamma(n+2) 索引 + LZ77（back≤8191, len≤512）
  - **每段独立 pad 到字节**，TOC 每段 12B `[dec_len, offset, span(下一段)]`
  - 自检 66/66；实机验证游戏接受重打包文件
  - 硬约束：**等长替换**，产物只写 `modkit/output/`，不覆盖原版

## 孩子培养 MOD（M2/M3/M4/M5）常用地址

| 用途 | VA / 原语 |
|---|---|
| 选项对话框 | `0x47BED0(count, 串指针数组, flag,0,0)` cdecl 5 push + `add esp,0x14`；`ax`=序号，`0xffff`=取消；入口 `0x47BE00` 限 count 1..12 |
| 支付 | `0x44E350(amt)` → `0x4A35C0 sat_sub(word[0x51662E], amt)`；**不查余额**，调用方先自查；主角金钱 = `word[0x51662E]` |
| 推天数 | `0x4A0D50(hours,1)` **cdecl，调用方必须 `add esp,8`**；原生调用点一律 `push 1; push 0x18; call; add esp,8`（2026-10-07 记反过一次，症状是日期狂奔，见下） |
| 日期 | 月 `byte[0x5205F1]`、日 `byte[0x5205F2]`、年 `byte[0x5205F0]` |
| 年龄 | `0x49A5C0(ecx=实体)` → `eax`=虚岁；元服阈值 `AGE_PUKU=15` |
| 五维写手 | `0x4A2F80 + d*0x20`，`push 1`，内部 sat_add 封顶 0x64 |
| KID_TAB | 12B/条，字段布局见 `.rev/child_growth.py` 注释；CMD_RING 头 8B + 64×8B |

- **★ 本工程有两套串池格式，禁止互抄解码**（2026-10-07 踩过："培养后界面全乱了"）：
  | 池 | 格式 | 配套解码 | 谁在用 |
  |---|---|---|---|
  | `kid_panel.STRINGS` | `[len u8][GBK][NUL]` **紧凑无 pad** | `movzx ecx,[eax]; inc eax` | 详情面板（走指针数组 `KD_STRTAB`） |
  | `child_menu.MSG_STRINGS` | `[GBK][NUL][pad 到 MS_STR_ROW]` **无长度前缀** | `push -1`（cbString，GDI 找 NUL） | 反馈小框 + **原生对话框 `0x47BED0`** |
  第二套不能加长度前缀：`cost_arr` / `deny_*_ptr` 直接喂给原生对话框，它收的是 C 字符串指针。
  抄错解码的症状 = **汉字高字节(0xb4/0xd5)被当长度 ⇒ TextOut 一次画 180~213 字节 ⇒ 屏幕糊出 8 行串池**。
- **★ 居中一律 `(wx0 + wx1) / 2`**，不许写 `(wx0 + 框宽)/2`（后者只在 wx0==0 时才对）。
  2026-10-07 反馈小框三处都写成后者，文字整体偏左 200px 甩到框外，看起来像"框里是空的 + 标题在外面"。
- **★ 给越界守卫取上界要用真实数据规模**：孩子实体在**槽 463..476**、姓名表按槽直索引共 **654 行**
  （4578B / 7B）。守卫写 `0x40` 会让 `kd_msg` 直接 return ⇒ 反馈框永远不弹，症状是"什么都没发生"。
- **货币单位**：`word[0x51662E]` 是**文**（UI 显示「0贯200文」，1 贯 = 1000 文），不是贯。
  原生修行每日 2 文，M5 培养照抄该口径。
- **★ 月钩递归**：`0x4A0D50 → 0x4A0DED → 0x4A4C60 → 0x4A4CC0 → 月钩 0x4A4CC5`，
  只要「日 ≥ 0x1f」就走月进位并重入成长桩 ⇒ 任何手工推天数都必须限 `日 + 天数 <= 30`。- **debug_log 是 stdcall `ret 4`**（`.edata@0x54C988`）：调用点后面不能再跟 `add esp,4`，
  2026-10-07 就因为这个 ESP 逐次漂移，"过日子/月边界必崩"。4 个调用点在成长桩、2 个在预载桩。
- **★ 改任何 asm 之后跑 `python .rev/audit_callconv.py TAIK2W95_big.exe`** —— 两类调用约定事故都出过：
  ① 调用方多清栈（fix2，`debug_log` 后面多一条 `add esp,4` ⇒ ESP 漂移 ⇒ ret 到 0）；
  ② 调用方少清栈（本次，`0x4A0D50` 后少了 `add esp,8` ⇒ 循环变量被栈顶残留实参吞掉 ⇒ 无限循环）。
  判据只能是**原生调用点的下一条指令**，不能凭印象 —— 同一批原语里 cdecl 与 `ret 4` 混着是常态。

## 环境约束

- **无外网** → 拿不到 upx / 现成解包器，一切自己写
- **无 C 编译器** → 新增 DLL 只能手工拼 PE + x86 机器码
- Python：反汇编/仿真用 venv `...\binaries\python\envs\default\Scripts\python.exe`（capstone 5.0.7 + unicorn 2.1.4 + keystone 0.9.2）
- **跑 `build_big.py` 必须用系统 Python**：`C:\Users\Administrator\AppData\Local\Programs\Python\Python312\python.exe`
  —— 唯一同时有 **pefile**（venv 没有）+ capstone + keystone 的解释器
- Godot：`Godot_v4.7.1\Godot_v4.7.1-stable_win64.exe`（--headless --check-only 可做语法校验）

## MOD 区（`.edata` / VA 0x53C000 起）硬约束

- MOD 私有区 base `0x54B600`，配额 `MOD_SZ = 0x8000`；所有子块地址由 `build_big.py` 顶部的 `M(off)` 推导
- **每个子块必须按实际长度圈地**（`regions` 表），不能手写 `(va, 0x500)` 之类的臆测值：
  2026-10-07 培养面板 `KD_CODE` 实际 1626B 却只圈 0x500，尾部被诊断 trampoline 本体覆盖，
  症状是「点培养 → 执行到半截指令 → AV@MOD 区最后一字节」。现用 `KD_CODE_SZ` 常量。
- **诊断 trampoline 默认关闭**（`TKID_DBG_TRAMP=1` 才装）。它们既战友钩子站点的头 5 字节
  （会导致进大地图 EIP=0），本体又占 MOD 区 —— 定位完当场关掉，不要留在正式产物里。
- **M5（2026-10-07）：`regions` 表里写了更小的窗口也不报错** —— 真正拦越界的是那几条显式 assert。
  `MENU_STUB` 曾写 `(va, 0x500)`，而 hook 196B + foster 1189B = 1385B 早已越过，却因为后面是空隙才没出事。
  现写成 `SC_CODE_VA - MENU_STUB_VA`（0x800），另加显式 assert：`foster 尾 <= SC_CODE_VA`。
- 构建产物 `TAIK2W95_big.exe == TAIK2W95_big_m5.exe`（同一份干净重建，无需任何事后 byte patch）。
  回归（都用系统 Python 跑）：`python .rev/verify_final.py TAIK2W95_big.exe` 期望 **12 OK / 0 FAIL**；
  `python .rev/verify_children.py` 期望 **237 通过 / 0 失败**；
  `python .rev/audit_callconv.py TAIK2W95_big.exe` 期望 **0 双清 / 30 处符合**。
- **`build_big.py` 的写盘路径必须以 `__file__` 锚定**（已修）：以前写 `_big_layout.json` 用相对路径，
  在根目录跑就更新根目录那份、在 `.rev` 跑就更新 `.rev` 那份，而 `verify_children.py` 只读 `.rev` 那份
  ⇒ 会出现"构建说成功、验收拿旧布局"的鬼打墙。

## 常用命令

```bash
cd "F:\Games\Taikou 2"
python scripts/_run_all_selfchecks.py     # 180 自测（约 12 分钟）
python scripts/_audit_progress.py          # 未破项清单
python modkit/selftest.py                  # LS11 round-trip，应 66 通过 / 0 失败
python modkit/cli.py unpack-all
```

Python venv（capstone 5.0.7 + Unicorn 2.1.4）用于反汇编与单函数仿真。
