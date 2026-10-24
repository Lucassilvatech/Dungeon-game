import type { State } from "./api";
import type { Target } from "./types";
export function route(state: State, target: Target): [number, number][] | null {
  const m = state.map,
    c = state.character;
  const blocked = new Set(m.walls.map((p) => p.join(",")));
  Object.values(m.monsters).forEach((p) => blocked.add(p.join(",")));
  if (m.npc) blocked.add(m.npc.join(","));
  const queue: { x: number; y: number; path: [number, number][] }[] = [
    { x: c.x, y: c.y, path: [] },
  ];
  const seen = new Set([`${c.x},${c.y}`]);
  for (let i = 0; i < queue.length; i++) {
    const p = queue[i],
      d = Math.abs(p.x - target.x) + Math.abs(p.y - target.y);
    if (d <= (target.kind === "ground" ? 0 : 1)) return p.path;
    for (const [dx, dy] of [
      [0, 1],
      [1, 0],
      [0, -1],
      [-1, 0],
    ]) {
      const x = p.x + dx,
        y = p.y + dy,
        key = `${x},${y}`;
      if (
        x < 0 ||
        y < 0 ||
        x >= m.width ||
        y >= m.height ||
        blocked.has(key) ||
        seen.has(key)
      )
        continue;
      seen.add(key);
      queue.push({ x, y, path: [...p.path, [dx, dy]] });
    }
  }
  return null;
}
