# DUNGEON GAME — MINÉRIO LUNAR, MOEDA LUNAR, ECONOMIA PERSISTENTE, BOSSES ÚNICOS, ECOS E EXPLORAÇÃO PROCEDURAL

Repositório:
https://github.com/Lucassilvatech/Dungeon-game

Este prompt consolida decisões de design já tomadas para o Dungeon Game.

NÃO trate este documento apenas como uma lista de novas features.

Primeiro analise o repositório existente, identifique os sistemas atuais e encaixe estas mudanças sem quebrar:

- inventário;
- combate;
- progressão;
- economia existente;
- Guilda;
- NPCs;
- mapas;
- aventuras;
- bosses;
- leilões;
- dívidas;
- recuperação de itens;
- administração;
- Godot;
- Discord;
- PostgreSQL;
- FastAPI.

O objetivo é construir uma base econômica e narrativa consistente que possa ser expandida para dezenas de andares no futuro.

==================================================
0. REGRAS GERAIS DE EXECUÇÃO
==================================================

Antes de alterar qualquer arquivo:

1. Analise completamente a arquitetura atual.

2. Identifique:
   - modelos existentes;
   - migrations;
   - serviços;
   - endpoints;
   - schemas;
   - economia atual;
   - campos atuais de moedas;
   - inventários;
   - sistema de aventuras;
   - geração procedural;
   - bosses;
   - combate;
   - Guilda;
   - NPCs;
   - Godot;
   - Discord;
   - Central ADM;
   - testes existentes.

3. Produza um relatório inicial classificando cada requisito como:
   - já implementado;
   - parcialmente implementado;
   - ausente;
   - incompatível com implementação atual;
   - necessita migration.

4. Monte um plano incremental.

5. Só depois execute as mudanças.

PRINCÍPIOS:

- Backend é autoritativo.
- Cliente nunca decide dinheiro, loot, boss, minério ou resultado de combate.
- Não criar dinheiro arbitrariamente.
- Não duplicar Minério Lunar.
- Não inventar drops ainda não definidos.
- Não inventar valores finais ainda não definidos.
- Não inventar nova lore que contradiga este documento.
- Não apagar dados existentes.
- Não resetar banco.
- Não usar `git reset --hard`.
- Não usar `git clean -fd`.
- Não usar `docker compose down -v`.
- Não remover `.env`.
- Não remover banco existente.
- Usar Alembic para migrations.
- Migrations devem ser reversíveis quando tecnicamente viável.
- Preservar o cliente Phaser enquanto Godot não estiver validado.
- Não fazer merge automático em `main`.
- Não enviar diretamente para `main`.
- Trabalhar em feature branch existente apropriada, preferencialmente `feature/procedural-economy-godot-fixes`, caso ainda seja a branch correta.
- Não fazer push ou merge sem autorização.
- Não alegar teste, build ou publicação que não tenha realmente executado.

Todos os parâmetros de balanceamento devem ficar configuráveis.

==================================================
1. PRINCÍPIO CENTRAL DA ECONOMIA
==================================================

A economia do Dungeon Game deve partir de um princípio físico:

MINÉRIO LUNAR É A BASE MATERIAL DA MOEDA.

Minério Lunar pode existir em diferentes estados:

1. Pepita.
2. Reserva do Tesouro.
3. Moeda Lunar cunhada.
4. Material incorporado futuramente em objetos.
5. Material consumido/destruído por ritual.

A troca entre estados NÃO pode criar matéria.

Exemplo:

500 g de Minério Lunar armazenado
↓ cunhagem
500 g de Minério Lunar representado em moedas

A massa total continua sendo 500 g.

Apenas duas operações alteram a quantidade total existente no mundo:

ENTRADA:
Minério Lunar realmente descoberto na Dungeon.

SAÍDA:
Minério Lunar efetivamente destruído por alguma mecânica.

Transferências, compras, vendas e impostos não alteram a massa total.

==================================================
2. UNIDADE CANÔNICA DE CONTABILIDADE
==================================================

Não usar `float` para representar dinheiro ou peso.

Criar uma unidade inteira e precisa.

Sugestão:

`weight_mg`

utilizando miligramas inteiros.

Exemplo:

100 g = 100.000 mg
500 g = 500.000 mg
1.000 g = 1.000.000 mg

Isso permite alterações futuras sem problemas de arredondamento.

Toda operação econômica deve possuir uma representação canônica de massa.

Nunca utilizar valores de ponto flutuante em:

- saldo;
- peso;
- cunhagem;
- destruição;
- rituais;
- dívidas;
- leilões;
- preços;
- reservas.

==================================================
3. MINÉRIO LUNAR
==================================================

Nome oficial:

MINÉRIO LUNAR.

Não existem nesta fase:

- Minério Lunar bruto;
- Minério Lunar refinado;
- níveis de pureza;
- sistema de fundição;
- minério de qualidade diferente.

Existe apenas Minério Lunar.

As pepitas aparecem naturalmente em três tamanhos.

PEPITA PEQUENA

100 g.

PEPITA MÉDIA

500 g.

PEPITA GRANDE

1.000 g.

Todas possuem exatamente o mesmo valor por unidade de massa.

Uma pepita de 500 g deve representar exatamente cinco vezes a quantidade de minério de uma pepita de 100 g.

Uma de 1.000 g representa exatamente dez vezes uma de 100 g.

==================================================
4. DIVISÃO DE PEPITAS
==================================================

Qualquer personagem pode quebrar pepitas.

Não existe profissão necessária.

Não existe ferramenta obrigatória.

Não existe taxa.

Não existe perda.

Não existe chance de falha.

A operação somente reorganiza a mesma quantidade de minério.

Permitir:

1 × 1.000 g
→
2 × 500 g

1 × 1.000 g
→
10 × 100 g

1 × 1.000 g
→
1 × 500 g
+
5 × 100 g

1 × 500 g
→
5 × 100 g

Nunca permitir:

100 g → unidades menores.

100 g é a menor pepita oficial atual.

Toda divisão deve ocorrer em transação atômica no servidor.

