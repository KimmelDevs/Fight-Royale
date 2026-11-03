extends Node3D
## Flying spell or thrown weapon. Moves straight; calls `on_hit(self)` when it reaches the
## target's chest. Jumping over it or stepping aside dodges it.

const Mat := preload("res://scripts/toon_mat.gd")
const Fx := preload("res://scripts/battle/combat_fx.gd")
const Gen := preload("res://scripts/mesh_gen.gd")
const Fighter := preload("res://scripts/battle/fighter.gd")

var shooter
var target
var atk: Dictionary
var power := 1.0
var velocity := Vector3.ZERO
var color := Color.WHITE
var on_hit: Callable

var radius := 0.32
var _life := 2.2
var _spin: Node3D


func _ready() -> void:
	add_to_group("projectiles")
	var size: float = atk.size
	radius = 0.3 * size
	look_at(global_position + velocity, Vector3.UP)
	_spin = Node3D.new()
	add_child(_spin)
	match atk.style:
		"wave":
			_build_wave(size)
		"shuriken":
			_build_shuriken(size)
		_:
			_build_orb(size)


func _glow(c: Color, energy := 4.0) -> StandardMaterial3D:
	var m := StandardMaterial3D.new()
	m.albedo_color = c
	m.emission_enabled = true
	m.emission = c
	m.emission_energy_multiplier = energy
	return m


func _sphere_mi(r: float, mat: Material) -> MeshInstance3D:
	var mi := MeshInstance3D.new()
	var s := SphereMesh.new()
	s.radius = r
	s.height = r * 2.0
	s.radial_segments = 16
	s.rings = 8
	mi.mesh = s
	mi.material_override = mat
	mi.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	return mi


func _build_orb(size: float) -> void:
	var element: String = atk.element
	var core_c := color
	if element == "electric":
		core_c = Color(1.0, 0.95, 0.6)
	var core := _sphere_mi(0.1 * size, _glow(core_c, 5.0))
	if element == "electric":
		core.scale = Vector3(0.7, 0.7, 2.6)
	_spin.add_child(core)
	var shell := _sphere_mi(0.17 * size, Mat.water(Color(color.r, color.g, color.b, 0.55), 1.8))
	_spin.add_child(shell)
	# Trail: embers rise, droplets fall, sparks crackle.
	var p := CPUParticles3D.new()
	var bm := BoxMesh.new()
	bm.size = Vector3(0.03, 0.03, 0.03) * size
	bm.material = _glow(color, 4.0)
	p.mesh = bm
	p.amount = 24
	p.lifetime = 0.3
	p.local_coords = false
	p.spread = 180.0
	p.initial_velocity_min = 0.3
	p.initial_velocity_max = 1.5 if element == "electric" else 0.6
	p.gravity = Vector3(0, 2.0, 0) if element == "fire" else Vector3(0, -3.0, 0)
	var curve := Curve.new()
	curve.add_point(Vector2(0, 1))
	curve.add_point(Vector2(1, 0))
	p.scale_amount_curve = curve
	add_child(p)


func _build_wave(size: float) -> void:
	var m := StandardMaterial3D.new()
	m.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	m.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	m.blend_mode = BaseMaterial3D.BLEND_MODE_ADD
	m.cull_mode = BaseMaterial3D.CULL_DISABLED
	m.albedo_color = Color(color.r, color.g, color.b, 0.9)
	var arc := MeshInstance3D.new()
	# A horizontal crescent bulging toward -Z (this node's forward).
	arc.mesh = Gen.cone_sheet(0.55 * size, 0.62 * size, 0.1 * size, PI - 1.1, PI + 1.1, 24, 2)
	arc.material_override = m
	arc.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	arc.position = Vector3(0, 0.05 * size, 0.45 * size)
	_spin.add_child(arc)
	var core := _sphere_mi(0.06 * size, _glow(color, 5.0))
	core.scale = Vector3(6.0, 0.4, 0.6)
	_spin.add_child(core)


func _build_shuriken(size: float) -> void:
	var steel := Mat.toon(Color("dcd6f0"), true, 0.8)
	for i in 2:
		var b := MeshInstance3D.new()
		var bm := BoxMesh.new()
		bm.size = Vector3(0.34, 0.012, 0.06) * size
		b.mesh = bm
		b.material_override = steel
		b.rotation.y = i * PI / 2.0
		_spin.add_child(b)
	_spin.add_child(_sphere_mi(0.035 * size, _glow(color, 4.0)))


func _physics_process(delta: float) -> void:
	global_position += velocity * delta
	_life -= delta
	match atk.style:
		"shuriken":
			_spin.rotate_y(delta * 30.0)
		"wave":
			pass
		_:
			_spin.rotate_z(delta * 12.0)
	if target != null and is_instance_valid(target) and target.state != Fighter.S.KO:
		var chest: Vector3 = target.global_position + Vector3(0, 1.1, 0)
		if global_position.distance_to(chest) < radius + 0.35:
			on_hit.call(self)
			queue_free()
			return
	var flat := Vector2(global_position.x, global_position.z)
	if _life <= 0.0 or global_position.y < 0.05 or flat.length() > 14.0:
		Fx.sparks(get_parent(), global_position, color, 8, 3.0)
		queue_free()
