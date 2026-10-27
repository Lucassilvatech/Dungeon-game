# Diagnóstico prévio — escopo lunar

Base auditada: af9dcb5, branch feature/web-discord-first-floor-0.8 limpa. Usar essa feature existente porque contém 0.8; voltar à feature 0.7 perderia integração de grupos/contratos/limites. Main preservada. Documento integral normalizado em SCOPE.md (o anexo era um envelope JSON contendo texto).

Arquitetura confirmada: SQLAlchemy models.py; migrações até 4cee57744ea1; FastAPI main.py; React/Phaser api/Map/main; Godot main/api/map; bot HTTP privado; ADM via admin_service com preview/confirm. Core econômico economy/admin_economy/auctions/debt/recovery/contracts mantém NUMERIC inteiro, ledger com referência única, carteira assinada e mutex antes do personagem. Não existe comerciante com ciclo produtivo. Coleta de erva/minério de musgo NÃO é Minério Lunar e não deve ser renomeada.

Incompatibilidades: coins negativo é dívida, não moedas físicas negativas; Treasury já tem gênese histórica, mint ADM e burn abstratos. Leilões/contratos reservam unidade antiga. Não fabricar minério retroativo para cobrir saldos. É necessária equivalência LEGACY_COIN_UNIT_WEIGHT_MG, decisão de lastro inicial e cutover único com reconciliação. Decisão posterior aprovada pelo usuário: 1 moeda antiga = 1g (1.000mg), com lastro inicial auditado. Nenhuma conversão ativada antes de integrar e testar os fluxos financeiros. A infraestrutura pode iniciar vazia, sem duplicar a carteira legada.

Expedições pertencem a personagem, não grupo; Raid é apenas lobby. Seed/estado sobrevivem reconexão, mas faltam anti-reroll e encerramento definitivo com recursos. Boss especial e chefe estático têm cópias por personagem, enquanto floor:2 já é global. Migrar first kill histórico requer reconciliação própria, sem conceder drops indefinidos. Ecos/rituais não existem. Combate avançado (sobrecarga/elementos/seis slots/maestria) aparece como preservar no escopo, mas não existe na base; não declarar preservado algo ausente.

## Classificação por seção

