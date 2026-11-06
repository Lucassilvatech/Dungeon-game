# Economia física Lunar e comércio completo da Guilda 0.9

Base: `feature/lunar-variable-nuggets-royal-admin-0.9`. Head: `feature/lunar-physical-denominations-guild-commerce-0.9`. Sem merge automático.

Corrige finance.move, que normalizava origem e destino pelo total de massa a cada pagamento. As moedas agora são selecionadas no caixa real, transferidas sem mudar denominação e recusadas quando faltar troco. Exchange é explícito. A Guilda recebe ferramenta manual 70/20/10 com preview/fingerprint/confirm/receipt, chave inicial V1 persistente e nenhuma execução no startup.

Implementa políticas independentes buy/sell por definição, flags, revisão/histórico, gratuidade/arbitragem conscientes e comércio bidirecional de stacks/equipamentos com estoque físico. Minério mantém lote inteiro e buy/sell rates por grama independentes. Web/Admin permitem carteira real, compra/venda, exchange, rebalanceamento, tabela/histórico de preços e estoque. Discord read-only e Godot frozen.

Migração aditiva d91e2ab604c7: três tabelas e ampliação não destrutiva da constraint de preço zero em NPCStock. Não muda carteiras, Supply, ledger/cutover ou estoque existente. Cópia privada preservou50 tabelas/1.680 hashes históricos e100.550.000 mg, gap0; CLI operacional também executada nessa cópia. Nenhuma aplicação no banco operacional do usuário.

Validação e números finais em [docs/lunar/DELIVERY_PHYSICAL_COMMERCE_0.9.md](https://github.com/Lucassilvatech/Dungeon-game/blob/feature/lunar-physical-denominations-guild-commerce-0.9/docs/lunar/DELIVERY_PHYSICAL_COMMERCE_0.9.md), evidência PHYSICAL_VALIDATION.json. Backend completo em PostgreSQL real; npm test/build; Chromium desktop/390 px com falta de troco dos dois lados, quote/preview obsoletos e corrida por estoque; Alembic;20mil pagamentos simulados conservando massa e peças. [Comandos Windows/backup/aplicação manual](https://github.com/Lucassilvatech/Dungeon-game/blob/feature/lunar-physical-denominations-guild-commerce-0.9/docs/lunar/OPERATIONAL_GUILD_COMMERCE.md).

Não implementa produção NPC, músicas, multiplayer avançado, Boss Global, Echo ou política monetária automática. Operador deve revisar e executar preview/confirm do rebalanceamento no ambiente dele; o cutover principal existente não é refeito.

Validação final: **290 passed, 0 failed, 0 skipped, 2 warnings, 646.26s** no backend; npm test/build e cinco scripts Chromium aprovados. Nenhum teste de subconjunto somado à suíte final.
