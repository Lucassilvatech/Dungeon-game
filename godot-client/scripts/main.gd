extends Control

const API = preload("res://scripts/api.gd")
const MAP = preload("res://scripts/map_view.gd")
var api
var state: Dictionary = {}
var busy = false
var root: VBoxContainer
var login_box: VBoxContainer
var game_box: VBoxContainer
var tabs: TabContainer
var notice: Label
var hud: Label
var room_label: Label
var health: ProgressBar
var energy: ProgressBar
var map_view
var login_user: LineEdit
var login_password: LineEdit
var api_url: LineEdit
var name_input: LineEdit
var creation: HBoxContainer
var displayed_death = 0
var polling: Timer
var current_auctions: Array = []
var socket = WebSocketPeer.new()
var socket_authenticated = false
var socket_retry_at = 0
var heartbeat_at = 0

func _process(_delta):
	if api==null or api.token.is_empty() or state.is_empty():
		if socket.get_ready_state()==WebSocketPeer.STATE_OPEN:
			socket.close()
		return
	var now=Time.get_ticks_msec()
	if socket.get_ready_state()==WebSocketPeer.STATE_CLOSED:
		map_view.peers=[]
		if now>=socket_retry_at:
			socket_authenticated=false
			socket_retry_at=now+2000
			var url=api.base_url.replace("https://","wss://").replace("http://","ws://")
			socket.connect_to_url(url+"/ws/rooms")
		return
	socket.poll()
	if socket.get_ready_state()==WebSocketPeer.STATE_OPEN:
		if not socket_authenticated:
			socket.send_text(JSON.stringify({"token":api.token}))
			socket_authenticated=true
		if now>=heartbeat_at:
			socket.send_text("ping")
			heartbeat_at=now+1000
		while socket.get_available_packet_count()>0:
			var payload=JSON.parse_string(socket.get_packet().get_string_from_utf8())
			if payload is Dictionary:
				map_view.peers=payload.get("players",[]) if payload.get("room_id")==state.room.id else []


func _ready():
	Engine.max_fps = 30
	var palette=Theme.new()
	palette.default_font_size=24 if OS.has_feature("android") else 18
	theme=palette
	api = API.new()
	add_child(api)
	api.session_expired.connect(show_login)
	build_ui()
	if not api.token.is_empty():
		await refresh()

func label(text: String, parent: Node, wrap = true) -> Label:
	var l = Label.new()
	l.text=text
	l.size_flags_horizontal=Control.SIZE_EXPAND_FILL
	l.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART if wrap else TextServer.AUTOWRAP_OFF
	parent.add_child(l)
	return l

func button(text: String, parent: Node, callback: Callable, blocked = false) -> Button:
	var b = Button.new()
	b.text=text
	b.custom_minimum_size=Vector2(64,64) if OS.has_feature("android") else Vector2(0,40)
	b.add_to_group("commands")
	b.set_meta("blocked",blocked)
	b.disabled=busy or blocked
	b.pressed.connect(callback)
	parent.add_child(b)
	return b

func line(placeholder: String, parent: Node, secret = false) -> LineEdit:
	var l = LineEdit.new()
	l.placeholder_text=placeholder
	l.secret=secret
	l.custom_minimum_size=Vector2(180,64 if OS.has_feature("android") else 40)
	l.size_flags_horizontal=Control.SIZE_EXPAND_FILL
	parent.add_child(l)
	return l

func row(parent: Node) -> HBoxContainer:
	var r = HBoxContainer.new()
	r.add_theme_constant_override("separation",8)
	parent.add_child(r)
	return r

func scroll_column(parent: Node) -> VBoxContainer:
	var scroll=ScrollContainer.new()
	scroll.size_flags_vertical=Control.SIZE_EXPAND_FILL
	scroll.size_flags_horizontal=Control.SIZE_EXPAND_FILL
	parent.add_child(scroll)
	var box=VBoxContainer.new()
	box.size_flags_horizontal=Control.SIZE_EXPAND_FILL
	box.add_theme_constant_override("separation",8)
	scroll.add_child(box)
	return box

