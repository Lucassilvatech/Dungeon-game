/* Visual review sheets rendered by the actual compositor, not game screenshots. */
const { chromium } = require("playwright"),
  fs = require("node:fs"),
  path = require("node:path"),
  assert = require("node:assert/strict");
(async () => {
  const root = path.resolve(__dirname, "../.."),
    catalog = JSON.parse(
      fs.readFileSync(root + "/backend/app/appearance_catalog.json"),
    );
  const browser = await chromium.launch({
    headless: true,
    executablePath: process.env.CHROMIUM_PATH,
    args: ["--no-sandbox"],
  });
  const page = await browser.newPage({ viewport: { width: 760, height: 900 } });
  try {
    await page.goto(process.env.BASE_URL || "http://127.0.0.1:5187");
    for (const [field, name] of [
      ["appearance_head", "head-fit"],
      ["appearance_torso", "clothing-fit"],
      ["appearance_legs", "legs-fit"],
      ["appearance_feet", "feet-fit"],
      ["hair_style_id", "hair-fit"],
    ]) {
      const result = await page.evaluate(
        async ({ field, options }) => {
          const { loadLayers, composeAppearance, npcAppearance } = await import(
            "/src/appearance/compositor.ts"
          );
          const sources = await loadLayers();
          document.body.innerHTML = '<main id="proof"></main>';
          document.body.style =
            "background:#18252a;color:#fff;font:14px monospace;margin:0";
          const records = [];
          for (const [i, option] of options.entries()) {
            const look = {
              ...npcAppearance("player"),
              [field]: option.id,
              sexo_visual: i % 2 ? "feminino" : "masculino",
            };
            if (field === "appearance_head") look.hair_style_id = "ponytail";
            const atlas = composeAppearance(sources, look);
            const row = document.createElement("div");
            row.style =
              "display:flex;align-items:center;gap:12px;padding:12px;background:" +
              (i % 2 ? "#e0c6a3" : "#26343b") +
              ";color:" +
              (i % 2 ? "#29212a" : "#fff");
            const label = document.createElement("span");
            label.style = "width:160px;flex-shrink:0";
            label.textContent = option.label;
            row.append(label);
            const c = document.createElement("canvas");
            c.width = 256;
            c.height = 96;
            c.style = "width:512px;height:192px;image-rendering:pixelated";
            const ctx = c.getContext("2d");
            let opaque = 0;
            for (let d = 0; d < 4; d++) {
              const frame = d * 4;
              ctx.drawImage(
                atlas,
                (frame % 8) * 64,
                Math.floor(frame / 8) * 96,
                64,
                96,
                d * 64,
                0,
                64,
                96,
              );
            }
            for (
              let j = 3, p = ctx.getImageData(0, 0, 256, 96).data;
              j < p.length;
              j += 4
            ) {
              if (p[j] === 255) opaque++;
              else if (p[j] !== 0) throw Error("Nonbinary runtime alpha");
            }
            row.append(c);
            document.querySelector("#proof").append(row);
            records.push({ option: option.id, opaque });
          }
          return records;
        },
        { field, options: catalog.options[field] },
      );
      assert(result.every((r) => r.opaque > 500));
      await page.screenshot({
        path: root + "/artifacts/appearance/" + name + ".png",
        fullPage: true,
      });
    }
    console.log(
      "PASS: every supplied hair/clothing choice composed in four directions on light/dark backgrounds; binary alpha",
    );
  } finally {
    await browser.close();
  }
})();
