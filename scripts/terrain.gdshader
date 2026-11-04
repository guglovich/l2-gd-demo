shader_type spatial;
render_mode cull_disabled, depth_draw_opaque;

// Dark Elf Village terrain: eight L2 color layers, each with its own mask.
// Layers are blended in slot order over a neutral gray base, matching the
// public l2mapconv terrain renderer. Layer 0 (Obase_1) is the base terrain
// and covers most of the tile; other layers add detail on top.

uniform float do_debug = 0.0;
uniform sampler2D layer_0_texture : source_color, repeat_enable, filter_linear_mipmap_anisotropic;
uniform sampler2D layer_1_texture : source_color, repeat_enable, filter_linear_mipmap_anisotropic;
uniform sampler2D layer_2_texture : source_color, repeat_enable, filter_linear_mipmap_anisotropic;
uniform sampler2D layer_3_texture : source_color, repeat_enable, filter_linear_mipmap_anisotropic;
uniform sampler2D layer_4_texture : source_color, repeat_enable, filter_linear_mipmap_anisotropic;
uniform sampler2D layer_5_texture : source_color, repeat_enable, filter_linear_mipmap_anisotropic;
uniform sampler2D layer_6_texture : source_color, repeat_enable, filter_linear_mipmap_anisotropic;
uniform sampler2D layer_7_texture : source_color, repeat_enable, filter_linear_mipmap_anisotropic;

uniform sampler2D mask_0 : source_color;
uniform sampler2D mask_1 : source_color;
uniform sampler2D mask_2 : source_color;
uniform sampler2D mask_3 : source_color;
uniform sampler2D mask_4 : source_color;
uniform sampler2D mask_5 : source_color;
uniform sampler2D mask_6 : source_color;
uniform sampler2D mask_7 : source_color;

uniform vec2 layer_0_uv_scale = vec2(1.0);
uniform vec2 layer_1_uv_scale = vec2(1.0);
uniform vec2 layer_2_uv_scale = vec2(1.0);
uniform vec2 layer_3_uv_scale = vec2(1.0);
uniform vec2 layer_4_uv_scale = vec2(1.0);
uniform vec2 layer_5_uv_scale = vec2(1.0);
uniform vec2 layer_6_uv_scale = vec2(1.0);
uniform vec2 layer_7_uv_scale = vec2(1.0);

uniform vec2 layer_0_uv_offset = vec2(0.0);
uniform vec2 layer_1_uv_offset = vec2(0.0);
uniform vec2 layer_2_uv_offset = vec2(0.0);
uniform vec2 layer_3_uv_offset = vec2(0.0);
uniform vec2 layer_4_uv_offset = vec2(0.0);
uniform vec2 layer_5_uv_offset = vec2(0.0);
uniform vec2 layer_6_uv_offset = vec2(0.0);
uniform vec2 layer_7_uv_offset = vec2(0.0);

varying vec2 tile_uv;

void vertex() {
	tile_uv = UV;
}

void fragment() {
	// Masks sample bilinearly at vertex UV — smooth layer blending like the
	// original client. The mask textures' V axis is INVERTED relative to the
	// terrain rows (verified: the west-road cell (33,158) texel (134,634) is
	// empty while the mirrored (134,390) carries the grass weight), so
	// sample at 1 - v.
	// Layer detail textures tile per world scale: uv = quad * Scale/64
	// (L2: su = 2*Scale/(128*128*UScale) per world unit, quad = 128 units).
	// Mask V is inverted vs terrain rows (see comment above).
	vec2 mask_uv = vec2(tile_uv.x, 1.0 - tile_uv.y);
	vec3 color = vec3(0.35);
	color = texture(layer_0_texture, tile_uv * layer_0_uv_scale + layer_0_uv_offset).rgb; // base layer, unconditional
	color = mix(color, texture(layer_1_texture, tile_uv * layer_1_uv_scale + layer_1_uv_offset).rgb, texture(mask_1, mask_uv).r);
	color = mix(color, texture(layer_2_texture, tile_uv * layer_2_uv_scale + layer_2_uv_offset).rgb, texture(mask_2, mask_uv).r);
	color = mix(color, texture(layer_3_texture, tile_uv * layer_3_uv_scale + layer_3_uv_offset).rgb, texture(mask_3, mask_uv).r);
	color = mix(color, texture(layer_4_texture, tile_uv * layer_4_uv_scale + layer_4_uv_offset).rgb, texture(mask_4, mask_uv).r);
	color = mix(color, texture(layer_5_texture, tile_uv * layer_5_uv_scale + layer_5_uv_offset).rgb, texture(mask_5, mask_uv).r);
	color = mix(color, texture(layer_6_texture, tile_uv * layer_6_uv_scale + layer_6_uv_offset).rgb, texture(mask_6, mask_uv).r);
	color = mix(color, texture(layer_7_texture, tile_uv * layer_7_uv_scale + layer_7_uv_offset).rgb, texture(mask_7, mask_uv).r);

	// L2_TERRAIN_DEBUG=uv -> paint tile_uv; =masks -> paint mask weights
	if (do_debug > 0.5) {
		ALBEDO = vec3(tile_uv.x, tile_uv.y, 0.0);
	} else {
		ALBEDO = color;
	}
	ROUGHNESS = 0.95;
	SPECULAR = 0.1;
}
