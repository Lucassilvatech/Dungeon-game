import { TILE } from "./scale";
import type { State } from "../api";
import type { MapModel } from "./model";
import { SceneLayer } from "./layer";

/** Ritual is a floor marking: it never blocks a combat tile or adds gameplay. */
export function drawSpecialRoom(layer: SceneLayer, model: MapModel, s: State) {
  if (!model.ritual) return;
  const boss = s.map.spawns
    ? Object.values(s.map.spawns).find((e) =>
        ["boss", "warden", "champion"].includes(e.species),
      )
    : s.map.enemies.find(
        (e) => e.category === "boss" || ["boss", "warden"].includes(e.species),
      );
  const x = (boss?.x ?? Math.floor(model.width / 2)) * TILE + TILE / 2;
  const y = ((boss?.y ?? Math.floor(model.height / 2)) + 1) * TILE - 42;
  const ring = layer
    .sprite("ritual", x, y, 2)
    .setOrigin(0.5)
    .setDisplaySize(320, 320)
    .setAlpha(0.85);
  if (s.map.theme === "crystal_bones") ring.setTint(0x9cb4c6).setAlpha(0.56);
  if (s.map.theme === "abandoned_wood") ring.setTint(0xf0ab86);
}
