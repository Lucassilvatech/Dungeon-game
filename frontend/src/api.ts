import type { Room } from "./types";
export type Item = {
  id: number;
  name: string;
  kind: string;
  quantity: number;
  equipped: boolean;
  location: string;
};
export type Battle = {
  id: number;
  monster: string;
  hp: number;
  turn: number;
  status: string;
  claimed: boolean;
  reward_amount: number | null;
};
export type State = {
  room: Room;
  atlas: {
    connections: { source: string; target: string | null }[];
    rooms: Room[];
    secrets: { found: number; total: number };
  };
  raid: {
    id: number;
    invite: string;
    leader_id: number;
    participants: { id: number; name: string }[];
    cooperative_combat: false;
  } | null;
  character: {
    id: number;
    name: string;
    level: number;
    xp: number;
    hp: number;
    energy: number;
    strength: number;
    defense: number;
    coins: number;
    floor: number;
    room_id: string;
    x: number;
    y: number;
  };
  inventory: Item[];
  battle: Battle | null;
  unlocked_floor: number;
  map: {
    width: number;
    height: number;
    walls: number[][];
    theme: string;
    enemy_names: Record<string, string>;
    buildings?: {
      x: number;
      y: number;
      width: number;
      height: number;
      name: string;
    }[];
    recommended_level?: number;
    difficulty?: string;
    recommended_group?: number;
    npc: number[] | null;
    monsters: Record<string, number[]>;
    portal: number[] | null;
  };
};
export async function api(path: string, body?: unknown) {
  const token = sessionStorage.getItem("token");
  const r = await fetch("/api" + path, {
    method: body === undefined ? "GET" : "POST",
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: "Bearer " + token } : {}),
    },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  const data = await r.json();
  if (!r.ok)
    throw new Error(
      typeof data.detail === "string"
        ? data.detail
        : "Revise os dados informados",
    );
  return data;
}
