# Refinamento visual diretamente baseado nas referências

Base `feature/pixel-art-visual-overhaul-0.9`,cadbe5b. Nova branch `feature/pixel-art-cohesion-refinement-0.9`. Diagnóstico prévio em ART_REFINEMENT_DIAGNOSIS.md.

## Direção de arte

A referência do usuário tem personagens compactos de cabeça quadrada, olhos pequenos e blocos de cor limpos. A fonte final foi gerada com essa imagem como referência direta. Prévias alternativas de anime foram descartadas antes da integração. Não é uma ampliação dos personagens anteriores.

Conteúdo32×48 em frames48×64, baseado em16×24 pixels lógicos ampliados2×; três cores profissionais principais e vestuário azul/verde/roxo/marrom mantidos. Quatro direções reais da fonte,80 poses/animações derivadas. Faces/cabelo/torso/braços/botas legíveis; capuz de recuperação sem rosto, recepção acolhedora. Inimigos usam a mesma unidade gráfica. Bosses mantêm quatro artes/anatomias exclusivas e identidade procedural determinística; contexto ritualístico mais escuro e legível.

O pedido9:16 aplica-se somente à referência vertical em art/pixel/reference-village-9x16.png, conforme resposta do usuário. Nenhuma mudança para viewport Web vertical obrigatório.

O chão deixou de amostrar a textura densa anterior. Superfícies novas usam campos de cor e placas grandes com detalhes raros, caminhos arredondados e flores agrupadas. Árvores ficam em pequenos bosques; um poço no máximo e estações comerciais ganham prioridade sobre plantas decorativas. Áreas comuns usam teal/ruína com luz quente e props periféricos; secret/boss têm índigo/ciano e centros claros para combate.16 atlas PNG; fontes não carregadas no cliente.

## Posicionamento sem exceções genéricas

`buildZones` em frontend/src/visual/placement.ts identifica PATH, BUILDING_FOOTPRINT, BUILDING_INTERIOR, DOOR_ACCESS, INTERACTION_ZONE, NPC_ZONE, SPAWN_ZONE, COMBAT_ZONE, RESOURCE_ZONE, WALL, SAFE_ZONE e DECORATION_ALLOWED. Máscaras são construídas a partir dos dados reais, entradas e spawns estáveis. `planScenery` exige que **todas as células do footprint visual** estejam permitidas e livres; detalhes pequenos também são validados. Rejeita em vez de forçar colocação. Props não se sobrepõem entre si.

Removidos os bypasses anteriores: pedras desenhadas incondicionalmente para todo wall de cidade, detalhes flat que ignoravam a máscara e fallback de decoração antiga. Ambiente só instancia props aprovados. Móveis fixos de interior passam por regras próprias de contexto e acesso; tapetes são piso. Casas e a barraca de recuperação são estruturas semânticas configuradas pelo servidor, não candidatos de decoração aleatória. O NPC continua visível na abertura da barraca.

Caminhos até portas da etapa anterior permanecem: BFS contorna paredes estruturais, soleira alinha à fachada, clique/toque resolve para o exit existente. Sprites maiores podem ser selecionados pelo corpo visual; ação continua usando identidade/posição/range validados no backend. Bounds gráficos não alteram hitbox, alcance, posição ou combate.

## Reparo espacial versionado

Migration **65a7c9e21b04**, descendente de7167b684d5f7, é uma correção de dados de mapa. Retira apenas tiles de wall ligados a props aleatórios solid de CITY, dentro dos limites e fora das construções. Mantém paredes estruturais/desconhecidas, outer walls, edifícios, portas, NPCs, personagens, inimigos e recursos. Registra VISUAL_ACCESS_REPAIRED com coordenadas exatas. Não altera geometria de expedições persistidas. Novas cidades são geradas sem essas colisões aleatórias; os outros geradores não mudam sua sequência RNG/gameplay.

O downgrade conserva o reparo de acessibilidade: reintroduzir obstáculos pode prender personagens que depois tenham caminhado sobre células liberadas. Não é um rollback destrutivo de tabelas/dados. Não há reset, reconversão Lunar, criação de moeda ou ajuste de economia. Procedimento de upgrade/backup em ART_REFINEMENT_LOCAL_WINDOWS.md.

## Validação

Testes Node de personagens/direções/máscaras, auditor independente de250 templates reais em10 tipos, fluxo Chromium de jogo/NPC/combate/reconexão e migração populada. Capturas reais em artifacts/art-refinement/. A auditoria independente exige navegação conectada às soleiras, ausência de colisões/zonas proibidas em cada célula desenhada e quantidade mínima de árvores, para não resolver poluição esvaziando a vila.

Cópia privada representativa:55 tabelas/940 registros não espaciais idênticos,31 colisões decorativas retiradas em uma cidade, massa100550000mg/gap0. Históricos antigos preservados, auditoria nova acrescentada. Banco operacional não acessado. Documento de entrega registra resultados finais efetivamente executados.

Discord permanece somente observação; Godot Windows/Android congelados. Sem APK/EXE, boss global, Echo, novo andar ou nova política econômica.