Invariante obrigatório:

PESO ANTES = PESO DEPOIS.

Criar testes específicos para isso.

==================================================
5. ORIGEM DO MINÉRIO LUNAR
==================================================

Minério Lunar deve ser extremamente raro.

Não haverá:

- mina permanente;
- área fixa para farm;
- veio que reaparece continuamente;
- NPC que cria minério;
- recurso infinito.

O minério será encontrado principalmente em EXPEDIÇÕES PROCEDURAIS.

Uma expedição pode ou não conter Minério Lunar.

Caso exista, o servidor escolhe aleatoriamente entre:

- 100 g;
- 500 g;
- 1.000 g.

As probabilidades ainda NÃO estão definidas.

Criar configuração para:

- chance de uma expedição possuir minério;
- distribuição entre tamanhos;
- quantidade máxima por expedição;
- modificadores por andar;
- eventos especiais.

Não estabelecer números finais ainda.

==================================================
6. MAPAS PROCEDURAIS EXCLUSIVOS
==================================================

Cada expedição procedural pertence exclusivamente ao grupo que a iniciou.

Outros grupos NÃO podem entrar naquela instância.

Não implementar:

- disputa entre grupos;
- PvP por minério;
- sistema de campeões;
- pedra/papel/tesoura;
- competição por recursos;
- invasão de instâncias.

Essas ideias foram discutidas e DESCARTADAS.

Fluxo:

GRUPO
↓
INICIA EXPEDIÇÃO
↓
SERVIDOR CRIA SEED
↓
MAPA PROCEDURAL É GERADO
↓
MONSTROS/RECURSOS SÃO GERADOS
↓
GRUPO EXPLORA
↓
COLETA RECURSOS
↓
FINALIZA OU ABANDONA
↓
INSTÂNCIA É ENCERRADA
↓
MAPA NÃO PODE MAIS SER ACESSADO

==================================================
7. ANTI-REROLL DAS EXPEDIÇÕES
==================================================

Um jogador não pode descobrir que o mapa não contém Minério Lunar, sair imediatamente e recriar indefinidamente mapas até obter minério.

O servidor deve impedir reroll abusivo.

A seed deve ser definida no início da expedição.

Reconectar NÃO cria nova seed.

Reiniciar cliente NÃO cria nova seed.

Abandonar NÃO permite restaurar aquela instância posteriormente.

Criar infraestrutura para política anti-reroll configurável.

Não inventar cooldown definitivo agora.

Registrar:

- expedition_id;
- group_id;
- seed;
- floor;
- created_at;
- closed_at;
- completion_status;
- resource_generation_result.

==================================================
8. RECONEXÃO
==================================================

Desconexão temporária NÃO deve destruir imediatamente uma expedição ativa.

Persistir informações mínimas necessárias para permitir reconexão segura.

Não é necessário armazenar eternamente cada mapa completo.

Preferir persistir:

- seed;
- posição lógica;
- encontros relevantes;
- recursos gerados;
- recursos coletados;
- estado dos jogadores;
- status da expedição.

Quando encerrada definitivamente, manter apenas registros necessários para auditoria e histórico.

==================================================
9. COLETA DE MINÉRIO
==================================================

Cada ocorrência de minério gerada em uma expedição possui ID único.

Ao coletar:

BEGIN TRANSACTION

validar recurso não coletado;

bloquear registro;

remover recurso disponível;

adicionar pepita ao inventário;

registrar entrada econômica;

COMMIT.

Nenhum recurso pode ser coletado duas vezes.

Proteções:

- double click;
- duas requests simultâneas;
- reconnect;
- retry HTTP;
- WebSocket duplicate;
- crash entre inventário e coleta.

Utilizar idempotência.

==================================================
10. MOEDA OFICIAL
==================================================

Nome oficial:

MOEDA LUNAR.

A Moeda Lunar é produzida utilizando Minério Lunar verdadeiro.

A moeda possui três denominações físicas:

MOEDA LUNAR PEQUENA.

MOEDA LUNAR MÉDIA.

MOEDA LUNAR GRANDE.

Cada uma possui:

- peso próprio;
- valor proporcional ao peso;
- quantidade física no saldo.

==================================================
11. PESOS DAS MOEDAS
==================================================

Os pesos definitivos ainda podem ser balanceados.

A arquitetura NÃO pode depender de números hardcoded.

Criar configurações como:

LUNAR_COIN_SMALL_WEIGHT_MG

LUNAR_COIN_MEDIUM_WEIGHT_MG

LUNAR_COIN_LARGE_WEIGHT_MG

Para desenvolvimento e testes, utilizar inicialmente:

Pequena:
1 g.

Média:
5 g.

Grande:
10 g.

Esses valores são defaults técnicos iniciais, NÃO uma limitação permanente de lore.

A razão inicial é:

1 : 5 : 10.

Isso produz uma correspondência simples:

1 moeda grande
=
2 médias
=
10 pequenas.

E:

100 g de minério
=
10 moedas grandes
=
20 médias
=
100 pequenas.

500 g
=
50 grandes
=
100 médias
=
500 pequenas.

1.000 g
=
100 grandes
=
200 médias
=
1.000 pequenas.

==================================================
12. VALOR DA MOEDA
==================================================

O valor fundamental da Moeda Lunar depende da quantidade de Minério Lunar que ela contém.

Portanto:

VALOR ∝ PESO.

Não criar uma Moeda Lunar Pequena com valor arbitrariamente superior a uma moeda pesada.

Manter uma taxa-base configurável caso a interface precise apresentar uma unidade monetária abstrata.

Mas o lastro físico continua sendo peso.

==================================================
13. CARTEIRA DO JOGADOR
==================================================

O jogador não terá apenas:

`coins = 1000`

A carteira deve distinguir:

small_lunar_coins

medium_lunar_coins

large_lunar_coins

Exemplo de UI:

Moedas Lunares

Pequenas: 27
Médias: 8
Grandes: 3

Peso monetário total:
97 g

O servidor deve conseguir calcular:

- quantidade por denominação;
- massa por denominação;
- massa total;
- valor total equivalente.

Não confiar em total enviado pelo cliente.

==================================================
14. CARTEIRAS ECONÔMICAS
==================================================

A mesma estrutura deve servir para:

- jogadores;
- NPCs;
- Guilda;
- Tesouro;
- comerciantes;
- casas de leilão;
- sistemas futuros.

Evitar criar implementações diferentes de saldo para cada ator.

Criar conceito reutilizável como:

EconomicAccount

ou equivalente compatível com arquitetura atual.

==================================================
15. TROCA DE DENOMINAÇÕES
==================================================

Uma moeda não deve simplesmente ser quebrada fisicamente pelo jogador como uma pepita.

Criar serviço de troca de denominação através da Guilda/Tesouro.

Exemplo:

1 grande
→
2 médias

1 média
→
5 pequenas

ou combinações equivalentes.

A operação deve conservar:

PESO TOTAL.

Inicialmente pode ser gratuita.

Não introduzir taxa sem decisão de design posterior.

Implementar isso como serviço configurável para que taxas possam existir futuramente.

==================================================
16. SELEÇÃO AUTOMÁTICA DE MOEDAS
==================================================

Criar algoritmo de pagamento que selecione denominações disponíveis.

Objetivos:

1. atingir valor/peso solicitado;
2. evitar sobrepagamento;
3. preferir menor número de moedas quando possível;
4. permitir ao jogador escolher manualmente se a interface oferecer essa opção.

O backend deve validar novamente a combinação.

==================================================
17. CUNHAGEM
==================================================

Diferenciar dois conceitos:

CUNHAGEM
=
transformar Minério Lunar em moedas.

EMISSÃO
=
colocar moedas já cunhadas em circulação.

Isso é importante.

Exemplo:

Tesouro possui 1.000 g de Minério Lunar.

Rei decide cunhar 300 g.

Após a cunhagem:

Minério não cunhado:
700 g.

Moedas no Tesouro:
300 g.

Nenhuma moeda necessariamente entrou em circulação ainda.

Depois, ao pagar Guilda ou algum serviço:

Tesouro
→
Guilda.

Isso é emissão/circulação, não criação de matéria.

==================================================
18. COMPOSIÇÃO DA CUNHAGEM
==================================================

O Tesouro poderá decidir em quais denominações cunhar.

Exemplo:

100 g poderiam virar:

10 moedas grandes;

ou

20 médias;

ou

100 pequenas;

ou

combinação equivalente.

Criar política configurável de distribuição das denominações.

Na primeira fase pode existir um target simples.

Posteriormente a política monetária pode observar quais denominações estão faltando na economia.

==================================================
19. INVARIANTE GLOBAL DO MINÉRIO
==================================================

Criar ferramentas de auditoria capazes de verificar:

MINÉRIO TOTAL DESCOBERTO

menos

MINÉRIO TOTAL DESTRUÍDO

deve corresponder à soma de:

- pepitas em jogadores;
- pepitas em NPCs;
- minério no Tesouro;
- minério na Guilda;
- minério ainda presente em expedições ativas;
- massa das Moedas Lunares existentes;
- minério incorporado futuramente em itens, se essa mecânica existir.

Não permitir dupla contabilização.

==================================================
20. GUILDA
==================================================

A Guilda atua como um dos principais intermediários entre aventureiros e governo.

Jogador encontra Minério Lunar.

Jogador retorna.

Pode vender minério à Guilda.

Guilda paga usando MOEDAS QUE ELA JÁ POSSUI.

A Guilda não cria dinheiro na hora da compra.

Depois:

Guilda
→
Tesouro.

Tesouro recebe minério.

Posteriormente pode cunhá-lo.

Se a Guilda estiver sem dinheiro suficiente:

não criar saldo magicamente.

A operação deverá:

- falhar;
- ficar indisponível;
- ou receber financiamento legítimo do Tesouro.

A política específica de financiamento deve ser configurável.

==================================================
21. NPCS E ECONOMIA REAL
==================================================

NPCs comerciais não possuem dinheiro infinito.

No início da simulação:

NPCs comerciais:
0 Moedas Lunares.

Porém possuem:

- produtos;
- materiais;
- equipamentos;
- estoque inicial.

O patrimônio inicial deles está em mercadorias.

Exemplo conceitual:

Ferreiro:

0 moedas.

20 armas em estoque.

Quando vende:

estoque diminui;

saldo aumenta.

Depois usa parte do saldo para:

- comprar minério;
- comprar madeira;
- comprar couro;
- comprar componentes;
- futuramente produzir novos produtos.

Isso cria circulação real.

==================================================
22. NPC NÃO PODE GASTAR O QUE NÃO TEM
==================================================

Invariante obrigatório:

NPC jamais pode comprar algo sem possuir saldo suficiente.

Não permitir saldo negativo, salvo sistemas específicos como dívida que já possuam regras próprias.

Se estiver sem dinheiro:

pode continuar vendendo estoque;

mas não pode comprar novos recursos até obter caixa.

==================================================
23. ESTOQUE DOS NPCS
==================================================

Não criar restock infinito escondido.

Se existir sistema atual de loja que repõe itens magicamente:

não simplesmente remover e quebrar o jogo.

Primeiro identificar.

Criar plano de migração.

Objetivo futuro:

estoque
→
venda
→
caixa
→
compra de insumos
→
produção
→
novo estoque.

Receitas e cadeias produtivas ainda não estão totalmente definidas.

Portanto criar interfaces/extensões sem inventar centenas de receitas agora.

==================================================
24. ORIGEM DA PRIMEIRA LIQUIDEZ
==================================================

NPCs comerciais começam sem dinheiro.

Isso NÃO significa que todo o reino começa sem dinheiro.

Tesouro e instituições reais podem possuir:

- Minério Lunar em reserva;
- Moedas Lunares já cunhadas.

Esses valores iniciais serão configuráveis.

A moeda já está em circulação quando o jogo começa.

Não fixar agora números definitivos.

==================================================
25. ECONOMIA EM DUAS FASES
==================================================

