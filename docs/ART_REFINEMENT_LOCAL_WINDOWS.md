# COMO EXECUTAR LOCALMENTE

Windows PowerShell, Git, Docker Desktop em modo Linux. Branch `feature/pixel-art-cohesion-refinement-0.9`. Migração incremental65a7c9e21b04: retira somente colisões decorativas antigas da cidade; mantém estrutura, personagens e economia. Preserve o banco, `.env`, cutover ativo e denominações existentes.

## Atualizar com segurança e backup

```powershell
cd "C:\Users\pcnov\OneDrive\Documentos\dev\Dungeon-game"
git status
git diff
if (git status --porcelain) { throw "Revise e preserve as alterações locais antes de continuar." }
git fetch origin
if ($LASTEXITCODE -ne 0) { throw "Fetch falhou." }
git switch feature/pixel-art-cohesion-refinement-0.9
if ($LASTEXITCODE -ne 0) { throw "Troca de branch falhou; não execute pull na branch anterior." }
git pull --ff-only origin feature/pixel-art-cohesion-refinement-0.9
if ($LASTEXITCODE -ne 0) { throw "Atualização Git falhou." }

if (!(Test-Path .env)) {
    Copy-Item .env.example .env
    throw "Preencha POSTGRES_PASSWORD no novo .env antes de iniciar; não substitua o .env de um banco existente."
}
# POSTGRES_PASSWORD é obrigatório. Discord é opcional: token/chave só no perfil discord.
# .env existente deve continuar com a senha do banco existente.
docker compose stop backend discord
if ($LASTEXITCODE -ne 0) { throw "Não foi possível parar os escritores." }
docker compose up -d --wait db
if ($LASTEXITCODE -ne 0) { throw "Banco indisponível." }
$backup = "before-art-refinement-" + (Get-Date -Format "yyyyMMdd-HHmmss") + "-" + ([guid]::NewGuid().ToString("N").Substring(0,8)) + ".dump"
New-Item -ItemType Directory -Path .\backups -Force | Out-Null
docker compose exec -T db pg_dump -U tower -d tower -Fc -f "/tmp/$backup"
if ($LASTEXITCODE -ne 0) { throw "Backup falhou; interrompa." }
docker compose cp "db:/tmp/$backup" ".\backups\$backup"
if ($LASTEXITCODE -ne 0) { throw "Cópia do backup falhou; interrompa." }

docker compose up -d --build --wait
if ($LASTEXITCODE -ne 0) { throw "Inicialização falhou; examine os logs." }
docker compose ps
docker compose exec -T backend alembic current
docker compose exec -T backend alembic check
docker compose exec -T backend python -m app.guild_cli audit
Start-Process "http://localhost:8080"
Start-Process "http://localhost:8080/admin"
```

Frontend8080, backend8000 (`/health`, `/docs`), Central8080/admin. Backend é ligado somente a127.0.0.1 no Compose. Não existe conta administrativa padrão. Não repetir cutover/rebalanceamento. Startup aplica upgrades pendentes e seed idempotente. Head esperado65a7c9e21b04. Não é necessário executar a migration manualmente antes do Compose: o CMD do backend a aplica antes de iniciar a API.

```powershell
docker compose logs -f --tail=200 backend frontend
# Ctrl+C interrompe apenas os logs.
```

## Revisão visual no jogo real

1. Entre com sua conta/personagem. A vila clara tem grama, casas, árvores e caminhos. WASD/setas e clique/toque continuam funcionando.
2. Caminhe até a Guilda e clique na porta desenhada. O caminho chega à entrada real, e o clique resolve para a saída autorizada pelo backend. Portas de casas decorativas não inventam interiores.
3. Abra **Lojas da vila**, escolha **Ferreiro**, **Alquimista** ou **Comerciante**, use **Ir até**. Na proximidade, clique/toque/E abre o serviço real. Confira loja, caixa, estoque e preços sem reconfigurar a economia.
4. Vá ao sudoeste, barraca em(3,27), figura encapuzada em(5,30). O rosto permanece oculto, mas o personagem aparece à frente da entrada. O serviço de recuperação continua com suas condições anteriores.
5. **AVENTURA** cria/retoma uma expedição procedural. Observe piso, paredes, inimigos, recursos, sombras, luzes e feedback de combate. Uma expedição ativa continua exigindo conclusão ou fuga confirmada; o novo visual não muda esse compromisso.
6. Secret Dungeon é descoberta pelas regras existentes de Aventura. Após descoberta, use sua entrada no mapa/atlas. Não é garantida em cada clique. A Cripta da Maré possui aparência abissal fixa. Não revelar/forçar salas pelo banco operacional.
7. O Guardião fixo mantém sua posição no Santuário, acessível pela progressão Bosque→Trilha→Clareira→Santuário. Visual de colosso do musgo; regras, vida, dificuldade e alertas continuam os existentes. Bosses procedurais existentes recebem aparência determinística por seed/sala/spawn.
8. Recarregue/reconecte na mesma instância e confira aparência/progresso. Nenhum recurso, inimigo ou resultado econômico é regenerado pelo renderer.
9. No navegador, teste1280×720,1920×1080 e modo responsivo390px; câmera mantém escala1 e muda a área visível, sem reduzir todo o mundo até ficar ilegível.

