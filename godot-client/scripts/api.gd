class_name DungeonAPI
extends Node

signal session_expired
var base_url = "http://127.0.0.1:8080/api"
var token = ""
const SESSION_PATH = "user://session.cfg"

func _ready():
	if OS.has_feature("android"):
		base_url = "" # Physical devices must configure a reachable server explicitly.
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
	if not (base_url.begins_with("https://") or base_url.begins_with("http://")) or base_url.contains(" "):
		return {"ok":false,"status":0,"data":{"detail":"Configure a URL do servidor: https://seu-servidor/api. Em aparelho físico, localhost não aponta para o computador."}}
	if OS.has_feature("android") and (base_url.contains("127.0.0.1") or base_url.contains("localhost")):
		return {"ok":false,"status":0,"data":{"detail":"No Android, informe o IP de rede do computador ou um servidor HTTPS. Emulador: http://10.0.2.2:8080/api."}}
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
		return {"ok": false, "status": 0, "data": {"detail": connection_error(int(response[0]))}}
	var parsed = JSON.parse_string(response[3].get_string_from_utf8())
	if parsed == null:
		parsed = {"detail": "Resposta inválida do servidor"}
	var status = int(response[1])
	if status >= 500:
		parsed = {"detail":"Servidor indisponível. Tente novamente em instantes."}
	elif status == 401 and not path.begins_with("/auth/"):
		parsed = {"detail":"Sessão expirada. Entre novamente."}
	elif status == 401:
		parsed = {"detail":"Conta não encontrada ou credenciais inválidas. Confira conta e senha."}
	elif status >= 400 and path == "/auth/register":
		parsed = {"detail":"Erro no cadastro: " + str(parsed.get("detail", "revise os campos informados"))}
	if status == 401 and not path.begins_with("/auth/"):
		logout()
		session_expired.emit()
	return {"ok": status >= 200 and status < 300, "status": status, "data": parsed}

func connection_error(result: int) -> String:
	match result:
		HTTPRequest.RESULT_TIMEOUT: return "Tempo limite excedido. Confira o endereço e toque em Tentar novamente."
		HTTPRequest.RESULT_TLS_HANDSHAKE_ERROR: return "Falha no certificado HTTPS. Verifique o certificado do servidor."
		HTTPRequest.RESULT_CANT_RESOLVE: return "Servidor não encontrado. Confira o endereço da API."
		HTTPRequest.RESULT_CANT_CONNECT: return "Falha de conexão. O backend precisa estar ativo e acessível nesta rede."
		_: return "Conexão interrompida. Confira a rede e tente novamente."
