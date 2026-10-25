# Primeiro andar: regras e implementação

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

Histórico anterior à migração é reconciliado na primeira leitura: vitória legada vira inimigo morto; combate ativo é vinculado sem perder HP/turno. Direitos monetários anteriores continuam resgatáveis. Uma derrota do jogador não concede recompensas e devolve o inimigo sobrevivente a ALIVE, permitindo nova tentativa. A derrota na masmorra secreta continua sem perdas de equipamento, moeda ou progresso.

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

Expedition é um modelo persistente com personagem, sala única, seed, início/fim, estado e resultado da fuga. Estados: ACTIVE, COMPLETED, FLED e FAILED (este último para histórico abandonado anterior à migração). Um índice parcial permite no máximo uma ACTIVE por personagem. Os inimigos continuam em EnemyInstance, vinculados à sala e ao dono.

ACTIVE com qualquer instância diferente de DEAD bloqueia nova aventura, saída normal, portal e viagem direta à masmorra. Guardas usam RoomType.PROCEDURAL e ExpeditionStatus, não nomes de sala. Repetir a mesma chave de criação é um replay idempotente, sem criar outra instância. Os dados de localização retomam a expedição ativa após reconexão. Salas comuns, cidade, treino e masmorra secreta não recebem essa trava.

O golpe final do último inimigo marca COMPLETED na mesma transação e registra EXPEDITION_COMPLETED uma vez. XP e recompensas continuam sendo concedidos normalmente; não existe XP pendente. A partir daí retorno e nova aventura estão liberados. Uma derrota numa procedural restaura o personagem na entrada da **mesma instância**, mantendo ACTIVE: morrer não pode servir para escapar da regra. Fora das procedurais, o resgate anterior à cidade continua, incluindo a ausência de perdas nas masmorras secretas.

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
