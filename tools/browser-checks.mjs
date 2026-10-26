import assert from 'node:assert/strict';

export function watchBrowser(page, errors) {
 page.on('pageerror',error=>errors.push(error.message));
 page.on('console',message=>{
  const text=message.text();
  // Strudel's per-note error logger uses console.log, and worklet failures warn.
  if(message.type()==='error'||/could not load AudioWorklet|\[(?:webaudio|superdough)\] error:/.test(text))
   errors.push(text);
 });
}

export async function assertBrowser(page, errors, external) {
 assert.deepEqual(errors,[],'Browser audio errors');
 assert.deepEqual(await page.evaluate(()=>window.__processorErrors??[]),[],'AudioWorklet processor failure');
 assert.deepEqual(external,[],'Unexpected network requests');
}
