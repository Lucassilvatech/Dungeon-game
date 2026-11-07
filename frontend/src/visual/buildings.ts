import { TILE } from "./scale";
import type { State } from "../api";
import type { MapModel } from "./model";
import { SceneLayer } from "./layer";

let serial = 0;
/** Fit the facade to the existing footprint AND its actual server doorway.
 * Two roof/facade wings meet at the door centre. The floor and route share that
 * exact coordinate, including off-centre historical doors such as the Guild.
 */
export function drawBuildings(
  layer: SceneLayer,
  model: MapModel,
  state: State,
) {
  for (const [i, entrance] of model.entrances.entries()) {
    const { building: b, x: dx, y: dy } = entrance;
    const source = layer.scene.textures.get("map-village"),
      frame = source.get("house_2");
    const image = source.getSourceImage() as HTMLImageElement;
    const canvas = document.createElement("canvas");
    canvas.width = b.width * TILE;
    canvas.height = b.height * TILE;
    const ctx = canvas.getContext("2d")!;
    ctx.imageSmoothingEnabled = false;
    const centre = (dx - b.x) * TILE + TILE / 2,
      split = Math.floor(frame.cutWidth / 2);
    ctx.drawImage(
      image,
      frame.cutX,
      frame.cutY,
      split,
      frame.cutHeight,
      0,
      0,
      centre,
      canvas.height,
    );
    ctx.drawImage(
      image,
      frame.cutX + split,
      frame.cutY,
      frame.cutWidth - split,
      frame.cutHeight,
      centre,
      0,
      canvas.width - centre,
      canvas.height,
    );
    // Slight roof variation shares the original architecture; no added vines or props.
    if (i % 3 === 1) {
      ctx.globalCompositeOperation = "source-atop";
      ctx.fillStyle = "#6c443208";
      ctx.fillRect(0, 0, canvas.width, Math.floor(canvas.height * 0.45));
    }
    const key = "map-building-" + serial++;
    layer.scene.textures.addCanvas(key, canvas);
    layer.keep(
      layer.scene.add
        .image(b.x * TILE, dy * TILE, key)
        .setOrigin(0, 1)
        .setDepth(100 + dy * TILE),
    );
    layer.disposers.push(() => layer.scene.textures.remove(key));
  }
  const tent = state.map.decorations?.find((d) => d.kind === "recovery_tent");
  if (
    model.village &&
    tent &&
    state.map.npc_role === "recovery" &&
    state.map.npc
  ) {
    const x = (tent.x + (tent.width ?? 5) / 2) * TILE,
      y = (tent.y + (tent.height ?? 5)) * TILE;
    const sprite = layer.sprite(
      "recovery_tent",
      x,
      y,
      100 + state.map.npc[1] * TILE,
    );
    sprite.setDisplaySize(
      Math.min(sprite.width, (tent.width ?? 5) * TILE),
      Math.min(sprite.height, (tent.height ?? 5) * TILE),
    );
  }
}