func build_ui():
	var margin=MarginContainer.new()
	margin.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	for edge in ["left","top","right","bottom"]:
		margin.add_theme_constant_override("margin_"+edge,12)
	add_child(margin)
	root=VBoxContainer.new()
	root.add_theme_constant_override("separation",8)
	margin.add_child(root)
	label("DUNGEON GAME · CRÔNICAS DO ALVORECER",root)
	notice=label("Conecte-se ao mundo persistente do primeiro andar.",root)
	login_box=VBoxContainer.new()
	root.add_child(login_box)
	label("Servidor da API (HTTPS no deploy; endereço local somente no desenvolvimento)",login_box)
	api_url=line("API URL",login_box)
	api_url.text=api.base_url
	login_user=line("Conta",login_box)
	login_password=line("Senha",login_box,true)
	var auth=row(login_box)
	button("Entrar",auth,func(): authenticate(false))
	button("Criar conta",auth,func(): authenticate(true))
	creation=row(root)
	name_input=line("Nome do personagem",creation)
	button("Criar personagem",creation,func(): act("/character",{"name":name_input.text}))
	creation.hide()
	game_box=VBoxContainer.new()
	game_box.size_flags_vertical=Control.SIZE_EXPAND_FILL
	root.add_child(game_box)
	game_box.hide()
	var top=row(game_box)
	room_label=label("",top)
	room_label.size_flags_horizontal=Control.SIZE_EXPAND_FILL
	button("Atualizar",top,func(): refresh())
	button("Sair",top,func(): api.logout(); show_login())
	hud=label("",game_box)
	var meters=row(game_box)
	health=ProgressBar.new()
	health.size_flags_horizontal=Control.SIZE_EXPAND_FILL
	meters.add_child(health)
	energy=ProgressBar.new()
	energy.max_value=10
	energy.size_flags_horizontal=Control.SIZE_EXPAND_FILL
	meters.add_child(energy)
	map_view=MAP.new()
	map_view.size_flags_vertical=Control.SIZE_EXPAND_FILL
	game_box.add_child(map_view)
	map_view.target_selected.connect(walk_to)
	var controls=ScrollContainer.new()
	controls.vertical_scroll_mode=ScrollContainer.SCROLL_MODE_DISABLED
	controls.custom_minimum_size.y=72 if OS.has_feature("android") else 48
	game_box.add_child(controls)
	var actions=row(controls)
	button("↑",actions,func(): move_one(0,-1))
	button("←",actions,func(): move_one(-1,0))
	button("↓",actions,func(): move_one(0,1))
	button("→",actions,func(): move_one(1,0))
	button("Aventura",actions,func(): act("/adventure",{"request_id":uuid()}))
	button("NPC",actions,func(): npc())
	button("Descansar",actions,func(): act("/rest",{}))
	button("Fugir",actions,flee_preview)
	button("Atacar",actions,func(): combat("attack"))
	button("Golpe",actions,func(): combat("skill"))
	button("Defender",actions,func(): combat("defend"))
	tabs=TabContainer.new()
	tabs.custom_minimum_size.y=200
	tabs.size_flags_vertical=Control.SIZE_EXPAND_FILL
	game_box.add_child(tabs)
	for title in ["Personagem","Inventário","Caminhos","Guilda","Leilões","Exploração","Raid"]:
		var container=ScrollContainer.new()
		container.name=title
		container.horizontal_scroll_mode=ScrollContainer.SCROLL_MODE_DISABLED
		tabs.add_child(container)
		var column=VBoxContainer.new()
		column.size_flags_horizontal=Control.SIZE_EXPAND_FILL
		column.add_theme_constant_override("separation",8)
		container.add_child(column)
	tabs.tab_changed.connect(func(_index): load_tab())
	polling=Timer.new()
	polling.wait_time=2.0
	polling.autostart=true
	polling.timeout.connect(func():
		if not busy and not api.token.is_empty():
			refresh(false))
	add_child(polling)

