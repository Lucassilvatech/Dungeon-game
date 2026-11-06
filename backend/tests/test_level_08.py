import math
from statistics import mean
import pytest
from app.procedural import SPECIES, generate


@pytest.mark.parametrize("p", [0, 0.25, 0.5, 1])
def test_level_range_and_rare_reachable_maximum(p):
    samples = [generate(SPECIES["slime"], 1, p, seed)["level"] for seed in range(12000)]
    assert min(samples) == 1 and max(samples) == 5
    rate = samples.count(5) / len(samples)
    assert 0.002 <= rate <= 0.03


def test_exact_extreme_draws_and_single_level(monkeypatch):
    class Fixed:
        def __init__(self, seed):
            pass

        def random(self):
            return self.value

    monkeypatch.setattr("app.procedural.random.Random", Fixed)
    for value, expected in [(0.0, 1), (math.nextafter(1.0, 0.0), 5)]:
        Fixed.value = value
        assert generate(SPECIES["slime"], 1, 1, "seed")["level"] == expected
    config = {
        **SPECIES["slime"],
        "floors": {"1": {**SPECIES["slime"]["floors"]["1"], "level": [3, 3]}},
    }
    for value in [0, 0.1, 0.99]:
        Fixed.value = value
        assert generate(config, 1, 0, "seed")["level"] == 3


def test_seed_distribution_bias_invalid_limits_and_disconnection():
    for species in SPECIES.values():
        assert generate(species, 1, 0.4, "same") == generate(species, 1, 0.4, "same")
    distant = [generate(SPECIES["slime"], 1, 0, s)["level"] for s in range(5000)]
    near = [generate(SPECIES["slime"], 1, 1, s)["level"] for s in range(5000)]
    assert mean(near) > mean(distant)
    with pytest.raises(ValueError):
        generate(SPECIES["slime"], 1, None, 1)
    invalid = {
        **SPECIES["slime"],
        "floors": {"1": {**SPECIES["slime"]["floors"]["1"], "level": [8, 9]}},
    }
    with pytest.raises(ValueError):
        generate(invalid, 1, 0.5, 1)
