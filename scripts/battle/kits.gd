extends RefCounted
## Per-class combat data: stats, attack/skill tables and pose tables.
## Attack dictionaries all share the keys in DEFAULT; `type` picks how the battle resolves them:
##   melee      - timed hit check in front of the attacker
##   projectile - flying bolts (count/spread/speed/size/style)
##   strike     - area hit at the target or self after `delay`, `repeat` times
##   buff       - self effect (ward: hits are absorbed for a while)
##   blink      - instant reposition (mode: back / behind)

const STATS := {
	"knight": {"hp": 1000.0, "guard": 100.0, "move": 3.2, "walk": 2.6, "parry": 0.16, "jump": 7.0},
	"mage": {"hp": 850.0, "guard": 80.0, "move": 3.4, "walk": 2.6, "parry": 0.16, "jump": 7.0},
	"assassin": {"hp": 800.0, "guard": 60.0, "move": 4.2, "walk": 3.4, "parry": 0.22, "jump": 8.2},
}

const DEFAULT := {
	"type": "melee", "wind": 0.14, "active": 0.08, "recover": 0.3, "dmg": 60.0, "guard": 20.0,
	"reach": 1.75, "lunge": 0.0, "knock": 2.0, "stun": 0.32, "heavy": false,
	"pose_w": "l1_w", "pose_s": "l1_s", "next": "",
	"speed": 15.0, "size": 1.0, "count": 1, "spread": 0.0, "style": "bolt",
	"at": "target", "delay": 0.4, "radius": 1.5, "repeat": 1, "interval": 0.3,
	"stagger": false, "self_jump": 0.0, "mode": "", "duration": 0.0,
	"cd": 0.0, "name": "", "desc": "",
}


static func _a(d: Dictionary) -> Dictionary:
	return DEFAULT.merged(d, true)


## Normal attacks keyed l1.. plus "heavy" (charged), and skills keyed z/x/c.
static func attacks(kit: String, element: String) -> Dictionary:
	var t := {}
	match kit:
		"mage":
			t = _mage(element)
		"assassin":
			t = _assassin()
		_:
			t = _knight()
	for k: String in t:
		t[k]["element"] = element
		t[k]["id"] = k
	return t


static func _knight() -> Dictionary:
	return {
		"l1": _a({"wind": 0.14, "recover": 0.24, "dmg": 62.0, "guard": 18.0, "lunge": 2.4, "next": "l2"}),
		"l2": _a({"wind": 0.12, "recover": 0.26, "dmg": 70.0, "lunge": 2.2, "pose_w": "l2_w", "pose_s": "l2_s", "next": "l3"}),
		"l3": _a({"wind": 0.2, "active": 0.09, "recover": 0.42, "dmg": 112.0, "guard": 30.0, "reach": 1.85,
			"lunge": 3.0, "knock": 4.5, "stun": 0.5, "pose_w": "l3_w", "pose_s": "l3_s"}),
		"heavy": _a({"wind": 0.12, "active": 0.1, "recover": 0.5, "dmg": 190.0, "guard": 55.0, "reach": 2.0,
			"lunge": 5.0, "knock": 6.0, "stun": 0.7, "heavy": true, "pose_w": "charge", "pose_s": "heavy_s"}),
		"z": _a({"name": "Shield Bash", "desc": "Ram the shield forward. Staggers and crushes guard.", "cd": 5.0,
			"wind": 0.12, "recover": 0.35, "dmg": 55.0, "guard": 60.0, "reach": 1.5, "lunge": 4.0,
			"knock": 3.0, "stagger": true, "stun": 0.8, "pose_w": "block", "pose_s": "bash"}),
		"x": _a({"name": "Rising Slash", "desc": "Leap upward with a soaring cut.", "cd": 6.0,
			"wind": 0.1, "active": 0.1, "recover": 0.4, "dmg": 115.0, "guard": 30.0, "reach": 1.9, "lunge": 2.0,
			"knock": 4.0, "stun": 0.55, "self_jump": 6.5, "pose_w": "charge", "pose_s": "rise"}),
		"c": _a({"name": "Blade Wave", "desc": "Fling a crescent of light that flies across the arena.", "cd": 9.0,
			"type": "projectile", "wind": 0.22, "active": 0.05, "recover": 0.45, "dmg": 140.0, "guard": 40.0,
			"knock": 5.0, "stun": 0.6, "heavy": true, "speed": 17.0, "size": 1.8, "style": "wave",
			"pose_w": "l3_w", "pose_s": "l3_s"}),
	}


