/* Fluxo RIP: animação de abertura opt-in à preferência de movimento do sistema. */
(() => {
  'use strict';
  const splash=document.getElementById('brand-splash');
  if(!splash)return;
  const reduce=window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  let disabled=false;
  try{disabled=localStorage.getItem('forge.motion.enabled.v1')==='false'}catch(_){ }
  if(reduce||disabled){splash.remove();return;}
  const hide=()=>{splash.classList.add('dismissed');setTimeout(()=>splash.remove(),420);};
  let shown=false;
  try{shown=sessionStorage.getItem('fluxorip.splash.shown')==='true';sessionStorage.setItem('fluxorip.splash.shown','true')}catch(_){ }
  if(shown){splash.remove();return;}
  setTimeout(hide,1750);
  document.addEventListener('click',e=>{if(e.target.closest('#motion-toggle'))hide()});
})();
