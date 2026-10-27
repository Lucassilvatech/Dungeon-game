# Implementação lunar — progresso verificável

**Escopo integral ainda em implementação. Não é release concluída.** A ordem do documento exige concluir a fundação e a transição financeira antes de conectar recursos, bosses e ecos. Fundações preservadas na branch de consolidação feature/lunar-web-discord-readonly-0.9; main e ambiente operacional preservados. Ver CONSOLIDATION_0.9.md para publicação e validações atuais.

## Decisão aprovada

Usuário confirmou **1 moeda antiga = 1g = 1.000mg**, com lastro inicial auditado. O relatório de gênese deve distinguir esse lastro histórico de minério descoberto em expedições novas. Saldos negativos representam obrigações, não moedas físicas negativas. A pergunta de equivalência registrada no diagnóstico foi respondida; não é mais bloqueio.

## Fundações implementadas

`backend/app/lunar.py`: unidade inteira validada (rejeita bool/float/string), ativos persistidos com pesos de moeda técnicos 1/5/10g e pepitas 100/500/1.000g; configuração de denominações somente antes de movimentações. Contas genéricas player/npc/guild/treasury/escrow/expedition. Quantidades não negativas; pagamentos exatos com três denominações divisíveis e menor número de moedas, sem sobrepagamento. Divisão gratuita de pepitas preserva massa; não divide pepita de 100g. Troca conserva peso; cunhagem transforma apenas minério já existente em moedas e emissão é transferência. Essas primitivas não são uma política monetária automática.

Ledger persistente com chave idempotente vinculada a parâmetros, ator, justificativa, postings, contexto e timestamp; trigger PostgreSQL rejeita editar/excluir histórico. Operações financeiras lunares usam mutex transacional antes de personagens/contas. Crédito de massa exige fonte explícita interna; nenhuma rota permite ao cliente inventar descoberta ou gênese. Auditoria reconcilia massa, contas e cada ativo com os postings; divergências geram log crítico, sem consertar silenciosamente.

`legacy_preview`: snapshot bloqueado/coerente de carteiras positivas, Tesouro, Banco Central, reservas de leilões e contratos; dívida em coluna separada. Produz massa exigida para lastro inicial e fingerprint, sem escrita, sem emissão e sem somar duas carteiras utilizáveis.

### Modelos e migração

`LunarAsset`, `LunarAccount`, `LunarHolding`, `LunarEntry`, `LunarSupply`. Revisão **4a8687e5317c**, pai 4cee57744ea1: cinco tabelas novas, constraints, índice de tipo no ledger, unicidade/idempotência, FKs e trigger de histórico. Seed de infraestrutura cria só definições e contadores zero, sem moedas/minério/contas financiadas. Nenhuma coluna antiga é alterada. Downgrade permite remoção apenas se não existir saldo nem histórico lunar; caso contrário rejeita para preservar dados.

### Endpoints

- `GET /lunar/wallet`: somente personagem autenticado; composição/massa em strings exatas; legado identificado separadamente, conversão ainda inativa.
- `POST /lunar/nuggets/split`: corpo estrito, UUID, fonte e composição; propriedade implícita do personagem, fora de combate, recibo persistente.
- `POST /lunar/coins/exchange`: mesma autorização, exige recepcionista e ausência de combate.
- `GET /admin/lunar/audit`: permissão economy.read.
- `GET /admin/lunar/legacy-preview`: permissão economy.read; dry-run sem conversão.

Cunhagem/transferência são serviços internos; não foi criada rota mutável administrativa que ignore prévia/justificativa/confirmação. Ainda não há ações lunares ADM integradas ao workflow existente.

## Validação executada

14 testes novos passaram em 6,83s: quatro divisões válidas, impossibilidade de massa arbitrária/fracionária, cunhagem idempotente, emissão, pagamento misto, troca, destruição simulada, concorrência de gasto, SQL de edição de histórico rejeitado, rollback de cunhagem, autorização/ownership, request estrita, dry-run sem alteração, congelamento de pesos e detecção de corrupção. Regressão anterior com migração preenchida/Web: 16 passaram em 13,26s (conjuntos sobrepostos, não somar). Alembic check sem divergências. Cópia real histórica: 1.155 hashes de campos originais preservados ao migrar ao novo head. **Suite completa executada: 188 testes aprovados, dois avisos de depreciação, 325,51s** (174 anteriores + 14 lunares). Nenhum teste pulado. Cópia adicional do banco real 0.8: 39 tabelas antigas (excluindo alembic_version), 1.554 hashes de linha preservados após upgrade; backup privado em /tmp, não versionado. Dry-run sobre essa cópia: 31 contas, lastro necessário 100.450.000mg (100,45kg), obrigações de dívida separadas 450.000mg, reconciliação antiga zero. Contadores lunares permaneceram zero: a leitura não converteu nem cunhou nada.

Simulador `scripts/simulate_lunar.py`: 15 cenários determinísticos isolados (10/100/1.000 jogadores × raridade/excesso/entesouramento/rituais/escassez de Tesouro), todos com diferença de massa zero. Em cada cenário 10kg iniciais são descoberta fictícia explícita; NPC começa sem dinheiro e com 50 produtos finitos de teste. Relatório SIMULATION.json discrimina descoberto/cunhado/destruído e recusas por falta de caixa por cenário. Não são probabilidades, estoques ou custos finais do jogo; não mede inflação/equilíbrio ou todas as mecânicas ainda não conectadas.

## Próximas etapas obrigatórias, não entregues

1. Conversão operacional única com preview/confirm auditados, fingerprint e reserva de lastro; adaptar **todos** os fluxos legados ao mesmo estado físico antes de ativar. Taxa médica hoje credita Tesouro mesmo quando gera dívida; no modelo lunar a parcela financiada é recebível, e só pagamento efetivo transfere moedas. Não espelhar esse crédito abstrato como criação de massa.
2. Inventário lunar integrado a capacidade/custódia/morte/recuperação e NPCs com estoque físico; venda à Guilda, comércio e financiamento legítimo. Não desativar o jogo legado até esse cutover estar testado.
3. Ocorrências únicas em expedições, geração configurável sem defaults finais, ciclo fechado e anti-reroll, snapshots de grupo e reconexão.
4. Boss único global/first kill histórico concorrente e compatibilidade com boss já derrotado; marca de eco e unlock de andar sem construir outro andar.
5. Escrow e contribuição coletiva, confirmação exata, cancelamento/timeout/reembolso, unlock permanente, combate de eco sem farm, first victory/recompensa sem inventar loot.
6. Integrações Godot/Web/Discord/ADM, leilões/dívidas/contratos/recuperação físicas, observabilidade completa, simulador comercial completo e política observe-only; só depois avaliar automatização do rei.

Histórico da etapa inicial de fundação: nenhum build novo ou publicação executada naquela etapa; a consolidação/publicação posterior é registrada em ../CONSOLIDATION_0.9.md. Não há link de download novo. Na etapa inicial não houve telas lunares; a consolidação 0.9 adiciona painel Web e consultas Discord. Godot permanece sem telas Lunares, agora congelado. Execução externa Discord e exportações nativas continuam fora da evidência atual. O simulador isolado não significa entrega antecipada da Fase K operacional.
