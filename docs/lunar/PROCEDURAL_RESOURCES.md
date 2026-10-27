# Recursos Lunares procedurais 0.9 — diagnóstico e decisões

Base obrigatória confirmada: `bf2ea7a52d090cae7d9260c573bd1e8d24354c6d`; árvore limpa, fetch executado. Nova branch: `feature/lunar-procedural-resources-0.9`. Main preservada.

O cutover está implementado e validado em cópia privada; ativação no ambiente operacional real ainda não executada. Fundação/ledger, facade, escrows, NPCs e fluxos financeiros serão reutilizados.

## Diagnóstico antes da programação

- Expedição persiste seed/room único e pertence a um personagem. Raid é somente formação social, sem exploração ou combate compartilhados. Snapshot elegível desta etapa é SOLO com um participante; membros de raid não ganham acesso à instância privada. Não serão criadas raids cooperativas.
- A geração de sala ocorre em exploration.adventure, com UUID/seed persistidos; snapshots podem materializar inimigos, mas não devem sortear recursos novos. Decisão sem ocorrência também precisa ser persistida.
- Encerramento COMPLETED/FLED/FAILED passa por procedural_retention.prune. Ocorrências e recibos devem sobreviver à limpeza de inimigos transitórios.
- Inventário tradicional limita slots para coleta, sem limite de peso físico. LunarHolding já representa moedas/pepitas separadamente de Item. Reutilizar holdings, sem duplicar pepita em Item. Cada pepita ocupará um slot da capacidade existente; moedas não ocupam slot. Divisão e coleta tradicional também respeitarão slots compartilhados.
- Morte seleciona somente Item elegível, até cinco unidades. Holdings Lunares existentes não entram nessa seleção. Pepitas permanecerão em custódia Lunar após fuga/morte, como na fundação, sem inventar perda ou preço de recuperação novo. A taxa médica continua cobrando somente moedas; não converte minério para cobrar dívida.
- Ledger já aceita source=discovery e mantém discovered_mg. Introduzir massa exclusivamente na coleta com DISCOVERED_MINERAL; spawn é potencial, sem massa econômica. GENESIS_BACKING permanece separado.
- Configuração administrativa já exige permissão, prévia, justificativa, confirmação e auditoria. Novos parâmetros usarão esse fluxo, sem endpoint de spawn arbitrário. Spawn desativado por padrão; valores técnicos restantes PROVISIONAL, não balanceamento final. Preços por tamanho começam zero (compra desativada), sem equivalência comercial implícita com massa.
- Discord usa transação SQL READ ONLY; apenas contagens de holdings e coleta própria serão expostas, sem posições/spawns disponíveis.

Implementação/testes/resultados serão registrados abaixo conforme executados. Boss global, Echo, automação do rei e Godot continuam fora do escopo.

## Modelo e geração implementados

Revisão aditiva **7f422c075115**, após 59d047e53dc8, cria:

- `LunarResourceGeneration`: uma decisão por expedição, room única, generation, versão, hash, snapshot do participante e configuração, flag spawned e timestamp. Também persiste ausência de minério. Trigger impede UPDATE/DELETE da decisão.
- `LunarResourceOccurrence`: ID persistente, expedição/room/generation/spawn_key, ativo/peso, coordenadas, estado, coletor/timestamp e chave do recibo. Unicidade `(expedition_id,generation,spawn_key)` e `receipt_key`; pesos somente 100.000/500.000/1.000.000 mg; checks de estado/recibo/coletor; índices expedição, room, state e collected_by. Trigger conserva identidade e estados terminais. Downgrade com decisões existentes é recusado para preservar proveniência.

`lunar_resources.generate` é chamado somente pela criação da expedição, após a sala ser configurada. Usa SHA-256 de versão, ID de expedição, UUID da sala, seed e generation. A seed/UUID são criados pelo servidor, não pelo request. Não precisa de nova chamada aleatória nem revela segredo. Chance usa inteiros em partes por milhão e distribuição inteira; posição é uma célula alcançável, sem parede/spawn/saída. Uma instância tem no máximo uma ocorrência nesta versão.

