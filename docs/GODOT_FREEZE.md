# Godot native clients are frozen

Fase de consolidação 0.9, registrada em 27/10/2026 (America/Sao_Paulo).

Web is the active gameplay client. Godot will resume later using the same authoritative backend. Congelado não significa abandonado: reduzimos manutenção paralela de clientes e distribuição nativa enquanto economia/backend/Web são consolidados.

- Windows: FROZEN.
- Android: FROZEN.
- APK: NOT REQUIRED.
- Windows build: NOT REQUIRED.
- Godot source: PRESERVED.

Referência de código preservada: HEAD local inicial `7ef6a1a`, branch feature/web-discord-first-floor-0.8. O diretório godot-client é idêntico à base 0.7 `370b14f`. Último estado funcional documentado em DELIVERY_0.7/GODOT_MIGRATION: fluxo Godot Linux/headless; Windows nativo/gráfico e aparelho Android possuem limites históricos de validação. Esta consolidação não revalida essas plataformas nem resolve o alerta histórico de Defender.

Preservados scripts, cenas, project.godot, presets, testes, builds anteriores e documentação histórica. Nenhuma exportação, APK, EXE, instalador ou pacote nativo foi gerado. Workflows godot-clients/windows-0.7-check/windows-build-scan ficam somente workflow_dispatch; não há acionamento automático por push/PR nem obrigatoriedade de CI neste ciclo.

Manter contratos HTTP normais: autenticação, personagem/state, movimento, batalha individual/action, inventário/equipamento, atributos, expedição/fuga, Guilda/recompensas, recuperação, leilões, destinos descobertos. Desativação restrita às rotas Discord de mutação, que Godot não utiliza.

Recursos Web ainda ausentes na UI Godot: seleção completa de grupos, coleta/contratos 0.8, painel/carteira física e divisão Lunar, futura transição financeira e futuros rituais/ecos. Nada desta lista deve ser portado durante o freeze.

Retomada: decisão explícita de roadmap; backend/contratos estabilizados, migração Lunar validada e gameplay Web testado; então portar por etapas e executar testes próprios em plataformas reais. Distribuição nativa futura requer processo de integridade/segurança próprio, sem desativar antivírus.
