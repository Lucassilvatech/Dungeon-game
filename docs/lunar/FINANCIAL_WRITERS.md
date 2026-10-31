# Inventário financeiro anterior ao cutover

## Consolidação física atual

`finance.move` agora seleciona peças existentes e preserva cada denominação, sem compose. `compose` é LEGACY, exclusivamente do cutover histórico, que não é refeito. Novos writers reutilizam a mesma economia:

| Arquivo/função | Classificação | Origem/destino e efeito |
|---|---|---|
| finance.move/fee/settle_debt | WRITE / LUNAR | Transferência física; dívida/recebível separados, sem mint/troco escondido |
| lunar.exchange | WRITE / LUNAR | Troca explicitamente confirmada, massa0, inputs reais |
| guild_admin.apply | ADMIN / LUNAR | Exchange/rebalance manuais; preços/revisões/histórico não movimentam massa |
| guild_commerce.item_trade | WRITE / LUNAR | Moedas reais pagador→recebedor e Item/NPCStock na direção oposta; atomicidade/receipt |
| guild_commerce.mineral_trade | WRITE / LUNAR | Moedas reais e mesmo lote inteiro entre jogador/Guilda; sem massa nova |
| guild_cli | ADMIN / READ / WRITE | Inspect/audit ou workflow preview/fingerprint/confirm existente; não ativa cutover |
| simulate_guild_liquidity.py | TEST | Fixture isolada; nenhuma escrita operacional |

Rewards, contratos, leilões/escrows, recuperação e NPCs abaixo já convergem para finance.move/economy.ledger e passam a conservar denominações. [Regras e limitações físicas](PHYSICAL_DENOMINATIONS.md).

Base 13ae213; branch nova feature/lunar-cutover-economy-0.9 criada limpa a partir da 0.9 após status/log/fetch. Inventário registrado antes de executar cutover. Main preservada.

## Writers críticos e decisão de migração

| Arquivo/função | Tabelas | Origem → destino | Semântica atual | Migração |
|---|---|---|---|---|
| seed.seed | Treasury/CentralBank/Ledger | initial_supply → treasury | Cria gênese antiga na instalação; nunca repõe saldo existente | LEGACY, bloquear criação pós-cutover |
| economy.credit_player_gold | Character/Ledger | fonte explícita → personagem | Crédito e abatimento de dívida assinada | WRITE, facade Lunar + obrigação separada |
| economy.reserve_gold | Character/AuctionBid/Ledger | player → auction | Débito em escrow | WRITE, transferência física |
| economy.medical_fee | Character/Treasury/Ledger | player → treasury + dívida | Hoje credita também parcela financiada (incompatível) | WRITE/LEGACY, receber só pago + recebível |
| game.pay | Battle/Treasury/Character | treasury → player | Recompensas com orçamento real | WRITE, preservar fonte Tesouro; sem mint |
| auctions.bid/settle_locked | Auction/Item/Bid/Treasury | player ↔ escrow → destino | Custódia, diferença de lance próprio, reembolso, entrega | WRITE, metadata continua, fundos exclusivamente Lunar |
| admin_service.cancel_auction | Auction/Item | escrow → bidder | Reembolso/custódia | ADMIN, facade crédito |
| contracts.publish/claim/cancel_publication | GuildContract/CharacterContract | treasury → contract escrow → player/treasury | Reserva total, direito concluído preservado | WRITE, escrow físico; reserved é metadata reconciliada |
| recovery.recover | RecoveryItem/Item/Treasury/Character | player → treasury | Pagamento legado ao Tesouro | WRITE, conta NPC recovery; não burn |
| debt.collect | DebtCollection/Item/Auction | treasury → player | Compra financiada real e abatimento | WRITE, fonte real e dívida separada |
| admin_economy.execute/assign | Character/Treasury/CentralBank/Ledger | mint/burn/transfer | Mint sem lastro e burn legado | ADMIN, rejeitar emissão abstrata/burn comum após conversão; só transferir existente |
| sandbox | AdminTestCredit | saldo teste isolado | Não moeda oficial | ADMIN, preservar isolamento |
| lunar.post/mint/exchange/transfer | Lunar* | contas físicas/descoberta/gênese/destruição | Fundação validada, massa exata | LUNAR, reutilizar |

