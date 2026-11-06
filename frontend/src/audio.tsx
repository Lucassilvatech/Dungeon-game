import {useEffect,useState} from 'react';
let context:AudioContext|undefined;
let volume=0;
let last=0;
export function sound(kind:'attack'|'hurt'|'win'|'interaction'|'ui'){
 if(volume<=0||typeof window==='undefined'||!window.AudioContext)return;
 const now=performance.now();if(now-last<40)return;last=now;
 try{
  context??=new AudioContext();void context.resume().catch(()=>{});
  const frequency={attack:440,hurt:120,win:880,interaction:660,ui:550}[kind];
  const oscillator=context.createOscillator(),gain=context.createGain();
  const time=context.currentTime;oscillator.type=kind==='hurt'?'triangle':'square';oscillator.frequency.setValueAtTime(frequency,time);oscillator.frequency.exponentialRampToValueAtTime(kind==='win'?1320:frequency*.8,time+.1);
  gain.gain.setValueAtTime(volume*.12,time);gain.gain.exponentialRampToValueAtTime(.0001,time+.12);oscillator.connect(gain);gain.connect(context.destination);oscillator.start(time);oscillator.stop(time+.13);
  oscillator.onended=()=>{oscillator.disconnect();gain.disconnect()};
 }catch{/* Audio is optional: browser policy or unavailable device never blocks play. */}
}
export function AudioControls(){
 const [level,setLevel]=useState(()=>{try{return Math.max(0,Math.min(100,Number(localStorage.getItem('dungeon_audio')??0)||0))}catch{return 0}});
 useEffect(()=>{volume=level/100;try{localStorage.setItem('dungeon_audio',String(level))}catch{}},[level]);
 return <div className="audio-controls"><label>Áudio opcional <input aria-label="Volume do jogo" type="range" min="0" max="100" value={level} onChange={e=>{const value=Number(e.target.value);volume=value/100;setLevel(value);sound('ui')}}/></label><button className="quiet" onClick={()=>{setLevel(level>0?0:35);volume=level>0?0:.35;sound('ui')}}>{level>0?'Silenciar':'Ativar áudio'}</button></div>
}
