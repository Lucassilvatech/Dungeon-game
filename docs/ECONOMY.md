> Nota de versão 0.6: o mercado geral descrito abaixo continua proposto. O Banco Central manual, créditos administrativos isolados e o leilão exclusivo de espólios já foram implementados; estado atual e contabilidade estão em [CENTRAL_BANK.md](CENTRAL_BANK.md), [ACCOUNTING.md](ACCOUNTING.md) e [AUCTIONS.md](AUCTIONS.md). Não confundir esse planejamento anterior de mercado com a implementação atual.

## Comércio agregado sem nova economia

TUDO/MAX são projeções; confirmação é autoritativa e atômica sobre Item/NPCStock/LunarHolding existentes. Guilda pode ter12438 unidades; entrada no jogador respeita99 por pilha e capacidade. Nenhum preço, estoque, supply ou carteira é redefinido. Recuperação na vila mantém transferência PLAYER→npc:recovery e custo200%. [Especificação](lunar/GUILD_SHOP_RECOVERY_UX.md).


## Regra operacional atual: peças físicas e liquidez

Total é derivado dos holdings coin_small/medium/large, nunca usado para reconstruí-los.72/1/2 recebendo 3 pequenas torna-se 72/1/5. Pagamentos exatos usam somente estoque do pagador, grandes→médias→pequenas. Sem troco:INSUFFICIENT_DENOMINATIONS, sem efeito. Exchange e rebalance 70/20/10 são explícitos/manuais; não mint. Rewards, escrows, contratos, leilões, recuperação, comércio e dívida passam pela facade física. Taxa compulsória/amortização automática pagam só a parcela representável, sem quebrar moedas; restante continua obrigação. [Especificação e casos](lunar/PHYSICAL_DENOMINATIONS.md).

Guilda compra/vende por políticas independentes/versionadas e estoque real. Minério tem buy/sell rate por grama, sem preço comercial derivado da massa da moeda. Preço/revisão não alteram Supply. Cutover principal informado ativo pelo usuário; nenhuma nova conversão. [Aplicação operacional](lunar/OPERATIONAL_GUILD_COMMERCE.md).


## Economia atual: pepitas individuais e Tesouro Real

Minério reside somente em LunarMineralLot HELD; moedas continuam LunarHolding 1/5/10 g, dívida separada. Spawn aprovado2%, pesos100..1000 g em faixas80/15/5, decisão persistente sem reroll. Coleta legítima gera DISCOVERED_MINERAL e lote, nunca moeda. Split exato é gratuito. Guilda paga floor(gramas×800/1000) inicialmente, com rate/revisão configuráveis e caixa real; mesmo ID muda de proprietário. Mint manual usa minério do Tesouro e conserva massa; burn/injection são excepcionais, nomeados e auditados.

Equação: gênese + descoberta + injeção administrativa − destruição = moedas + lotes HELD. Potencial procedural, dívida e pais consumidos ficam fora dessa soma. [Regras atuais e migração](lunar/VARIABLE_NUGGETS.md). As descrições de carteira assinada/pepitas fixas abaixo são históricas; após cutover não são segunda economia operacional.


> Atualização da continuação 0.9: [cutover operacional, migrações e validação](lunar/CUTOVER.md). O upgrade não converte o ambiente: confirmação administrativa ativa Lunar como fonte única. As descrições financeiras legadas e de conversão inativa abaixo registram a etapa anterior; após a confirmação, holdings Lunar e obrigações separadas são autoritativos. Discord segue estritamente read-only; Godot congelado.

> **Economia 0.7:** [sequência, geração, retenção, morte/recuperação, dívida e eventos](PROCEDURAL_ECONOMY_UPDATE.md). As regras novas substituem a perda de todos os itens por leilão das versões históricas abaixo.

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

## Implementação 2

Treinamento não concede XP, loot nem moedas. Masmorra secreta congela o direito de recompensa por combate: primeira conclusão 250 moedas/100 XP/cristal; repetições 1 moeda/zero XP/zero cristais, parâmetros monetários configuráveis. A contabilidade continua transferência do Tesouro, nunca emissão durante vitória. Uma tentativa derrotada em segredo não penaliza saldo, itens ou XP. Ajustes definitivos de balanceamento permanecem abertos.

## Primeiro andar 0.3

Pagamento centralizado na recepcionista, não na antiga curadora das salas. O resgate em lote é transacional e auditado por ledger; falta de orçamento não consome registros. Loot material usa stacks e morte por instância é única. Inimigos não reaparecem por recarregar/reconectar. Novas expedições são o mecanismo explícito de conteúdo repetível; treino não concede moedas, XP ou itens. Nenhuma política monetária ou emissão adicional foi implementada.


## Penalidade de fuga — 0.4

A fuga reduz direitos monetários ainda não resgatados, não moeda em circulação: restante=floor(total/2), perda=ceil(total/2). Todos os registros pendentes do personagem são considerados, sem filtrar pela expedição. A alocação do restante segue Battle.id; valores ajustados são a única fonte para resgate. Carteira e Tesouro permanecem intactos no ato da fuga. Ajustes antes/depois ficam no resultado da expedição; o ledger de transferências permanece exclusivo de pagamentos reais. XP atual é zerado sem reduzir nível ou itens. Nenhum banco/economia paralelo foi criado.

## Reservas de contratos — 0.8

Oferta líquida oficial agora inclui carteira assinada dos personagens + Tesouro + Banco Central + reservas de lances + reservas de contratos. Publicação transfere Tesouro → `contract:ID`; pagamento transfere pool → carteira, amortizando dívida pelo mecanismo normal; retirada devolve só orçamento livre. Direitos já concluídos mantêm reserva até pagamento. Ledger registra referências únicas de reserva/pagamento/cancelamento; nenhum contrato cria moedas implicitamente. Materiais coletados são itens finitos, sem conversão direta em moeda. Ver [COLLECTION_AND_CONTRACTS.md](COLLECTION_AND_CONTRACTS.md).


## Recursos Lunares procedurais 0.9

Ocorrência no mapa é potencial. Coleta válida registra DISCOVERED_MINERAL e aumenta Supply/holding na mesma massa, sem moedas. Gênese histórica continua segregada; Guilda compra pepitas com caixa existente e preço configurável independente do peso. Não cunha nem envia automaticamente ao Tesouro. Ver [lifecycle e auditoria](lunar/PROCEDURAL_RESOURCES.md).
