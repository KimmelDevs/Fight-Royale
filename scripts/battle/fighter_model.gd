extends "res://scripts/model_builder.gd"
## Procedural cel-shaded fighter. Faces +Z. Right hand (-X side) holds the main weapon.
## `look` (see roster.gd) picks the outfit kit (knight / mage / assassin), hair style, hat and colors.
## Posed by blend() each frame with joint rotations from a pose dictionary (see kits.gd).

const Mat := preload("res://scripts/toon_mat.gd")
const Gen := preload("res://scripts/mesh_gen.gd")
const Roster := preload("res://scripts/roster.gd")

const SKIN := Color("ffe9df")
const SKIN_SHADE := Color(1.0, 0.82, 0.82)
const METAL_SHADE := Color(0.62, 0.66, 0.85)
const BROWN := Color("5a3a2a")
const PEARL := Color("fff8ee")
const HEAD_R := 0.19
const HEAD_SCALE := 0.92
const HIP_HEIGHT := 0.84
const CAP_C := Vector3(0, 0.035, -0.035)
const JOINTS := ["torso", "head", "arm_r", "hand_r", "arm_l", "hand_l", "leg_l", "leg_r"]

var look: Dictionary = Roster.CHARACTERS[0].look
var kit := "knight"

var hips: Node3D
var torso: Node3D
var head: Node3D
var arm_l: Node3D
var arm_r: Node3D
var hand_l: Node3D
var hand_r: Node3D
var leg_l: Node3D
var leg_r: Node3D
var skirt: Node3D
var cape: Node3D
var blade_base: Node3D
var blade_tip: Node3D
## Where blocked hits spark (shield, barrier or off-hand dagger).
var shield_node: Node3D
## Where spells and thrown weapons leave from.
var cast_point: Node3D
var hair_sway: Array[Node3D] = []

## 0..1 walk cycle weight, set by the fighter.
var walk := 0.0
## Kick that decays to 0; pushes the torso back (blocked hits, clashes, landings).
var recoil := 0.0
## 0..1 charged-attack glow on the weapon.
var charge := 0.0

var _joints := {}
var _cur := {}
var _hips_y := 0.0
var _t := 0.0
var _walk_phase := 0.0
var _hair_mat: ShaderMaterial
var _face_mat: ShaderMaterial
var _glow_mat: StandardMaterial3D
var _barrier: Node3D
var _meshes: Array[MeshInstance3D] = []
var _flash_mat := StandardMaterial3D.new()
var _flash_tween: Tween
var _blink_wait := 2.0
var _blink_t := -1.0


func _ready() -> void:
	kit = look.get("kit", "knight")
	_hair_mat = Mat.toon(look.hair, true, 0.3, Color(0, 0, 0), look.hair_shade, 0.0045)
	_glow_mat = StandardMaterial3D.new()
	_glow_mat.albedo_color = Color(0, 0, 0)
	_glow_mat.emission_enabled = true
	_glow_mat.emission = look.glow
	_glow_mat.emission_energy_multiplier = 1.5

	hips = _pivot(self, Vector3(0, HIP_HEIGHT, 0))
	match kit:
		"mage":
			_mage_legs()
			_mage_skirt()
			_mage_torso()
			_mage_arms()
		"assassin":
			_assassin_legs()
			_assassin_lower()
			_assassin_torso()
			_assassin_arms()
		_:
			_knight_legs()
			_knight_skirt()
			_knight_torso()
			_knight_arms()
	_build_head()
	match kit:
		"mage":
			_build_staff()
		"assassin":
			_build_daggers()
		_:
			_build_sword()
			_build_shield()

	_joints = {"torso": torso, "head": head, "arm_r": arm_r, "hand_r": hand_r,
		"arm_l": arm_l, "hand_l": hand_l, "leg_l": leg_l, "leg_r": leg_r}
	for j: String in JOINTS:
		_cur[j] = Vector3.ZERO
	_collect_meshes(self)
	_flash_mat.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	_flash_mat.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	_flash_mat.albedo_color = Color(1, 1, 1, 0)


func _collect_meshes(n: Node) -> void:
	for c in n.get_children():
		if c is MeshInstance3D:
			_meshes.append(c)
		_collect_meshes(c)


# --- material shortcuts -------------------------------------------------------

func _toon(c: Color, outline := true, rim := 0.3) -> ShaderMaterial:
	return Mat.toon(c, outline, rim)


func _metal() -> ShaderMaterial:
	return Mat.toon(look.metal, true, 0.7, Color(0, 0, 0), METAL_SHADE)


func _skin() -> ShaderMaterial:
	return Mat.toon(SKIN, true, 0.2, Color(0, 0, 0), SKIN_SHADE)


func _gem() -> ShaderMaterial:
	var g: Color = look.glow
	return Mat.toon(g, false, 0.6, Color(g.r * 0.35, g.g * 0.35, g.b * 0.35))


func _bow(parent: Node3D, pos: Vector3, s := 1.0, rot := Vector3.ZERO) -> void:
	var b := _pivot(parent, pos, rot)
	b.scale = Vector3.ONE * s
	for side: float in [1.0, -1.0]:
		_mesh(b, _sphere(0.04, 12), _toon(look.tunic), Vector3(0.04 * side, 0, 0), Vector3(0, 0, 0.5 * side), Vector3(1.2, 0.75, 0.45))
		_mesh(b, _box(Vector3(0.018, 0.06, 0.006)), _toon(look.tunic), Vector3(0.015 * side, -0.035, 0.0), Vector3(0, 0, 0.35 * side))
	_mesh(b, _sphere(0.018, 12), _toon(look.trim), Vector3(0, 0, 0.012))


