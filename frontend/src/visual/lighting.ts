import { TILE } from "./scale";
import Phaser from "phaser";
import { SceneLayer } from "./layer";
import type { MapModel } from "./model";
import type { Zones } from "./placement";
import { wallMounts } from "./composition";

type Light = { image: Phaser.GameObjects.Image; phase: number };
/** Soft room-local illumination, cached texture and bounded light count. */
export class RoomLighting {
  lights: Light[] = [];
  constructor(
    private layer: SceneLayer,
    model: MapModel,
    zones: Zones,
  ) {
    if (model.village) return;
    const key = "map-warm-light";
    if (!layer.scene.textures.exists(key)) {
      const canvas = document.createElement("canvas");
      canvas.width = canvas.height = 256;
      const ctx = canvas.getContext("2d")!,
        gradient = ctx.createRadialGradient(128, 128, 2, 128, 128, 128);
      gradient.addColorStop(0, "rgba(255,156,65,.36)");
      gradient.addColorStop(0.3, "rgba(224,117,53,.15)");
      gradient.addColorStop(1, "rgba(170,83,40,0)");
      ctx.fillStyle = gradient;
      ctx.fillRect(0, 0, 256, 256);
      layer.scene.textures.addCanvas(key, canvas);
    }
    // Source artwork already carries the ambient palette. Do not wash it out
    // behind a full-screen dark rectangle or fluorescent additive blue lights.
    for (const mount of wallMounts(model.width, zones)) {
      layer.sprite(mount.kind, mount.x, mount.y, 100 + mount.y);
      if (mount.kind === "torch") this.add(mount.x, mount.y - 30, mount.x);
    }
  }
  add(x: number, y: number, phase = 0) {
    if (this.lights.length >= 10) return;
    const image = this.layer.keep(
      this.layer.scene.add
        .image(x, y, "map-warm-light")
        .setDepth(8001)
        .setBlendMode(Phaser.BlendModes.ADD),
    );
    this.lights.push({ image, phase });
  }
  update(time: number, reduced: boolean) {
    const view = this.layer.scene.cameras.main.worldView;
    for (const light of this.lights)
      light.image
        .setVisible(
          Phaser.Geom.Rectangle.Overlaps(view, light.image.getBounds()),
        )
        .setAlpha(
          reduced ? 0.75 : 0.75 + Math.sin(time / 310 + light.phase) * 0.06,
        );
  }
}
