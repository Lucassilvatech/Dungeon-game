/* Real HTTP/UI, new private PostgreSQL database; SQL is fixture setup and audit only. */
const { chromium } = require("playwright"),
  assert = require("node:assert/strict"),
  fs = require("node:fs"),
  path = require("node:path"),
  { execFileSync } = require("node:child_process");
(async () => {
  assert.equal(process.env.TOWER_TEST_DATABASE, "1");
  assert(process.env.NPC_TEST_DATABASE_URL?.includes("pixel_browser_"));
  const root = path.resolve(__dirname, "../.."),
    out = root + "/artifacts/appearance",
    base = process.env.BASE_URL,
    start = Date.now();
  fs.mkdirSync(out, { recursive: true });
  const env = {
      ...process.env,
      DATABASE_URL: process.env.NPC_TEST_DATABASE_URL,
    },
    python = process.env.PYTHON_EXECUTABLE || root + "/.venv/bin/python";
  const sql = (code) =>
    execFileSync(python, ["-c", code], {
      cwd: root + "/backend",
      env,
      encoding: "utf8",
    }).trim();
  const browser = await chromium.launch({
    headless: true,
    executablePath: process.env.CHROMIUM_PATH,
    args: ["--no-sandbox"],
  });
  const page = await browser.newPage({
      viewport: { width: 1280, height: 900 },
      hasTouch: true,
    }),
    errors = [],
    checks = [];
  page.setDefaultTimeout(30000);
  page.on("pageerror", (e) => errors.push(e.message));
  const name = "look" + Date.now(),
    password = "private-appearance-123";
  let cid, headers;
  const get = async (route) => {
    const r = await page.request.get(base + "/api" + route, { headers });
    assert.equal(r.status(), 200, await r.text());
    return r.json();
  };
  const post = async (route, data) => {
    const r = await page.request.post(base + "/api" + route, { headers, data });
    assert.equal(r.status(), 200, await r.text());
    return r.json();
  };
  const diag = async () =>
    JSON.parse(
      await page.locator(".canvas[data-visual]").getAttribute("data-visual"),
    );
  const waitRoom = async (id) => {
    await page.waitForFunction(
      (id) =>
        JSON.parse(document.querySelector(".canvas")?.dataset.visual || "{}")
          .room === id,
      id,
    );
    await page.waitForTimeout(350);
  };
  const capture = async (name) =>
    page.screenshot({ path: out + "/" + name + ".png", fullPage: true });
  const fixture = async (room, x, y) => {
    sql(
      `from app.database import Session\nfrom app.models import Character\nwith Session.begin() as db:\n c=db.get(Character,${cid});c.room_id=${JSON.stringify(room)};c.x=${x};c.y=${y}`,
    );
    await page.reload();
    await waitRoom(room);
  };
  const tapWorld = async (x, y) => {
    await page.locator(".canvas canvas").scrollIntoViewIfNeeded();
    const d = await diag(),
      box = await page.locator(".canvas canvas").boundingBox();
    await page.mouse.click(box.x + x - d.camera.x, box.y + y - d.camera.y);
  };
  try {
    await page.goto(base);
    await page.getByLabel("Conta", { exact: true }).fill(name);
    await page.getByLabel("Senha", { exact: true }).fill(password);
    await page
      .getByRole("button", { name: "Criar conta", exact: true })
      .click();
    await page.getByLabel("Nome do personagem", { exact: true }).fill("Aurora");
    await page
      .getByLabel("Sexo visual", { exact: true })
      .selectOption("feminino");
    await page
      .getByLabel("Modelo de cabelo", { exact: true })
      .selectOption("short_spiky");
    await page
      .getByLabel("Cor de cabelo", { exact: true })
      .selectOption("copper");
    await page
      .getByLabel("Peito", { exact: true })
      .selectOption("alchemist_coat");
    await page
      .getByLabel("Pernas", { exact: true })
      .selectOption("reinforced_trousers");
    await page.getByLabel("Animar caminhada").check();
    await page.waitForTimeout(350);
    await capture("creation-desktop");
    await page.setViewportSize({ width: 390, height: 844 });
    await capture("creation-mobile");
    assert(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= innerWidth + 1,
      ),
    );
    await page
      .getByRole("button", { name: "Iniciar jornada", exact: true })
      .click();
    await page.locator(".canvas[data-visual]").waitFor();
    headers = {
      Authorization:
        "Bearer " +
        (await page.evaluate(() => sessionStorage.getItem("token"))),
    };
    let s = await get("/state");
    cid = s.character.id;
    assert.equal(s.appearance.sexo_visual, "feminino");
    assert.equal(s.appearance.hair_style_id, "short_spiky");
    assert.equal(s.appearance.appearance_torso, "alchemist_coat");
    const initial = s.appearance,
      attributes = s.attributes,
      inventory = s.inventory;
    await page.reload();
    await page.locator(".canvas[data-visual]").waitFor();
    assert.deepEqual((await get("/state")).appearance, initial);
    assert((await diag()).hero.texture.includes("feminino"));
    checks.push(
      "Creation, unrestricted hair/clothes, four-direction preview, 390px, persisted game texture and reload",
    );
    sql(
      `from app.database import Session\nfrom app import finance,lunar\nwith Session.begin() as db:\n finance.move(db,'treasury','player:${cid}',10,'appearance-browser-funding',amortize=False)\n assert lunar.audit(db)['gap_mg']=='0'`,
    );
    const sites = [
      ["merchant_shop", 25, 10, "Comerciante"],
      ["blacksmith_workshop", 39, 9, "Ferreiro"],
      ["alchemy_laboratory", 38, 29, "Alquimista"],
      ["barber_shop", 17, 30, "Barbeiro"],
    ];
    for (const [room, dx, dy, label] of sites) {
      await page.setViewportSize({ width: 1280, height: 900 });
      await fixture("city1", dx, dy + 1);
      if (room === "barber_shop") await capture("village-desktop");
      await tapWorld(dx * 48 + 24, dy * 48 - 18);
      await waitRoom(room);
      s = await get("/state");
      assert.equal(s.room.safe, true);
      assert.equal(s.map.service_npcs[0].name, label);
      assert.deepEqual((await diag()).placement.violations, []);
      await capture(room + "-desktop");
      // Actual player clicks the service sprite and walks to its authoritative approach.
      await tapWorld(10 * 48 + 24, 9 * 48 - 40);
      await page
        .getByRole("heading", {
          name: room === "barber_shop" ? "Barbeiro" : "Lojas da vila",
          exact: true,
        })
        .waitFor();
      if (room === "barber_shop") break;
      await page.keyboard.press("Escape");
      await page.getByRole("button", { name: /Vila do Alvorecer/ }).click();
      await waitRoom("city1");
      s = await get("/state");
      assert.equal(s.character.x, dx);
      assert.equal(s.character.y, dy + 1);
      checks.push(
        label +
          ": facade entry, safe themed interior, real interaction, matching return door",
      );
    }
    await page
      .getByLabel("Sexo visual", { exact: true })
      .selectOption("masculino");
    await page
      .getByLabel("Modelo de cabelo", { exact: true })
      .selectOption("long_wavy");
    await page.getByLabel("Pernas", { exact: true }).selectOption("skirt");
    await page
      .getByLabel("Tom de pele", { exact: true })
      .selectOption("skin_5");
    await page.getByLabel("Peito", { exact: true }).selectOption("mage_robe");
    await page
      .getByRole("button", { name: "Conferir alteração e preço", exact: true })
      .click();
    await page
      .getByRole("button", { name: "Pagar e salvar aparência", exact: true })
      .waitFor();
    await capture("barber-desktop");
    await page.setViewportSize({ width: 390, height: 844 });
    await capture("barber-mobile");
    assert(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= innerWidth + 1,
      ),
    );
    const response = page.waitForResponse(
      (r) =>
        r.url().endsWith("/appearance/barber/confirm") &&
        r.request().method() === "POST",
    );
    await page
      .getByRole("button", { name: "Pagar e salvar aparência", exact: true })
      .click();
    const paid = await response;
    assert.equal(paid.status(), 200, await paid.text());
    const body = paid.request().postDataJSON();
    await page
      .getByRole("heading", { name: "Barbeiro", exact: true })
      .waitFor({ state: "hidden" });
    s = await get("/state");
    assert.equal(s.appearance.revision, 2);
    assert.equal(s.appearance.sexo_visual, "masculino");
    assert.equal(s.appearance.hair_style_id, "long_wavy");
    assert.equal(s.appearance.appearance_legs, "skirt");
    assert.deepEqual(s.attributes, attributes);
    assert.deepEqual(s.inventory, inventory);
    await post("/appearance/barber/confirm", body);
    await page.reload();
    await waitRoom("barber_shop");
    assert.deepEqual((await get("/state")).appearance, s.appearance);
    assert((await diag()).hero.texture.includes("long_wavy"));
    await capture("appearance-in-game-mobile");
    const audit = JSON.parse(
      sql(
        `import json\nfrom app.database import Session\nfrom app import lunar,finance,models as m\nfrom sqlalchemy import select,func\nwith Session() as db:\n print(json.dumps(dict(gap=lunar.audit(db)['gap_mg'],player=finance.coin_mg(db,'player:${cid}'),barber=finance.coin_mg(db,'npc:barber'),receipts=db.scalar(select(func.count()).select_from(m.WorldEvent).where(m.WorldEvent.kind=='CHARACTER_APPEARANCE_CHANGED')))))`,
      ),
    );
    assert.deepEqual(audit, {
      gap: "0",
      player: 9000,
      barber: 1000,
      receipts: 1,
    });
    checks.push(
      "Paid edit, real 1-small-coin transfer, retry charges once, unchanged equipment/stats, gap=0, mobile and reconnect",
    );
    // Queries never write appearance/cash; a fresh HTTP request is a reload observation.
    await Promise.all(
      Array.from({ length: 8 }, () => get("/character/appearance")),
    );
    assert.equal((await get("/character/appearance")).revision, 2);
    assert.deepEqual(errors, []);
    fs.writeFileSync(
      out + "/browser-validation.json",
      JSON.stringify(
        {
          status: "PASS",
          checks,
          audit,
          browser_errors: errors,
          duration_seconds: (Date.now() - start) / 1000,
        },
        null,
        2,
      ) + "\n",
    );
    console.log("PASS", JSON.stringify(checks), JSON.stringify(audit));
  } catch (e) {
    await capture("failure");
    throw e;
  } finally {
    await browser.close();
  }
})();
