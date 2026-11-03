extends Node3D
## 1v1 duel: player (left) vs AI (right), using the picks from the character select.
## Turns each attack's active frame into its effect (melee hit, projectiles, area strikes,
## buffs, blinks), resolves blocks / parries / clashes, and drives feel, camera and rounds.

const World := preload("res://scripts/world.gd")
const Roster := preload("res://scripts/roster.gd")
const Fighter := preload("res://scripts/battle/fighter.gd")
const PlayerBrain := preload("res://scripts/battle/player_brain.gd")
const AiBrain := preload("res://scripts/battle/ai_brain.gd")
const Hud := preload("res://scripts/battle/battle_hud.gd")
const Fx := preload("res://scripts/battle/combat_fx.gd")
const Projectile := preload("res://scripts/battle/projectile.gd")
const Vfx := preload("res://scripts/vfx.gd")

const S := Fighter.S
const SPAWN_GAP := 4.0
## Clash if the defender's own blade is this close (seconds) to its active frame.
const CLASH_WINDOW := 0.08
const SELECT_SCENE := "res://select.tscn"

var p1
var p2
var hud: Hud
var cam: Camera3D

var _trauma := 0.0
var _shake_t := 0.0
var _stop_serial := 0
var _round := 0
var _round_over := false
var _can_restart := false


func _ready() -> void:
	World.bind_mouse("attack", MOUSE_BUTTON_RIGHT)
	World.bind_mouse("block", MOUSE_BUTTON_LEFT)
	World.bind_keys("move_forward", [KEY_W, KEY_UP])
	World.bind_keys("move_back", [KEY_S, KEY_DOWN])
	World.bind_keys("move_left", [KEY_A, KEY_LEFT])
	World.bind_keys("move_right", [KEY_D, KEY_RIGHT])
	World.bind_keys("jump", [KEY_SPACE])
	World.bind_keys("skill_z", [KEY_Z])
	World.bind_keys("skill_x", [KEY_X])
	World.bind_keys("skill_c", [KEY_C])
	World.build(self)
	_build_arena()
	cam = Camera3D.new()
	cam.fov = 50.0
	add_child(cam)
	cam.make_current()
	hud = Hud.new()
	add_child(hud)
	_start_round()


func _build_arena() -> void:
	var mi := MeshInstance3D.new()
	var t := TorusMesh.new()
	t.inner_radius = Fighter.ARENA_RADIUS + 0.35
	t.outer_radius = Fighter.ARENA_RADIUS + 0.5
	t.rings = 96
	t.ring_segments = 6
	mi.mesh = t
	var m := StandardMaterial3D.new()
	m.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	m.albedo_color = Color("e6c26e")
	mi.material_override = m
	mi.scale = Vector3(1, 0.15, 1)
	add_child(mi)


func _start_round() -> void:
	for f in [p1, p2]:
		if f != null and is_instance_valid(f):
			f.queue_free()
	for n in get_tree().get_nodes_in_group("projectiles") + get_tree().get_nodes_in_group("strikes"):
		n.queue_free()
	_round += 1
	_round_over = false
	_can_restart = false
	Engine.time_scale = 1.0

	p1 = Fighter.new()
	p1.look = Roster.look(Roster.player_pick)
	p1.position = Vector3(-SPAWN_GAP * 0.5, 0, 0)
	p2 = Fighter.new()
	p2.look = Roster.look(Roster.resolve_enemy())
	p2.position = Vector3(SPAWN_GAP * 0.5, 0, 0)
	p1.opponent = p2
	p2.opponent = p1
	for f in [p1, p2]:
		add_child(f)
		f.swing.connect(_on_swing)
		f.knocked_out.connect(_on_ko)
		f.landed.connect(_on_landed)
	p1.rotation.y = PI / 2.0
	p2.rotation.y = -PI / 2.0
	# Turn bodies toward the camera (on +Z) so faces read. Mirrored signs because
	# the fighters face opposite ways.
	p1.view_bias = -0.85
	p2.view_bias = 0.85
	p1.auto_approach = false
	p2.auto_approach = p2.kit != "mage"
	hud.bind(p1, p2, "CPU - " + AiBrain.LEVELS[Roster.difficulty])
	_snap_camera()

	var round_id := _round
	hud.show_banner("READY", Color("ffe9a8"), "", 0.6)
	await get_tree().create_timer(1.0).timeout
	if round_id != _round:
		return
	hud.show_banner("FIGHT!", Color("ffffff"), "", 0.5)
	p1.brain = PlayerBrain.new()
	var ai := AiBrain.new()
	ai.configure(Roster.difficulty)
	p2.brain = ai