func uuid() -> String:
	var hex=Crypto.new().generate_random_bytes(16).hex_encode()
	return "%s-%s-4%s-a%s-%s" % [hex.substr(0,8),hex.substr(8,4),hex.substr(13,3),hex.substr(17,3),hex.substr(20,12)]

func set_busy(value: bool):
	busy=value
	for b in get_tree().get_nodes_in_group("commands"):
		b.disabled=value or b.get_meta("blocked",false)

func show_login():
	state={}
	login_box.show()
	game_box.hide()
	creation.hide()
	notice.text="Entre para continuar; seu progresso permanece no servidor."

func authenticate(register: bool):
	if busy:
		return
	set_busy(true)
	api.base_url=api_url.text.strip_edges().trim_suffix("/")
	var response=await api.call_api("/auth/register" if register else "/auth/login",{"username":login_user.text,"password":login_password.text})
	login_password.clear()
	if response.ok:
		api.token=response.data.token
		api.persist()
		login_box.hide()
	else:
		show_error(response)
	set_busy(false)
	if response.ok:
		await refresh()

func show_error(response: Dictionary):
	var detail=response.data.get("detail","Operação rejeitada") if response.data is Dictionary else "Operação rejeitada"
	notice.text=str(detail) if detail is String else "Revise os campos informados."

func refresh(panels = true):
	if busy or api.token.is_empty():
		return
	set_busy(true)
	var response=await api.call_api("/state")
	if response.ok:
		state=response.data
		login_box.hide()
		creation.hide()
		game_box.show()
		render_state()
	elif response.status==404:
		creation.show()
		login_box.hide()
	else:
		show_error(response)
	set_busy(false)
	if response.ok and panels:
		await load_tab()

func render_state():
	var c=state.character
	room_label.text=state.room.name+" · Perigo "+str(int(state.room.danger_tier))
	hud.text="%s · Nv. %d · XP %d/%d · Vida %d · Energia %d · Ouro %s · Reservado %s" % [c.name,int(c.level),int(c.xp),int(c.level)*50,int(c.hp),int(c.energy),state.coins_exact,state.reserved_gold]
	if str(state.coins_exact).begins_with("-"):
		hud.text+=" · DÍVIDA MÉDICA ATIVA"
	health.max_value=30+(int(c.level)-1)*5
	health.value=c.hp
	energy.value=c.energy
	map_view.set_state(state)
	var expedition=state.get("expedition")
	if expedition != null:
		notice.text="Expedição %s · %d inimigos restantes" % [expedition.status,int(expedition.alive_enemies)]
	if state.get("death") != null and displayed_death != int(state.death.death_event_id):
		show_death(state.death)

func act(path: String, body = {}):
	if busy:
		return
	set_busy(true)
	var response=await api.call_api(path,body)
	if response.ok:
		if response.data is Dictionary and response.data.has("message"):
			notice.text=response.data.message
		if response.data is Dictionary and response.data.get("open_auctions",false):
			tabs.current_tab=4
	else:
		show_error(response)
	set_busy(false)
	await refresh()

func move_one(dx: int,dy: int):
	if state.is_empty() or state.get("battle") != null or state.get("death") != null:
		return
	await act("/move",{"dx":dx,"dy":dy})

func _unhandled_key_input(event):
	if event is InputEventKey and event.pressed and not event.echo and not busy:
		if get_viewport().gui_get_focus_owner() is LineEdit or get_viewport().gui_get_focus_owner() is SpinBox:
			return
		match event.keycode:
			KEY_W, KEY_UP: move_one(0,-1)
			KEY_A, KEY_LEFT: move_one(-1,0)
			KEY_S, KEY_DOWN: move_one(0,1)
			KEY_D, KEY_RIGHT: move_one(1,0)

