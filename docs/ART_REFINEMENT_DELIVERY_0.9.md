# Entrega — refinamento direto da referência0.9

Base real após fetch de todas as features: `feature/pixel-art-visual-overhaul-0.9`, **cadbe5b309fd43ef4413589293388a07db2e2be0**. Nova branch **feature/pixel-art-cohesion-refinement-0.9**. A main e a base foram preservadas, sem merge ou force push. Histórico funcional nos commits666fa70 (diagnóstico),ca820a2 (reparo espacial),403c6ce (arte de referência),07e4817 (zonas/composição),7f55498 (auditorias/integração), com correção posterior da classificação de móveis e pacote final. HEAD final publicado é informado na resposta de entrega/histórico.

## O que mudou

Os personagens finais foram reconstruídos usando **diretamente os personagens da imagem enviada pelo usuário**: cabeça quadrada, olhos pequenos, torso compacto, braços/pernas distinguíveis e cores azul/verde/roxo/marrom. O modelo alternativo de anime foi descartado e não foi integrado. Fonte em art/pixel/source/reference-actors.png; down/left/right/up por personagem.16×24 pixels lógicos ampliados2×, conteúdo32×48 em frames48×64,80 frames derivados para idle/walk/attack/hurt/death. Genéricos, recepção, recuperação e inimigos seguem essa unidade; capuz sem rosto, elites identificáveis. Bosses mantêm quatro artes/anatomias próprias e aparência determinística.

A referência9:16 foi gerada como imagem vertical em art/pixel/reference-village-9x16.png. O usuário confirmou que a proporção vale **somente para a referência**; o jogo continua responsivo desktop/mobile.

Terreno redesenhado: grama limpa com variações discretas, pedra arredondada nos caminhos, placas de baixa frequência em ruínas, secret/boss mais escuros e ritualísticos. Árvores em bosques e flores agrupadas, poço único quando possível, prioridade para estações dos serviços. Luzes locais e sombras ficam legíveis;10 fontes/6 partículas no máximo. Renderer/câmera/autoridade backend anteriores reutilizados. Sem novas mecânicas, economia ou conteúdo de andares.

## Objetos nos lugares corretos

`buildZones/planScenery` identifica PATH, BUILDING_FOOTPRINT/INTERIOR, DOOR_ACCESS, INTERACTION_ZONE, NPC_ZONE, SPAWN_ZONE, COMBAT_ZONE, RESOURCE_ZONE, WALL, SAFE_ZONE e DECORATION_ALLOWED. Toda célula do footprint precisa estar permitida, inclusive a projeção das copas/props altos. Sem bypass para pedra/caixa/barril ou detalhes flat. Dúvida de colocação resulta em rejeição, não em prop forçado. Props não se sobrepõem entre si.

Móveis internos precisam ter footprint planejado, assento junto a mesa/balcão ou posição de parede coerente; nomes de objeto por si só não aprovam uma cadeira/estante aleatória no meio do salão. Móveis aprovados também respeitam acesso, NPCs/recursos/combate. Tapetes são piso; casas e a barraca são estruturas semânticas configuradas, não decoração sorteada.

Caminhos continuam diretamente ligados às portas reais. Clique/toque na fachada ou no corpo visível de um NPC resolve à identidade/posição real da API. Alcance, colisões e resultado de ação seguem autoritativos no servidor. Sprites maiores não ampliam hitbox/range.

## Migração e preservação

**65a7c9e21b04**, descendente de7167b684d5f7, é incremental e altera somente dados espaciais. Retira tiles de colisão de props aleatórios solid de CITY que não sejam estruturas, limites externos ou paredes desconhecidas. Marca o prop como visual e registra VISUAL_ACCESS_REPAIRED com a lista exata. Não move personagem/NPC/porta, não refaz salas procedurais persistidas e não altera lastro, moedas, dívidas, itens, equipamentos, leilões, contratos, progresso ou permissões.

Downgrade conserva o reparo: recolocar obstáculos poderia prender jogadores em células posteriormente liberadas. Nenhuma tabela/volume/banco é excluído. Novas cidades não geram esses obstáculos aleatórios; RNG/gameplay das outras regiões preservados.

Validação em cópia privada representativa, sem acesso ao banco operacional: **55 tabelas e940 registros não espaciais idênticos por hashes**,31 colisões decorativas retiradas em uma cidade; somente a alteração espacial esperada e o novo evento de auditoria. Massa100550000mg, **audit gap0**, sem divergência de ledger/metadados. [Evidência](../artifacts/art-refinement/private-copy-validation.json).

O teste histórico0.7→head foi atualizado para conservar cada linha antiga e validar precisamente o novo recibo/remoções, em vez de exigir ausência de qualquer novo evento. A primeira execução completa detectou essa expectativa desatualizada; o recheck de migração passou e uma execução integral posterior foi realizada. Resultado final abaixo é de uma execução completa, não soma de subconjuntos.

## Testes executados

- Backend PostgreSQL17, suíte **completa em uma execução**: **343 passed,0 failed,0 skipped,2 warnings,714,45s (11min54s)**.

