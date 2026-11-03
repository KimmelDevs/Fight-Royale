// Cel-shaded solid surface. See toon_common.gdshaderinc for the lighting model.
shader_type spatial;
render_mode unshaded, cull_back;

#include "res://shaders/toon_common.gdshaderinc"

uniform vec4 albedo : source_color = vec4(1.0);

void fragment() {
	ALBEDO = toon_shade(albedo.rgb, NORMAL, VIEW, VIEW_MATRIX);
}
