# Cutover financeiro Lunar 0.9

Continuação de `feature/lunar-web-discord-readonly-0.9`, HEAD inicial `13ae21357736d074c76a4724da884f58fc2deea4`, na branch `feature/lunar-cutover-economy-0.9`. O inventário [FINANCIAL_WRITERS.md](FINANCIAL_WRITERS.md) foi registrado no commit 7ea7362 antes da implementação. A fundação Lunar foi reutilizada. Main e branch base não recebem merge nem push desta etapa.

## Estado implementado

O upgrade de schema **não ativa conversão**. O ambiente operacional existente não foi convertido nem migrado nesta entrega. A ativação exige administrador com `economy.manage`, preview atual, motivo, UUID e confirmação explícita. Uma operação confirmada torna Lunar a única carteira operacional; os valores antigos ficam preservados e congelados por triggers de UPDATE. As APIs históricas de preço/saldo continuam usando unidades inteiras equivalentes a 1g para compatibilidade; os valores físicos exatos são strings em mg. Projeções assinadas de saldo disponível menos dívida não são moedas negativas.

`app.finance` centraliza carteira, transferência, reserva via escrow, pagamento de taxa e dívida, composição exata e reconciliação. Cunhagem, emissão, troca e burn continuam nas primitivas existentes de `app.lunar`; não há burn nem descoberta novos em gameplay. Não existe crédito sem origem física após conversão. Emissão abstrata e burn administrativo legado são recusados. Créditos administrativos de teste continuam isolados.

| Fluxo | Dinheiro operacional |
|---|---|
| Recompensa de batalha | Tesouro → jogador; sem orçamento, pagamento recusado e direito pendente preservado |
| Taxa médica | Jogador → Tesouro somente pelo pago; restante vira obrigação/recebível |
| Pagamento de dívida | Jogador → Tesouro e redução simultânea da obrigação; entradas futuras amortizam automaticamente |
| Lance / superação | Jogador → `auction:id`; escrow anterior → jogador; reajuste próprio reserva só diferença |
| Liquidação / cancelamento | Escrow → destino configurado / reembolso; item entregue uma vez |
| Contrato | Tesouro → `contract:id` na publicação; escrow → trabalhador ou reembolso; direitos prontos preservados |
| Recuperação | Jogador → `npc:recovery`, custódia → jogador; não é burn |
| Comércio | Conta NPC/Guilda ↔ jogador, contra entrega do item físico em estoque finito |
| Financiamento comercial ADM | Conta existente → Guilda/NPC, via prévia, motivo, confirmação e recibo |

Novos NPCs e Guilda começam com caixa zero. `npc.stock` permite custodiar um item elegível já existente com preço explícito por operação administrativa auditada; não cria produtos nem dinheiro. Venda do jogador à Guilda usa a avaliação-base existente, validada pelo servidor, por stack inteiro. Sem caixa, compra recusada; sem estoque, venda recusada. A espada inicial, itens protegidos/equipados e operações fora dos serviços elegíveis continuam proibidos. A prévia do comércio vincula item, quantidade, dono, local, preço e conta por hash; o cliente não define preço. Não há cadeia produtiva ou reposição automática.

O destino histórico de leilão `sink` passa a ser custódia aposentada, contabilizada separadamente, e não destruição de massa. A dívida e seu recebível são duas perspectivas da mesma obrigação `LunarDebt`, com credor Tesouro, e não duas fontes de moeda.

## Preview, dry-run e confirmação

`GET /admin/lunar/cutover/preview` é preview e dry-run integral: plano exato por conta/denominação, saldos positivos, obrigações, leilões/holds, contratos/reservas/aceites, recuperação, ledger legado, lastro exigido, timestamp e fingerprint. Não cria contas, holdings, ledger ou obrigações. Locks transacionais de leitura garantem um snapshot financeiro coerente, sem escrita persistente.

`POST /admin/lunar/cutover/confirm` recebe `request_id`, `fingerprint`, `reason` e `confirmed: true`. Dentro de uma única transação:

1. Adquire mutex financeiro e Lunar, sempre na mesma ordem.
2. Verifica recibo singleton persistente; repetição retorna `ALREADY_CONVERTED`.
3. Recalcula preview; qualquer fingerprint diferente exige nova aprovação.
4. Rejeita divergência no ledger legado, denominações incompatíveis, reserva sem dono ou estado Lunar prévio financiado. Não mistura silenciosamente uma economia Lunar já movimentada com o legado.
5. Converte positivos e escrows em moedas exatas: 27g = 2 grandes + 1 média + 2 pequenas. Nunca arredonda ou sobrepaga.
6. Registra **GENESIS_BACKING** e atualiza somente `legacy_backing_mg`. Dívidas negativas antigas viram obrigação, sem moeda e sem descoberta fictícia.
7. Reconcilia massa, postings por ativo, escrows e dívidas; qualquer diferença aborta tudo.
8. Persiste recibo imutável, fingerprint e mapa inicial de obrigações; commit pelo gerenciador de transação existente.

