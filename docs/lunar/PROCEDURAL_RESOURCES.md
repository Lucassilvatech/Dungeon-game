# Recursos Lunares procedurais — estado atual 0.9

A etapa inicial criou decisões/ocorrências persistentes na branch `feature/lunar-procedural-resources-0.9` (HEAD9026877958b5323cad34ab9fb9410d4d34c36a2e). A continuação atual é `feature/lunar-variable-nuggets-royal-admin-0.9`: [pepitas variáveis e migração física](VARIABLE_NUGGETS.md), [Administração Real](ROYAL_ADMINISTRATION.md) e [relatório de validação atual](DELIVERY_VARIABLE_NUGGETS_0.9.md). O cutover está implementado e validado em cópia privada; ativação no ambiente operacional real ainda não executada.

## Geração e exclusividade preservadas

`LunarResourceGeneration` registra uma decisão imutável por expedição, UUID da room, seed/generation, versão, configuração e snapshot do participante. Ausência de minério também é persistida. `LunarResourceOccurrence` tem identidade própria e unicidade `(expedition_id,generation,spawn_key)`, coordenadas, peso, estado, coletor e recibo. Índices por expedição/room/state/collected_by evitam busca global em snapshots. Revisão original7f422c075115 e histórico são preservados; revisão aditiva ca343e37b4ca permite pesos variáveis e custódia individual.

Geração usa SHA-256 de dados persistentes da instância, com chance/seleção em inteiros; é chamada somente na criação da expedição. Reconexão, reload, logout/login, restart, `/state`, consultas Web ou Discord nunca geram novo resultado. A mesma seed em nova expedição não reutiliza automaticamente a decisão anterior. Alteração de configuração afeta somente novas instâncias. Decisões antigas v1, inclusive sem spawn, continuam definitivas; expedições anteriores não são preenchidas retroativamente.

A arquitetura atual é **SOLO**: um personagem no snapshot elegível e uma sala privada. Raids sociais não concedem acesso compartilhado nem autorizam outro personagem a coletar. Não se inventou cooperação/raid/PvP. O backend recusa acesso de externos e mantém locks/recibos mesmo em requests concorrentes.

## Defaults atuais aprovados

| Chave | Valor |
|---|---|
| lunar_resource_spawn_enabled | true, somente com cutover ativo |
| lunar_resource_spawn_chance_ppm | 20000, ou 2% |
| lunar_resource_weight_bands | 80%: 100..200 g, 15%: 201..700 g, 5%: 701..1000 g |
| lunar_guild_buy_rate_milliunits_per_gram | 800, ou 0,8 unidade monetária/g |
| royal_admin_extraordinary_controls_enabled | true; ainda exige permissão e confirmação forte |

Limites de gramas são inclusivos e o peso dentro da faixa é uniforme inteiro. Unidade interna é mg, sem float. Esses defaults substituem a antiga configuração provisória desativada/fixa; não são TEST_DEFAULT. Chaves antigas por tamanho são mantidas somente para compatibilidade histórica, sem orientar novos spawns ou preços. Configuração via `economy.configure` exige economy.manage, razão, prévia/confirm e auditoria. Fixtures Chromium forçam chance 100% apenas em bancos descartáveis; não são deploy.

## Lifecycle, coleta e inventário

AVAILABLE→COLLECTED ou EXPIRED, sem retorno. COMPLETED/FLED/FAILED expiram ocorrências não coletadas no encerramento transacional. Recursos abandonados não vão ao Tesouro nem contam como oferta. Retenção preserva decisões/recibos; instância encerrada não pode ser reentrada para reroll.

`POST /expeditions/{id}/lunar-resources/{resource_id}/collect` aceita exclusivamente request_id UUID. O servidor resolve peso/owner, exige personagem no snapshot, mesma instância/generation, estado válido, distância Manhattan≤1, ausência de combate e capacidade. Mutex financeiro precede locks do personagem e ocorrência. Replay do mesmo request não duplica; outra tentativa sobre recurso coletado é recusada. Auditoria inválida aborta toda a transação.