func _unhandled_input(event: InputEvent) -> void:
	if event is InputEventKey and event.pressed and event.keycode == KEY_ESCAPE:
		Engine.time_scale = 1.0
		get_tree().change_scene_to_file(SELECT_SCENE)
	elif _can_restart and event is InputEventMouseButton and event.pressed:
		_start_round()


# --- attack resolution ------------------------------------------------------------

func _on_swing(attacker) -> void:
	var defender = attacker.opponent
	if defender == null or defender.state == S.KO:
		return
	var a: Dictionary = attacker.atk
	match a.type:
		"projectile":
			_fire_projectiles(attacker, a)
		"strike":
			_run_strike(attacker, a, attacker.atk_power)
		"buff":
			_apply_buff(attacker, a)
		"blink":
			_blink(attacker, a)
		_:
			_melee(attacker, defender, a)


func _melee(attacker, defender, a: Dictionary) -> void:
	var to: Vector3 = defender.global_position - attacker.global_position
	var dy := absf(to.y)
	to.y = 0.0
	var dist := to.length()
	var dir := to / maxf(dist, 0.001)
	var contact: Vector3 = attacker.global_position + dir * minf(dist * 0.5, 0.8) + Vector3.UP * 1.15

	# Clash: both blades are coming in at the same moment.
	var d_swinging: bool = defender.state == S.ATTACK and defender.atk.type == "melee" and (defender.atk_phase == 1 or
		(defender.atk_phase == 0 and float(defender.atk.wind) - defender.state_t <= CLASH_WINDOW))
	if d_swinging and dist <= float(a.reach) + 0.3 and dy < 0.8:
		_clash(attacker, defender, contact)
		return
	if dist > float(a.reach) or dy > 1.1:
		return
	var hit_pos: Vector3 = defender.global_position - dir * 0.15 + Vector3.UP * 1.1
	_apply_hit(attacker, defender, a, attacker.atk_power, hit_pos, dir, false)


func _fire_projectiles(attacker, a: Dictionary) -> void:
	var defender = attacker.opponent
	var origin: Vector3 = attacker.model.cast_point.global_position
	var aim: Vector3 = defender.global_position + Vector3(0, 1.1, 0) - origin
	var base := aim.normalized()
	var count: int = a.count
	for i in count:
		var off := 0.0 if count == 1 else lerpf(-a.spread, a.spread, float(i) / (count - 1))
		var p := Projectile.new()
		p.shooter = attacker
		p.target = defender
		p.atk = a
		p.power = attacker.atk_power
		p.color = attacker.look.glow
		p.velocity = base.rotated(Vector3.UP, off) * float(a.speed)
		p.on_hit = _on_projectile_hit
		add_child(p)
		p.global_position = origin
	var g: Color = attacker.look.glow
	Fx.flash(self, origin, Color(g.r, g.g, g.b, 0.7), 0.25, 0.1)


func _on_projectile_hit(p) -> void:
	var defender = p.target
	var dir: Vector3 = p.velocity
	dir.y = 0.0
	_impact_fx(p.atk, p.global_position, p.color, 0.7)
	_apply_hit(p.shooter, defender, p.atk, p.power, p.global_position, dir.normalized(), true)


