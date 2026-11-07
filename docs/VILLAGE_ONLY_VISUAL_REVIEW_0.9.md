# Vila do Alvorecer — revisão visual isolada (0.9)

## Escopo desta branch

Base: `feature/pixel-art-cohesion-refinement-0.9`. Mudanças restritas à apresentação da **CITY** (Vila do Alvorecer), à proteção geométrica das copas e a um teste de regressão. Não redesenhar os personagens já aprovados; não modificar sprites, dungeons, bosses, backend, moeda, inventário ou persistência.

Referência visual aprovada: gramado verde de baixa saturação com variações muito sutis, caminhos claros de pedra, árvores com copas arredondadas, casas de telhado terracota e pontos de circulação desimpedidos. Evitar hera/ramas inventadas, poços, caixas e objetos gratuitos no meio dos caminhos.

### Alterações

- `frontend/src/visual/villageTerrain.ts`: removidas placas retangulares sobrepostas sobre a grama; pequenos tufos determinísticos, sem aleatoriedade por frame. Pedras dos caminhos mantidas.
- `frontend/src/environment.ts`: árvores da CITY usam escala reduzida para se aproximarem da proporção da referência. Outras salas preservam a escala pré-existente.
- `frontend/src/visual/placement.ts`: o espaço protegido de cada árvore passa a 4×4 células, cobrindo a copa visualizada e evitando a sobreposição de ruas, portas, prédios e pontos de interação.
- `frontend/src/Map.tsx`: transição de passos e ritmo de caminhada específicos da CITY. Outras salas mantêm os tempos anteriores.
- `frontend/tests/visual.test.cjs`: teste de regressão da reserva espacial das árvores.

## Rodar no Windows (PowerShell)

Pré-requisitos: Git e Docker Desktop com Compose funcionando.

```powershell
# Dentro da pasta Dungeon-game:
git status
git fetch origin
git switch feature/village-natural-grass-grounded-walk-0.9
git pull --ff-only
if (!(Test-Path .env)) { Copy-Item .env.example .env }
docker compose up --build -d
docker compose ps
```

Abrir **http://localhost:8080** e entrar na Vila do Alvorecer. Se já há dados locais, conservar o volume Docker. Não usar `docker compose down -v`.

Para executar testes e build do frontend localmente, com Node.js e npm instalados:

```powershell
cd frontend
npm ci
npm test
npm run build
cd ..
```

Sem migração nova de banco nesta branch; o backend já existente continua sendo usado.

## Critérios de revisão visual

- Não há quadriculado artificial de placas retangulares sobrepostas na grama.
- Árvores têm proporção próxima à referência e não cobrem visualmente ruas, portas e serviços.
- Caminhos são contínuos e transitáveis.
- Sprites aprovados de jogador e NPCs permanecem inalterados, com caminhada suave na vila.
- Salas de combate, bosses e interiores não sofrem mudanças intencionais.

**Limite da entrega:** estas são correções de apresentação e colocação da vila; não constituem reprodução pixel a pixel da imagem aprovada. É necessário comparar capturas reais em 100% de zoom e aprovar ou ajustar a arte de árvores/casas antes de usar esta base em outros mapas. Testes e build ainda precisam ser executados no ambiente de desenvolvimento; commits, por si, não os validam.

## Continuação futura

Manter novas melhorias da vila sob `room.kind === "CITY"` e preferir módulos `visual/village*`. Ajustes posteriores em dungeon e boss deverão ser branches próprias derivadas de uma base revisada, nunca efeitos colaterais da renderização da vila.
