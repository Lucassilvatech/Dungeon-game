# Reconstrução dos mapas 0.9

## Base verificada

Branch existente `feature/village-natural-grass-grounded-walk-0.9`, HEAD inicial
`9260f4fb82f5784cacb12d037519beb4f3133c71`. Comparados os heads de todas as
branches remotas e suas datas: esta era a mais recente em 6/11/2026.
Nenhuma nova branch remota, merge ou reescrita de histórico.

## Diagnóstico e referências

1. **Vila:** gramado orgânico oliva, pedras claras, casas largas de paredes
   creme e telhados de terracota; árvores arredondadas com tronco visível.
   A versão anterior desenhava poucos retângulos por tile em runtime e usava
   casas de outro desenho. A escala das árvores era ajustada separadamente
   da área reservada pelo planejador.
2. **Ruínas:** lajes grandes de pedra em verde azulado, juntas irregulares,
   desgaste contido, paredes em cursos horizontais, ruínas relacionadas à
   arquitetura. O piso anterior repetia a mesma moldura quadrada simplificada.
3. **Câmara secreta:** pedra índigo, ambiente ritualístico, círculo vermelho,
   obeliscos e velas. Não exige novos bosses, regras ou layouts persistentes.
4. **Personagens:** preservar cabeça quadrada, rosto pequeno, paletas e roupas.
   O compilador anterior recortava duas regiões rígidas das botas. Isso não
   representa uma caminhada articulada; os quadros e sua sincronização precisam
   ser substituídos. A animação também dependia do relógio global.

## Limites

Reconstrução exclusivamente visual da Web. Dados lógicos, navegação, colisões,
instâncias, NPCs, economia, combate, inventários e progressão continuam no backend.
Não há migração de banco, cutover, reset, mudança de gameplay ou build nativo.
Discord permanece somente leitura. A proporção 9:16 continua exclusiva da antiga
imagem de referência; o cliente continua responsivo.

## Arte

Novas fontes em `art/maps/source/`, reconstruídas com as referências anexadas
como entrada visual. Não são recortes literais das três capturas originais.
O compilador produz sprites com alpha binário e amostragem NEAREST, dimensões
de conteúdo explícitas e checksums reproduzíveis. Nenhuma imagem generativa é
apresentada como captura do jogo.

Os resultados e diferenças remanescentes estão no
[relatório de entrega](MAP_REBUILD_DELIVERY_0.9.md). As fontes geradas são insumos
de arte, separadas das capturas reais do Chromium em `artifacts/map-rebuild/`.

## Arquitetura final

| Módulo | Responsabilidade |
|---|---|
| `visual/scale.ts` | Tile de apresentação de 48 px; conversão única entre tile e pixels. |
| `visual/model.ts` | Adaptador somente leitura: dados persistentes, construções, paredes e obstáculos. |
| `visual/themes.ts` | Família visual/identidade de boss conforme tipo e seed existentes. |
| `visual/paths.ts` | Rede conectada às entradas reais; alvo da fachada resolve para a saída da API. |
| `visual/ground.ts` | Materiais em coordenadas mundiais, pavimentação contínua, contatos de parede. |
| `visual/buildings.ts` | Fachada dentro do retângulo existente, porta alinhada inclusive quando descentralizada. |
| `visual/composition.ts` | Grupos de vegetação, sítios periféricos de ruínas e suportes de parede. |
| `visual/placement.ts` | Zonas protegidas, pegada visual real, contexto de móveis e validação. |
| `visual/decoration.ts` | Sprites novos; obstáculos existentes com aparência coerente ao ambiente. |
| `visual/specialRooms.ts` | Inscrição ritual sob o boss; sem alterar encontros ou adicionar mecânicas. |
| `visual/lighting.ts` | Luzes locais suaves, até dez, com culling e redução de movimento. |
| `visual/layer.ts` | Posse e descarte de objetos/texturas por sala. |
| `visual/motion.ts` | Interpolação de velocidade constante e fase de caminhada pela distância percorrida. |
| `environment.ts` | Composição dos módulos; substitui integralmente o renderer de cenários anterior. |

`villageTerrain.ts` e `battleTerrain.ts` foram removidos, assim como os atlases
legados de tiles/cenários do diretório publicado. Recursos Lunar, ervas e minério
mantêm seus ícones; os desenhos existentes dos bosses mantêm sua identidade.

## Pipeline de arte reproduzível

```bash
python -m pip install -r scripts/requirements-art.txt
python scripts/build_pixel_assets.py
python scripts/map_art/validate.py
```

`scripts/map_art/compiler.py` compila 44 sprites com dimensões de conteúdo
explícitas em três atlases. Recortes revisados individualmente, alpha binário,
amostragem NEAREST e hashes das fontes e resultados. Materiais: grama, pedras de
caminho, lajes verdes, lajes índigo, dois tipos de parede e madeira.

A grama é uma textura de 768×768 construída por amostras da fonte, com costuras
irregulares de mínimo erro e seed fixa de versão. Não há quadrados de ruído
sobrepostos a cada célula. O resultado é produzido offline, não recalculado no
`/state` nem durante animações. As demais superfícies têm 256×256. Uma textura
de chão por sala é desenhada uma vez e descartada na transição.

`walk.py` rasteriza poses completas com joelhos, cotovelos, ombros, tronco e
apoio alternado. Cabeças e paletas vêm dos sprites aprovados; os idle de oito
identidades, nas quatro direções, são idênticos byte a byte à base `9260f4f`.
Cada atlas passa de 80 para 96 quadros: idle16, caminhada32, ataque16, dano16,
morte16. Os oito quadros de caminhada são distintos em cada direção. O pé
apoiado termina na mesma linha61 do frame48×64; a sombra fica nesse contato.

## Regras de posicionamento

- A pegada usa os pixels efetivos dos sprites, incluindo copa; não há escala
  independente aplicada depois da aprovação.
- Caminhos, portas, construções, NPCs, interações, recursos e áreas de combate
  reservadas rejeitam decoração. Não há fallback que reviva objetos rejeitados.
- Tochas/estandartes de parede também validam sua extensão completa contra
  acesso, recursos e personagens; podem tocar a parede que os sustenta.
- Mesas rejeitadas não deixam cadeiras decorativas órfãs. Obstáculos físicos
  internos aparecem como mobiliário/caixas, não como pedras de dungeon.
- Construções e balcões cuja área já é uma colisão persistente são arquitetura,
  não nova decoração. Sua representação não cria nem remove colisões.
- Recursos e atores continuam recebendo estado e ownership pela API existente.

## Expansão

Novo bioma: adicionar fonte/manifest, perfil visual e composição; reutilizar o
adaptador lógico e o validador. Não introduzir regras de jogo na camada gráfica.
Mapas diferentes continuam usando suas seeds, obstáculos e inimigos persistidos.
Não há alteração de seed, geração procedural lógica, exploração ou economia.
