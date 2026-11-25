shader_type spatial;
render_mode unshaded, blend_add, depth_draw_never, cull_disabled;

// DEVLOG-163: the client's own five-frame flame animation (FX_E_T
// flame_a01..a05), displayed as camera-facing quads on every village candle.
// Additive on the black sprite background: no alpha-cutout sorting needed.
uniform sampler2DArray flame_frames : source_color, filter_linear_mipmap;
uniform float frame_speed = 8.0;
uniform float glow_energy = 1.25;
// Diagnostic only: L2_CANDLE_FIRE_FRAME pins one client frame and the
// matching flicker time for deterministic A/B. -1 keeps live TIME animation.
uniform int frame_override = -1;
uniform float time_override = -1.0;

varying vec2 flame_uv;
varying float flame_phase;

float phase_of(vec2 p) {
	return fract(sin(dot(p, vec2(12.9898, 78.233))) * 43758.5453);
}

void vertex() {
	mat4 inv_view = inverse(VIEW_MATRIX);
	vec3 right = inv_view[0].xyz;
	vec3 up = inv_view[1].xyz;
	vec3 center = (MODEL_MATRIX * vec4(0.0, 0.0, 0.0, 1.0)).xyz;
	float w = length(MODEL_MATRIX[0].xyz);
	float h = length(MODEL_MATRIX[1].xyz);
	float phase = phase_of(center.xz);
	float anim_time = time_override >= 0.0 ? time_override : TIME;
	float flick = 1.0 + 0.055 * sin(anim_time * 7.3 + phase * 6.2831)
			+ 0.025 * sin(anim_time * 13.7 + phase * 12.5664);
	vec3 world = center + right * VERTEX.x * w * flick + up * VERTEX.y * h;
	POSITION = PROJECTION_MATRIX * VIEW_MATRIX * vec4(world, 1.0);
	flame_uv = UV;
	flame_phase = phase;
}

void fragment() {
	float anim_time = time_override >= 0.0 ? time_override : TIME;
	float frame = frame_override >= 0 ? float(frame_override)
			: floor(mod(anim_time * frame_speed + flame_phase * 5.0, 5.0));
	vec4 tex = texture(flame_frames, vec3(flame_uv, frame));
	float flick = 1.0 + 0.075 * sin(anim_time * 8.1 + flame_phase * 6.2831)
			+ 0.035 * sin(anim_time * 15.3 + flame_phase * 12.5664);
	ALBEDO = tex.rgb * flick;
	ALPHA = tex.a;
	EMISSION = tex.rgb * glow_energy * flick;
}
