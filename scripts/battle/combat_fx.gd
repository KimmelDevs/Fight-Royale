extends RefCounted
## Combat VFX: sparks, impact flashes, shockwave rings and floating damage numbers.
## Every effect frees itself.

static var _spark_mesh: BoxMesh
static var _shrink: Curve


static func _glow_mat(color: Color, energy := 4.0) -> StandardMaterial3D:
	var m := StandardMaterial3D.new()
	m.albedo_color = color
	m.emission_enabled = true
	m.emission = color
	m.emission_energy_multiplier = energy
	return m


static func _additive(color: Color) -> StandardMaterial3D:
	var m := StandardMaterial3D.new()
	m.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	m.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	m.blend_mode = BaseMaterial3D.BLEND_MODE_ADD
	m.cull_mode = BaseMaterial3D.CULL_DISABLED
	m.albedo_color = color
	return m


static func _shrink_curve() -> Curve:
	if _shrink == null:
		_shrink = Curve.new()
		_shrink.add_point(Vector2(0, 1))
		_shrink.add_point(Vector2(1, 0))
	return _shrink


static func _free_later(node: Node, seconds: float) -> void:
	node.get_tree().create_timer(seconds).timeout.connect(node.queue_free)


## Streaking metal sparks. `dir` zero = all directions.
static func sparks(parent: Node, pos: Vector3, color: Color, amount := 24, speed := 7.0, dir := Vector3.ZERO) -> void:
	var p := CPUParticles3D.new()
	var mesh := BoxMesh.new()
	mesh.size = Vector3(0.012, 0.09, 0.012)
	mesh.material = _glow_mat(color)
	p.mesh = mesh
	p.amount = amount
	p.one_shot = true
	p.explosiveness = 1.0
	p.lifetime = 0.35
	p.particle_flag_align_y = true
	p.direction = dir if dir != Vector3.ZERO else Vector3.UP
	p.spread = 180.0 if dir == Vector3.ZERO else 55.0
	p.initial_velocity_min = speed * 0.5
	p.initial_velocity_max = speed
	p.gravity = Vector3(0, -9, 0)
	p.damping_min = 4.0
	p.damping_max = 8.0
	p.scale_amount_curve = _shrink_curve()
	parent.add_child(p)
	p.global_position = pos
	p.emitting = true
	_free_later(p, p.lifetime + 0.2)


## Expanding, fading glow ball.
static func flash(parent: Node, pos: Vector3, color: Color, size := 0.5, duration := 0.14) -> void:
	var mi := MeshInstance3D.new()
	var s := SphereMesh.new()
	s.radius = 1.0
	s.height = 2.0
	s.radial_segments = 16
	s.rings = 8
	mi.mesh = s
	var mat := _additive(color)
	mi.material_override = mat
	mi.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	parent.add_child(mi)
	mi.global_position = pos
	mi.scale = Vector3.ONE * size * 0.3
	var tw := mi.create_tween()
	tw.tween_property(mi, "scale", Vector3.ONE * size, duration).set_trans(Tween.TRANS_QUAD).set_ease(Tween.EASE_OUT)
	tw.parallel().tween_property(mat, "albedo_color:a", 0.0, duration)
	tw.tween_callback(mi.queue_free)


## Flat shockwave ring on the ground.
static func ring(parent: Node, pos: Vector3, color: Color, radius := 2.0, duration := 0.35) -> void:
	var mi := MeshInstance3D.new()
	var t := TorusMesh.new()
	t.inner_radius = 0.9
	t.outer_radius = 1.0
	t.rings = 48
	t.ring_segments = 6
	mi.mesh = t
	var mat := _additive(color)
	mi.material_override = mat
	mi.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	parent.add_child(mi)
	mi.global_position = Vector3(pos.x, 0.05, pos.z)
	mi.scale = Vector3(0.2, 0.3, 0.2)
	var tw := mi.create_tween()
	tw.tween_property(mi, "scale", Vector3(radius, 0.3, radius), duration).set_trans(Tween.TRANS_CUBIC).set_ease(Tween.EASE_OUT)
	tw.parallel().tween_property(mat, "albedo_color:a", 0.0, duration)
	tw.tween_callback(mi.queue_free)


## Floating number / word that pops, rises and fades.
static func number(parent: Node, pos: Vector3, text: String, color: Color, size := 1.0) -> void:
	var l := Label3D.new()
	l.text = text
	l.billboard = BaseMaterial3D.BILLBOARD_ENABLED
	l.no_depth_test = true
	l.render_priority = 10
	l.outline_render_priority = 9
	l.font_size = 72
	l.outline_size = 18
	l.pixel_size = 0.0032 * size
	l.modulate = color
	l.outline_modulate = Color(0.1, 0.08, 0.18, 1.0)
	parent.add_child(l)
	l.global_position = pos + Vector3(randf_range(-0.15, 0.15), 0.0, randf_range(-0.1, 0.1))
	l.scale = Vector3.ONE * 0.4
	var tw := l.create_tween()
	tw.tween_property(l, "scale", Vector3.ONE * 1.15, 0.09).set_trans(Tween.TRANS_BACK).set_ease(Tween.EASE_OUT)
	tw.tween_property(l, "scale", Vector3.ONE, 0.08)
	tw.parallel().tween_property(l, "global_position", l.global_position + Vector3(0, 0.55, 0), 0.8).set_trans(Tween.TRANS_QUAD).set_ease(Tween.EASE_OUT)
	tw.tween_property(l, "modulate:a", 0.0, 0.25)
	tw.parallel().tween_property(l, "outline_modulate:a", 0.0, 0.25)
	tw.tween_callback(l.queue_free)


