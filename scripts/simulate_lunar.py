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
    from app.lunar_resources import roll

    chance = 0 if scenario == "none" else 20000 if scenario == "rare" else 1000000
    config = {
        "lunar_resource_spawn_enabled": True,
        "lunar_resource_spawn_chance_ppm": chance,
        "lunar_resource_weight_bands": [
            {"min_g": 100, "max_g": 200, "percent": 80},
            {"min_g": 201, "max_g": 700, "percent": 15},
            {"min_g": 701, "max_g": 1000, "percent": 5},
        ],
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
            mass = decisions[i][1]
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
            mass = decisions[i][1]
            price = (mass // 1000) * 800 // 1000 * 1000
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


def simulate_variable_chain(extraordinary=False):
    genesis = 10000000
    discovery = 684000
    injection = 111000 if extraordinary else 0
    destroyed = 5000 if extraordinary else 0
    # Root684 ->500+184; sold500 keeps identity; Treasury mints437 and retains63.
    lots = [
        {"id": 1, "grams": 684, "state": "SPLIT", "parent": None},
        {"id": 2, "grams": 500, "state": "SPLIT", "parent": 1},
        {"id": 3, "grams": 184, "state": "HELD", "parent": 1, "owner": "player"},
        {"id": 4, "grams": 437, "state": "MINTED", "parent": 2},
        {"id": 5, "grams": 63, "state": "HELD", "parent": 2, "owner": "treasury"},
    ]
    if extraordinary:
        lots.append({"id": 6, "grams": 111, "state": "HELD", "parent": None,
                     "owner": "treasury", "origin": "ADMIN_INJECTION"})
    mineral = (184 + 63) * 1000 + injection
    coins = genesis + 437000 - destroyed
    assert genesis + discovery + injection - destroyed == mineral + coins
    return {
        "scenario": "extraordinary" if extraordinary else "normal",
        "genesis_mg": str(genesis),
        "discovered_mg": str(discovery),
        "admin_injection_mg": str(injection),
        "destroyed_mg": str(destroyed),
        "minted_mg": "437000",
        "sale_500g_units": 400,
        "lots": lots,
        "mineral_mg": str(mineral),
        "coins_mg": str(coins),
        "gap_mg": "0",
    }


def variable_statistics(n=1000000):
    import sys

    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
    from app.lunar_resources import roll
    from app.config import Settings

    settings = Settings(_env_file=None)
    config = {
        k: getattr(settings, k)
        for k in [
            "lunar_resource_spawn_enabled",
            "lunar_resource_spawn_chance_ppm",
            "lunar_resource_weight_bands",
        ]
    }
    counts = [0, 0, 0]
    minimum = 1000
    maximum = 0
    for i in range(n):
        _, w = roll(i, f"variable:{i}", 91, 0, config)
        if w:
            g = w // 1000
            assert w % 1000 == 0 and 100 <= g <= 1000
            counts[0 if g <= 200 else 1 if g <= 700 else 2] += 1
            minimum = min(minimum, g)
            maximum = max(maximum, g)
    total = sum(counts)
    assert n * 18 // 1000 < total < n * 22 // 1000
    assert (
        abs(counts[0] * 10000 // total - 8000) < 250
        and abs(counts[1] * 10000 // total - 1500) < 200
        and abs(counts[2] * 10000 // total - 500) < 150
    )
    return {
        "decisions": n,
        "spawned": total,
        "chance_ppm": 20000,
        "band_counts": counts,
        "minimum_g": minimum,
        "maximum_g": maximum,
        "rate_milliunits_per_g": 800,
        "note": "Approved initial design; statistical tolerances are verification only.",
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
    report["variable_statistics"] = variable_statistics()
    report["variable_chains"] = [
        simulate_variable_chain(False),
        simulate_variable_chain(True),
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
