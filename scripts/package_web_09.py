"""Package built0.9 Web assets only; inspect CRC and every file's SHA256."""

from pathlib import Path
import hashlib
import json
import subprocess
import zipfile

root = Path(__file__).resolve().parents[1]
commit = subprocess.check_output(
    ["git", "rev-parse", "HEAD"], cwd=root, text=True
).strip()
source = root / "frontend/dist"
assert (source / "index.html").is_file() and (
    source / "admin.html"
).is_file(), "Run npm run build first"
files = {
    str(p.relative_to(source)): p.read_bytes()
    for p in sorted(source.rglob("*"))
    if p.is_file() and not p.is_symlink()
}
assert all(not any(part.startswith(".") for part in Path(name).parts) for name in files)
assert not any(
    Path(name).suffix.lower() in {".exe", ".apk", ".pck", ".dump", ".env"}
    for name in files
)
info = {
    "version": "0.9.0-web-npc-economy-development",
    "source_commit": commit,
    "backend_schema": "7167b684d5f7",
    "files": {name: hashlib.sha256(data).hexdigest() for name, data in files.items()},
}
directory = root / "builds/development" / ("0.9.0-web-npc-economy-" + commit[:7])
directory.mkdir(parents=True, exist_ok=True)
archive = directory / "DungeonGame-Web-0.9-NPC-Economy.zip"
readme = """DUNGEON GAME0.9 — CLIENTE WEB DE DESENVOLVIMENTO

Arquivos estáticos React/TypeScript/Phaser. Requer backend desta branch
feature/autonomous-npc-economy-0.9, PostgreSQL com schema 7167b684d5f7,
proxy /api e WebSocket conforme frontend/nginx.conf.

Para jogar no Windows com Docker Desktop, siga:
docs/lunar/OPERATIONAL_NPC_ECONOMY.md
no repositório Lucassilvatech/Dungeon-game. Preserve banco e .env.
Não refaça cutover ou rebalanceamento para atualizar a interface.

Este ZIP não é executável Windows, APK ou jogo offline. Abrir index.html
via file:// não configura servidor/API. Não contém backend, banco, tokens
ou senhas. Áudio opcional começa silenciado. Não foram gerados builds nativos.
SHA256/CRC verificam integridade; não representam certificação antivírus.
"""
with zipfile.ZipFile(
    archive, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9
) as z:
    for name, data in {
        **{"dist/" + k: v for k, v in files.items()},
        "build-info.json": json.dumps(info, indent=2).encode(),
        "LEIA-ME.txt": readme.encode(),
    }.items():
        entry = zipfile.ZipInfo(name, date_time=(2026, 10, 31, 0, 0, 0))
        entry.compress_type = zipfile.ZIP_DEFLATED
        entry.external_attr = 0o100644 << 16
        z.writestr(entry, data)
with zipfile.ZipFile(archive) as z:
    assert z.testzip() is None
    manifest = json.loads(z.read("build-info.json"))
    for name, digest in manifest["files"].items():
        assert hashlib.sha256(z.read("dist/" + name)).hexdigest() == digest
sha = hashlib.sha256(archive.read_bytes()).hexdigest()
(directory / "SHA256SUMS").write_text(sha + "  " + archive.name + "\n")
(directory / "build-info.json").write_text(json.dumps(info, indent=2) + "\n")
print(
    json.dumps(
        {
            "archive": str(archive.relative_to(root)),
            "source_commit": commit,
            "files": len(files),
            "zip_crc": "PASS",
            "all_manifest_hashes": "PASS",
            "sha256": sha,
            "bytes": archive.stat().st_size,
        },
        indent=2,
    )
)
