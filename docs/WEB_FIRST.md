# Web First — 0.8

## Loja e recuperação — UX atual 0.9

Comércio em cards responsivos, pesquisa nos dois sentidos, quantidade/TUDO/MAX e total exato. Confirmação integrada sem browser dialogs nas compras/vendas, stale quote exige nova revisão. Recuperação abre pelo NPC encapuzado na vila; consulta remota não permite pagamento à distância. [Especificação](lunar/GUILD_SHOP_RECOVERY_UX.md).


## Carteira e comércio físico consolidados

Web lê quantidades reais das três denominações, separando saldo total e liquidez; não decompõe preço para inventar composição de caixa. Loja permite quantidade por stack, compra/venda por políticas independentes e estoque finito; minério negocia lote inteiro com rates distintos. Admin apresenta preços/histórico, exchange e rebalanceamento manual, com pending e tratamento de stale/sem troco/sem estoque. Testes Chromium desktop/390 px em [entrega atual](lunar/DELIVERY_PHYSICAL_COMMERCE_0.9.md).


## Web atual: lotes variáveis e Administração Real

Carteira/inventário mostram identidade e peso de cada pepita. Divisão permite fragmentos inteiros sem tarifa, com capacidade conjunta; Guilda mostra rate800 milliunits/g inicial e cotação individual/confirmada. Mapa preserva ocorrência e peso variável em F5/reconnect. Administração do Rei oferece as dez áreas com mint parcial, confisco, transferências e controles extraordinários explícitos. Fluxos principais cobertos em Chromium390 px, sem hover obrigatório. [Entrega](lunar/DELIVERY_VARIABLE_NUGGETS_0.9.md) · [Tesouro Real](lunar/ROYAL_ADMINISTRATION.md).


> Atualização da continuação 0.9: [cutover operacional, migrações e validação](lunar/CUTOVER.md). O upgrade não converte o ambiente: confirmação administrativa ativa Lunar como fonte única. As descrições financeiras legadas e de conversão inativa abaixo registram a etapa anterior; após a confirmação, holdings Lunar e obrigações separadas são autoritativos. Discord segue estritamente read-only; Godot congelado.

> **Estratégia atual 0.9:** backend autoritativo, **Web como cliente principal**, **Discord estritamente read-only para gameplay**. Godot Windows/Android estão **FROZEN**; APK/EXE não são requisitos deste ciclo. Código/presets/builds e documentação histórica preservados. Ver [GODOT_FREEZE.md](GODOT_FREEZE.md) e [CONSOLIDATION_0.9.md](CONSOLIDATION_0.9.md). Descrições de equipamento confirmado via Discord abaixo são históricas e foram desativadas em 0.9.

Backend autoritativo → navegador principal → Discord somente observação. Godot permanece preservado. Sem reescrita do React/TypeScript/Phaser, nem exigência de executáveis Windows/APK nesta entrega.

Web implementa exploração por teclado/clique/toque, caminhos de grade, saídas, destinos permanentes descobertos, combate individual/grupos, atributos, equipamentos, inventário, expedições, Guilda, recuperação, leilões, histórico, coleta e contratos. Restrições/custos são validados no backend; interfaces não concedem moedas, dano, teleporte ou direitos de outro jogador.

`/state` reúne estado do personagem e painéis usados com frequência. Polling em aba visível, uma requisição por ciclo, respostas antigas descartadas, timeout, pausa após três falhas e atualização manual. WebSocket reconecta até cinco vezes com atraso crescente; sessão revogada expira na UI. Recarregar restaura encontro/expedição, não zera progresso. Operações mutáveis passam pelo gate da UI e por locks/recibos no servidor; erro de rede não dispara repetição automática de pagamento.

Mapa/Phaser só é carregado depois do login; cores regionais, nome do NPC, saídas, categoria de inimigo, alvo selecionado, dano e morte dão feedback sem assets externos pesados. Efeitos limitados a 30 FPS, shake respeita preferência por movimento reduzido. Áudio sintetizado original começa mudo, tem volume/silêncio persistidos e falha sem interromper o jogo quando WebAudio não está disponível. Cliques e toque compartilham caminho validado, botões têm estados de espera/custo/eligibilidade.

Layout adaptável desktop/mobile; testes Chromium em 390 px verificam coleta e contratos. Isso não substitui testes em aparelhos reais ou auditoria completa de acessibilidade. Phaser ainda é grande e o snapshot faz muitas consultas; relatório técnico em [BALANCE_REPORT_0.8.md](BALANCE_REPORT_0.8.md).

Godot não foi reexportado/retestado nesta etapa. Diretório inteiro preservado; campos/rotas antigos continuam. Sua UI não apresenta todos os sistemas novos, e um encontro iniciado na Web deve preferencialmente ser concluído nela; ação legada delega ao coordenador de grupo, sem ignorar regras. Não há declaração de compatibilidade gráfica nativa para recursos 0.8 ausentes de suas telas.


## Continuação procedural Lunar 0.9

A Web mostra marcador☾, peso, coleta com pending, inventário de pepitas e cotação/venda à Guilda; suporta 390 px sem hover. Ver [recursos Lunares](lunar/PROCEDURAL_RESOURCES.md).
