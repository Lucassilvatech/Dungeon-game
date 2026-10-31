# Central Administrativa web

## Economia dos NPCs

Novo módulo na Central existente: estoques reais, caixas, receitas, preços/revisão, estado/histórico, fatores/margens/lotes/capacidades/alvos e flags. Edição de várias políticas por NPC é atômica e exige economy.manage, razão≥10, prévia/confirm e revisão original. Há transferência de estoque existente e financiamento real usando ações protegidas existentes. [Procedimento](lunar/OPERATIONAL_NPC_ECONOMY.md).


## Preços individuais e em lote — Guilda

Cada operação comercial tem justificativa local≥10 caracteres. Salvar este item ou revisar lote; conflitos de revisão rejeitam tudo e preservam rascunhos. Permissão economy.manage, preview, confirmação, UUID e auditoria permanecem. Histórico registra cada política sob UUID comum. Reconhecimento de arbitragem/gratuidade apenas quando risco ativo existe. [Fluxo e schema](lunar/GUILD_SHOP_RECOVERY_UX.md).


## Caixa físico e preços da Guilda

Administração do Rei → Guilda reúne Caixa, Rebalanceamento, Trocar denominações, Preços, Estoque, Histórico de preços e Comércio. Leituras economy.read; royal.exchange/guild.rebalance/guild.item_prices/guild.mineral_prices exigem economy.manage, motivo, prévia, confirmação, UUID/receipt e auditoria. Preços buy/sell independentes; revisão/histórico; flags distintas de preço zero; gratuidade/arbitragem exigem confirmação consciente. Estoque é operação material separada. [Manual Windows/CLI e aplicação inicial V1](lunar/OPERATIONAL_GUILD_COMMERCE.md).


## Administração do Rei: interface econômica principal 0.9

O menu **Administração do Rei** oferece Visão geral, Minério, Moedas, Cunhagem, Jogadores, Guilda, Tesouro, Auditoria, Configuração e Histórico administrativo. O Banco Central antigo passa a **Compatibilidade legada**, somente leitura. Leituras economy.read; mutações economy.manage com razão, prévia vinculada ao estado, confirmação, recibo e auditoria. Burn/injection exigem flag e DESTRUIR/INJETAR; não são emissão automática. [Manual completo e execução Windows](lunar/ROYAL_ADMINISTRATION.md). As instruções antigas sobre emissão abstrata do Banco Central abaixo não orientam o fluxo operacional pós-cutover.


Acesso de desenvolvimento: `http://localhost:8080/admin`. Entrada/bundle separados do jogo; Godot não possui privilégios administrativos. A navegação oferece Visão geral, Banco Central, Economia, Guildas, Jogadores, Itens, Monstros, Leilões, Mundo/eventos e Auditoria. A aplicação não tem senha padrão nem transforma a primeira conta em administrador.

## Primeiro acesso

Crie uma conta normal pelo jogo e conceda papel explicitamente no terminal do operador:

```powershell
docker compose exec backend python -m app.admin_cli SEU_USUARIO owner --reason "Responsável autorizado pela administração do servidor"
```

Use seu nome real de conta no lugar de SEU_USUARIO. A conta precisa existir. Para revogar, substitua owner por revoke; para leitura use observer. O comando registra mudança de papel em WorldEvent e revoga as sessões ADM anteriores. Nunca escreve senhas/tokens no log. O personagem da conta, se criado, continua normal, sem moedas ou equipamento adicional por ter papel administrativo.

Papéis: observer (consulta), operator (consulta e gestão de jogadores/itens/monstros/leilões/mundo), economist (consulta e operações econômicas) e owner (ambos). Cada operação também tem permissão específica de domínio no servidor. O painel não concede papéis por si próprio.

## Operações

Escolha entidade pelos registros reais e preencha o formulário da ação. Justificativa de 10–500 caracteres é obrigatória. Calcular prévia cria UUID, captura estado anterior e mostra impacto na oferta/saldos previstos quando financeiro. Nenhum efeito de jogo ocorre nessa etapa. Confirmar exige token da prévia, sessão/papel válidos e estado ainda compatível, com prazo de 5 minutos. Repetições de operações já confirmadas não as executam novamente.

Ações implementadas:

