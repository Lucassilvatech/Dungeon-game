const {chromium}=require('playwright');const assert=require('node:assert/strict');
(async()=>{
 const base=process.env.BASE_URL||'http://127.0.0.1:8080';const browser=await chromium.launch({headless:true,executablePath:process.env.CHROMIUM_PATH||'/usr/bin/chromium',args:['--no-sandbox']});const page=await browser.newPage({viewport:{width:1280,height:900}});page.setDefaultTimeout(20000);
 const errors=[];page.on('pageerror',e=>errors.push(e.message));
 try{
  const name='groupweb'+Date.now();const r=await page.request.post(base+'/api/auth/register',{data:{username:name,password:'group-browser-pass-123'}});assert.equal(r.status(),201);const token=(await r.json()).token;
  const headers={Authorization:'Bearer '+token};
  const call=async(path,body)=>{const response=await(body===undefined?page.request.get(base+'/api'+path,{headers}):page.request.post(base+'/api'+path,{headers,data:body}));assert.equal(response.status(),path==='/character'?201:200,await response.text());return response.json()};
  await call('/character',{name});let state=await call('/state');
  function path(s,target,adjacent=true){const walls=new Set(s.map.walls.map(p=>p.join(',')));Object.values(s.map.monsters).forEach(p=>walls.add(p.join(',')));if(s.map.npc)walls.add(s.map.npc.join(','));const q=[{x:s.character.x,y:s.character.y,p:[]}],seen=new Set([`${s.character.x},${s.character.y}`]);for(let i=0;i<q.length;i++){const c=q[i];if(Math.abs(c.x-target.x)+Math.abs(c.y-target.y)<=(adjacent?1:0))return c.p;for(const [dx,dy] of [[1,0],[-1,0],[0,1],[0,-1]]){const x=c.x+dx,y=c.y+dy,k=`${x},${y}`;if(!seen.has(k)&&!walls.has(k)&&x>0&&y>0&&x<s.map.width-1&&y<s.map.height-1){seen.add(k);q.push({x,y,p:[...c.p,[dx,dy]]})}}}throw Error('No walking path')}
  const walk=async target=>{for(const [dx,dy] of path(state,target)){state=await call('/move',{dx,dy})}};
  const exit=[...state.room.exits].sort((a,b)=>b.x-a.x)[0];assert(exit);await walk(exit);await call('/rooms/exits/'+exit.id,{});state=await call('/state');
  function nearby(s,a,b){const blocked=new Set(s.map.walls.map(p=>p.join(',')));if(s.map.npc)blocked.add(s.map.npc.join(','));const q=[[a.x,a.y,0]],seen=new Set([`${a.x},${a.y}`]);for(let i=0;i<q.length;i++){const[x,y,d]=q[i];if(x===b.x&&y===b.y)return true;if(d>=s.encounter_rules.radius)continue;for(const[dx,dy]of [[1,0],[-1,0],[0,1],[0,-1]]){const xx=x+dx,yy=y+dy,k=`${xx},${yy}`;if(!seen.has(k)&&!blocked.has(k)&&xx>0&&yy>0&&xx<s.map.width-1&&yy<s.map.height-1){seen.add(k);q.push([xx,yy,d+1])}}}return false}
  let pair;
  for(let region=0;region<3&&!pair;region++){
    for(const a of state.map.enemies)for(const b of state.map.enemies)if(a.id!==b.id&&nearby(state,a,b))pair??=[a,b];
    if(!pair&&region<2){const exit=[...state.room.exits].sort((a,b)=>b.x-a.x)[0];await walk(exit);await call('/rooms/exits/'+exit.id,{});state=await call('/state');}
  }
  assert(pair,'Natural first-floor enemy pair must be close enough for optional group');await walk(pair[0]);
  await page.goto(base);await page.evaluate(t=>sessionStorage.setItem('token',t),token);await page.reload();await page.locator('canvas').waitFor();
  await page.getByText('Encontro opcional com grupo pequeno',{exact:true}).click();
  await page.locator('.group-start').getByRole('checkbox',{name:new RegExp('#'+pair[0].id+' ·')}).check();
  await page.locator('.group-start').getByRole('checkbox',{name:new RegExp('#'+pair[1].id+' ·')}).check();
  await page.getByRole('button',{name:'Iniciar encontro em grupo',exact:true}).click();
  await page.getByRole('region',{name:'Encontro em grupo'}).waitFor();state=await call('/state');assert(state.encounter&&state.encounter.size===2);const id=state.encounter.id;
  await page.locator('.encounter-panel').getByRole('radio').nth(1).check();
  await page.waitForFunction(()=>document.querySelector('main')?.getAttribute('aria-busy')==='false');
  await page.reload();await page.getByRole('button',{name:'Defender do grupo',exact:true}).waitFor();
  assert.equal((await call('/state')).encounter.id,id);
  await page.getByRole('button',{name:'Defender do grupo',exact:true}).click();await page.waitForFunction(()=>document.querySelector('main')?.getAttribute('aria-busy')==='false');
  state=await call('/state');assert.equal(state.encounter.turn,1);assert.equal(state.encounter.last_round.length,3);
  await page.screenshot({path:'/tmp/web08-group-browser.png',fullPage:true});
  assert.deepEqual(errors,[]);console.log('PASS: natural small group, checkbox start, target selection, round order, damage and reload restore through the browser');
 }finally{await browser.close()}
})().catch(e=>{console.error(e);process.exit(1)});