- Frontend `npm test`: **26 passed,0 failed,0 skipped,734,95ms**.
- TypeScript+Vite `npm run build`: **PASS,4,83s**.
- Auditor independente: **250 mapas reais/10 tipos,2027 props,0 interseções proibidas**, todas as soleiras conectadas à malha; preserva bosques mínimos para não solucionar ruído deixando a vila vazia. [JSON](../artifacts/art-refinement/placement-audit.json).
- Chromium `visual`: **PASS** — login,5 cenas reais,16 capturas,1280×720/1920×1080/390px, bosses/reload, entrada na fachada e clique/toque real no corpo do comerciante em desktop/mobile, sem overflow/erro JS.
- Chromium `smoke`: **PASS** — movimento, Guilda/treino, combate, inventário/recompensas, reconexão, expedição, fuga/morte/recuperação e ownership.
- Chromium `npc-economy`: **PASS** — worker, produção/reposição com caixa real, lojas/estoque/lotes/preços/revisões/admin, seis slots,390px e audit gap0.
- Chromium `encounters`: **PASS** — grupo/seleção, ordem/dano/round e restore após reload.
- `alembic upgrade head`/`alembic check`: **PASS** nos bancos privados e na cópia representativa.
- Pipeline recompilada com Pillow fixado: PNG/manifestos reproduzidos, hashes verificados. Pacote final com CRC e SHA256 dos25 arquivos estáticos verificados.

Comandos efetivamente usados incluem `PYTHONPATH=backend .venv/bin/python -m pytest backend/tests -q` com DATABASE_URL privada/TOWER_TEST_DATABASE=1, `npm --prefix frontend test`, `npm --prefix frontend run build`, `scripts/test_visual_stack.py --suite visual|smoke|npc-economy|encounters`, export_visual_layout_fixtures.py e placement-audit.cjs. O runner cria outro banco UUID; não limpa o banco de origem. Windows físico não foi executado nesta nuvem.

Warnings backend existentes: BlockingPortal/AnyIO e audioop/discord.py. Build mantém aviso conhecido do chunk Phaser acima500KB. CI foi atualizado para recompilar arte, auditar templates e capturar cenas; execução remota de Actions não foi observada.

## Comparação e performance

As capturas foram abertas e revisadas. Personagens finais seguem proporções/silhueta/cores da referência, com pixels definidos; chão perdeu o grão aleatório e recuperou áreas de descanso; caminhos estão livres de props e conectados às portas. Vila clara/quente, combate teal e boss/secret índigo/ciano permanecem distintos. Chefes são maiores e têm anatomia/arte diferente dos mobs; centros de combate legíveis. Aceite artístico final é do usuário; não afirmar equivalência estética objetiva com uma imagem comercial.

Amostra real Chromium/Canvas:60FPS nas cinco cenas, mediana16,7ms, p95 até16,8ms, sem erro JS.120 intervalos por cena após warmup; não é benchmark prolongado nem teste físico de GPU/celular. Fontes de megabytes não carregam no cliente; terreno é batch por sala e atores reaproveitados. [Métricas](../artifacts/art-refinement/performance.json).

## Capturas e arquivos

`artifacts/art-refinement/` contém safe-zone,common-battle,boss-room,fixed-boss,guild em versõesdesktop/1920/mobile, além de recovery-tent-desktop:16 capturas reais de conta sintética/banco privado. A fixture visual posiciona o personagem somente no banco descartável; os outros roteiros exercitam gameplay/navegação reais. A pasta artifacts/visual-review da entrega anterior foi preservada para comparação.

Arquivos principais: scripts/build_pixel_assets.py, art/pixel/source/reference-actors.png,16 PNG e manifestos; frontend/src/visual/{placement,appearance,themes}.ts, environment.ts, Map.tsx e sprites.ts; backend/app/{layouts,visual_access}.py, migration65a7c9e21b04 e testes de upgrade; testes frontend/runner/CI, auditor de templates e documentação operacional.

## Plataformas e publicação

Discord permanece read-only e não controla personagem. Windows/Android Godot FROZEN, APK/EXE não gerados; fontes Godot preservadas. Nada de boss global, Echo, novo andar, política do rei ou nova economia.

[Baixar Web ZIP](https://raw.githubusercontent.com/Lucassilvatech/Dungeon-game/65fe31e11e58e58d06c9332363e21802d496805d/builds/development/0.9.0-web-art-refinement-7bcbde1/DungeonGame-Web-0.9-Art-Refinement.zip),721789 bytes. SHA256 `7e04e5363014f723f3e7ec0574581f12e4c3c3fff7152940c8d8cb0ff3295998`. Fonte funcional/testada **7bcbde1b31d863e447b0399f394f84c0d7eabaa6**, commit do pacote **65fe31e11e58e58d06c9332363e21802d496805d**. Requer backend/schema65a7c9e21b04 e proxy/API; não é EXE/APK/jogo offline. CRC e hashes verificam integridade, não certificação antivírus.

Descrição Draft em PULL_REQUEST_ART_REFINEMENT.md; compare contra `feature/pixel-art-visual-overhaul-0.9`. Não havia ferramenta/API de criação de PR; preparar descrição/compare não significa PR criado. Push apenas na nova feature, sem merge.

Pendentes: aceite artístico do usuário, benchmark/execução física em GPU/celular/Windows, execução remota do CI e deploy operacional pelo usuário. Não avançar automaticamente para outra fase.

## COMO EXECUTAR LOCALMENTE

[Guia completo PowerShell](ART_REFINEMENT_LOCAL_WINDOWS.md), com revisão Git, preservação do.env, backup, rebuild, upgrade automático antes da API, validação do head65a7c9e21b04/audit, URLs, frontend fora do Docker, testes isolados e encerramento seguro. Sem exclusão de volumes ou reconversão monetária.
