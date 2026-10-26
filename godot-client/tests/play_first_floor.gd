extends SceneTree

var game
var restored
var checks = 0

func _initialize():
	call_deferred("run")

func ensure(condition: bool, message: String):
	checks += 1
	if not condition:
		push_error("FAIL: " + message)
		quit(1)

func settle():
	for i in range(400):
		await create_timer(0.05).timeout
		if not game.busy:
			return
	ensure(false,"controller command timeout")

func exit_at(x: int,y: int):
	var found=false
	for e in game.state.room.exits:
		if int(e.x)==x and int(e.y)==y:
			found=true
			await game.walk_to({"kind":"exit","x":x,"y":y,"id":int(e.id)})
			break
	ensure(found,"physical room connection exists")

func enemy(species = "slime") -> Dictionary:
	for e in game.state.map.enemies:
		if e.state=="ALIVE" and e.species==species:
			return e
	return {}

func fight(e: Dictionary,action = "attack"):
	ensure(not e.is_empty(),"living target found")
	await game.walk_to({"kind":"enemy","x":int(e.x),"y":int(e.y),"id":int(e.id)})
	ensure(game.state.get("battle")!=null,"combat starts through controller")
	for i in range(40):
		if game.state.get("battle")==null:
			return
		await game.combat(action)
	ensure(false,"combat terminates")

func run():
	var deadline=create_timer(300.0)
	deadline.timeout.connect(func(): push_error("Godot smoke timed out"); quit(2))
	game=load("res://scenes/main.tscn").instantiate()
	root.add_child(game)
	await process_frame
	game.polling.stop()
	game.api.logout()
	game.show_login()
	game.login_user.text="native"+str(int(Time.get_unix_time_from_system()))
	game.login_password.text="native-test-pass-123"
	await game.authenticate(true)
	ensure(game.creation.visible,"registered account needs character")
	game.name_input.text="Godot"+str(int(Time.get_unix_time_from_system()))
	await game.act("/character",{"name":game.name_input.text})
	ensure(game.state.room.id=="city1","character loads into city")
	var character_id=int(game.state.character.id)
	var sword=game.state.inventory[0]
	await game.act("/inventory/%d/equip" % int(sword.id),{})
	ensure(game.state.inventory[0].equipped,"equipment persists")
	game.get_viewport().gui_release_focus()
	var before_x=int(game.state.character.x)
	var key=InputEventKey.new()
	key.keycode=KEY_D
	key.pressed=true
	game._unhandled_key_input(key)
	await settle()
	ensure(int(game.state.character.x)==before_x+1,"Windows keyboard movement reaches server")
	await game.move_one(0,1)
	ensure(int(game.state.character.y)==3,"touch/D-pad one-step command reaches server")
	await exit_at(9,7)
	ensure(game.state.room.id=="guild","guild physically reachable")
	await exit_at(35,20)
	ensure(game.state.room.id=="auction_hall","dedicated auction room reachable")
	ensure(game.state.map.npc_name=="Leiloeiro da Guilda","auctioneer identity distinct from receptionist")
	await game.npc()
	ensure(game.tabs.current_tab==4,"auctioneer opens native auction interface")
	await game.act("/fast-travel",{"destination":"city1"})
	var unknown=await game.api.call_api("/fast-travel",{"destination":"combat"})
	ensure(int(unknown.status)==403,"unvisited fast travel is rejected")
	await exit_at(50,18)
	await fight(enemy())
	ensure(int(game.state.character.xp)==30,"real combat grants XP once")
	var dead=game.state.map.enemies.filter(func(e): return e.state=="DEAD")
	ensure(dead.size()==1,"defeated enemy remains dead")
	await game.act("/fast-travel",{"destination":"city1"})
	await game.act("/rest",{})
	await game.act("/fast-travel",{"destination":"common_a"})
	await fight(enemy("goblin"),"skill")
	ensure(int(game.state.character.level)==2 and int(game.state.character.unspent_attribute_points)==1,"level gain grants manual point")
	await game.act("/character/attributes",{"strength":1,"defense":0,"request_id":game.uuid()})
	ensure(int(game.state.character.strength)==6 and int(game.state.character.unspent_attribute_points)==0,"manual allocation persists")
	await game.act("/adventure",{"request_id":game.uuid()})
	ensure(game.state.expedition.status=="ACTIVE","native procedural expedition is active")
	var blocked=await game.api.call_api("/fast-travel",{"destination":"city1"})
	ensure(int(blocked.status)==409,"expedition commitment blocks shortcut")
	await fight(enemy())
	var items_before=game.state.inventory.size()
	await game.flee_preview()
	var modal=null
	for child in game.get_children():
		if child is ConfirmationDialog:
			modal=child
	ensure(modal!=null,"real flee confirmation displayed")
	modal.confirmed.emit()
	await settle()
	ensure(game.state.room.id=="city1" and int(game.state.character.xp)==0,"confirmed flee resets current XP and returns city")
	ensure(game.state.inventory.size()==items_before,"flee retains items")
	await game.act("/fast-travel",{"destination":"guild"})
	await game.npc()
	await game.act("/guild/claim",{})
	ensure(game.state.coins_exact=="15","receptionist pays reduced guild rights")
	await game.act("/fast-travel",{"destination":"city1"})
	await game.act("/adventure",{"request_id":game.uuid()})
	await fight(enemy(),"defend")
	ensure(game.state.get("death")!=null and game.state.room.id=="city1","natural procedural death returns city with receipt")
	ensure(game.state.coins_exact=="-85","medical fee creates signed debt")
	ensure(game.state.inventory.any(func(i): return i.definition=="sword"),"starter sword survives bounded death loss")
	var lost_units=0
	for item in game.state.death.items:
		lost_units+=int(item.quantity)
	ensure(lost_units<=5,"death removes at most five units")
	var api_class=load("res://scripts/api.gd")
	restored=api_class.new()
	root.add_child(restored)
	await process_frame
	ensure(not restored.token.is_empty(),"session restored from client private storage")
	var r=await restored.call_api("/state")
	ensure(r.ok and int(r.data.character.id)==character_id and r.data.death!=null,"reconnect restores same character, debt and death")
	for child in game.get_children():
		if child is AcceptDialog and child.title=="VOCÊ MORREU":
			child.confirmed.emit()
	await settle()
	game.tabs.current_tab=4
	await settle()
	await game.load_tab()
	ensure(game.current_auctions.size()==0,"new death does not create public auctions")
	game.tabs.current_tab=7
	await settle()
	await game.load_tab()
	var recovery=await game.api.call_api("/recovery")
	ensure(recovery.ok and recovery.data.is_empty(),"common loot does not become valuable recovery")
	await game.act("/fast-travel",{"destination":"guild"})
	await exit_at(2,20)
	ensure(game.state.room.id=="recovery_hall","personal recovery NPC room reachable")
	await game.npc()
	ensure(game.tabs.current_tab==7,"recovery NPC opens personal recovery panel")
	print("PASS: Godot live controller access, registration/login/session, keyboard/touch commands, first-floor combat, equipment/effective status, travel, flee, death <=5, protected sword, recovery NPC and no death auctions (",checks," checks)")
	game.queue_free()
	restored.queue_free()
	await process_frame
	quit(0)
