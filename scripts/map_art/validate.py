"""Asset evidence: silhouette/alpha, foot contact, eight complete poses and hashes."""

from pathlib import Path
import hashlib
import json
import subprocess
from io import BytesIO
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "artifacts/map-rebuild"


def frame(sheet, n):
    return sheet.crop((n % 8 * 48, n // 8 * 64, (n % 8 + 1) * 48, (n // 8 + 1) * 64))


def validate():
    OUT.mkdir(parents=True, exist_ok=True)
    manifest = json.loads((ROOT / "frontend/src/visual/map-atlas.json").read_text())
    folder = ROOT / "frontend/public/assets/maps"
    for filename, metadata in manifest["files"].items():
        assert (
            hashlib.sha256((folder / filename).read_bytes()).hexdigest()
            == metadata["sha256"]
        )
    for name in ("village", "dungeon", "interior", "services"):
        sheet = Image.open(folder / (name + ".png")).convert("RGBA")
        assert set(sheet.getchannel("A").get_flattened_data()) <= {0, 255}
        atlas = json.loads((folder / (name + ".json")).read_text())
        for key, entry in atlas["frames"].items():
            f = entry["frame"]
            crop = sheet.crop((f["x"], f["y"], f["x"] + f["w"], f["y"] + f["h"]))
            assert crop.getbbox(), key
            assert (crop.width, crop.height) == (
                manifest["assets"][key]["width"],
                manifest["assets"][key]["height"],
            )
    checked = []
    for name in [
        "hero",
        "peer",
        "merchant",
        "alchemist",
        "blacksmith",
        "npc",
        "goblin",
        "goblin_elite",
    ]:
        sheet = Image.open(ROOT / f"frontend/public/assets/pixel/{name}.png")
        old_data = subprocess.check_output(
            ["git", "show", f"9260f4f:frontend/public/assets/pixel/{name}.png"],
            cwd=ROOT,
        )
        before = Image.open(BytesIO(old_data))
        for direction in range(4):
            assert (
                frame(before, direction * 4).tobytes()
                == frame(sheet, direction * 4).tobytes()
            ), (name, "approved idle identity")
            poses = [frame(sheet, 16 + direction * 8 + i) for i in range(8)]
            assert len({p.tobytes() for p in poses}) == 8, (
                name,
                direction,
                "distinct poses",
            )
            for p in poses:
                assert p.getbbox()[3] == 62, (name, direction, "planted feet")
        checked.append(name)
    hero = Image.open(ROOT / "frontend/public/assets/pixel/hero.png")
    contact = Image.new("RGB", (8 * 72, 4 * 80), "#526d51")
    for direction in range(4):
        for phase in range(8):
            crop = frame(hero, 16 + direction * 8 + phase)
            contact.paste(crop, (phase * 72 + 12, direction * 80 + 8), crop)
            ImageDraw.Draw(contact).line(
                (phase * 72, direction * 80 + 70, phase * 72 + 71, direction * 80 + 70),
                fill="#8e9a72",
            )
    contact.save(OUT / "walk-contact-sheet.png")
    result = {
        "status": "PASS",
        "map_sprites": len(manifest["assets"]),
        "alpha": "binary",
        "identity_preserved": checked,
        "unique_walk_frames_per_direction": 8,
        "directions": 4,
        "foot_row": 61,
        "source": "atlas inspection; real in-game motion is recorded separately",
    }
    (OUT / "asset-validation.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result))


if __name__ == "__main__":
    validate()
