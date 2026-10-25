# Dungeon Game — primeiro andar

RPG persistente com FastAPI, PostgreSQL, React/TypeScript, Phaser e cliente Discord. Esta versão aperfeiçoa exclusivamente o **primeiro andar**. Não expande andares superiores nem raids. Arte e sprites originais gerados pelo projeto, sem assets das referências comerciais.

## Windows: executar ou atualizar

Com Git e Docker Desktop/WSL2 instalados, dentro do checkout:

```powershell
git pull origin main
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

`down` conserva o volume. Migração atual: **904ca715f282**, que adiciona expedições persistentes e perigo regional. A migração anterior de stacks/inimigos é 11ac6a18a976. Aventuras antigas ocupadas são adotadas como ativas; histórico abandonado é arquivado sem aplicar penalidade retroativa. Contas, inventário, equipamentos, saldos, XP, inimigos mortos e batalhas em andamento são preservados. Faça backup dos dados importantes antes de atualizar.

## Discord e limites atuais

O bot continua usando o mesmo backend e personagem. Configure `DISCORD_TOKEN` e uma chave aleatória `DISCORD_SERVICE_KEY` apenas em `.env`, nunca no Git. No Developer Portal convide o bot com scopes `bot` e `applications.commands`, sem intents privilegiados. Execute:

```powershell
docker compose --profile discord up --build -d
```

Na aba Personagem, gere código de cinco minutos e use `/vincular` no bot; `/personagem`, `/status`, `/inventario` e `/mapa` consultam dados reais. A conexão externa depende das credenciais e não foi validada nesta entrega.

A prioridade adicional escolhida no roadmap foi sinalização de perigo e feedback de exploração; combate ainda é individual por alvo. A lista de instâncias prepara encontros com grupos, mas combate contra vários alvos simultâneos e raids coletivas não estão implementados. Presença visual usa um único worker; exige broker antes de escalar. Coleta, contratos, mercado e economia avançada permanecem futuros. Antes de exposição pública, completar TLS, rate limiting e gestão de sessões. O bundle Phaser ainda merece otimização.
