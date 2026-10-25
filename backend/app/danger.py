"""Danger belongs to first-floor regions, never to the visiting player's level."""

TIERS = {
    "city1": 0,
    "guild": 0,
    "training": 0,
    "common_a": 1,
    "common_b": 2,
    "combat": 3,
    "boss": 5,
}
REGIONAL_KINDS = {"COMMON", "COMBAT", "BOSS"}


def scale_stats(stats, tier, kind):
    hp, attack, defense, level, xp = stats
    extra = max(0, tier - 1) if kind in REGIONAL_KINDS else 0
    return (
        hp + extra * 6,
        attack + extra,
        defense + (extra + 1) // 2,
        level + (extra + 1) // 2,
        xp,
    )
