class_name DungeonAPI
extends Node

signal session_expired
var base_url = "http://127.0.0.1:8080/api"
var token = ""
const SESSION_PATH = "user://session.cfg"

func _ready():
	if OS.has_feature("android"):
		base_url = "http://10.0.2.2:8080/api"
	var config = ConfigFile.new()
	if config.load(SESSION_PATH) == OK:
		base_url = config.get_value("connection", "api_url", base_url)
		token = config.get_value("session", "token", "")
	var override = OS.get_environment("DUNGEON_API_URL")
	if not override.is_empty():
		base_url = override.trim_suffix("/")

func persist():
	var config = ConfigFile.new()
	config.set_value("connection", "api_url", base_url)
	config.set_value("session", "token", token)
	config.save(SESSION_PATH)

func logout():
	token = ""
	persist()

func call_api(path: String, body = null) -> Dictionary:
	var request = HTTPRequest.new()
	request.timeout = 15
	add_child(request)
	var headers = PackedStringArray(["Content-Type: application/json"])
	if not token.is_empty():
		headers.append("Authorization: Bearer " + token)
	var method = HTTPClient.METHOD_GET if body == null else HTTPClient.METHOD_POST
	var payload = "" if body == null else JSON.stringify(body)
	var error = request.request(base_url + path, headers, method, payload)
	if error != OK:
		request.queue_free()
		return {"ok": false, "status": 0, "data": {"detail": "Não foi possível iniciar a conexão."}}
	var response = await request.request_completed
	request.queue_free()
	if response[0] != HTTPRequest.RESULT_SUCCESS:
		return {"ok": false, "status": 0, "data": {"detail": "Conexão indisponível. Tentando reconectar…"}}
	var parsed = JSON.parse_string(response[3].get_string_from_utf8())
	if parsed == null:
		parsed = {"detail": "Resposta inválida do servidor"}
	var status = int(response[1])
	if status == 401 and not path.begins_with("/auth/"):
		logout()
		session_expired.emit()
	return {"ok": status >= 200 and status < 300, "status": status, "data": parsed}
