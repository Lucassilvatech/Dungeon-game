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

Abra `http://localhost:8080`. API e documentação: `http://localhost:8000/docs`.

Novos personagens começam na **Vila do Alvorecer**, uma cidade segura. Personagens da versão 1 mantêm posição, XP, moedas, equipamento e combate; o antigo primeiro mapa passa a ser o Bosque das Lanternas. Não apague o volume para atualizar.

1. Crie conta/personagem e equipe a espada na aba **Inventário**.
2. Use WASD/setas ou clique no chão. Selecione portas, NPCs e inimigos no mapa ou os caminhos abaixo dele: o personagem caminha até o destino e o servidor valida cada passo.
3. Entre na Guilda pela porta ao sul do prédio central. Converse com a curandeira e siga para o pátio de treinamento. O boneco não concede XP, itens ou moedas.
4. Volte à cidade e siga pelo caminho leste. Explore Bosque → Trilha → Clareira → Santuário. Selecionar o chefe apresenta um aviso; o combate só começa após confirmar a tentativa solo.
5. Use **Aventura** na cidade ou nas trilhas. O servidor escolhe uma sala procedural persistente ou a descoberta de uma entrada secreta. A chance padrão do segredo é 25%; não há garantia por tentativa.
6. Depois da descoberta, a aba **Exploração** permite voltar à masmorra. Sua dificuldade é independente do andar. Derrota preserva pertences e descobertas; a primeira conclusão tem recompensa maior, e repetições não dão mais XP/loot relevante.
7. Volte ao NPC da Guilda/curandeira e use a aba **Guilda** para reivindicar moedas do Tesouro. Derrotar o chefe de andar libera globalmente a cidade do segundo andar, acessível pelo portal da cidade.

Outros navegadores conectados na mesma sala aparecem via WebSocket. A aba **Mapa** mostra apenas salas e conexões descobertas. A aba **Raid** mantém convites e participantes; combate cooperativo ainda não está disponível.

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

## Capturas verificadas

[Cidade](docs/screenshots/city.png) · [Guilda](docs/screenshots/guild.png) · [Treinamento](docs/screenshots/training.png) · [Mobile](docs/screenshots/mobile.png). Capturadas do jogo em execução no Chromium.

## Atualizar uma instalação existente

```powershell
git pull origin main
docker compose up --build -d
```

As migrações Alembic `f2a7deb6dbfd` (salas/descobertas/raids) e `d348cc807194` (integridade de proprietário procedural) atualizam o banco sem recriá-lo. Faça backup antes de atualizar dados importantes. Preserve `.env` e o volume existente; nunca use `down -v` para atualizar.

## Estado e limites

Implementados: base da versão 1, cidade, Guilda e treinamento, salas conectadas, pathfinding visual, sprites/animações originais, câmera suave, aventuras, três templates procedurais por seed, segredo persistente com bestiário e primeira conclusão, chefe em sala própria, formação de raids e presença visual via WebSocket. O segundo andar tem cidade demonstrativa.

Parciais: raid é um lobby persistente de até quatro participantes, **sem combate coletivo**; presença funciona num único processo FastAPI, sem broker para múltiplos workers; animações são provisórias geradas em runtime e substituíveis por spritesheets. Monstros continuam sendo encontros pessoais, não inimigos globais compartilhados. Coleta de recursos, contratos reservados, mercado, profissões e mentoria não estão implementados.

Veja [desenvolvimento](docs/DEVELOPMENT.md), [arquitetura](docs/ARCHITECTURE.md), [salas](docs/ROOM_SYSTEM.md), [segredos](docs/SECRET_DUNGEONS.md) e [roadmap](docs/ROADMAP.md). Antes de exposição pública: TLS, limites de requisições, recuperação/revogação de sessões e observabilidade. A conexão com o Discord externo continua dependendo das credenciais; seus dados e vínculo são verificados por testes HTTP.