func _strand(parent: Node3D, p0: Vector3, p1: Vector3, p2: Vector3, width: float, thick: float, sway := false) -> void:
	var mesh := Gen.strand(p0, p1, p2, width, thick, CAP_C)
	if sway:
		var pv := _pivot(parent, p0)
		_mesh(pv, mesh, _hair_mat, -p0)
		hair_sway.append(pv)
	else:
		_mesh(parent, mesh, _hair_mat)


func _back_cape(length: float, a0: float, top_r: float, bottom_r: float, tail_len: float, wind := 0.03) -> void:
	var tails := func(a: float) -> float: return tail_len * pow(absf(a - PI) / (PI - a0), 2.0)
	cape = _pivot(torso, Vector3(0, 0.29, -0.03))
	_mesh(cape, Gen.cone_sheet(top_r, bottom_r, length, a0, TAU - a0, 32, 10, 0.0, 0.0, tails), Mat.cloth(look.cape, {
		"bottom": look.cape_bottom, "pattern": look.trim, "pattern_strength": 0.9, "pattern_v": 0.74,
		"pattern_freq": 3.0, "trim_bottom": 0.03, "trim_sides": 0.015, "wind": wind,
	}))


func _hand(parent: Node3D, color: Color) -> Node3D:
	var hand := _pivot(parent, Vector3(0, -0.38, 0))
	_mesh(hand, _sphere(0.033, 14), Mat.toon(color, true, 0.2, Color(0, 0, 0), SKIN_SHADE if color == SKIN else Mat.DEFAULT_SHADE),
		Vector3.ZERO, Vector3.ZERO, Vector3(0.92, 1.1, 0.8))
	return hand


# --- knight -------------------------------------------------------------------

func _knight_legs() -> void:
	for side: float in [1.0, -1.0]:
		var leg := _pivot(hips, Vector3(0.08 * side, 0.0, 0.0))
		_mesh(leg, _cap(0.05, 0.76), _toon(look.pants), Vector3(0, -0.37, 0))
		_mesh(leg, _cyl(0.058, 0.062, 0.36, 16), _toon(look.boots), Vector3(0, -0.66, 0.0))
		_mesh(leg, _box(Vector3(0.075, 0.26, 0.03)), _metal(), Vector3(0, -0.6, 0.052))
		_mesh(leg, _sphere(0.045, 14), _metal(), Vector3(0, -0.42, 0.045), Vector3.ZERO, Vector3(1.0, 0.9, 0.6))
		_mesh(leg, _sphere(0.012, 8), _gem(), Vector3(0, -0.42, 0.075))
		_mesh(leg, _torus(0.058, 0.068), _toon(look.trim), Vector3(0, -0.48, 0), Vector3.ZERO, Vector3(1, 0.6, 1))
		_mesh(leg, _box(Vector3(0.11, 0.06, 0.09)), _metal(), Vector3(0, -0.785, 0.07))
		_mesh(leg, _box(Vector3(0.12, 0.035, 0.2)), _toon(look.pants), Vector3(0, -0.822, 0.03))
		if side > 0.0:
			leg_l = leg
		else:
			leg_r = leg


func _knight_skirt() -> void:
	skirt = _pivot(hips, Vector3(0, 0.04, 0))
	_mesh(skirt, Gen.cone_sheet(0.11, 0.28, 0.3, 0.0, TAU, 40, 5), Mat.cloth(look.tunic, {
		"pattern": look.band, "pattern_strength": 1.0, "pattern_v": 0.68, "pattern_freq": 3.0,
		"pattern_fill": 1.0, "trim_bottom": 0.06,
	}))


func _knight_torso() -> void:
	torso = _pivot(hips, Vector3(0, 0.05, 0))
	_mesh(torso, _cyl(0.095, 0.11, 0.3), _toon(look.tunic), Vector3(0, 0.14, 0))
	_mesh(torso, _sphere(0.125, 24), _metal(), Vector3(0, 0.17, 0.035), Vector3.ZERO, Vector3(1.0, 0.95, 0.72))
	_mesh(torso, _torus(0.1, 0.112), _toon(look.trim, false), Vector3(0, 0.08, 0.03), Vector3(0.25, 0, 0), Vector3(1.05, 0.5, 0.9))
	_mesh(torso, _sphere(0.02, 12), _gem(), Vector3(0, 0.2, 0.125), Vector3.ZERO, Vector3(0.8, 1.2, 0.6))
	_mesh(torso, _torus(0.108, 0.13), _toon(BROWN), Vector3(0, -0.01, 0), Vector3(0.1, 0, 0), Vector3(1, 0.7, 1))
	_mesh(torso, _box(Vector3(0.04, 0.034, 0.012)), _toon(look.trim), Vector3(0, -0.01, 0.128))
	_mesh(torso, Gen.cone_sheet(0.048, 0.072, 0.08, 0.0, TAU, 24, 2), Mat.cloth(look.band, {"trim_bottom": 0.2}), Vector3(0, 0.38, 0))
	_mesh(torso, _cyl(0.034, 0.036, 0.08), _skin(), Vector3(0, 0.36, 0))
	_mesh(torso, _sphere(0.078, 18), _metal(), Vector3(-0.14, 0.27, 0), Vector3(0, 0, 0.3), Vector3(1.15, 0.75, 1.05))
	_mesh(torso, _torus(0.075, 0.088), _toon(look.trim), Vector3(-0.15, 0.255, 0), Vector3(0, 0, 0.3), Vector3(1.1, 0.5, 1.0))
	_mesh(torso, _sphere(0.062, 16), _metal(), Vector3(0.135, 0.27, 0), Vector3(0, 0, -0.3), Vector3(1.1, 0.7, 1.0))
	_back_cape(0.62, 2.0, 0.14, 0.34, 0.18)


