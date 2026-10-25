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
	ensure(game.state.inventory.size()==1 and game.state.inventory[0].definition=="sword","starter sword survives while other items go to custody")
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
	ensure(game.current_auctions.size()>=1,"native auction list includes lost physical items")
	var owned_lot=game.current_auctions[0]
	game.api.logout()
	game.show_login()
	game.login_user.text="nativebuyer"+str(int(Time.get_unix_time_from_system()))
	game.login_password.text="native-test-pass-123"
	await game.authenticate(true)
	await game.act("/character",{"name":"Buyer"+str(int(Time.get_unix_time_from_system()))})
	await game.act("/inventory/%d/equip" % int(game.state.inventory[0].id),{})
	await exit_at(50,18)
	await fight(enemy())
	await game.act("/fast-travel",{"destination":"city1"})
	await exit_at(9,7)
	await game.npc()
	await game.act("/guild/claim",{})
	ensure(game.state.coins_exact=="10","second native player earns funds through combat and receptionist")
	game.tabs.current_tab=4
	await settle()
	await game.load_tab()
	var bid_button=null
	for b in game.find_children("*","Button",true,false):
		if b.text=="Dar lance" and not b.disabled:
			bid_button=b
			break
	ensure(bid_button!=null,"funded native player has a bid control")
	bid_button.pressed.emit()
	await process_frame
	for child in game.get_children():
		if child is ConfirmationDialog and child.title=="Confirmar lance":
			child.confirmed.emit()
	await settle()
	ensure(game.state.reserved_gold==owned_lot.next_bid,"native bid confirmation reserves exact gold")
	print("PASS: Godot first-floor controller, keyboard/touch commands, city/guild/auctioneer, combat, XP/manual points, inventory/equipment, visited fast travel, committed expedition, flee preview, rewards, death/debt/protected sword, auction custody, session recovery and funded native bid confirmation (",checks," checks)")
	game.queue_free()
	restored.queue_free()
	await process_frame
	quit(0)
