# Dungeon Game — primeiro andar · Godot e Central ADM

> O build Windows de desenvolvimento recebeu relato de bloqueio “vírus detectado” e está em investigação. Não desative o antivírus ou crie exclusão. [Status e verificações](docs/security/WINDOWS_BUILD_TRIAGE.md).

RPG persistente com FastAPI, PostgreSQL, cliente Godot 4 para Windows/Android, Central Administrativa web e cliente Discord. React/TypeScript/Phaser permanece como cliente legado durante a migração. Esta versão aperfeiçoa exclusivamente o **primeiro andar**. Não expande andares superiores nem raids. Arte e sprites originais gerados pelo projeto, sem assets das referências comerciais.

## Revisar esta evolução sem alterar a main

Esta implementação está em **feature/godot-admin-migration**, para revisão por PR; a main permanece estável e não houve merge automático. Guarde alterações locais antes de trocar de branch. Para testar o código desta entrega:

```powershell
git fetch origin
git switch feature/godot-admin-migration
```

Use os comandos de execução abaixo na branch selecionada. Não use reset/force push ou apague volumes para atualizar.

## Cliente principal Godot e Central Administrativa

Abra `godot-client/project.godot` no Godot **4.6.3 Standard** e execute. Windows local usa API `http://127.0.0.1:8080/api`; Android permite configurar URL e controles por toque (emulador: `http://10.0.2.2:8080/api`, aparelho físico: endereço HTTPS alcançável). Os presets exportam `.exe` Windows x86-64 e APK Android; ambos foram gerados nesta nuvem. Execução nativa no Windows e em dispositivo Android permanece **não validada**; o fluxo jogável foi executado no motor Godot Linux/headless. [Cliente, controles, exportação e testes](docs/GODOT_MIGRATION.md).

Central ADM: `http://localhost:8080/admin`, com entrada web e sessão independentes. Não há administrador/senha padrão: crie uma conta normal e conceda um papel explicitamente pelo [procedimento local](docs/ADMINISTRATION.md). O personagem administrativo continua normal. O cliente web legado permanece em `http://localhost:8080`.

Implementado: viagem rápida validada somente a locais permanentes visitados, Salão de Leilões na Guilda, informações/histórico reais dos anúncios, proteção permanente da Espada de Aprendiz (`sword`), diagnóstico e recuperação individual auditada, módulos administrativos e Banco Central manual com contabilidade e créditos de teste isolados. Não foram implementados andares superiores ou habilidades futuras.

## Windows: executar ou atualizar

Com Git e Docker Desktop/WSL2 instalados, dentro do checkout:

```powershell
git pull --ff-only
if (!(Test-Path .env)) { Copy-Item .env.example .env }
docker compose up --build -d
```

Para uma instalação nova: clone `https://github.com/Lucassilvatech/Dungeon-game.git` e entre em `Dungeon-game` antes desses comandos.

Frontend: `http://localhost:8080`. API/documentação: `http://localhost:8000/docs`.

Não apague `.env` nem use `docker compose down -v` para atualizar. O startup aplica as migrações e faz seed idempotente; progresso e volume existente são preservados. A senha de exemplo é somente para desenvolvimento. A URL atual espera senha de banco sem caracteres reservados; use uma senha alfanumérica forte no deploy.

## Jogar no primeiro andar

