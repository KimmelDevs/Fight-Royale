extends RefCounted
## Opponent AI. Presses the same virtual buttons a player would, with human-ish reaction times.
## Reacts once to each enemy swing / projectile / ground marker (block, parry, jump, sidestep),
## keeps its preferred range (mages kite), and picks attacks and skills when idle.

const Fighter := preload("res://scripts/battle/fighter.gd")
const S := Fighter.S

const LEVELS := ["Easy", "Normal", "Hard", "Master"]
## Per difficulty: block / parry / jump-dodge odds, reaction window, how long it waits
## between attacks, between skills, and the longest combo it will throw.
const PRESETS := [
	{"block": 0.2, "parry": 0.0, "jump": 0.1, "react": Vector2(0.3, 0.5), "think": 1.8, "skill": Vector2(3.5, 6.0), "combo": 2},
	{"block": 0.38, "parry": 0.06, "jump": 0.22, "react": Vector2(0.18, 0.34), "think": 1.25, "skill": Vector2(2.0, 3.8), "combo": 3},
	{"block": 0.5, "parry": 0.14, "jump": 0.3, "react": Vector2(0.12, 0.26), "think": 1.0, "skill": Vector2(1.2, 2.6), "combo": 4},
	{"block": 0.65, "parry": 0.3, "jump": 0.45, "react": Vector2(0.08, 0.16), "think": 0.7, "skill": Vector2(0.8, 1.6), "combo": 4},
]

var block_chance := 0.5
var parry_chance := 0.14
var jump_chance := 0.3
var reaction_min := 0.12
var reaction_max := 0.26
var think_scale := 1.0
var skill_wait := Vector2(1.2, 2.6)
var max_combo := 4

var _queue: Array = []  # [[wait_before_press, hold_duration], ...]
var _hold := 0.0
var _block_wait := -1.0
var _block_dur := 0.0
var _block_hold := 0.0
var _jump_wait := -1.0
var _side_t := 0.0
var _side_sign := 1.0
var _strafe_t := 0.0
var _think_cd := 1.0
var _skill_cd := 2.0
var _seen_swing := -1
var _seen_charge := false
var _seen := {}  # projectiles and markers already reacted to


func configure(level: int) -> void:
	var p: Dictionary = PRESETS[clampi(level, 0, PRESETS.size() - 1)]
	block_chance = p.block
	parry_chance = p.parry
	jump_chance = p.jump
	reaction_min = p.react.x
	reaction_max = p.react.y
	think_scale = p.think
	skill_wait = p.skill
	max_combo = p.combo


func think(f, delta: float) -> void:
	var o = f.opponent
	if o == null or o.state == S.KO:
		return
	_react(f, o)
	_dodge(f)
	_position(f, o, delta)
	_plan_offense(f, o, delta)

	if _jump_wait >= 0.0:
		_jump_wait -= delta
		if _jump_wait < 0.0:
			f.in_jump = true

	# Block button.
	if _block_wait >= 0.0:
		_block_wait -= delta
		if _block_wait < 0.0:
			_block_hold = _block_dur
	if _block_hold > 0.0:
		_block_hold -= delta
		f.in_block = true
		_queue.clear()
		_hold = 0.0
		return

	# Attack button: hold for the scheduled time, release, then wait for the next press.
	if _hold > 0.0:
		_hold -= delta
		f.in_attack = _hold > 0.0
	elif not _queue.is_empty():
		_queue[0][0] -= delta
		if _queue[0][0] <= 0.0:
			_hold = _queue[0][1]
			_queue.pop_front()
			f.in_attack = true


func _react(f, o) -> void:
	var swinging: bool = o.state == S.ATTACK and o.atk_phase == 0 and o.atk.type == "melee"
	if swinging and o.swing_serial != _seen_swing:
		_seen_swing = o.swing_serial
		if f.state in [S.HITSTUN, S.STAGGER]:
			return
		var time_to_hit: float = float(o.atk.wind) - o.state_t
		var roll := randf()
		var bc := block_chance * (0.75 if o.atk.heavy else 1.0)
		if roll < parry_chance:
			_schedule_block(maxf(time_to_hit - 0.07, 0.0), 0.3)
		elif roll < parry_chance + bc:
			_schedule_block(randf_range(reaction_min, reaction_max) * 0.6, time_to_hit + 0.45)
		elif f.kit != "knight" and roll < parry_chance + bc + 0.2:
			_try_skill(f, "z", true)
	var charging: bool = o.state == S.CHARGE
	if charging and not _seen_charge:
		_seen_charge = true
		if randf() < 0.45:
			_schedule_block(randf_range(reaction_min, reaction_max), 1.4)
	elif not charging:
		_seen_charge = false


