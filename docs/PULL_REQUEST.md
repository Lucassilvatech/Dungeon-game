# Atualizar mecânicas, recuperação, dívida e distribuição no primeiro andar

O status agora usa os mesmos atributos efetivos do combate; o cliente nativo exige API acessível e diferencia falhas de autenticação/rede. Aventuras novas ganham sequência/boss 1–10%, geração universal limitada e retenção de estado temporário. A morte perde 0–5 unidades com recuperação pessoal de valiosos; confisco de dívida usa avaliação/abatimento/excedente e marcos adicionais, com leilões posteriores sem dupla cobrança. A Central permite ocultar/arquivar anúncios com reservas seguras e agendar eventos explicados.

Migração d0fc148417a5 preserva dados. Builds Windows/Android publicados e verificáveis. Main permaneceu intacta. A branch depende da entrega Godot/ADM anterior ainda em revisão; comparar com feature/godot-admin-migration para avaliar só este incremento, ou revisar ambas antes de integrar à main.

Validação: 142 testes PostgreSQL, 42 checks do controlador Godot, navegador legado/ADM/eventos, Alembic check, Docker/Vite, preservação de 274 registros e reinício, assinatura APK, downloads HTTPS com hashes, exportação CI e Defender/nuvem/inicialização Windows headless aprovados. Login/jogo gráfico Windows e execução em Android ainda requerem homologação; backend real configurado é obrigatório. Nenhuma conclusão de falso positivo ou garantia de segurança foi feita.

[Relatório completo](DELIVERY_0.7.md).
