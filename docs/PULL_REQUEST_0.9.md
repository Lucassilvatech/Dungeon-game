# Dungeon Game 0.9 — Lunar economy consolidation, Web-first and read-only Discord

Draft PR contra `feature/web-discord-first-floor-0.8`, cujo remoto é af9dcb5. A nova branch nasceu do HEAD local 7ef6a1a, preservando os cinco commits Lunares ainda não publicados. Main não é destino automático e não deve ser mergeada por esta tarefa.

Preserva fundação Lunar: modelos/ledger/migração aditiva 4a8687e5317c, APIs próprias e ADM, divisão/cunhagem/transferência como primitivas, dry-run 1 moeda antiga=1g e simulador isolado. Não ativa conversão, não cria bosses/rituais futuros e não inventa conclusão da economia.

Discord agora é estritamente observacional. Retira /equipar e botões/funções de controle. Rotas antigas de preview/confirmação retornam 410 e preservam DiscordOperation/recibos/migração. Queries usam transação PostgreSQL read-only e projeções sem geração, retomada, sync, wandering ou liquidação. Vinculação permanece a única exceção de identidade. Chave do bot não autoriza endpoints de jogadores/ADM.

Web mantém React/Phaser e recebe painel Lunar com denominações/pepitas, peso exato, conversão ainda inativa e divisão autorizada pelo backend. Godot inteiro preservado e congelado; workflows nativos somente manuais. CI prioriza pytest/Alembic/migrações/Lunar/simulador/bot, TypeScript/build/npm test e Chromium em PostgreSQL descartável separado. Não há exportação Windows/Android.

Validação executada e limitações: CONSOLIDATION_0.9.md. Testes de snapshot comparam tabelas antes/depois de consultas, inclusive leilão vencido; testes recusam controle e preservam recibos antigos. Credenciais externas Discord ausentes: sincronização externa não foi declarada validada; backend bloqueia mutações mesmo se /equipar antigo ainda estiver em cache no Discord.

Nenhum .env, token real, banco, dump ou backup privado deve entrar no diff. Dados existentes não são apagados. Pendências econômicas e de escala continuam em docs/lunar/IMPLEMENTATION.md e ROADMAP.md. Não habilitar auto-merge.
