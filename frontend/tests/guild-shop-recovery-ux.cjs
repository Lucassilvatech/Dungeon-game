const { chromium } = require("playwright"),
  assert = require("node:assert/strict"),
  { execFileSync } = require("node:child_process"),
  path = require("node:path"),
  fs = require("node:fs");
(async () => {
  assert.equal(process.env.TOWER_TEST_DATABASE, "1");
  assert(
    process.env.UX_TEST_DATABASE_URL,
    "Explicit disposable database required",
  );
  const base = process.env.BASE_URL || "http://127.0.0.1:8082",
    root = path.resolve(__dirname, "../.."),
    name = "ux" + Date.now(),
    password = "private-ux-test-123",
    env = { ...process.env, DATABASE_URL: process.env.UX_TEST_DATABASE_URL },
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
          "Disposable UX validation; temporary role revoked finally",
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
    player = await browser.newPage({ viewport: { width: 1440, height: 1000 } }),
    admin = await browser.newPage({ viewport: { width: 1440, height: 1000 } }),
    errors = [];
  let granted = false;
  for (const p of [player, admin]) {
    p.setDefaultTimeout(30000);
    p.on("pageerror", (e) => errors.push(e.message));
    p.on("dialog", (d) => {
      errors.push("Unexpected browser dialog: " + d.type());
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
      .getByRole("button", { name: "Administração do Rei", exact: true })
      .click();
    await admin.getByRole("button", { name: "Guilda", exact: true }).click();
    await admin
      .getByRole("heading", { name: "Caixa e comércio da Guilda", exact: true })
      .waitFor();
    const ah = {
      Authorization:
        "Bearer " +
        (await admin.evaluate(() => sessionStorage.getItem("admin_token"))),
    };
    const get = async (p, headers = ph) => {
      const x = await player.request.get(base + "/api" + p, { headers });
      assert.equal(x.status(), 200, await x.text());
      return x.json();
    };
    const operation = async (action, target, params) => {
      let x = await admin.request.post(base + "/api/admin/operations/preview", {
        headers: ah,
        data: {
          operation_id: crypto.randomUUID(),
          action,
          target,
          params,
          reason: "Explicit fixtures only in disposable UX browser database",
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
    await operation("royal.injection", "guild", {
      coins: { coin_large: 500, coin_medium: 100, coin_small: 500 },
      strong_confirmation: "INJETAR",
    });
    await operation("royal.injection", "player:" + cid, {
      coins: { coin_large: 500, coin_medium: 100, coin_small: 500 },
      strong_confirmation: "INJETAR",
    });
    for (const id of ["herb", "ore"])
      await operation("guild.item_prices", id, {
        buy_price_units: 1,
        sell_price_units: 2,
        buy_enabled: true,
        sell_enabled: true,
      });
    sql(
      `from app.database import Session\nfrom app import models as m\nwith Session.begin() as db:\n c=db.get(m.Character,${cid});c.room_id='guild';c.x=17;c.y=8\n for qty in [99,99,42]:db.add(m.Item(owner=c.id,definition='herb',quantity=qty,location='inventory'))\n db.add(m.Item(owner=c.id,definition='herb',quantity=99,location='inventory',equipped=True))\n for definition,qty in [('herb',12438),('ore',3000)]:\n  i=m.Item(owner=None,definition=definition,quantity=qty,location='npc');db.add(i);db.flush();db.add(m.NPCStock(item_id=i.id,account_id='guild',sale_weight_mg=qty*2000))`,
    );
    const openShop = async () => {
      await player.reload();
      await player.locator("canvas").waitFor();
      await player
        .getByRole("button", { name: "▤ Comércio", exact: true })
        .click();
      await player
        .getByRole("heading", { name: "Loja da Guilda", exact: true })
        .waitFor();
    };
    await player.addInitScript(
      (t) => sessionStorage.setItem("token", t),
      token,
    );
    await player.goto(base);
    await openShop();
    const herb = player.getByRole("article", {
        name: "Vender Folha Luminosa",
        exact: true,
      }),
      buy = player.getByRole("article", {
        name: "Comprar Folha Luminosa",
        exact: true,
      });
    await herb.getByRole("button", { name: "TUDO", exact: true }).click();
    assert.equal(await herb.getByRole("textbox").inputValue(), "240");
    await herb.getByText("Você receberá:").waitFor();
    assert.match(await herb.innerText(), /Você receberá: 240/);
    assert.equal(await buy.count(), 1);
    const originalCatalog = await get("/economy/shop/catalog");
    assert(
      BigInt(
        originalCatalog.buy.find((i) => i.definition_id === "herb").quantity,
      ) >= 12438n,
    );
    assert(
      BigInt(
        originalCatalog.buy.find((i) => i.definition_id === "ore").quantity,
      ) >= 3000n,
    );
    assert.match(
      await buy.innerText(),
      new RegExp(
        "Estoque: " +
          originalCatalog.buy.find((i) => i.definition_id === "herb").quantity,
      ),
    );
    const grids = await player
      .locator(".shop-grid")
      .first()
      .evaluate(
        (e) => getComputedStyle(e).gridTemplateColumns.split(" ").length,
      );
    assert(grids >= 2, "Desktop shop uses multiple columns");
    await player.getByPlaceholder("Pesquisar item…").fill("musgo");
    assert.equal(await herb.count(), 0);
    assert.equal(await buy.count(), 0);
    await player
      .getByRole("article", { name: "Comprar Minério de Musgo", exact: true })
      .waitFor();
    await player.getByPlaceholder("Pesquisar item…").fill("");
    await herb
      .getByRole("button", { name: "Vender Folha Luminosa", exact: true })
      .click();
    let dialog = player.getByRole("dialog", {
      name: "Confirmar venda",
      exact: true,
    });
    await dialog.waitFor();
    assert.match(await dialog.innerText(), /Quantidade: 240/);
    await dialog.getByRole("button", { name: "Cancelar", exact: true }).click();
    assert.equal(
      (await get("/state")).inventory
        .filter((i) => i.definition === "herb")
        .reduce((a, i) => a + i.quantity, 0),
      339,
    );
    await herb
      .getByRole("button", { name: "Vender Folha Luminosa", exact: true })
      .click();
    await dialog
      .getByRole("button", { name: "Confirmar venda", exact: true })
      .click();
    await dialog.waitFor({ state: "hidden" });
    assert.equal(
      (await get("/state")).inventory
        .filter((i) => i.definition === "herb")
        .reduce((a, i) => a + i.quantity, 0),
      99,
    );
    const catalog = await get("/economy/shop/catalog"),
      offer = catalog.buy.find((i) => i.definition_id === "herb");
    await buy.getByRole("button", { name: "MÁXIMO", exact: true }).click();
    assert.equal(
      await buy.getByRole("textbox").inputValue(),
      offer.maximum_quantity,
    );
    await buy.getByRole("textbox").fill("5");
    assert.match(await buy.innerText(), /Custo total: 10/);
    await buy
      .getByRole("button", { name: "Comprar Folha Luminosa", exact: true })
      .click();
    dialog = player.getByRole("dialog", {
      name: "Confirmar compra",
      exact: true,
    });
    await dialog
      .getByRole("button", { name: "Confirmar compra", exact: true })
      .click();
    await dialog.waitFor({ state: "hidden" });
    assert.equal(
      (await get("/state")).inventory
        .filter((i) => i.definition === "herb")
        .reduce((a, i) => a + i.quantity, 0),
      104,
    );
    if (process.env.UX_SCREENSHOTS) {
      fs.mkdirSync(process.env.UX_SCREENSHOTS, { recursive: true });
      await player.screenshot({
        path: path.join(process.env.UX_SCREENSHOTS, "shop-desktop.png"),
        fullPage: true,
      });
    }
    // Local reasons are independent; batch revisions belong to editing start, not last refresh.
    await admin.reload();
    await admin
      .getByRole("button", { name: "Administração do Rei", exact: true })
      .click();
    await admin.getByRole("button", { name: "Guilda", exact: true }).click();
    await admin
      .getByRole("heading", { name: "Caixa e comércio da Guilda", exact: true })
      .waitFor();
    await admin
      .getByRole("button", { name: "Editar preço herb", exact: true })
      .waitFor();
    await admin
      .getByRole("button", { name: "Prévia 70/20/10", exact: true })
      .click();
    await admin
      .getByText("Informe uma justificativa com pelo menos 10 caracteres.", {
        exact: true,
      })
      .waitFor();
    await admin
      .getByLabel("Justificativa do rebalanceamento", { exact: true })
      .fill("Razão apenas para o rebalanceamento privado");
    assert.equal(
      await admin
        .getByLabel("Justificativa da troca", { exact: true })
        .inputValue(),
      "",
    );
    const edit = async (id, buyPrice, sellPrice) => {
      await admin
        .getByRole("button", { name: "Editar preço " + id, exact: true })
        .click();
      await admin
        .getByLabel("Novo preço de compra", { exact: true })
        .fill(String(buyPrice));
      await admin
        .getByLabel("Novo preço de venda", { exact: true })
        .fill(String(sellPrice));
    };
    await edit("herb", 2, 3);
    assert.equal(
      await admin
        .getByLabel("Confirmar possível arbitragem", { exact: true })
        .count(),
      0,
    );
    assert.equal(
      await admin.getByLabel("Autorizar gratuidade", { exact: true }).count(),
      0,
    );
    await admin
      .getByRole("button", { name: "Salvar este item", exact: true })
      .click();
    await admin
      .getByRole("alert")
      .filter({ hasText: "Informe uma justificativa" })
      .first()
      .waitFor();
    await edit("ore", 2, 4);
    await admin.getByText("2 alterações pendentes", { exact: true }).waitFor();
    await admin
      .getByLabel("Justificativa do lote de preços", { exact: true })
      .fill("Dois materiais ajustados de forma consciente no teste privado");
    await admin
      .getByRole("button", { name: "Revisar alterações", exact: true })
      .click();
    const preview = admin.getByRole("region", {
      name: "Prévia comercial",
      exact: true,
    });
    await preview.getByText("Compra: 1 → 2", { exact: true }).first().waitFor();
    await preview.getByText("Venda: 2 → 3", { exact: true }).waitFor();
    await preview.getByText("Venda: 2 → 4", { exact: true }).waitFor();
    await preview
      .getByLabel("Confirmar impacto comercial", { exact: true })
      .check();
    let done = admin.waitForResponse(
      (r) => r.url().endsWith("/confirm") && r.request().method() === "POST",
    );
    await preview
      .getByRole("button", { name: "Confirmar todas", exact: true })
      .click();
    r = await done;
    assert.equal(r.status(), 200, await r.text());
    const result = await r.json();
    await preview.waitFor({ state: "hidden" });
    let data = await get("/admin/guild/commerce", ah);
    const records = data.history.filter((h) => h.request_id === result.id);
    assert.equal(records.length, 2);
    assert.deepEqual(records.map((h) => h.policy_key).sort(), ["herb", "ore"]);
    assert(records.every((h) => h.reason.includes("Dois materiais")));
    await edit("herb", 10, 8);
    await admin
      .getByLabel("Confirmar possível arbitragem", { exact: true })
      .waitFor();
    await admin.getByLabel("Novo preço de compra", { exact: true }).fill("0");
    await admin.getByLabel("Autorizar gratuidade", { exact: true }).waitFor();
    assert.equal(
      await admin
        .getByLabel("Confirmar possível arbitragem", { exact: true })
        .count(),
      0,
    );
    await admin.getByLabel("Compra da Guilda ativa", { exact: true }).uncheck();
    assert.equal(
      await admin.getByLabel("Autorizar gratuidade", { exact: true }).count(),
      0,
    );
    await admin
      .getByRole("button", {
        name: "Atualizar valores deste item",
        exact: true,
      })
      .click();
    await edit("herb", 3, 4);
    await edit("ore", 3, 5);
    await operation("guild.item_prices", "ore", { buy_price_units: 3 });
    await admin
      .getByRole("button", { name: "Revisar alterações", exact: true })
      .click();
    await admin
      .getByRole("alert")
      .filter({ hasText: /desatualizad/ })
      .waitFor();
    data = await get("/admin/guild/commerce", ah);
    assert.equal(
      data.items.find((i) => i.definition_id === "herb").buy_price_units,
      "2",
    );
    await admin.getByText("2 alterações pendentes", { exact: true }).waitFor();
    // Mobile cards retain touch controls, no native browser dialogs or page overflow.
    await player.setViewportSize({ width: 390, height: 844 });
    await openShop();
    await buy.getByRole("textbox").fill("1");
    await buy
      .getByRole("button", { name: "Comprar Folha Luminosa", exact: true })
      .click();
    await player
      .getByRole("dialog", { name: "Confirmar compra", exact: true })
      .getByRole("button", { name: "Cancelar", exact: true })
      .click();
    assert.equal(
      await player
        .locator(".shop-grid")
        .first()
        .evaluate(
          (e) => getComputedStyle(e).gridTemplateColumns.split(" ").length,
        ),
      1,
    );
    if (process.env.UX_SCREENSHOTS)
      await player.screenshot({
        path: path.join(process.env.UX_SCREENSHOTS, "shop-mobile.png"),
        fullPage: true,
      });
    // Existing custody and price rules: create a historical death fixture, then use the real recovery API.
    const rid = Number(
      sql(
        `from app.database import Session\nfrom app import models as m\nwith Session.begin() as db:\n c=db.get(m.Character,${cid});c.room_id='city1';c.x=2;c.y=2\n room=m.Room(id='ux-death-'+str(c.id),floor_id=1,name='Historical fixture',kind='COMMON',data={});db.add(room);db.flush()\n e=m.Expedition(character_id=c.id,room_id=room.id,seed=1,status='FAILED');db.add(e);db.flush()\n b=m.Battle(character_id=c.id,monster='slime',hp=0,status='lost');db.add(b);db.flush()\n death=m.DeathEvent(character_id=c.id,expedition_id=e.id,battle_id=b.id,receipt={},acknowledged=True);db.add(death);db.flush()\n d=db.get(m.ItemDefinition,'ux_blade')\n if not d:\n  d=m.ItemDefinition(id='ux_blade',name='Lâmina antiga',kind='weapon',power=3,base_value=10,rarity='rare');db.add(d);db.flush()\n i=m.Item(owner=None,definition=d.id,quantity=1,location='recovery');db.add(i);db.flush()\n r=m.RecoveryItem(character_id=c.id,item_id=i.id,death_event_id=death.id,price=d.base_value*2);db.add(r);db.flush();print(r.id)`,
      ),
    );
    r = await player.request.post(base + "/api/interact", {
      headers: ph,
      data: {},
    });
    assert.equal(r.status(), 409);
    r = await player.request.post(base + "/api/recovery/" + rid + "/recover", {
      headers: ph,
      data: { request_id: crypto.randomUUID() },
    });
    assert.equal(r.status(), 409);
    sql(
      `from app.database import Session\nfrom app import models as m\nwith Session.begin() as db:\n c=db.get(m.Character,${cid});c.x=5;c.y=31`,
    );
    await player.reload();
    await player.locator("canvas").waitFor();
    let s = await get("/state");
    assert.equal(s.map.npc_role, "recovery");
    assert.deepEqual(s.map.npc, [5, 30]);
    assert(
      s.map.npc[0] < s.map.width / 3 && s.map.npc[1] > (s.map.height * 2) / 3,
    );
    await player
      .getByRole("button", { name: "Falar com Figura encapuzada", exact: true })
      .click();
    await player
      .getByRole("heading", { name: "Recuperação pessoal", exact: true })
      .waitFor();
    await player
      .getByRole("button", { name: "Recuperar Lâmina antiga", exact: true })
      .click();
    const recoveryDialog = player.getByRole("dialog", {
      name: "Confirmar recuperação",
      exact: true,
    });
    await recoveryDialog.waitFor();
    await recoveryDialog
      .getByRole("button", { name: "Confirmar recuperação", exact: true })
      .click();
    await recoveryDialog.waitFor({ state: "hidden" });
    await player.getByText("Já recuperado", { exact: true }).waitFor();
    const list = await get("/recovery");
    assert.equal(list.find((r) => r.id === rid).recovered, true);
    const audit = await get("/admin/lunar/audit", ah);
    assert.equal(audit.gap_mg, "0");
    assert.deepEqual(audit.metadata_mismatches, []);
    assert.deepEqual(audit.ledger_mismatches, []);
    await player.getByRole("button", { name: "⌘ Mapa", exact: true }).click();
    if (process.env.UX_SCREENSHOTS)
      await player.screenshot({
        path: path.join(process.env.UX_SCREENSHOTS, "tent-mobile.png"),
        fullPage: true,
      });
    await player.setViewportSize({ width: 1440, height: 1000 });
    if (process.env.UX_SCREENSHOTS)
      await player.screenshot({
        path: path.join(process.env.UX_SCREENSHOTS, "tent-desktop.png"),
        fullPage: true,
      });
    await admin.setViewportSize({ width: 390, height: 844 });
    for (const p of [player, admin])
      assert(
        await p.evaluate(
          () => document.documentElement.scrollWidth <= innerWidth + 1,
        ),
        "No page overflow",
      );
    assert.deepEqual(errors, []);
    console.log(
      "PASS: aggregated stock>=12438/>=3000, desktop grid/mobile390, live search, TUDO240 excludes equipped99, MAX server capacity/coins, instant totals, integrated confirmation/cancel, per-operation reason, two-item atomic batch/history, conditional risks, stale revisions retained, southwest hooded tent, proximity recovery and audit gap0",
    );
  } finally {
    if (granted) cli("revoke");
    await browser.close();
  }
})().catch((e) => {
  console.error(e);
  process.exitCode = 1;
});