static func _mage(element: String) -> Dictionary:
	var speed := 15.0
	var mul := 1.0
	if element == "electric":
		speed = 24.0
		mul = 0.9
	elif element == "water":
		speed = 13.0
	var t := {
		"l1": _a({"type": "projectile", "wind": 0.16, "active": 0.05, "recover": 0.26, "dmg": 55.0 * mul, "guard": 15.0,
			"knock": 1.6, "stun": 0.28, "speed": speed, "pose_w": "m1_w", "pose_s": "m1_s", "next": "l2"}),
		"l2": _a({"type": "projectile", "wind": 0.16, "active": 0.05, "recover": 0.28, "dmg": 60.0 * mul, "guard": 15.0,
			"knock": 1.8, "stun": 0.3, "speed": speed, "pose_w": "m2_w", "pose_s": "m2_s", "next": "l3"}),
		"l3": _a({"type": "projectile", "wind": 0.24, "active": 0.05, "recover": 0.42, "dmg": 42.0 * mul, "guard": 14.0,
			"knock": 3.0, "stun": 0.4, "speed": speed, "count": 3, "spread": 0.22, "pose_w": "m3_w", "pose_s": "m3_s"}),
	}
	match element:
		"fire":
			t["heavy"] = _a({"type": "strike", "wind": 0.15, "active": 0.05, "recover": 0.55, "dmg": 210.0, "guard": 60.0,
				"knock": 6.0, "stun": 0.7, "heavy": true, "delay": 0.5, "radius": 1.6, "style": "explosion",
				"pose_w": "mh_w", "pose_s": "mh_s"})
			t["z"] = _a({"name": "Flame Burst", "desc": "Erupt in flames, blasting anyone close away.", "cd": 6.0,
				"type": "strike", "at": "self", "wind": 0.12, "recover": 0.4, "dmg": 120.0, "guard": 40.0, "knock": 7.0,
				"stun": 0.5, "delay": 0.05, "radius": 2.3, "style": "explosion", "pose_w": "mh_w", "pose_s": "m3_s"})
			t["x"] = _a({"name": "Fireball Volley", "desc": "Hurl a fan of five fireballs.", "cd": 7.0,
				"type": "projectile", "wind": 0.2, "recover": 0.4, "dmg": 40.0, "guard": 12.0, "knock": 2.0,
				"speed": 16.0, "count": 5, "spread": 0.45, "pose_w": "m3_w", "pose_s": "m3_s"})
			t["c"] = _a({"name": "Meteor", "desc": "Call a meteor down on the enemy's position.", "cd": 12.0,
				"type": "strike", "wind": 0.3, "recover": 0.6, "dmg": 290.0, "guard": 80.0, "knock": 8.0, "stun": 0.9,
				"heavy": true, "delay": 0.9, "radius": 2.1, "style": "meteor", "pose_w": "mh_w", "pose_s": "mh_s"})
		"electric":
			t["heavy"] = _a({"type": "strike", "wind": 0.15, "active": 0.05, "recover": 0.5, "dmg": 185.0, "guard": 55.0,
				"knock": 4.0, "stun": 0.8, "heavy": true, "delay": 0.35, "radius": 1.3, "style": "lightning",
				"pose_w": "mh_w", "pose_s": "mh_s"})
			t["z"] = _a({"name": "Blink", "desc": "Flash backward out of danger.", "cd": 4.0,
				"type": "blink", "mode": "back", "wind": 0.04, "recover": 0.15, "pose_w": "m1_w", "pose_s": "m1_s"})
			t["x"] = _a({"name": "Chain Lightning", "desc": "A near-instant bolt that locks the target in place.", "cd": 6.0,
				"type": "projectile", "wind": 0.14, "recover": 0.35, "dmg": 90.0, "guard": 25.0, "knock": 1.0,
				"stun": 0.75, "speed": 42.0, "size": 1.3, "pose_w": "m2_w", "pose_s": "m2_s"})
			t["c"] = _a({"name": "Thunderstorm", "desc": "Three lightning strikes hunt the enemy.", "cd": 12.0,
				"type": "strike", "wind": 0.3, "recover": 0.6, "dmg": 110.0, "guard": 35.0, "knock": 3.0, "stun": 0.6,
				"heavy": true, "delay": 0.45, "radius": 1.25, "repeat": 3, "interval": 0.35, "style": "lightning",
				"pose_w": "mh_w", "pose_s": "mh_s"})
		_:
			t["heavy"] = _a({"type": "projectile", "wind": 0.15, "active": 0.05, "recover": 0.55, "dmg": 190.0, "guard": 60.0,
				"knock": 7.0, "stun": 0.7, "heavy": true, "speed": 9.0, "size": 2.4, "pose_w": "mh_w", "pose_s": "mh_s"})
			t["z"] = _a({"name": "Bubble Ward", "desc": "A bubble that absorbs every hit for 4 seconds.", "cd": 10.0,
				"type": "buff", "mode": "ward", "duration": 4.0, "wind": 0.1, "recover": 0.25, "pose_w": "mh_w", "pose_s": "m3_s"})
			t["x"] = _a({"name": "Tidal Ring", "desc": "A ring of geysers bursts up around you.", "cd": 7.0,
				"type": "strike", "at": "self", "wind": 0.14, "recover": 0.45, "dmg": 105.0, "guard": 35.0, "knock": 7.0,
				"stun": 0.5, "delay": 0.1, "radius": 2.7, "style": "tide", "pose_w": "mh_w", "pose_s": "m3_s"})
			t["c"] = _a({"name": "Ocean Requiem", "desc": "Slam a colossal sphere of water onto the enemy.", "cd": 12.0,
				"type": "strike", "wind": 0.35, "recover": 0.6, "dmg": 270.0, "guard": 80.0, "knock": 8.0, "stun": 0.9,
				"heavy": true, "delay": 0.8, "radius": 2.4, "style": "requiem", "pose_w": "mh_w", "pose_s": "mh_s"})
	return t


