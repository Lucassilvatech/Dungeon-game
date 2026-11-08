import manifest from "../../public/assets/characters/manifest.json";
import type Phaser from "phaser";
import type { Appearance } from "./types";
import { fields } from "./types";
export const FRAME_W = manifest.frame_width,
  FRAME_H = manifest.frame_height;
const layers: Record<string, { file: string; mask?: string; sha256: string }> =
  manifest.layers;
const skins: Record<string, string> = manifest.palettes.skin_tone;
const hairColors: Record<string, string> = manifest.palettes.hair_color;
export type Sources = Map<string, HTMLImageElement | HTMLCanvasElement>;
let loading: Promise<Sources> | undefined;
export function loadLayers() {
  return (loading ??= (async () => {
    const result: Sources = new Map();
    await Promise.all(
      Object.entries(layers).flatMap(([id, row]) =>
        [[id, row.file], ...(row.mask ? [[id + "-skin", row.mask]] : [])].map(
          async ([key, file]) => {
            const image = new Image();
            image.src =
              "/assets/characters/" + file + "?v=" + row.sha256.slice(0, 12);
            await image.decode();
            result.set(key, image);
          },
        ),
      ),
    );
    return result;
  })().catch((e) => {
    loading = undefined;
    throw e;
  }));
}
function canvas(w: number, h: number) {
  const c = document.createElement("canvas");
  c.width = w;
  c.height = h;
  return c;
}
function coloured(
  source: HTMLImageElement | HTMLCanvasElement,
  color: string,
  reference: number,
) {
  const c = canvas(source.width, source.height),
    ctx = c.getContext("2d")!;
  ctx.drawImage(source, 0, 0);
  const pixels = ctx.getImageData(0, 0, c.width, c.height),
    p = pixels.data;
  const rgb = [1, 3, 5].map((i) => parseInt(color.slice(i, i + 2), 16));
  for (let i = 0; i < p.length; i += 4) {
    if (!p[i + 3]) continue;
    const shade = (p[i] + p[i + 1] + p[i + 2]) / 3 / reference;
    for (let j = 0; j < 3; j++)
      p[i + j] = Math.min(255, Math.round(rgb[j] * shade));
  }
  ctx.putImageData(pixels, 0, 0);
  return c;
}
/** Source layers stay separate. Only a specific validated appearance is cached as a texture. */
export function composeAppearance(sources: Sources, look: Appearance) {
  const c = canvas(FRAME_W * 8, FRAME_H * 12),
    ctx = c.getContext("2d")!;
  ctx.imageSmoothingEnabled = false;
  const get = (id: string) => {
    const result = sources.get(id);
    if (!result) throw Error("Camada ausente: " + id);
    return result;
  };
  const body = "body-" + look.sexo_visual;
  const draw = (id: string) => ctx.drawImage(get(id), 0, 0);
  draw(body);
  ctx.drawImage(
    coloured(get(body + "-skin"), skins[look.skin_tone] ?? skins.skin_2, 185),
    0,
    0,
  );
  const overBoots = ["skirt", "shorts", "light_greaves"].includes(
    look.appearance_legs,
  );
  if (!overBoots) draw("legs-" + look.appearance_legs);
  draw("feet-" + look.appearance_feet);
  if (overBoots) draw("legs-" + look.appearance_legs);
  draw("torso-" + look.appearance_torso);
  if (!["hood", "cloth_cap", "light_helmet"].includes(look.appearance_head))
    ctx.drawImage(
      coloured(
        get("hair-" + look.hair_style_id),
        hairColors[look.hair_color] ?? hairColors.brown,
        130,
      ),
      0,
      0,
    );
  if (look.appearance_head !== "none") draw("head-" + look.appearance_head);
  return c;
}
export function appearanceKey(look: Appearance) {
  return "appearance:" + fields.map((k) => look[k]).join(":");
}
export function preloadCharacterLayers(scene: Phaser.Scene) {
  for (const [id, row] of Object.entries(layers)) {
    scene.load.image(
      "look:" + id,
      "/assets/characters/" + row.file + "?v=" + row.sha256.slice(0, 12),
    );
    if (row.mask)
      scene.load.image(
        "look:" + id + "-skin",
        "/assets/characters/" + row.mask + "?v=" + row.sha256.slice(0, 12),
      );
  }
}
export function characterTexture(scene: Phaser.Scene, look: Appearance) {
  const key = appearanceKey(look);
  if (scene.textures.exists(key)) return key;
  // Reclaim unused appearances after edits/room transitions, retain all live actors.
  const old = scene.textures
    .getTextureKeys()
    .filter((k) => k.startsWith("appearance:"));
  if (old.length >= 24) {
    const live = new Set(scene.children.list.map((s: any) => s.texture?.key));
    for (const k of old) if (!live.has(k)) scene.textures.remove(k);
  }
  const sources: Sources = new Map();
  for (const [id, row] of Object.entries(layers)) {
    sources.set(
      id,
      scene.textures.get("look:" + id).getSourceImage() as HTMLImageElement,
    );
    if (row.mask)
      sources.set(
        id + "-skin",
        scene.textures
          .get("look:" + id + "-skin")
          .getSourceImage() as HTMLImageElement,
      );
  }
  const texture = scene.textures.addCanvas(
    key,
    composeAppearance(sources, look),
  );
  if (!texture) throw Error("Falha ao montar personagem");
  for (let i = 0; i < 96; i++)
    texture.add(
      i,
      0,
      (i % 8) * FRAME_W,
      Math.floor(i / 8) * FRAME_H,
      FRAME_W,
      FRAME_H,
    );
  texture.setFilter(1); // Phaser NEAREST, without loading Phaser in the creation screen.
  return key;
}

export function npcAppearance(id: string): Appearance {
  const base: Appearance = {
    sexo_visual: "masculino",
    skin_tone: "skin_2",
    hair_style_id: "short_spiky",
    hair_color: "brown",
    appearance_head: "none",
    appearance_torso: "adventurer_tunic",
    appearance_legs: "simple_trousers",
    appearance_feet: "leather_boots",
  };
  const roles: Record<string, Partial<Appearance>> = {
    merchant: {
      hair_style_id: "short_swept",
      appearance_torso: "peasant_shirt",
      appearance_head: "cloth_cap",
    },
    blacksmith: {
      skin_tone: "skin_4",
      hair_style_id: "short_curly",
      appearance_torso: "smith_apron",
      appearance_feet: "heavy_boots",
    },
    alchemist: {
      sexo_visual: "feminino",
      hair_style_id: "ponytail",
      hair_color: "copper",
      appearance_torso: "alchemist_coat",
      appearance_legs: "skirt",
    },
    barber: {
      hair_style_id: "side_swept",
      hair_color: "silver",
      appearance_torso: "peasant_shirt",
      appearance_feet: "simple_shoes",
    },
  };
  return { ...base, ...roles[id] };
}

export function residentAppearance(index: number): Appearance {
  const looks: Partial<Appearance>[] = [
    {
      sexo_visual: "feminino",
      hair_style_id: "bob",
      hair_color: "copper",
      appearance_torso: "peasant_shirt",
      appearance_legs: "skirt",
    },
    {
      hair_style_id: "short_swept",
      skin_tone: "skin_4",
      appearance_torso: "leather_armor",
    },
    {
      sexo_visual: "feminino",
      hair_style_id: "braid",
      hair_color: "black",
      appearance_torso: "peasant_shirt",
    },
    {
      hair_style_id: "short_curly",
      hair_color: "silver",
      appearance_torso: "smith_apron",
    },
  ];
  return { ...npcAppearance("resident"), ...looks[index % looks.length] };
}
