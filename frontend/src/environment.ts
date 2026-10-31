import Phaser from 'phaser';
import type {State} from './api';
import {frames} from './sprites';
import {resolveTheme,tileHash,type VisualThemeProfile} from './visual/themes';
import {cityPaths,buildingEntrances} from './visual/paths';
import {canPlace,placementMask} from './visual/placement';
type Image=Phaser.GameObjects.Image;
const scenery=frames.scenery as Record<string,number>,effects=frames.effects as Record<string,number>,tiles=frames.tiles as Record<string,number>;
const sizes:Record<string,[number,number]>={tree:[3,4],well:[2,3],recovery_tent:[5,4],ruin:[2,3],statue:[2,3],obelisk:[2,3],crystal:[2,2],barrel:[1,2],crate:[2,2]};
/** One terrain texture per room, bounded lights/particles, no per-frame terrain rebuild. */
export class Environment {
 objects:Phaser.GameObjects.GameObject[]=[];
 props:{image:Image;canopy:boolean}[]=[];
 lights:{image:Image;phase:number;flame?:Image}[]=[];
 particles:Image[]=[];
 theme:VisualThemeProfile;
 constructor(private scene:Phaser.Scene,private state:State){this.theme=resolveTheme(state);this.build();}
 image(x:number,y:number,atlas:string,frame:number,depth:number,scale=2){const sp=this.scene.add.image(Math.round(x),Math.round(y),atlas,frame).setScale(scale).setDepth(depth);this.objects.push(sp);return sp;}
 light(x:number,y:number,ritual=false,flame=true){
  if(this.lights.length>=12)return;
  const im=this.image(x,y,'effects',effects[ritual?'glow_cyan':'glow_warm'],8001,3).setBlendMode(Phaser.BlendModes.ADD);
  const fire=flame?this.image(x,y+12,'effects',effects.flame_0,110+y,1).setOrigin(.5,1):undefined;
  this.lights.push({image:im,phase:this.lights.length*1.73+x%7,flame:fire});
 }
 prop(kind:string,x:number,y:number,variant=0){
  if(this.theme.lightProfile!=='day'&&kind==='tree')kind='ruin';
  const name=kind==='tree'?'tree_green_0'+(variant%3+1):kind;
  const sp=this.image(x*32+16,(y+1)*32,name in scenery?'scenery':'effects',scenery[name]??effects[name]??effects.rock,100+(y+1)*32,name in scenery?2:0.75).setOrigin(.5,1);
  if(['rug','moss','flower','bones'].includes(kind))sp.setDepth(2);
  this.props.push({image:sp,canopy:kind==='tree'});
  if(kind==='torch'){sp.setVisible(false);this.light(x*32+16,y*32+7);}
  if(kind==='crystal'||kind==='obelisk')this.light(x*32+16,y*32,true,false);
 }
 build(){
  const {map:m,room}=this.state,seed=m.seed??0,p=this.theme;
  const ground=this.scene.add.renderTexture(0,0,m.width*32,m.height*32).setOrigin(0).setScale(1).setDepth(0);this.objects.push(ground);
  const buildings=new Set<string>();
  for(const b of m.buildings??[])for(let y=b.y;y<b.y+b.height;y++)for(let x=b.x;x<b.x+b.width;x++)buildings.add(`${x},${y}`);
  const paths=cityPaths(this.state),entrances=buildingEntrances(this.state);
  ground.beginDraw();
  for(let y=0;y<m.height;y++)for(let x=0;x<m.width;x++){
   const hash=tileHash(seed,x,y),set=paths.has(`${x},${y}`)?'path':p.groundSet;
   ground.batchDrawFrame('tiles',tiles[set+'_'+hash%8],x*32,y*32);
  }
  for(const [x,y]of m.walls){if(buildings.has(`${x},${y}`))continue;const interiorCity=room.kind==='CITY'&&x>0&&y>0&&x<m.width-1&&y<m.height-1;const base=p.groundSet==='grass'?'path':p.groundSet;ground.batchDrawFrame('tiles',tiles[(interiorCity?'grass_':base+'_wall_')+tileHash(seed,x,y)%8],x*32,y*32);}
  ground.endDraw();
  for(const [i,b]of(m.buildings??[]).entries()){
   const entrance=entrances[i];
   const sp=this.image(entrance.x*32+16,entrance.y*32,'scenery',scenery['house_0'+(i%3+1)],100+(b.y+b.height)*32,2).setOrigin(.5,1);this.props.push({image:sp,canopy:false});
  }
  if(room.kind==='CITY')for(const [x,y]of m.walls)if(!buildings.has(`${x},${y}`)&&x>0&&y>0&&x<m.width-1&&y<m.height-1)this.prop('rock',x,y);
  const mask=placementMask(this.state),flat=new Set(['rug','moss','flower','bones']);
  for(const d of m.decorations??[]){
   if(['counter','table','board','rug'].includes(d.kind)&&d.width){
    if(d.kind==='rug'){this.image((d.x+d.width/2)*32,(d.y+(d.height??1)/2)*32,'effects',effects.rug,2,Math.max(2,d.width/2));continue;}
    for(let xx=0;xx<d.width;xx+=2)this.image((d.x+xx+1)*32,(d.y+(d.height??1))*32,'effects',effects[d.kind==='board'?'sign':d.kind],100+(d.y+(d.height??1))*32,1.5).setOrigin(.5,1);
    continue;
   }
   if(d.kind==='recovery_tent'){this.prop(d.kind,d.x+(d.width??4)/2-0.5,d.y+(d.height??3)-1);continue;}
   const [w,h]=sizes[d.kind]??[1,1];
   if(!flat.has(d.kind)&&!canPlace({...d,x:d.x-Math.floor(w/2),y:d.y-h+1,width:w,height:h},mask,m.width,m.height))continue;
   this.prop(d.kind,d.x,d.y,tileHash(seed,d.x,d.y));
  }
  for(let y=3;y<m.height-2;y++)for(let x=2;x<m.width-2;x++){
   const h=tileHash(seed+97,x,y);if(mask.has(`${x},${y}`)||buildings.has(`${x},${y}`))continue;
   if(room.kind==='CITY'&&h%67===0){if(canPlace({kind:'tree',x:x-1,y:y-3,width:3,height:4},mask,m.width,m.height))this.prop('tree',x,y,h);}
   else if(h%29===0)this.prop(p.vegetationSet[h%p.vegetationSet.length],x,y,h);
   else if(room.kind!=='CITY'&&h%151===0&&canPlace({kind:'ruin',x:x-1,y:y-2,width:2,height:3},mask,m.width,m.height))this.prop('ruin',x,y);
  }
  for(const n of m.service_npcs??[]){const kind=n.id.includes('alchemist')?'alchemy':n.id.includes('blacksmith')?'forge':'crate';const x=n.x+3,y=n.y+1;if(canPlace({kind,x:x-1,y:y-2,width:3,height:3},mask,m.width,m.height))this.prop(kind,x,y);}
  for(const e of room.exits.filter(e=>!entrances.some(d=>d.exitId===e.id)))this.image(e.x*32+16,(e.y+1)*32,'effects',effects.portal,90+(e.y+1)*32,0.75).setOrigin(.5,1);
  if(['BOSS','SECRET_DUNGEON'].includes(room.kind)){
   const boss=m.enemies.find(e=>['boss','warden','champion'].includes(e.species)||e.category==='boss');
   const x=(boss?.x??Math.floor(m.width/2))*32+16,y=(boss?.y??Math.floor(m.height/2))*32+16;
   this.image(x,y,'effects',effects.rune,3,5);this.light(x,y,true,false);
   for(const [xx,yy]of[[m.width-3,5],[m.width-3,11],[m.width-3,17],[m.width-3,m.height-3],[4,m.height-3],[8,m.height-3]])if(canPlace({kind:'obelisk',x:xx-1,y:yy-2,width:2,height:3},mask,m.width,m.height))this.prop('obelisk',xx,yy);
  }
  if(p.lightProfile!=='day'){
   for(let x=4;x<m.width-2;x+=8){this.light(x*32,52,p.lightProfile==='ritual');if(x+3<m.width-2&&!mask.has(`${x+3},1`))this.image((x+3)*32,58,'effects',effects.banner,125,1).setOrigin(.5,1);}
   this.objects.push(this.scene.add.rectangle(0,0,m.width*32,m.height*32,0x080d20,p.ambientProfile).setOrigin(0).setDepth(8000));
  }
  for(let i=0;i<12;i++)this.particles.push(this.image((i*137+seed)%(m.width*32),(i*83)%(m.height*32),'effects',p.particleProfile==='leaves'?effects.flower:effects.smoke,8002,p.particleProfile==='leaves'?0.12:0.25).setAlpha(.25));
 }
 update(time:number,reduced:boolean,hero:Phaser.GameObjects.Sprite){
  const view=this.scene.cameras.main.worldView;
  for(const l of this.lights){l.image.setVisible(Phaser.Geom.Rectangle.Overlaps(view,l.image.getBounds()));l.image.setAlpha(reduced?.8:.8+Math.sin(time/240+l.phase)*.12);l.flame?.setFrame(effects['flame_'+(reduced?0:Math.floor(time/140+l.phase)%4)]);}
  for(const [i,sp]of this.particles.entries()){sp.setVisible(!reduced);if(!reduced)sp.setPosition(Math.round((i*137+time/110)%(this.state.map.width*32)),Math.round((i*83+time/300)%(this.state.map.height*32)));}
  for(const {image,canopy}of this.props)if(canopy)image.setAlpha(image.getBounds().contains(hero.x,hero.y-15)&&hero.y<image.y?.55:1);
 }
 destroy(){for(const obj of this.objects)obj.destroy();this.objects=[];}
}
