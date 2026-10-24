import Phaser from "phaser";
/** Original 16x24 pixel sprites, four poses in five animation states.
 * Texture keys/frame ranges are stable so authored spritesheets can replace them. */
export function createSprites(scene: Phaser.Scene) {
  const palettes: Record<string, string[]> = {
    hero: ["#e9cfa1", "#497b8d", "#473a39"],
    peer: ["#e7c6a2", "#9477a5", "#3e3242"],
    npc: ["#e8c7a0", "#c18c55", "#77543d"],
    slime: ["#a4d698", "#609967", "#284f48"],
    goblin: ["#a8b983", "#637a66", "#384c46"],
    boss: ["#c5a9a0", "#925965", "#45354c"],
    warden: ["#a5d4d7", "#447d97", "#273e65"],
    dummy: ["#d5b17b", "#947444", "#493e32"],
  };
  for (const [key, colors] of Object.entries(palettes)) {
    if (scene.textures.exists(key)) continue;
    const texture = scene.textures.createCanvas(key, 16 * 20, 24)!;
    const ctx = texture.context;
    for (let frame = 0; frame < 20; frame++) {
      const state = Math.floor(frame / 4),
        step = frame % 4,
        ox = frame * 16;
      const bob =
        state === 1 ? step % 2 : state === 0 ? (step === 2 ? 1 : 0) : 0;
      const rect = (
        x: number,
        y: number,
        w: number,
        h: number,
        color: string,
      ) => {
        ctx.fillStyle = color;
        ctx.fillRect(ox + x, y + bob, w, h);
      };
      if (state === 4) {
        rect(3, 20, 10, 2, colors[1]);
        texture.add(frame, 0, ox, 0, 16, 24);
        continue;
      }
      rect(4, 19, 3, 4, colors[2]);
      rect(9, 19 + (state === 1 ? step % 2 : 0), 3, 4, colors[2]);
      if (key === "slime") {
        rect(2, 13, 12, 8, colors[1]);
        rect(4, 10, 8, 3, colors[0]);
      } else {
        rect(3, 10, 10, 10, colors[2]);
        rect(4, 10, 8, 8, colors[1]);
        rect(4, 19, 3, 2, "#b0a079");
        rect(4, 16, 8, 2, colors[2]);
        rect(7, 16, 2, 2, "#dac38d");
        rect(4, 3, 8, 8, colors[0]);
        rect(3, 2, 10, 3, colors[2]);
        rect(2, 12, 2, 6, colors[0]);
        rect(13, 12, 2, 6, colors[0]);
      }
      rect(6, 6 + (key === "slime" ? 8 : 0), 1, 2, "#182d34");
      rect(10, 6 + (key === "slime" ? 8 : 0), 1, 2, "#182d34");
      if (key === "npc") {
        rect(3, 2, 10, 4, colors[2]);
        rect(4, 12, 7, 7, "#dfd3aa");
        rect(4, 12, 2, 4, colors[1]);
      }
      if (key === "goblin") {
        rect(1, 5, 3, 3, colors[0]);
        rect(12, 5, 3, 3, colors[0]);
      }
      if (key === "hero" || state === 2) {
        rect(13, 6 - step, 2, 12, "#d8e4d5");
        rect(12, 16 - step, 4, 2, "#c7a65e");
      }
      if (state === 3) {
        ctx.fillStyle = "#ffd5bd88";
        ctx.fillRect(ox + 2, 2, 13, 20);
      }
      texture.add(frame, 0, ox, 0, 16, 24);
    }
    texture.refresh();
  }
}
