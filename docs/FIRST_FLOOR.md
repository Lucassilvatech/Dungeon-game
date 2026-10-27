# Primeiro andar: regras e implementação

## Evolução atual 0.8

Web é o cliente principal; combate individual/regras de expedição da 0.7 continuam. Grupos opt-in começam com dois inimigos próximos: uma ação do jogador, seguida pelos sobreviventes em ordem estável de ID. Alvo, HP e recibos persistem; cada inimigo paga XP/loot/direito uma vez. O iniciante deve preferir combate individual até se preparar. [Regras e compatibilidade](COMBAT_ENCOUNTERS.md).

Máximo procedural agora tem cauda transformada `u >= 0.995`, preservando bins anteriores abaixo dela, influência da proximidade/perigo e consumo de RNG. Só novas instâncias recebem revisão 2; comparar resultados em [BALANCE_REPORT_0.8.md](BALANCE_REPORT_0.8.md).

Folha Luminosa em `common_a`, Minério de Musgo em `common_b`; até dois pontos pessoais por geração, estoque 3/2 respectivamente, sem reposição temporal. Coleta exige proximidade, ausência de combate e espaço de mochila (30 slots para novas coletas, preenchendo stacks existentes quando possível). Não afeta excedentes antigos nem cria moeda. Contratos da recepção exigem reserva antecipada do Tesouro e só contam ações após aceitação. Entregas consomem materiais; retirada de publicação preserva pagamentos já adquiridos. [Especificação](COLLECTION_AND_CONTRACTS.md).

Métricas são posteriores à instrumentação; simulações não representam sessões humanas. Áudio original opcional inicia mudo. Não implementados cooperação, raids completas, classes, habilidades avançadas ou andares superiores.

> **Regras atuais 0.7:** [sequência, geração, retenção, morte/recuperação, dívida e eventos](PROCEDURAL_ECONOMY_UPDATE.md). As regras novas substituem a perda de todos os itens por leilão das versões históricas abaixo.

## Combate

Parâmetros centrais em `balance.py` e Settings:

```text
base = ataque + floor(max(nível - 1, 0) / 2)
dano = clamp(base + bônus_habilidade - defesa - bônus_guarda, mínimo, máximo)
```

Valores iniciais: dano mínimo 2, máximo 999, habilidade +5 por 2 de energia, guarda +4 defesa. `DAMAGE_MIN`, `DAMAGE_MAX`, `SKILL_BONUS`, `GUARD_BONUS` podem ser definidos no ambiente; as definições de espécie ficam centralizadas em ENEMIES. A defesa do jogador é aplicada ao ataque do inimigo, e a defesa do inimigo ao ataque do jogador. O bônus de equipamento vem de ItemDefinition.power, não de um valor enviado pelo cliente. As estatísticas dos monstros não escalam artificialmente com o jogador.

| Espécie | Nível | HP | Ataque | Defesa | XP |
|---|---:|---:|---:|---:|---:|
| Slime | 1 | 24 | 6 | 2 | 30 |
| Batedor | 2 | 30 | 7 | 3 | 40 |
| Guardião | 3 | 60 | 9 | 3 | 100 |
| Sentinela secreta | 8 | 90 | 14 | 5 | primeira conclusão: 100 |
| Boneco | 1 | 24 | 0 | 2 | 0 |

Iniciante: força 5 + espada 3 − defesa 2 = **6 de dano**; slime exige 4 ataques. Ele revida com 6 − defesa 2 = 4 por turno e, em três respostas, tira 12 HP. Sem espada, o combate exige mais ações. Um batedor nível 2 é mais perigoso. Guardar reduz dano mas ainda respeita o mínimo; não é uma pausa infinita segura. Boneco é exceção explícita e não causa dano. Chefe exige preparação; o teste de vitória usa personagem de nível recomendado e habilidades, não o antigo iniciante.

## Identidade, morte e migração

EnemyInstance tem ID único, proprietário, sala, geração, spawn_key, espécie, estatísticas e posição. Estados: ALIVE → IN_COMBAT → DYING → DEAD. IDLE/WANDER são estados ambientais adicionais. A instância de encontro é pessoal; o multiplayer visual não transforma esses inimigos em um combate compartilhado.

A transação do golpe final bloqueia personagem/inimigo, confirma a vida zero, grava evento de morte, XP, loot e registro da Guilda, e termina em DEAD. DYING é uma etapa transacional; clientes nunca podem iniciar outro combate durante/depois dela. A chave única `death:<enemy_id>` e o índice parcial de uma vitória por inimigo reforçam idempotência. Dois ataques finais simultâneos resultam em uma vitória e uma rejeição.

