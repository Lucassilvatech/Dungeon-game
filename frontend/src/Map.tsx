import {useEffect,useRef} from 'react';
import Phaser from 'phaser';
import type {State} from './api';
export function Map({state,onMove,onInteract}:{state:State;onMove:(dx:number,dy:number)=>void;onInteract:()=>void}) {
 const el=useRef<HTMLDivElement>(null);const live=useRef({state,onMove,onInteract});live.current={state,onMove,onInteract};
 useEffect(()=>{
 class World extends Phaser.Scene {
  art!:Phaser.GameObjects.Graphics;last=0;
  create(){this.art=this.add.graphics();this.input.keyboard?.on('keydown',(e:KeyboardEvent)=>{if(e.repeat)return;const moves:Record<string,number[]>={ArrowUp:[0,-1],w:[0,-1],ArrowDown:[0,1],s:[0,1],ArrowLeft:[-1,0],a:[-1,0],ArrowRight:[1,0],d:[1,0]};if(moves[e.key]){e.preventDefault();live.current.onMove(moves[e.key][0],moves[e.key][1]);}if(e.key==='e')live.current.onInteract();});}
  update(){const {state:s}=live.current;const g=this.art;g.clear();const tile=(x:number,y:number,color:number,inset=0)=>{g.fillStyle(color);g.fillRect(x*32+inset,y*32+inset,32-inset*2,32-inset*2);};
   for(let y=0;y<s.map.height;y++)for(let x=0;x<s.map.width;x++){tile(x,y,(x+y)%2?0x233f37:0x27473b);g.fillStyle(0x42604a);g.fillRect(x*32+5,y*32+7,3,3);}
   s.map.walls.forEach(([x,y])=>{tile(x,y,0x172b30);tile(x,y,0x48605d,3);g.fillStyle(0x779081);g.fillRect(x*32+3,y*32+3,26,3);});
   tile(...s.map.portal as [number,number],0x6bc6de,5);tile(...s.map.npc as [number,number],0xe4bb67,7);
   Object.entries(s.map.monsters).forEach(([name,[x,y]])=>{tile(x,y,name==='boss'?0xba655d:0x80c887,7);g.fillStyle(0x13232b);g.fillRect(x*32+10,y*32+12,3,3);g.fillRect(x*32+20,y*32+12,3,3);});
   tile(s.character.x,s.character.y,0xf0dfb0,8);g.fillStyle(0x6498b0);g.fillRect(s.character.x*32+8,s.character.y*32+17,16,11);
  }
 }
 const game=new Phaser.Game({type:Phaser.AUTO,width:512,height:384,parent:el.current!,pixelArt:true,backgroundColor:'#172b30',scene:World,banner:false});
 return()=>game.destroy(true);
 },[]);
 return <div className="canvas" ref={el} aria-label="Mapa jogável do andar"/>;
}
