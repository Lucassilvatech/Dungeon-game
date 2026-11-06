# Dungeon Game — arte baseada na referência

A entrega atual é `feature/pixel-art-cohesion-refinement-0.9`. O usuário pediu personagens iguais ou muito próximos dos presentes na sua referência, rejeitando um modelo genérico de chibi/anime. A fonte final `source/reference-actors.png` foi gerada **usando diretamente a imagem enviada**: cabeças quadradas, olhos pequenos, corpos compactos, roupas simples, player azul, comerciante verde, alquimista roxo e ferreiro de avental marrom. As prévias de anime não foram integradas.

Linhas do atlas: player/comerciante/alquimista/ferreiro. Colunas: down/left/right/up. A compilação limita14 cores por sprite, normaliza16×24 pixels lógicos e amplia2× para32×48 de conteúdo em frames48×64. Isso mantém os pixels grandes e as proporções da referência.80 frames por ator: idle/walk/attack/hurt/death ×4 direções ×4 poses. Caminhada desloca botas, idle tem respiração discreta; ataque/dano/morte permanecem feedback das mecânicas existentes.

Peer utiliza a aparência púrpura da referência; recepção tem roupa burgundy acolhedora; recuperação tem capuz escuro sem rosto. Goblin usa a mesma escala/linguagem, com pele oliva e elite com armadura/chifres. Slimes têm silhueta arredondada, olhos pequenos e elite própria. Não são sprites humanos antigos apenas ampliados.

`reference-village-9x16.png` é a referência recomposta verticalmente pelo gerador de imagens. O usuário confirmou que9:16 vale **apenas para a imagem**, não para o viewport do jogo. A Web mantém desktop/mobile responsivos.

## Fontes e compilação

- `source/reference-actors.png`: fonte atual de personagens, gerada com referência direta em2026-10-31.
- `source/scenery-original.png`: casas, três árvores, poço, barraca, materiais/ruínas/props e estações. Fonte original da etapa anterior,1254×1254.
- `source/bosses-original.png`: quatro anatomias próprias (moss_colossus,thorn_chief,abyssal_warden,basalt_drake),1242×1266. Preservadas, com contexto/iluminação refinados.
- `source/terrain-original.png`: fonte anterior preservada para histórico; a amostragem ruidosa dela **não é usada** no terreno final atual.

`python scripts/build_pixel_assets.py` com Pillow12.3.0 (`scripts/requirements-art.txt`) compila16 PNG e manifestos src/public com SHA256. O PNG de terreno é desenho pixelado reproduzível: grama com campos discretos e poucos tufos, caminho de pedra arredondada, dungeon com grandes placas de baixo contraste/rachaduras raras e boss em índigo escuro. Flores/vegetação rica são grupos aprovados pelo planejador espacial, não ruído em cada célula.

Fontes ficam em art/, fora do cliente public/. Somatório de runtime e hashes exatos nos manifestos. Recompilar os arquivos versionados com a versão fixada de Pillow reproduz o resultado; regenerar imagens pelo modelo não é prometido bit a bit. Sem pacotes comerciais, sprites de outros jogos ou fontes externas sem licença.
