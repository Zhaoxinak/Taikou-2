# 太阁立志传2 — HD-2D 高清重制方案（1080p / 2K / 4K）

> **风格已定：HD-2D**（Square Enix 系：`OCTOPATH TRAVELER` / `TRIANGLE STRATEGY` / `DQ3 HD-2D`）
>
> **HD-2D 的本质 = 高分辨率像素 sprite + 3D 场景 + 现代后处理光照**
> 不是「把 16×16 放大」，而是**用 3D 重建世界、用高清像素重画角色**。
>
> **这对太阁2 的战略意义**：
> - ✅ **合战可以做真 3D 战场**——`HJMAPDAT` 的 40×19 地形网格直接变成 3D 地形
> - ✅ **绕开「武将头像拿不到原图」的死结**——HD-2D 立绘本就是重画的，不依赖原图
> - ✅ **1080p/2K/4K 全段清晰**——3D 分辨率无关，sprite 按 4K 规格重画
>
> **状态**：方案已定（2026-09-08）。渲染骨架 `src/render/` 已落地，素材生产待启动。

---

## 0. HD-2D 到底是什么（避免误解）

| 误解 | 实际 |
|---|---|
| 「把像素图放大」 | ❌ HD-2D 的 **背景是 3D 建模**，不是放大的 2D |
| 「加个滤镜就行」 | ❌ 需要 **3D 场景 + 正交相机 + 后处理管线** 三件套 |
| 「角色是 3D 模型」 | ❌ 角色仍是 **2D 高分辨率像素 sprite**（billboard 面片）|
| 「越高清越好」 | ⚠️ sprite 要**保持像素颗粒感**，不能做成写实画 |

**一句话**：**3D 的世界 + 2D 的人 + 电影级光影**。

### HD-2D 的四个视觉支柱

1. **3D 环境**：真实透视/正交 3D 场景，有景深、有光照
2. **2D 像素角色**：高清像素 art（128×128 ~ 256×256），billboard 面片贴在 3D 场景里
3. **现代后处理**：Bloom/Glow、景深(DOF)、环境光遮蔽(SSAO)、色调映射(ACES)
4. **精细光影**：动态光照 + 体积感 + 材质细节（水汽、火光、晨雾）

---

## 1. 素材现状：什么能用、什么要重画

### 1.1 可复用的（作为"数据"和"参考"）

| 数据 | 用途 |
|---|---|
| `HJMAPDAT` 40×19 地形网格（38 张）| ⭐ **直接生成 3D 地形**（最有价值）|
| 地形类型编码（16 种：平地/森林/河流/城/山地/桥…）| 3D 材质分配 |
| 部署图 40×19 | 单位初始站位 → 3D 世界坐标 |
| 城表 200 条 / 国表 49 条 | 3D 大地图的城池位置 |
| 16×16 tile（MAPCHIP/TOWNCHIP/HBCHAR 共 1050 张）| **仅作像素 sprite 重画的造型参考** |

### 1.2 需要重画的（HD-2D 核心工作）

| 素材 | 规格 | 数量 | 方式 |
|---|---|---|---|
| **武将立绘** | 512×640（HD-2D 半身）| **695** | ImageGen AI 重绘 |
| **武将头像** | 128×160（小头像）| 695 | 从立绘裁剪 |
| **单位 sprite** | 256×256 像素 art | ~4 兵种 × 4 方向 = 16 | ImageGen + 人工修 |
| **地形材质** | PBR / 高分辨率贴图 | 16 种 | 程序化 + ImageGen |
| **UI** | Godot 自绘 + 少量图片 | — | StyleBoxFlat |
| **背景板** | 3840×2400 | 13 个 GRP 场景 | ImageGen 重绘 |

> 🔑 **关键判断**：16×16 原图**不直接超分使用**——HD-2D 要的是"高清像素 art"，
> 不是"放大的模糊像素"。原图仅作为**造型参考**。

---

## 2. HD-2D 渲染架构（Godot 4 实现）

### 2.1 场景树