func path_to(target: Dictionary) -> Array:
	if state.is_empty():
		return []
	var m=state.map
	var start=Vector2i(int(state.character.x),int(state.character.y))
	var goal=Vector2i(int(target.x),int(target.y))
	var adjacent=target.kind!="ground"
	var blocked={}
	for p in m.walls:
		blocked[Vector2i(int(p[0]),int(p[1]))]=true
	for e in m.enemies:
		if e.state!="DEAD":
			blocked[Vector2i(int(e.x),int(e.y))]=true
	if m.get("npc")!=null:
		blocked[Vector2i(int(m.npc[0]),int(m.npc[1]))]=true
	var queue=[start]
	var parents={start:null}
	var index=0
	while index<queue.size():
		var p=queue[index]
		index+=1
		var distance=absi(p.x-goal.x)+absi(p.y-goal.y)
		if distance<=1 if adjacent else distance==0:
			var result=[]
			while parents[p]!=null:
				result.push_front(p-parents[p])
				p=parents[p]
			return result
		for delta in [Vector2i.RIGHT,Vector2i.LEFT,Vector2i.UP,Vector2i.DOWN]:
			var next=p+delta
			if next.x<=0 or next.y<=0 or next.x>=int(m.width)-1 or next.y>=int(m.height)-1 or parents.has(next) or blocked.has(next):
				continue
			parents[next]=p
			queue.append(next)
	return []

func walk_to(target: Dictionary):
	if busy or state.is_empty() or state.get("battle")!=null or state.get("death")!=null:
		return
	if target.kind=="exit" and state.get("expedition")!=null and state.expedition.status=="ACTIVE":
		notice.text="Derrote todos os inimigos ou use a fuga explícita."
		return
	set_busy(true)
	var steps=path_to(target)
	for delta in steps:
		var response=await api.call_api("/move",{"dx":delta.x,"dy":delta.y})
		if not response.ok:
			show_error(response)
			set_busy(false)
			await refresh()
			return
		state=response.data
		render_state()
		await get_tree().create_timer(0.05).timeout
	set_busy(false)
	match target.kind:
		"enemy": await act("/battles",{"monster":str(int(target.id))})
		"exit": await act("/rooms/exits/"+str(int(target.id)),{})
		"npc": await act("/interact",{})
		_: await load_tab()

func npc():
	if state.is_empty() or state.map.get("npc")==null:
		notice.text="Não há NPC de serviço nesta sala."
		return
	await walk_to({"kind":"npc","x":int(state.map.npc[0]),"y":int(state.map.npc[1])})

func combat(action: String):
	if not state.is_empty() and state.get("battle")!=null:
		var b=state.battle
		await act("/battles/%d/action" % int(b.id),{"turn":int(b.turn),"action":action})

func dialog(title: String,text: String,callback = Callable()):
	var popup=ConfirmationDialog.new() if callback.is_valid() else AcceptDialog.new()
	popup.title=title
	popup.dialog_text=text
	popup.dialog_autowrap=true
	popup.min_size=Vector2i(320,240)
	add_child(popup)
	popup.confirmed.connect(func():
		if callback.is_valid():
			callback.call()
		popup.queue_free())
	popup.canceled.connect(func(): popup.queue_free())
	popup.popup_centered_ratio(0.72)

func flee_preview():
	if busy or state.is_empty() or state.get("expedition")==null or state.expedition.status!="ACTIVE":
		return
	set_busy(true)
	var response=await api.call_api("/expeditions/%d/flee-preview" % int(state.expedition.id))
	set_busy(false)
	if not response.ok:
		show_error(response)
		return
	var p=response.data
	dialog("FUGIR DA AVENTURA","Pendências antes: %s\nPerda: %s\nRestante: %s\nXP perdido: %s\nNível, atributos, moedas recebidas e itens permanecem." % [str(p.pending_before),str(p.reward_loss),str(p.pending_after),str(p.xp_lost)],func(): act("/expeditions/%d/flee" % int(p.expedition_id),{"confirmed":true,"confirmation_token":p.confirmation_token}))

