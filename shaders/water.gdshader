// Stylized magic water: deep core, bright fresnel edge, swirling foam bands.
shader_type spatial;
render_mode unshaded, blend_mix, cull_back, depth_draw_opaque, shadows_disabled;

uniform vec4 deep_color : source_color = vec4(0.12, 0.45, 0.95, 0.75);
uniform vec4 foam_color : source_color = vec4(0.75, 0.97, 1.0, 1.0);
uniform float alpha_mult : hint_range(0.0, 1.0) = 1.0;
uniform float glow : hint_range(0.0, 4.0) = 1.4;
uniform float swirl_speed = 3.0;

void fragment() {
	float fres = pow(1.0 - clamp(dot(NORMAL, VIEW), 0.0, 1.0), 2.0);
	float w = sin(UV.x * 18.0 + UV.y * 9.0 + mod(TIME, 100.0) * swirl_speed) * 0.5 + 0.5;
	float band = smoothstep(0.72, 0.78, w);
	vec3 c = mix(deep_color.rgb, foam_color.rgb, clamp(fres + band * 0.6, 0.0, 1.0));
	ALBEDO = c * glow;
	ALPHA = clamp(mix(deep_color.a, 1.0, fres) * alpha_mult, 0.0, 1.0);
}
