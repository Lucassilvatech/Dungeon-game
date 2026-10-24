# Masmorras secretas — contém spoilers de desenvolvimento

A demonstração tem a Cripta da Maré Antiga (id interno secret), no primeiro andar, recomendada para nível 8. HP 90 e ataque 14 são configuração própria, sem fórmula baseada no andar. É possível configurar nível 999 sem alterar floor_id. Novas masmorras devem ser definidas no conteúdo/seed por migração aditiva.

`SECRET_CHANCE` (0–1, padrão .25) controla descoberta em Aventura. A descoberta fica em RoomState por personagem e gera evento único. Antes dela, `/state` só apresenta contagem found/total; não retorna nome, codex, nível, inimigo ou prêmio. Tentar entrar por ID sem descoberta responde 404. O atlas de outro jogador permanece independente.

Após descobrir, o atlas revela nome/entrada, mantendo codex vazio até entrar/encontrar conteúdo. `POST /dungeons/{id}/enter` permite retornar diretamente. Ao entrar numa sala, inimigos visíveis são marcados como encontrados no codex; derrotá-los acrescenta informação de derrota. O mapa interno só é retornado quando a sala é atual.

Derrota encerra a tentativa e envia à cidade com vida/energia restauradas: não altera equipamento, moedas, XP ou descoberta. A opção Voltar à cidade exige terminar o combate antes de sair. A primeira vitória marca completed e SECRET_DUNGEON_COMPLETED uma única vez. A recompensa monetária fica congelada no combate e é reivindicada normalmente na Guilda, com débito real do Tesouro.

Parâmetros provisórios: primeira recompensa 250 moedas, repetição 1; primeira vitória dá 100 XP e um cristal; repetições dão zero XP e nenhum cristal. `SECRET_FIRST_REWARD` e `SECRET_REPEAT_REWARD` são não negativos e configuráveis. Sem orçamento, o direito permanece pendente, como na versão 1. Não há emissão de moedas na vitória.

A instância é pessoal, não uma masmorra compartilhada com combate de raid. Esse é o próximo passo, junto com várias salas internas e bestiário mais detalhado. A sala demonstrativa tem apenas seu chefe. Tests cobrem spoilers, acesso indevido, persistência, derrota, primeira conclusão, repetição e conservação monetária.

Na versão 0.3, inimigos mortos permanecem DEAD na geração atual. Nova entrada explícita a partir de fora inicia outra geração de tentativa, com IDs novos; atualizar a interface não reinicia o encontro. A conclusão permanente e a redução de recompensa são preservadas.
