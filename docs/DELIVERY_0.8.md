# Dungeon Game 0.8 — entrega para revisão

## A. Resumo

Evolução incremental sobre `370b14f` da 0.7, na branch `feature/web-discord-first-floor-0.8`. Backend permanece autoritativo, Web passa a cliente principal e Discord usa o mesmo personagem persistente. Godot não foi alterado nem reexportado. Nenhum merge/force push/reset de dados ou alteração da main.

Diagnóstico foi registrado antes de programar em [DIAGNOSIS_0.8.md](DIAGNOSIS_0.8.md), após leitura dos documentos exigidos, comparação das três branches e inspeção de modelos, Alembic, endpoints, serviços, Web, bot e testes. Baseline executada: 142 testes aprovados.

## B. Correções

- Máximo procedural antes inalcançável com `floor((max-min)*u)`: manter bins antigos abaixo da cauda `u >= 0.995`, reservando essa cauda ao máximo. Distância/perigo/RNG/seed preservados; faixa unitária segura e instâncias existentes intocadas. Comparação de 60 mil amostras por configuração: taxa máxima 0% → 0,55% longe, 1,42% intermediária, 2,10% próxima. Ver artefatos de distribuição e [BALANCE_REPORT_0.8.md](BALANCE_REPORT_0.8.md).
- Web substitui quatro consultas periódicas por snapshot único, descarta respostas antigas, limita reconexão, trata timeout/401/429 e permite atualização manual. Logout/revogação realmente invalidam sessões no servidor.
- Recibos por inimigo e turno esperado evitam XP/loot/moedas duplicados; morte e fuga fecham grupo pela regra existente, sem rota gratuita.
- Cancelar publicação não destrói recompensa já adquirida nem materiais entregues: mantém reserva dos direitos prontos e devolve só orçamento livre.
- Vite 6.4.1 apresentava avisos altos de segurança no servidor dev. Patch exato 6.4.5/lockfile: audit final zero, build passou, bundles coincidem com os validados.
- Testes históricos de migração receberam cwd explícito; presença testa atualização eventual após mensagens legítimas enfileiradas, preservando a verificação de escopo.

## C. Funcionalidades e estado real

| Sistema | Estado/evidência |
|---|---|
| Web principal, navegação, personagem/inventário/atributos, Guilda/leilões/recuperação, expedição/histórico/reconexão | Implementado; fluxo Chromium e regressões API |
| Grupo pequeno opt-in, alvo, turno, persistência, vitória individual e recompensa única | Implementado; PostgreSQL concorrente e Chromium; padrão dois, máximo configurável três |
| Coleta pessoal finita por região/geração, stacks/capacidade/estoque, recibo/auditoria | Implementado; API concorrente e UI mobile |
| Contratos matar/coletar/entregar, reserva real, entrega atômica, cancelamento e pagamento único | Implementado; testes API/ADM e publicação→aceitação→coleta→pagamento no navegador |
| Métricas de combate, progressão, morte/dívida/recuperação, expedição e coleta/contratos | Implementado desde instrumentação; durações históricas desconhecidas, sem backfill inventado |
| Ferramentas de simulação/distribuição e relatório | Executadas: 54 mil encontros simulados e comparação procedural; não são sessões humanas |
| Visual original/feedback/seleção/região/portas/NPC; áudio sintetizado opcional | Implementado; áudio inicia mudo, funciona sem AudioContext; refinamento artístico contínuo |
| Discord: 14 comandos, consultas privadas e equipamento confirmado | Implementado/testado localmente com API e mocks; conexão/sync externos não validados sem credenciais |
| ADM de encontros/coleta/contratos/métricas, permissões/prévia/confirmação/auditoria | Implementado; API e Chromium, papéis temporários revogados |
| Limites persistentes, revogação, índices, logs estruturados | Implementado/testado; controles de borda/TLS continuam obrigação de implantação |
| Godot | Diretório byte a byte igual ao da base 0.7; UI das novidades Web não foi portada, sem novos testes nativos |

Não antecipados: novos andares, raids cooperativas completas, classes, maestria/habilidades avançadas, mercado geral, profissões completas, Banco Central autônomo ou endgame. Lances/distribuição de atributos/resgate de contratos pelo Discord foram adiados: primeiro consolidar consultas e confirmação inicial.

