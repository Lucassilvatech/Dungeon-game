# feat(lunar): cutover econômico operacional e migração dos writers 0.9

Base: `feature/lunar-web-discord-readonly-0.9`
Head: `feature/lunar-cutover-economy-0.9`
Status pretendido: **Draft**, sem merge automático.

Após confirmação administrativa, Lunar passa a ser a única carteira operacional. O cutover converte 1 moeda histórica em 1g com GENESIS_BACKING separado de descoberta, preserva os registros antigos e migra recompensas, taxas médicas, escrows de leilões/contratos, recuperação e comércio NPC/Guilda. Taxa100 com caixa30 transfere30 ao Tesouro e registra70 como obrigação/recebível, sem criar dinheiro.

Preview/dry-run sem persistência, fingerprint recalculado, mutex transacional, recibo singleton imutável e auditoria impedem conversão duplicada, aprovação obsoleta ou massa divergente. Após conversão, triggers rejeitam alterações nos campos financeiros legados. Não há espelhamento de carteiras. Recompensas precisam de fonte e orçamento, NPCs/Guilda precisam de caixa e estoque físico.

Web apresenta carteira/denominações/massa e dívida separada, comércio finito com prévia e painel ADM de conversão. Discord permanece estritamente read-only, inclusive com transação SQL READ ONLY. Godot Windows/Android preservados e congelados; nenhum APK/EXE novo. Sem minério procedural, bosses, ecos ou automação do rei.

## Banco

Três revisões incrementais após 4a8687e5317c: `ac5689b8a309`, `b52708c9a8a4`, `59d047e53dc8`. Criam recibo, obrigações/estoque, custódia NPC e proteções. Upgrade não ativa conversão. Downgrade recusa estado convertido/estoque; não descarta dados para reverter economia.

Cópia privada do banco operacional: upgrade head + alembic check + preview/dry-run + conversão + audit. Preservadas 39 tabelas históricas/1.554 hashes de linha. Gênese 100.450.000 mg, dívida/recebível 450.000 mg, descoberta 0, destruição 0, gap 0; sem divergência de holdings/postings/metadata. Banco operacional original intocado. Dumps privados não versionados.

## Validação

**Suíte backend completa: 216 passed, 0 failed, 0 skipped, 2 warnings, 458,65s.** npm test: 1 passed; build e Chromium de cutover/comércio/dívida e exploração pós-conversão aprovados. O relatório final de comandos e limitações está em [docs/lunar/CUTOVER.md](lunar/CUTOVER.md). Novos testes cobrem conversão/replay/concorrência/rollback, fingerprints, dívida/recebível, médicos100/30/0, reconexão e confirmação da morte, jogadores novos sem moeda, leilões/holds/outbid/settlement, contratos, recuperação, estoque/caixa NPC, autorização/ADM e leitura Discord pós-conversão.

Chromium testou o painel administrativo real de cutover, carteira, dívida e comércio mobile. O smoke completo de exploração também passou contra banco privado já convertido. npm test e build executados; warning de bundle Vite grande permanece. Alembic upgrade/check executados somente em bancos descartáveis/cópia privada.

## Limites operacionais

- Não houve deploy nem conversão do banco operacional; repetir backup/preview e confirmar sobre o estado atualizado para ativar.
- Mutex global privilegia integridade; throughput de produção não foi medido. Auditoria varre histórico e não deve ser chamada por frame.
- Agregação diária dos fluxos Lunar ainda pendente e sinalizada como indisponível; métricas de conservação e obrigações reais disponíveis.
- Broker de presença continua necessário antes de múltiplos workers. Nenhum Redis obrigatório introduzido.
- Discord externo real e carga de produção não foram validados; evidência é suíte/API e Chromium locais sobre PostgreSQL real de teste.
- Estoque e financiamento comercial são explícitos, sem seed de dinheiro/produtos gratuitos.

Detalhes: [cutover](lunar/CUTOVER.md), [inventário de writers](lunar/FINANCIAL_WRITERS.md).
