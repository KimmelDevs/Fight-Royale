// Cel-shaded double-sided cloth for generated sheets (UV.x around, UV.y top -> hem).
// Adds a top-to-hem color gradient, wave motif band, gold trims and a gentle wind ripple.
shader_type spatial;
render_mode unshaded, cull_disabled;

#include "res://shaders/toon_common.gdshaderinc"

uniform vec4 albedo : source_color = vec4(1.0);
uniform vec4 albedo_bottom : source_color = vec4(1.0);
uniform vec4 trim_color : source_color = vec4(0.9, 0.76, 0.43, 1.0);
uniform float trim_bottom = 0.0;  // hem trim thickness in UV.y
uniform float trim_sides = 0.0;  // open-edge trim thickness in UV.x
uniform vec4 pattern_color : source_color = vec4(1.0);
uniform float pattern_strength = 0.0;
uniform float pattern_v = 0.75;  // where the wave band sits, in UV.y
uniform float pattern_freq = 6.0;  // waves around the sheet
uniform float pattern_fill = 0.0;  // 1 = solid color below the crest, with a light wave line inside
uniform float wind = 0.0;  // ripple amplitude at the hem, in meters

void vertex() {
	float w = UV.y * UV.y * wind;
	VERTEX += NORMAL * sin(mod(TIME, 100.0) * 3.0 + UV.x * 9.0 + UV.y * 4.0) * w;
}

float line(float d, float half_width) {
	float fw = max(fwidth(d), 0.0005);
	return 1.0 - smoothstep(half_width - fw, half_width + fw, d);
}

void fragment() {
	vec3 base = mix(albedo.rgb, albedo_bottom.rgb, smoothstep(0.15, 1.0, UV.y));

	// Two offset wave lines read as stylized surf, like the art's water motif.
	float crest = pattern_v + sin(UV.x * pattern_freq * TAU) * 0.045;
	float crest2 = pattern_v + 0.08 + sin(UV.x * pattern_freq * TAU + 1.7) * 0.035;
	float l1 = line(abs(UV.y - crest), 0.014);
	float l2 = line(abs(UV.y - crest2), 0.009);
	if (pattern_fill > 0.0) {
		float fw = max(fwidth(UV.y), 0.0005);
		float below = smoothstep(-fw, fw, UV.y - crest);
		base = mix(base, pattern_color.rgb, below * pattern_strength);
		base = mix(base, albedo.rgb, l2 * below * pattern_strength);
	} else {
		base = mix(base, pattern_color.rgb, max(l1, l2 * 0.85) * pattern_strength);
	}

	float trim = trim_bottom > 0.0 ? step(1.0 - trim_bottom, UV.y) : 0.0;
	if (trim_sides > 0.0) {
		trim = max(trim, step(UV.x, trim_sides) + step(1.0 - trim_sides, UV.x));
	}
	base = mix(base, trim_color.rgb, clamp(trim, 0.0, 1.0));

	ALBEDO = toon_shade(base, NORMAL, VIEW, VIEW_MATRIX);
}