Não existe loja/comerciante com estoque físico na base. Criar somente infraestrutura de estoque finito com preços explícitos; nenhum estoque/preço final inventado. Guilda/NPC novos iniciam zerados. Leilões configurados com destino sink devem receber conta de custódia aposentada, não destruir material em gameplay comum. Preços/recompensas são unidades históricas de 1g (1.000mg) preservadas na API de compatibilidade.

Todos os testes atuais (backend/tests/test_*), especialmente helpers wallet, são TEST/LEGACY: podem construir fixtures por SQL em banco descartável. Testes pós-cutover devem financiar por transferência/gênese confirmada, nunca simular operacionalidade escrevendo Character.coins. UI/Discord apenas READ/DERIVED, precisam ler projeções Lunar após conversão. Nenhum writer de recompensa sem fonte foi encontrado: pendências de batalha pagam Tesouro e contratos pagam sua reserva. Políticas novas de drop/boss/echo estão fora desta etapa.

## Busca completa de funções com termos financeiros

Tabela gerada por AST e busca de todos os termos solicitados; linhas classificadas conservadoramente READ/DERIVED precisam ser revisadas ao integrar a facade. Campos de preço/maior lance são metadata, não carteiras. Funções sem atribuições diretas ainda podem chamar writers já classificados acima.

