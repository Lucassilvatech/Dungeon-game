# Arquitetura

Monorepo com três processos independentes e PostgreSQL 17. `frontend/src/Map.tsx` renderiza mapa e captura entrada; React apresenta menus e chama `/api`. Vite faz proxy no desenvolvimento; Nginx faz proxy na imagem de produção. Nenhum cliente envia dano, moedas ou atributos calculados.

`backend/app/main.py`: contratos HTTP e validação Pydantic. `security.py`: PBKDF2 com salt, sessões opacas com hash no banco e validade de sete dias. `game.py`: regras transacionais. `world.py`: mapa autoritativo. `models.py`: persistência SQLAlchemy; migrações Alembic congelam o schema. `seed.py`: catálogo e emissão inicial auditada, idempotente sob lock PostgreSQL.

Cada requisição abre uma transação e realiza commit apenas se terminar sem exceção. Personagens são bloqueados com SELECT FOR UPDATE antes de mutações; isso serializa ações do mesmo jogador, criação de combate e reivindicação. O turno esperado deve coincidir com o persistido. Inventário valida proprietário e custódia. Constraints impedem personagem duplicado por conta, nomes duplicados, saldo negativo, referência contábil duplicada e evento global duplicado.

O Tesouro é bloqueado depois do personagem. A vitória no chefe escreve `FLOOR_UNLOCKED` com chave `floor:2` única. Seu consumidor inicial é a projeção persistente de acesso aos andares: evento e projeção são a mesma linha, confirmados na mesma transação (`processed=true`). Não existe worker externo nesta versão. Ao integrar consumidores econômicos futuros, criar outbox e confirmações por consumidor; não usar apenas o booleano para garantir entrega externa.

`discord-bot/bot.py` é um cliente HTTP sem acesso direto ao banco. Uma chave de serviço autentica a consulta e o resgate de código, e o ID vem de `interaction.user.id`. Código aleatório, hash persistido, expiração curta, resgate com lock e vínculo único por conta/Discord impedem criar personagens separados. As respostas são privadas. A chave de serviço deve ser compartilhada de maneira segura entre bot e API; nunca expor ao navegador.

Separar novos domínios (mercado, crafting, guildas, mentoria) quando suas fatias verticais forem implementadas, sem criar serviços vazios. WebSockets e presença são futuros; o cliente atual consulta periodicamente a API. PostgreSQL é obrigatório para garantias de concorrência; SQLite não é substituto suportado.