1. Crie conta/personagem; equipe a espada na aba **Inventário**.
2. Use WASD/setas ou clique em chão, inimigo, NPC ou saída. As ações caminham visualmente até o destino, com passos validados no servidor.
3. A cidade é segura. Entre na Guilda pela porta abaixo do prédio inicial. A **recepcionista**, atrás do balcão, recebe os registros de monstros; não há mais curadora espalhada nas salas. Use **Descansar** na cidade/Guilda para restaurar vida e energia.
4. A Guilda leva ao pátio de treinamento. O boneco tem combate real, mas não dá XP, itens nem moedas. **Novo exercício** cria outra instância de treino de forma explícita.
5. Siga os caminhos Cidade → Bosque → Trilha → Clareira. Agora há vários inimigos, com identidade, vida, movimento e morte persistentes. Um slime de nível 1 exige quatro ataques básicos de um iniciante com a espada. Defesas, habilidades e descanso importam.
6. Inimigo derrotado executa morte/fade e desaparece. Não pode ser combatido novamente na mesma instância, nem ao recarregar. XP e loot são confirmados uma vez; moedas ficam como recompensa pendente.
7. Volte à Guilda, aproxime-se da recepcionista e escolha **RESGATAR RECOMPENSAS**. A tela agrupa os registros por monstro e mostra o total. O Tesouro é debitado atomicamente e os registros são marcados como pagos.
8. **Aventura é uma expedição com compromisso.** Ao entrar numa sala procedural com inimigos, não é possível gerar outra aventura nem usar saídas normais enquanto restar algum inimigo. A trava persiste em F5, logout/login, reconexão e chamadas diretas da API.
9. Derrote todos para marcar **EXPEDIÇÃO CONCLUÍDA** e liberar **RETORNAR** ou **NOVA AVENTURA**, preservando XP, itens e recompensas.
10. Para sair antes, escolha **FUGIR DA AVENTURA**. A confirmação mostra valores reais: perde-se 50% do total monetário pendente na Guilda (inclusive registros de outras salas), arredondando a perda para cima; todo o XP do nível atual é zerado. **Nível, atributos conquistados, moedas já recebidas e itens permanecem.** A fuga encerra a expedição e retorna à cidade. Exemplo: 301 pendentes → 150 restantes, 151 perdidas.

11. **Morrer em Aventura procedural é diferente de fugir:** encerra a expedição como FAILED, zera todo o XP atual e todas as recompensas monetárias pendentes da Guilda, e transfere todos os itens físicos carregados (inclusive equipados e stacks) para custódia de leilão. A **Espada de Aprendiz** e itens estruturais marcados como não transferíveis são preservados. A proteção vale para novos e antigos personagens, pela identidade estável da definição, sem proteger outras espadas. O resumo de morte persiste em F5 até você confirmar **RETORNAR À CIDADE**; o resgate já ocorreu no backend.
12. A taxa médica padrão provisória é **100 moedas por morte** (`MEDICAL_FEE_BASE`). Ela pode deixar o saldo negativo. Saldo 50 − taxa 100 = −50. Pagamentos futuros e devoluções de lances compensam automaticamente esse mesmo saldo, sem outra moeda de dívida: −500 +300 = −200; −500 +800 = 300.
13. O saldo nunca fica abaixo de **−10.000**. Cada morte que alcance ou tente ultrapassar esse limite reduz o nível em até 10, com mínimo 1. Em mortes futuras no limite, aplica novamente uma única penalidade por morte. Normalmente, morrer só zera XP e mantém o nível. O respawn restaura toda a vida e energia; `RESPAWN_HP_PERCENT` permite ajustar a porcentagem de vida apenas para esse resgate procedural.
14. Na aba **Leilão**, apenas personagens de contas autenticadas podem dar lances. O início é `max(MIN_AUCTION_START_PRICE, ceil(valor_base × quantidade / 5))`; espada vale 100 (início 20), cristal vale 10 por unidade (20 cristais iniciam em 40). Valores são provisórios, definidos no backend. Sem valor base confiável, usa-se o mínimo configurado, padrão 1. Duração provisória: **24 horas**, configurável em `AUCTION_DURATION_HOURS`.
15. O maior lance fica reservado: sai do saldo disponível e aparece como ouro em custódia. Ser superado devolve a reserva; aumentar seu próprio lance cobra só a diferença. Saldo disponível ≤0 impede lance, mesmo com uma reserva anterior. Não há teto comercial de lance; PostgreSQL NUMERIC e valores decimais em texto na UI preservam inteiros grandes. Ao terminar, o vencedor recebe o mesmo item/stack; o valor vai para o Tesouro (ou sink configurado), nunca para quem morreu. Sem lances, fica **UNSOLD**, arquivado em custódia, sem destruição automática. Não existe compra por NPC.
16. Na aba **Personagem**, distribua **1 ponto por novo nível** entre os atributos existentes: **Força e Defesa**. Prepare um ou vários pontos e confirme em lote. Eles acumulam; não há respec nesta etapa. A vida máxima continua derivada do nível. Ao perder níveis, consomem-se pontos não gastos primeiro; o restante vira `attribute_point_debt`, quitado por ganhos futuros antes de conceder novos pontos. Os atributos escolhidos permanecem.

