# Camadas derivadas das referências

Os originais intactos ficam em `../references`. Estes PNGs são adaptações:

- `body-occlusion-reconstruction-source.png`: partes do corpo/couro cabeludo
  ocultas nos personagens completos, reconstruídas com as proporções fornecidas.
- `clothing-head-repaired.png`: cinco acessórios, quatro vistas, alpha limpo.
- `clothing-torso-repaired.png`: seis roupas, quatro vistas, cores originais.
- `clothing-legs-repaired.png`: cinco opções de pernas, quatro vistas.
- `clothing-feet-repaired.png`: quatro calçados, com pares, perfis e calcanhares.
- `light-greaves-back-repaired.png`: correção localizada dos fechos traseiros,
  substituindo somente essa vista, sem joelheiras frontais no verso.

`provenance.json` identifica as fontes obrigatórias, a finalidade e os hashes.
As roupas mantêm o design fornecido; não são anunciadas como recortes pixel a
pixel. O cabelo continua sendo extraído diretamente da prancha original.

`scripts/character_art/compile.py` detecta os intervalos transparentes reais e
normaliza o encaixe em 64×96. O resultado fica em
`frontend/public/assets/characters`, com manifesto por camada, recortes,
direções, hash, âncoras e indicação da vista traseira corrigida.

A camada de pernas considera a sobreposição de saias/bermudas/grevas sobre
botas. Somente pele e cabelo recebem recoloração. A inspeção usa fundos claros
e escuros para evidenciar qualquer halo, fenda ou resíduo.
