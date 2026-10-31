# Entrega Web — overhaul pixel art0.9

Data:2026-10-31. Implementado e validado na branch `feature/pixel-art-visual-overhaul-0.9`, a partir de `feature/autonomous-npc-economy-0.9`, HEAD inicial **2ae4446a02d9a4507e11e57b9a6e52cae9233ef5**. Fetch de todas as features/ls-remote confirmou que era a única branch remota que continha essa evolução. Main **eab42d7e732befb04244e29d5e1615e821c5ea5e** e base preservadas; sem merge/force push.

HEAD funcional/testado **041587fd423f1886ba6ad0b9f650f7c72678fcf0**. Commit do pacote **31bdc7aac0611d959685cb43f8bbe811a2cb5f12**. Commits:6c9d7c1 diagnóstico; a48d78a arte/perfis/caminhos;22cb1cc renderer;5ad046a profundidade da barraca;041587f testes/CI;31bdc7a pacote. Documentação/evidências entregues em commit posterior. HEAD publicado final é informado na resposta de entrega e no histórico da branch.

## Implementação e arquivos

- `frontend/src/visual/{themes,appearance,placement,paths,renderer}.ts`: temas puros, aparência boss determinística, máscara, caminhos até portas, detecção de GPU por software.
- `Map.tsx`, `environment.ts`, `sprites.ts`, `style.css`, tipo readonly spawns em `api.ts`: atlas/câmera/camadas/atores/feedback/entrada/HUD. Sem alterações de backend.
- `art/pixel/source/`, `scripts/build_pixel_assets.py`, `scripts/requirements-art.txt`: três originais gerados para este projeto, pipeline de desenho pixelado/direções, nearest/alpha/paleta e16 PNG finais. **370.894 bytes** de PNG de runtime; fontes8,2MB não carregadas pelo jogo.
- Manifestos de frames/hashes em public/ e src/. `frontend/tests/visual.test.cjs`, `visual.cjs`, runner privado, compose de teste e CI atualizado. [relatório JSON](../artifacts/visual-review/validation.json) contém resultados sanitizados.

Temas implementados: SAFE_VILLAGE, SAFE_GUILD, COMMON_RUINS, MOSS_DUNGEON, CAVE, CRYPT, SECRET_DUNGEON, BOSS_RITUAL. Não são novos mapas/andares; mapeiam conteúdo real existente.

Player/NPCs:80 frames32×48 por ator, idle/walk/attack/hurt/death × quatro direções × quatro poses; roupa/silhueta/kit profissional, outline e sombras. Comerciante bolsa/chapéu; alquimista frasco/chapéu; ferreiro avental/martelo; encapuzado sem rosto visível. Bancada/forja contextuais quando a máscara permite. Slime/goblin/dummy refeitos, elites têm coroa/armadura própria, raros mantêm cor de leitura.

Bosses: **moss_colossus**, **thorn_chief**, **abyssal_warden**, **basalt_drake**; arte individual, não inimigo comum ampliado. Guardião e Sentinela têm identidade fixa; champion procedural usa seed+sala+spawn_key. Escala visual2, conteúdo96px, seleção/célula32 preservada. Sem boss global novo, Echo ou mudança de combate.

Caminhos chegam diretamente às portas dos prédios: usa exits reais quando há interior; BFS contorna walls/construções e conecta soleiras à malha existente. Fachada alinha à entrada; clique/toque na porta pintada resolve ao exit autorizado existente. Casas decorativas não ganham viagens/endpoint. Props novos não ocupam a máscara de portas/spawn/rotas/NPCs/recursos/combate; construções e colisões antigas preservadas.

Iluminação: glows pixelados aditivos limitados, tochas4 frames com fases distintas, sombra por ator, overlay discreto, até12 fontes e12 partículas. Ruínas têm pedra úmida/vegetação/pilares; arenas têm runas planas, cristais e obeliscos periféricos. Reduced motion elimina partículas/oscilação ambiental/shake. Sem shader/dependência gráfica nova.