## Area attack(s) at the target (or around the caster) after a telegraphed delay.
func _run_strike(attacker, a: Dictionary, power: float) -> void:
	var round_id := _round
	var color: Color = attacker.look.glow
	var count: int = a.repeat
	for i in count:
		var defender = attacker.opponent
		if round_id != _round or defender == null or not is_instance_valid(defender):
			return
		var src = attacker if a.at == "self" else defender
		var center: Vector3 = src.global_position
		center.y = 0.0
		var wait: float = a.delay if i == 0 else a.interval
		var tele := Fx.telegraph(self, center, color, a.radius)
		tele.add_to_group("strikes")
		tele.set_meta("target", defender)
		tele.set_meta("land_time", Time.get_ticks_msec() / 1000.0 + wait)
		match a.style:
			"meteor":
				Fx.meteor(self, center, color, wait)
			"requiem":
				_requiem_orb(center, wait)
		await get_tree().create_timer(wait).timeout
		if is_instance_valid(tele):
			tele.queue_free()
		if round_id != _round or not is_instance_valid(attacker):
			return
		_impact_fx(a, center, color, a.radius)
		defender = attacker.opponent
		if defender == null or defender.state == S.KO:
			continue
		var to: Vector3 = defender.global_position - center
		var lifted: bool = defender.global_position.y > 0.7
		to.y = 0.0
		if to.length() <= float(a.radius) and not lifted:
			var dir: Vector3 = to.normalized() if to.length() > 0.05 else (defender.global_position - attacker.global_position).normalized()
			dir.y = 0.0
			_apply_hit(attacker, defender, a, power, defender.global_position + Vector3.UP * 1.0, dir, true)
		elif to.length() <= float(a.radius) + 1.0:
			Fx.number(self, defender.global_position + Vector3.UP * 1.9, "DODGE", Color("c9d3e6"), 0.7)


func _requiem_orb(center: Vector3, wait: float) -> void:
	var orb := Vfx.big_orb(self)
	orb.global_position = center + Vector3(0, 4.0, 0)
	orb.scale = Vector3.ONE * 0.1
	var tw := orb.create_tween()
	tw.tween_property(orb, "scale", Vector3.ONE * 1.1, wait * 0.7).set_trans(Tween.TRANS_BACK).set_ease(Tween.EASE_OUT)
	tw.tween_property(orb, "global_position", center + Vector3(0, 0.6, 0), wait * 0.3).set_trans(Tween.TRANS_QUAD).set_ease(Tween.EASE_IN)
	tw.tween_callback(orb.queue_free)


func _impact_fx(a: Dictionary, pos: Vector3, color: Color, radius: float) -> void:
	var ground := Vector3(pos.x, 0.0, pos.z)
	match a.style:
		"explosion", "meteor":
			Fx.explosion(self, ground, color, radius)
			add_trauma(0.35 if a.style == "explosion" else 0.6)
		"lightning":
			Fx.lightning(self, ground, color)
			Fx.flash(self, ground + Vector3.UP * 0.4, Color(1.0, 0.95, 0.7, 0.9), radius * 0.6, 0.15)
			Fx.sparks(self, ground + Vector3.UP * 0.2, color, 30, 7.0, Vector3.UP)
			Fx.ring(self, ground, color, radius * 1.3, 0.3)
			add_trauma(0.3)
		"tide":
			Vfx.wave_ring(self, ground, radius * 2.2, 0.6)
			for i in 8:
				var ang := TAU * i / 8.0
				Vfx.geyser(self, ground + Vector3(cos(ang), 0, sin(ang)) * radius * 0.8, 1.8, 0.03 * i)
			add_trauma(0.3)
		"requiem":
			Vfx.wave_ring(self, ground, radius * 3.5, 1.0)
			Vfx.splash(self, ground + Vector3.UP * 0.3, 50, 2.2)
			for i in 10:
				var ang := TAU * i / 10.0
				Vfx.geyser(self, ground + Vector3(cos(ang), 0, sin(ang)) * radius, 2.6, 0.05)
			add_trauma(0.7)
		_:
			match a.element:
				"water":
					Vfx.splash(self, pos, 18, 1.0 if a.size < 2.0 else 2.0)
				"fire":
					Fx.flash(self, pos, Color(1.0, 0.6, 0.2, 0.8), 0.35 * a.size, 0.14)
					Fx.sparks(self, pos, color, 16, 5.0)
				"electric":
					Fx.sparks(self, pos, Color(1.0, 0.95, 0.6), 20, 8.0)
				_:
					Fx.sparks(self, pos, color, 14, 5.0)