## D. Banco de dados e preservação

Cinco migrações aditivas sobre `d0fc148417a5`:

| Revisão | Alteração |
|---|---|
| `76be3b21ba40` | Encontros persistentes e FK nullable em Battle |
| `4f7ba7966ca8` | Agregados diários, dano e timestamps nullable |
| `e70ea918061f` | Nós pessoais, publicações financiadas e aceitações |
| `947647462008` | Confirmações/recibos Discord com identidade e expiração |
| `4cee57744ea1` | Contadores de limite e índices de consultas frequentes |

Cópia descartável restaurada de dump real 0.7: **1.155 hashes de linhas usando todas as colunas originais permaneceram iguais**, após cada etapa e ao head final. Dump privado não foi publicado. Teste automatizado adicional cria schema 0.7 com contas, sessões, nível/XP/pontos/dívida, espada equipada, inventário/custódia, lances/reservas, expedição/combate ativos, recuperação, papéis e auditoria; compara todas as colunas antigas após upgrade. Testes antigos desde v1 também foram preservados.

Reinício operacional de backend/frontend: **1.553 linhas em 40 tabelas idênticas por hash canônico**, incluindo novos sistemas. Alembic check: nenhuma operação pendente. Banco/volumes não foram apagados. Testes só fizeram TRUNCATE em `tower08_test`; fixtures de migração criam/removem somente seus próprios bancos temporários. Nenhuma penalidade retroativa ou recalculação de inimigos antigos.

Reservas de contratos integram oferta oficial; Tesouro e pool transferem o mesmo valor pelo ledger. Reconciliação após fluxo real de contrato e testes administrativos: **gap 0**. Sandbox não compra itens nem paga contratos oficiais. Downgrade destrutivo 0.8 bloqueado: recuperar com backup verificado.

## E. Testes e comandos

**Resultado final: 174 testes aprovados, dois avisos de depreciação, 326,64s.** São 142 testes da baseline mais 32 novos. Primeira execução registrou 169 aprovados/cinco falhas de ambiente/observação; após as correções descritas, a suite inteira foi repetida e passou, sem testes pulados ou desabilitados.

```sh
# Na pasta backend; DATABASE_URL aponta EXCLUSIVAMENTE ao banco descartável.
TOWER_TEST_DATABASE=1 ../.venv/bin/python -m pytest tests -q
../.venv/bin/alembic upgrade head
../.venv/bin/alembic check

# Na pasta frontend, stack local saudável.
npm run build
npm audit --json
CHROMIUM_PATH=/usr/bin/chromium node tests/smoke.cjs
CHROMIUM_PATH=/usr/bin/chromium node tests/session.cjs
CHROMIUM_PATH=/usr/bin/chromium node tests/encounters.cjs
CHROMIUM_PATH=/usr/bin/chromium node tests/collection.cjs
CHROMIUM_PATH=/usr/bin/chromium node tests/contracts.cjs
CHROMIUM_PATH=/usr/bin/chromium node tests/admin.cjs
CHROMIUM_PATH=/usr/bin/chromium node tests/events.cjs
```

Execuções por etapa: 34 testes procedural/regressões; 13 Web/legados; 40 grupos/expedições; 49 métricas/morte/grupos; 14 coleta/contratos/grupos/métricas; quatro Discord; cinco segurança. Esses conjuntos **se sobrepõem**, não devem ser somados como testes únicos.

Sete scripts Chromium passaram: login/personagem, teclado/clique, combate/loot, expedição/fuga/morte/dívida/recuperação, lances de outro jogador, seleção de alvo/round/reload, coleta/estoque, contratos mobile, reconexão/sessão, ADM/permissões/prévia/confirmação/replay/auditoria e eventos. Tela 390px e áudio sem AudioContext incluídos. Depois do patch Vite, build manteve hashes dos mesmos bundles testados; não é declaração de testes em aparelhos físicos.

