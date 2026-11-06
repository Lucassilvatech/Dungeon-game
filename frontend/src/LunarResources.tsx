import type {State} from './api';
import type {Target} from './types';
export function LunarResources({state,busy,target}:{state:State;busy:boolean;target:(t:Target)=>void}) {
 return <section className="lunar-resources" aria-label="Minério Lunar desta expedição">
 {(state.map.lunar_resources??[]).map(r=><article key={r.id} data-lunar-resource-id={r.id}>
  <h3>☾ Minério Lunar</h3><p>Peso: {BigInt(r.weight_mg)/1000n+''} g · Disponível</p>
  <button disabled={busy||!!state.battle||!!state.death} onClick={()=>target({kind:'lunar',id:r.id,x:r.x,y:r.y})}>{busy?'Aguarde…':'Coletar Minério Lunar'}</button>
 </article>)}
 </section>;
}
