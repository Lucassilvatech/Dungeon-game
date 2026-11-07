import type Phaser from "phaser";
import manifest from "./map-atlas.json";

export type MapAsset = keyof typeof manifest.assets;
export const mapAssets = manifest.assets;
export const materials = [
  "grass",
  "path",
  "ruins",
  "ritual",
  "ruins_wall",
  "ritual_wall",
  "wood",
] as const;

export function preloadMapAssets(scene: Phaser.Scene) {
  for (const name of ["village", "dungeon", "interior"])
    scene.load.atlas(
      "map-" + name,
      `/assets/maps/${name}.png`,
      `/assets/maps/${name}.json`,
    );
  for (const name of materials)
    scene.load.image("material-" + name, `/assets/maps/${name}.png`);
}

/** The same dimensions drive drawing and placement. Never scale foliage separately. */
export function assetFor(kind: string, variant = 0): MapAsset {
  if (kind === "tree") return ("tree_" + ((variant % 3) + 1)) as MapAsset;
  if (kind in mapAssets) return kind as MapAsset;
  return "pebbles";
}

export function visualBounds(kind: string) {
  const names: MapAsset[] =
    kind === "tree" ? ["tree_1", "tree_2", "tree_3"] : [assetFor(kind)];
  return {
    width: Math.max(...names.map((n) => mapAssets[n].width)),
    height: Math.max(...names.map((n) => mapAssets[n].height)),
  };
}
