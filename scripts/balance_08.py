"""Controlled comparisons, with actual server damage/generator and no database writes."""

import json, statistics, sys
from pathlib import Path

root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root / "backend"))
from app.procedural import generate, SPECIES
from app.balance import damage

PROFILES = {
    "iniciante_sem_arma": {
        "level": 1,
        "strength": 5,
        "defense": 2,
        "weapon": 0,
        "coins": 0,
    },
    "iniciante_espada": {
        "level": 1,
        "strength": 5,
        "defense": 2,
        "weapon": 3,
        "coins": 0,
    },
    "iniciante_endividado": {
        "level": 1,
        "strength": 5,
        "defense": 2,
        "weapon": 3,
        "coins": -1000,
    },
    "forca_nivel5": {"level": 5, "strength": 9, "defense": 2, "weapon": 3, "coins": 0},
    "defesa_nivel5": {"level": 5, "strength": 5, "defense": 6, "weapon": 3, "coins": 0},
    "equilibrado_nivel3": {
        "level": 3,
        "strength": 6,
        "defense": 3,
        "weapon": 3,
        "coins": 0,
    },
}


def fight(profile, enemies):
    hp = 30 + (profile["level"] - 1) * 5
    energy = 10
    turns = 0
    dealt = received = 0
    remaining = [dict(e) for e in enemies]
    while hp > 0 and any(e["hp"] > 0 for e in remaining) and turns < 100:
        target = next(e for e in remaining if e["hp"] > 0)
        skill = energy >= 2
        if skill:
            energy -= 2
        amount = min(
            target["hp"],
            damage(
                profile["strength"] + profile["weapon"],
                target["defense"],
                profile["level"],
                skill=skill,
            ),
        )
        target["hp"] -= amount
        dealt += amount
        turns += 1
        for e in remaining:
            if e["hp"] <= 0:
                continue
            amount = min(hp, damage(e["attack"], profile["defense"], e["level"]))
            hp -= amount
            received += amount
            if hp == 0:
                break
    return {
        "won": hp > 0,
        "turns": turns,
        "damage_dealt": dealt,
        "damage_received": received,
        "hp_remaining": hp,
    }


def main():
    count = 1500
    report = {
        "samples_per_case": count,
        "profiles": PROFILES,
        "policy": "Skill while energy>=2 then basic; fixed target order; survivors answer by identity. Isolated encounters, full initial HP/energy, zero XP at start. No simulated wall-clock game time.",
        "results": {},
        "economic_note": "Debt does not alter combat stats; medical fee/death/flee/recovery impacts are measured from real transactions in gameplay_days. No synthetic coins issued.",
    }
    for name, profile in PROFILES.items():
        report["results"][name] = {}
        for p in (0, 0.5, 1):
            for size in (1, 2):
                samples = [
                    fight(
                        profile,
                        [
                            generate(
                                SPECIES["slime" if i % 2 == 0 else "goblin"],
                                1,
                                p,
                                f"{seed}:{i}",
                            )
                            for i in range(size)
                        ],
                    )
                    for seed in range(count)
                ]
                report["results"][name][f"p={p};size={size}"] = {
                    "win_rate": sum(s["won"] for s in samples) / count,
                    **{
                        "mean_" + key: statistics.mean(s[key] for s in samples)
                        for key in (
                            "turns",
                            "damage_dealt",
                            "damage_received",
                            "hp_remaining",
                        )
                    },
                }
    assert (
        report["results"]["iniciante_espada"]
        == report["results"]["iniciante_endividado"]
    )
    (root / "docs/balance-0.8.json").write_text(json.dumps(report, indent=2) + "\n")
    print(
        "PASS: 54000 controlled encounters across 6 legal profiles; debt does not change combat results"
    )


if __name__ == "__main__":
    main()