| Domínio | Ações |
|---|---|
| Banco Central | emitir, retirar, transferir reservas; quantidades inteiras exatas |
| Economia | parâmetros suportados de recompensa, taxa e leilão; créditos isolados de teste |
| Jogadores | consultar conta/personagem/inventário/combatente/local/dívida; curar em área segura, conceder XP com pontos normais, viajar somente a destino já permitido |
| Itens | consultar definição/custódia; criar lote autorizado, transferir item físico elegível, proteger definição, recuperar/repor espada inicial |
| Monstros | consultar perfis/instâncias; alterar perfil persistente aplicado a novos encontros |
| Mundo | consultar salas/eventos; ajustar tier de região de combate do primeiro andar; criar spawn identificado, em piso acessível fora de saídas |
| Leilões | filtrar estados, consultar detalhes/lances/reservas e cancelar com reembolso/destino explícito |
| Guildas | administrar a única Guilda real, tesouro, obrigações/pagamentos e transferências institucionais |
| Auditoria | ator, UUID/correlação, entidade, antes/depois, motivo, horário e resultado das operações |

Não existe editor SQL arbitrário, exclusão de ledger, criação fictícia de instituições, emissão automática ou ferramenta para ignorar combate/expedição e suas consequências. Configurações administrativas são persistidas em GameSetting e alteram novas operações, não recompensas já registradas ou preços/prazos de leilões existentes. Perfis de monstros preservam estatísticas/XP dos inimigos já instanciados e mortos.

Para concessão oficial a personagem use conta `character:ID` no fluxo auditado do Banco Central, com emissão explícita ou débito de reserva existente. Sandbox não é uma origem válida. Itens protegidos/externos não podem ser transferidos por um atalho de gestão de mochila.

API `/admin/auth/login` emite sessão administrativa independente; `/admin/session` consulta permissões; `/admin/auth/logout` revoga. Consultas por módulo e `/admin/operations/preview` / `.../{UUID}/confirm` verificam autorização no FastAPI. Dados financeiros exatos usam texto decimal. Login falho e sessão expirada exibem erro; falha de confirmação por estado alterado exige nova prévia. Rejeições de operações existentes são registradas como FAILED com rollback dos efeitos.

Não exponha o painel em endereço público sem TLS e configuração de proxy/autenticação adequadas. O Compose publica loopback; tokens Bearer não usam cookies, portanto não há credencial ambiental de cookie para CSRF. Mais detalhes em SECURITY_AUDIT.md.

## Módulos 0.8

Novas leituras: encontros, pontos pessoais de coleta, publicações/aceitações de contratos e métricas agregadas. Observer pode consultar; operator pode gerir estoque de coleta; economist pode publicar/retirar contratos; owner reúne permissões. Papéis existentes não viram poderes pelo Discord e não há conta padrão.

Em Contratos, formulário guiado apresenta objetivo/alvo/quantidade/vagas/recompensa e justificativa. Publicar exige prévia e confirmação; reserva `recompensa × vagas` do Tesouro, sem emissão. Retirada mostra aceitações e valores retidos/devolvidos: quem já concluiu mantém pagamento garantido. Alteração de progresso depois da prévia impede confirmação até recalcular. Cancelamento pessoal incompleto libera vaga sem destruir orçamento. Nunca alterar reservas por SQL para contornar auditoria.

Coleta mostra estoque por personagem/região/geração, não um estoque global. Reposição/desativação usa ID do ponto pessoal, permissão, motivo, prévia, confirmação e recibo. Não é reposição automática por timer nem criação direta de moedas. Métricas iniciam na instrumentação 0.8; não tratar ausência de amostras antigas como zero mortes/tempo.


## Continuação procedural Lunar 0.9

economy.configure admite lunar_resource_spawn_enabled, lunar_resource_spawn_chance_ppm, lunar_resource_weight_bands, lunar_guild_buy_rate_milliunits_per_gram e royal_admin_extraordinary_controls_enabled; as antigas chaves por tamanho são compatibilidade histórica; prévia/motivo/confirmação/auditoria continuam obrigatórios. Painel Lunar inclui ocorrências e métricas, sem spawn manual. Ver [recursos Lunares](lunar/PROCEDURAL_RESOURCES.md).
