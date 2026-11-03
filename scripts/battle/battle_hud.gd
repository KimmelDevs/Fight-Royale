extends CanvasLayer
## Two health bars (with a trailing "damage taken" bar) and guard meters, the player's
## Z/X/C skill bar with cooldowns, a center banner, and a controls hint.

const BAR_W := 420.0
const BAR_H := 18.0
const SLOT := 64.0

var left_fighter
var right_fighter
var right_tag := ""

var _bars := []  # per side: {hp, trail, guard, trail_v, delay, ...}
var _skill_bar: HBoxContainer
var _skills := {}  # key -> {overlay, timer}
var _banner: Label
var _sub: Label
var _banner_tween: Tween


func _ready() -> void:
	_bars.append(_make_bar(false, Color("7fd65b")))
	_bars.append(_make_bar(true, Color("e8534a")))

	_banner = _label(78, Color.WHITE)
	_banner.set_anchors_and_offsets_preset(Control.PRESET_CENTER)
	_banner.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	_banner.grow_horizontal = Control.GROW_DIRECTION_BOTH
	_banner.grow_vertical = Control.GROW_DIRECTION_BOTH
	_banner.position.y -= 80
	add_child(_banner)
	_sub = _label(22, Color.WHITE)
	_sub.set_anchors_and_offsets_preset(Control.PRESET_CENTER)
	_sub.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	_sub.grow_horizontal = Control.GROW_DIRECTION_BOTH
	_sub.position.y += 10
	add_child(_sub)

	var hint := _label(14, Color.WHITE)
	hint.text = "WASD move   Space jump   Right click: attack (tap) / charged (hold)   Left click: block (just before a hit = PARRY)   Z X C skills   Esc: select"
	hint.set_anchors_and_offsets_preset(Control.PRESET_CENTER_BOTTOM)
	hint.grow_horizontal = Control.GROW_DIRECTION_BOTH
	hint.grow_vertical = Control.GROW_DIRECTION_BEGIN
	hint.position.y -= 12
	add_child(hint)

	_skill_bar = HBoxContainer.new()
	_skill_bar.add_theme_constant_override("separation", 12)
	add_child(_skill_bar)


func bind(left, right, tag := "") -> void:
	left_fighter = left
	right_fighter = right
	right_tag = tag
	for c in _skill_bar.get_children():
		c.queue_free()
	_skills.clear()
	for key: String in ["z", "x", "c"]:
		_skill_bar.add_child(_make_skill(key, left.attacks[key].name, left.look.glow))
	_skill_bar.reset_size()
	_skill_bar.set_anchors_and_offsets_preset(Control.PRESET_CENTER_BOTTOM, Control.PRESET_MODE_MINSIZE, 40)


func _label(size: int, color: Color) -> Label:
	var l := Label.new()
	l.add_theme_font_size_override("font_size", size)
	l.add_theme_color_override("font_color", color)
	l.add_theme_color_override("font_outline_color", Color(0.1, 0.1, 0.22))
	l.add_theme_constant_override("outline_size", maxi(4, size / 6))
	return l


func _make_skill(key: String, title: String, glow: Color) -> Control:
	var col := VBoxContainer.new()
	col.alignment = BoxContainer.ALIGNMENT_CENTER
	var icon := Panel.new()
	icon.custom_minimum_size = Vector2(SLOT, SLOT)
	icon.size_flags_horizontal = Control.SIZE_SHRINK_CENTER
	icon.clip_children = CanvasItem.CLIP_CHILDREN_AND_DRAW
	var sb := StyleBoxFlat.new()
	sb.bg_color = Color(glow.r * 0.35, glow.g * 0.35, glow.b * 0.5, 0.92)
	sb.border_color = Color("e6c26e")
	sb.set_border_width_all(3)
	sb.set_corner_radius_all(int(SLOT / 2))
	icon.add_theme_stylebox_override("panel", sb)
	col.add_child(icon)
	var overlay := ColorRect.new()
	overlay.color = Color(0, 0, 0.1, 0.65)
	overlay.anchor_right = 1.0
	overlay.anchor_top = 1.0
	overlay.anchor_bottom = 1.0
	overlay.mouse_filter = Control.MOUSE_FILTER_IGNORE
	icon.add_child(overlay)
	var k := _label(22, Color.WHITE)
	k.text = key.to_upper()
	k.set_anchors_preset(Control.PRESET_FULL_RECT)
	k.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	k.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
	icon.add_child(k)
	var timer := _label(13, Color("ffe9a8"))
	timer.set_anchors_preset(Control.PRESET_FULL_RECT)
	timer.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	timer.vertical_alignment = VERTICAL_ALIGNMENT_BOTTOM
	icon.add_child(timer)
	var name_label := _label(12, Color.WHITE)
	name_label.text = title
	name_label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	col.add_child(name_label)
	_skills[key] = {"overlay": overlay, "timer": timer}
	return col


