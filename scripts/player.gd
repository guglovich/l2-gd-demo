extends CharacterBody3D
## Third-person player: mouse click-to-move (run to the destination in a
## straight line), WASD kept as the fallback, mouse orbit, terrain-following.
## The gait = a procedural bob until the skeletal animations are converted
## from the L2 .psa/.ukx data.

const WALK_SPEED := 2.6
const RUN_SPEED := 6.4
const GRAVITY := 14.0
const ARRIVE_DIST := 0.6

var terrain: Node3D
var yaw := 0.0
var _last_title_ms := 0
var _coord_label: Label
var move_target: Vector3
var has_target := false
var rig: Node3D
var bob_t := 0.0
var dest_marker: MeshInstance3D

func _init() -> void:
	if OS.get_environment("L2_VIEW_YAW") != "":
		yaw = float(OS.get_environment("L2_VIEW_YAW"))
var pitch := -0.35
var cam_pivot: Node3D
var cam: Camera3D

func _ready() -> void:
	cam_pivot = Node3D.new()
	add_child(cam_pivot)
	cam = Camera3D.new()
	if OS.get_environment("L2_DEBUG_CAM") != "":
		if OS.get_environment("L2_DEBUG_CAM") == "down":
			cam.position = Vector3(0, 6, 0.001)
			cam.rotation = Vector3(-1.55, 0, 0)
		else:
			cam.position = Vector3(0, 30, 0.001)
			cam.rotation = Vector3(-1.55, 0, 0)
	else:
		cam.position = Vector3(0, 2.4, 4.4)
	cam_pivot.add_child(cam)
	cam.current = true
	cam.far = 10000.0
	# Set initial camera rotation to avoid first-frame wrong orientation
	cam_pivot.rotation = Vector3(pitch, yaw, 0)
	var body := CollisionShape3D.new()
	var cap := CapsuleShape3D.new()
	cap.radius = 0.3
	cap.height = 1.7
	body.shape = cap
	body.position = Vector3(0, 0.85, 0)
	add_child(body)
	_load_character()
	# on-screen coordinates (visible in screenshots)
	_coord_label = Label.new()
	_coord_label.position = Vector2(12, 8)
	_coord_label.add_theme_font_size_override("font_size", 22)
	_coord_label.add_theme_color_override("font_color", Color(1, 1, 0.2))
	_coord_label.add_theme_color_override("font_outline_color", Color(0, 0, 0))
	_coord_label.add_theme_constant_override("outline_size", 6)
	var hud := CanvasLayer.new()
	hud.name = "HUD"
	add_child(hud)
	hud.add_child(_coord_label)
	# the destination marker: a glowing disc placed on the ground by the click
	dest_marker = MeshInstance3D.new()
	var disc := CylinderMesh.new()
	disc.top_radius = 0.35
	disc.bottom_radius = 0.35
	disc.height = 0.02
	var dm := StandardMaterial3D.new()
	dm.albedo_color = Color(0.4, 0.8, 1.0)
	dm.emission_enabled = true
	dm.emission = Color(0.3, 0.7, 1.0)
	dm.emission_energy_multiplier = 2.0
	dm.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	disc.material = dm
	dest_marker.mesh = disc
	dest_marker.visible = false
	add_child(dest_marker)
	Input.mouse_mode = Input.MOUSE_MODE_CAPTURED

func _load_character() -> void:
	rig = Node3D.new()
	rig.name = "Rig"
	rig.rotation_degrees.y = 180.0
	add_child(rig)
	for part in ["FDarkElf_m013_u", "FDarkElf_m013_l", "FDarkElf_m013_b", "FDarkElf_m013_g"]:
		var path := "res://assets/character/%s.gltf" % part
		if ResourceLoader.exists(path):
			var scene: PackedScene = load(path)
			var inst := scene.instantiate()
			rig.add_child(inst)

