# Diagnóstico anterior à implementação — economia autônoma NPC

Base limpa: feature/guild-shop-recovery-ux-0.9, HEAD66e88e5d461898054792db7597a7d94bfa6f3569. Status/branch/log/fetch conferidos antes de alterações. Nova feature/autonomous-npc-economy-0.9; main e base preservadas, sem merge/force push.

Documento completo do usuário lido(65 seções). Estoques iniciais dos produtores autorizados: Alquimista1 de cada poção+7folhas+7cristais; Ferreiro1 de cada peça+90minérios. Comerciante/carteiras novas:zero, conforme resposta explícita do usuário. Não emitir moeda para financiar reposição. Origem material inicial deve ficar auditada uma única vez; abastecimento posterior apenas físico/financiado.

Já existem finance/Lunar, Item/NPCStock, GuildItemPolicy, GuildTradeReceipt, catálogo/quote/checkout agregado, capacidade com pepitas, AdminService preview/confirm/revisão/razão e sweeper assíncrono. npc_economy atual só faz compra/venda finita; não tem receitas, produção, reposição, lotes nem revisão derivada. Reutilizar esses serviços, sem novo dinheiro/estoque paralelo.

Plano de domínio: perfis/políticas/receitas persistentes e revisão de preços imutável; referências das três matérias-primas seguem GuildItemPolicy.buy_price_units existente. Fatores racionais inteiros e arredondamento para cima na menor moeda. Compra/venda da Guilda continuam independentes: preço de venda configurado é a base, e a margem fixa é acrescentada uma vez por operação de revenda de matéria-prima; não sobrescrever preços históricos. Comerciante usa referência corrente×quantidade+uma margem por pedido. Preços de produtos dependem exclusivamente da receita/fator, sem margem percentual intermediária.

Job servidor independente de UI, mutex financeiro e ciclo persistente/idempotente: primeiro produção determinística, depois reposição em lotes válidos. Ferreiro funde sob demanda para déficits das seis peças; não produz lingotes indefinidamente quando todas estão no alvo. Compras usam moedas exatas: falta de caixa/troco/mercadoria/capacidade mantém espera. Sem catch-up ilimitado depois de reinício.

Políticas não especificadas terão defaults técnicos editáveis/conservadores: matéria-prima Ferreiro capacidade100/ponto10/pedido10; Comerciante capacidade100/ponto10/pedido10/lote10; lingotes capacidade100/reserva-alvo0. Alquimista20/10/10 e produtosalvo2. Novos equipamentos têm slots próprios; bônus não especificados permanecem neutros, sem inventar balanceamento. Não implementar consumo/efeitos de poções sem regras definidas; aquisição/estoque/produção são reais.

Migração aditiva após e06a9c24f8bd: modelos/configuração e campo de slot opcional em ItemDefinition. Seed somente entidades novas, sem redefinir carteiras, preços, itens ou políticas existentes. História NPC aproveita WorldEvent com timestamp/atores/revisões e proteção append-only para novos tipos; fluxos monetários continuam no ledger existente.

Integração: APIs compartilhadas jogo/ADM, lojas na vila com aproximação autoritativa, painel na Central existente; editor de políticas e fatores com preview/confirm/permissão/razão/revisões, transferências materiais auditadas sem criação. Validar PostgreSQL real, concorrência/rollback/reinício, upgrades/cópia privada, frontend/build e Chromium390px. Discord read-only; Godot congelado; sem Boss/Echo/novos materiais/receitas fora do documento.