static func _assassin() -> Dictionary:
	return {
		"l1": _a({"wind": 0.08, "active": 0.06, "recover": 0.16, "dmg": 36.0, "guard": 10.0, "reach": 1.55, "lunge": 3.0,
			"knock": 1.2, "stun": 0.26, "pose_w": "as1_w", "pose_s": "as1_s", "next": "l2"}),
		"l2": _a({"wind": 0.08, "active": 0.06, "recover": 0.16, "dmg": 36.0, "guard": 10.0, "reach": 1.55, "lunge": 3.0,
			"knock": 1.2, "stun": 0.26, "pose_w": "as2_w", "pose_s": "as2_s", "next": "l3"}),
		"l3": _a({"wind": 0.1, "active": 0.06, "recover": 0.18, "dmg": 44.0, "guard": 12.0, "reach": 1.7, "lunge": 4.0,
			"knock": 1.5, "stun": 0.28, "pose_w": "as3_w", "pose_s": "as3_s", "next": "l4"}),
		"l4": _a({"wind": 0.16, "active": 0.08, "recover": 0.36, "dmg": 75.0, "guard": 22.0, "reach": 1.7, "lunge": 3.0,
			"knock": 4.0, "stun": 0.45, "pose_w": "as4_w", "pose_s": "as4_s"}),
		"heavy": _a({"wind": 0.12, "active": 0.16, "recover": 0.5, "dmg": 170.0, "guard": 45.0, "reach": 2.0, "lunge": 13.0,
			"knock": 5.0, "stun": 0.7, "heavy": true, "pose_w": "ash_w", "pose_s": "ash_s"}),
		"z": _a({"name": "Smoke Step", "desc": "Vanish and reappear behind the enemy.", "cd": 5.0,
			"type": "blink", "mode": "behind", "wind": 0.06, "recover": 0.12, "pose_w": "ash_w", "pose_s": "idle"}),
		"x": _a({"name": "Shuriken Fan", "desc": "Throw three spinning shuriken.", "cd": 6.0,
			"type": "projectile", "wind": 0.12, "recover": 0.3, "dmg": 48.0, "guard": 14.0, "knock": 1.5, "stun": 0.35,
			"speed": 22.0, "count": 3, "spread": 0.3, "style": "shuriken", "pose_w": "as1_w", "pose_s": "as1_s"}),
		"c": _a({"name": "Phantom Rush", "desc": "A blinding dash that cuts through the enemy.", "cd": 10.0,
			"wind": 0.18, "active": 0.18, "recover": 0.55, "dmg": 260.0, "guard": 70.0, "reach": 2.2, "lunge": 16.0,
			"knock": 6.0, "stun": 0.9, "heavy": true, "stagger": true, "pose_w": "ash_w", "pose_s": "ash_s"}),
	}


