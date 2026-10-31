# Economia autônoma inicial dos NPCs

Implementação na branch `feature/autonomous-npc-economy-0.9`, baseada em `feature/guild-shop-recovery-ux-0.9`(66e88e5). Backend autoritativo, Web principal, Discord observacional e Godot preservado/congelado. Não existe segunda carteira nem segundo estoque: continuam **LunarAccount/LunarHolding/LunarEntry** e **Item/NPCStock**.

## Cadeia e origem dos recursos

Somente Folha Luminosa(`herb`), Cristal da Clareira(`crystal`) e Minério de Musgo(`ore`) entram nas receitas. Musgo é uma mercadoria comum: sua fundição não é cunhagem nem processamento de Minério Lunar. Pepitas Lunares, Supply, mint, burn e lastro não foram reimplementados.

| Produtor | Resultado | Ingredientes | Fator inicial |
|---|---|---|---|
|Alquimista|Poção de Cura Fraca|2 Folhas +1 Cristal|1,25|
|Alquimista|Poção de Cura|4 Folhas +2 Cristais|1,25|
|Alquimista|Poção de Energia|1 Folha +4 Cristais|1,25|
|Ferreiro|Lingote de Musgo|5 Minérios de Musgo|1,20|
|Ferreiro|Espada de Musgo|3 Lingotes|1,30|
|Ferreiro|Capacete de Musgo|2 Lingotes|1,30|
|Ferreiro|Peitoral de Musgo|5 Lingotes|1,30|
|Ferreiro|Luvas de Musgo|2 Lingotes|1,30|
|Ferreiro|Calças de Musgo|4 Lingotes|1,30|
|Ferreiro|Botas de Musgo|2 Lingotes|1,30|

Receitas persistem em NpcRecipe; ingredientes não guardam cópias de preços. Fatores persistem por NPC em inteiros de base10.000:12500/12000/13000. O editor aceita formato decimal legível e converte exatamente; o cálculo econômico permanece no servidor.

Alquimista novo recebe **1 de cada poção +7 Folhas +7 Cristais**. Ferreiro novo recebe **1 de cada peça +90 Minérios e0 Lingotes**. Cada produto final começa com capacidade/alvo2. Consumo determinístico completa2 de cada poção e2 de cada peça, sem saldo inicial adicional.

**Comerciante novo começa com estoque zero e caixa zero**, conforme decisão explícita do usuário. Todos os novos caixas começam em zero; a Guilda preserva seu caixa/mercadoria existentes. Não há financiamento, mercadoria ou emissão automática para preencher catálogo. Se uma conta histórica já possuir mercadoria, inicialização a adota e não sobrescreve sua propriedade/quantidade.

O seed concede somente o estoque histórico inicial autorizado dos produtores, uma vez por perfil, e registra NPC_INITIAL_STOCK com origem APPROVED_HISTORICAL_STOCK, quantidades e IDs. Não usa GENESIS_BACKING nem DISCOVERED_MINERAL para esses materiais comuns. Reinício não concede novamente7/7/90, produtos ou dinheiro.

## Políticas e defaults

| NPC/item | Capacidade inicial | Ponto de reposição | Pedido | Alvo | Lote/passo de venda |
|---|---:|---:|---:|---:|---:|
|Alquimista, cada matéria-prima|20|10|10|—|1/1; venda desativada|
|Alquimista, cada poção|2|—|—|2|1/1|
|Ferreiro, Minério de Musgo|100|10|10|—|1/1; venda desativada|
|Ferreiro, Lingote|100|—|—|0 de reserva|1/1; venda desativada|
|Ferreiro, cada equipamento|2|—|—|2|1/1|
|Comerciante, cada um dos3 materiais|100|10|10|—|10/10|

Capacidades100 e reserva0 onde não especificadas no documento são **defaults técnicos editáveis**, não balanceamento final. Não se aplica limite99 ao estoque institucional. Na mochila do jogador continuam valendo capacidade compartilhada com pepitas e max_stack_size existente.

Produção/purchase/sale e funcionamento podem ser pausados por perfil; políticas de cada item têm flags/revisão próprias. Ajustes do Alquimista não alteram o Ferreiro. Capacidade não pode ficar abaixo do estoque, alvo ou ponto de reposição; pedidos/lotes/passos são positivos. Configurar lote incompatível com a capacidade pode deixar uma reposição aguardando: o sistema não inventa espaço nem compra quantidade inválida.