func _unhandled_input(event: InputEvent) -> void:
	if event is InputEventMouseMotion and Input.mouse_mode == Input.MOUSE_MODE_CAPTURED:
		yaw -= event.relative.x * 0.003
		pitch = clampf(pitch - event.relative.y * 0.003, -1.2, 0.4)
	elif event is InputEventMouseButton and event.pressed \
			and Input.mouse_mode != Input.MOUSE_MODE_CAPTURED:
		Input.mouse_mode = Input.MOUSE_MODE_CAPTURED
	elif event is InputEventMouseButton and event.pressed \
			and event.button_index == MOUSE_BUTTON_LEFT \
			and Input.mouse_mode == Input.MOUSE_MODE_CAPTURED:
		# click-to-move: cast through the click position onto the world,
		# set the destination, the character runs there in a straight line
		var from := cam.project_ray_origin(event.position)
		var dir := cam.project_ray_normal(event.position)
		var q := PhysicsRayQueryParameters3D.create(from, from + dir * 2000.0)
		q.exclude = [get_rid()]
		var hit := get_world_3d().direct_space_state.intersect_ray(q)
		if hit:
			move_target = hit.position
			has_target = true
			dest_marker.global_position = move_target + Vector3(0, 0.05, 0)
			dest_marker.visible = true
	elif event.is_action_pressed("ui_cancel"):
		Input.mouse_mode = Input.MOUSE_MODE_VISIBLE

func _physics_process(delta: float) -> void:
	if OS.get_environment("L2_DEBUG_CAM") == "":
		cam_pivot.rotation = Vector3(pitch, yaw, 0)
	var input := Input.get_vector("ui_left", "ui_right", "ui_up", "ui_down")
	var dir := Vector3.ZERO
	var moving := false
	var speed := 0.0
	if input.length_squared() > 0.01:
		var basis_yaw := Basis(Vector3.UP, yaw)
		var fwd := -basis_yaw.z
		var right := basis_yaw.x
		dir = (fwd * -input.y + right * input.x).normalized()
		speed = RUN_SPEED if Input.is_key_pressed(KEY_SHIFT) else WALK_SPEED
		velocity.x = dir.x * speed
		velocity.z = dir.z * speed
		# face movement direction
		rotation.y = lerp_angle(rotation.y, atan2(-dir.x, -dir.z), 10.0 * delta)
		moving = true
	elif has_target:
		# click-to-move: run straight to the destination until close
		var to_t := move_target - position
		to_t.y = 0.0
		if to_t.length() > ARRIVE_DIST:
			dir = to_t.normalized()
			velocity.x = dir.x * RUN_SPEED
			velocity.z = dir.z * RUN_SPEED
			rotation.y = lerp_angle(rotation.y, atan2(-dir.x, -dir.z), 10.0 * delta)
			moving = true
			speed = RUN_SPEED
		else:
			has_target = false
			dest_marker.visible = false
	if not moving:
		velocity.x = move_toward(velocity.x, 0, 20 * delta)
		velocity.z = move_toward(velocity.z, 0, 20 * delta)
	if is_on_floor():
		velocity.y = 0
	else:
		velocity.y -= GRAVITY * delta
	move_and_slide()
	# the placeholder procedural gait: the bob + the lean while moving
	# (the real skeletal walk/run comes from the L2 .psa conversion)
	if moving and rig:
		bob_t += delta * (11.0 if speed >= RUN_SPEED else 7.5)
		rig.position.y = absf(sin(bob_t)) * 0.055
		rig.rotation_degrees.x = 4.0
	elif rig:
		rig.position.y = lerpf(rig.position.y, 0.0, minf(10.0 * delta, 1.0))
		rig.rotation_degrees.x = lerpf(rig.rotation_degrees.x, 0.0,
				minf(10.0 * delta, 1.0))
		bob_t = 0.0
	# live game coordinates: window title + on-screen HUD (debug aid)
	var now := Time.get_ticks_msec()
	if now - _last_title_ms > 250:
		_last_title_ms = now
		var g := Vector3(position.x / 0.01, position.y / 0.01, position.z / 0.01)
		DisplayServer.window_set_title(
			"L2 20_18  X=%.0f Y=%.0f Z=%.1f" % [g.x, g.z, g.y])
		if _coord_label:
			_coord_label.text = "X=%.0f  Y=%.0f  Z=%.1f" % [g.x, g.z, g.y]
	if terrain:
		var game_x: float = position.x / 0.01
		var game_y: float = position.z / 0.01
		if terrain.has_terrain_surface(game_x, game_y):
			var t: float = terrain.terrain_height(game_x, game_y)
			if position.y < t:
				position.y = t
				velocity.y = 0
