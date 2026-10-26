import React, { useEffect, useState, useRef } from "react";
import { createRoot } from "react-dom/client";
import "./style.css";
import { WorldEvents } from "./WorldEvents";

type Row = Record<string, any>;
const modules = [
  ["overview", "Visão geral"],
  ["bank", "Banco Central"],
  ["economy", "Economia"],
  ["guilds", "Guildas"],
  ["players", "Jogadores"],
  ["items", "Itens"],
  ["monsters", "Monstros"],
  ["auctions", "Leilões"],
  ["world", "Mundo e eventos"],
  ["audit", "Auditoria"],
];
const names: Record<string, string> = {
  "bank.issue": "Emitir moeda oficial",
  "bank.burn": "Retirar moeda de circulação",
  "bank.transfer": "Transferir reservas existentes",
  "economy.configure": "Ajustar parâmetro econômico",
  "sandbox.grant": "Adicionar créditos de teste isolados",
  "sandbox.consume": "Consumir créditos de teste isolados",
  "players.heal": "Restaurar jogador em área segura",
  "players.add_xp": "Conceder XP auditado",
  "players.travel": "Viagem administrativa validada",
  "items.create": "Criar item autorizado",
  "items.transfer": "Transferir item físico",
  "items.protect": "Proteger definição contra perda",
  "items.recover_starter": "Recuperar espada original em custódia",
  "items.replace_starter": "Autorizar reposição sem retirar do comprador",
  "monsters.balance": "Ajustar perfil para novos encontros",
  "world.spawn": "Criar spawn administrativo identificado",
  "world.region": "Ajustar perigo regional",
  "auctions.hide": "Ocultar e suspender com reembolso",
  "auctions.archive": "Arquivar histórico de leilão encerrado",
  "world.event_cancel": "Cancelar evento agendado",
  "world.event_create": "Agendar evento do mundo (use o formulário de eventos)",
  "auctions.cancel": "Suspender leilão e devolver reservas",
};
const targetLabels: Record<string, string> = {
  "items.protect": "ID da definição",
  "items.transfer": "ID do item",
  "items.recover_starter": "ID do leilão",
  "items.replace_starter": "ID do leilão",
  "items.create": "ID do personagem destinatário",
  "monsters.balance": "ID da espécie",
  "world.region": "ID da região",
  "world.spawn": "ID da região",
  "auctions.cancel": "ID do leilão",
  "auctions.hide": "ID do leilão",
  "auctions.archive": "ID do leilão",
  "world.event_cancel": "ID do evento",
  "economy.configure": "Parâmetro econômico",
};
const params: Record<string, Record<string, string>> = {
  "bank.issue": {
    amount: "Quantidade de moedas",
    destination: "Conta de destino",
  },
  "bank.burn": { amount: "Quantidade de moedas", source: "Conta de origem" },
  "bank.transfer": {
    amount: "Quantidade de moedas",
    source: "Conta de origem",
    destination: "Conta de destino",
  },
  "sandbox.grant": { amount: "Créditos de teste (não negociáveis)" },
  "sandbox.consume": { amount: "Créditos de teste a consumir" },
  "economy.configure": { value: "Novo valor" },
  "players.heal": {},
  "players.add_xp": { amount: "XP a conceder" },
  "players.travel": { destination: "ID do destino já visitado" },
  "items.create": { definition: "ID da definição", quantity: "Quantidade" },
  "items.transfer": { owner_id: "ID do novo proprietário" },
  "items.protect": {},
  "items.recover_starter": {},
  "items.replace_starter": {},
  "monsters.balance": {
    hp: "HP base",
    attack: "Ataque",
    defense: "Defesa",
    level: "Nível",
    xp: "XP por vitória",
  },
  "world.region": { danger_tier: "Danger Tier" },
  "world.spawn": {
    character_id: "ID do personagem presente",
    species: "Espécie",
    x: "Posição X",
    y: "Posição Y",
  },
  "auctions.cancel": { destination: "Destino do item" },
};
const numericKeys = new Set([
  "owner_id",
  "character_id",
  "quantity",
  "hp",
  "attack",
  "defense",
  "level",
  "xp",
  "x",
  "y",
  "danger_tier",
]);
async function request(path: string, body?: unknown) {
  const r = await fetch("/api/admin" + path, {
    method: body === undefined ? "GET" : "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: "Bearer " + sessionStorage.getItem("admin_token"),
    },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  const data = await r.json();
  if (!r.ok) {
    if (r.status === 401) sessionStorage.removeItem("admin_token");
    throw Error(
      typeof data.detail === "string"
        ? data.detail
        : "Revise os campos informados",
    );
  }
  return data;
}
function Table({
  rows,
  columns,
  onChoose,
}: {
  rows: Row[];
  columns: string[];
  onChoose?: (r: Row) => void;
}) {
  if (!rows.length) return <p>Nenhum registro.</p>;
  return (
    <div className="table-scroll">
      <table>
        <thead>
          <tr>
            {columns.map((c) => (
              <th key={c}>{c}</th>
            ))}
            {onChoose && <th>Ação</th>}
          </tr>
        </thead>
        <tbody>
          {rows.map((r, i) => (
            <tr key={r.id ?? i}>
              {columns.map((c) => (
                <td key={c}>
                  {typeof r[c] === "object" ? (
                    <details>
                      <summary>Consultar</summary>
                      <pre>{JSON.stringify(r[c], null, 2)}</pre>
                    </details>
                  ) : (
                    String(r[c] ?? "—")
                  )}
                </td>
              ))}
              {onChoose && (
                <td>
                  <button className="secondary" onClick={() => onChoose(r)}>
                    Selecionar
                  </button>
                </td>
              )}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
function App() {
  const requestGeneration = useRef(0);
  const [dataModule, setDataModule] = useState("");
  const [token, setToken] = useState(sessionStorage.getItem("admin_token"));
  const [session, setSession] = useState<Row | null>(null),
    [module, setModule] = useState("overview"),
    [data, setData] = useState<any>(null),
    [diagnostics, setDiagnostics] = useState<Row[]>([]);
  const [busy, setBusy] = useState(false),
    [message, setMessage] = useState(""),
    [search, setSearch] = useState(""),
    [offset, setOffset] = useState(0);
  const [action, setAction] = useState(""),
    [target, setTarget] = useState("central_bank"),
    [fields, setFields] = useState<Record<string, string>>({}),
    [reason, setReason] = useState(""),
    [preview, setPreview] = useState<Row | null>(null);
  async function load() {
    if (!token) return;
    const generation = ++requestGeneration.current;
    try {
      const result = await request(
        "/" +
          (module === "bank" ? "economy" : module) +
          "?q=" +
          encodeURIComponent(search) +
          "&offset=" +
          offset,
      );
      if (generation !== requestGeneration.current) return;
      setData(result);
      setDataModule(module);
      if (module === "items") {
        const d = await request("/items/starter-diagnostics");
        if (generation === requestGeneration.current) setDiagnostics(d);
      }
    } catch (e) {
      setMessage((e as Error).message);
      if (!sessionStorage.getItem("admin_token")) {
        setToken(null);
        setSession(null);
      }
    }
  }
  useEffect(() => {
    if (token)
      request("/session")
        .then(setSession)
        .catch((e) => {
          setMessage(e.message);
          setToken(null);
          sessionStorage.removeItem("admin_token");
        });
  }, [token]);
  useEffect(() => {
    void load();
  }, [token, module, search, offset]);
  const allowed = Object.keys(session?.actions ?? {}).filter((k) =>
    module === "bank"
      ? k.startsWith("bank.")
      : module === "economy"
        ? k.startsWith("economy.") || k.startsWith("sandbox.")
        : module === "guilds"
          ? k === "bank.transfer"
          : k.startsWith(module + "."),
  );
  function chooseAction(a: string, t?: string) {
    setAction(a);
    setTarget(t ?? (a.startsWith("bank.") ? "central_bank" : ""));
    setFields(
      a === "bank.transfer"
        ? { source: "central_bank", destination: "treasury" }
        : a === "bank.issue"
          ? { destination: "central_bank" }
          : a === "bank.burn"
            ? { source: "central_bank" }
            : a === "auctions.cancel"
              ? { destination: "custody" }
              : {},
    );
    setPreview(null);
  }
  useEffect(() => {
    setData(null);
    setOffset(0);
    setSearch("");
    chooseAction("");
  }, [module]);
  async function run(fn: () => Promise<void>) {
    if (busy) return;
    setBusy(true);
    try {
      await fn();
    } catch (e) {
      setMessage((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  async function makePreview(e: React.FormEvent) {
    e.preventDefault();
    await run(async () => {
      const p: Row = {};
      for (const k of Object.keys(params[action] ?? {})) {
        if (fields[k] !== undefined && fields[k] !== "") {
          p[k] = numericKeys.has(k)
            ? Number(fields[k])
            : k === "value" && target !== "auction_proceeds_destination"
              ? Number(fields[k])
              : fields[k];
        }
      }
      setPreview(
        await request("/operations/preview", {
          operation_id: crypto.randomUUID(),
          action,
          target: target || "central_bank",
          params: p,
          reason,
        }),
      );
      setMessage("Confira os valores e o impacto antes de confirmar.");
    });
  }
  async function confirm() {
    await run(async () => {
      if (!preview) return;
      const r = await request("/operations/" + preview.id + "/confirm", {
        confirmed: true,
        confirmation_token: preview.confirmation_token,
      });
      setPreview(null);
      setMessage("Operação registrada: " + r.id + " · " + r.status);
      await load();
    });
  }
  const labels: Record<string, string> = {
    official_net: "Moeda oficial líquida (saldos assinados)",
    expected_net: "Emissão histórica menos retiradas",
    reconciliation_gap: "Diferença de reconciliação (esperado zero)",
    player_available: "Moedas disponíveis aos jogadores",
    medical_debt: "Dívida médica total",
    escrow: "Ouro reservado em leilões",
    central_bank: "Reservas do Banco Central",
    guild_treasury: "Tesouro da Guilda",
    pending_obligations: "Recompensas pendentes (obrigações)",
    genesis: "Emissão inicial histórica",
    emissions: "Emissões administrativas",
    retired: "Retiradas e sink",
    administrative_test_credits:
      "Créditos de teste isolados (fora da economia)",
  };
  function indicators(values: Row) {
    return (
      <>
        <div className="metrics">
          {Object.entries(labels)
            .filter(([k]) => k in values)
            .map(([k, label]) => (
              <article
                className={
                  k === "reconciliation_gap" && values[k] !== "0" ? "error" : ""
                }
                key={k}
              >
                <span>{label}</span>
                <strong>{values[k]}</strong>
              </article>
            ))}
        </div>
        {values.suggestions?.map((x: string) => (
          <p className="notice" key={x}>
            {x} Nenhuma emissão é automática.
          </p>
        ))}
        {values.unavailable?.map((x: string) => (
          <p key={x}>{x}</p>
        ))}
      </>
    );
  }
  if (!token)
    return (
      <main className="login">
        <h1>Dungeon Game · Central Administrativa</h1>
        <p>
          Use uma conta existente com papel concedido pelo operador local. Não
          há administrador ou senha padrão. Esta sessão é separada do jogo.
        </p>
        <form
          onSubmit={(e) => {
            e.preventDefault();
            const form = new FormData(e.currentTarget);
            void run(async () => {
              const r = await request("/auth/login", {
                username: form.get("username"),
                password: form.get("password"),
              });
              sessionStorage.setItem("admin_token", r.token);
              setToken(r.token);
              setMessage("");
            });
          }}
        >
          <label>
            Conta administrativa
            <input name="username" autoComplete="username" required />
          </label>
          <label>
            Senha
            <input
              name="password"
              type="password"
              autoComplete="current-password"
              required
              minLength={8}
            />
          </label>
          <button disabled={busy}>Entrar na Central</button>
        </form>
        <p role="status">{message}</p>
      </main>
    );
  return (
    <div className="admin-shell">
      <aside>
        <h1>
          Dungeon Game <small>Central Administrativa</small>
        </h1>
        <p>Papel: {session?.role ?? "Validando sessão"}</p>
        <nav>
          {modules
            .filter(([id]) =>
              session?.permissions?.includes(
                (id === "bank" ? "economy" : id) + ".read",
              ),
            )
            .map(([id, title]) => (
              <button
                key={id}
                className={module === id ? "selected" : ""}
                onClick={() => {
                  setData(null);
                  setModule(id);
                }}
              >
                {title}
              </button>
            ))}
        </nav>
        <button
          className="secondary"
          onClick={() =>
            void run(async () => {
              try {
                await request("/auth/logout", {});
              } finally {
                sessionStorage.removeItem("admin_token");
                setToken(null);
                setSession(null);
              }
            })
          }
        >
          Encerrar sessão ADM
        </button>
        <a href="/">Cliente web legado</a>
      </aside>
      <main>
        <header>
          <h2>{modules.find(([id]) => id === module)?.[1]}</h2>
          <button disabled={busy} onClick={() => void load()}>
            Atualizar dados
          </button>
        </header>
        <p role="status" className="notice">
          {message}
        </p>
        {data && dataModule === module && (
          <section>
            {module === "overview" && (
              <>
                <p>
                  {data.players} personagens · {data.active_expeditions}{" "}
                  expedições ativas · Primeiro andar
                </p>
                {indicators(data.economy)}
              </>
            )}
            {(module === "bank" || module === "economy") && (
              <>
                {indicators(data.indicators)}
                <p>
                  Transferências usam reservas existentes. Emissão e retirada
                  alteram a oferta explicitamente. Dívidas são saldos negativos;
                  obrigações pendentes não são moeda emitida. Créditos de teste
                  nunca podem ser usados em contas oficiais ou leilões.
                </p>
                <h3>Distribuição de riqueza</h3>
                <Table
                  rows={data.indicators.wealth_distribution}
                  columns={["id", "name", "available", "debt"]}
                />
                <h3>Fluxos por dia (últimos 30 dias com registros)</h3>
                <Table
                  rows={data.indicators.daily_flows}
                  columns={[
                    "date",
                    "inflows_to_guild",
                    "outflows_from_guild",
                    "auction_volume",
                    "emitted",
                    "retired",
                  ]}
                />
                <h3>Livro-razão</h3>
                <Table
                  rows={data.ledger}
                  columns={[
                    "id",
                    "reference",
                    "source",
                    "destination",
                    "amount",
                    "created",
                  ]}
                />
                {module === "economy" && (
                  <>
                    <h3>Configuração efetiva</h3>
                    <Table
                      rows={Object.entries(data.default_configuration).map(
                        ([key, value]) => ({
                          key,
                          value:
                            data.settings.find((r: Row) => r.key === key)?.value
                              .value ?? value,
                        }),
                      )}
                      columns={["key", "value"]}
                    />
                  </>
                )}
              </>
            )}
            {module === "guilds" && (
              <Table
                rows={data}
                columns={["id", "name", "treasury", "pending_obligations"]}
              />
            )}
            {module === "players" && (
              <>
                <label>
                  Pesquisar nome
                  <input
                    value={search}
                    onChange={(e) => setSearch(e.target.value)}
                  />
                </label>
                <Table
                  rows={data}
                  columns={[
                    "id",
                    "name",
                    "account",
                    "level",
                    "xp",
                    "strength",
                    "defense",
                    "coins",
                    "room_id",
                    "inventory",
                    "active_battle",
                    "active_expedition",
                  ]}
                  onChoose={(r) => chooseAction("players.heal", String(r.id))}
                />
              </>
            )}
            {module === "items" && (
              <>
                <h3>Definições</h3>
                <Table
                  rows={data.definitions}
                  columns={[
                    "id",
                    "name",
                    "kind",
                    "power",
                    "base_value",
                    "death_transferable",
                    "stackable",
                    "max_stack_size",
                  ]}
                  onChoose={(r) => chooseAction("items.protect", r.id)}
                />
                <h3>Itens e custódia</h3>
                <Table
                  rows={data.instances}
                  columns={[
                    "id",
                    "owner",
                    "definition",
                    "quantity",
                    "location",
                    "equipped",
                  ]}
                  onChoose={(r) => chooseAction("items.transfer", String(r.id))}
                />
                <h3>Diagnóstico das espadas iniciais</h3>
                <p>
                  Recuperação individual. Item entregue a comprador legítimo não
                  será retirado silenciosamente; reposição requer autorização
                  separada.
                </p>
                {diagnostics.map((d) => (
                  <article className="diagnostic" key={d.auction.id}>
                    <p>
                      Leilão #{d.auction.id} · item #{d.item.id} · antigo dono #
                      {d.auction.former_owner_id} · {d.auction.status} · lance{" "}
                      {d.auction.highest_bid} · proprietário atual{" "}
                      {d.item.owner ?? "custódia"}
                    </p>
                    <p>{d.recommendation}</p>
                    {session?.permissions?.includes("items.manage") && (
                      <button
                        onClick={() =>
                          chooseAction(
                            d.auction.status === "SETTLED"
                              ? "items.replace_starter"
                              : "items.recover_starter",
                            String(d.auction.id),
                          )
                        }
                      >
                        Preparar resolução individual
                      </button>
                    )}
                  </article>
                ))}
              </>
            )}
            {module === "monsters" && (
              <>
                <h3>Perfis de novos encontros</h3>
                <p>
                  Alterar um perfil preserva os inimigos já instanciados e
                  mortos.
                </p>
                <Table
                  rows={data.definitions}
                  columns={["id", "hp", "attack", "defense", "level", "xp"]}
                  onChoose={(r) => {
                    chooseAction("monsters.balance", r.id);
                    setFields(
                      Object.fromEntries(
                        ["hp", "attack", "defense", "level", "xp"].map((k) => [
                          k,
                          String(r[k]),
                        ]),
                      ),
                    );
                  }}
                />
                <h3>Instâncias</h3>
                <Table
                  rows={data.instances}
                  columns={[
                    "id",
                    "character_id",
                    "room_id",
                    "spawn_key",
                    "species",
                    "state",
                    "hp",
                    "generation",
                  ]}
                />
              </>
            )}
            {module === "auctions" && (
              <>
                <label>
                  Filtrar estado
                  <select
                    value={search}
                    onChange={(e) => setSearch(e.target.value)}
                  >
                    {[
                      "",
                      "OPEN",
                      "CLOSED",
                      "SETTLED",
                      "UNSOLD",
                      "CANCELLED",
                    ].map((v) => (
                      <option key={v} value={v}>
                        {v || "Todos"}
                      </option>
                    ))}
                  </select>
                </label>
                <Table
                  rows={data}
                  columns={[
                    "id",
                    "item_id",
                    "name",
                    "quantity",
                    "status",
                    "former_owner_id",
                    "highest_bidder_id",
                    "highest_bid",
                    "bids",
                    "ends_at",
                    "proceeds_destination", "hidden", "archived", "origin", "assessed_value",
                  ]}
                  onChoose={(r) => chooseAction("auctions.cancel", String(r.id))}
                />
                <p>Ocultar suspende a negociação, cancela com reembolso de reservas e mantém a custódia. Arquivar exige leilão encerrado; histórico financeiro permanece disponível aqui.</p>
                {session?.permissions?.includes("auctions.manage") && data.map((a:Row)=><p key={a.id}>Leilão #{a.id}: <button onClick={()=>chooseAction("auctions.hide",String(a.id))}>Preparar ocultação</button> <button onClick={()=>chooseAction("auctions.archive",String(a.id))}>Preparar arquivamento</button></p>)}
              </>
            )}
            {module === "world" && (
              <>
                <h3>Regiões permanentes do primeiro andar</h3>
                <Table
                  rows={data.rooms}
                  columns={["id", "name", "kind", "danger_tier"]}
                  onChoose={(r) => chooseAction("world.region", r.id)}
                />
                <WorldEvents busy={busy} rooms={data.rooms} events={data.scheduled_events??[]} canManage={session?.permissions?.includes("world.manage")} preview={async body=>run(async()=>{setPreview(await request("/operations/preview",body));})} cancel={id=>chooseAction("world.event_cancel",id)} />
                <h3>Eventos persistentes</h3>
                <Table rows={data.events} columns={["id", "kind", "payload"]} />
              </>
            )}
            {module === "audit" && (
              <Table
                rows={data}
                columns={[
                  "id",
                  "actor_id",
                  "action",
                  "target",
                  "reason",
                  "status",
                  "created_at",
                  "finished_at",
                  "before",
                  "after",
                ]}
              />
            )}
          </section>
        )}
        {allowed.length > 0 && (
          <section className="operation">
            <h3>Operação autorizada</h3>
            <label>
              Ação
              <select
                aria-label="Ação"
                value={action}
                onChange={(e) => chooseAction(e.target.value)}
              >
                <option value="">Selecione uma operação</option>
                {allowed.filter(k=>k!=="world.event_create").map((k) => (
                  <option key={k} value={k}>
                    {names[k]}
                  </option>
                ))}
              </select>
            </label>
            {action && (
              <form onSubmit={makePreview}>
                {!action.startsWith("bank.") && (
                  <label>
                    {targetLabels[action] ?? "ID da conta ou personagem"}
                    {action === "economy.configure" ? (
                      <select
                        value={target}
                        onChange={(e) => setTarget(e.target.value)}
                        required
                      >
                        <option value="">Selecione</option>
                        {[
                          "medical_fee_base",
                          "monster_reward",
                          "boss_reward",
                          "min_auction_start_price",
                          "auction_duration_hours",
                          "auction_proceeds_destination",
                        ].map((k) => (
                          <option key={k}>{k}</option>
                        ))}
                      </select>
                    ) : (
                      <input
                        value={target}
                        onChange={(e) => setTarget(e.target.value)}
                        required
                      />
                    )}
                  </label>
                )}
                {Object.entries(params[action] ?? {}).map(([key, label]) => (
                  <label key={key}>
                    {label}
                    {action.startsWith("bank.") &&
                    (key === "source" || key === "destination") ? (
                      <>
                        <input
                          value={fields[key] ?? ""}
                          onChange={(e) =>
                            setFields({ ...fields, [key]: e.target.value })
                          }
                          list="official-accounts"
                          required
                        />
                        <small>
                          central_bank, treasury ou character:ID. Recursos de
                          teste são rejeitados.
                        </small>
                      </>
                    ) : action === "auctions.cancel" &&
                      key === "destination" ? (
                      <select
                        value={fields[key] ?? "custody"}
                        onChange={(e) =>
                          setFields({ ...fields, [key]: e.target.value })
                        }
                      >
                        <option value="custody">
                          Manter item arquivado em custódia
                        </option>
                        <option value="former_owner">
                          Devolver ao antigo proprietário
                        </option>
                      </select>
                    ) : (
                      <input
                        value={fields[key] ?? ""}
                        onChange={(e) =>
                          setFields({ ...fields, [key]: e.target.value })
                        }
                        inputMode={
                          numericKeys.has(key) || key === "amount"
                            ? "numeric"
                            : "text"
                        }
                        required
                      />
                    )}
                  </label>
                ))}
                <datalist id="official-accounts">
                  <option value="central_bank" />
                  <option value="treasury" />
                </datalist>
                <label>
                  Justificativa auditável
                  <textarea
                    aria-label="Justificativa auditável"
                    value={reason}
                    onChange={(e) => setReason(e.target.value)}
                    required
                    minLength={10}
                    maxLength={500}
                  />
                </label>
                <button disabled={busy}>Calcular prévia</button>
              </form>
            )}
          </section>
        )}
        <div className="pagination">
          <button
            className="secondary"
            disabled={offset === 0 || busy}
            onClick={() => setOffset(Math.max(0, offset - 100))}
          >
            Página anterior
          </button>
          <span>Registros a partir de {offset + 1}</span>
          <button
            className="secondary"
            disabled={busy}
            onClick={() => setOffset(offset + 100)}
          >
            Próxima página
          </button>
        </div>
        {preview && (
          <div
            className="modal"
            role="dialog"
            aria-modal="true"
            aria-labelledby="preview-title"
          >
            <section>
              <h2 id="preview-title">Revisar operação</h2>
              <p>
                {names[preview.action]} · destino/entidade: {preview.target}
              </p>
              <p>Justificativa: {preview.reason}</p>
              <p>
                Impacto previsto na oferta oficial:{" "}
                <strong>{preview.impact.supply_delta}</strong> moedas
              </p>
              <h3>Estado anterior</h3>
              <pre>{JSON.stringify(preview.before, null, 2)}</pre>
              <h3>Saldos previstos após a operação</h3>
              <pre>
                {JSON.stringify(preview.impact.projected_accounts, null, 2)}
              </pre>
              <h3>Alterações solicitadas</h3>
              <pre>{JSON.stringify(preview.impact.params, null, 2)}</pre>
              <p>
                Confirmação expira em 5 minutos e será rejeitada se os dados
                relevantes mudarem. A operação é auditada e não pode ser
                duplicada por repetição da requisição.
              </p>
              <button disabled={busy} onClick={() => void confirm()}>
                CONFIRMAR OPERAÇÃO
              </button>
              <button
                className="secondary"
                disabled={busy}
                onClick={() => setPreview(null)}
              >
                Cancelar prévia
              </button>
            </section>
          </div>
        )}
      </main>
    </div>
  );
}
createRoot(document.getElementById("root")!).render(<App />);
