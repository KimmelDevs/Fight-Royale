extends "res://scripts/model_builder.gd"
## Procedural cel-shaded water mage built from primitives plus generated cloth and hair.
## The model faces +Z. Her right hand (-X side) holds the staff.
## Animation is procedural: call animate() every physics frame.

const Mat := preload("res://scripts/toon_mat.gd")
const Gen := preload("res://scripts/mesh_gen.gd")

const SKIN := Color("ffe9df")
const HAIR := Color("8cc3f0")
const HAIR_LIGHT := Color("c9e6ff")
const NAVY := Color("23307a")
const WHITE := Color("f6f7ff")
const PALE_BLUE := Color("dcebff")
const GOLD := Color("e6c26e")
const CYAN := Color("a3e6f0")
const CAPE := Color("4f97dc")
const BROWN := Color("6e4632")
const PEARL := Color("fff8ee")
const GEM := Color("5fd0ff")

const HAIR_SHADE := Color(0.68, 0.74, 0.95)
const SKIN_SHADE := Color(1.0, 0.82, 0.82)
const HEAD_R := 0.19
const HEAD_SCALE := 0.92
const HIP_HEIGHT := 0.84
## Hair cap center in head space; strands bulge away from it.
const CAP_C := Vector3(0, 0.035, -0.035)

var hips: Node3D
var torso: Node3D
var head: Node3D
var arm_l: Node3D
var arm_r: Node3D
var hand_r: Node3D
var leg_l: Node3D
var leg_r: Node3D
var cape: Node3D
var skirt: Node3D
var ahoge: Node3D
var staff: Node3D
var staff_orb: Node3D
var orb_swirl: Node3D
var hair_sway: Array[Node3D] = []

## 0..1 blend toward "staff pointed forward" pose.
var cast_weight := 0.0
## 0..1 blend toward "staff raised overhead" pose.
var burst_weight := 0.0

var _face_mat: ShaderMaterial
var _hair_mat: ShaderMaterial
var _t := 0.0
var _run_phase := 0.0
var _air := 0.0
var _blink_wait := 2.0
var _blink_t := -1.0
var _squash_tween: Tween
var _orb_tween: Tween


func _ready() -> void:
	_hair_mat = Mat.toon(HAIR, true, 0.3, Color(0, 0, 0), HAIR_SHADE, 0.0045)
	hips = _pivot(self, Vector3(0, HIP_HEIGHT, 0))
	_build_legs()
	_build_skirt()
	_build_torso()
	_build_cape()
	_build_arms()
	_build_head()
	_build_staff()


# --- construction helpers ---------------------------------------------------

func _gem_mat() -> ShaderMaterial:
	return Mat.toon(GEM, false, 0.6, Color(0.15, 0.45, 0.6))


func _bow(parent: Node3D, pos: Vector3, s := 1.0, rot := Vector3.ZERO) -> void:
	var b := _pivot(parent, pos, rot)
	b.scale = Vector3.ONE * s
	for side: float in [1.0, -1.0]:
		_mesh(b, _sphere(0.04, 12), Mat.toon(NAVY), Vector3(0.04 * side, 0, 0), Vector3(0, 0, 0.5 * side), Vector3(1.2, 0.75, 0.45))
		# Ribbon tails.
		_mesh(b, _box(Vector3(0.018, 0.06, 0.006)), Mat.toon(NAVY), Vector3(0.015 * side, -0.035, 0.0), Vector3(0, 0, 0.35 * side))
	_mesh(b, _sphere(0.018, 12), Mat.toon(GOLD), Vector3(0, 0, 0.012))


## Hair lock in head space. Wrapped in a sway pivot at its root when `sway` is true.
func _strand(parent: Node3D, p0: Vector3, p1: Vector3, p2: Vector3, width: float, thick: float, sway := false) -> void:
	var mesh := Gen.strand(p0, p1, p2, width, thick, CAP_C)
	if sway:
		var pv := _pivot(parent, p0)
		_mesh(pv, mesh, _hair_mat, -p0)
		hair_sway.append(pv)
	else:
		_mesh(parent, mesh, _hair_mat)


# --- body parts ---------------------------------------------------------------

