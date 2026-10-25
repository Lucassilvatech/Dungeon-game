# Roadmap: primeiro andar antes de expandir a Torre

Entregue em 0.3: inimigos persistentes sem respawn indevido, golpe final idempotente, morte/fade/remoção visual, wandering autoritativo de baixa frequência, fórmula de dano, materiais empilháveis com limite, recompensa em lote pela recepcionista, ausência de curadora nas salas, salas amplas e novos temas/layouts por seed. Treino e persistência foram preservados.

Entregue em 0.4: ciclo de expedição com compromisso, fuga transacional com perda global de pendências/XP atual, retomada após reconexão, conclusão da sala e tiers de perigo regionais. A prioridade complementar escolhida foi a sinalização/feedback da exploração, alinhada aos itens 1 e 2 abaixo; combate multi-alvo não foi antecipado.

Entregue em 0.5: morte transacional em Aventura, perda global das pendências/XP atual, taxa e dívida médica com piso −10.000, penalidade repetível de até 10 níveis, transferência dos itens para leilões exclusivos de jogadores, reserva de lances e resolução automática, pontos manuais/dívida de atributos e UI. O mercado geral continua fora do escopo.

Entregue na branch de revisão 0.6: cliente Godot jogável por API, presets/exportações Windows/Android, viagem rápida descoberta, Salão de Leilões/NPC próprio, anúncios detalhados, proteção/recuperação individual da espada inicial, Central ADM web com permissões/prévias/auditoria e Banco Central manual com recursos de teste isolados. React/Phaser permanece. Não houve merge automático na main.

Próximos passos pequenos:

1. Executar os builds em Windows real e dispositivo Android (toque, GPU, sessões e rede) e validar a Central em ambiente de revisão; só considerar retirada do Phaser depois. Validar balanceamento do primeiro andar com jogadores: tempo por combate, risco entre concluir/fugir/morrer, capacidade de recuperação sem equipamento, taxa médica, crescimento de dívida e duração/preços dos espólios. Medir antes de fixar os parâmetros provisórios. Preservar a distinção entre salas comuns e Aventura.
2. Refinar arte original, sinalização de caminhos, áudio opcional e interação da Guilda. Melhorar seleção/navegação em dispositivos móveis.
3. Implementar encontros com grupos de inimigos: participantes/seleção de alvo/ordem de turnos, preservando a recompensa única por instância. Não declarar o lobby de raid como combate coletivo.
4. Coleta real com consumo/estoques e auditoria; contratos pequenos com orçamento reservado.
5. Medir contenção do mutex de leilões antes de escalar; broker de presença antes de múltiplos workers, limites de requisições, revogação de sessões, TLS e telemetria; otimizar bundle Phaser.
6. Validar bot em Discord externo com credenciais próprias; adicionar ações pelo mesmo backend quando tiverem fluxo estável no navegador.

Andares superiores, raids avançadas, mercado completo, emissão autônoma do Banco Central, mentoria, muitas profissões e endgame continuam fora do escopo atual. O conteúdo legado não foi apagado; não deve orientar novas implementações até o primeiro andar estar consolidado.


## Combate futuro aprovado conceitualmente — não implementado

Sistema sem classes, aprendizado livre e ensino entre jogadores, maestria individual, seis slots ativos, capacidade inicial proposta de 100 com expansão gradual até 120, sobrecarga universal, resistências/interações elementais, purificação e combate cooperativo por turnos. Esses números são planejamento de capacidade de habilidades futura, não os pontos de atributo atuais. A arquitetura do cliente separa API/estado/UI para acomodar evolução depois; nada dessa lista foi antecipado nesta migração.