# --- poses ----------------------------------------------------------------------
# Joint rotations in radians. arm x < 0 raises the arm forward; YXZ order, so y then yaws it.

const COMMON_POSES := {
	"hit": {"torso": Vector3(-0.3, 0.2, 0.1), "head": Vector3(-0.35, 0, 0),
		"arm_r": Vector3(-0.2, 0, -0.7), "hand_r": Vector3(0.4, 0, 0),
		"arm_l": Vector3(-0.2, 0, 0.7), "hand_l": Vector3(0, 0, -1.3),
		"leg_l": Vector3(0.1, 0, 0.06), "leg_r": Vector3(-0.2, 0, -0.06), "hips_y": -0.03},
	"stagger": {"torso": Vector3(-0.45, 0.35, 0.15), "head": Vector3(-0.4, 0, 0.1),
		"arm_r": Vector3(0.1, 0, -0.9), "hand_r": Vector3(1.0, 0, 0),
		"arm_l": Vector3(0.1, 0, 0.9), "hand_l": Vector3(0, 0, -1.5),
		"leg_l": Vector3(0.25, 0, 0.08), "leg_r": Vector3(-0.35, 0, -0.08), "hips_y": -0.1},
	"clash": {"torso": Vector3(-0.25, -0.2, 0), "head": Vector3(-0.15, 0.2, 0),
		"arm_r": Vector3(-1.9, -0.3, -0.3), "hand_r": Vector3(0.3, 0, 0),
		"arm_l": Vector3(-0.4, -0.2, 0.6), "hand_l": Vector3(0, 0, -1.2),
		"leg_l": Vector3(-0.1, 0, 0.06), "leg_r": Vector3(0.4, 0, -0.06), "hips_y": -0.08},
	"win": {"torso": Vector3(0, 0, 0), "head": Vector3(0.1, 0, 0),
		"arm_r": Vector3(-2.9, 0, -0.2), "hand_r": Vector3(0.0, 0, 0),
		"arm_l": Vector3(-0.1, 0, 0.4), "hand_l": Vector3(0, 0, -1.5),
		"leg_l": Vector3(-0.1, 0, 0.04), "leg_r": Vector3(0.1, 0, -0.04), "hips_y": 0.0},
	"jump": {"torso": Vector3(0.15, 0, 0), "head": Vector3(0.1, 0, 0),
		"arm_r": Vector3(-0.9, 0, -0.6), "hand_r": Vector3(0.5, 0, 0),
		"arm_l": Vector3(-0.9, 0, 0.6), "hand_l": Vector3(0, 0, -0.8),
		"leg_l": Vector3(-0.95, 0, 0.05), "leg_r": Vector3(-0.2, 0, -0.05), "hips_y": 0.0},
}