func _build_legs() -> void:
	for side: float in [1.0, -1.0]:
		var leg := _pivot(hips, Vector3(0.075 * side, 0.0, 0.0))
		# Thigh-high white stockings with gold band, garter strap and a little bow.
		_mesh(leg, _cap(0.05, 0.76), Mat.toon(WHITE), Vector3(0, -0.37, 0))
		_mesh(leg, _cyl(0.055, 0.055, 0.025), Mat.toon(GOLD), Vector3(0, -0.13, 0))
		_mesh(leg, _box(Vector3(0.007, 0.12, 0.006)), Mat.toon(GOLD, false), Vector3(0, -0.07, 0.05))
		_bow(leg, Vector3(0, -0.15, 0.05), 0.55)
		# Boots: navy shaft, white folded cuff, white toe and navy sole, shell + gem.
		_mesh(leg, _cyl(0.058, 0.06, 0.24, 16), Mat.toon(NAVY), Vector3(0, -0.7, 0.005))
		_mesh(leg, _cyl(0.078, 0.07, 0.07, 16), Mat.toon(WHITE), Vector3(0, -0.585, 0))
		_mesh(leg, _box(Vector3(0.11, 0.06, 0.09)), Mat.toon(WHITE), Vector3(0, -0.785, 0.07))
		_mesh(leg, _box(Vector3(0.12, 0.035, 0.2)), Mat.toon(NAVY), Vector3(0, -0.822, 0.03))
		_mesh(leg, _sphere(0.028, 12), Mat.toon(PEARL), Vector3(0, -0.68, 0.062), Vector3.ZERO, Vector3(1.2, 1.0, 0.5))
		_mesh(leg, _sphere(0.014, 10), _gem_mat(), Vector3(0, -0.585, 0.08))
		if side > 0.0:
			leg_l = leg
		else:
			leg_r = leg


func _build_skirt() -> void:
	skirt = _pivot(hips, Vector3(0, 0.04, 0))
	# Aqua frill peeking under the hem.
	_mesh(skirt, Gen.cone_sheet(0.2, 0.33, 0.1, 0.0, TAU, 56, 3, 0.02, 22), Mat.cloth(CYAN, {"bottom": Color("c8f3f8")}), Vector3(0, -0.15, 0))
	# White skirt with a navy surf band and gold hem.
	_mesh(skirt, Gen.cone_sheet(0.105, 0.31, 0.26, 0.0, TAU, 48, 6, 0.012, 14), Mat.cloth(WHITE, {
		"bottom": PALE_BLUE, "pattern": NAVY, "pattern_strength": 1.0, "pattern_v": 0.6,
		"pattern_freq": 5.0, "pattern_fill": 1.0, "trim_bottom": 0.07,
	}))


