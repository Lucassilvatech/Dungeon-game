import { useEffect, useRef, useState } from "react";
import { api } from "../api";
import { actorFrame } from "../visual/appearance";
import { loadLayers, composeAppearance, FRAME_W, FRAME_H } from "./compositor";
import {
  fields,
  labels,
  type Appearance,
  type AppearanceCatalog,
  type SavedAppearance,
} from "./types";
import type { Transact } from "../GameDialog";

export function AppearanceEditor({
  initial,
  onChange,
  disabled = false,
}: {
  initial?: Appearance;
  onChange: (v: Appearance) => void;
  disabled?: boolean;
}) {
  const [catalog, setCatalog] = useState<AppearanceCatalog | null>(null),
    [look, setLook] = useState<Appearance | null>(initial ?? null),
    [error, setError] = useState(""),
    [walk, setWalk] = useState(false),
    [ready, setReady] = useState(false);
  const output = useRef<HTMLCanvasElement>(null),
    atlas = useRef<HTMLCanvasElement | null>(null),
    callback = useRef(onChange);
  callback.current = onChange;
  useEffect(() => {
    let active = true;
    api("/appearance/catalog")
      .then((c: AppearanceCatalog) => {
        if (active) {
          setCatalog(c);
          if (!initial) {
            setLook(c.default);
            callback.current(c.default);
          }
        }
      })
      .catch((e) => {
        if (active) setError(e.message);
      });
    return () => {
      active = false;
    };
  }, []);
  useEffect(() => {
    let active = true;
    if (!look) return;
    setReady(false);
    loadLayers()
      .then((sources) => {
        if (active) {
          atlas.current = composeAppearance(sources, look);
          setReady(true);
        }
      })
      .catch((e) => {
        if (active)
          setError(
            "Não foi possível carregar as camadas do personagem: " + e.message,
          );
      });
    return () => {
      active = false;
    };
  }, [look]);
  useEffect(() => {
    let tick = 0;
    const draw = () => {
      const ctx = output.current?.getContext("2d");
      if (!ctx || !atlas.current) return;
      ctx.clearRect(0, 0, FRAME_W * 4, FRAME_H);
      ctx.imageSmoothingEnabled = false;
      for (let d = 0; d < 4; d++) {
        const frame = actorFrame(
          walk ? "walk" : "idle",
          d as 0 | 1 | 2 | 3,
          walk ? tick % 8 : Math.floor(tick / 4) % 4,
        );
        ctx.drawImage(
          atlas.current,
          (frame % 8) * FRAME_W,
          Math.floor(frame / 8) * FRAME_H,
          FRAME_W,
          FRAME_H,
          d * FRAME_W,
          0,
          FRAME_W,
          FRAME_H,
        );
      }
      tick++;
    };
    draw();
    const timer = setInterval(draw, 120);
    return () => clearInterval(timer);
  }, [ready, walk]);
  return (
    <section
      className="appearance-editor"
      aria-label="Personalização de aparência"
    >
      <div className="appearance-preview">
        <canvas
          ref={output}
          width={FRAME_W * 4}
          height={FRAME_H}
          aria-label="Prévia do personagem: frente, esquerda, direita e costas"
        />
        <div className="appearance-directions">
          <span>Frente</span>
          <span>Esquerda</span>
          <span>Direita</span>
          <span>Costas</span>
        </div>
        <label className="appearance-animation">
          <input
            type="checkbox"
            checked={walk}
            onChange={(e) => setWalk(e.target.checked)}
          />
          Animar caminhada
        </label>
      </div>
      {error && <p role="alert">{error}</p>}
      {!ready && !error && <p role="status">Carregando personagem…</p>}
      {catalog && look && (
        <div className="appearance-fields">
          {fields.map((field) => (
            <label key={field}>
              {labels[field]}
              <select
                aria-label={labels[field]}
                value={look[field]}
                disabled={disabled}
                onChange={(e) => {
                  const value = { ...look, [field]: e.target.value };
                  setLook(value);
                  onChange(value);
                }}
              >
                {catalog.options[field].map((row) => (
                  <option key={row.id} value={row.id}>
                    {row.label}
                  </option>
                ))}
              </select>
              {catalog.options[field].some((v) => v.color) && (
                <span className="appearance-colors" aria-hidden="true">
                  {catalog.options[field].map((row) => (
                    <i
                      key={row.id}
                      style={{
                        background: row.color,
                        outline:
                          look[field] === row.id ? "2px solid #f2ca8a" : "none",
                      }}
                    />
                  ))}
                </span>
              )}
            </label>
          ))}
        </div>
      )}
      <p className="appearance-note">
        Cabelos e roupas são livres para ambos os sexos. A aparência não altera
        atributos nem equipamentos.
      </p>
    </section>
  );
}

export function BarberEditor({
  initial,
  transact,
  onDone,
}: {
  initial: SavedAppearance;
  transact: Transact;
  onDone: () => void;
}) {
  const [look, setLook] = useState<Appearance>(initial),
    [pending, setPending] = useState(false),
    [offer, setOffer] = useState<any>(null),
    [error, setError] = useState("");
  const [revision] = useState(initial.revision);
  async function preview() {
    setPending(true);
    setError("");
    try {
      const appearance = Object.fromEntries(fields.map((k) => [k, look[k]]));
      const result = await api("/appearance/barber/preview", {
        appearance,
        expected_revision: revision,
      });
      setOffer({
        ...result,
        body: {
          appearance,
          expected_revision: revision,
          quote: result.quote,
          request_id: crypto.randomUUID(),
        },
      });
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setPending(false);
    }
  }
  async function confirm() {
    if (pending || !offer) return;
    setPending(true);
    setError("");
    try {
      await transact("/appearance/barber/confirm", offer.body);
      onDone();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setPending(false);
    }
  }
  return (
    <section>
      <h2>Barbeiro</h2>
      <AppearanceEditor
        initial={initial}
        disabled={pending}
        onChange={(value) => {
          setLook(value);
          setOffer(null);
        }}
      />
      {error && <p role="alert">{error}</p>}
      <button disabled={pending} onClick={() => void preview()}>
        Conferir alteração e preço
      </button>
      {offer && (
        <div className="appearance-confirm">
          <p>
            Serviço: <strong>{offer.fee_units} g em Moeda Lunar</strong>.
            Pagamento ao Barbeiro com moedas físicas.
          </p>
          {!offer.payment.payable && (
            <p role="alert">
              {offer.payment.error === "INSUFFICIENT_FUNDS"
                ? "Saldo insuficiente."
                : "Você precisa de denominações exatas para pagar a taxa."}
            </p>
          )}
          <button
            disabled={pending || !offer.payment.payable}
            onClick={() => void confirm()}
          >
            {pending ? "Confirmando…" : "Pagar e salvar aparência"}
          </button>
        </div>
      )}
    </section>
  );
}
