extends CharacterBody3D
## Water mage controller: camera-relative movement, jump, dash and four water skills.

const Model := preload("res://scripts/character_model.gd")
const Vfx := preload("res://scripts/vfx.gd")
const WaterBolt := preload("res://scripts/water_bolt.gd")
const CameraRig := preload("res://scripts/camera_rig.gd")

const COOLDOWN := {
	"attack": 0.3,
	"dash": 0.9,
	"skill": 4.0,
	"shield": 9.0,
	"burst": 12.0,
}
const BURST_CHARGE := 1.3
const SHIELD_DURATION := 5.0

@export var move_speed := 5.5
@export var acceleration := 14.0
@export var jump_velocity := 6.8
@export var gravity := 19.0
@export var dash_speed := 17.0

var cam_rig: CameraRig
var model: Model
var cooldowns := {"attack": 0.0, "dash": 0.0, "skill": 0.0, "shield": 0.0, "burst": 0.0}

var _facing := Vector3.BACK  # +Z, toward the starting camera, so you see her face first.
var _combo := 0
var _combo_reset := 0.0
var _cast_time := 0.0
var _dash_time := 0.0
var _dash_dir := Vector3.ZERO
var _dash_trail := 0.0
var _was_on_floor := true
var _shield: Node3D
var _shield_time := 0.0
var _burst_time := -1.0  # >= 0 while channeling the burst
var _burst_orb: Node3D


func _ready() -> void:
	var shape := CollisionShape3D.new()
	var cap := CapsuleShape3D.new()
	cap.radius = 0.25
	cap.height = 1.75
	shape.shape = cap
	shape.position.y = 0.875
	add_child(shape)
	model = Model.new()
	add_child(model)


func _physics_process(delta: float) -> void:
	for k: String in cooldowns:
		cooldowns[k] = maxf(cooldowns[k] - delta, 0.0)
	_combo_reset -= delta
	if _combo_reset <= 0.0:
		_combo = 0
	_cast_time = maxf(_cast_time - delta, 0.0)

	var input := Input.get_vector("move_left", "move_right", "move_forward", "move_back")
	var wish := Vector3(input.x, 0.0, input.y).rotated(Vector3.UP, cam_rig.yaw)

	if _burst_time < 0.0:
		_handle_skills(wish)

	if _burst_time >= 0.0:
		_update_burst(delta)
	elif _dash_time > 0.0:
		_dash_time -= delta
		velocity = _dash_dir * dash_speed
		_dash_trail -= delta
		if _dash_trail <= 0.0:
			_dash_trail = 0.03
			Vfx.splash(get_parent(), global_position + Vector3(0, 0.15, 0), 5, 0.6)
	else:
		var speed := move_speed * (0.35 if _cast_time > 0.0 else 1.0)
		var target := wish * speed
		var a := acceleration if is_on_floor() else acceleration * 0.4
		var k := 1.0 - exp(-a * delta)
		velocity.x = lerpf(velocity.x, target.x, k)
		velocity.z = lerpf(velocity.z, target.z, k)
		velocity.y -= gravity * delta
		if is_on_floor() and Input.is_action_just_pressed("jump"):
			velocity.y = jump_velocity
			model.squash(Vector3(0.85, 1.2, 0.85))
			Vfx.splash(get_parent(), global_position + Vector3(0, 0.05, 0), 8, 0.6)

	move_and_slide()

	if is_on_floor() and not _was_on_floor:
		model.squash(Vector3(1.18, 0.82, 1.18))
		Vfx.ripple(get_parent(), global_position, 0.9)
	_was_on_floor = is_on_floor()

	if wish.length() > 0.1 and _cast_time <= 0.0 and _burst_time < 0.0 and _dash_time <= 0.0:
		_facing = wish.normalized()
	model.rotation.y = lerp_angle(model.rotation.y, atan2(_facing.x, _facing.z), 1.0 - exp(-14.0 * delta))

	var hspeed := Vector2(velocity.x, velocity.z).length()
	model.cast_weight = move_toward(model.cast_weight, 1.0 if _cast_time > 0.0 else 0.0, delta * 10.0)
	model.burst_weight = move_toward(model.burst_weight, 1.0 if _burst_time >= 0.0 else 0.0, delta * 6.0)
	model.animate(delta, clampf(hspeed / move_speed, 0.0, 1.0), is_on_floor(), velocity.y)
	_update_shield(delta)


func _handle_skills(wish: Vector3) -> void:
	if Input.is_action_just_pressed("attack") and cooldowns["attack"] <= 0.0:
		_tide_shot()
	if Input.is_action_just_pressed("dash") and cooldowns["dash"] <= 0.0:
		_ripple_dash(wish)
	if Input.is_action_just_pressed("skill") and cooldowns["skill"] <= 0.0:
		_tidal_ring()
	if Input.is_action_just_pressed("shield") and cooldowns["shield"] <= 0.0:
		_bubble_ward()
	if Input.is_action_just_pressed("burst") and cooldowns["burst"] <= 0.0:
		_start_burst()


