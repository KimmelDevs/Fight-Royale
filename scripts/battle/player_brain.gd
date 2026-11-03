extends RefCounted
## Player controls: right button attacks (tap or hold), left button blocks, Space jumps,
## Z/X/C cast skills, WASD moves relative to the camera.


func think(f, _delta: float) -> void:
	f.in_attack = Input.is_action_pressed("attack")
	f.in_block = Input.is_action_pressed("block")
	f.in_jump = Input.is_action_pressed("jump")
	for key: String in ["z", "x", "c"]:
		if Input.is_action_just_pressed("skill_" + key):
			f.in_skill = key
	var input := Input.get_vector("move_left", "move_right", "move_forward", "move_back")
	var cam: Camera3D = f.get_viewport().get_camera_3d()
	if input != Vector2.ZERO and cam:
		var right := cam.global_basis.x
		var fwd := -cam.global_basis.z
		right.y = 0.0
		fwd.y = 0.0
		f.move_dir = right.normalized() * input.x - fwd.normalized() * input.y
