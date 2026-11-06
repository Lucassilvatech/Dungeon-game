# Diagnóstico prévio — denominações físicas e comércio da Guilda 0.9

Base limpa confirmada: `feature/lunar-variable-nuggets-royal-admin-0.9`, HEAD `43a69caa37533a85ac1fd7fd9dc741ce59f5f92a`; status/branch/log/fetch executados antes de alterações. Nova branch: `feature/lunar-physical-denominations-guild-commerce-0.9`. Main preservada.

O usuário informa que o cutover principal já está ativo no ambiente operacional dele. Esse cutover não será refeito. A base de desenvolvimento e cópias privadas são independentes; nenhuma operação será aplicada automaticamente ao banco do usuário.

## Origem confirmada dos problemas

- `finance.move` debita/crêdita massa e chama `compose` para reconstruir TODAS as denominações das contas envolvidas. Isso normaliza tanto a origem quanto o destinatário e equivale a trocar moedas escondido. `select_coins` já resolve pagamento exato limitado ao estoque; será reutilizado.
- `LunarWallet` já lê quantidades reais, mas `LunarGuild` decompõe o preço em 10/5/1 no frontend e apresenta essa composição ideal como se estivesse disponível. Deve receber seleção/liquidez da API.
- `lunar.transfer` e mint já preservam denominações explícitas. Exchange existe, mas precisa conferir os inputs físicos antes da compensação e integrar a Administração Real.
- Rewards, reservas/settlements de contratos e leilões, recuperação, NPCs e pagamentos de dívida já convergem na facade `finance.move` via `economy.ledger`. A correção central alcança esses writers; regressões específicas serão testadas.
- `NPCStock` já representa Item real, com caixa finito. A Guilda usa compra derivada de base_value e revenda por preço do estoque, sem política independente/versionada por definição; APIs vendem pilha inteira. Reutilizar Item/NPCStock, acrescentar política/histórico de preço, quantidade estrita, quotes e recibos.
- Venda de minério usa rate de compra800 e lot individual. Falta sell rate/flags/cotação de lote da Guilda; preservar identidade e não dividir durante checkout.
- AdminService já fornece economy.manage, razão, prévia, estado obsoleto, confirmação, transação e auditoria; novas ações usarão esse fluxo, sem poderes Discord.

## Decisões de implementação

Pagamentos selecionam moedas existentes, grandes→médias→pequenas, com conservação por ativo e sem normalização. Falta de denominação rejeita pagamentos exatos. Taxa médica compulsória e amortização automática poderão pagar somente a parcela fisicamente representável até o limite devido, deixando o restante como obrigação; nunca trocam moeda para cobrar dívida. Pagamento manual da dívida continua exato.

Rebalanceamento70/20/10 é operação manual de troca, não mint. Grandes e médias recebem suas metas inteiras arredondadas ao múltiplo da denominação mais próximo (empate para baixo), pequenas absorvem o resto; verificar fixture19.498.000mg→1365/780/1948. Prévia/fingerprint ligam composição e conta; operação inicial V1 tem chave persistente; mudanças futuras são manuais e não recorrentes.

Política comercial aditiva por definição com buy/sell independentes, flags/revisão/admin/data, histórico append-only e confirmação consciente para gratuidade/arbitragem. Sem criar estoque no upgrade ou ao editar preço. Configuração de minério preserva a chave de compra atual, adicionando sell rate/flags; sem inventar preço de venda habilitado.

Implementar backend, CLI operacional seguro, Web/Admin, migração, cópia privada, testes completos e simulações antes da publicação. Godot congelado; Discord read-only; sem produção NPC, Boss Global, Echo, músicas ou multiplayer avançado.
