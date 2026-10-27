# Recursos Lunares procedurais 0.9 — diagnóstico e decisões

Base obrigatória confirmada: `bf2ea7a52d090cae7d9260c573bd1e8d24354c6d`; árvore limpa, fetch executado. Nova branch: `feature/lunar-procedural-resources-0.9`. Main preservada.

O cutover está implementado e validado em cópia privada; ativação no ambiente operacional real ainda não executada. Fundação/ledger, facade, escrows, NPCs e fluxos financeiros serão reutilizados.

## Diagnóstico antes da programação

- Expedição persiste seed/room único e pertence a um personagem. Raid é somente formação social, sem exploração ou combate compartilhados. Snapshot elegível desta etapa é SOLO com um participante; membros de raid não ganham acesso à instância privada. Não serão criadas raids cooperativas.
- A geração de sala ocorre em exploration.adventure, com UUID/seed persistidos; snapshots podem materializar inimigos, mas não devem sortear recursos novos. Decisão sem ocorrência também precisa ser persistida.
- Encerramento COMPLETED/FLED/FAILED passa por procedural_retention.prune. Ocorrências e recibos devem sobreviver à limpeza de inimigos transitórios.
- Inventário tradicional limita slots para coleta, sem limite de peso físico. LunarHolding já representa moedas/pepitas separadamente de Item. Reutilizar holdings, sem duplicar pepita em Item. Cada pepita ocupará um slot da capacidade existente; moedas não ocupam slot. Divisão e coleta tradicional também respeitarão slots compartilhados.
- Morte seleciona somente Item elegível, até cinco unidades. Holdings Lunares existentes não entram nessa seleção. Pepitas permanecerão em custódia Lunar após fuga/morte, como na fundação, sem inventar perda ou preço de recuperação novo. A taxa médica continua cobrando somente moedas; não converte minério para cobrar dívida.
- Ledger já aceita source=discovery e mantém discovered_mg. Introduzir massa exclusivamente na coleta com DISCOVERED_MINERAL; spawn é potencial, sem massa econômica. GENESIS_BACKING permanece separado.
- Configuração administrativa já exige permissão, prévia, justificativa, confirmação e auditoria. Novos parâmetros usarão esse fluxo, sem endpoint de spawn arbitrário. Spawn desativado por padrão; valores técnicos restantes PROVISIONAL, não balanceamento final. Preços por tamanho começam zero (compra desativada), sem equivalência comercial implícita com massa.
- Discord usa transação SQL READ ONLY; apenas contagens de holdings e coleta própria serão expostas, sem posições/spawns disponíveis.

Implementação/testes/resultados serão registrados abaixo conforme executados. Boss global, Echo, automação do rei e Godot continuam fora do escopo.
