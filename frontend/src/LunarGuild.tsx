import { useEffect, useState } from "react";
import { api } from "./api";
import { GameDialog, commerceMessage, type Transact } from "./GameDialog";
type Quote = {
  lot_id: number;
  weight_g: number;
  rate: number;
  price_units: string;
  quote_hash: string;
  enabled: boolean;
  free_allowed: boolean;
  payment: { payable: boolean };
};
type Offer = {
  quote: Quote;
  buy: boolean;
  request_id: string;
  notice?: string;
};
export function LunarGuild({
  busy,
  transact,
}: {
  busy: boolean;
  transact: Transact;
}) {
  const [data, setData] = useState<any>(null),
    [error, setError] = useState(""),
    [pending, setPending] = useState(false),
    [offer, setOffer] = useState<Offer | null>(null);
  const load = async () => {
    const d = await api("/lunar/guild-quotes");
    setData(d);
    return d;
  };
  useEffect(() => {
    let live = true;
    api("/lunar/guild-quotes")
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
  const confirm = async () => {
    if (!offer) return;
    setPending(true);
    const old = offer;
    try {
      await transact(old.buy ? "/lunar/guild-buy" : "/lunar/guild-sell", {
        lot_id: old.quote.lot_id,
        quote: old.quote.quote_hash,
        request_id: old.request_id,
      });
      setOffer(null);
      setError("");
      await load();
    } catch (e) {
      if (e instanceof Error && e.message.includes("STALE_QUOTE")) {
        try {
          const d = await load();
          const q = (old.buy ? d.guild_quotes : d.quotes).find(
            (r: Quote) => r.lot_id === old.quote.lot_id,
          );
          if (q)
            setOffer({
              ...old,
              quote: q,
              request_id: crypto.randomUUID(),
              notice: "O preço ou a disponibilidade mudou. Revise novamente.",
            });
          else {
            setOffer(null);
            setError("Esta pepita não está mais disponível.");
          }
        } catch (refreshError) {
          setError(commerceMessage(refreshError));
        }
      } else setError(commerceMessage(e));
    } finally {
      setPending(false);
    }
  };
  const row = (q: Quote, buy: boolean) => (
    <article className="shop-card" data-lot-id={q.lot_id} key={q.lot_id}>
      <h4>Minério Lunar · {q.weight_g} g</h4>
      <p>
        Guilda {buy ? "vende" : "compra"} por <strong>{q.price_units}</strong>{" "}
        unidades
      </p>
      {!q.enabled && <p>{buy ? "Venda" : "Compra"} desativada.</p>}
      {!q.payment.payable && (
        <p>
          {buy ? "Você" : "A Guilda"} não possui moedas adequadas para este
          valor.
        </p>
      )}
      <button
        disabled={
          busy ||
          pending ||
          !data.active ||
          !q.enabled ||
          !q.payment.payable ||
          (q.price_units === "0" && !q.free_allowed)
        }
        onClick={() => {
          setError("");
          setOffer({ quote: q, buy, request_id: crypto.randomUUID() });
        }}
      >
        {buy ? "Comprar" : "Vender"} pepita
      </button>
    </article>
  );
  return (
    <section>
      <h3>Minério Lunar</h3>
      <p>Pepitas inteiras, negociadas pelo peso.</p>
      {error && !offer && <p role="alert">{error}</p>}
      {data && (
        <>
          <h4>Vender suas pepitas</h4>
          <div className="shop-grid">
            {data.quotes.map((q: Quote) => row(q, false))}
          </div>
          {!data.quotes.length && <p>Você não possui pepitas para vender.</p>}
          <h4>Comprar pepitas da Guilda</h4>
          <div className="shop-grid">
            {data.guild_quotes.map((q: Quote) => row(q, true))}
          </div>
          {!data.guild_quotes.length && <p>Sem pepitas no estoque.</p>}
        </>
      )}
      {offer && (
        <GameDialog
          title={
            offer.buy
              ? "Confirmar compra de minério"
              : "Confirmar venda de minério"
          }
          busy={busy || pending}
          onCancel={() => {
            setOffer(null);
            setError("");
          }}
        >
          <h3>Minério Lunar</h3>
          <p>Peso: {offer.quote.weight_g} g · pepita inteira</p>
          <p>
            {offer.buy ? "Custo" : "Você receberá"}:{" "}
            <strong>{offer.quote.price_units} unidades monetárias</strong>
          </p>
          {offer.notice && <p role="status">{offer.notice}</p>}
          {error && <p role="alert">{error}</p>}
          {!offer.quote.payment.payable && (
            <p>O pagador não possui as moedas necessárias.</p>
          )}
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
              {offer.buy ? "Confirmar compra" : "Confirmar venda"}
            </button>
          </div>
        </GameDialog>
      )}
    </section>
  );
}
