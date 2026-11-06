# Entrega 0.9 — pepitas variáveis e Administração Real

## Implementação e correções

Continuação integral da branch `feature/lunar-procedural-resources-0.9`, sem reconstruir cutover, facade financeira, dívida, escrows ou ledger. Nova branch: **feature/lunar-variable-nuggets-royal-admin-0.9**. HEAD inicial: **9026877958b5323cad34ab9fb9410d4d34c36a2e**. Main preservada; sem merge/force push.

Implementados backend, migração, inventário/split, Guilda, Web mobile, Administração Real e consultas Discord. O minério passa de saldo fungível por tamanho a custódia individual rastreável; a simulação e a cópia privada conferem conservação. Documentação antiga de defaults provisórios foi atualizada. Uma ocorrência antiga ainda disponível com asset_code fixo pode ser coletada pelo novo modelo, preservando origem; sua decisão não é rerolada. Configuração de preço agora tem revisão persistente, invalidando quote antigo mesmo após mudar e voltar o rate.

## Spawn, lotes e economia

- Chance inicial aprovada **2%**, faixas **80%: 100..200 g /15%: 201..700 g /5%: 701..1000 g**, limites inclusivos e inteiros. Hash determinístico/versionado, snapshot persistente inclusive sem recurso; novas configurações afetam novas instâncias. Não há minério em mapa permanente/treino/loot comum.
- `LunarMineralLot`: identidade, proprietário, gramas/mg, origem procedural/histórica/admin, pai, estados e recibos. HELD é material atual; SPLIT/MINTED/BURNED são histórico. Transferência conserva ID; split/mint parcial/burn parcial criam filhos com soma exata. Split gratuito ≥2 fragmentos positivos em gramas, capacidade conjunta, autorização, mutex e replay.
- Guilda: rate inicial **800 milliunits/g**, `floor(g×rate/1000)`; 143 g→114, 684 g→547, 1000 g→800. Sem arbitragem de arredondamento por split. Quote por ID/owner/estado/rate/revisão; caixa real exigido, mesmo ID de minério→Guilda e moedas→jogador. Não cunha automaticamente.
- Tesouro: mint manual escolhe quantidades 1 g/5 g/10 g, consumindo somente minério próprio. Caso comprovado:684 g → 437 g MINTED + 247 g HELD, pai SPLIT. Transferência/confisco não altera oferta. `ADMIN_BURN` destrói explicitamente; `ADMIN_INJECTION` acrescenta oferta separada de gênese/descoberta, exigindo flag e confirmação forte.
- Equação em mg: **gênese + descoberta + injeção administrativa − destruído = moedas + minério HELD**. Potencial procedural fica separado. Dívida/recebível não são moedas; legado não volta a ser economia paralela. Auditorias verificadas: **gap 0 mg**.

## Administração e clientes

Dez áreas Web: Visão geral, Minério, Moedas, Cunhagem, Jogadores, Guilda, Tesouro, Auditoria, Configuração e Histórico administrativo. Lotes localizáveis por filtros/paginação, árvore de origem, ocorrência/coletor/tempos, moedas por denominação/conta/localização, dívida/recebíveis e inventário real. Banco Central passa a Compatibilidade legada, sem ser Tesouro. Prévia mostra impacto, consumo/resíduo e oferta; mutações exigem economy.manage, motivo, confirmação/token, estado compatível, receipt e auditoria. Leitura economy.read; sem conta ADM padrão. [Manual e Windows](ROYAL_ADMINISTRATION.md).

Web gameplay conserva mapa/combate/recompensas/expedições; carteira e inventário mostram IDs/pesos/divisão; Guilda cota por lote. Administração e coleta/venda testadas com 390 px, sem overflow da página/hover obrigatório. Não há assets/dependências pesadas novos.

**Discord remains read-only. Discord cannot control the character.** Consultas listam apenas pepitas próprias/gramas/massa; cinco consultas pós-coleta foram comparadas contra snapshots de domínio sem alterações, sem revelar recurso potencial. Rotas de controle continuam bloqueadas. Não foi testada conexão externa real com servidor Discord.

