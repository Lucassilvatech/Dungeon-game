# Entrega 0.9 — denominações físicas, liquidez e comércio da Guilda

## Git e escopo

Base: **feature/lunar-variable-nuggets-royal-admin-0.9**, HEAD inicial **43a69caa37533a85ac1fd7fd9dc741ce59f5f92a**. Nova branch: **feature/lunar-physical-denominations-guild-commerce-0.9**. Desenvolvimento isolado; sem merge/force push ou alteração na main/base. O relatório da sessão identifica HEAD final e push. [Diagnóstico registrado antes de programar](PHYSICAL_DENOMINATIONS_DIAGNOSIS.md).

O usuário informou cutover Lunar principal já ativo no operacional dele. Esta etapa não o refaz. O agente validou PostgreSQL descartável e cópia privada previamente verificada, sem aplicar migração/rebalanceamento no operacional. [Comandos exatos de backup, atualização, inspect/preview/fingerprint/apply/audit e Windows](OPERATIONAL_GUILD_COMMERCE.md).

## Diagnóstico e correção física

Normalização estava no backend: finance.move calculava novos totais e chamava compose em todas as contas envolvidas. Frontend LunarGuild também decompunha preço em uma composição ideal sem verificar caixa. Agora finance.move seleciona somente moedas reais do pagador e credita as mesmas peças; UI usa seleção/liquidez do servidor. compose permanece somente no cutover histórico.

72 grandes/1 média/2 pequenas recebendo 3 pequenas torna-se **72/1/5**, total 730 g. Mint persiste exatamente quantidades solicitadas; transfer/payments preservam cada denominação entre contas. Seleção prioriza grandes, médias, pequenas, com valor exato e disponibilidade limitada. Dinheiro total suficiente não garante liquidez:5 grandes não pagam1;2 grandes não pagam19. **INSUFFICIENT_DENOMINATIONS** reverte sem converter/criar troco ou crédito.

Exchange é operação explícita, inputs conferidos antes da compensação, massa zero líquida e recibo persistente. Administração integra economy.manage, razão, prévia/fingerprint, confirmação, mutex e auditoria. Replays históricos de exchange/NPC_SALE/NPC_PURCHASE são preservados sem comparar contra estoque já consumido ou executar dinheiro novamente. Corpos de checkout são estritos e não aceitam preço, proprietário ou recompensa arbitrários.

## Guilda: caixa e rebalanceamento

Meta inicial por massa **70/20/10**, sem controle automático. Algoritmo inteiro aproxima grandes da meta, depois médias respeitando resto, e pequenas absorvem o resíduo. Fixture obrigatória **19.498.000 mg→1365 grandes/780 médias/1948 pequenas**, massa antes/depois 19.498.000 mg, diferença0. Nenhum jogador/Tesouro/NPC/escrow é recomposto automaticamente.

Operação **GUILD_DENOMINATION_REBALANCE**, chave inicial **GUILD_DENOMINATION_REBALANCE_V1**, sem MINT/DISCOVERED_MINERAL/ADMIN_INJECTION. Prévia captura caixa atual, total, percentuais, meta, proposta/diferenças e fingerprint; apply recusa STALE_PREVIEW e repetições V1 não normalizam pagamentos futuros. Decisões manuais posteriores usam outros UUIDs. CLI real inspect/preview/fingerprint/apply/audit/preços foi executada na cópia privada e aprovada.

A cópia disponível tinha Guilda com **0 mg/0G/0M/0P**. Isso não é medição do operacional atual do usuário, cujo total informado foi 19.498.000 mg. A prévia inicial usou o zero efetivamente encontrado. Em seguida, exclusivamente nessa cópia, uma transferência financiada pelo Tesouro preparou fixture19.498.000 mg para validar composição exata e comércio. Não se sobrescreveu um saldo real usando o número informado.

## Preços e comércio completos

`GuildItemPolicy` separa compra/venda da definição histórica do item, com flags/revisão/admin/data. Catálogo inicial tem quatro definições, inclusive a espada protegida; a lista acompanha definições reais. Preço por unidade de stack e por peça de equipamento. Flags independentes de zero; gratuidade e POSSIBLE_ARBITRAGE exigem confirmação consciente, sem margem obrigatória. Atualizações incrementam revisão e geram GuildPriceHistory append-only, incluindo antes/depois, flags, ator, motivo, horário e UUID. Mudança e reversão de preço invalidam quote anterior.

