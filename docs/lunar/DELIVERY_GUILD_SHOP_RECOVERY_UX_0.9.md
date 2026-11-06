# Entrega0.9 — loja da Guilda, preços em lote e barraca

Branch: **feature/guild-shop-recovery-ux-0.9**, base **feature/lunar-physical-denominations-guild-commerce-0.9**, HEAD inicial **9d79999e62fd31d36c24241c04715b08af47b416**. Código funcional até5d6901c; commits adicionais de pacote/documentação não modificam backend/Web. HEAD final publicado informado no relatório da sessão e no histórico Git. Main preservada, sem merge ou force push.

## Guild Shop

Implementado e testado: grade desktop/mobile390px, pesquisa nos dois sentidos, estoque material por definição, equipamento individual, TUDO entre pilhas elegíveis, MÁXIMO calculado no servidor com caixa/denominações/capacidade, quantidade manual/+/- e total exato. Guilda aceita estoque12438 e3000 reais sem limite99; jogador continua limitado por pilha/capacidade. Equipado/protegido/custódia não entram na venda. Endpoints anteriores preservados.

Quote/trade reutilizam custódia, finance, receipts, idempotência, mutex e auditoria. Confirmação integrada substitui alert/confirm de compra/venda de materiais e minério; cancelamento não altera patrimônio. Stale quote exige nova revisão, sem execução silenciosa de preço novo. Mensagens humanas para estoque/ownership/caixa/moedas/espaço. Minério continua por peso e lote inteiro.

## Admin

Justificativa própria e ajuda≥10 caracteres para rebalanceamento, exchange, preço individual, minério e lote. Erro visível junto do painel. Edição individual preservada; rascunhos simultâneos, antes/depois, flags, revisão original, confirmação de todas e histórico individual com UUID comum do lote. Conflito rejeita lote inteiro e mantém rascunhos. Editar formulário invalida a prévia anterior. Arbitragem/gratuidade exigem reconhecimento somente em risco ativo real, incluindo arredondamento mineral autorizado.

## Recovery

Serviço na barraca sudoeste de city1, NPC(5,30), figura escura encapuzada/rosto oculto. Interação por aproximação abre recuperação existente; distância maior que1 impede interação/pagamento. Custo200%, ownership, custódia, conta npc:recovery, ledger e receipts preservados.

Sala recovery_hall e IDs/conexões/visitas antigos ficam arquivados. Não aparecem como porta interna/destino novo/mapa ativo. Entrada direta é rejeitada; fast travel legado redireciona para cidade sob guardas existentes. Ocupantes são relocados com evento auditado. Não há reset ou perda nova.

## Arquivos principais

| Área | Arquivos |
|---|---|
|Agregação/checkout|backend/app/guild_catalog.py, guild_commerce.py, main.py|
|Lote/permissões/histórico|backend/app/guild_admin.py, admin_service.py, models.py|
|Recuperação e navegação|backend/app/recovery_site.py, recovery.py, rooms.py, game.py, fast_travel.py, npc_economy.py|
|Loja/diálogos|frontend/src/Shop.tsx, GameDialog.tsx, LunarGuild.tsx, LunarWallet.tsx, DeathEconomy.tsx, main.tsx, api.ts, style.css|
|Administração|frontend/src/admin/GuildCommerce.tsx, style.css|
|Arte/cidade|frontend/src/Map.tsx, sprites.ts, environment.ts|
|Regressões|backend/tests/test_shop_recovery_ux.py e testes existentes de recuperação/upgrade/cidade; frontend/tests/guild-shop-recovery-ux.cjs e cinco scripts existentes; workflow web-backend-0.8|

## Banco e conservação

Migration **e06a9c24f8bd**, após d91e2ab604c7. Amplia PK de GuildPriceHistory para(request_id,policy_key), sem apagar histórico; adiciona/arquiva metadados da recuperação e reloca ocupantes auditados. Não altera migrations históricas, preços, estoques, holdings, lotes, supply ou ledger. Conflito com NPC personalizado/combate inesperado aborta para revisão. Nenhuma tabela nova.

Upgrade/check passaram em banco PostgreSQL novo e cópia privada anteriormente validada. Na cópia: **53 tabelas**, **50 tabelas idênticas por hashes**, **816 linhas históricas idênticas nessas tabelas**. Nas outras três, somente apresentação/posição/evento esperado; campos não posicionais de personagens iguais, eventos anteriores preservados e um evento de relocação acrescentado. Room/connection IDs mantidos. Massa econômica **100.550.000mg**, **gap0mg**, sem divergências de ledger/metadados. Cutover existente intacto e não reexecutado.

O banco operacional do Windows do usuário não foi acessado/alterado. Esta cópia é representativa e privada, não backup atual do Windows. Preços operacionais continuam sob decisão do administrador.

## Testes finais

**Backend completo: 304 passed,0 failed,0 skipped, 2 warnings, 696.20s.** PostgreSQL real, comando `.venv/bin/python -m pytest backend/tests -q`, DATABASE_URL descartável explícita/TOWER_TEST_DATABASE=1/PYTHONPATH=backend. Esta é uma única execução integral; não soma subconjuntos. Avisos existentes: AnyIO BlockingPortal e audioop/discord.py.

**Frontend:1 passed,0 failed,0 skipped**, `npm test`,66,07ms. **Build:PASS**, `npm run build`, TypeScript/Vite,4.89s; aviso conhecido do chunk Phaser grande. Sem build nativo.

