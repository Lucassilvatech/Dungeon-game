# feat(lunar): recursos procedurais persistentes e compra física pela Guilda 0.9

Base: `feature/lunar-cutover-economy-0.9`
Head: `feature/lunar-procedural-resources-0.9`
Estado pretendido: **Draft**, sem merge automático.

Expedições novas passam a persistir uma decisão Lunar única, inclusive ausência de recurso. Ocorrências privadas de 100g/500g/1.000g não rerolam em snapshot, reload, login, restart ou consultas Discord. Coleta válida introduz massa pelo ledger DISCOVERED_MINERAL, nunca moedas; encerramento expira recursos não coletados sem entrada econômica.

Reutiliza holdings, Supply, ledger, facade e Guilda da etapa de cutover. Cada pepita ocupa um slot da capacidade existente, sem Item duplicado ou mochila paralela. Snapshot é SOLO, compatível com a exploração individual atual; raids sociais não recebem acesso extra. Coleta/venda idempotentes usam locks PostgreSQL e auditoria com rollback integral.

Guilda só compra com caixa real e preço configurado no servidor. Minério fica na reserva da Guilda, sem cunhagem automática. Spawn permanece desativado por padrão, preços começam sem oferta e parâmetros técnicos são PROVISIONAL. TEST_DEFAULT de chance 100% existe somente em fixtures/CI privadas.

Web inclui marcador leve no mapa, coleta por clique/toque, inventário, cotação/venda e métricas ADM. Discord continua somente leitura SQL e mensagens privadas, sem revelar ocorrências disponíveis. Godot Windows/Android preservados e congelados; nenhum build nativo. Boss global, Echo e automação do rei fora do escopo.

## Dados e revisão

Migração aditiva 7f422c075115 cria decisões e ocorrências, constraints de pesos/estado/recibo, unicidade e índices; triggers protegem decisões, identidade e estados terminais. Nenhuma revisão histórica alterada. Downgrade com proveniência persistida é recusado.

Cópia privada de base real já convertida: 47 tabelas/1.638 hashes anteriores preservados, recibo de cutover inalterado, upgrade/check aprovados. Coleta TEST adicionou 100.000 mg de descoberta, manteve 100.450.000 mg de gênese e gap 0. Banco operacional intocado, dumps não versionados.

**Backend completo: 234 passed, 0 failed, 0 skipped, 2 warnings em 669,46s. npm test: 1 aprovado; build e dois fluxos Chromium aprovados.** Consultas Discord pós-coleta preservaram seis snapshots de domínio. Validação final, comandos, métricas e limites em [relatório de recursos](https://github.com/Lucassilvatech/Dungeon-game/blob/feature/lunar-procedural-resources-0.9/docs/lunar/PROCEDURAL_RESOURCES.md). Simulador acrescenta9 cenários de 10.000 expedições, todos com conservação exata; não define balanceamento final. Chromium 390px cobre registro/login, mapa, coleta, inventário, reconexão/logout/login, fuga e venda. Smoke anterior também executado com cutover ativo e wandering normal.

## Limites

- Ativação/deploy real e balanceamento final não executados.
- Exploração permanece individual; cooperação futura exige novo modelo de membership, sem ampliar a raid atual.
- Pepitas seguem a custódia Lunar existente na fuga/morte; não foi inventada perda/recuperação nova.
- Holdings são fungíveis, com proveniência da ocorrência preservada no ledger; não atribui cada moeda atual a um lote específico.
- Auditoria varre histórico e mutex serializa finanças. Medição de produção e broker de presença antes de múltiplos workers continuam pendentes.
- Sem boss global, Echo, produção NPC completa, automação do rei ou exportações nativas.
