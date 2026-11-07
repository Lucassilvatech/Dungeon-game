# Executar a reconstrução dos mapas no Windows

Branch existente: `feature/village-natural-grass-grounded-walk-0.9`.
Requisitos: Git, Docker Desktop com containers Linux; Node 22 e Python 3.12
apenas para testes fora dos containers. **Nenhuma nova migration nesta entrega.**
O startup já aplica upgrades históricos pendentes antes de iniciar a API.
Não repetir cutover, redistribuição de moedas ou inicialização manual de saldos.

## Atualização e inicialização

PowerShell, a partir da instalação existente. O bloco interrompe a atualização
se houver alterações locais, Git divergente ou falha de backup.

```powershell
& {
    Set-Location "C:\Users\pcnov\OneDrive\Documentos\dev\Dungeon-game"
    git status
    if (git status --porcelain) { throw "Preserve e revise as alterações locais antes de atualizar." }
    git fetch origin
    if ($LASTEXITCODE -ne 0) { throw "Fetch falhou." }
    git switch feature/village-natural-grass-grounded-walk-0.9
    if ($LASTEXITCODE -ne 0) { throw "Troca de branch falhou; não continue na branch anterior." }
    git pull --ff-only origin feature/village-natural-grass-grounded-walk-0.9
    if ($LASTEXITCODE -ne 0) { throw "Git divergente; revise sem reset ou merge automático." }
    if (!(Test-Path .env)) { throw "Configure .env conforme .env.example. Não substitua a senha de um banco existente." }

    docker compose stop backend discord
    if ($LASTEXITCODE -ne 0) { throw "Não foi possível parar os escritores." }
    docker compose up -d --wait db
    if ($LASTEXITCODE -ne 0) { throw "Banco indisponível." }
    $backup = "before-map-rebuild-" + (Get-Date -Format "yyyyMMdd-HHmmss") + "-" + ([guid]::NewGuid().ToString("N").Substring(0,8)) + ".dump"
    New-Item -ItemType Directory -Path .\backups -Force | Out-Null
    docker compose exec -T db pg_dump -U tower -d tower -Fc -f "/tmp/$backup"
    if ($LASTEXITCODE -ne 0) { throw "Backup falhou." }
    docker compose cp "db:/tmp/$backup" ".\backups\$backup"
    if ($LASTEXITCODE -ne 0) { throw "Cópia do backup falhou." }

    # O build instala as dependências fixadas: npm ci e requirements.txt.
    docker compose up -d --build --wait
    if ($LASTEXITCODE -ne 0) { throw "Falha ao iniciar; confira os logs." }
    docker compose ps
    docker compose exec -T backend alembic current
    docker compose exec -T backend alembic check
    docker compose exec -T backend python -m app.guild_cli audit
    Start-Process "http://localhost:8080"
}
docker compose logs -f --tail=100 backend frontend
```

Jogo: <http://localhost:8080>. Administração: <http://localhost:8080/admin>.
API: <http://localhost:8000/docs>. Ctrl+C encerra somente o acompanhamento dos logs.
Discord é opcional e permanece read-only; este comando não habilita o perfil do bot.
Para reativar uma instalação do bot já configurada, use
`docker compose --profile discord up -d --build --wait discord`.

Se o navegador conservar assets antigos, faça Ctrl+F5. Os sprites finais estão
versionados: não é necessário instalar ferramentas de arte para jogar.

## Testes de frontend

```powershell
& {
    Set-Location "C:\Users\pcnov\OneDrive\Documentos\dev\Dungeon-game\frontend"
    npm ci
    if ($LASTEXITCODE -ne 0) { throw "Falha ao instalar dependências." }
    npm test
    if ($LASTEXITCODE -ne 0) { throw "Testes falharam." }
    npm run build
    if ($LASTEXITCODE -ne 0) { throw "Build falhou." }
}
```

## Backend e Chromium isolados

Use **outro PowerShell**, na raiz. O servidor abaixo é um projeto Docker de teste
na porta 55439 e não usa o volume `tower_data`. Cada suíte de navegador cria mais
um banco UUID privado. Os fixtures backend limpam o banco de teste; não configure
este bloco com a URL de uma instalação operacional.

```powershell
& {
    Set-Location "C:\Users\pcnov\OneDrive\Documentos\dev\Dungeon-game"
    docker compose -p dungeon-map-tests -f infrastructure/compose.visual-test.yml up -d --wait
    if ($LASTEXITCODE -ne 0) { throw "Servidor de teste indisponível." }
    if (!(Test-Path .venv\Scripts\python.exe)) { py -3.12 -m venv .venv }
    .\.venv\Scripts\python.exe -m pip install -r backend/requirements-dev.txt
    if ($LASTEXITCODE -ne 0) { throw "Dependências Python indisponíveis." }
    $env:DATABASE_URL = "postgresql+psycopg://tower:visual-test-only@localhost:55439/visual_test"
    $env:TOWER_TEST_DATABASE = "1"
    $env:PYTHONPATH = (Resolve-Path backend).Path
    $env:PATH = (Resolve-Path .venv\Scripts).Path + ";" + $env:PATH
    Push-Location backend
    try {
        ..\.venv\Scripts\python.exe -m alembic upgrade head
        if ($LASTEXITCODE -ne 0) { throw "Upgrade de teste falhou." }
        ..\.venv\Scripts\python.exe -m alembic check
        if ($LASTEXITCODE -ne 0) { throw "Alembic check falhou." }
    } finally { Pop-Location }
    .\.venv\Scripts\python.exe -m pytest backend/tests -q
    if ($LASTEXITCODE -ne 0) { throw "Backend falhou." }
    Push-Location frontend
    try {
        npm ci
        if ($LASTEXITCODE -ne 0) { throw "npm ci falhou." }
        npx playwright install chromium
        if ($LASTEXITCODE -ne 0) { throw "Chromium indisponível." }
    } finally { Pop-Location }
    foreach ($suite in @("visual", "movement", "smoke", "npc-economy", "encounters")) {
        .\.venv\Scripts\python.exe scripts/test_visual_stack.py --suite $suite
        if ($LASTEXITCODE -ne 0) { throw "Falhou a suíte $suite." }
    }
    docker compose -p dungeon-map-tests -f infrastructure/compose.visual-test.yml stop
}
```

As validações automatizadas desta entrega usam Linux/Chromium; os comandos foram
preparados para PowerShell, mas não executados em um Windows físico.

## Revisão e encerramento

Confira vila, Aventura, ruínas e salas especiais acessíveis pela progressão existente.
Teste WASD, clique/toque nas portas, NPCs, recursos, comércio, combate e reconexão.
O tamanho visual do tile é 48 px; as coordenadas lógicas do jogo não mudaram.
Personagens usam as identidades aprovadas e oito poses de caminhada por direção.

```powershell
docker compose stop
```

Não apagar `.env`, banco ou volumes. Godot Windows/Android permanecem congelados;
esta entrega não exige APK nem executável Windows.