O frontend anima apenas o alvo atingido: hurt, frame de morte, fade/recuo por cerca de 700 ms e destruição do sprite. Não anima todos os NPCs como mortos nem recria o inimigo quando o fade acaba. Reconectar encontra DEAD e não renderiza o morto como vivo. O tile deixa de bloquear passagem.

Histórico anterior à migração é reconciliado na primeira leitura: vitória legada vira inimigo morto; combate ativo é vinculado sem perder HP/turno. Direitos monetários anteriores continuam resgatáveis. Uma derrota não concede recompensas e devolve o inimigo sobrevivente a ALIVE. Nas salas comuns, a tentativa pode ser refeita. Em Aventura procedural, a regra 0.5 abaixo encerra a instância como FAILED e impede continuar o combate nela. A derrota na masmorra secreta continua sem perdas de equipamento, moeda ou progresso.

## Stacks e loot

ItemDefinition possui stackable e max_stack_size; Item mantém quantity, proprietário, custódia e ID. Apenas stacks compatíveis na mochila, não equipados, recebem novos itens. Preenchem-se pilhas existentes antes de criar outras. Exemplo: limite 99, 90 existentes +20 recebidos → 99 e 11. O limite é configurável por definição. Armas são não empilháveis e conservam identidades individuais.

`add_item` é interno, executado sob lock do personagem e com referência idempotente. O evento de morte chama loot uma vez. A migração consolida materiais já existentes, preservando a soma e sem fundir equipamentos. Custódias externas não são alteradas. Nenhuma quantidade de loot é escolhida pelo navegador.

## Guilda

Só a recepcionista da Guilda, por proximidade validada no backend, paga recompensas. Interagir mostra grupos/quantidades e total pendente; não cura automaticamente nem cria moedas. `POST /guild/claim` paga o lote atomicamente: débito do Tesouro, crédito do personagem, ledger por combate e marca de pago. Sem orçamento, tudo reverte e os registros continuam pendentes. O endpoint individual legado também exige a recepção. Treino não gera registro nem loot/XP.

A cidade e a Guilda oferecem descanso explícito, gratuito e somente fora de combate. Não há NPC curadora nas salas comuns, procedurais ou de combate. A recepcionista e os NPCs sociais são figuras distintas; os NPCs secundários têm movimento visual decorativo, sem serviços falsos.

## Procedural e instâncias

`layouts.py`: ROOM_SIZES, ENEMY_DENSITY, THEMES, DECORATIONS e generate(kind, seed). Temas originais: moss_stone, wild_ruins, crystal_bones, abandoned_wood. Variam dimensões, obstáculos, piso, objetos, densidade e spawns. Um RNG local garante reprodução por seed. A região inicial, entradas e saídas ficam reservadas, e flood-fill valida áreas navegáveis antes de posicionar inimigos. Temas consecutivos são diferentes.

Quando não existe expedição ativa com inimigos, Aventura pode criar uma Room com UUID e seed persistente; a chave UUID da requisição impede uma segunda criação por replay. O histórico permanece registrado. Ler estado, inventário, trocar cliente ou reconectar não muda a geração. Treinamento só reinicia por `Novo exercício`; masmorras secretas só criam outra tentativa ao entrar novamente a partir de fora. Os mortos da tentativa anterior não são reutilizados para pagar novas recompensas.

A IA muda IDLE/WANDER em baixa frequência (`WANDER_INTERVAL`, padrão 4 s), apenas ao observar a sala, sem loop global. Mantém raio de duas casas da origem e evita obstáculos, saídas, jogador e outros inimigos. Congela em combate e para definitivamente em DEAD. O Phaser interpola os movimentos; não decide posições de gameplay.

## Eventos e limites

Eventos persistentes: ENEMY_SPAWNED, ENEMY_COMBAT_STARTED, ENEMY_DAMAGED, ENEMY_DIED, ENEMY_REMOVED, ITEM_DROPPED, ITEM_ADDED, GUILD_REWARD_REGISTERED, GUILD_REWARD_CLAIMED e ROOM_GENERATED. `/state` retorna os últimos eventos do personagem e a projeção atual. O frontend usa essa projeção para morte/movimento e eventos para feedback de recebimento de item. Não existe entrega garantida a serviços externos; projeções permanecem a fonte autoritativa após reconexão.

