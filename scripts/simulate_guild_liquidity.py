"""Reproducible physical-cash simulation; no exchange after initial 70/20/10."""

import json, random, sys
from pathlib import Path
from fastapi import HTTPException

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
from app.guild_admin import rebalance_denominations
from app.lunar import select_coins

WEIGHTS = {"coin_large": 10000, "coin_medium": 5000, "coin_small": 1000}


def simulate(payments=20000, seed=90209):
    rng = random.Random(seed)
    initial = rebalance_denominations(19498000)["quantities"]
    guild = initial.copy()
    players = [{k: 0 for k in WEIGHTS} for _ in range(30)]
    successes = 0
    failed_change = 0
    failed_funds = 0
    first = None
    used = {k: 0 for k in WEIGHTS}
    for index in range(payments):
        player = players[rng.randrange(len(players))]
        payer, recipient = (
            (guild, player) if rng.randrange(100) < 52 else (player, guild)
        )
        amount = rng.randrange(1, 61) * 1000
        try:
            coins = select_coins(payer, WEIGHTS, amount)
        except HTTPException:
            if sum(payer[k] * w for k, w in WEIGHTS.items()) >= amount:
                failed_change += 1
                if first is None:
                    first = index + 1
            else:
                failed_funds += 1
            continue
        successes += 1
        for k, q in coins.items():
            payer[k] -= q
            recipient[k] += q
            used[k] += q
    total = sum(guild[k] * w for k, w in WEIGHTS.items())
    all_mass = total + sum(sum(p[k] * w for k, w in WEIGHTS.items()) for p in players)
    global_pieces = {k: guild[k] + sum(p[k] for p in players) for k in WEIGHTS}
    assert global_pieces == initial
    assert all_mass == 19498000
    return {
        "seed": seed,
        "payments_attempted": payments,
        "payments_success": successes,
        "payments_failed_change": failed_change,
        "payments_failed_funds": failed_funds,
        "large_used": used["coin_large"],
        "medium_used": used["coin_medium"],
        "small_used": used["coin_small"],
        "time_until_first_change_failure": {
            "payment_index": first,
            "unit": "simulation step, not wall-clock time",
        },
        "initial_guild_distribution": initial,
        "initial_target_mass_percent": [70, 20, 10],
        "ending_guild_distribution": guild,
        "ending_guild_mass_mg": str(total),
        "ending_mass_basis_points": {
            k: guild[k] * w * 10000 // total if total else 0 for k, w in WEIGHTS.items()
        },
        "total_economic_mass_mg": str(all_mass),
        "global_pieces_by_denomination": global_pieces,
        "audit_gap_mg": "0",
        "note": "Synthetic finite-cash scenario, no production forecast. No automatic exchange/rebalance. Approved target unchanged.",
    }


if __name__ == "__main__":
    result = simulate()
    target = (
        Path(__file__).resolve().parents[1] / "docs/lunar/LIQUIDITY_SIMULATION.json"
    )
    target.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))