Os personagens seguem diretamente a referência de cabeça quadrada e roupas simples.9:16 aplica-se apenas à imagem de referência, conforme decisão do usuário.

Renderização automática: GPU real usa WebGL; SwiftShader/llvmpipe/software ou ausência de WebGL usa Canvas. Para diagnosticar manualmente: `http://localhost:8080/?renderer=canvas` ou `?renderer=webgl`. Efeitos respeitam a preferência do sistema de movimento reduzido. Não são necessárias dependências gráficas adicionais.

## Frontend fora do Docker

Backend Docker deve estar ativo em8000. Em outro PowerShell:

```powershell
cd "C:\Users\pcnov\OneDrive\Documentos\dev\Dungeon-game\frontend"
npm ci
npm run dev -- --host 127.0.0.1 --port 5173
```

Abra5173 (admin5173/admin). Vite encaminha `/api`/WebSocket para127.0.0.1:8000. Para verificações estáticas, depois de encerrar o dev com Ctrl+C:

```powershell
npm test
npm run build
```

## Backend completo e Chromium em banco descartável

Execute este bloco em um **novo PowerShell de testes**, na raiz do repositório. Usa projeto Docker separado, porta55439, sem acessar `tower_data`. Python3.12 e Node22 são usados pelo projeto. Os fixtures backend limpam **somente este banco de teste**; nunca aponte DATABASE_URL para o operacional.

```powershell
cd "C:\Users\pcnov\OneDrive\Documentos\dev\Dungeon-game"
docker compose -p dungeon-visual-tests -f infrastructure/compose.visual-test.yml up -d --wait
if ($LASTEXITCODE -ne 0) { throw "Servidor de testes indisponível." }
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r backend/requirements-dev.txt
$env:DATABASE_URL = "postgresql+psycopg://tower:visual-test-only@localhost:55439/visual_test"
$env:TOWER_TEST_DATABASE = "1"
$env:PYTHONPATH = (Resolve-Path backend).Path
Push-Location backend
& ..\.venv\Scripts\python.exe -m alembic upgrade head
if ($LASTEXITCODE -ne 0) { Pop-Location; throw "Migração de teste falhou." }
& ..\.venv\Scripts\python.exe -m alembic check
Pop-Location
.\.venv\Scripts\python.exe -m pytest backend/tests -q

Push-Location frontend
npm ci
npx playwright install chromium
npm test
npm run build
Pop-Location
# Cada suite abaixo cria OUTRO banco UUID; não reseta o banco de origem.
.\.venv\Scripts\python.exe scripts/test_visual_stack.py --suite visual
.\.venv\Scripts\python.exe scripts/test_visual_stack.py --suite smoke
.\.venv\Scripts\python.exe scripts/test_visual_stack.py --suite npc-economy
.\.venv\Scripts\python.exe scripts/test_visual_stack.py --suite encounters
# Imagens/performance: artifacts/art-refinement/
docker compose -p dungeon-visual-tests -f infrastructure/compose.visual-test.yml stop
```

O runner possui tratamento de subprocessos Windows/Linux, mas sua execução automatizada nesta entrega ocorreu no Linux/Chromium. A execução desses comandos no Windows físico permanece validação local do operador. Para imagens originais, opcionalmente instale `scripts/requirements-art.txt` e execute `python scripts/build_pixel_assets.py`.

## Encerrar com segurança

```powershell
docker compose stop
```

Não usar exclusão de volumes, reset/clean, não apagar `.env`/banco e não executar testes destrutivos no volume operacional. Godot Windows/Android continuam congelados; nenhum APK/EXE novo é necessário.
