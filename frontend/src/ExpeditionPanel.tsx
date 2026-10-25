import type { State } from "./api";
export type FleePreview = {
  expedition_id: number;
  pending_before: number;
  pending_after: number;
  reward_loss: number;
  xp_lost: number;
  level: number;
  confirmation_token: string;
};
export function ExpeditionPanel({
  state,
  busy,
  onPreview,
  onReturn,
  onAdventure,
}: {
  state: State;
  busy: boolean;
  onPreview: () => void;
  onReturn: () => void;
  onAdventure: () => void;
}) {
  const e = state.expedition;
  if (!e) return null;
  return (
    <section
      className={
        "expedition-panel " + (e.status === "COMPLETED" ? "cleared" : "")
      }
      aria-label="Estado da expedição"
    >
      <div>
        <strong>
          {e.status === "COMPLETED" ? "EXPEDIÇÃO CONCLUÍDA" : "EXPEDIÇÃO ATIVA"}
        </strong>
        <p>
          {e.status === "COMPLETED"
            ? "Todos os inimigos foram derrotados. XP, itens e recompensas conquistadas foram preservados."
            : `${e.alive_enemies} inimigos restantes. Derrote-os ou fuja da aventura. Saída normal e nova aventura estão bloqueadas.`}
        </p>
      </div>
      {e.status === "ACTIVE" ? (
        <button className="flee" disabled={busy} onClick={onPreview}>
          FUGIR DA AVENTURA
        </button>
      ) : (
        <div className="actions">
          <button disabled={busy} onClick={onReturn}>
            RETORNAR
          </button>
          <button disabled={busy} onClick={onAdventure}>
            NOVA AVENTURA
          </button>
        </div>
      )}
    </section>
  );
}
export function FleeModal({
  preview,
  busy,
  onCancel,
  onConfirm,
}: {
  preview: FleePreview;
  busy: boolean;
  onCancel: () => void;
  onConfirm: () => void;
}) {
  return (
    <div
      className="modal"
      role="dialog"
      aria-modal="true"
      aria-labelledby="flee-title"
    >
      <section className="panel flee-confirmation">
        <p className="eyebrow">UMA DECISÃO COM CONSEQUÊNCIAS</p>
        <h1 id="flee-title">FUGIR DA AVENTURA?</h1>
        <p>
          Ainda existem inimigos nesta expedição. A fuga afeta{" "}
          <strong>todas</strong> as recompensas monetárias pendentes, inclusive
          as de outras salas.
        </p>
        <dl>
          <dt>Recompensas pendentes</dt>
          <dd>{preview.pending_before} moedas</dd>
          <dt>Você perderá</dt>
          <dd>{preview.reward_loss} moedas</dd>
          <dt>Permanecem pendentes</dt>
          <dd>{preview.pending_after} moedas</dd>
          <dt>XP atual perdido</dt>
          <dd>{preview.xp_lost} XP</dd>
        </dl>
        <p>
          Seu nível {preview.level}, os itens e as moedas já recebidas
          permanecem. Você retornará à cidade.
        </p>
        <small>
          Em valores ímpares, a perda é arredondada para cima. Se os valores
          mudarem, será necessária uma nova confirmação.
        </small>
        <div className="actions">
          <button className="flee" disabled={busy} onClick={onConfirm}>
            CONFIRMAR FUGA
          </button>
          <button className="secondary" disabled={busy} onClick={onCancel}>
            CANCELAR
          </button>
        </div>
      </section>
    </div>
  );
}