### Política de migração dos atributos

A versão anterior já acrescentava força automaticamente a cada nível. Por isso, **personagens existentes conservam força, defesa, nível e XP exatamente como estavam, começam com zero pontos disponíveis e zero dívida, sem pontos retroativos**. A partir desta atualização, os próximos níveis concedem pontos manuais, substituindo o ganho automático de força. Não foram criadas vitalidade, inteligência ou uma lista paralela de atributos. As novas regras de morte não são aplicadas retroativamente.

Salas comuns continuam livres: não é necessário eliminar inimigos para atravessar Bosque → Trilha → Clareira. O **Danger Tier** aumenta por região (1 → 2 → 3 → chefe 5); HP, ataque, defesa e nível dos inimigos dependem da região, nunca do nível de quem visita. O indicador de perigo aparece no HUD e no mapa conhecido.

Expedições novas preservam variação de temas e seed. Atualizar a interface mantém a mesma sala e suas baixas. Descobrir uma entrada secreta não cria, por si só, uma expedição procedural. As regras anteriores de masmorra secreta são preservadas.

Materiais se agrupam em stacks com limite por definição (cristais: 99). Equipamentos mantêm IDs individuais. O inventário mostra quantidade, capacidade e descrição no tooltip.

## Conteúdo

Cidade 52×36; Guilda 38×28; treinamento 32×24; salas comuns 34×26; combate 40×28. Expedições variam entre 32×24 e 44×30, com pedra/musgo, ruínas/vegetação, cristais/ossos ou entreposto de madeira. O chefe e o segredo existentes permanecem; a prioridade desta entrega é a qualidade do primeiro andar. Funcionalidade legada de andares superiores não foi expandida e não faz parte do novo fluxo.

[Capturas](docs/screenshots) · [Regras desta versão](docs/FIRST_FLOOR.md) · [Arquitetura](docs/ARCHITECTURE.md) · [Desenvolvimento/testes](docs/DEVELOPMENT.md) · [Roadmap](docs/ROADMAP.md).

```powershell
docker compose ps
docker compose logs backend
docker compose down
```

`down` conserva o volume. Migração atual: **b3057d8109ee**, que protege a espada inicial, cria sessões/papéis/auditoria administrativa, Banco Central inicialmente zerado, configurações e perfis persistentes de monstros, preservando os inimigos existentes e seu XP. A anterior, 039105b3ae1a, adicionou morte, dívida, custódia/leilões, pontos de atributo e NUMERIC. A anterior, 904ca715f282, adicionou expedições persistentes e perigo regional. A migração anterior de stacks/inimigos é 11ac6a18a976. Aventuras antigas ocupadas são adotadas como ativas; histórico abandonado é arquivado sem aplicar penalidade retroativa. Contas, inventário, equipamentos, saldos, XP, inimigos mortos e batalhas em andamento são preservados. Faça backup dos dados importantes antes de atualizar.

## Discord e limites atuais