| Seção | Requisito | Diagnóstico inicial |
|---|---|---|
| 0 | REGRAS GERAIS DE EXECUÇÃO | parcialmente implementado; reaproveitar base 0.8 |
| 1 | PRINCÍPIO CENTRAL DA ECONOMIA | ausente; necessita migration |
| 2 | UNIDADE CANÔNICA DE CONTABILIDADE | parcialmente implementado; reaproveitar base 0.8 |
| 3 | MINÉRIO LUNAR | ausente; necessita migration |
| 4 | DIVISÃO DE PEPITAS | ausente; necessita migration |
| 5 | ORIGEM DO MINÉRIO LUNAR | ausente; necessita migration |
| 6 | MAPAS PROCEDURAIS EXCLUSIVOS | parcial/incompatível; requer adaptação e testes |
| 7 | ANTI-REROLL DAS EXPEDIÇÕES | parcial/incompatível; requer adaptação e testes |
| 8 | RECONEXÃO | parcial/incompatível; requer adaptação e testes |
| 9 | COLETA DE MINÉRIO | ausente; necessita migration |
| 10 | MOEDA OFICIAL | ausente; necessita migration |
| 11 | PESOS DAS MOEDAS | ausente; necessita migration |
| 12 | VALOR DA MOEDA | ausente; necessita migration |
| 13 | CARTEIRA DO JOGADOR | ausente; necessita migration |
| 14 | CARTEIRAS ECONÔMICAS | ausente; necessita migration |
| 15 | TROCA DE DENOMINAÇÕES | ausente; necessita migration |
| 16 | SELEÇÃO AUTOMÁTICA DE MOEDAS | ausente; necessita migration |
| 17 | CUNHAGEM | ausente; necessita migration |
| 18 | COMPOSIÇÃO DA CUNHAGEM | ausente; necessita migration |
| 19 | INVARIANTE GLOBAL DO MINÉRIO | ausente; necessita migration |
| 20 | GUILDA | ausente; necessita migration |
| 21 | NPCS E ECONOMIA REAL | ausente; necessita migration |
| 22 | NPC NÃO PODE GASTAR O QUE NÃO TEM | ausente; necessita migration |
| 23 | ESTOQUE DOS NPCS | ausente; necessita migration |
| 24 | ORIGEM DA PRIMEIRA LIQUIDEZ | ausente; necessita migration |
| 25 | ECONOMIA EM DUAS FASES | ausente; necessita migration |
| 26 | LEDGER ECONÔMICO | ausente; necessita migration |
| 27 | FASE ECONÔMICA 2 — POLÍTICA DO REI | ausente; necessita migration |
| 28 | EMISSÃO AUTOMÁTICA DO REI | ausente; necessita migration |
| 29 | CENTRAL ADM ECONÔMICA | ausente; necessita migration |
| 30 | BOSSES ORIGINAIS | parcial/incompatível; requer adaptação e testes |
| 31 | MORTE GLOBAL DO BOSS | parcial/incompatível; requer adaptação e testes |
| 32 | PROGRESSÃO COLETIVA DO SERVIDOR | parcial/incompatível; requer adaptação e testes |
| 33 | EVENTO HISTÓRICO | parcial/incompatível; requer adaptação e testes |
| 34 | MARCA DO ECO | ausente; necessita migration |
| 35 | CONCEITO DO ECO | ausente; necessita migration |
| 36 | RITUAL DO ECO | ausente; necessita migration |
| 37 | PAGAMENTO COM PEPITAS | ausente; necessita migration |
| 38 | PAGAMENTO COM MOEDAS | ausente; necessita migration |
| 39 | PAGAMENTO MISTO | ausente; necessita migration |
| 40 | RITUAL COLETIVO | ausente; necessita migration |
| 41 | ESCROW DO RITUAL | ausente; necessita migration |
| 42 | QUEM RECEBE O DESBLOQUEIO | ausente; necessita migration |
| 43 | PAGAMENTO ÚNICO | ausente; necessita migration |
| 44 | RECOMPENSA DO ECO | ausente; necessita migration |
| 45 | REPETIÇÃO DO ECO | ausente; necessita migration |
| 46 | BOSS ORIGINAL VS ECO | ausente; necessita migration |
| 47 | RECOMPENSA DO BOSS ORIGINAL | ausente; necessita migration |
| 48 | INTEGRAÇÃO COM ECONOMIA EXISTENTE | parcial/incompatível; requer adaptação e testes |
| 49 | MIGRAÇÃO DA MOEDA ANTIGA | parcial/incompatível; requer adaptação e testes |
| 50 | PREÇOS | ausente; necessita migration |
| 51 | LEILÕES | parcial/incompatível; requer adaptação e testes |
| 52 | DÍVIDAS DA GUILDA | parcial/incompatível; requer adaptação e testes |
| 53 | RECUPERAÇÃO DE ITENS | parcial/incompatível; requer adaptação e testes |
| 54 | ESPADA DE APRENDIZ | parcialmente implementado; reaproveitar base 0.8 |
| 55 | COMBATE | parcial/incompatível; requer adaptação e testes |
| 56 | SISTEMA SEM CLASSES | parcial/incompatível; requer adaptação e testes |
| 57 | CAPACIDADE | parcial/incompatível; requer adaptação e testes |
| 58 | SOBRECARGA | parcial/incompatível; requer adaptação e testes |
| 59 | INTERAÇÕES ELEMENTAIS | parcial/incompatível; requer adaptação e testes |
| 60 | ALIADOS | parcial/incompatível; requer adaptação e testes |
| 61 | EQUIPAMENTOS | parcialmente implementado; reaproveitar base 0.8 |
| 62 | FUTURO USO DO MINÉRIO EM CRAFT | restrição/critério; preservar e verificar |
| 63 | MODELO DE DADOS SUGERIDO | ausente; necessita migration |
| 64 | CONCORRÊNCIA | ausente; necessita migration |
| 65 | TESTES DE CONSERVAÇÃO | ausente; necessita migration |
| 66 | TESTES DA MOEDA | ausente; necessita migration |
| 67 | TESTES DAS PEPITAS | ausente; necessita migration |
| 68 | TESTES DE EXPEDIÇÃO | ausente; necessita migration |
| 69 | TESTES DOS BOSSES | ausente; necessita migration |
| 70 | TESTES DOS ECOS | ausente; necessita migration |
| 71 | SIMULADOR ECONÔMICO | ausente; necessita migration |
| 72 | CENÁRIOS EXTREMOS | ausente; necessita migration |
| 73 | OBJETIVO DAS SIMULAÇÕES | ausente; necessita migration |
| 74 | GODOT — INVENTÁRIO | ausente; necessita migration |
| 75 | GODOT — CARTEIRA | ausente; necessita migration |
| 76 | GODOT — RITUAL | ausente; necessita migration |
| 77 | GODOT — ECO | ausente; necessita migration |
| 78 | DISCORD | parcialmente implementado; reaproveitar base 0.8 |
| 79 | PRIMEIRO ANDAR | parcialmente implementado; reaproveitar base 0.8 |
| 80 | COMPATIBILIDADE COM DADOS EXISTENTES | parcialmente implementado; reaproveitar base 0.8 |
| 81 | OBSERVABILIDADE | ausente; necessita migration |
| 82 | ALERTAS DE INVARIANTE | ausente; necessita migration |
| 83 | ORDEM DE IMPLEMENTAÇÃO | ausente; necessita migration |
| 84 | NÃO DEFINIR AGORA | restrição/critério; preservar e verificar |
| 86 | PUBLICAÇÃO | restrição/critério; preservar e verificar |
| 87 | RELATÓRIO FINAL | restrição/critério; preservar e verificar |
| 88 | CRITÉRIO PRINCIPAL DE ACEITAÇÃO | restrição/critério; preservar e verificar |
| 89 | PRINCÍPIO FINAL | restrição/critério; preservar e verificar |

## Plano incremental

A diagnóstico registrado antes do código. B unidade inteira, contas/ativos, ledger imutável e auditoria; migração puramente aditiva, sem gênese implícita. C pepitas e divisão exata. D moedas/seleção/exchange/transferências. E cunhagem de minério já existente; emissão como transferência. Testar essas fundações antes de F integração NPC/legado. F depende de equivalência/lastro explicitamente definidos; dry-run sem escrita primeiro. Depois G recursos de instância e lifecycle; H boss global; I escrow/ritual/unlocks/recompensas sem inventar loot; J UI Godot/Web/Discord/ADM e finanças legadas; K simulador isolado/observe-only; L regressão e cópia preenchida. Publicação não é requisito para modificar main e nunca haverá merge automático.

Valores indefinidos ficam indisponíveis/None, não substituídos por taxas/preços/drop inventados. Defaults técnicos de moedas 1/5/10g explicitamente permitidos. Documentar progresso real por fase; este diagnóstico não atesta implementação.