Imagens backend, frontend e Discord compilaram com CA/proxy e TLS verificados. `pip check`: dependências consistentes. `npm audit`: zero avisos no fechamento; não equivale a auditoria CVE Python ou certificação antimalware. Avisos conhecidos de depreciação TestClient/anyio e audioop (Discord) permanecem. O workflow novo de CI foi preparado; execução remota não foi presumida a partir dos testes locais.

## F. Desempenho e balanceamento

50 amostras úteis por endpoint/configuração, TestClient com PostgreSQL real, usuário sequencial na cidade. `/state` com limites: p50 **24,14ms**, p95 **26,58ms**, 38 consultas (sem limites: 20,63/24,17ms, 36). Métricas/recursos/contratos: p95 6,98/6,53/7,06ms. Não é carga concorrente pública nem medição de rede real.

Gargalos: snapshot faz muitas consultas; Phaser/Map aproximadamente 1,49MB minificado, carregado após login (jogo 45,54kB + compartilhado 186,05kB antes do mapa). Índices adicionados, sem Redis obrigatório. Presença continua em memória local com um worker; broker/coordenação de jobs precedem múltiplos workers. Índices convencionais podem bloquear escrituras durante migração em bases grandes: agendar janela após medir cópia.

Simulação mostrou grupos de dois difíceis para iniciantes, inclusive com equipamento básico. Mantidos opcionais com aviso, sem nerf arbitrário das regras individuais. Relatórios e limitações em BALANCE_REPORT_0.8.md.

## G. Git, PR e distribuição

Main continua `eab42d7e732befb04244e29d5e1615e821c5ea5e`. Branch 0.8 publicada por Git, sem force push/merge. Commits pequenos por etapa: diagnóstico `29103f4`; fórmula `589747b`; Web `b93d8c6`; grupos `7033d96`; métricas/visual `75cf99b`; coleta/contratos `e10ea85`; Discord `7703556`; segurança/desempenho `1a9680a`; migrações/presença `30c1214`; Vite `9c880ec`; acessibilidade/fluxo contratos `b3a3a51`; pacote Web `3863c2c`. Documentação final em commit separado.

PR **preparado, não criado**: título/descrição em [PULL_REQUEST_0.8.md](PULL_REQUEST_0.8.md). `gh pr create` recebeu `Post https://api.github.com/graphql: Forbidden`; requisição de diagnóstico à API também foi bloqueada pelo proxy (CONNECT 403). Push Git funciona; a restrição é específica da API. [Abrir comparação/revisão 0.7 → 0.8](https://github.com/Lucassilvatech/Dungeon-game/compare/feature%2Fprocedural-economy-godot-fixes...feature%2Fweb-discord-first-floor-0.8?expand=1). Não inventado número de PR; main permanece intacta.

Pacote estático Web de desenvolvimento: `builds/development/0.8.0-web-b3a3a51/DungeonGame-Web-0.8.zip`, oito arquivos compilados, manifesto de hashes e instruções. ZIP/CRC e todos os hashes conferidos; SHA256 `fa65bbd970f25b0551ab6a5a3f1ccf260b2c90a211c72a4774d5d19ceac947a7`. Requer backend 0.8/proxy HTTP, não é EXE/APK nem aplicativo offline. Integridade não significa certificação antimalware; o alerta histórico Windows tem investigação própria preservada.

## H. Próximos passos fundamentados (0.9)

1. Sessões reais com jogadores, especialmente sem equipamento/com dívida, para decidir ajustes dos grupos e recuperação com evidência humana.
2. Validar aplicação Discord real com credenciais seguras e só então ampliar operações confirmadas/localizadas.
3. Perfilar snapshot em volume representativo e agrupar leituras; medir contenção do mutex financeiro antes de mudar locks.
4. Broker de presença, coordenação de jobs, teste de carga e controles TLS/borda antes de escala horizontal/publicação.
5. Melhorar acessibilidade/aparelhos reais e arte com feedback de uso; ampliar recursos/contratos conforme economia observada.

Configuração cloud: `start_skill` atualizado e salvo com regras 0.8, comandos de retomada e proteção de dados. `install_script` anterior preservado por já instalar as mesmas dependências/serviços. Salvar rascunho não publica o ambiente: revisão/salvamento/publicação em configurações permanece ação do produto; restauração em tarefa nova não foi declarada validada.
