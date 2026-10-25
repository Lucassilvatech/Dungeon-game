# Contabilidade e concorrência

Ledger existente permanece a fonte das transferências oficiais; não foi substituído ou apagado. Cada operação nova tem referência única admin:UUID, com origem/destino e valor exato. Emissão usa source=mint; retirada destination=burn; leilão pode usar sink configurado. Créditos de teste vivem fora desse livro-razão oficial.

Reconciliação:

```text
líquido observado = soma de carteiras ASSINADAS + Treasury + CentralBank + escrow OPEN/CLOSED
líquido esperado = emissão inicial + emissões mint - retiradas burn - sink
```

Pendências da Guilda são obrigações, separadas dessa soma. A taxa médica transfere o débito efetivamente aplicado entre carteira assinada e Tesouro; o piso e a parte limitada/waived permanecem. Reserva tira ouro disponível e o mantém em escrow; ser superado devolve pela função de crédito. Liquidação tira escrow e credita Tesouro/sink, nunca quem perdeu o item. Cancelamento tira escrow e reembolsa uma única vez. Não contar histórico SETTLED/CANCELLED como reserva atual.

Comandos administrativos e leilões tomam o mutex transacional 7312027 antes de bloquear participantes. Carteiras são bloqueadas em ordem crescente antes de item/Tesouro/Banco Central; lotes de vencimento bloqueiam todos os vencedores antes do primeiro Tesouro. Morte segura personagem e cria somente novos leilões; não busca mutex de leilão existente. Confirmação reconsulta o estado após locks, expira a identity map e rejeita prévia alterada. Assim o retorno de outra transação não autoriza um saldo antigo.

AdminOperation registra PREVIEW, COMMITTED ou FAILED, ator da sessão, motivo, antes/depois e horários. Commit repetido devolve recibo sem alterar ouro, itens ou estado. Confirmar com outra identidade, token inválido, papel revogado ou dados obsoletos é rejeitado. Savepoint garante rollback de efeitos de uma rejeição, preservando seu resultado auditável. Falha inesperada reverte a transação externa; logs do servidor permitem investigação sem gravar segredos.

Históricos de AuctionBid, DeathEvent, Ledger e eventos de item não são excluídos pela ferramenta de recuperação. Reposição legítima cria outro ID de item com referência à operação; recuperação de custódia preserva o ID original. Antes/depois de criação mostra inventário e de spawn mostra as instâncias, permitindo localizar exatamente os registros novos.
