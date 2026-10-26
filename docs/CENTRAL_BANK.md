# Banco Central e economia oficial

A instituição é `CentralBank(id=1)`, separada de qualquer administrador/personagem. Migração/seed iniciam sua reserva em **zero**, sem reemitir o Tesouro ou criar moeda nova. A Guilda real mantém Treasury(id=1). A arquitetura permite novas instituições depois, mas não inventa guildas.

Operações oficializadas no painel:

- `bank.transfer`: debita origem e credita destino; não altera oferta. Contas válidas: central_bank, treasury, character:ID. Não permite origem=destino, dívida adicional por transferência nem saldo institucional negativo.
- `bank.issue`: emissão explícita, com quantidade, destino, justificativa, prévia de impacto e confirmação; ledger de mint para o destino. Não duplica por replay.
- `bank.burn`: retira saldo disponível existente, registra destino burn e reduz oferta. Não queima valor reservado ou saldo inexistente.
- Sugestões: compara orçamento da Guilda com obrigações pendentes e recomenda avaliação humana quando insuficiente. **Nenhuma emissão automática**, inclusive por preço/inflação.

Todas usam a transação administrativa, permissões e UUID, com locks de recursos e ledger. Valores NUMERIC/inteiros arbitrariamente grandes mantêm exatidão; a interface usa strings para quantidades monetárias. Um crédito oficial a personagem chama a mesma função que pagamentos/devoluções e amortiza dívida automaticamente.

## Indicadores reais

Saldo líquido oficial, emissão histórica/inicial, emissão administrativa, retiradas/sink, reservas do Banco Central, Tesouro, dinheiro disponível positivo de jogadores, dívida médica, escrow de lances e obrigações pendentes. Há distribuição de riqueza até 50 personagens e fluxos agregados dos últimos 30 dias com registros (entradas/saídas da Guilda, volume liquidado em leilão, emissão/retirada), além do ledger paginado. Não se trata de um índice de preços; inflação e comparação de preços estão marcadas como indisponíveis por falta de mercado/série comparável.

Dívida é saldo assinado, não segunda moeda. O painel distingue dinheiro disponível, reserva, obrigação e total líquido. A diferença de reconciliação compara saldos oficiais com emissão inicial + mint − burn − sink. Pagamento de uma obrigação ainda não emitida é transferência do Tesouro, não criação livre.

## Recursos administrativos isolados

AdminTestCredit é um contador próprio por conta administrativa, criado/consumido somente por operações auditadas sandbox. Não aparece no saldo Character.coins, não possui Item negociável, não é destino/origem de contas oficiais, não é aceito por lances e não entra no total oficial. A tela o identifica como crédito de teste não negociável; não há conversão para ouro. Ter papel ADM não concede ouro infinito ao personagem.

## Compatibilidade 0.8

Banco Central continua manual e preservado. Contratos não o tornam autônomo: são financiados pelo Tesouro existente e o pool `contract:ID` integra a reconciliação oficial. Créditos sandbox continuam excluídos. Não há emissão automática para pagar contratos sem orçamento; publicação insuficiente reverte integralmente.
