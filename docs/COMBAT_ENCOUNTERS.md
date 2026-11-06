# Encontros do primeiro andar — 0.8

Grupos são opt-in, padrão dois inimigos (ENCOUNTER_MAX_ENEMIES 2–3). Nada aumenta automaticamente os grupos das aventuras existentes. Primeiro alvo exige proximidade de uma casa; outros devem ter caminho de até ENCOUNTER_RADIUS (padrão 8) casas do primeiro. Somente COMMON/COMBAT/PROCEDURAL do primeiro andar; chefes/segredos e treino conservam as regras individuais.

CombatEncounter controla identidade, participantes, alvo, rodada, estado ACTIVE/WON/LOST/FLED e última rodada. Cada inimigo continua com EnemyInstance e Battle próprios: índice de vitória única e funções de XP/loot/recompensa existentes são reutilizados. Não há economia paralela.

Ordem por rodada: personagem age; inimigos ainda vivos respondem por ID crescente. Morto não responde. Defesa protege contra as respostas da rodada. O backend processa todas essas respostas atomicamente e devolve a ordem/resultados. Repetição ou corrida com mesmo turno resulta em uma aplicação e uma rejeição; lock do personagem serializa transições. Trocar alvo não gasta rodada, mas exige versão de turno e membro vivo.

Matar um alvo concede somente sua recompensa uma vez; o grupo termina após todos morrerem. Morte fecha os participantes e reutiliza DeathEvent/expedição/resgate existentes. Fuga não tem rota gratuita de grupo: em aventura continua pela prévia/confirmação com penalidades. Sair de sala/gerar outro encontro é bloqueado durante grupo. Reconectar carrega os mesmos participantes, HP, alvo e turno.

Rotas novas: POST /encounters, GET /encounters/{id}, POST /encounters/{id}/target e .../action. Snapshot acrescenta encounter/encounter_rules; campos antigos continuam. Battle.turn no snapshot legado projeta a rodada do encontro quando aplicável; a rota antiga de ação também encaminha ao controlador de grupo, sem contornar respostas/versão. Godot não foi modificado; cria combates individuais normalmente e a projeção mantém proteção se o personagem alternar clientes durante grupo. A nova seleção visual de múltiplos alvos é prioridade da Web.

Persistência: resumo mínimo de encontro e última rodada, sem log permanente de cada turno. A política 0.7 continua removendo instâncias/combates comuns procedurais ao terminar/pagar, preservando recibos e pendências financeiras. Não há cooperação/raids/classes/habilidades novas.
