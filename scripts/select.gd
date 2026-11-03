extends Node3D
## Character select in two steps: pick your fighter, then pick the CPU's fighter (or Random)
## and its difficulty. A turntable previews the highlighted fighter next to an info panel
## with stats and skills.

const World := preload("res://scripts/world.gd")
const Roster := preload("res://scripts/roster.gd")
const Kits := preload("res://scripts/battle/kits.gd")
const Model := preload("res://scripts/battle/fighter_model.gd")
const AiBrain := preload("res://scripts/battle/ai_brain.gd")
const BATTLE_SCENE := "res://battle.tscn"

const CONTROLS := {
	"knight": "Tap: 3-hit sword combo   Hold: charged slash   Block: shield",
	"mage": "Tap: 3-cast spell combo   Hold: charged spell   Block: magic barrier",
	"assassin": "Tap: 4-hit dagger flurry   Hold: dash strike   Block: dagger guard (wide parry)",
}
const STAT_NAMES := ["power", "speed", "range", "defense"]
const LEVEL_COLORS := [Color("6fcf7f"), Color("5fa8e3"), Color("f2994a"), Color("e8534a")]
const RANDOM := -1

var _step := 0
var _sel := 0
var _cpu := RANDOM
var _model: Model
var _pedestal: Node3D
var _question: Label3D
var _poses := {}
var _pose_name := "idle"
var _pose_t := 0.0
var _spin := 0.0
var _dragging := false

var _cards: Array[Button] = []
var _random_card: Button
var _header: Label
var _sub_header: Label
var _name: Label
var _title: Label
var _role: Label
var _desc: Label
var _stats_box: VBoxContainer
var _stat_pips := {}
var _skills_box: VBoxContainer
var _controls: Label
var _next_btn: Button
var _cpu_box: VBoxContainer
var _level_btns: Array[Button] = []


func _ready() -> void:
	Engine.time_scale = 1.0
	World.build(self)
	var cam := Camera3D.new()
	cam.fov = 40.0
	add_child(cam)
	cam.position = Vector3(1.05, 1.25, 4.4)
	cam.look_at(Vector3(1.05, 0.95, 0.0), Vector3.UP)
	cam.make_current()
	_build_pedestal()
	_build_ui()
	_sel = clampi(Roster.player_pick, 0, Roster.CHARACTERS.size() - 1)
	_cpu = Roster.enemy_pick
	_set_level(Roster.difficulty)
	_set_step(0)


func _build_pedestal() -> void:
	_pedestal = Node3D.new()
	add_child(_pedestal)
	var disc := MeshInstance3D.new()
	var c := CylinderMesh.new()
	c.top_radius = 0.9
	c.bottom_radius = 0.95
	c.height = 0.12
	c.radial_segments = 48
	disc.mesh = c
	var m := StandardMaterial3D.new()
	m.albedo_color = Color("eef2fb")
	disc.material_override = m
	disc.position.y = -0.06
	_pedestal.add_child(disc)
	var ring := MeshInstance3D.new()
	var t := TorusMesh.new()
	t.inner_radius = 0.88
	t.outer_radius = 0.97
	t.rings = 64
	ring.mesh = t
	var rm := StandardMaterial3D.new()
	rm.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	rm.albedo_color = Color("e6c26e")
	ring.material_override = rm
	ring.scale = Vector3(1, 0.4, 1)
	_pedestal.add_child(ring)
	_question = Label3D.new()
	_question.text = "?"
	_question.font_size = 256
	_question.outline_size = 32
	_question.pixel_size = 0.004
	_question.modulate = Color("ffe08a")
	_question.outline_modulate = Color(0.1, 0.1, 0.22)
	_question.position = Vector3(0, 0.95, 0)
	_question.billboard = BaseMaterial3D.BILLBOARD_ENABLED
	add_child(_question)


# --- UI ---------------------------------------------------------------------------

func _label(size: int, color := Color.WHITE) -> Label:
	var l := Label.new()
	l.add_theme_font_size_override("font_size", size)
	l.add_theme_color_override("font_color", color)
	l.add_theme_color_override("font_outline_color", Color(0.1, 0.1, 0.22))
	l.add_theme_constant_override("outline_size", maxi(4, size / 6))
	return l


