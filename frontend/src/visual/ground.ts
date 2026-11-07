import { TILE } from "./scale";
import type Phaser from "phaser";
import { cellKey, type MapModel } from "./model";

let serial = 0;
/** A continuous material field, sampled in world space. No per-tile colour squares. */
export function createGround(scene: Phaser.Scene, model: MapModel) {
  const key = "room-ground-" + serial++,
    canvas = document.createElement("canvas");
  canvas.width = model.width * TILE;
  canvas.height = model.height * TILE;
  const ctx = canvas.getContext("2d", { alpha: false });
  if (!ctx) throw new Error("Map canvas unavailable");
  ctx.imageSmoothingEnabled = false;
  const pattern = (name: string) => {
    const source = scene.textures
      .get("material-" + name)
      .getSourceImage() as HTMLImageElement;
    const result = ctx.createPattern(source, "repeat");
    if (!result) throw new Error("Material unavailable: " + name);
    // Repeatable phase is persisted-room-seed derived, never request-time randomness.
    result.setTransform(
      new DOMMatrix().translate(
        (model.seed % 4) * 64,
        ((model.seed >>> 3) % 4) * 64,
      ),
    );
    return result;
  };
  ctx.fillStyle = pattern(model.ground);
  ctx.fillRect(0, 0, canvas.width, canvas.height);
  if (model.village) drawPaths(ctx, model, pattern("path"));
  if (model.interior) {
    ctx.fillStyle = "#392c2470";
    for (const [x, y] of [...model.boundary, ...model.masonry])
      ctx.fillRect(x * TILE, y * TILE, TILE, TILE);
  } else {
    ctx.fillStyle = pattern(model.village ? "path" : model.wall);
    for (const [x, y] of [...model.boundary, ...model.masonry])
      ctx.fillRect(x * TILE, y * TILE, TILE, TILE);
  }
  // Contact shadow just below existing masonry. It does not create a collider.
  ctx.fillStyle = model.village ? "#34493530" : "#080f1648";
  for (const [x, y] of [...model.boundary, ...model.masonry]) {
    if (!model.walls.has(cellKey(x, y + 1))) {
      ctx.fillRect(x * TILE, (y + 1) * TILE, TILE, 3);
      ctx.fillStyle = model.village ? "#34493518" : "#080f1624";
      ctx.fillRect(x * TILE, (y + 1) * TILE + 3, TILE, 3);
      ctx.fillStyle = model.village ? "#34493530" : "#080f1648";
    }
  }
  scene.textures.addCanvas(key, canvas);
  const image = scene.add.image(0, 0, key).setOrigin(0).setDepth(0);
  return {
    image,
    destroy: () => {
      image.destroy();
      scene.textures.remove(key);
    },
  };
}

function drawPaths(
  ctx: CanvasRenderingContext2D,
  m: MapModel,
  material: CanvasPattern,
) {
  ctx.fillStyle = material;
  for (const k of m.paths) {
    const [x, y] = k.split(",").map(Number);
    ctx.fillRect(x * TILE, y * TILE, TILE, TILE);
  }
  // One narrow, connected edge against grass. Never a rectangle over each tile.
  for (const k of m.paths) {
    const [x, y] = k.split(",").map(Number),
      px = x * TILE,
      py = y * TILE;
    ctx.fillStyle = "#948461";
    if (
      !m.paths.has(cellKey(x - 1, y)) &&
      !m.buildingCells.has(cellKey(x - 1, y))
    )
      ctx.fillRect(px, py, 1, TILE);
    if (
      !m.paths.has(cellKey(x + 1, y)) &&
      !m.buildingCells.has(cellKey(x + 1, y))
    )
      ctx.fillRect(px + TILE - 1, py, 1, TILE);
    if (
      !m.paths.has(cellKey(x, y - 1)) &&
      !m.buildingCells.has(cellKey(x, y - 1))
    )
      ctx.fillRect(px, py, TILE, 1);
    if (
      !m.paths.has(cellKey(x, y + 1)) &&
      !m.buildingCells.has(cellKey(x, y + 1))
    )
      ctx.fillRect(px, py + TILE - 1, TILE, 1);
  }
}
