# Viagem rápida e Salão de Leilões

`GET /fast-travel` lista destinos permanentes elegíveis já visitados pelo personagem; `POST /fast-travel` recebe somente destination. Reutiliza RoomState no PostgreSQL; não há uma segunda lista local de desbloqueios. Uma descoberta sem visita não habilita destino (exceto a cidade inicial registrada na criação).

Destinos elegíveis atuais: city1, guild, auction_hall, training, common_a, common_b, combat e boss, todos no primeiro andar e sem proprietário privado. Cidade inicial é o ponto seguro conhecido. Segredos, procedurais e temporários não entram automaticamente. Um endereço de sala ou chave de descoberta não substitui os requisitos.

O backend bloqueia combate e expedição ativa pelos mesmos serviços de compromisso usados por saídas normais. Não se usa viagem para fugir sem penalidade. Entrar continua incrementando visitas e registrando evento; login/reconexão preservam descobertas. As conexões físicas originais permanecem livres nas salas comuns.

Guilda → Salão de Leilões usa nova porta em (35,20); o retorno do salão fica em (2,9). Leiloeiro próprio, identificação e decoração de pregão distinguem a sala. A recepcionista continua exclusivamente na recepção (`guild`); tentar resgatar recompensas no salão é rejeitado. Interagir com leiloeiro por proximidade abre a interface de leilões, não paga recompensas.

Godot apresenta os destinos na aba Caminhos e entradas físicas no mapa; web legada apresenta viagem rápida na aba Mapa. Nenhum cliente consegue autorizar um destino por conta própria. A configuração atual não acrescenta requisitos de nível artificiais a lugares que já tinham acesso livre por exploração; as restrições de progressão existentes continuam válidas.
