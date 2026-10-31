import { useEffect, useState } from "react";
import type { NpcEconomyState, NpcPolicy } from "../npcTypes";
type Props = {
  data: { npcs: NpcEconomyState[]; market: any };
  request: (p: string, b?: unknown) => Promise<any>;
  run: (f: () => Promise<void>) => Promise<void>;
  refresh: () => Promise<void>;
  busy: boolean;
  canManage: boolean;
};
const profileFlags = [
  ["enabled", "Ativo"],
  ["production_enabled", "Produção ativa"],
  ["purchase_enabled", "Compras ativas"],
  ["sale_enabled", "Vendas ativas"],
] as const;
const policyNames: Record<string, string> = {
  capacity: "Capacidade",
  reorder_point: "Ponto de reposição",
  order_quantity: "Quantidade por pedido",
  target_stock: "Estoque-alvo",
  minimum_lot_size: "Lote mínimo",
  order_step: "Passo do lote",
};
const factorNames: Record<string, string> = {
  alchemy: "Alquimia",
  smelting: "Fundição",
  smithing: "Ferraria",
};
const statuses: Record<string, string> = {
  IDLE: "Aguardando ciclo",
  AT_TARGET: "Alvo atendido",
  WAIT_MATERIAL: "Sem ingredientes",
  WAIT_STOCK: "Fornecedor sem estoque",
  WAIT_INSUFFICIENT_FUNDS: "Caixa insuficiente",
  WAIT_INSUFFICIENT_DENOMINATIONS: "Faltam moedas exatas",
  WAIT_CAPACITY: "Capacidade insuficiente",
  WAIT_DISABLED: "Compra desativada",
  PRODUCED: "Produção concluída",
  PURCHASED: "Compra recebida",
  STOCKED: "Estoque suficiente",
};
const bpsText = (n: number) =>
  `${Math.floor(n / 10000)},${String(n % 10000).padStart(4, "0")}`;
