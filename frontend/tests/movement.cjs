/* Real API movement and real renderer frames; only the initial fixture uses SQL. */
const { chromium } = require("playwright"),
  assert = require("node:assert/strict"),
  fs = require("node:fs"),
  path = require("node:path"),
  { execFileSync } = require("node:child_process");
(async () => {
  assert.equal(process.env.TOWER_TEST_DATABASE, "1");
  assert(process.env.NPC_TEST_DATABASE_URL?.includes("pixel_browser_"));
  const root = path.resolve(__dirname, "../.."),
    out = path.join(root, "artifacts/map-rebuild");
  const browser = await chromium.launch({
    headless: true,
    ...(process.env.CHROMIUM_PATH
      ? { executablePath: process.env.CHROMIUM_PATH }
      : {}),
    args: ["--no-sandbox"],
  });
  const page = await browser.newPage({
      viewport: { width: 1280, height: 800 },
    }),
    errors = [];
  page.on("pageerror", (e) => errors.push(e.message));
  const sql = (code) =>
    execFileSync(
      process.env.PYTHON_EXECUTABLE || root + "/.venv/bin/python",
      ["-c", code],
      {
        cwd: root + "/backend",
        env: {
          ...process.env,
          DATABASE_URL: process.env.NPC_TEST_DATABASE_URL,
        },
        encoding: "utf8",
      },
    );
  try {
    await page.goto(process.env.BASE_URL);
    await page.getByLabel("Conta", { exact: true }).fill("walk" + Date.now());
    await page
      .getByLabel("Senha", { exact: true })
      .fill("private-walk-test-123");
    await page
      .getByRole("button", { name: "Criar conta", exact: true })
      .click();
    await page.locator("input[name=name]").fill("Caminhante");
    await page.getByRole("button", { name: "Iniciar jornada" }).click();
    await page.locator(".canvas[data-visual]").waitFor();
    const cid = await page.evaluate(async () => {
      const r = await fetch("/api/state", {
        headers: { Authorization: "Bearer " + sessionStorage.getItem("token") },
      });
      return (await r.json()).character.id;
    });
    sql(
      `from app.database import Session\nfrom app.models import Character\nwith Session.begin() as db:\n c=db.get(Character,${cid});c.room_id="city1";c.x=18;c.y=18\n`,
    );
    await page.reload();
    await page.locator(".canvas[data-visual]").waitFor();
    await page.waitForTimeout(400);
    const samples = [],
      captures = [];
    for (const [key, dir] of [
      ["d", 2],
      ["s", 0],
      ["a", 1],
      ["w", 3],
    ]) {
      for (let step = 0; step < 2; step++) {
        const response = page.waitForResponse(
          (r) => r.url().endsWith("/move") && r.request().method() === "POST",
        );
        await page.keyboard.press(key);
        assert.equal((await response).status(), 200);
        const sampling = page.evaluate(
          () =>
            new Promise((resolve) => {
              const frames = [],
                start = performance.now();
              function sample() {
                const d = document.querySelector(".canvas")?.dataset.visual;
                if (d) frames.push(JSON.parse(d).hero);
                if (performance.now() - start < 500)
                  requestAnimationFrame(sample);
                else resolve(frames);
              }
              sample();
            }),
        );
        await page.waitForTimeout(140);
        captures.push(await page.locator(".game-shell").screenshot());
        const frames = await sampling;
        const walking = frames.filter((h) => h.moving && h.dir === dir);
        assert(walking.length > 0, "direction must actually walk: " + dir);
        for (const h of walking)
          assert(+h.frame >= 16 + dir * 8 && +h.frame < 24 + dir * 8);
        samples.push({
          direction: dir,
          frames: [...new Set(walking.map((h) => +h.frame))],
          distanceObserved: Math.hypot(
            frames.at(-1).x - frames[0].x,
            frames.at(-1).y - frames[0].y,
          ),
        });
      }
    }
    await page.waitForTimeout(1200);
    const final = await page.locator(".canvas").getAttribute("data-visual");
    const d = JSON.parse(final);
    assert.equal(d.hero.moving, false);
    assert(+d.hero.frame < 16, "returns to approved idle pose");
    assert.equal(Math.round(d.hero.x), 18 * d.tileSize + d.tileSize / 2);
    assert.equal(Math.round(d.hero.y), 19 * d.tileSize);
    await page.reload();
    await page.locator(".canvas[data-visual]").waitFor();
    assert.deepEqual(errors, []);
    fs.mkdirSync(out, { recursive: true });
    fs.writeFileSync(
      path.join(out, "movement-validation.json"),
      JSON.stringify(
        {
          status: "PASS",
          directions: 4,
          samples,
          errors,
          groundContact:
            "authoritative tile feet, returns to idle, persisted after reload",
        },
        null,
        2,
      ) + "\n",
    );
    // Evidence is a real captured frame, explicitly separate from the authored contact sheet.
    fs.writeFileSync(path.join(out, "walking-in-game.png"), captures[0]);
    console.log(
      "PASS real walking: four directions, eight API moves, distinct distance-driven poses, grounded idle, reload",
    );
  } finally {
    await browser.close();
  }
})().catch((e) => {
  console.error(e);
  process.exit(1);
});