func _build_torso() -> void:
	torso = _pivot(hips, Vector3(0, 0.05, 0))
	_mesh(torso, _cyl(0.09, 0.105, 0.3), Mat.toon(WHITE), Vector3(0, 0.14, 0))
	# Navy corset with gold edges and a lace diamond.
	_mesh(torso, _cyl(0.106, 0.109, 0.11), Mat.toon(NAVY), Vector3(0, 0.05, 0))
	for y: float in [0.105, -0.005]:
		_mesh(torso, _torus(0.1, 0.112), Mat.toon(GOLD, false), Vector3(0, y, 0), Vector3.ZERO, Vector3(1, 0.4, 1))
	_mesh(torso, _box(Vector3(0.03, 0.03, 0.008)), Mat.toon(GOLD), Vector3(0, 0.06, 0.108), Vector3(0, 0, PI / 4.0))
	# Belt, buckle, pouch, potion and a pearl chain.
	_mesh(torso, _torus(0.105, 0.127), Mat.toon(BROWN), Vector3(0, -0.015, 0), Vector3(0.1, 0, 0), Vector3(1, 0.7, 1))
	_mesh(torso, _box(Vector3(0.036, 0.03, 0.012)), Mat.toon(GOLD), Vector3(0, -0.015, 0.125))
	_mesh(torso, _box(Vector3(0.08, 0.07, 0.042)), Mat.toon(BROWN), Vector3(0.11, -0.06, 0.085), Vector3(0, 0.75, 0))
	_mesh(torso, _sphere(0.02, 12), Mat.toon(PEARL), Vector3(0.134, -0.05, 0.108), Vector3.ZERO, Vector3(1, 0.9, 0.5))
	_mesh(torso, _sphere(0.034, 16), Mat.water(Color(0.15, 0.55, 1.0, 0.8), 1.6), Vector3(-0.12, -0.075, 0.075))
	for i in 7:
		var x := -0.08 + i * 0.0267
		var y := -0.04 - 0.035 * (1.0 - pow(x / 0.08, 2.0))
		_mesh(torso, _sphere(0.009, 8), Mat.toon(PEARL, false), Vector3(x, y, sqrt(0.14 * 0.14 - x * x)))
	# Off-shoulder navy capelet with gold hem, frilled collar, shoulder bows.
	_mesh(torso, Gen.cone_sheet(0.075, 0.235, 0.15, 0.0, TAU, 40, 4, 0.006, 12), Mat.cloth(NAVY, {"trim_bottom": 0.14}), Vector3(0, 0.31, 0))
	_mesh(torso, Gen.cone_sheet(0.04, 0.066, 0.05, 0.0, TAU, 24, 2, 0.01, 16), Mat.cloth(WHITE), Vector3(0, 0.36, 0))
	for side: float in [1.0, -1.0]:
		_bow(torso, Vector3(0.15 * side, 0.21, 0.09), 1.2, Vector3(0, 0.5 * side, 0))
	# Chest bow with gem, and a white jabot cascading below it.
	for i in 3:
		_mesh(torso, _sphere(0.03, 12), Mat.toon(WHITE), Vector3(0, 0.235 - i * 0.03, 0.105 - i * 0.002), Vector3.ZERO, Vector3(1.1 - i * 0.15, 0.6, 0.45))
	_bow(torso, Vector3(0, 0.272, 0.12), 1.0)
	_mesh(torso, _sphere(0.02, 12), _gem_mat(), Vector3(0, 0.258, 0.142), Vector3.ZERO, Vector3(0.8, 1.2, 0.6))
	_mesh(torso, _cyl(0.032, 0.034, 0.08), Mat.toon(SKIN, true, 0.2, Color(0, 0, 0), SKIN_SHADE), Vector3(0, 0.36, 0))


func _build_cape() -> void:
	# Long cape around the back, open at the sides so the arms move freely.
	# The two front edges hang longer, like the pointed tails in the art.
	const A0 := 1.75
	var tails := func(a: float) -> float: return 0.22 * pow(absf(a - PI) / (PI - A0), 2.0)
	cape = _pivot(torso, Vector3(0, 0.29, -0.02))
	_mesh(cape, Gen.cone_sheet(0.13, 0.4, 0.6, A0, TAU - A0, 40, 10, 0.0, 0.0, tails), Mat.cloth(CAPE, {
		"bottom": CYAN, "pattern": WHITE, "pattern_strength": 1.0, "pattern_v": 0.7,
		"pattern_freq": 4.0, "trim_bottom": 0.03, "trim_sides": 0.012, "wind": 0.035,
	}))
	for a: float in [A0, TAU - A0]:
		var tip := Vector3(sin(a) * 0.4, -0.83, cos(a) * 0.4)
		_mesh(cape, _sphere(0.022, 12), Mat.toon(PEARL), tip)
		_mesh(cape, _sphere(0.018, 10), _gem_mat(), tip + Vector3(0, -0.05, 0), Vector3.ZERO, Vector3(0.8, 1.4, 0.8))


func _build_arms() -> void:
	for side: float in [1.0, -1.0]:
		var a := _pivot(torso, Vector3(0.125 * side, 0.25, 0))
		var skin := Mat.toon(SKIN, true, 0.2, Color(0, 0, 0), SKIN_SHADE)
		_mesh(a, _sphere(0.033, 14), skin)
		_mesh(a, _cap(0.027, 0.36), skin, Vector3(0, -0.18, 0))
		# Wide frilled bell sleeve, white fading to pale blue, gold hem.
		_mesh(a, Gen.cone_sheet(0.036, 0.115, 0.27, 0.0, TAU, 28, 4, 0.012, 9), Mat.cloth(WHITE, {
			"bottom": PALE_BLUE, "trim_bottom": 0.07,
		}), Vector3(0, -0.07, 0))
		var hand := _pivot(a, Vector3(0, -0.38, 0))
		_mesh(hand, _sphere(0.032, 14), skin, Vector3.ZERO, Vector3.ZERO, Vector3(0.9, 1.15, 0.75))
		if side > 0.0:
			arm_l = a
		else:
			arm_r = a
			hand_r = hand


