import Phaser from "phaser";
import { mapAssets, type MapAsset } from "./assets";

/** Own all room objects/textures so reconnect and room changes leave no old layers. */
export class SceneLayer {
  objects: Phaser.GameObjects.GameObject[] = [];
  disposers: (() => void)[] = [];
  constructor(readonly scene: Phaser.Scene) {}
  sprite(name: MapAsset, x: number, feetY: number, depth = 100 + feetY) {
    const sp = this.scene.add
      .image(
        Math.round(x),
        Math.round(feetY),
        "map-" + mapAssets[name].atlas,
        name,
      )
      .setOrigin(0.5, 1)
      .setDepth(depth);
    this.objects.push(sp);
    return sp;
  }
  keep<T extends Phaser.GameObjects.GameObject>(object: T): T {
    this.objects.push(object);
    return object;
  }
  destroy() {
    this.objects.forEach((o) => o.destroy());
    this.disposers.forEach((fn) => fn());
    this.objects.length = 0;
  }
}
