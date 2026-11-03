extends CanvasLayer
## Skill bar with cooldown sweeps, plus a controls hint.

const Player := preload("res://scripts/player.gd")
const SLOTS := [
	["attack", "LMB", "Tide Shot"],
	["dash", "Shift", "Ripple Dash"],
	["skill", "E", "Tidal Ring"],
	["shield", "R", "Bubble Ward"],
	["burst", "Q", "Ocean Requiem"],
]

var player: Player
var _overlays := {}
var _timers := {}


func _ready() -> void:
	var hint := Label.new()
	hint.text = "WASD move   Space jump   Click to aim with mouse (Esc frees it)   Wheel zoom"
	hint.position = Vector2(20, 16)
	hint.add_theme_color_override("font_color", Color(0.12, 0.2, 0.42))
	hint.add_theme_font_size_override("font_size", 15)
	add_child(hint)

	var bar := HBoxContainer.new()
	bar.add_theme_constant_override("separation", 14)
	add_child(bar)
	for slot: Array in SLOTS:
		bar.add_child(_make_slot(slot[0], slot[1], slot[2]))
	bar.set_anchors_and_offsets_preset(Control.PRESET_CENTER_BOTTOM, Control.PRESET_MODE_MINSIZE, 24)


func _make_slot(id: String, key: String, title: String) -> Control:
	var col := VBoxContainer.new()
	col.alignment = BoxContainer.ALIGNMENT_CENTER
	var icon := Panel.new()
	icon.custom_minimum_size = Vector2(64, 64)
	icon.size_flags_horizontal = Control.SIZE_SHRINK_CENTER
	icon.clip_children = CanvasItem.CLIP_CHILDREN_AND_DRAW
	var sb := StyleBoxFlat.new()
	sb.bg_color = Color(0.13, 0.22, 0.5, 0.9) if id != "burst" else Color(0.2, 0.45, 0.85, 0.95)
	sb.border_color = Color("e6c26e")
	sb.set_border_width_all(3)
	sb.set_corner_radius_all(32)
	icon.add_theme_stylebox_override("panel", sb)
	col.add_child(icon)

	var overlay := ColorRect.new()
	overlay.color = Color(0, 0, 0.1, 0.6)
	overlay.anchor_left = 0.0
	overlay.anchor_right = 1.0
	overlay.anchor_top = 1.0
	overlay.anchor_bottom = 1.0
	overlay.mouse_filter = Control.MOUSE_FILTER_IGNORE
	icon.add_child(overlay)
	_overlays[id] = overlay

	var key_label := Label.new()
	key_label.text = key
	key_label.set_anchors_preset(Control.PRESET_FULL_RECT)
	key_label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	key_label.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
	key_label.add_theme_font_size_override("font_size", 17)
	icon.add_child(key_label)

	var timer := Label.new()
	timer.set_anchors_preset(Control.PRESET_FULL_RECT)
	timer.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	timer.vertical_alignment = VERTICAL_ALIGNMENT_BOTTOM
	timer.add_theme_font_size_override("font_size", 13)
	timer.add_theme_color_override("font_color", Color("ffe9a8"))
	icon.add_child(timer)
	_timers[id] = timer

	var name_label := Label.new()
	name_label.text = title
	name_label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	name_label.add_theme_font_size_override("font_size", 12)
	name_label.add_theme_color_override("font_color", Color(0.12, 0.2, 0.42))
	col.add_child(name_label)
	return col


func _process(_delta: float) -> void:
	if player == null:
		return
	for id: String in _overlays:
		var left: float = player.cooldowns[id]
		var total: float = Player.COOLDOWN[id]
		_overlays[id].anchor_top = 1.0 - clampf(left / total, 0.0, 1.0)
		_timers[id].text = "%.1f" % left if left > 0.05 and total >= 1.0 else ""