FASE ECONÔMICA 1 — CONTABILIDADE.

Primeiro construir infraestrutura precisa.

Registrar:

- minério descoberto;
- minério coletado;
- minério dividido;
- minério negociado;
- minério do Tesouro;
- minério cunhado;
- moedas cunhadas;
- moedas emitidas;
- moedas por denominação;
- moedas transferidas;
- moedas gastas;
- moedas destruídas;
- minério destruído;
- moedas recolhidas por impostos;
- saldo de NPCs;
- saldo da Guilda;
- saldo do Tesouro.

NÃO tentar criar imediatamente um economista automático perfeito.

==================================================
26. LEDGER ECONÔMICO
==================================================

Criar ou reutilizar ledger existente.

Cada movimentação precisa conter, quando aplicável:

- id;
- timestamp;
- type;
- reason;
- from_account;
- to_account;
- actor;
- weight_mg;
- denomination;
- quantity;
- expedition_id;
- boss_id;
- ritual_id;
- auction_id;
- correlation_id;
- idempotency_key;
- metadata.

Tipos podem incluir:

LUNAR_MINERAL_DISCOVERED

LUNAR_MINERAL_COLLECTED

NUGGET_SPLIT

MINERAL_TRANSFER

MINERAL_GUILD_PURCHASE

COIN_MINT

COIN_ISSUE

COIN_TRANSFER

COIN_DENOMINATION_EXCHANGE

COIN_RITUAL_BURN

MINERAL_RITUAL_BURN

TAX_TRANSFER

AUCTION_TRANSFER

NPC_PURCHASE

NPC_SALE

Não permitir que editar histórico seja equivalente a alterar o estado econômico.

==================================================
27. FASE ECONÔMICA 2 — POLÍTICA DO REI
==================================================

Somente após a Fase 1 estar estável.

Criar inicialmente modo:

OBSERVE ONLY.

O rei analisa a economia mas ainda não executa automaticamente decisões.

Métricas possíveis:

- Minério Lunar total descoberto.
- Reservas do Tesouro.
- Moedas cunhadas.
- Moedas em circulação.
- Moedas fora de circulação.
- Taxa de destruição.
- Taxa de descoberta de minério.
- Volume de comércio.
- Frequência de transações.
- Preços médios.
- Variação de preços.
- Concentração de riqueza.
- Liquidez dos NPCs.
- Liquidez da Guilda.
- Número de compras recusadas por falta de caixa.
- Velocidade aproximada da moeda.
- Quantidade de moedas por denominação.

==================================================
28. EMISSÃO AUTOMÁTICA DO REI
==================================================

Depois das simulações, permitir modo automático.

O rei pode decidir:

- cunhar;
- não cunhar;
- emitir moedas já cunhadas;
- financiar a Guilda;
- aumentar reservas;
- reduzir emissão.

NUNCA:

criar dinheiro sem Minério Lunar.

A política não deve reagir a uma única transação grande.

Utilizar:

- médias móveis;
- tendências;
- hysteresis;
- limites por período;
- cooldown econômico;
- reserva mínima configurável.

Evitar oscilações:

muita moeda
→
freia emissão.

pouca liquidez
→
pode aumentar emissão caso exista lastro.

==================================================
29. CENTRAL ADM ECONÔMICA
==================================================

Adicionar observabilidade à administração.

Mostrar:

MINÉRIO

- descoberto;
- em jogadores;
- em NPCs;
- Guilda;
- Tesouro;
- em expedições;
- destruído.

MOEDAS

- cunhadas;
- em Tesouro;
- em Guilda;
- jogadores;
- NPCs;
- destruídas.

POR DENOMINAÇÃO

- pequena;
- média;
- grande.

INDICADORES

- circulação;
- velocidade;
- destruição;
- descoberta;
- reservas;
- distribuição.

Não permitir manipulação econômica perigosa sem auditoria e permissão apropriada.

Créditos administrativos de teste devem permanecer isolados da economia real caso o projeto já possua esse conceito.

==================================================
30. BOSSES ORIGINAIS
==================================================

Cada andar possui um boss original.

Boss original é ÚNICO por servidor.

Enquanto vivo:

ele pode ser encontrado através das regras normais existentes do andar.

Se já existir o sistema anterior de chance progressiva de encontro do boss:

preservar.

Compatibilizar com a regra previamente planejada:

chance inicial aproximada:
1%.

crescimento progressivo por aventuras concluídas com sucesso.

teto:
10%.

Os valores continuam configuráveis.

A lógica só vale enquanto o boss original estiver vivo.

==================================================
31. MORTE GLOBAL DO BOSS
==================================================

Quando alguém derrota o boss original:

BEGIN TRANSACTION / LOCK GLOBAL

confirmar boss vivo;

registrar grupo;

registrar participantes;

registrar horário;

registrar first_kill;

definir boss morto;

desbloquear andar seguinte;

criar estado necessário para marca do eco;

COMMIT.

Depois:

Boss original nunca reaparece.

Qualquer tentativa concorrente deve detectar que ele já morreu.

Não existem cópias pessoais do boss original.

==================================================
32. PROGRESSÃO COLETIVA DO SERVIDOR
==================================================

A Dungeon possui progressão coletiva.

Boss do andar 1 derrotado
→
andar 2 disponível globalmente.

Boss do andar 2 derrotado
→
andar 3 disponível globalmente.

E assim por diante.

Um jogador novo que entrar depois pode acessar andares já globalmente liberados conforme as demais regras de acesso do jogo.

Ele não precisa matar novamente um boss que morreu historicamente.

==================================================
33. EVENTO HISTÓRICO
==================================================

Registrar first kill como evento histórico.

Dados úteis:

- boss;
- andar;
- data/hora;
- grupo;
- participantes;
- duração;
- versão do jogo.

Posteriormente isso poderá alimentar:

- crônicas;
- Guilda;
- ranking;
- memorial;
- NPCs;
- notícias do mundo.

Não implementar sistemas enormes de ranking agora caso não existam.

Apenas guardar dados suficientes.

