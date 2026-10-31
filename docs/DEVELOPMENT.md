# Desenvolvimento e validação

## Validação da consolidação física

Revisão atual d91e2ab604c7: executar upgrade/check somente em PostgreSQL descartável/cópia privada durante desenvolvimento. Suíte: `cd backend` e `TOWER_TEST_DATABASE=1 ../.venv/bin/python -m pytest tests -q`, DATABASE_URL explicitamente de teste. Frontend npm test/build; novo Chromium tests/physical-commerce.cjs exige TOWER_TEST_DATABASE=1 e PHYSICAL_TEST_DATABASE_URL explícitos, com API/Vite ligados à mesma base. Cenários testam desktop/390 px, troca/preços/rebalance, falta de troco dos dois lados, concorrente esgotando estoque, stale quote/preview e minério bidirecional. Scripts de navegador concedem/revogam papel temporário somente em banco privado. `scripts/simulate_guild_liquidity.py` produz LIQUIDITY_SIMULATION.json, sem mudar a meta aprovada. [Comandos/evidências](lunar/DELIVERY_PHYSICAL_COMMERCE_0.9.md).


> Atualização da continuação 0.9: [cutover operacional, migrações e validação](lunar/CUTOVER.md). O upgrade não converte o ambiente: confirmação administrativa ativa Lunar como fonte única. As descrições financeiras legadas e de conversão inativa abaixo registram a etapa anterior; após a confirmação, holdings Lunar e obrigações separadas são autoritativos. Discord segue estritamente read-only; Godot congelado.

> **Estratégia atual 0.9:** backend autoritativo, **Web como cliente principal**, **Discord estritamente read-only para gameplay**. Godot Windows/Android estão **FROZEN**; APK/EXE não são requisitos deste ciclo. Código/presets/builds e documentação histórica preservados. Ver [GODOT_FREEZE.md](GODOT_FREEZE.md) e [CONSOLIDATION_0.9.md](CONSOLIDATION_0.9.md). Descrições de equipamento confirmado via Discord abaixo são históricas e foram desativadas em 0.9.

## Fluxo atual 0.8

Use branch `feature/web-discord-first-floor-0.8`; preserve main e `godot-client`. Suba PostgreSQL e serviços com os comandos abaixo. Runtime mantém um worker até presença ter broker. Execute apenas suites sequenciais por banco: as fixtures fazem TRUNCATE; paralelismo entre suites exige bancos separados.

No Linux, na raiz: `DATABASE_URL=postgresql+psycopg://USER:PASS@localhost:5432/tower08_test TOWER_TEST_DATABASE=1 PYTHONPATH=backend .venv/bin/python -m pytest backend/tests -q`. Alternativamente rode `../.venv/bin/python -m pytest -q` dentro de backend. O usuário de teste precisa de CREATEDB para testes de migração. `alembic upgrade head` e `alembic check` devem preceder os testes.

Frontend: `npm ci && npm run build` dentro de frontend. Stack Nginx ativa: `node tests/smoke.cjs`, `session.cjs`, `encounters.cjs`, `collection.cjs`, `contracts.cjs`, `admin.cjs` e `events.cjs` (cada caminho em `tests/`). Os testes usam contas próprias persistentes. `contracts.cjs`/ADM/eventos concedem papel temporário pelo CLI e revogam em finally; somente executar no ambiente local de desenvolvimento autorizado. Contratos de teste usam reserva real e cancelamento auditado; não limpe ledger/personagens para desfazer testes.

`scripts/compare_levels_08.py` compara distribuição anterior/revisada com a mesma seed; `scripts/balance_08.py` simula perfis legais; `scripts/benchmark_08.py` mede HTTP/SQL somente em DB explicitamente descartável. Artefatos ficam em docs. Nenhum desses scripts mede conexão Discord, GPU mobile ou carga pública.

Suite funcional isola regras de jogo desabilitando limites pelo monkeypatch da fixture. `test_security_08.py` habilita e testa limites reais concorrentes; produção permanece habilitada. `test_upgrade_08.py` popula schema 0.7 e compara todos os campos antigos após upgrade, inclusive reservas/auditoria/recuperação. Cópia real preservada foi verificada adicionalmente, sem publicar dump/senhas.

Integração externa Discord e execução GitHub Actions não são presumidas a partir de testes locais. Detalhes e resultados finais em [DELIVERY_0.8.md](DELIVERY_0.8.md). Seções seguintes registram implementação histórica.

