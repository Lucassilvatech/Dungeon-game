import { useState } from "react";
type Props = {busy:boolean; rooms:any[]; events:any[]; canManage:boolean; preview:(body:any)=>Promise<void>; cancel:(id:string)=>void};
export function WorldEvents({busy,rooms,events,canManage,preview,cancel}:Props) {
  const [name,setName]=useState("Mais monstros raros");
  const [description,setDescription]=useState("Aumenta a presença de monstros raros nas novas aventuras.");
  const [region,setRegion]=useState("procedural");
  const [intensity,setIntensity]=useState(100);
  const [duration,setDuration]=useState(60);
  const [start,setStart]=useState(new Date(Date.now()+60000).toISOString().slice(0,16));
  const [reason,setReason]=useState("");
  return <section><h3>Eventos do primeiro andar</h3><p>Eventos afetam somente encontros novos. Encontros ativos mantêm seus atributos e sorteios. Eventos sobrepostos usam o maior multiplicador.</p>
    {canManage&&<form onSubmit={e=>{e.preventDefault();void preview({operation_id:crypto.randomUUID(),action:"world.event_create",target:"first-floor",reason,params:{name,description,region,floor_id:1,effect:"rare_spawn",conditions:"new_adventures",intensity,duration_minutes:duration,starts_at:new Date(start+"Z").toISOString()}})}}>
      <label>Nome<input required maxLength={100} value={name} onChange={e=>setName(e.target.value)}/></label>
      <label>Descrição<textarea required maxLength={500} value={description} onChange={e=>setDescription(e.target.value)}/></label>
      <label>Andar<select><option>Primeiro andar</option></select></label>
      <label>Região afetada<select value={region} onChange={e=>setRegion(e.target.value)}><option value="procedural">Todas as novas aventuras procedurais</option><option value="all">Todo o primeiro andar</option>{rooms.filter(r=>["COMMON","COMBAT"].includes(r.kind)).map(r=><option key={r.id} value={r.id}>{r.name} (apenas se houver geração procedural nesta região)</option>)}</select></label>
      <label>Efeito<select><option>Aumentar chance de monstros raros</option></select></label>
      <label>Aumento percentual<input type="number" min={0} max={400} required value={intensity} onChange={e=>setIntensity(Number(e.target.value))}/><small>100% multiplica por dois. A chance final de raros nunca passa de 25%; não altera a chance de boss.</small></label>
      <label>Início (UTC)<input type="datetime-local" required value={start} onChange={e=>setStart(e.target.value)}/><small>Horário UTC explícito para evitar diferenças entre navegador e servidor.</small></label>
      <label>Duração em minutos<input type="number" required min={1} max={10080} value={duration} onChange={e=>setDuration(Number(e.target.value))}/></label>
      <p>Prévia: chance base 5% → {Math.min(25,5*(1+intensity/100))}%. Término: {start?new Date(new Date(start+"Z").getTime()+duration*60000).toISOString():"—"}. Condição: novas aventuras.</p>
      <label>Justificativa auditável<textarea required minLength={10} maxLength={500} value={reason} onChange={e=>setReason(e.target.value)}/></label>
      <button disabled={busy}>Revisar evento e impacto</button>
    </form>}
    <h3>Agenda e histórico</h3>{events.length===0?<p>Nenhum evento agendado.</p>:events.map(e=><article key={e.id}><h4>{e.name} · {e.state}</h4><p>{e.description}</p><p>Andar {e.floor_id} · {e.region} · {e.starts_at} → {e.ends_at} · {e.duration_minutes} minutos</p><p>{e.conditions}. {e.impact}</p>{canManage&&["ACTIVE","SCHEDULED"].includes(e.state)&&<button onClick={()=>cancel(e.id)}>Preparar cancelamento</button>}</article>)}
  </section>;
}