func _knight_arms() -> void:
	for side: float in [1.0, -1.0]:
		var a := _pivot(torso, Vector3(0.135 * side, 0.25, 0))
		_mesh(a, _cap(0.031, 0.36), _toon(look.band), Vector3(0, -0.18, 0))
		_mesh(a, _cyl(0.042, 0.036, 0.16, 14), _metal(), Vector3(0, -0.29, 0))
		_mesh(a, _torus(0.036, 0.048), _toon(look.trim), Vector3(0, -0.21, 0), Vector3.ZERO, Vector3(1, 0.6, 1))
		var hand := _hand(a, look.pants)
		if side > 0.0:
			arm_l = a
			hand_l = hand
		else:
			arm_r = a
			hand_r = hand


# --- mage (the water-mage silhouette, recolored per element) --------------------

func _mage_legs() -> void:
	for side: float in [1.0, -1.0]:
		var leg := _pivot(hips, Vector3(0.075 * side, 0.0, 0.0))
		_mesh(leg, _cap(0.05, 0.76), _toon(look.pants), Vector3(0, -0.37, 0))
		_mesh(leg, _cyl(0.055, 0.055, 0.025), _toon(look.trim), Vector3(0, -0.13, 0))
		_bow(leg, Vector3(0, -0.15, 0.05), 0.55)
		_mesh(leg, _cyl(0.058, 0.06, 0.24, 16), _toon(look.boots), Vector3(0, -0.7, 0.005))
		_mesh(leg, _cyl(0.078, 0.07, 0.07, 16), _toon(look.band), Vector3(0, -0.585, 0))
		_mesh(leg, _box(Vector3(0.11, 0.06, 0.09)), _toon(look.band), Vector3(0, -0.785, 0.07))
		_mesh(leg, _box(Vector3(0.12, 0.035, 0.2)), _toon(look.boots), Vector3(0, -0.822, 0.03))
		_mesh(leg, _sphere(0.014, 10), _gem(), Vector3(0, -0.585, 0.08))
		if side > 0.0:
			leg_l = leg
		else:
			leg_r = leg


func _mage_skirt() -> void:
	skirt = _pivot(hips, Vector3(0, 0.04, 0))
	_mesh(skirt, Gen.cone_sheet(0.2, 0.33, 0.1, 0.0, TAU, 56, 3, 0.02, 22), Mat.cloth(look.cape_bottom), Vector3(0, -0.15, 0))
	_mesh(skirt, Gen.cone_sheet(0.105, 0.31, 0.26, 0.0, TAU, 48, 6, 0.012, 14), Mat.cloth(look.band, {
		"pattern": look.emblem, "pattern_strength": 1.0, "pattern_v": 0.6,
		"pattern_freq": 5.0, "pattern_fill": 1.0, "trim_bottom": 0.07,
	}))


func _mage_torso() -> void:
	torso = _pivot(hips, Vector3(0, 0.05, 0))
	_mesh(torso, _cyl(0.09, 0.105, 0.3), _toon(look.band), Vector3(0, 0.14, 0))
	_mesh(torso, _cyl(0.106, 0.109, 0.11), _toon(look.tunic), Vector3(0, 0.05, 0))
	for y: float in [0.105, -0.005]:
		_mesh(torso, _torus(0.1, 0.112), _toon(look.trim, false), Vector3(0, y, 0), Vector3.ZERO, Vector3(1, 0.4, 1))
	_mesh(torso, _torus(0.105, 0.127), _toon(BROWN), Vector3(0, -0.015, 0), Vector3(0.1, 0, 0), Vector3(1, 0.7, 1))
	_mesh(torso, _sphere(0.034, 16), Mat.water(Color(look.glow.r, look.glow.g, look.glow.b, 0.8), 1.6), Vector3(-0.12, -0.075, 0.075))
	_mesh(torso, Gen.cone_sheet(0.075, 0.235, 0.15, 0.0, TAU, 40, 4, 0.006, 12), Mat.cloth(look.tunic, {"trim_bottom": 0.14}), Vector3(0, 0.31, 0))
	_mesh(torso, Gen.cone_sheet(0.04, 0.066, 0.05, 0.0, TAU, 24, 2, 0.01, 16), Mat.cloth(look.band), Vector3(0, 0.36, 0))
	for side: float in [1.0, -1.0]:
		_bow(torso, Vector3(0.15 * side, 0.21, 0.09), 1.2, Vector3(0, 0.5 * side, 0))
	for i in 3:
		_mesh(torso, _sphere(0.03, 12), _toon(look.band), Vector3(0, 0.235 - i * 0.03, 0.105 - i * 0.002), Vector3.ZERO, Vector3(1.1 - i * 0.15, 0.6, 0.45))
	_bow(torso, Vector3(0, 0.272, 0.12), 1.0)
	_mesh(torso, _sphere(0.02, 12), _gem(), Vector3(0, 0.258, 0.142), Vector3.ZERO, Vector3(0.8, 1.2, 0.6))
	_mesh(torso, _cyl(0.032, 0.034, 0.08), _skin(), Vector3(0, 0.36, 0))
	_back_cape(0.6, 1.75, 0.13, 0.4, 0.22, 0.035)


