# Denominações físicas e liquidez — 0.9

[Diagnóstico antes da programação](PHYSICAL_DENOMINATIONS_DIAGNOSIS.md) · [Aplicação operacional/Windows](OPERATIONAL_GUILD_COMMERCE.md) · [Entrega e validação](DELIVERY_PHYSICAL_COMMERCE_0.9.md).

## Fonte real do defeito e correção

`finance.move` reconstruía origem/destino usando `compose(total_mg)`. Isso preservava massa, mas trocava denominações a cada débito/crédito. Agora seleciona peças do pagador por `lunar.select_coins` e transfere as mesmas quantidades. `compose` permanece **somente no cutover histórico**; não há normalização de carteiras operacionais.

`LunarWallet` já lia holdings. A tela antiga de minério calculava uma decomposição ideal do preço; agora apresenta a seleção/liquidez fornecida pelo servidor. Total é derivado de quantidades reais; não serve para reconstruí-las. A API retorna assets.coin_small/medium/large.quantity e coin_total_weight_mg, lotes e massa mineral.

Moedas físicas fungíveis por denominação: pequena1 g/1000 mg/1 unidade; média5 g/5000 mg/5 unidades; grande10 g/10000 mg/10 unidades. Quantidades/massas são inteiras; UI usa strings/BigInt para valores monetários. Percentuais de exibição não participam de cálculo de dinheiro.

Regressão obrigatória: **72 grandes +1 média +2 pequenas**, recebendo **3 pequenas**, resulta em **72/1/5**, total 730 g. Nunca em73/0/0. Recebimentos, transferências, mint e burn conservam suas quantidades explícitas.

## Pagamentos exatos e falta de troco

Seleção limitada ao estoque, em ordem grande→média→pequena. Para1/5/10, o greedy é exato quando existe combinação e prioriza o maior número possível de grandes, depois médias. Não faz overpayment, não inventa troco, crédito ou exchange.

Exemplos com peças disponíveis:10→1G;15→1G1M;17→1G1M2P;19→1G1M4P;27→2G1M2P;100→10G. Sem grandes,19 com 4M20P usa3M4P. Com1G0M20P usa1G9P. Com5G0M0P, pagar1 é impossível mesmo com valor total 50: **INSUFFICIENT_DENOMINATIONS**, transação revertida.

Wallet, oferta de compra/venda e Administração distinguem total monetário da composição/liquidez. `payment_quote` retorna peças existentes ou erro; checkout recalcula sob mutex, sem confiar nessa leitura anterior como reserva.

`lunar.post` rejeita troca de ativos monetários disfarçada em um pagamento de massa líquida zero. Mudança global de denominação exige operação explícita de mint/exchange/rebalance; burn/injection têm origem/destruição explícitas. Postings e holdings são conciliados; ledger histórico permanece imutável.

## Exchange e rebalanceamento explícitos

`DENOMINATION_EXCHANGE` exige inputs reais, outputs de mesma massa, UUID/receipt e replay. Conferência de inputs ocorre antes da compensação líquida: não se pode declarar moedas inexistentes que seriam canceladas pelos outputs. Administração exige economy.manage, razão, prévia, confirmação e auditoria. Replays de `COIN_DENOMINATION_EXCHANGE` da versão anterior são reconhecidos pelo fingerprint histórico exato, sem comparar com o estoque atual ou reexecutar a troca.

`GUILD_DENOMINATION_REBALANCE` é exchange manual, **não MINT/DISCOVERED_MINERAL/ADMIN_INJECTION**. Meta70/20/10 por massa/valor: grande mais próxima de 70%, depois média mais próxima de 20% limitada ao restante, pequenas absorvem o resíduo. Arredondamento é inteiro ao múltiplo representável mais próximo, empate para baixo. Soma exata, sem float.

Para19.498 g: grande13650 g→1365 peças; média3900 g→780 peças; pequena1948 g→1948 peças. Total19.498.000 mg. Após transferências, a distribuição pode se afastar da meta; nenhuma correção automática é feita.

Chave inicial persistente **GUILD_DENOMINATION_REBALANCE_V1**; preview captura conta/composição/total/meta/fingerprint. Apply verifica tudo novamente, usa mutex e registra antes/depois/diferença0 mg. V1 nunca vira tarefa recorrente. Novas decisões manuais usam outros UUIDs. Somente Guilda é alvo do rebalanceamento; jogadores, Tesouro, NPCs e escrows não são reescritos.

## Rewards, escrows, dívida e outros writers

A facade física é reutilizada por `economy.ledger`, pagamentos de recompensas, reserva/pagamento/reembolso de contratos, bid/outbid/release/settlement de leilões, recuperação, comércio e transferências administrativas. Ex.: escrow recebe1G1M2P e devolve as mesmas peças, sem normalização. Uma reserva suficiente em valor pode faltar em liquidez para uma parcela; nesse caso o pagamento exato falha e requer uma decisão explícita de exchange por operador autorizado, sem perda do direito.

Pagamento manual de dívida exige valor exato representável e reduz obrigação/recebível junto à transferência real. **Dívida não é moeda negativa**.

Taxa médica compulsória: paga o maior subconjunto representável até a taxa, financiando o restante conforme o limite já existente. Exemplo3 grandes/taxa 100:30reais ao Tesouro,70de dívida. Se só possui1grande e taxa 7, não quebra a grande:0pago/7financiado. Amortização automática de recebimentos usa somente peças efetivamente recebidas; parcela não representável continua dívida. Isso evita impedir a morte por falta de troco ou inventar uma troca para cobrar dívida. Confisco financiado é adiado se a origem não consegue pagar exatamente a avaliação.

O caminho legado continua somente onde o cutover não foi ativado. No ambiente do usuário ele já está ativo; esta entrega não cria outra conversão. Replays de vendas/compras históricas da Guilda preservam recibos anteriores sem transferir novamente.

## Conservação

`GENESIS_BACKING + DISCOVERED_MINERAL + ADMIN_INJECTION − DESTROYED = moedas físicas + lotes HELD` em mg. Potencial procedural, dívidas e pais consumidos não integram a soma. Pagamento preserva cada denominação entre contas; exchange/rebalance preservam massa, sem Supply novo. Mint transforma minério existente; burn registra as peças/gramas destruídos. Preço não movimenta nenhum ativo.

Há mutex financeiro global, ordem de locks anterior preservada, recibos persistentes e constraints/triggers. Isso prioriza consistência; auditoria histórica e contenção precisam ser medidas em carga real. Não foram introduzidos serviços obrigatórios ou automação monetária.
