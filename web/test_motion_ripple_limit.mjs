// Synthetic-only regression for bounded concurrent CMYK ripple feedback.
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {runInNewContext} from 'node:vm';

const source=readFileSync(new URL('./motion.js',import.meta.url),'utf8');
const listeners={};
const timers=[];
const classes=new Set();
const ripples=[];
const target={
  classList:{add(x){classes.add(x);},remove(x){classes.delete(x);},contains(x){return classes.has(x);}},
  closest(){return null;},matches(){return false;},
  getBoundingClientRect(){return {width:100,height:40,left:0,top:0};},
  querySelectorAll(selector){assert.equal(selector,'.fx-ripple');return ripples.filter(r=>!r.removed);},
  querySelector(selector){assert.equal(selector,'.fx-ripple');return ripples.find(r=>!r.removed)||null;},
  appendChild(node){ripples.push(node);}
};
const document={
  documentElement:{classList:{toggle(){}}},
  hidden:false,
  addEventListener(name,cb){listeners[name]=cb;},
  getElementById(){return null;},
  querySelectorAll(selector){
    if(selector==='.fx-ripple')return ripples.filter(r=>!r.removed);
    return [];
  },
  createElement(){
    const events={};
    return {style:{},removed:false,className:'',
      setAttribute(){},addEventListener(name,cb){events[name]=cb;},
      remove(){this.removed=true;},
      finish(){events.animationend?.();}
    };
  }
};
runInNewContext(source,{
  document,
  window:{matchMedia(){return {matches:false,addEventListener(){}};}},
  localStorage:{getItem(){return null;}},
  setTimeout(fn){timers.push(fn);return timers.length;},
  clearTimeout(){},
},{timeout:1000});
for(let i=0;i<8;i++){
  listeners.pointerdown({isPrimary:true,button:0,target:{closest(){return target;}},clientX:25,clientY:15});
  assert.ok(ripples.filter(r=>!r.removed).length<=3,'per-control ripple count stays bounded');
}
assert.equal(ripples.filter(r=>!r.removed).length,3);
assert.equal(classes.has('fx-pressable'),true);
for(const ripple of ripples.filter(r=>!r.removed))ripple.finish();
assert.equal(ripples.filter(r=>!r.removed).length,0);
assert.equal(classes.has('fx-pressable'),false,'press marker clears after last ripple');
console.log('PASS: rapid pointer gestures bounded and press state cleared');
