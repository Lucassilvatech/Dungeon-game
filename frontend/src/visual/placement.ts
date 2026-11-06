import type { State } from "../api";
import { cityPaths, buildingEntrances } from "./paths";
import { tileHash } from "./themes";
export { isVillagePath } from "./paths";
export type Placement = {
  kind: string;
  x: number;
  y: number;
  width?: number;
  height?: number;
  solid?: boolean;
};
export type Zone =
  | "PATH"
  | "BUILDING_FOOTPRINT"
  | "BUILDING_INTERIOR"
  | "DOOR_ACCESS"
  | "INTERACTION_ZONE"
  | "NPC_ZONE"
  | "SPAWN_ZONE"
  | "COMBAT_ZONE"
  | "RESOURCE_ZONE"
  | "WALL"
  | "SAFE_ZONE"
  | "DECORATION_ALLOWED";
export type Zones = Record<Zone, Set<string>>;
const key = (x: number, y: number) => `${x},${y}`;
const forbidden: Zone[] = [
  "PATH",
  "BUILDING_FOOTPRINT",
  "BUILDING_INTERIOR",
  "DOOR_ACCESS",
  "INTERACTION_ZONE",
  "NPC_ZONE",
  "SPAWN_ZONE",
  "COMBAT_ZONE",
  "RESOURCE_ZONE",
  "WALL",
];
const sizes: Record<string, [number, number]> = {
  tree: [3, 4],
  well: [2, 3],
  ruin: [2, 3],
  statue: [2, 3],
  obelisk: [2, 3],
  crystal: [2, 2],
  barrel: [1, 2],
  crate: [2, 2],
  bush: [2, 1],
  flower: [1, 1],
  moss: [1, 1],
  mushroom: [1, 1],
  rock: [1, 1],
  alchemy: [3, 3],
  forge: [3, 3],
};
export function visualFootprint(p: Placement): Placement {
  const [w, h] = sizes[p.kind] ?? [1, 1];
  return {
    ...p,
    x: p.x - Math.floor(w / 2),
    y: p.y - h + 1,
    width: w,
    height: h,
  };
}
function cells(p: Pick<Placement, "x" | "y" | "width" | "height">) {
  const result: string[] = [];
  for (let y = p.y; y < p.y + (p.height ?? 1); y++)
    for (let x = p.x; x < p.x + (p.width ?? 1); x++) result.push(key(x, y));
  return result;
}
export function buildZones(s: Pick<State, "map" | "room">): Zones {
  const m = s.map,
    z = Object.fromEntries(
      [...forbidden, "SAFE_ZONE", "DECORATION_ALLOWED"].map((n) => [
        n,
        new Set<string>(),
      ]),
    ) as Zones;
  const walls = new Set(m.walls.map((p) => p.join(",")));
  z.WALL = walls;
  const square = (
    zone: Zone,
    x: number,
    y: number,
    r = 0,
    walkable = false,
  ) => {
    for (let yy = y - r; yy <= y + r; yy++)
      for (let xx = x - r; xx <= x + r; xx++)
        if (!walkable || !walls.has(key(xx, yy))) z[zone].add(key(xx, yy));
  };
  square("SPAWN_ZONE", 2, 2, 1);
  for (const e of s.room.exits) square("DOOR_ACCESS", e.x, e.y, 1);
  if (m.portal) square("DOOR_ACCESS", m.portal[0], m.portal[1], 1);
  const npcs = [
    ...(m.npc ? [m.npc] : []),
    ...(m.service_npcs ?? []).map((n) => [n.x, n.y]),
    ...(m.npcs ?? []).map((n) => [n.x, n.y]),
  ];
  for (const [x, y] of npcs) {
    square("NPC_ZONE", x, y);
    square("INTERACTION_ZONE", x, y, 1, true);
  }
  const resources = [
    ...(m.gather_nodes ?? []).map((n) => [n.x, n.y]),
    ...(m.lunar_resources ?? []).map((n) => [n.x, n.y]),
  ];
  for (const [x, y] of resources) square("RESOURCE_ZONE", x, y, 1);
  for (const b of m.buildings ?? [])
    for (const k of cells(b)) {
      z.BUILDING_FOOTPRINT.add(k);
      z.BUILDING_INTERIOR.add(k);
    }
  const spawns = m.spawns
    ? Object.values(m.spawns).map((p) => [p.x, p.y])
    : Object.values(m.monsters);
  for (const [x, y] of spawns) square("COMBAT_ZONE", x, y, 2);
  const goals = [
    [2, 2],
    ...s.room.exits.map((e) => [e.x, e.y]),
    ...npcs,
    ...resources,
    ...spawns,
  ];
  if (m.portal) goals.push(m.portal);
  const queue: [number, number][] = [[2, 2]],
    parent = new Map<string, string>([["2,2", ""]]);
  for (let i = 0; i < queue.length; i++) {
    const [x, y] = queue[i];
    for (const [dx, dy] of [
      [1, 0],
      [0, 1],
      [-1, 0],
      [0, -1],
    ]) {
      const a = x + dx,
        b = y + dy,
        k = key(a, b);
      if (
        a < 1 ||
        b < 1 ||
        a >= m.width - 1 ||
        b >= m.height - 1 ||
        walls.has(k) ||
        parent.has(k)
      )
        continue;
      parent.set(k, key(x, y));
      queue.push([a, b]);
    }
  }
  for (const [x, y] of goals) {
    let k = key(x, y);
    if (!parent.has(k))
      k =
        [
          [x + 1, y],
          [x - 1, y],
          [x, y + 1],
          [x, y - 1],
        ]
          .map((p) => p.join(","))
          .find((p) => parent.has(p)) ?? "";
    while (k) {
      z.PATH.add(k);
      k = parent.get(k) ?? "";
    }
  }
  if (s.room.kind === "CITY") {
    for (const k of cityPaths(s)) z.PATH.add(k);
    for (const d of buildingEntrances(s)) square("DOOR_ACCESS", d.x, d.y, 1);
  }
  const inside = ["GUILD", "TRAINING", "BUILDING_INTERIOR"].includes(
    s.room.kind,
  );
  const arena = ["BOSS", "SECRET_DUNGEON"].includes(s.room.kind);
  if (arena)
    for (let y = 4; y < m.height - 4; y++)
      for (let x = 5; x < m.width - 5; x++) z.COMBAT_ZONE.add(key(x, y));
  for (let y = 1; y < m.height - 1; y++)
    for (let x = 1; x < m.width - 1; x++) {
      const k = key(x, y);
      if (s.room.safe) z.SAFE_ZONE.add(k);
      if (inside) z.BUILDING_INTERIOR.add(k);
      const border = x <= 4 || y <= 4 || x >= m.width - 5 || y >= m.height - 5;
      if (
        !inside &&
        (s.room.kind === "CITY" || border) &&
        !forbidden.some((n) => z[n].has(k))
      )
        z.DECORATION_ALLOWED.add(k);
    }
  return z;
}
export function placementMask(s: Pick<State, "map" | "room">) {
  const z = buildZones(s);
  return new Set(forbidden.flatMap((n) => [...z[n]]));
}
export function canPlace(
  p: Placement,
  mask: Set<string>,
  width: number,
  height: number,
) {
  if (
    p.x < 1 ||
    p.y < 1 ||
    p.x + (p.width ?? 1) >= width ||
    p.y + (p.height ?? 1) >= height
  )
    return false;
  return cells(p).every((k) => !mask.has(k));
}
export function placementViolations(p: Placement, z: Zones): Zone[] {
  return forbidden.filter((n) => cells(p).some((k) => z[n].has(k)));
}
export type PlannedProp = Placement & { footprint: Placement; variant: number };
export function planScenery(s: Pick<State, "map" | "room">) {
  const z = buildZones(s),
    m = s.map,
    props: PlannedProp[] = [],
    occupied = new Set<string>();
  let rejected = 0;
  const approve = (p: Placement) => {
    const footprint = visualFootprint(p),
      cs = cells(footprint);
    if (
      !canPlace(footprint, new Set(), m.width, m.height) ||
      placementViolations(footprint, z).length ||
      !cs.every((k) => z.DECORATION_ALLOWED.has(k) && !occupied.has(k))
    ) {
      rejected++;
      return false;
    }
    cs.forEach((k) => occupied.add(k));
    props.push({ ...p, footprint, variant: tileHash(m.seed ?? 0, p.x, p.y) });
    return true;
  };
  const city = s.room.kind === "CITY",
    inside = ["GUILD", "TRAINING", "BUILDING_INTERIOR"].includes(s.room.kind),
    arena = ["BOSS", "SECRET_DUNGEON"].includes(s.room.kind);
  if (city) {
    // Visual reset: do not revive rejected props (wells, crates, barrels,
    // rock piles or generic profession stations). Only approved foliage
    // belongs on the village ground; interactive services remain intact.
    // Compose groves; do not scatter a random prop on every floor cell.
    const groves = [
      [0.08, 0.19],
      [0.35, 0.24],
      [0.6, 0.28],
      [0.86, 0.41],
      [0.32, 0.78],
      [0.85, 0.84],
    ];
    for (const [gx, gy] of groves) {
      const cx = Math.round(gx * m.width),
        cy = Math.round(gy * m.height),
        candidates: { x: number; y: number; rank: number }[] = [];
      for (let dy = -3; dy <= 4; dy++)
        for (let dx = -3; dx <= 3; dx++)
          candidates.push({
            x: cx + dx,
            y: cy + dy,
            rank:
              Math.abs(dx) +
              Math.abs(dy) +
              (tileHash(m.seed ?? 0, cx + dx, cy + dy) % 7) / 10,
          });
      candidates.sort((a, b) => a.rank - b.rank);
      let count = 0;
      for (const q of candidates) {
        if (approve({ kind: "tree", x: q.x, y: q.y })) {
          approve({ kind: "flower", x: q.x + 2, y: q.y - 1 });
          approve({ kind: "bush", x: q.x - 2, y: q.y });
          if (++count === 2) break;
        }
      }
    }
    for (const b of m.buildings ?? [])
      for (const x of [b.x - 2, b.x + b.width + 1])
        approve({ kind: "flower", x, y: b.y + b.height - 1 });
  } else if (!inside) {
    const theme = m.theme,
      kind = arena
        ? "obelisk"
        : theme === "crystal_bones"
          ? "crystal"
          : theme === "abandoned_wood"
            ? "statue"
            : "ruin";
    const candidates: { x: number; y: number; rank: number }[] = [];
    for (let y = 3; y < m.height - 1; y++)
      for (let x = 2; x < m.width - 1; x++)
        if (x <= 4 || y <= 4 || x >= m.width - 5 || y >= m.height - 5)
          candidates.push({ x, y, rank: tileHash((m.seed ?? 0) + 311, x, y) });
    candidates.sort((a, b) => a.rank - b.rank);
    let count = 0;
    for (const q of candidates)
      if (approve({ kind, x: q.x, y: q.y })) {
        if (!arena)
          approve({
            kind: "mushroom",
            x: q.x + (q.x < m.width / 2 ? 2 : -2),
            y: q.y - 1,
          });
        if (++count >= Math.min(6, Math.floor((m.width * m.height) / 140)))
          break;
      }
  }
  // Legacy large random props are deliberately NOT rendered through a bypass.
  // Their solid walls remain visible architecture; city scatter walls are repaired by migration.
  const authoredFurniture = (m.decorations ?? []).filter(
    (d) => ["counter", "table", "board"].includes(d.kind) && (d.width ?? 1) > 1,
  );
  const nearWall = (d: Placement) =>
    d.x <= 3 || d.y <= 3 || d.x >= m.width - 4 || d.y >= m.height - 4;
  const pairedSeat = (d: Placement) =>
    authoredFurniture.some(
      (f) =>
        d.x >= f.x - 1 &&
        d.x <= f.x + (f.width ?? 1) &&
        d.y >= f.y - 1 &&
        d.y <= f.y + (f.height ?? 1),
    );
  const fixtures = (m.decorations ?? [])
    .filter(
      (d) =>
        inside &&
        [
          "counter",
          "table",
          "board",
          "shelf",
          "chair",
          "bench",
          "banner",
        ].includes(d.kind),
    )
    .filter(
      (d) =>
        authoredFurniture.includes(d) ||
        (["shelf", "banner"].includes(d.kind) && nearWall(d)) ||
        (["chair", "bench"].includes(d.kind) && pairedSeat(d)),
    )
    .filter((d) => {
      const forbiddenFixture: Zone[] = [
        "PATH",
        "DOOR_ACCESS",
        "NPC_ZONE",
        "INTERACTION_ZONE",
        "SPAWN_ZONE",
        "RESOURCE_ZONE",
        "COMBAT_ZONE",
      ];
      return !forbiddenFixture.some((n) => cells(d).some((k) => z[n].has(k)));
    });
  const floorDetails = (m.decorations ?? []).filter(
    (d) => inside && d.kind === "rug",
  );
  const violations = props.flatMap((p) =>
    placementViolations(p.footprint, z).map((zone) => ({
      kind: p.kind,
      x: p.x,
      y: p.y,
      zone,
    })),
  );
  return { zones: z, props, fixtures, floorDetails, rejected, violations };
}
