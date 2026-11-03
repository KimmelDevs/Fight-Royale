extends RefCounted
## Water VFX helpers. Every effect frees itself when finished.

const Mat := preload("res://scripts/toon_mat.gd")

static var _drop_mesh: SphereMesh
static var _shrink: Curve


static func _droplet_mesh() -> SphereMesh:
	if _drop_mesh == null:
		_drop_mesh = SphereMesh.new()
		_drop_mesh.radius = 0.07
		_drop_mesh.height = 0.14
		_drop_mesh.radial_segments = 8
		_drop_mesh.rings = 4
		_drop_mesh.material = Mat.water(Color(0.2, 0.55, 1.0, 0.85), 1.5)
	return _drop_mesh


static func _shrink_curve() -> Curve:
	if _shrink == null:
		_shrink = Curve.new()
		_shrink.add_point(Vector2(0.0, 1.0))
		_shrink.add_point(Vector2(1.0, 0.0))
	return _shrink


static func _free_later(node: Node, seconds: float) -> void:
	node.get_tree().create_timer(seconds).timeout.connect(node.queue_free)


static func _fade(mat: ShaderMaterial) -> Callable:
	return func(v: float) -> void: mat.set_shader_parameter("alpha_mult", v)


## Burst of droplets thrown up and out.
static func splash(parent: Node, pos: Vector3, amount := 16, size := 1.0) -> void:
	var p := CPUParticles3D.new()
	p.mesh = _droplet_mesh()
	p.amount = amount
	p.one_shot = true
	p.explosiveness = 0.95
	p.lifetime = 0.8
	p.direction = Vector3.UP
	p.spread = 55.0
	p.initial_velocity_min = 2.0 * size
	p.initial_velocity_max = 5.0 * size
	p.gravity = Vector3(0, -15, 0)
	p.scale_amount_min = 0.5 * size
	p.scale_amount_max = 1.2 * size
	p.scale_amount_curve = _shrink_curve()
	p.emission_shape = CPUParticles3D.EMISSION_SHAPE_SPHERE
	p.emission_sphere_radius = 0.15 * size
	parent.add_child(p)
	p.global_position = pos
	p.emitting = true
	_free_later(p, p.lifetime + 0.3)


## Expanding, fading torus. `height` scales the tube vertically (wave vs. ripple).
static func ring(parent: Node, pos: Vector3, radius: float, duration: float, height: float, delay := 0.0) -> void:
	var mi := MeshInstance3D.new()
	var t := TorusMesh.new()
	t.inner_radius = 0.82
	t.outer_radius = 1.0
	t.rings = 48
	t.ring_segments = 8
	mi.mesh = t
	var mat := Mat.water(Color(0.15, 0.5, 1.0, 0.7), 1.4)
	mi.material_override = mat
	mi.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	parent.add_child(mi)
	mi.global_position = pos
	mi.scale = Vector3(0.2, height, 0.2)
	mi.visible = delay <= 0.0
	var tw := mi.create_tween()
	if delay > 0.0:
		tw.tween_interval(delay)
		tw.tween_callback(mi.show)
	tw.tween_property(mi, "scale", Vector3(radius, height, radius), duration).set_trans(Tween.TRANS_CUBIC).set_ease(Tween.EASE_OUT)
	tw.parallel().tween_method(_fade(mat), 1.0, 0.0, duration).set_ease(Tween.EASE_IN)
	tw.tween_callback(mi.queue_free)


static func ripple(parent: Node, pos: Vector3, radius := 1.0) -> void:
	ring(parent, pos + Vector3(0, 0.03, 0), radius, 0.45, 0.4)


static func wave_ring(parent: Node, pos: Vector3, radius: float, duration: float, delay := 0.0) -> void:
	ring(parent, pos + Vector3(0, 0.05, 0), radius, duration, 4.0, delay)


## Water column that shoots up from the ground, then collapses.
static func geyser(parent: Node, pos: Vector3, height: float, delay := 0.0) -> void:
	var root := Node3D.new()
	parent.add_child(root)
	root.global_position = pos
	var mi := MeshInstance3D.new()
	var c := CylinderMesh.new()
	c.top_radius = 0.08
	c.bottom_radius = 0.22
	c.height = 1.0
	c.radial_segments = 16
	mi.mesh = c
	mi.position.y = 0.5
	mi.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	var mat := Mat.water(Color(0.15, 0.5, 1.0, 0.75), 1.5)
	mi.material_override = mat
	root.add_child(mi)
	root.scale = Vector3(1, 0.01, 1)
	root.visible = false
	var tw := root.create_tween()
	if delay > 0.0:
		tw.tween_interval(delay)
	tw.tween_callback(func() -> void:
		root.visible = true
		splash(parent, pos + Vector3(0, 0.1, 0), 10, 0.8)
	)
	tw.tween_property(root, "scale", Vector3(1, height, 1), 0.2).set_trans(Tween.TRANS_BACK).set_ease(Tween.EASE_OUT)
	tw.tween_callback(func() -> void: splash(parent, pos + Vector3(0, height, 0), 12, 0.9))
	tw.tween_property(root, "scale", Vector3(0.4, height * 0.15, 0.4), 0.35).set_trans(Tween.TRANS_QUAD).set_ease(Tween.EASE_IN)
	tw.parallel().tween_method(_fade(mat), 1.0, 0.0, 0.35)
	tw.tween_callback(root.queue_free)


