# Discord 0.9 — somente observação

> Atualização da continuação 0.9: [cutover operacional, migrações e validação](lunar/CUTOVER.md). O upgrade não converte o ambiente: confirmação administrativa ativa Lunar como fonte única. As descrições financeiras legadas e de conversão inativa abaixo registram a etapa anterior; após a confirmação, holdings Lunar e obrigações separadas são autoritativos. Discord segue estritamente read-only; Godot congelado.

**Discord cannot control the character.** Backend autoritativo, Web principal, Discord somente consultas privadas do personagem vinculado. Não há economia/inventário/progresso paralelo.

Comandos: `/vincular`, `/personagem`, `/status`, `/atributos`, `/inventario`, `/equipamentos`, `/localizacao`, `/mapa`, `/expedicao`, `/recompensas`, `/divida`, `/leiloes`, `/contratos`, `/carteira`, `/minerio`, `/recuperacao`. Total 16 sem duplicações. Respostas e erros efêmeros, menções escapadas/desativadas, sem botões ou tokens. Saldo/massa Lunar exatos; conversão continua inativa e explicitamente identificada. Somente salas conhecidas do personagem; leilões relacionados e próprios holds, não identidade financeira de terceiros.

Removidos `/equipar`, EquipmentConfirmation e funções públicas de preview/confirm do adaptador. POST `/discord/{discord_id}/equipment/preview` e `/discord/{discord_id}/operations/{id}/confirm` são tombstones **410 Gone** após autenticar serviço, sem parsing/execução de intenção. Modelo DiscordOperation, registros antigos e migração histórica preservados como deprecated; nenhum recibo antigo pode reativar mutação. Demais ações de gameplay sob /discord não têm rota. Chave de bot não é credencial de jogador nem ADM.

Queries executam em transação PostgreSQL REPEATABLE READ/READ ONLY e não chamam snapshot/character/sync/settle/wandering. Consultar não gera mapa, não retoma personagem, não progride contrato, não cria estoque, não completa expedição nem resolve leilão vencido. GET state antigo retorna somente projeção segura do próprio personagem. Contadores de segurança podem registrar requisições em transação separada; não fazem parte do estado de gameplay.

Identidade é a única exceção: código Web de uso único e expiração 5min via `/vincular`; vínculo exclusivo, serviço autenticado, ID de interaction.user. POST /discord/unlink exige sessão Web do proprietário. Nenhuma chave/token deve ir em mensagem. Segredos reais ficam nas configurações do ambiente.

Testes devem comparar todas as tabelas antes/depois, incluindo leilão vencido, e rejeitar explicitamente equipamento, movimento, ataque, compras/vendas, contratos, lances e divisão Lunar. Testes locais/mocks não validam sincronização/entrega no Discord externo: faltam credenciais reais; não declarar essa conexão executada.


## Continuação procedural Lunar 0.9

Consultas de inventário/mineral incluem holdings de pepitas e coletas próprias. Não revelam ocorrências disponíveis ou coordenadas; não adicionam comandos mutáveis. Ver [recursos Lunares](lunar/PROCEDURAL_RESOURCES.md).
