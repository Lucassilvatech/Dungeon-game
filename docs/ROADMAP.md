# Roadmap verificável

1. Base entregue: conta → personagem → mapa → combate → loot → Guilda → retomada. Critério: testes PostgreSQL e fluxo navegador.
2. Validar bot em servidor Discord real com credenciais; consultar o mesmo personagem web e provar uso único do vínculo.
3. Endurecer autenticação: logout/revogação, limitação de tentativas, recuperação, TLS e auditoria operacional; testes de abuso.
4. Presença multiplayer e grupos: ver dois personagens, formar grupo persistente, reconectar e sincronizar ações via WebSocket. Só depois combate cooperativo com fila de turnos.
5. Masmorra e chefe em grupo: elegibilidade, reserva de encontro e recompensa única por participante; testar vitórias simultâneas e desbloqueio global único.
6. Mercado vertical: anúncio retira item da mochila, compra atômica transfere item/moedas/imposto. Testar dois compradores simultâneos e falha sem saldo. Acrescentar expiração/caixa e até três renovações.
7. Guilda: contratos com reserva de orçamento, filiais e despesas auditáveis. NPCs com estoque/orçamento e comércio entre andares desbloqueados.
8. Profissões: receita, consumo real de materiais, domínio e falha configurável; 5 categorias com 100 níveis; garantia ao dominar.
9. Mentoria: elegibilidade de veteranos, instâncias específicas, moeda vinculada, ranking mensal e proteção contra exploração.
10. Banco Central: painéis de oferta/preços, regras de emissão aprovadas, auditoria e intervenção de crise; sem empréstimos/juros.

Mercado, empréstimos, política monetária avançada, árvores complexas e todas as profissões não fazem parte do primeiro MVP.