==================================================
34. MARCA DO ECO
==================================================

Depois da morte definitiva do boss:

sua arena passa a possuir uma marca misteriosa.

Antes da morte:

marca não existe ou está inativa.

Depois:

marca aparece.

Ela deve possuir:

- representação visual;
- interação;
- texto enigmático;
- receptáculo para Minério Lunar;
- status do ritual.

Texto deve utilizar localization/string resource.

Não hardcode uma revelação final de lore.

==================================================
35. CONCEITO DO ECO
==================================================

Eco não é ressurreição.

Boss está morto.

Eco é:

uma memória;

uma impressão mágica;

uma manifestação residual;

um registro deixado pela Dungeon.

Isso resolve a coerência narrativa dos bosses repetíveis.

==================================================
36. RITUAL DO ECO
==================================================

Para desbloquear o eco:

o jogador ou grupo precisa fornecer determinada MASSA de Minério Lunar.

O custo específico de cada eco ainda NÃO está definido.

Criar campo:

required_lunar_weight_mg

configurável por boss.

O ritual aceita:

- pepitas;
- Moedas Lunares;
- combinação dos dois.

A soma deve ser EXATAMENTE igual ao peso requerido.

Não permitir sobrepagamento silencioso.

==================================================
37. PAGAMENTO COM PEPITAS
==================================================

Exemplo conceitual:

Ritual requer 500 g.

Pode utilizar:

1 × 500 g;

ou

5 × 100 g.

Caso possua 1 × 1.000 g:

jogador pode dividir antes.

==================================================
38. PAGAMENTO COM MOEDAS
==================================================

Como moedas também possuem peso real de Minério Lunar:

podem ser sacrificadas.

Exemplo com defaults atuais:

500 g poderiam ser:

50 Moedas Lunares Grandes de 10 g;

100 Médias de 5 g;

500 Pequenas de 1 g;

ou combinação equivalente.

Ao usar moedas:

ELAS SÃO DESTRUÍDAS.

Não vão para o rei.

Não vão para NPC.

Não vão para Guilda.

Elas deixam de existir.

O minério físico contido nelas também deixa de existir.

==================================================
39. PAGAMENTO MISTO
==================================================

Permitir:

Pepitas + moedas.

Exemplo:

Ritual:
500 g.

Jogador usa:

1 pepita de 100 g;

30 moedas grandes = 300 g;

20 moedas médias = 100 g.

Total:
500 g.

Servidor valida peso total.

==================================================
40. RITUAL COLETIVO
==================================================

O ritual pode ser financiado pelo grupo.

Criar uma sessão de contribuição.

Exemplo:

Ritual precisa 500 g.

Jogador A:
200 g.

Jogador B:
150 g.

Jogador C:
150 g.

Quando atingir exatamente 500 g:

confirmar participantes;

consumir recursos atomicamente;

conceder unlock.

==================================================
41. ESCROW DO RITUAL
==================================================

Não destruir recursos a cada clique de contribuição.

Utilizar escrow/reserva temporária.

Fluxo:

Jogador oferece recurso.

Servidor bloqueia/reserva recurso.

Outros contribuem.

Se completar:

transação final consome tudo.

Se cancelar/falhar antes da confirmação:

recursos são devolvidos.

Isso evita perda por:

- desconexão;
- erro;
- grupo incompleto;
- timeout;
- crash.

==================================================
42. QUEM RECEBE O DESBLOQUEIO
==================================================

Ao completar ritual coletivo:

registrar snapshot dos membros participantes elegíveis.

Esses personagens passam a possuir:

echo_unlocked = true

para aquele boss.

Quem já possuía acesso não perde nada.

Não cobrar novamente de personagem já desbloqueado.

==================================================
43. PAGAMENTO ÚNICO
==================================================

O custo serve para DESBLOQUEAR O ECO.

Não serve como ingresso por tentativa.

Depois de desbloquear:

tentativa 1 → grátis.

tentativa 2 → grátis.

tentativa 50 → grátis.

Se perder:

continua desbloqueado.

Se morrer:

continua desbloqueado.

==================================================
44. RECOMPENSA DO ECO
==================================================

Cada personagem recebe recompensa econômica/loot principal do eco apenas na PRIMEIRA vitória.

Persistir:

first_echo_victory_at

reward_claimed

Não permitir:

desconectar antes do loot;

reconectar;

refazer;

receber novamente.

Não definir ainda:

- item;
- raridade;
- valor;
- quantidade;
- chance;
- moeda;
- habilidade.

Isso será definido posteriormente junto ao sistema completo de drops dos bosses.

==================================================
45. REPETIÇÃO DO ECO
==================================================

Depois da primeira vitória:

o jogador ainda pode lutar contra o eco.

Objetivos possíveis futuros:

- treino;
- diversão;
- estratégia;
- ajudar amigos;
- desafio.

Por padrão, NÃO permitir farm econômico infinito.

Não conceder repetidamente:

- item raro;
- grande XP;
- moeda;
- recompensa exclusiva.

Se sistemas existentes concederem XP ou maestria automaticamente em qualquer combate, criar tratamento específico para o eco ou limites configuráveis.

Não inventar recompensa repetível agora.

==================================================
46. BOSS ORIGINAL VS ECO
==================================================

Manter distinção absoluta.

BOSS ORIGINAL

- único;
- vivo/morto global;
- altera mundo;
- abre próximo andar;
- first kill histórico;
- nunca reaparece.

ECO

- só existe após boss morto;
- individualmente desbloqueável;
- repetível;
- não muda progressão global;
- recompensa principal apenas uma vez por personagem.

==================================================
47. RECOMPENSA DO BOSS ORIGINAL
==================================================

Drops do boss original ainda não estão totalmente definidos.

Não inventar agora.

Preparar sistema data-driven.

Permitir no futuro:

- loot por participante;
- loot do grupo;
- item único;
- material;
- habilidade;
- título;
- recompensa histórica.

==================================================
48. INTEGRAÇÃO COM ECONOMIA EXISTENTE
==================================================

Pesquisar qualquer campo atual como:

coins

gold

money

balance

currency

guild_balance

auction_balance

Não remover imediatamente.

Planejar migration.

Criar camada de compatibilidade.

==================================================
49. MIGRAÇÃO DA MOEDA ANTIGA
==================================================

Se o banco já possuir saldo abstrato de moedas:

não escolher arbitrariamente equivalência sem investigar.

Criar configuração:

LEGACY_COIN_UNIT_WEIGHT_MG

Executar:

1. relatório dos saldos existentes;
2. dry-run;
3. conversão;
4. verificação de soma;
5. migration;
6. testes;
7. só depois deprecar campo antigo.

Durante transição, evitar dupla leitura que crie saldo duplicado.

==================================================
50. PREÇOS
==================================================

Internamente, preços podem utilizar uma unidade canônica baseada em peso.

Exemplo:

price_weight_mg

Isso evita vincular um produto a uma combinação específica de moedas.

Na hora de pagar:

price_weight_mg
↓
coin selection
↓
denominações usadas.

==================================================
51. LEILÕES
==================================================

Adaptar o sistema de leilão existente à Moeda Lunar.

Lances devem possuir valor canônico.

Holds precisam reservar moedas reais.

Cancelamento deve devolver exatamente o saldo reservado.

Não criar moeda ao liberar hold.

Histórico permanece auditável.

==================================================
52. DÍVIDAS DA GUILDA
==================================================

Preservar regras existentes de dívida/confisco.

Converter valores para a nova representação monetária sem modificar a lógica de gameplay já aprovada.

Não confundir:

PAGAMENTO DE DÍVIDA

com

DESTRUIÇÃO DE MOEDA.

Pagamento de dívida transfere moeda.

Ritual destrói moeda.

==================================================
53. RECUPERAÇÃO DE ITENS
==================================================

Preservar o sistema de recuperação após morte caso já esteja implementado.

Pagamentos ao NPC de recuperação são transações normais.

Não destruir moeda automaticamente.

O dinheiro passa para a conta econômica apropriada do NPC/sistema.

==================================================
54. ESPADA DE APRENDIZ
==================================================

Preservar proteções existentes da Espada de Aprendiz.

Mudanças econômicas não podem torná-la:

- confiscável indevidamente;
- perdida em morte;
- vendida por acidente se atualmente protegida.

==================================================
55. COMBATE
==================================================

Preservar sistema de combate planejado.

Combate por turnos.

Servidor calcula tudo.

Componentes:

- atributos;
- equipamento;
- buffs;
- debuffs;
- energia;
- cooldown;
- sobrecarga;
- elementos;
- resistências;
- maestria.

==================================================
56. SISTEMA SEM CLASSES
==================================================

Não criar classes fixas.

Personagens podem aprender habilidades diferentes.

Aprendizado e maestria são separados.

Personagem pode conhecer muitas habilidades.

Equipadas:

máximo 6 slots ativos.

==================================================
57. CAPACIDADE
==================================================

Capacidade inicial:

100 pontos.

Teto atualmente proposto:

120.

Aumento deve ser lento.

Pode envolver:

- treinamento;
- materiais;
- dinheiro;
- serviços;
- desafios.

Não permitir comprar toda evolução apenas com riqueza.

==================================================
58. SOBRECARGA
==================================================

Um único medidor universal.

0–100 inicialmente.

Faixas atualmente propostas:

0–49:
normal.

50–79:
maior custo de energia.

80–99:
habilidades de alto impacto podem ser bloqueadas.

100:
exaustão.

Configurar tudo.

Não hardcode para sempre.

==================================================
59. INTERAÇÕES ELEMENTAIS
==================================================

Preservar motor de reações.

Exemplos:

QUEIMANDO + ÁGUA
→ reduz queimadura.

MOLHADO + ELETRICIDADE
→ intensifica efeito.

MOLHADO + GELO
→ aumenta chance de congelamento.

CONGELADO + FOGO
→ pode remover/alterar congelamento.

Servidor determina resultado.

==================================================
60. ALIADOS
==================================================

Não existe friendly fire direto.

Habilidade ofensiva de jogador não aplica reação prejudicial em aliado.

Habilidades de suporte podem:

- curar;
- purificar;
- remover debuff;
- proteger.

Monstros podem aplicar estados negativos normalmente nos jogadores.

==================================================
61. EQUIPAMENTOS
==================================================

Preservar fórmula correta:

effective_stat
=
base_stat
+
equipment_bonus
+
temporary_effects.

Não permitir dupla aplicação ao equipar/desequipar.

==================================================
62. FUTURO USO DO MINÉRIO EM CRAFT
==================================================

A lore estabelece que Minério Lunar também pode possuir utilização em itens mágicos.

Não criar receitas agora.

Porém preparar contabilidade para diferenciar:

minério destruído

de

minério incorporado em item.

Caso um futuro item use 50 g:

não registrar automaticamente esses 50 g como destruídos caso o material continue fisicamente incorporado ao equipamento.

Criar possibilidade futura:

embedded_lunar_weight_mg.

==================================================
63. MODELO DE DADOS SUGERIDO
==================================================

Adaptar nomes ao projeto.

Não criar tabelas duplicadas se equivalentes já existirem.

Possíveis entidades:

LunarMineralConfig

CoinDenomination

EconomicAccount

EconomicBalance

EconomicLedgerEntry

TreasuryState

GuildEconomyState

Expedition

ExpeditionResource

BossWorldState

BossFirstKill

EchoDefinition

EchoUnlock

EchoRitualSession

EchoRitualContribution

EchoVictory

NPCInventory

NPCProductionState

==================================================
64. CONCORRÊNCIA
==================================================

Economia multiplayer exige proteção contra race condition.

Utilizar:

- row locks;
- transações;
- unique constraints;
- idempotency;
- versioning quando adequado.

Casos obrigatórios:

dois requests coletando mesma pepita;

dois requests gastando mesma moeda;

duas tentativas de dividir mesma pepita;

dois grupos tentando first kill simultaneamente;

duas confirmações de ritual;

duas claims de recompensa.

