# Atualizar e executar a loja/recuperação no Windows PowerShell

Branch: `feature/guild-shop-recovery-ux-0.9`. Preserva a economia operacional existente. **Não repetir cutover nem rebalanceamento inicial** por causa desta atualização. Os preços administrados continuam valendo.

Requer Docker Desktop Linux e Git. Execute os blocos na ordem. Se `git status` mostrar alterações locais, preserve-as antes de trocar de branch; não use reset/clean. `.env` existente é mantido. Se for um ambiente novo, configure `.env.example` em `.env` antes de iniciar; não sobrescreva o arquivo existente.

```powershell
cd "C:\Users\pcnov\OneDrive\Documentos\dev\Dungeon-game"
git status
git fetch origin
git switch feature/guild-shop-recovery-ux-0.9
git pull --ff-only origin feature/guild-shop-recovery-ux-0.9
```

Pare somente escritores da aplicação, mantendo volume/banco. O backup binário usa arquivo no container e compose cp; funciona também no Windows PowerShell antigo.

```powershell
docker compose stop backend discord
docker compose up -d db
$uxBackupName = "before-guild-ux-" + (Get-Date -Format "yyyyMMdd-HHmmss") + "-" + ([guid]::NewGuid().ToString("N").Substring(0,8)) + ".dump"
New-Item -ItemType Directory -Path .\backups -Force | Out-Null
docker compose exec -T db pg_dump -U tower -d tower -Fc -f "/tmp/$uxBackupName"
if ($LASTEXITCODE -ne 0) { throw "Backup falhou; interrompa a atualização." }
docker compose cp "db:/tmp/$uxBackupName" ".\backups\$uxBackupName"
if ($LASTEXITCODE -ne 0) { throw "Cópia do backup falhou; interrompa a atualização." }

docker compose up -d --build
if ($LASTEXITCODE -ne 0) { throw "Inicialização falhou; examine os logs antes de continuar." }
docker compose ps
docker compose logs --tail=80 backend

docker compose exec -T backend alembic current
docker compose exec -T backend alembic check
docker compose exec -T backend python -m app.guild_cli inspect
docker compose exec -T backend python -m app.guild_cli audit
```

Startup executa `alembic upgrade head` e seed idempotente. Head esperado **e06a9c24f8bd**; check sem operações pendentes e audit com `gap_mg=0`, sem divergências de ledger/metadados. Se a migration recusar NPC personalizado/combate inesperado na sala antiga, interrompa e revise o conflito; não apague a sala nem ignore a validação. Dump deve ficar privado e fora do Git.

Abrir:

```powershell
Start-Process "http://localhost:8080"
Start-Process "http://localhost:8080/admin"
```

Jogador: vá à recepção da Guilda e abra **Comércio**. Busca filtra compra/venda. TUDO soma itens vendáveis; MÁXIMO usa caixa/moedas/capacidade reais. Revise a confirmação integrada antes de pagar. Não há troco automático.

ADM: Administração do Rei → Guilda. Justificativa fica em cada operação, mínimo10 caracteres. Edite um ou vários preços; use **Salvar este item** ou **Revisar alterações → Confirmar todas**. Atualize rascunhos desatualizados, sem reaproveitar preço antigo. Nenhuma conta ADM padrão foi criada.

Recuperação: explore o canto inferior esquerdo da vila; aproxime-se da figura encapuzada na barraca e interaja. Custo200% e propriedade continuam iguais. A Guilda não possui mais porta de recuperação.

Parar com segurança:

```powershell
docker compose stop
```

Não apague volumes, `.env` ou banco. Não execute pytest contra esse volume operacional. Nenhum APK/EXE precisa ser gerado.
