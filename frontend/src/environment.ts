import type Phaser from "phaser";
import type { State } from "./api";
import { mapModel } from "./visual/model";
import { SceneLayer } from "./visual/layer";
import { createGround } from "./visual/ground";
import { drawBuildings } from "./visual/buildings";
import { drawScenery } from "./visual/decoration";
import { drawSpecialRoom } from "./visual/specialRooms";
import { RoomLighting } from "./visual/lighting";
import { planScenery } from "./visual/placement";
import { TILE } from "./visual/scale";

/** New scene composition root. Logical map/navigation remain owned by the server. */
export class Environment {
  readonly model;
  readonly plan;
  readonly theme;
  readonly layer;
  readonly lighting;
  readonly canopies;
  readonly particles: Phaser.GameObjects.Image[] = [];
  get objects() {
    return this.layer.objects;
  }
  get lights() {
    return this.lighting.lights;
  }
  constructor(scene: Phaser.Scene, state: State) {
    this.model = mapModel(state);
    this.theme = this.model.theme;
    this.plan = planScenery(state);
    this.layer = new SceneLayer(scene);
    const ground = createGround(scene, this.model);
    this.layer.disposers.push(ground.destroy);
    drawBuildings(this.layer, this.model, state);
    this.canopies = drawScenery(this.layer, this.model, this.plan, state);
    drawSpecialRoom(this.layer, this.model, state);
    this.lighting = new RoomLighting(this.layer, this.model, this.plan.zones);
    for (const d of state.map.decorations ?? [])
      if (d.kind === "service_forge")
        this.lighting.add((d.x + 2) * TILE, (d.y + 3) * TILE, d.x);
    for (const p of this.plan.props)
      if (p.kind === "candle")
        this.lighting.add(p.x * TILE + TILE / 2, (p.y + 1) * TILE - 40, p.x);
  }
  update(time: number, reduced: boolean, hero: Phaser.GameObjects.Sprite) {
    this.lighting.update(time, reduced);
    for (const tree of this.canopies)
      tree.setAlpha(
        tree.getBounds().contains(hero.x, hero.y - 15) && hero.y < tree.y
          ? 0.3
          : 1,
      );
  }
  destroy() {
    this.layer.destroy();
  }
}
