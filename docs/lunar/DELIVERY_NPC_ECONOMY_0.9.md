# Entrega0.9 — economia autônoma inicial dos NPCs

Branch **feature/autonomous-npc-economy-0.9**, base **feature/guild-shop-recovery-ux-0.9**, HEAD inicial **66e88e5d461898054792db7597a7d94bfa6f3569**. Código funcional/testes até **d3fa50171ed4dd26935181c9b2541ce14820ac8d**; commits posteriores contêm pacote/documentação. HEAD final publicado consta no relatório da sessão/histórico Git. Main/base preservadas, sem merge ou force push.

## Implementação entregue

Economia pequena e persistente, integrada de verdade ao jogo e à Central existente. Alquimista produz3 poções consumindo7 Folhas/7 Cristais iniciais; Ferreiro consome90 Minérios para18 Lingotes e a segunda unidade de cada uma das6 peças. Produção determinística respeita alvos e capacidades. Todas as peças mantêm IDs e slots independentes; não substituem a Espada de Aprendiz protegida.

Comerciante começa **vazio/caixa0**, conforme resposta do usuário. Todos os novos caixas começam0; Guilda mantém patrimônio anterior. A entrada inicial autorizada dos produtores é histórica e auditada uma vez. Abastecimento posterior usa estoque já existente/compra real; não há faucet nem segunda carteira.

Worker FastAPI independente de UI, ciclo UTC persistente e idempotente, locks existentes, produção antes da reposição. Alquimista/Ferreiro compram lotes do Comerciante; ele pode repor da Guilda com caixa real e flags/preços dela. Falta de material, caixa, moedas exatas, lote/capacidade mantém espera. Registros de espera não fazem spam em idle. Nenhum catch-up ilimitado após reinício.

Referências são os valores atuais de compra da Guilda. Venda da Guilda continua independente: **base×quantidade+margem fixa**, inicialmente1 por operação de matéria-prima. Comerciante usa **referência×quantidade+margem**, inicialmente1 por lote.10×2+1=21;100+1=101. Campos históricos de preço não são redefinidos. A nova margem altera somente cotações futuras, e recibos históricos continuam idempotentes.

MarketPricing centraliza fatores inteiros12500/12000/13000 e ceil para a menor moeda. Folha/Cristal propagam às poções; Minério→Lingote→peças. Snapshots MarketRevision são imutáveis. Sem mudança relevante não há nova revisão; worker consulta a revisão persistida. Não há inflação percentual por revendas, market maker ou lucratividade garantida por código.

## Banco de dados

Migração aditiva **7167b684d5f7**, após e06a9c24f8bd:

- NpcProfile: conta Lunar, flags, margem/fatores, revisão e último ciclo.
- NpcInventoryPolicy: capacidade/alvo/reposição/lote/flags/revisão/status por SKU/NPC.
- NpcRecipe: somente as10 receitas autorizadas.
- MarketRevision: snapshots derivados imutáveis.
- ItemDefinition.equipment_slot: coluna opcional; dados originais preservados.
- Triggers append-only para revisões e novos tipos históricos NPC em WorldEvent.

Sem nova moeda ou tabela de estoque paralelo. Item/NPCStock, LunarHolding/Entry/Supply, GuildTradeReceipt e AdminService continuam autoritativos. Fonte de matéria-prima inicial é APPROVED_HISTORICAL_STOCK; isso não aumenta descobertas/lastro Lunar. Seed não repete materiais, produtos, preços configurados ou créditos. Contas/mercadorias históricas são adotadas sem sobrescrita.

Upgrade/check passaram em bancos novos e cópia privada previamente validada da UX: **53 tabelas anteriores**, **1.778 hashes de linhas/colunas originais preservados** após upgrade. Após seed repetido, todas as linhas históricas continuaram presentes; somente novos dados autorizados/metadados de NPC foram acrescentados. Produção real nessa cópia foi validada. Massa **100.550.000mg**, **gap0mg**, sem divergências de ledger/metadados; recibo de cutover mantido, sem reconversão.

A cópia é representativa/privada e não é um backup atual do Windows. O agente não acessou/migrou o banco operacional do usuário. [Evidência sanitizada](NPC_ECONOMY_VALIDATION.json).

## Administração

Módulo Economia dos NPCs integrado à Central: nome/tipo/status, composição física do caixa, estoques, capacidades/alvos, receitas, preços/revisão, produção/reposição, compras/vendas, última atualização e histórico privado.

Configurar NPC permite fatores/margens/flags e várias políticas no mesmo lote. Captura revisões originais, exige economy.manage, justificativa≥10, prévia antes/depois/preços afetados e confirmação. Conflito rejeita integralmente; UUID repetido não reaplica. Formulário editado invalida a revisão anterior. Alterações não cruzam perfis inadvertidamente.

Ações adicionais: transferir mercadoria **existente** entre instituições com capacidade/proveniência/auditoria; financiar caixas pela transferência Royal de moedas **existentes**. Não cria estoque ou dinheiro. O writer legado npc.stock também respeita capacidades dos novos NPCs. Royal→Guilda→Preços mantém compra/venda/flags e mostra base/margem/total; margem editável no módulo NPC.

