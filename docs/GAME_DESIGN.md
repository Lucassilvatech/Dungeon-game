# Design do jogo

Especificação fornecida pelo autor. O escopo implementado e as pendências estão no README e ROADMAP; requisitos futuros abaixo não significam funcionalidades existentes.

1. OBJETIVO DO PROJETO
==================================================

Criar um RPG multiplayer persistente com:

- Mundo dividido em andares.
- Progressão global por derrotas de chefes.
- Combate por turnos.
- Exploração de mapas.
- NPCs.
- Monstros.
- Inventário.
- Equipamentos.
- Atributos.
- Progressão de personagens.
- Grupos de jogadores.
- Masmorras.
- Economia persistente.
- Mercado entre jogadores e NPCs.
- Sistema de profissões.
- Guilda dos Aventureiros.
- Banco Central da Torre.
- Sistema de mentoria.
- Integração com Discord.

O jogo deve funcionar por dois clientes:

1. Navegador web.
2. Bot do Discord.

Ambos devem compartilhar:

- Mesmo backend.
- Mesmo banco de dados.
- Mesmos personagens.
- Mesmo inventário.
- Mesmo mundo.
- Mesma economia.
- Mesmo progresso.

Não desenvolver duas lógicas de jogo independentes.

==================================================
2. TECNOLOGIAS
==================================================

Backend:
- Python.
- FastAPI.
- SQLAlchemy.
- Alembic.
- Pydantic.
- WebSockets quando necessário.

Banco de dados:
- PostgreSQL.

Frontend:
- React.
- TypeScript.
- Vite.
- Phaser 3.

Discord:
- discord.py.
- Slash commands.
- Botões e menus interativos.

Infraestrutura:
- Docker Compose.
- Variáveis de ambiente.
- Git.
- GitHub.

Testes:
- pytest.
- Testes de integração.
- Testes de regras de negócio.

O desenvolvimento inicial acontecerá no Windows.

Posteriormente, o projeto será migrado para um servidor Proxmox utilizando containers ou máquinas virtuais.

Portanto, evitar dependências exclusivas do Windows.

==================================================
3. ARQUITETURA
==================================================

Organizar o projeto como um monorepositório.

Estrutura sugerida:

tower-rpg/
├── backend/
│   ├── app/
│   │   ├── core/
│   │   ├── database/
│   │   ├── auth/
│   │   ├── characters/
│   │   ├── world/
│   │   ├── combat/
│   │   ├── inventory/
│   │   ├── equipment/
│   │   ├── economy/
│   │   ├── marketplace/
│   │   ├── guilds/
│   │   ├── crafting/
│   │   ├── mentorship/
│   │   └── api/
│   ├── migrations/
│   └── tests/
├── frontend/
├── discord-bot/
├── infrastructure/
├── docs/
├── .env.example
├── .gitignore
├── docker-compose.yml
└── README.md

Essa estrutura pode ser ajustada se houver justificativa técnica.

A lógica principal deve ficar no backend.

O frontend e o Discord devem atuar como clientes.

Nunca confiar em valores de moedas, atributos, danos ou inventários enviados pelos clientes.

==================================================
4. SISTEMA DE PERSONAGENS
==================================================

Cada conta poderá possuir inicialmente um personagem.

Implementar:

- Criação de personagem.
- Nome.
- Identificador único.
- Nível.
- Experiência.
- Vida.
- Energia.
- Atributos básicos.
- Inventário.
- Equipamentos.
- Localização atual.
- Andar atual.
- Saldo de moedas.

O sistema de progressão não terá classes fixas.

Os jogadores poderão desenvolver diferentes especializações conforme distribuem atributos e aprendem habilidades.

A redistribuição futura de atributos deverá custar moedas do jogo.

Não implementar ainda árvores complexas de habilidades.

Preparar a arquitetura para essa expansão.

==================================================
5. MUNDO DA TORRE
==================================================

O mundo será dividido em andares.

Cada andar poderá conter:

- Cidades.
- Áreas de exploração.
- NPCs.
- Monstros.
- Masmorras.
- Recursos naturais.
- Comerciantes.
- Chefes.
- Pontos de teletransporte.

Cada andar funciona como uma região própria.

Os andares anteriores continuam acessíveis.

O desbloqueio de novos andares é global.

Exemplo:

Quando o primeiro grupo derrota o chefe do primeiro andar:

1. O segundo andar é desbloqueado globalmente.
2. Os jogadores que derrotaram o chefe podem avançar imediatamente.
3. Outros jogadores também passam a poder acessar o novo andar.
4. Os sistemas econômicos recebem o evento de desbloqueio.
5. Os NPCs dos andares desbloqueados podem negociar entre si.