## LMB: 3-hit combo. Hits 1-2 fire one orb, hit 3 fires a fan of three bigger orbs.
func _tide_shot() -> void:
	cooldowns["attack"] = COOLDOWN["attack"]
	_facing = cam_rig.forward_flat()
	_cast_time = 0.35
	_combo_reset = 0.9
	var finisher := _combo == 2
	var origin := global_position + Vector3(0, 1.4, 0) + _facing * 0.5
	var angles := [-0.22, 0.0, 0.22] if finisher else [0.0]
	for a in angles:
		var bolt := WaterBolt.new()
		bolt.setup(_facing.rotated(Vector3.UP, a) + Vector3(0, 0.05, 0), 20.0, 1.3 if finisher else 1.0)
		get_parent().add_child(bolt)
		bolt.global_position = origin
	model.pop_orb(2.0 if finisher else 1.5)
	cam_rig.add_trauma(0.25 if finisher else 0.1)
	_combo = (_combo + 1) % 3


## Shift: short burst of speed with a splash trail.
func _ripple_dash(wish: Vector3) -> void:
	cooldowns["dash"] = COOLDOWN["dash"]
	_dash_dir = (wish if wish.length() > 0.1 else _facing).normalized()
	_facing = _dash_dir
	_dash_time = 0.2
	_dash_trail = 0.0
	model.squash(Vector3(0.85, 0.9, 1.3))
	Vfx.splash(get_parent(), global_position + Vector3(0, 0.1, 0), 14, 0.9)


## E: wave ring + a circle of geysers around her.
func _tidal_ring() -> void:
	cooldowns["skill"] = COOLDOWN["skill"]
	_cast_time = 0.5
	var c := global_position
	c.y = 0.0
	Vfx.wave_ring(get_parent(), c, 6.5, 0.7)
	Vfx.splash(get_parent(), c + Vector3(0, 0.1, 0), 30, 1.4)
	for i in 8:
		var ang := TAU * i / 8.0
		Vfx.geyser(get_parent(), c + Vector3(cos(ang), 0, sin(ang)) * 2.4, 1.7, 0.1 + 0.03 * i)
	model.squash(Vector3(1.15, 0.88, 1.15))
	model.pop_orb(2.2)
	cam_rig.add_trauma(0.4)


## R: bubble shield that follows her for a few seconds, then pops.
func _bubble_ward() -> void:
	cooldowns["shield"] = COOLDOWN["shield"]
	_cast_time = 0.3
	if _shield:
		_shield.queue_free()
	_shield = Vfx.bubble(self)
	_shield_time = SHIELD_DURATION
	model.pop_orb(1.8)


func _update_shield(delta: float) -> void:
	if _shield == null:
		return
	_shield_time -= delta
	var t := Time.get_ticks_msec() / 1000.0
	var mesh := _shield.get_node("Mesh") as Node3D
	mesh.scale = Vector3(1.0 + 0.035 * sin(t * 5.0), 1.0 + 0.035 * sin(t * 5.0 + 2.0), 1.0 + 0.035 * sin(t * 5.0 + 4.0))
	if _shield_time <= 0.0:
		Vfx.splash(get_parent(), _shield.global_position, 40, 1.6)
		_shield.queue_free()
		_shield = null


## Q: float up, gather a huge water orb overhead, then slam it down in front.
func _start_burst() -> void:
	cooldowns["burst"] = COOLDOWN["burst"]
	_burst_time = 0.0
	_facing = cam_rig.forward_flat()
	_burst_orb = Vfx.big_orb(get_parent())
	_burst_orb.scale = Vector3.ONE * 0.1
	cam_rig.add_trauma(0.2)


func _update_burst(delta: float) -> void:
	_burst_time += delta
	velocity = Vector3(0.0, (0.6 - global_position.y) * 5.0, 0.0)
	var charge := clampf(_burst_time / BURST_CHARGE, 0.0, 1.0)
	_burst_orb.scale = Vector3.ONE * lerpf(0.1, 1.0, ease(charge, 0.4))
	_burst_orb.global_position = global_position + Vector3(0, 3.2, 0)
	cam_rig.add_trauma(0.6 * delta)
	if _burst_time >= BURST_CHARGE:
		_release_burst()


func _release_burst() -> void:
	_burst_time = -1.0
	var target := global_position + _facing * 5.0
	target.y = 0.4
	var orb := _burst_orb
	_burst_orb = null
	model.squash(Vector3(0.9, 1.15, 0.9))
	var tw := orb.create_tween()
	tw.tween_property(orb, "global_position", target, 0.22).set_trans(Tween.TRANS_QUAD).set_ease(Tween.EASE_IN)
	tw.tween_callback(func() -> void:
		_burst_impact(Vector3(target.x, 0.0, target.z))
		orb.queue_free()
	)


func _burst_impact(pos: Vector3) -> void:
	var parent := get_parent()
	Vfx.wave_ring(parent, pos, 11.0, 1.1)
	Vfx.wave_ring(parent, pos, 7.0, 0.8, 0.12)
	Vfx.splash(parent, pos + Vector3(0, 0.3, 0), 60, 2.5)
	for i in 10:
		var ang := TAU * i / 10.0
		Vfx.geyser(parent, pos + Vector3(cos(ang), 0, sin(ang)) * 3.2, 3.0, 0.05)
	for i in 14:
		var ang := TAU * i / 14.0 + 0.2
		Vfx.geyser(parent, pos + Vector3(cos(ang), 0, sin(ang)) * 6.0, 2.0, 0.25)
	cam_rig.add_trauma(0.9)
	_hit_stop(0.09)


func _hit_stop(duration: float) -> void:
	Engine.time_scale = 0.05
	# ignore_time_scale = true so the timer still runs while the game is slowed.
	await get_tree().create_timer(duration, true, false, true).timeout
	Engine.time_scale = 1.0