Python 3.12+, Node 22+, PostgreSQL 17. Execute no checkout existente; tarefas cloud já são isoladas e não precisam de worktrees.

## Sem containers para aplicação

Crie `.venv` na raiz, instale `backend/requirements-dev.txt` (runtime e dependências de teste do bot). Disponibilize PostgreSQL e configure `DATABASE_URL` no ambiente do terminal (não no Git). Dentro de `backend`:

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

Validação inicial na nuvem: PostgreSQL real, testes de concorrência, build TypeScript/Vite, build Docker com CA e fluxo Chromium sobre Nginx/Compose. Na validação histórica, o bot foi importado e seus cinco comandos da época foram registrados localmente; a API de vínculo/consulta foi testada. Conexão e slash commands no Discord externo continuam pendentes de credenciais. Arte procedural provisória, sem assets externos. O bundle Phaser é grande; otimização de carregamento fica para a próxima etapa.

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


## Expedições comprometidas — 0.4

A suite usa os mesmos comandos e PostgreSQL descartável. Novas verificações: nova aventura/saída/atalhos bloqueados enquanto houver inimigos, conclusão/liberação, prévia/confirmacao/staleness, fuga global 300→150, arredondamento de ímpares no total, carteira/itens/nível intactos, ganho de nível preservado, F5/login/reconexão, fuga e criação concorrentes, rollback completo, resgate reduzido inclusive individual, combate interrompido e derrota sem fuga implícita, liberdade das salas comuns e tiers independentes do jogador. Outro teste cria banco da 0.3 com procedural ativa, migra e verifica XP/carteira/baixa/pendência preservados.

O smoke Chromium mantém o trajeto cidade/Guilda/treino e agora verifica a expedição ativa, bloqueio da API/saída, F5, morte parcial, prévia com XP real, cancelar/confirmar fuga, retorno à cidade, preservação de itens/carteira/nível e nova expedição após FLED. O caminho de conclusão completa é coberto por integração no PostgreSQL. Screenshots de confirmação e resultado ficam em docs/screenshots.

Nunca use os testes contra o volume do jogo. O reinício operacional pode usar compose down/up sem -v e comparar dados persistidos, incluindo Expedition, resultados de fuga e danger_tier. Andares superiores e combate coletivo continuam fora desta entrega.

Validação final da 0.4: **58 testes passaram**, com um aviso de depreciação de TestClient. O teste direcionado de fuga durante combate também confirmou o evento COMBAT_FINISHED/fled após o ajuste de auditoria. `alembic check` não encontrou divergências; TypeScript/Vite e imagens Docker compilaram. O Chromium passou pelo fluxo real de bloqueio, F5, prévia/cancelamento/fuga e preservação de nível, carteira e itens. O ciclo operacional de down/up sem -v preservou Expedition/status/resultados, tiers, inventário, inimigos, combates, ledger e personagens. A conexão externa Discord permanece fora da validação por falta de credenciais.


## Morte, dívida, leilões e atributos — 0.5

Baseline antes de editar: **58 testes passaram**. A regra histórica de derrota que mantinha ACTIVE foi atualizada explicitamente para o novo FAILED/resgate; fuga em combate e ausência de perdas nas salas comuns/segredos continuam verificadas.

Use somente PostgreSQL descartável e a mesma flag TOWER_TEST_DATABASE=1. A suite adicional cobre saldos 500→400, 50→−50, dívida acumulada, atingir/exceder piso, mortes repetidas no piso, nível mínimo, consumo de pontos livres/dívida, pendências globais e registros pagos intactos, transferência de equipamentos/stacks/IDs, recibo persistente, concorrência e replay de morte, falha injetada com rollback completo, resgate que amortiza dívida, preço de 20%/fallback, autenticação de jogador, validação/fundos, reserva/diferença/devolução, leilão sem lances, resolução concorrente única, rollback de entrega, reentrada do mesmo item em outro leilão após outra morte, sink, saldo exato acima de 10²⁵, atribuição em lote, pontos por combate real, quitação de dívida de pontos, gasto concorrente e overflow rejeitado.

Migração 039105b3ae1a é testada a partir de bancos populados nos schemas v1, v0.3 e v0.4. O teste v0.4 conserva nível 37, força 41/defesa 5, XP, saldo, arma equipada, stack 25 e pendência 850, sem pontos retroativos, mortes ou leilões espontâneos. Confere ainda índice de custódia e rejeição de saldo abaixo de −10.000. alembic check deve permanecer sem divergências.

