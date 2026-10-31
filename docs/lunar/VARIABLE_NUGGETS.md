# Pepitas variáveis 0.9 — implementação e validação

## Continuação física/comercial

Pepitas e geração desta etapa permanecem preservadas. A continuação atual corrige denominações monetárias e amplia compra/venda da Guilda; a composição de pagamento agora vem do estoque real do pagador, sem decomposição ideal automática. Sell rate/flags do minério são independentes do buy rate800. [Entrega atual](DELIVERY_PHYSICAL_COMMERCE_0.9.md) · [Comércio](GUILD_COMMERCE.md). Este documento mantém evidências históricas das pepitas variáveis.


Implementação em `feature/lunar-variable-nuggets-royal-admin-0.9`, baseada em `feature/lunar-procedural-resources-0.9`. Backend, migração, gameplay Web, inventário/split, Guilda e [Administração Real completa](ROYAL_ADMINISTRATION.md) implementados. Resultados executados e limitações estão no relatório de entrega vinculado ao final. Não há deploy/ativação automática no banco operacional.

## Diagnóstico registrado antes da programação

Base confirmada9026877958b5323cad34ab9fb9410d4d34c36a2e, branch limpa feature/lunar-procedural-resources-0.9; fetch executado. Desenvolvimento isolado em feature/lunar-variable-nuggets-royal-admin-0.9. Main preservada.

Estado real: LunarResourceOccurrence aceita somente 100/500/1000 g e LunarHolding guarda pepitas fungíveis. Livro-razão é append-only. O cutover, moedas1/5/10 g, dívida, escrows e caixa finito funcionam; precisam ser reutilizados. Geração já persiste decisões negativas e privadas SOLO. As APIs atuais vendem por categoria, e o painel ainda usa Banco Central como rótulo.

Plano contábil: LunarMineralLot será a custódia autoritativa do minério, LunarHolding permanece para moedas. Um ativo contábil mineral_mg (peso1 mg) permite reutilizar o ledger de partidas exatas; nenhum holding material desse ativo será criado. Migração converte cada unidade fixa em um lot e acrescenta lançamento compensatório (ativos fixos→mineral_mg), sem editar ledger anterior. Auditoria considera holdings monetários + lotes HELD, e recompõe a linhagem/entrada histórica. Administração excepcional separará ADMIN_INJECTION de descoberta/gênese. Split/mint parcial geram filhos e encerram o pai; transferência conserva ID.

Não haverá ativação, coleta artificial ou migração no banco operacional; validação somente em cópias privadas e fixtures PostgreSQL. Escopo integral inclui Administração Real, Web, mint, confisco, burn, injection, testes e publicação; boss global/Echo/política automática/Godot permanecem fora.

## Configuração inicial aprovada

| Parâmetro persistente/Settings | Default aprovado | Unidade/regra |
|---|---|---|
| lunar_resource_spawn_enabled | true | Exige cutover ativo e nova expedição procedural |
| lunar_resource_spawn_chance_ppm | 20000 | 2%; uma decisão por instância |
| lunar_resource_weight_bands | 80/15/5 | 80%: 100..200 g; 15%: 201..700 g; 5%: 701..1000 g, inclusivos |
| lunar_guild_buy_rate_milliunits_per_gram | 800 | 0,8 unidade monetária por grama de minério |
| royal_admin_extraordinary_controls_enabled | true | Burn/injection ainda exigem permissão e confirmação forte |

Esses valores substituem os defaults provisórios da etapa procedural anterior. São os valores de design solicitados, não rótulos TEST_DEFAULT. Somente fixtures Chromium usam chance 100% para percorrer o fluxo de forma confiável, exclusivamente em banco descartável. Variáveis de ambiente correspondentes usam maiúsculas; GameSetting persistido prevalece sobre Settings. Alterações pela Web exigem prévia/justificativa/confirmação/auditoria. Faixas devem cobrir exatamente 100..1000 g, contíguas, com percentuais somando 100. Números inteiros estritos, nunca float/bool como quantidade.

`roll` usa SHA-256 de versão, expedição, UUID/seed da sala e geração. Sorteia chance em PPM, faixa por ticket inteiro e grama uniforme dentro da faixa. Versão nova: `lunar-resource-v2-variable`. Decisão e configuração são persistidas na criação. Reconnect/F5/login/snapshot/Discord/restart não recalculam; uma decisão negativa também é definitiva. Decisões antigas v1 e suas ocorrências fixas continuam válidas, sem reroll ou preenchimento retroativo. Não há minério nos mapas permanentes, treino ou loot de inimigo.

