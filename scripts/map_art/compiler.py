"""Compile reference-derived map art, with explicit trimmed frames and hard alpha.

Sources are versioned. This only builds images; it never accesses a game database.
No legacy scenery or runtime rectangle textures are used by the new renderer.
"""

from pathlib import Path
import hashlib
import json
import random
from PIL import Image, ImageDraw, ImageChops, ImageStat

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "art/maps/source"
OUT = ROOT / "frontend/public/assets/maps"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def clean(image, size):
    image = image.convert("RGBA")
    alpha = image.getchannel("A").point(lambda a: 255 if a >= 160 else 0)
    image.putalpha(alpha)
    bbox = alpha.getbbox()
    if not bbox:
        raise ValueError("Empty source cell")
    image = image.crop(bbox)
    image.thumbnail(size, Image.Resampling.NEAREST)
    image = image.quantize(colors=96, method=Image.Quantize.FASTOCTREE).convert("RGBA")
    # Remove invisible RGB too, for clean edges and deterministic hashes.
    result = Image.new("RGBA", image.size)
    result.paste(image, (0, 0), image.getchannel("A"))
    return result


def sprites(name, source_name, specs):
    source = Image.open(SOURCE / source_name)
    atlas = Image.new("RGBA", (1024, 1024))
    frames, dimensions = {}, {}
    for index, (key, crop, size) in enumerate(specs):
        art = clean(source.crop(crop), size)
        x, y = index % 4 * 256 + 2, index // 4 * 256 + 2
        atlas.alpha_composite(art, (x, y))
        frames[key] = {
            "frame": {"x": x, "y": y, "w": art.width, "h": art.height},
            "rotated": False,
            "trimmed": False,
            "spriteSourceSize": {"x": 0, "y": 0, "w": art.width, "h": art.height},
            "sourceSize": {"w": art.width, "h": art.height},
        }
        dimensions[key] = {"atlas": name, "width": art.width, "height": art.height}
    atlas.save(OUT / (name + ".png"), optimize=True)
    (OUT / (name + ".json")).write_text(
        json.dumps({"frames": frames, "meta": {"scale": "1"}}, indent=2) + "\n"
    )
    return dimensions


def cell(col, row):
    return (col * 320, row * 320, (col + 1) * 320, (row + 1) * 320)


