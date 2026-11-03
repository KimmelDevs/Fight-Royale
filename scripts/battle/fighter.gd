extends Node3D
## Duelist driven by a brain (player input or AI) that sets intents every frame:
##   in_attack tap (release < HOLD_T)  -> normal attack, chains into the kit's combo
##   in_attack hold, then release      -> charged attack (stronger the longer it charged)
##   in_block hold                     -> block; the first parry_window seconds parry
##   in_jump                           -> jump (dodges ground strikes and low bolts)
##   in_skill "z"/"x"/"c"              -> skill, if off cooldown
## The battle listens to `swing` (attack reached its active frame) to resolve its effect.

signal swing(fighter)
signal knocked_out(fighter)
signal landed(fighter)

const Model := preload("res://scripts/battle/fighter_model.gd")
const SwordTrail := preload("res://scripts/battle/sword_trail.gd")
const Kits := preload("res://scripts/battle/kits.gd")

enum S { IDLE, ATTACK, CHARGE, BLOCK, HITSTUN, STAGGER, KO, WIN }

const HOLD_T := 0.22
const CHARGE_MAX := 0.9
const ENGAGE_DIST := 1.45
const MIN_DIST := 0.95
const GUARD_REGEN := 30.0
const GRAVITY := 22.0
const ARENA_RADIUS := 7.0
const SKILL_KEYS := ["z", "x", "c"]

var look: Dictionary
var kit := "knight"
var display_name := ""
## Object with think(fighter, delta). Null = no input (intro / after the round).
var brain
## The other fighter.
var opponent
var model: Model
## Extra yaw on the body so both fighters "cheat" toward the side camera.
var view_bias := 0.0
## AI melee fighters walk into range on their own; the player and mages steer instead.
var auto_approach := true

var in_attack := false
var in_block := false
var in_jump := false
var in_skill := ""
## World-space direction from the brain. Zero = stand still.
var move_dir := Vector3.ZERO

var max_hp := 1000.0
var max_guard := 100.0
var move_speed := 3.2
var walk_speed := 2.6
var parry_window := 0.16
var jump_velocity := 7.0
var attacks: Dictionary
var poses: Dictionary

var state := S.IDLE
var state_t := 0.0
var hp := 1000.0
var guard := 100.0
var atk: Dictionary = {}
var atk_id := ""
var atk_phase := 0  # 0 windup, 1 active, 2 recovery
var atk_power := 1.0
## Increments on every new attack so the AI can react once per swing.
var swing_serial := 0
var last_damage := 0.0
var last_crit := false
var cooldowns := {"z": 0.0, "x": 0.0, "c": 0.0}
var on_ground := true
var vel_y := 0.0
## While > 0, every hit is absorbed (Bubble Ward).
var ward_t := 0.0
## While > 0, attacks pass through (blinks).
var invuln_t := 0.0

var _stun := 0.0
var _stun_pose := "hit"
var _combo_next := "l1"
var _combo_timer := 0.0
var _buffered := false
var _atk_prev := false
var _jump_prev := false
var _holding := false
var _hold_t := 0.0
var _guard_delay := 0.0
var _knock := 0.0
var _trail: SwordTrail


func _ready() -> void:
	kit = look.get("kit", "knight")
	display_name = look.name
	var st: Dictionary = Kits.STATS[kit]
	max_hp = st.hp
	max_guard = st.guard
	move_speed = st.move
	walk_speed = st.walk
	parry_window = st.parry
	jump_velocity = st.jump
	hp = max_hp
	guard = max_guard
	attacks = Kits.attacks(kit, look.get("element", "none"))
	poses = Kits.poses(kit)
	model = Model.new()
	model.look = look
	add_child(model)
	_trail = SwordTrail.new()
	_trail.base_node = model.blade_base
	_trail.tip_node = model.blade_tip
	_trail.color = look.glow
	add_child(_trail)


func _physics_process(delta: float) -> void:
	in_attack = false
	in_block = false
	in_jump = false
	in_skill = ""
	move_dir = Vector3.ZERO
	if brain and state != S.KO and state != S.WIN:
		brain.think(self, delta)
	if not on_ground:
		in_block = false
	state_t += delta
	for k: String in cooldowns:
		cooldowns[k] = maxf(cooldowns[k] - delta, 0.0)
	ward_t = maxf(ward_t - delta, 0.0)
	invuln_t = maxf(invuln_t - delta, 0.0)
	_read_attack_button(delta)
	_read_jump()
	_read_skill()

	match state:
		S.IDLE:
			_combo_timer -= delta
			if _combo_timer <= 0.0:
				_combo_next = "l1"
			if in_block:
				_set_state(S.BLOCK)
		S.ATTACK:
			_attack_step()
		S.CHARGE:
			if in_block:
				_holding = false
				_set_state(S.BLOCK)
			elif state_t >= CHARGE_MAX:
				_holding = false
				_start_attack("heavy")
		S.BLOCK:
			if not in_block:
				_set_state(S.IDLE)
		S.HITSTUN, S.STAGGER:
			if state_t >= _stun:
				_set_state(S.IDLE)

	_move(delta)
	_vertical(delta)
	if state != S.BLOCK:
		_guard_delay -= delta
		if _guard_delay <= 0.0:
			guard = minf(guard + GUARD_REGEN * delta, max_guard)
	_trail.emitting = state == S.ATTACK and atk.type == "melee" and (atk_phase == 1 or (atk_phase == 0 and state_t > atk.wind * 0.6) or (atk_phase == 2 and state_t < atk.wind + atk.active + 0.05))
	model.set_barrier(state == S.BLOCK)
	model.charge = clampf(state_t / CHARGE_MAX, 0.0, 1.0) if state == S.CHARGE else move_toward(model.charge, 0.0, delta * 4.0)
	_pose(delta)


