extends Node
## AudioManager — 音效管理（阶段 6：39 个原版音效接入 + BGM 占位）
##
## 对齐原版 `play_sfx(id)`（0x4997c0）的数字 id 语义：
##   AudioManager.play_sfx(0)   # UI 点击（CLICK）
##   AudioManager.play_sfx(1)   # UI 取消（CANCEL）
##   AudioManager.play_sfx_named("TEPPOU")   # 洋枪（按名播放）
##
## 载入策略（与 CJK 字体同一课）：
##   AudioStreamWAV.load_from_file(绝对路径) 直载 WAV，**不用 ResourceLoader.load(res://)** ——
##   后者依赖 .import 导入缓存，未导入过的工程会静默失败。惰性载入 + 结果缓存。
##
## ⚠️ 不声明 class_name（与 autoload 注册名冲突的风险 + 无头模式不建类缓存）。

const Sfx = preload("res://src/audio/Sfx.gd")

## SFX 并发池大小（重叠音效如连续攻击音）
const POOL_SIZE := 8

var _streams: Dictionary = {}        # id -> AudioStreamWAV（失败缓存 null，避免反复重试 IO）
var _pool: Array = []                # AudioStreamPlayer 池
var _bgm_player: AudioStreamPlayer   # BGM 独占一轨（循环）
var _sfx_volume_db: float = 0.0
var _muted: bool = false


func _ready() -> void:
	process_mode = Node.PROCESS_MODE_ALWAYS
	for i in POOL_SIZE:
		var p := AudioStreamPlayer.new()
		add_child(p)
		_pool.append(p)
	_bgm_player = AudioStreamPlayer.new()
	add_child(_bgm_player)


## 惰性载入音效流（含失败缓存）；id 越界返回 null
## ⚠️ Godot 4.7 的 AudioStreamWAV.load_from_file 是实例调用、**返回载入后的流**
##   （失败返回 null），不返回 Error 码 —— 与 FontFile.load_dynamic_font 不同。
func _stream_of(id: int) -> AudioStreamWAV:
	if _streams.has(id):
		return _streams.get(id)
	if id < 0 or id >= Sfx.COUNT:
		return null
	var fp := ProjectSettings.globalize_path(Sfx.PATHS[id])
	var loaded = AudioStreamWAV.new().load_from_file(fp)
	if not FileAccess.file_exists(fp) or loaded == null:
		push_warning("[Audio] 音效载入失败 id=%d (%s): %s" %
			[id, Sfx.NAMES[id], fp])
		_streams[id] = null
		return null
	_streams[id] = loaded
	return loaded


## 播放音效（id = 原版 play_sfx 数字 id）
func play_sfx(id: int) -> void:
	if _muted:
		return
	var s := _stream_of(id)
	if s == null:
		return
	for p in _pool:
		var player := p as AudioStreamPlayer
		if not player.playing:
			player.stream = s
			player.volume_db = _sfx_volume_db
			player.play()
			return
	# 池满：抢占 0 号
	var p0 := _pool[0] as AudioStreamPlayer
	p0.stream = s
	p0.play()


## 按名称播放（id 未知场景 / 调试）
func play_sfx_named(sfx_name: String) -> void:
	var idx := Sfx.NAMES.find(sfx_name)
	if idx >= 0:
		play_sfx(idx)


## 预载全部音效（进加载画面时调一次，避免首播卡顿）
func preload_all() -> void:
	for id in Sfx.COUNT:
		_stream_of(id)


func stop_all_sfx() -> void:
	for p in _pool:
		(p as AudioStreamPlayer).stop()


func set_sfx_volume_db(db: float) -> void:
	_sfx_volume_db = db
	for p in _pool:
		(p as AudioStreamPlayer).volume_db = db


func set_muted(v: bool) -> void:
	_muted = v
	if v:
		stop_all_sfx()


func is_muted() -> bool:
	return _muted


## —— BGM（assets/audio/bgm/ 目录已就绪，素材待接入；原版为 MIDI/CD 音轨，方案未定）——

func play_bgm(name: String) -> void:
	var fp := ProjectSettings.globalize_path("res://assets/audio/bgm/%s" % name)
	if not FileAccess.file_exists(fp):
		push_warning("[Audio] BGM 不存在（目录已就绪，素材待接入）: %s" % fp)
		return
	# 素材接入后按实际格式实现（AudioStreamOggVorbis.load_from_file 等）
	push_warning("[Audio] BGM 播放尚未实现: %s" % fp)


func stop_bgm() -> void:
	_bgm_player.stop()
