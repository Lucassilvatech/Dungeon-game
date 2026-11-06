const { chromium } = require("playwright");
const assert = require("node:assert/strict");
const { execFileSync } = require("node:child_process");
(async () => {
  const base = process.env.BASE_URL || "http://127.0.0.1:8080";
  const username = "eventcheck" + Date.now(),
    password = "events-test-pass-123";
  const browser = await chromium.launch({
    headless: true,
    executablePath: process.env.CHROMIUM_PATH || "/usr/bin/chromium",
    args: ["--no-sandbox"],
  });
  const page = await browser.newPage({
    viewport: { width: 1440, height: 1000 },
  });
  page.setDefaultTimeout(8000);
  const errors = [];
  page.on("pageerror", (e) => errors.push(e.message));
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
        "Temporary scheduled world event interface verification",
      ],
      { stdio: "pipe" },
    );
  let granted = false;
  try {
    assert.equal(
      (
        await page.request.post(base + "/api/auth/register", {
          data: { username, password },
        })
      ).status(),
      201,
    );
    cli("owner");
    granted = true;
    await page.goto(base + "/admin");
    await page.getByLabel("Conta").fill(username);
    await page.getByLabel("Senha").fill(password);
    await page
      .getByRole("button", { name: "Entrar na Central", exact: true })
      .click();
    await page
      .getByRole("button", { name: "Mundo e eventos", exact: true })
      .click();
    await page
      .getByRole("heading", { name: "Eventos do primeiro andar", exact: true })
      .waitFor();
    const form = page
      .locator("form")
      .filter({
        has: page.getByRole("button", {
          name: "Revisar evento e impacto",
          exact: true,
        }),
      });
    const name = "Evento de interface " + Date.now();
    await form.getByLabel("Nome", { exact: true }).fill(name);
    await form
      .getByLabel("Descrição", { exact: true })
      .fill("Validação de evento futuro, cancelado antes do início.");
    await form.getByLabel("Aumento percentual", { exact: true }).fill("100");
    await form
      .getByLabel("Início (UTC)", { exact: true })
      .fill(new Date(Date.now() + 3600000).toISOString().slice(0, 16));
    await form.getByLabel("Duração em minutos", { exact: true }).fill("1");
    await form
      .getByLabel("Justificativa auditável", { exact: true })
      .fill(
        "Verificar prévia e cancelamento de evento futuro sem efeito ativo.",
      );
    await form
      .getByRole("button", { name: "Revisar evento e impacto", exact: true })
      .click();
    await page.getByRole("dialog").waitFor();
    await page
      .getByRole("button", { name: "CONFIRMAR OPERAÇÃO", exact: true })
      .click();
    const article = page
      .locator("article")
      .filter({
        has: page.getByRole("heading", {
          name: name + " · SCHEDULED",
          exact: true,
        }),
      });
    await article.waitFor();
    await article
      .getByRole("button", { name: "Preparar cancelamento", exact: true })
      .click();
    await page
      .locator(".operation")
      .getByLabel("Justificativa auditável", { exact: true })
      .fill("Cancelar o evento de validação antes do início programado.");
    await page
      .locator(".operation")
      .getByRole("button", { name: "Calcular prévia", exact: true })
      .click();
    await page.getByRole("dialog").waitFor();
    await page
      .getByRole("button", { name: "CONFIRMAR OPERAÇÃO", exact: true })
      .click();
    await page
      .getByRole("heading", { name: name + " · CANCELLED", exact: true })
      .waitFor();
    await page.screenshot({
      path: "/tmp/procedural-world-events.png",
      fullPage: true,
    });
    assert.deepEqual(errors, []);
    console.log(
      "PASS: explained event form, 100% preview, schedule, audited confirmation and cancellation through the browser",
    );
  } finally {
    if (granted) cli("revoke");
    await browser.close();
  }
})().catch((e) => {
  console.error(e);
  process.exit(1);
});
