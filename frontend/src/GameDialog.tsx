import { useEffect, useRef, type ReactNode } from "react";
export type Transact = (path: string, body: unknown) => Promise<any>;
export function GameDialog({
  title,
  busy,
  onCancel,
  children,
}: {
  title: string;
  busy: boolean;
  onCancel: () => void;
  children: ReactNode;
}) {
  const ref = useRef<HTMLDialogElement>(null);
  useEffect(() => {
    const prior = document.activeElement as HTMLElement | null;
    ref.current?.showModal();
    return () => {
      prior?.focus();
    };
  }, []);
  return (
    <dialog
      ref={ref}
      className="game-dialog"
      aria-label={title}
      onCancel={(e) => {
        e.preventDefault();
        if (!busy) onCancel();
      }}
    >
      <h2>{title}</h2>
      {children}
    </dialog>
  );
}
export function commerceMessage(error: unknown) {
  const raw = error instanceof Error ? error.message : String(error);
  if (/STALE_QUOTE/.test(raw))
    return "O preço ou estoque mudou. Revise a operação novamente.";
  if (/INSUFFICIENT_DENOMINATIONS/.test(raw))
    return "Há valor suficiente, mas o pagador não possui a combinação de moedas necessária.";
  if (/INSUFFICIENT_FUNDS|Saldo físico insuficiente/.test(raw))
    return "Saldo insuficiente para esta operação.";
  if (/OUT_OF_STOCK/.test(raw)) return "Estoque insuficiente.";
  if (/OWNERSHIP/.test(raw))
    return "Você não possui essa quantidade disponível para venda.";
  if (/GUILD_BUY_DISABLED/.test(raw))
    return "Compra desativada para este item.";
  if (/GUILD_SELL_DISABLED/.test(raw))
    return "Venda desativada para este item.";
  if (/ZERO_PRICE/.test(raw))
    return "A política atual não permite esta transferência gratuita.";
  return raw.replace(/^[A-Z_]+:\s*/, "");
}
