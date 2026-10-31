# Aplicação operacional e execução local — economia física da Guilda 0.9

Branch publicada desta etapa: `feature/lunar-physical-denominations-guild-commerce-0.9`, baseada em `feature/lunar-variable-nuggets-royal-admin-0.9` (43a69ca).

O usuário informa que o cutover Lunar principal **já está ativo no ambiente operacional dele**. Esta atualização não o refaz. Migração de schema e rebalanceamento são operações diferentes: o startup aplica schema/seed idempotente, mas **não troca moedas nem rebalanceia a Guilda**. O agente validou somente bancos descartáveis e uma cópia privada; os comandos abaixo são para execução manual pelo operador.

## Atualizar com backup no Windows PowerShell

Requer Git e Docker Desktop com engine Linux. Preserve alterações locais antes de trocar de branch. `.env` existente é mantido. Não coloque dumps/credenciais no Git. O backup usa arquivo binário dentro do container e `compose cp`, evitando corrupção por redirecionamento binário do PowerShell antigo.

```powershell
cd "C:\Users\pcnov\OneDrive\Documentos\dev\Dungeon-game"
git status
git fetch origin
git switch feature/lunar-physical-denominations-guild-commerce-0.9
git pull --ff-only origin feature/lunar-physical-denominations-guild-commerce-0.9

if (!(Test-Path .env)) {
    Copy-Item .env.example .env
}

# Iniciar apenas o PostgreSQL, sem atualizar o backend antes do backup.
docker compose up -d db
$guildBackupName = "before-physical-" + (Get-Date -Format "yyyyMMdd-HHmmss") + "-" + ([guid]::NewGuid().ToString("N").Substring(0,8)) + ".dump"
New-Item -ItemType Directory -Path .\backups -Force | Out-Null
docker compose exec -T db pg_dump -U tower -d tower -Fc -f "/tmp/$guildBackupName"
if ($LASTEXITCODE -ne 0) { throw "Backup falhou; interrompa a atualização." }
docker compose cp "db:/tmp/$guildBackupName" ".\backups\$guildBackupName"
if ($LASTEXITCODE -ne 0) { throw "Cópia do backup falhou; interrompa a atualização." }

# Atualizar os serviços mantendo o volume existente.
docker compose up -d --build
docker compose ps

# Startup já aplica upgrade; repetir estes comandos é idempotente.
docker compose exec -T backend alembic upgrade head
docker compose exec -T backend alembic current
docker compose exec -T backend alembic check
```

Head esperado: **d91e2ab604c7**. Migração aditiva cria políticas de preço, histórico e recibos, e permite preço zero no registro de custódia NPC. Não altera holdings, lotes, Supply, cutover ou ledger existente. Não cria mercadoria.

Web: **http://localhost:8080**. Administração: **http://localhost:8080/admin**. API/documentação: **http://localhost:8000/docs**. Portas da stack são publicadas no loopback por padrão.

## Inspecionar caixa e preços reais

```powershell
docker compose exec -T backend python -m app.guild_cli inspect
docker compose exec -T backend python -m app.guild_cli audit
```

`inspect` apresenta cutover_active, caixa real, quantidades por denominação, percentuais por massa, proposta calculada sobre o total atual, políticas por item e rates/flags do minério. Confirme `cutover_active=true`. Se não for true, pare e investigue se está usando o `.env`/volume esperado; esta entrega não manda refazer a conversão.

Não há usuário/senha padrão. Use uma conta administrativa existente com **economy.manage**. A CLI local é ferramenta do operador do servidor e valida o papel dessa conta; não é acesso remoto sem autenticação. Se precisar conceder/revogar papéis explicitamente, siga [ADMINISTRATION.md](../ADMINISTRATION.md); o personagem não recebe dinheiro por ser administrador.

## Prévia, fingerprint e aplicação inicial V1

