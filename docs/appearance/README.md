# Aparência, Barbeiro e interiores — Web 0.9

Continuação na branch existente `feature/village-natural-grass-grounded-walk-0.9`,
a partir de `f96aa9c512d7cbdee18e98f63e01f57b8f2a34e9`. Sem nova branch, merge ou
alteração da main. A especificação recebida está em [REQUEST_0.9.txt](REQUEST_0.9.txt).

## Uso

A criação do personagem apresenta os oito campos de aparência e uma prévia nas
quatro direções, com caminhada opcional. Os dois corpos compartilham todos os
cabelos e todas as roupas: não existem restrições por sexo. A aparência é
independente dos equipamentos, atributos, combate e inventário físico.

O Barbeiro fica na Barbearia, cuja porta está ligada ao caminho da vila. A
alteração posterior exige proximidade, personagem vivo e livre de combate ou
expedição ativa, e economia Lunar ativada. A prévia mostra o preço e a possibilidade
de pagar com denominações físicas exatas. O padrão é **1 moeda pequena / 1 g de
Moeda Lunar**, configurável por `BARBER_FEE_UNITS` ou pela operação administrativa
`economy.configure`, parâmetro `barber_fee_units` (inteiro de 1 a 1000).

A confirmação transfere moeda real de `player:<id>` para `npc:barber`. Não emite
moeda, não utiliza crédito e não troca denominações automaticamente. O recibo
registra o lançamento Lunar, a aparência anterior e a nova, o preço, a revisão e
a chave de idempotência. Repetir a mesma confirmação devolve o recibo; duas
confirmações concorrentes para a mesma revisão cobram apenas uma vez. Mudanças
na taxa ou na revisão exigem nova prévia. Uma falha na auditoria desfaz pagamento
e aparência na mesma transação.

## Persistência e integração

- Migration aditiva `8c2a71e93d60`, após `65a7c9e21b04`: tabela
  `character_appearances`, PK/FK `character_id`, `revision >= 1`, `choices` JSON e
  `updated_at`. Nenhuma migration histórica foi modificada.
- Catálogo canônico: `backend/app/appearance_catalog.json`. APIs rejeitam campos
  extras e valores desconhecidos. Não aceitam um ID de outro personagem.
- Personagens antigos recebem um visual padrão em leitura, sem inserção nem
  cobrança. A primeira mudança paga persiste sua aparência.
- `/state`, a presença de outros jogadores e a consulta administrativa expõem a
  aparência. A consulta administrativa e a presença carregam aparências em lote.
- Endpoints: `GET /appearance/catalog`, `GET /character/appearance`,
  `POST /appearance/barber/preview`, `POST /appearance/barber/confirm`.
- O editor mantém a revisão com que foi aberto; uma atualização de outra sessão
  não autoriza silenciosamente sobrescrever o visual mais recente.
- A consulta de inventário agora ordena por ID, mantendo a ordem das pilhas
  estável após atualizações do PostgreSQL e reconexões.

## Assets e correções de qualidade

Os **quatro PNG originais** do ZIP foram salvos, byte a byte, em
[`art/characters/references`](../../art/characters/references/README.md), com
nomes organizados e SHA256. O arquivo original de roupas contém painéis, fundo
claro, escalas diferentes e vistas que exigem adaptação. Ele não foi tratado como
um atlas pronto para uso.

Os derivados em `art/characters/layers` mantêm os modelos e as cores das
referências. O corpo oculto foi reconstruído usando o turnaround fornecido.
As roupas receberam limpeza assistida pela ferramenta de imagem e correção das
quatro vistas, incluindo os fechos traseiros das grevas. As fontes e os hashes
estão em [provenance.json](../../art/characters/layers/provenance.json).
Os 12 cabelos são recortes da prancha original em cinza; não foram substituídos
por penteados genéricos.

O compilador identifica as separações transparentes reais entre os sprites,
remove fragmentos, fixa âncoras de pescoço/cintura/pés e gera 34 camadas em quadros
de 64×96. O alpha final é binário e pixels transparentes não carregam manchas
visíveis. Pele e cabelo têm máscaras/paletas independentes; roupas preservam sua
paleta original. Saias, bermudas e grevas ficam sobre a parte correspondente das
botas, evitando que o calçado esconda essas escolhas. Capuz, touca e elmo cobrem
o cabelo para evitar que ele atravesse o acessório.

