const { chromium } = require('playwright'), assert = require('node:assert/strict'), { execFileSync } = require('node:child_process'), path = require('node:path');
(async () => {
    const base = process.env.BASE_URL || 'http://127.0.0.1:8091', name = 'cutover' + Date.now(), pass = 'cutover-browser-test-123', root = path.resolve(__dirname, '../..'), env = { ...process.env, DATABASE_URL: process.env.CUTOVER_TEST_DATABASE_URL };
    assert.equal(process.env.TOWER_TEST_DATABASE, '1', 'Use only an explicitly marked disposable database');
    assert(env.DATABASE_URL, 'Set CUTOVER_TEST_DATABASE_URL to the disposable API database');
    const browser = await chromium.launch({ headless: true, executablePath: process.env.CHROMIUM_PATH || '/usr/bin/chromium', args: ['--no-sandbox'] });
    const admin = await browser.newPage(), player = await browser.newPage({ viewport: { width: 390, height: 844 } });
    for (const p of [admin, player])
        p.setDefaultTimeout(25000);
    let granted = false;
    const errors = [];
    [admin, player].forEach(p => p.on('pageerror', e => errors.push(e.message)));
    const cli = role => execFileSync(root + '/.venv/bin/python', ['-m', 'app.admin_cli', name, role, '--reason', 'Temporary cutover UI verification; role revoked finally'], { cwd: root + '/backend', env, stdio: 'pipe' });
    try {
        const create = async (username) => { const r = await admin.request.post(base + '/api/auth/register', { data: { username, password: pass } }); assert.equal(r.status(), 201); const token = (await r.json()).token; assert.equal((await admin.request.post(base + '/api/character', { headers: { Authorization: 'Bearer ' + token }, data: { name: username } })).status(), 201); return token; };
        const token = await create(name), debtToken = await create(name + 'debt');
        // Explicit private fixture: positions and legacy funds only, before conversion. No production DB.
        const fixture = JSON.parse(execFileSync(root + '/.venv/bin/python', ['-c', `import json; from sqlalchemy import select; from app.database import Session; from app import models as m
with Session.begin() as s:
 a=s.scalar(select(m.Account).where(m.Account.username=='${name}')); c=s.scalar(select(m.Character).where(m.Character.account_id==a.id)); c.coins=100
 n=s.get(m.Room,'guild').data['npc']; c.room_id='guild'; c.x=n[0]-1; c.y=n[1]
 a2=s.scalar(select(m.Account).where(m.Account.username=='${name}debt')); c2=s.scalar(select(m.Character).where(m.Character.account_id==a2.id)); c2.coins=-70
 s.get(m.Treasury,1).balance-=30
 i=m.Item(owner=c.id,definition='crystal',quantity=1,location='inventory'); s.add(i); s.flush(); print(json.dumps({'item':i.id}))`], { cwd: root + '/backend', env, encoding: 'utf8' }));
        cli('owner');
        granted = true;
        await admin.goto(base + '/admin');
        await admin.getByLabel('Conta administrativa', { exact: true }).fill(name);
        await admin.getByLabel('Senha', { exact: true }).fill(pass);
        await admin.getByRole('button', { name: 'Entrar na Central', exact: true }).click();
        await admin.getByRole('button', { name: 'Cutover Lunar', exact: true }).click();
        await admin.getByRole('heading', { name: 'Preview / dry-run sem escrita' }).waitFor();
        await admin.getByLabel('Justificativa do cutover', { exact: true }).fill('Conversão autorizada apenas no banco descartável de teste Web');
        await admin.getByRole('checkbox').check();
        admin.on('dialog', d => d.accept());
        await admin.getByRole('button', { name: 'Confirmar cutover Lunar', exact: true }).click();
        await admin.getByRole('heading', { name: 'Economia Lunar · CONVERTED', exact: true }).waitFor();
        const ah = { Authorization: 'Bearer ' + await admin.evaluate(() => sessionStorage.getItem('admin_token')) }, ph = { Authorization: 'Bearer ' + token };
        const api = async (path, body, h = ph) => { const r = await (body === undefined ? admin.request.get(base + '/api' + path, { headers: h }) : admin.request.post(base + '/api' + path, { headers: h, data: body })); assert.equal(r.status(), 200, await r.text()); return r.json(); };
        const operation = async (action, target, params) => { const p = await api('/admin/operations/preview', { operation_id: crypto.randomUUID(), action, target: String(target), params, reason: 'Operação explícita para validar comércio físico no navegador' }, ah); return api('/admin/operations/' + p.id + '/confirm', { confirmed: true, confirmation_token: p.confirmation_token }, ah); };
        await operation('npc.stock', fixture.item, { account_id: 'npc:smith', price_weight_mg: '20000' });
        await operation('bank.transfer', 'central_bank', { source: 'treasury', destination: 'guild', amount: '20' });
        await player.addInitScript(t => sessionStorage.setItem('token', t), token);
        await player.goto(base);
        await player.locator('canvas').waitFor();
        await player.getByRole('button', { name: '☾ Lunar', exact: true }).click();
        await player.getByText('Estado: LUNAR — conversão concluída', { exact: true }).waitFor();
        await player.getByText('Peso monetário total: 100000 mg', { exact: true }).waitFor();
        player.on('dialog', d => d.accept());
        await player.getByRole('button', { name: '▤ Comércio', exact: true }).click();
        await player.getByRole('button', { name: 'Comprar Cristal da clareira', exact: true }).click();
        await player.waitForFunction(() => document.querySelector('main')?.getAttribute('aria-busy') === 'false');
        await player.getByRole('button', { name: /^Vender Cristal da clareira/ }).waitFor();
        await player.getByRole('button', { name: /^Vender Cristal da clareira/ }).click();
        await player.waitForFunction(() => document.querySelector('main')?.getAttribute('aria-busy') === 'false');
        assert.equal((await api('/lunar/wallet')).assets.coin_large.quantity, '9');
        const debtor = await browser.newPage({ viewport: { width: 390, height: 844 } });
        await debtor.addInitScript(t => sessionStorage.setItem('token', t), debtToken);
        await debtor.goto(base);
        await debtor.locator('canvas').waitFor();
        await debtor.getByRole('button', { name: '☾ Lunar', exact: true }).click();
        await debtor.getByText('Dívida separada da carteira: 70000 mg', { exact: true }).waitFor();
        const audit = await api('/admin/lunar/audit', undefined, ah);
        assert.equal(audit.gap_mg, '0');
        assert.deepEqual(audit.metadata_mismatches, []);
        assert(await player.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1));
        assert.deepEqual(errors, []);
        console.log('PASS: ADM preview/confirm cutover; Lunar wallet principal, separate debt, finite NPC buy/sell UI and zero audit gap; mobile responsive');
    }
    finally {
        try {
            if (granted)
                cli('revoke');
        }
        finally {
            await browser.close();
        }
    }
})().catch(e => { console.error(e); process.exit(1); });