**Windows: FROZEN. Android: FROZEN. APK: NOT REQUIRED. Windows build: NOT REQUIRED. Godot source: PRESERVED.** Nenhum arquivo Godot ou workflow de exportação nativa foi alterado por esta entrega; nenhum APK/EXE gerado.

## Banco e preservação

Migração aditiva **ca343e37b4ca**, após 7f422c075115. Acrescenta modelo/índices/checks/triggers de lotes, contador de injeção e ativo contábil mineral_mg sem holding físico. Converte unidades fungíveis com proveniência FIFO e lançamento compensatório `LEGACY_NUGGET_MIGRATION`; histórico anterior não é editado/apagado. Nova projeção de minério só em lotes; holdings antigos zerados, holdings monetários preservados. Não toca migrações históricas ou ativa cutover implicitamente.

| Verificação PostgreSQL | Resultado |
|---|---|
| Fixture antiga preenchida | 2×100 g+500 g+1000 g → 4 lotes; 1.700.000 mg antes/depois |
| Cópia privada previamente verificada do real |49 tabelas antigas; 1.666 hashes históricos preservados; recibo cutover inalterado |
| Unidades fixas nessa cópia |1 unidade de 100 g→1 lote |
| Massa física na cópia |100.550.000 mg antes/depois; minério 100.000 mg; moedas 100.450.000 mg |
| Origens nessa cópia |gênese 100.450.000 mg; descoberta 100.000 mg; injeção 0; destruído 0; gap 0 |
| Operações posteriores só na cópia |split 100=1+99; venda 99=79 moedas; Guilda→Tesouro mesmo ID; mint 37/resíduo 62; gap 0 |

Comparação preserva linhas históricas, exceto projeção fixa deliberadamente migrada e atualização aprovada de defaults com valor anterior registrado; ledger antigo e recibo de cutover são preservados. O banco operacional original permaneceu parado/intocado, sem upgrade, cutover, spawn artificial ou coleta. Dump privado não foi versionado.

## Testes executados

Suíte backend completa, **uma execução final integral**: **257 passed, 0 failed, 0 skipped, 2 warnings, 592,55 s (9 min 52 s)**. Não é soma de subconjuntos. Uma tentativa anterior foi interrompida antes da conclusão para corrigir a compatibilidade da ocorrência antiga AVAILABLE; ela não entra na contagem. A execução final usou PostgreSQL17 novo com toda a cadeia de migrations, sem aproveitar esquema parcial.

Os dois avisos existentes são AnyIO BlockingPortal no Starlette e audioop no discord.py. Não há falha suprimida. Cobertura inclui testes anteriores e novos de geração/limites/estatística, coleta de 143/684/917/1000 g, anti-reroll, split/capacidade/ownership/retry/concorrência, preço/quote/rate, insolvência, mint parcial, transfer/confisco, burn/injection/flag, permissões, prévia obsoleta, rollback, triggers SQL, migração preenchida, Discord puro e cadeia contábil completa. Concorrência executada em PostgreSQL real, não SQLite/mocks.

| Comando/verificação | Resultado |
|---|---|
| `npm test` |1 passed, 0 failed, 0 skipped; 51,92 ms (freeze dos workflows nativos) |
| `npm run build` |PASS; 4,74 s; TypeScript/Vite; aviso conhecido do chunk Phaser grande |
| Chromium `npm run test:e2e` |PASS:login/mobile/exploração/combate/recompensas/fuga/morte/dívida/recuperação/reconexão/ownership |
| Chromium `node tests/lunar.cjs` |PASS:carteira/mobile/sem estoque e sem overflow |
| Chromium `node tests/lunar-resources.cjs` |PASS 390 px:mapa/coleta/inventário/reload/logout/login/fuga/venda/caixa/audit |
| Chromium `node tests/royal.cjs` |PASS 390 px:injection,mint 437 de 684,resíduo 247,split 500+184,venda 400, confisco,burn parcial,coin injection,audit 0 |
| `alembic upgrade head` / `alembic check` |PASS em banco novo/fixture/cópia privada; sem operações pendentes |
| `python scripts/simulate_lunar.py` |PASS:cenários históricos+cadeias normal/extraordinária+1 milhão de decisões |

