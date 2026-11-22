// DEVLOG-133 DIAGNOSTIC ONLY (L2_TERRAIN_LIGHTDEBUG=1): a light-path canvas
// for the terrain. The albedo is forced WHITE so every pixel shows the raw
// light response:
//   - ~126 gray  = the ambient reaches the terrain (the env ambient on a
//     white albedo), the sun does not (the shadow factor 0)
//   - bright 200+ = the direct sun reaches the pixel (its color x shadow x
//     NdotL over the white canvas)
//   - black      = the terrain receives NOTHING at all (the mesh/shader
//     pipeline broken, e.g. the normals path)
// The diffuse term is the plain Lambert read of the engine's LIGHT block —
// LIGHT_COLOR already carries the sun energy/color, ATTENUATION carries the
// shadow factor. Replaces terrain.gdshader only when the flag is set; the
// normal render path is untouched.
shader_type spatial;
render_mode cull_disabled, depth_draw_opaque;

uniform float placeholder = 0.0;

varying vec2 tile_uv;

void vertex() {
	tile_uv = UV;
}

void fragment() {
	ALBEDO = vec3(1.0);
	ROUGHNESS = 1.0;
	SPECULAR = 0.0;
}

void light() {
	float cNdotL = clamp(dot(NORMAL, normalize(LIGHT)), 0.0, 1.0);
	DIFFUSE_LIGHT += cNdotL * LIGHT_COLOR * ATTENUATION;
}
