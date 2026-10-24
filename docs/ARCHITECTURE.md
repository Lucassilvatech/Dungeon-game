# Arquitetura

Monorepo com três processos independentes e PostgreSQL 17. `frontend/src/Map.tsx` renderiza mapa e captura entrada; React apresenta menus e chama `/api`. Vite faz proxy no desenvolvimento; Nginx faz proxy na imagem de produção. Nenhum cliente envia dano, moedas ou atributos calculados.

`backend/app/main.py`: contratos HTTP e validação Pydantic. `security.py`: PBKDF2 com salt, sessões opacas com hash no banco e validade de sete dias. `game.py`: regras transacionais. `world.py`: mapa autoritativo. `models.py`: persistência SQLAlchemy; migrações Alembic congelam o schema. `seed.py`: catálogo e emissão inicial auditada, idempotente sob lock PostgreSQL.

Cada requisição abre uma transação e realiza commit apenas se terminar sem exceção. Personagens são bloqueados com SELECT FOR UPDATE antes de mutações; isso serializa ações do mesmo jogador, criação de combate e reivindicação. O turno esperado deve coincidir com o persistido. Inventário valida proprietário e custódia. Constraints impedem personagem duplicado por conta, nomes duplicados, saldo negativo, referência contábil duplicada e evento global duplicado.

O Tesouro é bloqueado depois do personagem. A vitória no chefe escreve `FLOOR_UNLOCKED` com chave `floor:2` única. Seu consumidor inicial é a projeção persistente de acesso aos andares: evento e projeção são a mesma linha, confirmados na mesma transação (`processed=true`). Não existe worker externo nesta versão. Ao integrar consumidores econômicos futuros, criar outbox e confirmações por consumidor; não usar apenas o booleano para garantir entrega externa.

`discord-bot/bot.py` é um cliente HTTP sem acesso direto ao banco. Uma chave de serviço autentica a consulta e o resgate de código, e o ID vem de `interaction.user.id`. Código aleatório, hash persistido, expiração curta, resgate com lock e vínculo único por conta/Discord impedem criar personagens separados. As respostas são privadas. A chave de serviço deve ser compartilhada de maneira segura entre bot e API; nunca expor ao navegador.

`rooms.py` define RoomType/DomainEvent, templates, grafo e projeções de descoberta. `exploration.py` executa transições, aventuras idempotentes por UUID, viagem a segredos e formação de raids. `presence.py` autentica WebSockets e consulta posições já validadas por HTTP; mensagens recebidas nunca alteram posição ou atributos. PostgreSQL continua obrigatório para locks e integridade.

O primeiro mapa foi preservado como common_a para personagens existentes; novas contas nascem em city1. A migração mantém IDs, campos econômicos e combate ativo. Migrações contêm dados congelados e não importam templates mutáveis. O seed cria apenas conteúdo ausente e conexões, sem repor Tesouro.

A presença é um registro de conexões em memória num único worker. Lê posições persistidas aproximadamente a cada 500 ms, transmite somente payload alterado e remove conexões ao desconectar. O token vai na primeira mensagem, não na URL; a sessão é revalidada a cada consulta. O frontend reconecta e limpa pares de outras salas. Para escalar a múltiplos workers, introduzir broker e presença distribuída antes de habilitar workers extras.

A câmera acompanha sprites interpolados nas cidades e enquadra salas pequenas por inteiro. Texturas geradas em `sprites.ts` têm 20 frames (idle, walk, attack, hurt, death × quatro poses). O fundo é desenhado apenas ao trocar de sala; apenas sprites e efeitos limitados atualizam a 30 FPS. Interiores e outros andares não permanecem renderizados. Nenhum asset de terceiros é necessário.

Novos domínios econômicos permanecem futuros. O lobby de raid não altera os combates individuais existentes. Eventos de domínio e projeções são confirmados na transação da ação, sem prometer entrega a sistemas externos. Ver WORLD_SYSTEM, ROOM_SYSTEM e SECRET_DUNGEONS.