Na amostra de **1.000.000 decisões**, houve **19.891 spawns (1,9891%)**, bandas **15.994/2.956/941**, mínimo 100 g/máximo 1000 g. Tolerâncias estatísticas verificam implementação; não redefinem o design aprovado. Os 15 cenários históricos e 9 fixtures procedurais continuam no simulador; suas probabilidades de stress são TEST/PROVISIONAL e não defaults operacionais. Cadeias normal e extraordinária têm gap 0, incluindo origem/adminInjection/burn separados.

Reprodução: DATABASE_URL deve apontar **somente a PostgreSQL descartável**, com TOWER_TEST_DATABASE=1. Na raiz:

```sh
cd backend
../.venv/bin/alembic upgrade head
../.venv/bin/alembic check
TOWER_TEST_DATABASE=1 ../.venv/bin/python -m pytest tests -q
cd ../frontend
npm test
npm run build
BASE_URL=http://127.0.0.1:8075 CHROMIUM_PATH=/usr/bin/chromium npm run test:e2e
BASE_URL=http://127.0.0.1:8075 CHROMIUM_PATH=/usr/bin/chromium node tests/lunar.cjs
TOWER_TEST_DATABASE=1 PROCEDURAL_TEST_DATABASE_URL="$DATABASE_URL" BASE_URL=http://127.0.0.1:8075 CHROMIUM_PATH=/usr/bin/chromium node tests/lunar-resources.cjs
TOWER_TEST_DATABASE=1 ROYAL_TEST_DATABASE_URL="$DATABASE_URL" BASE_URL=http://127.0.0.1:8075 CHROMIUM_PATH=/usr/bin/chromium node tests/royal.cjs
cd ..
.venv/bin/python scripts/simulate_lunar.py
```

Os testes de navegador exigem API/Vite ligados à mesma base privada e chance 100% TEST_ONLY; Royal executa depois do teste procedural, que faz cutover privado. Ambos concedem/revogam owner temporário apenas ao usuário de teste. O workflow Web reproduz essa sequência com PostgreSQL descartável. [Evidência sanitizada](VARIABLE_VALIDATION.json) · [Simulação](SIMULATION.json).

## Desempenho, limites e pendências

Decisões persistidas evitam recalcular procedural por snapshot. Consultas de lotes são indexadas/paginadas; movimentos indexados por lote durante auditoria evitam repetir a leitura do ledger por identidade. Auditoria completa ainda cresce com histórico e o mutex financeiro global serializa escritores: gargalo conhecido a medir em carga real. Bundle Phaser grande, presença de um worker/broker futuro e conexão Discord externa permanecem limitações, sem novos serviços obrigatórios.

Fora desta entrega: boss global, Echo, política automática do rei, produção NPC, cooperação avançada, carga/deploy/ativação operacional real e validação externa Discord. Nenhum desses recursos foi antecipado. A implementação desta etapa termina aqui, aguardando nova autorização.

## Git e revisão

| Commit | Tema |
|---|---|
|36830b0|Diagnóstico anterior à programação |
|14c968f|Modelo individual, contabilidade e migração física |
|5d1718d|Geração variável, coleta e compra por grama |
|e7364a2|Operações manuais do Tesouro Real |
|e957dba|Carteira, split, Guilda e dez áreas Reais na Web |
|502468e|Discord observacional com lotes individuais |
|fde4a68|Conservação, migração, concorrência e simulador |
|cd3ace7|Chromium mobile e CI |

Documentação/validação são commits adicionais após os funcionais. Publicação autorizada somente na nova branch. PR draft contra a base procedural; API GitHub devolveu Forbidden no ambiente, portanto descrição pronta em [PULL_REQUEST_VARIABLE_NUGGETS_ROYAL.md](../PULL_REQUEST_VARIABLE_NUGGETS_ROYAL.md) e comparação: https://github.com/Lucassilvatech/Dungeon-game/compare/feature%2Flunar-procedural-resources-0.9...feature%2Flunar-variable-nuggets-royal-admin-0.9?expand=1 . O relatório final da sessão informa HEAD final e confirmação do push.

## Como executar localmente

[Comandos exatos Windows PowerShell, URLs, bootstrap explícito, migrations, logs e parada segura](ROYAL_ADMINISTRATION.md#execução-local-no-windows-powershell). Não há senha/conta administrativa padrão. Nenhum comando destrutivo de dados é necessário.
