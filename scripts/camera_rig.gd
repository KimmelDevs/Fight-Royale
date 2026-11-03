extends Node3D
## Third-person orbit camera with smooth follow and trauma-based screen shake.

var target: Node3D
var yaw := 0.0
var pitch := -0.22
var distance := 3.4
var mouse_sensitivity := 0.004

var trauma := 0.0
var _shake_t := 0.0
var _pitch_node: Node3D
var _cam: Camera3D


func _ready() -> void:
	_pitch_node = Node3D.new()
	add_child(_pitch_node)
	_cam = Camera3D.new()
	_cam.fov = 55.0
	_pitch_node.add_child(_cam)
	_cam.make_current()
	if target:
		global_position = target.global_position + Vector3(0, 1.2, 0)


func _unhandled_input(event: InputEvent) -> void:
	if event is InputEventMouseMotion and Input.mouse_mode == Input.MOUSE_MODE_CAPTURED:
		yaw -= event.relative.x * mouse_sensitivity
		pitch = clampf(pitch - event.relative.y * mouse_sensitivity, -1.2, 0.15)
	elif event is InputEventMouseButton and event.pressed:
		if event.button_index == MOUSE_BUTTON_WHEEL_UP:
			distance = maxf(1.8, distance - 0.3)
		elif event.button_index == MOUSE_BUTTON_WHEEL_DOWN:
			distance = minf(10.0, distance + 0.3)


func _process(delta: float) -> void:
	if target:
		var goal := target.global_position + Vector3(0, 1.2, 0)
		global_position = global_position.lerp(goal, 1.0 - exp(-12.0 * delta))
	rotation.y = yaw
	_pitch_node.rotation.x = pitch
	_cam.position = Vector3(0, 0, distance)

	# Shake the camera offset (never the player). shake = trauma^2 keeps small hits subtle.
	trauma = maxf(trauma - 1.3 * delta, 0.0)
	var shake := trauma * trauma
	_shake_t += delta * 30.0
	_cam.h_offset = 0.25 * shake * sin(_shake_t * 1.7)
	_cam.v_offset = 0.18 * shake * sin(_shake_t * 2.3)
	_cam.rotation.z = 0.05 * shake * sin(_shake_t * 1.1)


func add_trauma(amount: float) -> void:
	trauma = clampf(trauma + amount, 0.0, 1.0)


## Camera forward on the ground plane.
func forward_flat() -> Vector3:
	return Vector3(-sin(yaw), 0.0, -cos(yaw))