Guilda compra do jogador e vende ao jogador com **Item/NPCStock existentes**, sem segundo estoque. Quantidade parcial, custódia/equipamento/proteção, capacidade compartilhada, empilhamento e ledger/receipt são transacionais. Sem estoque:OUT_OF_STOCK. Sem troco em qualquer pagador:falha, com item/dinheiro intactos. Mesmo request retorna replay; concorrentes não compram o mesmo estoque. Atualização de preços não cria/repõe mercadoria.

Minério usa buy rate800 preservado, sell rate configurável separado e flags independentes. Sell rate inicial0/sell_enabled=false, sem oferta comercial inventada. Quotes vinculam lote inteiro real, peso, owner/estado, direção, rate/revisão/hash e pagamento físico. Guilda só vende lote HELD próprio; mesma identidade e origem são preservadas, sem split implícito ou nova massa. Gratuidade de preço arredondado zero exige autorização explícita. Os dois sentidos foram executadas em testes/cópia/Chromium.

## Writers financeiros preservados

Rewards/Guilda/Tesouro, contratos/reservas/refunds, leilões/bids/outbid/settlement, NPCs, recuperação, dívida e taxas usam a facade física compartilhada. Testes confirmam escrow recebendo/devolvendo denominações reais e item entregue uma vez. Uma parcela pode não ser pagável apesar do total reservado; não há exchange escondido.

Dívida continua obrigação separada. Pagamento manual exato reduz obrigação/recebível junto à transferência. Taxa100 com 3 grandes:30físicos ao Tesouro,70de obrigação. Taxa compulsória e amortização automática usam somente parcela representável; restante permanece dívida, sem quebrar moeda ou impedir o fluxo de morte por falta de troco. Confisco financiado é adiado se não puder ser pago exatamente. Burn registra peças/gramas realmente destruídos. [Detalhamento](PHYSICAL_DENOMINATIONS.md).

## Migração e auditoria

Revisão aditiva **d91e2ab604c7**, pai ca343e37b4ca: três tabelas novas (políticas, histórico, recibos), FKs/índices/checks/triggers de imutabilidade; permite preço zero no campo histórico de NPCStock. Não altera holdings/lotes/Supply/ledger/cutover existentes, não gera stock e não edita migrações antigas. Seed não altera políticas já configuradas.

Cópia privada: **50 tabelas e 1.680 hashes históricos preservados** antes/depois do upgrade; recibo de cutover inalterado. Massa econômica **100.550.000 mg antes/depois**, gap **0 mg**, sem nova gênese/descoberta/injeção durante os fluxos comerciais de validação. Depois da comparação de preservação, só a cópia recebeu fixtures materiais explícitas e operações de teste. Executados:upgrade/check, caixa real, preview/apply, falta de troco, rebalanceamento, preços, item sell/buy, stale quote, out of stock, mineral sell/buy, contrato, leilão, taxa/dívida/pagamento e auditoria final. Dump privado não versionado.

Equação global: **GENESIS_BACKING + DISCOVERED_MINERAL + ADMIN_INJECTION − DESTROYED = moedas + lotes HELD**. Exchange/rebalance/preço/comércio não mudam Supply. Postings físicos por ativo e genealogia de minério permanecem conciliados. Potencial procedural e dívidas são separados da massa material.

## Web e Administração

Web mostra total e peças reais, comércio por quantidade e flags, preços buy/sell claramente separados, pending/confirm, falta de troco, stale quote e estoque esgotado. Administração do Rei → Guilda integra Caixa, Rebalanceamento, Trocar denominações, Preços, Estoque, Histórico e Comércio com operações separadas. Testados desktop e390 px, sem overflow da página ou hover obrigatório. Sem administrador/senha padrão.

Chromium validou:72/1/5 após recebimento; Guilda sem troco; troca explícita; preços17/19 e histórico; compra/venda parcial/merge; jogador com 20sem combinação19; compra concorrente esgotando estoque; rebalance/fingerprint/stale preview; stale quote em checkout real; minério684 g comprado/vendido inteiro; auditoria0. Os testes legados de carteira, procedural/Guilda, Royal mint/burn e gameplay também foram executados. Roles temporários de teste revogados em finally, somente em banco descartável.

## Simulação e testes

**Suíte backend completa final: 290 passed, 0 failed, 0 skipped, 2 warnings, 646,26s (10min46s).** Executada em PostgreSQL17 novo, com a cadeia completa de migrations.

A execução final integral é a contagem oficial; não soma subconjuntos ou a execução intermediária de 289testes anterior ao ajuste de recibos históricos. Avisos existentes:AnyIO BlockingPortal no Starlette e audioop no discord.py.

