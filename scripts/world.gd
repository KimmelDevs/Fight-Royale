extends RefCounted
## Shared scene setup: sky, sun, flat ground, and input binding helpers.

const GROUND_SHADER := preload("res://shaders/ground.gdshader")

## Direction toward the sun. The toon/face shaders use the same default light_dir.
const LIGHT_DIR := Vector3(0.45, 0.8, 0.4)


static func build(parent: Node3D) -> void:
	var sky_mat := ProceduralSkyMaterial.new()
	sky_mat.sky_top_color = Color("6aa6ea")
	sky_mat.sky_horizon_color = Color("d8eeff")
	sky_mat.ground_horizon_color = Color("d8eeff")
	sky_mat.ground_bottom_color = Color("a8c8e8")
	var sky := Sky.new()
	sky.sky_material = sky_mat

	var env := Environment.new()
	env.background_mode = Environment.BG_SKY
	env.sky = sky
	env.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	env.ambient_light_color = Color("c9d8e8")
	env.ambient_light_energy = 0.25
	# Linear keeps the hand-picked toon colors exact; glow makes the water pop.
	env.tonemap_mode = Environment.TONE_MAPPER_LINEAR
	env.glow_enabled = true
	env.glow_intensity = 0.7
	env.glow_hdr_threshold = 1.0
	env.glow_blend_mode = Environment.GLOW_BLEND_MODE_ADDITIVE
	env.fog_enabled = true
	env.fog_light_color = Color("d8eeff")
	env.fog_density = 0.003
	var world_env := WorldEnvironment.new()
	world_env.environment = env
	parent.add_child(world_env)

	var sun := DirectionalLight3D.new()
	sun.basis = Basis.looking_at(-LIGHT_DIR.normalized(), Vector3.UP)
	sun.light_energy = 1.0
	sun.shadow_enabled = true
	sun.directional_shadow_max_distance = 40.0
	parent.add_child(sun)

	var ground := MeshInstance3D.new()
	var plane := PlaneMesh.new()
	plane.size = Vector2(400, 400)
	ground.mesh = plane
	var gmat := ShaderMaterial.new()
	gmat.shader = GROUND_SHADER
	ground.material_override = gmat
	parent.add_child(ground)

	var body := StaticBody3D.new()
	var col := CollisionShape3D.new()
	col.shape = WorldBoundaryShape3D.new()
	body.add_child(col)
	parent.add_child(body)


static func bind_keys(action: String, keys: Array[Key]) -> void:
	if not InputMap.has_action(action):
		InputMap.add_action(action)
	for k in keys:
		var ev := InputEventKey.new()
		ev.physical_keycode = k
		InputMap.action_add_event(action, ev)


static func bind_mouse(action: String, button: MouseButton) -> void:
	if not InputMap.has_action(action):
		InputMap.add_action(action)
	var ev := InputEventMouseButton.new()
	ev.button_index = button
	InputMap.action_add_event(action, ev)
