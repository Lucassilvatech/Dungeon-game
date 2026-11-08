import Phaser from "phaser";
import manifest from "./visual/atlas.json";
import { preloadMapAssets } from "./visual/assets";
import { preloadCharacterLayers } from "./appearance/compositor";
/** Shipping PNG atlases; original source and compiler are versioned with the game. */
export function preloadSprites(scene: Phaser.Scene) {
  preloadMapAssets(scene);
  preloadCharacterLayers(scene);
  for (const [name, e] of Object.entries(manifest)) {
    scene.load.spritesheet(name, "/assets/pixel/" + e.file, {
      frameWidth: "frameWidth" in e.frames ? 48 : name === "effects" ? 64 : 128,
      frameHeight:
        "frameWidth" in e.frames ? 64 : name === "effects" ? 64 : 128,
    });
  }
}
export function createSprites(scene: Phaser.Scene) {
  for (const key of Object.keys(manifest)) {
    if (!scene.textures.exists(key)) throw Error("Asset não carregado: " + key);
    scene.textures.get(key).setFilter(Phaser.Textures.FilterMode.NEAREST);
  }
}
export const frames = {
  effects: manifest.effects.frames,
  bosses: manifest.bosses.frames,
};
