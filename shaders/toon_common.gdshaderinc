// Shared cel-shading: two hard-edged light bands, tinted shadows and a thin rim light.
// Unshaded so the look stays identical in every renderer; the sun direction is a uniform.

uniform vec4 shade_tint : source_color = vec4(0.74, 0.72, 0.9, 1.0);
uniform float shade_threshold : hint_range(-1.0, 1.0) = 0.0;
uniform float shade_softness : hint_range(0.0, 0.5) = 0.03;
uniform vec4 rim_color : source_color = vec4(1.0);
uniform float rim_amount : hint_range(0.0, 1.0) = 0.3;
uniform vec4 emission : source_color = vec4(0.0, 0.0, 0.0, 1.0);
// Direction toward the sun in world space. Keep in sync with main.gd LIGHT_DIR.
uniform vec3 light_dir = vec3(0.45, 0.8, 0.4);

vec3 toon_shade(vec3 base, vec3 normal, vec3 view, mat4 view_matrix) {
	vec3 l = normalize((view_matrix * vec4(normalize(light_dir), 0.0)).xyz);
	float ndl = dot(normal, l);
	float lit = smoothstep(shade_threshold - shade_softness, shade_threshold + shade_softness, ndl);
	vec3 col = mix(base * shade_tint.rgb, base, lit);
	float fres = 1.0 - clamp(dot(normal, view), 0.0, 1.0);
	float rim = smoothstep(0.62, 0.68, fres) * (0.35 + 0.65 * lit);
	col += rim_color.rgb * 0.35 * rim * rim_amount;
	return col + emission.rgb;
}
