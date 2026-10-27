import { useEffect, useState } from "react";
import { api, type State } from "./api";

type Action = (path: string, body?: unknown) => void;
export type DeathReceipt = {
  death_event_id: number;
  expedition_id: number;
  xp_lost: number;
  pending_lost_exact: string;
  medical_fee: number;
  charged: number;
  waived: number;
  balance_after_exact: string;
  debt_limit_reached: boolean;
  levels_lost: number;
  level_before: number;
  level_after: number;
  attribute_debt_added: number;
  items: {
    item_id: number;
    name: string;
    quantity: number;
    auction_id?: number;
    destination?: string;
    recovery_id?: number;
  }[];
};

export function DeathSummary({
  death,
  busy,
  onReturn,
}: {
  death: DeathReceipt;
  busy: boolean;
  onReturn: () => void;
}) {
  return (
    <div
      className="modal death-modal"
      role="dialog"
      aria-modal="true"
      aria-labelledby="death-title"
    >
      <section className="panel">
        <p className="eyebrow">RESGATE DA GUILDA · EXPEDIÇÃO FRACASSADA</p>
        <h1 id="death-title">VOCÊ MORREU</h1>
        <p>
          Seu personagem foi resgatado e está na cidade. Esta aventura foi
          encerrada.
        </p>
        <dl className="death-costs">
          <dt>XP do nível perdido</dt>
          <dd>{death.xp_lost}</dd>
          <dt>Recompensas pendentes perdidas</dt>
          <dd>{death.pending_lost_exact} moedas</dd>
          <dt>Taxa médica</dt>
          <dd>{death.medical_fee} moedas</dd>
          <dt>Saldo atual</dt>
          <dd
            className={death.balance_after_exact.startsWith("-") ? "debt" : ""}
          >
            {death.balance_after_exact} moedas
          </dd>
        </dl>
        {death.waived > 0 && (
          <p>
            A cobrança foi limitada em −10.000: {death.charged} moedas cobradas
            e {death.waived} limitadas pelo teto.
          </p>
        )}
        {death.debt_limit_reached && (
          <p className="debt" role="alert">
            Sua dívida médica atingiu o limite. Você perdeu {death.levels_lost}{" "}
            níveis ({death.level_before} → {death.level_after}), respeitando o
            mínimo 1. Dívida de atributos adicionada:{" "}
            {death.attribute_debt_added}. Outra morte no limite poderá reduzir
            níveis novamente.
          </p>
        )}
        <h2>Itens perdidos (até cinco unidades)</h2>
        {death.items.length ? (
          <ul>
            {death.items.map((i) => (
              <li key={i.item_id}>
                {i.name} ×{i.quantity} ·{" "}
                {i.destination ?? `leilão histórico #${i.auction_id}`}
              </li>
            ))}
          </ul>
        ) : (
          <p>Nenhum item físico elegível carregado.</p>
        )}
        <p>
          Itens comuns são destruídos; valiosos ficam na recuperação pessoal por
          200% do valor-base. Confisco de dívida é independente. Pagamentos
          futuros compensam automaticamente qualquer saldo negativo.
        </p>
        <button disabled={busy} autoFocus onClick={onReturn}>
          RETORNAR À CIDADE
        </button>
      </section>
    </div>
  );
}

export function AttributePanel({
  state,
  busy,
  action,
}: {
  state: State;
  busy: boolean;
  action: Action;
}) {
  const c = state.character;
  const [draft, setDraft] = useState({ strength: 0, defense: 0 });
  useEffect(
    () => setDraft({ strength: 0, defense: 0 }),
    [c.id, c.unspent_attribute_points],
  );
  const total = draft.strength + draft.defense;
  return (
    <div className="attributes">
      <h3>Distribuir atributos</h3>
      <p>
        Pontos disponíveis: <strong>{c.unspent_attribute_points}</strong> ·
        Dívida de pontos: {c.attribute_point_debt}
      </p>
      <p>
        Cada novo nível concede 1 ponto à sua escolha. Dívida de pontos é
        quitada primeiro. Vida máxima continua acompanhando o nível.
      </p>
      {(
        [
          ["strength", "Força"],
          ["defense", "Defesa"],
        ] as const
      ).map(([key, label]) => (
        <div className="attribute-row" key={key}>
          <label>
            {label} atual: {c[key]}
            <input
              type="number"
              aria-label={"Pontos em " + label}
              min={0}
              max={c.unspent_attribute_points}
              step={1}
              value={draft[key]}
              disabled={busy}
              onChange={(e) => {
                const n = Number(e.target.value);
                if (Number.isInteger(n) && n >= 0)
                  setDraft({ ...draft, [key]: n });
              }}
            />
          </label>
          <button
            className="secondary"
            aria-label={"Adicionar 1 em " + label}
            disabled={busy || total >= c.unspent_attribute_points}
            onClick={() => setDraft({ ...draft, [key]: draft[key] + 1 })}
          >
            +
          </button>
        </div>
      ))}
      <p>
        Preparado: Força +{draft.strength} · Defesa +{draft.defense} · Total{" "}
        {total}
      </p>
      <button
        disabled={busy || total <= 0 || total > c.unspent_attribute_points}
        onClick={() =>
          action("/character/attributes", {
            ...draft,
            request_id: crypto.randomUUID(),
          })
        }
      >
        CONFIRMAR ATRIBUTOS
      </button>
    </div>
  );
}