func _mage_arms() -> void:
	for side: float in [1.0, -1.0]:
		var a := _pivot(torso, Vector3(0.125 * side, 0.25, 0))
		_mesh(a, _sphere(0.033, 14), _skin())
		_mesh(a, _cap(0.027, 0.36), _skin(), Vector3(0, -0.18, 0))
		var b: Color = look.band
		_mesh(a, Gen.cone_sheet(0.036, 0.115, 0.27, 0.0, TAU, 28, 4, 0.012, 9), Mat.cloth(b, {
			"bottom": b.lerp(look.cape_bottom, 0.35), "trim_bottom": 0.07,
		}), Vector3(0, -0.07, 0))
		var hand := _hand(a, SKIN)
		if side > 0.0:
			arm_l = a
			hand_l = hand
		else:
			arm_r = a
			hand_r = hand


# --- assassin -------------------------------------------------------------------

func _assassin_legs() -> void:
	for side: float in [1.0, -1.0]:
		var leg := _pivot(hips, Vector3(0.075 * side, 0.0, 0.0))
		_mesh(leg, _cap(0.048, 0.76), _toon(look.pants), Vector3(0, -0.37, 0))
		# Wrapped shins and soft boots.
		for i in 4:
			_mesh(leg, _torus(0.044, 0.056), _toon(look.band), Vector3(0, -0.5 - i * 0.055, 0), Vector3(0.25 * (1 if i % 2 == 0 else -1), 0, 0), Vector3(1, 0.6, 1))
		_mesh(leg, _box(Vector3(0.1, 0.05, 0.18)), _toon(look.boots), Vector3(0, -0.8, 0.03))
		_mesh(leg, _box(Vector3(0.012, 0.18, 0.04)), _metal(), Vector3(0.055 * side, -0.25, 0.0))
		if side > 0.0:
			leg_l = leg
		else:
			leg_r = leg


func _assassin_lower() -> void:
	skirt = _pivot(hips, Vector3(0, 0.04, 0))
	# Split tassets: front and back flaps only, so the legs read clearly.
	for a0: float in [-0.7, PI - 0.7]:
		_mesh(skirt, Gen.cone_sheet(0.11, 0.2, 0.34, a0, a0 + 1.4, 12, 5), Mat.cloth(look.tunic, {
			"bottom": look.band, "trim_bottom": 0.05, "trim_sides": 0.04,
		}))
	_mesh(skirt, _cyl(0.11, 0.12, 0.08, 20), _toon(look.pants), Vector3(0, -0.02, 0))


func _assassin_torso() -> void:
	torso = _pivot(hips, Vector3(0, 0.05, 0))
	_mesh(torso, _cyl(0.088, 0.1, 0.3), _toon(look.tunic), Vector3(0, 0.14, 0))
	# Diagonal sash, belt with pouches.
	_mesh(torso, _torus(0.1, 0.118), _toon(look.band), Vector3(0, 0.15, 0), Vector3(0, 0, 0.6), Vector3(1, 1.6, 0.95))
	_mesh(torso, _torus(0.1, 0.122), _toon(BROWN), Vector3(0, -0.01, 0), Vector3(0.1, 0, 0), Vector3(1, 0.7, 1))
	for x: float in [0.08, -0.08]:
		_mesh(torso, _box(Vector3(0.05, 0.05, 0.03)), _toon(BROWN), Vector3(x, -0.04, 0.09))
	_mesh(torso, _box(Vector3(0.03, 0.03, 0.01)), _toon(look.trim), Vector3(0, -0.01, 0.122), Vector3(0, 0, PI / 4.0))
	_mesh(torso, _cyl(0.032, 0.034, 0.08), _skin(), Vector3(0, 0.36, 0))
	# Scarf wrapped at the neck; its long tails act as the cape.
	_mesh(torso, Gen.cone_sheet(0.062, 0.1, 0.09, 0.0, TAU, 24, 2, 0.008, 10), Mat.cloth(look.band), Vector3(0, 0.37, 0))
	cape = _pivot(torso, Vector3(0, 0.32, -0.08))
	var scarf := Mat.toon(look.band, true, 0.3)
	for side: float in [1.0, -1.0]:
		var m := Gen.strand(Vector3(0.03 * side, 0, 0), Vector3(0.08 * side, -0.1, -0.25), Vector3(0.12 * side, -0.55, -0.32), 0.06, 0.012, Vector3(0, 0, 0.3))
		_mesh(cape, m, scarf)
	_mesh(torso, _sphere(0.06, 14), _metal(), Vector3(-0.13, 0.27, 0), Vector3(0, 0, 0.3), Vector3(1.0, 0.7, 1.0))


func _assassin_arms() -> void:
	for side: float in [1.0, -1.0]:
		var a := _pivot(torso, Vector3(0.125 * side, 0.25, 0))
		_mesh(a, _cap(0.029, 0.36), _toon(look.tunic), Vector3(0, -0.18, 0))
		_mesh(a, _cyl(0.038, 0.034, 0.14, 12), _metal(), Vector3(0, -0.3, 0))
		_mesh(a, _torus(0.034, 0.044), _toon(look.band), Vector3(0, -0.23, 0), Vector3.ZERO, Vector3(1, 0.6, 1))
		var hand := _hand(a, look.pants)
		if side > 0.0:
			arm_l = a
			hand_l = hand
		else:
			arm_r = a
			hand_r = hand


