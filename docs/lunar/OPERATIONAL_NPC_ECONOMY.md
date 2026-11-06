# Atualizar e validar no Windows PowerShell — economia NPC

Branch `feature/autonomous-npc-economy-0.9`, base UX66e88e5. Migração7167b684d5f7. Preserve `.env`, volumes, contas, inventários e histórico. O cutover Lunar informado ativo pelo usuário **não deve ser repetido**; esta atualização não manda rebalancear a Guilda novamente.

## Atualização com backup

Requer Git e Docker Desktop Linux. Se git status mostrar trabalho local, preserve-o antes da troca; não use reset/clean.

```powershell
cd "C:\Users\pcnov\OneDrive\Documentos\dev\Dungeon-game"
git status
if (git status --porcelain) { throw "Preserve as alterações locais antes de continuar." }
git fetch origin
if ($LASTEXITCODE -ne 0) { throw "Fetch falhou; interrompa." }
git switch feature/autonomous-npc-economy-0.9
if ($LASTEXITCODE -ne 0) { throw "Troca de branch falhou; não execute pull na branch anterior." }
git pull --ff-only origin feature/autonomous-npc-economy-0.9
if ($LASTEXITCODE -ne 0) { throw "Atualização Git falhou; interrompa." }

# Parar escritores antes do backup; manter volume/banco.
docker compose stop backend discord
docker compose up -d --wait db
$npcBackupName = "before-npc-" + (Get-Date -Format "yyyyMMdd-HHmmss") + "-" + ([guid]::NewGuid().ToString("N").Substring(0,8)) + ".dump"
New-Item -ItemType Directory -Path .\backups -Force | Out-Null
docker compose exec -T db pg_dump -U tower -d tower -Fc -f "/tmp/$npcBackupName"
if ($LASTEXITCODE -ne 0) { throw "Backup falhou; interrompa a atualização." }
docker compose cp "db:/tmp/$npcBackupName" ".\backups\$npcBackupName"
if ($LASTEXITCODE -ne 0) { throw "Cópia do backup falhou; interrompa a atualização." }

docker compose up -d --build --wait
if ($LASTEXITCODE -ne 0) { throw "Inicialização falhou; examine os logs." }
docker compose ps
docker compose logs --tail=80 backend
docker compose exec -T backend alembic current
docker compose exec -T backend alembic check
docker compose exec -T backend python -m app.guild_cli inspect
docker compose exec -T backend python -m app.guild_cli audit

Start-Process "http://localhost:8080"
Start-Process "http://localhost:8080/admin"
```

Startup executa upgrade e seed idempotente. Head esperado7167b684d5f7; check sem operações pendentes; audit gap0, sem divergências de ledger/metadados. Dump privado fica fora do Git. Não use pytest no volume operacional.

## Validar os estoques e a produção

1. Entre na Central com sua conta existente, permissão economy.read/manage; não há administrador/senha padrão.
2. Abra Economia dos NPCs. Perfis novos começam com os estoques autorizados: Alquimista1 poção de cada+7/7 matérias; Ferreiro1 peça de cada+90 minérios; Comerciante vazio. Caixas novos zero.
3. Com produção ativa, após o próximo ciclo(default30s), Alquimista passa a2 poções de cada, materiais0; Ferreiro a2 peças de cada, Minérios/Lingotes0. O histórico mostra3 receitas alquímicas e fundição18 seguida das6 peças. Se abrir a tela depois do primeiro ciclo, essa produção já terá ocorrido; não é um novo seed.
4. Feche a ADM. A produção continua no servidor. Pausar produção mantém os estoques/caixa existentes.

## Abastecer o Comerciante e financiar os produtores

O Comerciante não recebe estoque nem dinheiro artificial.

- **Transferência material administrativa:** em Economia dos NPCs, escolha origem Guilda, destinatário Comerciante, material realmente existente e quantidade que caiba. Informe justificativa≥10, revise, confirme. A origem perde exatamente o que o destinatário recebe. Esta é uma capitalização explícita, sem pagamento implícito.
- **Reposição comercial automática:** configure na Guilda as vendas dos3 materiais/base por unidade e flags. Financie o Comerciante com transferência real do Tesouro/Guilda, e habilite suas compras. Abaixo do ponto de reposição ele compra um pedido válido da Guilda pagando base×quantidade+margem da Guilda.
- **Produtores:** financie seus caixas com moedas existentes e habilite compras. Abaixo do ponto, eles compram do Comerciante. Inicialmente cada pedido tem10 unidades; Comerciante usa lote10/passo10 e margem1.

