const { chromium } = require("playwright"),
  assert = require("node:assert/strict"),
  { execFileSync } = require("node:child_process"),
  path = require("node:path"),
  fs = require("node:fs");
(async () => {
  assert.equal(process.env.TOWER_TEST_DATABASE, "1");
  assert(
    process.env.NPC_TEST_DATABASE_URL,
    "Explicit disposable HTTP database required",
  );
  const root = path.resolve(__dirname, "../.."),
    base = process.env.BASE_URL || "http://127.0.0.1:8085",
    name = "npc" + Date.now(),
    password = "private-npc-test-123",
    env = { ...process.env, DATABASE_URL: process.env.NPC_TEST_DATABASE_URL },
    python =
      process.env.PYTHON_EXECUTABLE ||
      (fs.existsSync(root + "/.venv/bin/python")
        ? root + "/.venv/bin/python"
        : "python");
  const sql = (code) =>
      execFileSync(python, ["-c", code], {
        cwd: root + "/backend",
        env,
        encoding: "utf8",
      }).trim(),
    cli = (role) =>
      execFileSync(
        python,
        [
          "-m",
          "app.admin_cli",
          name,
          role,
          "--reason",
          "Private live NPC worker browser verification; role revoked finally",
        ],
        { cwd: root + "/backend", env, stdio: "pipe" },
      );
  const browser = await chromium.launch({
      headless: true,
      ...(process.env.CHROMIUM_PATH
        ? { executablePath: process.env.CHROMIUM_PATH }
        : {}),
      args: ["--no-sandbox"],
    }),
    admin = await browser.newPage({ viewport: { width: 1440, height: 1000 } }),
    player = await browser.newPage({ viewport: { width: 1440, height: 1000 } }),
    errors = [];
  let granted = false;
  for (const p of [admin, player]) {
    p.setDefaultTimeout(45000);
    p.on("pageerror", (e) => errors.push(e.message));
    p.on("dialog", (d) => {
      errors.push("Unexpected native dialog");
      d.dismiss();
    });
  }
  try {
    let r = await player.request.post(base + "/api/auth/register", {
      data: { username: name, password },
    });
    assert.equal(r.status(), 201);
    const token = (await r.json()).token,
      ph = { Authorization: "Bearer " + token };
    r = await player.request.post(base + "/api/character", {
      headers: ph,
      data: { name },
    });
    assert.equal(r.status(), 201);
    const cid = (await r.json()).character.id;
    cli("owner");
    granted = true;
    await admin.goto(base + "/admin");
    await admin.getByLabel("Conta administrativa", { exact: true }).fill(name);
    await admin.getByLabel("Senha", { exact: true }).fill(password);
    await admin
      .getByRole("button", { name: "Entrar na Central", exact: true })
      .click();
    await admin
      .getByRole("button", { name: "Economia dos NPCs", exact: true })
      .click();
    await admin
      .getByRole("heading", { name: "Economia dos NPCs", exact: true })
      .waitFor();
    const ah = {
      Authorization:
        "Bearer " +
        (await admin.evaluate(() => sessionStorage.getItem("admin_token"))),
    };
    const get = async (p, headers = ah) => {
      const x = await admin.request.get(base + "/api" + p, { headers });
      assert.equal(x.status(), 200, await x.text());
      return x.json();
    };
    const op = async (action, target, params) => {
      let x = await admin.request.post(base + "/api/admin/operations/preview", {
        headers: ah,
        data: {
          operation_id: crypto.randomUUID(),
          action,
          target,
          params,
          reason: "Explicit private browser fixture using only existing cash",
        },
      });
      assert.equal(x.status(), 200, await x.text());
      const p = await x.json();
      x = await admin.request.post(
        base + "/api/admin/operations/" + p.id + "/confirm",
        {
          headers: ah,
          data: { confirmed: true, confirmation_token: p.confirmation_token },
        },
      );
      assert.equal(x.status(), 200, await x.text());
      return x.json();
    };
    const overview = () => get("/admin/npc-economy"),
      find = (d, id) => d.npcs.find((n) => n.id === id),
      stock = (n, id) =>
        Number(n.items.find((i) => i.definition_id === id)?.stock || 0);
    let d = await overview();
    assert.equal(stock(find(d, "alchemist"), "herb"), 7);
    assert.equal(stock(find(d, "alchemist"), "weak_healing_potion"), 1);
    assert.equal(stock(find(d, "blacksmith"), "ore"), 90);
    assert.equal(find(d, "merchant").stock_items.length, 0);
    await op("guild.item_prices", "herb", { buy_price_units: 2 });
    await op("royal.transfer_coins", "treasury", {
      destination: "player:" + cid,
      amount_units: 5000,
    });
    sql(
      `from app.database import Session\nfrom app import models as m\nwith Session.begin() as db:\n for definition,qty in [('herb',80),('crystal',80),('ore',90)]:\n  i=m.Item(owner=None,definition=definition,quantity=qty,location='npc');db.add(i);db.flush();db.add(m.NPCStock(item_id=i.id,account_id='guild',sale_weight_mg=0))`,
    );
    const confirm = async () => {
      const panel = admin.getByRole("region", {
        name: "Prévia da economia NPC",
        exact: true,
      });
      await panel.waitFor();
      await panel.getByLabel("Confirmar impacto NPC", { exact: true }).check();
      const done = admin.waitForResponse(
        (r) => r.url().endsWith("/confirm") && r.request().method() === "POST",
      );
      await panel
        .getByRole("button", { name: "Confirmar operação NPC", exact: true })
        .click();
      const response = await done;
      assert.equal(response.status(), 200, await response.text());
      await panel.waitFor({ state: "hidden" });
      return response.json();
    };
    const edit = async (name) => {
      await admin
        .getByRole("button", { name: "Configurar " + name, exact: true })
        .click();
      await admin
        .getByRole("group", { name: "Configuração de " + name, exact: true })
        .waitFor();
    };
    const save = async () => {
      await admin
        .getByLabel("Justificativa da configuração", { exact: true })
        .fill("Alteração consciente da cadeia fechada no banco privado");
      await admin
        .getByRole("button", { name: "Revisar configuração NPC", exact: true })
        .click();
      return confirm();
    };
    await edit("Alquimista");
    await admin
      .getByRole("button", { name: "Revisar configuração NPC", exact: true })
      .click();
    await admin
      .getByRole("alert")
      .filter({ hasText: "pelo menos 10" })
      .waitFor();
    await admin.getByLabel("Produção ativa", { exact: true }).check();
    await save();
    // Real HTTP server worker, not a browser call to tick or a simulated producer.
    async function until(test) {
      for (let i = 0; i < 30; i++) {
        const current = await overview();
        if (test(current)) return current;
        await admin.waitForTimeout(500);
      }
      throw Error("Real NPC worker did not reach expected persistent state");
    }
    d = await until(
      (d) => stock(find(d, "alchemist"), "weak_healing_potion") === 2,
    );
    assert.equal(stock(find(d, "alchemist"), "herb"), 0);
    assert.equal(stock(find(d, "alchemist"), "crystal"), 0);
    await edit("Ferreiro");
    await admin.getByLabel("Produção ativa", { exact: true }).check();
    await save();
    d = await until((d) => stock(find(d, "blacksmith"), "moss_boots") === 2);
    assert.equal(stock(find(d, "blacksmith"), "ore"), 0);
    assert.equal(stock(find(d, "blacksmith"), "moss_ingot"), 0);
    assert.equal(
      find(d, "blacksmith")
        .items.filter((i) => i.recipe && i.definition_id !== "moss_ingot")
        .every((i) => i.stock === "2"),
      true,
    );
    // Finance the producer using the existing Royal transfer action from this panel.
    await admin
      .getByLabel("Caixa destinatário", { exact: true })
      .selectOption("npc:alchemist");
    await admin.getByLabel("Valor para financiar", { exact: true }).fill("500");
    await admin
      .getByLabel("Justificativa do financiamento", { exact: true })
      .fill("Capital real transferido do Tesouro para compra de materiais");
    await admin
      .getByRole("button", { name: "Revisar financiamento", exact: true })
      .click();
    await confirm();
    await admin
      .getByLabel("Justificativa da transferência", { exact: true })
      .fill("Mercadoria existente da Guilda para abastecer o Comerciante");
    for (const id of ["herb", "crystal", "ore"]) {
      await admin
        .getByLabel("Origem do estoque", { exact: true })
        .selectOption("guild");
      await admin
        .getByLabel("Destino do estoque", { exact: true })
        .selectOption("merchant");
      await admin
        .getByLabel("Material existente", { exact: true })
        .selectOption(id);
      await admin
        .getByLabel("Quantidade de material", { exact: true })
        .fill("30");
      await admin
        .getByRole("button", {
          name: "Revisar transferência material",
          exact: true,
        })
        .click();
      await confirm();
    }
    await edit("Alquimista");
    await admin.getByLabel("Compras ativas", { exact: true }).check();
    await save();
    d = await until(
      (d) =>
        stock(find(d, "alchemist"), "herb") === 10 &&
        stock(find(d, "alchemist"), "crystal") === 10,
    );
    assert.equal(stock(find(d, "merchant"), "herb"), 20);
    assert.equal(stock(find(d, "merchant"), "crystal"), 20);
    const near = (id) =>
      sql(
        `from app.database import Session\nfrom app import models as m\nfrom app.npc_economy import SERVICES\nwith Session.begin() as db:\n s=next(s for s in SERVICES if s['id']=='${id}');c=db.get(m.Character,${cid});c.room_id='city1';c.x=s['x'];c.y=s['y']+1`,
      );
    await player.addInitScript(
      (t) => sessionStorage.setItem("token", t),
      token,
    );
    near("merchant");
    await player.goto(base);
    await player.locator("canvas").waitFor();
    await player
      .getByRole("button", { name: "⚒ Lojas da vila", exact: true })
      .click();
    await player
      .getByRole("heading", { name: "Loja · Comerciante", exact: true })
      .waitFor();
    const leaf = player.getByRole("article", {
      name: "Comprar Folha Luminosa",
      exact: true,
    });
    await leaf.getByText("Custo total: 21", { exact: true }).waitFor();
    assert.equal(await leaf.getByRole("textbox").inputValue(), "10");
    async function purchase(card) {
      await card.getByRole("button", { name: /^Comprar / }).click();
      const modal = player.getByRole("dialog", {
        name: "Confirmar compra",
        exact: true,
      });
      await modal
        .getByRole("button", { name: "Confirmar compra", exact: true })
        .click();
      await modal.waitFor({ state: "hidden" });
    }
    await purchase(leaf);
    let wallet = await get("/lunar/wallet", ph);
    assert.equal(wallet.coin_total_weight_mg, "4979000");
    d = await until((d) => stock(find(d, "merchant"), "herb") === 10);
    await admin
      .getByLabel("Material existente", { exact: true })
      .selectOption("herb");
    await admin
      .getByLabel("Quantidade de material", { exact: true })
      .fill("20");
    await admin
      .getByRole("button", {
        name: "Revisar transferência material",
        exact: true,
      })
      .click();
    await confirm();
    await edit("Comerciante");
    await admin
      .getByLabel("Lote mínimo de Folha Luminosa", { exact: true })
      .fill("20");
    await admin
      .getByLabel("Passo do lote de Folha Luminosa", { exact: true })
      .fill("20");
    await save();
    await leaf
      .getByText("Lote mínimo: 20 · múltiplos de 20", { exact: true })
      .waitFor();
    await leaf.getByText("Custo total: 41", { exact: true }).waitFor();
    assert.equal(await leaf.getByRole("textbox").inputValue(), "20");
    await leaf
      .getByRole("button", { name: "Comprar Folha Luminosa", exact: true })
      .click();
    await edit("Comerciante");
    await admin.getByLabel("Margem fixa", { exact: true }).fill("3");
    await save();
    let modal = player.getByRole("dialog", {
      name: "Confirmar compra",
      exact: true,
    });
    await modal
      .getByRole("button", { name: "Confirmar compra", exact: true })
      .click();
    await modal
      .getByText(
        "O preço ou estoque mudou. Confira os novos valores antes de confirmar.",
        { exact: true },
      )
      .waitFor();
    assert.equal(
      (await get("/lunar/wallet", ph)).coin_total_weight_mg,
      "4979000",
    );
    await modal.getByText("43 unidades monetárias", { exact: false }).waitFor();
    await modal
      .getByRole("button", { name: "Confirmar compra", exact: true })
      .click();
    await modal.waitFor({ state: "hidden" });
    assert.equal(
      (await get("/lunar/wallet", ph)).coin_total_weight_mg,
      "4936000",
    );
    // Price propagation uses the persisted market revision everywhere.
    d = await overview();
    const oldRevision = d.market.revision,
      oldSword = d.market.prices.moss_sword;
    await op("guild.item_prices", "ore", { buy_price_units: 12 });
    await edit("Alquimista");
    await admin.getByLabel("Fator Alquimia", { exact: true }).fill("1,35");
    await admin.getByLabel("Produção ativa", { exact: true }).uncheck();
    await save();
    d = await overview();
    assert(d.market.revision > oldRevision);
    assert(BigInt(d.market.prices.moss_sword) > BigInt(oldSword));
    assert.equal(d.market.prices.weak_healing_potion, "19");
    near("alchemist");
    await player.reload();
    await player.locator("canvas").waitFor();
    await player
      .getByRole("button", { name: "⚒ Lojas da vila", exact: true })
      .click();
    await player
      .getByRole("button", { name: "Alquimista", exact: true })
      .click();
    const potion = player.getByRole("article", {
      name: "Comprar Poção de Cura Fraca",
      exact: true,
    });
    await potion.getByRole("textbox").fill("2");
    await potion.getByText("Custo total: 38", { exact: true }).waitFor();
    await purchase(potion);
    await potion.waitFor({ state: "hidden" });
    assert.equal(
      (await get("/economy/npcs/alchemist/shop", ph)).buy.some(
        (i) => i.definition_id === "weak_healing_potion",
      ),
      false,
    );
    // Every armour piece is a distinct physical item and independently equipable.
    near("blacksmith");
    await player.reload();
    await player.locator("canvas").waitFor();
    await player
      .getByRole("button", { name: "⚒ Lojas da vila", exact: true })
      .click();
    await player.getByRole("button", { name: "Ferreiro", exact: true }).click();
    for (const label of [
      "Espada de Musgo",
      "Capacete de Musgo",
      "Peitoral de Musgo",
      "Luvas de Musgo",
      "Calças de Musgo",
      "Botas de Musgo",
    ])
      await purchase(
        player
          .getByRole("article", { name: "Comprar " + label, exact: true })
          .first(),
      );
    await player.getByRole("button", { name: /^▣ Inventário/ }).click();
    for (const label of [
      "Espada de Musgo",
      "Capacete de Musgo",
      "Peitoral de Musgo",
      "Luvas de Musgo",
      "Calças de Musgo",
      "Botas de Musgo",
    ]) {
      const item = player.locator(".item").filter({ hasText: label }).first();
      await item.getByRole("button", { name: "Equipar", exact: true }).click();
      await item
        .getByRole("button", { name: "Desequipar", exact: true })
        .waitFor();
    }
    let s = await get("/state", ph);
    const equipped = s.inventory.filter(
      (i) => i.equipped && i.definition.startsWith("moss_"),
    );
    assert.equal(equipped.length, 6);
    assert.equal(new Set(equipped.map((i) => i.equipment_slot)).size, 6);
    await player.setViewportSize({ width: 390, height: 844 });
    await admin.setViewportSize({ width: 390, height: 844 });
    await player
      .getByRole("button", { name: "⚒ Lojas da vila", exact: true })
      .click();
    await player.getByRole("button", { name: "Ferreiro", exact: true }).click();
    for (const p of [player, admin])
      assert(
        await p.evaluate(
          () => document.documentElement.scrollWidth <= innerWidth + 1,
        ),
        "No390px page overflow",
      );
    if (process.env.NPC_SCREENSHOTS) {
      fs.mkdirSync(process.env.NPC_SCREENSHOTS, { recursive: true });
      await player.screenshot({
        path: path.join(process.env.NPC_SCREENSHOTS, "npc-shop-mobile.png"),
        fullPage: true,
      });
      await admin.screenshot({
        path: path.join(process.env.NPC_SCREENSHOTS, "npc-admin-mobile.png"),
        fullPage: true,
      });
    }
    const before = await get("/economy/npcs", ph);
    sql("from app.seed import seed\nseed()\nseed()");
    const after = await get("/economy/npcs", ph);
    const projection = (rows) =>
      rows.map((n) => ({
        id: n.id,
        items: n.items.map((i) => ({
          id: i.definition_id,
          stock: i.stock,
          capacity: i.capacity,
          lot: i.minimum_lot_size,
          step: i.order_step,
        })),
        wallet: n.wallet,
        factors: n.factors,
        margin: n.fixed_margin,
      }));
    assert.deepEqual(projection(after), projection(before));
    const audit = await get("/admin/lunar/audit");
    assert.equal(audit.gap_mg, "0");
    assert.deepEqual(audit.ledger_mismatches, []);
    assert.deepEqual(audit.metadata_mismatches, []);
    assert.deepEqual(errors, []);
    if (process.env.NPC_RESTART_AUTH) {
      fs.writeFileSync(
        process.env.NPC_RESTART_AUTH,
        JSON.stringify({ token, projection: projection(after) }),
        { mode: 0o600 },
      );
    }
    console.log(
      "PASS: actual autonomous worker1→2 potions,90ore→18ingots→six equipment targets, financed physical restock, merchant10x2+1=21, shared market/factors/margins/lots, stale quote requires second confirmation, finite inventory, six independent equipment slots, admin/game sync,390px, idempotent seed and audit gap0",
    );
  } finally {
    if (granted) cli("revoke");
    await browser.close();
  }
})().catch((e) => {
  console.error(e);
  process.exitCode = 1;
});