# --- head, hair, hats -----------------------------------------------------------------

func _build_head() -> void:
	head = _pivot(torso, Vector3(0, 0.37, 0))
	head.scale = Vector3.ONE * HEAD_SCALE
	var hc := _pivot(head, Vector3(0, HEAD_R, 0))
	_face_mat = Mat.face(SKIN)
	_face_mat.set_shader_parameter("iris_top", look.iris_top)
	_face_mat.set_shader_parameter("iris_bottom", look.iris_bottom)
	_face_mat.set_shader_parameter("eye_dark", look.eye_dark)
	_mesh(hc, _sphere(HEAD_R, 40), _face_mat, Vector3.ZERO, Vector3.ZERO, Vector3(1.0, 0.98, 0.97))
	_mesh(hc, _sphere(0.205, 32), _hair_mat, CAP_C)
	var hl: Color = look.hair
	_mesh(hc, _torus(0.188, 0.207), Mat.toon(hl.lightened(0.45), false, 0.0), Vector3(0, 0.085, -0.035), Vector3(-0.15, 0, 0), Vector3(1, 0.35, 1))
	match look.get("style", "short"):
		"ponytail":
			_hair_ponytail(hc)
		"bob":
			_hair_bob(hc)
		"twintails":
			_hair_twintails(hc)
		_:
			_hair_short(hc)
	match look.get("hat", "none"):
		"beret":
			_hat_beret(hc)
		"witch":
			_hat_witch(hc)
		"goggles":
			_hat_goggles(hc)
		"hood":
			_hat_hood(hc)


func _bangs(hc: Node3D, tips: Array[float], sweep: float) -> void:
	for k in tips.size():
		var x := lerpf(-0.15, 0.15, k / float(tips.size() - 1))
		var y := tips[k]
		var tx := clampf(x + sweep, -0.17, 0.17)
		var root := CAP_C + Vector3(x * 0.6, 0.75, 0.62).normalized() * 0.2
		var tip := Vector3(tx, y, sqrt(maxf(0.19 * 0.19 - tx * tx - y * y, 0.0))).normalized() * 0.2
		var mid := CAP_C + ((root + tip) * 0.5 - CAP_C).normalized() * 0.236
		_strand(hc, root, mid, tip, 0.036, 0.015)


func _side_locks(hc: Node3D, length: float) -> void:
	for side: float in [1.0, -1.0]:
		_strand(hc, Vector3(0.15 * side, 0.1, 0.11), Vector3(0.21 * side, -0.03, 0.11), Vector3(0.19 * side, -0.05 - length, 0.08), 0.04, 0.016, true)


func _hair_short(hc: Node3D) -> void:
	_mesh(hc, _sphere(0.18, 28), _hair_mat, Vector3(0, -0.03, -0.07), Vector3.ZERO, Vector3(1.05, 0.78, 0.92))
	var tips: Array[float] = [0.08, 0.045, 0.07, 0.035, 0.065, 0.04, 0.085]
	_bangs(hc, tips, 0.0)
	_side_locks(hc, 0.07)
	for side: float in [1.0, -1.0]:
		_mesh(hc, _sphere(0.014, 10), _gem(), Vector3(0.19 * side, -0.07, 0.0), Vector3.ZERO, Vector3(0.8, 1.4, 0.8))
	for i in 9:
		var a := lerpf(1.4, TAU - 1.4, i / 8.0)
		var d := Vector3(sin(a), 0.0, cos(a))
		_strand(hc, CAP_C + d * 0.15 + Vector3.UP * 0.12, CAP_C + d * 0.23, CAP_C + d * 0.28 + Vector3.UP * -0.1, 0.06, 0.02, true)
	for a: float in [PI - 0.9, PI - 0.3, PI + 0.4, PI + 1.0]:
		var d := Vector3(sin(a), 0.0, cos(a))
		_strand(hc, CAP_C + d * 0.05 + Vector3.UP * 0.19, CAP_C + d * 0.15 + Vector3.UP * 0.26, CAP_C + d * 0.26 + Vector3.UP * 0.2, 0.045, 0.016)


func _hair_bob(hc: Node3D) -> void:
	_mesh(hc, _sphere(0.19, 28), _hair_mat, Vector3(0, -0.07, -0.06), Vector3.ZERO, Vector3(1.08, 0.85, 0.95))
	var tips: Array[float] = [0.06, 0.025, 0.045, 0.005, 0.03, -0.005, 0.04, 0.02, 0.06]
	_bangs(hc, tips, 0.0)
	_side_locks(hc, 0.17)
	for i in 11:
		var a := lerpf(1.35, TAU - 1.35, i / 10.0)
		var d := Vector3(sin(a), 0.0, cos(a))
		var flick := 0.02 * sin(i * 2.3)
		_strand(hc, CAP_C + d * 0.16 + Vector3.UP * 0.1, CAP_C + d * 0.235 + Vector3.UP * -0.06,
			CAP_C + d * (0.27 + flick) + Vector3.UP * (-0.19 + flick), 0.065, 0.022, true)