## Translucent bubble shield. Returns the root; wobble its "Mesh" child.
static func bubble(parent: Node3D) -> Node3D:
	var root := Node3D.new()
	root.position = Vector3(0, 0.88, 0)
	parent.add_child(root)
	var mi := MeshInstance3D.new()
	mi.name = "Mesh"
	var s := SphereMesh.new()
	s.radius = 1.0
	s.height = 2.0
	mi.mesh = s
	mi.material_override = Mat.water(Color(0.35, 0.7, 1.0, 0.15), 1.25)
	mi.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	root.add_child(mi)
	# Specular glint so it reads as a bubble.
	var glint := MeshInstance3D.new()
	var gs := SphereMesh.new()
	gs.radius = 0.12
	gs.height = 0.24
	glint.mesh = gs
	glint.material_override = Mat.flat(Color(1, 1, 1))
	glint.position = Vector3(-0.35, 0.55, 0.55)
	glint.scale = Vector3(1.0, 0.6, 0.3)
	mi.add_child(glint)
	var drops := CPUParticles3D.new()
	drops.mesh = _droplet_mesh()
	drops.amount = 18
	drops.lifetime = 1.0
	drops.emission_shape = CPUParticles3D.EMISSION_SHAPE_SPHERE_SURFACE
	drops.emission_sphere_radius = 1.0
	drops.gravity = Vector3(0, 0.6, 0)
	drops.initial_velocity_min = 0.0
	drops.initial_velocity_max = 0.1
	drops.scale_amount_min = 0.2
	drops.scale_amount_max = 0.5
	drops.scale_amount_curve = _shrink_curve()
	root.add_child(drops)
	root.scale = Vector3.ONE * 0.2
	var tw := root.create_tween()
	tw.tween_property(root, "scale", Vector3.ONE, 0.45).set_trans(Tween.TRANS_ELASTIC).set_ease(Tween.EASE_OUT)
	return root


## Big charging water sphere for the burst. Caller drives position and scale.
static func big_orb(parent: Node) -> Node3D:
	var root := Node3D.new()
	parent.add_child(root)
	var core := MeshInstance3D.new()
	var s := SphereMesh.new()
	s.radius = 1.0
	s.height = 2.0
	core.mesh = s
	core.material_override = Mat.water(Color(0.08, 0.38, 1.0, 0.85), 1.6)
	root.add_child(core)
	var inner := MeshInstance3D.new()
	var si := SphereMesh.new()
	si.radius = 0.55
	si.height = 1.1
	inner.mesh = si
	inner.material_override = Mat.water(Color(0.6, 0.95, 1.0, 1.0), 2.2)
	root.add_child(inner)
	for i in 2:
		var swirl := MeshInstance3D.new()
		var t := TorusMesh.new()
		t.inner_radius = 1.2
		t.outer_radius = 1.32
		swirl.mesh = t
		swirl.material_override = Mat.water(Color(0.3, 0.75, 1.0, 0.7), 1.6)
		swirl.rotation = Vector3(0.5 + i * 0.9, 0, 0.3 - i * 0.7)
		root.add_child(swirl)
		var tw := swirl.create_tween().set_loops()
		tw.tween_property(swirl, "rotation:y", TAU, 0.8 + i * 0.3).as_relative()
	# Droplets pulled inward while charging.
	var suck := CPUParticles3D.new()
	suck.mesh = _droplet_mesh()
	suck.amount = 40
	suck.lifetime = 0.6
	suck.emission_shape = CPUParticles3D.EMISSION_SHAPE_SPHERE_SURFACE
	suck.emission_sphere_radius = 2.8
	suck.gravity = Vector3.ZERO
	suck.radial_accel_min = -14.0
	suck.radial_accel_max = -10.0
	suck.scale_amount_curve = _shrink_curve()
	root.add_child(suck)
	return root
