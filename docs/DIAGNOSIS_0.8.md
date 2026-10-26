# Diagnóstico anterior à programação — 0.8

Base inspecionada e limpa: `370b14fa09550698d204141318a79b642519b055`, feature/procedural-economy-godot-fixes. Branch nova: feature/web-discord-first-floor-0.8. Main remota: eab42d7e732befb04244e29d5e1615e821c5ea5e. Godot/ADM: b685bd37b8378552d641983f15fc1018eb194ad9. A evolução 0.6 tem 11 commits sobre main; a 0.7 mais 11. Não houve merge entre essas entregas e main. Não existe branch 0.8 remota antes deste trabalho.

Foram lidos os doze documentos obrigatórios, estrutura completa (backend/migrações/testes, frontend/Phaser/admin, bot, Godot, infraestrutura e workflows), modelos, rotas, regras transacionais e testes. Documentos históricos ainda descrevem como atuais regras já substituídas; a entrega deve distinguir versão atual/histórico. Dependências existentes: FastAPI/SQLAlchemy/Alembic/PostgreSQL, React19/Phaser3.88/TypeScript/Vite, discord.py2.5/httpx. Nenhuma reescrita ou serviço novo obrigatório é necessário.

| Sistema | Confirmação no código/testes | Estado anterior |
|---|---|---|
| Exploração Web | main.tsx, Map.tsx, pathfinding, smoke Chromium | Implementada: teclado/clique, salas, NPCs, mapas, mobile, reconexão |
| Personagem/inventário/economia | game/attributes/inventory, suites game/death/admin/procedural | Implementados: atributos efetivos, espada protegida, saldos assinados, pontos, ledger |
| Expedição/morte/recuperação | expeditions/deaths/recovery/debt e testes concorrentes | Implementados; preservar bloqueios, penalidades e recibos |
| Leilões/Banco/ADM | auctions/admin_* e testes concorrentes | Implementados com mutex, reservas, prévia/confirmação/auditoria e sandbox isolado |
| Gerador | procedural.generate, teste que exige máximo 4 no intervalo 1–5 | Defeito confirmado: floor(span*r^expoente) nunca inclui teto se span>0 |
| Combate | Battle referencia um EnemyInstance; game.action valida turno | Somente individual. Vários sprites/lobby de raid não são encontro múltiplo |
| Coleta | layouts.resources é metadado; nenhuma rota consome estoques | Não iniciada; add_item não tem limite de slots de coleta |
| Contratos | sem modelo, rota, reservas ou UI | Não iniciados |
| Discord | cinco comandos: vincular/personagem/status/inventario/mapa; consultas a /discord/{id}/state | Cliente real compartilhado, porém consultas limitadas, sem operações confirmadas, sem teste externo de credenciais |
| Sessão e segurança | token digerido/expiração, ADM revoga; sessão normal sem logout; limite somente login ADM | Parcial: adicionar revogação normal e limites persistentes nos endpoints críticos |
| Presença | connections em memória, consultas a cada ~500ms | Um worker; broker requerido para presença coerente entre workers. Não adicionar Redis sem medir |
| Métricas/áudio | ledger/eventos/turnos permitem derivação parcial; sem tempos/danos agregados nem áudio opcional | Parcial/não iniciado |
| Godot | diretório e compatibilidade existentes; builds 0.7 | Preservar byte a byte, sem exportar nesta etapa |

A suite baseline 0.7 foi iniciada em PostgreSQL descartável; o resultado será registrado antes de concluir a etapa 0. Dados operacionais não são usados por pytest. Antes da migração operacional, criar backup e testar atualização de uma cópia 0.7 populada.

## Decisões para implementação incremental

1. Correção de nível por uma cauda superior rara na variável transformada: manter todos os bins antigos, promovendo apenas a pequena cauda do último bin ao teto (0,5% distante, cerca de 1,99% em p=1/k=3). Mesmo RNG/seed; encontros já congelados não mudam. Comparar distribuição/atributos antes/depois; nenhuma mudança arbitrária em HP/taxas/recompensas.
2. Web permanece React/Phaser. Reduzir polling redundante, tratar sessão/retentativas, histórico e serviço da Guilda; áudio sintetizado opcional, sem assets externos/dependências pesadas.
3. Grupos pequenos opt-in (padrão 2, limite configurável e alcance explicitado), com wrapper de encontro reutilizando Battle/EnemyInstance/recompensa única. Backend controla ordem personagem→inimigos sobreviventes; nenhum atalho para fugir. Compatibilidade de combate individual preservada.
4. Métricas agregadas por personagem/dia, não histórico de cada turno procedural permanente. Relatórios/simulações de personagens explícitos; não presumir equilíbrio a partir de README.
5. Coleta pessoal finita por sala/geração, sem reposição temporal implícita, consumida sob lock; capacidade/stack verificados antes de transferir. Contratos com orçamento previamente debitado do Tesouro para reserva identificada no ledger, pagamento único e cancelamento que devolve saldo não gasto. Sem emissão automática.
6. Discord primeiro amplia consultas privadas; operações selecionadas usam intenções com confirmação vinculadas ao usuário, expiração/idempotência e as mesmas funções do jogo. Não haverá poderes ADM nem economia paralela. Token/chave externa não foram fornecidos; testes locais devem usar mocks e API real em banco descartável, sem declarar teste em servidor Discord.
7. Estender permissões/observabilidade ADM pelo fluxo existente. Locks financeiros antes dos personagens; progresso de contratos durante combate/coleta não pode adquirir mutex financeiro depois de segurar personagem. Sessões/rate limiting não devem revelar tokens nem ser anulados por rollback de requisição rejeitada.
8. Migrações aditivas sem penalidades retroativas; copiar banco 0.7 representativo e comparar campos anteriores. PR preparado, main e Godot intactos, sem merge/force push.

## Registro da etapa 1

A comparação de 60 mil amostras seed-idênticas confirmou: frequência do teto passou de zero para 0,55% em p=0 e 2,10% em p=1; média do slime aumentou apenas 0,0055/0,021 nível nesses extremos. Os atributos/seed continuam calculados no mesmo fluxo RNG; somente a pequena cauda promovida muda o t. Dados congelados de aventuras existentes não são atualizados. Evidência detalhada: level-distribution-0.8.json.

Baseline 0.7 executada: **142 testes aprovados** (209,32s), sem falhas/skips. Correção de níveis: **34 testes direcionados aprovados** (15,65s).

Etapa 2: consultas de recompensas/destinos consolidadas no snapshot, reduzindo polling de quatro requisições para uma; rotas antigas preservadas. Logout normal e de todas as sessões agora revogam no servidor. Web diferencia expedição/sala comum, mostra conexão/retentativa e histórico, ignora respostas obsoletas e limita reconexões. Build TypeScript/Vite e 13 testes PostgreSQL da etapa aprovados; smoke de navegador será executado sobre a stack atualizada antes de avançar.

Smoke da etapa 2 executado e aprovado: cadastro/personagem, movimento, falha de rede com pausa após três tentativas, retentativa manual, polling consolidado e revogação real de sessão com retorno ao login. Backup 0.7 fora do Git antes da atualização; Godot sem alterações.