Auditoria global verifica massa entrada/gênese/descoberta/cunhagem/destruição, holdings de moedas/pepitas por conta e classe, escrows contra metadata de leilões/contratos e dívida contra recibos imutáveis. Gap de massa **e** listas de divergências precisam ser zero/vazias. A leitura administrativa expõe métricas `lunar_*_mg`; valores financeiros não usam float. Contas Tesouro, Banco Central e custódia aposentada são visíveis individualmente, evitando confundir reservas com circulação.

## Taxa médica

Taxa 100g, carteira 30g: Tesouro recebe 30g; obrigação e recebível aumentam 70g. Pagamento posterior de 70g transfere 70g reais ao Tesouro e zera obrigação/recebível. Carteira 100g paga 100g sem dívida. Limite médico e regras históricas de penalidade/confisco permanecem. O recibo conserva `death_event_id`, necessário para reconexão e confirmação do retorno à cidade. O Chromium encontrou essa regressão na primeira execução pós-conversão; foi corrigida e coberta por teste de morte/reconexão/acknowledge.

## Migrações incrementais e preservação

Após `4a8687e5317c`, sem sobrescrever revisões anteriores:

- `ac5689b8a309`: recibo singleton, obrigações, estoque NPC e triggers que congelam os campos financeiros legados após cutover.
- `b52708c9a8a4`: amplia a constraint de custódia de itens para estoque NPC; não recria tabela nem altera registros históricos.
- `59d047e53dc8`: protege recibo de cutover contra UPDATE/DELETE e congela pesos/tipos de ativos já financiados.

Downgrade com cutover ou estoque é recusado: reversão econômica exige backup revisado, não destruição automática. Nenhuma penalidade retroativa, limpeza de inventário, exclusão de ledger, volume ou `.env`.

Uma nova cópia privada do banco operacional foi extraída por pg_dump/pg_restore para PostgreSQL de teste. Upgrade até head, `alembic check`, preview, dry-run, conversão e auditoria executados somente na cópia. **39 tabelas históricas e 1.554 hashes de linha preservados** tanto após upgrade quanto após conversão (excluindo apenas alembic_version). Resultado da cópia:

| Medida | mg |
|---|---:|
| Gênese / massa total | 100450000 |
| Dívida / recebível (fora da massa) | 450000 |
| Descoberta | 0 |
| Destruição | 0 |
| Gap | 0 |

Nenhum posting ou metadata divergente. Backup e dados privados ficaram fora do Git. Os testes de concorrência usam bancos descartáveis separados; não apontar pytest ao banco operacional.

## Web, Discord e Godot

Web mostra estado LEGACY/LUNAR, três denominações, massa monetária, pepitas e dívida separada. Após conversão o legado não aparece como segunda carteira. Comércio exige proximidade, confirmação do preço e backend autoritativo. A Central possui painel de cutover com dry-run/fingerprint/motivo/confirm e relatórios reconciliados.

**Discord remains read-only. Discord cannot control the character.** Consultas usam transação PostgreSQL `REPEATABLE READ, READ ONLY`, sem geração, movimentação, settlement, coleta ou comércio. Identidade/vinculação permanece separada. Comandos mutáveis antigos seguem bloqueados; mensagens privadas e restrições anteriores preservadas. Testes cobrem consultas também depois da conversão; não foi usada uma conta de bot externa real.

**Windows: FROZEN. Android: FROZEN. APK: NOT REQUIRED. Windows build: NOT REQUIRED. Godot source: PRESERVED.** Nenhum arquivo Godot ou pipeline nativo alterado; nenhum novo download nativo gerado.

## Validação e operação

Resultados finais e comandos são registrados no PR desta etapa. Comandos locais, sempre com DATABASE_URL de teste e TOWER_TEST_DATABASE=1:

```sh
cd backend
../.venv/bin/alembic upgrade head
../.venv/bin/alembic check
../.venv/bin/python -m pytest tests -q
cd ../frontend
npm test
npm run build
BASE_URL=http://127.0.0.1:8093 CHROMIUM_PATH=/usr/bin/chromium npm run test:e2e
```

