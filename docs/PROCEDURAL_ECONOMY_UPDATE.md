# Atualização 0.7 em desenvolvimento

Branch: `feature/procedural-economy-godot-fixes`, baseada na entrega 0.6 e sua investigação de distribuição. Main não recebe commits nem merge automático. Todos os cinco documentos solicitados existem e foram inspecionados, assim como migrações, dependências, API, regras e testes.

Ordem: acesso Android/diagnóstico de conexão e atributos; sequência/geração universal; morte/recuperação e dívida; leilões/eventos; regressões, migração e builds. Dados legados permanecem; novas regras não confiscam nem alteram espólios históricos retroativamente.

Atributos são projeções: base + equipamento + temporários. `power` de arma antiga representa bônus de força; não se altera a base. Status e combate consultam a mesma função. Não há modificadores temporários existentes: parcela explicitamente zero.

Android físico exige URL alcançável terminada em `/api`. `localhost` pertence ao aparelho; `10.0.2.2` serve somente ao emulador. Não existe backend público configurado nesta nuvem. Configurar HTTPS com certificado válido, ou endereço LAN para desenvolvimento, antes de autenticar. O app não contém credenciais administrativas.

## Regras implementadas

- Status e combate usam `attributes.effective`; a projeção apresenta base/equipamento/temporário/efetivo. Desequipar e trocar não modificam bases nem duplicam bônus. O inventário retorna o poder real, sem texto fixo +3.
- Sequência persistente: começa em zero, chance `min(0.10, 0.01 + sequência * incremento)`; incremento padrão 0.01. Conclusão incrementa uma vez sob lock do personagem. Morte/fuga/abandono explícito zeram; desconexão não altera nada. Abandonar sequência fora de aventura não aplica penalidade econômica; durante aventura ativa deve-se usar a fuga confirmada.
- Sorteio único do guardião errante ao criar a aventura, armazenado em Expedition (`boss_chance` em pontos-base, `boss_rolled`, `special_boss`). Quando sorteado, ocupa o último spawn em ordem estável no mapa da aventura. Não substitui o boss do andar nem o segredo, não libera andares e não altera suas condições especiais. Aventura histórica não recebe sorteio retroativo.
- Gerador universal: configurações de espécie por andar, limites, regiões e multiplicadores; RNG local por seed/spawn, atributos independentes e pesos configuráveis. Slime e batedor usam faixas conservadoras ancoradas nos valores anteriores; não se adotou automaticamente o exemplo de ataque 3–15. Miniboss: máximo um por aventura, chance `2% + 6% * p` no primeiro andar, apenas espécies/regiões elegíveis. Raro: 5% base; evento pode ampliar até 25%. Boss: vermelho; único/segredo: dourado; raro: azul; miniboss: roxo; todos têm rótulo/ícone além da cor.
- Distância: BFS reversa sobre `RoomConnection` dirigidas do mesmo andar, acessíveis ao personagem. `p=1-d/D`, máximo D entre salas alcançáveis; D=0 → p=1; sala desconectada → None/geração rejeitada. Não usa distância visual. O mapa procedural atual é uma sala conectada à trilha, portanto a proximidade é da sala inteira; não se inventam gradientes entre pixels de uma mesma sala.
- As fórmulas solicitadas foram mantidas literalmente. Com `r<1` e `floor`, Lmax não é alcançado quando Lmin<Lmax. Isso é uma consequência matemática registrada, não uma correção silenciosa. Para incluir o teto na distribuição seria necessário revisar o princípio aprovado. Ver a simulação reproduzível em `docs/procedural-simulation.json` (60 mil amostras).
- Durante aventura ativa, inimigos/turnos/HP/seed persistem no PostgreSQL para sobreviver ao reinício. Em aventuras novas 0.7, instâncias comuns/raras sem prêmio único/minibosses e eventos de turnos são temporários e removidos ao terminar. Combates pendentes ficam somente até pagamento/perda; DeathEvent e combates de bosses, recibos financeiros, inventário e auditoria permanecem. Salas/expedições guardam seed/resumo/idempotência. Histórico legado permanece intacto, sem limpeza retroativa de dados.

