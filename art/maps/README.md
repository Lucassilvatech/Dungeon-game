# Arte dos mapas reconstruídos

Fontes novas em `source/`, criadas com as referências do usuário como entrada
visual. Não são capturas do jogo, nem extrações literais pixel a pixel. Os sprites
dos personagens permanecem derivados de `art/pixel/source/reference-actors.png`.

Compilador: `python scripts/build_pixel_assets.py` (Pillow fixado em
`scripts/requirements-art.txt`). O submódulo `scripts/map_art/compiler.py` gera
sprites recortados com alpha binário, materiais contínuos e manifestos SHA256.
Nada é gerado por IA durante o gameplay.

O renderer usa apenas `frontend/public/assets/maps` para novos cenários.
`art/pixel/source/scenery-original.png` e `terrain-original.png` são arquivos
históricos e não alimentam a implementação atual dos mapas.

Validação: `python scripts/map_art/validate.py`. Capturas reais, evidências de
animação e desempenho ficam em `artifacts/map-rebuild`, com limites documentados
em `docs/MAP_REBUILD_DELIVERY_0.9.md`.
