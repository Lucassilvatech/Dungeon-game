# Web First — 0.8

Backend autoritativo → navegador principal → Discord complementar. Godot permanece preservado. Sem reescrita do React/TypeScript/Phaser, nem exigência de executáveis Windows/APK nesta entrega.

Web implementa exploração por teclado/clique/toque, caminhos de grade, saídas, destinos permanentes descobertos, combate individual/grupos, atributos, equipamentos, inventário, expedições, Guilda, recuperação, leilões, histórico, coleta e contratos. Restrições/custos são validados no backend; interfaces não concedem moedas, dano, teleporte ou direitos de outro jogador.

`/state` reúne estado do personagem e painéis usados com frequência. Polling em aba visível, uma requisição por ciclo, respostas antigas descartadas, timeout, pausa após três falhas e atualização manual. WebSocket reconecta até cinco vezes com atraso crescente; sessão revogada expira na UI. Recarregar restaura encontro/expedição, não zera progresso. Operações mutáveis passam pelo gate da UI e por locks/recibos no servidor; erro de rede não dispara repetição automática de pagamento.

Mapa/Phaser só é carregado depois do login; cores regionais, nome do NPC, saídas, categoria de inimigo, alvo selecionado, dano e morte dão feedback sem assets externos pesados. Efeitos limitados a 30 FPS, shake respeita preferência por movimento reduzido. Áudio sintetizado original começa mudo, tem volume/silêncio persistidos e falha sem interromper o jogo quando WebAudio não está disponível. Cliques e toque compartilham caminho validado, botões têm estados de espera/custo/eligibilidade.

Layout adaptável desktop/mobile; testes Chromium em 390px verificam coleta e contratos. Isso não substitui testes em aparelhos reais ou auditoria completa de acessibilidade. Phaser ainda é grande e o snapshot faz muitas consultas; relatório técnico em [BALANCE_REPORT_0.8.md](BALANCE_REPORT_0.8.md).

Godot não foi reexportado/retestado nesta etapa. Diretório inteiro preservado; campos/rotas antigos continuam. Sua UI não apresenta todos os sistemas novos, e um encontro iniciado na Web deve preferencialmente ser concluído nela; ação legada delega ao coordenador de grupo, sem ignorar regras. Não há declaração de compatibilidade gráfica nativa para recursos 0.8 ausentes de suas telas.
