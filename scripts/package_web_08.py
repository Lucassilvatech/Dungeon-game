"""Package only the built static Web client; no executables, credentials or backend state."""

from pathlib import Path
import hashlib, json, subprocess, zipfile

root = Path(__file__).resolve().parents[1]
commit = subprocess.check_output(
    ["git", "rev-parse", "HEAD"], cwd=root, text=True
).strip()
source = root / "frontend/dist"
assert (source / "index.html").is_file() and (
    source / "admin.html"
).is_file(), "Run npm run build in frontend first"
files = {
    str(p.relative_to(source)): p.read_bytes()
    for p in sorted(source.rglob("*"))
    if p.is_file() and not p.is_symlink()
}
assert all(not any(part.startswith(".") for part in Path(name).parts) for name in files)
info = {
    "version": "0.8.0-web-development",
    "source_commit": commit,
    "backend_schema": "4cee57744ea1",
    "files": {name: hashlib.sha256(data).hexdigest() for name, data in files.items()},
}
directory = root / "builds/development" / ("0.8.0-web-" + commit[:7])
directory.mkdir(parents=True, exist_ok=True)
archive = directory / "DungeonGame-Web-0.8.zip"
readme = """DUNGEON GAME 0.8 — BUILD WEB DE DESENVOLVIMENTO

Conteúdo estático React/TypeScript/Phaser para servidor HTTP. Requer backend FastAPI/PostgreSQL 0.8 (schema 4cee57744ea1), API em /api e proxy WebSocket. Não é aplicativo Windows nem APK; abrir index.html diretamente por file:// não configura o backend.

Para jogar a versão completa, use o checkout da branch feature/web-discord-first-floor-0.8 e os comandos Docker Compose do README. Este ZIP permite revisar/publicar os arquivos de frontend/dist no servidor Web já configurado. Preserve a pasta assets e admin; Nginx deve usar fallback de SPA e proxy /api conforme frontend/nginx.conf. Use TLS em publicação externa.

Áudio opcional começa silenciado. Nenhuma senha/token/banco está incluída. SHA256 verifica integridade; não constitui certificação de ausência de malware. Esta entrega não resolve nem substitui a investigação histórica do executável Windows.
"""
with zipfile.ZipFile(
    archive, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9
) as z:
    for name, data in {
        **{"dist/" + k: v for k, v in files.items()},
        "build-info.json": json.dumps(info, indent=2).encode(),
        "LEIA-ME.txt": readme.encode(),
    }.items():
        entry = zipfile.ZipInfo(name, date_time=(2026, 10, 26, 0, 0, 0))
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
    f"PASS: {archive.relative_to(root)}; {len(files)} static files; ZIP CRC and all manifest hashes verified; SHA256 {sha}"
)
