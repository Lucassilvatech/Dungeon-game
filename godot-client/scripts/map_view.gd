class_name DungeonMapView
extends Control

signal target_selected(target: Dictionary)
var state: Dictionary = {}
var peers: Array = []
var tile = 26.0
var origin = Vector2.ZERO
var elapsed = 0.0
var deaths: Dictionary = {}
var previous_alive: Dictionary = {}

func _ready():
	custom_minimum_size = Vector2(280, 280)
	mouse_filter = Control.MOUSE_FILTER_STOP
	clip_contents = true

func set_state(next: Dictionary):
	if state.get("room", {}).get("id", "") != next.get("room", {}).get("id", ""):
		deaths.clear()
		previous_alive.clear()
	for e in next.get("map", {}).get("enemies", []):
		var id = int(e.id)
		if e.state == "DEAD" and previous_alive.has(id):
			deaths[id] = {"enemy": e, "at": elapsed}
			previous_alive.erase(id)
		elif e.state != "DEAD":
			previous_alive[id] = true
	state = next
	queue_redraw()

func _process(delta):
	elapsed += delta
	for id in deaths.keys():
		if elapsed - deaths[id].at > 0.7:
			deaths.erase(id)
	queue_redraw()

func _draw():
	draw_rect(Rect2(Vector2.ZERO, size), Color("111e23"))
	if state.is_empty():
		return
	var m = state.map
	var c = state.character
	tile = 24.0 if size.x > 600 else 22.0
	var world = Vector2(float(m.width), float(m.height)) * tile
	origin = size / 2.0 - (Vector2(float(c.x), float(c.y)) + Vector2(0.5, 0.5)) * tile
	origin.x = clampf(origin.x, minf(0.0, size.x - world.x), maxf(0.0, (size.x-world.x)/2))
	origin.y = clampf(origin.y, minf(0.0, size.y - world.y), maxf(0.0, (size.y-world.y)/2))
	var interior = state.room.safe or state.room.kind == "TRAINING"
	var ground = Color("604735") if interior else Color("314b3d")
	for x in range(int(m.width)):
		for y in range(int(m.height)):
			var rect = Rect2(origin + Vector2(x, y) * tile, Vector2.ONE * tile)
			if not rect.intersects(Rect2(Vector2.ZERO, size)):
				continue
			var shade = ground.lightened(0.06 * ((x * 7 + y * 11) % 3))
			draw_rect(rect, shade)
			draw_line(rect.position, rect.position + Vector2(tile, 0), shade.darkened(0.2), 1)
	for p in m.walls:
		var at = origin + Vector2(float(p[0]), float(p[1])) * tile
		draw_rect(Rect2(at, Vector2.ONE * tile), Color("776f64") if interior else Color("263b31"))
		draw_rect(Rect2(at + Vector2(2, 2), Vector2(tile-4, tile-6)), Color("a29a7c") if interior else Color("527049"))
	for d in m.get("decorations", []):
		var at = origin + (Vector2(float(d.x), float(d.y)) + Vector2(0.5,0.5)) * tile
		var color = Color("67a896") if d.kind == "crystal" else Color("9c7b4d")
		draw_rect(Rect2(at-Vector2(5,5), Vector2(10,10)), color)
	for exit in state.room.exits:
		var at = origin + Vector2(float(exit.x), float(exit.y)) * tile
		draw_rect(Rect2(at, Vector2.ONE*tile), Color("bca66d"))
		draw_line(at+Vector2(6,12),at+Vector2(18,12),Color("212d36"),3)
	if m.get("npc") != null:
		var n = m.npc
		actor(Vector2(float(n[0]),float(n[1])), Color("699ead") if state.room.id=="auction_hall" else Color("9d7eaa"), false)
	for e in m.get("enemies", []):
		if e.state != "DEAD":
			enemy(e, 1.0)
	for death in deaths.values():
		enemy(death.enemy, maxf(0.0,1.0-(elapsed-death.at)/0.7))
	for peer in peers:
		if int(peer.id)!=int(c.id):
			actor(Vector2(float(peer.x),float(peer.y)),Color("6297aa"),false)
	actor(Vector2(float(c.x), float(c.y)), Color("c3a15a"), true)

func actor(pos: Vector2, color: Color, player: bool):
	var at = origin + (pos + Vector2(0.5, 0.6)) * tile
	var bob = sin(elapsed*3.0)*0.6
	draw_rect(Rect2(at+Vector2(-6,-13+bob),Vector2(12,18)),Color("172327"))
	draw_rect(Rect2(at+Vector2(-4,-11+bob),Vector2(8,7)),Color("d8b88b"))
	draw_rect(Rect2(at+Vector2(-5,-4+bob),Vector2(10,9)),color)
	draw_rect(Rect2(at+Vector2(-5,5),Vector2(4,4)),Color("273345"))
	draw_rect(Rect2(at+Vector2(1,5),Vector2(4,4)),Color("273345"))
	if player and state.inventory.any(func(i): return i.equipped):
		draw_rect(Rect2(at+Vector2(7,-6),Vector2(2,14)),Color("d8e2df"))

func enemy(e: Dictionary, alpha: float):
	var at = origin + (Vector2(float(e.x),float(e.y)) + Vector2(0.5,0.65)) * tile
	var color = Color("75a763") if e.species == "slime" else Color("975d67")
	color.a = alpha
	draw_rect(Rect2(at+Vector2(-8,-9),Vector2(16,12)),color)
	draw_rect(Rect2(at+Vector2(-6,-13),Vector2(12,4)),color.lightened(0.15))
	draw_rect(Rect2(at+Vector2(-4,-8),Vector2(2,3)),Color(0.05,0.1,0.12,alpha))
	draw_rect(Rect2(at+Vector2(3,-8),Vector2(2,3)),Color(0.05,0.1,0.12,alpha))
	draw_string(ThemeDB.fallback_font,at+Vector2(-30,-24),e.get("category_label","Comum")+" · "+e.name,HORIZONTAL_ALIGNMENT_LEFT,-1,12,Color(e.get("name_color","#eeeeee")))
	if e.state == "IN_COMBAT":
		draw_rect(Rect2(at+Vector2(-10,-18),Vector2(20,2)),Color("412b36"))
		draw_rect(Rect2(at+Vector2(-10,-18),Vector2(20*float(e.hp)/float(e.max_hp),2)),Color("e4ae67"))

func _gui_input(event):
	var pressed = (event is InputEventMouseButton and event.button_index == MOUSE_BUTTON_LEFT and event.pressed) or (event is InputEventScreenTouch and event.pressed)
	if not pressed or state.is_empty():
		return
	var p = ((event.position-origin)/tile).floor()
	var target = {"kind":"ground", "x":int(p.x), "y":int(p.y)}
	for e in state.map.enemies:
		if e.state != "DEAD" and int(e.x)==int(p.x) and int(e.y)==int(p.y):
			target.kind="enemy"
			target.id=int(e.id)
	for exit in state.room.exits:
		if int(exit.x)==int(p.x) and int(exit.y)==int(p.y):
			target.kind="exit"
			target.id=int(exit.id)
	var npc = state.map.get("npc")
	if npc != null and int(npc[0])==int(p.x) and int(npc[1])==int(p.y):
		target.kind="npc"
	target_selected.emit(target)
	accept_event()
