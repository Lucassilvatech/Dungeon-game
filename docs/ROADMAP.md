# Roadmap: primeiro andar antes de expandir a Torre

> **Estratégia atual 0.9:** backend autoritativo, **Web como cliente principal**, **Discord estritamente read-only para gameplay**. Godot Windows/Android estão **FROZEN**; APK/EXE não são requisitos deste ciclo. Código/presets/builds e documentação histórica preservados. Ver [GODOT_FREEZE.md](GODOT_FREEZE.md) e [CONSOLIDATION_0.9.md](CONSOLIDATION_0.9.md). Descrições de equipamento confirmado via Discord abaixo são históricas e foram desativadas em 0.9.

## Prioridade ativa

1. Fundações e integração da economia Lunar (consolidação atual não conclui o cutover).
2. Backend autoritativo e testes de integridade.
3. Web e Central ADM.
4. NPCs/estoques/fluxo econômico.
5. Procedural/recursos/anti-reroll.
6. Bosses globais.
7. Ecos e rituais.
8. Balanceamento por evidência.
9. Observabilidade e desempenho.

Depois: retomar Godot, portar sistemas consolidados, melhorar arte e gerar Windows/Android. Discord permanece observacional, inclusive para novos sistemas. Não planejar mais mutações confirmadas no Discord. Histórico a seguir preservado; propostas anteriores de mutações Discord não são mais prioridades.

Entregue em 0.3: inimigos persistentes sem respawn indevido, golpe final idempotente, morte/fade/remoção visual, wandering autoritativo de baixa frequência, fórmula de dano, materiais empilháveis com limite, recompensa em lote pela recepcionista, ausência de curadora nas salas, salas amplas e novos temas/layouts por seed. Treino e persistência foram preservados.

Entregue em 0.4: ciclo de expedição com compromisso, fuga transacional com perda global de pendências/XP atual, retomada após reconexão, conclusão da sala e tiers de perigo regionais. A prioridade complementar escolhida foi a sinalização/feedback da exploração, alinhada aos itens 1 e 2 abaixo; combate multi-alvo não foi antecipado.

Entregue em 0.5: morte transacional em Aventura, perda global das pendências/XP atual, taxa e dívida médica com piso −10.000, penalidade repetível de até 10 níveis, transferência dos itens para leilões exclusivos de jogadores, reserva de lances e resolução automática, pontos manuais/dívida de atributos e UI. O mercado geral continua fora do escopo.

Entregue na branch de revisão 0.6: cliente Godot jogável por API, presets/exportações Windows/Android, viagem rápida descoberta, Salão de Leilões/NPC próprio, anúncios detalhados, proteção/recuperação individual da espada inicial, Central ADM web com permissões/prévias/auditoria e Banco Central manual com recursos de teste isolados. React/Phaser permanece. Não houve merge automático na main.

Implementado na evolução 0.7: atributos efetivos no status/combate; acesso Android configurável e diagnóstico específico; sequência persistente 1–10%; espécies procedurais compartilhadas; retenção de estado temporário; morte 0–5 unidades e recuperação pessoal; confisco com avaliação/recorrência; visibilidade/histórico de leilões e eventos ADM explicados. Builds versionados e checks de distribuição. Ver PROCEDURAL_ECONOMY_UPDATE.md para evidências e limites reais de validação.

Implementado em 0.8: Web como cliente principal, máximo procedural raro/alcançável com comparação estatística, grupos pequenos opcionais com estado persistente e recompensa única, coleta finita e contratos com reserva real, consultas privadas Discord/equipamento confirmado, métricas e simulações, áudio opcional, painel ADM e limites persistentes. Evidências e limitações em [DELIVERY_0.8.md](DELIVERY_0.8.md); Godot preservado sem exportação nova.

Próximos passos 0.9, sem marcar como entregues:

1. Sessões reais com iniciantes para avaliar tempo de combate, dívida e risco dos grupos. Simulação mostrou dificuldade alta para iniciantes; não alterar estatísticas individuais arbitrariamente.
2. Validar bot em servidor Discord com credenciais seguras; manter somente consultas privadas, sem operações de gameplay.
3. Perfilar snapshot com volume representativo, agrupar consultas e medir contenção financeira. Bundle Phaser ainda grande, embora carregado após login.
4. Broker de presença antes de múltiplos workers, teste de carga e implantação TLS protegida. Rate limits e revogação já existem, mas não substituem controles de borda.
5. Refinar acessibilidade e apresentação com feedback de jogadores. Expandir poucos recursos/contratos somente com dados de economia real.
6. Godot permanece opcional; Windows/Android reais e o alerta histórico de distribuição mantêm trilha de validação separada, sem exigir novo build para jogar na Web.

Andares superiores, raids avançadas, mercado completo, emissão autônoma do Banco Central, mentoria, muitas profissões e endgame continuam fora do escopo atual. O conteúdo legado não foi apagado; não deve orientar novas implementações até o primeiro andar estar consolidado.


## Combate futuro aprovado conceitualmente — não implementado

Sistema sem classes, aprendizado livre e ensino entre jogadores, maestria individual, seis slots ativos, capacidade inicial proposta de 100 com expansão gradual até 120, sobrecarga universal, resistências/interações elementais, purificação e combate cooperativo por turnos. Esses números são planejamento de capacidade de habilidades futura, não os pontos de atributo atuais. A arquitetura do cliente separa API/estado/UI para acomodar evolução depois; nada dessa lista foi antecipado nesta migração.
