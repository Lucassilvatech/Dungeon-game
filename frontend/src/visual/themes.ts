import type { State } from '../api';
export type ThemeId = 'SAFE_VILLAGE'|'SAFE_GUILD'|'COMMON_RUINS'|'MOSS_DUNGEON'|'CAVE'|'CRYPT'|'BOSS_RITUAL'|'SECRET_DUNGEON';
export type VisualThemeProfile = {
  id:ThemeId; groundSet:string; wallSet:string; propSet:string[]; vegetationSet:string[];
  palette:{label:string; accent:number}; lightProfile:'day'|'warm'|'teal'|'ritual';
  particleProfile:'leaves'|'dust'|'embers'; ambientProfile:number; bossProfile:string[];
};
const theme=(id:ThemeId,groundSet:string,wallSet:string,lightProfile:VisualThemeProfile['lightProfile'],props:string[],accent:number,bossProfile:string[]):VisualThemeProfile=>({id,groundSet,wallSet,propSet:props,vegetationSet:lightProfile==='day'?['flower','bush']:['moss','mushroom'],palette:{label:lightProfile==='day'?'#fff4ce':'#d0e4df',accent},lightProfile,particleProfile:lightProfile==='day'?'leaves':lightProfile==='ritual'?'embers':'dust',ambientProfile:lightProfile==='ritual'?0.16:lightProfile==='day'?0:0.08,bossProfile});
export const THEMES:Record<ThemeId,VisualThemeProfile>={
 SAFE_VILLAGE:theme('SAFE_VILLAGE','grass','village_wall','day',['tree','bush','flower','crate'],0xe2c789,['moss_colossus']),
 SAFE_GUILD:theme('SAFE_GUILD','wood','guild_wall','warm',['shelf','barrel','banner','table'],0xf0c279,['thorn_chief']),
 COMMON_RUINS:theme('COMMON_RUINS','ruins','ruins_wall','teal',['ruin','rock','moss','mushroom'],0x8cc3b1,['thorn_chief','basalt_drake']),
 MOSS_DUNGEON:theme('MOSS_DUNGEON','moss','moss_wall','teal',['ruin','moss','mushroom','rock'],0x9ccda3,['moss_colossus','thorn_chief']),
 CAVE:theme('CAVE','cave','cave_wall','teal',['crystal','rock','bones'],0x8cbecb,['basalt_drake']),
 CRYPT:theme('CRYPT','crypt','crypt_wall','teal',['statue','bones','ruin'],0xb1b6d1,['abyssal_warden']),
 BOSS_RITUAL:theme('BOSS_RITUAL','ritual','ritual_wall','ritual',['obelisk','crystal','statue'],0xe6ba7b,['moss_colossus']),
 SECRET_DUNGEON:theme('SECRET_DUNGEON','secret','secret_wall','ritual',['obelisk','crystal','bones'],0x87d1df,['abyssal_warden']),
};
export function resolveTheme(s:Pick<State,'room'|'map'>):VisualThemeProfile {
 const k=s.room.kind;
 if(k==='BOSS')return THEMES.BOSS_RITUAL;
 if(k==='SECRET_DUNGEON')return THEMES.SECRET_DUNGEON;
 if(k==='CITY')return THEMES.SAFE_VILLAGE;
 if(['GUILD','TRAINING','BUILDING_INTERIOR'].includes(k))return THEMES.SAFE_GUILD;
 return THEMES[({moss_stone:'MOSS_DUNGEON',wild_ruins:'COMMON_RUINS',crystal_bones:'CAVE',abandoned_wood:'CRYPT'} as Record<string,ThemeId>)[s.map.theme]??'COMMON_RUINS'];
}
export function visualHash(value:string):number {let h=2166136261;for(let i=0;i<value.length;i++)h=Math.imul(h^value.charCodeAt(i),16777619);return h>>>0;}
export function tileHash(seed:number,x:number,y:number):number{return visualHash(`${seed}:${x}:${y}`);}
