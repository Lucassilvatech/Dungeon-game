# Linguagem visual Web — Dungeon Game0.9

Base verificada após fetch de todas as features: `feature/autonomous-npc-economy-0.9`,2ae4446. Era a única branch remota descendente desse HEAD. Nova branch `feature/pixel-art-visual-overhaul-0.9`; sem merge ou alterações na main/base.

## Arquitetura

`visual/themes.ts` contém perfis puros: SAFE_VILLAGE, SAFE_GUILD, COMMON_RUINS, MOSS_DUNGEON, CAVE, CRYPT, BOSS_RITUAL, SECRET_DUNGEON. Escolha usa tipos reais e temas persistidos; BOSS/SECRET têm prioridade sobre o tema de piso antigo. Perfis separam palette/ground/wall/props/vegetation/light/particle/ambient/boss pool, sem objetos Phaser.

`sprites.ts` carrega16 atlas PNG, filtros nearest, sem geração de atores em memória. `art/pixel/` guarda originais e proveniência; `scripts/build_pixel_assets.py` compila desenho pixelado original,32×32 de terreno,32×48 de atores,80 frames por ator, fontes de sombra/chama/glow e quatro bosses com arte independente. Manifestos iguais em public/ e src/ contêm SHA256 e índices. Fontes de8,2MB não vão para o cliente; os16 PNG finais somam370.894 bytes. Valores exatos atuais no manifesto.

`Environment` desenha terreno numa RenderTexture em batch **uma vez ao entrar na sala**. Camadas: terreno0, detalhe plano2, sombra/seleção1–6, props/construções/atores100+péY, atmosfera8000, luz/partícula8001/8002, labels10000. Não recria terreno/sprites por frame. Atores são mantidos por ID e posicionados por snapshots autoritativos. Copas ficam translúcidas quando ocultam o personagem. Barraca tem profundidade especial para a figura aparecer na abertura sem revelar o rosto.

Câmera usa zoom1, follow sem lerp fracionário, roundPixels; ResizeObserver muda viewport em pixels pares sem CSS FIT de960px sobre390px. Texturas nítidas, antialiasfalse, pixelArttrue, alvo60FPS. WebGL é mantido para GPU real; detecção de renderer por software prefere Canvas. Alternativa manual `?renderer=canvas|webgl`. Sem dependência nova no runtime.

## Portas, caminhos e colocação

`visual/paths.ts` identifica a entrada real adjacente à fachada por coordenadas dos exits. Para casas sem interior, escolhe apenas um ponto visual de porta; não cria saída nem endpoint. BFS conecta cada soleira à malha de caminhos caminháveis, contornando walls/prédios existentes. A arte da fachada fica alinhada com essa coordenada. Clique na área pintada da porta resolve ao **exit real existente**, com o mesmo backend/pathfinding/range de antes; o portal genérico não é desenhado diante da fachada.

`placementMask` reserva spawn estável2,2, exits/portais, NPCs, recursos, posições de combate, construções, caminhos necessários e arena central. Usa spawns persistidos quando disponíveis, não a posição errante atual, para evitar reroll decorativo por wandering. Props opcionais grandes validam o footprint completo; não criam colisão. Walls/obstáculos antigos não são apagados: um obstáculo que interrompa visualmente um caminho aparece como pedra/ilha e a rota continua por células válidas. Ground details não bloqueiam nada. Móveis fixos existentes conservam os footprints de conteúdo.

## Atores e bosses

Hero/NPCs têm delineado, roupa/sombras/detalhes de profissão; quatro direções em idle/walk/attack/hurt/death. NPCs de serviço mantêm coordenadas reais, comerciante bolsa/chapeu, alquimista frasco/chapéu, ferreiro avental/martelo, recuperação capuz sem rosto. Slime/goblin/dummy possuem arte própria; elite adiciona coroa/armadura e escala1,5, raro tem destaque discreto/cor de label.

Aparências de boss são exclusivamente visuais, não novos bosses de gameplay:

| Aparência | Uso |
|---|---|
| moss_colossus | Guardião fixo; pool de ruínas do musgo |
| thorn_chief | Procedural nas ruínas; máscara, capa, arma e armadura |
| abyssal_warden | Sentinela secreta fixa; cefaloide com máscara e tentáculos |
| basalt_drake | Pool procedural de caverna/ruínas; quadrúpede escamado |

Boss tem arte96px em célula128, escala2, presença até quatro vezes a altura do ator. Bounds visuais não mudam seleção/célula32, alcance, pathfinding, atributos ou colisão. Procedural escolhe por hash de seed+sala+spawn_key persistidos; reload não altera. Miniboss nunca usa o boss apenas ampliado.

## Luzes, ambiente e custo

Máximo12 fontes e12 partículas por sala. Quatro frames de chama com fases diferentes; glows pixelados aditivos e overlay leve. Luzes fora da câmera são ocultadas. Ambiente seguro usa vegetação/partículas leves; dungeon usa poeira, pedras úmidas, musgo, ruínas e luz quente localizada; secret/boss usa índigo, runas planas, obeliscos/cristais e luz ciano. Círculos/runas não implementam ritual. Reduced motion desliga partículas e oscilação ambiental/câmera.

Não altera gameplay, economia, estoque/produção/preço, autorização, dados ou API. Sem migration. Discord read-only; Godot preservado e congelado. Não introduz boss global, Echo, novo andar, automação do rei ou novos efeitos de poção.

Validação e evidências em [DELIVERY_PIXEL_ART_0.9](DELIVERY_PIXEL_ART_0.9.md). [Como executar localmente](PIXEL_ART_LOCAL_WINDOWS.md).
