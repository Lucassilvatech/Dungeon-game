# Central Administrativa web

Acesso de desenvolvimento: `http://localhost:8080/admin`. Entrada/bundle separados do jogo; Godot não possui privilégios administrativos. A navegação oferece Visão geral, Banco Central, Economia, Guildas, Jogadores, Itens, Monstros, Leilões, Mundo/eventos e Auditoria. A aplicação não tem senha padrão nem transforma a primeira conta em administrador.

## Primeiro acesso

Crie uma conta normal pelo jogo e conceda papel explicitamente no terminal do operador:

```powershell
docker compose exec backend python -m app.admin_cli SEU_USUARIO owner --reason "Responsável autorizado pela administração do servidor"
```

Use seu nome real de conta no lugar de SEU_USUARIO. A conta precisa existir. Para revogar, substitua owner por revoke; para leitura use observer. O comando registra mudança de papel em WorldEvent e revoga as sessões ADM anteriores. Nunca escreve senhas/tokens no log. O personagem da conta, se criado, continua normal, sem moedas ou equipamento adicional por ter papel administrativo.

Papéis: observer (consulta), operator (consulta e gestão de jogadores/itens/monstros/leilões/mundo), economist (consulta e operações econômicas) e owner (ambos). Cada operação também tem permissão específica de domínio no servidor. O painel não concede papéis por si próprio.

## Operações

Escolha entidade pelos registros reais e preencha o formulário da ação. Justificativa de 10–500 caracteres é obrigatória. Calcular prévia cria UUID, captura estado anterior e mostra impacto na oferta/saldos previstos quando financeiro. Nenhum efeito de jogo ocorre nessa etapa. Confirmar exige token da prévia, sessão/papel válidos e estado ainda compatível, com prazo de 5 minutos. Repetições de operações já confirmadas não as executam novamente.

Ações implementadas:

| Domínio | Ações |
|---|---|
| Banco Central | emitir, retirar, transferir reservas; quantidades inteiras exatas |
| Economia | parâmetros suportados de recompensa, taxa e leilão; créditos isolados de teste |
| Jogadores | consultar conta/personagem/inventário/combatente/local/dívida; curar em área segura, conceder XP com pontos normais, viajar somente a destino já permitido |
| Itens | consultar definição/custódia; criar lote autorizado, transferir item físico elegível, proteger definição, recuperar/repor espada inicial |
| Monstros | consultar perfis/instâncias; alterar perfil persistente aplicado a novos encontros |
| Mundo | consultar salas/eventos; ajustar tier de região de combate do primeiro andar; criar spawn identificado, em piso acessível fora de saídas |
| Leilões | filtrar estados, consultar detalhes/lances/reservas e cancelar com reembolso/destino explícito |
| Guildas | administrar a única Guilda real, tesouro, obrigações/pagamentos e transferências institucionais |
| Auditoria | ator, UUID/correlação, entidade, antes/depois, motivo, horário e resultado das operações |

Não existe editor SQL arbitrário, exclusão de ledger, criação fictícia de instituições, emissão automática ou ferramenta para ignorar combate/expedição e suas consequências. Configurações administrativas são persistidas em GameSetting e alteram novas operações, não recompensas já registradas ou preços/prazos de leilões existentes. Perfis de monstros preservam estatísticas/XP dos inimigos já instanciados e mortos.

Para concessão oficial a personagem use conta `character:ID` no fluxo auditado do Banco Central, com emissão explícita ou débito de reserva existente. Sandbox não é uma origem válida. Itens protegidos/externos não podem ser transferidos por um atalho de gestão de mochila.

API `/admin/auth/login` emite sessão administrativa independente; `/admin/session` consulta permissões; `/admin/auth/logout` revoga. Consultas por módulo e `/admin/operations/preview` / `.../{UUID}/confirm` verificam autorização no FastAPI. Dados financeiros exatos usam texto decimal. Login falho e sessão expirada exibem erro; falha de confirmação por estado alterado exige nova prévia. Rejeições de operações existentes são registradas como FAILED com rollback dos efeitos.

Não exponha o painel em endereço público sem TLS e configuração de proxy/autenticação adequadas. O Compose publica loopback; tokens Bearer não usam cookies, portanto não há credencial ambiental de cookie para CSRF. Mais detalhes em SECURITY_AUDIT.md.
