// Synthetic DOM only: rapid keyboard feedback and reduced-motion cancellation.
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {runInNewContext} from 'node:vm';
const source=readFileSync(new URL('./motion.js',import.meta.url),'utf8');
const listeners={};
const timers=new Map(); let next=0;
const classes=new Set();
const target={
  offsetWidth:120,
  classList:{add(x){classes.add(x);},remove(x){classes.delete(x);}},
  matches(){return false;},
  closest(){return null;}
};
const toggle={setAttribute(){},querySelector(){return {textContent:''};}};
const query={matches:false,addEventListener(_,fn){listeners.media=fn;}};
const document={
  documentElement:{classList:{toggle(){}}},
  querySelectorAll(){return [];},
  getElementById(id){return id==='motion-toggle'?toggle:null;},
  addEventListener(name,fn){listeners[name]=fn;}
};
runInNewContext(source,{
  document,window:{matchMedia(){return query;}},
  localStorage:{getItem(){return null;}},
  setTimeout(fn){const id=++next;timers.set(id,fn);return id;},
  clearTimeout(id){timers.delete(id);}
},{timeout:1000});
const press=()=>listeners.keydown({key:'Enter',repeat:false,target:{closest(){return target;}}});
press();
assert.equal(classes.has('fx-keypress'),true);
const first=[...timers.keys()][0];
press();
assert.equal(timers.size,1,'older timer must be canceled');
assert.equal(timers.has(first),false);
const second=[...timers.keys()][0];
query.matches=true;listeners.media();
assert.equal(timers.size,0,'motion-off cancels pending feedback');
assert.equal(classes.has('fx-keypress'),false);
query.matches=false;listeners.media();
press();
assert.equal(timers.size,1);
const active=[...timers.values()][0];
active();
assert.equal(classes.has('fx-keypress'),false);
assert.equal(timers.size,1,'fake clock retains callback until flushed');
console.log('PASS: rapid keypress timeout replacement and reduced-motion cancellation');