Spawn é potencial; **somente coleta** registra `DISCOVERED_MINERAL`, aumenta discovered_mg e cria `LunarMineralLot` HELD com a mesma massa e identidade/origem próprias. Não cria moeda ou Item duplicado. `LunarHolding` passa a guardar moedas; minério fica somente em lotes. Coleta de ocorrência antiga ainda AVAILABLE também usa o novo modelo, preservando origem e peso fixo histórico.

Cada lote HELD ocupa um slot junto aos itens/stacks tradicionais; moedas não ocupam slot. Split preserva soma/capacidade e gera filhos com origem/pai. Morte/fuga mantêm a regra de custódia Lunar anterior: não se criou perda nova de minério, venda forçada ou conversão para taxa médica. Sem sistema paralelo de mochila/peso físico.

## Guilda e auditoria

Cotação por lot_id, peso, rate, preço, caixa e revisão/hash. Preço `floor(g×rate/1000)`; com rate 800, 143 g→114, 684 g→547 e1000 g→800 moedas/unidades. Preço comercial é independente da equivalência física da moeda. Mudança/reversão do rate invalida quote anterior; replay confirmado continua idempotente.

Venda junto à recepcionista e fora de combate move moedas reais Guilda→jogador e o mesmo ID de minério jogador→Guilda, atomicamente. Caixa insuficiente recusa; não há criação de dinheiro, cunhagem ou envio automático ao Tesouro. Transferências/confisco e mint somente pelo workflow manual auditado da Administração Real.

Equação atual: `GENESIS_BACKING + DISCOVERED_MINERAL + ADMIN_INJECTION − DESTROYED = moedas + lotes HELD`. Auditoria separa potencial procedural, origens, contas, dívida/recebível e transformações. Pais SPLIT/filhos MINTED/BURNED são histórico, sem dupla contagem de massa. Linhagem alcança ocorrência/expedição/coletor, splits, venda, owners, mint/burn e recibos. [Detalhamento contábil](VARIABLE_NUGGETS.md).

Métricas incluem ocorrências geradas/coletadas/expiradas, massa disponível/expirada potencial, massa coletada/vendida, origem da oferta e material por categoria de conta. Logs de spawn/coleta/expiração/venda/conflito não expõem dados secretos do RNG. Painel Real mostra esses estados sem endpoint de spawn público.

## Clientes, desempenho e evidências

Web/Phaser mostra marcador☾, peso variável e botão acessível por toque, pending e confirmação; inventário mostra lotes e split; Guilda cota/vende por ID. Fluxos mobile 390 px e reconexão validados em Chromium na entrega atual. Discord mostra apenas lotes próprios/pesos/massa/coletas próprias em transação SQL READ ONLY; não revela localização de recurso potencial ou outro grupo. **Discord remains read-only. Discord cannot control the character.**

Windows: FROZEN. Android: FROZEN. APK: NOT REQUIRED. Windows build: NOT REQUIRED. Godot source: PRESERVED.

Snapshots consultam ocorrências persistidas sem recalcular geração. Sem serviço obrigatório novo. Auditoria de escrita cresce com histórico; mutex prioriza correção, com contenção a medir em carga real. Presença permanece com um worker; broker necessário antes de múltiplos workers. Sem afirmação de benchmark de produção.

Evidências históricas da etapa procedural: [PROCEDURAL_VALIDATION.json](PROCEDURAL_VALIDATION.json). São resultados de uma revisão anterior, não contagem da suíte atual. Evidências atuais, fixture de migração, cópia privada e comandos em [VARIABLE_NUGGETS.md](VARIABLE_NUGGETS.md) e [DELIVERY_VARIABLE_NUGGETS_0.9.md](DELIVERY_VARIABLE_NUGGETS_0.9.md). Dumps/credenciais não são versionados.

Boss global, Echo, automação do rei, produção NPC, cooperação avançada, deploy/carga real e conexão Discord externa permanecem futuros e exigem autorização separada. Não foram antecipados.
