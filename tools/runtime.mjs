// @kabelsalat/web 0.4.1 declares a UMD `main` alongside its ESM `module`.
// Node does not use `module`. Resolve that one dependency to its published ESM
// entry without patching node_modules or changing the browser runtime.
import {registerHooks} from 'node:module';
registerHooks({resolve(specifier,context,next){
 return next(specifier==='@kabelsalat/web'?'@kabelsalat/web/dist/index.mjs':specifier,context);
}});
export const core=await import('@strudel/core');
export const mini=await import('@strudel/mini');
