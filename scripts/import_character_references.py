"""Import user-provided originals without modification; reject ambiguous ZIP contents."""

import argparse
import hashlib
import io
import json
import zipfile
from pathlib import Path
from PIL import Image

NAMES = [
    "03-character-interiors-village-art-guide.png",
    "01-character-body-directions-palettes.png",
    "02-hair-styles-four-directions.png",
    "04-clothing-slots-four-directions.png",
]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("zip")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1] / "art/characters/references"
    with zipfile.ZipFile(args.zip) as archive:
        pngs = [
            n
            for n in archive.namelist()
            if n.lower().endswith(".png") and not n.startswith("__MACOSX/")
        ]
        if len(pngs) != 4:
            raise ValueError("Expected exactly the four reviewed source PNGs")
        mapping = {}
        for name in pngs:
            target = next(
                (
                    NAMES[i]
                    for i, suffix in enumerate(
                        [
                            "Guia Pixel Art do Dungeon RPG.png",
                            "17_31_02-1.png",
                            "17_31_03-2.png",
                            "17_31_04-3.png",
                        ]
                    )
                    if name.endswith(suffix)
                ),
                None,
            )
            if not target or target in mapping:
                raise ValueError("Unknown or duplicate reference: " + name)
            data = archive.read(name)
            image = Image.open(io.BytesIO(data))
            image.verify()
            mapping[target] = (name, data)
        root.mkdir(parents=True, exist_ok=True)
        manifest = []
        for target, (name, data) in mapping.items():
            output = root / target
            if output.exists() and output.read_bytes() != data:
                raise ValueError(
                    "Refusing to overwrite a different original: " + target
                )
            output.write_bytes(data)
            manifest.append(
                {
                    "file": target,
                    "archive_member": name,
                    "sha256": hashlib.sha256(data).hexdigest(),
                    "bytes": len(data),
                    "origin": "user_upload",
                    "modified": False,
                }
            )
        (root / "manifest.json").write_text(
            json.dumps(
                {"source_zip": Path(args.zip).name, "originals": manifest},
                indent=2,
                ensure_ascii=False,
            )
            + "\n"
        )
        print(
            "Imported four byte-identical original PNGs; no image reconstruction in import"
        )


if __name__ == "__main__":
    main()
