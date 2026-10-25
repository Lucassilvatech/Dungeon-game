# Windows build 0.6 — investigação de bloqueio

**Não recomendar execução nem liberação no antivírus enquanto a investigação estiver pendente.**

O usuário relatou “Falha: vírus detectado” ao baixar o build Windows. A captura recebida confirma **Microsoft Defender: Trojan:Script/Wacatac.B!ml**, severidade Grave e status Em quarentena, afetando o ZIP baixado e o cache/download parcial do Opera GX. O alerta aponta o link publicado no commit 18ec8e5. Não é somente aviso do SmartScreen e não é correto concluir automaticamente que seja falso positivo. Não foi gerado outro executável para tentar contornar o bloqueio. A captura original contém caminhos locais do usuário e não foi publicada.

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

## Resultado independente inicial

O workflow [40236131027](https://github.com/Lucassilvatech/Dungeon-game/actions/runs/40236131027) passou no Windows runner: verificação dos hashes, Microsoft Defender ativo, atualização das assinaturas e scan do ZIP/EXE concluídos com retorno zero e sem detecções nesse ambiente. O status da execução e da etapa de varredura foi consultado publicamente. O relatório detalhado fica no artefato windows-defender-report; não foram inventadas versões de assinatura ausentes dessa consulta. Isso **não** invalida a detecção local Wacatac.B!ml nem confirma falso positivo. A configuração de proteção em nuvem também será capturada para investigar diferenças de contexto, sem modificar/desativar proteção.

A segunda execução capturou `CloudMAPS=0` no runner (engine 1.1.26090.9, assinaturas 1.461.202.0): [40236648088](https://github.com/Lucassilvatech/Dungeon-game/actions/runs/40236648088). Portanto esse teste não reproduz por completo uma detecção dependente de aprendizado/proteção em nuvem. O workflow foi reforçado para ativar MAPS e bloqueio no primeiro encontro no runner descartável, mantendo a proteção, verificar a conexão com a Microsoft e repetir a análise do **mesmo arquivo/hash**, sem reempacotamento. Erro de conexão/configuração não será contado como aprovação.