## Ciclo autônomo

O lifespan FastAPI inicia o worker, independentemente de jogo/ADM/Discord abertos. Default30s, `Settings.npc_economy_tick_seconds`; ambiente de teste funcional desativa workers por TOWER_TEST_DATABASE=1. O teste HTTP dedicado usa banco novo e executa o worker normal com intervalo2s.

Cada ciclo usa o mutex financeiro existente e bucket UTC persistido em NpcProfile.last_cycle. Duas execuções/worker/reinícios no mesmo bucket não repetem efeitos. Não há recuperação ilimitada de ticks durante downtime: apenas o bucket atual é processado.

Ordem por produtor:

1. Calcula déficits dos produtos ativos.
2. Consome materiais já existentes e fabrica deterministicamente.
3. Atualiza custódia e histórico.
4. Avalia materiais com estoque **abaixo** do ponto de reposição.
5. Compra lote válido com caixa real ou registra espera.

Ferreiro funde sob demanda: reserva-alvo de Lingotes +ingotes necessários aos déficits das peças. Não fabrica Lingotes indefinidamente quando tudo está no alvo.90 Minérios →18 Lingotes →segunda unidade das6 peças. Há um limite técnico de1000 saídas por receita/ciclo, além dos limites físicos/capacidades, para evitar uma atualização administrativa grande monopolizar o servidor.

Alquimista/Ferreiro compram do Comerciante. Comerciante repõe a partir da Guilda, respeitando sua ativação de venda, estoque e preço. A quantidade de pedido é elevada ao lote mínimo/múltiplo válido; se não couber inteira, aguarda. Não há entrega parcial oculta, empréstimo ou geração de recursos.

Estados relevantes: sem ingredientes, fornecedor sem estoque, compra desativada, caixa insuficiente, falta de moedas exatas e capacidade insuficiente. Espera é persistente/visível. Log de espera é emitido na transição, sem repetir o mesmo aviso a cada tick.

## Preços e revisões

A referência dos3 materiais é **GuildItemPolicy.buy_price_units** já existente, sem criar outra tabela de preços-base. Compra/venda da Guilda continuam independentes. O campo sell_price_units existente continua sendo a **base por unidade**, sem sobrescrita no startup.

- Guilda revende matéria-prima: `base_venda × quantidade + margem fixa`, inicialmente1 pequena por operação.
- Comerciante: `referência × quantidade + margem fixa`, inicialmente1 pequena por pedido.
- Poção: `ceil(custo dos ingredientes × fator de alquimia)`.
- Lingote: `ceil(5 × referência do Minério × fator de fundição)`.
- Equipamento: `ceil(quantidade de Lingotes × preço do Lingote × fator de ferraria)`.

Arredondamento central ceil_price usa somente inteiros e retorna unidades representáveis pela menor moeda.20 de base +1 de margem =21, nunca30; base100 +1 =101, nunca120. Valores em moedas são convertidos pelo facade financeiro para mg;1/5/10g continuam peças físicas independentes. A margem faz parte do total; não obriga decomposição fictícia em moedas pequenas.

Não se recobra margem por unidade nem se aplica percentual a cada intermediário. O preço não cresce pelo histórico de proprietários. Não há ajuste automático de lucratividade: uma base de revenda da Guilda acima da referência do Comerciante pode tornar a cadeia deficitária. A Administração decide os parâmetros, com impacto/valores visíveis; caixa finito limita as operações.

Mudança de referência/fator/margem gera MarketRevision imutável com snapshot derivado. Sem mudança real, não há revisão repetida; o worker lê a revisão persistida, sem recalcular preços a cada tick/frame. Guild item/batch prices e configuração NPC passam pelo mesmo pipeline administrativo que atualiza o mercado.

## Comércio, persistência e concorrência

O catálogo agregado/checkout foi generalizado para os3 balcões. Materiais e poções empilháveis são agregados com segurança; equipamentos continuam Item individuais. Uma única transferência financeira e os movimentos materiais formam a mesma transação. Falha de qualquer passo reverte moedas, custódia e recibo.

Quote vincula seleção física, quantidade, proprietário, perfil/política/revisões e mercado. Alteração de preço/lote/ativação/estoque invalida a confirmação. UUID repetido retorna recibo persistente; outra tentativa de comprar o último produto falha sem duplicação. Caminho NPC legado não pode ignorar o balcão, lote ou capacidade dos perfis novos.

