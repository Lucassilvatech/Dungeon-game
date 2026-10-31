import { useEffect, useState } from "react";
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
}: {
  state: State;
  busy: boolean;
  transact: Transact;
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
  const load = async () => setData(await api("/economy/shop/catalog"));
  useEffect(() => {
    let live = true;
    api("/economy/shop/catalog")
      .then((d) => {
        if (live) setData(d);
      })
      .catch((e) => {
        if (live) setError(commerceMessage(e));
      });
    return () => {
      live = false;
    };
  }, [busy]);
  const key = (r: Card, direction: string) => direction + ":" + r.key;
  const amount = (r: Card, direction: string) =>
    values[key(r, direction)] ?? "1";
  const valid = (s: string) =>
    /^\d+$/.test(s) && BigInt(s) > 0n && BigInt(s) <= 9007199254740991n;
  const payload = (row: Card, direction: string, n: string) => ({
    definition_id: row.definition_id,
    item_id: row.item_id,
    quantity: Number(n),
    operation_type: direction,
  });
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
      const q = await api(
        "/economy/shop/catalog/quote",
        payload(row, direction, quantity),
      );
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
      await transact("/economy/shop/catalog/trade", {
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
        [key(current.row, current.direction)]: "1",
      }));
      await load();
    } catch (e) {
      if (e instanceof Error && e.message.includes("STALE_QUOTE")) {
        try {
          const q = await api(
            "/economy/shop/catalog/quote",
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
      total = value * BigInt(row.unit_price_units),
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
          Guilda {direction === "sell" ? "compra" : "vende"}:{" "}
          <strong>{row.unit_price_units}</strong> por unidade
        </p>
        <div className="shop-quantity">
          <button
            aria-label={`Diminuir ${row.name} para ${direction === "sell" ? "vender" : "comprar"}`}
            disabled={busy || pending || value <= 1n}
            onClick={() => change(value - 1n)}
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
            onClick={() => change(value + 1n)}
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
            busy || pending || !!state.battle || !row.enabled || maximum === 0n
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
      <h2>Loja da Guilda</h2>
      <p>Escolha seus materiais e negocie junto à recepcionista.</p>
      <label className="shop-search">
        Pesquisar item
        <input
          type="search"
          placeholder="Pesquisar item…"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
      </label>
      {error && !offer && <p role="alert">{error}</p>}
      {pending && <p role="status">Preparando a operação…</p>}
      {!data && <p>Carregando a loja…</p>}
      {data && !data.active && (
        <p>Comércio indisponível enquanto a economia não estiver ativa.</p>
      )}
      {data?.active && (
        <>
          {(["buy", "sell"] as const).map((direction) => (
            <section key={direction}>
              <h3>
                {direction === "buy"
                  ? "Comprar da Guilda"
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
          ))}
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
