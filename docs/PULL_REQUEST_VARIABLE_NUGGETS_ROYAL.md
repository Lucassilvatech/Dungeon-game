# Pepitas variáveis e Administração Real 0.9

Base: `feature/lunar-procedural-resources-0.9`. Head: `feature/lunar-variable-nuggets-royal-admin-0.9`. PR para revisão, sem merge automático.

O minério anteriormente fungível por tamanho passa a ter identidade física individual, peso variável e linhagem. Spawn inicial aprovado2%, faixas 80/15/5 e pesos inteiros 100..1000 g. Coleta persiste origem; reconexão não rerola decisões. Split gratuito conserva massa/capacidade; Guilda paga floor(g×rate/1000), rate inicial800, com caixa real e cotação por lote/revisão.

Administração do Rei substitui o Banco Central como interface econômica principal, preservando o legado somente para compatibilidade. Dez áreas Web incluem composição por conta, minério/ocorrências/linhagem, mint manual das três denominações, confisco/transferências, burn/injection excepcionais, configuração e histórico. Toda mutação reutiliza permissão, razão, prévia vinculada ao estado, confirmação e recibos. Não existe conta ADM padrão ou política monetária automática.

## Migração e integridade

Revisão aditiva **ca343e37b4ca**: cada unidade fixa100/500/1000 g vira LunarMineralLot; postings compensatórios preservam o ledger antigo sem edição. Holdings ficam monetários; mineral_mg é ativo contábil sem holding físico. Triggers protegem identidade/estados terminais; Supply separa admin_injected_mg. Equação global inclui gênese+descoberta+injection−destruição, com potencial procedural fora da oferta.

Fixture PostgreSQL: 4 lotes/1.700.000 mg preservados. Cópia privada real:49 tabelas/1.666 hashes históricos, 1 lote migrado, 100.550.000 mg antes/depois, cutover inalterado e gap 0. Split, venda, transferência e mint parcial nessa cópia também reconciliam. Nenhuma ativação/migração no banco operacional real.

## Validação

Resultados completos, comandos e limitações em [docs/lunar/DELIVERY_VARIABLE_NUGGETS_0.9.md](lunar/DELIVERY_VARIABLE_NUGGETS_0.9.md) e evidência sanitizada `docs/lunar/VARIABLE_VALIDATION.json`. Backend completo em PostgreSQL real; frontend npm test/build; Chromium gameplay/carteira/coleta/Guilda/Administração Real em390 px; Alembic upgrade/check; simulador de1 milhão de decisões e cadeias normal/extraordinária. Não somar subconjuntos à suíte completa.

## Limites e operação

Discord remains read-only. Discord cannot control the character. Windows/Android FROZEN; nenhum APK/EXE novo. Boss global, Echo, automação do rei, produção NPC, deploy/carga real e Discord externo ficam fora desta entrega. Mutex financeiro global e auditoria crescente precisam de medição antes de escala; presença continua com um worker. [Comandos Windows e acesso ADM](lunar/ROYAL_ADMINISTRATION.md).