type Auction = {
  id: number;
  item_id: number;
  name: string;
  quantity: number;
  description: string;
  accepts_bids: boolean;
  protected: boolean;
  kind: string;
  attributes: { power: number };
  origin: string;
  death_event_id: number;
  next_bid: string;
  minimum_increment: string;
  proceeds_destination: string;
  opening_price: string;
  highest_bid: string;
  highest_bidder_id: number | null;
  status: string;
  ends_at: string;
};
export function AuctionHouse({
  state,
  busy,
  action,
}: {
  state: State;
  busy: boolean;
  action: Action;
}) {
  const [auctions, setAuctions] = useState<Auction[]>([]);
  const [offset, setOffset] = useState(0);
  const [details, setDetails] = useState<
    Record<
      number,
      {
        bids: {
          id: number;
          bidder_id: number;
          amount: string;
          created_at: string;
        }[];
      }
    >
  >({});
  const [error, setError] = useState("");
  const [bids, setBids] = useState<Record<number, string>>({});
  useEffect(() => {
    let alive = true;
    const load = async () => {
      try {
        const rows = await api("/auctions?offset=" + offset);
        if (alive) {
          setAuctions(rows);
          setError("");
        }
      } catch (e) {
        if (alive) setError((e as Error).message);
      }
    };
    if (!busy) void load();
    const timer = setInterval(() => {
      if (!busy) void load();
    }, 5000);
    return () => {
      alive = false;
      clearInterval(timer);
    };
  }, [busy, offset]);
  return (
    <>
      <p className="eyebrow">GUILDA · ESPÓLIOS DE AVENTURA</p>
      <h2>Salão de Leilões</h2>
      <p>
        Apenas jogadores. Lance inicial de 20% do valor base total, arredondado
        para cima, com mínimo configurado. Não há teto de lance. O ouro vencedor
        vai para a Guilda ou sink configurado, sem pagamento ao antigo dono.
      </p>
      <p>
        Saldo disponível: <strong>{state.coins_exact}</strong> · {state.economy_mode==='LUNAR'?'Reserva Lunar (g equivalentes)':'Ouro reservado'}:{" "}
        {state.reserved_gold}. A reserva sai do saldo disponível; quando
        superado, o lance é devolvido e compensa dívidas.
      </p>
      {state.coins_exact.startsWith("-") && (
        <p className="debt">
          Dívida médica ativa. Não é possível dar lances enquanto seu saldo for
          zero ou negativo.
        </p>
      )}
      {error && <p role="alert">{error}</p>}
      <div className="auction-list">
        {auctions.map((a) => {
          const minimum =
            BigInt(a.highest_bid) > 0n
              ? BigInt(a.highest_bid) + 1n
              : BigInt(a.opening_price);
          const amount = bids[a.id] ?? minimum.toString();
          const valid = /^[0-9]+$/.test(amount) && BigInt(amount) >= minimum;
          const open = a.accepts_bids;
          return (
            <article className="auction-card" key={a.id}>
              <h3>
                {a.name} ×{a.quantity} <small>#{a.id}</small>
              </h3>
              <p>{a.description}</p>
              <p>
                Tipo: {a.kind} · Poder: {a.attributes?.power} · Origem: {a.origin==="guild_debt"?"Confisco da Guilda":"Espólio histórico de morte #"+a.death_event_id}
              </p>
              <p>
                Próximo lance: {a.next_bid} · Incremento mínimo:{" "}
                {a.minimum_increment} · Destino: {a.proceeds_destination}
              </p>
              <p>Entrega: mesmo item/stack, desequipado, ao vencedor.</p>
              {a.protected && (
                <p className="debt">
                  Item protegido: negociação suspensa para recuperação
                  administrativa individual.
                </p>
              )}
              <button
                className="secondary"
                disabled={busy}
                onClick={() => {
                  void api("/auctions/" + a.id)
                    .then((d) => setDetails({ ...details, [a.id]: d }))
                    .catch((e) => setError(e.message));
                }}
              >
                Detalhes e histórico
              </button>
              {details[a.id] && (
                <ul>
                  {details[a.id].bids.length ? (
                    details[a.id].bids.map((b) => (
                      <li key={b.id}>
                        Jogador #{b.bidder_id}: {b.amount} moedas ·{" "}
                        {new Date(b.created_at).toLocaleString()}
                      </li>
                    ))
                  ) : (
                    <li>Nenhum lance registrado.</li>
                  )}
                </ul>
              )}
              <p>
                Inicial: {a.opening_price} · Maior lance: {a.highest_bid}
                {a.highest_bidder_id === state.character.id && ["OPEN","CLOSED"].includes(a.status)
                  ? " · sua reserva neste anúncio: "+a.highest_bid
                  : ""}
              </p>
              <p>
                {a.status === "UNSOLD"
                  ? "SEM LANCES · item arquivado em custódia"
                  : a.status === "SETTLED"
                    ? "FINALIZADO · entregue ao vencedor"
                    : a.status}{" "}
                · Fim: {new Date(a.ends_at).toLocaleString()} · {new Date(a.ends_at).getTime()>Date.now()?Math.ceil((new Date(a.ends_at).getTime()-Date.now())/60000)+" minutos restantes":"prazo encerrado"}
              </p>
              {open && (
                <form
                  onSubmit={(e) => {
                    e.preventDefault();
                    if (valid)
                      action("/auctions/" + a.id + "/bids", {
                        amount,
                        request_id: crypto.randomUUID(),
                      });
                  }}
                >
                  <label>
                    Lance em moedas
                    <input
                      aria-label={"Lance no leilão " + a.id}
                      inputMode="numeric"
                      pattern="[0-9]+"
                      value={amount}
                      onChange={(e) =>
                        setBids({ ...bids, [a.id]: e.target.value })
                      }
                      disabled={busy}
                      required
                    />
                  </label>
                  <button
                    disabled={busy || !valid || BigInt(state.coins_exact) <= 0n}
                  >
                    CONFIRMAR LANCE
                  </button>
                </form>
              )}
            </article>
          );
        })}
      </div>
      {!auctions.length && <p>Nenhum leilão nesta página.</p>}
      <div className="actions">
        <button
          className="secondary"
          disabled={busy || offset === 0}
          onClick={() => setOffset(Math.max(0, offset - 100))}
        >
          Página anterior
        </button>
        <button
          className="secondary"
          disabled={busy || auctions.length < 100}
          onClick={() => setOffset(offset + 100)}
        >
          Próxima página
        </button>
      </div>
      <p>
        Prazo provisório definido pelo servidor. Leilões expirados são
        resolvidos automaticamente; sem lances, o item permanece arquivado e não
        é destruído.
      </p>
    </>
  );
}

