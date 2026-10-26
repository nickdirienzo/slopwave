import assert from 'node:assert/strict';
import {readFile,writeFile,mkdir} from 'node:fs/promises';
import {dirname,resolve} from 'node:path';
import {createHash} from 'node:crypto';
import {chromium} from 'playwright';
import {core} from './runtime.mjs';
const {noteToMidi}=core;
import {serve} from './server.mjs';
import {renderSegments, canSegment} from './render-segments.mjs';
import {watchBrowser, assertBrowser} from './browser-checks.mjs';
const [mode,scorePath='build/mixed.json',sourcePath='build/lantern.strudel.js',output=mode==='render'?'build/lantern.wav':'build/playback.json',modulePath]=process.argv.slice(2);
assert(['render','playback'].includes(mode),'Use render or playback');
const score=JSON.parse(await readFile(scorePath,'utf8'));
const source=await readFile(sourcePath);
assert(!score.soundfonts,'Local browser checks require embedded sample_buffers instead of network soundfonts');
const {server,url}=await serve(scorePath,sourcePath,modulePath);
let browser;
try {
 browser=await chromium.launch({headless:true,...(process.env.CHROMIUM_PATH?{executablePath:process.env.CHROMIUM_PATH}:{})});
 const page=await browser.newPage({acceptDownloads:true});
 const errors=[]; const external=[];
 watchBrowser(page,errors);
 await page.route('**/*',route=>{
  const request=route.request().url();
  if(!request.startsWith(url+'/')&&!request.startsWith('blob:')){external.push(request);return route.abort();}
  return route.continue();
 });
 await page.goto(url+(modulePath?'/?module=1':''));
 await page.waitForFunction(()=>window.__ready||window.__failure,{},{timeout:30000});
 assert.equal(await page.evaluate(()=>window.__failure),undefined,'Player failed');
 const report={mode,source_sha256:createHash('sha256').update(source).digest('hex'),score_sha256:createHash('sha256').update(await readFile(scorePath)).digest('hex'),strudel_web:'1.3.0',seconds:score.loop_seconds,errors,external_requests:external,listening_comparison:false};
 await mkdir(dirname(resolve(output)),{recursive:true});
 if(mode==='render') {
  if(score.loop_seconds>60&&!modulePath&&canSegment(score)) {
   await page.close();
   report.segment_render=await renderSegments(browser,url,score,output);
  } else {
  const downloading=page.waitForEvent('download',{timeout:Math.max(120000,score.loop_seconds*4000)});
  if(process.env.SLOPWAVE_TEST_KEYBOARD==='1') {await page.focus('#render');await page.keyboard.press('Enter');}
  else await page.click('#render');
  const download=await downloading; await download.saveAs(output);
  assert.equal(await download.failure(),null);
  }
  if(!page.isClosed()) await assertBrowser(page,errors,external);
  const wav=await readFile(output);
  assert.equal(wav.toString('ascii',0,4),'RIFF');
  let pos=12,format,pcm;
  while(pos+8<=wav.length){const id=wav.toString('ascii',pos,pos+4),len=wav.readUInt32LE(pos+4);if(id==='fmt ')format={code:wav.readUInt16LE(pos+8),channels:wav.readUInt16LE(pos+10),rate:wav.readUInt32LE(pos+12),bits:wav.readUInt16LE(pos+22)};if(id==='data')pcm=wav.subarray(pos+8,pos+8+len);pos+=8+len+(len%2);}
  assert(pcm&&format);let peak=0,sum=0;const bytes=format.bits/8;
  for(let i=0;i<pcm.length;i+=bytes){const n=format.code===3?pcm.readFloatLE(i):pcm.readInt16LE(i)/32768;assert(Number.isFinite(n));peak=Math.max(peak,Math.abs(n));sum+=n*n;}
  const duration=pcm.length/bytes/format.channels/format.rate;
  assert(Math.abs(duration-score.loop_seconds)<2/format.rate,'Wrong render duration');
  assert(peak>.001,`Silent render: peak=${peak}`);
  assert(peak<.99,`Clipped render: peak=${peak}`);
  Object.assign(report,{...format,peak,rms:Math.sqrt(sum/(pcm.length/bytes)),duration_seconds:duration,wav_sha256:createHash('sha256').update(wav).digest('hex')});
 } else {
  report.noise_scope='Noise buffer starts are checked as a combined class; noise color/part identity is structural evidence only';
  report.sample_scope='Named custom sample buffer starts, including their audio-clock scheduling times';
  await page.click('#play');
  // Follow the audio clock: browser startup and suspended contexts consume wall
  // time without advancing the performance.
  await page.waitForFunction(()=>window.__failure||(window.__playing&&window.__starts.length>0));
  assert.equal(await page.evaluate(()=>window.__failure),undefined,'Playback failed');
  await page.waitForFunction(seconds=>window.__context.currentTime>=window.__starts[0].when+seconds+.1,score.loop_seconds,{timeout:Math.max(30000,score.loop_seconds*2000)});
  const starts=await page.evaluate(()=>{window.__stop();return window.__starts;});
  const expected=Object.entries(score.parts).flatMap(([part,rows])=>rows.map(([at,,pitch])=>{
   const voice=score.voices?.[part]??{};
   let type=voice.sound??(['snare','hat'].includes(part)?'white':part==='kick'?'sine':'triangle');
   if(['pink','brown'].includes(type)) type='white';
   const frequency=(type==='white'||score.sample_buffers?.[type])?0:voice.freq??(part==='kick'&&!voice.sound?65:440*2**(((typeof pitch==='number'?pitch:noteToMidi(pitch))-69)/12));
   return {at:at*60/score.bpm,frequency,type};
  })).sort((a,b)=>a.at-b.at);
  assert(expected.length,'No events to check');
  const first=starts.find(s=>s.type===expected[0].type&&Math.abs(s.frequency-expected[0].frequency)<.2);
  assert(first,'First attack missing'); const origin=first.when-expected[0].at;
  const available=starts.map(s=>({...s,at:s.when-origin}));let missed=[],late=[];
  for(const e of expected){const i=available.findIndex(s=>s.type===e.type&&Math.abs(s.frequency-e.frequency)<.2&&Math.abs(s.at-e.at)<.025);if(i<0){missed.push(e);continue;}const [s]=available.splice(i,1);if(s.calledAt>s.when+.01)late.push({...e,lateness:s.calledAt-s.when});}
  Object.assign(report,{expected_attacks:expected.length,missing:missed,late,observed_starts:starts.length});
  await assertBrowser(page,errors,external);
  await writeFile(output,JSON.stringify(report,null,2)+'\n');
  assert.equal(missed.length,0,'Dropped attacks');assert.equal(late.length,0,'Late scheduling');
 }
 assert.deepEqual(errors,[],'Browser errors');assert.deepEqual(external,[],'Unexpected network requests');
 await writeFile(mode==='render'?output+'.json':output,JSON.stringify(report,null,2)+'\n');
 console.log(JSON.stringify(report));
}finally{await browser?.close();await new Promise(resolve=>server.close(resolve));}
