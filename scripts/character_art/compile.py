"""Deterministic packing of reviewed source cut-outs, masks and articulated layer frames.
Original PNGs remain byte-identical. No full-body generic sprite is substituted.
"""

from pathlib import Path
from collections import deque
import hashlib, json, math
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[2]
REF = ROOT / "art/characters/references"
OUT = ROOT / "frontend/public/assets/characters"
W, H = 64, 96
DIRS = ["down", "left", "right", "up"]


def largest(im):
    """Remove detached extraction flecks; retain real disconnected shoe pairs."""
    a = im.getchannel("A")
    pix = a.load()
    seen = set()
    groups = []
    for y in range(im.height):
        for x in range(im.width):
            if pix[x, y] < 128 or (x, y) in seen:
                continue
            q = deque([(x, y)])
            seen.add((x, y))
            group = []
            while q:
                p = q.popleft()
                group.append(p)
                for dx, dy in [(1, 0), (-1, 0), (0, 1), (0, -1)]:
                    n = (p[0] + dx, p[1] + dy)
                    if (
                        0 <= n[0] < im.width
                        and 0 <= n[1] < im.height
                        and n not in seen
                        and pix[n] >= 128
                    ):
                        seen.add(n)
                        q.append(n)
            groups.append(group)
    if not groups:
        raise ValueError("Empty source crop")
    minimum = max(12, max(map(len, groups)) // 10)
    mask = Image.new("L", im.size)
    p = mask.load()
    for group in groups:
        # Panel separators are thin straight components, never part of a sprite.
        gw = max(x for x, y in group) - min(x for x, y in group) + 1
        gh = max(y for x, y in group) - min(y for x, y in group) + 1
        if len(group) >= minimum and not (gh > gw * 8):
            for xy in group:
                p[xy] = 255
    im.putalpha(mask)
    box = im.getbbox()
    return im.crop(box)


def cut(source, box, beige=False):
    im = source.crop(box).convert("RGBA")
    if beige:
        # Only flood background connected to edges. Light fabric enclosed by its
        # original dark contour is retained, unlike a global white-colour key.
        pixels = im.load()
        queue = deque()
        seen = set()
        for x in range(im.width):
            queue.extend([(x, 0), (x, im.height - 1)])
        for y in range(im.height):
            queue.extend([(0, y), (im.width - 1, y)])
        while queue:
            p = queue.popleft()
            if p in seen:
                continue
            seen.add(p)
            x, y = p
            r, g, b, a = pixels[p]
            neutral = min(r, g, b) > 145 and max(r, g, b) - min(r, g, b) < 30
            if a < 128 or neutral:
                pixels[p] = (0, 0, 0, 0)
                for dx, dy in [(1, 0), (-1, 0), (0, 1), (0, -1)]:
                    n = x + dx, y + dy
                    if 0 <= n[0] < im.width and 0 <= n[1] < im.height:
                        queue.append(n)
    return largest(im)


def separate_cells(source, rows):
    """Detect real transparent gutters instead of cutting through irregular cells."""
    pix = source.load()

    def groups(values, gap):
        parts = []
        for i, present in enumerate(values):
            if not present:
                continue
            if not parts or i - parts[-1][-1] > gap:
                parts.append([])
            parts[-1].append(i)
        return [(p[0], p[-1] + 1) for p in parts if len(p) > 10]

    ys = groups(
        [
            sum(pix[x, y][3] > 128 for x in range(source.width)) > 5
            for y in range(source.height)
        ],
        30,
    )
    assert len(ys) == rows, ("row segmentation", len(ys), rows)
    boxes = []
    for y1, y2 in ys:
        xs = groups(
            [
                sum(pix[x, y][3] > 128 for y in range(y1, y2)) > 4
                for x in range(source.width)
            ],
            40,
        )
        assert len(xs) == 4, ("direction segmentation", xs)
        boxes.append(
            [
                (
                    max(0, x1 - 3),
                    max(0, y1 - 3),
                    min(source.width, x2 + 3),
                    min(source.height, y2 + 3),
                )
                for x1, x2 in xs
            ]
        )
    return boxes


def placed(im, width=None, height=None, top=None, bottom=None):
    ratio = min(
        width / im.width if width else 100, height / im.height if height else 100
    )
    size = (max(1, round(im.width * ratio)), max(1, round(im.height * ratio)))
    im = im.resize(size, Image.Resampling.NEAREST)
    out = Image.new("RGBA", (W, H))
    y = top if top is not None else bottom - im.height
    out.alpha_composite(im, ((W - im.width) // 2, y))
    return out


def skin_mask(im):
    mask = Image.new("RGBA", im.size)
    for y in range(im.height):
        for x in range(im.width):
            r, g, b, a = im.getpixel((x, y))
            if a and r > 75 and r > g * 1.12 and g > b * 1.08:
                # Gray source intensity retains shading; runtime applies a skin palette.
                lum = min(255, round((r + g + b) / 3))
                mask.putpixel((x, y), (lum, lum, lum, a))
    return mask


def pose(im, mode, dir, tick, kind):
    """Rasterize joints for each frame; head/shoulders/elbows/knees share anchors.
    No interpolation of rigid top and bottom halves; every region bends locally.
    """
    if mode == "idle":
        return im.copy() if tick < 2 else deform(im, dir, 0, 0, 1, kind)
    if mode == "walk":
        phase = math.sin(tick * math.tau / 8)
        lift = math.cos(tick * math.tau / 8)
        return deform(im, dir, phase, lift, 0, kind)
    if mode == "attack":
        return deform(im, dir, math.sin((tick + 1) * math.pi / 5) * 0.8, 0, 0, kind)
    if mode == "hurt":
        out = im.copy()
        out = Image.frombytes(
            "RGBA",
            out.size,
            bytes(
                v if i % 4 != 0 else min(255, v + 20)
                for i, v in enumerate(out.tobytes())
            ),
        )
        return out
    return im.copy()


def deform(im, dir, phase, lift, breath, kind):
    out = Image.new("RGBA", (W, H))
    src = im.load()
    dst = out.load()

    def displacement(x, y):
        dx = dy = 0
        side = -1 if x < W / 2 else 1
        if y < 50:
            dx = round(phase * 0.55 + lift * 0.55)
            dy = -breath
        elif y < 74:
            dx = round(phase * 0.6 * (74 - y) / 24)
            dy = -breath if y < 60 else 0
            if x < 20 or x > 43:
                elbow = max(0, (y - 56) / 18)
                dx += round(side * phase * elbow * 2)
                dy += round(side * phase * 2)
        else:
            knee = min(1, max(0, (y - 76) / 18))
            dx = (
                round(side * phase * 3 * knee)
                if dir in (1, 2)
                else round(side * abs(phase) * knee)
            )
            dy = -round(max(0, side * phase) * (3 + lift) * knee)
        return dx, dy

    # Inverse nearest-neighbour sampling fills articulated joins. Forward-scattering
    # pixels would leave transparent seams at shoulders/waist during breathing.
    for y in range(H):
        for x in range(W):
            dx, dy = displacement(x, y)
            sx, sy = x - dx, y - dy
            if 0 <= sx < W and 0 <= sy < H:
                dst[x, y] = src[sx, sy]

    return out


def emit(id, frames, kind, manifest, source, boxes):
    modes = [("idle", 4), ("walk", 8), ("attack", 4), ("hurt", 4), ("death", 4)]
    atlas = Image.new("RGBA", (W * 8, H * 12))
    mask = Image.new("RGBA", atlas.size)
    index = 0
    for mode, count in modes:
        for d, frame in enumerate(frames):
            for tick in range(count):
                part = pose(frame, mode, d, tick, kind)
                atlas.alpha_composite(part, ((index % 8) * W, (index // 8) * H))
                if kind == "body":
                    mask.alpha_composite(
                        skin_mask(part), ((index % 8) * W, (index // 8) * H)
                    )
                index += 1
    path = OUT / (id + ".png")
    atlas.save(path, optimize=True)
    item = {
        "file": path.name,
        "kind": kind,
        "source": source,
        "source_boxes": boxes,
        "directions": DIRS,
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
    }
    if kind == "body":
        mp = OUT / (id + "-skin.png")
        mask.save(mp, optimize=True)
        item["mask"] = mp.name
    manifest["layers"][id] = item
    return frames


def build():
    OUT.mkdir(parents=True, exist_ok=True)
    manifest = {
        "version": 2,
        "anchors": {"neck": [32, 46], "waist": [32, 71], "feet": [32, 94]},
        "frame_width": W,
        "frame_height": H,
        "frames": 96,
        "columns": 8,
        "feet_y": 94,
        "layers": {},
        "original_manifest": "art/characters/references/manifest.json",
    }
    catalog = json.loads((ROOT / "backend/app/appearance_catalog.json").read_text())
    manifest["palettes"] = {
        field: {v["id"]: v["color"] for v in catalog["options"][field]}
        for field in ["skin_tone", "hair_color"]
    }
    thumbs = []
    bodyfile = ROOT / "art/characters/layers/body-occlusion-reconstruction-source.png"
    source = Image.open(bodyfile).convert("RGBA")
    for sex, row in [("masculino", 0), ("feminino", 1)]:
        boxes = []
        frames = []
        for d in range(4):
            box = (
                round(d * source.width / 4),
                round(row * source.height / 2),
                round((d + 1) * source.width / 4),
                round((row + 1) * source.height / 2),
            )
            boxes.append(box)
            frame = placed(cut(source, box), height=82, bottom=94)
            # Keep a covered body under sleeves, with hands aligned to the supplied
            # torso width. Footwear/trousers own the lower silhouette completely.
            exposed = frame.copy()
            pixels = exposed.load()
            for y in range(49, H):
                for x in range(W):
                    pixels[x, y] = (0, 0, 0, 0)
            for y in range(49, 75):
                for x in range(W):
                    if frame.getpixel((x, y))[3]:
                        pixels[round(32 + (x - 32) * 0.80), y] = frame.getpixel((x, y))
            frame = exposed
            frames.append(frame)
        emit(
            "body-" + sex,
            frames,
            "body",
            manifest,
            str(bodyfile.relative_to(ROOT)),
            boxes,
        )
        thumbs.append(("body-" + sex, frames))
    source = Image.open(REF / "02-hair-styles-four-directions.png").convert("RGBA")
    styles = [
        ("short_swept", 0, 0),
        ("short_spiky", 0, 1),
        ("side_swept", 1, 0),
        ("wild_spiky", 1, 1),
        ("medium_wavy", 2, 0),
        ("receding", 2, 1),
        ("bob", 3, 0),
        ("ponytail", 3, 1),
        ("long_straight", 4, 0),
        ("long_wavy", 4, 1),
        ("braid", 5, 0),
        ("short_curly", 5, 1),
    ]
    xs = [[65, 224, 382, 537, 697], [744, 908, 1067, 1223, 1400]]
    ys = [(26, 174), (190, 339), (359, 513), (518, 682), (680, 870), (878, 1075)]
    for style, row, col in styles:
        boxes = [(xs[col][d], ys[row][0], xs[col][d + 1], ys[row][1]) for d in range(4)]
        frames = []
        for box in boxes:
            piece = cut(source, box)
            piece = piece.resize(
                (round(piece.width * 0.31), round(piece.height * 0.31)),
                Image.Resampling.NEAREST,
            )
            frame = Image.new("RGBA", (W, H))
            frame.alpha_composite(piece, ((W - piece.width) // 2, 7))
            frames.append(frame)
        emit(
            "hair-" + style,
            frames,
            "hair",
            manifest,
            "02-hair-styles-four-directions.png",
            boxes,
        )
        thumbs.append((style, frames))
    specs = {
        "head": ["cloth_cap", "hood", "headband", "circlet", "light_helmet"],
        "torso": [
            "adventurer_tunic",
            "peasant_shirt",
            "leather_armor",
            "mage_robe",
            "smith_apron",
            "alchemist_coat",
        ],
        "legs": [
            "simple_trousers",
            "reinforced_trousers",
            "skirt",
            "shorts",
            "light_greaves",
        ],
        "feet": ["simple_shoes", "sandals", "leather_boots", "heavy_boots"],
    }
    for kind, names in specs.items():
        source_path = (
            ROOT / "art/characters/layers" / ("clothing-" + kind + "-repaired.png")
        )
        source = Image.open(source_path).convert("RGBA")
        boxes_by_row = separate_cells(source, len(names))
        for name, boxes in zip(names, boxes_by_row):
            frames = []
            for d, box in enumerate(boxes):
                piece = cut(source, box)
                if name == "light_greaves" and d == 3:
                    alternate = Image.open(
                        ROOT / "art/characters/layers/light-greaves-back-repaired.png"
                    )
                    piece = cut(alternate, (0, 0, *alternate.size))
                front = d in (0, 3)
                if kind == "head":
                    # Anatomical anchors, not unrelated crop bounding-box heights.
                    if name == "hood":
                        width, height, top = (44 if front else 36), 46, 6
                    elif name == "cloth_cap":
                        width, height, top = (40 if front else 36), 34, 8
                    elif name == "headband":
                        width, height, top = (
                            (40 if front else 36),
                            (17 if d == 0 else 25),
                            20,
                        )
                    elif name == "circlet":
                        width, height, top = (
                            (40 if front else 36),
                            (10 if d == 3 else 15),
                            (25 if d == 3 else 22),
                        )
                    else:
                        width, height, top = (42 if front else 36), 40, 7
                elif kind == "torso":
                    width = 36 if front else 24
                    height = {
                        "mage_robe": 42,
                        "alchemist_coat": 40,
                        "smith_apron": 38,
                        "leather_armor": 30,
                    }.get(name, 28)
                    top = 46
                elif kind == "legs":
                    width = (
                        (30 if front else 24)
                        if name == "skirt"
                        else (26 if front else 18)
                    )
                    height = {"shorts": 12, "skirt": 16, "light_greaves": 19}.get(
                        name, 23
                    )
                    top = 71
                else:
                    width = 28 if front else 24
                    height = 12 if name in ("leather_boots", "heavy_boots") else 9
                    top = 94 - height
                piece = piece.resize((width, height), Image.Resampling.NEAREST)
                f = Image.new("RGBA", (W, H))
                f.alpha_composite(piece, ((W - width) // 2, top))
                frames.append(f)
            emit(
                kind + "-" + name,
                frames,
                kind,
                manifest,
                str(source_path.relative_to(ROOT)),
                boxes,
            )
            if name == "light_greaves":
                manifest["layers"][kind + "-" + name]["direction_source_override"] = {
                    "up": "art/characters/layers/light-greaves-back-repaired.png"
                }
            thumbs.append((name, frames))
    (OUT / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    # Human review proof: original layers remain distinct. This is NOT a game capture.
    sheet = Image.new("RGBA", (450, len(thumbs) * 102), (36, 40, 48, 255))
    draw = ImageDraw.Draw(sheet)
    for row, (name, frames) in enumerate(thumbs):
        draw.text((2, row * 102 + 36), name, fill="white")
        for d, frame in enumerate(frames):
            sheet.alpha_composite(frame, (174 + d * 66, row * 102))
    (ROOT / "artifacts/appearance").mkdir(exist_ok=True, parents=True)
    sheet.convert("RGB").save(ROOT / "artifacts/appearance/layer-contact-sheet.png")
    print(
        "Compiled",
        len(manifest["layers"]),
        "reference layers;",
        sum(p.stat().st_size for p in OUT.glob("*.png")),
        "PNG bytes",
    )


if __name__ == "__main__":
    build()
