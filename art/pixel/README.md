# Dungeon Game — personagens aprovados e arquivos históricos

A implementação atual está na branch existente
`feature/village-natural-grass-grounded-walk-0.9`. O usuário pediu personagens
iguais ou muito próximos da referência, rejeitando um modelo genérico de anime.
`source/reference-actors.png` continua sendo a fonte: cabeças quadradas, olhos
pequenos, roupas simples; player azul, comerciante verde, alquimista roxo e
ferreiro de avental marrom. As prévias de anime não foram integradas.

## Personagens e animações atuais

Linhas da fonte: player/comerciante/alquimista/ferreiro. Colunas:
down/left/right/up. A compilação mantém a identidade de 16×24 pixels lógicos,
amostragem NEAREST 2× e frames de 48×64. A caminhada foi reconstruída em
`scripts/map_art/walk.py`: oito poses por direção com joelhos, cotovelos, tronco,
ombros e apoio alternado. Não recorta duas metades rígidas do sprite.

Os atlases agora têm **96 quadros**: idle16, walk32, attack16, hurt16, death16.
A fase acompanha a distância real percorrida. Os idle das oito identidades
principais, nas quatro direções, são idênticos byte a byte à base `9260f4f`.
Verificação: `python scripts/map_art/validate.py`.

Peer preserva roupa púrpura; recepção, burgundy; recuperação, capuz escuro.
Goblin e elite preservam escala, pele oliva e armadura/chifres. Slimes mantêm
silhueta arredondada e identidade própria. Os quatro bosses continuam usando
`source/bosses-original.png`; esta entrega reconstrói seus ambientes.

`reference-village-9x16.png` é uma referência recomposta pelo gerador de imagens.
O usuário confirmou que 9:16 vale **apenas para a referência**, não para o
viewport da Web, que continua responsivo.

## Cenários substituídos

Os mapas agora usam as fontes novas de [art/maps](../maps/README.md).
`source/scenery-original.png` e `source/terrain-original.png` permanecem como
histórico, mas não são entradas do renderer/compilador atual de cenários.
Os antigos `public/assets/pixel/scenery.png` e `tiles.png` foram removidos.

`python scripts/build_pixel_assets.py`, com Pillow fixado em
`scripts/requirements-art.txt`, produz 14 PNG de atores/bosses/recursos e os
novos atlases/materiais de mapas. Manifestos SHA256 acompanham os resultados.
As fontes ficam fora de `public/`. Compilar as fontes versionadas é reproduzível;
regenerar imagens pelo modelo não é prometido bit a bit.

Arquitetura: [reconstrução dos mapas](../../docs/MAP_REBUILD_0.9.md).
Evidências e limitações: [relatório](../../docs/MAP_REBUILD_DELIVERY_0.9.md).
