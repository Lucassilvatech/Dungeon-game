# Referências obrigatórias — aparência 0.9

As quatro pranchas foram analisadas individualmente e importadas do ZIP enviado
pelo usuário. Os quatro PNG originais são cópias byte a byte, sem alterações,
com SHA256 no manifesto. Não foram substituídos por imagens geradas.

Arquivos originais organizados:

1. `01-character-body-directions-palettes.png`: aventureiro de cabelo castanho
   e lenço vermelho; aventureira ruiva de rabo de cavalo e roupa verde. Frente,
   esquerda, direita e costas; seis tons de pele, paleta de roupas e expressões.
2. `02-hair-styles-four-directions.png`: 12 cabelos em cinza, quatro direções por
   modelo; duas colunas de conjuntos em seis linhas. Cabelo curto, repartido,
   espetado, comprido, preso, ondulado e trançado. Catálogo livre para ambos os sexos.
3. `03-character-interiors-village-art-guide.png`: guerreiro, arqueira, mago,
   clériga e ladino; exemplos de animação, quarto acolhedor, forja, alquimia,
   vila, dungeon e props. É uma prancha de direção artística, não um atlas pronto.
4. `04-clothing-slots-four-directions.png`: cinco peças de cabeça, seis de torso,
   cinco de pernas e quatro de pés; quatro direções por peça, fundos/rótulos.

## Cuidados de extração

Preservar os originais e seus hashes. Não assumir que o fundo visualmente preto
é transparente antes de inspecionar o canal alpha. Fundo, rótulos e halos de
compressão não podem permanecer nos sprites. As pranchas têm escalas diferentes;
exigem âncoras comuns de cabeça, cintura e pés. A indicação 16×32–34 da prancha
artística é conceitual e não comprova a resolução nativa dos arquivos.

Não há todas as poses de caminhada, ataque e dano para cada camada. Partes
ocultas sob cabelos/roupas também não podem ser recuperadas por simples recorte.
Esses elementos precisarão de reconstrução localizada e revisão contra as fontes.
Máscaras de pele/cabelo devem preservar sombras, contornos, detalhes e cores
que pertencem a outros materiais. Sem tingimento global do personagem.

Os derivados devem ficar em `art/characters/layers`, com manifesto de origem,
retângulo de recorte, direção, âncora, máscara de cor e identificação de frames
reconstruídos. Os quatro originais foram salvos e conferidos contra o ZIP.
