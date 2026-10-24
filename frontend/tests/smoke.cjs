const { chromium } = require("playwright");
const assert = require("node:assert/strict");
const path = require("node:path"),
  os = require("node:os");
(async () => {
  const browser = await chromium.launch({
    ...(process.env.CHROMIUM_PATH
      ? { executablePath: process.env.CHROMIUM_PATH }
      : {}),
    headless: true,
    args: ["--no-sandbox"],
  });
  try {
    const page = await browser.newPage({
      viewport: { width: 1440, height: 1000 },
    });
    page.setDefaultTimeout(30000);
    const errors = [];
    page.on("pageerror", (e) => errors.push(e.message));
    const state = () =>
      page.evaluate(async () => {
        const r = await fetch("/api/state", {
          headers: {
            Authorization: "Bearer " + sessionStorage.getItem("token"),
          },
        });
        return r.json();
      });
    const idle = () =>
      page.waitForFunction(
        () =>
          document.querySelector("main")?.getAttribute("aria-busy") === "false",
      );
    const shot = (name) =>
      page.screenshot({
        path: path.join(os.tmpdir(), "first-floor-" + name + ".png"),
        fullPage: true,
      });
    const exitAt = async (x, y) => {
      await idle();
      const s = await state(),
        i = s.room.exits.findIndex((e) => e.x === x && e.y === y);
      assert(i >= 0);
      const response = page.waitForResponse(
        (r) =>
          r.url().includes("/rooms/exits/") && r.request().method() === "POST",
      );
      await page.locator(".paths button").nth(i).click();
      assert.equal((await response).status(), 200);
      await idle();
    };
    async function fight(button) {
      await idle();
      const before = await state();
      await button.click();
      await page
        .getByRole("button", { name: "⚔ Atacar", exact: true })
        .waitFor();
      let turns = 0,
        b;
      do {
        await page
          .getByRole("button", { name: "⚔ Atacar", exact: true })
          .click();
        await idle();
        turns++;
        b = (await state()).battle;
      } while (b && turns < 20);
      assert(!b, "Encounter did not finish");
      return turns;
    }
    await page.goto(process.env.BASE_URL || "http://127.0.0.1:8080");
    await page
      .getByLabel("Conta", { exact: true })
      .fill("quality" + Date.now());
    await page.getByLabel("Senha", { exact: true }).fill("quality-pass-123");
    await page
      .getByRole("button", { name: "Criar conta", exact: true })
      .click();
    await page.locator("input[name=name]").fill("Explorer" + Date.now());
    await page.getByRole("button", { name: "Iniciar jornada" }).click();
    await page.locator("canvas").waitFor();
    await page.waitForTimeout(500);
    let s = await state();
    assert(
      s.map.width >= 50 &&
        s.map.monsters &&
        Object.keys(s.map.monsters).length === 0,
    );
    assert(!s.map.npc);
    await page.getByRole("button", { name: "▣ Inventário" }).click();
    await page.getByRole("button", { name: "Equipar", exact: true }).click();
    await page.getByRole("button", { name: "Equipada", exact: true }).waitFor();
    await page.getByRole("button", { name: "Fechar menu" }).click();
    await shot("city");
    await page.setViewportSize({ width: 390, height: 844 });
    await page.waitForTimeout(300);
    assert(
      await page.evaluate(() => document.body.scrollWidth <= innerWidth + 1),
    );
    await shot("mobile");
    await page.setViewportSize({ width: 1440, height: 1000 });
    await exitAt(9, 7);
    s = await state();
    assert.equal(s.room.id, "guild");
    assert.equal(s.map.npc_name, "Recepcionista da Guilda");
    await shot("guild");
    await page
      .getByRole("button", { name: "Falar com recepcionista", exact: true })
      .click();
    await idle();
    await page.getByRole("button", { name: "RESGATAR RECOMPENSAS" }).waitFor();
    assert(
      await page
        .getByRole("button", { name: "RESGATAR RECOMPENSAS" })
        .isDisabled(),
    );
    await page.getByRole("button", { name: "Fechar menu" }).click();
    await exitAt(35, 10);
    assert.equal((await state()).room.kind, "TRAINING");
    await shot("training");
    assert.equal(
      await fight(
        page.getByRole("button", { name: "⚔ Treinar no boneco", exact: true }),
      ),
      4,
    );
    s = await state();
    assert.equal(s.character.xp, 0);
    assert(!s.map.enemies.some((e) => e.state === "ALIVE"));
    assert.equal(s.inventory.length, 1);
    await page
      .getByRole("button", { name: "Novo exercício", exact: true })
      .click();
    await idle();
    assert((await state()).map.enemies.some((e) => e.state === "ALIVE"));
    await exitAt(2, 9);
    await exitAt(2, 9);
    await exitAt(50, 18);
    s = await state();
    assert.equal(s.room.id, "common_a");
    assert(!s.map.npc && s.map.enemies.length >= 3);
    const target = s.map.enemies.find((e) => e.spawn_key === "slime"),
      selector = `.encounters button[data-enemy-id="${target.id}"]`;
    const turns = await fight(page.locator(selector));
    assert.equal(turns, 4);
    await page.waitForTimeout(850);
    assert.equal(await page.locator(selector).count(), 0);
    const after = await state();
    assert.equal(
      after.map.enemies.find((e) => e.id === target.id).state,
      "DEAD",
    );
    assert.equal(after.character.coins, 0);
    const rejected = await page.evaluate(async (id) => {
      const r = await fetch("/api/battles", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: "Bearer " + sessionStorage.getItem("token"),
        },
        body: JSON.stringify({ monster: String(id) }),
      });
      return r.status;
    }, target.id);
    assert.equal(rejected, 409);
    await page.getByRole("button", { name: "▣ Inventário" }).click();
    await page
      .locator(".item")
      .filter({ hasText: "Cristal da clareira" })
      .waitFor();
    await shot("inventory");
    await page.getByRole("button", { name: "Fechar menu" }).click();
    await page.reload();
    await page.locator("canvas").waitFor();
    await idle();
    assert.equal(
      (await state()).map.enemies.find((e) => e.id === target.id).state,
      "DEAD",
    );
    await exitAt(2, 9);
    await exitAt(9, 7);
    await page
      .getByRole("button", { name: "Falar com recepcionista", exact: true })
      .click();
    await idle();
    await page.getByRole("button", { name: "RESGATAR RECOMPENSAS" }).click();
    await idle();
    assert.equal((await state()).character.coins, 10);
    assert(
      await page
        .getByRole("button", { name: "RESGATAR RECOMPENSAS" })
        .isDisabled(),
    );
    await shot("receipt");
    await page.getByRole("button", { name: "Fechar menu" }).click();
    await page.getByRole("button", { name: "Descansar", exact: true }).click();
    await idle();
    await exitAt(2, 9);
    // A secret discovery can consume one action, so allow a second attempt to reach procedural content.
    for (let i = 0; i < 2 && (await state()).room.kind !== "PROCEDURAL"; i++) {
      await page
        .getByRole("button", { name: "✧ AVENTURA", exact: true })
        .click();
      await idle();
    }
    const roomA = await state();
    assert.equal(roomA.room.kind, "PROCEDURAL");
    await shot("procedural-a");
    await page.getByRole("button", { name: "✧ AVENTURA", exact: true }).click();
    await idle();
    const roomB = await state();
    assert.equal(roomB.room.kind, "PROCEDURAL");
    assert.notEqual(roomA.room.id, roomB.room.id);
    assert.notEqual(roomA.map.theme, roomB.map.theme);
    await shot("procedural-b");
    // Observe authoritative wandering on an idle living instance.
    const positions = roomB.map.enemies.map((e) => [e.id, e.x, e.y]);
    let wandered = false;
    for (let i = 0; i < 6; i++) {
      await page.waitForTimeout(1500);
      const next = await state();
      if (
        next.map.enemies.some((e) =>
          positions.some(
            (p) => p[0] === e.id && (p[1] !== e.x || p[2] !== e.y),
          ),
        )
      ) {
        wandered = true;
        break;
      }
    }
    assert(wandered, "No enemy wandered during the observation window");
    assert.deepEqual(errors, []);
    console.log(
      "PASS: expanded city/guild/training, mobile, four-turn combat, death removal/rejection, inventory, guild claim, reconnect, two distinct procedural themes and authoritative wandering",
    );
  } finally {
    await browser.close();
  }
})().catch((e) => {
  console.error(e);
  process.exit(1);
});
