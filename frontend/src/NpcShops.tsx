import { useEffect, useState } from "react";
import { api, type State } from "./api";
import { Shop } from "./Shop";
import type { Transact } from "./GameDialog";
import type { Target } from "./types";
import type { NpcEconomyState } from "./npcTypes";
export function NpcShops({
  state,
  busy,
  transact,
  target,
  selected,
  onSelect,
}: {
  state: State;
  busy: boolean;
  transact: Transact;
  target: (t: Target) => void;
  selected: string;
  onSelect: (s: string) => void;
}) {
  const [npcs, setNpcs] = useState<NpcEconomyState[]>([]),
    [error, setError] = useState("");
  useEffect(() => {
    let live = true;
    api("/economy/npcs")
      .then((d) => {
        if (live) setNpcs(d);
      })
      .catch((e) => {
        if (live) setError(e.message);
      });
    return () => {
      live = false;
    };
  }, [busy]);
  return (
    <section>
      <h2>Lojas da vila</h2>
      {error && <p role="alert">{error}</p>}
      <nav className="npc-shop-nav">
        {npcs.map((n) => (
          <button
            key={n.id}
            aria-pressed={selected === n.id}
            onClick={() => onSelect(n.id)}
          >
            {n.name}
          </button>
        ))}
      </nav>
      {npcs
        .filter((n) => n.id === selected)
        .map((n) => {
          const service = state.map.service_npcs?.find((s) => s.id === n.id);
          return (
            <section key={n.id}>
              {service && (
                <button
                  disabled={busy || !!state.battle}
                  onClick={() =>
                    target({
                      x: service.x,
                      y: service.y,
                      kind: "service",
                      serviceId: n.id,
                    })
                  }
                >
                  Ir até {n.name}
                </button>
              )}
              {!service && <p>Visite a vila para negociar pessoalmente.</p>}
              <Shop
                key={n.id}
                npcId={n.id}
                npcName={n.name}
                state={state}
                busy={busy}
                transact={transact}
              />
            </section>
          );
        })}
    </section>
  );
}