## Morte e recuperação

O backend sorteia uniformemente `random_int(0,min(5,total de unidades elegíveis))`, e escolhe unidades sem reposição. Uma unidade de stack conta como um item: uma morte não pode perder 99 materiais tratando uma pilha como uma unidade. Pilha parcial é separada sem alterar o total; equipamento inteiro mantém seu ID. Espada inicial, definições não transferíveis e itens `system/structural/quest` ficam protegidos. Valiosos sem avaliação confiável ficam protegidos até revisão.

Comuns/incomuns selecionados tornam-se destruídos (tombstone de item para referências/auditoria, indisponível para uso). Raros/épicos/lendários/únicos vão para RecoveryItem pessoal, nunca para leilão público. Recuperar exige proximidade do Guardião de Recuperação na sala `recovery_hall`, saldo suficiente, preço congelado `valor-base * quantidade * 2`, transação atômica e UUID. Repetição não entrega/cobra novamente; outra conta não pode ver nem recuperar. A UI informa o acréscimo de 100% e o total de 200%.

Taxa médica, perda de XP/pendências e piso de dívida anteriores permanecem. A coleta de dívida é uma operação distinta, depois da seleção de perdas da morte; não compartilha o limite de cinco.

## Dívida e contabilidade

A primeira tentativa ocorre quando dívida ≥1000. `debt_accrued` conta somente dívida nova realmente financiada por taxas (não a parcela perdoada pelo piso). Após tentativa, `debt_next_collection = debt_accrued + 1000`. Repetir requisição, reconectar, receber item ou manter dívida remanescente não permite nova tentativa. Se uma avaliação de 500 reduz dívida de 1000 para 500, são necessários mais 1000 de dívida nova para nova tentativa, chegando a 1500 sem outros pagamentos.

Seleção determinística de unidades: ordenar valor decrescente/ID crescente, escolher a quantidade mínima que cobre a dívida; se não há cobertura, escolher todos os elegíveis de valor positivo. Melhorar excedente com trocas locais estritamente redutoras que preservam a cardinalidade e a cobertura. É uma heurística documentada de excedente, não uma promessa de resolver subset-sum global em inventários ilimitados. O número de unidades confiscadas não tem teto cinco.

Guilda compra a custódia pela avaliação: débito real do Tesouro e crédito na carteira assinada amortizam a dívida e devolvem o excedente. Se o Tesouro não pode financiar a avaliação, a tentativa fica adiada e auditada, sem criar moeda ou bloquear o resgate por morte. DebtCollection registra dívida anterior/final, avaliação, excedente, itens e marco de recorrência. Auction com origem `guild_debt` guarda a avaliação e não precisa de DeathEvent. A venda posterior registra receita do Tesouro; não credita nem cobra novamente o devedor. Receita diferente da avaliação é resultado da Guilda. Reservas de lances continuam independentes.

## Leilões e eventos ADM

Ocultar um anúncio ativo cancela com reembolso atômico das reservas e mantém custódia; não continua aceitando lances escondidos. Anúncio encerrado pode ser ocultado sem mexer na entrega. Arquivar exige estado terminal. Listagem/detalhes/lances/resolução pública rejeitam ocultos; Central mantém histórico e auditoria. Não há DELETE financeiro.

Formulário de eventos explica nome, descrição, região, andar 1, condição (novas aventuras), efeito, intensidade, início UTC, duração, fim calculado e prévia. +100% dobra a chance de raros, respeitando teto 25%. Sobreposição usa o maior multiplicador; evento não rerrola inimigos ativos nem chance de boss. Estados SCHEDULED/ACTIVE/ENDED/CANCELLED e cancelamento auditado; permissões/prévia/confirmação existentes preservadas. Não é necessário editar JSON.

