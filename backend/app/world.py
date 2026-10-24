# Original 16x12 tile map. Walls are authoritative on the server.
WIDTH, HEIGHT = 16, 12
WALLS = {
    (x, y)
    for x in range(WIDTH)
    for y in range(HEIGHT)
    if x in (0, WIDTH - 1) or y in (0, HEIGHT - 1)
} | {(7, y) for y in range(2, 9) if y != 5}
NPC = (3, 3)
MONSTERS = {"slime": (5, 6), "boss": (12, 8)}
PORTAL = (13, 2)


def distance(a, b):
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def map_data(floor):
    return {
        "width": WIDTH,
        "height": HEIGHT,
        "walls": sorted(WALLS),
        "npc": NPC,
        "monsters": MONSTERS if floor == 1 else {},
        "portal": PORTAL,
    }
