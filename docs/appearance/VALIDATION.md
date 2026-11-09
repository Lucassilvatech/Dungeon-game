# Validação — aparência, roupas e proporções

Base: `f96aa9c512d7cbdee18e98f63e01f57b8f2a34e9`, na branch existente
`feature/village-natural-grass-grounded-walk-0.9`. Nenhuma alteração na main,
nos fontes Godot ou no bot Discord.

## Resultados finais

| Verificação | Resultado | Duração |
|---|---|---|
| Backend completo, PostgreSQL 17 | 354 passed, 0 failed, 0 skipped, 2 warnings | 863,08 s (14 min 23 s) |
| `npm test` | 39 passed, 0 failed, 0 skipped | 0,698 s |
| `npm run build` | PASS, TypeScript + Vite | 5,76 s no Vite |
| Chromium: aparência/Barbeiro/interiores | PASS, desktop e 390 px, zero erros de página | 35,248 s |
| Chromium: regressão visual | PASS, cinco salas reais, 1280/1920/390 px, portas e interação por toque | Não instrumentada |
| Chromium: movimento | PASS, oito movimentos reais via API, quatro direções e reconexão | Não instrumentada |
| Chromium: economia NPC | PASS, worker real, estoque/caixa finitos, compra/venda e painel administrativo | Não instrumentada |
| Chromium: encaixe das camadas | PASS, todas as opções de roupa/cabelo nas quatro direções, fundos claros/escuros | Não instrumentada |
| Alembic: upgrade + check | PASS, banco novo e ensaio privado com dados da revisão anterior | Não instrumentada |
| Builds Docker backend/frontend | PASS | Não instrumentada |
| Inicialização real das imagens Docker | PASS, migration/seed, Nginx, API e manifesto de assets | 3,714 s |
| Recompilação dos assets | PASS, 70 arquivos com SHA256 idêntico | Não instrumentada |
| Posicionamento | PASS, 254 layouts, 2.410 objetos, zero interseções proibidas | Não instrumentada |

O resultado do backend é de uma execução integral, sem somar subconjuntos.
Os dois avisos são depreciações de bibliotecas: o alias `BlockingPortal` do
AnyIO e `audioop` usado pelo Discord. O teste de consultas read-only do bot passa.
O aviso do Vite sobre o chunk de Phaser maior que 500 kB permanece; não é erro
de compilação. O desempenho registrado é de Chromium em nuvem, não um benchmark
de celular físico.

## O que foi exercitado

Criação com os oito campos, escolhas livres entre os dois corpos, catálogo
validado no servidor, aparência persistida, presença dos outros jogadores,
prévia nas quatro vistas e mudança visual após reconectar.

O Barbeiro foi testado com pagamento físico, saldo insuficiente, denominações
incompatíveis, distância incorreta, personagem morto, taxa/revisão desatualizada,
repetição da mesma request, requests concorrentes diferentes e rollback de falha
de auditoria. O pagamento real de teste transferiu 1.000 mg do jogador ao
Barbeiro uma única vez, com `gap_mg = 0`, sem alterar equipamento/atributos.

As quatro lojas foram acessadas pelas fachadas e seus NPCs interagiram no
interior. O retorno usa a porta correspondente. O seed repetido preservou os
estoques, os caixas e o inventário; uma posição antiga dentro da nova Barbearia
foi relocada apenas ao ponto livre mais próximo, com evento auditado.

Os quatro PNGs originais foram comparados byte a byte ao ZIP. Os 34 layers
possuem 96 quadros não vazios, alpha binário e catálogo completo. A caminhada
tem oito poses distintas por direção e mantém os pés em `y = 94`. As pranchas
`*-fit.png` usam o compositor da aplicação; são evidências de composição, não
capturas de gameplay. As capturas das lojas permitem comparar móveis e
personagens na mesma escala.

## Upgrade e preservação

O ensaio utiliza um banco privado novo, criado com código da revisão anterior,
cutover de teste já executado, personagem, inventário e contas existentes.
Foram comparadas integralmente as linhas de cutover, ledger Lunar, holdings,
supply, dívidas, itens, perfis e estoques NPC antes/depois do upgrade e de dois
seeds. A aparência de personagens antigos é um fallback somente de leitura.

Não foi disponibilizada nem acessada uma cópia do banco operacional do usuário.
Esse ensaio não substitui uma validação com os dados operacionais reais.

## Ocorrências resolvidas durante a validação

- O teste antigo dos NPCs ainda procurava os serviços ao ar livre; passou a
  navegar até o interior correspondente.
- A comparação de migrations passou a aceitar somente a nova tabela vazia,
  continuando a exigir preservação integral das tabelas antigas.
- O PostgreSQL expôs ordem instável das pilhas após atualização; `/state` agora
  recebe inventário ordenado por ID.
- Um build Docker esgotou o disco do executor e interrompeu testes. Foi removido
  apenas cache de build não utilizado, preservando bancos e volumes; o banco de
  teste recuperou-se e as verificações afetadas foram reiniciadas.
- A execução real do Nginx revelou permissão de leitura restrita em arquivos
  importados. O Dockerfile agora garante leitura dos assets estáticos.

## Evidências

[`artifacts/appearance`](../../artifacts/appearance) contém os relatórios JSON,
as pranchas de roupas/cabelos e as capturas reais de criação, Barbeiro, quatro
interiores e mobile. [`artifacts/map-rebuild`](../../artifacts/map-rebuild)
contém a regressão dos mapas, movimento e métricas do Chromium.

As partes ocultas e as poses ausentes nas referências foram adaptadas conforme
[provenance.json](../../art/characters/layers/provenance.json). Ataque/dano/morte
mantêm compatibilidade com o renderizador, sem prometer um conjunto completo de
animações desenhadas individualmente por arma. A pousada continua opcional.
Não há deploy operacional, nova etapa de Boss/Echo nem builds Windows/APK.
