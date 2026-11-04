extends CharacterBody3D
## Third-person player: WASD + mouse orbit, terrain-following.

const WALK_SPEED := 2.6
const RUN_SPEED := 6.4
const GRAVITY := 14.0

var terrain: Node3D
var yaw := 0.0
var _last_title_ms := 0
var _coord_label: Label

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
	Input.mouse_mode = Input.MOUSE_MODE_CAPTURED

func _load_character() -> void:
	var rig := Node3D.new()
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
	elif event.is_action_pressed("ui_cancel"):
		Input.mouse_mode = Input.MOUSE_MODE_VISIBLE

func _physics_process(delta: float) -> void:
	if OS.get_environment("L2_DEBUG_CAM") == "":
		cam_pivot.rotation = Vector3(pitch, yaw, 0)
	var input := Input.get_vector("ui_left", "ui_right", "ui_up", "ui_down")
	var dir := Vector3.ZERO
	if input.length_squared() > 0.01:
		var basis_yaw := Basis(Vector3.UP, yaw)
		var fwd := -basis_yaw.z
		var right := basis_yaw.x
		dir = (fwd * -input.y + right * input.x).normalized()
		var speed := RUN_SPEED if Input.is_key_pressed(KEY_SHIFT) else WALK_SPEED
		velocity.x = dir.x * speed
		velocity.z = dir.z * speed
		# face movement direction
		rotation.y = lerp_angle(rotation.y, atan2(-dir.x, -dir.z), 10.0 * delta)
	else:
		velocity.x = move_toward(velocity.x, 0, 20 * delta)
		velocity.z = move_toward(velocity.z, 0, 20 * delta)
	if is_on_floor():
		velocity.y = 0
	else:
		velocity.y -= GRAVITY * delta
	move_and_slide()
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
