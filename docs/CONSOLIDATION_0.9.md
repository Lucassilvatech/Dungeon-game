# Consolidação 0.9 — registro inicial

Antes de modificar: `git status` limpo, branch `feature/web-discord-first-floor-0.8`, HEAD `7ef6a1a`. Histórico de 20 commits e origin inspecionados; origin HTTPS `Lucassilvatech/Dungeon-game`. Main remoto `eab42d7e732befb04244e29d5e1615e821c5ea5e`; 0.8 remota `af9dcb549d60825620db3ef953cb4f1241baaeb6`.

Nova branch `feature/lunar-web-discord-readonly-0.9` criada do HEAD local, sem reset/checkout de main. Preservados cinco commits locais `aa3042c`, `35502f6`, `947c8ec`, `f32d317`, `7ef6a1a`. Encontrados lunar.py, cinco modelos Lunar, revisão 4a8687e5317c, APIs privadas/ADM, dry-run legacy_preview, simulador, testes e docs/lunar. Sem alterações não commitadas na entrada.

Diagnóstico Discord: além do comando /equipar, consultas usavam game.snapshot/game.character (resume/sync/geração) e auctions.listing (liquidação). Esses caminhos precisam ser substituídos, não apenas escondidos no bot. Nova projeção deve executar transação PostgreSQL READ ONLY, com identidade vinculada e sem ler personagens de terceiros. Metadados de limite de requisições continuam sendo gravados separadamente, sem constituir gameplay.

Economia Lunar é fundação incompleta; esta consolidação não ativa conversão nem implementa bosses/rituais futuros. Preserve saldos e documentação honesta. Godot deve ficar byte a byte igual à base local, workflows nativos manuais. Resultados finais serão registrados após execução.

## Alterações consolidadas

- Lunar existente preservado sem reescrita: lunar.py, LunarAsset/Account/Holding/Entry/Supply, 4a8687e5317c, legacy_preview, APIs /lunar e ADM, simulador, testes e docs/lunar. Não há cutover operacional, descoberta procedural Lunar ou ecos concluídos.
- Bot: dezesseis comandos privados, apenas vinculação e observação; /equipar e EquipmentConfirmation removidos. Serviço rejeita POST de gameplay; 410 nas duas rotas legadas, 404 em ações inexistentes, chave de serviço não autoriza rotas Web/ADM. DiscordOperation/recibos/migrações permanecem.
- Projeções Discord não usam game.snapshot/character/pending com locks nem auctions.listing. READ ONLY e snapshot REPEATABLE READ no PostgreSQL; leitura não retoma/gera/completa/liquida. Inventário/recuperação/holds apenas do personagem; mapa somente descobertas próprias. Rate limiting pode registrar metadados, não gameplay.
- Web: painel Lunar com moeda por denominação, peso monetário separado do minério, pepitas, status de conversão inativa e divisão via API estrita. Sem estoque não oferece divisão. Mantidos demais menus e React/Phaser.
- Godot: diretório idêntico a 7ef6a1a; scripts/cenas/presets/builds antigos preservados. Windows/Android FROZEN, APK/EXE NOT REQUIRED. Três workflows nativos somente manuais. CI Web/backend passa a incluir npm test, simulador e job Chromium HTTP com PostgreSQL separado, sem build nativo.

## Verificações executadas até aqui

17 testes direcionados Discord+vínculo legado passaram em 35,32s; incluem 15 projeções com snapshot de tabelas e leilão vencido sem liquidação, 13 rotas de controle proibidas, recibos preservados, vinculação/revogação, erros privados/ausência de botões e chave de bot sem permissão Web/ADM. Teste adicional de barreira PostgreSQL passou em 3,06s: tentativa de escrita acidental dentro de consulta falha e o snapshot permanece idêntico. Corrigida projeção inicial para preservar os campos character legados; a rodada final direcionada passou.

Frontend: TypeScript/Vite compilou; npm test passou (1 teste de freeze de workflows). Chromium passou smoke de gameplay (cidade/Guilda/treino, mapa, teclado, combate, inventário, expedição/reload/fuga, morte/dívida, recuperação e propriedade de segundo jogador) e painel Lunar móvel 390px (sem overflow, zero físico, separação de massas e bloqueio sem estoque). Teste Lunar teve corrida com reload/HMR inicialmente; inicialização do token passou para antes da navegação e execução final passou. Stack de teste HTTP local API/Vite, banco descartável tower09_web; banco operacional não foi convertido nem resetado. Phaser continua emitindo aviso de bundle grande.