## Executar servidor e clientes

1. Faça checkout da branch desta atualização. Preserve `.env` e volumes. Se `.env` não existir, copie `.env.example` e ajuste a senha local.
2. `docker compose up --build -d` aplica migração aditiva `d0fc148417a5` e seed idempotente. Web/ADM: porta 8080; docs API: 8000/docs. Só a porta web precisa ficar acessível aos clientes; mantenha banco/API interna protegidos.
3. Windows x64: extraia ZIP completo e execute DungeonGame.exe. O PCK já está embutido. Configure `http://127.0.0.1:8080/api` para servidor no mesmo PC.
4. Android API 24+: instale APK de desenvolvimento (assinatura v2/v3). Emulador: `http://10.0.2.2:8080/api`. Aparelho físico na LAN: configure `FRONTEND_BIND=0.0.0.0` no `.env` do servidor, recrie frontend e informe `http://IP-DO-PC:8080/api`; permita acesso somente pela rede privada no firewall. Para internet, use proxy HTTPS com certificado válido e proteção administrativa. Esta nuvem não oferece um backend público permanente configurado.
5. Cadastro e login exigem backend ligado/alcançável. O cliente não desativa validação TLS. Falha de DNS/conexão/timeout/certificado/credenciais/cadastro/sessão possuem feedback. Atualização automática pausa após três falhas; Atualizar/Tentar novamente permite nova ação explícita. Trocar URL limpa token antes de autenticar, evitando enviar sessão ao servidor anterior.

A assinatura de desenvolvimento não é distribuição de produção. Não há certificado Authenticode fornecido; não se inventa assinatura Windows. O relato Defender do ZIP 0.6 continua documentado e não é invalidado por um hash ou uma varredura posterior. Nunca desative proteção nem crie exclusões para baixar.

## Exportar e revisar

`scripts/build_clients.py <diretório>` importa e exporta Windows/Android, empacota instruções, calcula hashes e registra commit-fonte. Requer Godot 4.6.3, templates oficiais, JDK e SDK Android 36 configurados nas preferências do editor; chave debug via variáveis `GODOT_ANDROID_KEYSTORE_DEBUG_*`, nunca commitada. `.github/workflows/godot-clients.yml` configura ferramentas e publica artefatos de desenvolvimento. Builds publicados em `builds/development/0.7.0-bd480e0/` são imutáveis por URL de commit; não sobrescrevem release estável.

A branch parte de `feature/godot-admin-migration`, ainda não integrada à main. Para revisar apenas esta evolução, compare aquela branch com `feature/procedural-economy-godot-fixes`; para integrar à main, revise também a migração Godot/ADM anterior. Faça backup e teste as migrações antes de qualquer integração. Não houve merge automático nem alteração direta na main.

## Evidências de validação

