// Inverted-hull outline: draws back faces pushed out along the normal.
// `wind` must match the cloth material it outlines so the hull ripples with it.
shader_type spatial;
render_mode unshaded, cull_front, shadows_disabled;

uniform vec4 outline_color : source_color = vec4(0.12, 0.12, 0.25, 1.0);
uniform float width = 0.0065;
uniform float wind = 0.0;

void vertex() {
	float w = UV.y * UV.y * wind;
	VERTEX += NORMAL * sin(mod(TIME, 100.0) * 3.0 + UV.x * 9.0 + UV.y * 4.0) * w;
	VERTEX += normalize(NORMAL) * width;
}

void fragment() {
	ALBEDO = outline_color.rgb;
}
