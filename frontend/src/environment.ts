import Phaser from "phaser";
import type { State } from "./api";
import { frames } from "./sprites";
import { resolveTheme, type VisualThemeProfile } from "./visual/themes";
import { cityPaths, buildingEntrances } from "./visual/paths";
import { planScenery, type PlannedProp } from "./visual/placement";
import { ensureVillageTerrain, VILLAGE_TERRAIN_KEY } from "./visual/villageTerrain";
import { battleGroundSet, battleTileFrame, ensureBattleTerrain, BATTLE_TERRAIN_KEY } from "./visual/battleTerrain";
type Image = Phaser.GameObjects.Image;
const scenery = frames.scenery as Record<string, number>,
  effects = frames.effects as Record<string, number>,
  tiles = frames.tiles as Record<string, number>;
export class Environment {
  objects: Phaser.GameObjects.GameObject[] = [];
  props: { image: Image; canopy: boolean }[] = [];
  lights: { image: Image; phase: number; flame?: Image }[] = [];
  particles: Image[] = [];
  theme: VisualThemeProfile;
  plan: ReturnType<typeof planScenery>;
  constructor(
    private scene: Phaser.Scene,
    private state: State,
  ) {
    this.theme = resolveTheme(state);
    this.plan = planScenery(state);
    this.build();
  }
  image(
    x: number,
    y: number,
    atlas: string,
    frame: number,
    depth: number,
    scale = 2,
  ) {
    const sp = this.scene.add
      .image(Math.round(x), Math.round(y), atlas, frame)
      .setScale(scale)
      .setDepth(depth);
    this.objects.push(sp);
    return sp;
  }
  light(x: number, y: number, ritual = false, flame = true) {
    if (this.lights.length >= 10) return;
    const im = this.image(
      x,
      y,
      "effects",
      effects[ritual ? "glow_cyan" : "glow_warm"],
      8001,
      4,
    ).setBlendMode(Phaser.BlendModes.ADD);
    const fire = flame
      ? this.image(x, y + 12, "effects", effects.flame_0, 110 + y, 1).setOrigin(
          0.5,
          1,
        )
      : undefined;
    this.lights.push({
      image: im,
      phase: this.lights.length * 1.73 + (x % 7),
      flame: fire,
    });
  }
  private prop(p: PlannedProp) {
    const name =
      p.kind === "tree" ? "tree_green_0" + ((p.variant % 3) + 1) : p.kind;
    const sp = this.image(
      p.x * 32 + 16,
      (p.y + 1) * 32,
      name in scenery ? "scenery" : "effects",
      scenery[name] ?? effects[name] ?? effects.rock,
      100 + (p.y + 1) * 32,
      name in scenery ? 2 : 0.75,
    ).setOrigin(0.5, 1);
    if (["moss", "flower"].includes(p.kind)) sp.setDepth(2);
    this.props.push({ image: sp, canopy: p.kind === "tree" });
    if (p.kind === "crystal" || p.kind === "obelisk")
      this.light(p.x * 32 + 16, p.y * 32, true, false);
  }
  build() {
    const { map: m, room } = this.state,
      p = this.theme,
      paths = cityPaths(this.state),
      entrances = buildingEntrances(this.state),
      battleGround = battleGroundSet(p.groundSet, m.theme);
    if (room.kind === "CITY") ensureVillageTerrain(this.scene);
    if (battleGround) ensureBattleTerrain(this.scene);
    const ground = this.scene.add
      .renderTexture(0, 0, m.width * 32, m.height * 32)
      .setOrigin(0)
      .setDepth(0);
    this.objects.push(ground);
    const buildings = new Set<string>();
    for (const b of m.buildings ?? [])
      for (let y = b.y; y < b.y + b.height; y++)
        for (let x = b.x; x < b.x + b.width; x++) buildings.add(`${x},${y}`);
    ground.beginDraw();
    for (let y = 0; y < m.height; y++)
      for (let x = 0; x < m.width; x++) {
        const set = paths.has(`${x},${y}`) ? "path" : p.groundSet;
        // Large deterministic fields, not a different high-contrast texture at every pixel/tile.
        const variant =
          ((Math.floor(x / 3) * 5 + Math.floor(y / 3) * 3 + (m.seed ?? 0)) >>>
            0) %
          8;
        if (room.kind === "CITY") {
          ground.batchDrawFrame(
            VILLAGE_TERRAIN_KEY,
            (set === "path" ? 8 : 0) + variant,
            x * 32,
            y * 32,
          );
        } else if (battleGround) {
          ground.batchDrawFrame(
            BATTLE_TERRAIN_KEY,
            battleTileFrame(battleGround, variant),
            x * 32,
            y * 32,
          );
        } else {
          ground.batchDrawFrame(
            "tiles",
            tiles[set + "_" + variant],
            x * 32,
            y * 32,
          );
        }
      }
    for (const [x, y] of m.walls) {
      if (buildings.has(`${x},${y}`)) continue;
      const base = p.groundSet === "grass" ? "path" : p.groundSet;
      if (battleGround) {
        ground.batchDrawFrame(
          BATTLE_TERRAIN_KEY,
          battleTileFrame(battleGround, (x + y) % 8, true),
          x * 32, y * 32,
        );
      } else {
        ground.batchDrawFrame("tiles", tiles[base + "_wall_0"], x * 32, y * 32);
      }
    }
    ground.endDraw();
    for (const [i, b] of (m.buildings ?? []).entries()) {
      const door = entrances[i],
        sp = this.image(
          door.x * 32 + 16,
          door.y * 32,
          "scenery",
          scenery["house_0" + ((i % 3) + 1)],
          100 + (b.y + b.height) * 32,
          2,
        ).setOrigin(0.5, 1);
      this.props.push({ image: sp, canopy: false });
    }
    for (const prop of this.plan.props) this.prop(prop);
    for (const d of this.plan.floorDetails)
      this.image(
        (d.x + (d.width ?? 1) / 2) * 32,
        (d.y + (d.height ?? 1) / 2) * 32,
        "effects",
        effects.rug,
        2,
        Math.max(2, (d.width ?? 4) / 2),
      );
    for (const d of this.plan.fixtures) {
      const width = d.width ?? 1;
      for (let xx = 0; xx < width; xx += 2)
        this.image(
          (d.x + xx + 1) * 32,
          (d.y + (d.height ?? 1)) * 32,
          "effects",
          effects[d.kind === "board" ? "sign" : d.kind] ?? effects.table,
          100 + (d.y + (d.height ?? 1)) * 32,
          width > 1 ? 1.5 : 0.75,
        ).setOrigin(0.5, 1);
    }
    // The server-defined recovery building is a semantic structure, not random decoration.
    const tent = (m.decorations ?? []).find((d) => d.kind === "recovery_tent");
    if (room.kind === "CITY" && m.npc_role === "recovery" && tent && m.npc) {
      const sp = this.image(
        (tent.x + (tent.width ?? 5) / 2) * 32,
        (tent.y + (tent.height ?? 5)) * 32,
        "scenery",
        scenery.recovery_tent,
        100 + m.npc[1] * 32,
        2,
      ).setOrigin(0.5, 1);
      this.props.push({ image: sp, canopy: false });
    }
    for (const e of room.exits.filter(
      (e) => !entrances.some((d) => d.exitId === e.id),
    ))
      this.image(
        e.x * 32 + 16,
        (e.y + 1) * 32,
        "effects",
        effects.portal,
        90 + (e.y + 1) * 32,
        0.75,
      ).setOrigin(0.5, 1);
    if (["BOSS", "SECRET_DUNGEON"].includes(room.kind)) {
      const boss = m.spawns
        ? Object.values(m.spawns).find((e) =>
            ["boss", "warden", "champion"].includes(e.species),
          )
        : m.enemies.find(
            (e) =>
              ["boss", "warden", "champion"].includes(e.species) ||
              e.category === "boss",
          );
      const x = (boss?.x ?? Math.floor(m.width / 2)) * 32 + 16,
        y = (boss?.y ?? Math.floor(m.height / 2)) * 32 + 16;
      const rune = this.image(x, y, "effects", effects.rune, 3, 5);
      if (battleGround === "boss_frost") rune.setTint(0x8cd5e0);
      if (battleGround === "boss_ember") rune.setTint(0xea927e);
      this.light(x, y, battleGround !== "boss_ember", false);
    }
    if (p.lightProfile !== "day") {
      for (let x = 5; x < m.width - 2; x += 8) {
        if (
          this.plan.zones.DOOR_ACCESS.has(`${x},1`) ||
          this.plan.zones.PATH.has(`${x},1`)
        )
          continue;
        this.light(x * 32, 52, false);
        if (
          x + 3 < m.width - 2 &&
          !this.plan.zones.DOOR_ACCESS.has(`${x + 3},1`)
        )
          this.image(
            (x + 3) * 32,
            58,
            "effects",
            effects.banner,
            125,
            1,
          ).setOrigin(0.5, 1);
      }
      this.objects.push(
        this.scene.add
          .rectangle(
            0,
            0,
            m.width * 32,
            m.height * 32,
            0x080d20,
            p.ambientProfile,
          )
          .setOrigin(0)
          .setDepth(8000),
      );
    }
    for (let i = 0; i < 6; i++)
      this.particles.push(
        this.image(
          (i * 137) % (m.width * 32),
          (i * 83) % (m.height * 32),
          "effects",
          effects.smoke,
          8002,
          0.25,
        ).setAlpha(0.15),
      );
  }
  update(time: number, reduced: boolean, hero: Phaser.GameObjects.Sprite) {
    const view = this.scene.cameras.main.worldView;
    for (const l of this.lights) {
      l.image
        .setVisible(Phaser.Geom.Rectangle.Overlaps(view, l.image.getBounds()))
        .setAlpha(reduced ? 0.8 : 0.8 + Math.sin(time / 240 + l.phase) * 0.1);
      l.flame?.setFrame(
        effects[
          "flame_" + (reduced ? 0 : Math.floor(time / 140 + l.phase) % 4)
        ],
      );
    }
    for (const [i, sp] of this.particles.entries()) {
      sp.setVisible(!reduced && this.theme.lightProfile !== "day");
      if (!reduced)
        sp.setPosition(
          Math.round((i * 137 + time / 150) % (this.state.map.width * 32)),
          Math.round((i * 83 + time / 350) % (this.state.map.height * 32)),
        );
    }
    for (const { image, canopy } of this.props)
      if (canopy)
        image.setAlpha(
          image.getBounds().contains(hero.x, hero.y - 15) && hero.y < image.y
            ? 0.55
            : 1,
        );
  }
  destroy() {
    this.objects.forEach((o) => o.destroy());
    this.objects = [];
  }
}
