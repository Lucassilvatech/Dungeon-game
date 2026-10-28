# Implementação lunar — progresso verificável

## Estado atual: lotes variáveis e Administração Real

A fundação abaixo é histórica e preservada. A revisão atual **ca343e37b4ca** migra pepitas fixas para LunarMineralLot, sem holding de minério duplicado nem edição do ledger; moedas1/5/10g permanecem. Spawn2%, faixas80/15/5 e rate800 milliunits/g são defaults aprovados desta entrega. Split livre, mint parcial e operações Reais auditadas estão implementados. [Modelo e migração](VARIABLE_NUGGETS.md) · [Administração](ROYAL_ADMINISTRATION.md) · [Validação final](DELIVERY_VARIABLE_NUGGETS_0.9.md). Cutover validado em cópia privada, sem ativação operacional real.


> Atualização da continuação 0.9: [cutover operacional, migrações e validação](CUTOVER.md). O upgrade não converte o ambiente: confirmação administrativa ativa Lunar como fonte única. As descrições financeiras legadas e de conversão inativa abaixo registram a etapa anterior; após a confirmação, holdings Lunar e obrigações separadas são autoritativos. Discord segue estritamente read-only; Godot congelado.

**Registro histórico da fundação.** O cutover está implementado e validado em cópia privada; ativação no ambiente operacional real ainda não executada. A continuação procedural está em [PROCEDURAL_RESOURCES.md](PROCEDURAL_RESOURCES.md). A ordem do documento exige concluir a fundação e a transição financeira antes de conectar recursos, bosses e ecos. Fundações preservadas na branch de consolidação feature/lunar-web-discord-readonly-0.9; main e ambiente operacional preservados. Ver CONSOLIDATION_0.9.md para publicação e validações atuais.

## Decisão aprovada

Usuário confirmou **1 moeda antiga = 1g = 1.000mg**, com lastro inicial auditado. O relatório de gênese deve distinguir esse lastro histórico de minério descoberto em expedições novas. Saldos negativos representam obrigações, não moedas físicas negativas. A pergunta de equivalência registrada no diagnóstico foi respondida; não é mais bloqueio.

## Fundações implementadas

`backend/app/lunar.py`: unidade inteira validada (rejeita bool/float/string), ativos persistidos com pesos de moeda técnicos 1/5/10g e pepitas 100/500/1.000g; configuração de denominações somente antes de movimentações. Contas genéricas player/npc/guild/treasury/escrow/expedition. Quantidades não negativas; pagamentos exatos com três denominações divisíveis e menor número de moedas, sem sobrepagamento. Divisão gratuita de pepitas preserva massa; não divide pepita de 100g. Troca conserva peso; cunhagem transforma apenas minério já existente em moedas e emissão é transferência. Essas primitivas não são uma política monetária automática.

Ledger persistente com chave idempotente vinculada a parâmetros, ator, justificativa, postings, contexto e timestamp; trigger PostgreSQL rejeita editar/excluir histórico. Operações financeiras lunares usam mutex transacional antes de personagens/contas. Crédito de massa exige fonte explícita interna; nenhuma rota permite ao cliente inventar descoberta ou gênese. Auditoria reconcilia massa, contas e cada ativo com os postings; divergências geram log crítico, sem consertar silenciosamente.

`legacy_preview`: snapshot bloqueado/coerente de carteiras positivas, Tesouro, Banco Central, reservas de leilões e contratos; dívida em coluna separada. Produz massa exigida para lastro inicial e fingerprint, sem escrita, sem emissão e sem somar duas carteiras utilizáveis.

### Modelos e migração

`LunarAsset`, `LunarAccount`, `LunarHolding`, `LunarEntry`, `LunarSupply`. Revisão **4a8687e5317c**, pai 4cee57744ea1: cinco tabelas novas, constraints, índice de tipo no ledger, unicidade/idempotência, FKs e trigger de histórico. Seed de infraestrutura cria só definições e contadores zero, sem moedas/minério/contas financiadas. Nenhuma coluna antiga é alterada. Downgrade permite remoção apenas se não existir saldo nem histórico lunar; caso contrário rejeita para preservar dados.

