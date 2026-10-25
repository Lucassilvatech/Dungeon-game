# Plano incremental Godot e administração

Base: main eab42d7, 99 testes PostgreSQL aprovados antes das mudanças. Trabalho exclusivo em feature/godot-admin-migration, sem merge automático. React/Phaser permanece.

1. Migração aditiva e proteção da definição estável sword; suspender sua negociação, diagnosticar leilões por ID e oferecer recuperação individual confirmada/auditada. Nunca retirar item de comprador legítimo automaticamente.
2. Viagem rápida autoritativa somente a destinos permanentes visitados do primeiro andar, preservando combate/expedições e conexões. Sala de leilões na Guilda e detalhes/histórico reais.
3. Cliente Godot 4: serviço HTTP/sessão, mapa e controles mouse/teclado/toque, menus e fluxos existentes, reconexão e export presets Windows/Android. Validar jogo, não só importação.
4. Central web em entrada separada, sessões administrativas independentes, papéis/permissões, limitação de login, prévia e confirmação idempotente, auditoria. Módulos funcionais sobre as entidades reais.
5. Banco Central inicialmente sem reservas novas; transferências conservativas, emissão/retirada explícitas, métricas com dívida e escrow, sandbox administrativo sem caminhos à economia oficial.
6. Testes de permissões, concorrência, recuperação, viagem, economia e regressão; builds, navegador, Godot real e documentação de limitações por plataforma; commits separados e PR para revisão.

Dados: preservar volume/.env, fazer backup antes de upgrade real e validar schema populado em PostgreSQL descartável. Sem down -v, andares superiores, habilidades futuras ou mercado geral.

## Resultado de execução

Escopo de software implementado em branch separada, com baseline 99 e regressão final 114 aprovadas. Godot validado jogando por API (44 verificações), Central web e legado validados por Chromium. EXE/APK de desenvolvimento gerados; execução nativa Windows/Android e CI remoto não validados. Recuperação individual do item diagnosticado executada com o ID original e auditoria, sem alterações monetárias. A main continua eab42d7 até revisão; nenhuma integração automática.
