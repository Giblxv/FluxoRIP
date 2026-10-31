'use strict';
/* Editor de Arte Fluxo RIP: preview local, controle de versões e processamento servidor. */
const artState={list:[],selected:null,capabilities:null,busy:false,crop:null,orderCode:''};
const artGet=()=>artState.list.find(a=>a.id===artState.selected)||null;
const artUrl=(id,kind='preview')=>`/api/art/${encodeURIComponent(id)}/${kind}`;
const artFmt=(a)=>a?`${a.width} × ${a.height} px · ${a.dpi_x} DPI · ${(a.width/a.dpi_x*2.54).toFixed(1)} × ${(a.height/a.dpi_y*2.54).toFixed(1)} cm`:'Escolha uma imagem';
const artDate=(iso)=>iso?new Date(iso).toLocaleString('pt-BR'):'—';
const artOperation=(o)=>({'importada':'ORIGINAL','crop':'RECORTE','resize':'TAMANHO','dpi':'DPI','background_simple':'FUNDO SIMPLES','background_ai':'FUNDO IA','vectorize':'SVG','upscale_ai':'AMPLIAÇÃO IA','generated_ai':'ARTE ANTERIOR'})[o]||o.toUpperCase();

function artView(){
 const a=artGet();const cap=artState.capabilities||{};
 const orderOptions=`<option value="" ${!artState.orderCode?'selected':''}>Sem projeto associado</option>${state.data.orders.map(o=>`<option value="${esc(o.code)}" ${artState.orderCode===o.code?'selected':''}>${esc(o.code)} — ${esc(o.customer)}</option>`).join('')}`;
 const rows=artState.list.map(q=>`<button class="art-asset ${q.id===a?.id?'active':''}" data-art-select="${esc(q.id)}"><span class="art-asset-icon">${q.file_format==='SVG'?'◇':'▧'}</span><span class="art-asset-copy"><b>${esc(q.original_name)}</b><small>${artOperation(q.operation)} · ${q.width}×${q.height}${q.order_code?' · '+esc(q.order_code):''}</small></span><span class="art-asset-time">${artDate(q.created_at).split(' ')[0]}</span></button>`).join('');
 const svg=a?.file_format==='SVG';
 const preview=a?svg?`<div class="art-vector-notice"><div class="symbol">◇</div><strong>SVG VETORIZADO</strong><p>Arquivo vetorial gerado. Faça o download para abrir no Inkscape, Illustrator ou software compatível.</p><a class="action primary" href="${artUrl(a.id,'download')}">↓ Baixar SVG</a></div>`:`<div class="art-picture" id="art-picture"><img id="art-preview" src="${artUrl(a.id)}" alt="Prévia da arte selecionada" draggable="false"><canvas id="art-crop-layer" aria-label="Arraste para selecionar a área do recorte"></canvas></div>`:`<div class="art-vector-notice"><div class="symbol">▧</div><strong>SEM ARTE SELECIONADA</strong><p>Importe uma imagem PNG, JPG, WEBP, TIFF ou BMP. Seu arquivo original ficará preservado.</p><button class="action primary" data-art-upload>＋ Importar imagem</button></div>`;
 return `<div class="art-topline"><span><span class="mode-dot"></span> PROCESSAMENTO LOCAL · SEM ENVIO PARA SERVIÇOS EXTERNOS</span><span>IMAGENS ORIGINAIS PRESERVADAS · FORMATOS PNG / SVG</span></div>
 <input id="art-upload" type="file" hidden accept="image/png,image/jpeg,image/webp,image/bmp,image/tiff,.png,.jpg,.jpeg,.webp,.bmp,.tif,.tiff" />
 <div class="art-layout">
   <aside class="panel art-library"><div class="panel-header"><strong>ARQUIVOS E REVISÕES</strong><button class="mini-btn" data-art-upload>＋ Adicionar</button></div><div class="art-library-filter"><span>Associar novo upload a um pedido</span><select class="select" id="art-order">${orderOptions}</select></div><div class="art-asset-list">${rows||'<div class="art-placeholder">Nenhuma arte importada.</div>'}</div><div class="art-library-bottom">${artState.list.length} versões armazenadas localmente</div></aside>
   <section class="art-stage">
     <div class="art-stage-bar"><span class="art-stage-label">${a?esc(a.original_name):'PRÉ-VISUALIZAÇÃO'}</span><span class="art-file-info">${a?artFmt(a):'Aguardando arquivo'}</span><span class="art-safe">◉ ORIGINAL SEGURO</span></div>
     <div class="art-viewport checkerboard">${preview}</div>
     <div class="art-stage-foot"><span id="art-selection-label">${a&&!svg?'Arraste sobre a imagem para selecionar a área de recorte.':'Selecione uma imagem raster para editar.'}</span>${a?`<div class="row-actions"><a href="${artUrl(a.id,'original')}" class="action soft sm">↓ Original</a><a href="${artUrl(a.id,'download')}" class="action soft sm">↓ Baixar versão</a></div>`:''}</div>
     <div class="art-hint">Para DTF: imagens pequenas não recuperam detalhes apenas ao alterar DPI. Verifique a resolução em pixels antes de imprimir.</div>
   </section>
   <aside class="panel art-tools"><div class="panel-header"><strong>FERRAMENTAS DE EDIÇÃO</strong><small>${artState.busy?'PROCESSANDO...':'Fluxo RIP ART 0.6'}</small></div>
     <div class="art-tools-scroller">
       <section class="art-tool-section"><div class="art-tool-title">01 / Recortar</div><div class="art-tool-tip">Selecione com o mouse na imagem para recortar a região.</div>
         <div class="art-field-row"><label>X (px)<input id="crop-x" type="number" min="0" value="0"></label><label>Y (px)<input id="crop-y" type="number" min="0" value="0"></label></div>
         <div class="art-field-row"><label>Largura<input id="crop-w" type="number" min="1" value="${a?.width||''}"></label><label>Altura<input id="crop-h" type="number" min="1" value="${a?.height||''}"></label></div>
         <button class="action art-tool-button" data-art-action="crop" ${!a||svg?'disabled':''}>▣ Aplicar recorte</button>
       </section>
       <section class="art-tool-section"><div class="art-tool-title">02 / Redimensionar e DPI</div><div class="art-tool-tip">LANCZOS preserva a nitidez possível na reamostragem, mas não recria detalhes perdidos.</div>
         <div class="art-field-row"><label>Largura (px)<input id="art-width" type="number" min="1" max="15000" value="${a?.width||''}"></label><label>Altura (px)<input id="art-height" type="number" min="1" max="15000" value="${a?.height||''}"></label></div>
         <label class="art-check"><input id="art-aspect" type="checkbox" checked> Manter proporção</label>
         <div class="art-field-row"><label>DPI de impressão<input id="art-dpi" type="number" min="30" max="2400" value="${a?.dpi_x||300}"></label><label>Largura em cm<input id="art-cm" type="number" min="0.1" step="0.1" value="${a?(a.width/a.dpi_x*2.54).toFixed(1):''}"></label></div>
         <div class="art-tool-buttons"><button class="action art-tool-button" data-art-action="resize" ${!a||svg?'disabled':''}>↗ Alterar pixels</button><button class="action art-tool-button" data-art-action="dpi" ${!a||svg?'disabled':''}>◈ Gravar DPI</button></div>
       </section>
       <section class="art-tool-section"><div class="art-tool-title">03 / Remover fundo</div><div class="art-tool-tip">Fundo simples: elimina cores chapadas conectadas às bordas. Salva em PNG transparente.</div>
         <label class="art-full-label">Tolerância de cor <b id="art-tol-caption">28</b><input id="art-tolerance" type="range" min="0" max="100" value="28"></label>
         <button class="action art-tool-button" data-art-action="background_simple" ${!a||svg?'disabled':''}>◫ Remover fundo simples</button>
         <button class="action art-tool-button optional" data-art-action="background_ai" ${!a||svg||!cap.ai_background?'disabled':''}>✦ Fundo com IA ${cap.ai_background?'':'· instalar rembg'}</button>
       </section>
       <section class="art-tool-section"><div class="art-tool-title">04 / Vetorizar em SVG</div><div class="art-tool-tip">Ideal para logos, desenhos planos, linhas e estampas de poucas cores.</div>
         <select class="select art-wide" id="art-vector-mode"><option value="color">Cores / Posterização</option><option value="bw">Preto e branco</option></select>
         <button class="action art-tool-button" data-art-action="vectorize" ${!a||svg||!cap.vectorization?'disabled':''}>◇ Gerar SVG ${cap.vectorization?'':'· instalar VTracer'}</button>
       </section>
       <section class="art-tool-section"><div class="art-tool-title">05 / Ampliar com IA</div><div class="art-tool-tip">Integração opcional Real-ESRGAN NCNN/Vulkan (GPU AMD compatível com Vulkan).</div>
         <select class="select art-wide" id="art-scale"><option value="2">2× os pixels</option><option value="4">4× os pixels</option></select>
         <button class="action art-tool-button optional" data-art-action="upscale_ai" ${!a||svg||!cap.ai_upscale?'disabled':''}>✦ Ampliação IA ${cap.ai_upscale?'':'· configurar executável'}</button>
       </section>
     </div><div class="art-plugin-status">MÓDULOS: Pillow ✓ &nbsp; VTracer ${cap.vectorization?'✓':'—'} &nbsp; rembg ${cap.ai_background?'✓':'—'} &nbsp; Real-ESRGAN ${cap.ai_upscale?'✓':'—'}</div>
   </aside>
 </div>`;
}

