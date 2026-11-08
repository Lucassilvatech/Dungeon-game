"""Validate source identity, complete catalog layers, shading masks and frame contact."""

from pathlib import Path
import hashlib, json
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]


def validate():
    folder = ROOT / "frontend/public/assets/characters"
    manifest = json.loads((folder / "manifest.json").read_text())
    originals = json.loads(
        (ROOT / "art/characters/references/manifest.json").read_text()
    )
    catalog = json.loads((ROOT / "backend/app/appearance_catalog.json").read_text())
    expected = {"body-" + v["id"] for v in catalog["options"]["sexo_visual"]}
    expected |= {"hair-" + v["id"] for v in catalog["options"]["hair_style_id"]}
    for slot in ["head", "torso", "legs", "feet"]:
        expected |= {
            slot + "-" + v["id"]
            for v in catalog["options"]["appearance_" + slot]
            if v["id"] != "none"
        }
    assert expected == set(manifest["layers"])
    sheets = {}
    for id, layer in manifest["layers"].items():
        p = folder / layer["file"]
        assert hashlib.sha256(p.read_bytes()).hexdigest() == layer["sha256"]
        im = Image.open(p).convert("RGBA")
        sheets[id] = im
        assert im.size == (512, 1152)
        assert set(im.getchannel("A").get_flattened_data()) <= {0, 255}
        for frame in range(96):
            crop = im.crop(
                (
                    frame % 8 * 64,
                    frame // 8 * 96,
                    frame % 8 * 64 + 64,
                    frame // 8 * 96 + 96,
                )
            )
            assert crop.getbbox(), (id, frame)
        if layer.get("mask"):
            mask = Image.open(folder / layer["mask"])
            assert mask.size == im.size
            for p, b in zip(mask.get_flattened_data(), im.get_flattened_data()):
                assert not p[3] or b[3]

    def frame(sheet, n):
        return sheet.crop((n % 8 * 64, n // 8 * 96, n % 8 * 64 + 64, n // 8 * 96 + 96))

    walking = []
    for sex in ["masculino", "feminino"]:
        composite = Image.new("RGBA", (512, 1152))
        for name in [
            "body-" + sex,
            "legs-simple_trousers",
            "feet-leather_boots",
            "torso-adventurer_tunic",
            "hair-short_spiky",
        ]:
            composite.alpha_composite(sheets[name])
        for d in range(4):
            poses = [frame(composite, 16 + d * 8 + i) for i in range(8)]
            unique = len({p.tobytes() for p in poses})
            assert unique == 8, (sex, d, unique)
            assert all(p.getbbox()[3] == 94 for p in poses), (sex, d, "foot contact")
            walking.append(dict(sex=sex, direction=d, unique_frames=unique, feet_y=94))
    # Original files are audited against the import manifest, not generated output.
    for row in originals["originals"]:
        path = ROOT / "art/characters/references" / row["file"]
        assert hashlib.sha256(path.read_bytes()).hexdigest() == row["sha256"]
    result = dict(
        status="PASS",
        originals=4,
        layers=len(expected),
        frames_per_layer=96,
        directions=4,
        walking=walking,
        source="Source and derived image inspection; browser proofs are separate",
    )
    (ROOT / "artifacts/appearance/asset-validation.json").write_text(
        json.dumps(result, indent=2) + "\n"
    )
    print(json.dumps(result))


if __name__ == "__main__":
    validate()
