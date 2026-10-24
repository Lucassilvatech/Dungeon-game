# Mundo da Torre — implementação 2

```text
Andar 1
Vila do Alvorecer (CITY, 28×20, segura)
├── Guilda · Recepção (GUILD)
│   └── Pátio de treinamento (TRAINING)
└── Bosque das lanternas (COMMON, antigo mapa)
    └── Trilha dos vagalumes (COMMON)
        └── Clareira dos ecos (COMBAT)
            └── Santuário do Guardião (BOSS)

Aventura → Refúgio errante (PROCEDURAL, individual, seed persistente)
          ou descoberta de entrada secreta
Andar 2 → Mirante das Nuvens (CITY, após FLOOR_UNLOCKED)
```

Existe uma masmorra secreta configurada no primeiro andar. Seu nome/conteúdo não aparece no grafo da API antes da descoberta. A documentação SECRET_DUNGEONS contém detalhes para desenvolvedores e spoilers da demonstração.

Cidades não têm spawns de monstros e rejeitam combate normal no servidor. A Guilda oferece curandeira, quadro visual de recompensas e saída ao treino; contratos econômicos ainda não estão implementados. O chefe tem sala separada e descobrir/entrar não inicia combate. O navegador mostra nível recomendado 3, dificuldade extrema, recomendação de quatro jogadores e confirmação para solo. A força do chefe permanece a da versão 1 para preservar o combate existente, com balanceamento provisório.

Floor, Room, RoomConnection e RoomState são persistidos. RoomType usa enum central: CITY, COMMON, COMBAT, BOSS, PROCEDURAL, SECRET_DUNGEON, BUILDING_INTERIOR, GUILD, TRAINING e SPECIAL. BUILDING_INTERIOR/SPECIAL são categorias preparadas sem serviços adicionais. Cada personagem ocupa uma sala; a localização física é validada no backend. Andares anteriores permanecem acessíveis.

Eventos persistentes: ROOM_DISCOVERED, ROOM_ENTERED, ADVENTURE_STARTED, SECRET_DUNGEON_DISCOVERED, SECRET_DUNGEON_COMPLETED, FLOOR_BOSS_DISCOVERED, FLOOR_BOSS_DEFEATED, FLOOR_UNLOCKED, RAID_CREATED, RAID_JOINED, COMBAT_STARTED, COMBAT_FINISHED. Chaves únicas protegem descobertas/conclusões únicas. Os eventos não constituem um broker nem uma API pública de segredos.