func _style(bg: Color, border: Color, width := 2, radius := 10) -> StyleBoxFlat:
	var sb := StyleBoxFlat.new()
	sb.bg_color = bg
	sb.border_color = border
	sb.set_border_width_all(width)
	sb.set_corner_radius_all(radius)
	sb.content_margin_left = 12
	sb.content_margin_right = 12
	sb.content_margin_top = 8
	sb.content_margin_bottom = 8
	return sb


func _big_button(text: String, color: Color, size: Vector2) -> Button:
	var b := Button.new()
	b.text = text
	b.custom_minimum_size = size
	b.focus_mode = Control.FOCUS_NONE
	b.add_theme_font_size_override("font_size", 28 if size.y > 50 else 18)
	b.add_theme_color_override("font_color", Color("2a1c08"))
	b.add_theme_color_override("font_hover_color", Color("2a1c08"))
	b.add_theme_color_override("font_pressed_color", Color("2a1c08"))
	b.add_theme_stylebox_override("normal", _style(color, color.lightened(0.5), 3, 12))
	b.add_theme_stylebox_override("hover", _style(color.lightened(0.15), Color.WHITE, 3, 12))
	b.add_theme_stylebox_override("pressed", _style(color.darkened(0.15), Color.WHITE, 3, 12))
	return b


func _build_ui() -> void:
	var ui := CanvasLayer.new()
	add_child(ui)

	_header = _label(44)
	_header.position = Vector2(36, 20)
	ui.add_child(_header)
	_sub_header = _label(15, Color("eef2ff"))
	_sub_header.position = Vector2(38, 78)
	ui.add_child(_sub_header)

	# Info panel on the right.
	var panel := PanelContainer.new()
	panel.add_theme_stylebox_override("panel", _style(Color(0.07, 0.1, 0.22, 0.82), Color("e6c26e"), 2, 14))
	panel.set_anchors_preset(Control.PRESET_RIGHT_WIDE)
	panel.offset_left = -470
	panel.offset_right = -28
	panel.offset_top = 84
	panel.offset_bottom = -170
	ui.add_child(panel)
	var info := VBoxContainer.new()
	info.add_theme_constant_override("separation", 6)
	panel.add_child(info)
	_name = _label(38)
	info.add_child(_name)
	_title = _label(20, Color("ffe08a"))
	info.add_child(_title)
	_role = _label(15, Color("b9c6e6"))
	info.add_child(_role)
	_desc = _label(13)
	_desc.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	_desc.custom_minimum_size.x = 400
	info.add_child(_desc)
	_stats_box = VBoxContainer.new()
	info.add_child(_stats_box)
	_stats_box.add_child(HSeparator.new())
	for s: String in STAT_NAMES:
		var row := HBoxContainer.new()
		var l := _label(15, Color("b9c6e6"))
		l.text = s.capitalize()
		l.custom_minimum_size.x = 90
		row.add_child(l)
		var pips: Array[ColorRect] = []
		for i in 5:
			var pip := ColorRect.new()
			pip.custom_minimum_size = Vector2(30, 10)
			row.add_child(pip)
			pips.append(pip)
		_stat_pips[s] = pips
		_stats_box.add_child(row)
	_stats_box.add_child(HSeparator.new())
	_controls = _label(12, Color("d8e2ff"))
	_controls.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	_controls.custom_minimum_size.x = 400
	_stats_box.add_child(_controls)
	_skills_box = VBoxContainer.new()
	_skills_box.add_theme_constant_override("separation", 4)
	_stats_box.add_child(_skills_box)

	# Roster cards along the bottom, plus a Random card for the CPU step.
	var row := HBoxContainer.new()
	row.add_theme_constant_override("separation", 6)
	ui.add_child(row)
	for i in Roster.CHARACTERS.size():
		var ch: Dictionary = Roster.CHARACTERS[i]
		var b := _card("%s\n%s" % [ch.look.name, ch.role.split(" - ")[0]], ch.look.tunic)
		b.pressed.connect(_pick.bind(i))
		row.add_child(b)
		_cards.append(b)
	_random_card = _card("Random\n?", Color("4a4f66"))
	_random_card.pressed.connect(_pick.bind(RANDOM))
	row.add_child(_random_card)
	row.reset_size()
	row.set_anchors_and_offsets_preset(Control.PRESET_BOTTOM_LEFT, Control.PRESET_MODE_MINSIZE, 32)

	# Bottom right: NEXT on step 1; difficulty, BACK and FIGHT on step 2.
	var go := VBoxContainer.new()
	go.add_theme_constant_override("separation", 8)
	go.alignment = BoxContainer.ALIGNMENT_END
	go.custom_minimum_size = Vector2(300, 140)
	ui.add_child(go)
	_next_btn = _big_button("NEXT  >", Color("e6c26e"), Vector2(300, 64))
	_next_btn.pressed.connect(_set_step.bind(1))
	go.add_child(_next_btn)
	_cpu_box = VBoxContainer.new()
	_cpu_box.add_theme_constant_override("separation", 8)
	go.add_child(_cpu_box)
	var dl := _label(15)
	dl.text = "CPU difficulty"
	_cpu_box.add_child(dl)
	var levels := HBoxContainer.new()
	levels.add_theme_constant_override("separation", 6)
	_cpu_box.add_child(levels)
	for i in AiBrain.LEVELS.size():
		var b := Button.new()
		b.text = AiBrain.LEVELS[i]
		b.custom_minimum_size = Vector2(70, 34)
		b.focus_mode = Control.FOCUS_NONE
		b.add_theme_font_size_override("font_size", 14)
		b.pressed.connect(_set_level.bind(i))
		levels.add_child(b)
		_level_btns.append(b)
	var buttons := HBoxContainer.new()
	buttons.add_theme_constant_override("separation", 8)
	_cpu_box.add_child(buttons)
	var back := _big_button("<  BACK", Color("b9c6e6"), Vector2(96, 56))
	back.pressed.connect(_set_step.bind(0))
	buttons.add_child(back)
	var fight := _big_button("FIGHT!", Color("e6c26e"), Vector2(196, 56))
	fight.pressed.connect(_start)
	buttons.add_child(fight)
	go.reset_size()
	go.set_anchors_and_offsets_preset(Control.PRESET_BOTTOM_RIGHT, Control.PRESET_MODE_MINSIZE, 28)


