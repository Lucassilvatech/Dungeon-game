# Economia

## Regras definidas

Moeda única; Tesouro finito. Monstros não emitem moedas. Vitórias criam direito de recompensa; a Guilda paga depois, perto do NPC, com recursos do Tesouro. Débito, crédito, ledger e marca de pagamento são atômicos. Sem orçamento, toda a operação reverte e o direito permanece disponível. Cada combate é pago uma vez. O ledger registra gênese e transferências; nenhuma ação de cliente define saldo.

## Parâmetros provisórios

`INITIAL_TREASURY=100000`, `MONSTER_REWARD=10`, `BOSS_REWARD=100`. Configuráveis por ambiente; não são decisões definitivas de balanceamento. Fornecimento inicial só no seed de um banco novo. Personagens começam sem moedas. Loot material é criado por vitória; ele não representa emissão monetária. Sem taxas, empréstimos ou juros no MVP.

## Futuro

Mercado global: vendedor recebe o líquido solicitado; comprador paga valor mais imposto; imposto vai ao sistema tributário. Compra e custódia devem ser transacionais, com lock do anúncio e saldo. Anúncio dura sete dias, renovação automática opcional com até três renovações; taxas configuráveis de publicação/renovação; expirados voltam à caixa de recebimento.

Modelo proposto, ainda não migrado: `listing(item_instance, seller, net_price, status, expires_at, renewals)`, `wallet`, `ledger_transaction`, `ledger_entry`, `npc_stock`, `guild_budget`, `budget_reservation`, `claim`. Índice de anúncio ativo por instância e chave idempotente por compra. Locks em ordem consistente de IDs para múltiplas carteiras. NPCs usam dinheiro e estoques reais, sem recursos infinitos; comércio entre andares só se desbloqueados. Filiais da Guilda terão orçamentos próprios e contratos com reserva garantida. Banco Central monitorará preços, circulação, crises e emissão controlada, com auditoria e intervenção administrativa.

## Questões abertas

Oferta inicial definitiva, impostos, taxas, preços de serviços, limites de emissão, distribuição orçamentária, frequência de recompensas, prevenção de farming, indicadores de inflação e política de emergência. Não há política monetária automática avançada nesta versão.