```
Main.tscn
├── WorldEnvironment          ← HD-2D 后处理（Glow/DOF/SSAO/Tonemap）
│   └── Environment (.tres)
├── Camera3D                  ← 正交相机（2.5D 视角）
├── DirectionalLight3D        ← 主光（模拟日光/月夜）
├── BattleTerrain             ← 3D 地形（由 HJMAPDAT 生成）
│   └── MeshInstance3D
├── UnitSprites               ← 2D 像素 sprite（Sprite3D billboard）
│   └── Sprite3D × N
├── FXLayer                   ← 粒子/光效（火计、烟、雨）
└── UILayer (CanvasLayer)     ← 2D UI（菜单/状态栏）
```

### 2.2 相机：正交 vs 透视

| 模式 | 适用 | 效果 |
|---|---|---|
| `PROJECTION_ORTHOGONAL` | **合战俯视**（推荐）| 经典战棋 2.5D 视角，无透视变形 |
| `PROJECTION_PERSPECTIVE` + 低 FOV(20~30°) | 城下町/大地图 | 有纵深，接近 `OCTOPATH` |

**太阁2 合战推荐正交**（原版是俯视网格，正交最还原）：

```gdscript
camera.projection = Camera3D.PROJECTION_ORTHOGONAL
camera.size = 24.0                      # 正交视野（世界单位）
camera.position = Vector3(20, 30, 20)   # 斜俯视
camera.look_at(Vector3(20, 0, 10))      # 看向战场中心
```

### 2.3 3D 地形（HJMAPDAT → 3D）

`HJMAPDAT` section B = **40×19 地形网格**，每格 `{code, type, mod}`。
直接映射为 3D 网格：

```gdscript
# src/battle/Terrain3DBuilder.gd
const TILE_SIZE := 1.0
const HEIGHT_BY_TYPE := {
	"平地": 0.0, "荒地": 0.05, "草地": 0.0, "森林": 0.35,
	"河流": -0.15, "城": 0.8, "空": -0.3, "山地": 1.2,
	"桥": 0.0, "阵": 0.1,
}

static func build(terrain_rows: Array) -> Node3D:
	# terrain_rows = 40 行 × 19 列，每格 {code,type,mod}
	var root := Node3D.new()
	var st := SurfaceTool.new()
	st.begin(Mesh.PRIMITIVE_TRIANGLES)
	for z in 19:
		for x in 40:
			var cell = terrain_rows[z][x]
			var h: float = HEIGHT_BY_TYPE.get(cell["type"], 0.0)
			_add_tile(st, x * TILE_SIZE, z * TILE_SIZE, h)
	st.generate_normals()
	var mi := MeshInstance3D.new()
	mi.mesh = st.commit()
	root.add_child(mi)
	return root
```

> 地形高度差 + 法线 → 配合 DirectionalLight 自动产生 HD-2D 的体积感。

### 2.4 2D 像素 sprite（Billboard）

角色/单位用 `Sprite3D`，保持像素颗粒：

```gdscript
# src/render/UnitSprite.gd
static func make_unit_sprite(tex: Texture2D, pos: Vector3) -> Sprite3D:
	var s := Sprite3D.new()
	s.texture = tex
	s.billboard = BaseMaterial3D.BILLBOARD_ENABLED           # 永远面向相机
	s.texture_filter = BaseMaterial3D.TEXTURE_FILTER_NEAREST # ★ 保住像素感
	s.pixel_size = 0.012                                     # 控制屏幕上像素大小
	s.position = pos
	s.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_ON
	return s
```

> 🔑 **`texture_filter = NEAREST`** 是 HD-2D 灵魂——放大时保持硬边像素，不做平滑插值。

### 2.5 后处理（HD-2D 的"电影感"来源）