==================================================
65. TESTES DE CONSERVAÇÃO
==================================================

Criar testes de propriedade/invariantes.

Exemplo:

peso antes da divisão
=
peso depois.

peso de minério consumido na cunhagem
=
peso das moedas criadas.

peso transferido
=
peso recebido.

ritual:
peso removido
=
peso requerido.

Nenhuma operação normal deve gerar massa positiva inesperada.

==================================================
66. TESTES DA MOEDA
==================================================

Testar:

1 pequena.

1 média.

1 grande.

Conversão entre denominações.

Pagamento misto.

Saldo insuficiente.

Pagamento exato.

Tentativa de gasto duplo.

Transferência concorrente.

Wallet de jogador.

Wallet de NPC.

Wallet da Guilda.

Wallet do Tesouro.

==================================================
67. TESTES DAS PEPITAS
==================================================

Testar:

1.000 → 500 + 500.

1.000 → 10 × 100.

1.000 → 500 + 5 × 100.

500 → 5 × 100.

Impedir:

100 → 50 + 50.

Testar concorrência.

==================================================
68. TESTES DE EXPEDIÇÃO
==================================================

Testar:

instância exclusiva.

seed estável.

reconnect.

resource unique ID.

coleta única.

encerramento.

tentativa de reentrada.

anti-reroll.

minério inexistente.

100 g.

500 g.

1.000 g.

==================================================
69. TESTES DOS BOSSES
==================================================

Testar:

boss vivo.

first kill.

duas kills concorrentes.

global unlock.

boss não respawna.

chance de encontro desligada após morte.

criação da marca do eco.

==================================================
70. TESTES DOS ECOS
==================================================

Testar:

marca não existe antes do boss morrer.

marca existe depois.

ritual individual.

ritual coletivo.

pepitas.

moedas.

pagamento misto.

escrow.

cancelamento.

desconexão.

pagamento exato.

impedir overpay.

unlock permanente.

derrota não remove unlock.

nova tentativa gratuita.

first victory.

reward única.

tentativa de claim duplicado.

==================================================
71. SIMULADOR ECONÔMICO
==================================================

Criar simulador separado dos dados reais de produção.

Permitir simular:

10 jogadores.

100 jogadores.

1.000 jogadores.

NPCs vendendo.

NPCs comprando.

descoberta de minério.

cunhagem.

destruição em rituais.

leilões.

acúmulo de riqueza.

falta de liquidez.

==================================================
72. CENÁRIOS EXTREMOS
==================================================

Simular:

Minério Lunar quase nunca aparece.

Minério aparece demais.

Jogadores guardam todo minério.

Jogadores vendem tudo.

Muitas moedas são destruídas por ecos.

Ninguém usa ecos.

NPC rico acumula grande saldo.

Guilda fica sem caixa.

Tesouro fica com pouco minério.

Grande concentração de moedas em poucos jogadores.

==================================================
73. OBJETIVO DAS SIMULAÇÕES
==================================================

Não buscar “economia perfeita”.

Buscar estabilidade jogável.

Detectar:

- inflação;
- deflação;
- moeda parada;
- NPCs sem dinheiro;
- excesso de dinheiro;
- falta de minério;
- rituais caros demais;
- rituais irrelevantes;
- emissão excessiva.

==================================================
74. GODOT — INVENTÁRIO
==================================================

Atualizar interface para apresentar:

Pepita Lunar 100 g.

Pepita Lunar 500 g.

Pepita Lunar 1.000 g.

Permitir ação:

DIVIDIR.

Mostrar resultado antes de confirmar.

==================================================
75. GODOT — CARTEIRA
==================================================

Exibir claramente:

MOEDAS LUNARES

Pequena:
X.

Média:
Y.

Grande:
Z.

Mostrar também:

equivalência/peso total.

Evitar esconder denominações em um único número.

==================================================
76. GODOT — RITUAL
==================================================

Na marca do eco:

mostrar texto enigmático.

Mostrar:

peso exigido.

peso contribuído.

peso restante.

Permitir:

pepitas;

moedas;

contribuição coletiva.

Mostrar claramente que:

RECURSOS SERÃO DESTRUÍDOS.

Exigir confirmação.

==================================================
77. GODOT — ECO
==================================================

Mostrar estados:

BOSS AINDA VIVO.

ECO INDISPONÍVEL.

ECO DISPONÍVEL — NÃO DESBLOQUEADO.

RITUAL EM PROGRESSO.

ECO DESBLOQUEADO.

PRIMEIRA VITÓRIA PENDENTE.

PRIMEIRA VITÓRIA CONCLUÍDA.

==================================================
78. DISCORD
==================================================

Discord deve consumir as mesmas APIs.

Não duplicar lógica econômica dentro do bot.

Comandos futuros podem consultar:

saldo;

pepitas;

boss status;

echo status.

Mas servidor continua sendo fonte de verdade.

==================================================
79. PRIMEIRO ANDAR
==================================================

Implementar e testar tudo inicialmente no primeiro andar.

Não construir vinte andares manualmente.

Fazer arquitetura data-driven.

Quando andar 1 estiver validado:

andar 2 deve poder reutilizar a mesma infraestrutura alterando configuração.

==================================================
80. COMPATIBILIDADE COM DADOS EXISTENTES
==================================================

Executar migrations com cuidado.

Antes:

backup lógico ou orientação clara.

Gerar relatório:

- tabelas alteradas;
- colunas;
- índices;
- constraints;
- dados migrados.

Nunca apagar dados para simplificar implementação.

==================================================
81. OBSERVABILIDADE
==================================================

Adicionar logs estruturados.

Métricas importantes:

lunar_mineral_discovered_total

lunar_mineral_destroyed_total

lunar_coin_minted_weight

lunar_coin_burned_weight

lunar_coin_circulating_weight

treasury_mineral_weight

guild_coin_weight

echo_rituals_completed

echo_coin_burn_weight

echo_mineral_burn_weight

==================================================
82. ALERTAS DE INVARIANTE
==================================================

Se auditoria detectar:

massa duplicada;