## Custódia individual e migração

`LunarMineralLot` é a única custódia material do minério: ID, owner, weight_mg, origin_occurrence_id, parent_lot_id, state, source/split/mint/burn entry IDs, timestamps e detalhes de origem. Peso positivo em gramas inteiras, persistido em mg; spawn entre 100 e 1000 g, mas fragmentos podem ter 1 g ou mais. Estados HELD/SPLIT/MINTED/BURNED. Somente HELD conta na massa material atual. Transferência conserva ID; transformação encerra pai e conserva linhagem nos filhos.

`LunarHolding` continua guardando **moedas**, com denominações 1 g/5 g/10 g. `mineral_mg` é ativo contábil do ledger, peso 1 mg, sem holding físico. Triggers rejeitam holdings positivos de minério e alteração de identidade/peso/origem/detalhes de um lote ou de seus estados terminais. Item tradicional não duplica a pepita.

Migração aditiva **ca343e37b4ca**, pai **7f422c075115**:

1. Obtém os mutex financeiros e confere massa/ledger antes de converter.
2. Cria tabela/índices/FKs/checks, contador admin_injected_mg e ativo contábil mineral_mg; flexibiliza apenas a faixa da ocorrência.
3. Reconstrói proveniência FIFO das antigas unidades fungíveis, incluindo origem, transferências, splits e mint anteriores quando presentes no ledger.
4. Cada unidade antiga de 100/500/1000 g vira um lote individual de mesmo dono/peso. Acrescenta `LEGACY_NUGGET_MIGRATION`: postings dos ativos antigos negativos e mineral_mg positivo. Zera a projeção antiga; não edita nem apaga lançamentos históricos.
5. Preserva configurações antigas como histórico/legacy_value e aplica novos defaults iniciais de spawn. Não sobrescreve migrações anteriores. Upgrade cria contas zero ausentes para personagens existentes, sem dar dinheiro.

Fixa unicidade já existente por ocorrência/expedição/geração e recibos. Índices em proprietário, pai, origem, estado/conta e source_entry facilitam inventário/linhagem/admin. Downgrade destrutivo é recusado; restauração exige backup revisado.

Fixture PostgreSQL de migração: jogador 2×100 g, Guilda 1×500 g, Tesouro 1×1000 g → **4 lotes, 1.700.000 mg antes/depois**, owners e histórico preservados; zero saldo residual em holdings fixos, alembic check sem divergências.

Cópia privada previamente verificada do banco real: **49 tabelas antigas, 1.666 hashes históricos preservados**, 1 unidade fixa de 100 g → 1 lote; massa física total **100.550.000 mg antes/depois**. Gênese 100.450.000 mg, descoberta 100.000 mg, injection/destruição zero e gap zero. Recibo do cutover inalterado. Depois, exclusivamente na cópia, split 100=1+99, venda 99=79 moedas, mesmo ID Guilda→Tesouro e mint 37/resíduo 62 mantiveram gap zero. Dump privado e banco operacional não são versionados nem modificados.

## Coleta, capacidade e divisão

`POST /expeditions/{id}/lunar-resources/{resource_id}/collect` conserva corpo estrito `{request_id}`. O servidor confere snapshot SOLO elegível, posição, expedição ativa, ausência de combate, capacidade e estado; mutex/locks e recibo persistente garantem coleta única. `DISCOVERED_MINERAL` acrescenta massa ao Supply e a um lote do jogador com vínculo à ocorrência, sem moedas. Repetição igual retorna replay; outra tentativa sobre recurso consumido é recusada. Falha de auditoria reverte tudo. Ocorrências antigas AVAILABLE com asset_code fixo também coletam pelo novo modelo, sem duplicar holdings.

Cada lote HELD ocupa um slot do inventário compartilhado com Item/stack, sem mochila ou peso paralelo. Moedas não ocupam slot. Morte/fuga seguem custódia Lunar existente: não introduzem perda nova de minério, venda compulsória ou conversão para pagar dívida. Encerramento expira recursos potenciais não coletados e mantém os já coletados.

