extends RefCounted
## The playable cast, plus the current match picks (kept in static vars across scenes).
## Each entry's "look" drives both the model (colors, hair, hat, outfit kit) and the combat kit.

const CHARACTERS := [
	{"id": "aster", "title": "Azure Knight", "role": "Knight - Sword & Shield",
		"desc": "A steady guardian. Big guard, heavy sword swings, a shield that shrugs off blows.",
		"stats": {"power": 4, "speed": 3, "range": 2, "defense": 5},
		"look": {"name": "Aster", "kit": "knight", "element": "light", "style": "short", "hat": "none",
			"hair": Color("e6edf8"), "hair_shade": Color(0.7, 0.76, 0.95),
			"iris_top": Color("1c6fd1"), "iris_bottom": Color("7fe3ff"), "eye_dark": Color("152a5e"),
			"tunic": Color("2b4fa8"), "band": Color("f4f6ff"), "pants": Color("1d2442"), "boots": Color("5a3a2a"),
			"metal": Color("d5deef"), "trim": Color("e6c26e"),
			"cape": Color("3d6fd6"), "cape_bottom": Color("9fd8ff"),
			"glow": Color(0.4, 0.85, 1.0), "shield": Color("2b4fa8"), "emblem": Color("f4f6ff")}},
	{"id": "vesper", "title": "Crimson Duelist", "role": "Knight - Sword & Shield",
		"desc": "A ruthless duelist who trades a little defense for relentless pressure.",
		"stats": {"power": 5, "speed": 3, "range": 2, "defense": 4},
		"look": {"name": "Vesper", "kit": "knight", "element": "flame", "style": "ponytail", "hat": "none",
			"hair": Color("c22a3e"), "hair_shade": Color(0.75, 0.62, 0.82),
			"iris_top": Color("a3122b"), "iris_bottom": Color("ffb347"), "eye_dark": Color("3a0d18"),
			"tunic": Color("8f1d2c"), "band": Color("221827"), "pants": Color("221827"), "boots": Color("3a2420"),
			"metal": Color("4a4256"), "trim": Color("e6b45c"),
			"cape": Color("221827"), "cape_bottom": Color("8f1d2c"),
			"glow": Color(1.0, 0.45, 0.2), "shield": Color("221827"), "emblem": Color("c4283c")}},
	{"id": "ember", "title": "Flame Witch", "role": "Mage - Fire",
		"desc": "Fireballs at range, explosive charged blasts, and a meteor to end the fight.",
		"stats": {"power": 5, "speed": 3, "range": 5, "defense": 2},
		"look": {"name": "Ember", "kit": "mage", "element": "fire", "style": "twintails", "hat": "witch",
			"hair": Color("ff7448"), "hair_shade": Color(0.85, 0.62, 0.7),
			"iris_top": Color("c0392b"), "iris_bottom": Color("ffd166"), "eye_dark": Color("4a1410"),
			"tunic": Color("7a1f1f"), "band": Color("fff2e0"), "pants": Color("2a1414"), "boots": Color("3a1a12"),
			"metal": Color("c9b8a6"), "trim": Color("e6c26e"),
			"cape": Color("c0392b"), "cape_bottom": Color("ffb347"),
			"glow": Color(1.0, 0.5, 0.15), "shield": Color("7a1f1f"), "emblem": Color("c0392b")}},
	{"id": "marina", "title": "Tide Sorceress", "role": "Mage - Water",
		"desc": "Controls space with water: bubble wards, geyser rings, and a crushing ocean sphere.",
		"stats": {"power": 4, "speed": 3, "range": 5, "defense": 3},
		"look": {"name": "Marina", "kit": "mage", "element": "water", "style": "bob", "hat": "beret",
			"hair": Color("8cc3f0"), "hair_shade": Color(0.68, 0.74, 0.95),
			"iris_top": Color("1f6fd0"), "iris_bottom": Color("73dcf5"), "eye_dark": Color("1a2a66"),
			"tunic": Color("23307a"), "band": Color("f6f7ff"), "pants": Color("f6f7ff"), "boots": Color("23307a"),
			"metal": Color("d5deef"), "trim": Color("e6c26e"),
			"cape": Color("4f97dc"), "cape_bottom": Color("a3e6f0"),
			"glow": Color(0.35, 0.75, 1.0), "shield": Color("23307a"), "emblem": Color("23307a")}},
	{"id": "volta", "title": "Storm Caller", "role": "Mage - Electric",
		"desc": "Lightning-fast bolts, a blink escape, and a storm that hunts the enemy down.",
		"stats": {"power": 4, "speed": 4, "range": 5, "defense": 2},
		"look": {"name": "Volta", "kit": "mage", "element": "electric", "style": "short", "hat": "goggles",
			"hair": Color("ffe066"), "hair_shade": Color(0.85, 0.72, 0.85),
			"iris_top": Color("6c3fd1"), "iris_bottom": Color("ffe066"), "eye_dark": Color("241a4a"),
			"tunic": Color("3b2a6b"), "band": Color("f4f0ff"), "pants": Color("2b2140"), "boots": Color("2b2140"),
			"metal": Color("cfc6e8"), "trim": Color("ffd84d"),
			"cape": Color("6c4bd1"), "cape_bottom": Color("c9b6ff"),
			"glow": Color(0.78, 0.62, 1.0), "shield": Color("3b2a6b"), "emblem": Color("ffd84d")}},
	{"id": "nyx", "title": "Shadow Blade", "role": "Assassin - Twin Daggers",
		"desc": "Blinding speed and a four-hit flurry. Fragile, but almost impossible to pin down.",
		"stats": {"power": 4, "speed": 5, "range": 2, "defense": 1},
		"look": {"name": "Nyx", "kit": "assassin", "element": "shadow", "style": "ponytail", "hat": "hood",
			"hair": Color("3a3550"), "hair_shade": Color(0.7, 0.66, 0.9),
			"iris_top": Color("7b2cbf"), "iris_bottom": Color("e0aaff"), "eye_dark": Color("1d1030"),
			"tunic": Color("1f1b2e"), "band": Color("6b3fa0"), "pants": Color("17141f"), "boots": Color("17141f"),
			"metal": Color("8f8aa8"), "trim": Color("c9a7ff"),
			"cape": Color("6b3fa0"), "cape_bottom": Color("b38cff"),
			"glow": Color(0.75, 0.4, 1.0), "shield": Color("1f1b2e"), "emblem": Color("c9a7ff")}},
]

static var player_pick := 0
## -1 = random opponent.
static var enemy_pick := -1
## CPU difficulty, index into ai_brain.gd LEVELS (0 Easy .. 3 Master).
static var difficulty := 1


static func look(i: int) -> Dictionary:
	return CHARACTERS[i].look


static func resolve_enemy() -> int:
	if enemy_pick >= 0:
		return enemy_pick
	var choices: Array[int] = []
	for i in CHARACTERS.size():
		if i != player_pick:
			choices.append(i)
	return choices.pick_random()
