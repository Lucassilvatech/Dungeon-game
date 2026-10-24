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

Cada Aventura procedural cria uma Room com UUID e seed persistente; a chave UUID da requisição impede uma segunda criação por replay. O histórico permanece registrado. Ler estado, inventário, trocar cliente ou reconectar não muda a geração. Treinamento só reinicia por `Novo exercício`; masmorras secretas só criam outra tentativa ao entrar novamente a partir de fora. Os mortos da tentativa anterior não são reutilizados para pagar novas recompensas.

A IA muda IDLE/WANDER em baixa frequência (`WANDER_INTERVAL`, padrão 4 s), apenas ao observar a sala, sem loop global. Mantém raio de duas casas da origem e evita obstáculos, saídas, jogador e outros inimigos. Congela em combate e para definitivamente em DEAD. O Phaser interpola os movimentos; não decide posições de gameplay.

## Eventos e limites

Eventos persistentes: ENEMY_SPAWNED, ENEMY_COMBAT_STARTED, ENEMY_DAMAGED, ENEMY_DIED, ENEMY_REMOVED, ITEM_DROPPED, ITEM_ADDED, GUILD_REWARD_REGISTERED, GUILD_REWARD_CLAIMED e ROOM_GENERATED. `/state` retorna os últimos eventos do personagem e a projeção atual. O frontend usa essa projeção para morte/movimento e eventos para feedback de recebimento de item. Não existe entrega garantida a serviços externos; projeções permanecem a fonte autoritativa após reconexão.

Não foram expandidos andares superiores, combate de raid, economia avançada ou profissões. Combate multi-alvo ainda é futuro: instâncias e fórmulas já são separadas e a sala retorna uma coleção, mas a batalha atual seleciona um alvo. Coleta de recursos continua apenas metadado, sem simular coleta.