def periodic(image):
    """Match opposite edge pixels; retain NEAREST pixels and avoid tile borders.

    Restrict correction to an eight-pixel border. This is a seam repair of the
    extracted material, not an overlay rectangle placed on the playable map.
    """
    image = image.convert("RGB")
    pixels = image.load()
    w, h = image.size
    for horizontal in (True, False):
        length, other = (w, h) if horizontal else (h, w)
        for t in range(other):
            p = (0, t) if horizontal else (t, 0)
            q = (length - 1, t) if horizontal else (t, length - 1)
            avg = tuple((a + b) // 2 for a, b in zip(pixels[p], pixels[q]))
            for d in range(8):
                for v in (d, length - 1 - d):
                    xy = (v, t) if horizontal else (t, v)
                    pixels[xy] = tuple(
                        (c * d + a * (8 - d)) // 8 for c, a in zip(pixels[xy], avg)
                    )
    return image


def seam(error):
    """Minimum-error path down an overlap, preserving original pixel clusters."""
    w, h = error.size
    pixels = error.load()
    costs = [pixels[x, 0] for x in range(w)]
    parents = []
    for y in range(1, h):
        previous, following = [], []
        for x in range(w):
            parent = min(range(max(0, x - 1), min(w, x + 2)), key=lambda xx: costs[xx])
            previous.append(parent)
            following.append(costs[parent] + pixels[x, y])
        parents.append(previous)
        costs = following
    path = [min(range(w), key=lambda x: costs[x])]
    for row in reversed(parents):
        path.append(row[path[-1]])
    return list(reversed(path))


def meadow(source):
    """Deterministic image quilting from the actual reference material.

    Irregular minimum-error seams avoid repeated 256px stamps and grid overlays.
    Samples retain their original pixels; no Gaussian blur or invented noise.
    """
    size, patch, overlap = 768, 128, 24
    step = patch - overlap
    canvas = Image.new("RGB", (size + patch, size + patch))
    rng = random.Random("dungeon-map-reference-meadow-v1")
    for y in range(0, size, step):
        for x in range(0, size, step):
            old = canvas.crop((x, y, x + patch, y + patch))
            choices = []
            for _ in range(12):
                sx, sy = rng.randrange(source.width - patch + 1), rng.randrange(
                    source.height - patch + 1
                )
                candidate = source.crop((sx, sy, sx + patch, sy + patch))
                error = ImageChops.difference(old, candidate).convert("L")
                score = 0
                if x:
                    score += ImageStat.Stat(error.crop((0, 0, overlap, patch))).sum[0]
                if y:
                    score += ImageStat.Stat(error.crop((0, 0, patch, overlap))).sum[0]
                choices.append((score, candidate, error))
            _, candidate, error = min(choices, key=lambda entry: entry[0])
            mask = Image.new("L", (patch, patch), 255)
            d = ImageDraw.Draw(mask)
            if x:
                for row, cut in enumerate(seam(error.crop((0, 0, overlap, patch)))):
                    d.line((0, row, cut, row), fill=0)
            if y:
                top = error.crop((0, 0, patch, overlap)).transpose(
                    Image.Transpose.TRANSPOSE
                )
                for col, cut in enumerate(seam(top)):
                    d.line((col, 0, col, cut), fill=0)
            canvas.paste(candidate, (x, y), mask)
    return canvas.crop((0, 0, size, size))


def build():
    OUT.mkdir(parents=True, exist_ok=True)
    assets = sprites(
        "village",
        "village.png",
        [
            ("tree_1", cell(0, 0), (124, 148)),
            ("tree_2", cell(1, 0), (128, 148)),
            ("tree_3", cell(2, 0), (118, 140)),
            ("bush", cell(3, 0), (38, 32)),
            # Reviewed custom boxes: the broad second roof crosses a regular grid cell.
            ("house_1", (10, 370, 300, 640), (192, 136)),
            ("house_2", (310, 370, 685, 640), (224, 152)),
            ("house_3", (695, 370, 955, 640), (192, 136)),
            ("recovery_tent", cell(3, 1), (148, 136)),
            ("barrel", cell(0, 2), (26, 36)),
            ("crate", cell(1, 2), (32, 36)),
            ("rock", cell(2, 2), (28, 24)),
            ("well", cell(3, 2), (48, 46)),
            ("flower", cell(0, 3), (22, 16)),
            ("grass_tuft", cell(1, 3), (20, 14)),
            ("planter", cell(2, 3), (38, 28)),
            ("pebbles", cell(3, 3), (22, 14)),
        ],
    )
    specs = [
        ("ruin", (44, 66)),
        ("statue", (44, 64)),
        ("boulder", (38, 42)),
        ("moss", (26, 20)),
        ("obelisk", (46, 84)),
        ("crystal", (42, 66)),
        ("tomb", (42, 48)),
        ("broken_column", (42, 40)),
        ("torch", (28, 52)),
        ("candle", (24, 50)),
        ("banner", (38, 64)),
        ("bones", (25, 18)),
        ("ritual", (250, 250)),
        ("altar", (64, 48)),
        ("web", (38, 38)),
        ("mushroom", (20, 18)),
    ]
    assets.update(
        sprites(
            "dungeon",
            "dungeon.png",
            [(name, cell(i % 4, i // 4), size) for i, (name, size) in enumerate(specs)],
        )
    )
    interior = Image.open(SOURCE / "interior.png")
    iw, ih = interior.size

    def box(x1, y1, x2, y2):
        return tuple(
            round(v * bound) for v, bound in zip((x1, y1, x2, y2), (iw, ih, iw, ih))
        )

    assets.update(
        sprites(
            "interior",
            "interior.png",
            [
                ("counter", box(0, 0, 0.30, 0.33), (248, 64)),
                ("table", box(0.31, 0, 0.53, 0.33), (88, 60)),
                ("chair", box(0.56, 0, 0.73, 0.33), (22, 32)),
                ("bench", box(0.77, 0, 1, 0.33), (32, 22)),
                ("shelf", box(0, 0.34, 0.24, 0.65), (30, 32)),
                ("board", box(0.28, 0.34, 0.49, 0.65), (112, 64)),
                ("rug", box(0.51, 0.34, 0.74, 0.65), (248, 168)),
                ("door", box(0.78, 0.34, 1, 0.65), (30, 32)),
                ("forge", box(0, 0.66, 0.25, 1), (64, 64)),
                ("alchemy", box(0.27, 0.66, 0.50, 1), (64, 54)),
                ("standing_torch", box(0.56, 0.66, 0.73, 1), (24, 64)),
                ("planks", box(0.77, 0.66, 1, 1), (32, 18)),
            ],
        )
    )
    # Reconstructed only where the supplied environment guide occludes the object.
    # The untouched guide remains in art/characters/references.
    service_source = Image.open(SOURCE / "service-interiors-reference.png")
    service_names = [
        ("service_forge", (104, 144)),
        ("service_anvil", (56, 42)),
        ("service_tools", (90, 70)),
        ("service_potions", (80, 110)),
        ("service_alchemy", (104, 80)),
        ("service_goods", (80, 110)),
        ("service_counter", (120, 70)),
        ("service_mirror", (64, 100)),
        ("service_chair", (48, 64)),
        ("service_barber_sign", (32, 56)),
        ("service_bed", (64, 80)),
        ("service_barrels", (56, 40)),
        ("garden_fence", (96, 58)),
        ("garden_steps", (92, 52)),
        ("garden_planter", (70, 52)),
        ("market_stall", (132, 120)),
    ]
    # Reviewed gutters differ from a regular grid: preserve the complete fireplace
    # and exclude the previous row's base from desks, chairs and barrels.
    sx = [0, 320, 630, 950, service_source.width]
    sy = [0, 360, 660, 970, service_source.height]
    assets.update(
        sprites(
            "services",
            "service-interiors-reference.png",
            [
                (name, (sx[i % 4], sy[i // 4], sx[i % 4 + 1], sy[i // 4 + 1]), size)
                for i, (name, size) in enumerate(service_names)
            ],
        )
    )
    source = Image.open(SOURCE / "materials.png").convert("RGB")
    for i, name in enumerate(
        ["grass", "path", "ruins", "ritual", "ruins_wall", "ritual_wall"]
    ):
        x, y = i % 3 * 512, i // 3 * 512
        crop = source.crop((x, y, x + 512, y + 512))
        crop = crop.resize((256, 256), Image.Resampling.NEAREST)
        if name == "grass":
            crop = meadow(crop)
        if name in ("ritual", "ritual_wall"):
            crop = crop.point(lambda c: c * 82 // 100)
        crop = periodic(crop)
        crop = crop.quantize(colors=96, method=Image.Quantize.MEDIANCUT)
        crop.save(OUT / (name + ".png"), optimize=True)

    # Newly authored interior plank material. Same warm, restrained family;
    # no invented change to the Guild's furnishing or interaction coordinates.
    wood = Image.new("RGB", (256, 256), "#493b32")
    d = ImageDraw.Draw(wood)
    for row in range(16):
        for col in range(-1, 4):
            x, y = col * 96 + row % 2 * 48, row * 16
            base = ["#79583e", "#70513c", "#7c5b41", "#74533a"][(row + col) % 4]
            d.rectangle((x + 1, y + 1, x + 94, y + 14), fill=base)
            d.line((x + 3, y + 2, x + 92, y + 2), fill="#8d6948")
            d.line((x + 12, y + 7, x + 52, y + 8), fill="#684b36")
            d.line((x + 43, y + 11, x + 82, y + 11), fill="#826044")
    wood.save(OUT / "wood.png", optimize=True)
    manifest = {
        "version": 1,
        "assets": assets,
        "files": {
            p.name: {"sha256": digest(p), "bytes": p.stat().st_size}
            for p in sorted(OUT.iterdir())
            if p.suffix in (".png", ".json") and p.name != "manifest.json"
        },
        "sources": {p.name: digest(p) for p in sorted(SOURCE.glob("*.png"))},
    }
    encoded = json.dumps(manifest, indent=2) + "\n"
    (OUT / "manifest.json").write_text(encoded)
    (ROOT / "frontend/src/visual/map-atlas.json").write_text(encoded)
    print("Map atlas bytes:", sum(v["bytes"] for v in manifest["files"].values()))


if __name__ == "__main__":
    build()
