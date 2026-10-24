# Roadmap após implementação 2

Entregue nesta etapa: migração aditiva, salas/cidade/Guilda/treino, trajetos e transições, sprites originais e animações, câmera e HUD compactos, Aventura procedural determinística, segredo sem spoilers, derrota sem perdas, conclusão única e recompensa reduzida, chefe separado, lobby de raid e presença WebSocket. Os critérios de backend estão cobertos por testes; a conexão Discord externa segue pendente de credenciais.

1. **Combate cooperativo real**: reservar encontro para raid, validar presença/eligibilidade, ordem de turnos coletiva, reconectar e recompensar participantes uma única vez. Não reutilizar combates pessoais como se fossem compartilhados.
2. **Presença distribuída**: broker, expiração de presença e testes entre workers antes de aumentar processos FastAPI.
3. **Conteúdo**: novas masmorras com múltiplas subsalas, tabelas e bestiário mais rico; coleta real e layouts procedurais renováveis com limites e auditoria; rotas de NPCs.
4. **Validação Discord**: convidar bot real e consultar dados do mesmo personagem; depois expor Aventura/viagem/raids pelo backend já existente, sem duplicar regras.
5. **Segurança**: TLS, rate limit, revogação/recuperação de sessões, logs estruturados, backups e monitoramento; teste de carga.
6. **Mercado**: custódia, compra atômica com imposto, expiração e renovação; duas compras simultâneas devem produzir só uma venda.
7. **Guilda econômica**: contratos com orçamento reservado, filiais, NPCs com estoques e orçamentos reais.
8. **Profissões e mentoria**: progressão, consumo de materiais, moedas vinculadas e ranking auditável.
9. **Banco Central**: indicadores e regras de emissão aprovadas; sem empréstimos/juros.

O segundo andar segue demonstrativo. Não há economia NPC avançada, raids em combate, MMO distribuído ou todas as profissões nesta etapa.