## Incoming projectiles: block or jump. Ground markers on us: sidestep or jump at the end.
func _dodge(f) -> void:
	for p in f.get_tree().get_nodes_in_group("projectiles"):
		if p.target != f or _seen.has(p.get_instance_id()):
			continue
		_seen[p.get_instance_id()] = true
		var to_me: Vector3 = f.global_position + Vector3(0, 1.1, 0) - p.global_position
		var speed: float = maxf(p.velocity.length(), 0.1)
		var eta: float = to_me.length() / speed
		var roll := randf()
		if roll < jump_chance and f.on_ground:
			_jump_wait = maxf(eta - 0.28, 0.0)
		elif roll < jump_chance + block_chance:
			_schedule_block(clampf(eta - 0.2, 0.0, reaction_max), eta + 0.2)
	for m in f.get_tree().get_nodes_in_group("strikes"):
		if m.get_meta("target") != f or _seen.has(m.get_instance_id()):
			continue
		_seen[m.get_instance_id()] = true
		var eta: float = float(m.get_meta("land_time")) - Time.get_ticks_msec() / 1000.0
		if randf() < 0.6:
			_side_t = clampf(eta, 0.3, 0.8)
			_side_sign = 1.0 if randf() < 0.5 else -1.0
		elif randf() < 0.5:
			_jump_wait = maxf(eta - 0.3, 0.0)
	if _seen.size() > 200:
		_seen.clear()


func _position(f, o, delta: float) -> void:
	var d: Vector3 = o.global_position - f.global_position
	d.y = 0.0
	var dist := d.length()
	d = d / maxf(dist, 0.001)
	var side := Vector3(-d.z, 0.0, d.x)
	if _side_t > 0.0:
		_side_t -= delta
		f.move_dir = side * _side_sign
		return
	if f.kit == "mage":
		_strafe_t -= delta
		if _strafe_t <= 0.0:
			_strafe_t = randf_range(0.6, 1.4)
			_side_sign = [-1.0, 0.0, 1.0].pick_random()
		if dist < 3.2:
			f.move_dir = -d + side * _side_sign * 0.5
		elif dist > 6.5:
			f.move_dir = d
		elif _side_sign != 0.0:
			f.move_dir = side * _side_sign * 0.6


func _schedule_block(wait: float, duration: float) -> void:
	if _block_hold > 0.0 or _block_wait >= 0.0:
		return
	_block_wait = wait
	_block_dur = duration


func _try_skill(f, key: String, force := false) -> bool:
	if f.cooldowns[key] > 0.0:
		return false
	if not force and randf() > 0.5:
		return false
	f.in_skill = key
	return true


func _plan_offense(f, o, delta: float) -> void:
	if f.state != S.IDLE or not _queue.is_empty() or _hold > 0.0 or _block_hold > 0.0:
		return
	var dist: float = f.global_position.distance_to(o.global_position)
	var ranged: bool = f.kit == "mage"
	var reach := 9.0 if ranged else (1.7 if f.kit == "assassin" else 1.9)

	_skill_cd -= delta
	if _skill_cd <= 0.0:
		_skill_cd = randf_range(skill_wait.x, skill_wait.y)
		var keys: Array = ["c", "x", "z"]
		keys.shuffle()
		for key: String in keys:
			var a: Dictionary = f.attacks[key]
			var usable := true
			match a.type:
				"melee":
					usable = dist < float(a.reach) + 1.5
				"strike":
					usable = a.at != "self" or dist < float(a.radius)
				"buff":
					usable = f.hp < f.max_hp * 0.7
				"blink":
					usable = (a.mode == "behind" and dist < 6.0) or (a.mode == "back" and dist < 2.5)
			if usable and _try_skill(f, key):
				return

	if dist > reach:
		return
	if o.state == S.STAGGER:
		_think_cd = 0.0
	_think_cd -= delta
	if _think_cd > 0.0:
		return
	_think_cd = (randf_range(0.5, 1.1) if f.kit == "assassin" else randf_range(0.7, 1.6)) * think_scale
	var heavy_chance := 0.45 if o.state == S.BLOCK else 0.22
	if o.state == S.STAGGER:
		heavy_chance = 0.5
	if randf() < heavy_chance:
		_queue.append([0.0, Fighter.HOLD_T + randf_range(0.3, 0.65)])
	else:
		var hits := randi_range(1, mini(max_combo, 4 if f.kit == "assassin" else 3))
		for i in hits:
			_queue.append([0.0 if i == 0 else 0.14, 0.06])
