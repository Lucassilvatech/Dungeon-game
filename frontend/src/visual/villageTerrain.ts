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
const GRASS = ["#5e8950", "#608b50", "#628b50", "#5d8850", "#618c50", "#5f8950", "#638d51", "#608b4f"];
const STONE = ["#c3a78c", "#cbb398", "#c7ad94", "#d0b89d"];

function drawGrass(ctx: CanvasRenderingContext2D, variant: number) {
  // Gentle tile-to-tile tonal variation, as in the approved village image.
  // No rectangular overlay patches: their straight edges made the grass
  // look like a noisy checkerboard instead of a continuous meadow.
  ctx.fillStyle = GRASS[variant];
  ctx.fillRect(0, 0, SIZE, SIZE);

  // Each tile contains only a few tiny, low-contrast organic clusters.
  // The positions remain deterministic and the borders stay visually calm.
  const clusters: ReadonlyArray<ReadonlyArray<readonly [number, number]>> = [
    [[9, 11]], [[21, 24]], [], [[7, 22]],
    [[24, 9]], [], [[14, 17]], [[25, 26]],
  ];
  for (const [x, y] of clusters[variant]) {
    ctx.fillStyle = "#5c844c";
    ctx.fillRect(x, y + 2, 2, 2);
    ctx.fillRect(x + 3, y + 1, 1, 2);
    ctx.fillStyle = "#6a9157";
    ctx.fillRect(x + 1, y, 1, 3);
    ctx.fillRect(x + 4, y + 2, 2, 1);
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
  // Phaser 3.88 accepts a Phaser Texture, not an HTMLCanvasElement,
  // as the sprite-sheet source. Register the canvas first.
  const texture = scene.textures.addCanvas(VILLAGE_TERRAIN_KEY, canvas);
  if (!texture) throw new Error("Could not register terrain canvas");
  scene.textures.addSpriteSheet("", texture, {
    frameWidth: SIZE, frameHeight: SIZE,
  });
}