## Testes executados

| Verificação | Resultado final |
|---|---|
| Backend completo PostgreSQL17 | **339 passed,0 failed,0 skipped,2 warnings,1003,34s** |
| Frontend `npm test` | **22 passed,0 failed,0 skipped,311,36ms** |
| `npm run build` (TypeScript+Vite) | **PASS,4,87s** |
| Chromium `visual` | **PASS** — login,5 salas reais,16 capturas,1280/1920/390px, sem overflow, bosses fixos/reload, clique na fachada desktop/mobile |
| Chromium `smoke` | **PASS** — movimento/NPC/Guilda/treino/combate/loot/reconexão/expedição/fuga/morte/recuperação/ownership |
| Chromium `npc-economy` | **PASS** — worker real, cadeia produtiva/reposição paga/lojas/preços/lotes/revisões/6 slots/admin/mobile/audit gap0 |
| Chromium `encounters` | **PASS** — grupo real, seleção, ordem/dano/round e restore por reload |
| Alembic upgrade/check | **PASS** nos bancos privados novos de cada runner; sem nova migration |
| Compose opcional de teste | `docker compose ... config --quiet` **PASS** |
| Pacote Web | CRC e hashes de todos25 arquivos estáticos **PASS** |

Backend foi **uma execução completa**, não soma de subconjuntos:

```bash
DATABASE_URL=postgresql+psycopg://tower:tower@localhost:5432/pixel_suite_3a5dee99ab TOWER_TEST_DATABASE=1 PYTHONPATH=backend .venv/bin/python -m pytest backend/tests -q
npm --prefix frontend test
npm --prefix frontend run build
# Todos os runners criam um banco novo; DATABASE_URL é um servidor privado de testes.
DATABASE_URL=postgresql+psycopg://tower:tower@localhost:5432/postgres TOWER_TEST_DATABASE=1 CHROMIUM_PATH=/usr/bin/chromium REQUIRE_CANVAS=1 .venv/bin/python scripts/test_visual_stack.py --suite visual
# Mesmo prefixo de ambiente, suites independentes smoke/npc-economy/encounters.
```

Warnings backend existentes: alias BlockingPortal/AnyIO e audioop/discord.py. Build mantém aviso conhecido do chunk Phaser acima500KB. GitHub Actions foi preparado, mas sua execução remota não foi observada. No Linux/Chromium, todos os comandos acima foram executados; Windows físico não foi executado nesta nuvem.

## Performance e revisão das referências

Captura real com Chromium headless e Canvas automático: **60FPS em cada uma das cinco salas**, mediana16,7ms, p95 entre16,7 e16,8ms,64–161 objetos, máximo12 luzes/12 partículas. [Dados brutos sanitizados](../artifacts/visual-review/performance.json). Amostra120 intervalos requestAnimationFrame por sala, após warmup; não é um teste prolongado de carga nem benchmark em celular físico.

Na revisão intermediária, WebGL SwiftShader ficou11–21FPS com outras suítes simultâneas. A detecção de renderização por software prefere Canvas, que manteve60FPS com a mesma arte. Não comparar esses números como benchmark controlado de hardware. GPU real mantém WebGL e requer validação física adicional. Terreno é renderizado em batch por entrada; não há recriação per-frame nem React por frame, nem PNG fonte de megabytes no cliente.

Comparação visual feita nas capturas reais: vila tem árvores com copa/raízes/sombras, grama variada, casas texturizadas e caminhos de pedra conectados; ruínas têm piso/paleta/props próprios, tochas e contraste legível; secret/boss usa índigo/ciano, símbolos, obeliscos e criatura dominante com anatomia própria. Respeita a direção das referências sem copiá-las. Equivalência artística exata é subjetiva; aprovação final do usuário e benchmark em GPU/celular físicos permanecem pendentes.