func _apply_buff(attacker, a: Dictionary) -> void:
	if a.mode == "ward":
		attacker.ward_t = a.duration
		var bubble := Vfx.bubble(attacker)
		var round_id := _round
		await get_tree().create_timer(a.duration).timeout
		if is_instance_valid(bubble):
			if round_id == _round:
				Vfx.splash(self, bubble.global_position, 30, 1.4)
			bubble.queue_free()


func _blink(attacker, a: Dictionary) -> void:
	var defender = attacker.opponent
	var color: Color = attacker.look.glow
	var from: Vector3 = attacker.global_position
	var d: Vector3 = defender.global_position - from
	d.y = 0.0
	d = d.normalized()
	var to := from - d * 3.0
	if a.mode == "behind":
		to = defender.global_position + d * 1.3
	Fx.smoke(self, from, color)
	attacker.teleport(to)
	Fx.smoke(self, attacker.global_position, color)


## Shared hit result handling for every delivery type.
func _apply_hit(attacker, defender, a: Dictionary, power: float, hit_pos: Vector3, dir: Vector3, ranged: bool) -> void:
	var result: String = defender.receive_hit(attacker, a, power)
	var glow: Color = attacker.look.glow
	var heavy: bool = a.heavy or a.id == "l3"
	match result:
		"hit", "crit", "ko":
			var crit: bool = defender.last_crit
			Fx.sparks(self, hit_pos, glow, 30 if heavy else 18, 8.0 if heavy else 6.0, dir)
			Fx.flash(self, hit_pos, Color(glow.r, glow.g, glow.b, 0.8), 0.45 if heavy else 0.3)
			if a.heavy:
				Fx.ring(self, hit_pos, glow, 2.2)
			var txt := "%d" % roundi(defender.last_damage)
			Fx.number(self, hit_pos + Vector3.UP * 0.5, txt + ("!" if crit else ""),
				Color("ffb347") if crit else Color.WHITE, 1.5 if crit else 1.0)
			add_trauma(0.5 if a.heavy else (0.3 if heavy else 0.18))
			hit_stop(0.11 if a.heavy else (0.07 if heavy else 0.045))
		"blocked":
			var shield_pos: Vector3 = defender.model.shield_node.global_position
			Fx.sparks(self, shield_pos, Color("ffd27a"), 16, 5.0, -dir + Vector3.UP * 0.3)
			Fx.flash(self, shield_pos, Color(1.0, 0.85, 0.5, 0.6), 0.35, 0.1)
			Fx.number(self, shield_pos + Vector3.UP * 0.4, "BLOCK", Color("c9d3e6"), 0.7)
			if not ranged:
				attacker.model.recoil = 0.6
			add_trauma(0.14)
			hit_stop(0.04)
		"parry":
			var shield_pos: Vector3 = defender.model.shield_node.global_position
			# Ranged parries deflect; melee parries also stagger the attacker.
			if not ranged:
				attacker.stagger(0.95)
			Fx.sparks(self, shield_pos, Color("aee9ff"), 40, 9.0)
			Fx.flash(self, shield_pos, Color(0.7, 0.95, 1.0, 0.9), 0.5, 0.2)
			Fx.ring(self, shield_pos, Color(0.7, 0.95, 1.0, 0.9), 1.6)
			Fx.number(self, shield_pos + Vector3.UP * 0.5, "PARRY!", Color("8fe6ff"), 1.4)
			add_trauma(0.4)
			slow_mo(0.3, 0.35)
		"guard_break":
			Fx.sparks(self, hit_pos, Color("ffb347"), 40, 9.0)
			Fx.flash(self, hit_pos, Color(1.0, 0.7, 0.3, 0.9), 0.5, 0.2)
			Fx.number(self, hit_pos + Vector3.UP * 0.55, "GUARD BREAK", Color("ff8a50"), 1.2)
			add_trauma(0.55)
			hit_stop(0.12)
		"warded":
			Fx.flash(self, hit_pos, Color(0.5, 0.85, 1.0, 0.7), 0.5, 0.15)
			Fx.number(self, hit_pos + Vector3.UP * 0.5, "ABSORBED", Color("8fe6ff"), 0.8)
			add_trauma(0.12)
		"miss":
			Fx.number(self, hit_pos + Vector3.UP * 0.5, "MISS", Color("c9d3e6"), 0.8)


