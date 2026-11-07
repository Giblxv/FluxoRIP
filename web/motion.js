/* FORGE v0.9 — microinterações: sem dependências de terceiros. */
(() => {
  'use strict';
  const preferenceKey='forge.motion.enabled.v1';
  const root=document.documentElement;
  let enabled=true;
  try{enabled=localStorage.getItem(preferenceKey)!=='false'}catch(_){ /* modo privado */ }
  const motionQuery=window.matchMedia('(prefers-reduced-motion: reduce)');
  const respectsReducedMotion=()=>motionQuery.matches;
  const animationsAvailable=()=>enabled && !respectsReducedMotion();
  const keypressTimers=new Map();
  function clearTransientEffects(){
    for(const timer of keypressTimers.values())clearTimeout(timer);
    keypressTimers.clear();
    document.querySelectorAll('.fx-ripple').forEach(node=>node.remove());
    document.querySelectorAll('.fx-keypress').forEach(node=>node.classList.remove('fx-keypress'));
    document.querySelectorAll('.fx-pressable').forEach(node=>node.classList.remove('fx-pressable'));
  }
  function apply(){
    const reduced=respectsReducedMotion();
    if(reduced || !enabled){
      clearPageMotion();
      clearTransientEffects();
    }
    root.classList.toggle('motion-off',!enabled || reduced);
    const toggle=document.getElementById('motion-toggle');
    if(!toggle)return;
    toggle.setAttribute('aria-pressed', String(enabled && !reduced));
    toggle.setAttribute('aria-label', reduced ? 'Animações reduzidas pela preferência do sistema' : enabled ? 'Desativar animações da interface' : 'Ativar animações da interface');
    toggle.disabled=reduced;
    toggle.querySelector('.motion-switch-label').textContent=reduced?'MOV. REDUZIDO':enabled?'MOTION ON':'MOTION OFF';
    toggle.title=reduced?'O sistema prefere movimento reduzido; controle temporariamente indisponível':enabled?'Desativar microanimações':'Ativar microanimações';
  }
  function targetForEffect(el){
    const hit=el.closest('button:not(:disabled),a.action,a[href][download],.task-card[role="button"]');
    return hit && !hit.closest('[hidden]') ? hit : null;
  }
  document.addEventListener('click',event=>{
    if(event.target.closest('#motion-toggle') && !respectsReducedMotion()){
      enabled=!enabled;
      try{localStorage.setItem(preferenceKey,String(enabled))}catch(_){ /* modo privado */ }
      apply();
    }
  });
  document.addEventListener('pointerdown',event=>{
    if(!animationsAvailable() || !event.isPrimary || event.button!==0)return;
    const target=targetForEffect(event.target);
    if(!target || target.matches('.task-card') || target.classList.contains('dragging'))return;
    const rect=target.getBoundingClientRect();
    if(!rect.width || !rect.height)return;
    // Bound simultaneous ripples on one control during rapid pointer input.
    // Keep other controls independent; the last three gestures remain visible.
    const activeRipples=target.querySelectorAll('.fx-ripple');
    for(let i=0;i<activeRipples.length-2;i++)activeRipples[i].remove();
    target.classList.add('fx-pressable');
    const ripple=document.createElement('span');
    ripple.className='fx-ripple';
    ripple.setAttribute('aria-hidden','true');
    const d=Math.max(rect.width,rect.height)*2.4;
    ripple.style.width=`${d}px`;
    ripple.style.height=`${d}px`;
    ripple.style.left=`${event.clientX-rect.left}px`;
    ripple.style.top=`${event.clientY-rect.top}px`;
    target.appendChild(ripple);
    const finish=()=>{
      ripple.remove();
      // Do not leave the pressed marker on controls after feedback ends.
      if(!target.querySelector('.fx-ripple'))target.classList.remove('fx-pressable');
    };
    ripple.addEventListener('animationend',finish,{once:true});
    // Fallback for interrupted animations or background tab throttling.
    setTimeout(finish,600);
  },{passive:true});
  // A second keypress must not let the first timeout cancel newer feedback.
  document.addEventListener('keydown',event=>{
    if(!animationsAvailable() || event.repeat || !['Enter',' '].includes(event.key))return;
    const target=targetForEffect(event.target);
    if(!target || target.matches('.task-card') && event.key===' ')return;
    const previousTimer=keypressTimers.get(target);
    if(previousTimer!==undefined)clearTimeout(previousTimer);
    target.classList.remove('fx-keypress');
    // Reinicia a animação da tecla sem alterar a função do botão.
    void target.offsetWidth;
    target.classList.add('fx-keypress');
    const timer=setTimeout(()=>{
      if(keypressTimers.get(target)!==timer)return;
      keypressTimers.delete(target);
      target.classList.remove('fx-keypress');
    },280);
    keypressTimers.set(target,timer);
  });
  let previousPage=null;
  let pageMotionTimer=null;
  function clearPageMotion(){
    if(pageMotionTimer!==null){
      clearTimeout(pageMotionTimer);
      pageMotionTimer=null;
    }
    document.getElementById('view')?.classList.remove('motion-page-enter');
    document.getElementById('title')?.classList.remove('motion-page-title');
  }
  function onRender(page){
    if(previousPage===page)return;
    previousPage=page;
    clearPageMotion();
    // Data refreshes while the window is hidden must not schedule entrances.
    if(!animationsAvailable() || document.hidden)return;
    const view=document.getElementById('view');
    const title=document.getElementById('title');
    if(!view)return;
    // A short-lived class prevents refreshes within the same page from
    // reanimating every freshly rendered card or metric.
    void view.offsetWidth;
    view.classList.add('motion-page-enter');
    title?.classList.add('motion-page-title');
    pageMotionTimer=setTimeout(clearPageMotion,700);
  }
  // Background tabs should not retain a half-finished entrance effect.
  // The next explicit navigation can animate normally after returning.
  document.addEventListener('visibilitychange',()=>{
    if(document.hidden){
      clearPageMotion();
      // Hidden windows must not retain pressed/ripple/keyboard feedback.
      // The next visible interaction starts with a clean visual state.
      clearTransientEffects();
    }
  });
  window.forgeMotionOnRender=onRender;
  // Respeita alterações feitas nas preferências do Windows enquanto o app está aberto.
  if(typeof motionQuery.addEventListener==='function')motionQuery.addEventListener('change',apply);
  else if(typeof motionQuery.addListener==='function')motionQuery.addListener(apply);
  // Script é defer; preserva o padrão nativo de movimento reduzido.
  apply();
  document.addEventListener('DOMContentLoaded',apply,{once:true});
})();