func _card(text: String, color: Color) -> Button:
	var b := Button.new()
	b.custom_minimum_size = Vector2(96, 80)
	b.text = text
	b.add_theme_font_size_override("font_size", 15)
	b.focus_mode = Control.FOCUS_NONE
	b.set_meta("color", color)
	b.add_theme_stylebox_override("hover", _style(color, Color(1, 1, 1, 0.6), 2))
	b.add_theme_stylebox_override("pressed", _style(color, Color("e6c26e"), 4))
	return b


func _highlight_cards(current: int) -> void:
	var all: Array[Button] = _cards.duplicate()
	all.append(_random_card)
	for k in all.size():
		var b := all[k]
		var idx := k if k < _cards.size() else RANDOM
		var color: Color = b.get_meta("color")
		var on := idx == current
		b.add_theme_stylebox_override("normal", _style(color, Color("e6c26e"), 4) if on else _style(color.darkened(0.2), Color(1, 1, 1, 0.25), 2))


# --- flow -----------------------------------------------------------------------------

func _set_step(step: int) -> void:
	_step = step
	_random_card.visible = step == 1
	_next_btn.visible = step == 0
	_cpu_box.visible = step == 1
	if step == 0:
		_header.text = "CHOOSE YOUR FIGHTER"
		_header.add_theme_color_override("font_color", Color.WHITE)
		_sub_header.text = "Click a card or use Left / Right.  Drag to rotate.  Enter: next."
		_show(_sel)
	else:
		_header.text = "CHOOSE YOUR OPPONENT"
		_header.add_theme_color_override("font_color", Color("ffb3a8"))
		_sub_header.text = "You: %s.  Pick the CPU's fighter and difficulty.  Enter: fight.  Esc: back." % Roster.CHARACTERS[_sel].look.name
		_show(_cpu)