| Arquivo/linha | Função | Classificação | Evidência |
|---|---|---|---|
| admin.py:80 | operation_confirm | ADMIN, READ/DERIVED | from .auctions import mutex |
| admin.py:104 | starter_diagnostics | ADMIN, READ/DERIVED | select(m.Auction, m.Item); .join(m.Item, m.Item.id == m.Auction.item_id); .order_by(m.Auction.id); "auction": data(a), |
| admin.py:134 | view | ADMIN, READ/DERIVED | if module == "contracts":; from .contracts import payload; select(m.GuildContract); .order_by(m.GuildContract.id.desc()) |
| admin_economy.py:17 | metrics | ADMIN, READ/DERIVED | treasury = db.get(Treasury, 1).balance; bank = db.get(CentralBank, 1).balance; select(Auction).where(Auction.status.in_(["OPEN", "CLOSED"])); entries = db.scalars(select(Ledger)).all() |
| admin_economy.py:127 | account | ADMIN, READ/DERIVED | if name == "treasury":; return db.get(Treasury, 1) |
| admin_economy.py:139 | balance | ADMIN, READ/DERIVED | def balance(row):; return row.coins if isinstance(row, Character) else row.balance |
| admin_economy.py:143 | assign | ADMIN, WRITE | row.coins = value; row.balance = value |
| admin_economy.py:150 | execute | ADMIN, WRITE | credit_player_gold(db, dst, n, "mint", f"admin:{op.id}"); assign(dst, balance(dst) + n); ledger(db, f"admin:{op.id}", "mint", dest, n); if balance(src) < n: |
| admin_service.py:90 | data | ADMIN, READ/DERIVED | "coins",; "balance",; "reward_amount",; "reward", |
| admin_service.py:136 | lock_resources | ADMIN, READ/DERIVED | # Metadata is re-read after locks. Auction/admin mutex serializes custody changes.; auction = None; "auctions.cancel",; "auctions.hide", |
| admin_service.py:214 | describe | ADMIN, READ/DERIVED | if action == "contracts.publish":; from .contracts import validate, payload; if target != "guild":; fail("Publicação exige a Guilda do primeiro andar", 422) |
| admin_service.py:439 | operation_payload | ADMIN, READ/DERIVED | if op.action == "contracts.publish":; projected["treasury"] = str(; int(projected["treasury"]) - int(op.before["reservation"]); projected["contract_reserve"] = op.before["reservation"] |
| admin_service.py:512 | cancel_auction | ADMIN, WRITE | from .economy import credit_player_gold; a = get(db, m.Auction, op.target); or item.location != "auction"; bidder = get(db, m.Character, a.highest_bidder_id) |
| admin_service.py:540 | apply | ADMIN, WRITE | if action == "contracts.publish":; from .contracts import publish; elif action == "contracts.cancel":; from .contracts import cancel_publication |
| attributes.py:10 | gain_levels | LEGACY, READ/DERIVED | debt=c.attribute_point_debt, |
| attributes.py:51 | penalize_levels | LEGACY, READ/DERIVED | c.level = max(MIN_LEVEL, c.level - DEBT_LEVEL_PENALTY) |
| auctions.py:14 | mutex | LEGACY, READ/DERIVED | # All bids and settlements share this transaction lock, including background sweeps. |
| auctions.py:20 | create_from_death | LEGACY, READ/DERIVED | item.location = "auction"; auction = Auction(; + timedelta(hours=runtime_setting(db, "auction_duration_hours")),; proceeds_destination=runtime_setting(db, "auction_proceeds_destination"), |
| auctions.py:114 | settle_locked | LEGACY, WRITE | """Caller holds auction mutex; lock winner before item/Treasury, never the reverse."""; "UNSOLD"  # Archive custody; no destruction, relisting or NPC purchase.; if item.owner is not None or item.location != "auction":; raise RuntimeError("Auction custody invariant violated") |
| auctions.py:172 | settle_due | LEGACY, READ/DERIVED | select(Auction); .join(Item, Item.id == Auction.item_id); Auction.status == "OPEN",; Auction.ends_at <= utc_now(), |
| auctions.py:206 | listing | LEGACY, READ/DERIVED | select(Auction); .where(Auction.hidden == False, Auction.archived == False); .order_by(Auction.id.desc()) |
| auctions.py:220 | bid | LEGACY, WRITE | def bid(db, account, auction_id, amount, request_id):; select(AuctionBid).where(; AuctionBid.bidder_id == c.id, AuctionBid.request_id == request_id; if previous.auction_id != auction_id or previous.amount != amount: |
| auctions.py:276 | settle | LEGACY, READ/DERIVED | def settle(db, auction_id):; a = db.scalar(select(Auction).where(Auction.id == auction_id).with_for_update()) |
| auctions.py:286 | sweeper | LEGACY, READ/DERIVED | "Auction sweep failed; transaction rolled back; retrying"; await asyncio.sleep(settings.auction_sweep_seconds) |
| auctions.py:316 | detail | LEGACY, READ/DERIVED | def detail(db, auction_id, administrative=False):; a = db.get(Auction, auction_id); "bids": [; bidder_id=b.bidder_id, |
| contracts.py:18 | validate | LEGACY, READ/DERIVED | reward = amount(p["reward"]); "reward": reward, |
| contracts.py:74 | publish | LEGACY, WRITE | budget = data["reward"] * data["slots"]; treasury = db.scalar(select(Treasury).where(Treasury.id == 1).with_for_update()); if treasury.balance < budget:; contract = GuildContract( |
| contracts.py:98 | definition | LEGACY, READ/DERIVED | query = select(GuildContract).where(GuildContract.id == id) |
| contracts.py:110 | payload | LEGACY, READ/DERIVED | "reward": str(row.reward),; "reserved": str(row.reserved),; "location_rule": "Aceitar, entregar e resgatar junto à recepcionista da Guilda, fora de combate.", |
| contracts.py:128 | listing | LEGACY, READ/DERIVED | select(GuildContract); .order_by(GuildContract.id.desc()); select(CharacterContract, GuildContract); .join(GuildContract, GuildContract.id == CharacterContract.contract_id) |
| contracts.py:166 | accept | LEGACY, READ/DERIVED | if old.contract_id != id:; CharacterContract.character_id == c.id, CharacterContract.contract_id == id; character_id=c.id, contract_id=d.id, request_id=request_id, progress=0; add(db, c, contracts_accepted=1) |
| contracts.py:223 | progress | LEGACY, READ/DERIVED | select(CharacterContract, GuildContract); .join(GuildContract, GuildContract.id == CharacterContract.contract_id); GuildContract.status == "OPEN",; GuildContract.kind == kind, |
| contracts.py:239 | owned | LEGACY, READ/DERIVED | return a, definition(db, a.contract_id, True) |
| contracts.py:252 | deliver | LEGACY, READ/DERIVED | key = f"contract-delivery:{c.id}:{request_id}"; add(db, c, contract_items_delivered=required); event(db, "CONTRACT_DELIVERED", c, key=key, acceptance_id=a.id, items=consumed) |
| contracts.py:310 | claim | LEGACY, WRITE | "paid": str(d.reward),; if a.status != "ACTIVE" or a.progress < d.required or d.reserved < d.reward:; d.reserved -= d.reward; credit_player_gold(db, c, d.reward, f"contract:{d.id}", f"contract-pay:{a.id}") |
| contracts.py:348 | cancel_personal | LEGACY, READ/DERIVED | db, "CONTRACT_CANCELLED", c, key=f"contract-cancel:{a.id}", acceptance_id=a.id |
| contracts.py:368 | cancellation_plan | LEGACY, READ/DERIVED | CharacterContract.contract_id == d.id, CharacterContract.status == "ACTIVE"; "retained": str(ready * d.reward),; "refund": str(d.reserved - ready * d.reward), |
| contracts.py:392 | cancel_publication | LEGACY, WRITE | treasury = db.scalar(select(Treasury).where(Treasury.id == 1).with_for_update()); treasury.balance += refund; d.reserved -= refund; ledger( |
| deaths.py:13 | resolve | LEGACY, WRITE | from .game import pending, reward_value; adjustments = [dict(battle_id=b.id, amount=reward_value(b)) for b in rows]; b.reward_amount = 0; fee = medical_fee( |
| debt.py:13 | select_units | LEGACY, READ/DERIVED | def select_units(rows, debt):; count = min(item.quantity, max(0, (debt - total + value - 1) // value)); if total >= debt:; if total >= debt: |
| debt.py:61 | collect | LEGACY, WRITE | debt = max(0, -c.coins); if debt < 1000 or c.debt_accrued < c.debt_next_collection:; rows, total = select_units(eligible(db, c), debt); treasury = db.scalar(select(Treasury).where(Treasury.id == 1).with_for_update()) |
| discord_client.py:10 | query | LEGACY, READ/DERIVED | reserved = int(; select(func.coalesce(func.sum(m.Auction.highest_bid), 0)).where(; m.Auction.highest_bidder_id == c.id,; m.Auction.status.in_(["OPEN", "CLOSED"]), |
| economy.py:13 | ledger | LEGACY, WRITE | def ledger(db, reference, source, destination, amount):; Ledger( |
| economy.py:21 | credit_player_gold | LEGACY, WRITE | def credit_player_gold(db, c, amount, source, reference):; raise ValueError("Credit must be nonnegative"); before = c.coins; c.coins += amount |
| economy.py:44 | reserve_gold | LEGACY, WRITE | def reserve_gold(db, c, amount, reference, auction_id):; if c.coins <= 0 or amount <= 0 or c.coins < amount:; c.coins -= amount; ledger(db, reference, f"character:{c.id}", f"auction:{auction_id}", amount) |
| economy.py:55 | medical_fee | LEGACY, WRITE | before = c.coins; after = max(-DEBT_LIMIT, before - assessed); c.coins = after; c.debt_accrued += max(0, -after) - max(0, -before) |
| expeditions.py:140 | preview | LEGACY, READ/DERIVED | from .game import fail, pending, reward_value, active; amounts = [(b.id, reward_value(b)) for b in rows]; reward_loss=total - total // 2, |
| expeditions.py:188 | flee | LEGACY, READ/DERIVED | from .game import fail, pending, reward_value, active; before = reward_value(b); b.reward_amount = after; message=f"Você fugiu da expedição. Recompensas perdidas: {result['reward_loss']}; pendentes restantes: {result['pending_after']};  |
| game.py:92 | snapshot | LEGACY, READ/DERIVED | from .models import Auction; reserved = db.scalar(; select(func.coalesce(func.sum(Auction.highest_bid), 0)).where(; Auction.highest_bidder_id == c.id, Auction.status.in_(["OPEN", "CLOSED"]) |
| game.py:196 | battle_data | LEGACY, READ/DERIVED | "reward_amount", |
| game.py:240 | interact | LEGACY, READ/DERIVED | if current(db, c).id == "auction_hall":; if current(db, c).id == "recovery_hall":; "message": "Recepcionista da Guilda: seus registros estão prontos para conferência.",; "rewards": reward_summary(db, c), |
| game.py:265 | rest | LEGACY, READ/DERIVED | if current(db, c).kind not in (RoomType.CITY, RoomType.GUILD):; fail("Descanse na cidade ou na Guilda") |
| game.py:292 | start_battle | LEGACY, READ/DERIVED | if room.kind in (RoomType.CITY, RoomType.GUILD):; fail("Cidade e Guilda são zonas seguras") |
| game.py:337 | action | LEGACY, READ/DERIVED | b.reward_amount = 0; b.reward_amount = (; b.reward_amount = (; from .contracts import progress |
| game.py:527 | receptionist | LEGACY, READ/DERIVED | if room.id != "guild" or not npc or distance((c.x, c.y), npc) > 1:; fail("Aproxime-se da recepcionista na Guilda") |
| game.py:545 | reward_value | LEGACY, READ/DERIVED | def reward_value(b):; b.reward_amount; if b.reward_amount is not None |
| game.py:553 | reward_summary | LEGACY, READ/DERIVED | def reward_summary(db, c):; return reward_summary_from(pending(db, c)) |
| game.py:557 | reward_summary_from | LEGACY, READ/DERIVED | def reward_summary_from(rows):; "total": sum(reward_value(b) for b in rows), |
| game.py:569 | pay | LEGACY, WRITE | total = sum(reward_value(b) for b in rows); treasury = db.scalar(select(Treasury).where(Treasury.id == 1).with_for_update()); if total < 0 or treasury.balance < total:; treasury.balance -= total |
| layouts.py:46 | generate | LEGACY, READ/DERIVED | else "interior" if kind in ("GUILD", "TRAINING") else THEMES[seed % 4]; npc=[17, 7] if kind == "GUILD" else None,; npc_name="Recepcionista da Guilda",; dict(x=7, y=3, width=6, height=4, name="Guilda"), |
| lunar.py:70 | balances | LUNAR, READ/DERIVED | def balances(db, id): |
| lunar.py:83 | post | LUNAR, READ/DERIVED | Replay is bound to all parameters. Failure is raised before modifying any balance.; holding = db.get(LunarHolding, (o, a)); before = holding.quantity if holding else 0; updates.append((holding, o, a, before + q)) |
| lunar.py:202 | mint | LUNAR, READ/DERIVED | def mint(db, id, nuggets, coins, key):; if not owner or owner.kind != "treasury":; for sign, values, kind in [(-1, nuggets, "nugget"), (1, coins, "coin")]: |
| lunar.py:250 | transfer | LUNAR, READ/DERIVED | def transfer(db, source, target, coins, key, kind="COIN_TRANSFER"):; for code, q in coins.items(): |
| lunar.py:266 | wallet | LUNAR, READ/DERIVED | held = balances(db, id) |
| lunar.py:285 | audit | LUNAR, READ/DERIVED | ledger_balances = defaultdict(int); ledger_balances[(r["account"], r["asset"])] += r["quantity"]; "difference": str(physical.get((o, a), 0) - ledger_balances.get((o, a), 0)),; for o, a in sorted(set(physical) / set(ledger_balances)) |
| lunar.py:343 | legacy_preview | LUNAR, READ/DERIVED | from .auctions import mutex as financial_mutex; db.scalar(select(m.Treasury).where(m.Treasury.id == 1).with_for_update()); f"player:{c.id}": max(c.coins, 0) for c in db.scalars(select(m.Character)); debts = { |
| main.py:28 | lifespan | LEGACY, READ/DERIVED | from .auctions import sweeper |
| main.py:165 | rewards | LEGACY, READ/DERIVED | def rewards(a=Depends(current_account), db=Depends(get_db)): |
| main.py:313 | guild_rewards | LEGACY, READ/DERIVED | def guild_rewards(a=Depends(current_account), db=Depends(get_db)):; return game.reward_summary(db, game.character(db, a)) |
| main.py:318 | guild_claim | LEGACY, READ/DERIVED | def guild_claim(a=Depends(current_account), db=Depends(get_db)): |
| main.py:404 | auctions | LEGACY, READ/DERIVED | def auctions(offset: int = 0, a=Depends(current_account), db=Depends(get_db)):; from .auctions import listing |
| main.py:415 | auction_bid | LEGACY, READ/DERIVED | def auction_bid(; auction_id: int, body: BidInput, a=Depends(current_account), db=Depends(get_db); from .auctions import bid; return bid(db, a, auction_id, int(body.amount), str(body.request_id)) |
| main.py:424 | settle_auction | LEGACY, READ/DERIVED | def settle_auction(auction_id: int, a=Depends(current_account), db=Depends(get_db)):; from .auctions import settle; return settle(db, auction_id) |
| main.py:453 | auction_details | LEGACY, READ/DERIVED | def auction_details(auction_id: int, a=Depends(current_account), db=Depends(get_db)):; from .auctions import detail; return detail(db, auction_id) |
| main.py:485 | recovery_items | LEGACY, READ/DERIVED | def recovery_items(a=Depends(current_account), db=Depends(get_db)):; from .recovery import listing |
| main.py:492 | recovery_item | LEGACY, READ/DERIVED | def recovery_item(; id: int, body: RecoveryConfirmation, a=Depends(current_account), db=Depends(get_db); from .recovery import recover |
| main.py:605 | contracts | LEGACY, READ/DERIVED | def contracts(offset: int = 0, a=Depends(current_account), db=Depends(get_db)):; from .contracts import listing |
| main.py:614 | contract_accept | LEGACY, READ/DERIVED | def contract_accept(; from .contracts import accept; from .auctions import mutex |
| main.py:625 | contract_deliver | LEGACY, READ/DERIVED | def contract_deliver(; from .contracts import deliver; from .auctions import mutex |
| main.py:636 | contract_claim | LEGACY, READ/DERIVED | def contract_claim(; from .contracts import claim; from .auctions import mutex |
| main.py:647 | contract_cancel | LEGACY, READ/DERIVED | def contract_cancel(; from .contracts import cancel_personal; from .auctions import mutex |
| main.py:688 | lunar_wallet | LEGACY, READ/DERIVED | "legacy_balance": str(c.coins),; "legacy_debt": str(max(0, -c.coins)), |
| recovery.py:54 | lose | LEGACY, READ/DERIVED | item.location = "recovery" if valuable else "destroyed"; recovery = None; raise ValueError("Recovery requires trustworthy base value"); recovery = RecoveryItem( |
| recovery.py:122 | listing | LEGACY, READ/DERIVED | select(RecoveryItem); .where(RecoveryItem.character_id == c.id); .order_by(RecoveryItem.id.desc()); "base_value": str(r.price // 2), |
| recovery.py:146 | recover | LEGACY, WRITE | select(RecoveryItem); .where(RecoveryItem.id == id, RecoveryItem.character_id == c.id); if room.id != "recovery_hall" or distance((c.x, c.y), room.data["npc"]) > 1:; fail("Aproxime-se do Guardião de Recuperação na Guilda") |
| request_controls.py:21 | policy | LEGACY, READ/DERIVED | if path.startswith("/contracts/"):; return ("contracts", 30, 60); if path.startswith(("/auctions/", "/guild/", "/recovery/")): |
| resources.py:90 | collect | LEGACY, READ/DERIVED | from .contracts import progress |
| rooms.py:106 | seed_world | LEGACY, READ/DERIVED | hall = db.get(Room, "auction_hall"); if hall.data.get("npc_name") != "Leiloeiro da Guilda":; "npc_name": "Leiloeiro da Guilda",; "npc_role": "auctioneer", |
| rooms.py:218 | room_payload | LEGACY, READ/DERIVED | "safe": room.kind in (RoomType.CITY, RoomType.GUILD), |
| seed.py:7 | seed | LEGACY, READ/DERIVED | from .balance import ENEMIES; db.add(CentralBank(id=1, balance=0)); if not db.get(Treasury, 1):; db.add(Treasury(id=1, balance=settings.initial_treasury)) |

## Resultado da migração operacional

Todos os writers críticos listados acima delegam a `finance`/`lunar` após `LunarCutover.id=1`. `economy.ledger` conserva recibos legados de compatibilidade, mas o dinheiro somente se move em `LunarEntry`/`LunarHolding`. `Character.coins`, `Treasury.balance` e `CentralBank.balance` ficam congelados e não são espelhados. Leituras Web/Discord/ADM usam projeções Lunar; colunas antigas permanecem auditáveis. Campos `highest_bid`, `reserved`, `reward_amount`, `price` e checkpoints médicos são DERIVED/metadata de direitos/preços, não carteiras paralelas. Seeds não abastecem instituições convertidas.

Novos writers: `cutover.confirm` (ADMIN/LUNAR: gênese histórica uma vez); `finance.move/fee/settle_debt` (LUNAR: transferência/obrigação sem criação); `npc_economy.sell_to_player/buy_from_player` (WRITE/LUNAR: custódia física contra pagamento); `admin_service.apply npc.stock` (ADMIN: item preexistente → estoque, caixa inicial zero). `finance.metrics/reconcile`, `cutover.preview` e `discord_client.query` são READ/DERIVED; queries Discord têm barreira SQL READ ONLY. Ações financeiras abstratas ADM são rejeitadas depois da conversão. Testes TEST usam somente bancos descartáveis. Ver [CUTOVER.md](CUTOVER.md) para fluxo, blockers explícitos, conservação e evidências.
