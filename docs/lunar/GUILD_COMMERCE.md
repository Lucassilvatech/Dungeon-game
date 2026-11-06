# Preços independentes e comércio físico da Guilda

## Evolução NPC atual

Nesta etapa a revenda de matérias-primas da Guilda acrescenta uma margem fixa configurável por operação à base de venda existente; valores antigos não são sobrescritos e recibos históricos continuam reexecutáveis sem novo efeito. O catálogo/checkout atende também os3 balcões novos, com preço/lote/revisão autoritativos. [Regras completas](NPC_ECONOMY.md). Descrições anteriores de ausência de produção NPC abaixo são históricas.


## Interface atual: loja agregada e preços em lote

A Web usa o novo catálogo `/economy/shop/catalog`, somando materiais elegíveis por definição e mantendo equipamento individual. TUDO/MAX, confirmações integradas e edição administrativa individual/em lote estão descritos em [GUILD_SHOP_RECOVERY_UX.md](GUILD_SHOP_RECOVERY_UX.md). Os endpoints por Item abaixo permanecem como compatibilidade. Migration e06a9c24f8bd amplia a identidade de GuildPriceHistory para(request_id,policy_key), preservando registros anteriores e vinculando cada política ao mesmo lote. Preços configurados não são sobrescritos.


Políticas de preço são separadas de ItemDefinition. `GuildItemPolicy` guarda definition_id, buy_price_units, sell_price_units, buy_enabled, sell_enabled, revision, updated_at e updated_by. Preços inteiros por unidade para stacks e por peça para equipamento. Não existe margem automática nem fórmula que derive venda da compra.

Migração aditiva **d91e2ab604c7**, após ca343e37b4ca: cria políticas, `GuildPriceHistory` e `GuildTradeReceipt`, com FKs/índices/checks e triggers append-only de histórico/recibos. Amplia a constraint do preço em NPCStock para permitir zero, sem mudar nenhum registro antigo. Políticas iniciais preservam avaliação de compra anterior; revenda histórica só é ativada quando estoque da Guilda tem preço unitário inteiro/unívoco. Ambiguidade mantém venda desativada e preço0 até decisão administrativa. Seed cria somente política ausente; não repõe estoque nem muda políticas existentes.

## Administração

Administração do Rei → Guilda integra Caixa, Rebalanceamento, Trocar denominações, Preços, Estoque, Histórico e Comércio. Tabela mostra item/estoque/compra/venda/flags/revisão. Edição permite mudar só compra, só venda, ambas ou flags independentes, com economy.manage, motivo, prévia/antes/depois, confirmação e recibo. Cada atualização incrementa revisão; o histórico persiste valores anteriores/novos, flags, revisão, administrador, motivo, data e request_id. Triggers proíbem editar/apagar esses históricos.

Zero não significa disabled. Habilitar preço zero exige acknowledge_free. Compra acima da venda mostra POSSIBLE_ARBITRAGE e exige acknowledge_arbitrage, sem bloquear uma decisão consciente. Essas confirmações são separadas da confirmação final de impacto. Alteração de preço nunca cria ou transfere item/moeda/minério.

## Estoque e checkout

Reutiliza **Item/NPCStock**, sem segundo estoque. Item sob custódia da Guilda tem owner=NULL / location=npc e NPCStock.account_id=guild. Compra de jogador paga moedas Guilda→jogador e move item/quantidade jogador→Guilda. Venda ao jogador paga moedas jogador→Guilda e move mercadoria existente. Sem estoque:OUT_OF_STOCK; sem peças exatas:INSUFFICIENT_DENOMINATIONS. Tudo na mesma transação; falha de capacidade, autorização, quote ou auditoria reverte dinheiro, item e recibo.

Stack é cotado por unidade×quantidade. Transferência parcial cria registro material separado e o recibo liga ID original/ID movido/quantidade anterior. Ao comprar, pilhas existentes podem receber unidades até o limite; o registro totalmente absorvido fica em custódia histórica destruída, sem duplicar estoque disponível. Equipamento conserva identidade, sem split e com quantidade1. Propriedade, equipado, proteção, death_transferable, custódia e capacidade conjunta com pepitas são conferidos. Espada de Aprendiz continua protegida mesmo se houver preço.

`GET /economy/shop` apresenta ofertas e estoque, unit_price_units, preço total, flags/revisão e caixa físico. `POST /economy/shop/quote` aceita item_id, quantidade e buy/sell, sem preço do cliente. `POST /economy/shop/buy|sell` aceita request_id, item_id, quantidade e quote. Corpos estritos, autorização/localização na Guilda e ausência de combate; compras continuam impedidas com dívida ativa, conforme a regra já existente.

Quotes vinculam item, quantidade, direção, unit_price, total, price_revision e snapshot de quantidade/propriedade/custódia. Mudança de preço e sua reversão continuam invalidando quote antigo. Checkout recalcula sob mutex; alteração de estoque também invalida ou recusa. Receipt é persistente e vinculado aos parâmetros, com pagamento/IDs/material. Mesma requisição retorna replay mesmo se o preço mudou depois; requisição diferente não compra estoque já consumido. Registros históricos NPC_SALE/NPC_PURCHASE anteriores continuam com replay compatível.

Lojas NPC já existentes mantêm seu caminho finito anterior; não recebem reposição ou produção autônoma. A Guilda usa a política nova, não o preço histórico armazenado no NPCStock.

## Minério individual por grama

Preserva `lunar_guild_buy_rate_milliunits_per_gram=800`, acrescenta sell_rate inicial0, buy_enabled=true, sell_enabled=false e allow_zero_price=false. Venda de minério pela Guilda começa desativada, sem inventar preço final. Configure as chaves explicitamente na Administração. Histórico de rates/flags e revisões usa o mesmo workflow; alterações isoladas via economy.configure também deixam histórico equivalente.

Preço:floor(gramas×rate/1000). Buy e sell são independentes. Lote selecionado é **inteiro**, real e HELD do proprietário correto; mantém o mesmo ID ao mudar de custódia. Não há split escondido, geração de lote durante quote, refino, produção NPC ou cunhagem automática. Fragmento cujo preço arredonda para zero só é negociável se gratuidade tiver sido explicitamente habilitada/confirmada.

`GET /lunar/guild-quotes` retorna quotes de compra da Guilda e guild_quotes de venda dela, com lot_id, gramas/mg, direção, rate/revisão, preço, proprietário/estado, hash e seleção/liquidez real do pagador. `POST /lunar/guild-sell` e `/lunar/guild-buy` aceitam somente lot_id/quote/request_id. Ownership, capacidade, caixa, denominações e ledger são atômicos. Origem, pai e source_entry do minério não mudam na venda.

Web distingue “Guilda compra” e “Guilda vende”, permite quantidade por item, exibe pending/erros e confirmação por preço atual. Interfaces de carteira, comércio e administração testadas em desktop/390 px, sem hover obrigatório. Discord apenas observa carteira/itens/lotes próprios; nenhum comando financeiro novo. Godot permanece congelado.

[Regras físicas](PHYSICAL_DENOMINATIONS.md) · [Comandos operacionais e Windows](OPERATIONAL_GUILD_COMMERCE.md) · [Entrega/testes](DELIVERY_PHYSICAL_COMMERCE_0.9.md).