export function PersonalRecovery({
  state,
  busy,
  action,
}: {
  state: State;
  busy: boolean;
  action: Action;
}) {
  const [items, setItems] = useState<any[]>([]);
  const [error, setError] = useState("");
  useEffect(() => {
    let active = true;
    api("/recovery")
      .then((r) => {
        if (active) setItems(r);
      })
      .catch((e) => {
        if (active) setError(String(e.message));
      });
    return () => {
      active = false;
    };
  }, [state]);
  return (
    <>
      <h2>Recuperação pessoal</h2>
      <p>
        O Guardião de Recuperação, na Guilda, guarda somente seus itens
        valiosos. Preço: valor-base + 100% = 200%. Itens comuns perdidos são
        destruídos.
      </p>
      <p role="status">{error}</p>
      {items.length === 0 ? (
        <p>Nenhum item para recuperar.</p>
      ) : (
        items.map((i) => (
          <article key={i.id}>
            <h3>
              {i.name} ×{i.quantity}
            </h3>
            <p>
              Valor-base: {i.base_value} · Recuperação: {i.price} moedas (+100%)
            </p>
            {i.recovered ? (
              <p>Já recuperado</p>
            ) : (
              <button
                disabled={busy}
                onClick={() => {
                  if (
                    window.confirm(
                      `Pagar ${i.price} moedas para recuperar este item?`,
                    )
                  )
                    action(`/recovery/${i.id}/recover`, {
                      request_id: crypto.randomUUID(),
                    });
                }}
              >
                Recuperar
              </button>
            )}
          </article>
        ))
      )}
    </>
  );
}
