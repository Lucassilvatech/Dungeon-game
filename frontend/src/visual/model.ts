import type { State } from "../api";
import { buildingEntrances, cityPaths } from "./paths";
import { resolveTheme } from "./themes";

export { TILE } from "./scale";
export const cellKey = (x: number, y: number) => `${x},${y}`;
/** Read-only adapter. No geometry, persisted seeds or gameplay coordinates are changed. */
export function mapModel(s: Pick<State, "map" | "room">) {
  const m = s.map,
    walls = new Set(m.walls.map(([x, y]) => cellKey(x, y)));
  const buildingCells = new Set<string>();
  for (const b of m.buildings ?? [])
    for (let y = b.y; y < b.y + b.height; y++)
      for (let x = b.x; x < b.x + b.width; x++)
        buildingCells.add(cellKey(x, y));
  const boundary: number[][] = [],
    masonry: number[][] = [],
    obstacles: number[][] = [];
  for (const [x, y] of m.walls) {
    if (buildingCells.has(cellKey(x, y))) continue;
    if (x === 0 || y === 0 || x === m.width - 1 || y === m.height - 1)
      boundary.push([x, y]);
    else if (
      [
        [1, 0],
        [-1, 0],
        [0, 1],
        [0, -1],
      ].some(([dx, dy]) => walls.has(cellKey(x + dx, y + dy)))
    )
      masonry.push([x, y]);
    else obstacles.push([x, y]);
  }
  const theme = resolveTheme(s),
    village = s.room.kind === "CITY";
  const interior = ["GUILD", "TRAINING", "BUILDING_INTERIOR"].includes(
    s.room.kind,
  );
  const ritual = ["BOSS", "SECRET_DUNGEON"].includes(s.room.kind);
  return {
    width: m.width,
    height: m.height,
    seed: m.seed ?? 0,
    walls,
    buildingCells,
    boundary,
    masonry,
    obstacles,
    paths: cityPaths(s),
    entrances: buildingEntrances(s),
    theme,
    village,
    interior,
    ritual,
    ground: village ? "grass" : interior ? "wood" : ritual ? "ritual" : "ruins",
    wall: ritual ? "ritual_wall" : "ruins_wall",
  };
}
export type MapModel = ReturnType<typeof mapModel>;