func _hair_ponytail(hc: Node3D) -> void:
	_mesh(hc, _sphere(0.185, 28), _hair_mat, Vector3(0, -0.05, -0.06), Vector3.ZERO, Vector3(1.05, 0.85, 0.95))
	var tips: Array[float] = [0.05, 0.03, 0.01, -0.005, 0.01, 0.03, 0.05, 0.07]
	_bangs(hc, tips, 0.04)
	_side_locks(hc, 0.22)
	var tie := Vector3(0, 0.13, -0.21)
	_mesh(hc, _torus(0.022, 0.04), _toon(look.trim), tie, Vector3(PI / 2.0 + 0.5, 0, 0))
	var tail := _pivot(hc, tie)
	hair_sway.append(tail)
	for i in 5:
		var sx := (i - 2) * 0.025
		var m := Gen.strand(Vector3(sx * 0.5, 0.0, 0.0), Vector3(sx, 0.02, -0.2), Vector3(sx * 1.6, -0.48 + absf(sx) * 2.0, -0.2), 0.06, 0.03, Vector3(0, 0, 0.3))
		_mesh(tail, m, _hair_mat)
	if look.get("hat", "none") == "none":
		var orn := Vector3(0.14, 0.15, 0.1)
		for i in 5:
			var a := TAU * i / 5.0
			_mesh(hc, _sphere(0.017, 10), _toon(look.emblem), orn + Vector3(cos(a), sin(a), 0.0) * 0.02)
		_mesh(hc, _sphere(0.012, 8), _toon(look.trim), orn + Vector3(0, 0, 0.012))


func _hair_twintails(hc: Node3D) -> void:
	_mesh(hc, _sphere(0.185, 28), _hair_mat, Vector3(0, -0.05, -0.06), Vector3.ZERO, Vector3(1.05, 0.82, 0.95))
	var tips: Array[float] = [0.06, 0.03, 0.05, 0.015, 0.04, 0.02, 0.06]
	_bangs(hc, tips, 0.0)
	_side_locks(hc, 0.12)
	for side: float in [1.0, -1.0]:
		var tie := Vector3(0.17 * side, 0.1, -0.1)
		_mesh(hc, _sphere(0.03, 12), _toon(look.trim), tie)
		var tail := _pivot(hc, tie)
		hair_sway.append(tail)
		for i in 3:
			var sz := (i - 1) * 0.03
			var m := Gen.strand(Vector3(0, 0, sz), Vector3(0.12 * side, -0.05, sz - 0.05), Vector3(0.1 * side, -0.55, sz - 0.08), 0.06, 0.03, Vector3(-0.2 * side, 0, 0.1))
			_mesh(tail, m, _hair_mat)


func _hat_beret(hc: Node3D) -> void:
	var beret := _pivot(hc, Vector3(0.02, 0.155, -0.03), Vector3(-0.2, 0, -0.22))
	_mesh(beret, _cyl(0.18, 0.185, 0.04, 28), _toon(look.tunic))
	_mesh(beret, _torus(0.176, 0.193), _toon(look.trim), Vector3(0, -0.02, 0), Vector3.ZERO, Vector3(1, 0.5, 1))
	_mesh(beret, _sphere(0.225, 28), _toon(look.band), Vector3(0, 0.04, -0.015), Vector3.ZERO, Vector3(1, 0.33, 1))
	_mesh(beret, _box(Vector3(0.07, 0.016, 0.01)), _toon(look.trim), Vector3(0, 0.012, 0.19))
	_bow(beret, Vector3(0.165, 0.0, 0.08), 1.1, Vector3(0, 1.1, 0))
	_mesh(beret, _sphere(0.038, 14), _toon(PEARL), Vector3(0.19, -0.005, 0.085), Vector3(0, 1.1, 0), Vector3(1, 0.85, 0.4))
	for i in 2:
		_mesh(beret, _sphere(0.012, 8), _toon(PEARL, false), Vector3(0.195, -0.05 - i * 0.032, 0.1))
	_mesh(beret, _sphere(0.014, 10), _gem(), Vector3(0.195, -0.12, 0.1), Vector3.ZERO, Vector3(0.8, 1.4, 0.8))


func _hat_witch(hc: Node3D) -> void:
	var hat := _pivot(hc, Vector3(0.0, 0.17, -0.03), Vector3(-0.12, 0, 0.08))
	_mesh(hat, _cyl(0.34, 0.34, 0.018, 36), _toon(look.tunic))
	_mesh(hat, _cyl(0.07, 0.18, 0.26, 24), _toon(look.tunic), Vector3(0, 0.13, 0))
	_mesh(hat, _cyl(0.182, 0.186, 0.05, 24), _toon(look.trim), Vector3(0, 0.03, 0))
	# Floppy bent tip.
	var tip := _pivot(hat, Vector3(0, 0.25, 0), Vector3(-0.9, 0, 0.2))
	_mesh(tip, _cyl(0.0, 0.072, 0.2, 16), _toon(look.tunic), Vector3(0, 0.09, 0))
	_mesh(hat, _sphere(0.024, 12), _gem(), Vector3(0, 0.03, 0.185), Vector3.ZERO, Vector3(1, 1, 0.6))


func _hat_goggles(hc: Node3D) -> void:
	var g := _pivot(hc, Vector3(0, 0.12, 0.0), Vector3(-0.35, 0, 0))
	_mesh(g, _torus(0.2, 0.216), _toon(look.pants), Vector3.ZERO, Vector3.ZERO, Vector3(1, 1.6, 1))
	for side: float in [1.0, -1.0]:
		var lens := _pivot(g, Vector3(0.065 * side, 0.0, 0.195), Vector3(PI / 2.0, 0, 0))
		_mesh(lens, _cyl(0.05, 0.05, 0.035, 18), _toon(look.trim))
		_mesh(lens, _cyl(0.04, 0.04, 0.04, 18), _glow_mat, Vector3(0, 0.002, 0))
	# Lightning-bolt hair clip.
	_mesh(hc, _box(Vector3(0.012, 0.06, 0.01)), _toon(look.trim), Vector3(-0.12, 0.03, 0.16), Vector3(0, -0.5, 0.5))
	_mesh(hc, _box(Vector3(0.012, 0.05, 0.01)), _toon(look.trim), Vector3(-0.135, 0.0, 0.155), Vector3(0, -0.5, -0.4))


