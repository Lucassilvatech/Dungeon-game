const { chromium } = require("playwright");
const assert = require("node:assert/strict");
const { execFileSync } = require("node:child_process");
const os = require("node:os"),
  path = require("node:path");
(async () => {
  const base = process.env.BASE_URL || "http://127.0.0.1:8080";
  const browser = await chromium.launch({
    executablePath: process.env.CHROMIUM_PATH || "/usr/bin/chromium",
    headless: true,
    args: ["--no-sandbox"],
  });
  const page = await browser.newPage({
    viewport: { width: 1440, height: 1000 },
  });
  const username = "admcheck" + Date.now();
  let granted = false;
  let pendingEmission = 0;
  const cli = (role) =>
    execFileSync(
      "docker",
      [
        "--host=unix:///var/run/docker.sock",
        "exec",
        "dungeon-game-backend-1",
        "python",
        "-m",
        "app.admin_cli",
        username,
        role,
        "--reason",
        "Temporary browser validation of authorized administration",
      ],
      { stdio: "pipe" },
    );
  page.setDefaultTimeout(10000);
  const errors = [];
  page.on("pageerror", (e) => errors.push(e.message));
  try {
    const r = await page.request.post(base + "/api/auth/register", {
      data: { username, password: "browser-admin-pass-123" },
    });
    assert.equal(r.status(), 201);
    const ordinary = (await r.json()).token;
    assert.equal(
      (
        await page.request.get(base + "/api/admin/overview", {
          headers: { Authorization: "Bearer " + ordinary },
        })
      ).status(),
      401,
    );
    cli("owner");
    granted = true;
    await page.goto(base + "/admin");
    await page
      .getByLabel("Conta administrativa", { exact: true })
      .fill(username);
    await page
      .getByLabel("Senha", { exact: true })
      .fill("browser-admin-pass-123");
    await page
      .getByRole("button", { name: "Entrar na Central", exact: true })
      .click();
    await page
      .getByRole("heading", { name: "Visão geral", exact: true })
      .waitFor();
    async function api(route, body) {
      return page.evaluate(
        async ({ route, body }) => {
          const r = await fetch("/api/admin" + route, {
            method: body === undefined ? "GET" : "POST",
            headers: {
              "Content-Type": "application/json",
              Authorization: "Bearer " + sessionStorage.getItem("admin_token"),
            },
            body: body === undefined ? undefined : JSON.stringify(body),
          });
          return { status: r.status, data: await r.json() };
        },
        { route, body },
      );
    }
    const initial = (await api("/economy")).data.indicators;
    assert.equal(initial.reconciliation_gap, "0");
    await page
      .getByRole("button", { name: "Banco Central", exact: true })
      .click();
    await page
      .getByRole("heading", { name: "Banco Central", exact: true })
      .waitFor();
    async function operation(action) {
      await page.getByLabel("Ação", { exact: true }).selectOption(action);
      await page
        .getByLabel("Quantidade de moedas", { exact: true })
        .fill("100");
      await page
        .getByLabel(
          action === "bank.issue" ? /Conta de destino/ : /Conta de origem/,
        )
        .fill("central_bank");
      await page
        .getByLabel("Justificativa auditável", { exact: true })
        .fill(
          "Validação do navegador: emissão e retirada pareadas, sem benefício a personagens.",
        );
      const pending = page.waitForResponse(
        (r) =>
          r.url().endsWith("/api/admin/operations/preview") &&
          r.request().method() === "POST",
      );
      await page
        .getByRole("button", { name: "Calcular prévia", exact: true })
        .click();
      const pre = await (await pending).json();
      await page.getByRole("dialog").waitFor();
      await page
        .getByRole("button", { name: "CONFIRMAR OPERAÇÃO", exact: true })
        .click();
      await page.getByRole("dialog").waitFor({ state: "hidden" });
      assert.equal(
        (
          await api("/operations/" + pre.id + "/confirm", {
            confirmed: true,
            confirmation_token: pre.confirmation_token,
          })
        ).data.replayed,
        true,
      );
      return pre;
    }
    await operation("bank.issue");
    pendingEmission = 100;
    assert.equal(
      (await api("/economy")).data.indicators.central_bank,
      String(BigInt(initial.central_bank) + 100n),
    );
    await operation("bank.burn");
    pendingEmission = 0;
    const final = (await api("/economy")).data.indicators;
    assert.equal(final.official_net, initial.official_net);
    assert.equal(final.central_bank, initial.central_bank);
    assert.equal(final.reconciliation_gap, "0");
    await page.screenshot({
      path: path.join(os.tmpdir(), "dungeon-admin-bank.png"),
      fullPage: true,
    });
    for (const name of [
      "Economia",
      "Guildas",
      "Jogadores",
      "Itens",
      "Monstros",
      "Leilões",
      "Mundo e eventos",
      "Auditoria",
    ]) {
      await page.getByRole("button", { name, exact: true }).click();
      await page.getByRole("heading", { name, exact: true }).waitFor();
    }
    await page.locator("table").first().waitFor();
    await page.screenshot({
      path: path.join(os.tmpdir(), "dungeon-admin-audit.png"),
      fullPage: true,
    });
    await page.setViewportSize({ width: 390, height: 844 });
    assert(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= innerWidth + 1,
      ),
    );
    await page
      .getByRole("button", { name: "Encerrar sessão ADM", exact: true })
      .click();
    await page
      .getByRole("button", { name: "Entrar na Central", exact: true })
      .waitFor();
    assert.deepEqual(errors, []);
    console.log(
      "PASS: independent admin login, ordinary-token denial, bank preview/confirmation/replay, paired issuance/retirement with exact reconciliation, all modules, audit, mobile and session revocation",
    );
  } catch (e) {
    await page.screenshot({
      path: path.join(os.tmpdir(), "dungeon-admin-failure.png"),
      fullPage: true,
    });
    console.error("Browser errors:", errors);
    console.error(
      "Form labels:",
      await page.locator("label").allTextContents(),
    );
    throw e;
  } finally {
    try {
      if (granted && pendingEmission) {
        // Always retire only this test's unmatched issuance, through the official API.
        const result = await page.evaluate(async (amount) => {
          const headers = {
            "Content-Type": "application/json",
            Authorization: "Bearer " + sessionStorage.getItem("admin_token"),
          };
          const p = await (
            await fetch("/api/admin/operations/preview", {
              method: "POST",
              headers,
              body: JSON.stringify({
                operation_id: crypto.randomUUID(),
                action: "bank.burn",
                target: "central_bank",
                params: { amount: String(amount), source: "central_bank" },
                reason:
                  "Retirada pareada de limpeza da emissão temporária do teste do navegador.",
              }),
            })
          ).json();
          const r = await fetch("/api/admin/operations/" + p.id + "/confirm", {
            method: "POST",
            headers,
            body: JSON.stringify({
              confirmed: true,
              confirmation_token: p.confirmation_token,
            }),
          });
          return r.status;
        }, pendingEmission);
        assert.equal(result, 200, "Paired test issuance cleanup failed");
      }
    } finally {
      try {
        if (granted) cli("revoke");
      } finally {
        await browser.close();
      }
    }
  }
})().catch((e) => {
  console.error(e);
  process.exit(1);
});
