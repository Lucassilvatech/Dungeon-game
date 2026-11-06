import type Phaser from "phaser";

/**
 * Direction set by user references:
 * - regular fights: mossy dark green / teal masonry, readable floor;
 * - bosses: darker indigo / violet ritual masonry, optional thematic accents.
 * The palette changes; geometry, walkable tiles and encounter logic do not.
 *
 * Each 32x32 frame is an authored-like, restrained pixel-art tile, drawn once.
 * No visible trash, random props or objects are added to navigation cells.
 */
export const BATTLE_TERRAIN_KEY = "battle_reference_terrain";
const SIZE = 32;

export type BattleGround =
  | "ruins" | "moss" | "cave" | "crypt"
  | "ritual" | "secret" | "boss_frost" | "boss_ember";

type Palette = {
  mortar: string;
  stone: string[];
  edge: string;
  highlight: string;
  shadow: string;
  accent: string;
};

const PALETTES: Record<BattleGround, Palette> = {
  ruins: {
    mortar: "#1c2d2d", stone: ["#2b3b3a", "#2c3e3c", "#2e4140", "#30413e"],
    edge: "#253532", highlight: "#40504a", shadow: "#1b2b2b", accent: "#426144",
  },
  moss: {
    mortar: "#1e3030", stone: ["#2c403a", "#304540", "#2a403c", "#344741"],
    edge: "#273932", highlight: "#415a49", shadow: "#1b2e2b", accent: "#547046",
  },
  cave: {
    mortar: "#1a2935", stone: ["#2c3b47", "#303f4c", "#32424f", "#2d3d49"],
    edge: "#253542", highlight: "#445763", shadow: "#192734", accent: "#5d6e77",
  },
  crypt: {
    mortar: "#222535", stone: ["#333849", "#35394a", "#393d50", "#343747"],
    edge: "#292c3d", highlight: "#505369", shadow: "#1c2230", accent: "#5e6175",
  },
  ritual: {
    mortar: "#171b2d", stone: ["#272b41", "#2d3047", "#292c43", "#303148"],
    edge: "#212438", highlight: "#3c3d58", shadow: "#131727", accent: "#59415b",
  },
  secret: {
    mortar: "#161d32", stone: ["#292f48", "#272e45", "#2c324a", "#2a2c43"],
    edge: "#20253b", highlight: "#3c435c", shadow: "#13192b", accent: "#3a5b6b",
  },
  boss_frost: {
    mortar: "#151e31", stone: ["#27374c", "#2d3a4e", "#263448", "#303e52"],
    edge: "#1f2c3d", highlight: "#43566a", shadow: "#121b2a", accent: "#477987",
  },
  boss_ember: {
    mortar: "#211b2b", stone: ["#373044", "#332b3d", "#392d40", "#342b3e"],
    edge: "#2a2234", highlight: "#554055", shadow: "#1d1625", accent: "#79504f",
  },
};
export const BATTLE_GROUNDS = Object.keys(PALETTES) as BattleGround[];

export function battleGroundSet(ground: string, mapTheme?: string): BattleGround | null {
  if (ground === "ritual" || ground === "secret") {
    if (mapTheme === "crystal_bones") return "boss_frost";
    if (mapTheme === "abandoned_wood") return "boss_ember";
  }
  return Object.prototype.hasOwnProperty.call(PALETTES, ground)
    ? ground as BattleGround : null;
}

export function battleTileFrame(ground: BattleGround, variant: number, wall = false): number {
  const index = BATTLE_GROUNDS.indexOf(ground);
  if (index < 0) throw new Error("Unknown battle terrain: " + ground);
  return index * 16 + (wall ? 8 : 0) + ((variant % 8 + 8) % 8);
}