func _hat_hood(hc: Node3D) -> void:
	var hood := Mat.toon(look.tunic, true, 0.35)
	_mesh(hc, _sphere(0.228, 32), hood, Vector3(0, 0.045, -0.065))
	_mesh(hc, _torus(0.19, 0.21), _toon(look.band), Vector3(0, 0.03, 0.035), Vector3(PI / 2.0 - 0.25, 0, 0), Vector3(1.0, 1.0, 1.15))
	# Mask over the lower face.
	_mesh(hc, Gen.cone_sheet(0.193, 0.12, 0.13, 0.0, TAU, 32, 3), Mat.cloth(look.band, {"bottom": look.tunic}), Vector3(0, -0.055, 0))


# --- weapons ------------------------------------------------------------------

func _build_sword() -> void:
	var sword := _pivot(hand_r, Vector3.ZERO, Vector3(PI / 2.0, 0, 0))
	_mesh(sword, _cyl(0.016, 0.018, 0.17, 10), _toon(BROWN), Vector3(0, 0.0, 0))
	_mesh(sword, _sphere(0.026, 12), _toon(look.trim), Vector3(0, -0.1, 0))
	_mesh(sword, _box(Vector3(0.21, 0.03, 0.04)), _toon(look.trim), Vector3(0, 0.1, 0))
	_mesh(sword, _sphere(0.018, 10), _gem(), Vector3(0, 0.1, 0.022))
	var steel := Mat.toon(Color("eef3ff"), true, 0.8, Color(0, 0, 0), METAL_SHADE)
	_mesh(sword, _box(Vector3(0.056, 0.84, 0.012)), steel, Vector3(0, 0.535, 0))
	_mesh(sword, _cyl(0.0, 0.028, 0.12, 4), steel, Vector3(0, 1.015, 0), Vector3.ZERO, Vector3(1, 1, 0.22))
	var fuller := _mesh(sword, _box(Vector3(0.014, 0.72, 0.016)), _glow_mat, Vector3(0, 0.5, 0))
	fuller.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	blade_base = _pivot(sword, Vector3(0, 0.4, 0))
	blade_tip = _pivot(sword, Vector3(0, 1.05, 0))
	cast_point = blade_tip


func _build_shield() -> void:
	# Disc faces +-Y of the hand; the wrist turns it outward at rest and forward when blocking.
	shield_node = _pivot(hand_l, Vector3(0, -0.02, 0))
	_mesh(shield_node, _cyl(0.29, 0.29, 0.035, 24), _toon(look.shield))
	_mesh(shield_node, _torus(0.275, 0.31), _toon(look.trim), Vector3.ZERO, Vector3.ZERO, Vector3(1, 0.9, 1))
	_mesh(shield_node, _cyl(0.17, 0.17, 0.045, 4), _toon(look.emblem), Vector3(0, -0.002, 0), Vector3(0, PI / 4.0, 0), Vector3(1, 1, 1.35))
	_mesh(shield_node, _sphere(0.07, 16), _metal(), Vector3(0, -0.028, 0), Vector3.ZERO, Vector3(1, 0.55, 1))
	_mesh(shield_node, _sphere(0.02, 10), _gem(), Vector3(0, -0.064, 0))


func _build_staff() -> void:
	var staff := _pivot(hand_r, Vector3.ZERO)
	_mesh(staff, _cyl(0.016, 0.016, 1.55, 12), _toon(look.tunic), Vector3(0, 0.2, 0))
	for y: float in [-0.45, -0.1, 0.3, 0.73]:
		_mesh(staff, _cyl(0.022, 0.022, 0.035, 12), _toon(look.trim), Vector3(0, y, 0))
	_mesh(staff, _cyl(0.034, 0.016, 0.08, 12), _toon(look.trim), Vector3(0, 0.99, 0))
	for side: float in [1.0, -1.0]:
		_mesh(staff, _cyl(0.0, 0.02, 0.2, 8), _toon(look.trim), Vector3(0.085 * side, 1.08, 0), Vector3(0, 0, -0.45 * side))
	var orb := _pivot(staff, Vector3(0, 1.14, 0))
	var g: Color = look.glow
	_mesh(orb, _sphere(0.085, 24), Mat.water(Color(g.r * 0.4, g.g * 0.4, g.b * 0.9, 0.85), 1.7))
	_mesh(orb, _sphere(0.045, 16), Mat.water(Color(g.r, g.g, g.b, 1.0), 2.4))
	_mesh(orb, _torus(0.1, 0.118), _toon(look.trim), Vector3.ZERO, Vector3(PI / 2.0, 0, 0))
	_mesh(orb, _cyl(0.0, 0.015, 0.07, 8), _toon(look.trim), Vector3(0, 0.14, 0))
	var core := _mesh(orb, _sphere(0.03, 10), _glow_mat)
	core.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	_mesh(staff, _cyl(0.02, 0.0, 0.08, 10), _toon(look.trim), Vector3(0, -0.6, 0))
	blade_base = _pivot(staff, Vector3(0, 0.75, 0))
	blade_tip = orb
	cast_point = orb
	# Magic barrier on the free hand, shown only while blocking.
	shield_node = _pivot(hand_l, Vector3(0, -0.05, 0))
	_barrier = _pivot(shield_node, Vector3.ZERO)
	var disc := _mesh(_barrier, _cyl(0.42, 0.42, 0.012, 32), Mat.water(Color(g.r * 0.6, g.g * 0.6, g.b, 0.3), 1.4))
	disc.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	var rim := _mesh(_barrier, _torus(0.4, 0.43), Mat.water(Color(g.r, g.g, g.b, 0.9), 2.0))
	rim.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	_barrier.visible = false


