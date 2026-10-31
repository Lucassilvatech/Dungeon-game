import {useEffect,useState} from 'react';
import {api} from './api';
import {LunarGuild} from './LunarGuild';
type Lot={lot_id:number;weight_g:number;weight_mg:string;state:string};
export function LunarWallet({busy,action}:{busy:boolean;action:(path:string,body:unknown)=>void}){
 const [wallet,setWallet]=useState<any>(null),[error,setError]=useState(''),[parts,setParts]=useState<Record<number,string>>({});
 useEffect(()=>{let live=true;void api('/lunar/wallet').then(w=>{if(live){setWallet(w);setError('')}}).catch(e=>{if(live)setError(e.message)});return()=>{live=false}},[busy]);
 const split=(r:Lot)=>{const g=Number(parts[r.lot_id]);if(!Number.isSafeInteger(g)||g<1||g>=r.weight_g){setError('O primeiro fragmento deve ter entre1g e o peso da pepita menos1g.');return}if(confirm(`Dividir Pepita #${r.lot_id}: ${g}g + ${r.weight_g-g}g, sem taxa nem perda?`))action(`/lunar/lots/${r.lot_id}/split`,{request_id:crypto.randomUUID(),fragments_g:[g,r.weight_g-g]})};
 return <><h2>Minério e Moedas Lunares</h2>{error&&<p role="alert">{error}</p>}{!wallet&&!error&&<p>Carregando carteira…</p>}{wallet&&<>
 <p>Estado: {wallet.legacy_conversion_active?'LUNAR — conversão concluída':'LEGADO — em migração'}</p>{!wallet.legacy_conversion_active&&<p>Saldo legado — em migração: {wallet.legacy_balance}. A carteira Lunar não é saldo adicional.</p>}
 <p>Dívida separada da carteira: {wallet.debt_weight_mg} mg</p><p>Saldo monetário: {(BigInt(wallet.coin_total_weight_mg)/1000n).toString()} g · {wallet.coin_total_weight_mg} mg</p><p>Minério em pepitas: {wallet.mineral_weight_mg} mg</p><p>Massa física total: {wallet.weight_mg} mg</p>
 <ul>{[['coin_small','Pequenas'],['coin_medium','Médias'],['coin_large','Grandes']].map(([k,n])=><li key={k}>Moedas {n}: {wallet.assets[k]?.quantity??'0'}</li>)}</ul>
 <h3>Pepitas individuais</h3>{wallet.lots.length===0&&<p>Nenhuma pepita na carteira.</p>}{wallet.lots.map((r:Lot)=><article key={r.lot_id}><h4>Pepita #{r.lot_id} · {r.weight_g} g</h4><label>Primeiro fragmento da pepita #{r.lot_id} (g)<input type="number" min={1} max={r.weight_g-1} value={parts[r.lot_id]??''} onChange={e=>setParts({...parts,[r.lot_id]:e.target.value})}/></label><p>Restante: {parts[r.lot_id]&&Number(parts[r.lot_id])>0?r.weight_g-Number(parts[r.lot_id]):r.weight_g} g</p><button disabled={busy||r.weight_g<2} onClick={()=>split(r)}>Dividir Pepita #{r.lot_id}</button></article>)}
 </>}<LunarGuild busy={busy} action={action}/></>;
}
