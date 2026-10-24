"""First-floor combat parameters. No random client damage or level scaling to player."""

from .config import settings

# hp, attack, defense, level, XP. Independent enemy groups can reference instances.
ENEMIES = {
    "slime": (24, 6, 2, 1, 30),
    "goblin": (30, 7, 3, 2, 40),
    "boss": (60, 9, 3, 3, 100),
    "warden": (90, 14, 5, 8, 100),
    "dummy": (24, 0, 2, 1, 0),
}
NAMES = {
    "slime": "Slime do musgo",
    "goblin": "Batedor da clareira",
    "boss": "Guardião da Clareira",
    "warden": "Sentinela da Maré",
    "dummy": "Boneco de treinamento",
}


def damage(attack, defense, level, skill=False, guard=False):
    raw = attack + max(0, level - 1) // 2 + (settings.skill_bonus if skill else 0)
    reduction = defense + (settings.guard_bonus if guard else 0)
    return max(settings.damage_min, min(settings.damage_max, raw - reduction))
