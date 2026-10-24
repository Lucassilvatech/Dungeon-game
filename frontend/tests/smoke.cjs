const { chromium } = require("playwright");
const assert = require("node:assert/strict");
const base = process.env.BASE_URL || "http://127.0.0.1:8080";
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
      viewport: { width: 1440, height: 1100 },
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
        () => {
          const combat = document.querySelector(".combat button");
          return combat
            ? !combat.disabled
            : !document.querySelector(".adventure")?.disabled;
        },
        { timeout: 30000 },
      );
    const exitAt = async (x, y) => {
      await idle();
      const s = await state();
      const i = s.room.exits.findIndex((e) => e.x === x && e.y === y);
      assert(i >= 0);
      const response = page.waitForResponse(
        (r) =>
          r.url().includes("/api/rooms/exits/") &&
          r.request().method() === "POST",
      );
      await page.locator(".paths button").nth(i).click();
      assert.equal((await response).status(), 200);
      await idle();
    };
    await page.goto(base);
    await page.getByLabel("Conta", { exact: true }).fill("smoke" + Date.now());
    await page.getByLabel("Senha", { exact: true }).fill("smoke-pass-123");
    await page
      .getByRole("button", { name: "Criar conta", exact: true })
      .click();
    await page.locator("input[name=name]").fill("Hero" + Date.now());
    await page.getByRole("button", { name: "Iniciar jornada" }).click();
    await page.locator("canvas").waitFor();
    await page.waitForTimeout(700);
    assert.equal((await state()).room.id, "city1");
    await page.getByRole("button", { name: "▣ Inventário" }).click();
    await page.getByRole("button", { name: "Equipar", exact: true }).click();
    await page.getByRole("button", { name: "Equipada", exact: true }).waitFor();
    await page.getByRole("button", { name: "Fechar menu" }).click();
    const screenshot =
      process.env.SMOKE_SCREENSHOT ||
      require("node:path").join(
        require("node:os").tmpdir(),
        "tower-phase2-city.png",
      );
    await page.screenshot({ path: screenshot, fullPage: true });
    await exitAt(9, 7);
    assert.equal((await state()).room.id, "guild");
    await page.screenshot({
      path: require("node:path").join(
        require("node:os").tmpdir(),
        "tower-phase2-guild.png",
      ),
      fullPage: true,
    });
    await page
      .getByRole("button", { name: "Conversar / curar", exact: true })
      .click();
    await idle();
    assert.equal((await state()).character.hp, 30);
    await exitAt(13, 5);
    assert.equal((await state()).room.id, "training");
    await page.screenshot({
      path: require("node:path").join(
        require("node:os").tmpdir(),
        "tower-phase2-training.png",
      ),
      fullPage: true,
    });
    await page
      .getByRole("button", { name: "⚔ Treinar no boneco", exact: true })
      .click();
    await page
      .getByRole("button", { name: "⚔ Atacar", exact: true })
      .waitFor();
    for (let i = 0; i < 2; i++) {
      await page
        .getByRole("button", { name: "⚔ Atacar", exact: true })
        .click();
      await idle();
    }
    assert.equal((await state()).battle, null);
    assert.equal((await state()).character.xp, 0);
    await exitAt(2, 9);
    await exitAt(2, 9);
    assert.equal((await state()).room.id, "city1");
    await exitAt(26, 10);
    assert.equal((await state()).room.id, "common_a");
    // Actual keyboard input goes through Phaser and the authoritative move endpoint.
    await page.locator("canvas").click({ position: { x: 10, y: 10 } });
    await idle();
    const response = page.waitForResponse((r) => r.url().endsWith("/api/move"));
    await page.keyboard.press("ArrowRight");
    assert.equal((await response).status(), 200);
    await idle();
    await page
      .getByRole("button", { name: "⚔ Enfrentar slime", exact: true })
      .click();
    await page
      .getByRole("button", { name: "⚔ Atacar", exact: true })
      .waitFor();
    for (let i = 0; i < 2; i++) {
      await page
        .getByRole("button", { name: "⚔ Atacar", exact: true })
        .click();
      await idle();
    }
    assert(
      (await state()).inventory.some((i) => i.name === "Cristal da clareira"),
    );
    await page.getByRole("button", { name: "✧ AVENTURA", exact: true }).click();
    await idle();
    if ((await state()).room.kind !== "PROCEDURAL") {
      await page
        .getByRole("button", { name: "✧ AVENTURA", exact: true })
        .click();
      await idle();
    }
    assert.equal((await state()).room.kind, "PROCEDURAL");
    const before = await state();
    await page.reload();
    await page.locator("canvas").waitFor();
    await idle();
    const after = await state();
    assert.equal(after.room.id, before.room.id);
    assert.deepEqual(after.inventory, before.inventory);
    // The room socket must upgrade through Nginx and emit authenticated presence.
    const presence = await page.evaluate(
      () =>
        new Promise((resolve, reject) => {
          const ws = new WebSocket(
            `${location.protocol === "https:" ? "wss" : "ws"}://${location.host}/api/ws/rooms`,
          );
          const timer = setTimeout(() => {
            ws.close();
            reject(Error("Presence timeout"));
          }, 5000);
          ws.onopen = () =>
            ws.send(JSON.stringify({ token: sessionStorage.getItem("token") }));
          ws.onmessage = (e) => {
            clearTimeout(timer);
            ws.close();
            resolve(JSON.parse(e.data));
          };
          ws.onerror = () => reject(Error("WebSocket failed"));
        }),
    );
    assert.equal(presence.room_id, after.room.id);
    await exitAt(2, 9); // procedural -> bosque
    await exitAt(14, 5); // trilha
    await exitAt(14, 5); // clareira
    await exitAt(14, 5); // santuário
    assert.equal((await state()).battle, null);
    await page
      .getByRole("button", { name: "⚔ Chefe do andar", exact: true })
      .click();
    await page.getByText("CHEFE DO ANDAR", { exact: true }).waitFor();
    await page.getByRole("button", { name: "Criar raid", exact: true }).click();
    await idle();
    assert((await state()).raid.invite);
    await page.getByRole("button", { name: "Fechar menu" }).click();
    await page
      .getByRole("button", { name: "⚔ Chefe do andar", exact: true })
      .click();
    await page
      .getByRole("button", { name: "Entrar mesmo assim · solo", exact: true })
      .click();
    await page
      .getByRole("button", { name: "⚔ Atacar", exact: true })
      .waitFor();
    for (let i = 0; i < 5; i++) {
      await page
        .getByRole("button", { name: "⚔ Atacar", exact: true })
        .click();
      await idle();
    }
    assert.equal((await state()).unlocked_floor, 2);
    await page.reload();
    await page.locator("canvas").waitFor();
    await idle();
    assert((await state()).raid.participants.length === 1);
    assert.deepEqual(errors, []);
    console.log(
      "PASS: city, original animated sprites, click pathfinding, guild, NPC, training without farming, keyboard, combat, procedural adventure, persistence, WebSocket proxy, boss warning, raid formation and global floor unlock",
    );
  } finally {
    await browser.close();
  }
})().catch((e) => {
  console.error(e);
  process.exit(1);
});