saldo negativo;

coin supply incompatível;

resource coletado duas vezes;

reward duplicada;

gerar log crítico.

Nunca corrigir silenciosamente criando ou apagando dinheiro.

==================================================
83. ORDEM DE IMPLEMENTAÇÃO
==================================================

A ordem é obrigatoriamente pensada para reduzir retrabalho.

FASE A — AUDITORIA

1. Ler repositório.
2. Mapear arquitetura.
3. Mapear economia.
4. Mapear migrations.
5. Mapear Godot.
6. Mapear boss.
7. Mapear procedural.
8. Mapear testes.
9. Gerar relatório.

FASE B — FUNDAÇÃO ECONÔMICA

10. Criar unidade canônica de peso.
11. Criar configurações.
12. Criar denominações.
13. Criar contas econômicas.
14. Criar ledger.
15. Criar migrations.
16. Criar invariantes.

FASE C — MINÉRIO

17. Criar pepitas.
18. Migrar/adaptar inventário.
19. Implementar divisão.
20. Testar conservação.

FASE D — MOEDA LUNAR

21. Criar três denominações.
22. Criar wallets.
23. Criar seleção de moedas.
24. Criar troca de denominação.
25. Criar transferências.
26. Testar.

FASE E — TESOURO

27. Reservas.
28. Cunhagem.
29. Emissão.
30. Distribuição de denominações.
31. Auditoria.

FASE F — GUILDA/NPCS

32. Integrar Guilda.
33. Remover geração artificial de dinheiro.
34. NPC wallet.
35. NPC inventory.
36. Compra/venda.
37. Garantir zero saldo inicial dos comerciantes.
38. Preservar estoques iniciais.

FASE G — PROCEDURAL

39. Instâncias exclusivas.
40. Seeds.
41. lifecycle.
42. reconexão.
43. recursos raros.
44. anti-reroll.
45. coleta atômica.

FASE H — BOSS ORIGINAL

46. Estado global.
47. encounter existente.
48. first kill.
49. unlock global.
50. persistência histórica.

FASE I — ECO

51. marca.
52. definição de ritual.
53. escrow.
54. contribuição.
55. consumo.
56. desbloqueio.
57. repetição.
58. first reward.

FASE J — INTEGRAÇÕES

59. leilão.
60. dívidas.
61. recuperação de itens.
62. Central ADM.
63. Discord.
64. Godot.

FASE K — ECONOMIA AUTOMÁTICA

65. simulador.
66. telemetria.
67. observe-only.
68. validação.
69. somente depois política ativa do rei.

FASE L — REGRESSÃO

70. testes unitários.
71. testes integração.
72. concorrência.
73. migrations.
74. first-floor end-to-end.
75. reconexão.
76. economia.

==================================================
84. NÃO DEFINIR AGORA
==================================================

Ainda NÃO definir valores finais de:

- frequência do Minério Lunar;
- preço absoluto por grama;
- reservas iniciais;
- quantidade inicial de moedas;
- custo de cada eco;
- recompensa do eco;
- loot do boss;
- equipamentos do boss;
- probabilidades finais de drop;
- taxas de Guilda;
- impostos;
- taxas de troca de moedas;
- receitas complexas dos NPCs.

Criar infraestrutura configurável.

==================================================
86. PUBLICAÇÃO
==================================================

Se houver permissão:

publicar artefatos verificáveis usando:

GitHub Actions

ou

GitHub Release prerelease.

Não fazer merge em main automaticamente.

Se ambiente não permitir publicação:

configurar workflow reproduzível.

Informar exatamente:

- o que falta;
- qual permissão;
- qual dependência;
- qual comando;
- qual artifact deveria ser produzido.

NUNCA fabricar link de download.

==================================================
87. RELATÓRIO FINAL
==================================================

Ao final apresentar:

Branch utilizada.

Arquivos modificados.

Migrations.

Novos modelos.

Novos endpoints.

Mudanças Godot.

Mudanças Discord.

Mudanças Central ADM.

Testes executados.

Testes aprovados.

Testes não executados.

Problemas encontrados.

Invariantes econômicos verificados.

Quantidade de Minério Lunar simulada.

Moedas cunhadas em simulação.

Moedas destruídas.

Resultados das simulações.

Pendências

Links reais, se existirem.

==================================================
88. CRITÉRIO PRINCIPAL DE ACEITAÇÃO
==================================================

O sistema deverá conseguir responder corretamente, em qualquer momento:

QUANTO MINÉRIO LUNAR JÁ ENTROU NO MUNDO?

ONDE ELE ESTÁ?

QUANTO ESTÁ EM PEPITAS?

QUANTO ESTÁ EM MOEDAS?

QUANTO ESTÁ NO TESOURO?

QUANTO FOI DESTRUÍDO?

QUANTAS MOEDAS PEQUENAS EXISTEM?

QUANTAS MÉDIAS?

QUANTAS GRANDES?

QUANTAS ESTÃO EM CIRCULAÇÃO?

QUEM POSSUI CADA SALDO?

QUAIS BOSSES AINDA ESTÃO VIVOS?

QUAIS ANDARES FORAM LIBERADOS?

QUAIS ECOS EXISTEM?

QUEM DESBLOQUEOU CADA ECO?

QUEM JÁ RECEBEU SUA RECOMPENSA ÚNICA?

Se qualquer uma dessas respostas depender de estimativa,
dados duplicados ou valores criados pelo cliente,
a implementação está incorreta.

==================================================
89. PRINCÍPIO FINAL
==================================================

Não tente fazer uma economia perfeita na primeira versão.

Primeiro faça uma economia:

RASTREÁVEL.

CONSISTENTE.

AUDITÁVEL.

SERVER-AUTHORITATIVE.

SEM DUPLICAÇÃO.

SEM DINHEIRO INFINITO.

SEM MINÉRIO INFINITO.

Depois use simulações para balancear.

O Dungeon Game deve parecer um mundo em funcionamento,
não uma série de lojas com recursos infinitos.

Implemente as fundações primeiro.

Só depois automatize a economia.