Cada camada possui quatro direções e 96 quadros compatíveis com o renderizador:
idle, caminhada de oito quadros por direção, ataque, dano e morte. A caminhada
usa poses com articulação local, amostragem inversa sem fendas e contato dos pés
fixo. No mapa, sua fase acompanha a distância percorrida; o idle respira
suavemente, respeitando a preferência de movimento reduzido. Não há geração de
imagens durante o jogo. Texturas de combinações são reutilizadas e as que deixam
de ser usadas são descartadas quando o cache cresce.

**Limitação artística:** as pranchas não fornecem todas as poses nem as partes
ocultas. As animações são derivações técnicas das referências; não são uma
coleção completa de animações desenhadas individualmente para cada arma. Os
originais e as adaptações permanecem separados e identificados.

## Escala e interiores

Os personagens principais usam a escala nativa das novas camadas, com cerca de
87 px de altura visível. O mobiliário tem dimensões próprias: balcão de até 70 px
de altura, barris de até 40, cadeira de até 64, estantes de até 110 e forja de até
144. O desenho não é ampliado para preencher um retângulo de colisão. A passagem
interna usa um degrau no chão, sem uma porta vertical cobrindo o personagem.

| Serviço | Interior | Porta na vila |
|---|---|---|
| Comerciante | `merchant_shop` | 25,10 |
| Ferreiro | `blacksmith_workshop` | 39,9 |
| Alquimista | `alchemy_laboratory` | 38,29 |
| Barbeiro | `barber_shop` | 17,30 |

As três primeiras lojas reutilizam casas existentes. A pequena Barbearia recebe
uma fachada e um sinal próprio. O seed é idempotente, preserva estoque/caixa dos
NPCs, conecta os dois sentidos das portas e só desloca para o ponto livre mais
próximo personagens que estavam dentro da nova construção. Esse deslocamento é
auditado. Layouts personalizados conflitantes são detectados, sem sobrescrita.

A vila recebe canteiros, pequenas cercas, barracas e detalhes próximos às casas.
Todos passam pela máscara de proteção de caminhos, portas, NPCs e recursos.
Os interiores têm móveis de loja, ferramentas/bigorna/forja, frascos/livros/orbe,
e espelho/cadeira de barbeiro. A pousada opcional não ganhou uma mecânica nova.

Os produtores e o Comerciante continuam usando estoque finito, caixa real,
preços e produção existentes. Nenhum estoque ou dinheiro novo foi criado por
esta atualização. Discord permanece read-only; os fontes Godot e seus builds
Windows/Android permanecem congelados.

O build Docker da Web também normaliza a leitura dos arquivos estáticos pelo
Nginx. Isso evita respostas 403 para PNGs importados com permissões restritas.

## Evidências

As capturas reais do Chromium e as pranchas de composição estão em
[`artifacts/appearance`](../../artifacts/appearance). Arquivos `*-fit.png` e
`layer-contact-sheet.png` são pranchas de inspeção, **não capturas de gameplay**.
`creation-*.png`, `barber-*.png`, `*-desktop.png` e
`appearance-in-game-mobile.png` são capturas do jogo com o backend real em banco
PostgreSQL privado descartável. Resultados detalhados: [VALIDATION.md](VALIDATION.md).

A validação de upgrade usa o código da revisão anterior e dados de teste com
cutover já realizado, inventário e contas existentes. Não é uma cópia do banco
operacional do usuário; nenhum banco operacional foi acessado ou alterado.

## Execução local

Preserve seu `.env` e os volumes existentes. Na pasta do projeto:

```powershell
git switch feature/village-natural-grass-grounded-walk-0.9
git pull --ff-only origin feature/village-natural-grass-grounded-walk-0.9
docker compose up -d --build db backend frontend
```

O comando de inicialização do backend executa `alembic upgrade head` e o seed
idempotente automaticamente. Acesse **http://localhost:8080**.
Não é necessário gerar Windows/APK nem ativar novamente o cutover.