```gdscript
# src/render/Hd2DEnvironment.gd
static func build_environment() -> Environment:
	var env := Environment.new()
	env.background_mode  = Environment.BG_COLOR
	env.background_color = Color(0.04, 0.06, 0.10)

	# ── Glow / Bloom（柔光溢出，HD-2D 招牌）
	env.glow_enabled       = true
	env.glow_intensity     = 0.55
	env.glow_bloom         = 0.25
	env.glow_hdr_threshold = 0.85
	env.glow_blend_mode    = Environment.GLOW_BLEND_MODE_SOFTLIGHT

	# ── 景深（虚化远景，突出前景单位）
	env.dof_blur_far_enabled  = true
	env.dof_blur_far_distance = 18.0
	env.dof_blur_far_amount   = 0.18

	# ── 环境光遮蔽（接触阴影，增强体积）
	env.ssao_enabled   = true
	env.ssao_intensity = 0.9
	env.ssao_radius    = 1.2

	# ── 色调映射（ACES 电影级）
	env.tonemapper       = Environment.TONE_MAPPER_ACES
	env.tonemap_exposure = 1.05

	# ── 色彩微调（HD-2D 偏浓郁）
	env.adjustment_enabled    = true
	env.adjustment_saturation = 1.15
	env.adjustment_contrast   = 1.08

	return env
```

### 2.6 光照 / 天气联动

配合太阁2 **已破解的天气系统**（`GAME_DATA_SPEC §3.9`）：

| 天气 | 表现 |
|---|---|
| 晴 | `light_energy=1.3`，暖白光 |
| 雨 | `light_energy=0.7` + 雨粒子 + 地面反射 |
| 雪 | `light_energy=0.9` + 雪粒子 + 冷色调 |
| 雾 | `env.fog_enabled=true`，`fog_density` 调高 |
| 夜 | `light_energy=0.25`，冷蓝光 + 篝火点光源 |

> 这是 HD-2D 相对原版**最大的表现力提升**：太阁2 原本静态像素，现在有真实天气光影。

---

## 3. 素材生产规格（HD-2D）

### 3.1 武将立绘（695 张）

| 项 | 规格 |
|---|---|
| 尺寸 | **512×640**（4:5）|
| 风格 | HD-2D 半身立绘：高清像素 art + 细腻光影 |
| 背景 | 透明（PNG RGBA）|
| 命名 | `assets/gfx/portrait/full_{id:04d}.png` |
| 小头像 | 由立绘裁 `128×160` → `face_{id:04d}.png` |

**ImageGen 提示词模板**：

```
HD-2D style portrait, Japanese Sengoku warlord,
half-body, 4:5 vertical, high-resolution pixel art,
{age} years old, rank: {rank_name}, clan of {province_name},
{detailed_samurai_armor}, {facial_expression},
Octopath Traveler HD-2D aesthetic,
soft rim lighting, warm color palette,
sharp pixel edges, 512x640, transparent background
```

**负面提示**：
```
blurry, photorealistic, 3D render, western armor, modern clothing,
smooth gradients, anti-aliased pixels, low resolution, jpeg artifacts
```

**按角色属性驱动提示词**（从 `data/officers.json`）：

| 条件 | 追加描述 |
|---|---|
| `forces.martial` ≥ 90 | `battle-worn armor, fierce expression, scars` |
| `forces.charm` ≥ 90 | `charismatic, refined features, elegant` |
| `forces.domestic` ≥ 90 | `scholarly, court attire, calm demeanor` |
| `rank == 7`（大名）| `daimyo, elaborate armor, gold accents, commanding presence` |
| `archetype == 0`（藤吉郎）| `humble origin, clever eyes, thin build` |

### 3.2 单位 sprite（兵种）

| 兵种 | 尺寸 | 方向 |
|---|---|---|
| 步兵 / 骑兵 / 洋枪 / 城守备 | **256×256** | 4 方向（左下/右下/左上/右上）|

```
HD-2D pixel art sprite, {unit_type} samurai soldier,
{direction} view, 256x256,
detailed pixel armor, sharp edges,
Octopath Traveler style, transparent background
```

### 3.3 地形材质（16 种）

| 地形 | HD-2D 表现 |
|---|---|
| 平地 / 草地 | 3D 平面 + 草地贴图 + 法线 |
| 森林 | 3D 低模树 + 顶点风动画 |
| 河流 | 半透明水面 shader + 波动 |
| 城 | 3D 简化城郭模型 |
| 山地 | 高度场 + 岩石材质 |
| 桥 | 3D 木桥模型 |

### 3.4 UI

Godot 4 原生 `StyleBoxFlat` 自绘（HD-2D 的 UI 偏简洁半透明）：

