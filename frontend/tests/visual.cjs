const {chromium}=require('playwright'),assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),{execFileSync}=require('node:child_process');
(async()=>{
 assert.equal(process.env.TOWER_TEST_DATABASE,'1');assert(process.env.NPC_TEST_DATABASE_URL?.includes('pixel_browser_'),'New disposable visual DB required');
 const root=path.resolve(__dirname,'../..'),out=path.join(root,'artifacts/visual-review');fs.mkdirSync(out,{recursive:true});
 const browser=await chromium.launch({headless:true,...(process.env.CHROMIUM_PATH?{executablePath:process.env.CHROMIUM_PATH}:{}),args:['--no-sandbox']}),page=await browser.newPage({viewport:{width:1280,height:720}}),errors=[],metrics=[];
 page.on('pageerror',e=>{errors.push(e.message);console.error('Browser error:',e.message)});page.setDefaultTimeout(30000);
 const user='pixel'+Date.now(),password='pixel-private-test-123';
 const sql=code=>execFileSync(process.env.PYTHON_EXECUTABLE||root+'/.venv/bin/python',['-c',code],{cwd:root+'/backend',env:{...process.env,DATABASE_URL:process.env.NPC_TEST_DATABASE_URL},encoding:'utf8'}).trim();
 let cid;
 const snapshot=async()=>{await page.locator('.canvas[data-visual]').waitFor();return JSON.parse(await page.locator('.canvas').getAttribute('data-visual'));};
 async function room(id,x,y){
  sql(`from app.database import Session\nfrom app.models import Character\nwith Session.begin() as db:\n c=db.get(Character,${cid});c.room_id=${JSON.stringify(id)};c.x=${x};c.y=${y};c.hp=85;c.level=12\n`);
  await page.reload();await page.locator('canvas').waitFor();await page.waitForFunction(id=>{const el=document.querySelector('.canvas');return el?.dataset.visual&&JSON.parse(el.dataset.visual).room===id},id);await page.waitForTimeout(800);
 }
 const shot=async name=>{await page.locator('.game-shell').screenshot({path:path.join(out,name+'.png')});};
 try{
  await page.goto(process.env.BASE_URL+(process.env.VISUAL_RENDERER==='canvas'?'?renderer=canvas':''));await page.getByLabel('Conta',{exact:true}).fill(user);await page.getByLabel('Senha',{exact:true}).fill(password);await page.getByRole('button',{name:'Criar conta',exact:true}).click();await page.locator('input[name=name]').fill('Sentinela');await page.getByRole('button',{name:'Iniciar jornada'}).click();await page.locator('canvas').waitFor();
  cid=await page.evaluate(async()=>{const r=await fetch('/api/state',{headers:{Authorization:'Bearer '+sessionStorage.getItem('token')}});return(await r.json()).character.id});
  for(const [id,x,y,theme,name]of[['city1',18,12,'SAFE_VILLAGE','safe-zone'],['common_a',12,9,null,'common-battle'],['secret',12,10,'SECRET_DUNGEON','boss-room'],['boss',14,10,'BOSS_RITUAL','fixed-boss'],['guild',17,12,'SAFE_GUILD','guild']]){
   await page.setViewportSize({width:1280,height:720});await room(id,x,y);let diag=await snapshot();if(theme)assert.equal(diag.theme,theme);if(process.env.REQUIRE_CANVAS==='1')assert.equal(diag.renderer,'CANVAS');assert(diag.lights<=12);assert.equal(diag.particles,12);assert.equal(diag.camera.zoom,1);
   await shot(name+'-desktop');
   if(id==='secret'||id==='boss'){const boss=diag.enemies.find(e=>e.boss);assert(boss);assert.equal(boss.key,'bosses');assert.equal(boss.scale,2);assert.equal(boss.hitbox,32);await page.reload();await page.locator('.canvas[data-visual]').waitFor();const again=(await snapshot()).enemies.find(e=>e.id===boss.id);assert.equal(again.frame,boss.frame);}
   const timings=await page.evaluate(()=>new Promise(resolve=>{const frames=[];let previous;const f=t=>{if(previous!==undefined)frames.push(t-previous);previous=t;if(frames.length<120)requestAnimationFrame(f);else resolve(frames)};requestAnimationFrame(f)}));
   timings.sort((a,b)=>a-b);metrics.push({room:id,phaser_fps:(await snapshot()).fps,raf_median_ms:timings[60],raf_p95_ms:timings[114],objects:diag.objects,renderer:diag.renderer});
   await page.setViewportSize({width:1920,height:1080});await page.waitForTimeout(400);await shot(name+'-1920');
   await page.setViewportSize({width:390,height:844});await page.waitForTimeout(500);assert(await page.evaluate(()=>document.body.scrollWidth<=innerWidth+1),'Mobile overflow');await shot(name+'-mobile');
  }
  await page.setViewportSize({width:1280,height:720});await room('city1',5,28);await shot('recovery-tent-desktop');
  for(const width of [1280,390]){
   await page.setViewportSize({width,height:width===390?844:720});await room('city1',9,9);const d=await snapshot(),box=await page.locator('canvas').boundingBox();
   await page.mouse.click(box.x+304-d.camera.x,box.y+208-d.camera.y);
   await page.waitForFunction(()=>JSON.parse(document.querySelector('.canvas').dataset.visual).room==='guild');
  }
  assert.deepEqual(errors,[]);fs.writeFileSync(path.join(out,'performance.json'),JSON.stringify({environment:'Headless Chromium virtualized cloud, not physical mobile/GPU benchmark',metrics,errors},null,2)+'\n');console.log('PASS visual: login, five actual server rooms, fixed bosses/reload, 1280/1920/390px, 16 screenshots, painted facade travel desktop/mobile, bounded effects, performance capture');
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exit(1)});
