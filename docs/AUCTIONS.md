# Espólios, proteção e recuperação

> **Atualização 0.7 dos leilões:** [sequência, geração, retenção, morte/recuperação, dívida e eventos](PROCEDURAL_ECONOMY_UPDATE.md). As regras novas substituem a perda de todos os itens por leilão das versões históricas abaixo.

O leilão permanece exclusivo de itens perdidos em morte procedural. Não é mercado geral. Reserva/diferença/devolução, escrow, entrega única, Tesouro/sink e prazo configurável de 24h da 0.5 permanecem.

A API de anúncio/detalhe retorna somente informações reais: ID, item/quantidade original, descrição, tipo, poder da definição, proteção, origem/death_event_id, preço inicial/atual, incremento mínimo 1, próximo lance, início/fim, situação e destino financeiro. `GET /auctions/{id}` acrescenta histórico de lances com licitante, valor exato e timestamp. Raridade, durabilidade e efeitos especiais não existentes **não** são inventados. Interface Godot e web exibem os campos suportados e a regra de entrega.

## Espada de Aprendiz

Identidade protegida é a definição estável **sword**, usada pelo equipamento inicial; não o texto do nome nem todo item de tipo weapon. A migração marca `death_transferable=false` e uma constraint impede desprotegê-la. Seed de novas instalações também marca false. Outras espadas continuam pelas regras normais. A perda de inventário exclui esse ID e definições estruturais não transferíveis. Espada permanece equipada ou na mochila após a morte.

Espadas históricas ainda em custódia ficam com negociação suspensa: lances e resolução rejeitam item protegido, e o sweeper não o entrega. A reserva existente continua contabilizada até resolução individual. A migração **não** devolve itens, cancela lotes ou reembolsa indiscriminadamente.

## Resolução individual no painel

1. Operador consulta Itens → Diagnóstico das espadas iniciais, que mostra item original, antigo dono, dono atual/custódia, leilão, estado e maior lance; lances completos ficam no módulo Leilões.
2. Se original está em custódia OPEN/CLOSED/UNSOLD: preparar `items.recover_starter` com o ID real do leilão e justificativa. Prévia mostra item/donos/reserva. Confirmar devolve reserva ao maior licitante pela função econômica central (inclusive amortizando dívida), cancela o lote e retorna **o mesmo ID** ao antigo proprietário, sem duplicação.
3. Se já foi entregue legitimamente: `items.recover_starter` rejeita. `items.replace_starter` permite **reposição separada e autorizada**, desde que o antigo dono ainda não tenha espada inicial. O comprador mantém o original; a criação do substituto é auditada e idempotente. Não há compensação monetária automática.
4. Repetir confirmação bem-sucedida retorna o resultado anterior. Mudança no item/lance/proprietário após a prévia exige nova revisão. Não apagar histórico de AuctionBid, Ledger ou DeathEvent.

Cancelamento administrativo geral (`auctions.cancel`) reembolsa reserva e exige decidir entre manter item arquivado em custódia ou devolver ao antigo dono. Não é exclusão de registros. O status CANCELLED não destrói o item. Histórico de morte continua imutável; a intervenção administrativa correlacionada explica a correção posterior.

Diagnóstico observado nesta nuvem antes da atualização: leilão **1**, item **18**, antigo proprietário **9**, OPEN, sem lances. A recuperação individual foi executada pelo fluxo administrativo de prévia/confirmação, com autorização temporária registrada e revogada ao terminar. O mesmo item 18 retornou à mochila do proprietário 9; leilão 1 ficou CANCELLED, sem alterar moeda, lances ou recibo de morte. Operação auditada: `e3343461-3584-4963-bb20-ad908f28c017`. Não houve recuperação em lote nem retirada de comprador. A ferramenta não depende desses IDs e consulta o estado atual antes de cada confirmação.