Não foram expandidos andares superiores, combate de raid, economia avançada ou profissões. Combate multi-alvo ainda é futuro: instâncias e fórmulas já são separadas e a sala retorna uma coleção, mas a batalha atual seleciona um alvo. Coleta de recursos continua apenas metadado, sem simular coleta.


## Expedição com compromisso — 0.4

Expedition é um modelo persistente com personagem, sala única, seed, início/fim, estado e resultado da fuga. Estados: ACTIVE, COMPLETED, FLED e FAILED (morte procedural; também usado para histórico abandonado anterior à migração, sem morte retroativa). Um índice parcial permite no máximo uma ACTIVE por personagem. Os inimigos continuam em EnemyInstance, vinculados à sala e ao dono.

ACTIVE com qualquer instância diferente de DEAD bloqueia nova aventura, saída normal, portal e viagem direta à masmorra. Guardas usam RoomType.PROCEDURAL e ExpeditionStatus, não nomes de sala. Repetir a mesma chave de criação é um replay idempotente, sem criar outra instância. Os dados de localização retomam a expedição ativa após reconexão. Salas comuns, cidade, treino e masmorra secreta não recebem essa trava.

O golpe final do último inimigo marca COMPLETED na mesma transação e registra EXPEDITION_COMPLETED uma vez. XP e recompensas continuam sendo concedidos normalmente; não existe XP pendente. A partir daí retorno e nova aventura estão liberados. **Atualização 0.5:** a derrota procedural agora encerra FAILED e resgata à cidade com as penalidades de morte abaixo; substitui o antigo respawn na mesma instância da 0.4. Fora das procedurais, o resgate anterior à cidade continua, incluindo a ausência de perdas nas masmorras secretas.

### Fuga e arredondamento

`GET /expeditions/{id}/flee-preview` calcula a confirmação para o personagem autenticado. `POST /expeditions/{id}/flee` exige confirmed=true e confirmation_token da prévia. Esse token é um fingerprint dos registros/valores, nível, XP e turno; não substitui autenticação. Se esses dados mudarem, a confirmação é rejeitada e precisa ser refeita. Nenhum valor monetário enviado pelo cliente define a penalidade.

Para total pendente T:

```text
restante = T // 2
perda = T - restante = ceil(T / 2)
XP do nível atual = 0
```

A regra incide no **total**, não arredonda cada registro separadamente. Assim, três registros de 1 moeda deixam 1 moeda, não zero. O valor restante é distribuído deterministicamente pelos registros mais antigos (ordem Battle.id), até esgotar o orçamento restante; os demais ficam com valor zero. Quantidades de monstros continuam auditáveis. Todos os endpoints de resgate usam reward_amount ajustado, inclusive o resgate individual legado.

Uma transação bloqueia primeiro o personagem e a expedição, depois os registros pendentes. Ela valida a prévia, ajusta os mesmos direitos monetários já existentes, zera XP, interrompe combate ativo se necessário, grava FLED/resultado/evento e retorna à city1. Não debita carteira nem Tesouro, não remove itens e não reduz nível/atributos. O ledger só registra moeda quando a Guilda paga efetivamente; resultado da expedição guarda ajustes antes/depois por registro. Falha em qualquer etapa reverte tudo.

Repetir a fuga do mesmo ID retorna o resultado original com replayed=true, sem outra penalidade e sem mover o personagem novamente, mesmo que já esteja em uma expedição nova. Não é permitido fugir de uma expedição COMPLETED. A API é independente do navegador e pode ser reutilizada por futuros comandos Discord.

A curva de XP permanece a anterior: próximo nível custa nível×50. Os exemplos de design 950/1000 não redefinem essa curva; o comportamento preservado é zerar somente XP atual. Testes verificam 9/950→9/0, 10/0→10/0 e ganho real na curva atual: 9/440 +30→10/20, fuga→10/0.

## Perigo regional

Room.danger_tier é configuração do mundo: cidade/Guilda/treino 0, Bosque 1, Trilha 2, Clareira 3 e chefe 5. Não foi criada uma sala pré-boss nem outro andar. Para COMMON/COMBAT/BOSS, com E=max(tier−1,0):

```text
HP = HP base + 6×E
ataque = ataque base + E
defesa = defesa base + ceil(E/2)
nível do inimigo = nível base + ceil(E/2)
```

| Região | Tier | Slime: HP / ataque / defesa / nível | Densidade inicial |
|---|---:|---|---:|
| Bosque | 1 | 24 / 6 / 2 / 1 | 3 |
| Trilha | 2 | 30 / 7 / 3 / 2 | 4 |
| Clareira | 3 | 36 / 8 / 3 / 2 | 8 |

