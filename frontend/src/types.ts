export type Exit = {
  id: number;
  x: number;
  y: number;
  name: string;
  known: boolean;
};
export type Room = {
  id: string;
  name: string;
  kind: string;
  completed: boolean;
  safe: boolean;
  danger_tier: number;
  codex: Record<string, { name: string; seen: boolean; defeated: boolean }>;
  exits: Exit[];
};
export type Peer = { id: number; name: string; x: number; y: number };
export type Target = {
  x: number;
  y: number;
  kind: "ground" | "exit" | "npc" | "monster";
  id?: number;
  monster?: string;
};
