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

## Verificação da implementação 2

A suite PostgreSQL agora inclui salas, conexões, safe zones, treino sem farm, geração por seed, idempotência de Aventura, segredos sem spoilers, acesso por proprietário, derrota sem perda, primeira conclusão/repetição, raid persistente, autenticação/escopo WebSocket e migração de v1 com personagem, inventário e combate ativo. O teste de migração cria e remove um banco temporário `tower_upgrade_*`; o usuário do servidor de testes precisa de CREATEDB.

Os testes originais mantêm suas verificações de combate/economia; seus helpers agora percorrem conexões reais para chegar ao boss/NPC em salas diferentes. A resposta a um monstro que não existe na sala é 404; cidades rejeitam combate com 409.

O smoke browser percorre cidade → Guilda → treino → bosque, equipa a espada, testa cura e ausência de XP no treino, usa teclado, vence um slime, faz Aventura, recarrega e autentica um WebSocket pelo Nginx. A coleta visual de sprites é feita no navegador sem downloads de assets. O teste cria uma conta própria e não remove progresso alheio.

No PowerShell, para uma captura em lugar específico: `$env:SMOKE_SCREENSHOT = "$PWD\phase2-city.png"`; execute `npm run test:e2e` dentro de frontend após `npm ci` e `npx playwright install chromium`. Use um ambiente de desenvolvimento para esses testes, pois eles criam personagens de teste reais.

Para verificar persistência operacional, pare e suba a stack com `docker compose down` e `docker compose up -d` sem `-v`, e compare personagem, inventário, salas descobertas e raid. Reinício limpa conexões presenciais, não as posições no banco. Os clientes reconectam automaticamente.

Resultados históricos da implementação 2 (0.2): **20 testes PostgreSQL passaram**, `alembic check` sem divergências, build TypeScript/Vite e imagens Docker concluídos, fluxo Chromium completo até aviso do chefe, formação de raid e desbloqueio global passou. Um ciclo real `compose down`/`up` com o volume preservado manteve personagens, itens, descobertas/codex, raids/participantes e Tesouro idênticos. Há um aviso de depreciação da biblioteca TestClient; o bundle Phaser ainda exige otimização de tamanho. Nenhuma conexão externa Discord foi declarada validada.

## Regressão do primeiro andar 0.3

Execute a suite PostgreSQL normalmente. Ela agora cobre morte persistente/rejeição de novo combate, golpe final concorrente com XP/loot/registro únicos, stack idempotente/capacidade configurável/overflow, equipamento separado, resgate só pela recepcionista, rollback de orçamento, geração de mapas navegáveis e wandering limitado. O teste de migração também conserva equipamento/combate/saldo e consolida material legado 90+20 em 99+11. Testes históricos foram adaptados à maior distância e ao novo nível do chefe, preservando verificações de integridade; progressão a outro andar não é o foco desta suite.

O smoke Chromium agora percorre cidade/Guilda/treino/sala comum, confirma combate em quatro turnos, rejeição de morto, inventário, resgate pela recepcionista, reconexão, dois temas procedurais distintos e wandering recebido do servidor. As capturas atuais estão em docs/screenshots. Use `CHROMIUM_PATH` para Chromium instalado ou `npx playwright install chromium` fora da nuvem quando necessário.

Dimensões/densidades/temas ficam em layouts.py. Alterações em conteúdo persistido existente exigem migração; o seed não sobrescreve mapas nem renova Tesouro. `DAMAGE_MIN`, `DAMAGE_MAX`, `SKILL_BONUS`, `GUARD_BONUS` e `WANDER_INTERVAL` podem ser configurados no ambiente. Nenhum segredo deve ser commitado.

Validação da 0.3: **34 testes passaram**, com um aviso de depreciação do TestClient; `alembic check` sem divergências. TypeScript/Vite e imagens Docker compilaram. O Chromium confirmou cidade/Guilda/treino, layout mobile, quatro turnos contra slime, desaparecimento/rejeição de morto, inventário, resgate e reconexão, dois temas procedurais e wandering. Após `compose down`/`up` sem apagar volumes, personagens, stacks/definições, inimigos mortos, combates, ledger, descobertas, raids e Tesouro permaneceram idênticos.