O Guardião usa seu perfil base com tier 5: HP 84, ataque 13, defesa 5 e nível 5; nível solo recomendado 7 com espada/energia. Seu teste de vitória usa atributos alcançáveis pela progressão atual. Procedurais e segredos mantêm configuração independente. Voltar ao Bosque encontra os mesmos valores, mesmo em nível alto. O dano continua usando a fórmula de combate anterior.

A migração conserva combates em andamento e mortos; ajusta apenas inimigos ociosos vivos e acrescenta poucos spawns válidos nas regiões mais perigosas. Perfis de batalhas antigas já iniciadas ficam congelados por compatibilidade. O HUD e o atlas conhecido mostram perigo crescente, sem revelar salas secretas.

O próximo passo continua sendo validar balanceamento/retorno à Guilda com jogadores, depois refinar navegação e desenvolver combate multi-alvo incremental. Múltiplos sprites não são apresentados como combate de grupo pronto.


## Morte em Aventura — 0.5

Somente uma batalha perdida em RoomType.PROCEDURAL privada, com Expedition ACTIVE do mesmo personagem, dispara PLAYER_DIED_IN_EXPEDITION. Cidade, treino, salas comuns, áreas seguras e masmorra secreta mantêm suas regras anteriores. O backend confirma a morte na transação do turno: bloqueia personagem/expedição, cria DeathEvent único por batalha e expedição, invalida todas as pendências globais não pagas, zera XP atual, cobra taxa, aplica eventual perda de níveis, transfere itens e encerra FAILED. O inimigo pode continuar registrado como vivo no histórico, mas a aventura terminou e não admite novo combate.

Recompensas já resgatadas não mudam. As ainda pendentes são marcadas como pagas/inválidas com valor zero; o recibo registra valores anteriores por batalha. Nenhum Tesouro é debitado por esses direitos perdidos. XP já virou progresso corrente: zera somente esse XP, não desfaz níveis normais. Fuga permanece distinta: FLED, metade das pendências, XP zero, itens e saldo preservados.

Taxa: `fee = MEDICAL_FEE_BASE` (padrão provisório 100). `saldo_depois = max(-10000, saldo_antes - fee)`. O débito efetivo é `saldo_antes - saldo_depois`; o restante fica auditado como waived. O ledger transfere somente o débito efetivo para a Guilda. Auditoria inclui personagem, expedição, death_event_id, taxa avaliada, valor cobrado/limitado, antes/depois, financiamento novo, timestamp UTC e motivo. MEDICAL_FEE e MEDICAL_DEBT são eventos persistentes.

Ao atingir −10.000, inclusive exatamente ou já estando no limite: `novo_nivel = max(1, nivel - 10)`, uma vez por DeathEvent. Nos próximos óbitos no limite, repete. Nível 37→27; nível 6→1, com perda real 5. A perda real consome primeiro pontos disponíveis; o restante soma dívida de atributos, sem apagar escolhas. Exemplo: perde 10 níveis, tem 2 pontos livres → consome 2, cria dívida de 8; os próximos 8 níveis quitam essa dívida. No mínimo 1, nova morte não cria dívida fictícia de 10 pontos.

O resgate envia à city1, restaura energia 10 e `max(1, floor(HP_max × RESPAWN_HP_PERCENT / 100))` de vida, padrão 100%. O resumo é um recibo durável e confirmável pelo proprietário; F5/login não o perde. Repetir turno rejeita sem efeitos; reprocessar o mesmo DeathEvent devolve recibo sem cobrar ou mover o personagem novamente. Falha em qualquer efeito reverte também o turno, HP, pendências, custódia e ledger.

## Custódia e leilão exclusivo de espólios

Itens físicos de `location=inventory` e definição `death_transferable=true` (a Espada de Aprendiz `sword` é permanentemente excluída na 0.6) saem da mochila, ficam `owner=NULL`, `location=auction`, `equipped=false`. Nenhum item é apagado ou duplicado; quantidade e ID permanecem. Não há flags técnicas disfarçadas de item no catálogo atual; futuras definições estruturais podem marcar false. Outros locais de custódia não são confiscados.