`frontend/tests/cutover.cjs` é um teste Chromium de integração destrutivo **apenas em banco descartável ainda não convertido**: exige `TOWER_TEST_DATABASE=1`, `CUTOVER_TEST_DATABASE_URL` igual ao banco da API e `BASE_URL`. Usa a `.venv` do repositório para fixtures e uma função owner temporária, revogada em finally. Prepara 100g e dívida70g conservando o legado, confirma conversão pela Central, abastece item físico, financia Guilda por transferência auditada e testa compra/venda e carteira/dívida mobile. Não executar contra produção. O smoke completo de exploração é executado também com banco privado já convertido.

A serialização por mutex PostgreSQL foi estendida aos writers e à aquisição de personagem, antes dos locks de linha, para evitar inversão entre gameplay, sweep e cutover. Isso reduz paralelismo de gameplay; **não há benchmark de carga de produção nesta etapa**. Auditoria é uma varredura de histórico/contas e deve ser operacional, não polling por frame. Antes de escalar, medir espera de locks/latência e paginar/agregar relatórios; presença WebSocket continua exigindo broker compartilhado antes de múltiplos workers. Redis não foi introduzido.

## Pendências e limites

- Deploy e ativação no banco operacional não foram executados; o usuário pediu validação em cópia privada. Operação real exige repetir backup, preview e confirmação sobre o estado atualizado, nunca reutilizar fingerprint de teste.
- A agregação diária dos fluxos Lunar ainda não foi implementada; a API sinaliza a indisponibilidade, sem apresentar agregados fictícios. Obrigações pendentes são derivadas das recompensas reais.
- Não foi validada carga concorrente equivalente à produção nem integração com Discord externo; concorrência funcional, idempotência e conservação foram testadas em PostgreSQL real de teste.
- Estoque comercial depende de custódia explícita e financiamento; não há produtos/moedas gratuitos por seed.
- Minério procedural, bosses globais, ecos, política monetária automática e evolução nativa não fazem parte desta entrega. Rei permanece sem automação (observe-only).

## Commits de implementação

| Commit | Tema |
|---|---|
| 7ea7362 | Inventário financeiro antes do cutover |
| 1e59a5f | Conversão atômica, obrigações, migrações e proteções |
| 8159864 | Taxa médica, dívida e recibo compatível |
| d33d2a3 | Writers, escrows, Guilda/NPC e endpoints |
| 6ad7932 | Web operacional e projeções Discord read-only |
| 2f16a58 | Regressão, concorrência, conservação e Chromium |
| dfc2908 | Exibição de pagamento físico versus saldo líquido |
| 5e512d5 | Obrigações pendentes reais e limites das métricas |

Publicação: somente a feature branch. Draft PR destinado à base 0.9; a API GitHub deste ambiente retorna Forbidden. Descrição revisável em [PULL_REQUEST_LUNAR_CUTOVER.md](../PULL_REQUEST_LUNAR_CUTOVER.md). Compare: https://github.com/Lucassilvatech/Dungeon-game/compare/feature%2Flunar-web-discord-readonly-0.9...feature%2Flunar-cutover-economy-0.9?expand=1

## Resultado final executado

- Suíte backend completa, execução única final: **216 passed, 0 failed, 0 skipped, 2 warnings, 458,65s (7min38s)**. Não soma subconjuntos nem rodadas interrompidas. Avisos: alias AnyIO no Starlette e audioop no discord.py, ambos depreciações. Inclui testes Lunares, Discord, administração e regressões anteriores.
- `npm test`: **1 passed, 0 failed, 0 skipped** (controle dos workflows nativos).
- `npm run build`: **PASS**, 5,30s; aviso Vite de chunk acima de 500kB, sem erro de build.
- Chromium: **PASS** no painel ADM de conversão, carteira, dívida, compra/venda finita, auditoria zero e mobile; **PASS** no smoke completo de exploração contra banco privado já convertido, incluindo recompensas, expedição/fuga, morte, dívida, recuperação e reconexão.
- `alembic upgrade head` e `alembic check`: **PASS**, sem operações pendentes, apenas em banco descartável/cópia privada.
- Verificação adicional de reservas históricas: hold de leilão de 50.000 mg + contrato de 40.000 mg existentes antes do cutover foram convertidos uma vez, sem duplicação e com gap zero. Executada em outro banco descartável, sem alterar o banco da suíte.
- Cópia real: hashes e auditoria confirmados novamente com o código final. Evidência sanitizada em [CUTOVER_VALIDATION.json](CUTOVER_VALIDATION.json).