const KNIGHT_POSES := {
	"idle": {"torso": Vector3(0.08, -0.35, 0), "head": Vector3(0, 0.3, 0),
		"arm_r": Vector3(-0.55, -0.25, -0.25), "hand_r": Vector3(-0.5, 0, 0),
		"arm_l": Vector3(-0.75, -0.35, 0.2), "hand_l": Vector3(0, 0, -1.1),
		"leg_l": Vector3(-0.3, 0, 0.06), "leg_r": Vector3(0.3, 0, -0.06), "hips_y": -0.04},
	"block": {"torso": Vector3(0.05, -0.1, 0), "head": Vector3(0.05, 0.1, 0),
		"arm_r": Vector3(-0.3, 0, -0.35), "hand_r": Vector3(0.2, 0, 0),
		"arm_l": Vector3(-1.45, -0.6, 0.0), "hand_l": Vector3(0, 0, 0),
		"leg_l": Vector3(-0.4, 0, 0.08), "leg_r": Vector3(0.35, 0, -0.08), "hips_y": -0.08},
	"bash": {"torso": Vector3(0.25, 0.25, 0), "head": Vector3(0.0, -0.2, 0),
		"arm_r": Vector3(-0.3, 0, -0.45), "hand_r": Vector3(0.2, 0, 0),
		"arm_l": Vector3(-1.55, -0.1, 0.0), "hand_l": Vector3(0, 0, 0),
		"leg_l": Vector3(-0.6, 0, 0.08), "leg_r": Vector3(0.5, 0, -0.08), "hips_y": -0.14},
	"rise": {"torso": Vector3(-0.2, 0.3, 0), "head": Vector3(-0.2, -0.2, 0),
		"arm_r": Vector3(-2.8, 0.3, -0.2), "hand_r": Vector3(0.5, 0, 0),
		"arm_l": Vector3(-0.6, -0.3, 0.6), "hand_l": Vector3(0, 0, -1.2),
		"leg_l": Vector3(-0.8, 0, 0.06), "leg_r": Vector3(0.2, 0, -0.06), "hips_y": 0.0},
	"charge": {"torso": Vector3(0.15, -1.0, 0), "head": Vector3(0, 0.9, 0),
		"arm_r": Vector3(-0.7, -1.5, -0.3), "hand_r": Vector3(1.1, 0, 0),
		"arm_l": Vector3(-0.9, 0.4, 0.3), "hand_l": Vector3(0, 0, -1.0),
		"leg_l": Vector3(-0.45, 0, 0.1), "leg_r": Vector3(0.45, 0, -0.1), "hips_y": -0.14},
	"heavy_s": {"torso": Vector3(0.25, 0.9, 0), "head": Vector3(0, -0.7, 0),
		"arm_r": Vector3(-1.5, 1.3, 0), "hand_r": Vector3(1.3, 0, 0),
		"arm_l": Vector3(-0.4, -0.3, 0.6), "hand_l": Vector3(0, 0, -1.2),
		"leg_l": Vector3(-0.6, 0, 0.1), "leg_r": Vector3(0.5, 0, -0.1), "hips_y": -0.16},
	"l1_w": {"torso": Vector3(0.05, -0.8, 0), "head": Vector3(0, 0.7, 0),
		"arm_r": Vector3(-1.4, -1.2, 0), "hand_r": Vector3(1.3, 0, 0),
		"arm_l": Vector3(-0.8, -0.2, 0.3), "hand_l": Vector3(0, 0, -1.0),
		"leg_l": Vector3(-0.35, 0, 0.06), "leg_r": Vector3(0.3, 0, -0.06), "hips_y": -0.06},
	"l1_s": {"torso": Vector3(0.12, 0.6, 0), "head": Vector3(0, -0.5, 0),
		"arm_r": Vector3(-1.45, 1.0, 0), "hand_r": Vector3(1.3, 0, 0),
		"arm_l": Vector3(-0.5, -0.5, 0.4), "hand_l": Vector3(0, 0, -1.2),
		"leg_l": Vector3(-0.45, 0, 0.06), "leg_r": Vector3(0.35, 0, -0.06), "hips_y": -0.1},
	"l2_w": {"torso": Vector3(0.05, 0.6, 0), "head": Vector3(0, -0.5, 0),
		"arm_r": Vector3(-1.5, 1.1, 0), "hand_r": Vector3(1.3, 0, 0.3),
		"arm_l": Vector3(-0.5, -0.5, 0.4), "hand_l": Vector3(0, 0, -1.2),
		"leg_l": Vector3(-0.4, 0, 0.06), "leg_r": Vector3(0.3, 0, -0.06), "hips_y": -0.08},
	"l2_s": {"torso": Vector3(0.1, -0.7, 0), "head": Vector3(0, 0.6, 0),
		"arm_r": Vector3(-1.7, -1.1, 0), "hand_r": Vector3(1.3, 0, 0.3),
		"arm_l": Vector3(-0.8, -0.2, 0.3), "hand_l": Vector3(0, 0, -1.0),
		"leg_l": Vector3(-0.45, 0, 0.06), "leg_r": Vector3(0.35, 0, -0.06), "hips_y": -0.1},
	"l3_w": {"torso": Vector3(-0.1, -0.2, 0), "head": Vector3(0.1, 0.2, 0),
		"arm_r": Vector3(-2.9, 0, -0.1), "hand_r": Vector3(0.6, 0, 0),
		"arm_l": Vector3(-1.0, 0, 0.4), "hand_l": Vector3(0, 0, -1.0),
		"leg_l": Vector3(-0.3, 0, 0.06), "leg_r": Vector3(0.3, 0, -0.06), "hips_y": -0.02},
	"l3_s": {"torso": Vector3(0.4, -0.1, 0), "head": Vector3(-0.2, 0, 0),
		"arm_r": Vector3(-0.9, 0, -0.05), "hand_r": Vector3(1.2, 0, 0),
		"arm_l": Vector3(-0.6, -0.3, 0.5), "hand_l": Vector3(0, 0, -1.2),
		"leg_l": Vector3(-0.6, 0, 0.08), "leg_r": Vector3(0.5, 0, -0.08), "hips_y": -0.18},
}

