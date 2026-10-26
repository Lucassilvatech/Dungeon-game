# Entrega 0.7 — mecânicas, economia, acesso e distribuição

Branch publicada: `feature/procedural-economy-godot-fixes`. Base da evolução: `b685bd3`, na branch Godot/ADM anterior. Main conferida em `eab42d7e732befb04244e29d5e1615e821c5ea5e`; nenhum commit direto/merge/force push nela.

## Download e instalação

- [Windows x64 — ZIP completo](https://raw.githubusercontent.com/Lucassilvatech/Dungeon-game/b17d07bc16fc14a0767c99f66cc6a139f0235739/builds/development/0.7.0-bd480e0/DungeonGame-Windows-x64.zip): extraia e execute DungeonGame.exe, com PCK embutido. 33.536.490 bytes; SHA256 `19a069950896650e1c165f95129f74088f0e4fb7fe8c91feef34479e6a416e02`.
- [Android — APK instalável de desenvolvimento](https://raw.githubusercontent.com/Lucassilvatech/Dungeon-game/b17d07bc16fc14a0767c99f66cc6a139f0235739/builds/development/0.7.0-bd480e0/DungeonGame-Android.apk): Android API 24+, ARMv7/ARM64/x86_64, assinatura debug v2/v3. 84.547.008 bytes; SHA256 `72a8fa5bbaecde3b10a2ed966921abeeb082ad6f064669d9798912bab3f65bc1`.

Ambos foram publicados e baixados integralmente via HTTPS, com HTTP 200, tamanho e hash verificados. Instruções também dentro do ZIP. São builds de desenvolvimento, sem substituir release estável. Arquivos binários publicados na branch; exportação por GitHub Actions também passou. O EXE não possui Authenticode. Se houver detecção local, mantenha a quarentena; hashes/CI não comprovam ausência de malware.

O backend não está embutido: faça checkout da branch, copie `.env.example` para `.env` **apenas se não existir**, configure a senha e execute `docker compose up --build -d`. No cliente Windows do mesmo PC use `http://127.0.0.1:8080/api`. No emulador Android use `http://10.0.2.2:8080/api`. Em aparelho físico, habilite `FRONTEND_BIND=0.0.0.0` no servidor de desenvolvimento, recrie o frontend e use `http://IP-DO-PC:8080/api`, com firewall restrito à LAN. Para internet, HTTPS com certificado válido e proteção administrativa. Não há servidor público permanente configurado nesta nuvem. Não apague `.env`/volumes nem use `down -v`.

## Implementado/corrigido

1. Atributos efetivos compartilhados por API/status/combate; equipar, trocar e desequipar sem alterar bases ou duplicar bônus. Exibição de cada parcela, poder real dos itens e compatibilidade com armas antigas.
2. Android com URL explícita, sessão preservada, erro específico de rede/DNS/timeout/TLS/cadastro/credenciais/sessão e tentativas HTTP limitadas com ação explícita de tentar novamente.
3. Sequência persistente, chance inicial 1%/teto 10%, sorteio backend único por aventura, conclusão uma vez e reset por morte/fuga/abandono; reconexão preserva. Guardião procedural não altera as condições dos bosses antigos.
4. Gerador universal por configurações de espécie/andar, BFS das conexões válidas, fórmulas propostas, limites/seed/minibosses/raros e identificação por cor + rótulo. Simulações reproduzíveis: 60 mil inimigos e 120 mil combates isolados; somente primeiro andar. A propriedade de Lmax exclusivo na fórmula solicitada está documentada, sem mudança silenciosa do princípio.
5. Estado de inimigos/turnos comuns da nova geração é transitório, persistido somente durante a aventura/pendência e podado ao terminar/pagar. Controles de bosses, recibos, direitos financeiros, inventário e auditoria permanecem; histórico legado preservado.
6. Morte sorteia 0–5 unidades sem reposição, com proteção da espada/itens estruturais. Comuns destruídos; valiosos em recuperação pessoal a 200% do valor-base. NPC próprio, acesso por proprietário, transação atômica, pagamento e entrega única.
7. Dívida ≥1000: confisco separado, seleção mínima determinística de unidades com redução heurística de excedente, avaliação financiada pelo Tesouro, amortização/excedente e marco persistente de +1000 de dívida nova. Venda posterior não cobra a dívida novamente. Sem limite cinco para confisco.
8. ADM oculta/suspende/reembolsa e arquiva anúncios sem apagar histórico. Eventos têm formulário explicativo, prévia, região/andar, início/fim/duração, efeito/intensidade/condições, agenda/histórico/cancelamento, permissões e auditoria.
9. Exportações reproduzíveis, pacotes completos, manifestos/hashes e verificações remotas Windows/Defender.

Migração aditiva: **d0fc148417a5**, sobre b3057d8109ee. Downgrade destrutivo recusado. Backup operacional fora do repositório; **274 registros existentes com todos os campos originais preservados** após upgrade/seed. Reinício real manteve todos os registros acompanhados exatamente iguais, inclusive novas tabelas. Reconciliação final 0, Banco Central 0, nenhum papel administrativo temporário ativo.

## Testes executados e resultado

| Verificação | Resultado |
|---|---|
| Baseline PostgreSQL anterior | 114 aprovados |
| Suite PostgreSQL final, banco descartável | **142 aprovados**, sem falhas/skips, 239,07 s |
| Godot controlador real contra API isolada | **42 verificações aprovadas** |
| Godot URL/erros/rede recusada | Aprovado |
| TypeScript/Vite e imagens Docker | Aprovados |
| Cliente web legado no Chromium | Aprovado, incluindo morte nova e duas contas |
| Central ADM no Chromium | Aprovado, finanças pareadas/replay/permissões/mobile/revogação |
| Formulário de eventos no Chromium | Aprovado, criação/prévia/confirmação/cancelamento futuro |
| Alembic check | Sem divergências |
| Preservação e reinício operacional | Aprovados |
| Exportação Windows/Android local + assinatura APK | Aprovadas |
| [Exportação GitHub Actions](https://github.com/Lucassilvatech/Dungeon-game/actions/runs/40258147700) | **Success** |
| [Defender atualizado + nuvem + inicialização Windows/headless](https://github.com/Lucassilvatech/Dungeon-game/actions/runs/40258420595) | **Success**, nenhuma detecção nessa varredura |
| Downloads públicos completos | HTTP 200 e SHA256 corretos |

As execuções intermediárias que falharam não são apresentadas como aprovação. Suite final usa as expectativas novas; fixtures explícitas de anúncios históricos conservam testes de reservas, concorrência, entrega e contabilidade anteriores. Alertas de depreciação TestClient/Node actions e bundle Phaser grande continuam.

## Limitações e pendências

Não foram executados login/jogo gráfico em Windows nem instalação/cadastro/login/jogo num aparelho/emulador Android. A inicialização nativa Windows foi headless; o fluxo jogável/cadastro/sessão foi executado no Godot Linux com o mesmo controlador/backend. GPU/toque/rede do dispositivo ainda precisam de homologação. Não há certificado Authenticode nem backend público permanente fornecido. A conectividade Android exige configurar o servidor real. Não houve revisão final da Microsoft que confirme falso positivo do ZIP antigo. A varredura CI aprovada do ZIP novo não invalida alertas locais.

Não foram expandidos andares superiores, habilidades futuras ou raids. A seleção de excedente de confisco é uma heurística documentada; não promete ótimo global de subset-sum para inventários ilimitados. Sala procedural atual usa a proximidade do nó inteiro, sem distância artificial por pixels.

## Commits e revisão

Commits de implementação/testes desta evolução:

- `7c94ed5`: atributos efetivos e diagnóstico de autenticação.
- `b58360a`: schema aditivo.
- `183757f`: geração universal, sequência e retenção.
- `689d7f0`: morte, recuperação pessoal e confisco.
- `853ea1a`: leilões/eventos ADM e interfaces.
- `bd480e0`: ajustes, acesso e exportação reproduzível; fonte dos clientes publicados.
- `b17d07b`: publicação dos dois builds/hashes/CI Windows.
- `cfe5e87`: SDK Android do runner e diagnóstico CI.
- `9feac66`: rótulos acessíveis e evidências/retentativas da nuvem Defender.
- `ababe50`: regressões PostgreSQL/navegador/Godot.

[Histórico completo da branch](https://github.com/Lucassilvatech/Dungeon-game/commits/feature/procedural-economy-godot-fixes). [Comparar apenas esta evolução](https://github.com/Lucassilvatech/Dungeon-game/compare/feature/godot-admin-migration...feature/procedural-economy-godot-fixes). A base Godot/ADM anterior ainda não foi integrada à main: revise essa dependência também antes de integrar. O PR pode ser preparado em [nova revisão](https://github.com/Lucassilvatech/Dungeon-game/pull/new/feature/procedural-economy-godot-fixes). Nenhum merge automático foi realizado.

Detalhes técnicos/reprodução: [PROCEDURAL_ECONOMY_UPDATE.md](PROCEDURAL_ECONOMY_UPDATE.md), [desenvolvimento](DEVELOPMENT.md), [evidência dos downloads](security/downloads-0.7-verification.json), [evidência Windows](security/windows-0.7-verification.json).
