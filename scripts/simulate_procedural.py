#!/usr/bin/env python3
"""Reproducible first-floor distribution + combat simulation; no database mutation."""
import json
from pathlib import Path
import statistics
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
from app.procedural import SPECIES, generate
from app.balance import damage
from app.config import settings


def fight(enemy, level):
    hp = 30 + (level - 1) * 5
    attack = 5 + (level - 1) + 3
    defense = 2 + (level - 1) // 2
    energy = 10
    remaining = enemy["hp"]
    turns = 0
    while hp > 0 and remaining > 0 and turns < 100:
        skill = energy >= 2
        if skill:
            energy -= 2
        remaining -= damage(attack, enemy["defense"], level, skill=skill)
        turns += 1
        if remaining > 0:
            hp -= damage(enemy["attack"], defense, enemy["level"])
    return hp > 0, turns, max(0, hp)


def main():
    count = 10000
    report = {
        "floor": 1,
        "samples_per_species_proximity": count,
        "total_samples": 60000,
        "k": settings.procedural_proximity_k,
        "level_weight": settings.procedural_level_weight,
        "level_formula_note": "With r<1 and floor, Lmax is exclusive unless Lmin=Lmax. Formula preserved as requested.",
        "combat_policy": "Isolated fights; starter sword +3, level-based sample base stats explicitly stated, skill while energy >=2, then basic; enemy counters only when alive. Does not predict player skill or multi-enemy survival.",
        "combat_heroes": {
            "1": {"hp": 30, "strength_base": 5, "defense": 2, "weapon_power": 3},
            "3": {"hp": 40, "strength_base": 7, "defense": 3, "weapon_power": 3},
        },
        "distributions": {},
    }
    for name, config in SPECIES.items():
        for p in [0, 0.5, 1]:
            samples = [generate(config, 1, p, seed) for seed in range(count)]
            stats = {
                key: {
                    "min": min(s[key] for s in samples),
                    "max": max(s[key] for s in samples),
                    "mean": statistics.mean(s[key] for s in samples),
                    "max_frequency": sum(
                        s[key] == config["floors"]["1"][key][1] for s in samples
                    )
                    / count,
                }
                for key in samples[0]
            }
            combat = {}
            for level in [1, 3]:
                fights = [fight(s, level) for s in samples]
                combat[str(level)] = {
                    "win_rate": sum(row[0] for row in fights) / count,
                    "mean_turns": statistics.mean(row[1] for row in fights),
                    "mean_remaining_hp": statistics.mean(row[2] for row in fights),
                }
            report["distributions"][f"{name}:{p}"] = {"stats": stats, "combat": combat}
    path = (
        Path(__file__).resolve().parents[1] / "docs/procedural-combat-simulation.json"
    )
    path.write_text(json.dumps(report, indent=2) + "\n")
    print(
        json.dumps(
            {key: value["combat"] for key, value in report["distributions"].items()},
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