### Endpoints

- `GET /lunar/wallet`: somente personagem autenticado; composição/massa em strings exatas; legado identificado separadamente, status LEGACY/LUNAR, sem duplicar carteira.
- `POST /lunar/nuggets/split`: corpo estrito, UUID, fonte e composição; propriedade implícita do personagem, fora de combate, recibo persistente.
- `POST /lunar/coins/exchange`: mesma autorização, exige recepcionista e ausência de combate.
- `GET /admin/lunar/audit`: permissão economy.read.
- `GET /admin/lunar/legacy-preview`: permissão economy.read; dry-run sem conversão.

Cunhagem/transferência são serviços internos; não foi criada rota mutável administrativa que ignore prévia/justificativa/confirmação. Cutover, configuração econômica e financiamento já exigem workflow administrativo explícito; ver CUTOVER.md.

## Validação executada

14 testes novos passaram em 6,83s: quatro divisões válidas, impossibilidade de massa arbitrária/fracionária, cunhagem idempotente, emissão, pagamento misto, troca, destruição simulada, concorrência de gasto, SQL de edição de histórico rejeitado, rollback de cunhagem, autorização/ownership, request estrita, dry-run sem alteração, congelamento de pesos e detecção de corrupção. Regressão anterior com migração preenchida/Web: 16 passaram em 13,26s (conjuntos sobrepostos, não somar). Alembic check sem divergências. Cópia real histórica: 1.155 hashes de campos originais preservados ao migrar ao novo head. **Suite completa executada: 188 testes aprovados, dois avisos de depreciação, 325,51s** (174 anteriores + 14 lunares). Nenhum teste pulado. Cópia adicional do banco real 0.8: 39 tabelas antigas (excluindo alembic_version), 1.554 hashes de linha preservados após upgrade; backup privado em /tmp, não versionado. Dry-run sobre essa cópia: 31 contas, lastro necessário 100.450.000mg (100,45kg), obrigações de dívida separadas 450.000mg, reconciliação antiga zero. Contadores lunares permaneceram zero: a leitura não converteu nem cunhou nada.

Simulador `scripts/simulate_lunar.py`: 15 cenários determinísticos isolados (10/100/1.000 jogadores × raridade/excesso/entesouramento/rituais/escassez de Tesouro), todos com diferença de massa zero. Em cada cenário 10kg iniciais são descoberta fictícia explícita; NPC começa sem dinheiro e com 50 produtos finitos de teste. Relatório SIMULATION.json discrimina descoberto/cunhado/destruído e recusas por falta de caixa por cenário. Não são probabilidades, estoques ou custos finais do jogo; não mede inflação/equilíbrio ou todas as mecânicas ainda não conectadas.

## Planejamento histórico e status atualizado

1. Cutover operacional, gênese e taxa médica: implementados e validados em cópia privada; ver CUTOVER.md. Ativação real ainda não executada.
2. Writers, Guilda/NPC, leilões, contratos e recuperação físicos: implementados na etapa de cutover, sem segunda economia.
3. Recursos procedurais persistentes, anti-reroll, coleta e venda de pepitas: implementação desta continuação, com validação em PROCEDURAL_RESOURCES.md. Não gera moeda na coleta.
4. Boss global e Echo: futuros, não implementados nesta etapa.
5. Cooperação avançada, cadeia produtiva NPC, automação monetária e evolução Godot: futuros. Discord permanece read-only; Godot congelado.

Histórico da etapa inicial de fundação: nenhum build novo ou publicação executada naquela etapa; a consolidação/publicação posterior é registrada em ../CONSOLIDATION_0.9.md. Não há link de download novo. Na etapa inicial não houve telas lunares; a consolidação 0.9 adiciona painel Web e consultas Discord. Godot permanece sem telas Lunares, agora congelado. Execução externa Discord e exportações nativas continuam fora da evidência atual. O simulador isolado não significa entrega antecipada da Fase K operacional.