# Staff in the right hand; hand_r x tilts the staff so it stays upright as the arm rises.
const MAGE_POSES := {
	"idle": {"torso": Vector3(0.05, -0.15, 0), "head": Vector3(0, 0.12, 0),
		"arm_r": Vector3(-0.35, 0, -0.3), "hand_r": Vector3(0.45, 0, 0.3),
		"arm_l": Vector3(-0.5, -0.3, 0.45), "hand_l": Vector3(0, 0, -0.6),
		"leg_l": Vector3(-0.15, 0, 0.05), "leg_r": Vector3(0.15, 0, -0.05), "hips_y": -0.02},
	"block": {"torso": Vector3(0.0, -0.1, 0), "head": Vector3(0, 0.1, 0),
		"arm_r": Vector3(-0.35, 0, -0.35), "hand_r": Vector3(0.5, 0, 0.3),
		"arm_l": Vector3(-1.5, -0.45, 0.0), "hand_l": Vector3(0, 0, 0),
		"leg_l": Vector3(-0.3, 0, 0.06), "leg_r": Vector3(0.3, 0, -0.06), "hips_y": -0.06},
	"m1_w": {"torso": Vector3(0.0, 0.3, 0), "head": Vector3(0, -0.2, 0),
		"arm_r": Vector3(-0.5, 0, -0.3), "hand_r": Vector3(0.6, 0, 0.3),
		"arm_l": Vector3(-1.1, 0.5, 0.5), "hand_l": Vector3(0, 0, -0.6),
		"leg_l": Vector3(-0.2, 0, 0.05), "leg_r": Vector3(0.2, 0, -0.05), "hips_y": -0.04},
	"m1_s": {"torso": Vector3(0.05, -0.35, 0), "head": Vector3(0, 0.3, 0),
		"arm_r": Vector3(-0.5, 0, -0.3), "hand_r": Vector3(0.6, 0, 0.3),
		"arm_l": Vector3(-1.55, -0.35, 0.0), "hand_l": Vector3(0, 0, 0),
		"leg_l": Vector3(-0.35, 0, 0.05), "leg_r": Vector3(0.3, 0, -0.05), "hips_y": -0.06},
	"m2_w": {"torso": Vector3(0.0, -0.4, 0), "head": Vector3(0, 0.35, 0),
		"arm_r": Vector3(-0.6, -0.4, -0.35), "hand_r": Vector3(0.6, 0, 0.3),
		"arm_l": Vector3(-0.6, -0.3, 0.5), "hand_l": Vector3(0, 0, -0.6),
		"leg_l": Vector3(-0.2, 0, 0.05), "leg_r": Vector3(0.2, 0, -0.05), "hips_y": -0.04},
	"m2_s": {"torso": Vector3(0.08, 0.35, 0), "head": Vector3(0, -0.3, 0),
		"arm_r": Vector3(-1.2, 0.15, -0.1), "hand_r": Vector3(1.3, 0, 0),
		"arm_l": Vector3(-0.5, -0.3, 0.6), "hand_l": Vector3(0, 0, -0.6),
		"leg_l": Vector3(-0.4, 0, 0.05), "leg_r": Vector3(0.35, 0, -0.05), "hips_y": -0.08},
	"m3_w": {"torso": Vector3(-0.1, 0, 0), "head": Vector3(-0.1, 0, 0),
		"arm_r": Vector3(-2.0, 0, -0.2), "hand_r": Vector3(2.0, 0, 0),
		"arm_l": Vector3(-2.2, 0, 0.3), "hand_l": Vector3(0, 0, -0.4),
		"leg_l": Vector3(-0.2, 0, 0.05), "leg_r": Vector3(0.2, 0, -0.05), "hips_y": -0.02},
	"m3_s": {"torso": Vector3(0.2, 0, 0), "head": Vector3(0, 0, 0),
		"arm_r": Vector3(-1.4, 0, -0.1), "hand_r": Vector3(1.4, 0, 0),
		"arm_l": Vector3(-1.5, 0, 0.1), "hand_l": Vector3(0, 0, 0),
		"leg_l": Vector3(-0.45, 0, 0.05), "leg_r": Vector3(0.4, 0, -0.05), "hips_y": -0.1},
	"mh_w": {"torso": Vector3(-0.12, 0, 0), "head": Vector3(-0.2, 0, 0),
		"arm_r": Vector3(-2.9, 0, -0.15), "hand_r": Vector3(2.9, 0, 0),
		"arm_l": Vector3(-1.2, -0.5, 0.6), "hand_l": Vector3(0, 0, -0.4),
		"leg_l": Vector3(-0.3, 0, 0.08), "leg_r": Vector3(0.3, 0, -0.08), "hips_y": -0.05},
	"mh_s": {"torso": Vector3(0.22, 0, 0), "head": Vector3(0, 0, 0),
		"arm_r": Vector3(-1.4, 0, -0.05), "hand_r": Vector3(1.4, 0, 0),
		"arm_l": Vector3(-0.6, 0, 0.7), "hand_l": Vector3(0, 0, -0.8),
		"leg_l": Vector3(-0.5, 0, 0.08), "leg_r": Vector3(0.45, 0, -0.08), "hips_y": -0.12},
}