Uma Auction por item/stack e morte guarda antigo dono, quantidade original, preço inicial, maior lance/licitante, início/fim, destino e estado. Um índice parcial impede duas custódias abertas do mesmo item; seu histórico permite nova morte após compra legítima. O lance inicial arredonda para cima os 20% do valor total: `(base × quantidade + 4) // 5`, mínimo configurado. Sem valor positivo confiável, usa o mínimo. Catálogo inicial provisório: espada 100, cristal 10/unidade.

Somente autenticação de conta com Character permite lance; a API não recebe um NPC/licitante escolhido pelo cliente. Exige valor inteiro positivo, acima do maior lance e pelo menos o inicial, com fundos disponíveis. Não há teto comercial. Ouro usa NUMERIC inteiro no servidor; preços/lances/saldos exatos têm representação textual na interface. Leilões usam 24h provisórias, configuráveis somente para novas criações.

O maior lance é debitado para escrow, separado do saldo disponível e mostrado na UI. Seu aumento cobra a diferença. Um novo líder devolve o valor anterior pela função central de crédito; toda entrada compensa saldo negativo automaticamente. Reservas prévias permanecem se o licitante morrer e podem ser devolvidas para amortizar a dívida. Nunca se gasta duas vezes o mesmo saldo. Lances usam UUID de idempotência; repetir com outros parâmetros é rejeitado.

O backend resolve vencidos em lotes até 100 a cada AUCTION_SWEEP_SECONDS, no startup e ao listar leilões; a rota autenticada de resolução também exige prazo vencido. Com vencedor: SETTLED, mesmo item/stack para a mochila, desequipado, cobrança já reservada enviada ao Tesouro ou sink gravado. Nunca paga ao antigo dono. Sem lance: UNSOLD em custódia arquivada, sem descarte, NPC ou relistagem automática. CLOSED/CANCELLED estão reservados no schema, sem fluxo de cancelamento nesta etapa.

## Pontos manuais

Os atributos existentes são strength (Força) e defense (Defesa). Novos níveis concedem 1 ponto, acumulável, depois de quitar attribute_point_debt. Não existe mais +1 de força automático; HP máximo e curva nível×50 continuam anteriores. Personagens legados preservam os valores atuais, com zero pontos retroativos, pois sua força já continha ganhos automáticos. A política evita um segundo bônus para os mesmos níveis.

POST /character/attributes aceita lote não negativo, inteiro, somente desses atributos e UUID. Soma deve ser positiva e não superar os pontos livres; o resultado não pode estourar o armazenamento do atributo. O lock do personagem e chave do evento serializam gastos concorrentes/replay. Sem redução manual ou respec. Eventos ATTRIBUTE_POINT_GAINED e ATTRIBUTE_POINT_SPENT auditam ganhos, quitação de dívida e escolhas.


## Consolidação e cliente Godot — 0.6

A regra de morte/fuga permanece, com exceção explícita: a Espada de Aprendiz inicial sobrevive à morte. Proteção é por ID de definição sword e não por nome/tipo de arma. Outras espadas continuam elegíveis; materiais/stacks e equipamentos físicos não protegidos vão ao leilão. Não há devolução automática de todo histórico: recuperação/reembolso/reposição exigem revisão administrativa individual (AUCTIONS.md).

Exploração acrescenta viagem rápida a locais permanentes visitados, sem combate/ACTIVE, segredos ou procedurais como destinos. O Salão de Leilões fica ligado à Guilda e tem seu próprio leiloeiro; recompensas continuam exclusivamente com a recepcionista. A duração dos anúncios continua 24h configuráveis; detalhes/histórico/entrega/preços são dados reais do backend.

Godot joga o mesmo primeiro andar por API: mapa/teclado/toque, combate, inventário, pontos, NPCs, expedição/fuga/morte, leilões e reconexão. Web legada e Discord preservados. Exportações de desenvolvimento Windows/Android foram geradas; hardware Windows/Android e experiência visual móvel ainda precisam de validação nativa antes de descontinuar Phaser.

Administração não é um poder do personagem: operações financeiras/oficiais usam contexto separado, permissões, antes/depois, UUID e justificativa. Taxa/recompensa e perfil regional podem ser ajustados de modo auditado; saldo já recebido, direito já registrado, leilão existente e inimigo já instanciado não são recalculados retroativamente. Sem segundo andar, combate coletivo ou habilidades novas.


## Continuação procedural Lunar 0.9

Expedições novas podem conter Minério Lunar raro configurável; coletar não dá moedas. Disponibilidade é decidida uma vez, com mapa privado e slots compartilhados. Ver [recursos Lunares](lunar/PROCEDURAL_RESOURCES.md).