Reexecutar generate encontra a decisão gravada e retorna sem rolar novamente. `/state`, carteira, consultas Discord e reconexão nunca chamam geração Lunar. Alterar configuração só afeta novas expedições. Expedições anteriores à migração não recebem minério retroativo; consultas não preenchem decisões históricas ausentes. Nova expedição recebe outra identidade e decisão independente, mesmo se uma seed numérica coincidir.

O grupo elegível persistido é `SOLO`, com o personagem dono da expedição. Raids sociais existentes não compartilham room nem elegibilidade. Não há dois membros elegíveis na arquitetura atual; requests concorrentes do dono competem pelo mesmo lock, e outros personagens, inclusive membros da mesma raid social, são rejeitados. Cooperação com múltiplos participantes é futura, sem relaxar autorização agora.

## Configuração — não é balanceamento final

| Parâmetro | Default | Semântica |
|---|---|---|
| lunar_resource_spawn_enabled | false | Desativado até configuração administrativa explícita; exige cutover ativo |
| lunar_resource_spawn_chance_ppm | 1000 | PROVISIONAL técnico; 1.000 de 1.000.000, não chance final |
| lunar_resource_weight_distribution | small 90, medium 9, large 1 | PROVISIONAL, pesos relativos inteiros |
| lunar_guild_prices | três preços 0 | Sem oferta de compra; nunca significa pepita gratuita |

Os tamanhos permanecem 100g/500g/1.000g. Preços são por pepita, em unidades monetárias compatíveis (1 unidade = 1g de moeda Lunar), **independentes do peso comercial do minério**. Exemplo de fixture: pepita 100g vendida por 7g de moeda, não uma conversão de massa em moeda.

Usar `economy.configure` com economy.manage, motivo, prévia, confirmação e recibo administrativo. Bool estrito, chance 0..1.000.000, mapas exatamente com nugget_small/medium/large e valores inteiros não negativos. Não aceita float, bool em valor numérico, tamanhos extras ou distribuição vazia/zero. A Web ADM aceita JSON para esses parâmetros. Não há endpoint de spawn manual nem bot com poderes administrativos.

CI/Chromium e cenários usam **TEST_DEFAULT**: chance 100%, tamanho 100g e preço 7 unidades, somente em bancos descartáveis. A distribuição/rendimento das simulações não é recomendação de design. Não ativar esses parâmetros no ambiente operacional.

## Lifecycle, coleta e custódia

Estados: AVAILABLE → COLLECTED ou EXPIRED, sem retorno. COMPLETED/FLED/FAILED expiram ocorrências restantes no mesmo fluxo transacional de encerramento. Retenção não apaga decisões, ocorrências ou recibos; instância encerrada não pode ser reentrada após sair. Recursos abandonados não vão ao Tesouro e não acrescentam massa à Supply.

`POST /expeditions/{id}/lunar-resources/{resource_id}/collect` aceita somente UUID request_id. Resolve peso/quantidade/dono no servidor. Exige sessão, snapshot elegível, expedição ativa, mesma room/generation, distância Manhattan≤1, ausência de combate e capacidade. Mutex financeiro existente precede lock de personagem e ocorrência. Request igual retorna replay; request diferente sobre ocorrência coletada retorna RESOURCE_ALREADY_COLLECTED; instância expirada recusa coleta. Qualquer falha na auditoria aborta holdings, Supply, ledger e estado juntos.

Entrada econômica ocorre **somente na coleta**: `DISCOVERED_MINERAL`, source discovery, uma pepita em LunarHolding do jogador, contexto com occurrence_id/expedition_id/peso. LunarSupply.discovered_mg aumenta na mesma massa, sem moedas, mint ou gênese. Ocorrência mantém identidade própria mesmo quando holdings agregam ativos fungíveis; splits/vendas usam o ledger existente, sem duplicar pepita em Item.

Capacidade compartilhada: número de stacks/itens tradicionais + quantidade total de pepitas. Cada pepita ocupa um slot; moedas continuam fora da mochila de coleta. Não foi criado limite de peso ou mochila nova. Coleta tradicional, comércio que utiliza ensure_collection_capacity e divisão Web de pepitas respeitam a capacidade conjunta. Loot legado que já ultrapassava o limite não é apagado.

Fuga preserva inventário coletado. Morte mantém a política atual: sorteia até cinco unidades Item elegíveis para destruição/recuperação; holdings Lunares permanecem em custódia. Pepitas não são convertidas em Item nem avaliadas automaticamente para confisco/recuperação. Não há nova perda específica, liquidação forçada ou conversão de minério para pagar taxa médica. A taxa/dívida em moedas continua na facade existente.

