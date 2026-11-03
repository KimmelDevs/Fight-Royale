extends Node3D
## Water orb projectile: arcs slightly, leaves a droplet trail, splashes on the ground.

const Mat := preload("res://scripts/toon_mat.gd")
const Vfx := preload("res://scripts/vfx.gd")

var velocity := Vector3.ZERO
var size := 1.0
var _life := 1.6
var _core: MeshInstance3D
var _trail: CPUParticles3D


func setup(dir: Vector3, speed: float, s: float) -> void:
	velocity = dir.normalized() * speed
	size = s


func _ready() -> void:
	_core = MeshInstance3D.new()
	var sm := SphereMesh.new()
	sm.radius = 0.15 * size
	sm.height = 0.3 * size
	_core.mesh = sm
	_core.material_override = Mat.water(Color(0.12, 0.45, 1.0, 0.85), 1.8)
	_core.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	add_child(_core)

	_trail = CPUParticles3D.new()
	var tm := SphereMesh.new()
	tm.radius = 0.05 * size
	tm.height = 0.1 * size
	tm.radial_segments = 8
	tm.rings = 4
	tm.material = Mat.water(Color(0.3, 0.7, 1.0, 0.8), 1.6)
	_trail.mesh = tm
	_trail.amount = 28
	_trail.lifetime = 0.35
	_trail.local_coords = false
	_trail.spread = 180.0
	_trail.initial_velocity_min = 0.2
	_trail.initial_velocity_max = 0.8
	_trail.gravity = Vector3(0, -4, 0)
	var curve := Curve.new()
	curve.add_point(Vector2(0, 1))
	curve.add_point(Vector2(1, 0))
	_trail.scale_amount_curve = curve
	add_child(_trail)


func _process(delta: float) -> void:
	velocity.y -= 3.0 * delta
	global_position += velocity * delta
	_life -= delta
	# Stretch along travel direction for a sense of speed.
	if velocity.length_squared() > 0.01:
		_core.look_at(global_position + velocity, Vector3.UP)
		_core.scale = Vector3(0.85, 0.85, 1.5)
	if global_position.y < 0.15 or _life <= 0.0:
		_burst()


func _burst() -> void:
	var parent := get_parent()
	var ground := Vector3(global_position.x, maxf(global_position.y, 0.05), global_position.z)
	Vfx.splash(parent, ground, 18, size)
	Vfx.ripple(parent, Vector3(ground.x, 0.0, ground.z), 1.3 * size)
	# Let the trail finish instead of popping out of existence.
	_trail.emitting = false
	_trail.reparent(parent)
	parent.get_tree().create_timer(_trail.lifetime + 0.1).timeout.connect(_trail.queue_free)
	queue_free()
