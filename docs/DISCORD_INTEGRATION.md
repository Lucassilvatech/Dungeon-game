# Discord 0.8

Cliente complementar do mesmo FastAPI: nenhum inventário, economia ou progresso separado. Web é o cliente principal. Comandos registrados uma vez no factory `TowerBot`, importável sem conectar ou exigir credenciais de produção.

Consultas implementadas: `/personagem`, `/status`, `/atributos`, `/inventario`, `/equipamentos`, `/localizacao`, `/mapa`, `/expedicao`, `/recompensas`, `/divida`, `/leiloes`, `/contratos`. Respostas e erros são efêmeros, menções desabilitadas, descrições limitadas. Saldo financeiro é string exata; dados privados nunca são enviados a canal público pelo cliente.

`/vincular` consome código Web de uso único (5 minutos); vínculo exclusivo por Discord. `POST /discord/unlink` autenticado permite retirar o vínculo. A chave de serviço é obrigatória para rotas do bot e permanece somente nos cabeçalhos servidor-servidor. Nunca publicar a chave nem tokens de sessão/confirmação em mensagens.

Operação inicial: `/equipar item_id equipado` apresenta prévia privada e botão com dono e prazo (120 segundos). Backend persiste recibo `DiscordOperation`, hash da confirmação, conta/personagem/Discord, item, estado anterior e resultado. Confirmação revalida vínculo, propriedade, mochila, combate e estado anterior. Personagem bloqueado serializa requisições; repetir confirmação aplicada retorna recibo sem nova mutação. Web reflete o mesmo item imediatamente. Nenhum poder ADM é oferecido.

Testado com PostgreSQL/TestClient e interações/httpx simulados: vinculação exclusiva/uso único, consultas, chave inválida, identidade, propriedade, expiração, prévia obsoleta, confirmação concorrente única, retirada do vínculo, respostas privadas e falha de API. A conexão externa, sincronização de comandos e entrega pelo Discord **não foram validadas**: não foram fornecidas credenciais reais de aplicação/bot. Executar o perfil Compose `discord` somente após configurar `DISCORD_TOKEN` e a mesma `DISCORD_SERVICE_KEY` no backend e bot.

Adiados: lances, distribuição de atributos, aceitar/resgatar contratos e pagamento da Guilda via Discord. São consultas nesta entrega; novas operações exigem a mesma disciplina de confirmação e regras de localização/finanças do backend.

Validação executada nesta etapa: `pytest tests/test_discord_08.py -xq` — 4 testes aprovados em 8,87s, incluindo sucesso privado, conexão indisponível e bloqueio do segundo clique. Limites por identidade no backend são consolidados na etapa de segurança.
