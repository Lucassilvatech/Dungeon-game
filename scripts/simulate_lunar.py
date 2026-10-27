"""Deterministic isolated mass-flow scenarios. Numbers are fixtures, not game balance."""

import json, random
from pathlib import Path


def simulate(players, scenario, seed=77):
    rng = random.Random(seed)
    coins = [0] * players
    nuggets = [0] * players
    guild = 0
    treasury = 0
    reserve = 10000000
    discovered = reserve
    destroyed = minted = trades = refused = 0
    npc = 0
    stock = 50
    for tick in range(100):
        # Convert existing material, then issue; never mint without reserve.
        if scenario != "treasury_shortage" and reserve >= 100000:
            reserve -= 100000
            treasury += 100000
            minted += 100000
        if treasury >= 100000:
            treasury -= 100000
            guild += 100000
        for p in range(players):
            threshold = 1 if scenario == "rare" else 200 if scenario == "excess" else 10
            if rng.randrange(1000) < threshold:
                nuggets[p] += 100000
                discovered += 100000
            if scenario != "hoard" and nuggets[p] >= 100000:
                if guild >= 100000:
                    nuggets[p] -= 100000
                    reserve += 100000
                    guild -= 100000
                    coins[p] += 100000
                    trades += 1
                else:
                    refused += 1
            if stock and coins[p] >= 1000:
                coins[p] -= 1000
                npc += 1000
                stock -= 1
                trades += 1
            if scenario == "ritual_heavy" and coins[p] >= 100000:
                coins[p] -= 100000
                destroyed += 100000
    held = reserve + treasury + guild + npc + sum(coins) + sum(nuggets)
    assert held == discovered - destroyed
    return {
        "players": players,
        "scenario": scenario,
        "seed": seed,
        "discovered_mg": discovered,
        "minted_mg": minted,
        "destroyed_mg": destroyed,
        "treasury_mineral_mg": reserve,
        "treasury_coin_mg": treasury,
        "guild_coin_mg": guild,
        "npc_coin_mg": npc,
        "player_coin_mg": sum(coins),
        "player_nugget_mg": sum(nuggets),
        "trades": trades,
        "refused_insufficient_cash": refused,
        "npc_stock_remaining": stock,
        "gap_mg": held - discovered + destroyed,
    }


if __name__ == "__main__":
    report = {
        "note": "Isolated integer-mass fixtures, not production configuration or equilibrium claims. Initial 10kg is explicit simulated discovery. NPC starts with zero coins and 50 finite fixture products. No economic policy tuning.",
        "results": [
            simulate(n, s)
            for n in [10, 100, 1000]
            for s in ["rare", "excess", "hoard", "ritual_heavy", "treasury_shortage"]
        ],
    }
    target = Path(__file__).resolve().parents[1] / "docs/lunar/SIMULATION.json"
    target.write_text(json.dumps(report, indent=2) + "\n")
    print("PASS:", len(report["results"]), "reproducible scenarios; all mass gaps zero")
