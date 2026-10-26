import assert from 'node:assert/strict';
import {readFile,writeFile,mkdir} from 'node:fs/promises';
import {dirname,resolve} from 'node:path';
import {createHash} from 'node:crypto';
import {chromium} from 'playwright';
import {core} from './runtime.mjs';
const {noteToMidi}=core;
import {serve} from './server.mjs';
const [mode,scorePath='build/mixed.json',sourcePath='build/lantern.strudel.js',output=mode==='render'?'build/lantern.wav':'build/playback.json']=process.argv.slice(2);
assert(['render','playback'].includes(mode),'Use render or playback');
const score=JSON.parse(await readFile(scorePath,'utf8'));
const source=await readFile(sourcePath);
assert(!score.soundfonts&&!score.sample_buffers,'Local browser checks currently support synth-only scores');
const {server,url}=await serve(scorePath,sourcePath);
let browser;
try {
 browser=await chromium.launch({headless:true,...(process.env.CHROMIUM_PATH?{executablePath:process.env.CHROMIUM_PATH}:{})});
 const page=await browser.newPage({acceptDownloads:true});
 const errors=[]; const external=[];
 page.on('pageerror',e=>errors.push(e.message));
 page.on('console',m=>{if(m.type()==='error')errors.push(m.text());});
 await page.route('**/*',route=>{
  const request=route.request().url();
  if(!request.startsWith(url+'/')&&!request.startsWith('blob:')){external.push(request);return route.abort();}
  return route.continue();
 });
 await page.goto(url);
 await page.waitForFunction(()=>window.__ready||window.__failure,{},{timeout:30000});
 assert.equal(await page.evaluate(()=>window.__failure),undefined,'Player failed');
 const report={mode,source_sha256:createHash('sha256').update(source).digest('hex'),score_sha256:createHash('sha256').update(await readFile(scorePath)).digest('hex'),strudel_web:'1.3.0',seconds:score.loop_seconds,errors,external_requests:external,listening_comparison:false};
 await mkdir(dirname(resolve(output)),{recursive:true});
 if(mode==='render') {
  const downloading=page.waitForEvent('download',{timeout:120000});
  await page.click('#render');
  const download=await downloading; await download.saveAs(output);
  assert.equal(await download.failure(),null);
  const wav=await readFile(output);
  assert.equal(wav.toString('ascii',0,4),'RIFF');
  let pos=12,format,pcm;
  while(pos+8<=wav.length){const id=wav.toString('ascii',pos,pos+4),len=wav.readUInt32LE(pos+4);if(id==='fmt ')format={code:wav.readUInt16LE(pos+8),channels:wav.readUInt16LE(pos+10),rate:wav.readUInt32LE(pos+12),bits:wav.readUInt16LE(pos+22)};if(id==='data')pcm=wav.subarray(pos+8,pos+8+len);pos+=8+len+(len%2);}
  assert(pcm&&format);let peak=0,sum=0;const bytes=format.bits/8;
  for(let i=0;i<pcm.length;i+=bytes){const n=format.code===3?pcm.readFloatLE(i):pcm.readInt16LE(i)/32768;assert(Number.isFinite(n));peak=Math.max(peak,Math.abs(n));sum+=n*n;}
  const duration=pcm.length/bytes/format.channels/format.rate;
  assert(Math.abs(duration-score.loop_seconds)<2/format.rate,'Wrong render duration');
  assert(peak>.001&&peak<.99,'Silent or clipped render');
  Object.assign(report,{...format,peak,rms:Math.sqrt(sum/(pcm.length/bytes)),duration_seconds:duration,wav_sha256:createHash('sha256').update(wav).digest('hex')});
 } else {
  assert(Object.values(score.voices??{}).every(v=>!v.noise),'Playback check cannot distinguish added synth noise from percussion');
  report.noise_scope='Combined default white-noise snare/hat starts; instrument identity remains covered by the structural check';
  await page.click('#play');
  // Follow the audio clock: browser startup and suspended contexts consume wall
  // time without advancing the performance.
  await page.waitForFunction(()=>window.__playing&&window.__starts.length>0);
  await page.waitForFunction(seconds=>window.__context.currentTime>=window.__starts[0].when+seconds+.1,score.loop_seconds,{timeout:Math.max(30000,score.loop_seconds*2000)});
  const starts=await page.evaluate(()=>{window.__stop();return window.__starts;});
  const expected=Object.entries(score.parts).flatMap(([part,rows])=>rows.map(([at,,pitch])=>({at:at*60/score.bpm,frequency:['snare','hat'].includes(part)?0:part==='kick'?65:440*2**(((typeof pitch==='number'?pitch:noteToMidi(pitch))-69)/12),type:score.voices?.[part]?.sound??(['snare','hat'].includes(part)?'white':part==='kick'?'sine':'triangle')}))).sort((a,b)=>a.at-b.at);
  assert(expected.length,'No events to check');
  const first=starts.find(s=>s.type===expected[0].type&&Math.abs(s.frequency-expected[0].frequency)<.2);
  assert(first,'First attack missing'); const origin=first.when-expected[0].at;
  const available=starts.map(s=>({...s,at:s.when-origin}));let missed=[],late=[];
  for(const e of expected){const i=available.findIndex(s=>s.type===e.type&&Math.abs(s.frequency-e.frequency)<.2&&Math.abs(s.at-e.at)<.025);if(i<0){missed.push(e);continue;}const [s]=available.splice(i,1);if(s.calledAt>s.when+.01)late.push({...e,lateness:s.calledAt-s.when});}
  Object.assign(report,{expected_attacks:expected.length,missing:missed,late,observed_starts:starts.length});
  await writeFile(output,JSON.stringify(report,null,2)+'\n');
  assert.equal(missed.length,0,'Dropped attacks');assert.equal(late.length,0,'Late scheduling');
 }
 assert.deepEqual(errors,[],'Browser errors');assert.deepEqual(external,[],'Unexpected network requests');
 await writeFile(mode==='render'?output+'.json':output,JSON.stringify(report,null,2)+'\n');
 console.log(JSON.stringify(report));
}finally{await browser?.close();await new Promise(resolve=>server.close(resolve));}
