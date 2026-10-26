import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import vm from 'node:vm';
import {pathToFileURL} from 'node:url';
import {resolve} from 'node:path';
import {core,mini} from './runtime.mjs';
mini.miniAllStrings();
const [scorePath='build/mixed.json', sourcePath='build/lantern.strudel.js', modulePath] = process.argv.slice(2);
const score = JSON.parse(await readFile(scorePath,'utf8'));
const source = await readFile(sourcePath,'utf8');
const executable=source.replace(/^await Promise\.all\(preload\);$/m,'')
 .replace(/^\/\/ Preload acoustic percussion[^]*?^\/\/ mini-on\n/m,'');
let cpm;
const pattern=vm.runInNewContext(executable,{...core,setcpm:x=>cpm=x,getAudioContext:()=>null,getFontBufferSource:()=>null},{timeout:20000});
assert.equal(typeof pattern.queryArc,'function');
assert(Math.abs(cpm-score.bpm/4)<1e-5);
if(modulePath) {
 const song=await import(pathToFileURL(resolve(modulePath)).href);
 assert(Math.abs(song.cps-score.bpm/240)<1e-10);
 assert.equal(song.beats,score.beats);
 const modulePattern=song.createPattern({...core,setcpm:()=>{throw new Error('Consumer owns tempo');}});
 const signature=p=>p.queryArc(0,score.beats/2).filter(h=>h.hasOnset()).map(h=>({
  begin:Number(h.whole.begin),end:Number(h.whole.end),value:h.value,
 }));
 assert.deepEqual(signature(modulePattern),JSON.parse(JSON.stringify(signature(pattern))), 'Module differs from REPL pattern');
}
const wanted=Object.entries(score.parts).flatMap(([part,rows])=>rows.map(([at,len,pitch,level])=>({at,len,pitch:typeof pitch==='string'?core.noteToMidi(pitch):pitch,part,level})));
const cycles=score.beats/4;
for(let repeat=0;repeat<2;repeat++) {
 const haps=pattern.queryArc(repeat*cycles,(repeat+1)*cycles).filter(h=>h.hasOnset());
 assert.equal(haps.length,wanted.length,'Lost or duplicated attacks');
 const remaining=haps.map(h=>({at:Number(h.whole.begin)*4-repeat*score.beats,len:Number(h.whole.end.sub(h.whole.begin))*4*(h.value.clip??1),value:h.value}));
 for(const e of wanted) {
  const sound=score.voices?.[e.part]?.sound??(['kick','snare','hat'].includes(e.part)?(e.part==='kick'?'sine':'white'):'triangle');
  const index=remaining.findIndex(h=>Math.abs(h.at-e.at)<2e-5 && Math.abs(h.len-e.len)<2e-5 && h.value.s===sound && (typeof h.value.note==='number'?h.value.note:core.noteToMidi(h.value.note))===e.pitch);
  assert(index>=0,`Missing/mutated ${e.part} ${e.pitch} at ${e.at}`);
  const [h]=remaining.splice(index,1);
  const bus=['kick','snare','hat'].includes(e.part)?'drums':e.part;
  const drumScale=e.part==='snare'?(score.drum_mix?.snare??.45):e.part==='hat'?(score.drum_mix?.hat??.20):1;
  assert(Math.abs(h.value.gain-e.level*score.mix[bus]*drumScale)<1e-7,'Gain changed');
 }
}
console.log(JSON.stringify({structural:true,events:wanted.length,repetitions:2,seconds:score.loop_seconds}));