## Compra pela Guilda e auditoria

`GET /lunar/guild-quotes` retorna quantidade própria, tamanho, preço monetário configurado, caixa e hash da cotação. `POST /lunar/guild-sell` aceita somente ativo conhecido, quote e UUID. Vende uma pepita por operação junto à recepcionista, fora de combate. Sem minério, caixa ou oferta válida, recusa. Preço alterado exige nova cotação. Replay usa recibo persistente mesmo após mudança de preço.

Transação transfere moedas reais Guilda→jogador via finance.move e minério jogador→Guilda via lunar.post/MINERAL_SALE. Pagamento amortiza dívida médica pela regra existente. Trigger/ledger preservam proveniência e massa. Não há cunhagem automática, emissão, transferência automática ao Tesouro ou burn. Fundação de mint permanece exclusiva do Tesouro sobre minério já existente.

Auditoria existente continua conferindo holdings/postings e gênese+descoberta−destruição. Nova reconciliação liga cada DISCOVERED_MINERAL à ocorrência/coletor/ativo/peso; verifica também contadores de origem contra entradas líquidas do ledger. Relatório separa gênese, descoberta e destruição, e holdings de pepitas por categoria de conta. Ativos existentes são fungíveis: não se atribui arbitrariamente cada moeda atual a um lote histórico específico.

Métricas: ocorrências geradas/coletadas/expiradas, massa coletada/descoberta/vendida/disponível/expirada, mineral nos jogadores/Guilda/Tesouro e ledger por origem. Massa disponível/expirada é potencial, não deve ser somada à massa econômica. `GET /admin/lunar/resources` exige economy.read e pagina as últimas 100 ocorrências. Painel Lunar mostra configuração, métricas, coletor e timestamps. Logs: resource_spawned, resource_collected, resource_expired, resource_sale e resource_collection_conflict, sem seed secreta ou hash RNG.

## Web, Discord e limites

Web apresenta marcador leve ☾ no Phaser, nome, peso e botão de coleta acessível por toque/teclado. O botão caminha até a ocorrência e chama a API com pending/gate contra duplo clique. Coleta atualiza mapa, carteira e inventário; venda requer confirmação de preço. Nenhum asset pesado novo.

Discord mantém transações SQL REPEATABLE READ, READ ONLY. Carteira/mineral/inventário mostram pepitas e massa próprias; consultas incluem contagem de coletas próprias, sem revelar spawn disponível, coordenadas de minério ou recursos de outro participante. Nenhum comando de coleta/venda/mint/split foi adicionado. **Discord remains read-only. Discord cannot control the character.**

Windows: FROZEN. Android: FROZEN. APK: NOT REQUIRED. Windows build: NOT REQUIRED. Godot source: PRESERVED.

Leitura de ocorrências não recalcula mapas. Verificação executada: 100 leituras de recursos persistidos resultaram em 100 queries SQL, sem escrita/geração (uma query por consulta, sem N+1). Isso não é benchmark de produção. Auditoria de escrita varre o histórico e o mutex financeiro serializa operações; medir contenção/latência antes de escalar. Presença continua exigindo broker antes de múltiplos workers; nenhum serviço obrigatório novo foi introduzido.

## Validação executada e procedimento

A regressão dirigida executou 64 testes com sucesso, 2 avisos de depreciação, 164,22s; contém conjuntos sobrepostos e **não deve ser somada** à suíte completa final. Simulador preservou 15 cenários da fundação e adicionou 9 cenários procedurais de 10.000 expedições: ausência, raridade, excesso artificial, coleta parcial, abandono, venda, Guilda insolvente, reconexão e concorrência. Todos com gap 0. Valores são fixtures, não balanceamento final.

Cópia privada da base real já convertida: upgrade até 7f422c075115 + alembic check; preservados 47 tabelas e 1.638 hashes de registros anteriores, inclusive recibo do cutover. Coleta TEST nessa cópia acrescentou 100.000 mg de descoberta, manteve 100.450.000 mg de gênese e gap 0. Ambiente operacional original intocado; dump privado fora do Git. A preservação foi comparada antes de inserir o personagem/ocorrência de teste.

