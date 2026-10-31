# Tesouro Real e Administração do Rei — 0.9

## Continuação: caixa físico, preços e comércio completos

Exchange auditado, rebalanceamento manual 70/20/10 e tabela de preços/histórico/estoque/comércio integrados à área Guilda. Pagamentos deixam de normalizar contas; exigem moedas reais e valor exato. Compra/venda de itens e minério com rates independentes. [Novo manual operacional/Windows](OPERATIONAL_GUILD_COMMERCE.md), que substitui a branch/comandos desta entrega histórica. Cutover operacional informado ativo pelo usuário, sem repetição automática.


Implementado na branch `feature/lunar-variable-nuggets-royal-admin-0.9`. A economia continua única: `LunarHolding` guarda moedas, `LunarMineralLot` guarda minério individual e `LunarDebt` representa obrigação, sem moeda negativa. O Banco Central antigo permanece somente como compatibilidade/histórico, sem ser o Tesouro Real.

## Web e permissões

Abra `http://localhost:8080/admin` e escolha **Administração do Rei**. As dez áreas são Visão geral, Minério, Moedas, Cunhagem, Jogadores, Guilda, Tesouro, Auditoria, Configuração e Histórico administrativo.

- Visão geral/Auditoria: gênese, descoberta, injeção administrativa, minério econômico, moedas, destruído, dívida/recebível, potencial procedural e gap em mg. Potencial não integra a oferta.
- Minério: filtros por conta/tipo/estado/origem/ocorrência/expedição/faixa de peso; paginação de 100; identidade, peso, pai, data, proprietário e linhagem completa. Ocorrências mostram disponível/coletada/expirada e coletor/timestamp.
- Moedas: pequenas/médias/grandes por conta e localização, massa, dívida e inventário. Contas incluem jogadores, Guilda, NPCs, Tesouro e escrows. A conta `central_bank` é marcada LEGACY/COMPATIBILITY.
- Jogadores/Guilda/Tesouro: composição física, itens/estoque, lotes e obrigações. Clique na conta para detalhes reais. Nenhuma compra, produção ou política financeira automática.
- Cunhagem: escolha quantidades das três denominações e, opcionalmente, IDs de minério. Vazio seleciona FIFO. A prévia mostra consumo/resíduo por pepita e massa exata. Somente minério do Tesouro pode ser cunhado.
- Configuração: parâmetros JSON estritos, todos pelo mesmo fluxo administrativo.
- Histórico: operações, ator, razão, antes/depois e recibos, além do ledger Lunar append-only.

Leituras exigem `economy.read`; `royal.mint`, `royal.transfer_lot`, `royal.transfer_coins`, `royal.burn`, `royal.injection` e `economy.configure` exigem `economy.manage`. Observer consulta; economist/owner podem administrar a economia. Jogador normal e chave Discord são recusados.

Cada mutação usa `/admin/operations/preview` e `/admin/operations/{UUID}/confirm`: permissão no backend, razão de 10–500 caracteres, prévia vinculada ao estado, confirmação explícita/token, mutex financeiro, transação, auditoria e recibo persistente. Estado alterado invalida a prévia; mesmo UUID não executa duas vezes. Nenhuma conta/senha administrativa é criada automaticamente.

## Operações físicas

| Ação | Efeito |
|---|---|
| Cunhar | Consome minério real do Tesouro e cria moedas de mesma massa no Tesouro; não aumenta oferta |
| Transferir/confiscar pepita | Muda proprietário do mesmo ID; preserva peso, origem e linhagem; sem oferta nova |
| Transferir moedas | Origem real → destino real, incluindo fundos da Guilda; mesma massa |
| DESTRUIR / RETIRAR DA ECONOMIA | `ADMIN_BURN`: minério e/ou moedas deixam de existir; contador destruído aumenta |
| INJEÇÃO EXCEPCIONAL DE MASSA | `ADMIN_INJECTION`: minério e/ou moedas novos, explicitamente separados de descoberta/gênese |

Em mint parcial, 684 g → consumo de 437 g + resíduo de 247 g: pai fica SPLIT, filho de 437 g fica MINTED e filho de 247 g fica HELD. Todo o caminho permanece consultável. Transferência não cria novo lote; split, burn parcial e mint parcial criam filhos com soma exata.

Burn/injection exigem também `royal_admin_extraordinary_controls_enabled=true` e a palavra exata **DESTRUIR** ou **INJETAR**, além da confirmação normal. Default inicial da flag: true, conforme escopo aprovado; configurá-la como false oculta/desabilita os controles e o backend rejeita execução, inclusive de prévias anteriores. Injeção não é descoberta legítima nem GENESIS_BACKING: aparece destacada na auditoria e altera a oferta explicitamente. Não existe endpoint público de spawn nem emissão automática do rei.

## Execução local no Windows PowerShell

Requer Git e Docker Desktop com engine Linux. Preserve alterações locais antes de trocar de branch. A migração aplica-se ao banco indicado no `.env`; faça backup dos dados importantes. Atualização não executa o cutover administrativo automaticamente.

```powershell
cd "C:\Users\pcnov\OneDrive\Documentos\dev\Dungeon-game"
git status
git fetch origin
git switch feature/lunar-variable-nuggets-royal-admin-0.9
git pull --ff-only origin feature/lunar-variable-nuggets-royal-admin-0.9
if (!(Test-Path .env)) {
    Copy-Item .env.example .env
}
docker compose up -d --build
docker compose ps
docker compose exec backend alembic current
docker compose exec backend alembic check
```

Web: **http://localhost:8080**. Administração: **http://localhost:8080/admin**. API: **http://localhost:8000/docs**. Compose publica portas no loopback; banco não é exposto como serviço público. O backend aplica `alembic upgrade head` e seed idempotente ao iniciar; revisão desta entrega: **ca343e37b4ca**.

Não há credencial padrão. Cadastre sua conta pela Web. Se o usuário cadastrado for `pcnov`, conceda papel somente por decisão explícita do operador:

```powershell
docker compose exec backend python -m app.admin_cli pcnov owner --reason "Autorização explícita para administrar o ambiente privado"
```

Substitua `pcnov` pelo usuário realmente cadastrado. O comando não cria senha/conta nem dá recursos ao personagem. A entrada ADM usa essa conta com sessão separada. Para revogar, use `revoke` no lugar de `owner`.

Instalação com saldos ainda legados: use backup, prévia/dry-run/fingerprint e confirmação do módulo Cutover Lunar antes das operações Reais. O upgrade não inventa lastro ou ativa conversão operacional por conta própria. Cutover implementado e validado em cópia privada; ativação no ambiente operacional real ainda não executada.

Logs e parada com volume preservado:

```powershell
docker compose logs -f
# Ctrl+C encerra somente o acompanhamento dos logs.
docker compose down
```

Windows: FROZEN. Android: FROZEN. APK: NOT REQUIRED. Windows build: NOT REQUIRED. Godot source: PRESERVED. Nenhum build nativo novo foi gerado.
