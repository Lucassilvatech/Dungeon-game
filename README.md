# Torre RPG

Protótipo de RPG persistente com FastAPI, PostgreSQL, React/TypeScript, Phaser e um cliente Discord. Arte original desenhada com formas pixeladas. Um backend controla todas as regras e os dois clientes consultam os mesmos personagens.

## Windows: executar

Instale Git e Docker Desktop com WSL2 e Docker Compose. No PowerShell:

```powershell
git clone https://github.com/Lucassilvatech/Dungeon-game.git
cd Dungeon-game
Copy-Item .env.example .env
docker compose up --build -d
```

Abra `http://localhost:8080`. API e documentação: `http://localhost:8000/docs`. Crie uma conta, um personagem e equipe a espada na mochila. Use WASD/setas ou os botões. Aproxime-se dos alvos: curandeira/Guilda amarela em (3,3), slime em (5,6), chefe em (12,8), portal em (13,2). A curandeira restaura vida e energia. Vença, volte à Guilda e receba as recompensas pendentes. O chefe libera o segundo andar para todas as contas. Atualizar a página conserva personagem, itens e combate.

```powershell
docker compose ps
docker compose logs backend
docker compose down
```

O volume `tower_data` conserva o banco; não use `down -v` se quiser manter personagens. A migração e o seed idempotente executam no startup do backend. O saldo inicial só é aplicado ao criar o Tesouro, nunca a cada reinício. A senha de exemplo é apenas para desenvolvimento; use uma senha alfanumérica forte no deploy (a URL atual não codifica caracteres reservados).

## Discord (opcional)

No Discord Developer Portal, crie uma aplicação/bot e convide-o com scopes `bot` e `applications.commands`. Não precisa de intents privilegiados. Preencha `DISCORD_TOKEN` e uma chave aleatória `DISCORD_SERVICE_KEY` em `.env`; nunca publique esses valores. Recrie o backend após configurar a chave:

```powershell
docker compose --profile discord up --build -d
```

No navegador, gere um código e use `/vincular codigo:...` no bot em até 5 minutos. Depois `/personagem`, `/status`, `/inventario` e `/mapa` consultam dados reais. Códigos são de uso único. Não há criação paralela de personagens pelo Discord. Os demais comandos ainda não estão disponíveis. Sincronização global de comandos pode demorar no Discord.

## Estado e limites

Implementados: contas e sessões, personagem único por conta, colisões no servidor, NPC, combate por turnos com retomada, XP/nível, inventário e espada, recompensa contábil com orçamento, desbloqueio global persistente e vínculo Discord. Sem mercado, grupos, profissões, mentoria ou combate cooperativo nesta etapa. Monstros representam encontros pessoais repetíveis; os outros jogadores ainda não são desenhados no mapa. O estado global compartilhado é o desbloqueio dos andares e o Tesouro. O segundo andar é uma área demonstrativa.

Veja [desenvolvimento](docs/DEVELOPMENT.md), [arquitetura](docs/ARCHITECTURE.md), [economia](docs/ECONOMY.md), [design](docs/GAME_DESIGN.md) e [roadmap](docs/ROADMAP.md). Este protótipo precisa de endurecimento de segurança antes de exposição pública: TLS, limites de requisições, recuperação de senha, expiração/limpeza de sessões e observabilidade.
