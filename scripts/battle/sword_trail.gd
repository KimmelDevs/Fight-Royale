extends MeshInstance3D
## Fading ribbon swept by the blade while `emitting` is on. Built in world space.

const LIFE := 0.16
const MAX_SAMPLES := 28

var base_node: Node3D
var tip_node: Node3D
var color := Color(0.5, 0.9, 1.0)
var emitting := false

var _samples: Array = []  # [base: Vector3, tip: Vector3, age: float]
var _imesh := ImmediateMesh.new()
var _mat := StandardMaterial3D.new()


func _ready() -> void:
	top_level = true
	global_transform = Transform3D.IDENTITY
	mesh = _imesh
	cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	_mat.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	_mat.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	_mat.blend_mode = BaseMaterial3D.BLEND_MODE_ADD
	_mat.cull_mode = BaseMaterial3D.CULL_DISABLED
	_mat.vertex_color_use_as_albedo = true


func _process(delta: float) -> void:
	for s: Array in _samples:
		s[2] += delta
	while not _samples.is_empty() and _samples[0][2] > LIFE:
		_samples.pop_front()
	if emitting and base_node and tip_node:
		var b := base_node.global_position
		var t := tip_node.global_position
		# Insert a midpoint so fast swings stay a smooth arc instead of a fan of slabs.
		if not _samples.is_empty():
			var last: Array = _samples[-1]
			_samples.append([(last[0] + b) * 0.5, ((last[1] + t) * 0.5 - (last[0] + b) * 0.5).normalized() * b.distance_to(t) + (last[0] + b) * 0.5, delta * 0.5])
		_samples.append([b, t, 0.0])
		while _samples.size() > MAX_SAMPLES:
			_samples.pop_front()
	_imesh.clear_surfaces()
	if _samples.size() < 2:
		return
	_imesh.surface_begin(Mesh.PRIMITIVE_TRIANGLE_STRIP, _mat)
	for s: Array in _samples:
		var f := clampf(1.0 - s[2] / LIFE, 0.0, 1.0)
		_imesh.surface_set_color(Color(color.r, color.g, color.b, 0.0))
		_imesh.surface_add_vertex(s[0])
		_imesh.surface_set_color(Color(color.r * 1.2, color.g * 1.2, color.b * 1.2, f * 0.9))
		_imesh.surface_add_vertex(s[1])
	_imesh.surface_end()
