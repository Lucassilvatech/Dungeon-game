import type { State } from "../api";
import { tileHash } from "./themes";
import { TILE } from "./scale";
import { mapAssets } from "./assets";
import type { Zones } from "./placement";

export type Candidate = { x: number; y: number; rank: number };
/** Stable site composition, as opposed to independent random props per floor tile. */
export function villageGroves(s: Pick<State, "room" | "map">): Candidate[][] {
  const m = s.map;
  const anchors = [
    [0.08, 0.2],
    [0.34, 0.3],
    [0.61, 0.3],
    [0.86, 0.42],
    [0.31, 0.76],
    [0.86, 0.84],
  ];
  return anchors.map(([ax, ay]) => {
    const cx = Math.round(ax * m.width),
      cy = Math.round(ay * m.height),
      candidates = [];
    for (let dy = -4; dy <= 5; dy++)
      for (let dx = -4; dx <= 4; dx++) {
        const x = cx + dx,
          y = cy + dy;
        candidates.push({
          x,
          y,
          rank:
            Math.abs(dx) +
            Math.abs(dy) +
            (tileHash(m.seed ?? 0, x, y) % 17) / 20,
        });
      }
    return candidates.sort((a, b) => a.rank - b.rank);
  });
}

export function ruinSites(s: Pick<State, "room" | "map">): Candidate[] {
  const m = s.map,
    candidates = [];
  for (let y = 3; y < m.height - 1; y++)
    for (let x = 2; x < m.width - 1; x++) {
      const edge = Math.min(x, y, m.width - 1 - x, m.height - 1 - y);
      if (edge <= 4)
        candidates.push({
          x,
          y,
          rank:
            (tileHash((m.seed ?? 0) + 461, x, y) % 97) +
            Math.abs(edge - 3) * 60,
        });
    }
  return candidates.sort((a, b) => a.rank - b.rank);
}

/** Architectural wall fixtures may touch their supporting wall, never access zones. */
export function wallMounts(width: number, zones: Zones) {
  const result: {
    kind: "torch" | "banner";
    x: number;
    y: number;
    cells: string[];
  }[] = [];
  for (let x = 5; x < width - 2; x += 8)
    for (const [kind, xx] of [
      ["torch", x],
      ["banner", x + 3],
    ] as const) {
      if (xx >= width - 2 || !zones.WALL.has(`${xx},0`)) continue;
      const asset = mapAssets[kind],
        px = xx * TILE + TILE / 2,
        py = TILE + (kind === "torch" ? 30 : 32),
        cells = [];
      for (
        let yy = Math.floor((py - asset.height) / TILE);
        yy < Math.ceil(py / TILE);
        yy++
      )
        for (
          let xx = Math.floor((px - asset.width / 2) / TILE);
          xx < Math.ceil((px + asset.width / 2) / TILE);
          xx++
        )
          cells.push(`${xx},${yy}`);
      const protectedZones = [
        zones.PATH,
        zones.DOOR_ACCESS,
        zones.NPC_ZONE,
        zones.INTERACTION_ZONE,
        zones.RESOURCE_ZONE,
        zones.SPAWN_ZONE,
        zones.COMBAT_ZONE,
        zones.BUILDING_FOOTPRINT,
      ];
      if (cells.some((k) => protectedZones.some((z) => z.has(k)))) continue;
      result.push({ kind, x: px, y: py, cells });
    }
  return result;
}