```powershell
$guildAdmin = Read-Host "Nome da sua conta ADM existente com economy.manage"

$guildPreview = docker compose exec -T backend python -m app.guild_cli preview --username "$guildAdmin" --reason "Rebalanceamento inicial auditado do caixa físico da Guilda" | ConvertFrom-Json
if ($LASTEXITCODE -ne 0) { throw "Prévia recusada; não aplique nada." }

# Revise composição atual, total, proposta, diferenças, meta e fingerprint.
$guildPreview.before | ConvertTo-Json -Depth 20
$guildPreview.before.fingerprint

# Execute somente depois de revisar a prévia acima.
docker compose exec -T backend python -m app.guild_cli apply --username "$guildAdmin" --operation-id "$($guildPreview.id)" --fingerprint "$($guildPreview.before.fingerprint)" --confirmation-token "$($guildPreview.confirmation_token)" --confirm
if ($LASTEXITCODE -ne 0) { throw "Aplicação recusada; gere nova prévia e investigue a causa." }

docker compose exec -T backend python -m app.guild_cli inspect
docker compose exec -T backend python -m app.guild_cli audit
```

A prévia expira em cinco minutos. Mudança no caixa causa **STALE_PREVIEW**; gere outra prévia, sem reaproveitar números antigos. O apply confere fingerprint, token, ator/permissão, mutex e estado transacional. Não edite o objeto JSON para mudar a proposta.

A operação inicial tem chave persistente **GUILD_DENOMINATION_REBALANCE_V1**. Repetição não troca o caixa novamente, mesmo após pagamentos futuros; a prévia informa ALREADY_REBALANCED e o ledger não recebe outro efeito V1. Se o caixa ainda tiver **19.498.000 mg**, a proposta deve ser **1365 grandes / 780 médias / 1948 pequenas**. Se mudou, a ferramenta calcula outra composição sobre o valor real.

Para uma **nova decisão manual futura**, use a mesma sequência de preview/apply, acrescentando `--manual` somente ao comando `preview`. Isso cria outra operação auditada com UUID próprio, não altera a chave V1 nem ativa controle automático. A meta continua 70/20/10 por valor/massa, não por número de peças.

## Preços, estoque e exchange na Web

Em Administração do Rei → Guilda, consulte as seções Caixa, Rebalanceamento, Trocar denominações, Preços, Estoque, Histórico de preços e Comércio.

- **Editar preço**: compra e venda por unidade/peça são independentes. Flags independentes; revisão, motivo, antes/depois e recibo persistentes.
- **Preço zero ativo**: exige autorização consciente de gratuidade. Não significa disabled. Compra acima da venda mostra POSSIBLE_ARBITRAGE e exige confirmação consciente, sem impor margem automática.
- **Minério**: buy rate inicial800 milliunits/g preservado. Sell rate inicial0 e sell_enabled=false, sem oferta comercial inventada. Configure ambos os rates/flags de forma explícita. Uma pepita é vendida inteira; split deve ser outra operação.
- **Estoque**: editar preço não cria nem repõe mercadoria. Custódia Item/NPCStock e LunarMineralLot é física/finita. Entrada/transferência de estoque usa a ação material separada; item protegido/equipado continua inelegível.
- **Troca de denominações**: informe conta, inputs e outputs de mesma massa, razão, prévia e confirmação. O caixa precisa possuir os inputs exatos. A troca nunca é chamada escondida por um pagamento.

Confira preços persistidos novamente por `python -m app.guild_cli inspect`, ou pela tabela/histórico na Web. Nenhuma produção/reposição autônoma NPC foi implementada.

## Logs e parada segura

```powershell
docker compose logs -f
```

Ctrl+C encerra o acompanhamento. Para parar os serviços mantendo o volume:

```powershell
docker compose down
```

Discord remains read-only. Discord cannot control the character. Windows/Android FROZEN; APK e Windows build NOT REQUIRED; Godot source PRESERVED.
