# Economia autônoma inicial dos NPCs com estoque e dinheiro reais

Alquimista/Ferreiro fabricam as receitas autorizadas consumindo materiais persistentes; Comerciante vazio/caixa0 trabalha em lotes e repõe da Guilda mediante pagamento real. Worker independente de UI, ciclo UTC persistente/idempotente, capacidades/flags e estados de espera. Reutiliza Item/NPCStock, Lunar finance/ledger e receipts, sem economia paralela ou faucet.

Centraliza preços de referência, margens fixas e fatores inteiros/ceil em MarketRevision imutável. Guilda preserva compra/venda independentes; revenda de matéria-prima acrescenta margem uma vez por operação. Novas lojas e módulo da Central compartilham estado/cotações, revisão/preview/confirm/razão/permissões, histórico, transferências de mercadoria e financiamento real. Seis peças mantêm identidade/slots próprios.

Base:`feature/guild-shop-recovery-ux-0.9`. Head:`feature/autonomous-npc-economy-0.9`. Preparado para Draft PR, sem merge automático.

Migration7167b684d5f7:4 tabelas, slot opcional e proteção de histórico; sem reset de carteiras/dados nem alteração de migrations históricas. Cópia privada preservou1.778 hashes originais de53 tabelas; seed/produção auditados,100.550.000mg/gap0. Operacional do usuário não foi alterado.

Validação final: **339 passed,0 failed,0 skipped,2 warnings,716.27s**, uma suíte backend integral PostgreSQL. `npm test`:1 passed; `npm run build`:PASS;7 scripts Chromium:PASS, incluindo worker HTTP real em banco novo, desktop/390px. Upgrade/check e reinício real:PASS. [Relatório/evidências](https://github.com/Lucassilvatech/Dungeon-game/blob/feature/autonomous-npc-economy-0.9/docs/lunar/DELIVERY_NPC_ECONOMY_0.9.md).

Discord read-only; Godot congelado/preservado. Não inventa efeitos de poções ou bônus não especificados. Sem Boss/Echo/rei automático, novos materiais/receitas/profissões ou market maker. Carga real/Discord externo/deploy operacional não validados. [Windows, backup e validação manual](https://github.com/Lucassilvatech/Dungeon-game/blob/feature/autonomous-npc-economy-0.9/docs/lunar/OPERATIONAL_NPC_ECONOMY.md).