`POST /lunar/lots/{id}/split` aceita UUID e `fragments_g`: ao menos dois inteiros positivos, soma exatamente igual ao pai, máximo 1000 fragmentos por operação, capacidade suficiente. É gratuito. Exemplos 684 g → 500+184 ou 300+200+184; 299→100+199. Pai SPLIT, filhos HELD com mesmo dono/origem/source e parent_lot_id. Mutex, chave vinculada aos parâmetros, trigger e transação impedem consumo/split duplo. O endpoint antigo permanece apenas como adaptador para clientes históricos; novas telas usam identidade.

## Venda à Guilda

Preço: `floor(weight_g × rate_milliunits_per_gram / 1000)`, sempre inteiro. Com rate 800: **143 g→114**, **684 g→547**, **1000 g→800** unidades de moeda. A escolha de denominações minimiza moedas sem arredondar: 547=54 grandes+1 média+2 pequenas. A soma dos preços dos fragmentos nunca excede o preço do pai. O preço comercial não é regra de conservação: 1 g de minério não garante 1 unidade monetária.

`GET /lunar/guild-quotes` retorna lote/gramas/rate/preço/caixa/hash. `POST /lunar/guild-sell` aceita apenas lot_id, quote e request_id, junto à recepcionista e fora de combate. Hash vincula identidade, propriedade/estado, preço e revisão da configuração; mudar e voltar o rate invalida a cotação antiga. Replay confirmado continua válido mesmo após mudança de preço.

Venda atômica: moedas Guilda→jogador (com amortização de dívida pela facade existente) e mesmo lote jogador→Guilda, lançamentos, receipt e audit. Caixa insuficiente, lote ausente/alheio/consumido ou quote obsoleto recusam sem efeito. Guilda guarda minério sem cunhar automaticamente. Transferência ao Tesouro é decisão manual auditada, nunca política automática.

## Auditoria e proveniência

Equação global em mg: `GENESIS_BACKING + DISCOVERED_MINERAL + ADMIN_INJECTION − DESTROYED = moedas em holdings + minério em lotes HELD`. Esperado: **gap 0 mg**. Spawn/ocorrência AVAILABLE/EXPIRED é massa potencial, fora da equação. Mint transforma minério em moeda de mesma massa, sem entrada nova. Transferências/split não alteram oferta; dívida/recebível não são massa física.

Auditoria compara Supply com origens do ledger, holdings monetários com postings, lotes HELD com saldos mineral_mg, entrada/filhos por source, donos com trajetórias de transferência, filhos com massa do pai e estados MINTED/BURNED com lançamentos correspondentes. Conta pai e filho consumido apenas como histórico, sem dupla contagem. Linhagem mostra ocorrência, coletor, expedição, lote original, divisões, owners, venda/transferência, mint/burn e recibos. Não se inventa rastreio individual de cada moeda fungível depois de misturas.

## Web, Discord, desempenho e limites

Web: mapa existente mostra peso variável; inventário/carteira exibem IDs/gramas, split grátis e capacidade; Guilda oferece cotação por lote com pending/confirm; Administração Real tem as dez áreas completas e prévia de impacto. Fluxos validados com toque/390 px, sem hover obrigatório ou overflow da página.

Discord lista apenas lotes próprios, pesos e massa em consultas SQL READ ONLY. Não revela spawn potencial de outra instância e não movimenta nem liquida jogo. **Discord remains read-only. Discord cannot control the character.**

Windows: FROZEN. Android: FROZEN. APK: NOT REQUIRED. Windows build: NOT REQUIRED. Godot source: PRESERVED.

Sem novos serviços/dependências pesadas. Snapshots leem decisões/recursos persistidos; não rolam mapas a cada request. Auditoria completa cresce com ledger/lotes e escritas usam mutex financeiro global: correção é priorizada; medir contenção e tamanho real antes de otimizar/particionar. Presença continua com um worker; broker será necessário antes de múltiplos workers. O chunk Phaser grande e conexão Discord externa não são resolvidos por esta etapa.

## Validação e entrega

Ver [DELIVERY_VARIABLE_NUGGETS_0.9.md](DELIVERY_VARIABLE_NUGGETS_0.9.md) para execução completa, comandos, resultados e publicação; [ROYAL_ADMINISTRATION.md](ROYAL_ADMINISTRATION.md) inclui execução exata no Windows. A suíte não é contada pela soma dos subconjuntos. Simulador cobre 1 milhão de decisões e cadeias normais/extraordinárias, preservando cenários históricos. Boss global, Echo, política automática do rei, produção NPC, carga/deploy real e novas exportações nativas permanecem fora desta entrega.