# --- input -> actions ---------------------------------------------------------

func _read_attack_button(delta: float) -> void:
	var pressed := in_attack and not _atk_prev
	var released := not in_attack and _atk_prev
	_atk_prev = in_attack
	if state in [S.HITSTUN, S.STAGGER, S.KO, S.WIN]:
		_holding = false
		return
	if pressed:
		_holding = true
		_hold_t = 0.0
	if _holding:
		_hold_t += delta
		if _hold_t >= HOLD_T and state == S.IDLE and not in_block:
			_set_state(S.CHARGE)
	if released and _holding:
		_holding = false
		if state == S.CHARGE:
			_start_attack("heavy")
		elif _hold_t < HOLD_T:
			_request_light()


func _read_jump() -> void:
	var pressed := in_jump and not _jump_prev
	_jump_prev = in_jump
	if pressed and on_ground and state in [S.IDLE, S.BLOCK]:
		vel_y = jump_velocity
		on_ground = false
		if state == S.BLOCK:
			_set_state(S.IDLE)


func _read_skill() -> void:
	if in_skill == "" or cooldowns.get(in_skill, 1.0) > 0.0:
		return
	var free := state in [S.IDLE, S.BLOCK, S.CHARGE] or (state == S.ATTACK and atk_phase == 2)
	if not free:
		return
	_holding = false
	cooldowns[in_skill] = attacks[in_skill].cd
	_start_attack(in_skill)


func _request_light() -> void:
	if state == S.IDLE or state == S.BLOCK:
		_start_attack(_combo_next if _combo_timer > 0.0 else "l1")
	elif state == S.ATTACK and atk.next != "":
		_buffered = true


func _start_attack(id: String) -> void:
	atk_power = 1.0
	if id == "heavy" and state == S.CHARGE:
		atk_power = lerpf(1.0, 1.5, clampf(state_t / CHARGE_MAX, 0.0, 1.0))
	atk_id = id
	atk = attacks[id]
	atk_phase = 0
	_buffered = false
	swing_serial += 1
	if atk.self_jump > 0.0:
		vel_y = atk.self_jump
		on_ground = false
	_set_state(S.ATTACK)


func _attack_step() -> void:
	var w: float = atk.wind
	var a: float = atk.active
	var r: float = atk.recover
	if atk_phase == 0 and state_t >= w:
		atk_phase = 1
		swing.emit(self)
	elif atk_phase == 1 and state_t >= w + a:
		atk_phase = 2
	elif atk_phase == 2:
		if _buffered and atk.next != "" and state_t >= w + a + minf(0.1, r):
			_start_attack(atk.next)
		elif in_block and state_t >= w + a + 0.06:
			_finish_attack()
			_set_state(S.BLOCK)
		elif state_t >= w + a + r:
			_finish_attack()
			_set_state(S.IDLE)


func _finish_attack() -> void:
	_combo_next = atk.next if atk.next != "" else "l1"
	_combo_timer = 0.45 if atk.next != "" else 0.0


func _set_state(s: S) -> void:
	state = s
	state_t = 0.0


# --- movement -------------------------------------------------------------------

func _move(delta: float) -> void:
	if opponent == null:
		return
	var to: Vector3 = opponent.global_position - global_position
	to.y = 0.0
	var dist := to.length()
	var dir := to / maxf(dist, 0.001)
	if state != S.KO:
		rotation.y = lerp_angle(rotation.y, atan2(dir.x, dir.z), 1.0 - exp(-12.0 * delta))
	var v := 0.0
	var walking := false
	if state == S.IDLE and auto_approach and dist > ENGAGE_DIST and opponent.state != S.KO:
		v = walk_speed
		walking = true
	if state == S.ATTACK and atk_phase <= 1 and dist > MIN_DIST + 0.15:
		v += float(atk.lunge)
	_knock = move_toward(_knock, 0.0, 14.0 * delta)
	v -= _knock
	if dist < MIN_DIST and v > 0.0:
		v = 0.0
	global_position += dir * v * delta
	# Steering: full speed when free, slower while blocking or charging, none mid-swing.
	var steer := 0.0
	match state:
		S.IDLE:
			steer = 1.0
		S.BLOCK:
			steer = 0.5
		S.CHARGE:
			steer = 0.4
	if steer > 0.0 and move_dir != Vector3.ZERO:
		var step := move_dir.normalized() * move_speed * steer * delta
		# Don't walk through the opponent.
		if dist < MIN_DIST and step.dot(dir) > 0.0:
			step -= dir * step.dot(dir)
		global_position += step
		walking = on_ground
	if dist < MIN_DIST * 0.9:
		global_position -= dir * (MIN_DIST * 0.9 - dist) * 0.5
	var flat := Vector2(global_position.x, global_position.z)
	if flat.length() > ARENA_RADIUS:
		flat = flat.normalized() * ARENA_RADIUS
		global_position = Vector3(flat.x, global_position.y, flat.y)
	model.walk = move_toward(model.walk, 1.0 if walking else 0.0, delta * 6.0)
	if state != S.KO:
		model.rotation.y = view_bias


