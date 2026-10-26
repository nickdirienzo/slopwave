// Bound the offline audio graph for long, dry synth arrangements. Re-render
// preceding gates/releases as pre-roll, then retain only each interval's PCM.
import assert from 'node:assert/strict';
import {mkdtemp, readFile, writeFile, rm} from 'node:fs/promises';
import {tmpdir} from 'node:os';
import {join} from 'node:path';
import {watchBrowser, assertBrowser} from './browser-checks.mjs';

// Global/time-dependent effects and sampled tails need an uninterrupted graph.
export function canSegment(score) {
 return !score.sample_buffers && !score.soundfonts &&
  Object.values(score.voices??{}).every(v=>
   !['room','delay','phaser','tremolo','vib','noise'].some(k=>v[k]));
}

function pcm(wav) {
  assert.equal(wav.toString('ascii',0,4),'RIFF');
  let format, data;
  for(let pos=12;pos+8<=wav.length;) {
    const id=wav.toString('ascii',pos,pos+4),size=wav.readUInt32LE(pos+4);
    if(id==='fmt ')format=wav.subarray(pos+8,pos+8+size);
    if(id==='data')data=wav.subarray(pos+8,pos+8+size);
    pos+=8+size+(size%2);
  }
  assert(format&&data);
  assert.equal(format.readUInt16LE(0),1);
  assert.equal(format.readUInt16LE(2),2);
  assert.equal(format.readUInt32LE(4),44100);
  assert.equal(format.readUInt16LE(14),16);
  return {format,data};
}

export async function renderSegments(browser,url,score,output) {
  const rate=44100, frameBytes=4, cps=score.bpm/240;
  const maxGate=Object.values(score.parts).flat().reduce((max,e)=>Math.max(max,e[1]),0);
  const maxRelease=Math.max(.2,...Object.values(score.voices??{}).map(v=>v.release??.1));
  const preCycles=Math.ceil((maxGate+maxRelease*score.bpm/60)/4)+1;
  const end=score.beats/4, step=16, chunks=[], intervals=[];
  const temp=await mkdtemp(join(tmpdir(),'slopwave-render-'));
  let format;
  try {
    for(let start=0;start<end;start+=step) {
      const stop=Math.min(end,start+step),begin=Math.max(0,start-preCycles);
      const page=await browser.newPage({acceptDownloads:true});
      const errors=[],external=[];
      try {
        watchBrowser(page,errors);
        await page.route('**/*',route=>{
          const address=route.request().url();
          if(!address.startsWith(url+'/')&&!address.startsWith('blob:')){external.push(address);return route.abort();}
          return route.continue();
        });
        await page.goto(`${url}/?render_begin=${begin}&render_end=${stop}`);
        await page.waitForFunction(()=>window.__ready||window.__failure,{},{timeout:30000});
        assert.equal(await page.evaluate(()=>window.__failure),undefined);
        const downloadPromise=page.waitForEvent('download',{timeout:120000});
        await page.click('#render');
        const download=await downloadPromise;
        const file=join(temp,`${start}.wav`);
        await download.saveAs(file);
        assert.equal(await download.failure(),null);
        await assertBrowser(page,errors,external);
        const parsed=pcm(await readFile(file));
        if(format)assert.deepEqual(parsed.format,format);else format=parsed.format;
        const offset=Math.round((start-begin)/cps*rate);
        const frames=Math.round(stop/cps*rate)-Math.round(start/cps*rate);
        assert(parsed.data.length>=(offset+frames)*frameBytes);
        chunks.push(parsed.data.subarray(offset*frameBytes,(offset+frames)*frameBytes));
        assert.deepEqual(errors,[]);assert.deepEqual(external,[]);
        intervals.push({begin_cycle:begin,retain_begin_cycle:start,end_cycle:stop,frames});
        console.log(`Rendered bars ${start+1}–${stop}`);
      } finally {await page.close();}
    }
    const data=Buffer.concat(chunks),header=Buffer.alloc(44);
    header.write('RIFF',0);header.writeUInt32LE(36+data.length,4);header.write('WAVE',8);
    header.write('fmt ',12);header.writeUInt32LE(16,16);format.copy(header,20,0,16);
    header.write('data',36);header.writeUInt32LE(data.length,40);
    assert.equal(data.length/frameBytes,Math.round(score.loop_seconds*rate));
    await writeFile(output,Buffer.concat([header,data]));
    return {method:'bounded-dry-synth-segments',preroll_cycles:preCycles,intervals};
  } finally {await rm(temp,{recursive:true,force:true});}
}
