"""Reproducible original pixel-art atlas compiler. Pillow only; no runtime dependency.
Generated source paintings are preserved; nearest sampling, palette reduction and
hand-authored directional sprite/tile programs produce the shipping PNG assets.
Run: .venv/bin/python scripts/build_pixel_assets.py
"""

from pathlib import Path
import hashlib
import json
import math
import random
from PIL import Image, ImageDraw
from map_art.walk import walk_pose
from map_art.compiler import build as build_maps

ROOT = Path(__file__).resolve().parents[1] / "frontend/public/assets/pixel"
ROOT.mkdir(parents=True, exist_ok=True)
manifest = {}


def save(name, image, frames):
    image.save(ROOT / (name + ".png"), optimize=True)
    manifest[name] = {
        "file": name + ".png",
        "frames": frames,
        "width": image.width,
        "height": image.height,
        "sha256": hashlib.sha256((ROOT / (name + ".png")).read_bytes()).hexdigest(),
    }


def source_atlas(filename, names, sizes, cols):
    source = Image.open(ROOT.parents[3] / "art/pixel/source" / filename).convert("RGBA")
    rows = math.ceil(len(names) / cols)
    atlas = Image.new("RGBA", (cols * 128, rows * 128))
    for i, name in enumerate(names):
        x, y = i % cols, i // cols
        crop = source.crop(
            (
                round(x * source.width / cols),
                round(y * source.height / rows),
                round((x + 1) * source.width / cols),
                round((y + 1) * source.height / rows),
            )
        )
        alpha = crop.getchannel("A").point(lambda v: 255 if v >= 112 else 0)
        crop.putalpha(alpha)
        box = alpha.getbbox()
        assert box, name
        crop = crop.crop(box)
        if name.startswith("house_"):
            crop = crop.resize(sizes[i], Image.Resampling.NEAREST)
        else:
            crop.thumbnail(sizes[i], Image.Resampling.NEAREST)
        # Keep hard alpha and a coherent finite palette, never runtime smoothing.
        crop = crop.quantize(colors=48, method=Image.Quantize.FASTOCTREE).convert(
            "RGBA"
        )
        atlas.alpha_composite(
            crop, (x * 128 + (128 - crop.width) // 2, y * 128 + 126 - crop.height)
        )
    save(filename.split("-")[0], atlas, {name: i for i, name in enumerate(names)})


if (ROOT.parents[3] / "art/pixel/source/bosses-original.png").exists():
    source_atlas(
        "bosses-original.png",
        ["moss_colossus", "thorn_chief", "abyssal_warden", "basalt_drake"],
        [(96, 96)] * 4,
        2,
    )

# Map materials/scenery are rebuilt separately from the supplied reference sheets.
# Approved character identities and existing boss identities stay here.
reference = Image.open(
    ROOT.parents[3] / "art/pixel/source/reference-actors.png"
).convert("RGBA")


def cell(row, col):
    crop = reference.crop(
        (
            round(col * reference.width / 4),
            round(row * reference.height / 4),
            round((col + 1) * reference.width / 4),
            round((row + 1) * reference.height / 4),
        )
    )
    alpha = crop.getchannel("A").point(lambda v: 255 if v > 120 else 0)
    crop.putalpha(alpha)
    crop = crop.crop(alpha.getbbox())
    # 16x24 logical pixels enlarged2x is the reference's actual visual language.
    crop = (
        crop.resize((16, 24), Image.Resampling.NEAREST)
        .quantize(colors=14, method=Image.Quantize.FASTOCTREE)
        .convert("RGBA")
    )
    return crop.resize((32, 48), Image.Resampling.NEAREST)


def recolor(im, role):
    im = im.copy()
    pixels = im.load()
    for y in range(im.height):
        for x in range(im.width):
            r, g, b, a = pixels[x, y]
            if not a:
                continue
            if role == "reception" and g > r * 1.08 and g > b * 1.05:
                pixels[x, y] = (min(160, r + 44), g // 2, min(120, b + 12), a)
            if role == "goblin" and r > g * 1.10 and r > b * 1.20 and r > 110:
                pixels[x, y] = (
                    int(r * 0.57),
                    min(175, int(g * 1.02)),
                    int(b * 0.62),
                    a,
                )
    return im


for key in [
    "hero",
    "peer",
    "npc",
    "merchant",
    "alchemist",
    "blacksmith",
    "hooded",
    "goblin",
    "goblin_elite",
    "slime",
    "slime_elite",
    "dummy",
]:
    row = {
        "hero": 0,
        "merchant": 1,
        "npc": 1,
        "alchemist": 2,
        "blacksmith": 3,
        "peer": 2,
    }.get(key, 0)
    poses = [cell(row, c) for c in range(4)]
    if key == "npc":
        poses = [recolor(v, "reception") for v in poses]
    if key.startswith("goblin"):
        poses = [recolor(v, "goblin") for v in poses]
    atlas = Image.new("RGBA", (48 * 8, 64 * 12))
    for frame in range(96):
        if frame < 16:
            mode, di, step = 0, frame // 4, frame % 4
        elif frame < 48:
            mode, di, step = 1, (frame - 16) // 8, (frame - 16) % 8
        else:
            mode, di, step = 2 + (frame - 48) // 16, (frame % 16) // 4, frame % 4
        im = Image.new("RGBA", (48, 64))
        d = ImageDraw.Draw(im)
        if key.startswith("slime"):
            top = 29 + (1 if step % 2 else 0)
            dark = "#223e38"
            mid = "#638c4e"
            light = "#9cbc66"
            d.polygon(
                [
                    (7, 57),
                    (7, top + 9),
                    (11, top + 3),
                    (20, top),
                    (30, top + 2),
                    (39, top + 9),
                    (41, 57),
                    (34, 61),
                    (13, 61),
                ],
                fill=dark,
            )
            d.polygon(
                [
                    (10, 55),
                    (10, top + 10),
                    (15, top + 5),
                    (28, top + 4),
                    (36, top + 10),
                    (38, 56),
                    (31, 58),
                    (15, 58),
                ],
                fill=mid,
            )
            d.polygon(
                [
                    (12, top + 10),
                    (17, top + 5),
                    (28, top + 4),
                    (33, top + 8),
                    (27, top + 10),
                ],
                fill=light,
            )
            d.rectangle((17, top + 13, 19, top + 17), fill="#162e2b")
            d.rectangle((29, top + 13, 31, top + 17), fill="#162e2b")
            d.rectangle((15, top + 7, 18, top + 8), fill="#ccdb91")
            if key.endswith("elite"):
                d.polygon(
                    [
                        (10, top + 4),
                        (10, top - 5),
                        (17, top - 1),
                        (24, top - 8),
                        (30, top - 1),
                        (37, top - 5),
                        (37, top + 5),
                    ],
                    fill="#a58a54",
                )
                d.rectangle((22, top - 2, 25, top + 1), fill="#a4d9c7")
                d.rectangle((8, 47, 13, 53), fill="#647a6b")
        elif key == "hooded":
            d.polygon(
                [
                    (11, 58),
                    (12, 24),
                    (17, 13),
                    (24, 8),
                    (32, 14),
                    (36, 25),
                    (38, 60),
                    (30, 62),
                    (14, 62),
                ],
                fill="#18232e",
            )
            d.polygon(
                [(15, 29), (16, 20), (24, 15), (32, 21), (33, 30)], fill="#050b12"
            )
            d.line((15, 32, 13, 57), fill="#45505a", width=2)
            d.line((34, 33, 36, 57), fill="#2d3946", width=2)
            d.line((17, 13, 23, 10, 30, 15), fill="#535962", width=2)
        elif key == "dummy":
            d.rectangle((22, 18, 25, 62), fill="#614933")
            d.rectangle((10, 34, 38, 38), fill="#795b3c")
            d.rectangle((15, 22, 33, 51), fill="#ad8b55")
            d.rectangle((17, 12, 31, 24), fill="#c5a56d")
            d.rectangle((16, 26, 32, 28), fill="#d3bb80")
            d.ellipse((20, 32, 29, 41), outline="#684e32", width=2)
        else:
            pose = poses[di].copy()
            if mode == 1:
                im = walk_pose(pose, di, step)
                d = ImageDraw.Draw(im)
            else:
                # Idle is the approved design, without artificial bouncing.
                im.alpha_composite(pose, (8, 14))
            if key.startswith("goblin"):
                d.polygon([(9, 28), (3, 24), (7, 34), (11, 33)], fill="#829a61")
                d.polygon([(37, 28), (44, 24), (40, 34), (36, 33)], fill="#829a61")
                if key.endswith("elite"):
                    d.rectangle((7, 39, 14, 44), fill="#7b7381")
                    d.rectangle((33, 39, 40, 44), fill="#7b7381")
                    d.polygon(
                        [(12, 21), (8, 15), (16, 19), (31, 19), (39, 15), (34, 24)],
                        fill="#b8a783",
                    )
            if key == "hero" and mode == 2:
                xx = 4 if di == 1 else 41
                d.rectangle((xx, 25 - step * 2, xx + 1, 48), fill="#d2ddd3")
                d.rectangle((xx - 2, 45, xx + 3, 46), fill="#bba36c")
        if mode == 3:
            alpha = im.getchannel("A")
            im = Image.blend(im, Image.new("RGBA", im.size, "#f5b0a0"), 0.25)
            im.putalpha(alpha)
        if mode == 4:
            crop = im.crop(im.getbbox()).rotate(
                90, expand=True, resample=Image.Resampling.NEAREST
            )
            crop.thumbnail((44, 15), Image.Resampling.NEAREST)
            im = Image.new("RGBA", (48, 64))
            im.alpha_composite(crop, ((48 - crop.width) // 2, 62 - crop.height))
        atlas.alpha_composite(im, ((frame % 8) * 48, (frame // 8) * 64))
    save(key, atlas, {"frameWidth": 48, "frameHeight": 64, "endFrame": 95})

# Small authored effects/props atlas. Four flames have deliberately different silhouettes.
names = [
    "flame_0",
    "flame_1",
    "flame_2",
    "flame_3",
    "shadow",
    "glow_warm",
    "glow_cyan",
    "glow_ritual",
    "flower",
    "bush",
    "moss",
    "mushroom",
    "bones",
    "banner",
    "shelf",
    "table",
    "counter",
    "chair",
    "bench",
    "rug",
    "portal",
    "herb",
    "ore",
    "lunar",
    "rock",
    "sign",
    "rune",
    "smoke",
]
effects = Image.new("RGBA", (64 * 8, 64 * 4))
for i, name in enumerate(names):
    im = Image.new("RGBA", (64, 64))
    d = ImageDraw.Draw(im)
    if name.startswith("flame"):
        f = int(name[-1])
        d.rectangle((29, 44, 34, 60), fill="#80604a")
        d.rectangle((26, 39, 37, 43), fill="#555a58")
        d.polygon(
            [
                (27, 39),
                (24, 30),
                (29, 21),
                (28 + f, 10),
                (34, 18),
                (37 + f, 28),
                (37, 37),
                (33, 41),
            ],
            fill="#d85b35",
        )
        d.polygon(
            [(28, 37), (28, 29), (33, 20 + f), (35, 30), (34, 38)], fill="#f8ac52"
        )
        d.rectangle((30, 32, 33, 38), fill="#ffeab0")
    elif name == "shadow":
        d.polygon(
            [
                (12, 28),
                (20, 24),
                (44, 24),
                (52, 28),
                (52, 34),
                (44, 38),
                (20, 38),
                (12, 34),
            ],
            fill="#081d2855",
        )
    elif name.startswith("glow"):
        rgb = {
            "glow_warm": (255, 159, 70),
            "glow_cyan": (84, 202, 214),
            "glow_ritual": (139, 92, 197),
        }[name]
        for r, a in [(31, 7), (26, 12), (20, 18), (15, 24), (9, 35)]:
            d.ellipse((32 - r, 32 - r, 32 + r, 32 + r), fill=(*rgb, a))
    elif name in ("flower", "herb", "moss", "bush", "mushroom"):
        for x, y in [(15, 48), (28, 42), (40, 51), (34, 57)]:
            d.line((x, y, x - 3, y - 8), fill="#3e643e", width=2)
            d.line((x, y, x + 4, y - 12), fill="#7f9c50", width=2)
            if name in ("flower", "herb"):
                d.rectangle(
                    (x + 2, y - 15, x + 5, y - 12),
                    fill="#e8d4a1" if x % 2 else "#d5a19b",
                )
                d.point((x + 3, y - 13), fill="#f6edc9")
            if name == "mushroom":
                d.rectangle((x, y - 8, x + 1, y), fill="#8cae93")
                d.ellipse((x - 4, y - 12, x + 5, y - 7), fill="#63a0a1")
                d.point((x - 1, y - 10), fill="#c0d9b0")
        if name == "bush":
            for x, y, r in [(18, 48, 9), (30, 42, 12), (44, 49, 10)]:
                d.ellipse((x - r, y - r, x + r, y + r), fill="#355739")
                d.arc((x - r, y - r, x + r, y + r), 180, 290, fill="#94aa58", width=3)
    elif name in ("ore", "lunar", "rock"):
        col = "#7eacbe" if name == "lunar" else "#777f72"
        d.polygon(
            [(16, 54), (20, 41), (31, 35), (46, 40), (50, 54), (39, 60), (24, 59)],
            fill="#263f48",
        )
        d.polygon(
            [(18, 51), (22, 41), (32, 38), (45, 42), (46, 51), (35, 54)], fill=col
        )
        d.line((23, 42, 31, 39, 40, 42), fill="#ccdbbd", width=2)
        if name == "lunar":
            d.polygon(
                [(27, 49), (28, 40), (33, 35), (37, 44), (34, 51)], fill="#c8f5ec"
            )
    elif name == "bones":
        d.line((15, 55, 45, 39), fill="#9b9c89", width=4)
        d.ellipse((17, 35, 29, 46), fill="#c5c4a5")
        d.rectangle((20, 38, 22, 40), fill="#343f40")
        d.rectangle((25, 38, 27, 40), fill="#343f40")
    elif name in ("portal", "rune"):
        if name == "portal":
            d.rectangle((11, 10, 52, 61), fill="#324f56")
            d.rectangle((15, 14, 48, 61), fill="#b19a6a")
            d.rectangle((19, 18, 44, 61), fill="#172c38")
            d.line((21, 23, 41, 23), fill="#7eaba9", width=2)
        else:
            d.ellipse((5, 5, 59, 59), outline="#9a52687a", width=1)
            d.ellipse((10, 10, 54, 54), outline="#6e7d9a88", width=1)
            d.line((32, 11, 49, 43, 14, 43, 32, 11), fill="#84476077", width=1)
            for a in range(0, 360, 30):
                x, y = round(32 + 24 * math.cos(math.radians(a))), round(
                    32 + 24 * math.sin(math.radians(a))
                )
                d.line((x, y - 1, x + 1, y + 1, x - 1, y + 2), fill="#c1889777")
    elif name == "smoke":
        d.rectangle((29, 20, 33, 25), fill="#b3bfab44")
        d.rectangle((31, 11, 36, 16), fill="#c7d0b533")
    elif name == "rug":
        d.rectangle((3, 3, 60, 60), fill="#513d44")
        d.rectangle((5, 5, 58, 58), outline="#c4a36b", width=2)
        d.rectangle((9, 9, 54, 54), fill="#754f53")
        d.rectangle((12, 12, 51, 51), outline="#a9825c")
        for xx in range(8, 60, 6):
            d.line((xx, 1, xx, 3), fill="#d0b47e")
            d.line((xx, 61, xx, 63), fill="#d0b47e")
        for xx, yy in [(20, 20), (40, 20), (20, 40), (40, 40)]:
            d.polygon(
                [(xx, yy - 5), (xx + 4, yy), (xx, yy + 5), (xx - 4, yy)],
                outline="#c09b67",
            )
    elif name == "banner":
        d.rectangle((17, 4, 47, 6), fill="#a08759")
        d.polygon([(20, 7), (44, 7), (44, 48), (32, 56), (20, 48)], fill="#513947")
        d.line((24, 10, 24, 45, 32, 49, 40, 45, 40, 10), fill="#8a5a5b")
        d.line((32, 18, 32, 37), fill="#b78361", width=2)
        d.line((27, 22, 37, 29, 27, 34), fill="#b78361", width=2)
    else:
        # Crafted timber furniture with joinery, textured planks, rivets, highlighted edges.
        w = 44 if name in ("table", "counter", "rug") else 30
        left = (64 - w) // 2
        d.rectangle((left + 2, 28, left + w - 2, 59), fill="#352d2c")
        d.rectangle((left, 24, left + w, 52), fill="#785438")
        d.rectangle((left + 2, 25, left + w - 2, 27), fill="#c19b64")
        for yy in (32, 40, 48):
            d.line((left + 2, yy, left + w - 2, yy), fill="#493c2f")
            d.line((left + 3, yy + 1, left + w - 3, yy + 1), fill="#9d774e")
        for xx in (left + 3, left + w - 3):
            d.rectangle((xx, 28, xx + 1, 49), fill="#ad895c")
        if name == "shelf":
            for j, c in enumerate(["#829b85", "#b88662", "#a7966a", "#6d7d99"]):
                d.rectangle((left + 4 + j * 6, 29, left + 7 + j * 6, 39), fill=c)
        if name == "sign":
            d.line((32, 48, 32, 63), fill="#65482f", width=4)
            d.line((22, 35, 42, 35), fill="#d3b776", width=2)
    effects.alpha_composite(im, ((i % 8) * 64, (i // 8) * 64))
save("effects", effects, {name: i for i, name in enumerate(names)})
(ROOT / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
(ROOT.parents[3] / "frontend/src/visual/atlas.json").write_text(
    json.dumps(manifest, indent=2) + "\n"
)
print(
    f"Compiled {len(manifest)} original atlases; "
    + str(sum((ROOT / v["file"]).stat().st_size for v in manifest.values()))
    + " bytes"
)

build_maps()

from character_art.compile import build as build_character_layers
build_character_layers()
