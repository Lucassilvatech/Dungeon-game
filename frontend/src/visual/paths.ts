import type {State} from '../api';
const key=(x:number,y:number)=>`${x},${y}`;
export const isVillagePath=(x:number,y:number)=>Math.abs(x-10)<2||Math.abs(y-18)<2||y===10;
/** Match real entry coordinates to facade before choosing decorative door coordinates. */
export function buildingEntrances(s:Pick<State,'map'|'room'>){return (s.map.buildings??[]).map(b=>{
 const exit=s.room.exits.find(e=>e.x>=b.x&&e.x<b.x+b.width&&Math.abs(e.y-(b.y+b.height))<=1);
 return {building:b,x:exit?.x??b.x+Math.floor((b.width-1)/2),y:exit?.y??b.y+b.height,exitId:exit?.id};
});}
export function cityPaths(s:Pick<State,'map'|'room'>):Set<string>{
 const m=s.map,paths=new Set<string>(),walls=new Set(m.walls.map(p=>p.join(',')));
 if(s.room.kind!=='CITY')return paths;
 for(let y=1;y<m.height-1;y++)for(let x=1;x<m.width-1;x++)if(isVillagePath(x,y)&&!walls.has(key(x,y)))paths.add(key(x,y));
 for(const door of buildingEntrances(s)){
  if(walls.has(key(door.x,door.y)))continue;
  const queue:[number,number][]=[[door.x,door.y]],parents=new Map<string,string>([[key(door.x,door.y),'']]);let found='';
  for(let i=0;i<queue.length;i++){const [x,y]=queue[i],k=key(x,y);if(paths.has(k)){found=k;break;}
   for(const [dx,dy]of [[0,1],[-1,0],[1,0],[0,-1]]){const a=x+dx,b=y+dy,n=key(a,b);if(a<1||b<1||a>=m.width-1||b>=m.height-1||walls.has(n)||parents.has(n))continue;parents.set(n,k);queue.push([a,b]);}
  }
  while(found){paths.add(found);found=parents.get(found)??'';}
 }
 return paths;
}
