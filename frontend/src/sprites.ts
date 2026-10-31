import Phaser from 'phaser';
import manifest from './visual/atlas.json';
/** Shipping PNG atlases; original source and compiler are versioned with the game. */
export function preloadSprites(scene:Phaser.Scene){
 for(const [name,e] of Object.entries(manifest)){
  scene.load.spritesheet(name,'/assets/pixel/'+e.file,{frameWidth:'frameWidth' in e.frames?48:name==='tiles'?32:name==='effects'?64:128,frameHeight:'frameWidth' in e.frames?64:name==='tiles'?32:name==='effects'?64:128});
 }
}
export function createSprites(scene:Phaser.Scene){for(const key of Object.keys(manifest)){
 if(!scene.textures.exists(key))throw Error('Asset não carregado: '+key);
 scene.textures.get(key).setFilter(Phaser.Textures.FilterMode.NEAREST);
}}
export const frames={tiles:manifest.tiles.frames,effects:manifest.effects.frames,scenery:manifest.scenery.frames,bosses:manifest.bosses.frames};