func show_death(d: Dictionary):
	displayed_death=int(d.death_event_id)
	var text="Expedição fracassada. Resgate concluído na cidade.\nXP perdido: %d\nPendências perdidas: %s\nTaxa médica: %s\nSaldo atual: %s\nNíveis perdidos: %d\nItens enviados ao leilão:\n" % [int(d.xp_lost),d.pending_lost_exact,str(d.medical_fee),d.balance_after_exact,int(d.levels_lost)]
	for item in d.items:
		text+="%s ×%d\n" % [item.name,int(item.quantity)]
	text+="A espada inicial protegida permanece com você."
	var popup=AcceptDialog.new()
	popup.title="VOCÊ MORREU"
	popup.dialog_text=text
	popup.dialog_autowrap=true
	popup.ok_button_text="RETORNAR À CIDADE"
	add_child(popup)
	popup.confirmed.connect(func(): act("/deaths/%d/acknowledge" % int(d.death_event_id),{}); popup.queue_free())
	popup.popup_centered_ratio(0.75)

func panel() -> VBoxContainer:
	return tabs.get_child(tabs.current_tab).get_child(0)

func clear_panel():
	for node in panel().get_children():
		panel().remove_child(node)
		node.queue_free()

func load_tab():
	if busy or state.is_empty():
		return
	clear_panel()
	var box=panel()
	var c=state.character
	match tabs.current_tab:
		0:
			label("Nível %d · Força %d · Defesa %d\nPontos livres: %d · Dívida de pontos: %d\nCada novo nível quita dívida antes de conceder 1 ponto manual." % [int(c.level),int(c.strength),int(c.defense),int(c.unspent_attribute_points),int(c.attribute_point_debt)],box)
			label("Ouro disponível: "+state.coins_exact+" · Reservado: "+state.reserved_gold,box)
			if state.coins_exact.begins_with("-"):
				label("Dívida médica ativa. Pagamentos futuros compensam o saldo negativo. Cada morte ao atingir −10.000 perde até 10 níveis (mínimo 1).",box)
			var controls=row(box)
			label("Força +",controls)
			var strength=SpinBox.new()
			strength.max_value=int(c.unspent_attribute_points)
			controls.add_child(strength)
			label("Defesa +",controls)
			var defense=SpinBox.new()
			defense.max_value=int(c.unspent_attribute_points)
			controls.add_child(defense)
			button("Confirmar distribuição",box,func(): act("/character/attributes",{"strength":int(strength.value),"defense":int(defense.value),"request_id":uuid()}),int(c.unspent_attribute_points)<=0)
			button("Código para vincular Discord",box,func():
				var r=await api.call_api("/discord/code",{})
				if r.ok:
					dialog("Discord · válido por 5 minutos",r.data.code)
				else:
					show_error(r))
		1:
			for item in state.inventory:
				var r=row(box)
				label("%s ×%d%s%s\n%s" % [item.name,int(item.quantity)," · equipado" if item.equipped else ""," · protegido" if item.get("protected",false) else "",item.description],r)
				if item.kind=="weapon":
					button("Equipar",r,func(): act("/inventory/%d/equip" % int(item.id),{}),item.equipped)
		2:
			label("Caminhos físicos (preservados)",box)
			for e in state.room.exits:
				button(e.name,box,func(): walk_to({"kind":"exit","x":int(e.x),"y":int(e.y),"id":int(e.id)}))
			label("Viagem rápida · apenas locais permanentes já visitados",box)
			set_busy(true)
			var result=await api.call_api("/fast-travel")
			set_busy(false)
			if not is_instance_valid(box):
				return
			if result.ok:
				for dest in result.data:
					button(dest.name+" · Perigo "+str(int(dest.danger_tier)),box,func(): act("/fast-travel",{"destination":dest.id}),state.get("battle")!=null or (state.get("expedition")!=null and state.expedition.status=="ACTIVE"))
		3:
			label("A recepcionista paga somente por proximidade na Guilda. O leiloeiro é outro NPC no Salão de Leilões.",box)
			button("Caminhar até o NPC",box,npc)
			set_busy(true)
			var result=await api.call_api("/guild/rewards")
			set_busy(false)
			if result.ok and is_instance_valid(box):
				label("Pendências: %s moedas · %d registros" % [str(result.data.total),int(result.data.count)],box)
				for monster in result.data.groups:
					label("%s ×%d" % [monster,int(result.data.groups[monster])],box)
				button("Resgatar recompensas",box,func(): act("/guild/claim",{}),state.room.id!="guild")
		4:
			label("Espólios de morte · jogadores somente. Ouro vencedor vai ao Tesouro/sink. Prazo configurável, padrão 24h. Sem lances, item arquivado em custódia.",box)
			set_busy(true)
			var result=await api.call_api("/auctions")
			set_busy(false)
			if result.ok and is_instance_valid(box):
				current_auctions=result.data
				for a in result.data:
					render_auction(box,a)
		5:
			if state.get("expedition")!=null:
				label("Expedição "+state.expedition.status+" · restantes "+str(int(state.expedition.alive_enemies)),box)
			for e in state.map.enemies:
				if e.state!="DEAD":
					button("%s · Nv. %d · HP %d/%d" % [e.name,int(e.level),int(e.hp),int(e.max_hp)],box,func(): walk_to({"kind":"enemy","x":int(e.x),"y":int(e.y),"id":int(e.id)}))
			if state.room.kind=="TRAINING":
				button("Novo exercício sem recompensas",box,func(): act("/training/reset",{}))
			if state.room.kind=="SECRET_DUNGEON":
				button("Retornar da masmorra",box,func(): act("/dungeons/leave",{}))
			for r in state.atlas.rooms:
				if r.kind=="SECRET_DUNGEON":
					button("Ir para "+r.name,box,func(): act("/dungeons/"+r.id+"/enter",{}))
		6:
			label("Formação persistente. Combate cooperativo ainda não implementado.",box)
			if state.get("raid")!=null:
				label("Convite: "+state.raid.invite,box)
				for p in state.raid.participants:
					label(p.name,box)
				button("Sair da raid",box,func(): act("/raids/leave",{}))
			else:
				button("Criar raid",box,func(): act("/raids",{}))
				var invite=line("Convite",box)
				button("Entrar",box,func(): act("/raids/join",{"invite":invite.text}))

