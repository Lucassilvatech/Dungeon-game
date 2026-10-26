# Arquitetura

> **Módulos 0.7:** [sequência, geração, retenção, morte/recuperação, dívida e eventos](PROCEDURAL_ECONOMY_UPDATE.md). As regras novas substituem a perda de todos os itens por leilão das versões históricas abaixo.

Monorepo com backend FastAPI, PostgreSQL 17, clientes Godot/web/Discord e entrada web independente para a Central ADM. `frontend/src/Map.tsx` renderiza mapa e captura entrada; React apresenta menus e chama `/api`. Vite faz proxy no desenvolvimento; Nginx faz proxy na imagem de produção. Nenhum cliente envia dano, moedas ou atributos calculados.

`backend/app/main.py`: contratos HTTP e validação Pydantic. `security.py`: PBKDF2 com salt, sessões opacas com hash no banco e validade de sete dias. `game.py`: regras transacionais. `world.py`: mapa autoritativo. `models.py`: persistência SQLAlchemy; migrações Alembic congelam o schema. `seed.py`: catálogo e emissão inicial auditada, idempotente sob lock PostgreSQL.

Cada requisição abre uma transação e realiza commit apenas se terminar sem exceção. Personagens são bloqueados com SELECT FOR UPDATE antes de mutações; isso serializa ações do mesmo jogador, criação de combate e reivindicação. O turno esperado deve coincidir com o persistido. Inventário valida proprietário e custódia. Constraints impedem personagem duplicado por conta, nomes duplicados, saldo abaixo de −10.000, referência contábil duplicada e evento global duplicado.

O Tesouro é bloqueado depois do personagem. A vitória no chefe escreve `FLOOR_UNLOCKED` com chave `floor:2` única. Seu consumidor inicial é a projeção persistente de acesso aos andares: evento e projeção são a mesma linha, confirmados na mesma transação (`processed=true`). Não existe worker externo nesta versão. Ao integrar consumidores econômicos futuros, criar outbox e confirmações por consumidor; não usar apenas o booleano para garantir entrega externa.

`discord-bot/bot.py` é um cliente HTTP sem acesso direto ao banco. Uma chave de serviço autentica a consulta e o resgate de código, e o ID vem de `interaction.user.id`. Código aleatório, hash persistido, expiração curta, resgate com lock e vínculo único por conta/Discord impedem criar personagens separados. As respostas são privadas. A chave de serviço deve ser compartilhada de maneira segura entre bot e API; nunca expor ao navegador.

`rooms.py` define RoomType/DomainEvent, templates, grafo e projeções de descoberta. `exploration.py` executa transições, aventuras idempotentes por UUID, viagem a segredos e formação de raids. `presence.py` autentica WebSockets e consulta posições já validadas por HTTP; mensagens recebidas nunca alteram posição ou atributos. PostgreSQL continua obrigatório para locks e integridade.

O primeiro mapa foi preservado como common_a para personagens existentes; novas contas nascem em city1. A migração mantém IDs, campos econômicos e combate ativo. Migrações contêm dados congelados e não importam templates mutáveis. O seed cria apenas conteúdo ausente e conexões, sem repor Tesouro.

A presença é um registro de conexões em memória num único worker. Lê posições persistidas aproximadamente a cada 500 ms, transmite somente payload alterado e remove conexões ao desconectar. O token vai na primeira mensagem, não na URL; a sessão é revalidada a cada consulta. O frontend reconecta e limpa pares de outras salas. Para escalar a múltiplos workers, introduzir broker e presença distribuída antes de habilitar workers extras.

A câmera acompanha sprites interpolados nas cidades e enquadra salas pequenas por inteiro. Texturas geradas em `sprites.ts` têm 20 frames (idle, walk, attack, hurt, death × quatro poses). O fundo é desenhado apenas ao trocar de sala; apenas sprites e efeitos limitados atualizam a 30 FPS. Interiores e outros andares não permanecem renderizados. Nenhum asset de terceiros é necessário.

Economia avançada e mercado geral permanecem futuros; a 0.5 adiciona somente morte, dívida médica e leilão de espólios. O lobby de raid não altera os combates individuais existentes. Eventos de domínio e projeções são confirmados na transação da ação, sem prometer entrega a sistemas externos. Ver WORLD_SYSTEM, ROOM_SYSTEM e SECRET_DUNGEONS.

## Aperfeiçoamento do primeiro andar (0.3)