## Jogo

3 NPCs originais leves na vila: Comerciante(34,8), Alquimista(36,15), Ferreiro(16,22). Lojas da vila/Ir até, clique/toque/E usam posição real e aproximação. Servidor rejeita compra remota, corpo extra, quantidade inválida, capacidade insuficiente, falta de peças exatas e cotação antiga.

Comerciante vende lotes10/10 iniciais; edição para20 chega ao jogo sem código. Alquimista mostra produtos disponíveis; ingrediente sem venda ativa não vira oferta. Ferreiro tem estoque/ID por peça e equipamento por slot. Busca, controles de quantidade, MÁXIMO, total recebido do servidor e confirmação integrada aproveitam Shop existente. Não há fórmula de preço duplicada no React.

Jogo/ADM compartilham NpcEconomyState/NpcPolicy e preços do mesmo backend. Histórico privado é omitido na consulta pública. Commit é imediato na API; após ações há refresh e clientes ativos consultam em2,5s/3s. Mercado alterado exige revisar/confirmar novamente, sem cobrança silenciosa.

## Arquivos importantes

| Arquivo | Responsabilidade |
|---|---|
|backend/app/npc_economy.py|Custódia existente, bootstrap idempotente, transferências, aproximação, DTO e logs estruturados|
|backend/app/npc_production.py|Worker/ciclos persistentes, receitas determinísticas, reposição e espera|
|backend/app/market_pricing.py|Preço de referência/derivados, fatores/ceil/margens e revisão imutável|
|backend/app/models.py|4 modelos e slot opcional|
|backend/app/npc_admin.py|Validação de políticas, previews/confirm/after e transferências auditadas|
|backend/app/admin_service.py, admin.py|Integração com permissões/revisões/auditoria existentes e snapshot consistente|
|backend/app/guild_catalog.py, guild_commerce.py|Catálogo/quote/trade compartilhado; máximo físico com taxa/lotes|
|backend/app/seed.py, config.py, main.py|Bootstrap seguro, cadência, lifespan e APIs autenticadas|
|backend/app/game.py, attributes.py|NPCs bloqueiam tile; arma/5 armaduras equipáveis separadamente|
|frontend/src/NpcShops.tsx, Shop.tsx, npcTypes.ts|Lojas/DTOs, lotes, totais autoritativos e confirmação|
|frontend/src/admin/NpcEconomy.tsx, GuildCommerce.tsx, main.tsx, style.css|Configuração/histórico/transferências/financiamento e base/margem/total|
|frontend/src/Map.tsx, sprites.ts, main.tsx, types.ts, api.ts, pathfinding.ts|Apresentação/interação/caminhada e inventário|
|backend/tests/test_npc_economy.py|35 novos casos expandidos de domínio/integração/concorrência/logs|
|scripts/test_npc_browser_stack.py, frontend/tests/npc-economy.cjs|Banco isolado/worker real/HTTP/Chromium ponta a ponta|
|.github/workflows/web-backend-0.8.yml|Runner real adicional em CI; execução remota não foi observada|
|scripts/package_web_09.py|Pacote Web atual, schema/manifesto/CRC/SHA256|

Testes existentes de setup/estoque/carteira/UX foram adaptados à entrada dos NPCs e à margem fixa explícita. Consulta de estoque da Guilda filtra sua conta, sem somar os7 materiais do Alquimista. Exemplo de falta de troco passa a usar base18+margem1=19; nenhuma troca monetária foi escondida para fazer o teste passar.

## Testes finais executados

```text
backend:
339 passed
0 failed
0 skipped
2 warnings
716.27s

frontend (npm test):
1 passed
0 failed
0 skipped
48.21ms

build:
PASS (5.08s)

Chromium:
7 scripts PASS
```

Contagem backend vem de **uma execução integral final**, não soma subconjuntos ou as execuções intermediárias336/338. PostgreSQL17 real. Avisos existentes:AnyIO BlockingPortal/Starlette e audioop/discord.py. TypeScript/Vite passaram; aviso conhecido do chunk Phaser grande. Nenhum teste foi declarado aprovado sem execução.

Cobertura nova: receitas/7+7/90, seed idempotente, produção18 e6 peças, preços derivados, taxas/lotes contra enumeração física independente, mercado/revisões, configurações/políticas/limites/permissões, material/caixa/troco/capacidade, rollback, replay, compras e ciclos concorrentes, último produto, slots, proximidade/caminhada e logs JSON/idle sem spam. Suite antiga de economia, contratos/leilões, dívida/recuperação e Discord continua aprovada.

Chromium existente: gameplay, carteira, procedural/Minério Lunar, Royal, comércio físico e Guild UX. Cenário novo usa **worker real em outro processo**, iniciado com produção inicialmente pausada apenas na fixture privada; habilita pela ADM e observa fabricação, transferências financiadas e compras reais. Não chama tick pelo browser nem usa simulação de estoque.

