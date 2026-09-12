extends Node
## AudioManager — 音效 + BGM（阶段 6：39 个原版音效 + 34 首原版 BGM 全部接入）
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
const Bgm = preload("res://src/audio/Bgm.gd")

## SFX 并发池大小（重叠音效如连续攻击音）
const POOL_SIZE := 8

var _streams: Dictionary = {}        # id -> AudioStreamWAV（失败缓存 null，避免反复重试 IO）
var _pool: Array = []                # AudioStreamPlayer 池
var _bgm_player: AudioStreamPlayer   # BGM 独占一轨（循环）
var _cur_bgm: int = 0                # 当前 BGM 轨号（对齐原版 byte[0x501294]）
var _sfx_volume_db: float = 0.0
var _bgm_volume_db: float = 0.0
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
		_bgm_player.stream_paused = true
	else:
		_bgm_player.stream_paused = false
		if _cur_bgm > 0 and not _bgm_player.playing:
			_bgm_player.play()


func is_muted() -> bool:
	return _muted


## —— BGM（原版 = CD 数字音频；中文版改走 MP3/ 34 首，轨号 1..34）——
##
## 复刻 `CdPlay(track, flag, from, to)` @0x401310（`add esp,0x10` 实证 4 参）：
##   * track <= 0            ⇒ 停止（原版 bl==0 跳 0x401441 → CdStopClose 0x4012c0）
##   * track > 轨数(34)      ⇒ 停止（原版 `cmp al,bl; jb` 越界分支）
##   * 正在播且当前轨 == track ⇒ 直接返回，不重播（原版 0x401322 比对 byte[0x501294]）
##   * 成功 ⇒ 记录当前轨（原版 `mov byte[0x501294], bl` @0x401430）
## 载入同音效：FileAccess 读字节 → AudioStreamMP3.data，绕开 .import 导入缓存。

## 按 CD 轨号播放（1..34）；返回是否真的起播
func play_bgm_track(track: int) -> bool:
	if _bgm_player == null:
		return false                     # autoload 未就绪（--script 无头测试等）
	if track < Bgm.TRACK_MIN or track > Bgm.TRACK_MAX:
		stop_bgm()                       # 0 / 越界 ⇒ 停止（原版语义）
		return false
	if _bgm_player.playing and _cur_bgm == track:
		return false                     # 防重播（0x401322）
	var s := _bgm_stream_of(track)
	if s == null:
		return false
	_bgm_player.stream = s
	_bgm_player.volume_db = _bgm_volume_db
	_bgm_player.play()
	_cur_bgm = track                     # 0x401430
	return true


## 按原版「BGM 槽位」播放（轨号 = 槽位 + 2，0x498eb8 `add al,2`）
func play_bgm_slot(slot: int) -> bool:
	return play_bgm_track(Bgm.track_for_slot(slot))


func stop_bgm() -> void:
	_bgm_player.stop()
	_bgm_player.stream = null
	_cur_bgm = 0


## 当前 BGM 轨号（0 = 未播放），对齐原版 byte[0x501294]
func get_bgm_track() -> int:
	return _cur_bgm


func is_bgm_playing() -> bool:
	return _bgm_player.playing


func set_bgm_volume_db(db: float) -> void:
	_bgm_volume_db = db
	_bgm_player.volume_db = db


func get_bgm_volume_db() -> float:
	return _bgm_volume_db


## 载入 BGM 流（不缓存全部 34 首：单曲 1~5MB，全缓存约 54MB）
func _bgm_stream_of(track: int) -> AudioStreamMP3:
	var fp := ProjectSettings.globalize_path(Bgm.PATHS[track - 1])
	if not FileAccess.file_exists(fp):
		push_warning("[Audio] BGM 缺失 轨 %d: %s" % [track, fp])
		return null
	var f := FileAccess.open(fp, FileAccess.READ)
	if f == null:
		push_warning("[Audio] BGM 打开失败 轨 %d: %s" % [track, fp])
		return null
	var bytes := f.get_buffer(f.get_length())
	f.close()
	var s := AudioStreamMP3.new()
	s.data = bytes
	s.loop = true   # 原版 CD-DA 单遍 + MCI_NOTIFY 回调续播（回调未逆）；复刻层直接循环
	return s
