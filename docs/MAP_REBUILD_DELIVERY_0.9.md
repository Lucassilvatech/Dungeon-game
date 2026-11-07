# Entrega — reconstrução visual dos mapas 0.9

Implementação validada em 7/11/2026. A apresentação dos mapas foi substituída,
preservando o backend e as identidades aprovadas dos personagens. As capturas
abaixo são do jogo funcionando, não imagens geradas para representar um resultado.

## Git

- Repositório: `Lucassilvatech/Dungeon-game`.
- Comparados os heads/datas de todas as branches remotas antes das alterações.
- Branch existente mais recente: `feature/village-natural-grass-grounded-walk-0.9`.
- Base: `9260f4fb82f5784cacb12d037519beb4f3133c71`.
- Implementação: `ea2b6c0` — `feat(visual): rebuild reference map art and grounded character motion`.
- Testes/evidências: `028b254` — `test(visual): validate rebuilt maps movement and preserved gameplay`.
- Documentação: `edd6498` — `docs(visual): record map reconstruction evidence and safe local commands`.
- O HEAD final, incluindo a revisão factual do relatório, e o resultado do push são
  informados na resposta de entrega. O próprio documento não incorpora o hash
  do commit que o contém.
- `main` permaneceu em `eab42d7e732befb04244e29d5e1615e821c5ea5e` durante a validação.
- Nenhuma nova branch remota, merge, force push ou reescrita de histórico.

## O que foi reconstruído

| Área | Implementação |
|---|---|
| Vila | Grama contínua, casas creme com telhados de terracota, árvores arredondadas, plantas discretas e caminhos claros ligados às portas reais. |
| Ruínas | Novas lajes esverdeadas, paredes, colunas, pedras, vegetação e suportes de iluminação. |
| Salas especiais | Piso índigo, inscrição ritual, obeliscos, velas e luz local; identidades dos bosses preservadas. |
| Interiores | Piso de madeira, balcão, mesas, assentos e tapete; obstáculos físicos representados por mobiliário compatível. |
| Personagens | Oito poses articuladas por direção; fase pela distância percorrida, pé apoiado, sombra e profundidade por posição. |
| Arquitetura | Adaptador lógico somente leitura, materiais, construções, composição, decoração, iluminação, ciclo de vida e validação separados. |

Novas fontes em `art/maps/source`. Compilador com **44 sprites**, três atlases,
sete materiais, alpha binário, NEAREST e manifestos SHA256. Grama de 768×768
composta offline com costuras de mínimo erro; demais materiais de 256×256.
Arquivos de mapas: **706.858 bytes**; PNG de atores/bosses/recursos:
**221.993 bytes**. Isso não inclui o bundle JavaScript nem as fontes de arte.

O tile de apresentação passa a 48 px, com transformação centralizada. As
coordenadas, paredes, caminhos navegáveis e regras da API continuam em tiles.
O clique na fachada resolve para a entrada existente mesmo quando a porta
fica fora do centro da construção.

Os antigos `environment.ts` monolítico, `villageTerrain.ts`, `battleTerrain.ts`
e os atlases publicados `pixel/scenery.png`/`tiles.png` foram substituídos ou
removidos. As fontes antigas ficam arquivadas, sem alimentar os cenários atuais.
Ícones de recursos e desenhos existentes dos bosses foram preservados.

## Caminhada e posicionamento

- As poses usam joelhos, cotovelos, ombros, tronco e apoio alternado; não são
  duas partes rígidas do sprite original.
- As cabeças/paletas vêm da fonte aprovada. Os idle de oito identidades, nas
  quatro direções, foram comparados byte a byte com a base e são idênticos.
- Cada atlas tem 96 quadros. Há oito quadros distintos de caminhada por direção;
  o pé apoiado termina na linha 61 do frame de 48×64.
- Interpolação acompanha a cadência das atualizações autoritativas, evitando
  acumular atraso em rotas automáticas. Parada retorna ao idle; teleporte/reload
  não simula passos extras. A preferência de movimento reduzido é respeitada.
- Árvores reservam sua copa inteira. Portas, recursos, NPCs, caminhos e zonas
  protegidas rejeitam decoração. A copa fica translúcida ao cruzar o personagem.
- Tochas/estandartes validam toda a extensão visual. Móveis rejeitados não
  deixam cadeiras decorativas órfãs. Balcões já presentes nas colisões lógicas
  continuam visíveis sem criar novas colisões.

## Capturas reais

| Ambiente | Desktop | Mobile |
|---|---|---|
| Vila | [1920 px](../artifacts/map-rebuild/safe-zone-1920.png) | [390 px](../artifacts/map-rebuild/safe-zone-mobile.png) |
| Ruínas | [1920 px](../artifacts/map-rebuild/common-battle-1920.png) | [390 px](../artifacts/map-rebuild/common-battle-mobile.png) |
| Câmara secreta | [1920 px](../artifacts/map-rebuild/boss-room-1920.png) | [390 px](../artifacts/map-rebuild/boss-room-mobile.png) |
| Boss fixo | [1920 px](../artifacts/map-rebuild/fixed-boss-1920.png) | [390 px](../artifacts/map-rebuild/fixed-boss-mobile.png) |
| Guilda | [1920 px](../artifacts/map-rebuild/guild-1920.png) | [390 px](../artifacts/map-rebuild/guild-mobile.png) |

Também: [expedição criada pela UI](../artifacts/map-rebuild/procedural-expedition.png),
[caminhada real](../artifacts/map-rebuild/walking-in-game.png) e
[contato das poses do atlas](../artifacts/map-rebuild/walk-contact-sheet.png).
Esta última imagem é uma inspeção estática do atlas, não uma captura do jogo.

