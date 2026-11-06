# Balanceamento 0.8 — evidências e decisões

Simulações locais reproduzíveis, sem alterar dados ou moedas: `python scripts/compare_levels_08.py` (60 mil monstros, comparação com relatório 0.7 congelado) e `python scripts/balance_08.py` (54 mil encontros isolados, seis perfis legais, duas espécies e três proximidades).

A correção preservou todos os bins anteriores, exceto cauda superior transformada de 0,5%: o nível máximo saiu de 0% para 0,55% distante e 2,10% perto do boss nas seeds medidas. Média do slime: 2,5112→2,5167 em p=0; 3,6262→3,6472 em p=1. Nenhum HP/ataque/taxa/recompensa foi arbitrariamente reduzido. Perfis antigos e estatísticas congeladas não foram recalculados.

Comparação em p=0,5, início com vida/energia completas, alvo em ordem fixa, habilidade enquanto houver energia e ataque básico depois. Não há tempo sintético por turno ou medição de decisões humanas. Dívida não modifica combate; o perfil endividado reproduziu exatamente o de equipamento básico.

| Perfil | Vitória individual | Turnos médios | Vitória grupo 2 | Turnos médios grupo |
|---|---:|---:|---:|---:|
| iniciante_sem_arma | 98.6% | 4.73 | 0.0% | 2.96 |
| iniciante_espada | 100.0% | 3.65 | 0.0% | 3.00 |
| iniciante_endividado | 100.0% | 3.65 | 0.0% | 3.00 |
| forca_nivel5 | 100.0% | 2.33 | 92.5% | 5.26 |
| defesa_nivel5 | 100.0% | 2.98 | 100.0% | 7.77 |
| equilibrado_nivel3 | 100.0% | 2.98 | 5.5% | 5.22 |

Grupos são opcionais e oferecem mais risco ao iniciante, pois cada sobrevivente responde. Não se aumentou o número automático de inimigos nem se modificaram spawns para criar pares artificiais. O padrão permanece dois alvos com alcance limitado; preparação/equipamento/atributos importam. Recomenda-se observar jogadores antes de alterar recompensas ou facilitar grupos.

Telemetria real: `GameplayDay` agrega contadores por personagem/dia UTC; combate registra turnos, dano efetivo, vitória/derrota/fuga e duração de parede (inclui pensamento/desconexão), evolução de nível, sequência/expedição, pendências resgatadas, taxa/dívida, perdas de unidades e recuperação. Duração histórica desconhecida permanece nula, não é inventada. Treino é separado; ganhos administrativos não entram nos intervalos normais de nível. Agregados não substituem teste controlado nem provam equilíbrio de todas as jornadas.

Performance: polling principal consolidado de quatro requisições para uma; Phaser/mapa importados somente quando necessários ao personagem. Build atual: aproximadamente 41 kB do jogo + 186 kB do cliente compartilhado antes do mapa; o chunk Map/Phaser de 1.494 kB continua necessário durante o jogo e ainda merece acompanhamento. Servidor e consultas serão medidos na validação final. Nenhum Redis obrigatório adicionado.

Efeitos sintetizados originais de ataque/dano/vitória/interação/interface são opcionais, desligados por padrão, com volume e silêncio persistidos. Ausência de AudioContext não bloqueia o jogo. Visual usa sprites existentes, tintas/rótulos por categoria, foco de alvo, feedback numérico e nomes reais de NPCs, sem assets comerciais.

## Medição técnica local

`scripts/benchmark_08.py`, 50 amostras úteis por endpoint/configuração, TestClient HTTP e PostgreSQL real, usuário sequencial na cidade, duas chamadas de aquecimento. Artefato: `performance-0.8.json`. Sem limites, `/state` p50 20,63ms/p95 24,17ms e 36 consultas. Com limites persistentes, p50 24,14ms/p95 26,58ms e 38 consultas. Consultas de métricas/recursos/contratos com limites: p95 6,98/6,53/7,06ms. Não é teste de carga concorrente nem latência de rede/produção; recursos/contratos vazios na cidade não representam regiões carregadas.

Gargalos observados: snapshot ainda faz muitas consultas de salas/atlas/estado e serializa a carteira/histórico; Phaser continua aproximadamente 1,49MB minificado (adiado até login). Polling Web consolidado reduziu quatro chamadas periódicas a uma, mas não eliminou o trabalho SQL interno. Próxima versão deve perfilar snapshots representativos com muitos personagens, agrupar leituras e verificar plano/índices em volume real antes de cache. Limites adicionam duas consultas curtas por requisição autenticada em troca de consistência entre processos e sobrevivência ao rollback. Testes de carga e broker de presença continuam pendentes antes de múltiplos workers.
