// Anime face painted analytically onto the head sphere (no textures needed).
// Features are placed in (longitude, latitude) of the object-space normal; +Z is the face.
shader_type spatial;
render_mode unshaded, cull_back;

uniform vec4 skin : source_color = vec4(1.0, 0.91, 0.87, 1.0);
uniform vec4 shade_tint : source_color = vec4(1.0, 0.82, 0.82, 1.0);
uniform vec4 eye_dark : source_color = vec4(0.1, 0.16, 0.42, 1.0);
uniform vec4 iris_top : source_color = vec4(0.13, 0.42, 0.82, 1.0);
uniform vec4 iris_bottom : source_color = vec4(0.45, 0.86, 0.96, 1.0);
uniform vec4 blush : source_color = vec4(1.0, 0.65, 0.7, 1.0);
uniform vec4 mouth : source_color = vec4(0.55, 0.18, 0.25, 1.0);
uniform vec4 tongue : source_color = vec4(0.98, 0.55, 0.6, 1.0);
uniform vec3 light_dir = vec3(0.45, 0.8, 0.4);
uniform float blink : hint_range(0.0, 1.0) = 0.0;

varying vec3 local_pos;

void vertex() {
	local_pos = VERTEX;
}

// Normalized distance to an ellipse: < 1 inside.
float ell(vec2 p, vec2 c, vec2 r) {
	return length((p - c) / r);
}

// Anti-aliased fill of an ellipse distance.
float fill(float d) {
	float w = max(fwidth(d), 0.001);
	return 1.0 - smoothstep(1.0 - w, 1.0 + w, d);
}

void fragment() {
	vec3 n = normalize(local_pos);
	vec2 p = vec2(atan(n.x, n.z), asin(clamp(n.y, -1.0, 1.0)));
	float front = smoothstep(0.0, 0.2, n.z);

	vec3 l = normalize((VIEW_MATRIX * vec4(normalize(light_dir), 0.0)).xyz);
	float lit = smoothstep(-0.03, 0.03, dot(NORMAL, l));
	vec3 col = mix(skin.rgb * shade_tint.rgb, skin.rgb, lit);

	float open = 1.0 - blink * 0.93;
	for (int i = 0; i < 2; i++) {
		float side = i == 0 ? 1.0 : -1.0;
		vec2 ec = vec2(0.37 * side, -0.03);
		vec2 er = vec2(0.15, 0.19 * open);

		// Blush sits under the eyes.
		float b = fill(ell(p, vec2(0.58 * side, -0.3), vec2(0.13, 0.055)));
		col = mix(col, blush.rgb, b * 0.35 * front);

		float eye = fill(ell(p, ec, er)) * front;
		float t = clamp((p.y - (ec.y - er.y)) / (2.0 * er.y), 0.0, 1.0);
		vec3 iris = mix(iris_bottom.rgb, iris_top.rgb, t);
		float inner = fill(ell(p, ec + vec2(0.0, -0.01 * open), er * 0.8));
		vec3 ecol = mix(eye_dark.rgb, iris, inner);
		float pupil = fill(ell(p, ec + vec2(0.0, 0.015 * open), vec2(0.05, 0.08 * open)));
		ecol = mix(ecol, eye_dark.rgb, pupil * 0.8);
		float h1 = fill(ell(p, ec + vec2(-0.045 * side, 0.065 * open), vec2(0.035, 0.042 * open)));
		float h2 = fill(ell(p, ec + vec2(0.04 * side, -0.075 * open), vec2(0.018, 0.018)));
		ecol = mix(ecol, vec3(1.0), max(h1, h2 * 0.9));
		col = mix(col, ecol, eye);

		// Thick upper lash line; becomes the closed-eye curve when blinking.
		float outer = fill(ell(p, ec + vec2(0.0, 0.012), er * vec2(1.14, 1.12) + vec2(0.0, 0.02)));
		float lash = outer * (1.0 - eye) * step(ec.y + er.y * 0.15, p.y) * front;
		col = mix(col, eye_dark.rgb, lash);
	}

	// Open smile: a D-shaped mouth with a little tongue.
	vec2 mc = vec2(0.0, -0.43);
	float m = fill(ell(p, mc, vec2(0.11, 0.085))) * step(p.y, mc.y + 0.012) * front;
	float tg = fill(ell(p, mc + vec2(0.0, -0.06), vec2(0.065, 0.04))) * m;
	col = mix(col, mouth.rgb, m);
	col = mix(col, tongue.rgb, tg);

	ALBEDO = col;
}