Para financiar pelo módulo NPC: escolha conta financiadora, caixa destinatário e valor; justificativa, prévia e confirmação. Não há emissão automática nem crédito sem origem.

**Troco importa:** um caixa com valor suficiente pode não formar o pagamento exato. Use a troca administrativa explícita já existente em Administração do Rei → Guilda → Trocar denominações, com conta `npc:merchant`, `npc:alchemist` ou `npc:blacksmith`. Informe peças de entrada/saída de mesma massa, motivo, prévia e confirmação. Isso é uma decisão manual separada; nenhuma compra quebra moedas escondida.

Estados “Fornecedor sem estoque”, “Caixa insuficiente”, “Faltam moedas exatas” ou “Capacidade insuficiente” são esperas legítimas. Não corrija resetando banco/carteiras. Confira estoque, flags, lotes, capacidade e composição física.

## Validar preços, lotes e sincronização

1. Configure referência de um material pela compra da Guilda. Exemplo Folha=2; Comerciante lote10/margem1 mostra base20+1=21.
2. Venda da Guilda é independente: base configurada×quantidade+uma margem por operação. Uma base maior que a referência do Comerciante pode gerar prejuízo ao intermediário; não há correção automática de lucro.
3. Em Configurar Alquimista, altere fator1,25→1,35. A prévia mostra antes/depois e preços afetados. Confirme; jogo/ADM recebem a mesma revisão.
4. Altere preço do Minério: Lingote e todas as peças acompanham. Não precisa editar receitas nem frontend.
5. Altere lote/passo do Comerciante para20. Ajuste capacidades/pedidos dos compradores quando necessário: um lote20 não cabe em capacidade20 se ainda houver7 unidades. O sistema aguarda em vez de ultrapassar limite.
6. Abra compra no jogo, altere preço/margem na ADM, tente confirmar a cotação antiga. Ela deve ser recusada e exigir revisão dos novos valores, sem débito/material parcial.

Toda configuração exige revisão original, justificativa, permissão, prévia/confirm e auditoria. Se outro administrador ou uma mudança relevante invalidar a prévia, atualize o rascunho e revise; não force o conflito.

## Validar o jogo

Na vila, abra **Lojas da vila**. Escolha Comerciante, Alquimista ou Ferreiro e **Ir até**; clique/toque/E também funcionam no NPC. Compra efetiva exige aproximação. A Guilda conserva seu Comércio, TUDO/MÁXIMO e recuperação continua na barraca sudoeste.

Comerciante vende lotes válidos. Alquimista vende somente poções disponíveis. Ferreiro vende peças independentes; compre uma de cada e equipe no Inventário. Equipe outra arma e confirme que só substitui a arma, mantendo as5 peças de armadura. Poções podem ser adquiridas/guardadas; seus efeitos de uso e novos bônus de combate não foram definidos pelo documento desta etapa.

Teste390px: cards em uma coluna, controles de toque, total/cancelamento/confirmação sem popup nativo, sem overflow da página.

## Validar persistência

Anote estoques/caixas, fatores, margens, lotes, preços/revisões e equipamento do personagem. Reinicie sem apagar volumes:

```powershell
docker compose restart backend
docker compose logs --tail=60 backend
docker compose exec -T backend python -m app.guild_cli audit
```

Dados permanecem; mudanças posteriores só podem vir de compras/produção reais. Seed não volta a adicionar7/7/90 ou produtos. Para observar sem movimentos, pause produção/compras dos NPCs antes do reinício; reative com prévia/justificativa depois.

Parar com segurança: `docker compose stop`. Nunca apagar volumes/ledger, `.env`, banco ou inventários para instalar esta evolução. Windows/Android nativos permanecem congelados; não gerar APK/EXE.
