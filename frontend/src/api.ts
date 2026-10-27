import type { DeathReceipt } from "./DeathEconomy";
import type { Room } from "./types";
export type Item = {
  power:number;
  id: number;
  name: string;
  kind: string;
  quantity: number;
  equipped: boolean;
  location: string;
  stackable: boolean;
  max_stack_size: number;
  description: string;
  definition: string;
  protected: boolean;
};
export type Battle = {
  id: number;
  enemy_id: number;
  monster: string;
  hp: number;
  turn: number;
  status: string;
  claimed: boolean;
  reward_amount: number | null;
};
export type Enemy = {
  category?:string;
  category_label?: string;
  name_color?: string;
  id: number;
  spawn_key: string;
  species: string;
  name: string;
  x: number;
  y: number;
  hp: number;
  max_hp: number;
  level: number;
  state: "ALIVE" | "IN_COMBAT" | "DYING" | "DEAD";
  ai_state: string;
};
export type Encounter={id:number;status:string;turn:number;size:number;selected_enemy_id:number;enemies:Enemy[];last_round:{actor:string;enemy_id?:number;damage:number}[];damage_dealt:number;damage_received:number};
export type ResourceNode={id:number;name:string;definition:string;x:number;y:number;remaining:number;capacity:number;enabled:boolean};
export type State = {
 economy_mode?:"LUNAR"|"LEGACY";guild_balance?:string;
 collection_capacity:{used:number;limit:number};
  encounter:Encounter|null;
  encounter_rules:{max_enemies:number;radius:number};
  guild_rewards:{count:number;total:number;groups:Record<string,number>};
  reward_records:Battle[];
  fast_destinations:{id:string;name:string;danger_tier:number}[];
  guild_treasury:string;
  attributes: Record<
    string,
    { base: number; equipment: number; temporary: number; effective: number }
  >;
  next_boss_chance: number;
  death: DeathReceipt | null;
  coins_exact: string;
  reserved_gold: string;
  expedition: {
    id: number;
    room_id: string;
    status: "ACTIVE" | "COMPLETED" | "FLED" | "FAILED";
    alive_enemies: number;
    can_leave: boolean;
  } | null;
  events: { id: number; kind: string; payload: Record<string, unknown> }[];
  room: Room;
  atlas: {
    connections: { source: string; target: string | null }[];
    rooms: Room[];
    secrets: { found: number; total: number };
  };
  raid: {
    id: number;
    invite: string;
    leader_id: number;
    participants: { id: number; name: string }[];
    cooperative_combat: false;
  } | null;
  character: {
    id: number;
    name: string;
    level: number;
    xp: number;
    hp: number;
    energy: number;
    unspent_attribute_points: number;
    attribute_point_debt: number;
    strength: number;
    defense: number;
    coins: number;
    floor: number;
    room_id: string;
    x: number;
    y: number;
  };
  inventory: Item[];
  battle: Battle | null;
  unlocked_floor: number;
  map: {
 gather_nodes:ResourceNode[];
    enemies: Enemy[];
    seed?: number;
    npc_name?: string;
    decorations?: {
      kind: string;
      x: number;
      y: number;
      width?: number;
      height?: number;
      solid?: boolean;
    }[];
    npcs?: { id: string; name: string; x: number; y: number; walk: boolean }[];
    width: number;
    height: number;
    walls: number[][];
    theme: string;
    enemy_names: Record<string, string>;
    buildings?: {
      x: number;
      y: number;
      width: number;
      height: number;
      name: string;
    }[];
    recommended_level?: number;
    difficulty?: string;
    recommended_group?: number;
    npc: number[] | null;
    monsters: Record<string, number[]>;
    portal: number[] | null;
  };
};
export class APIError extends Error {
  constructor(message:string,public status:number){super(message);this.name="APIError";}
}
export async function api(path:string,body?:unknown) {
  const token=sessionStorage.getItem("token");
  const controller=new AbortController();
  const timer=setTimeout(()=>controller.abort(),15000);
  try {
    const r=await fetch("/api"+path,{
      method:body===undefined?"GET":"POST", signal:controller.signal,
      headers:{"Content-Type":"application/json",...(token&&!["/auth/login","/auth/register"].includes(path)?{Authorization:"Bearer "+token}:{})},
      body:body===undefined?undefined:JSON.stringify(body)
    });
    const data=await r.json().catch(()=>({detail:"Resposta inválida do servidor."}));
    if(!r.ok){
      if(r.status===401&&!path.startsWith("/auth/")){
        sessionStorage.removeItem("token");window.dispatchEvent(new Event("dungeon:session-expired"));
      }
      throw new APIError((typeof data.detail==="string"?data.detail:"Revise os dados informados")+(r.status===429&&data.retry_after?` Aguarde ${data.retry_after}s.`:""),r.status);
    }
    return data;
  }catch(e){
    if(e instanceof APIError)throw e;
    throw new APIError((e as Error).name==="AbortError"?"Tempo limite excedido. Tente atualizar novamente.":"Falha de conexão com o servidor. Confira a rede e tente novamente.",0);
  }finally{clearTimeout(timer);}
}
