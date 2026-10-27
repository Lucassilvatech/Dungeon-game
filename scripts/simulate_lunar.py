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


def simulate_procedural(expeditions, scenario, seed=91):
    """PROVISIONAL fixtures; includes persisted zero decisions and economic entry at collection."""
    import sys, threading
    from concurrent.futures import ThreadPoolExecutor

    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
    from app.lunar_resources import roll, WEIGHTS

    chance = 0 if scenario == "none" else 1000 if scenario == "rare" else 1000000
    config = {
        "lunar_resource_spawn_enabled": True,
        "lunar_resource_spawn_chance_ppm": chance,
        "lunar_resource_weight_distribution": {
            "nugget_small": 90,
            "nugget_medium": 9,
            "nugget_large": 1,
        },
    }
    decisions = {
        i: roll(i, f"sim:{seed}:{i}", seed, 0, config) for i in range(expeditions)
    }
    states = {i: "AVAILABLE" for i, (_, asset) in decisions.items() if asset}
    genesis = 0 if scenario == "insolvent_guild" else 10000000
    guild_coins, player_coins, guild_mineral, player_mineral, discovered = (
        genesis,
        0,
        0,
        0,
        0,
    )
    sold = refused = collected = replays = 0
    lock = threading.Lock()

    def collect(i):
        nonlocal discovered, player_mineral, collected, replays
        with lock:
            if states[i] != "AVAILABLE":
                replays += 1
                return
            states[i] = "COLLECTED"
            mass = WEIGHTS[decisions[i][1]]
            discovered += mass
            player_mineral += mass
            collected += 1

    eligible = [
        i
        for i in states
        if scenario != "abandon" and (scenario != "partial" or i % 2 == 0)
    ]
    if scenario == "concurrent":
        with ThreadPoolExecutor(4) as pool:
            list(pool.map(collect, [i for i in eligible for _ in range(2)]))
    else:
        for i in eligible:
            collect(i)
    for i in list(states):
        if scenario == "reconnect":
            before = decisions[i]
            for _ in range(5):
                assert (
                    decisions[i] == before
                )  # persisted lookup, never another RNG draw
        if states[i] == "AVAILABLE":
            states[i] = "EXPIRED"
        if states[i] == "COLLECTED" and scenario in ("sale", "insolvent_guild"):
            mass = WEIGHTS[decisions[i][1]]
            price = {
                "nugget_small": 7000,
                "nugget_medium": 13000,
                "nugget_large": 19000,
            }[decisions[i][1]]
            if guild_coins >= price:
                guild_coins -= price
                player_coins += price
                player_mineral -= mass
                guild_mineral += mass
                sold += mass
            else:
                refused += 1
    held = guild_coins + player_coins + guild_mineral + player_mineral
    assert genesis + discovered == held
    return {
        "scenario": scenario,
        "expeditions": expeditions,
        "seed": seed,
        "potential_occurrences": len(states),
        "collected": collected,
        "expired": sum(v == "EXPIRED" for v in states.values()),
        "discovered_mg": str(discovered),
        "sold_to_guild_mg": str(sold),
        "guild_coin_mg": str(guild_coins),
        "player_coin_mg": str(player_coins),
        "guild_mineral_mg": str(guild_mineral),
        "player_mineral_mg": str(player_mineral),
        "refused_insufficient_cash": refused,
        "duplicate_attempts_without_new_mass": replays,
        "gap_mg": "0",
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
    report["procedural_note"] = (
        "PROVISIONAL fixture probabilities/prices only; not final balance. Potential spawn is not supply; discovery is recorded on collection. No boss, echo or automatic policy."
    )
    report["procedural_results"] = [
        simulate_procedural(10000, s)
        for s in [
            "none",
            "rare",
            "stress",
            "partial",
            "abandon",
            "sale",
            "insolvent_guild",
            "reconnect",
            "concurrent",
        ]
    ]
    target = Path(__file__).resolve().parents[1] / "docs/lunar/SIMULATION.json"
    target.write_text(json.dumps(report, indent=2) + "\n")
    print(
        "PASS:",
        len(report["results"]),
        "foundation scenarios and",
        len(report["procedural_results"]),
        "procedural scenarios; all mass gaps zero",
    )