func render_auction(box: VBoxContainer,a: Dictionary):
	label("#%d · %s ×%d · %s\n%s\nTipo: %s · Atributos: %s\nInicial: %s · Atual: %s · Próximo: %s · Incremento mínimo: %s\nEncerramento: %s · Destino: %s" % [int(a.id),a.name,int(a.quantity),a.status,a.description,a.kind,str(a.attributes),a.opening_price,a.highest_bid,a.next_bid,a.minimum_increment,a.ends_at,a.proceeds_destination],box)
	button("Detalhes e histórico",box,func():
		var r=await api.call_api("/auctions/%d" % int(a.id))
		if r.ok:
			var text="Origem: espólio da morte #%d\nEntrega: mesmo item/stack, desequipado, ao vencedor.\n" % int(r.data.death_event_id)
			for b in r.data.bids:
				text+="Jogador %d: %s moedas · %s\n" % [int(b.bidder_id),b.amount,b.created_at]
			dialog(a.name,text)
		else:
			show_error(r))
	if a.accepts_bids:
		var bid=line("Lance inteiro em moedas",box)
		bid.text=a.next_bid
		button("Dar lance",box,func(): dialog("Confirmar lance", "Reservar "+bid.text+" moedas do saldo disponível?",func(): act("/auctions/%d/bids" % int(a.id),{"amount":bid.text,"request_id":uuid()})),state.coins_exact=="0" or state.coins_exact.begins_with("-"))
	elif a.protected:
		label("Item protegido: negociação suspensa, recuperação administrativa individual.",box)
