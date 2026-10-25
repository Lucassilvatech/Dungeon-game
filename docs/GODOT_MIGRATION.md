# Cliente Godot 4 — 0.6

O cliente principal novo está em `godot-client/`. React/Phaser permanece funcional durante a migração; não foi removido nem substituído por uma tela de administração.

## Executar

Instale Godot **4.6.3 Standard** (GDScript; não precisa .NET), importe `godot-client/project.godot` e execute a cena principal. Ou:

```powershell
godot --path godot-client
```

Inicie o backend da branch com Docker Compose conforme README. Na tela de login Godot, configure a URL da API. Windows local: `http://127.0.0.1:8080/api`. Emulador Android: `http://10.0.2.2:8080/api`. Em telefone físico use o endereço HTTPS de um servidor alcançável pelo aparelho; localhost aponta para o próprio aparelho. A stack de desenvolvimento publica apenas loopback por padrão. Não precisa alterar `.env` ou abrir o PostgreSQL ao cliente.

Conta e personagem são os mesmos da web e do Discord. Se não houver personagem, o cliente pede sua criação; caso exista, carrega o persistido. Sessão e URL são salvas em `user://session.cfg` no armazenamento privado da aplicação; senhas não são salvas. Token expirado volta ao login; falha de rede mantém o último estado e tenta nova consulta a cada 2s. A sessão deve ser protegida pelas permissões do usuário do sistema em Windows. Backups Android da aplicação estão desabilitados no preset.

## Jogar

- Windows: WASD/setas ou clique. Android: toque no mapa, botões direcionais e controles maiores. Interface com containers, menus com scroll e viewport adaptável; orientação Android em paisagem.
- Clique/toque no chão para caminhar, no inimigo para aproximar e combater, na saída para atravessar, ou use os caminhos listados.
- NPC da recepção paga recompensas; outro NPC abre leilões no Salão da Guilda.
- Ataque, golpe com energia e defesa usam as regras existentes. Treinamento reinicia explicitamente e não dá recompensas.
- Menus: personagem/atributos, inventário/equipamento, caminhos/viagem rápida, Guilda, leilões/detalhes/lances, exploração/segredos e formação de raid. Raid permanece lobby; combate coletivo e novas habilidades não foram implementados.
- Aventura ACTIVE bloqueia saídas e viagem rápida. Fuga exige prévia com valores do servidor e confirmação. Morte tem resumo persistente, dívida e retorno à cidade; a espada inicial protegida permanece.
- Ouro e lances usam os valores textuais exatos fornecidos pela API, evitando perda de precisão do JSON numérico no Godot.

## Arquitetura

`scenes/main.tscn` compõe `scripts/main.gd` (interface/controlador), `api.gd` (HTTP/autenticação/sessão) e `map_view.gd` (pixel art original, câmera, atores e entrada). A renderização usa paleta própria, formas em pixels, materiais da sala e fade individual de mortos; não usa assets comerciais. Presença visual usa WebSocket autenticado por mensagem, heartbeat e reconexão, seguindo o mesmo protocolo da web.

O caminho local é somente uma fila de passos; o servidor valida cada passo, combate, equipamento, valor, recompensa e transição. O cliente nunca acessa PostgreSQL e não calcula dano, loot, imposto ou resultado de leilão. Todas as decisões econômicas continuam no FastAPI.

## Exportar Windows/Android

Instale os templates oficiais **da mesma versão 4.6.3**. Presets Windows x86-64 e Android estão versionados; `exports/`, binários e credenciais não entram no Git. Para Android instale JDK 17+ e SDK com platform-tools, plataforma 36 e build-tools 36.0.0. Configure os caminhos no Editor Settings → Export → Android.

```powershell
New-Item -ItemType Directory -Force exports
godot --headless --path godot-client --export-debug Windows ../exports/DungeonGame.exe
godot --headless --path godot-client --export-debug Android ../exports/DungeonGame.apk
```

A chave Android de desenvolvimento deve ser configurada no editor ou por `GODOT_ANDROID_KEYSTORE_DEBUG_PATH`, `GODOT_ANDROID_KEYSTORE_DEBUG_USER`, `GODOT_ANDROID_KEYSTORE_DEBUG_PASSWORD`. Não coloque uma chave de produção no repositório. O workflow `.github/workflows/godot-clients.yml` prepara ferramentas e produz artefatos de desenvolvimento para revisão; sua execução remota ainda depende de abrir/disparar o workflow no GitHub.

## Validação real e limites

- Godot 4.6.3 executado em Linux/headless contra FastAPI e PostgreSQL isolados: **44 verificações** do controlador, incluindo entrada por teclado/comando de toque, caminhos/NPCs, combate real, pontos, equipamento, viagem descoberta, expedição, fuga, pagamento, morte, dívida, proteção, reconexão e lance de segundo jogador financiado por combate.
- Templates oficiais verificados por SHA512; ferramentas Android verificadas contra o catálogo oficial.
- `.exe` Windows gerado; pacote embutido carregado pelo Godot Linux para verificar recursos/scripts. Isso **não** é execução nativa no Windows.
- APK gerado, assinatura v2/v3 verificada com apksigner; pacote `tech.lucassilva.dungeongame`, mínimo API 24 (Android 7), target API 36. Assinatura de desenvolvimento, sem publicação em loja.
- **Não validado:** execução em Windows real, instalação/toque/GPU em dispositivo Android e execução do workflow remoto. O teste headless verifica comandos e integração, não ergonomia, FPS ou renderização numa GPU móvel. Validar esses itens antes de descontinuar o Phaser.

Para repetir o teste nativo use backend isolado com `SECRET_CHANCE=0`, `WANDER_INTERVAL=100000` e `DUNGEON_API_URL` apontando para ele, então `godot --headless --path godot-client --script tests/play_first_floor.gd`. O teste cria suas próprias contas e nunca modifica progresso de outros jogadores. Use diretório de dados Godot de teste vazio para não restaurar uma sessão anterior durante o bootstrap.
