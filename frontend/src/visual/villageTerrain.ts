import type Phaser from "phaser";

/**
 * Village terrain drawn in the palette and scale of the approved safe-zone
 * reference. These tiles replace the generic, noisy procedural grass and
 * unrelated stone-floor graphics. Drawing is pixel-perfect and deterministic.
 *
 * Never draw decorative obstacles or flowers on a traversable road tile:
 * those are planned separately by the protected placement mask.
 */
export const VILLAGE_TERRAIN_KEY = "village_reference_terrain";
const SIZE = 32;
const GRASS = ["#628a50", "#638c52", "#658e53", "#60884e", "#648d52", "#628b50", "#658c51", "#638b50"];
const STONE = ["#cbb398", "#cfb99f", "#c9b096", "#d1bba1"];

function drawGrass(ctx: CanvasRenderingContext2D, variant: number) {
  ctx.fillStyle = GRASS[variant];
  ctx.fillRect(0, 0, SIZE, SIZE);
  // Broad, subtle vegetation rather than high-frequency texture/noise.
  ctx.fillStyle = variant % 2 ? "#60884c" : "#678e55";
  ctx.fillRect(0, 19, 13, 10);
  ctx.fillRect(13, 24, 12, 8);
  ctx.fillStyle = variant % 3 === 0 ? "#6b9559" : "#628b50";
  ctx.fillRect(18, 0, 14, 11);
  ctx.fillRect(23, 7, 9, 7);
  // A few discrete blades; no random stones, crates, wells or ground dirt.
  const blades = [
    [[4, 6], [22, 20]], [[7, 21], [25, 5]],
    [[13, 12], [28, 27]], [[5, 28], [20, 15]],
    [[8, 8], [27, 21]], [[12, 26], [26, 11]],
    [[15, 5], [5, 17]], [[12, 18], [25, 27]],
  ][variant];
  for (const [x, y] of blades) {
    ctx.fillStyle = "#557b43";
    ctx.fillRect(x, y + 2, 2, 3);
    ctx.fillStyle = "#789d61";
    ctx.fillRect(x + 1, y, 1, 3);
    ctx.fillRect(x + 3, y + 1, 1, 2);
  }
}

function drawStonePath(ctx: CanvasRenderingContext2D, variant: number) {
  ctx.fillStyle = "#a8927b";
  ctx.fillRect(0, 0, SIZE, SIZE);
  // Four aligned courses of cobblestone. The half-brick shift is consistent
  // across adjacent map cells, preventing the floating-tile appearance.
  for (let row = 0; row < 4; row++) {
    const y = row * 8;
    const shift = row % 2 ? 8 : 0;
    for (let x = -shift; x < SIZE; x += 16) {
      const stone = STONE[(row + Math.floor(x / 16) + variant + 12) % STONE.length];
      ctx.fillStyle = "#9d8773";
      ctx.fillRect(x + 1, y + 2, 14, 6);
      ctx.fillStyle = stone;
      ctx.fillRect(x + 2, y + 1, 12, 6);
      ctx.fillRect(x + 1, y + 2, 14, 4);
      ctx.fillStyle = "#ddc7b0";
      ctx.fillRect(x + 3, y + 1, 10, 1);
      ctx.fillRect(x + 1, y + 3, 1, 2);
      ctx.fillStyle = "#b59d85";
      ctx.fillRect(x + 4, y + 6, 9, 1);
    }
  }
}

/** A runtime-generated spritesheet avoids stale committed PNG atlases. */
export function ensureVillageTerrain(scene: Phaser.Scene): void {
  if (scene.textures.exists(VILLAGE_TERRAIN_KEY)) return;
  const canvas = document.createElement("canvas");
  canvas.width = SIZE * 16;
  canvas.height = SIZE;
  const ctx = canvas.getContext("2d", { alpha: false });
  if (!ctx) throw new Error("Could not create reference village terrain");
  ctx.imageSmoothingEnabled = false;
  for (let frame = 0; frame < 16; frame++) {
    ctx.save();
    ctx.translate(frame * SIZE, 0);
    if (frame < 8) drawGrass(ctx, frame);
    else drawStonePath(ctx, frame - 8);
    ctx.restore();
  }
  scene.textures.addSpriteSheet(VILLAGE_TERRAIN_KEY, canvas, {
    frameWidth: SIZE, frameHeight: SIZE,
  });
}
