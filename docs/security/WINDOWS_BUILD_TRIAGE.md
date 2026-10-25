# Windows build 0.6 — investigação de bloqueio

**Não recomendar execução nem liberação no antivírus enquanto a investigação estiver pendente.**

O usuário relatou “Falha: vírus detectado” ao baixar o build Windows. Ainda não recebemos o nome da ameaça ou o produto responsável; não é correto concluir que seja falso positivo ou simplesmente SmartScreen. Não foi gerado outro executável para tentar contornar o bloqueio.

Arquivo reportado: DungeonGame-Windows.zip (SHA256 cbb4dafb3eafb37e12895d9d3b685003f0eaefe68d77fb1aa7ba5525550fe090), contendo DungeonGame.exe (SHA256 c3475a6c1a12a6860559ebc8893104f2b98c05fc002a719b2404a07538eacbc9).

Verificações locais executadas:

- SHA512 do arquivo de templates corresponde ao manifesto oficial Godot 4.6.3.
- CRC do ZIP e igualdade do EXE extraído com o arquivo exportado confirmados.
- Seções de código/dados do motor (.text, .rdata, .data e demais seções originais) idênticas ao template oficial; diferenças em recursos e pacote do projeto são esperadas da exportação.
- Não há assinatura Authenticode no build nem no template de origem. Isso não demonstra a causa deste alerta e não equivale a um resultado antivírus.
- Scripts de runtime não invocam shell, PowerShell, subprocessos ou download de executáveis; HTTP/WebSocket e sessão local pertencem ao cliente do jogo.

Relatório de origem em windows-0.6-origin.json. A verificação anterior de HTTP 200/SHA256 validou entrega e integridade, **não ausência de malware**. O teste Godot em Linux não substitui verificação de segurança em Windows.

O workflow windows-build-scan.yml verifica os hashes, extrai o mesmo ZIP e pede uma varredura ao Microsoft Defender com assinaturas atualizadas, sem executar o jogo nem adicionar exclusões/desativar proteção. Salva versão do motor/assinaturas, resultado e detecções como artefato. Scanner indisponível ou erro deve falhar, não ser registrado como arquivo aprovado. Mesmo um resultado sem detecção nesse ambiente não autoriza ignorar uma detecção local diferente.

Se o nome da ameaça estiver disponível em Histórico de proteção do Windows, registrar produto, nome, versão/horário da assinatura e hash afetado. Com esses dados, encaminhar o caso ao fornecedor para análise de possível falso positivo. Assinatura de distribuição exigirá certificado legítimo; certificado autoassinado não comprova segurança nem substitui a investigação.

Durante a investigação, o cliente web existente pode ser utilizado com o backend, sem executar este EXE.
