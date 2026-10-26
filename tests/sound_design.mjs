// Browser integration coverage for effect processors, sample starts and modules.
import assert from 'node:assert/strict';
import {spawnSync} from 'node:child_process';
import {readFile, writeFile} from 'node:fs/promises';
const root='build/sound-design/';
function run(args,ok=true) {
 const p=spawnSync(process.execPath,args,{encoding:'utf8',timeout:240000});
 if(ok) assert.equal(p.status,0,p.stdout+p.stderr);
 else assert.notEqual(p.status,0,'Negative control unexpectedly passed');
 console.log(args.join(' '),ok?'PASS':'rejected as expected');
}
for(const name of ['effects','samples','long']) {
 const score=root+name+'.json',source=root+name+'.strudel.js',module=root+name+'.mjs';
 run(['tools/check.mjs',score,source,module]);
 run(['tools/audio.mjs','render',score,source,root+name+'.wav']);
 run(['tools/audio.mjs','playback',score,source,root+name+'.playback.json']);
 if(name==='effects') {
  process.env.SLOPWAVE_TEST_KEYBOARD='1';
  run(['tools/audio.mjs','render',score,source,root+'keyboard.wav']);
  delete process.env.SLOPWAVE_TEST_KEYBOARD;
 }
 if(name==='samples') {
  run(['tools/audio.mjs','render',score,source,root+'module.wav',module]);
  run(['tools/audio.mjs','playback',score,source,root+'module.playback.json',module]);
  // Correct score paired with a source whose sample never starts must fail.
  const broken=(await readFile(source,'utf8')).replace('source.start(time);','// source.start removed for negative control');
  await writeFile(root+'missing-sample.js',broken);
  run(['tools/audio.mjs','playback',score,root+'missing-sample.js',root+'missing.json'],false);
 }
}
