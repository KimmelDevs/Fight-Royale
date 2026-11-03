extends RefCounted
## Material factory for the cel-shaded look. Toon materials are cached by parameters;
## water and face materials are per-instance because their uniforms get animated.

const TOON := preload("res://shaders/toon.gdshader")
const OUTLINE := preload("res://shaders/outline.gdshader")
const WATER := preload("res://shaders/water.gdshader")
const FACE := preload("res://shaders/face.gdshader")
const CLOTH := preload("res://shaders/cloth.gdshader")
const OUTLINE_WIDTH := 0.0065
const DEFAULT_SHADE := Color(0.74, 0.72, 0.9)

static var _toon_cache := {}
static var _flat_cache := {}


static func toon(color: Color, outline := true, rim := 0.3, emission := Color(0, 0, 0), shade := DEFAULT_SHADE, width := OUTLINE_WIDTH) -> ShaderMaterial:
	var key := "%s|%s|%s|%s|%s|%s" % [color.to_html(), outline, rim, emission.to_html(), shade.to_html(), width]
	if _toon_cache.has(key):
		return _toon_cache[key]
	var m := ShaderMaterial.new()
	m.shader = TOON
	m.set_shader_parameter("albedo", color)
	m.set_shader_parameter("shade_tint", shade)
	m.set_shader_parameter("rim_amount", rim)
	m.set_shader_parameter("emission", emission)
	if outline:
		m.next_pass = _outline(color, width)
	_toon_cache[key] = m
	return m


static func _outline(color: Color, width: float, wind := 0.0) -> ShaderMaterial:
	var o := ShaderMaterial.new()
	o.shader = OUTLINE
	# Anime outlines are a darker, cooler version of the fill, not pure black.
	o.set_shader_parameter("outline_color", Color(color.r * 0.38, color.g * 0.36, color.b * 0.5))
	o.set_shader_parameter("width", width)
	o.set_shader_parameter("wind", wind)
	return o


## Double-sided cloth for generated sheets. Options: bottom (Color), trim_bottom, trim_sides,
## pattern (Color), pattern_strength, pattern_v, pattern_freq, pattern_fill, wind, shade (Color).
static func cloth(color: Color, opts := {}) -> ShaderMaterial:
	var m := ShaderMaterial.new()
	m.shader = CLOTH
	m.set_shader_parameter("albedo", color)
	m.set_shader_parameter("albedo_bottom", opts.get("bottom", color))
	m.set_shader_parameter("shade_tint", opts.get("shade", DEFAULT_SHADE))
	m.set_shader_parameter("trim_bottom", opts.get("trim_bottom", 0.0))
	m.set_shader_parameter("trim_sides", opts.get("trim_sides", 0.0))
	m.set_shader_parameter("pattern_color", opts.get("pattern", Color.WHITE))
	m.set_shader_parameter("pattern_strength", opts.get("pattern_strength", 0.0))
	m.set_shader_parameter("pattern_v", opts.get("pattern_v", 0.75))
	m.set_shader_parameter("pattern_freq", opts.get("pattern_freq", 6.0))
	m.set_shader_parameter("pattern_fill", opts.get("pattern_fill", 0.0))
	var wind: float = opts.get("wind", 0.0)
	m.set_shader_parameter("wind", wind)
	m.next_pass = _outline(color, OUTLINE_WIDTH * 0.8, wind)
	return m


static func flat(color: Color) -> StandardMaterial3D:
	var key := color.to_html()
	if _flat_cache.has(key):
		return _flat_cache[key]
	var m := StandardMaterial3D.new()
	m.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	m.albedo_color = color
	_flat_cache[key] = m
	return m


static func water(deep: Color, glow := 1.4) -> ShaderMaterial:
	var m := ShaderMaterial.new()
	m.shader = WATER
	m.set_shader_parameter("deep_color", deep)
	m.set_shader_parameter("glow", glow)
	return m


static func face(skin: Color) -> ShaderMaterial:
	var m := ShaderMaterial.new()
	m.shader = FACE
	m.set_shader_parameter("skin", skin)
	var o := _outline(skin, OUTLINE_WIDTH)
	o.set_shader_parameter("outline_color", Color(skin.r * 0.45, skin.g * 0.32, skin.b * 0.35))
	m.next_pass = o
	return m
