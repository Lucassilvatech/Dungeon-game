import Phaser from "phaser";
import type { State } from "./api";
const palette: Record<string, number[]> = {
  city: [0x66866a, 0x5f7f66, 0xbcb399, 0x626d64],
  interior: [0x99714e, 0x8f6747, 0x76543e, 0xd0b087],
  moss_stone: [0x657b6c, 0x607565, 0x889389, 0x485d55],
  wild_ruins: [0x607d50, 0x59764b, 0x9c936d, 0x48664d],
  crystal_bones: [0x535d70, 0x4d5768, 0x7a8494, 0x3b4659],
  abandoned_wood: [0x80654b, 0x785d46, 0xa48963, 0x544b42],
};
export function drawEnvironment(g: Phaser.GameObjects.Graphics, s: State) {
  const m = s.map,
    p = s.room.id==="common_b"?[0x526e59,0x4a6554,0x9a9d7c,0x394e46]:s.room.id==="combat"?[0x75694c,0x6b6146,0xb0a47b,0x4e523e]:palette[m.theme] || palette.wild_ruins,
    wood = m.theme === "interior" || m.theme === "abandoned_wood";
  for (let y = 0; y < m.height; y++)
    for (let x = 0; x < m.width; x++) {
      const hash = ((x * 73856093) ^ (y * 19349663) ^ (m.seed || 0)) >>> 0;
      const path =
        m.theme === "city" &&
        (Math.abs(x - 10) < 2 || Math.abs(y - 18) < 2 || Math.abs(y - 10) < 1);
      g.fillStyle(path ? p[2] : (x + y) % 2 ? p[0] : p[1]);
      g.fillRect(x * 32, y * 32, 32, 32);
      if (wood) {
        g.lineStyle(1, p[3], 0.28);
        g.lineBetween(x * 32, y * 32 + 31, x * 32 + 32, y * 32 + 31);
        g.lineStyle(1, p[2], 0.4);
        g.lineBetween(
          x * 32 + (y % 2 ? 8 : 24),
          y * 32,
          x * 32 + (y % 2 ? 8 : 24),
          y * 32 + 32,
        );
        g.fillStyle(p[3], 0.35);
        g.fillRect(x * 32 + 4, y * 32 + 9, 17, 1);
        g.fillRect(x * 32 + 12, y * 32 + 22, 14, 1);
      } else {
        g.fillStyle(p[2], 0.4);
        g.fillRect(x * 32 + (hash % 21) + 3, y * 32 + (hash % 19) + 4, 3, 2);
        g.fillStyle(0xb6c38f, 0.35);
        if (hash % 5 === 0) {
          g.fillRect(x * 32 + 7, y * 32 + 22, 1, 4);
          g.fillRect(x * 32 + 10, y * 32 + 20, 1, 6);
        }
        if (path) {
          g.lineStyle(1, 0x837e6c, 0.5);
          g.strokeRect(x * 32 + 1, y * 32 + 1, 30, 14);
          g.strokeRect(x * 32 + 5, y * 32 + 17, 25, 13);
        }
      }
    }
  m.walls.forEach(([x, y]) => {
    g.fillStyle(0x182e30, 0.2);
    g.fillRect(x * 32 + 3, y * 32 + 8, 31, 29);
    g.fillStyle(wood ? 0x6e6660 : p[3]);
    g.fillRect(x * 32, y * 32, 32, 32);
    g.fillStyle(wood ? 0xb6a188 : p[2]);
    g.fillRect(x * 32 + 1, y * 32 + 2, 30, 22);
    g.lineStyle(1, 0x3c4b45, 0.4);
    g.lineBetween(x * 32, y * 32 + 13, x * 32 + 32, y * 32 + 13);
    g.lineBetween(x * 32 + 14, y * 32, x * 32 + 14, y * 32 + 13);
    g.fillStyle(0xddd0a0, 0.22);
    g.fillRect(x * 32 + 2, y * 32 + 2, 28, 2);
  });
  for (const b of m.buildings || []) {
    const x = b.x * 32,
      y = b.y * 32,
      w = b.width * 32,
      h = b.height * 32;
    g.fillStyle(0x152e30, 0.24);
    g.fillRect(x + 8, y + 10, w, h);
    g.fillStyle(0xc3a984);
    g.fillRect(x, y, w, h);
    g.fillStyle(0x6f4f49);
    g.fillRect(x - 4, y - 9, w + 8, 65);
    for (let row = 0; row < 4; row++)
      for (let col = 0; col < b.width * 2; col++) {
        g.lineStyle(1, 0xb37c66, 0.55);
        g.strokeRect(x + col * 16 + (row % 2 ? 5 : 0), y + row * 14, 16, 13);
      }
    g.fillStyle(0x5c5549);
    g.fillRect(x, y + 56, w, 7);
    for (let a = 1; a < b.width - 1; a += 2) {
      g.fillStyle(0x644a3b);
      g.fillRect(x + a * 32, y + h - 28, 21, 24);
      g.fillStyle(0xf0cf88);
      g.fillRect(x + a * 32 + 3, y + h - 25, 15, 18);
      g.lineStyle(2, 0x795b40);
      g.lineBetween(x + a * 32 + 10, y + h - 25, x + a * 32 + 10, y + h - 7);
    }
    g.fillStyle(0x67503e);
    g.fillRect(x + w / 2 - 20, y + h - 42, 40, 33);
    g.fillStyle(0xc9ae72);
    g.fillRect(x + w / 2 - 15, y + h - 36, 30, 4);
  }
  for (const d of m.decorations || []) drawObject(g, d);
  if (s.room.kind === "GUILD") {
    // Original wall trophy: crossed practice blades and a bronze compass shield.
    const x = 18 * 32,
      y = 3 * 32;
    g.fillStyle(0x5d5147);
    g.fillRect(x - 39, y - 18, 78, 55);
    g.lineStyle(5, 0xc5b79b);
    g.lineBetween(x - 30, y + 28, x + 29, y - 11);
    g.lineBetween(x - 29, y - 11, x + 30, y + 28);
    g.fillStyle(0xa4874c);
    g.fillCircle(x, y + 7, 16);
    g.fillStyle(0x536e70);
    g.fillCircle(x, y + 7, 10);
    g.lineStyle(2, 0xe4ce93);
    g.strokeTriangle(x, y - 1, x - 6, y + 14, x + 6, y + 14);
  }
}
export function drawObject(
  g: Phaser.GameObjects.Graphics,
  d: {
    kind: string;
    x: number;
    y: number;
    width?: number;
    height?: number;
    solid?: boolean;
  },
) {
  const x = d.x * 32,
    y = d.y * 32,
    w = (d.width || 1) * 32,
    h = (d.height || 1) * 32;
  g.fillStyle(0x192f30, 0.18);
  if (d.kind !== "rug" && d.kind !== "flower" && d.kind !== "moss")
    g.fillEllipse(x + w / 2 + 3, y + h - 2, w * 0.9, 12);
  switch (d.kind) {
    case "rug":
      g.fillStyle(0x7b4b4b);
      g.fillRect(x, y, w, h);
      g.lineStyle(3, 0xd3b678);
      g.strokeRect(x + 6, y + 6, w - 12, h - 12);
      g.lineStyle(1, 0xb18b60);
      for (let z = 12; z < w; z += 16)
        g.lineBetween(x + z, y + 9, x + z, y + h - 9);
      break;
    case "counter":
    case "table":
      g.fillStyle(0x4f4038);
      g.fillRect(x + 2, y + 10, w - 4, h - 8);
      g.fillStyle(0xae7c4d);
      g.fillRect(x, y, w, h - 12);
      g.fillStyle(0xd1a66a);
      g.fillRect(x + 2, y + 2, w - 4, 4);
      g.lineStyle(1, 0x6c4934);
      for (let z = 16; z < w; z += 24)
        g.lineBetween(x + z, y + 5, x + z, y + h - 14);
      if (d.kind === "table") {
        g.fillStyle(0xe2d3a5);
        g.fillRect(x + w / 2 - 9, y + 7, 18, 13);
        g.fillStyle(0x5d6f65);
        g.fillRect(x + 6, y + 8, 7, 8);
      } else {
        for (let z = 25; z < w; z += 61) {
          g.fillStyle(0xdeb77b);
          g.fillRect(x + z, y + 5, 18, 14);
          g.fillStyle(0xebe0bd);
          g.fillRect(x + z + 2, y + 7, 14, 10);
        }
      }
      break;
    case "barrel":
      g.fillStyle(0xa67c4e);
      g.fillRoundedRect(x + 5, y + 3, 23, 27, 6);
      g.lineStyle(2, 0x514a40);
      g.strokeEllipse(x + 16, y + 6, 21, 7);
      g.lineBetween(x + 5, y + 12, x + 28, y + 12);
      g.lineBetween(x + 5, y + 24, x + 28, y + 24);
      g.lineStyle(1, 0xd0a770);
      g.lineBetween(x + 12, y + 9, x + 12, y + 28);
      break;
    case "crate":
      g.fillStyle(0xb08b58);
      g.fillRect(x + 3, y + 6, 27, 24);
      g.lineStyle(2, 0x6a5239);
      g.strokeRect(x + 5, y + 8, 23, 20);
      g.lineBetween(x + 5, y + 8, x + 28, y + 28);
      g.lineBetween(x + 28, y + 8, x + 5, y + 28);
      break;
    case "shelf":
      g.fillStyle(0x584839);
      g.fillRect(x + 1, y - 10, w - 2, 40);
      for (let row = 0; row < 2; row++)
        for (let i = 0; i < 4; i++) {
          g.fillStyle([0x80715d, 0x9f6d5d, 0x6d8981, 0xc4ab72][i]);
          g.fillRect(x + 5 + i * 6, y - 5 + row * 16, 4, 12);
        }
      g.fillStyle(0xc09562);
      g.fillRect(x, y + 9, w, 3);
      break;
    case "board":
      g.fillStyle(0x6b4b36);
      g.fillRect(x, y, w, h);
      g.fillStyle(0xb69d69);
      g.fillRect(x + 4, y + 4, w - 8, h - 8);
      for (let i = 0; i < Math.max(2, w / 24); i++) {
        g.fillStyle(0xe9dcaf);
        g.fillRect(x + 9 + i * 22, y + 11, 14, 25);
        g.lineStyle(1, 0x947e5d);
        g.lineBetween(x + 11 + i * 22, y + 17, x + 20 + i * 22, y + 17);
      }
      break;
    case "tree":
      g.fillStyle(0x846347);
      g.fillRect(x + 12, y, 8, 30);
      g.fillStyle(0x315841);
      g.fillRect(x - 3, y - 20, 37, 28);
      g.fillStyle(0x4e7951);
      g.fillRect(x + 1, y - 29, 30, 27);
      g.fillStyle(0x769661);
      g.fillRect(x + 7, y - 32, 18, 14);
      break;
    case "bush":
    case "moss":
      g.fillStyle(0x4f754d);
      g.fillRoundedRect(x + 2, y + 16, 29, 13, 5);
      g.fillStyle(0x8ba86a);
      g.fillRect(x + 9, y + 13, 12, 6);
      break;
    case "flower":
      g.fillStyle(0x426847);
      g.fillRect(x + 12, y + 13, 3, 14);
      g.fillStyle(0xe7b794);
      g.fillRect(x + 8, y + 10, 12, 5);
      g.fillRect(x + 12, y + 6, 4, 13);
      g.fillStyle(0xf3d292);
      g.fillRect(x + 12, y + 10, 4, 5);
      break;
    case "crystal":
      g.fillStyle(0x51657f);
      g.fillTriangle(x + 5, y + 28, x + 14, y + 1, x + 24, y + 28);
      g.fillStyle(0x9ccac9);
      g.fillTriangle(x + 14, y + 1, x + 14, y + 27, x + 24, y + 28);
      g.fillStyle(0xc9ece0);
      g.fillRect(x + 14, y + 9, 2, 10);
      break;
    case "bones":
      g.lineStyle(3, 0xc9c4a5);
      g.lineBetween(x + 6, y + 24, x + 26, y + 13);
      g.fillStyle(0xddd6b6);
      g.fillRect(x + 6, y + 12, 9, 7);
      break;
    case "banner":
      g.fillStyle(0xb29156);
      g.fillRect(x + 5, y - 6, 23, 4);
      g.fillStyle(0x546d7b);
      g.fillRect(x + 8, y - 2, 17, 27);
      g.fillTriangle(x + 8, y + 25, x + 25, y + 25, x + 16, y + 32);
      g.fillStyle(0xd9c28b);
      g.fillRect(x + 14, y + 6, 5, 10);
      break;
    case "chair":
    case "bench":
      g.fillStyle(0x6f5037);
      g.fillRect(x + 4, y + 13, 24, 15);
      g.fillStyle(0xb78d55);
      g.fillRect(x + 3, y + 9, 26, 7);
      g.fillRect(x + 4, y - 2, 24, 8);
      break;
    case "statue":
      g.fillStyle(0x969d92);
      g.fillRect(x + 9, y - 5, 14, 24);
      g.fillStyle(0xc0c1a5);
      g.fillRect(x + 10, y - 12, 12, 10);
      g.fillStyle(0x747e76);
      g.fillRect(x + 4, y + 20, 25, 11);
      break;
    case "torch":
      g.fillStyle(0x806344);
      g.fillRect(x + 13, y + 7, 5, 21);
      break;
    case "well":
      g.fillStyle(0x6e7873);
      g.fillEllipse(x + 16, y + 17, 31, 24);
      g.fillStyle(0x36515d);
      g.fillEllipse(x + 16, y + 13, 22, 10);
      break;
    default:
      g.fillStyle(0x858c7e);
      g.fillRoundedRect(x + 3, y + 10, 26, 19, 5);
      g.fillStyle(0xadb297);
      g.fillRect(x + 8, y + 9, 14, 5);
  }
}