func _build_head() -> void:
	head = _pivot(torso, Vector3(0, 0.37, 0))
	head.scale = Vector3.ONE * HEAD_SCALE
	var hc := _pivot(head, Vector3(0, HEAD_R, 0))
	_face_mat = Mat.face(SKIN)
	_mesh(hc, _sphere(HEAD_R, 40), _face_mat, Vector3.ZERO, Vector3.ZERO, Vector3(1.0, 0.98, 0.97))

	# Cap sits back and up so the face stays clear; the back bob fills out the silhouette.
	_mesh(hc, _sphere(0.205, 32), _hair_mat, CAP_C)
	_mesh(hc, _sphere(0.19, 28), _hair_mat, Vector3(0, -0.07, -0.06), Vector3.ZERO, Vector3(1.08, 0.85, 0.95))
	# Glossy "angel ring" highlight band.
	_mesh(hc, _torus(0.188, 0.207), Mat.toon(HAIR_LIGHT, false, 0.0), Vector3(0, 0.085, -0.035), Vector3(-0.15, 0, 0), Vector3(1, 0.35, 1))

	# Bangs: curved locks of uneven length sweeping over the forehead.
	var tips: Array[float] = [0.06, 0.025, 0.045, 0.005, 0.03, -0.005, 0.04, 0.02, 0.06]
	for k in tips.size():
		var x := lerpf(-0.155, 0.155, k / 8.0)
		var y := tips[k]
		var root := CAP_C + Vector3(x * 0.6, 0.75, 0.62).normalized() * 0.2
		var tip := Vector3(x, y, sqrt(maxf(0.19 * 0.19 - x * x - y * y, 0.0))).normalized() * 0.2
		var mid := CAP_C + ((root + tip) * 0.5 - CAP_C).normalized() * 0.236
		_strand(hc, root, mid, tip, 0.034, 0.014)

	for side: float in [1.0, -1.0]:
		# Face-framing locks that reach the jaw.
		_strand(hc, Vector3(0.13 * side, 0.14, 0.12), Vector3(0.195 * side, 0.06, 0.15), Vector3(0.185 * side, -0.05, 0.13), 0.03, 0.013)
		_strand(hc, Vector3(0.15 * side, 0.1, 0.11), Vector3(0.215 * side, -0.04, 0.11), Vector3(0.18 * side, -0.22, 0.085), 0.04, 0.016, true)
		_strand(hc, Vector3(0.18 * side, 0.08, 0.02), Vector3(0.235 * side, -0.06, 0.0), Vector3(0.215 * side, -0.19, -0.02), 0.05, 0.02, true)
	# Messy bob around the back, ends flicking outward.
	for i in 11:
		var a := lerpf(1.35, TAU - 1.35, i / 10.0)
		var d := Vector3(sin(a), 0.0, cos(a))
		var flick := 0.02 * sin(i * 2.3)
		_strand(hc, CAP_C + d * 0.16 + Vector3.UP * 0.1, CAP_C + d * 0.235 + Vector3.UP * -0.06,
			CAP_C + d * (0.27 + flick) + Vector3.UP * (-0.19 + flick), 0.065, 0.022, true)

	# Ahoge poking up over the beret.
	ahoge = _pivot(hc, Vector3(-0.05, 0.25, -0.08))
	var ah := Gen.strand(Vector3.ZERO, Vector3(0.01, 0.11, 0.03), Vector3(0.05, 0.09, 0.12), 0.02, 0.01, Vector3(0, -0.2, 0.0))
	_mesh(ahoge, ah, _hair_mat)
	# Gold hair clip.
	_mesh(hc, _box(Vector3(0.055, 0.012, 0.012)), Mat.toon(GOLD), Vector3(-0.115, 0.07, 0.17), Vector3(0, -0.5, 0.7))

	# Beret: navy band, gold trim, puffy white crown, bow + shell + pearl dangles.
	var beret := _pivot(hc, Vector3(0.02, 0.155, -0.03), Vector3(-0.2, 0, -0.22))
	_mesh(beret, _cyl(0.18, 0.185, 0.04, 28), Mat.toon(NAVY))
	_mesh(beret, _torus(0.176, 0.193), Mat.toon(GOLD), Vector3(0, -0.02, 0), Vector3.ZERO, Vector3(1, 0.5, 1))
	_mesh(beret, _sphere(0.225, 28), Mat.toon(WHITE), Vector3(0, 0.04, -0.015), Vector3.ZERO, Vector3(1, 0.33, 1))
	_mesh(beret, _box(Vector3(0.07, 0.016, 0.01)), Mat.toon(GOLD), Vector3(0, 0.012, 0.19))
	_bow(beret, Vector3(0.165, 0.0, 0.08), 1.1, Vector3(0, 1.1, 0))
	_mesh(beret, _sphere(0.038, 14), Mat.toon(PEARL), Vector3(0.19, -0.005, 0.085), Vector3(0, 1.1, 0), Vector3(1, 0.85, 0.4))
	_mesh(beret, _box(Vector3(0.025, 0.1, 0.006)), Mat.toon(NAVY), Vector3(0.19, -0.07, 0.03), Vector3(0, 1.1, 0.2))
	for i in 2:
		_mesh(beret, _sphere(0.012, 8), Mat.toon(PEARL, false), Vector3(0.195, -0.05 - i * 0.032, 0.1))
	_mesh(beret, _sphere(0.014, 10), _gem_mat(), Vector3(0.195, -0.12, 0.1), Vector3.ZERO, Vector3(0.8, 1.4, 0.8))