- Baseline anterior: 114 testes PostgreSQL aprovados.
- Suite final: **142 testes aprovados**, sem skips/falhas (239,07 s), em banco PostgreSQL descartável; inclui concorrência, rollback, migrações históricas, fórmulas, posse, finanças e novas regras. Houve execuções intermediárias com expectativas antigas ajustadas; elas não foram contabilizadas como aprovação. Compatibilidade de leilões históricos usa uma fixture explícita da política antiga, sem flag em produção.
- Godot Linux/headless contra backend isolado: **42 verificações do controlador real** aprovadas; cadastro/sessão/movimento/combate/equipamento/fuga/morte limitada/NPC de recuperação. Teste adicional passou na validação de URL, mensagens de timeout/TLS/DNS e conexão real recusada.
- `alembic check`: sem divergências. Docker backend/frontend e TypeScript/Vite compilados. Central ADM no Chromium aprovada: sessão independente, permissões, prévia/confirmação/replay, emissão/retirada pareadas, reconciliação exata, módulos, mobile e revogação. Formulário de eventos no Chromium aprovado: preencher sem JSON, prévia +100%, agendar, confirmar e cancelar antes do início.
- Migração sobre banco operacional: backup prévio fora do repositório e **274 registros existentes com todos os campos originais preservados** após upgrade/seed; adições são colunas/estruturas novas e NPC/perfil ausentes. Nenhum progresso foi apagado.
- Exportação local Windows/Android concluída. ZIP CRC válido, executável e PCK embutido, APK v2/v3 válido, mínimo Android API 24/target 36, permissões INTERNET/ACCESS_NETWORK_STATE e arquiteturas conferidas. APK usa chave de desenvolvimento; EXE não tem Authenticode.
- [Exportação reproduzida no GitHub Actions](https://github.com/Lucassilvatech/Dungeon-game/actions/runs/40258147700): **success**. A primeira execução teve falha de preparação do SDK; a correção usa SDK já fornecido pelo runner Ubuntu 24.04, preservando validação normal.
- [Windows nativo e Defender](https://github.com/Lucassilvatech/Dungeon-game/actions/runs/40258420595): **success**. Mesmo ZIP publicado/hash esperado, engine 1.1.26090.9, definições 1.461.206.0, MAPS=2, conexão ao serviço Microsoft verificada e nenhuma detecção nessa varredura. EXE iniciou e encerrou corretamente em Windows/headless, sem erros de carregamento de scripts. Nas duas primeiras execuções a conexão à nuvem não foi validada; o workflow foi corrigido para tentativas limitadas, diagnóstico explícito e retenção do relatório, sem desligar proteções/excluir arquivos.
- Ambos os downloads públicos foram lidos integralmente via HTTPS: HTTP 200, tamanhos e SHA256 conferidos; evidências em `docs/security/downloads-0.7-verification.json`. Isso é verificação de integridade/acesso, não atestado de segurança.

Limites: login/jogo em janela no Windows, GPU/toque e instalação/cadastro/login em Android real/emulador ainda não executados neste ambiente. Não há backend público permanente nem certificado Windows de assinatura de código fornecido. A conexão Android depende da URL/rede/servidor configurados pelo operador. Avisos conhecidos: depreciação do TestClient/Node actions e bundle Phaser grande. Não declarar falso positivo confirmado nem restaurar um arquivo detectado com base no resultado CI.

Regressão web legado também aprovada: cidade/Guilda/treino/mobile/combate, reconexão, aventura/fuga, atributos e morte/recuperação de duas contas. Reinício real backend/frontend preservou exatamente todos os registros acompanhados, incluindo recuperação, cobrança, eventos agendados, custódia, lances, Banco Central e ledger; papéis ADM temporários revogados (contagem final zero).

Simulação reproduzível de combate/distribuição: `.venv/bin/python scripts/simulate_procedural.py`, 60 mil inimigos e 120 mil combates isolados pelas fórmulas reais de dano, resultados em `procedural-combat-simulation.json`. Política e atributos dos dois personagens-modelo estão explícitos; isso não simula decisões humanas ou sobrevivência à aventura inteira. Somente primeiro andar: não se inventaram limites ou balanceamento para andares futuros. As duas simulações não alteram bases, RNG global ou dados do jogo.

## Revisão incremental 0.8

O limite superior inalcançável documentado na 0.7 foi corrigido somente para novas instâncias: bins antigos permanecem abaixo da cauda transformada `u >= 0.995`, agora reservada ao máximo. Mesma seed reproduz a versão revisada, com igual número de sorteios; instâncias congeladas não são refeitas. Fórmula, contagens antes/depois, distribuição e limitações em [BALANCE_REPORT_0.8.md](BALANCE_REPORT_0.8.md). Grupos/coleta/contratos são aditivos e mantêm as regras econômicas/expedições descritas nesta versão histórica.
