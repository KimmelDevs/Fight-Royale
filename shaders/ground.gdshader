// Flat plain with a faint 2 m grid so movement reads clearly. Lit, so it receives shadows.
shader_type spatial;

uniform vec4 base_color : source_color = vec4(0.62, 0.7, 0.6, 1.0);
uniform vec4 line_color : source_color = vec4(0.5, 0.6, 0.52, 1.0);
uniform float cell = 2.0;

varying vec3 world_pos;

void vertex() {
	world_pos = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz;
}

void fragment() {
	vec2 uv = world_pos.xz / cell;
	vec2 g = abs(fract(uv - 0.5) - 0.5) / fwidth(uv);
	float line = 1.0 - clamp(min(g.x, g.y), 0.0, 1.0);
	ALBEDO = mix(base_color.rgb, line_color.rgb, line * 0.6);
	ROUGHNESS = 1.0;
	SPECULAR = 0.0;
}