## Mecânicas e dados preservados

`backend/app`, migrations, `discord-bot` e código Godot não tiveram alterações.
Nenhuma migração nova, exclusão de dados, reset ou cutover no banco operacional.
A única alteração em `backend/tests` remove host/porta/senha fixos de um teste
histórico, usando a configuração explícita do PostgreSQL de teste; as asserções
de conservação de massa, ownership e ledger foram mantidas.

Os testes usaram PostgreSQL 17 em projeto Docker separado, porta 55439, com
bancos privados de nomes únicos. Fixtures de navegador inicializam sua própria
base vazia e nunca reutilizam um banco operacional. Não foi obtida nem alterada
uma cópia de banco real nesta etapa exclusivamente visual.

Preservados: personagens/progresso, inventário/equipamentos, economia Lunar,
comércio/NPCs, leilões, contratos, Guilda, recursos, recuperação, instâncias,
procedural persistente, inimigos/bosses/minibosses, combate, loot, administração
e transições. Backend completo e navegação real verificam esses limites.

**Discord remains read-only. Discord cannot control the character.**
Os testes de observação e bloqueio de mutações fazem parte da suíte backend.

**Windows: FROZEN. Android: FROZEN. APK: NOT REQUIRED. Windows build: NOT REQUIRED.
Godot source: PRESERVED.** Nenhum build nativo foi produzido.
A Web continua responsiva: 9:16 permanece exclusivo da referência anteriormente
solicitada, não é imposto à área jogável.

## Validação

| Verificação | Resultado |
|---|---|
| Backend completo, uma execução final | **343 passed, 0 failed, 0 skipped, 2 warnings; 767,84 s**. |
| Frontend `npm test` | **37 passed, 0 failed, 0 skipped; 797,42421 ms**. |
| `npm run build` | TypeScript + Vite passaram; **5,73 s** no build Vite. |
| Alembic em PostgreSQL descartável | `upgrade head` e `check` passaram; head `65a7c9e21b04`. |
| Layouts | 250 mapas, dez tipos, 2.458 props, **zero interseções proibidas**, portas conectadas. |
| Arte | Hashes/alpha/dimensões válidos, idle preservado, oito poses distintas/direção, apoio consistente. |
| Recompilação | 31 arquivos de runtime/manifestos idênticos por SHA256 após recompilar. |
| Chromium visual | Login, cinco ambientes reais, 1280/1920/390 px, 16 capturas, portas e corpos de NPC por clique/toque. |
| Chromium movimento | Oito movimentos por API, quatro direções, quadros distintos, retorno ao idle e reload. |
| Chromium smoke | Cidade/Guilda/treino, inventário, combate, morte, expedição, fuga, dívida médica, recuperação e isolamento de ownership. |
| Chromium NPC | Worker real, produção/estoque/caixa finitos, preços/lotes, fluxo administrativo em 390 px e audit gap 0. |
| Chromium encontros | Grupo, seleção de alvo, ordem/dano dos turnos e restauração após reload. |

Backend não é soma de subconjuntos. A execução completa inicialmente encontrou
um teste histórico com conexão fixa a `localhost:5432`; ele foi corrigido para
respeitar o servidor de teste configurado, e toda a suíte foi executada novamente.

Avisos: alias AnyIO `BlockingPortal` depreciado; `audioop` do discord.py
depreciado; Vite avisa sobre o chunk Phaser acima de 500 kB. Nenhum é ocultado
como se tivesse sido corrigido.

Amostra final de Canvas/Chromium headless: **58–60 FPS**, mediana rAF aproximadamente
16,7 ms, p95 de até 16,8 ms. É uma amostra curta virtualizada, não um benchmark
em telefone/GPU físico. Resultados e saídas estão em
[artifacts/map-rebuild](../artifacts/map-rebuild/README.md).
O workflow foi atualizado; não se afirma execução remota do GitHub Actions.

## Diferenças restantes e pendências

- Os assets novos foram reconstruídos usando as referências como entrada visual;
  não são recortes literais nem reprodução pixel a pixel. Há diferenças de
  textura, detalhe e desenho das copas/fachadas.
- A geometria persistente e os pontos de interação foram preservados. Por isso,
  posição/quantidade de casas, obstáculos, mobs e composição enquadrada diferem
  das imagens estáticas. O validador também reduz decoração perto do combate.
- Os bosses conservam as quatro ilustrações existentes. A arena e iluminação
  foram refeitas; a anatomia não foi substituída pela criatura da referência.
- Os interiores usam uma continuação visual da paleta da vila; não havia
  referência independente de interior entre as três imagens.
- As capturas mobile são de viewport 390 px em Chromium Linux. Windows físico,
  telefone físico e GPUs diferentes ainda precisam de validação local.
- Avaliação artística final pelo usuário e deploy no ambiente real permanecem
  pendentes. Nenhum novo boss, Echo ou política automática do rei foi implementado.

## Arquivos e execução local

[Arquitetura e extensão](MAP_REBUILD_0.9.md) ·
[Lista completa dos arquivos alterados](MAP_REBUILD_FILES_0.9.txt) ·
[Comandos PowerShell, Git, Docker, backup e testes isolados](MAP_REBUILD_LOCAL_WINDOWS.md).

O guia preserva `.env`, banco e volumes, usa `git pull --ff-only`, recompila as
dependências pelos Dockerfiles e oferece testes em servidor separado.
Jogo local: <http://localhost:8080>. Administração: <http://localhost:8080/admin>.
