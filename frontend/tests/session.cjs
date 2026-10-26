const {chromium}=require('playwright');
const assert=require('node:assert/strict');
(async()=>{
 const base=process.env.BASE_URL||'http://127.0.0.1:8080';
 const browser=await chromium.launch({headless:true,executablePath:process.env.CHROMIUM_PATH||'/usr/bin/chromium',args:['--no-sandbox']});
 const page=await browser.newPage({viewport:{width:1280,height:900}});
 page.setDefaultTimeout(20000);const errors=[];page.on('pageerror',e=>errors.push(e.message));
 try{
  await page.goto(base);
  await page.locator('input[name=username]').fill('web08'+Date.now());
  await page.locator('input[name=password]').fill('session-test-pass-123');
  await page.getByRole('button',{name:'Criar conta',exact:true}).click();
  await page.locator('input[name=name]').fill('Web08 '+Date.now());
  await page.getByRole('button',{name:'Iniciar jornada',exact:true}).click();
  await page.locator('canvas').waitFor();
  const state=()=>page.evaluate(async()=>{const r=await fetch('/api/state',{headers:{Authorization:'Bearer '+sessionStorage.getItem('token')}});return r.json()});
  const s=await state();assert.equal(s.room.id,'city1');
  await page.locator('canvas').click({position:{x:100,y:100}});
  // Allow any pointer route to finish before testing reconnection; no client position injection.
  await page.waitForFunction(()=>document.querySelector('main')?.getAttribute('aria-busy')==='false');
  await page.route('**/api/state',route=>route.abort('failed'));
  await page.getByText('Atualização pausada após 3 falhas',{exact:false}).waitFor();
  await page.unroute('**/api/state');
  await page.getByRole('button',{name:'Atualizar',exact:true}).click();
  await page.getByText('Conectado · Progresso persistente',{exact:true}).waitFor();
  assert.equal((await state()).character.id,s.character.id);
  const count={state:0,extra:0};const onRequest=r=>{if(r.method()==='GET'){if(r.url().endsWith('/api/state'))count.state++;if(['/api/rewards','/api/guild/rewards','/api/fast-travel'].some(p=>r.url().endsWith(p)))count.extra++;}};
  page.on('request',onRequest);await page.waitForTimeout(3300);page.off('request',onRequest);
  assert(count.state>=1);assert.equal(count.extra,0);
  await page.evaluate(async()=>{await fetch('/api/auth/logout-all',{method:'POST',headers:{'Content-Type':'application/json',Authorization:'Bearer '+sessionStorage.getItem('token')},body:'{}'})});
  await page.getByRole('button',{name:'Entrar',exact:true}).waitFor();
  assert.equal(await page.evaluate(()=>sessionStorage.getItem('token')),null);
  assert.deepEqual(errors,[]);
  console.log('PASS: web registration, movement, bounded reconnect/manual retry, consolidated polling and revoked-session logout');
 }finally{await browser.close()}
})().catch(e=>{console.error(e);process.exit(1)});