Criar um evento de domínio:

FLOOR_UNLOCKED

O evento deve ser persistente e processado de maneira segura.

Não permitir desbloqueios duplicados ou recompensas duplicadas por concorrência.

Na primeira versão, implementar um primeiro andar funcional e preparar o segundo andar como demonstração do desbloqueio.

==================================================
6. INTERFACE WEB
==================================================

Criar uma interface jogável em pixel art.

Referência visual:
- Zelda clássico visto de cima.
- RPGs 2D tradicionais.
- Interface moderna e organizada.

Utilizar Phaser para:

- Renderização do mapa.
- Personagem.
- Movimentação.
- Colisões.
- Interação com NPCs.
- Interação com monstros.

Utilizar React para:

- Menus.
- Inventário.
- Equipamentos.
- Atributos.
- Informações do personagem.
- Interface de combate.
- Notificações.

Na primeira versão, utilizar gráficos provisórios simples e originais.

Não depender de imagens protegidas por direitos autorais.

O jogo precisa ser utilizável mesmo antes da criação dos gráficos definitivos.

==================================================
7. COMBATE
==================================================

Implementar inicialmente combate por turnos.

O backend deve determinar:

- Ordem das ações.
- Dano.
- Consumo de energia.
- Efeitos.
- Vitória.
- Derrota.
- Recompensas.

Não permitir que o frontend determine resultados.

Criar um combate básico entre personagem e monstro.

Preparar a estrutura para:

- Combate em grupo.
- Chefes.
- Masmorras.
- Habilidades.
- Efeitos de status.
- Reconexão durante combate.

==================================================
8. INVENTÁRIO E EQUIPAMENTOS
==================================================

Implementar inventário persistente.

Itens devem possuir identificadores únicos quando necessário.

Diferenciar:

- Definição do item.
- Instância individual do item.
- Quantidade de itens empilháveis.
- Proprietário.
- Local de armazenamento.

Preparar o sistema para equipamentos com atributos aleatórios e raridades.

Não permitir:

- Duplicação de itens.
- Equipar itens vendidos.
- Transferir itens inexistentes.
- Utilizar itens que estão sob custódia do mercado.

Toda movimentação importante deve ser validada no backend.

==================================================
9. ECONOMIA
==================================================

A economia será persistente e utilizará uma moeda única.

Jogadores e NPCs utilizam a mesma moeda.

O jogo deverá ter uma quantidade inicial configurável de moeda.

Não criar moedas arbitrariamente ao derrotar monstros.

As recompensas monetárias serão pagas por instituições do mundo, principalmente a Guilda dos Aventureiros, utilizando recursos existentes no Tesouro.

O Banco Central poderá futuramente emitir moeda conforme regras econômicas controladas.

Não implementar empréstimos ou juros.

Criar desde o início um registro contábil das movimentações monetárias.

As operações precisam ser auditáveis.

Nunca permitir saldos negativos não autorizados.

Parâmetros econômicos devem ser configuráveis.

Exemplos:

- Impostos.
- Taxas de anúncios.
- Recompensas.
- Orçamentos.
- Limites de emissão.
- Custos de serviços.

Evitar valores fixos espalhados pelo código.

==================================================
10. MERCADO
==================================================

O mercado será único e acessível a partir dos andares desbloqueados.

Jogadores e NPCs poderão comprar e vender.

Regras:

1. O vendedor define quanto deseja receber.
2. O imposto é acrescentado ao preço final do comprador.
3. O vendedor recebe exatamente o valor solicitado.
4. O comprador paga o preço final com impostos.
5. O imposto é encaminhado ao sistema tributário.
6. O anúncio permanece disponível mesmo com o vendedor offline.
7. A compra transfere imediatamente item e moedas.
8. O item anunciado deixa de estar disponível no inventário do vendedor.

Exemplo:

Preço solicitado: 100 moedas.
Imposto ilustrativo: 5%.
Preço final: 105 moedas.

Vendedor recebe: 100.
Imposto: 5.
Comprador paga: 105.

Interface do vendedor:

"O valor informado corresponde ao que você receberá pela venda. Impostos serão aplicados ao preço final apresentado ao comprador."

Interface do comprador:

"Preço final: 105 moedas. Impostos já incluídos."

Os anúncios terão validade de sete dias.

Permitir renovação automática opcional.

Limitar inicialmente a três renovações consecutivas.

Ao expirar, devolver o item para uma caixa de recebimento do jogador.

A publicação e a renovação terão taxas configuráveis, cujos valores definitivos serão decididos posteriormente.

IMPORTANTE:

As compras devem utilizar transações atômicas no banco de dados.

Impedir que dois compradores adquiram simultaneamente o mesmo item.