Não há carteira negativa nem estoque negativo. Entrada de material por reposição, transferência administrativa ou writer legado npc.stock verifica a capacidade do destinatário. Item consumido pode permanecer arquivado como destroyed, preservando identidade/histórico; não faz parte do estoque disponível.

## Jogo e Administração

Na vila city1: Comerciante(34,8), Alquimista(36,15), Ferreiro(16,22), sprites originais leves. Clique/toque, E ou **Lojas da vila → Ir até** usam caminhada real e aproximação≤1. Consulta remota não autoriza compra. Guilda e recuperação continuam em seus serviços existentes.

Lojas mostram estoque disponível, busca, lotes, controles de quantidade, total calculado pelo servidor, MÁXIMO com moedas/capacidade reais e confirmação integrada. Sem estoque, não há compra. Uma alteração de lote chega sem alteração de código; uma quote desatualizada exige nova revisão/confirmação.

Central ADM → **Economia dos NPCs**: tipo/status, carteira por denominação, estoque/políticas, receitas, fatores, produção/compras/vendas, última atualização e histórico. Editor captura revisões e permite alterar perfil e várias políticas no mesmo lote, com justificativa≥10, prévia antes/depois, preços afetados, confirmação, permissão economy.manage, UUID e auditoria.

Também permite transferir **mercadoria existente** entre instituições e financiar caixas com a ação Royal de transferência de **moedas existentes**. Não há botão de gerar estoque/dinheiro. Royal → Guilda → Preços mantém compra/venda/flags e agora mostra base, margem e total para1 unidade; a margem é editada no módulo NPC.

Jogo/ADM usam NpcEconomyState/NpcPolicy e o mesmo serviço de preços. Histórico administrativo contém atores/quantidades/revisões/recibos/timestamps/request IDs e é omitido na resposta pública. APIs refletem o commit imediatamente; clientes ativos consultam novamente após ações e fazem polling2,5s/3s. Não há fórmula econômica duplicada na UI.

## APIs

- `GET /economy/npcs`: estado público dos3 balcões, sem histórico administrativo.
- `GET /economy/npcs/{npc}/shop`: catálogo real compartilhado.
- `POST /economy/npcs/{npc}/quote|trade`: mesmos corpos estritos do catálogo, com owner/preço resolvidos pelo servidor.
- `POST /economy/npcs/{npc}/interact`: aproximação autoritativa.
- `GET /admin/npc-economy`: snapshot consistente/read permission e detalhes privados.
- `npc.configure`, `npc.stock_transfer`: ações do AdminService existente.

Endoints financeiros herdam os limites PostgreSQL de requisições, sessão/autorização e mutex. Registros NPC usam WorldEvent com timestamp/request ID e proteção append-only para seus tipos; MarketRevision também é imutável. LunarEntry/AdminOperation/receipts existentes permanecem a auditoria monetária/autorização. Logs JSON registram mudanças reais, sem segredos ou spam em idle.

## Compatibilidade e limites

Migration7167b684d5f7 após e06a9c24f8bd cria4 tabelas e equipment_slot opcional em ItemDefinition; não modifica migrations históricas. Seed inicializa somente entidades ausentes. Seis peças usam slots independentes; a Espada de Aprendiz continua protegida. O documento não especifica bônus de combate dos equipamentos nem efeitos de uso das poções: não foram inventados. Equipar/persistir as6 peças e comprar/produzir/guardar as poções são funcionais; consumo/atributos novos exigem regras futuras. Bônus novos começam neutros.

Discord remains read-only. Discord cannot control the character. Godot source PRESERVED, Windows/Android FROZEN, sem APK/EXE. Novos balcões não foram portados ao cliente nativo congelado. Sem outros materiais/receitas, classes, market maker, inflação por revendas, Boss/Echo ou política automática do rei.

Usar um worker HTTP para a presença WebSocket atual; broker continua necessário antes de ampliar presença para múltiplos workers. Mutex global, catálogo completo e auditoria crescente são limites conhecidos de escala, sem Redis obrigatório. [Entrega/evidências](DELIVERY_NPC_ECONOMY_0.9.md) · [Windows e validação manual](OPERATIONAL_NPC_ECONOMY.md).