async function editorLoad(){
 try{
   const [items,cap]=await Promise.all([api('/api/art'),api('/api/art/capabilities')]);
   artState.list=items;artState.capabilities=cap;
   if(!artState.list.some(a=>a.id===artState.selected))artState.selected=items[0]?.id||null;
   if(state.page==='art')render();
 }catch(e){flash('Não foi possível carregar o Editor de Arte: '+e.message,true)}
}
function artBusy(b){artState.busy=b;if(state.page==='art')render()}
function artDrawCrop(){
 const canvas=document.querySelector('#art-crop-layer'),img=document.querySelector('#art-preview');
 if(!canvas||!img||!img.complete||!img.naturalWidth)return;
 const width=img.clientWidth,height=img.clientHeight;if(!width||!height)return;
 canvas.width=width;canvas.height=height;canvas.style.width=width+'px';canvas.style.height=height+'px';
 const ctx=canvas.getContext('2d');ctx.clearRect(0,0,width,height);
 const crop=artState.crop;if(crop&&crop.width>0&&crop.height>0){
 const factorX=width/img.naturalWidth,factorY=height/img.naturalHeight;
 ctx.fillStyle='rgba(105,225,158,0.20)';ctx.strokeStyle='#a3ffc3';ctx.lineWidth=2;ctx.setLineDash([7,4]);
 ctx.fillRect(crop.x*factorX,crop.y*factorY,crop.width*factorX,crop.height*factorY);
 ctx.strokeRect(crop.x*factorX,crop.y*factorY,crop.width*factorX,crop.height*factorY);
 }
}
function artAttachCrop(){
 const img=document.querySelector('#art-preview'),canvas=document.querySelector('#art-crop-layer');
 if(!img||!canvas)return;
 img.addEventListener('load',artDrawCrop);if(img.complete)artDrawCrop();
 let start=null;
 const coords=e=>{const r=canvas.getBoundingClientRect();return {x:Math.max(0,Math.min(img.naturalWidth,Math.round((e.clientX-r.left)/r.width*img.naturalWidth))),y:Math.max(0,Math.min(img.naturalHeight,Math.round((e.clientY-r.top)/r.height*img.naturalHeight)))}};
 canvas.addEventListener('pointerdown',e=>{start=coords(e);canvas.setPointerCapture(e.pointerId);artState.crop={x:start.x,y:start.y,width:0,height:0};artDrawCrop()});
 canvas.addEventListener('pointermove',e=>{if(!start)return;const end=coords(e);artState.crop={x:Math.min(start.x,end.x),y:Math.min(start.y,end.y),width:Math.abs(end.x-start.x),height:Math.abs(end.y-start.y)};artDrawCrop();for(const [k,v] of Object.entries({'crop-x':artState.crop.x,'crop-y':artState.crop.y,'crop-w':artState.crop.width,'crop-h':artState.crop.height})){const input=document.getElementById(k);if(input)input.value=v}const label=document.getElementById('art-selection-label');if(label)label.textContent=`Seleção: ${artState.crop.width} × ${artState.crop.height} pixels`});
 canvas.addEventListener('pointerup',()=>start=null);canvas.addEventListener('pointercancel',()=>start=null);
}
async function artUpload(file){if(!file)return;const fd=new FormData();fd.append('file',file,file.name);const selectedOrder=document.querySelector('#art-order')?.value;if(selectedOrder)fd.append('order_code',selectedOrder);artBusy(true);
 try{const res=await fetch('/api/art/upload',{method:'POST',body:fd});const answer=await res.json();if(!res.ok)throw Error(typeof answer.detail==='string'?answer.detail:JSON.stringify(answer.detail));artState.selected=answer.id;artState.crop=null;flash('Arte importada. Original preservado.');await editorLoad()}
 catch(e){flash(e.message,true)}finally{artState.busy=false;if(state.page==='art')render()}
}
async function artProcess(action){const a=artGet();if(!a||artState.busy)return;
 const number=id=>Number(document.getElementById(id)?.value);
 let payload={action};
 if(action==='crop'){payload={...payload,x:number('crop-x'),y:number('crop-y'),width:number('crop-w'),height:number('crop-h')}}
 if(action==='resize'){payload={...payload,width:number('art-width'),height:number('art-height'),keep_aspect:document.getElementById('art-aspect')?.checked}}
 if(action==='dpi'){payload.dpi=number('art-dpi')}
 if(action==='background_simple'){payload.tolerance=number('art-tolerance')}
 if(action==='vectorize'){payload.mode=document.getElementById('art-vector-mode')?.value}
 if(action==='upscale_ai'){payload.scale=number('art-scale')}
 artBusy(true);
 try{const result=await api(`/api/art/${encodeURIComponent(a.id)}/process`,{method:'POST',body:JSON.stringify(payload)});artState.selected=result.id;artState.crop=null;flash('Nova revisão criada. Original intacto.');await editorLoad()}
 catch(e){flash('Falha no Editor: '+e.message,true)}finally{artState.busy=false;if(state.page==='art')render()}
}

