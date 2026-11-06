> **Build Windows em investigação:** houve relato de “Falha: vírus detectado”. Não execute nem libere no antivírus enquanto a causa não for esclarecida. Hash correto significa integridade, não aprovação antivírus. Veja [relatório](../../../docs/security/WINDOWS_BUILD_TRIAGE.md) e o workflow de varredura Windows.

# Dungeon Game 0.6 — builds de desenvolvimento

Código-fonte: commit 424f97a, branch feature/godot-admin-migration.

- Windows x86-64: baixe DungeonGame-Windows.zip, extraia e execute DungeonGame.exe.
- Android: baixe DungeonGame.apk. APK assinado com chave de desenvolvimento, mínimo Android 7/API 24.
- Confira integridade em SHA256SUMS.txt.

O cliente precisa do backend Dungeon Game em execução. Configure a URL na tela de login: Windows local http://127.0.0.1:8080/api; emulador Android http://10.0.2.2:8080/api; telefone físico deve usar o endereço alcançável do servidor.

Builds exportados e verificados na nuvem. Execução nativa em Windows e dispositivo Android ainda não validada; fluxo do cliente testado no Godot Linux/headless. Phaser e main preservados.