Novo fluxo confirmou1→2 poções,90→18→6 equipamentos adicionais, reposição financiada,10×2+1=21, fator/lote/margem editados via UI, revisão compartilhada, stale quote com segunda confirmação, estoque finito,6 slots independentes, seed repetido, desktop/390px e gap0.

Reinício HTTP real também preservou estoques/carteiras/fatores/lotes/margens. Hash da projeção antes/depois: `a8b77d49dc84a1b7a815d4ff7f560cc09717723ce2b526f7ad9378a61a85416f`. Nenhuma senha/token consta da evidência versionada.

Com DATABASE_URL explicitamente apontando a PostgreSQL de teste descartável:

```sh
cd backend
../.venv/bin/alembic upgrade head
../.venv/bin/alembic check
TOWER_TEST_DATABASE=1 ../.venv/bin/python -m pytest tests -q
cd ../frontend
npm test
npm run build
cd ..
TOWER_TEST_DATABASE=1 DATABASE_URL="$DATABASE_URL" .venv/bin/python scripts/test_npc_browser_stack.py
```

O runner exige autorização de teste, cria **outra** base UUID e nunca reseta/migra a base indicada. Preserva sua base privada para diagnóstico, encerra os processos próprios e revoga o papel temporário do navegador em finally. Requer permissão CREATE DATABASE no servidor de testes e Chromium instalado; CHROMIUM_PATH pode selecionar o navegador do ambiente. CI usa PostgreSQL descartável. Não executar pytest/browsers de fixtures no volume operacional.

## Pacote e revisão

[ZIP Web](../../builds/development/0.9.0-web-npc-economy-d3fa501/DungeonGame-Web-0.9-NPC-Economy.zip) · [SHA256](../../builds/development/0.9.0-web-npc-economy-d3fa501/SHA256SUMS).8 arquivos estáticos; CRC e todos os hashes do manifesto conferidos. SHA256 `d7a7eb2d42d80efc0e16e2326a5dbf1c6bcd96b093901b6db4f61dadc86b7f00`. Requer backend desta branch/schema7167b684d5f7 e proxy /api; não é jogo offline nem aplicativo Windows/APK.

[Loja390px](../screenshots/npc-economy-0.9/npc-shop-mobile.png) · [Administração390px](../screenshots/npc-economy-0.9/npc-admin-mobile.png). Capturas funcionais de QA com contas sintéticas.

```text
ace7e74 docs(npc): diagnose production stock pricing and integration before implementation
d42c02f feat(npc): persist finite production restocking and derived market revisions
fc93a2d feat(economy): integrate NPC shops fixed margins admin previews and equipment slots
4ff9b54 fix(npc): enforce capacity across legacy writers and consistent market observations
c94c245 feat(web): expose village NPC shops lots and independently equipped armour
78ee642 feat(admin): review NPC factors margins stock policies and funded transfers
84b950a fix(npc): emit structured operation logs and clarify policy applicability
d3fa501 test(npc): validate autonomous production pricing persistence and real browser worker
5945b42 build(web): package autonomous NPC client with schema and integrity manifest
```

Documentação/evidências são commits posteriores, sem mudança funcional. Compare para revisão: https://github.com/Lucassilvatech/Dungeon-game/compare/feature%2Fguild-shop-recovery-ux-0.9...feature%2Fautonomous-npc-economy-0.9?expand=1 . [Descrição preparada](../PULL_REQUEST_NPC_ECONOMY.md). Não houve criação de PR pela API: não há ferramenta GitHub PR disponível e api.github.com não está habilitado na política de rede. Push limitado à nova feature; sem merge.

## Pendências e limites explícitos

Nenhuma funcionalidade econômica obrigatória foi substituída por mock/placeholders. Não foram definidos no documento efeitos de uso das poções nem valores novos de bônus de combate: não foram inventados; aquisição/produção/custódia e equipamento independente funcionam, com bônus novos neutros. Consumo/atributos requerem uma especificação futura.

Defaults técnicos de capacidade100/reserva0 são configuráveis, não balanceamento final. Não há garantia automática de lucro ou preços por oferta/demanda. Escala/carga de produção não foi medida; mutex financeiro global, catálogo completo e auditoria crescente continuam gargalos conhecidos. Presença WebSocket ainda recomenda1 worker até broker apropriado; nenhum Redis obrigatório foi introduzido.

**Discord remains read-only. Discord cannot control the character.** Controle/bot externo ao vivo não foi validado. Ciclos são autônomos do servidor, não disparados por consultas Discord.

**Windows:FROZEN. Android:FROZEN. APK:NOT REQUIRED. Windows build:NOT REQUIRED. Godot source:PRESERVED.** Nenhum arquivo Godot/bot ou build nativo foi alterado/gerado. Novas lojas não foram portadas ao cliente nativo congelado.

Sem novos materiais/receitas além do documento, profissões adicionais, encantamento, crafting aleatório, market maker, estoque/caixa infinito, Boss/Echo ou automação do rei. Deploy/migração operacional no Windows, Discord externo e carga real não foram executados pelo agente. [Validação manual/Windows completa](OPERATIONAL_NPC_ECONOMY.md). Não repetir cutover nem rebalanceamento inicial; não avançar automaticamente a outras etapas.
