// Synthetic DOM regression: animation classes must not survive into same-page refreshes.
import assert from "node:assert/strict";
import {readFileSync} from "node:fs";
import {runInNewContext} from "node:vm";

const source=readFileSync(new URL("./motion.js",import.meta.url),"utf8");
function harness(){
  const timers=new Map();
  let nextTimer=0;
  const listeners={};
  const rootClasses=new Set();
  const mkClassList=()=>{
    const values=new Set();
    return {
      add(name){values.add(name);},
      remove(name){values.delete(name);},
      contains(name){return values.has(name);}
    };
  };
  const view={classList:mkClassList(),offsetWidth:640};
  const title={classList:mkClassList()};
  const label={textContent:""};
  const toggle={
    disabled:false,
    setAttribute(){},
    querySelector(){return label;}
  };
  const query={matches:false,addEventListener(name,cb){listeners.media=cb;}};
  const root={classList:{
    toggle(name,on){if(on)rootClasses.add(name);else rootClasses.delete(name);},
    contains(name){return rootClasses.has(name);}
  }};
  const document={
    documentElement:root,
    getElementById(id){return {view,title,"motion-toggle":toggle}[id]||null;},
    addEventListener(name,cb){listeners[name]=cb;}
  };
  const context={
    document,
    window:{matchMedia(){return query;}},
    localStorage:{getItem(){return null;}},
    setTimeout(callback){const id=++nextTimer;timers.set(id,callback);return id;},
    clearTimeout(id){timers.delete(id);}
  };
  runInNewContext(source,context,{timeout:1000});
  return {
    view,title,timers,query,
    render(page){context.window.forgeMotionOnRender(page);},
    flush(){const jobs=[...timers.values()];timers.clear();jobs.forEach(fn=>fn());},
    reduce(on){query.matches=on;listeners.media();},
    toggle(){listeners.click({target:{closest(){return toggle;}}});}
  };
}
{
  const app=harness();
  app.render("projects");
  assert.equal(app.view.classList.contains("motion-page-enter"),true);
  assert.equal(app.timers.size,1);
  app.flush();
  assert.equal(app.view.classList.contains("motion-page-enter"),false);
  assert.equal(app.title.classList.contains("motion-page-title"),false);
  app.render("projects");
  assert.equal(app.timers.size,0,"same-page refresh cannot restart entrance");
  app.render("queue");
  assert.equal(app.timers.size,1);
  app.reduce(true);
  assert.equal(app.timers.size,0,"reduced-motion cancels pending entrance");
  assert.equal(app.view.classList.contains("motion-page-enter"),false);
  app.render("history");
  assert.equal(app.timers.size,0,"reduced-motion prevents new entrance");
  app.reduce(false);
  app.render("printers");
  assert.equal(app.timers.size,1);
  app.toggle();
  assert.equal(app.timers.size,0,"manual motion-off cancels entrance");
  app.render("stations");
  assert.equal(app.timers.size,0);
}
{
  const app=harness();
  app.render("projects");
  app.render("queue");
  assert.equal(app.timers.size,1,"rapid navigation replaces previous timer");
  app.flush();
  assert.equal(app.view.classList.contains("motion-page-enter"),false);
}
console.log("PASS: page entrance lifecycle, refresh stability and reduced-motion cancellation");
