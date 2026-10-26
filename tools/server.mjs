import { createServer } from 'node:http';
import { readFile } from 'node:fs/promises';
import { resolve, sep } from 'node:path';
import { fileURLToPath } from 'node:url';
const root=fileURLToPath(new URL('..',import.meta.url));
export async function serve(scorePath='build/mixed.json',sourcePath='build/lantern.strudel.js',modulePath) {
 const vendor=resolve(root,'node_modules/@strudel/web/dist');
 const server=createServer(async(req,res)=>{
  try {
   const path=new URL(req.url,'http://localhost').pathname;
   let file;
   if(path==='/') file=resolve(root,'tools/player.html');
   else if(path==='/score.json') file=resolve(scorePath);
   else if(path==='/song.mjs'&&modulePath) file=resolve(modulePath);
   else if(path==='/score.js') file=resolve(sourcePath);
   else if(path.startsWith('/vendor/')) {
    file=resolve(vendor,decodeURIComponent(path.slice(8)));
    if(!file.startsWith(vendor+sep)) throw new Error('Invalid path');
   } else {res.writeHead(404);res.end();return;}
   const body=await readFile(file);
   res.setHeader('Content-Type',file.endsWith('.html')?'text/html':file.endsWith('.json')?'application/json':'text/javascript');
   res.end(body);
  }catch(error){res.writeHead(404);res.end('File not found');}
 });
 await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));
 return {server,url:`http://127.0.0.1:${server.address().port}`};
}
