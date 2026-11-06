import { useEffect, useId, useState } from "react";
type Props = {
  request: (p: string, b?: unknown) => Promise<any>;
  run: (f: () => Promise<void>) => Promise<void>;
  busy: boolean;
  canManage: boolean;
  refresh: () => Promise<void>;
};
type Draft = {
  base: any;
  buy_price_units: string;
  sell_price_units: string;
  buy_enabled: boolean;
  sell_enabled: boolean;
  acknowledge_free: boolean;
  acknowledge_arbitrage: boolean;
};
const denoms = [
  ["coin_large", "Grandes"],
  ["coin_medium", "Médias"],
  ["coin_small", "Pequenas"],
];
function Reason({
  label,
  value,
  set,
  attempted,
}: {
  label: string;
  value: string;
  set: (s: string) => void;
  attempted: boolean;
}) {
  const id = useId(),
    valid = value.trim().length >= 10 && value.length <= 500;
  return (
    <div className="operation-reason">
      <label>
        {label}
        <textarea
          aria-label={label}
          aria-describedby={id}
          value={value}
          maxLength={500}
          onChange={(e) => set(e.target.value)}
        />
      </label>
      <p id={id}>Justificativa obrigatória — mínimo de 10 caracteres.</p>
      {attempted && !valid && (
        <p role="alert">
          Informe uma justificativa com pelo menos 10 caracteres.
        </p>
      )}
    </div>
  );
}
function risks(buy: string, sell: string, bo: boolean, so: boolean) {
  return {
    arb:
      bo &&
      so &&
      /^\d+$/.test(buy) &&
      /^\d+$/.test(sell) &&
      BigInt(sell) < BigInt(buy),
    free: (bo && /^0+$/.test(buy)) || (so && /^0+$/.test(sell)),
  };
}
function Acknowledgements({
  arb,
  free,
  values,
  set,
}: {
  arb: boolean;
  free: boolean;
  values: { acknowledge_arbitrage: boolean; acknowledge_free: boolean };
  set: (v: any) => void;
}) {
  return (
    <>
      {arb && (
        <div className="price-warning">
          <p>
            A Guilda compra por mais do que vende. Isso pode permitir
            arbitragem.
          </p>
          <label>
            <input
              aria-label="Confirmar possível arbitragem"
              type="checkbox"
              checked={values.acknowledge_arbitrage}
              onChange={(e) =>
                set({ ...values, acknowledge_arbitrage: e.target.checked })
              }
            />
            Confirmo que quero manter esta configuração.
          </label>
        </div>
      )}
      {free && (
        <div className="price-warning">
          <p>Esta configuração permite transferência gratuita.</p>
          <label>
            <input
              aria-label="Autorizar gratuidade"
              type="checkbox"
              checked={values.acknowledge_free}
              onChange={(e) =>
                set({ ...values, acknowledge_free: e.target.checked })
              }
            />
            Confirmo conscientemente a gratuidade.
          </label>
        </div>
      )}
    </>
  );
}
export function GuildCommerceAdmin({
  request,
  run,
  busy,
  canManage,
  refresh,
}: Props) {
  const [data, setData] = useState<any>(null),
    [error, setError] = useState(""),
    [preview, setPreview] = useState<any>(null),
    [confirmed, setConfirmed] = useState(false),
    [initial, setInitial] = useState(true),
    [owner, setOwner] = useState("guild"),
    [inputs, setInputs] = useState<Record<string, string>>({}),
    [outputs, setOutputs] = useState<Record<string, string>>({}),
    [offset, setOffset] = useState(0);
  const [rebalanceReason, setRebalanceReason] = useState(""),
    [exchangeReason, setExchangeReason] = useState(""),
    [batchReason, setBatchReason] = useState(""),
    [mineralReason, setMineralReason] = useState(""),
    [itemReasons, setItemReasons] = useState<Record<string, string>>({}),
    [attempts, setAttempts] = useState<Record<string, boolean>>({}),
    [drafts, setDrafts] = useState<Record<string, Draft>>({}),
    [active, setActive] = useState<string | null>(null),
    [mineral, setMineral] = useState<any>(null);
  // A review belongs to its captured form values. Editing any operation
  // requires a fresh preview rather than discarding a newer draft on confirm.
  useEffect(() => {
    setPreview(null);
    setConfirmed(false);
  }, [
    drafts,
    rebalanceReason,
    exchangeReason,
    batchReason,
    mineralReason,
    itemReasons,
    mineral,
    inputs,
    outputs,
    owner,
    initial,
  ]);
  const load = async () => {
    setData(await request("/guild/commerce?offset=" + offset));
    setError("");
  };
  useEffect(() => {
    let live = true;
    request("/guild/commerce?offset=" + offset)
      .then((d) => {
        if (live) setData(d);
      })
      .catch((e) => {
        if (live) setError(e.message);
      });
    return () => {
      live = false;
    };
  }, [busy, offset]);
  const number = (s: string) => {
    if (!/^\d+$/.test(s) || !Number.isSafeInteger(Number(s)))
      throw Error("Informe um inteiro não negativo.");
    return Number(s);
  };
  const localRun = (fn: () => Promise<void>) =>
    run(async () => {
      setError("");
      try {
        await fn();
      } catch (error) {
        setError((error as Error).message);
      }
    });
  const submit = (id: string, reason: string, fn: () => Promise<void>) => {
    setAttempts((a) => ({ ...a, [id]: true }));
    if (reason.trim().length < 10 || reason.length > 500) return;
    void localRun(fn);
  };
  const propose = async (
    action: string,
    target: string,
    params: any,
    reason: string,
  ) => {
    setPreview(null);
    setConfirmed(false);
    setPreview(
      await request("/operations/preview", {
        operation_id: crypto.randomUUID(),
        action,
        target,
        params,
        reason,
      }),
    );
  };
  const quantities = (v: Record<string, string>) =>
    Object.fromEntries(
      Object.entries(v)
        .filter(([, n]) => n !== "" && number(n) > 0)
        .map(([k, n]) => [k, number(n)]),
    );
  const newDraft = (i: any): Draft => ({
    base: i,
    buy_price_units: i.buy_price_units,
    sell_price_units: i.sell_price_units,
    buy_enabled: i.buy_enabled,
    sell_enabled: i.sell_enabled,
    acknowledge_free: false,
    acknowledge_arbitrage: false,
  });
  const edit = (i: any) => {
    if (!drafts[i.definition_id])
      setDrafts((d) => ({ ...d, [i.definition_id]: newDraft(i) }));
    setActive(i.definition_id);
  };
  const changed = (d: Draft) =>
    ["buy_price_units", "sell_price_units", "buy_enabled", "sell_enabled"].some(
      (k) => String((d as any)[k]) !== String(d.base[k]),
    );
  const pending = Object.keys(drafts).filter((id) => changed(drafts[id]));
  const params = (d: Draft) => ({
    buy_price_units: number(d.buy_price_units),
    sell_price_units: number(d.sell_price_units),
    buy_enabled: d.buy_enabled,
    sell_enabled: d.sell_enabled,
    expected_revision: d.base.revision,
    acknowledge_free: d.acknowledge_free,
    acknowledge_arbitrage: d.acknowledge_arbitrage,
  });
  const updateDraft = (id: string, fields: any) =>
    setDrafts((v) => ({
      ...v,
      [id]: {
        ...v[id],
        ...fields,
        acknowledge_free: false,
        acknowledge_arbitrage: false,
      },
    }));
  const saveItem = (id: string) =>
    submit(id, itemReasons[id] ?? "", () =>
      propose("guild.item_prices", id, params(drafts[id]), itemReasons[id]),
    );
  const saveBatch = () =>
    submit("batch", batchReason, () =>
      propose(
        "guild.batch_prices",
        "guild",
        {
          changes: pending.map((id) => ({
            definition_id: id,
            ...params(drafts[id]),
          })),
        },
        batchReason,
      ),
    );
  const mineralKeys = [
    "lunar_guild_buy_rate_milliunits_per_gram",
    "lunar_guild_sell_rate_milliunits_per_gram",
    "lunar_guild_buy_enabled",
    "lunar_guild_sell_enabled",
    "lunar_guild_allow_zero_price",
  ];
  const mr = mineral
    ? risks(
        String(mineral.lunar_guild_buy_rate_milliunits_per_gram),
        String(mineral.lunar_guild_sell_rate_milliunits_per_gram),
        mineral.lunar_guild_buy_enabled,
        mineral.lunar_guild_sell_enabled,
      )
    : { arb: false, free: false };
  if (
    mineral &&
    mineral.lunar_guild_allow_zero_price &&
    ((mineral.lunar_guild_buy_enabled &&
      Number(mineral.lunar_guild_buy_rate_milliunits_per_gram) < 1000) ||
      (mineral.lunar_guild_sell_enabled &&
        Number(mineral.lunar_guild_sell_rate_milliunits_per_gram) < 1000))
  )
    mr.free = true;
  const saveMineral = () =>
    submit("mineral", mineralReason, async () => {
      const p: any = {
        expected_revision: mineral.revision,
        acknowledge_free: mineral.acknowledge_free,
        acknowledge_arbitrage: mineral.acknowledge_arbitrage,
      };
      for (const k of mineralKeys)
        p[k] =
          typeof mineral[k] === "boolean"
            ? mineral[k]
            : number(String(mineral[k]));
      await propose("guild.mineral_prices", "mineral", p, mineralReason);
    });
  const reviewed =
    preview?.before.items ??
    (preview?.action === "guild.item_prices"
      ? [
          {
            name: data?.items.find(
              (i: any) => i.definition_id === preview.target,
            )?.name,
            before: preview.before.before,
            proposed: preview.before.proposed,
            warnings: preview.before.warnings,
          },
        ]
      : []);
  return (
    <section aria-label="Administração comercial da Guilda">
      <h3>Caixa e comércio da Guilda</h3>
      {error && <p role="alert">{error}</p>}
      {!data && <p>Carregando…</p>}
      {data && (
        <>
          <h4>Caixa físico</h4>
          <p>Total: {data.cash.total_weight_mg} mg</p>
          <ul>
            {denoms.map(([k, n]) => (
              <li key={k}>
                {n}: {data.cash.coins[k]} ·{" "}
                {(data.cash.mass_percent_basis_points[k] / 100).toFixed(2)}% da
                massa
              </li>
            ))}
          </ul>
          {canManage && (
            <>
              <fieldset>
                <legend>Rebalanceamento manual 70/20/10</legend>
                <label>
                  <input
                    type="checkbox"
                    aria-label="Rebalanceamento inicial V1"
                    checked={initial}
                    onChange={(e) => setInitial(e.target.checked)}
                  />
                  Operação inicial V1; desmarque para uma nova decisão manual.
                </label>
                <Reason
                  label="Justificativa do rebalanceamento"
                  value={rebalanceReason}
                  set={setRebalanceReason}
                  attempted={!!attempts.rebalance}
                />
                <button
                  disabled={busy}
                  onClick={() =>
                    submit("rebalance", rebalanceReason, () =>
                      propose(
                        "guild.rebalance",
                        "guild",
                        { initial },
                        rebalanceReason,
                      ),
                    )
                  }
                >
                  Prévia 70/20/10
                </button>
              </fieldset>
              <fieldset>
                <legend>Trocar denominações</legend>
                <label>
                  Conta da troca
                  <input
                    aria-label="Conta da troca"
                    value={owner}
                    onChange={(e) => setOwner(e.target.value)}
                  />
                </label>
                {[
                  { title: "Entrada", values: inputs, set: setInputs },
                  { title: "Saída", values: outputs, set: setOutputs },
                ].map(({ title, values, set }) => (
                  <div className="royal-filters" key={title}>
                    {denoms.map(([k, n]) => (
                      <label key={k}>
                        {title} {n}
                        <input
                          aria-label={`${title} ${n}`}
                          type="number"
                          min={0}
                          value={values[k] ?? "0"}
                          onChange={(e) =>
                            set({ ...values, [k]: e.target.value })
                          }
                        />
                      </label>
                    ))}
                  </div>
                ))}
                <Reason
                  label="Justificativa da troca"
                  value={exchangeReason}
                  set={setExchangeReason}
                  attempted={!!attempts.exchange}
                />
                <button
                  disabled={busy}
                  onClick={() =>
                    submit("exchange", exchangeReason, () =>
                      propose(
                        "royal.exchange",
                        owner,
                        {
                          inputs: quantities(inputs),
                          outputs: quantities(outputs),
                        },
                        exchangeReason,
                      ),
                    )
                  }
                >
                  Prévia de troca
                </button>
              </fieldset>
            </>
          )}
          <h4>Preços da Guilda</h4>
          <p>
            Compra: a Guilda paga ao jogador. Venda: base por unidade;
            matérias-primas acrescentam uma margem fixa por operação. A margem é
            configurada em Economia dos NPCs.
          </p>
          <div className="guild-price-table">
            <table>
              <thead>
                <tr>
                  {[
                    "Item",
                    "Estoque",
                    "Compra",
                    "Venda (base)",
                    "Margem por operação",
                    "Total para 1 unidade",
                    "Compra ativa",
                    "Venda ativa",
                    "Revisão",
                    "Editar",
                  ].map((n) => (
                    <th key={n}>{n}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {data.items.map((i: any) => (
                  <tr key={i.definition_id}>
                    <td>
                      {i.name}
                      {drafts[i.definition_id] &&
                        changed(drafts[i.definition_id]) && (
                          <strong> · PENDENTE</strong>
                        )}
                    </td>
                    <td>{i.stock}</td>
                    <td>{i.buy_price_units}</td>
                    <td>{i.sell_price_units}</td>
                    <td>{i.resale_quote.fixed_margin_units}</td>
                    <td>{i.resale_quote.total_price_units}</td>
                    <td>{i.buy_enabled ? "Sim" : "Não"}</td>
                    <td>{i.sell_enabled ? "Sim" : "Não"}</td>
                    <td>{i.revision}</td>
                    <td>
                      {canManage && (
                        <button onClick={() => edit(i)}>
                          Editar preço {i.definition_id}
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {canManage &&
            active &&
            drafts[active] &&
            (() => {
              const d = drafts[active],
                risk = risks(
                  d.buy_price_units,
                  d.sell_price_units,
                  d.buy_enabled,
                  d.sell_enabled,
                );
              return (
                <fieldset>
                  <legend>Editar {d.base.name}</legend>
                  <label>
                    Guilda compra
                    <input
                      aria-label="Novo preço de compra"
                      type="number"
                      min={0}
                      value={d.buy_price_units}
                      onChange={(e) =>
                        updateDraft(active, { buy_price_units: e.target.value })
                      }
                    />
                  </label>
                  <label>
                    Guilda vende
                    <input
                      aria-label="Novo preço de venda"
                      type="number"
                      min={0}
                      value={d.sell_price_units}
                      onChange={(e) =>
                        updateDraft(active, {
                          sell_price_units: e.target.value,
                        })
                      }
                    />
                  </label>
                  {["buy_enabled", "sell_enabled"].map((k, i) => (
                    <label key={k}>
                      <input
                        aria-label={
                          i ? "Venda da Guilda ativa" : "Compra da Guilda ativa"
                        }
                        type="checkbox"
                        checked={(d as any)[k]}
                        onChange={(e) =>
                          updateDraft(active, { [k]: e.target.checked })
                        }
                      />
                      {i ? "Venda" : "Compra"} ativa
                    </label>
                  ))}
                  <Acknowledgements
                    arb={risk.arb}
                    free={risk.free}
                    values={d}
                    set={(value) =>
                      setDrafts((v) => ({ ...v, [active]: value }))
                    }
                  />
                  <Reason
                    label={`Justificativa da alteração de preços de ${d.base.name}`}
                    value={itemReasons[active] ?? ""}
                    set={(s) => setItemReasons((v) => ({ ...v, [active]: s }))}
                    attempted={!!attempts[active]}
                  />
                  <button
                    disabled={busy || !changed(d)}
                    onClick={() => saveItem(active)}
                  >
                    Salvar este item
                  </button>
                  <button
                    className="secondary"
                    disabled={busy}
                    onClick={() => {
                      const current = data.items.find(
                        (i: any) => i.definition_id === active,
                      );
                      setDrafts((v) => ({ ...v, [active]: newDraft(current) }));
                      setPreview(null);
                    }}
                  >
                    Atualizar valores deste item
                  </button>
                </fieldset>
              );
            })()}
          {canManage && pending.length > 0 && (
            <fieldset>
              <legend>{pending.length} alterações pendentes</legend>
              {pending.map((id) => (
                <p key={id}>
                  {drafts[id].base.name} · Compra:{" "}
                  {drafts[id].base.buy_price_units} →{" "}
                  {drafts[id].buy_price_units} · Venda:{" "}
                  {drafts[id].base.sell_price_units} →{" "}
                  {drafts[id].sell_price_units}
                </p>
              ))}
              <Reason
                label="Justificativa do lote de preços"
                value={batchReason}
                set={setBatchReason}
                attempted={!!attempts.batch}
              />
              <button disabled={busy} onClick={saveBatch}>
                Revisar alterações
              </button>
            </fieldset>
          )}
          <h4>Política do Minério Lunar</h4>
          <p>
            Compra: {data.mineral.lunar_guild_buy_rate_milliunits_per_gram}{" "}
            milliunits/g · Venda:{" "}
            {data.mineral.lunar_guild_sell_rate_milliunits_per_gram}{" "}
            milliunits/g
          </p>
          {canManage && (
            <button
              onClick={() =>
                setMineral({
                  ...data.mineral,
                  acknowledge_free: false,
                  acknowledge_arbitrage: false,
                })
              }
            >
              Editar rates do minério
            </button>
          )}
          {canManage && mineral && (
            <fieldset>
              <legend>Editar política do Minério Lunar</legend>
              {mineralKeys.map((k, i) => (
                <label key={k}>
                  {
                    [
                      "Guilda compra (milliunits/g)",
                      "Guilda vende (milliunits/g)",
                      "Compra do minério ativa",
                      "Venda do minério ativa",
                      "Permitir preço arredondado zero",
                    ][i]
                  }
                  {typeof mineral[k] === "boolean" ? (
                    <input
                      aria-label={
                        [
                          "",
                          "",
                          "Compra do minério ativa",
                          "Venda do minério ativa",
                          "Permitir minério com preço zero",
                        ][i]
                      }
                      type="checkbox"
                      checked={mineral[k]}
                      onChange={(e) =>
                        setMineral({
                          ...mineral,
                          [k]: e.target.checked,
                          acknowledge_free: false,
                          acknowledge_arbitrage: false,
                        })
                      }
                    />
                  ) : (
                    <input
                      aria-label={
                        i
                          ? "Rate de venda do minério"
                          : "Rate de compra do minério"
                      }
                      type="number"
                      min={0}
                      value={mineral[k]}
                      onChange={(e) =>
                        setMineral({
                          ...mineral,
                          [k]: e.target.value,
                          acknowledge_free: false,
                          acknowledge_arbitrage: false,
                        })
                      }
                    />
                  )}
                </label>
              ))}
              <Acknowledgements
                arb={mr.arb}
                free={mr.free}
                values={mineral}
                set={setMineral}
              />
              <Reason
                label="Justificativa da alteração da política do Minério Lunar"
                value={mineralReason}
                set={setMineralReason}
                attempted={!!attempts.mineral}
              />
              <button disabled={busy} onClick={saveMineral}>
                Prévia da política do minério
              </button>
            </fieldset>
          )}
          {preview && (
            <section
              aria-label="Prévia comercial"
              className="commercial-preview"
            >
              <h4>
                {preview.action === "guild.batch_prices"
                  ? "Revisar lote de preços"
                  : "Revisar operação"}
              </h4>
              <p>Justificativa: {preview.reason}</p>
              {reviewed.length ? (
                reviewed.map((r: any, i: number) => (
                  <article key={i}>
                    <h5>{r.name ?? r.definition_id}</h5>
                    <p>
                      Compra: {r.before.buy_price_units} →{" "}
                      {r.proposed.buy_price_units}
                    </p>
                    <p>
                      Venda: {r.before.sell_price_units} →{" "}
                      {r.proposed.sell_price_units}
                    </p>
                    <p>
                      Compra ativa: {String(r.before.buy_enabled)} →{" "}
                      {String(r.proposed.buy_enabled)} · Venda ativa:{" "}
                      {String(r.before.sell_enabled)} →{" "}
                      {String(r.proposed.sell_enabled)}
                    </p>
                    {r.warnings?.includes("POSSIBLE_ARBITRAGE") && (
                      <p>Arbitragem reconhecida.</p>
                    )}
                    {r.warnings?.includes("ZERO_PRICE") && (
                      <p>Gratuidade reconhecida.</p>
                    )}
                  </article>
                ))
              ) : (
                <pre>{JSON.stringify(preview.before, null, 2)}</pre>
              )}
              <label>
                <input
                  aria-label="Confirmar impacto comercial"
                  type="checkbox"
                  checked={confirmed}
                  onChange={(e) => setConfirmed(e.target.checked)}
                />
                Revisei valores, flags e consequências.
              </label>
              <button
                disabled={busy || !confirmed}
                onClick={() =>
                  void localRun(async () => {
                    await request("/operations/" + preview.id + "/confirm", {
                      confirmed: true,
                      confirmation_token: preview.confirmation_token,
                    });
                    const ids =
                      preview.action === "guild.batch_prices"
                        ? preview.params.changes.map(
                            (c: any) => c.definition_id,
                          )
                        : preview.action === "guild.item_prices"
                          ? [preview.target]
                          : [];
                    setDrafts((v) =>
                      Object.fromEntries(
                        Object.entries(v).filter(([id]) => !ids.includes(id)),
                      ),
                    );
                    if (ids.includes(active)) setActive(null);
                    if (preview.action === "guild.mineral_prices")
                      setMineral(null);
                    setPreview(null);
                    await load();
                    await refresh();
                  })
                }
              >
                {preview.action === "guild.batch_prices"
                  ? "Confirmar todas"
                  : "Confirmar operação comercial"}
              </button>
            </section>
          )}
          <h4>Estoque real</h4>
          {data.items
            .filter((i: any) => BigInt(i.stock) > 0n)
            .map((i: any) => (
              <p key={i.definition_id}>
                {i.name} × {i.stock}
              </p>
            ))}
          {data.lots.map((r: any) => (
            <p key={r.id}>Pepita · {r.weight_g} g</p>
          ))}
          <h4>Histórico de preços</h4>
          {data.history.map((h: any) => (
            <details key={h.request_id + ":" + h.policy_key}>
              <summary>
                {h.policy_key} · {h.created_at} · {h.reason}
              </summary>
              <pre>{JSON.stringify(h, null, 2)}</pre>
            </details>
          ))}
          <h4>Comércio</h4>
          {data.trades.map((t: any) => (
            <details key={t.key}>
              <summary>
                {t.created_at} · {t.result.message}
              </summary>
              <pre>{JSON.stringify(t, null, 2)}</pre>
            </details>
          ))}
          <button
            disabled={busy || !offset}
            onClick={() => setOffset(Math.max(0, offset - 100))}
          >
            Histórico anterior
          </button>
          <button disabled={busy} onClick={() => setOffset(offset + 100)}>
            Próximo histórico
          </button>
        </>
      )}
    </section>
  );
}
