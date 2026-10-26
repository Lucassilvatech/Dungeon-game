"""Compare revised generator against recorded, seed-identical 0.7 simulations."""

import json, statistics, sys
from pathlib import Path

root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root / "backend"))
from app.procedural import SPECIES, generate

old = json.loads((root / "docs/procedural-combat-simulation.json").read_text())
report = {
    "samples_per_profile": 10000,
    "formula_07": "low+floor(span*u), u=r^(1/(1+k*p))",
    "formula_08": "high if span>0 and u>=0.995 else low+floor(span*u)",
    "frozen_instances": "unchanged",
    "results": {},
}
for species, config in SPECIES.items():
    for p in [0, 0.5, 1]:
        key = f"{species}:{p}"
        samples = [generate(config, 1, p, i) for i in range(10000)]
        before = old["distributions"][key]["stats"]
        after = {
            attr: {
                "mean": statistics.mean(s[attr] for s in samples),
                "min": min(s[attr] for s in samples),
                "max": max(s[attr] for s in samples),
                "max_frequency": sum(
                    s[attr] == config["floors"]["1"][attr][1] for s in samples
                )
                / len(samples),
            }
            for attr in samples[0]
        }
        report["results"][key] = {
            "before": before,
            "after": after,
            "level_mean_delta": after["level"]["mean"] - before["level"]["mean"],
        }
(root / "docs/level-distribution-0.8.json").write_text(
    json.dumps(report, indent=2) + "\n"
)
print(
    json.dumps(
        {
            k: {
                "old_mean": v["before"]["level"]["mean"],
                "new_mean": v["after"]["level"]["mean"],
                "max_rate": v["after"]["level"]["max_frequency"],
            }
            for k, v in report["results"].items()
        },
        indent=2,
    )
)
