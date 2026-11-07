import { TILE } from "./scale";
import type { State } from "../api";
import { cityPaths, buildingEntrances } from "./paths";
import { tileHash } from "./themes";
import { visualBounds } from "./assets";
import { villageGroves, ruinSites } from "./composition";
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
export function visualFootprint(p: Placement): Placement {
  const { width, height } = visualBounds(p.kind);
  const left = Math.floor(p.x + 0.5 - width / (TILE * 2));
  const right = Math.ceil(p.x + 0.5 + width / (TILE * 2));
  const top = Math.floor(p.y + 1 - height / TILE);
  return {
    ...p,
    x: left,
    y: top,
    width: right - left,
    height: p.y + 1 - top,
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
    for (const candidates of villageGroves(s)) {
      let count = 0;
      for (const q of candidates)
        if (approve({ kind: "tree", x: q.x, y: q.y })) {
          approve({ kind: "flower", x: q.x + 2, y: q.y });
          approve({ kind: "bush", x: q.x - 2, y: q.y - 1 });
          approve({ kind: "grass_tuft", x: q.x + 2, y: q.y + 1 });
          if (++count === 2) break;
        }
    }
    for (const b of m.buildings ?? [])
      for (const x of [b.x - 1, b.x + b.width])
        approve({ kind: "flower", x, y: b.y + b.height - 1 });
  } else if (!inside) {
    let count = 0;
    const pool = arena
      ? ["obelisk", "crystal", "tomb", "broken_column", "candle"]
      : m.theme === "crystal_bones"
        ? ["crystal", "boulder", "ruin"]
        : ["ruin", "statue", "boulder", "broken_column"];
    for (const q of ruinSites(s)) {
      const kind = pool[count % pool.length];
      if (approve({ kind, x: q.x, y: q.y })) {
        approve({
          kind: arena ? "bones" : "moss",
          x: q.x + (q.x < m.width / 2 ? 2 : -2),
          y: q.y,
        });
        if (++count >= Math.min(8, Math.floor((m.width * m.height) / 110)))
          break;
      }
    }
  }
  // Legacy large random props are deliberately NOT rendered through a bypass.
  // Their solid walls remain visible architecture; city scatter walls are repaired by migration.
  const authoredFurniture = (m.decorations ?? []).filter(
    (d) => ["counter", "table", "board"].includes(d.kind) && (d.width ?? 1) > 1,
  );
  const nearWall = (d: Placement) =>
    d.x <= 3 || d.y <= 3 || d.x >= m.width - 4 || d.y >= m.height - 4;
  const pairedSeat = (d: Placement, tables: Placement[] = authoredFurniture) =>
    tables.some(
      (f) =>
        d.x >= f.x - 1 &&
        d.x <= f.x + (f.width ?? 1) &&
        d.y >= f.y - 1 &&
        d.y <= f.y + (f.height ?? 1),
    );
  const eligibleFixtures = (m.decorations ?? [])
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
  const retainedTables = [
    ...eligibleFixtures.filter((d) => ["table", "counter"].includes(d.kind)),
    ...authoredFurniture.filter(
      (d) =>
        d.kind === "counter" && d.solid && cells(d).every((k) => z.WALL.has(k)),
    ),
  ];
  const fixtures = eligibleFixtures.filter(
    (d) =>
      !["chair", "bench"].includes(d.kind) || pairedSeat(d, retainedTables),
  );
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
