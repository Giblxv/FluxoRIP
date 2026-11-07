// Synthetic DOM regression: completed, evicted and hidden ripples cancel fallback timers.
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {runInNewContext} from 'node:vm';
const source=readFileSync(new URL('./motion.js',import.meta.url),'utf8');
const listeners={},timers=new Map(),ripples=[],classes=new Set();
let next=0;
const target={
  classList:{add(x){classes.add(x);},remove(x){classes.delete(x);},contains(x){return classes.has(x);}},
  closest(){return null;},matches(){return false;},
  getBoundingClientRect(){return {width:100,height:50,left:0,top:0};},
  querySelectorAll(){return ripples.filter(x=>!x.removed);},
  querySelector(){return ripples.find(x=>!x.removed)||null;},
  appendChild(node){ripples.push(node);}
};
const document={
  hidden:false,documentElement:{classList:{toggle(){}}},
  addEventListener(name,cb){listeners[name]=cb;},
  getElementById(){return null;},
  querySelectorAll(selector){
    if(selector==='.fx-ripple')return ripples.filter(x=>!x.removed);
    if(selector==='.fx-pressable')return classes.has('fx-pressable')?[target]:[];
    if(selector==='.fx-keypress')return classes.has('fx-keypress')?[target]:[];
    return [];
  },
  createElement(){
    const events={};
    return {style:{},removed:false,setAttribute(){},addEventListener(name,cb){events[name]=cb;},
      remove(){this.removed=true;},finish(){events.animationend?.();}};
  }
};
runInNewContext(source,{
  document,window:{matchMedia(){return {matches:false,addEventListener(){}};}},
  localStorage:{getItem(){return null;}},
  setTimeout(fn){const id=++next;timers.set(id,fn);return id;},
  clearTimeout(id){timers.delete(id);}
},{timeout:1000});
const press=()=>listeners.pointerdown({isPrimary:true,button:0,target:{closest(){return target;}},clientX:10,clientY:20});
press();press();press();
assert.equal(timers.size,3);
ripples[0].finish();
assert.equal(timers.size,2,'animation completion clears its fallback timer');
press();press();
assert.equal(timers.size,3,'eviction clears stale timer without affecting newer gestures');
document.hidden=true;
listeners.visibilitychange();
assert.equal(timers.size,0,'hidden tab clears all fallback timers');
assert.equal(ripples.filter(x=>!x.removed).length,0);
assert.equal(classes.has('fx-pressable'),false);
// Synthetic input delivered while hidden must not recreate visual feedback.
press();
listeners.keydown({repeat:false,key:'Enter',target:{closest(){return target;}}});
assert.equal(timers.size,0,'hidden input does not schedule ripple or keyboard timers');
assert.equal(ripples.filter(x=>!x.removed).length,0);
assert.equal(classes.has('fx-keypress'),false);
document.hidden=false;
press();
assert.equal(timers.size,1);
const pending=[...timers.values()];
pending[0]();
assert.equal(timers.size,0,'fallback removes its own timer entry');
assert.equal(classes.has('fx-pressable'),false);
console.log('PASS: ripple timers cleaned and hidden input feedback suppressed');
