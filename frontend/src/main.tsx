import React, { useEffect, useRef, useState } from "react";
import { createRoot } from "react-dom/client";
import { api, State, Battle } from "./api";
import { Map } from "./Map";
import {
  ExpeditionPanel,
  FleeModal,
  type FleePreview,
} from "./ExpeditionPanel";
import { route } from "./pathfinding";
import type { Peer, Target } from "./types";
import {
  DeathSummary,
  AttributePanel,
  AuctionHouse,
  PersonalRecovery,
} from "./DeathEconomy";
import "./style.css";
import {Encounters} from "./Encounters";
const wait = (ms: number) => new Promise((r) => setTimeout(r, ms));
function App() {
  const [state, setState] = useState<State | null>(null),
    [token, setToken] = useState(sessionStorage.getItem("token")),
    [needsCharacter, setNeedsCharacter] = useState(false),
    [notice, setNotice] = useState(
      "Bem-vindo ao Alvorecer. Sua história está apenas começando.",
    ),
    [busy, setBusy] = useState(false),
    [connection,setConnection]=useState("Conectando…"),
    [connectionEpoch,setConnectionEpoch]=useState(0),
    [rewards, setRewards] = useState<Battle[]>([]),
    [rewardSummary, setRewardSummary] = useState<{
      count: number;
      total: number;
      groups: Record<string, number>;
    }>({ count: 0, total: 0, groups: {} }),
    [fastDestinations, setFastDestinations] = useState<
      { id: string; name: string; danger_tier: number }[]
    >([]),
    [lootFlash, setLootFlash] = useState(""),
    [tab, setTab] = useState(""),
    [fleePreview, setFleePreview] = useState<FleePreview | null>(null),
    [peers, setPeers] = useState<Peer[]>([]),
    [bossWarning, setBossWarning] = useState(false),
    [fx, setFx] = useState<{
      seq: number;
      status: string;
      enemy_id?: number;
    } | null>(null),
    [invite, setInvite] = useState("");
  const gate = useRef(false),
    live = useRef<State | null>(null);
  const sequence = useRef(0);
  const freshness=useRef(0), refreshGate=useRef(false), failures=useRef(0);
  const lastEvent = useRef(0);
  useEffect(() => {
    if (!state?.events.length) return;
    const fresh = state.events.filter((e) => e.id > lastEvent.current);
    const initialized = lastEvent.current !== 0;
    lastEvent.current = Math.max(...state.events.map((e) => e.id));
    const item = fresh.find((e) => e.kind === "ITEM_ADDED");
    if (initialized && item) {
      setLootFlash("+" + item.payload.quantity + " material na mochila");
      const timer = setTimeout(() => setLootFlash(""), 2200);
      return () => clearTimeout(timer);
    }
  }, [state?.events.at(-1)?.id]);
  function apply(s: State) {
    live.current = s;
    setState(s);
  }
  async function refresh(force=false):Promise<void> {
    if(refreshGate.current){if(force){await wait(30);return refresh(true);}return;}
    refreshGate.current=true;
    const revision=freshness.current,session=sessionStorage.getItem("token");
    try {
      const current=await api("/state") as State;
      if(revision!==freshness.current||session!==sessionStorage.getItem("token"))return;
      apply(current);setNeedsCharacter(false);
      setRewards(current.reward_records);setRewardSummary(current.guild_rewards);setFastDestinations(current.fast_destinations);
      failures.current=0;setConnection("Conectado");
    }catch(e){
      const message=(e as Error).message;
      if(message.includes("Crie seu"))setNeedsCharacter(true);
      else {failures.current++;setNotice(message);setConnection(failures.current>=3?"Atualização pausada após 3 falhas":"Conexão interrompida");}
    }finally{refreshGate.current=false;}
  }
  function clearSession(){
    freshness.current++;sessionStorage.removeItem("token");setToken(null);setState(null);live.current=null;setPeers([]);
  }
  useEffect(()=>{
    const expired=()=>{clearSession();setNotice("Sessão expirada ou revogada. Entre novamente.")};
    const reconnect=()=>{failures.current=0;setConnectionEpoch(v=>v+1);if(sessionStorage.getItem("token"))void refresh()};
    const escape=(e:KeyboardEvent)=>{if(e.key==="Escape")setTab("")};
    window.addEventListener("dungeon:session-expired",expired);window.addEventListener("online",reconnect);window.addEventListener("keydown",escape);
    return()=>{window.removeEventListener("dungeon:session-expired",expired);window.removeEventListener("online",reconnect);window.removeEventListener("keydown",escape)};
  },[]);
  useEffect(() => {
    if (!token) return;
    void refresh();
    const timer = setInterval(() => {
      if (!gate.current && failures.current<3 && document.visibilityState!=="hidden") void refresh();
    }, 1500);
    return () => clearInterval(timer);
  }, [token]);
  useEffect(() => {
    if (!token || !state) return;
    let disposed = false,
      socket: WebSocket | undefined,
      reconnect: ReturnType<typeof setTimeout>, attempts=0;
    const heartbeat = setInterval(() => {
      if (socket?.readyState === 1) socket.send("ping");
    }, 1000);
    function connect() {
      socket = new WebSocket(
        `${location.protocol === "https:" ? "wss" : "ws"}://${location.host}/api/ws/rooms`,
      );
      socket.onopen = () => socket?.send(JSON.stringify({ token }));
      socket.onmessage = (e) => {
        let data;try{data=JSON.parse(e.data)}catch{return;}
        attempts=0;
        if (data.room_id === live.current?.room.id) setPeers(data.players);
        else setPeers([]);
      };
      socket.onclose = (e) => {
        setPeers([]);
        if(e.code===4401){window.dispatchEvent(new Event("dungeon:session-expired"));return;}
        if(!disposed && attempts<5){attempts++;reconnect=setTimeout(connect,Math.min(16000,1000*2**attempts));}
        else if(!disposed)setConnection("Presença desconectada; use Atualizar. Progresso salvo no servidor.");
      };
    }
    connect();
    return () => {
      disposed = true;
      clearInterval(heartbeat);
      clearTimeout(reconnect);
      socket?.close();
    };
  }, [token, !!state,connectionEpoch]);
  async function execute(fn: () => Promise<unknown>) {
    if (gate.current) return;
    gate.current = true;
    freshness.current++;
    setBusy(true);
    try {
      const r = (await fn()) as any;
      if (r?.message) {
        setNotice(r.message);
        if (r?.rewards) setTab("guild");
        if (r?.open_auctions) setTab("auction");
        if (r?.open_recovery) setTab("recovery");
      } else if (r?.code) setNotice("Código Discord (5 minutos): " + r.code);
      else if (r?.status) {
        setFx({
          seq: ++sequence.current,
          status: r.status,
          enemy_id: r.enemy_id,
        });
        setNotice(
          r.status === "won"
            ? "Vitória! Consulte suas recompensas na Guilda."
            : r.status === "lost"
              ? "Tentativa encerrada. Consulte o resumo do resgate."
              : "Turno concluído.",
        );
      }
      if(sessionStorage.getItem("token"))await refresh(true);
    } catch (e) {
      setNotice((e as Error).message);
    } finally {
      gate.current = false;
      setBusy(false);
    }
  }
  const move = (dx: number, dy: number) =>
    void execute(async () => {
      if (live.current?.battle || live.current?.death) return;
      apply(await api("/move", { dx, dy }));
    });
  const target = (t: Target) =>
    void execute(async () => {
      const s = live.current;
      if (!s || s.battle || s.death) return;
      if (t.kind === "exit" && s.expedition?.status === "ACTIVE")
        throw Error(
          "Você ainda está em uma expedição. Derrote os inimigos restantes ou fuja da aventura.",
        );
      const path = route(s, t);
      if (!path) throw Error("Não há um caminho livre até esse destino.");
      setNotice("Caminhando…");
      for (const [dx, dy] of path) {
        apply(await api("/move", { dx, dy }));
        await wait(160);
      }
      if (t.kind === "exit") {
        setPeers([]);
        return api("/rooms/exits/" + t.id, {});
      }
      if (t.kind === "npc") return api("/interact", {});
      if (t.kind === "monster") {
        if (
          s.map.enemies.find(
            (e) => String(e.id) === t.monster || e.spawn_key === t.monster,
          )?.species === "boss"
        ) {
          setBossWarning(true);
          return;
        }
        return api("/battles", { monster: t.monster });
      }
    });
  async function authenticate(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const form = new FormData(e.currentTarget);
    setBusy(true);
    try {
      const button = (e.nativeEvent as SubmitEvent)
        .submitter as HTMLButtonElement;
      const data = await api("/auth/" + button.value, {
        username: form.get("username"),
        password: form.get("password"),
      });
      sessionStorage.setItem("token", data.token);
      setToken(data.token);
    } catch (e) {
      setNotice((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  const openFlee = () =>
    void execute(async () => {
      const id = live.current?.expedition?.id;
      if (id) setFleePreview(await api("/expeditions/" + id + "/flee-preview"));
    });
  const confirmFlee = () =>
    void execute(async () => {
      if (!fleePreview) return;
      try {
        const result = await api(
          "/expeditions/" + fleePreview.expedition_id + "/flee",
          {
            confirmed: true,
            confirmation_token: fleePreview.confirmation_token,
          },
        );
        setFleePreview(null);
        setPeers([]);
        return result;
      } catch (error) {
        setFleePreview(null);
        throw error;
      }
    });
  const c = state?.character,
    b = state?.battle;
  const action = (path: string, body: unknown = {}) =>
    void execute(() => api(path, body));
  return (
    <main aria-busy={busy}>
      <header>
        <a className="brand" href="/">
          ♜{" "}
          <span>
            DUNGEON <b>GAME</b>
            <small>CRÔNICAS DO ALVORECER</small>
          </span>
        </a>
        <div className="server">
          <i /> MUNDO PERSISTENTE <span>• PRIMEIRO ANDAR</span>
        </div>
        {token && (
          <button
            className="quiet"
            onClick={()=>void execute(async()=>{try{await api("/auth/logout",{})}finally{clearSession();}})}
          >
            Sair
          </button>
        )}
      </header>
      {!token ? (
        <section className="welcome">
          <div>
            <p className="eyebrow">ENTRE SALAS, SEGREDOS E NOVOS COMEÇOS</p>
            <h1>
              Uma pequena vila.
              <br />
              Uma torre de <em>possibilidades.</em>
            </h1>
            <p>
              Encontre seu caminho entre bosques iluminados, uma guilda
              acolhedora e portas que ainda não têm nome.
            </p>
            <div className="welcome-art">✦　♜　✧</div>
          </div>
          <form className="panel login" onSubmit={authenticate}>
            <small>SEU PRÓXIMO CAPÍTULO</small>
            <h2>Entre no Alvorecer</h2>
            <label>
              Conta
              <input
                name="username"
                required
                minLength={3}
                maxLength={40}
                pattern="[a-zA-Z0-9_]+"
                autoComplete="username"
              />
            </label>
            <label>
              Senha
              <input
                name="password"
                type="password"
                required
                minLength={8}
                maxLength={128}
                autoComplete="current-password"
              />
            </label>
            <div className="actions">
              <button disabled={busy} value="login">
                Entrar
              </button>
              <button className="secondary" disabled={busy} value="register">
                Criar conta
              </button>
            </div>
          </form>
        </section>
      ) : needsCharacter ? (
        <form
          className="panel create"
          onSubmit={(e) => {
            e.preventDefault();
            const name = new FormData(e.currentTarget).get("name");
            void execute(() => api("/character", { name }));
          }}
        >
          <p className="eyebrow">SEU LUGAR NESTA HISTÓRIA</p>
          <h1>Como se chama seu aventureiro?</h1>
          <input name="name" required minLength={2} maxLength={30} />
          <button disabled={busy}>Iniciar jornada</button>
        </form>
      ) : state && c ? (
        <>
          <div className="connection-bar" role="status">
            <span>{connection} · Progresso persistente</span>
            <button disabled={busy} onClick={()=>{failures.current=0;setConnectionEpoch(v=>v+1);void refresh()}}>Atualizar</button>
          </div>
          <div className="room-heading">
            <div>
              <p className="eyebrow">
                ANDAR {c.floor} /{" "}
                {state.room.kind==="PROCEDURAL"?"EXPEDIÇÃO COM COMPROMISSO":state.room.safe ? "PORTO SEGURO" : "SALA COMUM · EXPLORAÇÃO LIVRE"}
              </p>
              <h1>{state.room.name}</h1>
            </div>
            {state.room.danger_tier > 0 && (
              <div className={"danger-tier danger-" + state.room.danger_tier}>
                PERIGO {state.room.danger_tier}{" "}
                <small>
                  {state.room.danger_tier >= 3
                    ? "REGIÃO HOSTIL"
                    : "REGIÃO DE EXPLORAÇÃO"}
                </small>
              </div>
            )}
            <div className="discovery">
              <span>✧ SEGREDOS</span>
              <strong>
                {state.atlas.secrets.found}{" "}
                <small>/ {state.atlas.secrets.total}</small>
              </strong>
            </div>
          </div>
          {state.death && (
            <DeathSummary
              death={state.death}
              busy={busy}
              onReturn={() =>
                action(
                  "/deaths/" + state.death!.death_event_id + "/acknowledge",
                )
              }
            />
          )}
          <ExpeditionPanel
            state={state}
            busy={busy}
            onPreview={openFlee}
            onAdventure={() =>
              action("/adventure", { request_id: crypto.randomUUID() })
            }
            onReturn={() => {
              const exit = state.room.exits[0];
              if (exit)
                target({ x: exit.x, y: exit.y, kind: "exit", id: exit.id });
            }}
          />
          {fleePreview && (
            <FleeModal
              preview={fleePreview}
              busy={busy}
              onCancel={() => setFleePreview(null)}
              onConfirm={confirmFlee}
            />
          )}
          <Encounters state={state} busy={busy} action={action} start={ids=>void execute(async()=>{
            const current=live.current; if(!current)return;
            const lead=current.map.enemies.find(e=>e.id===ids[0]);if(!lead)throw Error("Alvo indisponível");
            const path=route(current,{kind:"monster",monster:String(lead.id),x:lead.x,y:lead.y});if(!path)throw Error("Não há caminho até o primeiro alvo");
            for(const [dx,dy] of path){apply(await api("/move",{dx,dy}));await wait(100);}
            return api("/encounters",{enemy_ids:ids,request_id:crypto.randomUUID()});
          })}/>
          <section className="game-shell">
            <div className="status-bar">
              <div className="portrait">♙</div>
              <div>
                <strong>{c.name}</strong>
                <small>
                  NÍVEL {c.level} · XP {c.xp}/{c.level * 50}
                </small>
              </div>
              <div className="meter">
                <span>
                  ♥ {c.hp}/{30 + (c.level - 1) * 5}
                </span>
                <progress value={c.hp} max={30 + (c.level - 1) * 5} />
              </div>
              <div className="meter energy">
                <span>✦ {c.energy}/10</span>
                <progress value={c.energy} max={10} />
              </div>
              <span
                className={"coins" + (c.coins < 0 ? " debt" : "")}
                title="Pagamentos futuros da Guilda serão usados automaticamente para quitar sua dívida."
              >
                ◈ {state.coins_exact}
                {c.coins < 0 && <small>Dívida médica ativa</small>}
              </span>
              <small className="online">{peers.length + 1} NESTA SALA</small>
            </div>
            <div className="stage">
              {lootFlash && (
                <div className="loot-flash" role="status">
                  ◆ {lootFlash}
                </div>
              )}
              <Map
                state={state}
                peers={peers}
                fx={fx}
                onMove={move}
                onInteract={() => action("/interact")}
                onTarget={target}
              />
              <div className="stage-chip">
                {state.room.safe
                  ? "❖ ZONA SEGURA"
                  : "◇ " + state.room.kind.replaceAll("_", " ")}{" "}
                {state.room.completed ? "· CONCLUÍDA" : ""}
              </div>
              <div className="map-tip">
                Clique no chão para caminhar · NPCs e portas são interativos
              </div>
              {b && !state.encounter && (
                <div className="combat panel">
                  <small>COMBATE POR TURNOS · TURNO {b.turn + 1}</small>
                  <h2>
                    {state.map.enemy_names?.[b.monster] || b.monster}{" "}
                    <span>♥ {b.hp}</span>
                  </h2>
                  <div className="actions">
                    {[
                      ["attack", "⚔ Atacar"],
                      ["skill", "✦ Golpe · 2 energia"],
                      ["defend", "◇ Defender"],
                    ].map(([a, label]) => (
                      <button
                        disabled={busy}
                        key={a}
                        onClick={() =>
                          action("/battles/" + b.id + "/action", {
                            turn: b.turn,
                            action: a,
                          })
                        }
                      >
                        {label}
                      </button>
                    ))}
                  </div>
                  {b.monster === "dummy" && (
                    <small>
                      Prática sem risco. Não concede XP, itens nem moedas.
                    </small>
                  )}
                </div>
              )}
            </div>
            <div className="toolbar">
              <div className="movement">
                {[
                  [0, -1, "↑"],
                  [-1, 0, "←"],
                  [0, 1, "↓"],
                  [1, 0, "→"],
                ].map(([dx, dy, label]) => (
                  <button
                    title="Movimentar"
                    disabled={busy || !!b}
                    key={label}
                    onClick={() => move(Number(dx), Number(dy))}
                  >
                    {label}
                  </button>
                ))}
                <small>WASD / SETAS</small>
              </div>
              <button
                className="adventure"
                disabled={
                  busy ||
                  !!b ||
                  state.expedition?.status === "ACTIVE" ||
                  !["CITY", "COMMON", "COMBAT", "PROCEDURAL"].includes(
                    state.room.kind,
                  )
                }
                onClick={() =>
                  action("/adventure", { request_id: crypto.randomUUID() })
                }
              >
                ✧ AVENTURA
              </button>
              {state.room.kind === "GUILD" && (
                <button
                  className="secondary"
                  disabled={busy || !!b}
                  onClick={() => {
                    const npc = state.map.npc;
                    if (npc) target({ x: npc[0], y: npc[1], kind: "npc" });
                  }}
                >
                  Falar com recepcionista
                </button>
              )}
              {c.floor > 1 && state.map.portal && (
                <button
                  disabled={busy || !!b}
                  onClick={() =>
                    void execute(async () => {
                      const portal = state.map.portal!;
                      const path = route(state, {
                        x: portal[0],
                        y: portal[1],
                        kind: "npc",
                      });
                      if (!path) throw Error("Portal inacessível");
                      for (const [dx, dy] of path) {
                        apply(await api("/move", { dx, dy }));
                        await wait(160);
                      }
                      return api("/travel", { floor: c.floor === 1 ? 2 : 1 });
                    })
                  }
                >
                  Portal de andar
                </button>
              )}
              {state.room.safe && (
                <button disabled={busy || !!b} onClick={() => action("/rest")}>
                  Descansar
                </button>
              )}
              {state.room.kind === "TRAINING" && (
                <button
                  disabled={busy || !!b}
                  onClick={() => action("/training/reset")}
                >
                  Novo exercício
                </button>
              )}
              {state.room.kind === "SECRET_DUNGEON" && (
                <button
                  disabled={busy || !!b}
                  onClick={() => action("/dungeons/leave")}
                >
                  Voltar à cidade
                </button>
              )}
            </div>
          </section>
          <nav className="tabs">
            {[
              ["character", "♙ Personagem"],
              ["inventory", "▣ Inventário"],
              ["map", "⌘ Mapa"],
              ["exploration", "✧ Exploração"],
              ["guild", "⚑ Guilda"],
              ["auction", "⚖ Leilão"],
              ["recovery", "♜ Recuperação"],
              ["history", "◷ Histórico"],
              ["raid", "♧ Raid"],
            ].map(([id, label]) => (
              <button
                key={id}
                aria-pressed={tab === id}
                onClick={() => setTab(tab === id ? "" : id)}
              >
                {label}
                {id === "inventory" && <small>{state.inventory.length}</small>}
              </button>
            ))}
          </nav>
          <div className="lower">
            <p role="status" className="notice">
              {busy ? "◌ " : "✦ "}
              {notice}
            </p>
            <span>PRIMEIRO ANDAR · EM APERFEIÇOAMENTO</span>
          </div>
          {tab && (
            <section className="drawer panel">
              <button
                className="close"
                aria-label="Fechar menu"
                onClick={() => setTab("")}
              >
                ×
              </button>
              {tab === "character" && (
                <>
                  <p className="eyebrow">FICHA DO AVENTUREIRO</p>
                  <h2>
                    {c.name} · Nível {c.level}
                  </h2>
                  <p>
                    Força {c.strength} · Defesa {c.defense} · Experiência {c.xp}
                    /{c.level * 50}
                  </p>
                  <p>
                    Vida {c.hp} · Energia {c.energy} · Saldo {state.coins_exact}{" "}
                    moedas
                  </p>
                  {c.coins < 0 && (
                    <p className="debt">
                      Dívida médica ativa. Pagamentos futuros da Guilda serão
                      usados automaticamente para quitar sua dívida. Ao atingir
                      −10.000, cada morte em Aventura causa perda de até 10
                      níveis (mínimo 1).
                    </p>
                  )}
                  {Object.entries(state.attributes).map(([key, a]) => (
                    <p key={key}>
                      {key}: base {a.base} + equipamentos {a.equipment} +
                      temporários {a.temporary} = <strong>{a.effective}</strong>
                    </p>
                  ))}
                  <p>Ouro reservado em leilões: {state.reserved_gold}</p>
                  <AttributePanel state={state} busy={busy} action={action} />
                  <button
                    disabled={busy}
                    onClick={() => action("/discord/code")}
                  >
                    Gerar código Discord
                  </button>
                </>
              )}
              {tab === "inventory" && (
                <>
                  <p className="eyebrow">O QUE VOCÊ CARREGA</p>
                  <h2>Inventário persistente</h2>
                  <div className="items">
                    {state.inventory.map((i) => (
                      <div
                        className="item"
                        key={i.id}
                        title={
                          i.name +
                          " — " +
                          i.description +
                          " Quantidade: " +
                          i.quantity +
                          " / " +
                          i.max_stack_size
                        }
                      >
                        <div className="item-icon">
                          {i.kind === "weapon" ? "⚔" : "◆"}
                          {i.stackable && (
                            <b className="stack-count">×{i.quantity}</b>
                          )}
                        </div>
                        <span>
                          {i.name} ×{i.quantity}
                          {i.protected ? " · protegido" : ""}
                          <small>
                            {i.kind === "weapon"
                              ? "ARMA · FORÇA +" + i.power
                              : "EMPILHÁVEL · " +
                                i.quantity +
                                "/" +
                                i.max_stack_size}
                          </small>
                        </span>
                        {i.kind === "weapon" && (
                          <button
                            disabled={busy}
                            onClick={() =>
                              action(
                                "/inventory/" +
                                  i.id +
                                  (i.equipped ? "/unequip" : "/equip"),
                              )
                            }
                          >
                            {i.equipped ? "Desequipar" : "Equipar"}
                          </button>
                        )}
                      </div>
                    ))}
                  </div>
                </>
              )}
              {tab === "map" && (
                <div className="fast-travel">
                  <h3>Viagem rápida · locais visitados</h3>
                  <p>
                    Combate e expedições ativas impedem viagem. Instâncias
                    temporárias não são destinos.
                  </p>
                  {fastDestinations.map((d) => (
                    <button
                      key={d.id}
                      disabled={
                        busy || !!b || state.expedition?.status === "ACTIVE"
                      }
                      onClick={() =>
                        action("/fast-travel", { destination: d.id })
                      }
                    >
                      {d.name} · Perigo {d.danger_tier}
                    </button>
                  ))}
                </div>
              )}
              {tab === "map" && (
                <>
                  <p className="eyebrow">SUAS DESCOBERTAS</p>
                  <h2>Mapa do andar {c.floor}</h2>
                  <div className="atlas">
                    {state.atlas.rooms.map((r) => (
                      <div
                        key={r.id}
                        className={r.id === state.room.id ? "current" : ""}
                      >
                        <small>
                          {r.kind}
                          {r.danger_tier > 0
                            ? " · PERIGO " + r.danger_tier
                            : ""}
                        </small>
                        <strong>{r.name}</strong>
                        <span>
                          {r.completed
                            ? "✓ Concluída"
                            : r.id === state.room.id
                              ? "Você está aqui"
                              : "Descoberta"}
                        </span>
                      </div>
                    ))}
                  </div>
                  <div className="connections">
                    {state.atlas.connections
                      .filter(
                        (edge, i, all) =>
                          edge.target === null ||
                          all.findIndex(
                            (e) =>
                              e.source === edge.target &&
                              e.target === edge.source,
                          ) > i,
                      )
                      .map((edge, i) => (
                        <p key={i}>
                          {
                            state.atlas.rooms.find((r) => r.id === edge.source)
                              ?.name
                          }{" "}
                          <span>───</span>{" "}
                          {edge.target
                            ? state.atlas.rooms.find(
                                (r) => r.id === edge.target,
                              )?.name
                            : "? Caminho desconhecido"}
                        </p>
                      ))}
                  </div>
                  <p>
                    Caminhos ainda desconhecidos aparecem como ? nas saídas da
                    sala atual. Segredos não encontrados não aparecem no mapa.
                  </p>
                </>
              )}
              {tab === "exploration" && (
                <>
                  <p className="eyebrow">O DESCONHECIDO CHAMA</p>
                  <h2>
                    Segredos {state.atlas.secrets.found}/
                    {state.atlas.secrets.total}
                  </h2>
                  <p>
                    Aventura pode revelar uma clareira procedural ou uma entrada
                    secreta. A descoberta é permanente.
                  </p>
                  <button
                    disabled={busy || !!b}
                    onClick={() =>
                      action("/adventure", { request_id: crypto.randomUUID() })
                    }
                  >
                    Iniciar aventura
                  </button>
                  {state.atlas.rooms
                    .filter((r) => r.kind === "SECRET_DUNGEON")
                    .map((r) => (
                      <article key={r.id}>
                        <h3>{r.name}</h3>
                        <p>
                          {r.completed
                            ? "MASMORRA CONCLUÍDA · recompensas de repetição reduzidas"
                            : "Conteúdo desconhecido. A dificuldade é independente do andar. Não há perda de pertences na derrota."}
                        </p>
                        <button
                          disabled={busy || !!b}
                          onClick={() => action("/dungeons/" + r.id + "/enter")}
                        >
                          Ir para masmorra
                        </button>
                        <p>
                          Bestiário:{" "}
                          {Object.keys(r.codex).length
                            ? Object.values(r.codex)
                                .map(
                                  (m) =>
                                    m.name +
                                    (m.defeated
                                      ? " · derrotado"
                                      : " · encontrado"),
                                )
                                .join(", ")
                            : "???"}
                        </p>
                      </article>
                    ))}
                </>
              )}
              {tab === "guild" && (
                <>
                  <p className="eyebrow">GUILDA DOS AVENTUREIROS</p>
                  <h2>Recepcionista da Guilda</h2>
                  <p>
                    Registros confirmados de monstros derrotados. O Tesouro paga
                    somente na recepção, uma vez por baixa.
                  </p>
                  <div className="reward-summary">
                    {Object.entries(rewardSummary.groups).map(
                      ([name, count]) => (
                        <p key={name}>
                          {name} <strong>×{count}</strong>
                        </p>
                      ),
                    )}
                    <p>
                      Total pendente:{" "}
                      <strong>{rewardSummary.total} moedas</strong> ·{" "}
                      {rewardSummary.count} registros
                    </p>
                  </div>
                  <button
                    disabled={busy || !rewardSummary.count}
                    onClick={() => action("/guild/claim")}
                  >
                    RESGATAR RECOMPENSAS
                  </button>
                  <p>
                    Tesouro disponível da Guilda: {state.guild_treasury} moedas. Recompensas usam orçamento existente, sem emissão automática.
                  </p>
                  <p>
                    O pátio de treinamento é acessível pela porta da Guilda.
                    Praticar não concede recompensas.
                  </p>
                </>
              )}
              {tab === "auction" && (
                <AuctionHouse state={state} busy={busy} action={action} />
              )}
              {tab === "recovery" && (
                <PersonalRecovery state={state} busy={busy} action={action} />
              )}
              {tab==="history"&&<><h2>Histórico e notificações</h2><p>Últimas operações do seu personagem. Registros financeiros completos permanecem auditados.</p><ol>{state.events.slice(-20).reverse().map(e=><li key={e.id}>{({ITEM_ADDED:"Item recebido",GUILD_REWARD_CLAIMED:"Recompensa paga",EXPEDITION_STARTED:"Expedição iniciada",EXPEDITION_COMPLETED:"Expedição concluída",EXPEDITION_FLED:"Fuga confirmada",PLAYER_DIED_IN_EXPEDITION:"Resgate após morte",PERSONAL_ITEM_RECOVERED:"Item recuperado",GUILD_DEBT_COLLECTION:"Cobrança da Guilda",ATTRIBUTE_POINT_SPENT:"Atributos distribuídos",FAST_TRAVEL:"Viagem rápida"} as Record<string,string>)[e.kind]??"Progresso registrado"}{e.payload.amount!=null?" · "+String(e.payload.amount)+" moedas":""}</li>)}</ol></>}
              {tab === "raid" && (
                <>
                  <p className="eyebrow">NINGUÉM PRECISA EXPLORAR SOZINHO</p>
                  <h2>Formação de raid</h2>
                  <p>
                    Convites e participantes são persistentes. Combate
                    cooperativo ainda indisponível; enfrentar o chefe por
                    enquanto é uma tentativa individual.
                  </p>
                  {state.raid ? (
                    <>
                      <p>
                        Convite: <code>{state.raid.invite}</code>
                      </p>
                      <ul>
                        {state.raid.participants.map((p) => (
                          <li key={p.id}>
                            {p.name}
                            {p.id === state.raid?.leader_id ? " · líder" : ""}
                          </li>
                        ))}
                      </ul>
                      <button
                        disabled={busy}
                        onClick={() => action("/raids/leave")}
                      >
                        Sair / encerrar
                      </button>
                    </>
                  ) : (
                    <>
                      <button disabled={busy} onClick={() => action("/raids")}>
                        Criar raid
                      </button>
                      <form
                        onSubmit={(e) => {
                          e.preventDefault();
                          action("/raids/join", { invite });
                        }}
                      >
                        <label>
                          Convite
                          <input
                            value={invite}
                            onChange={(e) => setInvite(e.target.value)}
                            required
                          />
                        </label>
                        <button disabled={busy}>Entrar na raid</button>
                      </form>
                    </>
                  )}
                </>
              )}
            </section>
          )}
          <section className="encounters">
            {state.map.enemies
              .filter((e) => e.state === "ALIVE")
              .map((e) => (
                <button
                  className="secondary"
                  disabled={busy || !!b}
                  key={e.id}
                  data-enemy-id={e.id}
                  onClick={() =>
                    target({
                      x: e.x,
                      y: e.y,
                      kind: "monster",
                      monster: String(e.id),
                    })
                  }
                >
                  {e.species === "boss"
                    ? "⚔ Chefe do andar"
                    : e.species === "dummy"
                      ? "⚔ Treinar no boneco"
                      : "⚔ " + e.name + " · Nv." + e.level}
                </button>
              ))}
          </section>
          {state.room.exits.length > 0 && (
            <section className="paths">
              <small>CAMINHOS DESTA SALA</small>
              {state.room.exits.map((e) => (
                <button
                  className="secondary"
                  disabled={
                    busy || !!b || state.expedition?.status === "ACTIVE"
                  }
                  key={e.id}
                  onClick={() =>
                    target({ x: e.x, y: e.y, kind: "exit", id: e.id })
                  }
                >
                  ↗ {e.name}
                </button>
              ))}
            </section>
          )}
          {bossWarning && (
            <div className="modal">
              <section className="panel">
                <p className="eyebrow">CHEFE DO ANDAR</p>
                <h1>Guardião da Clareira</h1>
                <p>
                  Dificuldade: EXTREMA · Nível recomendado:{" "}
                  {state.map.recommended_level || 3}
                </p>
                <p>
                  Grupo recomendado: 4 jogadores. Você pode ser derrotado. A
                  formação de raid já existe; o combate coletivo ainda não está
                  disponível.
                </p>
                <div className="actions">
                  <button
                    onClick={() => {
                      setBossWarning(false);
                      setTab("raid");
                      action("/raids");
                    }}
                  >
                    Criar raid
                  </button>
                  <button
                    disabled={busy}
                    onClick={() => {
                      setBossWarning(false);
                      action("/battles", { monster: "boss" });
                    }}
                  >
                    Entrar mesmo assim · solo
                  </button>
                  <button
                    className="secondary"
                    onClick={() => setBossWarning(false)}
                  >
                    Voltar
                  </button>
                </div>
              </section>
            </div>
          )}
        </>
      ) : (
        <p>Carregando sua jornada…</p>
      )}
      {(!state || !token) && (
        <p role="status" className="notice">
          {notice}
        </p>
      )}
      <footer>
        ARTE ORIGINAL · UM MUNDO EM DESCOBERTA{" "}
        <span>DUNGEON GAME / ANDAR 1</span>
      </footer>
    </main>
  );
}
createRoot(document.getElementById("root")!).render(<App />);