function floor(ctx: CanvasRenderingContext2D, p: Palette, variant: number): void {
  const a = p.stone[variant % p.stone.length];
  ctx.fillStyle = p.mortar;
  ctx.fillRect(0, 0, 32, 32);
  // Slab edges remain coherent, aligned across the entire tile map.
  ctx.fillStyle = p.edge;
  ctx.fillRect(1, 1, 30, 30);
  ctx.fillStyle = a;
  ctx.fillRect(2, 2, 28, 28);
  ctx.fillStyle = p.highlight;
  ctx.fillRect(3, 2, 25, 1);
  ctx.fillRect(2, 3, 1, 23);
  ctx.fillStyle = p.shadow;
  ctx.fillRect(28, 3, 2, 27);
  ctx.fillRect(3, 28, 25, 2);
  // Sparse wear appears on no more than three of the eight variants.
  if (variant === 2 || variant === 5) {
    ctx.fillStyle = p.edge;
    ctx.fillRect(18, 7, 1, 6);
    ctx.fillRect(19, 12, 4, 1);
    ctx.fillRect(23, 13, 1, 5);
    ctx.fillRect(22, 18, 1, 3);
  } else if (variant === 7) {
    ctx.fillStyle = p.accent;
    ctx.fillRect(5, 24, 3, 2);
    ctx.fillRect(8, 21, 2, 4);
    ctx.fillRect(11, 24, 1, 2);
  }
}

function wall(ctx: CanvasRenderingContext2D, p: Palette, variant: number): void {
  ctx.fillStyle = p.mortar;
  ctx.fillRect(0, 0, 32, 32);
  // Staggered stone courses resemble the reference's solid dungeon walls.
  for (let row = 0; row < 4; row++) {
    const offset = row % 2 ? 8 : 0;
    for (let x = -offset; x < 32; x += 16) {
      const y = row * 8;
      ctx.fillStyle = p.edge;
      ctx.fillRect(x + 1, y + 1, 14, 7);
      ctx.fillStyle = p.stone[(variant + row) % p.stone.length];
      ctx.fillRect(x + 2, y + 2, 12, 5);
      ctx.fillStyle = p.highlight;
      ctx.fillRect(x + 3, y + 2, 10, 1);
      ctx.fillStyle = p.shadow;
      ctx.fillRect(x + 3, y + 6, 10, 1);
    }
  }
  ctx.fillStyle = p.shadow;
  ctx.fillRect(0, 29, 32, 3);
  if (variant === 3) {
    ctx.fillStyle = p.accent;
    ctx.fillRect(23, 19, 1, 5);
    ctx.fillRect(24, 22, 2, 1);
  }
}

/** One 8-column atlas, two rows per palette: floor row + wall row. */
export function ensureBattleTerrain(scene: Phaser.Scene): void {
  if (scene.textures.exists(BATTLE_TERRAIN_KEY)) return;
  const canvas = document.createElement("canvas");
  canvas.width = SIZE * 8;
  canvas.height = SIZE * 2 * BATTLE_GROUNDS.length;
  const ctx = canvas.getContext("2d", { alpha: false });
  if (!ctx) throw new Error("Could not create reference battle terrain");
  ctx.imageSmoothingEnabled = false;
  BATTLE_GROUNDS.forEach((name, index) => {
    const palette = PALETTES[name];
    for (let v = 0; v < 8; v++) {
      ctx.save();
      ctx.translate(v * SIZE, index * SIZE * 2);
      floor(ctx, palette, v);
      ctx.translate(0, SIZE);
      wall(ctx, palette, v);
      ctx.restore();
    }
  });
  // Phaser 3.88 accepts a Phaser Texture, not an HTMLCanvasElement,
  // as the sprite-sheet source. Register the canvas first.
  const texture = scene.textures.addCanvas(BATTLE_TERRAIN_KEY, canvas);
  if (!texture) throw new Error("Could not register terrain canvas");
  scene.textures.addSpriteSheet("", texture, {
    frameWidth: SIZE, frameHeight: SIZE,
  });
}