func _dagger(hand: Node3D) -> Node3D:
	var d := _pivot(hand, Vector3.ZERO, Vector3(PI / 2.0, 0, 0))
	_mesh(d, _cyl(0.014, 0.015, 0.12, 10), _toon(look.pants), Vector3(0, 0.0, 0))
	_mesh(d, _box(Vector3(0.09, 0.022, 0.03)), _toon(look.trim), Vector3(0, 0.07, 0))
	var steel := Mat.toon(Color("dcd6f0"), true, 0.8, Color(0, 0, 0), METAL_SHADE)
	_mesh(d, _box(Vector3(0.04, 0.3, 0.01)), steel, Vector3(0, 0.23, 0))
	_mesh(d, _cyl(0.0, 0.02, 0.08, 4), steel, Vector3(0, 0.42, 0), Vector3.ZERO, Vector3(1, 1, 0.25))
	var edge := _mesh(d, _box(Vector3(0.008, 0.28, 0.013)), _glow_mat, Vector3(0, 0.23, 0))
	edge.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	return d


func _build_daggers() -> void:
	var right := _dagger(hand_r)
	_dagger(hand_l)
	blade_base = _pivot(right, Vector3(0, 0.12, 0))
	blade_tip = _pivot(right, Vector3(0, 0.46, 0))
	cast_point = blade_tip
	shield_node = hand_l


# --- posing -------------------------------------------------------------------

## Exponentially blends joints toward `target` and applies overlays (walk, breathing, cloth).
func blend(target: Dictionary, delta: float, speed: float) -> void:
	var k := 1.0 - exp(-speed * delta)
	for j: String in JOINTS:
		var tv: Vector3 = target.get(j, Vector3.ZERO)
		_cur[j] = (_cur[j] as Vector3).lerp(tv, k)
	_hips_y = lerpf(_hips_y, float(target.get("hips_y", 0.0)), k)

	_t += delta
	_walk_phase += delta * 11.0 * walk
	var s := sin(_walk_phase)
	recoil = move_toward(recoil, 0.0, delta * 5.0)
	hips.position.y = HIP_HEIGHT + _hips_y + absf(s) * 0.03 * walk + sin(_t * 2.4) * 0.005
	for j: String in JOINTS:
		(_joints[j] as Node3D).rotation = _cur[j]
	torso.rotation.x += -recoil * 0.3 + sin(_t * 2.4) * 0.012
	leg_l.rotation.x += s * 0.55 * walk
	leg_r.rotation.x -= s * 0.55 * walk
	cape.rotation = Vector3(0.08 + 0.3 * walk + 0.3 * recoil + sin(_t * 2.1) * 0.03, 0.0, sin(_t * 1.7) * 0.03)
	for i in hair_sway.size():
		hair_sway[i].rotation.x = 0.1 * walk + 0.25 * recoil + sin(_t * 2.0 + i) * 0.05
	_glow_mat.emission_energy_multiplier = 1.5 + charge * (5.0 + sin(_t * 30.0) * 1.5)
	_update_blink(delta)


func set_barrier(on: bool) -> void:
	if _barrier:
		_barrier.visible = on


func _update_blink(delta: float) -> void:
	if _blink_t < 0.0:
		_blink_wait -= delta
		if _blink_wait <= 0.0:
			_blink_t = 0.0
		return
	_blink_t += delta / 0.14
	_face_mat.set_shader_parameter("blink", sin(clampf(_blink_t, 0.0, 1.0) * PI))
	if _blink_t >= 1.0:
		_blink_t = -1.0
		_blink_wait = randf_range(1.8, 4.5)
		_face_mat.set_shader_parameter("blink", 0.0)


## Brief color flash over the whole body (hit feedback).
func flash(color := Color.WHITE, duration := 0.12) -> void:
	if _flash_tween:
		_flash_tween.kill()
	for m in _meshes:
		m.material_overlay = _flash_mat
	_flash_mat.albedo_color = Color(color.r, color.g, color.b, 0.75)
	_flash_tween = create_tween()
	_flash_tween.tween_property(_flash_mat, "albedo_color:a", 0.0, duration)
	_flash_tween.tween_callback(func() -> void:
		for m in _meshes:
			m.material_overlay = null
	)


## Topple backward (knocked out).
func fall() -> void:
	var tw := create_tween()
	tw.tween_property(self, "rotation:x", -1.45, 0.55).set_trans(Tween.TRANS_QUAD).set_ease(Tween.EASE_IN)
	tw.tween_property(self, "rotation:x", -1.3, 0.12).set_trans(Tween.TRANS_QUAD).set_ease(Tween.EASE_OUT)
	tw.tween_property(self, "rotation:x", -1.45, 0.12).set_trans(Tween.TRANS_QUAD).set_ease(Tween.EASE_IN)