func _vertical(delta: float) -> void:
	if on_ground:
		return
	vel_y -= GRAVITY * delta
	position.y += vel_y * delta
	if position.y <= 0.0:
		position.y = 0.0
		vel_y = 0.0
		on_ground = true
		model.recoil = 0.35
		landed.emit(self)


## Instant reposition (blink skills).
func teleport(to: Vector3) -> void:
	var flat := Vector2(to.x, to.z)
	if flat.length() > ARENA_RADIUS:
		flat = flat.normalized() * ARENA_RADIUS
	global_position = Vector3(flat.x, global_position.y, flat.y)
	invuln_t = 0.3
	if opponent:
		var d: Vector3 = opponent.global_position - global_position
		rotation.y = atan2(d.x, d.z)


# --- getting hit ------------------------------------------------------------------

## Resolves an incoming attack. Returns "miss", "warded", "parry", "blocked", "guard_break",
## "hit", "crit" or "ko".
func receive_hit(_attacker, a: Dictionary, power: float) -> String:
	if state == S.KO:
		return "none"
	if invuln_t > 0.0:
		return "miss"
	if ward_t > 0.0:
		model.recoil = 0.4
		return "warded"
	var dmg: float = a.dmg * power
	if state == S.BLOCK:
		if state_t <= parry_window:
			guard = minf(guard + 20.0, max_guard)
			model.flash(Color(0.6, 0.9, 1.0), 0.18)
			return "parry"
		guard -= a.guard * power
		_guard_delay = 1.0
		if guard <= 0.0:
			guard = 0.0
			last_damage = dmg * 0.4
			last_crit = false
			hp = maxf(hp - last_damage, 0.0)
			_knock = 3.5
			if hp <= 0.0:
				_ko()
				return "ko"
			stagger(1.1)
			model.flash(Color(1.0, 0.85, 0.4), 0.2)
			return "guard_break"
		_knock = a.knock * 0.5
		model.recoil = 0.7
		return "blocked"

	last_crit = randf() < 0.2
	if last_crit:
		dmg *= 1.6
	last_damage = dmg
	hp = maxf(hp - dmg, 0.0)
	_knock = a.knock
	model.flash()
	if hp <= 0.0:
		_ko()
		return "ko"
	if a.heavy or a.stagger:
		stagger(a.stun)
	else:
		_stun = a.stun
		_stun_pose = "hit"
		_holding = false
		_set_state(S.HITSTUN)
	return "crit" if last_crit else "hit"


func stagger(duration: float) -> void:
	_stun = duration
	_stun_pose = "stagger"
	_holding = false
	_set_state(S.STAGGER)


## Both blades met: bounce apart.
func clash_recoil() -> void:
	_stun = 0.38
	_stun_pose = "clash"
	_holding = false
	_knock = 4.0
	model.recoil = 1.0
	_set_state(S.HITSTUN)


func win() -> void:
	if state != S.KO:
		_set_state(S.WIN)


func _ko() -> void:
	_set_state(S.KO)
	model.fall()
	knocked_out.emit(self)


# --- posing -----------------------------------------------------------------------

func _pose(delta: float) -> void:
	var pose: String = "idle"
	var speed := 14.0
	match state:
		S.IDLE:
			if not on_ground:
				pose = "jump"
				speed = 12.0
		S.BLOCK:
			pose = "block"
			speed = 30.0
		S.CHARGE:
			pose = attacks.heavy.pose_w
			speed = 10.0
		S.ATTACK:
			if atk_phase == 0:
				pose = atk.pose_w
				speed = 22.0
			elif atk_phase == 1:
				pose = atk.pose_s
				speed = 45.0
			elif state_t < atk.wind + atk.active + atk.recover * 0.5:
				pose = atk.pose_s
				speed = 20.0
			else:
				speed = 9.0
		S.HITSTUN, S.STAGGER:
			pose = _stun_pose
			speed = 28.0
		S.KO:
			pose = "stagger"
			speed = 10.0
		S.WIN:
			pose = "win"
			speed = 6.0
	model.blend(poses[pose], delta, speed)
