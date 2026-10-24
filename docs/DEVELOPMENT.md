# Desenvolvimento e validação

Python 3.12+, Node 22+, PostgreSQL 17. Execute no checkout existente; tarefas cloud já são isoladas e não precisam de worktrees.

## Sem containers para aplicação

Crie `.venv` na raiz, instale `backend/requirements.txt` e `discord-bot/requirements.txt`. Disponibilize PostgreSQL e configure `DATABASE_URL` no ambiente do terminal (não no Git). Dentro de `backend`:

```powershell
..\.venv\Scripts\alembic upgrade head
..\.venv\Scripts\python -m app.seed
..\.venv\Scripts\uvicorn app.main:app --reload
```

Em outro terminal, dentro de `frontend`: `npm ci`, `npm run dev`. Abra a porta indicada pelo Vite. `npm run build` verifica TypeScript e gera produção. O proxy padrão aponta para API na porta 8000. Para bot: defina `API_URL`, `DISCORD_SERVICE_KEY`, `DISCORD_TOKEN` e execute `python discord-bot/bot.py` na raiz com a venv ativa.

## Testes PostgreSQL (banco descartável!)

Os testes fazem TRUNCATE. Nunca aponte para banco com progresso real. Crie `tower_test` em PostgreSQL com credenciais locais. No PowerShell, dentro de `backend`:

```powershell
$env:DATABASE_URL = "postgresql+psycopg://tower:tower@localhost:5432/tower_test"
$env:TOWER_TEST_DATABASE = "1"
..\.venv\Scripts\alembic upgrade head
..\.venv\Scripts\python -m pytest -q
```

No Linux, use `../.venv/bin/python` / `../.venv/bin/alembic` e variáveis prefixadas ao comando. A suite exige PostgreSQL por testar locks e concorrência. Cobertura: conta e personagem único/persistente; movimento/colisão; combate/replay; inventário; ownership; concorrência de turnos e pagamentos; conservação monetária e rollback; chefe/progressão/portal global; código Discord de uso único e consulta real.

## Cloud

Cache npm pode usar `--cache /tmp/tower-npm` quando HOME é somente leitura. Builds Docker precisam da CA da sessão: `BUILDX_CONFIG=/tmp/tower-buildx docker compose -f docker-compose.yml -f infrastructure/compose.cloud.yml build` com `CODEX_PROXY_CERT` já fornecida. O overlay monta a CA somente durante downloads e preserva verificação TLS. Não copiar CA nem credenciais para imagens.

PostgreSQL local pode ser iniciado com `docker run -d --name tower-postgres -e POSTGRES_DB=tower -e POSTGRES_USER=tower -e POSTGRES_PASSWORD=tower -p 127.0.0.1:5432:5432 postgres:17-alpine`. Verifique com `pg_isready`, rode migração/seed, inicie API e Vite e consulte `/api/health`. Processos devem ser reiniciados após restauração; volumes de banco devem ser preservados.

## Smoke test no navegador

Com a stack Compose ativa, dentro de `frontend`:

```powershell
npm ci
npx playwright install chromium
npm run test:e2e
```

`BASE_URL` muda o destino (padrão porta 8080); `CHROMIUM_PATH` permite usar Chromium já instalado; `SMOKE_SCREENSHOT` define onde salvar a captura (padrão: `tower-smoke.png` na pasta temporária do sistema). O teste cria uma conta de teste real e não apaga seu registro. Ele cobre criação, mapa Phaser, equipamento, teclado, combate, loot e persistência ao recarregar.

Validação inicial na nuvem: PostgreSQL real, testes de concorrência, build TypeScript/Vite, build Docker com CA e fluxo Chromium sobre Nginx/Compose. O bot foi importado e seus cinco comandos foram registrados localmente; a API de vínculo/consulta foi testada. Conexão e slash commands no Discord externo continuam pendentes de credenciais. Arte procedural provisória, sem assets externos. O bundle Phaser é grande; otimização de carregamento fica para a próxima etapa.