## Jagged lightning bolt from the sky down to `pos`.
static func lightning(parent: Node, pos: Vector3, color: Color) -> void:
	var root := Node3D.new()
	parent.add_child(root)
	var mat := _glow_mat(Color(1.0, 0.97, 0.75), 6.0)
	var halo := _additive(Color(color.r, color.g, color.b, 0.6))
	var top := pos + Vector3(randf_range(-0.6, 0.6), 9.0, randf_range(-0.6, 0.6))
	var prev := top
	for i in 9:
		var t := float(i + 1) / 9.0
		var next := top.lerp(pos, t) + Vector3(randf_range(-0.35, 0.35), 0.0, randf_range(-0.35, 0.35)) * (1.0 - t * 0.8)
		if i == 8:
			next = pos
		for pass_i in 2:
			var seg := MeshInstance3D.new()
			var b := BoxMesh.new()
			var w := 0.05 if pass_i == 0 else 0.16
			b.size = Vector3(w, prev.distance_to(next), w)
			seg.mesh = b
			seg.material_override = mat if pass_i == 0 else halo
			seg.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
			root.add_child(seg)
			var mid := (prev + next) * 0.5
			var up := (next - prev).normalized()
			var side := up.cross(Vector3.FORWARD if absf(up.dot(Vector3.FORWARD)) < 0.9 else Vector3.RIGHT).normalized()
			seg.global_transform = Transform3D(Basis(side, up, side.cross(up)), mid)
		prev = next
	var tw := root.create_tween()
	tw.tween_interval(0.07)
	tw.tween_callback(func() -> void: root.visible = false)
	tw.tween_interval(0.04)
	tw.tween_callback(func() -> void: root.visible = true)
	tw.tween_interval(0.08)
	tw.tween_callback(root.queue_free)


## Pulsing ground marker where an area attack will land. Freed by the caller.
static func telegraph(parent: Node, pos: Vector3, color: Color, radius: float) -> Node3D:
	var root := Node3D.new()
	parent.add_child(root)
	root.global_position = Vector3(pos.x, 0.03, pos.z)
	var disc := MeshInstance3D.new()
	var c := CylinderMesh.new()
	c.top_radius = radius
	c.bottom_radius = radius
	c.height = 0.01
	c.radial_segments = 40
	disc.mesh = c
	var dm := _additive(Color(color.r, color.g, color.b, 0.22))
	disc.material_override = dm
	disc.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	root.add_child(disc)
	var rim := MeshInstance3D.new()
	var t := TorusMesh.new()
	t.inner_radius = radius - 0.06
	t.outer_radius = radius
	t.rings = 48
	t.ring_segments = 4
	rim.mesh = t
	rim.material_override = _additive(Color(color.r, color.g, color.b, 0.9))
	rim.scale = Vector3(1, 0.2, 1)
	rim.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	root.add_child(rim)
	var tw := root.create_tween().set_loops()
	tw.tween_property(dm, "albedo_color:a", 0.45, 0.15)
	tw.tween_property(dm, "albedo_color:a", 0.18, 0.15)
	return root


## Fiery blast: flash, sparks, rising embers and a shockwave.
static func explosion(parent: Node, pos: Vector3, color: Color, radius: float) -> void:
	var center := Vector3(pos.x, 0.6, pos.z)
	flash(parent, center, Color(1.0, 0.75, 0.35, 0.7), radius * 0.4, 0.2)
	flash(parent, center, Color(color.r, color.g, color.b, 0.45), radius * 0.6, 0.3)
	sparks(parent, center, color, 50, 9.0)
	sparks(parent, center, Color(1.0, 0.9, 0.5), 30, 6.0, Vector3.UP)
	ring(parent, pos, color, radius * 1.4, 0.4)


## A burning rock falling from the sky onto `pos` over `duration` seconds.
static func meteor(parent: Node, pos: Vector3, color: Color, duration: float) -> void:
	var mi := MeshInstance3D.new()
	var s := SphereMesh.new()
	s.radius = 0.55
	s.height = 1.1
	mi.mesh = s
	mi.material_override = _glow_mat(color, 3.5)
	mi.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	parent.add_child(mi)
	var start := pos + Vector3(-3.0, 10.0, -1.5)
	mi.global_position = start
	var fire := CPUParticles3D.new()
	var bm := BoxMesh.new()
	bm.size = Vector3(0.12, 0.12, 0.12)
	bm.material = _glow_mat(Color(1.0, 0.6, 0.2), 4.0)
	fire.mesh = bm
	fire.amount = 40
	fire.lifetime = 0.4
	fire.local_coords = false
	fire.emission_shape = CPUParticles3D.EMISSION_SHAPE_SPHERE
	fire.emission_sphere_radius = 0.45
	fire.gravity = Vector3(0, 3, 0)
	fire.scale_amount_curve = _shrink_curve()
	mi.add_child(fire)
	var tw := mi.create_tween()
	tw.tween_property(mi, "global_position", Vector3(pos.x, 0.4, pos.z), duration).set_trans(Tween.TRANS_QUAD).set_ease(Tween.EASE_IN)
	tw.tween_callback(mi.queue_free)


## Shadowy puff for blinks.
static func smoke(parent: Node, pos: Vector3, color: Color) -> void:
	flash(parent, pos + Vector3.UP * 0.9, Color(color.r * 0.5, color.g * 0.4, color.b * 0.7, 0.8), 0.7, 0.25)
	sparks(parent, pos + Vector3.UP * 0.9, color, 26, 4.0)
