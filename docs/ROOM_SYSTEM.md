# Salas, transições e procedural

`GET /state` retorna sala atual, mapa atual, saídas locais e atlas conhecido. Destinos ainda não visitados têm nome genérico e identificador de conexão, não conteúdo/IDs do destino. A API não oferece listagem global das definições de sala. Conexões do atlas ligam salas conhecidas ou um destino `null` representando ?. Segredos desconhecidos ficam fora do grafo.

`POST /rooms/exits/{id}` exige origem atual, proximidade de uma casa, ausência de combate e autorização de proprietário. Cada passo via `/move` valida limites, obstáculos, prédios, NPC e monstros da sala. O cliente usa BFS apenas para sugerir o trajeto, envia passos sequenciais e interrompe em erro; não define posições finais livremente. A entrada persiste sala, andar, posição e descoberta na mesma transação. O fade visual dura 220 ms.

`POST /adventure` recebe um UUID de requisição, não recebe seed nem loot. Sob lock do personagem, uma repetição da mesma chave não cria novas salas/recompensas. O servidor escolhe o resultado com aleatoriedade segura. Um segredo já encontrado deixa de competir com a geração procedural. Há uma sala procedural persistente por personagem/andar para limitar crescimento de dados. Ela pode ser revisitada; a geração de novos layouts sob demanda é futura.

`RoomTemplate` contém grove, ruins, pond; ENEMY_SPAWN_TABLE, RESOURCE_SPAWN_TABLE e ENVIRONMENT_THEMES centralizam configuração. `template(seed)` é determinística e usa RNG local, preservando passagens. A geração armazena seed, inimigo, recurso demonstrativo, tema e dificuldade. Recursos são metadados para futura coleta; não há botão que finja coletar. O cliente não sorteia conteúdo.

`POST /raids` exige descoberta do boss; `/raids/join` usa convite aleatório e lock de raid para o limite de quatro. Lock de personagem impede entrar em múltiplos lobbies ativos. `/raids/leave` remove membro ou fecha a formação quando o líder sai. Convite e membros sobrevivem a reinício. Iniciar combate cooperativo está pendente; a interface informa isso e mantém tentativa solo explícita.

WebSocket `/ws/rooms`: autenticação por primeira mensagem `{token}`, heartbeat textual, resposta `{room_id, players:[{id,name,x,y}]}` apenas da sala atual. Posições continuam autoritativas no HTTP/PostgreSQL. Presence é temporária; posição e descobertas são permanentes. Ao reiniciar, clientes reconectam e as posições persistidas reaparecem.
