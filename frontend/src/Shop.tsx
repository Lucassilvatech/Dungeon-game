import { useEffect, useRef, useState } from "react";
import { api, type State } from "./api";
import { GameDialog, commerceMessage, type Transact } from "./GameDialog";
type Card = {
  key: string;
  name: string;
  definition_id: string | null;
  item_id: number | null;
  quantity: string;
  unit_price_units: string;
  maximum_quantity: string;
  enabled: boolean;
  fixed_margin_units: string;
  minimum_lot_size: number;
  order_step: number;
  minimum_total_price_units: string;
  price_revision: unknown;
  market_revision: number;
};
type Offer = {
  row: Card;
  direction: "buy" | "sell";
  quote: any;
  request_id: string;
  notice?: string;
};
export function Shop({
  state,
  busy,
  transact,
  npcId,
  npcName,
}: {
  state: State;
  busy: boolean;
  transact: Transact;
  npcId?: string;
  npcName?: string;
}) {
  const [data, setData] = useState<{
      active: boolean;
      buy: Card[];
      sell: Card[];
    } | null>(null),
    [search, setSearch] = useState(""),
    [values, setValues] = useState<Record<string, string>>({}),
    [error, setError] = useState(""),
    [pending, setPending] = useState(false),
    [offer, setOffer] = useState<Offer | null>(null);
  const previousLots = useRef<Record<string, string>>({});
  const [totals, setTotals] = useState<Record<string, string>>({});
  const base = npcId ? `/economy/npcs/${npcId}` : "/economy/shop/catalog";
  const catalogPath = npcId ? base + "/shop" : base;
  const service = state.map.service_npcs?.find((n) => n.id === npcId);
  const nearNpc =
    !npcId ||
    (!!service &&
      state.room.id === "city1" &&
      Math.abs(state.character.x - service.x) +
        Math.abs(state.character.y - service.y) <=
        1);
  const load = async () => setData(await api(catalogPath));
  useEffect(() => {
    let live = true;
    const refresh = () =>
      api(catalogPath)
        .then((d) => {
          if (live) setData(d);
        })
        .catch((e) => {
          if (live) setError(commerceMessage(e));
        });
    void refresh();
    const timer = setInterval(refresh, 2500);
    return () => {
      live = false;
      clearInterval(timer);
    };
  }, [busy, npcId]);
  const key = (r: Card, direction: string) => direction + ":" + r.key;
  const amount = (r: Card, direction: string) =>
    values[key(r, direction)] ?? String(r.minimum_lot_size);
  const valid = (s: string) =>
    /^\d+$/.test(s) && BigInt(s) > 0n && BigInt(s) <= 9007199254740991n;
  const payload = (row: Card, direction: string, n: string) => ({
    definition_id: row.definition_id,
    item_id: row.item_id,
    quantity: Number(n),
    operation_type: direction,
  });
  useEffect(() => {
    if (!data) return;
    const changed: Record<string, string> = {};
    for (const direction of ["buy", "sell"] as const)
      for (const row of data[direction]) {
        const k = key(row, direction),
          lot = `${row.minimum_lot_size}:${row.order_step}`;
        if (previousLots.current[k] && previousLots.current[k] !== lot) {
          const value = values[k];
          if (
            value &&
            (!valid(value) ||
              BigInt(value) < BigInt(row.minimum_lot_size) ||
              BigInt(value) % BigInt(row.order_step))
          )
            changed[k] = String(row.minimum_lot_size);
        }
        previousLots.current[k] = lot;
      }
    if (Object.keys(changed).length) setValues((v) => ({ ...v, ...changed }));
  }, [data]);
  const totalKey = (r: Card, d: string, n: string) =>
    key(r, d) +
    ":" +
    n +
    ":" +
    JSON.stringify(r.price_revision) +
    ":" +
    r.market_revision;
  useEffect(() => {
    let live = true;
    const timer = setTimeout(() => {
      for (const direction of ["buy", "sell"] as const)
        for (const row of data?.[direction] ?? []) {
          const n = amount(row, direction),
            k = totalKey(row, direction, n);
          if (!valid(n) || n === String(row.minimum_lot_size) || totals[k])
            continue;
          void api(base + "/quote", payload(row, direction, n))
            .then((q) => {
              if (live) setTotals((v) => ({ ...v, [k]: q.total_price_units }));
            })
            .catch(() => {});
        }
    }, 150);
    return () => {
      live = false;
      clearTimeout(timer);
    };
  }, [values, data, npcId]);
  const prepare = async (
    row: Card,
    direction: "buy" | "sell",
    quantity = amount(row, direction),
    notice?: string,
  ) => {
    setError("");
    setPending(true);
    try {
      if (!valid(quantity) || BigInt(quantity) > BigInt(row.maximum_quantity))
        throw Error(
          direction === "sell"
            ? "Você não possui essa quantidade vendável."
            : "A quantidade excede o que você pode comprar com seu caixa e mochila.",
        );
      const q = await api(base + "/quote", payload(row, direction, quantity));
      if (!q.payment.payable)
        throw Error(
          direction === "sell"
            ? "A Guilda não possui moedas adequadas para pagar este valor."
            : "Você possui valor insuficiente ou não possui a combinação de moedas necessária.",
        );
      setOffer({
        row,
        direction,
        quote: q,
        request_id: crypto.randomUUID(),
        notice,
      });
    } catch (e) {
      setError(commerceMessage(e));
    } finally {
      setPending(false);
    }
  };
  const confirm = async () => {
    if (!offer) return;
    setPending(true);
    setError("");
    const current = offer;
    try {
      await transact(base + "/trade", {
        ...payload(
          current.row,
          current.direction,
          String(current.quote.quantity),
        ),
        quote: current.quote.quote_hash,
        request_id: current.request_id,
      });
      setOffer(null);
      setValues((values) => ({
        ...values,
        [key(current.row, current.direction)]: String(
          current.row.minimum_lot_size,
        ),
      }));
      await load();
    } catch (e) {
      if (e instanceof Error && e.message.includes("STALE_QUOTE")) {
        try {
          const q = await api(
            base + "/quote",
            payload(
              current.row,
              current.direction,
              String(current.quote.quantity),
            ),
          );
          setOffer({
            ...current,
            quote: q,
            request_id: crypto.randomUUID(),
            notice:
              "O preço ou estoque mudou. Confira os novos valores antes de confirmar.",
          });
        } catch (other) {
          setOffer(null);
          setError(commerceMessage(other));
        }
      } else setError(commerceMessage(e));
      await load();
    } finally {
      setPending(false);
    }
  };
  const card = (row: Card, direction: "buy" | "sell") => {
    const s = amount(row, direction),
      maximum = BigInt(row.maximum_quantity),
      value = valid(s) ? BigInt(s) : 0n,
      total =
        s === String(row.minimum_lot_size)
          ? row.minimum_total_price_units
          : (totals[totalKey(row, direction, s)] ?? "…"),
      label = direction === "sell" ? "Vender" : "Comprar";
    const change = (n: bigint) =>
      setValues((v) => ({
        ...v,
        [key(row, direction)]: (n < 1n
          ? 1n
          : n > maximum
            ? maximum
            : n
        ).toString(),
      }));
    return (
      <article
        className="shop-card"
        key={row.key}
        aria-label={`${label} ${row.name}`}
      >
        <h4>{row.name}</h4>
        <p>
          {direction === "sell" ? "Você possui" : "Estoque"}:{" "}
          <strong>{row.quantity}</strong>
        </p>
        <p>
          {npcName ?? "Guilda"} {direction === "sell" ? "compra" : "vende"}:{" "}
          <strong>{row.unit_price_units}</strong> por unidade
        </p>
        {row.minimum_lot_size > 1 && (
          <p>
            Lote mínimo: {row.minimum_lot_size} · múltiplos de {row.order_step}
          </p>
        )}
        {BigInt(row.fixed_margin_units) > 0n && (
          <p>Margem por operação: {row.fixed_margin_units}</p>
        )}
        <div className="shop-quantity">
          <button
            aria-label={`Diminuir ${row.name} para ${direction === "sell" ? "vender" : "comprar"}`}
            disabled={busy || pending || value <= BigInt(row.minimum_lot_size)}
            onClick={() => change(value - BigInt(row.order_step))}
          >
            −
          </button>
          <label>
            <span className="sr-only">
              Quantidade de {row.name} para{" "}
              {direction === "sell" ? "vender" : "comprar"}
            </span>
            <input
              inputMode="numeric"
              pattern="[0-9]*"
              value={s}
              onChange={(e) =>
                setValues((v) => ({
                  ...v,
                  [key(row, direction)]: e.target.value,
                }))
              }
            />
          </label>
          <button
            aria-label={`Aumentar ${row.name} para ${direction === "sell" ? "vender" : "comprar"}`}
            disabled={busy || pending || value >= maximum}
            onClick={() => change(value + BigInt(row.order_step))}
          >
            +
          </button>
          <button
            className="secondary"
            disabled={busy || pending || maximum === 0n}
            onClick={() => change(maximum)}
          >
            {direction === "sell" ? "TUDO" : "MÁXIMO"}
          </button>
        </div>
        <p>
          {direction === "sell" ? "Você receberá" : "Custo total"}:{" "}
          <strong>{total.toString()}</strong>
        </p>
        {!row.enabled && (
          <p>
            {direction === "sell" ? "Compra" : "Venda"} desativada para este
            item.
          </p>
        )}
        {direction === "buy" && row.enabled && maximum === 0n && (
          <p>Sem capacidade, saldo ou moedas adequadas para comprar agora.</p>
        )}
        <button
          disabled={
            busy ||
            pending ||
            !!state.battle ||
            !nearNpc ||
            !row.enabled ||
            maximum === 0n
          }
          onClick={() => void prepare(row, direction)}
        >
          {label} {row.name}
        </button>
      </article>
    );
  };
  const filtered = (rows: Card[]) =>
    rows.filter((r) =>
      r.name
        .toLocaleLowerCase("pt-BR")
        .includes(search.toLocaleLowerCase("pt-BR").trim()),
    );
  return (
    <section className="guild-shop">
      <h2>{npcId ? "Loja · " + npcName : "Loja da Guilda"}</h2>
      <p>
        {npcId
          ? "Negocie o estoque disponível junto ao NPC na vila."
          : "Escolha seus materiais e negocie junto à recepcionista."}
      </p>
      <label className="shop-search">
        Pesquisar item
        <input
          type="search"
          placeholder="Pesquisar item…"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
      </label>
      {!nearNpc && (
        <p>Aproxime-se do NPC para comprar. Use “Ir até” para caminhar.</p>
      )}
      {error && !offer && <p role="alert">{error}</p>}
      {pending && <p role="status">Preparando a operação…</p>}
      {!data && <p>Carregando a loja…</p>}
      {data && !data.active && (
        <p>Comércio indisponível enquanto a economia não estiver ativa.</p>
      )}
      {data?.active && (
        <>
          {(npcId ? (["buy"] as const) : (["buy", "sell"] as const)).map(
            (direction) => (
              <section key={direction}>
                <h3>
                  {direction === "buy"
                    ? npcId
                      ? "Comprar de " + npcName
                      : "Comprar da Guilda"
                    : "Vender para a Guilda"}
                </h3>
                <div className="shop-grid">
                  {filtered(data[direction]).map((r) => card(r, direction))}
                </div>
                {!filtered(data[direction]).length && (
                  <p>
                    {search
                      ? "Nenhum item encontrado."
                      : direction === "buy"
                        ? "Estoque esgotado."
                        : "Você não possui itens vendáveis."}
                  </p>
                )}
              </section>
            ),
          )}
        </>
      )}
      {offer && (
        <GameDialog
          title={
            offer.direction === "sell" ? "Confirmar venda" : "Confirmar compra"
          }
          busy={busy || pending}
          onCancel={() => {
            setOffer(null);
            setError("");
          }}
        >
          <h3>{offer.row.name}</h3>
          <p>
            Quantidade: <strong>{offer.quote.quantity}</strong>
          </p>
          <p>
            {offer.direction === "sell" ? "Você receberá" : "Custo"}:{" "}
            <strong>{offer.quote.total_price_units} unidades monetárias</strong>
          </p>
          {offer.notice && <p role="status">{offer.notice}</p>}
          {!offer.quote.payment.payable && (
            <p role="alert">
              O pagador não possui as moedas necessárias. Cancele e revise a
              quantidade.
            </p>
          )}
          {error && <p role="alert">{error}</p>}
          <div className="dialog-actions">
            <button
              className="secondary"
              disabled={busy || pending}
              onClick={() => {
                setOffer(null);
                setError("");
              }}
            >
              Cancelar
            </button>
            <button
              disabled={busy || pending || !offer.quote.payment.payable}
              onClick={() => void confirm()}
            >
              {offer.direction === "sell"
                ? "Confirmar venda"
                : "Confirmar compra"}
            </button>
          </div>
        </GameDialog>
      )}
    </section>
  );
}