O smoke Chromium mantém o fluxo anterior e acrescenta distribuição manual de ponto ganho, morte natural via combate procedural, resumo persistente em F5, confirmação/cidade, dívida na UI, inventário vazio e custódia, bloqueio de lances do endividado e segundo jogador que ganha 10 moedas num combate, resgata na recepcionista e dá lance financiado pelo próprio saldo. Não usa endpoint administrativo, SQL para obter fundos ou relógio adulterado. Expiração/entrega e concorrência ficam nos testes PostgreSQL com clock de listing controlado no banco descartável. Capturas: death-summary.png, death-auctions.png, attributes.png e auction-bid.png em docs/screenshots.

O worker de vencimentos inicia no lifespan da API; testes desativam o agendamento e exercitam settle_due/resolução explicitamente. Para verificar operação, reinicie a stack sem apagar volumes e compare também DeathEvent, recibos, Auction/AuctionBid, custódia, reservas, pontos/dívidas, ledger e valores monetários. Falha de rede/Discord não deve ser confundida com validação econômica local.

Validação final: **99 testes passaram**, sem falhas ou skips (166,91s). Antes da execução completa final, os 40 testes direcionados de morte/economia também passaram, incluindo vencimento concorrente com resgate na Guilda. TypeScript/Vite, imagens Docker, alembic check e smoke Chromium passaram. Reinício Compose down/up sem -v preservou personagens, dívida, pontos, recibos, itens, custódia, lances/reservas, inimigos, expedições, ledger, Tesouro e descobertas. Permanecem o aviso de depreciação TestClient e o aviso de bundle Phaser grande; Discord externo não foi testado.

A comparação operacional com o backup pré-migração confirmou 155 registros de gameplay existentes exatamente preservados (personagens, inventário, definições antigas, inimigos, expedições, batalhas, ledger, descobertas, raids e salas); as novas colunas foram adicionadas e a variação do Tesouro correspondeu às transações auditadas criadas pelo smoke, sem reset de progresso.


## Godot, proteção e Central ADM — 0.6

Baseline: **99 testes PostgreSQL passaram** antes das mudanças. Uma primeira regressão ampliada passou com 109; a suite final acrescenta cobertura de recuperação com reservas, sessão/confirmação, XP congelado e upgrade v0.5 populado. Somente bancos descartáveis podem ser usados com TOWER_TEST_DATABASE=1; nunca rode pytest contra o volume do jogo.

Migrações v1, v0.3, v0.4 e v0.5 populadas são exercitadas. O caso v0.5 conserva espada original em custódia, leilão OPEN, maior lance/licitante, ledger, dívida/saldos, nível/XP e recibo de morte; muda só proteção e adiciona estruturas com Banco Central zerado, sem restituição/emissão indiscriminada. Os testes administrativos cobrem papéis/tokens, janela de falhas de login, emissão/retirada/transferência, créditos isolados, stale preview, replay/concorrência, rollback, recuperação/reposição, reembolso, fast travel, NPC distinto e perfis congelados.

Com Compose ativo: `CHROMIUM_PATH=/usr/bin/chromium npm run test:e2e --prefix frontend` mantém o fluxo legado e verifica espada preservada e lances de jogador com fundos conquistados. `CHROMIUM_PATH=/usr/bin/chromium node frontend/tests/admin.cjs` verifica login separado/negação de token normal, todos os módulos, prévia/confirmação/replay, emissão e retirada pareadas com reconciliação, responsividade e revogação. Este último cria conta temporária e usa CLI local no container para conceder/revogar owner; executá-lo requer acesso local ao daemon Docker. Não deixa papel de teste ativo.

Godot: importar com `godot --headless --path godot-client --editor --quit`, depois executar `tests/play_first_floor.gd` com backend/banco isolados (ver GODOT_MIGRATION.md). O teste usa o controlador real e duas contas, não injeta fundos por SQL: o segundo jogador combate, recebe da Guilda e confirma um lance na UI nativa. Diretórios XDG de teste evitam reutilizar token salvo de outra execução. O servidor isolado usa SECRET_CHANCE=0 e WANDER_INTERVAL=100000 para cenário determinístico, sem alterar o jogo real.

Build `npm run build --prefix frontend` verifica entradas game/admin. Imagens usam o overlay cloud com CA da sessão. Exportar Godot requer templates oficiais da mesma versão, texturas ETC2/ASTC habilitadas, JDK/SDK e assinatura de desenvolvimento para APK. Não desative TLS ou validação de checksums para instalar ferramentas. O workflow gera artefatos quando executado; não se confunde sua configuração com CI remoto aprovado.

