// No printer, browser or API dependency: verify OS preference changes and manual toggle.
import assert from "node:assert/strict";
import {readFileSync} from "node:fs";
import {runInNewContext} from "node:vm";

const source=readFileSync(new URL("./motion.js", import.meta.url),"utf8");

function harness({legacy=false, stored=null}={}) {
  const listeners={};
  const classes=new Set();
  const ripple={removed:false,remove(){this.removed=true;}};
  const keypress={classes:new Set(['fx-keypress']),classList:{remove(name){keypress.classes.delete(name);}}};
  const pressable={classes:new Set(['fx-pressable']),classList:{remove(name){pressable.classes.delete(name);}}};
  const label={textContent:""};
  const toggle={
    disabled:false, title:"", attributes:{},
    setAttribute(key,value){this.attributes[key]=value;},
    querySelector(query){assert.equal(query,".motion-switch-label");return label;}
  };
  const query={matches:false};
  if(legacy)query.addListener=callback=>{listeners.change=callback;};
  else query.addEventListener=(name,callback)=>{assert.equal(name,"change");listeners.change=callback;};
  const root={
    classList:{
      toggle(name,enabled){if(enabled)classes.add(name);else classes.delete(name);},
      contains(name){return classes.has(name);}
    }
  };
  const document={
    documentElement:root,
    querySelectorAll(selector){
      if(selector==='.fx-ripple')return [ripple];
      if(selector==='.fx-keypress')return keypress.classes.has('fx-keypress')?[keypress]:[];
      if(selector==='.fx-pressable')return pressable.classes.has('fx-pressable')?[pressable]:[];
      throw Error('unexpected selector '+selector);
    },
    getElementById(id){return id==="motion-toggle"?toggle:null;},
    addEventListener(name,callback){listeners[name]=callback;}
  };
  const storage={value:stored, getItem(){return this.value;},setItem(key,value){this.value=value;}};
  const window={matchMedia(selector){
    assert.equal(selector,"(prefers-reduced-motion: reduce)");
    return query;
  }};
  runInNewContext(source,{
    document,window,localStorage:storage,
    setTimeout(){}, // No ripple effects triggered.
  },{timeout:1000});
  return {
    query,classes,toggle,label,storage,ripple,keypress,pressable,
    change(value){query.matches=value;listeners.change();},
    click(){listeners.click({target:{closest(selector){
      assert.equal(selector,"#motion-toggle");
      return toggle;
    }}});}
  };
}
for(const legacy of [false,true]){
  const app=harness({legacy});
  assert.equal(app.label.textContent,"MOTION ON");
  assert.equal(app.toggle.disabled,false);
  assert.equal(app.toggle.attributes["aria-pressed"],"true");
  app.change(true);
  assert.equal(app.ripple.removed,true,'in-flight ripple removed immediately');
  assert.equal(app.keypress.classes.has('fx-keypress'),false,'keypress effect removed immediately');
  assert.equal(app.pressable.classes.has('fx-pressable'),false,'pressed marker removed immediately');
  assert.equal(app.label.textContent,"MOV. REDUZIDO");
  assert.equal(app.toggle.disabled,true);
  assert.equal(app.toggle.attributes["aria-pressed"],"false");
  assert.equal(app.classes.has("motion-off"),true);
  app.click(); // System preference must not silently invert stored manual preference.
  assert.equal(app.storage.value,null);
  app.change(false);
  assert.equal(app.toggle.disabled,false);
  assert.equal(app.classes.has("motion-off"),false);
  app.click();
  assert.equal(app.storage.value,"false");
  assert.equal(app.label.textContent,"MOTION OFF");
  assert.equal(app.classes.has("motion-off"),true);
  app.change(true);
  app.change(false);
  assert.equal(app.label.textContent,"MOTION OFF", "manual off survives OS preference changes");
  assert.equal(app.toggle.attributes["aria-pressed"],"false");
}
{
  const app=harness({stored:"false"});
  assert.equal(app.label.textContent,"MOTION OFF");
  assert.equal(app.classes.has("motion-off"),true);
}
console.log("PASS: live OS reduced-motion changes, legacy listener and manual preference");