O bot continua usando o mesmo backend e personagem. Configure `DISCORD_TOKEN` e uma chave aleatória `DISCORD_SERVICE_KEY` apenas em `.env`, nunca no Git. No Developer Portal convide o bot com scopes `bot` e `applications.commands`, sem intents privilegiados. Execute:

```powershell
docker compose --profile discord up --build -d
```

Na aba Personagem, gere código de cinco minutos e use `/vincular` no bot; `/personagem`, `/status`, `/inventario` e `/mapa` consultam dados reais. A conexão externa depende das credenciais e não foi validada nesta entrega.

A prioridade adicional escolhida no roadmap foi sinalização de perigo e feedback de exploração; combate ainda é individual por alvo. A lista de instâncias prepara encontros com grupos, mas combate contra vários alvos simultâneos e raids coletivas não estão implementados. Presença visual usa um único worker; exige broker antes de escalar. O leilão atual é exclusivo de espólios de morte. Coleta, contratos, mercado geral e economia avançada permanecem futuros. Antes de exposição pública, completar TLS, rate limiting e gestão de sessões. O bundle Phaser ainda merece otimização.

## Configuração provisória desta etapa

Ajuste `.env` antes de subir a stack; `docker compose up --build -d` aplica sem apagar o volume:

| Variável | Padrão | Regra |
|---|---:|---|
| MEDICAL_FEE_BASE | 100 | Taxa fixa por morte procedural |
| RESPAWN_HP_PERCENT | 100 | Porcentagem de vida máxima no resgate |
| MIN_AUCTION_START_PRICE | 1 | Mínimo/fallback do lance inicial |
| AUCTION_DURATION_HOURS | 24 | Prazo provisório de novos leilões |
| AUCTION_PROCEEDS_DESTINATION | treasury | `treasury` ou `sink`, gravado ao criar o leilão |
| AUCTION_SWEEP_SECONDS | 30 | Intervalo de resolução automática de vencidos |

Leilões mantêm prazo/preço/destino originalmente gravados. A reserva de um lance feito antes da morte continua em custódia; não é item carregado nem saldo disponível para pagar a taxa médica. Se devolvida depois, amortiza a dívida. O custo efetivo da taxa é limitado pelo piso do saldo; a parte que excederia −10.000 é registrada como `waived`, e a penalidade de níveis ocorre uma vez. O Tesouro recebe somente o débito efetivamente aplicado ao saldo, preservando a soma contábil dos saldos assinados e reservas.

## Administração e Banco Central

O painel consulta dados reais de jogadores/contas, inventário/custódia, monstros/instâncias, Guilda/Tesouro, leilões/lances, mundo/eventos e auditoria. Operações mutáveis exigem permissão de domínio, justificativa, prévia do estado/impacto e confirmação em até 5 minutos. Backend rejeita sessão normal, confirmação repetida com dados diferentes, prévia obsoleta, fundos insuficientes e transferência de recursos de teste.

Banco Central começa com **reserva 0**, sem emissão retroativa. Transferência debita a conta de origem; emissão/retirada alteram oferta explicitamente e deixam ledger único por UUID. A tela distingue dinheiro disponível, dívida assinada, reservas, escrow e obrigações, apresenta reconciliação, riqueza e fluxos por período. Sugestões não executam emissão automática. Contador administrativo sandbox nunca vira ouro ou lance de jogador.

Espadas históricas em custódia têm negociação suspensa, sem devolução indiscriminada. Administrador identifica item/donos/lances e pode recuperar o mesmo ID com reembolso da reserva ou autorizar reposição se houve comprador legítimo, preservando seu item. [Leilões e recuperação](docs/AUCTIONS.md) · [Viagem rápida](docs/FAST_TRAVEL.md) · [Central ADM](docs/ADMINISTRATION.md) · [Banco Central](docs/CENTRAL_BANK.md) · [Contabilidade](docs/ACCOUNTING.md) · [Segurança/auditoria](docs/SECURITY_AUDIT.md).
