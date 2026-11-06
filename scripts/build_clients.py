#!/usr/bin/env python3
"""Export and package development clients with Godot 4.6.3 + configured Android SDK.
No download, signing secret generation, or remote publication happens in this script.
"""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import zipfile

root = Path(__file__).resolve().parents[1]
output = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else root / "exports"
output.mkdir(parents=True, exist_ok=True)


def run(*args):
    subprocess.run(args, cwd=root, check=True)


run("godot", "--headless", "--path", "godot-client", "--editor", "--quit")
run(
    "godot",
    "--headless",
    "--path",
    "godot-client",
    "--export-debug",
    "Windows",
    str(output / "DungeonGame.exe"),
)
run(
    "godot",
    "--headless",
    "--path",
    "godot-client",
    "--export-debug",
    "Android",
    str(output / "DungeonGame-Android.apk"),
)
readme = """Dungeon Game 0.7 — desenvolvimento
Windows x64: extraia todos os arquivos e execute DungeonGame.exe.
Android: instale DungeonGame-Android.apk; exige Android compatível e permissão para instalar o APK.
Build de desenvolvimento: APK assinado com chave de teste; EXE sem certificado Authenticode.
Nenhuma conta ou senha administrativa está embutida.

O servidor NÃO está embutido no jogo. Use um backend atualizado na mesma branch.
No computador com Git e Docker Desktop:
  git clone https://github.com/Lucassilvatech/Dungeon-game.git
  cd Dungeon-game
  git switch feature/procedural-economy-godot-fixes
  copie .env.example para .env SOMENTE se ainda não existir
  docker compose up --build -d
Windows no mesmo computador: http://127.0.0.1:8080/api
Android emulador: http://10.0.2.2:8080/api
Android físico na mesma LAN: configure FRONTEND_BIND=0.0.0.0 no .env do servidor,
reinicie docker compose up -d e use http://IP-DO-COMPUTADOR:8080/api.
Autorize apenas a rede privada no firewall. Para acesso pela internet, use HTTPS
com certificado válido, autenticação e proxy reverso; não exponha a Central ADM sem proteção.
Não publique .env, não apague volumes e não use docker compose down -v.

Informe a URL no campo Servidor do aplicativo antes de cadastrar ou entrar.
Localhost no Android pertence ao próprio aparelho. O servidor deve estar ligado.
Se o Defender detectar ameaça, mantenha a quarentena; não desative a proteção.
Uma verificação CI sem detecção não garante ausência de malware nem substitui análise local.
Detalhes: docs/PROCEDURAL_ECONOMY_UPDATE.md e docs/security/.
"""
(output / "LEIA-ME.txt").write_text(readme, encoding="utf-8")
with zipfile.ZipFile(
    output / "DungeonGame-Windows-x64.zip", "w", zipfile.ZIP_DEFLATED
) as z:
    for name in ("DungeonGame.exe", "LEIA-ME.txt"):
        z.write(output / name, name)
with zipfile.ZipFile(output / "DungeonGame-Windows-x64.zip") as z:
    assert z.testzip() is None
source = subprocess.check_output(
    ["git", "rev-parse", "HEAD"], cwd=root, text=True
).strip()
manifest = {
    "version": "0.7.0",
    "source_commit": source,
    "godot": subprocess.check_output(["godot", "--version"], text=True).strip(),
    "development": True,
    "backend_required": True,
    "artifacts": {},
}
for name in (
    "DungeonGame.exe",
    "DungeonGame-Windows-x64.zip",
    "DungeonGame-Android.apk",
):
    f = output / name
    manifest["artifacts"][name] = {
        "sha256": hashlib.file_digest(f.open("rb"), "sha256").hexdigest(),
        "bytes": f.stat().st_size,
    }
(output / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
(output / "SHA256SUMS.txt").write_text(
    "".join(f"{v['sha256']}  {k}\n" for k, v in manifest["artifacts"].items())
)
print(json.dumps(manifest, indent=2))