func _make_bar(right: bool, fill_color: Color) -> Dictionary:
	var root := Control.new()
	root.size = Vector2(BAR_W, 70)
	if right:
		root.set_anchors_preset(Control.PRESET_TOP_RIGHT)
		root.position = Vector2(-BAR_W - 28, 22)
	else:
		root.position = Vector2(28, 22)
	add_child(root)

	var name_label := _label(20, Color.WHITE)
	name_label.size = Vector2(BAR_W, 26)
	name_label.horizontal_alignment = HORIZONTAL_ALIGNMENT_RIGHT if right else HORIZONTAL_ALIGNMENT_LEFT
	root.add_child(name_label)

	var bg := ColorRect.new()
	bg.color = Color(0.08, 0.1, 0.2, 0.75)
	bg.position = Vector2(-3, 27)
	bg.size = Vector2(BAR_W + 6, BAR_H + 6)
	root.add_child(bg)
	var trail := ColorRect.new()
	trail.color = Color(1.0, 0.95, 0.8)
	trail.position = Vector2(0, 30)
	trail.size = Vector2(BAR_W, BAR_H)
	root.add_child(trail)
	var hp := ColorRect.new()
	hp.color = fill_color
	hp.position = Vector2(0, 30)
	hp.size = Vector2(BAR_W, BAR_H)
	root.add_child(hp)

	var gbg := ColorRect.new()
	gbg.color = Color(0.08, 0.1, 0.2, 0.6)
	gbg.position = Vector2(0, 54)
	gbg.size = Vector2(BAR_W * 0.6, 7)
	if right:
		gbg.position.x = BAR_W * 0.4
	root.add_child(gbg)
	var guard := ColorRect.new()
	guard.color = Color("f2c94c")
	guard.position = gbg.position
	guard.size = gbg.size
	root.add_child(guard)
	return {"right": right, "name": name_label, "hp": hp, "trail": trail, "guard": guard,
		"guard_x": gbg.position.x, "trail_v": 1.0, "delay": 0.0, "last_hp": 1.0}


func _process(delta: float) -> void:
	var fighters := [left_fighter, right_fighter]
	for i in 2:
		var f = fighters[i]
		if f == null or not is_instance_valid(f):
			continue
		var b: Dictionary = _bars[i]
		b.name.text = f.display_name if i == 0 or right_tag == "" else "%s  (%s)" % [f.display_name, right_tag]
		var hp_v: float = f.hp / f.max_hp
		if hp_v < b.last_hp:
			b.delay = 0.45
		b.last_hp = hp_v
		b.delay -= delta
		if b.delay <= 0.0:
			b.trail_v = move_toward(b.trail_v, hp_v, delta * 0.8)
		b.trail_v = maxf(b.trail_v, hp_v)
		_set_fill(b.hp, b.right, 0.0, BAR_W, hp_v)
		_set_fill(b.trail, b.right, 0.0, BAR_W, b.trail_v)
		var g: float = f.guard / f.max_guard
		_set_fill(b.guard, b.right, b.guard_x, BAR_W * 0.6, g)
		b.guard.color = Color("f2c94c") if g > 0.25 else Color("ff7043")
	if left_fighter != null and is_instance_valid(left_fighter):
		for key: String in _skills:
			var left: float = left_fighter.cooldowns[key]
			var total: float = left_fighter.attacks[key].cd
			_skills[key].overlay.anchor_top = 1.0 - clampf(left / total, 0.0, 1.0)
			_skills[key].timer.text = "%.1f" % left if left > 0.05 else ""


## Right-side bars drain toward the screen edge, like a fighting game.
func _set_fill(rect: ColorRect, right: bool, x0: float, width: float, v: float) -> void:
	var w := width * clampf(v, 0.0, 1.0)
	rect.size.x = w
	rect.position.x = x0 + (width - w if right else 0.0)


func show_banner(text: String, color: Color, sub := "", hold := 0.0) -> void:
	_banner.text = text
	_banner.add_theme_color_override("font_color", color)
	_sub.text = sub
	_banner.modulate.a = 1.0
	_sub.modulate.a = 1.0
	_banner.scale = Vector2.ONE * 1.6
	_banner.pivot_offset = _banner.size * 0.5
	if _banner_tween:
		_banner_tween.kill()
	# Real-time so hit-stop and slow-mo do not freeze the banner.
	_banner_tween = create_tween().set_ignore_time_scale(true)
	_banner_tween.tween_property(_banner, "scale", Vector2.ONE, 0.25).set_trans(Tween.TRANS_BACK).set_ease(Tween.EASE_OUT)
	if hold > 0.0:
		_banner_tween.tween_interval(hold)
		_banner_tween.tween_property(_banner, "modulate:a", 0.0, 0.3)
		_banner_tween.parallel().tween_property(_sub, "modulate:a", 0.0, 0.3)
