extends Node3D
## Skill sandbox: flat plain, sun, sky, the water mage, camera and HUD.

const Player := preload("res://scripts/player.gd")
const CameraRig := preload("res://scripts/camera_rig.gd")
const Hud := preload("res://scripts/hud.gd")
const World := preload("res://scripts/world.gd")


func _ready() -> void:
	_setup_input()
	World.build(self)
	var player := Player.new()
	var rig := CameraRig.new()
	player.cam_rig = rig
	rig.target = player
	add_child(player)
	add_child(rig)
	var hud := Hud.new()
	hud.player = player
	add_child(hud)


func _unhandled_input(event: InputEvent) -> void:
	if event is InputEventMouseButton and event.pressed and event.button_index == MOUSE_BUTTON_LEFT:
		Input.mouse_mode = Input.MOUSE_MODE_CAPTURED
	elif event.is_action_pressed("ui_cancel"):
		Input.mouse_mode = Input.MOUSE_MODE_VISIBLE


func _setup_input() -> void:
	World.bind_keys("move_forward", [KEY_W, KEY_UP])
	World.bind_keys("move_back", [KEY_S, KEY_DOWN])
	World.bind_keys("move_left", [KEY_A, KEY_LEFT])
	World.bind_keys("move_right", [KEY_D, KEY_RIGHT])
	World.bind_keys("jump", [KEY_SPACE])
	World.bind_keys("dash", [KEY_SHIFT])
	World.bind_keys("skill", [KEY_E])
	World.bind_keys("shield", [KEY_R])
	World.bind_keys("burst", [KEY_Q])
	World.bind_keys("attack", [KEY_J])
	World.bind_mouse("attack", MOUSE_BUTTON_LEFT)
