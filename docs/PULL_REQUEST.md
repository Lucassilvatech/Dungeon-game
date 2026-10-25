O cliente era restrito à web, a espada inicial podia ser perdida em morte procedural e não havia ferramentas administrativas autenticadas para correções e operações monetárias. Esta branch acrescenta o cliente Godot e a Central ADM mantendo o primeiro andar, os clientes existentes e os dados persistidos.

### Mudanças

- Godot 4.6.3 com autenticação/sessão, mapa/câmera/pixel art original, teclado/mouse/toque, combate, inventário/equipamentos/pontos, Guilda, expedições/fuga/morte, leilões/lances, presença e reconexão. Presets e workflow de exportação Windows/Android; Phaser preservado.
- Viagem rápida autoritativa para locais permanentes visitados, respeitando combate/ACTIVE. Sala de leilões com NPC próprio e anúncios/histórico com dados reais.
- Espada inicial protegida por definição estável/constraint. Diagnóstico, recuperação original com reembolso e reposição autorizada sem retirar bem de comprador legítimo. Cancelamentos preservam histórico e custódia.
- Central web independente em /admin, papéis/permissões no FastAPI, sessões ADM independentes, limite de login, prévia/confirmação idempotente e auditoria. Módulos sobre as entidades reais.
- Banco Central zerado na migração, transferência conservativa, emissão/retirada explícitas, métricas/reconciliação com dívida e escrow, fluxos e créditos de teste sem conversão para moeda oficial. Sem emissão automática.

### Dados e migração

Migração aditiva **b3057d8109ee**, após 039105b3ae1a. Não reinicia volume/.env/Tesouro, não concede poderes ou fundos a contas e não restitui inventários indiscriminadamente. Congela estatísticas/XP de inimigos existentes; perfis administrativos afetam novas instâncias. Recuperação individual do caso diagnosticado foi feita pelo fluxo auditado preservando o mesmo item e sem alterar moedas. Backup/compare e reinício operacional foram verificados.

### Validação

- Baseline 99; execução final **114 testes PostgreSQL passaram**, incluindo bancos populados v1/v0.3/v0.4/v0.5, permissões, perdas, lances, concorrência, rollback, recuperação, contabilidade e viagem rápida.
- Godot real Linux/headless: **44 verificações** do controlador e API com duas contas, incluindo lance financiado por combate/pagamento da Guilda.
- Chromium: fluxo legado e Central ADM, todos os módulos, confirmação/replay, emissão/retirada pareadas, reconciliação, responsividade e revogação de papel temporário.
- TypeScript/Vite, imagens Docker, alembic check e persistência após reinício.
- EXE Windows exportado e pacote embutido carregado em Godot Linux. APK exportado com SDK 36 e assinatura v2/v3 verificada. Artefatos de desenvolvimento; sem segredos/chaves de produção versionados.

### Limites para revisão

Execução nativa em Windows, instalação/toque/GPU em aparelho Android e workflow remoto não foram executados nesta nuvem. Não descontinuar Phaser antes dessa validação. Discord externo continua sem validação por falta de credenciais. Avisos conhecidos de depreciação TestClient e bundle Phaser grande permanecem. Uma repetição da suíte foi interrompida por disco cheio, resolvida removendo somente cache/imagens obsoletas; a execução completa posterior passou.

Sem andares superiores, novas habilidades, combate cooperativo implementado, mercado geral, juros ou emissão autônoma. O planejamento conceitual de combate futuro foi preservado no roadmap. **Não realizar merge automático na main.**