func _build_staff() -> void:
	staff = _pivot(hand_r, Vector3.ZERO)
	_mesh(staff, _cyl(0.016, 0.016, 1.55, 12), Mat.toon(NAVY), Vector3(0, 0.2, 0))
	for y: float in [-0.45, -0.1, 0.3, 0.73]:
		_mesh(staff, _cyl(0.022, 0.022, 0.035, 12), Mat.toon(GOLD), Vector3(0, y, 0))
	_mesh(staff, _cyl(0.034, 0.016, 0.08, 12), Mat.toon(GOLD), Vector3(0, 0.99, 0))
	_mesh(staff, _sphere(0.045, 14), Mat.toon(PEARL), Vector3(0, 1.035, 0.0), Vector3.ZERO, Vector3(1.1, 0.8, 0.55))
	# Crescent prongs curving up to the ring.
	for side: float in [1.0, -1.0]:
		_mesh(staff, _cyl(0.0, 0.02, 0.2, 8), Mat.toon(GOLD), Vector3(0.085 * side, 1.08, 0), Vector3(0, 0, -0.45 * side))

	staff_orb = _pivot(staff, Vector3(0, 1.14, 0))
	_mesh(staff_orb, _sphere(0.085, 24), Mat.water(Color(0.1, 0.42, 1.0, 0.85), 1.7))
	_mesh(staff_orb, _sphere(0.045, 16), Mat.water(Color(0.6, 0.95, 1.0, 1.0), 2.4))
	_mesh(staff_orb, _torus(0.1, 0.118), Mat.toon(GOLD), Vector3.ZERO, Vector3(PI / 2.0, 0, 0))
	_mesh(staff_orb, _cyl(0.0, 0.015, 0.07, 8), Mat.toon(GOLD), Vector3(0, 0.14, 0))
	orb_swirl = _pivot(staff_orb, Vector3.ZERO, Vector3(0.6, 0, 0.4))
	_mesh(orb_swirl, _torus(0.13, 0.142), Mat.water(Color(0.3, 0.7, 1.0, 0.6), 1.5))

	# Floating droplets drifting off the orb.
	var drops := CPUParticles3D.new()
	var dm := _sphere(0.012, 8)
	dm.material = Mat.water(Color(0.3, 0.7, 1.0, 0.8), 1.8)
	drops.mesh = dm
	drops.amount = 10
	drops.lifetime = 1.2
	drops.local_coords = false
	drops.emission_shape = CPUParticles3D.EMISSION_SHAPE_SPHERE
	drops.emission_sphere_radius = 0.16
	drops.gravity = Vector3(0, -0.6, 0)
	drops.initial_velocity_min = 0.05
	drops.initial_velocity_max = 0.2
	drops.spread = 180.0
	staff_orb.add_child(drops)

	_mesh(staff, _cyl(0.02, 0.0, 0.08, 10), Mat.toon(GOLD), Vector3(0, -0.6, 0))
	_mesh(staff, _sphere(0.018, 10), _gem_mat(), Vector3(0, -0.66, 0), Vector3.ZERO, Vector3(0.8, 1.4, 0.8))


