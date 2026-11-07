import type { Enemy, State } from "../api";
import { resolveTheme, visualHash } from "./themes";
export const ACTOR_FRAME = { width: 48, height: 64, count: 96 };
export type Direction = 0 | 1 | 2 | 3; // down, left, right, up
export function direction(
  dx: number,
  dy: number,
  previous: Direction = 0,
): Direction {
  return Math.abs(dx) + Math.abs(dy) === 0
    ? previous
    : Math.abs(dx) > Math.abs(dy)
      ? dx < 0
        ? 1
        : 2
      : dy < 0
        ? 3
        : 0;
}
export function actorFrame(
  mode: "idle" | "walk" | "attack" | "hurt" | "death",
  dir: Direction,
  tick: number,
): number {
  const start = { idle: 0, walk: 16, attack: 48, hurt: 64, death: 80 }[mode],
    count = mode === "walk" ? 8 : 4;
  return start + dir * count + (((Math.floor(tick) % count) + count) % count);
}
export function appearance(
  e: Pick<Enemy, "species" | "category" | "spawn_key">,
  s: Pick<State, "map" | "room">,
) {
  const boss =
    e.category === "boss" || ["boss", "warden", "champion"].includes(e.species);
  if (boss) {
    // Narrative identities stay fixed; procedural identity uses persisted room seed/spawn key.
    const pool = resolveTheme(s).bossProfile;
    const key =
      e.species === "warden"
        ? "abyssal_warden"
        : e.species === "boss"
          ? "moss_colossus"
          : pool[
              visualHash(`${s.map.seed ?? 0}:${s.room.id}:${e.spawn_key}`) %
                pool.length
            ];
    return {
      key: "boss_" + key,
      scale: 2,
      boss: true,
      width: 96,
      height: 96,
      hitbox: 32,
    };
  }
  const mini = e.category === "miniboss",
    rare = e.category === "rare";
  const species = ["slime", "goblin", "dummy"].includes(e.species)
    ? e.species
    : "goblin";
  return {
    key: species + (mini ? "_elite" : ""),
    scale: mini ? 1.5 : 1,
    boss: false,
    width: 48,
    height: 64,
    hitbox: 32,
    rare,
  };
}
