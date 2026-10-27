import {useEffect,useState} from 'react';
import {api} from './api';
type Quote={asset_code:string;weight_mg:string;quantity:string;price_units:string;quote:string};
export function LunarGuild({busy,action}:{busy:boolean;action:(path:string,body:unknown)=>void}){
 const [data,setData]=useState<{active:boolean;guild_coin_mg:string;quotes:Quote[]}|null>(null),[error,setError]=useState('');
 useEffect(()=>{let alive=true;void api('/lunar/guild-quotes').then(d=>{if(alive){setData(d);setError('')}}).catch(e=>{if(alive)setError(e.message)});return()=>{alive=false}},[busy]);
 return <section><h3>Venda de Minério Lunar à Guilda</h3><p>Negocie junto à recepcionista. A Guilda compra com seu próprio caixa; o pagamento pode abater dívida médica. Comprar minério não o transforma em moeda.</p>
 {error&&<p role="alert">{error}</p>}{data&&<><p>Caixa da Guilda: {data.guild_coin_mg} mg de moeda.</p>{!data.quotes.length&&<p>A Guilda não publicou preços de compra de minério.</p>}{data.quotes.map(q=><article key={q.asset_code}><p>Pepita {BigInt(q.weight_mg)/1000n+''} g · Quantidade: {q.quantity} · Preço: {q.price_units} g de moeda por pepita</p><button disabled={busy||!data.active||BigInt(q.quantity)<1n} onClick={()=>{if(confirm(`Vender uma pepita de ${BigInt(q.weight_mg)/1000n} g por ${q.price_units} g de moeda?`))action('/lunar/guild-sell',{asset_code:q.asset_code,quote:q.quote,request_id:crypto.randomUUID()})}}>Vender pepita {BigInt(q.weight_mg)/1000n+''} g</button></article>)}</>}
 </section>;
}
