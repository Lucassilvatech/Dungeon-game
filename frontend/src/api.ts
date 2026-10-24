export type Item = {id:number;name:string;kind:string;quantity:number;equipped:boolean;location:string};
export type Battle = {id:number;monster:string;hp:number;turn:number;status:string;claimed:boolean};
export type State = {character:{id:number;name:string;level:number;xp:number;hp:number;energy:number;strength:number;defense:number;coins:number;floor:number;x:number;y:number};inventory:Item[];battle:Battle|null;unlocked_floor:number;map:{width:number;height:number;walls:number[][];npc:number[];monsters:Record<string,number[]>;portal:number[]}};
export async function api(path:string, body?:unknown) {
 const token=sessionStorage.getItem('token');
 const r=await fetch('/api'+path,{method:body===undefined?'GET':'POST',headers:{'Content-Type':'application/json',...(token?{Authorization:'Bearer '+token}:{})},body:body===undefined?undefined:JSON.stringify(body)});
 const data=await r.json();if(!r.ok)throw new Error(typeof data.detail==='string'?data.detail:'Revise os dados informados');return data;
}