function factor(text: string) {
  const match = /^(\d+)(?:[,.](\d{1,4}))?$/.exec(text);
  if (!match)
    throw Error("Use um fator positivo com até quatro casas decimais.");
  return Number(match[1]) * 10000 + Number((match[2] ?? "").padEnd(4, "0"));
}
export function NpcEconomyAdmin({
  data,
  request,
  run,
  refresh,
  busy,
  canManage,
}: Props) {
  const [view, setView] = useState(data),
    [draft, setDraft] = useState<NpcEconomyState | null>(null),
    [base, setBase] = useState<NpcEconomyState | null>(null),
    [factors, setFactors] = useState<Record<string, string>>({}),
    [reason, setReason] = useState(""),
    [error, setError] = useState(""),
    [preview, setPreview] = useState<any>(null),
    [confirmed, setConfirmed] = useState(false),
    [attempted, setAttempted] = useState(false);
  const [source, setSource] = useState("guild"),
    [destination, setDestination] = useState("merchant"),
    [material, setMaterial] = useState("herb"),
    [quantity, setQuantity] = useState("10"),
    [stockReason, setStockReason] = useState(""),
    [fundSource, setFundSource] = useState("treasury"),
    [fundTarget, setFundTarget] = useState("npc:merchant"),
    [amount, setAmount] = useState("0"),
    [fundReason, setFundReason] = useState("");
  useEffect(() => setView(data), [data]);
  useEffect(() => {
    let alive = true;
    const timer = setInterval(() => {
      if (!busy)
        void request("/npc-economy")
          .then((d) => {
            if (alive) setView(d);
          })
          .catch((e) => {
            if (alive) setError(e.message);
          });
    }, 3000);
    return () => {
      alive = false;
      clearInterval(timer);
    };
  }, [busy]);
  useEffect(() => {
    setPreview(null);
    setConfirmed(false);
  }, [
    draft,
    reason,
    factors,
    source,
    destination,
    material,
    quantity,
    stockReason,
    fundSource,
    fundTarget,
    amount,
    fundReason,
  ]);
  const perform = (fn: () => Promise<void>) =>
    void run(async () => {
      setError("");
      try {
        await fn();
      } catch (e) {
        setError((e as Error).message);
      }
    });
  const propose = (
    action: string,
    target: string,
    params: any,
    why: string,
  ) => {
    setAttempted(true);
    if (why.trim().length < 10) {
      setError("Informe uma justificativa com pelo menos 10 caracteres.");
      return;
    }
    perform(async () => {
      setPreview(
        await request("/operations/preview", {
          operation_id: crypto.randomUUID(),
          action,
          target,
          params,
          reason: why,
        }),
      );
      setConfirmed(false);
    });
  };
  const label = (id: string) =>
    view.npcs.flatMap((n) => n.items).find((i) => i.definition_id === id)
      ?.name ?? id;
  const edit = (npc: NpcEconomyState) => {
    setBase(structuredClone(npc));
    setDraft(structuredClone(npc));
    setFactors(
      Object.fromEntries(
        Object.entries(npc.factors).map(([k, v]) => [k, bpsText(v)]),
      ),
    );
    setReason("");
    setError("");
    setPreview(null);
  };
  const updatePolicy = (index: number, key: string, value: any) => {
    if (draft)
      setDraft({
        ...draft,
        items: draft.items.map((p, i) =>
          i === index ? { ...p, [key]: value } : p,
        ),
      });
  };
  const save = () => {
    if (!draft || !base) return;
    try {
      const params: any = { expected_revision: base.revision };
      for (const [key] of profileFlags) params[key] = draft[key];
      if (["merchant", "guild"].includes(draft.id))
        params.fixed_margin = draft.fixed_margin;
      params.factors = Object.fromEntries(
        Object.entries(factors).map(([k, v]) => [k, factor(v)]),
      );
      params.policies = draft.items
        .filter((p, i) =>
          [
            ...Object.keys(policyNames),
            "production_enabled",
            "buy_enabled",
            "sell_enabled",
          ].some((k) => (p as any)[k] !== (base.items[i] as any)[k]),
        )
        .map((p) => ({
          definition_id: p.definition_id,
          expected_revision: p.revision,
          ...Object.fromEntries(
            [
              ...Object.keys(policyNames),
              "production_enabled",
              "buy_enabled",
              "sell_enabled",
            ].map((k) => [k, (p as any)[k]]),
          ),
        }));
      propose("npc.configure", draft.id, params, reason);
    } catch (e) {
      setError((e as Error).message);
    }
  };
  return (
    <section className="npc-economy-admin">
      <h3>Economia dos NPCs</h3>
      <p>
        Revisão de mercado: {view.market?.revision} · produção e reposição são
        executadas pelo servidor.
      </p>
      {error && <p role="alert">{error}</p>}
      <div className="npc-overview">
        {view.npcs.map((n) => (
          <article key={n.id}>
            <h4>{n.name}</h4>
            <p>
              {n.enabled ? "Ativo" : "Pausado"} · caixa{" "}
              {(BigInt(n.wallet.total_weight_mg) / 1000n).toString()} unidades
            </p>
            <p>
              Moedas: {n.wallet.coins.coin_large} grandes ·{" "}
              {n.wallet.coins.coin_medium} médias · {n.wallet.coins.coin_small}{" "}
              pequenas
            </p>
            {Object.entries(n.factors).map(([k, v]) => (
              <p key={k}>
                Fator {factorNames[k] ?? k}: {bpsText(v)}
              </p>
            ))}
            {["guild", "merchant"].includes(n.id) && (
              <p>Margem fixa por operação: {n.fixed_margin}</p>
            )}
            <p>Última atualização: {n.last_update}</p>
            <div className="npc-policy-grid">
              {n.items.map((p) => (
                <article key={p.definition_id}>
                  <h5>{p.name}</h5>
                  <p>
                    Estoque: {p.stock} · capacidade {p.capacity} · alvo{" "}
                    {p.target_stock}
                  </p>
                  <p>
                    Preço atual: {p.price_units} · estado{" "}
                    {statuses[p.status] ?? p.status}
                  </p>
                  {p.recipe && (
                    <p>
                      Receita:{" "}
                      {Object.entries(p.recipe)
                        .map(([id, q]) => `${q} ${label(id)}`)
                        .join(" + ")}{" "}
                      → 1 {p.name}
                    </p>
                  )}
                  {!p.recipe && (
                    <p>
                      Reposição: abaixo de {p.reorder_point} · pedido{" "}
                      {p.order_quantity}
                    </p>
                  )}
                  {n.id === "merchant" && (
                    <>
                      <p>
                        Lote: {p.minimum_lot_size}, passo {p.order_step}
                      </p>
                      <p>
                        Base {p.minimum_lot_quote.base_price_units} + margem{" "}
                        {p.minimum_lot_quote.fixed_margin_units} ={" "}
                        {p.minimum_lot_quote.total_price_units}
                      </p>
                    </>
                  )}
                </article>
              ))}
            </div>
            {!n.items.length && (
              <p>
                Estoque:{" "}
                {n.stock_items
                  .map((i) => `${i.name} ×${i.quantity}`)
                  .join(" · ") || "vazio"}
              </p>
            )}
            {canManage && (
              <button disabled={busy} onClick={() => edit(n)}>
                Configurar {n.name}
              </button>
            )}
            <details>
              <summary>
                Produção, compras, vendas e histórico de {n.name}
              </summary>
              {n.history.map((h) => (
                <details key={h.id}>
                  <summary>
                    {h.occurred_at} · {h.kind}
                  </summary>
                  <pre>{JSON.stringify(h, null, 2)}</pre>
                </details>
              ))}
            </details>
          </article>
        ))}
      </div>
      {canManage && draft && (
        <fieldset>
          <legend>Configuração de {draft.name}</legend>
          {profileFlags.map(([key, name]) => (
            <label key={key}>
              <input
                type="checkbox"
                aria-label={name}
                checked={draft[key]}
                onChange={(e) =>
                  setDraft({ ...draft, [key]: e.target.checked })
                }
              />
              {name}
            </label>
          ))}
          {["guild", "merchant"].includes(draft.id) && (
            <label>
              Margem fixa
              <input
                aria-label="Margem fixa"
                type="number"
                min={0}
                value={draft.fixed_margin}
                onChange={(e) =>
                  setDraft({ ...draft, fixed_margin: Number(e.target.value) })
                }
              />
            </label>
          )}
          {Object.keys(factors).map((k) => (
            <label key={k}>
              Fator {factorNames[k] ?? k}
              <input
                aria-label={"Fator " + (factorNames[k] ?? k)}
                inputMode="decimal"
                value={factors[k]}
                onChange={(e) =>
                  setFactors({ ...factors, [k]: e.target.value })
                }
              />
            </label>
          ))}
          {draft.items.map((p, index) => (
            <fieldset key={p.definition_id}>
              <legend>{p.name}</legend>
              {Object.entries(policyNames).map(([key, name]) => (
                <label key={key}>
                  {name}
                  <input
                    type="number"
                    min={0}
                    aria-label={name + " de " + p.name}
                    value={(p as any)[key]}
                    onChange={(e) =>
                      updatePolicy(index, key, Number(e.target.value))
                    }
                  />
                </label>
              ))}
              {[
                ["production_enabled", "Produção do item"],
                ["buy_enabled", "Compra do material"],
                ["sell_enabled", "Venda do item"],
              ].map(([key, name]) => (
                <label key={key}>
                  <input
                    type="checkbox"
                    aria-label={name + " " + p.name}
                    checked={(p as any)[key]}
                    onChange={(e) => updatePolicy(index, key, e.target.checked)}
                  />
                  {name}
                </label>
              ))}
            </fieldset>
          ))}
          <label>
            Justificativa da configuração
            <textarea
              aria-label="Justificativa da configuração"
              minLength={10}
              maxLength={500}
              value={reason}
              onChange={(e) => setReason(e.target.value)}
            />
          </label>
          <p>Justificativa obrigatória — mínimo de 10 caracteres.</p>
          <button disabled={busy} onClick={save}>
            Revisar configuração NPC
          </button>
          <button
            className="secondary"
            disabled={busy}
            onClick={() => {
              const fresh = view.npcs.find((n) => n.id === draft.id);
              if (fresh) edit(fresh);
            }}
          >
            Atualizar rascunho NPC
          </button>
        </fieldset>
      )}
      {canManage && (
        <>
          <fieldset>
            <legend>Transferir estoque existente</legend>
            <p>
              Movimentação administrativa de patrimônio; não cria mercadoria nem
              dinheiro.
            </p>
            <label>
              Origem do estoque
              <select
                aria-label="Origem do estoque"
                value={source}
                onChange={(e) => setSource(e.target.value)}
              >
                {view.npcs.map((n) => (
                  <option key={n.id} value={n.id}>
                    {n.name}
                  </option>
                ))}
              </select>
            </label>
            <label>
              Destino do estoque
              <select
                aria-label="Destino do estoque"
                value={destination}
                onChange={(e) => setDestination(e.target.value)}
              >
                {view.npcs.map((n) => (
                  <option key={n.id} value={n.id}>
                    {n.name}
                  </option>
                ))}
              </select>
            </label>
            <label>
              Material existente
              <select
                aria-label="Material existente"
                value={material}
                onChange={(e) => setMaterial(e.target.value)}
              >
                {view.npcs
                  .find((n) => n.id === source)
                  ?.stock_items.map((i) => (
                    <option value={i.definition_id} key={i.definition_id}>
                      {i.name} · {i.quantity}
                    </option>
                  ))}
              </select>
            </label>
            <label>
              Quantidade de material
              <input
                aria-label="Quantidade de material"
                type="number"
                min={1}
                value={quantity}
                onChange={(e) => setQuantity(e.target.value)}
              />
            </label>
            <label>
              Justificativa da transferência
              <textarea
                aria-label="Justificativa da transferência"
                value={stockReason}
                onChange={(e) => setStockReason(e.target.value)}
              />
            </label>
            <p>Mínimo de 10 caracteres.</p>
            <button
              disabled={busy}
              onClick={() =>
                propose(
                  "npc.stock_transfer",
                  source,
                  {
                    destination,
                    definition_id: material,
                    quantity: Number(quantity),
                  },
                  stockReason,
                )
              }
            >
              Revisar transferência material
            </button>
          </fieldset>
          <fieldset>
            <legend>Financiar caixa com moedas existentes</legend>
            <label>
              Conta financiadora
              <input
                aria-label="Conta financiadora"
                value={fundSource}
                onChange={(e) => setFundSource(e.target.value)}
              />
            </label>
            <label>
              Caixa destinatário
              <select
                aria-label="Caixa destinatário"
                value={fundTarget}
                onChange={(e) => setFundTarget(e.target.value)}
              >
                {view.npcs.map((n) => (
                  <option key={n.id} value={n.account_id}>
                    {n.name}
                  </option>
                ))}
              </select>
            </label>
            <label>
              Valor para financiar
              <input
                aria-label="Valor para financiar"
                type="number"
                min={1}
                value={amount}
                onChange={(e) => setAmount(e.target.value)}
              />
            </label>
            <label>
              Justificativa do financiamento
              <textarea
                aria-label="Justificativa do financiamento"
                value={fundReason}
                onChange={(e) => setFundReason(e.target.value)}
              />
            </label>
            <p>
              Mínimo de 10 caracteres. Pagamento exige as moedas físicas exatas.
            </p>
            <button
              disabled={busy}
              onClick={() =>
                propose(
                  "royal.transfer_coins",
                  fundSource,
                  { destination: fundTarget, amount_units: Number(amount) },
                  fundReason,
                )
              }
            >
              Revisar financiamento
            </button>
          </fieldset>
        </>
      )}
      {preview && (
        <section aria-label="Prévia da economia NPC">
          <h4>Revisar impacto</h4>
          <p>{preview.reason}</p>
          {preview.action === "npc.configure" && (
            <>
              <h5>Configuração · antes → depois</h5>
              {profileFlags.map(([key, name]) => (
                <p key={key}>
                  {name}: {preview.before.before[key] ? "Sim" : "Não"} →{" "}
                  {preview.before.proposed[key] ? "Sim" : "Não"}
                </p>
              ))}
              {preview.before.before.fixed_margin !==
                preview.before.proposed.fixed_margin && (
                <p>
                  Margem fixa: {preview.before.before.fixed_margin} →{" "}
                  {preview.before.proposed.fixed_margin}
                </p>
              )}
              {Object.keys(preview.before.proposed.factors).map((key) => (
                <p key={key}>
                  Fator {factorNames[key] ?? key}:{" "}
                  {bpsText(preview.before.before.factors[key])} →{" "}
                  {bpsText(preview.before.proposed.factors[key])}
                </p>
              ))}
              {preview.before.policies.map((p: any) => (
                <article key={p.definition_id}>
                  <h5>
                    {label(p.definition_id)} · estoque atual {p.stock}
                  </h5>
                  {Object.entries(policyNames)
                    .filter(([key]) => p.before[key] !== p.proposed[key])
                    .map(([key, name]) => (
                      <p key={key}>
                        {name}: {p.before[key]} → {p.proposed[key]}
                      </p>
                    ))}
                  {["production_enabled", "buy_enabled", "sell_enabled"]
                    .filter((key) => p.before[key] !== p.proposed[key])
                    .map((key) => (
                      <p key={key}>
                        {
                          (
                            {
                              production_enabled: "Produção",
                              buy_enabled: "Compra",
                              sell_enabled: "Venda",
                            } as Record<string, string>
                          )[key]
                        }
                        : {p.before[key] ? "Sim" : "Não"} →{" "}
                        {p.proposed[key] ? "Sim" : "Não"}
                      </p>
                    ))}
                </article>
              ))}
              <h5>Preços afetados</h5>
              {Object.entries(preview.before.market_proposed.prices)
                .filter(
                  ([key, value]) =>
                    preview.before.market_before.prices[key] !== value,
                )
                .map(([key, value]) => (
                  <p key={key}>
                    {label(key)}: {preview.before.market_before.prices[key]} →{" "}
                    {String(value)}
                  </p>
                ))}
            </>
          )}
          <details>
            <summary>Dados completos da prévia</summary>
            <pre>{JSON.stringify(preview.before, null, 2)}</pre>
          </details>
          <label>
            <input
              aria-label="Confirmar impacto NPC"
              type="checkbox"
              checked={confirmed}
              onChange={(e) => setConfirmed(e.target.checked)}
            />
            Revisei valores, estoque, revisão e consequências.
          </label>
          <button
            disabled={busy || !confirmed}
            onClick={() =>
              perform(async () => {
                await request("/operations/" + preview.id + "/confirm", {
                  confirmed: true,
                  confirmation_token: preview.confirmation_token,
                });
                setPreview(null);
                setDraft(null);
                setBase(null);
                await refresh();
              })
            }
          >
            Confirmar operação NPC
          </button>
        </section>
      )}
    </section>
  );
}