root.addEventListener('click',e=>{
 if(state.page!=='art')return;
 const selected=e.target.closest('[data-art-select]');if(selected){artState.selected=selected.dataset.artSelect;artState.crop=null;render();return}
 if(e.target.closest('[data-art-upload]')){document.querySelector('#art-upload')?.click();return}
 const action=e.target.closest('[data-art-action]');if(action)artProcess(action.dataset.artAction);
});
root.addEventListener('change',e=>{
 if(e.target.id==='art-upload'){artUpload(e.target.files[0]);return}
 if(e.target.id==='art-order'){artState.orderCode=e.target.value;return}
 const a=artGet();if(!a)return;
 if(e.target.id==='art-cm'){const cm=Number(e.target.value),dpi=Number(document.querySelector('#art-dpi')?.value)||300;if(cm>0){const w=Math.round(cm/2.54*dpi);document.querySelector('#art-width').value=w; if(document.querySelector('#art-aspect')?.checked)document.querySelector('#art-height').value=Math.round(w*a.height/a.width)}}
 if(e.target.id==='art-width'&&document.querySelector('#art-aspect')?.checked){document.querySelector('#art-height').value=Math.max(1,Math.round(Number(e.target.value)*a.height/a.width))}
 if(e.target.id==='art-height'&&document.querySelector('#art-aspect')?.checked){document.querySelector('#art-width').value=Math.max(1,Math.round(Number(e.target.value)*a.width/a.height))}
 if(e.target.id==='art-dpi'){document.querySelector('#art-cm').value=(a.width/Number(e.target.value||300)*2.54).toFixed(1)}
});
root.addEventListener('input',e=>{if(e.target.id==='art-tolerance'){document.querySelector('#art-tol-caption').textContent=e.target.value}});
// A página anterior usa render() síncrono; agendamos os eventos após montar o HTML.
const _renderArtBase=artView;
artView=function(){const result=_renderArtBase();queueMicrotask(artAttachCrop);return result};