- `npm test`: **1 passed,0 failed,0 skipped**,57,64 ms; freeze dos workflows nativos.
- `npm run build`: **PASS**,4,97s, TypeScript/Vite; aviso conhecido do chunk Phaser grande.
- Chromium: **PASS** para carteira, procedural/coleta/Guilda, Royal e comércio físico desktop/390 px; smoke legado detalhado registrado na evidência.
- `alembic upgrade head` / `alembic check`: **PASS**, sem operações pendentes em banco novo/cópia privada.
- Simulador: **20.000 tentativas**, **18.525 sucessos**, **1.020 falhas de troco**, **455 falhas de fundos**; uso46.588 grandes/10.660 médias/39.802 pequenas. Primeira falta de troco na etapa 8, contada entre ambos os sentidos. Distribuição final Guilda 7G/4M/30P,120.000 mg; massa global 19.498.000 mg e peças globais por denominação preservadas. Sem rebalanceamento durante os pagamentos; meta aprovada não alterada. [Resultado](LIQUIDITY_SIMULATION.json).

Cenário de liquidez é sintético/reproduzível, não previsão de produção ou recomendação de outra proporção. Mutex financeiro global e auditoria crescente são gargalos conhecidos; escala/carga reais não foram validadas. Não se adicionou broker ou outro serviço; presença continua com um worker.

Com DATABASE_URL explicitamente de PostgreSQL descartável:

```sh
cd backend
../.venv/bin/alembic upgrade head
../.venv/bin/alembic check
TOWER_TEST_DATABASE=1 ../.venv/bin/python -m pytest tests -q
cd ../frontend
npm test
npm run build
TOWER_TEST_DATABASE=1 PHYSICAL_TEST_DATABASE_URL="$DATABASE_URL" BASE_URL=http://127.0.0.1:8080 node tests/physical-commerce.cjs
cd ..
.venv/bin/python scripts/simulate_guild_liquidity.py
```

API/Vite e navegador devem usar a mesma base de teste. No CI, o workflow Web cria PostgreSQL descartável e executa os cenários em sequência; fixtures de chance100% são exclusivamente de teste. [Evidência sanitizada](PHYSICAL_VALIDATION.json).

## Discord, Godot e limites finais

**Discord remains read-only. Discord cannot control the character.** Nenhuma mutação buy/sell/exchange/rebalance/mint/admin/preço foi adicionada; consultas privadas mostram holdings/lotes reais. Testes de autorização/consultas puras foram mantidos. Discord externo real não foi usado.

**Windows: FROZEN. Android: FROZEN. APK: NOT REQUIRED. Windows build: NOT REQUIRED. Godot source: PRESERVED.** Nenhum arquivo Godot/build nativo foi alterado/gerado.

Fora desta entrega:produção/consumo/reposição autônoma NPC, jobs/cadeias produtivas/mercados dinâmicos, Boss Global, Echo/rituais, política automática do rei, multiplayer avançado, músicas, deploy/ativação operacional pelo agente e carga real. A próxima implementação exige autorização separada.

## Commits e revisão

| Commit | Conteúdo |
|---|---|
|160d089|Diagnóstico antes da programação |
|3e58da3|Denominações físicas e pagamentos exatos |
|1fdec4a|Rebalanceamento/preços/comércio/migração/CLI e replays históricos |
|8a756b6|Web/Admin de caixa, preços, exchange e checkout |
|7fb0c7d|Regressões físicas, concorrência, estoque e simulação |
|89559aa|Chromium desktop/mobile, falta de troco e corrida por estoque |

Documentação/CI/evidências são commits adicionais, sem alteração de código funcional após a suíte final. Comparação contra a base: https://github.com/Lucassilvatech/Dungeon-game/compare/feature%2Flunar-variable-nuggets-royal-admin-0.9...feature%2Flunar-physical-denominations-guild-commerce-0.9?expand=1 . Descrição pronta em [PULL_REQUEST_PHYSICAL_GUILD_COMMERCE.md](../PULL_REQUEST_PHYSICAL_GUILD_COMMERCE.md). Push somente à nova feature branch; HEAD final e confirmação do remoto no relatório da sessão.

## Como executar localmente

[Windows PowerShell completo: backup, branch publicada, migration, inspect, preview, fingerprint, apply V1, audit, preços, URLs, logs e parada segura](OPERATIONAL_GUILD_COMMERCE.md). Nenhum comando operacional foi aplicado pelo agente. O operador revisa e confirma a proposta calculada sobre o caixa real dele.
