# Diagnóstico anterior à implementação — loja, administração e recuperação

Base limpa confirmada: feature/lunar-physical-denominations-guild-commerce-0.9, HEAD9d79999e62fd31d36c24241c04715b08af47b416. Status/branch/log/fetch executados antes de alterações. Nova branch: feature/guild-shop-recovery-ux-0.9. Main preservada; banco operacional não será alterado pelo agente.

O comércio atual é físico e finito, com seleção real de denominações, políticas independentes e recibos. Contudo, catalog limita100 Item/NPCStock e expõe uma pilha por card; quote/trade só aceitam um Item. TUDO entre stacks e MÁXIMO com capacidade/troco precisam de suporte real no servidor. transfer_item também precisa dividir uma entrada grande da Guilda em pilhas válidas do jogador.

AdminService já oferece permissão/razão/preview/confirm/atomicidade/replay. A UI usa uma razão global e avisos de arbitragem/gratuidade permanentes. Adicionar lote com revisão original por política, rejeição integral de conflito, e histórico individual vinculado ao UUID comum. GuildPriceHistory atualmente tem PK somente request_id: ampliar a chave para(request_id,policy_key), preservando IDs/linhas antigas, permite vários registros no mesmo lote sem duplicar o sistema de auditoria.

Recuperação hoje exige recovery_hall e depende de portas da Guilda, fast travel e rótulos de funcionário. Manter a sala antiga somente como registro arquivado, remover suas conexões e destinos, transferir ocupantes para a cidade de forma auditada e acrescentar barraca/NPC de rosto oculto no sudoeste da cidade. Preservar RecoveryItem, preço200%, propriedade, recibos e conta npc:recovery. Atualizar seed para não recriar o acesso interno.

Plano: catálogo agregado/quotes transacionais sobre os mesmos itens, máximo calculado com moedas reais/capacidade, loja em grade com busca e confirmação integrada, justificativas locais e edição individual/em lote; migração não destrutiva e testes PostgreSQL/Chromium desktop390px. Nenhum preço atual, moeda, supply ou estoque será redefinido. Discord read-only; Godot permanece congelado, com limitações textuais históricas documentadas. Sem crafting, produção NPC ou mercado automático.