## Screenshots reais

Em `artifacts/visual-review/`:

- `safe-zone-desktop.png`, `safe-zone-1920.png`, `safe-zone-mobile.png`.
- `common-battle-desktop.png`, `common-battle-1920.png`, `common-battle-mobile.png`.
- `boss-room-desktop.png`, `boss-room-1920.png`, `boss-room-mobile.png`.
- `fixed-boss-desktop.png`, `fixed-boss-1920.png`, `fixed-boss-mobile.png`.
- `guild-desktop.png`, `guild-1920.png`, `guild-mobile.png`.
- `recovery-tent-desktop.png`.

Screenshots usam personagem/conta sintéticos e dados reais de servidor privado. Fixture desloca o personagem somente nesse banco para revisar cenas fixas; smoke/encounters/NPC exercitam navegação e regras reais. Não são mockups ou referências inseridas no canvas.

## Regressões encontradas e corrigidas

1. Piso intermediário com grade forte e árvores em dungeon: substituído por texturas originais/materiais e ruínas contextuais.
2. Importar manifest de public/ falhava no Vite dev: manifesto de código gerado em src/, cópia pública para inspeção/hashes.
3. Terrain drawing individual tinha custo excessivo: beginDraw/batchDrawFrame/endDraw por sala.
4. SwiftShader consumia CPU e perdia FPS: detecção automática e Canvas, sem diminuir a arte.
5. Porta genérica diante da fachada e acesso visual desalinhado: soleira real/caminho conectado/clique na fachada; testes de clique desktop/mobile.
6. Barraca ocultava o NPC por depth: figura desenhada à frente da abertura; captura revisada após correção.

## Dados, economia e plataformas

Nenhum arquivo backend, migration, `discord-bot` ou `godot-client` foi alterado. Schema7167b684d5f7 preservado. Banco operacional não acessado, volumes/.env intactos. Nenhuma reconversão, reset, alteração de lastro, estoque, preço, moeda, dívida ou progresso. Os bancos de teste/captura são independentes e retidos para diagnóstico.

**Discord remains read-only. Discord cannot control the character.**

**Windows: FROZEN. Android: FROZEN. APK: NOT REQUIRED. Windows build: NOT REQUIRED. Godot source: PRESERVED.**

## Publicação e próximos passos

[Download Web ZIP](https://raw.githubusercontent.com/Lucassilvatech/Dungeon-game/31bdc7aac0611d959685cb43f8bbe811a2cb5f12/builds/development/0.9.0-web-pixel-art-041587f/DungeonGame-Web-0.9-Pixel-Art.zip),814.305 bytes. SHA256 `edb95db53d8d9e3b957fba9a009339d0715fae7ceddbff846556e8771eb23878`. Requer backend/proxy; não é EXE/APK/offline. Integridade não é certificação antivírus.

Descrição Draft pronta em `docs/PULL_REQUEST_PIXEL_ART.md`; [compare contra a base](https://github.com/Lucassilvatech/Dungeon-game/compare/feature%2Fautonomous-npc-economy-0.9...feature%2Fpixel-art-visual-overhaul-0.9?expand=1). Nenhuma ferramenta/API de criação de PR estava disponível. Push somente na nova feature; nenhum merge automático.

Pendentes: aceite artístico do usuário, validação prolongada em GPU/celular físicos, execução dos comandos em Windows e deploy operacional pelo usuário. Boss global/Echo/novos andares/automação do rei não implementados nem antecipados.

## COMO EXECUTAR LOCALMENTE

Guia completo com comandos exatos PowerShell: [PIXEL_ART_LOCAL_WINDOWS](PIXEL_ART_LOCAL_WINDOWS.md). Inclui revisão Git, .env, backup, Docker, URLs, frontend, walkthrough de todos os serviços/cenas, testes isolados e encerramento seguro.