Regras atuais detalhadas em FIRST_FLOOR.md. `layouts.py` produz os novos mapas; `enemies.py` mantém identidade/vida e wandering com posição no PostgreSQL; `balance.py` separa fórmula e definições; `inventory.py` centraliza concessão idempotente e stacks. Battle referencia a instância, com índice único parcial para impedir duas vitórias sobre ela. A API de recompensas consulta registros e paga só na recepção. A migração 11ac6a18a976 contém conteúdo/generação congelados para atualizar salas existentes sem importar regras mutáveis.

`environment.ts` desenha pisos, paredes, móveis e objetos originais; `Map.tsx` mantém atores por ID, remove mortos após animação e interpola wandering recebido. `sprites.ts` agora inclui frames válidos de morte e o batedor. O sprite mede 16×24, escala 1.5, câmera zoom 1 e pixelArt/roundPixels, com bounds de salas grandes e acompanhamento suave. O fundo não é redesenhado a cada frame; partículas/luzes e NPCs sociais são limitados à sala atual.

Os comportamentos legados de boss/desbloqueio permanecem para compatibilidade de dados, sem desenvolvimento de outro andar nesta etapa. A UI e o conteúdo novo se concentram no primeiro andar.


## Compromisso de expedição — 0.4

`expeditions.py` centraliza ACTIVE/COMPLETED/FLED/FAILED, retomada, guardas de saída, prévia e fuga. As rotas de exploração/viagem chamam a guarda; combate sincroniza conclusão ao matar o último inimigo. Nenhuma lógica econômica foi duplicada: a fuga altera Battle.reward_amount e a Guilda continua pagando pelos mesmos registros e ledger. O resultado persiste os ajustes e o evento EXPEDITION_FLED. Fuga durante combate emite também COMBAT_FINISHED com resultado fled. Chaves de idempotência e locks/índice parcial protegem concorrência.

`danger.py` contém o perfil de região e a escala; Room.danger_tier é a configuração autoritativa. `ExpeditionPanel.tsx` apresenta restante, conclusão e confirmação com valores do servidor. As restrições visuais espelham as guardas, mas chamadas diretas da API continuam validadas. A migração 904ca715f282 adota aventuras existentes sem penalidade retroativa e não apaga dados.


## Morte, economia, atributos e leilões — 0.5

`deaths.py` processa somente morte em expedição válida. `DeathEvent` tem unicidade por Battle e Expedition, recibo JSON imutável e confirmação separada; Expedition.result preserva o resultado mesmo após a confirmação. `economy.py` centraliza crédito assinado, reserva e taxa; Ledger registra movimento efetivo, WorldEvent registra perda de direito, dívida e nível. `attributes.py` centraliza ganho, alocação e consumo/dívida por perda de nível. Não foi criado atributo paralelo nem moeda extra.

`Gold` em money.py usa Decimal/NUMERIC no PostgreSQL e int em Python, sem ponto flutuante ou teto comercial. Snapshot mantém coins numérico por compatibilidade e fornece coins_exact/reserved_gold em texto; UI monetária nova usa valores exatos e BigInt nos lances. AuctionBid vincula conta/personagem autenticado, leilão e UUID, sem identidade arbitrária enviada pelo cliente.

Ordem de locks: comandos de leilão e sweeper tomam o advisory lock transacional 7312027 **antes** de bloquear personagens; isso serializa lances e resolução entre processos. Depois bloqueiam leilão/participantes necessários, item e Tesouro por último. Lotes de vencimentos bloqueiam todos os vencedores antes do primeiro débito no Tesouro, evitando conflito com pagamentos da Guilda a um vencedor posterior do mesmo lote. Rotas de listagem/resolução não tomam game.character antes desse mutex. Morte já segura o personagem, mas só cria novas listings e nunca toma o mutex de leilões existentes; não cancela reservas anteriores. O pagamento da Guilda segura personagem e depois Tesouro, sem mutex de leilão. Assim não há ciclo de espera entre resgate, morte, lance e resolução. Essa serialização conservadora é adequada ao laboratório do primeiro andar; medir antes de particionar locks para escala.

Item em custódia tem owner nulo e equipped false, com constraint explícita. Auction conserva antigo dono e quantidade original, unicidade por morte/item e índice único parcial para custódia OPEN/CLOSED/UNSOLD. SETTLED conserva histórico e permite que o mesmo item seja confiscado noutra morte futura. Itens recebidos não são fundidos ao entregar: preserva-se o ID/stack arrematado. A função de loot continua preenchendo stacks válidos na mochila.