```gdscript
var sb := StyleBoxFlat.new()
sb.bg_color = Color(0.08, 0.06, 0.04, 0.92)
sb.border_color = Color(0.75, 0.55, 0.25, 0.9)
sb.set_border_width_all(2)
sb.set_corner_radius_all(6)
sb.shadow_color = Color(0, 0, 0, 0.5)
sb.shadow_size = 8
```

---

## 4. 多分辨率适配（1080p / 2K / 4K）

HD-2D **天生分辨率无关**——3D 部分自动适配，只需处理 sprite 与 UI：

| 屏幕 | viewport | 3D 渲染 | 256×256 sprite 显示 |
|---|---|---|---|
| 1080p | 1920×1080 | 原生 | ~180px（缩小 0.7x）✓ 锐利 |
| 2K | 2560×1440 | 原生 | ~240px（近似原生）✓ 锐利 |
| 4K | 3840×2160 | 原生 | ~360px（放大 1.4x）✓ 可接受 |

> sprite 规格 **256×256** 是甜点：1080p 缩小仍锐利，4K 放大仅 1.4x（像素感仍在，符合 HD-2D 美学）。

**已实现**：`src/core/DisplayAdapter.gd`（autoload，自动检测屏幕选 viewport）。

---

## 5. 分场景 HD-2D 应用

| 场景 | HD-2D 处理 | 优先级 |
|---|---|---|
| **合战（野战/攻城）** | ⭐ 3D 地形 + 像素单位 + 光影 + 天气 | **P0（最先做）** |
| **武将状态/立绘** | 512×640 HD-2D 立绘 | P0 |
| **大地图（49 国）** | 3D 日本地图 + 城池标记 + 势力色 | P1 |
| **城下町/内政** | 2D UI + HD-2D 背景板 + 景深 | P1 |
| **单挑** | 立绘对决 + 特效 + 光影 | P2 |
| **店铺/事件** | 2D 背景 + 立绘 | P2 |

> **为什么合战最先做**：`HJMAPDAT` 的 40×19 地形是**现成的 3D 网格数据**，
> 且合战公式已 100% 破解 —— 数据 + 公式都在手，只差渲染层。

---

## 6. 实施路线（修订版里程碑）

| 里程碑 | 内容 | 产出 |
|---|---|---|
| **HD-0** | 渲染骨架：Environment + 相机 + Sprite3D | `src/render/`（已落地）|
| **HD-1** | 3D 地形生成（HJMAPDAT → Mesh）| 可看的 3D 战场 |
| **HD-2** | 单位 sprite 系统（billboard + NEAREST）| 战场上有兵 |
| **HD-3** | 光照 + 天气联动 | 晴/雨/雪/昼夜 |
| **HD-4** | 武将立绘 695 张（ImageGen 批量）| 立绘库 |
| **HD-5** | UI 自绘 + 分辨率适配 | 完整界面 |
| **HD-6** | 视觉回归 + 4K 性能基准 | 60fps @4K |

---

## 7. 风险与对策

| 风险 | 对策 |
|---|---|
| 695 张立绘风格不统一 | 固定提示词模板 + 负向词；先生成 20 张定风格；人工抽查 5% |
| ImageGen 调用量大 | 分批（每天 50 张）；优先主角 6 + 大名 45 + 常用 200 |
| 4K 下 sprite 像素块明显 | 256×256 规格；或接受其为 HD-2D 特征 |
| 3D 地形工作量大 | 先简化平面 + 高度差（MVP），树木/城郭后补 |
| 4K + 后处理性能 | 后处理分级（4K 降 DOF 采样）；sprite 用图集 |

---

## 8. 立即可执行的下一步

1. **确认风格**：先生成 3 张 HD-2D 立绘样本（织田信长 / 木下藤吉郎 / 上杉谦信）
2. **HD-1**：写 `Terrain3DBuilder.gd`，把 HJMAPDAT 第 0 战变成可看的 3D 地形
3. **HD-2**：用 16×16 原图临时占位，跑通 billboard sprite 管线

---

*编写日期：2026-09-08 ｜ 风格：HD-2D ｜ 配套：Godot复刻实施方案.md / src/core/DisplayAdapter.gd*
