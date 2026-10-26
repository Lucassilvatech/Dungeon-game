"""Official institutional money is separate from nontradable administrative test credits."""

from sqlalchemy import select, func
from .models import (
    Character,
    Treasury,
    CentralBank,
    Auction,
    Battle,
    Ledger,
    AdminTestCredit,
)
from .economy import credit_player_gold, ledger
from .game import fail, reward_value


def metrics(db):
    players = db.scalars(select(Character)).all()
    treasury = db.get(Treasury, 1).balance
    bank = db.get(CentralBank, 1).balance
    escrow = sum(
        a.highest_bid
        for a in db.scalars(
            select(Auction).where(Auction.status.in_(["OPEN", "CLOSED"]))
        )
    )
    entries = db.scalars(select(Ledger)).all()
    genesis = sum(e.amount for e in entries if e.source == "initial_supply")
    emitted = sum(e.amount for e in entries if e.source == "mint")
    retired = sum(e.amount for e in entries if e.destination in ("burn", "sink"))
    signed = sum(c.coins for c in players)
    from .models import GuildContract

    contract_reserves = int(
        db.scalar(select(func.coalesce(func.sum(GuildContract.reserved), 0)))
    )
    net = signed + treasury + bank + escrow + contract_reserves
    pending = sum(
        reward_value(b)
        for b in db.scalars(
            select(Battle).where(Battle.status == "won", Battle.claimed == False)
        )
    )
    daily = {}
    for entry in entries:
        key = entry.created.date().isoformat()
        totals = daily.setdefault(
            key,
            {
                "inflows_to_guild": 0,
                "outflows_from_guild": 0,
                "auction_volume": 0,
                "emitted": 0,
                "retired": 0,
            },
        )
        if entry.destination == "treasury":
            totals["inflows_to_guild"] += entry.amount
        if entry.source == "treasury":
            totals["outflows_from_guild"] += entry.amount
        if entry.source.startswith("auction:") and entry.destination in (
            "treasury",
            "sink",
        ):
            totals["auction_volume"] += entry.amount
        if entry.source == "mint":
            totals["emitted"] += entry.amount
        if entry.destination in ("burn", "sink"):
            totals["retired"] += entry.amount
    return dict(
        official_net=str(net),
        expected_net=str(genesis + emitted - retired),
        reconciliation_gap=str(net - (genesis + emitted - retired)),
        player_available=str(sum(max(0, c.coins) for c in players)),
        player_signed=str(signed),
        medical_debt=str(sum(max(0, -c.coins) for c in players)),
        escrow=str(escrow),
        contract_reserves=str(contract_reserves),
        central_bank=str(bank),
        guild_treasury=str(treasury),
        pending_obligations=str(pending),
        genesis=str(genesis),
        emissions=str(emitted),
        retired=str(retired),
        administrative_test_credits=str(
            sum(x.balance for x in db.scalars(select(AdminTestCredit)))
        ),
        wealth_distribution=[
            dict(
                id=c.id,
                name=c.name,
                available=str(max(0, c.coins)),
                debt=str(max(0, -c.coins)),
            )
            for c in sorted(players, key=lambda c: c.coins, reverse=True)[:50]
        ],
        suggestions=(
            [
                "Tesouro insuficiente para obrigações pendentes; avaliar transferência de reservas ou emissão autorizada."
            ]
            if treasury < pending
            else []
        ),
        daily_flows=[
            {"date": day, **{k: str(v) for k, v in totals.items()}}
            for day, totals in sorted(daily.items(), reverse=True)[:30]
        ],
        unavailable=[
            "Índice de preços/inflação: não há mercado geral ou série de preços comparável."
        ],
    )


def amount(value):
    if type(value) is int and value > 0:
        return value
    if (
        isinstance(value, str)
        and value.isascii()
        and value.isdigit()
        and int(value) > 0
    ):
        return int(value)
    fail("Quantidade deve ser um inteiro positivo", 422)


def account(db, name):
    if name == "central_bank":
        return db.get(CentralBank, 1)
    if name == "treasury":
        return db.get(Treasury, 1)
    if name.startswith("character:") and name[10:].isdigit():
        c = db.get(Character, int(name[10:]))
        if c:
            return c
    fail("Conta oficial inexistente; créditos de teste não são negociáveis", 422)


def balance(row):
    return row.coins if isinstance(row, Character) else row.balance


def assign(row, value):
    if isinstance(row, Character):
        row.coins = value
    else:
        row.balance = value


def execute(db, op):
    p = op.params
    n = amount(p["amount"])
    source = p.get("source", "central_bank")
    dest = p.get("destination", "central_bank")
    if op.action == "bank.issue":
        dst = account(db, dest)
        if isinstance(dst, Character):
            credit_player_gold(db, dst, n, "mint", f"admin:{op.id}")
        else:
            assign(dst, balance(dst) + n)
            ledger(db, f"admin:{op.id}", "mint", dest, n)
    elif op.action == "bank.burn":
        src = account(db, source)
        if balance(src) < n:
            fail("Saldo oficial insuficiente")
        assign(src, balance(src) - n)
        ledger(db, f"admin:{op.id}", source, "burn", n)
    elif op.action == "bank.transfer":
        if source == dest:
            fail("Origem e destino devem ser diferentes", 422)
        src = account(db, source)
        dst = account(db, dest)
        if balance(src) < n:
            fail("Reservas oficiais insuficientes")
        assign(src, balance(src) - n)
        if isinstance(dst, Character):
            credit_player_gold(db, dst, n, source, f"admin:{op.id}")
        else:
            assign(dst, balance(dst) + n)
            ledger(db, f"admin:{op.id}", source, dest, n)