O lifespan da API inicia sweeper assíncrono, que executa transações independentes em thread a cada 30s, inclusive no startup; falhas revertem e são tentadas novamente. Listar e a rota settle também resolvem vencidos. Não depende de relógio do navegador nem de conexão de jogador para finalizar. Testes PostgreSQL desativam só o agendamento automático via TOWER_TEST_DATABASE e verificam a mesma função transacional diretamente. Presença ainda exige um worker/broker futuro, independentemente da proteção de leilões entre processos.

Migração aditiva 039105b3ae1a conserva todos os valores e IDs existentes, altera moedas/recompensas/ledger/Tesouro de INTEGER para NUMERIC, relaxa a carteira até −10.000, permite custódia sem dono e cria auditoria/leilões/atributos. Migração não concede pontos retroativos nem aplica mortes retroativas. Downgrade recusa dados que não cabem no modelo anterior, evitando apagar mortes, dívida, custódia ou pontos; atualização normal usa upgrade e volume preservado.

UI `DeathEconomy.tsx`: resumo persistente com perdas reais, formulário de distribuição em lote, dívida visível e leilão paginado (100 por página). A API oferece GET /auctions, POST /auctions/{id}/bids, POST /auctions/{id}/settle, POST /character/attributes e POST /deaths/{id}/acknowledge. Discord segue compartilhando o estado do mesmo backend; não foram adicionados comandos de leilão/morte nem acesso a banco pelo bot.


## Migração incremental 0.6

Godot é o novo cliente principal; React/Phaser permanece durante a validação de plataforma. `godot-client/scripts/api.gd` comunica por HTTP com sessão persistida; `main.gd` coordena menus/comandos e reconexão; `map_view.gd` renderiza pixel art original/câmera/entrada. Presença usa o WebSocket existente. Não há cálculo econômico/combate ou acesso SQL no cliente. Android tem controles maiores e presets; exportações Windows/Android são separadas do teste de execução em Linux.

`fast_travel.py` consulta RoomState de locais permanentes visitados e preserva as guardas de expedição/combate. Nova sala auction_hall e conexão são criadas pelo seed idempotente, sem substituir mapas/saldos existentes. Interact diferencia recepcionista e leiloeiro pelo ID/serviço.

`admin.py` declara rotas, `admin_security.py` sessões/permissões/rate limit, `admin_service.py` operações/locks/prévias/confirmação/auditoria e `admin_economy.py` contas oficiais/métricas. AdminRole não altera Account ou sua carteira. AdminSession é independente de AuthSession; AdminOperation é correlacionada ao ledger e eventos por UUID. AdminTestCredit é isolado de Character.coins. `admin_cli.py` concede/revoga papel em conta existente, com evento auditado e revogação de sessões.

A Central web tem entrada `frontend/admin.html` e bundle `src/admin`, servido em /admin pelo Nginx; compartilha dependências de build, mas não a sessão do jogo. Respostas são vinculadas ao módulo/requisição, impedindo renderizar dados antigos de outro módulo. Sessão Bearer não usa cookies.

CentralBank(id=1) nasce com zero e integra o ledger existente; transferências não emitem, mint/burn são explícitos. Contabilidade e ordem dos locks estão em ACCOUNTING.md. Configuração administrativa é GameSetting com valores allowlisted. MonsterDefinition é persistente e aplicado somente a novas instâncias; EnemyInstance.xp_reward congela também o XP, preservando mortos e batalhas em andamento.

Migração b3057d8109ee é aditiva: protege somente definição sword, cria os modelos ADM/econômicos e congela XP dos inimigos históricos pelos perfis anteriores. Não recupera itens nem reembolsa lances automaticamente. A constraint impede desproteger a espada inicial. Leilões de item protegido são suspensos logicamente até procedimento individual; nenhum original entregue a comprador é retirado silenciosamente.


0.7: `attributes.effective` projeta base/bônus/resultado sem mutar bases. `procedural.py` fornece distribuição universal e BFS de conexões; Expedition congela sorteio. `procedural_retention.py` elimina estado transitório ao encerrar, mantendo pendências/recibos e bosses. `recovery.py` separa perda de unidades e recuperação pessoal; `debt.py` executa avaliação/compra de custódia com ledger e marcos acumulados. `world_events.py` valida agenda e aplica multiplicador somente a novos encontros. Operações administrativas reaproveitam mutex, permissões, prévia, confirmação e auditoria. Migração d0fc148417a5 é aditiva; downgrade destrutivo é recusado.
