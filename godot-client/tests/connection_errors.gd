extends SceneTree
func _initialize():
	call_deferred("run")
func run():
	var api=load("res://scripts/api.gd").new()
	root.add_child(api)
	api.base_url=""
	var missing=await api.call_api("/auth/login",{})
	assert(not missing.ok and missing.data.detail.contains("Configure"))
	assert(api.connection_error(HTTPRequest.RESULT_TIMEOUT).contains("limite"))
	assert(api.connection_error(HTTPRequest.RESULT_TLS_HANDSHAKE_ERROR).contains("certificado"))
	assert(api.connection_error(HTTPRequest.RESULT_CANT_RESOLVE).contains("encontrado"))
	api.base_url="http://127.0.0.1:1/api"
	var failed=await api.call_api("/auth/login",{})
	assert(not failed.ok and failed.status==0 and not failed.data.detail.contains("reconectar"))
	print("PASS: native URL validation, timeout/TLS/DNS messages and real connection refusal")
	api.queue_free()
	await process_frame
	quit(0)