func _clash(a, b, pos: Vector3) -> void:
	a.clash_recoil()
	b.clash_recoil()
	Fx.sparks(self, pos, Color("fff2c0"), 50, 10.0)
	Fx.sparks(self, pos, a.look.glow, 16, 7.0)
	Fx.sparks(self, pos, b.look.glow, 16, 7.0)
	Fx.flash(self, pos, Color(1.0, 0.95, 0.8, 0.95), 0.55, 0.18)
	Fx.ring(self, pos, Color(1.0, 0.9, 0.6, 0.9), 3.0, 0.45)
	Fx.number(self, pos + Vector3.UP * 0.45, "CLASH!", Color("ffe08a"), 1.3)
	add_trauma(0.45)
	hit_stop(0.13)


func _on_landed(f) -> void:
	Fx.ring(self, f.global_position, Color(1, 1, 1, 0.5), 0.8, 0.25)


func _on_ko(loser) -> void:
	if _round_over:
		return
	_round_over = true
	var winner = loser.opponent
	for f in [p1, p2]:
		f.brain = null
	add_trauma(0.8)
	slow_mo(0.25, 0.9)
	await get_tree().create_timer(0.6, true, false, true).timeout
	winner.win()
	if winner == p1:
		hud.show_banner("VICTORY", Color("ffe08a"), "Click to fight again  -  Esc for character select")
	else:
		hud.show_banner("DEFEAT", Color("ff7b7b"), "Click to try again  -  Esc for character select")
	await get_tree().create_timer(0.8, true, false, true).timeout
	_can_restart = true


# --- feel ---------------------------------------------------------------------------

func add_trauma(amount: float) -> void:
	_trauma = clampf(_trauma + amount, 0.0, 1.0)


## Freeze-frame on impact. Timer ignores time scale so it always resumes.
func hit_stop(duration: float) -> void:
	_stop_serial += 1
	var serial := _stop_serial
	Engine.time_scale = 0.03
	await get_tree().create_timer(duration, true, false, true).timeout
	if serial == _stop_serial:
		Engine.time_scale = 1.0


func slow_mo(scale: float, duration: float) -> void:
	_stop_serial += 1
	var serial := _stop_serial
	Engine.time_scale = scale
	await get_tree().create_timer(duration, true, false, true).timeout
	if serial == _stop_serial:
		Engine.time_scale = 1.0


# --- camera ---------------------------------------------------------------------------

func _camera_goal() -> Array:
	var mid: Vector3 = (p1.global_position + p2.global_position) * 0.5
	var d: Vector3 = p2.global_position - p1.global_position
	d.y = 0.0
	var sep := d.length()
	d = d / sep if sep > 0.01 else Vector3.RIGHT
	# Side-on view with the player on the left, pulled slightly behind the player.
	var side := Vector3(-d.z, 0.0, d.x)
	var dist := 3.4 + sep * 0.6
	var lift := mid.y * 0.5
	mid.y = 0.0
	return [mid + side * dist - d * 0.5 + Vector3.UP * (1.45 + lift), mid + Vector3.UP * (1.0 + lift)]


func _snap_camera() -> void:
	var g := _camera_goal()
	cam.global_position = g[0]
	cam.look_at(g[1], Vector3.UP)


func _process(delta: float) -> void:
	if p1 == null or not is_instance_valid(p1) or not is_instance_valid(p2):
		return
	# Real-time delta so the camera keeps moving smoothly during hit-stop.
	var rd := delta / maxf(Engine.time_scale, 0.001)
	rd = minf(rd, 0.05)
	var g := _camera_goal()
	cam.global_position = cam.global_position.lerp(g[0], 1.0 - exp(-5.0 * rd))
	cam.look_at(g[1], Vector3.UP)
	_trauma = maxf(_trauma - 1.4 * rd, 0.0)
	var shake := _trauma * _trauma
	_shake_t += rd * 32.0
	cam.h_offset = 0.22 * shake * sin(_shake_t * 1.7)
	cam.v_offset = 0.16 * shake * sin(_shake_t * 2.3)
	cam.rotate_object_local(Vector3.FORWARD, 0.04 * shake * sin(_shake_t * 1.1))