# --- animation ---------------------------------------------------------------

func animate(delta: float, speed01: float, on_floor: bool, vel_y: float) -> void:
	_t += delta
	_air = move_toward(_air, 0.0 if on_floor else 1.0, delta * 6.0)
	var run := speed01 * (1.0 - _air)
	_run_phase += delta * 12.5 * speed01
	var s := sin(_run_phase)
	var breathe := sin(_t * 2.2)

	hips.position.y = HIP_HEIGHT + absf(s) * 0.045 * run + breathe * 0.004 * (1.0 - run)

	# Legs swing opposite each other; tuck up in the air.
	leg_l.rotation.x = s * 0.75 * run - 0.55 * _air
	leg_r.rotation.x = -s * 0.75 * run + 0.25 * _air
	skirt.rotation.x = 0.07 * run + 0.05 * _air
	var flare := 1.0 + 0.05 * absf(s) * run + 0.06 * _air
	skirt.scale = Vector3(flare, 1.0, flare)

	torso.rotation.x = 0.14 * run
	torso.rotation.y = s * 0.1 * run
	head.rotation.x = -0.1 * run + sin(_t * 1.3) * 0.02
	head.rotation.z = sin(_t * 0.9) * 0.035 * (1.0 - run)

	# Free arm: open, welcoming pose at rest; swings when running.
	arm_l.rotation = Vector3(-s * 0.7 * run - 0.2 * _air, 0.0, lerpf(0.5, 0.18, run) + 0.5 * _air)

	# Staff arm blends idle -> cast (forward) -> burst (overhead).
	var r_idle := Vector3(s * 0.25 * run - 0.1, 0.0, -0.3 - 0.2 * _air)
	var r := r_idle.lerp(Vector3(-1.35, 0.0, -0.15), cast_weight).lerp(Vector3(-2.9, 0.0, -0.1), burst_weight)
	arm_r.rotation = r
	# Counter-rotate so the staff stays upright, tips forward when casting, straight up for burst.
	var staff_euler := Vector3(0.1 + 0.25 * run, 0.0, 0.12).lerp(Vector3(1.1, 0.0, 0.0), cast_weight).lerp(Vector3.ZERO, burst_weight)
	staff.basis = arm_r.basis.inverse() * Basis.from_euler(staff_euler)
	orb_swirl.rotate_object_local(Vector3.UP, delta * 4.0)

	# Cloth and hair trail behind with speed and float up while falling.
	var fall_float := clampf(-vel_y * 0.08, 0.0, 0.9)
	cape.rotation = Vector3(0.06 + 0.28 * run + 0.5 * fall_float + 0.2 * _air + sin(_t * 2.1) * 0.03, 0.0, sin(_t * 1.7) * 0.03)
	for i in hair_sway.size():
		hair_sway[i].rotation.x = 0.3 * run + 0.4 * fall_float + sin(_t * 2.0 + i) * 0.04
	ahoge.rotation = Vector3(sin(_t * 7.0) * 0.08 + 0.25 * run * absf(s), 0.0, sin(_t * 4.3) * 0.12)

	_update_blink(delta)


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


# --- juice ----------------------------------------------------------------------

## Instant squash/stretch that springs back with overshoot.
func squash(s: Vector3) -> void:
	if _squash_tween:
		_squash_tween.kill()
	scale = s
	_squash_tween = create_tween()
	_squash_tween.tween_property(self, "scale", Vector3.ONE, 0.28).set_trans(Tween.TRANS_BACK).set_ease(Tween.EASE_OUT)


func pop_orb(amount := 1.6) -> void:
	if _orb_tween:
		_orb_tween.kill()
	staff_orb.scale = Vector3.ONE * amount
	_orb_tween = create_tween()
	_orb_tween.tween_property(staff_orb, "scale", Vector3.ONE, 0.22).set_trans(Tween.TRANS_BACK).set_ease(Tween.EASE_OUT)
