import { TILE } from "./scale";
import type Phaser from "phaser";
import type { State } from "../api";
import { SceneLayer } from "./layer";
import { assetFor } from "./assets";
import { type MapModel } from "./model";
import { planScenery } from "./placement";

export function drawScenery(
  layer: SceneLayer,
  model: MapModel,
  plan: ReturnType<typeof planScenery>,
  state: State,
) {
  const canopies: Phaser.GameObjects.Image[] = [];
  for (const p of plan.props) {
    const name = assetFor(p.kind, p.variant);
    const groundDetail = ["moss", "flower", "grass_tuft", "bones"].includes(
      p.kind,
    );
    const sp = layer.sprite(
      name,
      p.x * TILE + TILE / 2,
      (p.y + 1) * TILE,
      groundDetail ? 2 : 100 + (p.y + 1) * TILE,
    );
    if (p.kind === "tree") canopies.push(sp);
  }
  // Physical isolated wall cells remain obstacles. Their silhouettes fit inside
  // the original collider; ordinary decorations use the separate full mask.
  for (const [x, y] of model.obstacles) {
    if (
      plan.fixtures.some(
        (d) =>
          x >= d.x &&
          x < d.x + (d.width ?? 1) &&
          y >= d.y &&
          y < d.y + (d.height ?? 1),
      )
    )
      continue;
    const existing = state.map.decorations?.find(
      (d) => d.x === x && d.y === y && d.solid,
    );
    const indoorAsset =
      existing &&
      ["barrel", "crate", "shelf", "table", "chair", "bench"].includes(
        existing.kind,
      )
        ? assetFor(existing.kind)
        : "crate";
    const art = model.interior
      ? indoorAsset
      : model.ritual
        ? "broken_column"
        : model.village
          ? "rock"
          : "boulder";
    layer
      .sprite(art, x * TILE + TILE / 2, (y + 1) * TILE)
      .setDisplaySize(TILE - 4, TILE - 4);
  }
  // Authored service furniture occupies only its authoritative collision rectangle.
  for (const d of state.map.decorations ?? []) {
    if (!model.interior || !d.solid || !d.kind.startsWith("service_")) continue;
    const width = (d.width ?? 1) * TILE,
      height = (d.height ?? 1) * TILE;
    const sp = layer.sprite(
      assetFor(d.kind),
      (d.x + (d.width ?? 1) / 2) * TILE,
      (d.y + (d.height ?? 1)) * TILE,
    );
    const scale = Math.min(1, width / sp.width, height / sp.height);
    sp.setScale(scale);
  }
  for (const d of plan.fixtures) {
    const width = (d.width ?? 1) * TILE,
      height = (d.height ?? 1) * TILE;
    const sprite = layer.sprite(
      assetFor(d.kind),
      d.x * TILE + width / 2,
      d.y * TILE + height,
    );
    sprite.setScale(Math.min(1, width / sprite.width, height / sprite.height));
  }
  // A counter whose entire footprint already IS a server collider is architecture,
  // not extra decoration. Render it even when its service approach touches it.
  for (const d of state.map.decorations ?? []) {
    if (
      !model.interior ||
      d.kind !== "counter" ||
      !d.solid ||
      plan.fixtures.includes(d)
    )
      continue;
    const cells = [];
    for (let y = d.y; y < d.y + (d.height ?? 1); y++)
      for (let x = d.x; x < d.x + (d.width ?? 1); x++) cells.push(`${x},${y}`);
    if (!cells.every((k) => model.walls.has(k))) continue;
    layer
      .sprite(
        "counter",
        (d.x + (d.width ?? 1) / 2) * TILE,
        (d.y + (d.height ?? 1)) * TILE,
      )
      .setDisplaySize((d.width ?? 1) * TILE, (d.height ?? 1) * TILE);
  }
  for (const d of plan.floorDetails) {
    const sprite = layer.sprite(
      "rug",
      (d.x + (d.width ?? 1) / 2) * TILE,
      (d.y + (d.height ?? 1)) * TILE,
      2,
    );
    sprite
      .setDisplaySize((d.width ?? 1) * TILE, (d.height ?? 1) * TILE)
      .setAlpha(0.85);
  }
  for (const e of state.room.exits) {
    if (model.entrances.some((d) => d.exitId === e.id)) continue;
    const sprite = layer.sprite(
      model.interior && state.map.interior_theme ? "garden_steps" : "door",
      e.x * TILE + TILE / 2,
      (e.y + 1) * TILE,
      model.interior && state.map.interior_theme ? 2 : 100 + (e.y + 1) * TILE,
    );
    if (model.interior && state.map.interior_theme)
      sprite.setDisplaySize(64, 31);
    if (model.village) sprite.setAlpha(0.8);
  }
  return canopies;
}