**Chromium:6 scripts PASS**, com autenticação real HTTP e PostgreSQL privado: smoke, lunar, lunar-resources, royal, physical-commerce e guild-shop-recovery-ux. Desktop/390px; busca, estoque≥12438/≥3000, TUDO240 excluindo99 equipados, MAX e totais, confirmação/cancelamento, duas políticas/histórico, revisão editada invalidada, conflito concorrente, avisos condicionais, tenda/ownership/pagamento e auditoria. Scripts anteriores também cobrem moedas72/1/5, falta de troco dos dois lados, exchange explícito, preço17/19, corrida por estoque, stale quote/preview, minério684g e jogo completo. Papéis de teste concedidos somente em base descartável e revogados em finally.

Backend acrescenta14 casos, incluindo máximo contra enumeração independente, multi-stack/capacidade/protegidos, atomicidade, replay/concorrência, equipamento individual, lote/rollback/revisões/permissões/riscos e compatibilidade de recuperação. Testes antigos que exigiam cidade sem NPC foram atualizados para a mudança solicitada; cura/descanso e preservação financeira seguem verificados. Uma execução intermediária foi interrompida ao detectar essa expectativa antiga; não é a contagem final.

`alembic upgrade head` e `alembic check`: **PASS**, sem operações pendentes. [Evidência sanitizada](GUILD_UX_VALIDATION.json). [Especificação](GUILD_SHOP_RECOVERY_UX.md).

Para repetir browsers, API/Vite devem usar a mesma base privada:

```sh
TOWER_TEST_DATABASE=1 UX_TEST_DATABASE_URL="$DATABASE_URL" BASE_URL=http://127.0.0.1:8080 CHROMIUM_PATH=/usr/bin/chromium node frontend/tests/guild-shop-recovery-ux.cjs
```

Não execute pytest/browsers de fixtures no volume operacional. CI executa os mesmos cenários sequencialmente em PostgreSQL descartável.

## Web de desenvolvimento

[ZIP Web](../../builds/development/0.9.0-web-guild-ux-5d6901c/DungeonGame-Web-0.9-GuildUX.zip) · [SHA256](../../builds/development/0.9.0-web-guild-ux-5d6901c/SHA256SUMS). **8 arquivos estáticos**, CRC e todos os hashes do manifesto conferidos. SHA256: `877cd431fbb5a20a67687181604ec1d86966c172d0f492c7df4fe5bbe33f38b1`. Requer backend desta branch/schema e06a9c24f8bd; não é jogo offline nem executável Windows/APK.

[Loja desktop](../screenshots/guild-ux-0.9/shop-desktop.png) · [Loja390px](../screenshots/guild-ux-0.9/shop-mobile.png) · [Barraca390px](../screenshots/guild-ux-0.9/tent-mobile.png). Capturas só contêm contas sintéticas de teste. Assets originais desenhados no código, sem nova dependência de produção.

## Git e revisão

```text
26213fe docs(ux): diagnose aggregate trading batch pricing and recovery relocation
bb7cc75 feat(guild): add atomic aggregate catalog and exact affordable quantities
3cd69b9 feat(admin): audit batch pricing and relocate recovery without deleting history
a3f3126 feat(web): present aggregate shop with integrated transaction confirmations
cda08fb feat(web): add local price drafts batch review and secluded recovery tent
38bf754 test(guild): cover aggregate checkout batch conflicts and recovery relocation
5d6901c fix(admin): invalidate commercial review when its form changes
fa0ef63 build(web): package guild UX development client with verified manifest
```

Documentação/evidências são commits adicionais. Compare para revisão, sem merge: https://github.com/Lucassilvatech/Dungeon-game/compare/feature%2Flunar-physical-denominations-guild-commerce-0.9...feature%2Fguild-shop-recovery-ux-0.9?expand=1 . [Descrição preparada](../PULL_REQUEST_GUILD_SHOP_RECOVERY_UX.md). Não há ferramenta GitHub PR disponível e a política de rede não habilita api.github.com; PR não foi criado pela API. Push limitado à nova feature branch.

## Preservação e pendências

**Discord remains read-only. Discord cannot control the character.** Consultas/autorização continuam na suíte; bot externo ao vivo não foi validado.

**Windows:FROZEN; Android:FROZEN; APK:NOT REQUIRED; Windows build:NOT REQUIRED; Godot source:PRESERVED.** Nenhum arquivo Godot ou workflow nativo foi alterado. Texto antigo sobre a sala no Godot é histórico; compatibilidade segura de API foi preservada, sem evoluir UI nativa.

Sem crafting/refino, produção NPC, reposição infinita, market maker, rebalanceamento/preço automático, Boss Global, Echo ou política automática do rei. Não foi feito deploy/migration operacional pelo agente nem teste de carga de produção. Mutex financeiro global, catálogo completo em memória e custo da auditoria crescente continuam limites de escala; não representam problema de conservação nos testes. Revisar paginação/busca no servidor e cache por definição se o volume justificar, sem mudar regras econômicas.

[Windows PowerShell: backup, atualização, migration/check/audit, URLs e parada segura](OPERATIONAL_GUILD_SHOP_RECOVERY_UX.md). Não repetir cutover nem rebalanceamento inicial para aplicar esta UX. Parar nesta entrega, sem antecipar outros sistemas.
