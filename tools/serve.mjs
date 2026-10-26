import {serve} from './server.mjs';
const {server,url}=await serve(...process.argv.slice(2));
console.log(`slopwave preview: ${url} (Ctrl-C to stop)`);
process.on('SIGINT',()=>server.close());
