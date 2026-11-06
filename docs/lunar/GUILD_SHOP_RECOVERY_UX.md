# Loja agregada, preços em lote e barraca de recuperação

Continuação de `feature/lunar-physical-denominations-guild-commerce-0.9`, em `feature/guild-shop-recovery-ux-0.9`. Reutiliza economia Lunar, seleção física de moedas, ledger, recibos, custódia e permissões. Nenhum preço existente é redefinido por seed, startup ou migration.

## Loja do jogador

`guild_catalog.py` fornece `GET /economy/shop/catalog`, `POST /economy/shop/catalog/quote` e `POST /economy/shop/catalog/trade`. O catálogo não é truncado aos primeiros100 itens. Compra consulta somente Item/NPCStock realmente em custódia da Guilda. Venda consulta somente inventário elegível do personagem. Materiais empilháveis não únicos são agregados por ItemDefinition; equipamentos continuam selecionados por Item individual. Não se perde estado individual.

Uma operação informa exatamente um de `definition_id` ou `item_id`, `quantity` inteiro positivo seguro e `operation_type=buy|sell`. Trade acrescenta quote e UUID. IDs são transporte interno; cards do jogador apresentam nome, quantidade, preço unitário, seletor, total e ação. Busca filtra ambos os sentidos sem requests por tecla. Grade adapta colunas e controles de toque.

**TUDO** soma todas as pilhas realmente vendáveis. Exclui equipado, protegido, não transferível e custódias externas ao inventário. Não promete que a Guilda terá caixa para tudo: a cotação verifica o pagamento. **MÁXIMO** de compra considera estoque, preço, dívida, espaços livres, preenchimento das pilhas existentes, pepitas ocupando slots e moedas físicas disponíveis. Não divide moedas automaticamente.20 em duas grandes não paga19.

O algoritmo de máximo pesquisa no máximo10 classes de resíduos módulo `10/gcd(preço,10)` e faz busca binária em cada classe. Com denominações1/5/10, qualquer combinação de valor≥10 contém um subconjunto de valor10; a viabilidade em cada classe é um prefixo. Não percorre todas as unidades de um estoque grande. Teste compara o resultado com enumeração independente de combinações físicas, inclusive caixas sem pequenas/médias e preço zero autorizado.

Compra de uma pilha grande da Guilda preenche pilhas existentes e divide o restante respeitando `max_stack_size` do jogador. A Guilda não recebe limite99. O estoque continua finito; nenhum item é gerado para completar o catálogo.

Quote congela revisão/preço/quantidade e impressão digital de toda a seleção elegível. Trade reutiliza mutex financeiro, revalida a quote e a capacidade, transfere moedas físicas e todos os itens, grava GuildTradeReceipt e WorldEvent, e verifica auditoria na mesma transação. Repetição do UUID recupera recibo sem repetir efeito; payload diferente é conflito. Falha de qualquer passo reverte a transação. Endpoints anteriores de um Item continuam para compatibilidade.

Confirmação usa `<dialog>` estilizado, foco contido e Escape/cancelamento; sem `window.confirm/alert` nos fluxos de compra/venda de materiais ou minério. Total usa BigInt; o servidor continua autoritativo. Mudança da quote apresenta novos valores e exige nova confirmação. Falta de estoque, combinação de moedas, propriedade ou espaço apresenta mensagem humana. Minério continua negociado por peso/pepita inteira, em fluxo separado.

## Administração

Cada rebalanceamento, exchange, item, política mineral e lote possui justificativa local, ajuda visível e erro de mínimo10 caracteres após tentativa. Permissão `economy.manage`, prévia, confirmação e auditoria permanecem obrigatórias. Conflitos aparecem junto do painel comercial e os rascunhos são mantidos.

Editar vários itens mantém rascunhos com revisão capturada no início, antes/depois e flags. “Salvar este item” preserva edição individual. “Revisar alterações” chama `guild.batch_prices` com1–100 alterações distintas; a prévia lista cada política e sua justificativa comum. “Confirmar todas” exige revisão explícita do impacto. Editar o formulário após a prévia invalida essa revisão e exige outra. Conflito em qualquer item rejeita o lote inteiro, informando nomes e quantidades afetadas; não aplica uma parte silenciosamente.

Cada política mantém GuildPriceHistory próprio, com mesmo request_id/AdminOperation do lote. A PK ampliada `(request_id, policy_key)` permite esse relacionamento sem substituir IDs nem apagar histórico. Replays e confirmação concorrente continuam protegidos pelo serviço administrativo/mutex existente.

Reconhecimento de arbitragem aparece/exige confirmação somente quando compra e venda estão ativas e a venda está abaixo da compra. Gratuidade só aparece para preço zero ativo; minério também considera a política que permite preço arredondado zero quando o rate ativo pode produzi-lo. Operações desabilitadas não exigem reconhecimento sem risco real.

## Recuperação fora da Guilda

O serviço fica em `city1`, NPC em `(5,30)`, barraca em `(3,27)`, no sudoeste da vila52×36. Lona remendada/escura, cordas e figura encapuzada com rosto preto são desenhos originais do Phaser. Não há placa grande. Rótulo/interação aparecem ao aproximar; teclado/clique/toque usam o mesmo caminho autoritativo. É necessário ficar a distância Manhattan≤1 para interagir ou pagar.

A interface e `recovery.py` existentes continuam usando ownership, custódia, preço200% do valor-base, request_id, receipt, ledger e conta `npc:recovery`. Não há nova perda ou alteração econômica. Consulta de itens permanece possível de longe; recuperação efetiva exige o NPC.

Migration **e06a9c24f8bd**, após d91e2ab604c7: amplia a chave do histórico e adiciona metadados da barraca. A sala `recovery_hall`, suas conexões e visitas são preservadas como histórico arquivado. Runtime deixa de mostrar a sala/portas no mapa e em destinos novos; entrada direta é rejeitada com orientação. Fast travel legado para esse ID redireciona para a cidade, respeitando descoberta/combate/expedição. Ocupantes antigos são relocados com evento auditado; seus demais campos ficam intactos. Conflito com NPC personalizado ou combate ativo inesperado na sala antiga aborta a migration para revisão.

Não foi modificada migration histórica. Não há reset de inventário, políticas, moedas, supply ou ledger. Downgrade destrutivo é recusado; reversão exige procedimento de backup revisado.

## Limites

Discord remains read-only. Discord cannot control the character. Godot source PRESERVED; Windows/Android FROZEN. Textos antigos do cliente Godot sobre a sala são históricos; não houve evolução de UI nativa nem builds. Compatibilidade de API foi mantida quando segura.

Sem crafting, produção NPC, preço automático, reposição infinita, Boss Global, Echo ou política monetária automática. Validação/desempenho de produção e aplicação operacional desta migration não foram executados pelo agente. [Evidências e resultados atuais](DELIVERY_GUILD_SHOP_RECOVERY_UX_0.9.md) e [Windows PowerShell](OPERATIONAL_GUILD_SHOP_RECOVERY_UX.md).
