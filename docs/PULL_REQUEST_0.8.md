# Dungeon Game 0.8 — Web principal, grupos persistentes e contratos financiados

Base de implementação: `feature/procedural-economy-godot-fixes` (`370b14f`). Branch: `feature/web-discord-first-floor-0.8`. Destino sugerido de revisão: a branch base 0.7, para mostrar somente o delta 0.8; eventual integração em main requer revisão explícita das entregas anteriores. Sem merge automático ou force push.

O gerador 0.7 nunca alcançava o máximo em faixas variáveis; a cauda transformada agora permite máximos raros, preservando os bins anteriores fora da cauda e os monstros existentes. React/Phaser volta a ser o cliente principal com polling consolidado/reconexão, grupos opt-in persistentes, coleta finita e contratos pagos por reserva real do Tesouro. Discord consulta o mesmo estado e oferece somente equipamento confirmado como mutação inicial.

Grupos reutilizam Battle/XP/loot/expedição, um recibo por inimigo. Coleta respeita estoque, propriedade, capacidade e stacks. Contratos reservam todo orçamento, só contam ações posteriores à aceitação e conservam pagamentos concluídos após cancelamento. Reserva entra na reconciliação oficial. ADM mantém permissão, justificativa, prévia, confirmação, rejeição de estado alterado e auditoria.

Migrações aditivas (em ordem): `76be3b21ba40`, `4f7ba7966ca8`, `e70ea918061f`, `947647462008`, `4cee57744ea1`. Backup/cópia 0.7 e fixture representativa comprovam preservação de campos antigos; nenhuma penalidade retroativa ou reset. Campos novos de duração histórica continuam desconhecidos. Godot e binários nativos existentes preservados.

Validação e números finais: [DELIVERY_0.8.md](DELIVERY_0.8.md). Suites PostgreSQL, sete cenários Chromium, TypeScript/Vite, imagens Docker, Alembic e reinício com hashes de todas as tabelas. CI novo prepara testes de backend/Web sem exportar Godot.

Pendências declaradas: conexão real Discord sem credenciais, ensaios com jogadores/carga pública, broker antes de múltiplos workers, snapshot SQL ainda custoso e bundle Phaser grande embora adiado até login. Grupos são perigosos para iniciantes segundo simulações; individuais não foram alterados. Não implementados novos andares, raids cooperativas, classes, habilidades avançadas ou mercado geral. Nenhuma alegação de resolução do alerta histórico de antivírus Windows por esta entrega Web.