Com DATABASE_URL apontando exclusivamente a PostgreSQL descartável:

```sh
cd backend
../.venv/bin/alembic upgrade head
../.venv/bin/alembic check
TOWER_TEST_DATABASE=1 ../.venv/bin/python -m pytest tests -q
cd ../frontend
npm test
npm run build
BASE_URL=http://127.0.0.1:8070 CHROMIUM_PATH=/usr/bin/chromium npm run test:e2e
TOWER_TEST_DATABASE=1 PROCEDURAL_TEST_DATABASE_URL="$DATABASE_URL" BASE_URL=http://127.0.0.1:8070 CHROMIUM_PATH=/usr/bin/chromium node tests/lunar-resources.cjs
```

O Chromium de recursos exige banco privado explícito, parâmetros TEST_DEFAULT na API e cria/revoga owner temporário só nesse banco. PYTHON_EXECUTABLE permite selecionar Python; por padrão usa .venv local se disponível. O workflow Web executa esse teste depois do smoke legado, com banco descartável. Não apontar fixtures, scripts ou pytest ao banco operacional.

Pendências intencionais: balanceamento final, sessões de jogadores, grupos cooperativos, produção de NPCs, transferências/cunhagem automáticas, deploy/ativação real, carga de produção e Discord externo real. Boss global, Echo e política automática do rei não foram implementados. Próxima fase depende de nova autorização.

## Resultado final da execução

- Suíte backend completa, execução única final: **234 passed, 0 failed, 0 skipped, 2 warnings, 669,46s (11min09s)**. Não soma a regressão dirigida ou tentativas anteriores. Avisos de depreciação existentes: alias AnyIO no Starlette e audioop no discord.py.
- `npm test`: **1 passed, 0 failed, 0 skipped** (freeze dos workflows nativos). `npm run build`: **PASS**, 4,96s, aviso conhecido de chunk Phaser grande.
- Chromium com 390px: **PASS** no fluxo procedural e venda à Guilda, com reload/logout/login, inventário, fuga e auditoria; repetido com wandering normal. Smoke legado completo pós-cutover: **PASS**, incluindo exploração, combate, recompensas, expedições, morte, dívida, recuperação e reconexão.
- Discord pós-coleta: **PASS** em cinco consultas; pepita/peso/inventário corretos, nenhuma ocorrência potencial revelada e seis snapshots de domínio rigorosamente inalterados. A suíte também mantém bloqueio dos controles do personagem. Não foi usado bot externo real.
- Alembic upgrade/check: **PASS** em bancos de teste/cópias privadas, sem operações pendentes. Cópia já convertida preservou 47 tabelas/1.638 hashes e o recibo de cutover. Backup adicional fresco do banco operacional foi restaurado em outro banco privado: 39 tabelas/1.554 hashes preservados após upgrade/cutover/audit. Nenhuma escrita no operacional.
- Simulação: **15 cenários anteriores + 9 novos cenários procedurais**, com gap 0 em todos; números não são balanceamento final.

Evidência sanitizada: [PROCEDURAL_VALIDATION.json](PROCEDURAL_VALIDATION.json). Dumps privados, credenciais e fixtures de banco não foram versionados.

## Git e revisão

| Commit | Tema |
|---|---|
| b780afb | Diagnóstico antes da implementação e correção do estado do cutover |
| 9402958 | Decisões/ocorrências, coleta, custódia e migração aditiva |
| 9cda07c | Integração com lifecycle, endpoints e capacidade compartilhada |
| b0ee885 | Configuração/preços, observação ADM e Discord read-only |
| 1be2f68 | Mapa, coleta e venda Web |
| d3bca02 | Regressão de recursos, concorrência e simulações |
| ddf1d5c | Chromium procedural e workflow Web privado |
| 7aa95d7 | Totais explícitos da custódia mineral no ADM |

Push somente para a nova feature branch; sem merge/force push. Draft PR destinado à feature/lunar-cutover-economy-0.9. Descrição em [PULL_REQUEST_LUNAR_PROCEDURAL.md](../PULL_REQUEST_LUNAR_PROCEDURAL.md). Compare: https://github.com/Lucassilvatech/Dungeon-game/compare/feature%2Flunar-cutover-economy-0.9...feature%2Flunar-procedural-resources-0.9?expand=1
