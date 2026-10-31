import type { State } from '../api';
import {cityPaths,buildingEntrances} from './paths';
export {isVillagePath} from './paths';
export type Placement={kind:string;x:number;y:number;width?:number;height?:number;solid?:boolean};
const key=(x:number,y:number)=>`${x},${y}`;
/** Conservative visual-only reserved mask. Never modifies authoritative walls or route rules. */
export function placementMask(s:Pick<State,'map'|'room'>):Set<string>{
 const m=s.map,mask=new Set<string>(),walls=new Set(m.walls.map(p=>p.join(',')));
 const reserve=(x:number,y:number,r=1)=>{for(let yy=y-r;yy<=y+r;yy++)for(let xx=x-r;xx<=x+r;xx++)mask.add(key(xx,yy));};
 const goals:number[][]=[[2,2],...s.room.exits.map(e=>[e.x,e.y]),...(m.npc?[m.npc]:[]),...(m.service_npcs??[]).map(n=>[n.x,n.y]),...(m.gather_nodes??[]).map(n=>[n.x,n.y]),...(m.lunar_resources??[]).map(n=>[n.x,n.y]),...Object.values(m.monsters)];
 if(m.portal)goals.push(m.portal);
 goals.forEach(([x,y])=>reserve(x,y,1));
 // Required routes from the stable saved spawn; no random decoration along narrow corridors.
 const queue:[[number,number]]|[number,number][]=[[2,2]],parent=new Map<string,string>();parent.set('2,2','');
 for(let i=0;i<queue.length;i++){const [x,y]=queue[i];for(const [dx,dy] of [[1,0],[0,1],[-1,0],[0,-1]]){const a=x+dx,b=y+dy,k=key(a,b);if(a<1||b<1||a>=m.width-1||b>=m.height-1||walls.has(k)||parent.has(k))continue;parent.set(k,key(x,y));queue.push([a,b]);}}
 for(const [x,y] of goals){let k=key(x,y);if(!parent.has(k))k=[[x+1,y],[x-1,y],[x,y+1],[x,y-1]].map(p=>p.join(',')).find(p=>parent.has(p))??'';while(k){mask.add(k);k=parent.get(k)??'';}}
 if(s.room.kind==='CITY'){for(const k of cityPaths(s))mask.add(k);for(const d of buildingEntrances(s))reserve(d.x,d.y,1);}
 // Arena's center is intentionally clear; ornamental runes are flat and exempt.
 if(['BOSS','SECRET_DUNGEON'].includes(s.room.kind))for(let y=4;y<m.height-4;y++)for(let x=5;x<m.width-5;x++)mask.add(key(x,y));
 return mask;
}
export function canPlace(p:Placement,mask:Set<string>,width:number,height:number):boolean {
 const w=p.width??1,h=p.height??1;
 if(p.x<1||p.y<1||p.x+w>=width||p.y+h>=height)return false;
 for(let y=p.y;y<p.y+h;y++)for(let x=p.x;x<p.x+w;x++)if(mask.has(key(x,y)))return false;
 return true;
}