Não implementar ainda o mercado completo se isso comprometer a entrega do MVP.

Preparar modelos e documentação para implementação posterior.

==================================================
11. ECONOMIA DOS NPCs
==================================================

NPCs comerciantes possuirão:

- Estoques.
- Orçamentos.
- Necessidades.
- Especializações.
- Preços dinâmicos.

NPCs não terão dinheiro ou produtos infinitos.

Poderão negociar:

- Com jogadores.
- Com outros NPCs.

NPCs compradores poderão adquirir anúncios de jogadores offline.

As negociações entre NPCs de diferentes andares só serão permitidas quando esses andares estiverem desbloqueados.

Não será necessário passar por andares intermediários.

Exemplo:

Um NPC do décimo andar poderá negociar diretamente com outro do primeiro andar.

As transações serão instantâneas.

Os recursos transferidos deverão existir de verdade nos estoques.

Não gerar materiais ou moedas artificialmente para concluir uma negociação.

==================================================
12. GUILDA DOS AVENTUREIROS
==================================================

Existirá uma Guilda Central com filiais nos andares.

Cada filial terá orçamento próprio.

A guilda poderá pagar recompensas por:

- Monstros derrotados.
- Contratos.
- Missões.
- Atividades autorizadas.

O jogador poderá derrotar monstros e posteriormente solicitar suas recompensas à guilda.

O pagamento utilizará recursos disponíveis no Tesouro.

Criar mecanismos para evitar recompensas duplicadas.

Contratos aceitos devem ter seus pagamentos garantidos por reserva de orçamento.

==================================================
13. BANCO CENTRAL DA TORRE
==================================================

O Banco Central deverá futuramente:

- Monitorar a circulação monetária.
- Acompanhar inflação.
- Acompanhar preços.
- Controlar emissão monetária.
- Redistribuir recursos.
- Acompanhar impostos.
- Gerenciar situações de crise.

Operação normal: automática.

Situações críticas: intervenção administrativa.

Criar arquitetura para auditoria e configuração.

Não implementar algoritmos avançados de política monetária nesta primeira etapa.

==================================================
14. PROFISSÕES
==================================================

Preparar o jogo para profissões como:

- Ferreiro.
- Refinador.
- Comerciante.
- Mentor.

O refinamento terá progressão de domínio.

Categorias planejadas:

- Iniciante.
- Aprendiz.
- Experiente.
- Especialista.
- Mestre.

Cada categoria terá 100 níveis de progressão.

O refinamento poderá falhar antes do domínio completo.

Ao dominar totalmente uma categoria, o jogador terá sucesso garantido nos refinamentos correspondentes.

Os preços dos serviços de refinamento serão definidos pelas regras do jogo.

Não implementar o sistema completo nesta primeira versão.

==================================================
15. MENTORIA
==================================================

Jogadores veteranos poderão atuar como mentores.

O sistema permitirá:

- Ajudar iniciantes.
- Participar de masmorras de mentoria.
- Reenfrentar chefes antigos em condições específicas.
- Receber pagamentos.
- Ganhar moedas especiais de mentoria.
- Participar de rankings mensais.

Veteranos não poderão participar normalmente de confrontos de chefes destinados a iniciantes fora do sistema de mentoria.

As moedas de mentoria serão vinculadas ao personagem.

Preparar a arquitetura para:

- Ranking mensal.
- Recompensas.
- Loja especial.
- Proteções contra exploração de recompensas.

Não implementar integralmente nesta primeira etapa.

==================================================
16. DISCORD
==================================================

Criar um bot conectado ao mesmo backend.

Implementar inicialmente comandos como:

/personagem
/status
/inventario
/mapa

Conforme os sistemas ficarem disponíveis, adicionar:

/explorar
/combater
/grupo
/mercado
/guilda
/mentoria

Não criar comandos que apenas simulem sucesso.

Comandos ainda não implementados devem ser omitidos ou informar claramente que a funcionalidade está indisponível.

A conta do Discord deverá poder ser vinculada à conta utilizada no navegador.

Não criar personagens duplicados para a mesma conta vinculada.

==================================================
17. SEGURANÇA E INTEGRIDADE
==================================================

Implementar validações no backend.

Proteger contra:

- Duplicação de itens.
- Duplicação de moedas.
- Compras simultâneas.
- Recompensas duplicadas.
- Manipulação de atributos.
- Ações inválidas.
- Acesso indevido a personagens.
- Repetição maliciosa de requisições.

Usar transações de banco de dados para operações críticas.

Registrar movimentações importantes.

Credenciais e tokens devem ficar em variáveis de ambiente.

Nunca enviar segredos ao GitHub.

==================================================
