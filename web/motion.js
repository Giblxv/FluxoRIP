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
  function apply(){
    const reduced=respectsReducedMotion();
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
    ripple.addEventListener('animationend',()=>ripple.remove(),{once:true});
    // Fallback se a preferência de animação mudar durante o clique.
    setTimeout(()=>ripple.remove(),600);
  },{passive:true});
  document.addEventListener('keydown',event=>{
    if(!animationsAvailable() || event.repeat || !['Enter',' '].includes(event.key))return;
    const target=targetForEffect(event.target);
    if(!target || target.matches('.task-card') && event.key===' ')return;
    target.classList.remove('fx-keypress');
    // Reinicia a animação da tecla sem alterar a função do botão.
    void target.offsetWidth;
    target.classList.add('fx-keypress');
    setTimeout(()=>target.classList.remove('fx-keypress'),280);
  });
  let previousPage=null;
  function onRender(page){
    if(previousPage===page)return;
    previousPage=page;
    if(!animationsAvailable())return;
    const view=document.getElementById('view');
    const title=document.getElementById('title');
    if(!view)return;
    view.classList.remove('motion-page-enter');
    title?.classList.remove('motion-page-title');
    void view.offsetWidth;
    view.classList.add('motion-page-enter');
    title?.classList.add('motion-page-title');
  }
  window.forgeMotionOnRender=onRender;
  // Respeita alterações feitas nas preferências do Windows enquanto o app está aberto.
  if(typeof motionQuery.addEventListener==='function')motionQuery.addEventListener('change',apply);
  else if(typeof motionQuery.addListener==='function')motionQuery.addListener(apply);
  // Script é defer; preserva o padrão nativo de movimento reduzido.
  apply();
  document.addEventListener('DOMContentLoaded',apply,{once:true});
})();