func _pick(i: int) -> void:
	if _step == 0:
		_sel = i
	else:
		_cpu = i
	_show(i)


func _set_level(i: int) -> void:
	Roster.difficulty = i
	for k in _level_btns.size():
		var c: Color = LEVEL_COLORS[k]
		var on := k == i
		var sb := _style(c if on else c.darkened(0.55), Color.WHITE if on else c, 2, 8)
		_level_btns[k].add_theme_stylebox_override("normal", sb)
		_level_btns[k].add_theme_stylebox_override("hover", _style(c.darkened(0.2), Color.WHITE, 2, 8))
		_level_btns[k].add_theme_color_override("font_color", Color("1a1a2a") if on else Color.WHITE)


## Fill the panel and the turntable for roster index `i` (or RANDOM).
func _show(i: int) -> void:
	_highlight_cards(i)
	if _model:
		_model.queue_free()
		_model = null
	_question.visible = i == RANDOM
	if i == RANDOM:
		_name.text = "Random"
		_title.text = "A surprise opponent"
		_role.text = "Any fighter except yours"
		_desc.text = "The CPU picks someone when the fight starts."
		_stats_box.visible = false
		return
	_stats_box.visible = true
	var ch: Dictionary = Roster.CHARACTERS[i]
	var look: Dictionary = ch.look
	_name.text = look.name
	_title.text = ch.title
	_role.text = ch.role
	_desc.text = ch.desc
	var glow: Color = look.glow
	for s: String in STAT_NAMES:
		var v: int = ch.stats[s]
		var pips: Array = _stat_pips[s]
		for p in 5:
			pips[p].color = glow if p < v else Color(1, 1, 1, 0.15)
	_controls.text = CONTROLS[look.kit]
	for c in _skills_box.get_children():
		c.queue_free()
	var atks := Kits.attacks(look.kit, look.element)
	for key: String in ["z", "x", "c"]:
		var l := _label(11)
		l.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
		l.custom_minimum_size.x = 400
		l.text = "[%s] %s - %s  (%ds)" % [key.to_upper(), atks[key].name, atks[key].desc, int(atks[key].cd)]
		_skills_box.add_child(l)

	_model = Model.new()
	_model.look = look
	_pedestal.add_child(_model)
	_poses = Kits.poses(look.kit)
	_pose_name = "win"
	_pose_t = 0.0


func _start() -> void:
	Roster.player_pick = _sel
	Roster.enemy_pick = _cpu
	get_tree().change_scene_to_file(BATTLE_SCENE)


func _unhandled_input(event: InputEvent) -> void:
	if event is InputEventKey and event.pressed and not event.echo:
		match event.keycode:
			KEY_LEFT, KEY_A:
				_step_pick(-1)
			KEY_RIGHT, KEY_D:
				_step_pick(1)
			KEY_ENTER, KEY_KP_ENTER, KEY_SPACE:
				if _step == 0:
					_set_step(1)
				else:
					_start()
			KEY_ESCAPE:
				if _step == 1:
					_set_step(0)
	elif event is InputEventMouseButton and event.button_index == MOUSE_BUTTON_LEFT:
		_dragging = event.pressed
	elif event is InputEventMouseMotion and _dragging:
		_spin += event.relative.x * 0.01


## Cycle the current step's pick; the CPU step includes Random (shown as index n).
func _step_pick(dir: int) -> void:
	var n := Roster.CHARACTERS.size()
	if _step == 0:
		_pick(posmod(_sel + dir, n))
	else:
		var cur := n if _cpu == RANDOM else _cpu
		var nxt := posmod(cur + dir, n + 1)
		_pick(RANDOM if nxt == n else nxt)


func _process(delta: float) -> void:
	_spin += delta * 0.25
	_pedestal.rotation.y = sin(_spin) * 0.6
	if _model == null:
		return
	# Strike a victory pose when picked, then settle into the fighting stance.
	_pose_t += delta
	if _pose_name == "win" and _pose_t > 1.1:
		_pose_name = "idle"
	_model.blend(_poses[_pose_name], delta, 6.0)