const ASSASSIN_POSES := {
	"idle": {"torso": Vector3(0.25, -0.3, 0), "head": Vector3(-0.15, 0.3, 0),
		"arm_r": Vector3(-0.9, -0.3, -0.3), "hand_r": Vector3(0.2, 0, 0),
		"arm_l": Vector3(-0.8, 0.5, 0.35), "hand_l": Vector3(0.2, 0, 0),
		"leg_l": Vector3(-0.5, 0, 0.1), "leg_r": Vector3(0.45, 0, -0.1), "hips_y": -0.12},
	"block": {"torso": Vector3(0.1, 0, 0), "head": Vector3(0, 0, 0),
		"arm_r": Vector3(-1.4, 0.55, 0), "hand_r": Vector3(1.0, 0, 0.6),
		"arm_l": Vector3(-1.4, -0.55, 0), "hand_l": Vector3(1.0, 0, -0.6),
		"leg_l": Vector3(-0.4, 0, 0.08), "leg_r": Vector3(0.4, 0, -0.08), "hips_y": -0.1},
	"as1_w": {"torso": Vector3(0.2, -0.7, 0), "head": Vector3(-0.1, 0.6, 0),
		"arm_r": Vector3(-1.3, -1.2, 0), "hand_r": Vector3(1.3, 0, 0),
		"arm_l": Vector3(-0.8, 0.5, 0.35), "hand_l": Vector3(0.2, 0, 0),
		"leg_l": Vector3(-0.5, 0, 0.1), "leg_r": Vector3(0.45, 0, -0.1), "hips_y": -0.12},
	"as1_s": {"torso": Vector3(0.25, 0.5, 0), "head": Vector3(-0.1, -0.4, 0),
		"arm_r": Vector3(-1.35, 0.9, 0), "hand_r": Vector3(1.3, 0, 0),
		"arm_l": Vector3(-0.8, 0.5, 0.35), "hand_l": Vector3(0.2, 0, 0),
		"leg_l": Vector3(-0.55, 0, 0.1), "leg_r": Vector3(0.5, 0, -0.1), "hips_y": -0.14},
	"as2_w": {"torso": Vector3(0.2, 0.6, 0), "head": Vector3(-0.1, -0.5, 0),
		"arm_r": Vector3(-0.9, -0.3, -0.3), "hand_r": Vector3(0.2, 0, 0),
		"arm_l": Vector3(-1.3, 1.2, 0), "hand_l": Vector3(1.3, 0, 0),
		"leg_l": Vector3(-0.5, 0, 0.1), "leg_r": Vector3(0.45, 0, -0.1), "hips_y": -0.12},
	"as2_s": {"torso": Vector3(0.25, -0.5, 0), "head": Vector3(-0.1, 0.4, 0),
		"arm_r": Vector3(-0.9, -0.3, -0.3), "hand_r": Vector3(0.2, 0, 0),
		"arm_l": Vector3(-1.35, -0.9, 0), "hand_l": Vector3(1.3, 0, 0),
		"leg_l": Vector3(-0.55, 0, 0.1), "leg_r": Vector3(0.5, 0, -0.1), "hips_y": -0.14},
	"as3_w": {"torso": Vector3(0.1, -0.5, 0), "head": Vector3(-0.05, 0.45, 0),
		"arm_r": Vector3(-0.9, -0.2, -0.4), "hand_r": Vector3(1.4, 0, 0),
		"arm_l": Vector3(-0.7, 0.5, 0.4), "hand_l": Vector3(0.2, 0, 0),
		"leg_l": Vector3(-0.45, 0, 0.1), "leg_r": Vector3(0.45, 0, -0.1), "hips_y": -0.12},
	"as3_s": {"torso": Vector3(0.3, 0.3, 0), "head": Vector3(-0.15, -0.25, 0),
		"arm_r": Vector3(-1.6, 0.1, 0), "hand_r": Vector3(1.5, 0, 0),
		"arm_l": Vector3(-0.6, 0.6, 0.5), "hand_l": Vector3(0.2, 0, 0),
		"leg_l": Vector3(-0.7, 0, 0.1), "leg_r": Vector3(0.6, 0, -0.1), "hips_y": -0.2},
	"as4_w": {"torso": Vector3(0.0, 0, 0), "head": Vector3(0, 0, 0),
		"arm_r": Vector3(-1.3, -1.4, 0), "hand_r": Vector3(1.3, 0, 0),
		"arm_l": Vector3(-1.3, 1.4, 0), "hand_l": Vector3(1.3, 0, 0),
		"leg_l": Vector3(-0.4, 0, 0.1), "leg_r": Vector3(0.4, 0, -0.1), "hips_y": -0.1},
	"as4_s": {"torso": Vector3(0.3, 0, 0), "head": Vector3(-0.1, 0, 0),
		"arm_r": Vector3(-1.4, 0.9, 0), "hand_r": Vector3(1.3, 0, 0),
		"arm_l": Vector3(-1.4, -0.9, 0), "hand_l": Vector3(1.3, 0, 0),
		"leg_l": Vector3(-0.6, 0, 0.1), "leg_r": Vector3(0.55, 0, -0.1), "hips_y": -0.18},
	"ash_w": {"torso": Vector3(0.5, -0.2, 0), "head": Vector3(-0.35, 0.2, 0),
		"arm_r": Vector3(-0.4, -0.8, -0.6), "hand_r": Vector3(1.2, 0, 0),
		"arm_l": Vector3(-0.4, 0.8, 0.6), "hand_l": Vector3(1.2, 0, 0),
		"leg_l": Vector3(-0.7, 0, 0.12), "leg_r": Vector3(0.6, 0, -0.12), "hips_y": -0.25},
	"ash_s": {"torso": Vector3(0.4, 0, 0), "head": Vector3(-0.25, 0, 0),
		"arm_r": Vector3(-1.5, 0.6, 0), "hand_r": Vector3(1.4, 0, 0),
		"arm_l": Vector3(-1.5, -0.6, 0), "hand_l": Vector3(1.4, 0, 0),
		"leg_l": Vector3(-0.8, 0, 0.12), "leg_r": Vector3(0.7, 0, -0.12), "hips_y": -0.22},
}


static func poses(kit: String) -> Dictionary:
	match kit:
		"mage":
			return COMMON_POSES.merged(MAGE_POSES, true)
		"assassin":
			return COMMON_POSES.merged(ASSASSIN_POSES, true)
	return COMMON_POSES.merged(KNIGHT_POSES, true)