Avisos anteriores de TestClient/bundle Phaser permanecem. A plataforma cloud teve falta de espaço numa repetição da suíte; somente cache de builds/imagens obsoletas foi removido, sem volumes/banco/.env, antes da nova execução. Esse resultado interrompido não é contado como aprovação. Execução Windows/dispositivo Android e conexão externa Discord permanecem não validadas. Artefatos APK/EXE são builds de desenvolvimento, separados do código versionado.

Validação final 0.6: **114 testes PostgreSQL passaram** (195,80s), com um aviso de depreciação TestClient. Godot real passou em **44 verificações** incluindo lance financiado de segundo jogador; Chromium passou no cliente legado e na Central ADM (todos os módulos, emissão/retirada pareadas, replay, reconciliação, mobile e revogação). TypeScript/Vite, imagens Docker e alembic check passaram. EXE Windows e APK Android foram gerados; pacote embutido Windows foi carregado pelo Godot Linux e assinatura APK v2/v3 foi verificada com SDK 36. Não houve execução nativa em Windows ou dispositivo Android.

Persistência operacional: comparação do backup pré-0.6 confirmou **207 registros existentes preservados**, com somente a proteção prevista e a recuperação individual auditada do item 18 como alterações intencionais; a variação do Tesouro correspondeu ao ledger dos novos fluxos de teste. Reinício Compose down/up sem -v manteve todos os registros de gameplay, custódia, lances, dívida, Banco Central, configurações/perfis e auditoria idênticos. Ao encerrar a validação: reconciliação 0, Banco Central 0 e nenhum papel administrativo temporário ativo.


## Mecânicas e distribuição 0.7

Use a mesma suíte em banco descartável: baseline 114; suite final **142 aprovados**, sem skips/falhas (239,07s). As fixtures de anúncios antigos reproduzem explicitamente custódia histórica, sem alterar a regra nova de morte em produção. Novos testes validam sequência/geração/BFS/limites/distribuição, atributos efetivos, 0–5 unidades, recuperação pessoal atômica/concurrente, confisco/marcos, não cobrar dívida duas vezes e ocultação/eventos administrativos.

Godot: `tests/play_first_floor.gd` passou com 42 verificações contra backend isolado; `tests/connection_errors.gd` verifica URL/timeout/TLS/DNS e conexão recusada. Chromium: `node frontend/tests/events.cjs` cria/cancela um evento futuro pela UI e revoga o papel temporário; requer o mesmo acesso local ao Docker do teste ADM. Nunca executar pytest contra o volume operacional.

`python scripts/build_clients.py /diretório/saída` exporta ambos os clientes e gera ZIP/instruções/hashes/manifesto. SDK/configuração e limites de validação estão em PROCEDURAL_ECONOMY_UPDATE.md. Workflows foram realmente executados: exportação remota aprovada e Windows/Defender/nuvem/inicialização headless aprovados. Não confundir inicialização headless com jogo gráfico ou execução em Android.

Smoke completo do cliente legado também passou após atualizar as expectativas de morte. Comparação de reinício manteve registros de gameplay/economia/novas tabelas exatamente iguais; zero papéis ADM temporários ao encerrar. Simulação reproduzível: `scripts/simulate_procedural.py` grava estatísticas e combates isolados em docs/procedural-combat-simulation.json.

## Consolidar e testar 0.9

Branch feature/lunar-web-discord-readonly-0.9 contém a base 0.8 e o trabalho Lunar local. No backend: requirements-dev, upgrade head (7f422c075115 recursos; 59d047e53dc8 cutover; 4a8687e5317c fundação), alembic check, pytest somente em PostgreSQL descartável. Em frontend: npm ci, npm run build, npm test, Chromium smoke e tests/lunar.cjs. O job Chromium usa banco separado e API/Vite HTTP locais; não exporta nativos. scripts/simulate_lunar.py mantém cenários fictícios isolados, não altera banco.

A consulta read-only Discord inclui testes de snapshot completo e bloqueio PostgreSQL de escrita. Rate counters são excluídos do snapshot por serem metadados de segurança. Testes API podem desabilitar limites na fixture; produção os mantém habilitados. O CI preparado não é evidência de execução remota: conferir Actions após PR/manual.


## Continuação procedural Lunar 0.9

Head procedural 7f422c075115. Testes de recursos usam PostgreSQL descartável e Chromium; flags 100% e preços de fixture são TEST_DEFAULT, nunca produção. Ver [recursos Lunares](lunar/PROCEDURAL_RESOURCES.md).
