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
    assert.equal(roomA.expedition.status, "ACTIVE");
    assert(
      await page
        .getByRole("button", { name: "✧ AVENTURA", exact: true })
        .isDisabled(),
    );
    assert(await page.locator(".paths button").first().isDisabled());
    const activeId = roomA.expedition.id;
    const rejectedAdventure = await page.evaluate(async () => {
      const r = await fetch("/api/adventure", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: "Bearer " + sessionStorage.getItem("token"),
        },
        body: JSON.stringify({ request_id: crypto.randomUUID() }),
      });
      return r.status;
    });
    assert.equal(rejectedAdventure, 409);
    await page.reload();
    await page.locator("canvas").waitFor();
    await idle();
    assert.equal((await state()).expedition.id, activeId);
    const first = roomA.map.enemies.find((e) => e.spawn_key === "slime");
    await fight(
      page.locator(`.encounters button[data-enemy-id="${first.id}"]`),
    );
    const beforeFlee = await state();
    assert(beforeFlee.expedition.alive_enemies > 0);
    await page
      .getByRole("button", { name: "FUGIR DA AVENTURA", exact: true })
      .click();
    await idle();
    const modal = page.getByRole("dialog");
    await modal.waitFor();
    await modal
      .getByText(beforeFlee.character.xp + " XP", { exact: true })
      .waitFor();
    await shot("flee-confirmation");
    await page.getByRole("button", { name: "CANCELAR", exact: true }).click();
    assert.equal((await state()).expedition.status, "ACTIVE");
    await page
      .getByRole("button", { name: "FUGIR DA AVENTURA", exact: true })
      .click();
    await idle();
    await page
      .getByRole("button", { name: "CONFIRMAR FUGA", exact: true })
      .click();
    await idle();
    const fled = await state();
    assert.equal(fled.room.id, "city1");
    assert.equal(fled.character.xp, 0);
    assert.equal(fled.character.level, beforeFlee.character.level);
    assert.equal(fled.character.coins, beforeFlee.character.coins);
    assert.deepEqual(fled.inventory, beforeFlee.inventory);
    await shot("flee-result");
    for (let i = 0; i < 2 && (await state()).room.kind !== "PROCEDURAL"; i++) {
      await page
        .getByRole("button", { name: "✧ AVENTURA", exact: true })
        .click();
      await idle();
    }
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
    // Manual allocation is available after the real level gain in the first expedition.
    await page
      .getByRole("button", { name: "♙ Personagem", exact: true })
      .click();
    const pointsBefore = (await state()).character.unspent_attribute_points;
    assert(pointsBefore >= 1);
    const defenseBefore = (await state()).character.defense;
    await page.getByLabel("Pontos em Defesa", { exact: true }).fill("1");
    await page
      .getByRole("button", { name: "CONFIRMAR ATRIBUTOS", exact: true })
      .click();
    await idle();
    assert.equal((await state()).character.defense, defenseBefore + 1);
    assert.equal(
      (await state()).character.unspent_attribute_points,
      pointsBefore - 1,
    );
    await shot("attributes");
    await page.getByRole("button", { name: "Fechar menu" }).click();
    const beforeDeath = await state();
    const pendingBeforeDeath = await page.evaluate(
      async () =>
        (
          await (
            await fetch("/api/guild/rewards", {
              headers: {
                Authorization: "Bearer " + sessionStorage.getItem("token"),
              },
            })
          ).json()
        ).total,
    );
    const victim = beforeDeath.map.enemies.find((e) => e.state === "ALIVE");
    await page
      .locator('.encounters button[data-enemy-id="' + victim.id + '"]')
      .click();
    await page
      .getByRole("button", { name: "◇ Defender", exact: true })
      .waitFor();
    for (let i = 0; i < 100 && (await state()).battle; i++) {
      await page
        .getByRole("button", { name: "◇ Defender", exact: true })
        .click();
      await idle();
    }
    const dead = await state();
    assert.equal(dead.room.id, "city1");
    assert(dead.death);
    assert.equal(
      dead.character.coins,
      beforeDeath.character.coins - dead.death.medical_fee,
    );
    assert.equal(dead.character.xp, 0);
    assert.equal(dead.character.level, beforeDeath.character.level);
    assert.equal(dead.death.pending_lost_exact, String(pendingBeforeDeath));
    assert.equal(dead.inventory.length, 1);
    assert.equal(dead.inventory[0].definition, "sword");
    assert(dead.inventory[0].protected);
    assert.deepEqual(
      dead.death.items.map((i) => [i.item_id, i.quantity]).sort(),
      beforeDeath.inventory
        .filter((i) => !i.protected)
        .map((i) => [i.id, i.quantity])
        .sort(),
    );
    await page
      .getByRole("dialog")
      .getByRole("heading", { name: "VOCÊ MORREU", exact: true })
      .waitFor();
    await shot("death-summary");
    await page.reload();
    await page.getByRole("dialog").waitFor();
    assert.equal(
      (await state()).death.death_event_id,
      dead.death.death_event_id,
    );
    await page
      .getByRole("button", { name: "RETORNAR À CIDADE", exact: true })
      .click();
    await idle();
    assert.equal((await state()).death, null);
    await page.getByRole("button", { name: "⚖ Leilão", exact: true }).click();
    await page.locator(".auction-card").first().waitFor();
    assert(
      await page.locator(".auction-card form button").first().isDisabled(),
    );
    await shot("death-auctions");

    // A second real player earns the funds through combat and the receptionist.
    const buyer = await browser.newPage({
      viewport: { width: 1440, height: 1000 },
    });
    buyer.on("pageerror", (e) => errors.push(e.message));
    await buyer.goto(process.env.BASE_URL || "http://127.0.0.1:8080");
    async function buyerApi(path, body) {
      const r = await buyer.evaluate(
        async ({ path, body }) => {
          const response = await fetch("/api" + path, {
            method: body === undefined ? "GET" : "POST",
            headers: {
              "Content-Type": "application/json",
              Authorization: "Bearer " + sessionStorage.getItem("token"),
            },
            body: body === undefined ? undefined : JSON.stringify(body),
          });
          return { status: response.status, data: await response.json() };
        },
        { path, body },
      );
      assert(r.status < 300, JSON.stringify(r));
      return r.data;
    }
    const buyerName = "bidder" + Date.now();
    const credentials = await buyerApi("/auth/register", {
      username: buyerName,
      password: "quality-pass-123",
    });
    await buyer.evaluate(
      (t) => sessionStorage.setItem("token", t),
      credentials.token,
    );
    await buyerApi("/character", { name: buyerName });
    let bs = await buyerApi("/state");
    await buyerApi("/inventory/" + bs.inventory[0].id + "/equip", {});
    async function buyerWalk(tx, ty) {
      const s = await buyerApi("/state"),
        m = s.map,
        start = [s.character.x, s.character.y];
      const blocked = new Set(
        [
          ...m.walls,
          ...m.enemies.filter((e) => e.state !== "DEAD").map((e) => [e.x, e.y]),
          ...(m.npc ? [m.npc] : []),
        ].map((p) => p.join(",")),
      );
      const seen = new Set([start.join(",")]),
        queue = [[start, []]];
      for (let i = 0; i < queue.length; i++) {
        const [[x, y], steps] = queue[i];
        if (Math.abs(x - tx) + Math.abs(y - ty) <= 1) {
          for (const [dx, dy] of steps) await buyerApi("/move", { dx, dy });
          return;
        }
        for (const [dx, dy] of [
          [1, 0],
          [-1, 0],
          [0, 1],
          [0, -1],
        ]) {
          const nx = x + dx,
            ny = y + dy,
            key = [nx, ny].join(",");
          if (
            nx <= 0 ||
            ny <= 0 ||
            nx >= m.width - 1 ||
            ny >= m.height - 1 ||
            seen.has(key) ||
            blocked.has(key)
          )
            continue;
          seen.add(key);
          queue.push([
            [nx, ny],
            [...steps, [dx, dy]],
          ]);
        }
      }
      throw Error("Buyer path unavailable");
    }
    async function buyerExit(x, y) {
      const s = await buyerApi("/state"),
        exit = s.room.exits.find((e) => e.x === x && e.y === y);
      assert(exit);
      await buyerWalk(x, y);
      await buyerApi("/rooms/exits/" + exit.id, {});
    }
    await buyerExit(50, 18);
    bs = await buyerApi("/state");
    const prey = bs.map.enemies.find((e) => e.spawn_key === "slime");
    await buyerWalk(prey.x, prey.y);
    let battle = await buyerApi("/battles", { monster: String(prey.id) });
    while (battle.status === "active")
      battle = await buyerApi("/battles/" + battle.id + "/action", {
        turn: battle.turn,
        action: "attack",
      });
    assert.equal(battle.status, "won");
    await buyerExit(2, 9);
    await buyerExit(9, 7);
    bs = await buyerApi("/state");
    await buyerWalk(...bs.map.npc);
    assert.equal((await buyerApi("/guild/claim", {})).paid, 10);
    const auctions = await buyerApi("/auctions");
    const affordable = auctions.find(
      (a) =>
        dead.death.items.some((i) => i.auction_id === a.id) &&
        BigInt(a.opening_price) <= 10n,
    );
    assert(affordable);
    await buyer.reload();
    await buyer.getByRole("button", { name: "⚖ Leilão", exact: true }).click();
    const input = buyer.getByLabel("Lance no leilão " + affordable.id, {
      exact: true,
    });
    await input.waitFor();
    await input.fill(affordable.opening_price);
    await input
      .locator("xpath=ancestor::form")
      .getByRole("button", { name: "CONFIRMAR LANCE", exact: true })
      .click();
    await buyer.waitForFunction(
      () =>
        document.querySelector("main")?.getAttribute("aria-busy") === "false",
    );
    bs = await buyerApi("/state");
    assert.equal(bs.reserved_gold, affordable.opening_price);
    assert.equal(
      bs.coins_exact,
      String(10n - BigInt(affordable.opening_price)),
    );
    await buyer.screenshot({
      path: path.join(os.tmpdir(), "first-floor-auction-bid.png"),
      fullPage: true,
    });
    await buyer.close();
    assert.deepEqual(errors, []);
    console.log(
      "PASS: expanded city/guild/training, mobile, four-turn combat, death removal/rejection, inventory, guild claim, reconnect, committed expedition, API/exit blocking, flee preview/cancel/penalty, two procedural themes, wandering, manual attributes, persistent death summary, medical debt, auction custody and funded player bidding",
    );
  } finally {
    await browser.close();
  }
})().catch((e) => {
  console.error(e);
  process.exit(1);
});
