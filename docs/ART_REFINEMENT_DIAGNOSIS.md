# Refinamento artístico — diagnóstico e decisões

Base limpa verificada após fetch: `feature/pixel-art-visual-overhaul-0.9`,cadbe5b. Única feature remota contendo esse HEAD. Nova branch `feature/pixel-art-cohesion-refinement-0.9`. Main/base preservadas.

O documento do usuário foi lido integralmente. As referências anteriores têm prioridade sobre a arte desta base. Problemas confirmados no código/capturas: atores estreitos com desenho programático simples; terreno de textura muito frequente; mistura de escala/grão entre atores e construções; poços/props repetidos; exceções que ignoram a máscara de posição (pedras desenhadas para todo wall interior, detalhes flat e móveis); paredes decorativas antigas interrompem vias da cidade, mesmo quando a decoração visual é escondida.

Direção: personagens chibi maiores com cabeça proporcional e vestuário legível, novas fontes originais, terreno de baixa frequência com áreas de respiro, decoração agrupada em zonas próprias, safe clara/quente, combate teal mais escuro, secret/boss índigo ritualístico. Reutilizar renderer/temas/PNG pipeline já funcionais. Nenhuma economia/bot/nativo novo.

Posicionamento precisa validar tanto conteúdo legado quanto novo: zonas explícitas PATH/BUILDING_FOOTPRINT/BUILDING_INTERIOR/DOOR_ACCESS/INTERACTION_ZONE/NPC_ZONE/SPAWN_ZONE/COMBAT_ZONE/SAFE_ZONE/DECORATION_ALLOWED; footprint visual completo e não só célula de origem. Objetos importantes fixos (recepção/barraca) têm zonas semânticas próprias, não exceções genéricas para decoração arbitrária.

Se for necessário retirar obstáculos decorativos legados de vias, fazer reparo espacial incremental e auditável, preservando paredes estruturais, entradas, personagens, inimigos, recursos e todo estado econômico. Nunca esconder uma colisão. Salas procedurais em atividade não devem ter geometria refeita. A necessidade/escopo exatos de migração serão registrados após validar fixtures; não alterar migrations históricas.

Validação: cenas reais com antes/depois, desktop390/1280/1920, auditoria de colocação para todos tipos reais e seeds, navegação/serviços/reconexão/combate, frontend e backend, upgrade preservando dados se houver reparo. Arte final passa por inspeção das imagens reais, não apenas hash/testes.
