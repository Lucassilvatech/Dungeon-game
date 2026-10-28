# Pepitas variáveis 0.9 — diagnóstico anterior à implementação

Base confirmada9026877958b5323cad34ab9fb9410d4d34c36a2e, branch limpa feature/lunar-procedural-resources-0.9; fetch executado. Desenvolvimento isolado em feature/lunar-variable-nuggets-royal-admin-0.9. Main preservada.

Estado real: LunarResourceOccurrence aceita somente100/500/1000g e LunarHolding guarda pepitas fungíveis. Livro-razão é append-only. O cutover, moedas1/5/10g, dívida, escrows e caixa finito funcionam; precisam ser reutilizados. Geração já persiste decisões negativas e privadas SOLO. As APIs atuais vendem por categoria, e o painel ainda usa Banco Central como rótulo.

Plano contábil: LunarMineralLot será a custódia autoritativa do minério, LunarHolding permanece para moedas. Um ativo contábil mineral_mg (peso1mg) permite reutilizar o ledger de partidas exatas; nenhum holding material desse ativo será criado. Migração converte cada unidade fixa em um lot e acrescenta lançamento compensatório (ativos fixos→mineral_mg), sem editar ledger anterior. Auditoria considera holdings monetários + lotes HELD, e recompõe a linhagem/entrada histórica. Administração excepcional separará ADMIN_INJECTION de descoberta/gênese. Split/mint parcial geram filhos e encerram o pai; transferência conserva ID.

Não haverá ativação, coleta artificial ou migração no banco operacional; validação somente em cópias privadas e fixtures PostgreSQL. Escopo integral inclui Administração Real, Web, mint, confisco, burn, injection, testes e publicação; boss global/Echo/política automática/Godot permanecem fora.