Simulador: 15 cenários isolados, todos massa gap zero; pip check sem dependências quebradas. Suite completa: **200 aprovados, zero falhas, zero pulados, dois avisos, 416,93s**. O teste de barreira PostgreSQL foi adicionado após a coleta dessa execução e passou separadamente: **1 aprovado em 3,06s**, totalizando 201 testes distintos executados com sucesso. Os avisos são depreciações TestClient/anyio e audioop do Discord. CI remoto/Discord externo não foram presumidos a partir de checks locais. Credenciais Discord reais não fornecidas; sincronização externa pendente, mas 410 bloqueia controle mesmo se slash command antigo estiver em cache.

## Segurança e revisão

Somente arquivos do projeto são adicionados; backups/dumps/bancos reais/.env/segredos permanecem fora do Git. Não foram criadas credenciais reais em arquivos. Credenciais e chaves de teste nas suites são fixtures explícitas. Nenhuma alteração de schema destrutiva ou remoção de DiscordOperation. Nenhuma migração nova além da Lunar já existente. Nenhuma exportação nativa. Main não recebe commits/merge/force push.

PR preparado como draft contra a **0.8 remota af9dcb5**, abrangendo tanto os cinco commits Lunares preservados quanto a política 0.9. Push autorizado executado e validado; detalhes abaixo. Relatório do escopo Lunar continua distinguindo as fundações de sistemas futuros.


## Publicação e validação remota

Branch anterior feature/web-discord-first-floor-0.8, HEAD inicial local **7ef6a1a23881fb664a73af1585013dc1e2323ec2**. Nova branch **feature/lunar-web-discord-readonly-0.9**, criada sem perder os cinco commits locais. Commits desta consolidação: d098d8d (Discord), 49898d2 (Web/CI), 686e42c (massa monetária/pepitas), df232ec (documentação). Este registro de verificação é um commit posterior, sem alterar o código testado.

`git push -u origin feature/lunar-web-discord-readonly-0.9` concluiu. HEAD remoto do primeiro push: **df232ec8f0da3c03f3988ca47fb7d6698a8aab32**, igual ao local naquele momento. Conteúdo baixado pelo raw.githubusercontent.com conferido por SHA256 contra o workspace para lunar.py, migração 4a8687e5317c, discord_client.py, bot.py, GODOT_FREEZE.md e este relatório. Fundação Lunar inteira publicada por ancestralidade dos commits preservados; não houve cherry-pick parcial ou reconstrução da main.

Main remoto antes/depois: **eab42d7e732befb04244e29d5e1615e821c5ea5e**, inalterado. 0.8 remoto antes/depois: **af9dcb549d60825620db3ef953cb4f1241baaeb6**, inalterado. Nenhum merge, force push, reset/clean, banco real ou segredo publicado. Worktree revisado e arquivos do Godot byte a byte iguais à referência local. Sem novo APK, EXE, ZIP Windows ou pacote nativo.

Draft PR tentado com `gh pr create --draft --base feature/web-discord-first-floor-0.8 --head feature/lunar-web-discord-readonly-0.9 --body-file docs/PULL_REQUEST_0.9.md`. **Não criado**: API retornou `Post https://api.github.com/graphql: Forbidden`. Push Git funciona; acesso à API não foi contornado. Título/descrição preparados no arquivo, sem auto-merge.

- [Branch publicada](https://github.com/Lucassilvatech/Dungeon-game/tree/feature/lunar-web-discord-readonly-0.9)
- [Compare real contra 0.8](https://github.com/Lucassilvatech/Dungeon-game/compare/feature%2Fweb-discord-first-floor-0.8...feature%2Flunar-web-discord-readonly-0.9?expand=1)

Resultado: backend 200/200 na suite completa + 1 teste adicional da barreira read-only; Lunar 14 incluídos na suite; Discord 16 incluídos na suite + barreira adicional; Web build/npm test/Chromium smoke e Lunar mobile passaram. Falhas finais zero, pulados zero. Dois avisos Python de depreciação e aviso de tamanho de bundle Vite. CI remoto não executado/confirmado neste ambiente (workflow preparado); Discord externo sem credenciais, sem alegação de conexão real. Segurança revisada pelo diff/nomes: nenhum .env real, token real, banco, dump privado ou backup entrou no Git. Fixtures de teste não são credenciais operacionais.

**Discord cannot control the character.** Windows: FROZEN. Android: FROZEN. APK: NOT REQUIRED. Windows build: NOT REQUIRED. Godot source: PRESERVED. A economia Lunar continua uma fundação incompleta e publicada, sem ativação do cutover. Esta tarefa termina na consolidação, validação e publicação; não implementa futuros bosses/rituais.
