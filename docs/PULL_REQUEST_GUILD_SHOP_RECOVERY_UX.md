# Loja agregada da Guilda, preços em lote e recuperação na vila

A loja mostrava pilhas separadas e não suportava TUDO/MAX entre inventários. Agora agrega materiais físicos por definição, preserva equipamentos individuais e calcula quantidade máxima com estoque, moedas reais1/5/10 e capacidade. Confirmações integradas substituem diálogos nativos de compra/venda; quote antiga exige nova revisão.

Administração mantém justificativas por operação, edição individual e lote atômico com revisão capturada, prévia antes/depois, confirmação, riscos condicionais e histórico por política/UUID comum. Recuperação muda da sala interna da Guilda para a barraca com NPC encapuzado no sudoeste da vila; custo200%, custódia e ledger permanecem.

Base: `feature/lunar-physical-denominations-guild-commerce-0.9`. Head: `feature/guild-shop-recovery-ux-0.9`. Preparado para Draft PR, sem merge automático.

Migração e06a9c24f8bd: amplia PK do histórico e adiciona/arquiva metadados de localização; preserva dados e preços existentes. Cópia privada validou50 tabelas/816 hashes históricos inalterados, campos não posicionais preservados,100.550.000mg e gap0. Operacional do usuário não foi alterado.

Validação final: **304 passed,0 failed,0 skipped,2 warnings,696.20s**, uma suíte backend integral PostgreSQL. `npm test`:1 passed; `npm run build`:PASS; seis scripts Chromium desktop/390px:PASS; upgrade/check novo e cópia privada:PASS. [Relatório/evidências](https://github.com/Lucassilvatech/Dungeon-game/blob/feature/guild-shop-recovery-ux-0.9/docs/lunar/DELIVERY_GUILD_SHOP_RECOVERY_UX_0.9.md).

Discord estritamente read-only; Godot preservado/congelado. Sem crafting/produção NPC/preços automáticos/Boss/Echo. Aplicação operacional, Discord externo e carga real permanecem fora da validação. [Atualizar no Windows com backup](https://github.com/Lucassilvatech/Dungeon-game/blob/feature/guild-shop-recovery-ux-0.9/docs/lunar/OPERATIONAL_GUILD_SHOP_RECOVERY_UX.md).
