const { chromium } = require('playwright'), assert = require('node:assert/strict'), { execFileSync } = require('node:child_process'), path = require('node:path'),fs=require('node:fs');
(async () => {
    assert.equal(process.env.TOWER_TEST_DATABASE, '1', 'Disposable database required');
    assert(process.env.PROCEDURAL_TEST_DATABASE_URL, 'Set the private API database explicitly');
    const root = path.resolve(__dirname, '../..'), base = process.env.BASE_URL || 'http://127.0.0.1:8070', name = 'mineral' + Date.now(), password = 'browser-test-only-123', env = { ...process.env, DATABASE_URL: process.env.PROCEDURAL_TEST_DATABASE_URL };
    const browser = await chromium.launch({ headless: true, ...(process.env.CHROMIUM_PATH ? { executablePath: process.env.CHROMIUM_PATH } : {}), args: ['--no-sandbox'] });
    const page = await browser.newPage({ viewport: { width: 390, height: 844 } }), admin = await browser.newPage();
    page.setDefaultTimeout(45000);
    admin.setDefaultTimeout(30000);
    const errors = [];
    [page, admin].forEach(p => p.on('pageerror', e => errors.push(e.message)));
    const python=process.env.PYTHON_EXECUTABLE || (fs.existsSync(root+'/.venv/bin/python')?root+'/.venv/bin/python':'python');
    const cli = role => execFileSync(python, ['-m', 'app.admin_cli', name, role, '--reason', 'Private procedural browser verification; role revoked finally'], { cwd: root + '/backend', env, stdio: 'pipe' });
    let granted = false;
    try {
        await page.goto(base);
        await page.getByLabel('Conta', { exact: true }).fill(name);
        await page.getByLabel('Senha', { exact: true }).fill(password);
        await page.getByRole('button', { name: 'Criar conta', exact: true }).click();
        await page.locator('input[name=name]').fill(name);
        await page.getByRole('button', { name: 'Iniciar jornada', exact: true }).click();
        await page.locator('canvas').waitFor();
        cli('owner');
        granted = true;
        await admin.goto(base + '/admin');
        await admin.getByLabel('Conta administrativa', { exact: true }).fill(name);
        await admin.getByLabel('Senha', { exact: true }).fill(password);
        await admin.getByRole('button', { name: 'Entrar na Central', exact: true }).click();
        await admin.getByRole('button', { name: 'Cutover Lunar', exact: true }).click();
        await admin.getByRole('heading', { name: /Economia Lunar ·/ }).waitFor();
        if(await admin.getByRole('heading',{name:'Economia Lunar · LEGACY',exact:true}).count()) {
        await admin.getByRole('heading', { name: 'Preview / dry-run sem escrita' }).waitFor();
        await admin.getByLabel('Justificativa do cutover', { exact: true }).fill('Cutover autorizado somente para banco descartável Chromium');
        await admin.getByRole('checkbox').check();
        admin.on('dialog', d => d.accept());
        await admin.getByRole('button', { name: 'Confirmar cutover Lunar', exact: true }).click();
        await admin.getByRole('heading', { name: 'Economia Lunar · CONVERTED', exact: true }).waitFor();
        }
        const ah = { Authorization: 'Bearer ' + await admin.evaluate(() => sessionStorage.getItem('admin_token')) };
        const adm = async (p, body) => { const r = await (body ? admin.request.post(base + '/api/admin' + p, { headers: ah, data: body }) : admin.request.get(base + '/api/admin' + p, { headers: ah })); assert.equal(r.status(), 200, await r.text()); return r.json(); };
        const initial=await adm('/lunar/audit');
        const p = await adm('/operations/preview', { operation_id: crypto.randomUUID(), action: 'bank.transfer', target: 'central_bank', params: { source: 'treasury', destination: 'guild', amount: '800' }, reason: 'Financiar compra real de pepita no teste privado' });
        await adm('/operations/' + p.id + '/confirm', { confirmed: true, confirmation_token: p.confirmation_token });
        const reb=await adm('/operations/preview',{operation_id:crypto.randomUUID(),action:'guild.rebalance',target:'guild',params:{initial:false},reason:'Explicit physical cash composition for disposable browser fixture'});
        await adm('/operations/'+reb.id+'/confirm',{confirmed:true,confirmation_token:reb.confirmation_token});
        const state = () => page.evaluate(async () => { const r = await fetch('/api/state', { headers: { Authorization: 'Bearer ' + sessionStorage.getItem('token') } }); if (!r.ok)
            throw Error('state ' + r.status); return r.json(); });
        const idle = () => page.waitForFunction(() => document.querySelector('main')?.getAttribute('aria-busy') === 'false');
        await page.getByRole('button', { name: '✧ AVENTURA', exact: true }).click();
        await idle();
        let s = await state();
        assert.equal(s.expedition.status, 'ACTIVE');
        const occurrence = s.map.lunar_resources[0];
        assert(occurrence);
        assert(BigInt(occurrence.weight_mg)>=100000n&&BigInt(occurrence.weight_mg)<=1000000n);const weight=BigInt(occurrence.weight_mg),g=weight/1000n;
        await page.getByText(`Peso: ${g} g · Disponível`, { exact: true }).waitFor();
        for (let i = 0; i < 3 && (await state()).map.lunar_resources.length; i++) {
            await page.getByRole('button', { name: 'Coletar Minério Lunar', exact: true }).click();
            await idle();
        }
        s = await state();
        assert.deepEqual(s.map.lunar_resources, []);
        assert.equal(s.lunar_inventory[0].weight_mg,weight.toString());const lotId=s.lunar_inventory[0].lot_id;
        assert.equal(s.character.coins, 0);
        await page.getByRole('button', { name: /^▣ Inventário/ }).click();
        await page.getByText(`Pepita #${lotId} · ${g} g`, { exact: true }).waitFor();
        await page.reload();
        await page.locator('canvas').waitFor();
        await idle();
        assert.deepEqual((await state()).map.lunar_resources, []);
        await page.getByRole('button', { name: 'Sair', exact: true }).click();
        await page.getByLabel('Conta', { exact: true }).fill(name);
        await page.getByLabel('Senha', { exact: true }).fill(password);
        await page.getByRole('button', { name: 'Entrar', exact: true }).click();
        await page.locator('canvas').waitFor();
        await idle();
        assert.equal((await state()).lunar_inventory[0].lot_id,lotId);
        await page.getByRole('button', { name: 'FUGIR DA AVENTURA', exact: true }).click();
        await page.getByRole('button', { name: 'CONFIRMAR FUGA', exact: true }).click();
        await idle();
        s = await state();
        const guild = s.room.exits.findIndex(e => e.x === 9 && e.y === 7);
        assert(guild >= 0);
        await page.locator('.paths button').nth(guild).click();
        await idle();
        assert.equal((await state()).room.id, 'guild');
        await page.getByRole('button', { name: 'Falar com recepcionista', exact: true }).click();
        await idle();
        await page.getByRole('button', { name: '☾ Lunar', exact: true }).click();
        await page.getByRole('button', { name: `Vender Pepita #${lotId}`, exact: true }).waitFor();
        page.on('dialog', d => d.accept());
        await page.getByRole('button', { name: `Vender Pepita #${lotId}`, exact: true }).click();
        await idle();
        s = await state();
        assert.deepEqual(s.lunar_inventory, []);
        assert.equal(s.character.coins,Number(g*800n/1000n));
        const audit = await adm('/lunar/audit');
        assert.equal(audit.gap_mg, '0');
        assert.equal(BigInt(audit.discovered_mg)-BigInt(initial.discovered_mg),weight);
        assert.equal(BigInt(audit.lunar_resource_sold_to_guild_mg)-BigInt(initial.lunar_resource_sold_to_guild_mg),weight);
        assert.deepEqual(audit.metadata_mismatches, []);
        const view = await adm('/lunar/resources');
        assert.equal(view.metrics.lunar_resource_occurrences_collected-initial.lunar_resource_occurrences_collected, 1);
        assert.equal(BigInt(view.metrics.mineral_by_account_kind_mg.guild)-BigInt(initial.mineral_by_account_kind_mg.guild??'0'),weight);
        assert(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1));
        assert.deepEqual(errors, []);
        console.log('PASS: Chromium 390px registration/login, procedural map and mineral marker, collection, inventory, reload/logout/login, flee custody, Guild sale with real cash, admin metrics and audit gap 0');
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
