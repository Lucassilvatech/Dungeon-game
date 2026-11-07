# Evidências da reconstrução visual

Os PNG desta pasta são capturas reais do Chromium contra API/worker e
PostgreSQL privados, **exceto `walk-contact-sheet.png`**, que é uma inspeção
estática dos quadros do atlas. Fontes geradas para arte estão em `art/maps/source`.

- `safe-zone-*`: vila, desktop 1280/1920 e viewport 390 px.
- `common-battle-*`: sala comum, mesmos três viewports.
- `boss-room-*`: sala secreta ritualística.
- `fixed-boss-*`: boss fixo, identidade estável após reload.
- `guild-*`: interior e interação da Guilda.
- `recovery-tent-desktop.png`: tenda existente.
- `procedural-expedition.png`: expedição criada pelo fluxo real de Aventura,
  capturada pela suíte smoke; inclui a página completa.
- `walking-in-game.png`: frame real durante movimento por teclado/API.
- `movement-validation.json`: amostragem de oito movimentos nas quatro direções.
- `placement-audit.json`: 250 layouts, 10 tipos, zero interseções proibidas.
- `asset-validation.json`: alpha, hashes, identidades e poses/apoio dos pés.
- `performance.json`: amostra de FPS/rAF em Canvas/Chromium headless virtualizado.
- `validation-summary.json`: resultados finais consolidados, sem somar subconjuntos.
- `backend-suite.txt`, `frontend-suite.txt`, `frontend-build.txt`,
  `browser-results.txt`: saídas dos testes executados.

Nomes de personagens e contas nas capturas pertencem a fixtures descartáveis.
A suíte visual posiciona o personagem por SQL privado para visitar cada ambiente;
portas/NPCs/clique/toque e caminhada usam a API real. A suíte smoke cobre também
expedição, combate, fuga, morte e recuperação pelo fluxo de jogo.

Capturas em 390 px não equivalem a teste em telefone físico. Não há simulação de
resultados de produção nem medição de GPU física. As diferenças remanescentes
em relação às referências estão em `docs/MAP_REBUILD_DELIVERY_0.9.md`.
