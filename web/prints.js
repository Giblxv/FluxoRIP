'use strict';
/* Fluxo RIP PRINT CONSOLE — independent recreation of documented PrintExp workflows.
   All actions use local administrative APIs only. No sockets or Hoson commands. */
const printConsole = {tab:'jobs',printer:'',job:null,profile:null,layout:null,records:[],arts:[],capabilities:null,busy:false};
const pcTabs=[['jobs','Trabalhos'],['settings','Configurações'],['calibration','Calibração'],['maintenance','Manutenção'],['advanced','Avançado'],['logs','Logs']];
const pcProcedure={TESTE_BICOS:'Teste de bicos',NIVEL_CABECOTE:'Nivelamento do cabeçote',VERTICAL_CABECOTE:'Alinhamento vertical',STEPPING:'Calibração de avanço / stepping',ESPACAMENTO_HORIZONTAL:'Espaçamento horizontal dos cabeçotes',ESPACAMENTO_VERTICAL:'Espaçamento vertical dos cabeçotes',BIDIRECIONAL:'Alinhamento bidirecional',TRAPPING:'Registro de cores / trapping',LIMPEZA:'Limpeza',FLASH:'Flash spray',HIDRATACAO:'Hidratação',MOVIMENTACAO:'Deslocamento / retorno',ALIMENTACAO:'Avanço / retorno do material',TINTA:'Carga / circulação de tinta',TENSÃO_VERIFICADA:'Verificação de tensão',VERIFICACAO_REDE:'Conexão Ethernet',BACKUP_PARAMETROS:'Backup de parâmetros',OUTRO:'Outra intervenção'};
function pcPrinter(){return state.data.printers.find(x=>x.id===(printConsole.printer||state.selectedPrinter))||state.data.printers[0]||null}
function pcJobs(){const pr=pcPrinter();return state.data.jobs.filter(j=>j.printer_id===pr?.id)}
function pcJob(){const jobs=pcJobs();return jobs.find(j=>j.id===Number(printConsole.job))||jobs[0]||null}
function pcFormat(v){return Number(v??0).toLocaleString('pt-BR',{maximumFractionDigits:2})}
function pcField(label,key,value,{type='text',min='',max='',step='',placeholder=''}={}){
  return `<label class="pc-field"><span>${esc(label)}</span><input name="${esc(key)}" type="${type}" value="${esc(value??'')}" ${min!==''?`min="${esc(min)}"`:''} ${max!==''?`max="${esc(max)}"`:''} ${step!==''?`step="${esc(step)}"`:''} placeholder="${esc(placeholder)}"></label>`;
}
function pcSelect(label,key,choices,value){return `<label class="pc-field"><span>${esc(label)}</span><select name="${esc(key)}">${choices.map(([k,n])=>option(k,n,value)).join('')}</select></label>`;}
// A navegação de seções aparece somente na primeira linha.
// A segunda linha oferece ações reais da seção ativa, nunca atalhos para as mesmas abas.
const pcContextActions={
 jobs:[
  ['new-job','＋','Novo trabalho','Abrir cadastro de trabalho'],
  ['preview','▧','Ver prévia','Ir para a área de pré-visualização'],
  ['save-layout','▤','Salvar composição','Salvar propriedades do trabalho selecionado'],
  ['move-up','↑','Subir na fila','Reordenar trabalho na fila administrativa'],
 ],
 settings:[
  ['focus-dpi','▦','Ajustar DPI','Editar resolução no perfil local'],
  ['focus-passes','≋','Passadas','Editar passadas no perfil local'],
  ['focus-margin','↔','Margens','Editar margem no perfil local'],
  ['save-profile','✓','Salvar perfil','Salvar no Fluxo RIP, não na impressora'],
 ],
 calibration:[
  ['nozzles','⌖','Teste de bicos','Registrar teste realizado na máquina'],
  ['bidirectional','⇄','Bidirecional','Registrar alinhamento bidirecional'],
  ['stepping','↕','Avanço / passo','Registrar calibração de avanço'],
  ['all-calibration','▦','Ver procedimentos','Ir para os checklists de calibração'],
 ],
 maintenance:[
  ['cleaning','✳','Limpeza','Registrar manutenção de limpeza'],
  ['flash','✶','Flash','Registrar verificação de flash'],
  ['feeding','↕','Avanço de mídia','Registrar teste de alimentação'],
  ['all-maintenance','▦','Ver checklist','Ir para todos os procedimentos de manutenção'],
 ],
 advanced:[
  ['edit-printer','⚙','Editar cadastro','Editar dados locais da impressora'],
  ['network','◇','Rede cadastrada','Consultar IP e informações do equipamento'],
  ['safety','⊘','Restrições','Ver ações bloqueadas por segurança'],
 ],
 logs:[
  ['refresh-logs','↻','Atualizar','Recarregar o histórico desta impressora'],
  ['export-logs','⇩','Exportar CSV','Baixar registros em planilha CSV'],
  ['new-note','＋','Registrar ocorrência','Adicionar registro técnico manual'],
 ]
};
function pcContextToolbar(){
 const context=pcContextActions[printConsole.tab]||[];
 const job=pcJob(),hasPrinter=Boolean(pcPrinter());
 return `<div class="pc-context-toolbar" role="toolbar" aria-label="Ações de ${esc(pcTabs.find(([id])=>id===printConsole.tab)?.[1]||'impressão')}">
 <span class="pc-context-label">AÇÕES</span>
 ${context.map(([id,icon,label,title])=>{
  const disabled=!hasPrinter || (['preview','save-layout','move-up'].includes(id)&&!job) || (id==='save-layout'&&job?.status!=='AGUARDANDO');
  return `<button type="button" class="pc-context-action" data-pc-action="${id}" title="${esc(title)}" ${disabled?'disabled':''}><span aria-hidden="true" class="pc-context-symbol">${icon}</span><span>${esc(label)}</span></button>`;
 }).join('')}
 <span class="pc-context-hint">${printConsole.tab==='jobs'?'Fila administrativa • sem comandos à máquina':printConsole.tab==='settings'?'Perfil local • não altera o PrintExp':printConsole.tab==='logs'?'Registros manuais por equipamento':'Registro e consulta • operação física no PrintExp'}</span>
 </div>`;
}
function pcInfo(){return '<div class="pc-warning"><strong>CONTROLE PASSIVO</strong> Os valores e ocorrências desta tela são registros do Fluxo RIP. Não são enviados ao PrintExp, não executam ações na impressora e não representam telemetria.</div>'}
function pcPanelTitle(title,minor=''){return `<div class="pc-panel-title"><b>${esc(title)}</b><small>${esc(minor)}</small></div>`}
function pcRow(title,desc,stateText){return `<div class="pc-spec-row"><span><b>${esc(title)}</b><small>${esc(desc)}</small></span><em>${esc(stateText)}</em></div>`}
async function printsLoad(){
 if(state.page!=='prints'||printConsole.busy)return;
 const p=pcPrinter();if(!p){render();return}printConsole.printer=p.id;
 printConsole.busy=true;
 try{
  const j=pcJob();
  const [profile,records,caps,arts,layout]=await Promise.all([
   api('/api/print-console/profiles/'+encodeURIComponent(p.id)),
   api('/api/print-console/records?printer_id='+encodeURIComponent(p.id)),
   api('/api/print-console/capabilities'),
   api('/api/art'),
   j?api('/api/print-console/jobs/'+j.id+'/layout'):Promise.resolve(null)
  ]);
  printConsole.profile=profile;printConsole.records=records;printConsole.capabilities=caps;
  printConsole.arts=arts;printConsole.layout=layout;printConsole.job=j?.id||null;
  if(state.page==='prints')render();
 }catch(err){flash('Impressões: '+err.message,true)}finally{printConsole.busy=false}
}
function printsView(){
 const p=pcPrinter(),j=pcJob();const printer= p?`<b>${esc(p.name)}</b> <span>${processLabel(p.technology)} • Hoson</span>`:'Nenhuma impressora cadastrada';
 return `<div class="pc-shell">
  <div class="pc-top"><div class="pc-top-brand"><span class="pc-dot"></span><b>PRINT CONTROL</b><small>Fluxo RIP / HOSON</small></div><div class="pc-top-select"><label>IMPRESSORA</label><select id="pc-printer">${state.data.printers.map(x=>option(x.id,x.name+' • '+processLabel(x.technology),p?.id)).join('')}</select></div><div class="pc-top-connection"><span class="pc-offline">SEM TELEMETRIA</span><small>Ethernet • estado real desconhecido</small></div></div>
  <div class="pc-toolbars"><div class="pc-toolbar-top">${pcTabs.map(([id,label])=>`<button data-pc-tab="${id}" class="pc-tab ${printConsole.tab===id?'active':''}">${esc(label)}</button>`).join('')}</div>
  ${pcContextToolbar()}</div>
  ${pcInfo()}
  ${!p?`<div class="panel">${empty('Nenhum equipamento','Cadastre uma impressora Hoson na aba Impressoras.')}</div>`:({jobs:pcJobsView,settings:pcSettingsView,calibration:pcCalibrationView,maintenance:pcMaintenanceView,advanced:pcAdvancedView,logs:pcLogsView}[printConsole.tab]||pcJobsView)(p,j)}
  <div class="pc-statusbar"><span>IMPRESSORA: ${printer}</span><span>TRABALHOS NA FILA: ${pcJobs().filter(x=>x.status==='AGUARDANDO').length}</span><span>CONEXÃO HOSON: NÃO VERIFICADA</span><span>Fluxo RIP 1.4 • MODO PASSIVO</span></div>
 </div>`;
}
function pcJobsView(p,j){const jobs=pcJobs(), l=printConsole.layout?.job_id===j?.id?printConsole.layout?.values:null;
 const art=l?.art_revision_id?printConsole.arts.find(a=>a.id===l.art_revision_id):null;
 return `<div class="pc-layout"><div class="pc-listpanel">${pcPanelTitle('LISTA DE TRABALHOS',`${jobs.length} trabalhos / ${p.name}`)}
 <div class="pc-list-scroll">${jobs.length?jobs.map(x=>`<button class="pc-job ${j?.id===x.id?'selected':''}" data-pc-job="${x.id}"><span class="pc-job-icon">▣</span><span class="pc-job-copy"><b>${esc(x.file_name||'Trabalho #'+x.id)}</b><small>${esc(x.order_code)} • ${x.copies} cópia(s) • #${x.id}</small><i>${jobName(x.status)} (manual)</i></span></button>`).join(''):empty('Fila vazia','Adicione trabalhos na aba Fila de impressão.')}</div>
 <div class="pc-list-actions"><button class="action sm soft" data-pc-move="up" ${!j?'disabled':''}>↑ Subir</button><button class="action sm soft" data-pc-move="down" ${!j?'disabled':''}>↓ Descer</button><button class="action sm soft" data-pc-move="top" ${!j?'disabled':''}>⇧ Primeiro</button><button class="action sm soft" data-pc-move="bottom" ${!j?'disabled':''}>⇩ Último</button></div></div>
 <div class="pc-previewpanel">${pcPanelTitle('PRÉ-VISUALIZAÇÃO DO TRABALHO','Arquivo raster vinculado quando disponível')}
 <div class="pc-preview-stage">${art&&art.file_format!=='SVG'?`<img src="/api/art/${encodeURIComponent(art.id)}/preview" alt="Prévia da arte vinculada">`:`<div class="pc-preview-empty"><span>▧</span><b>${esc(j?.file_name||'Nenhum arquivo selecionado')}</b><small>Arquivos PRN não são decodificados neste módulo.<br>Vincule uma revisão do Editor de Arte para mostrar a prévia.</small></div>`}</div>
 <div class="pc-job-commands">${j?`
 ${j.status==='AGUARDANDO'?`<button class="action primary sm" data-pc-status="IMPRIMINDO">Registrar início (manual)</button><button class="action danger sm" data-pc-status="CANCELADO">Cancelar no Fluxo RIP</button>`:''}
 ${j.status==='IMPRIMINDO'?`<button class="action sm soft" data-pc-status="AGUARDANDO">Registrar pausa (manual)</button><button class="action primary sm" data-pc-status="CONCLUIDO">Registrar conclusão</button><button class="action danger sm" data-pc-status="ERRO">Registrar falha</button>`:''}
 ${j.status==='ERRO'||j.status==='CANCELADO'?`<button class="action sm soft" data-pc-status="AGUARDANDO">Recolocar na fila do Fluxo RIP</button>`:''}
 `:''}</div>
 <div class="pc-job-details">${j?`<span>Pedido <b>${esc(j.order_code)}</b></span><span>Status <b>${jobName(j.status)}</b></span><span>Cópias <b>${j.copies}</b></span>`:'Selecione um trabalho'}</div>
 </div><div class="pc-inspectorpanel">${pcPanelTitle('PROPRIEDADES DO TRABALHO',j?'#'+j.id:'Sem seleção')}${j?`<form id="pc-layout-form" class="pc-form">
 <div class="pc-field-grid">${pcField('Colunas','columns',l?.columns??1,{type:'number',min:1,max:100})}${pcField('Linhas','rows',l?.rows??1,{type:'number',min:1,max:100})}${pcField('Espaço X (mm)','spacing_x_mm',l?.spacing_x_mm??0,{type:'number',min:0,step:.1})}${pcField('Espaço Y (mm)','spacing_y_mm',l?.spacing_y_mm??0,{type:'number',min:0,step:.1})}${pcField('Origem X (mm)','origin_x_mm',l?.origin_x_mm??0,{type:'number',min:0,step:.1})}${pcField('Origem Y (mm)','origin_y_mm',l?.origin_y_mm??0,{type:'number',min:0,step:.1})}${pcField('Largura da região (mm)','region_width_mm',l?.region_width_mm??'',{type:'number',min:0.01,step:.1,placeholder:'Opcional'})}${pcField('Altura da região (mm)','region_height_mm',l?.region_height_mm??'',{type:'number',min:0.01,step:.1,placeholder:'Opcional'})}</div>
 ${pcSelect('Revisão da arte para prévia','art_revision_id',[['','Sem arte vinculada'],...printConsole.arts.filter(a=>a.order_code===j.order_code&&a.file_format!=='SVG').map(a=>[a.id,a.original_name+' • '+a.operation+' • '+a.id.slice(0,8)])],l?.art_revision_id||'')}
 <label class="pc-field"><span>Observações do operador</span><textarea name="operator_notes" rows="2" maxlength="2000">${esc(l?.operator_notes||'')}</textarea></label>
 <button type="submit" class="action primary" ${j.status!=='AGUARDANDO'?'disabled title="Edição somente para trabalhos aguardando"':''}>Salvar composição (Fluxo RIP)</button>
 </form>`:empty('Nenhum trabalho','Crie um trabalho na fila administrativa.')}</div></div>`;
}
function pcSettingsView(p){const v=printConsole.profile?.printer_id===p.id?printConsole.profile.values:{};
 return `<div class="pc-split"><div class="pc-config-panel">${pcPanelTitle('PERFIL LOCAL DE IMPRESSÃO','Parâmetros de referência — não enviados à máquina')}
 <form id="pc-profile-form" class="pc-form"><div class="pc-field-grid">
 ${pcField('Modo de impressão (informativo)','print_mode',v.print_mode??'A definir no PrintExp')}${pcField('Passadas','passes',v.passes??'',{type:'number',min:1,max:32,placeholder:'Ex.: 4 ou 6'})}
 ${pcField('Resolução X (DPI)','dpi_x',v.dpi_x??'',{type:'number',min:72,max:2400})}${pcField('Resolução Y (DPI)','dpi_y',v.dpi_y??'',{type:'number',min:72,max:2400})}
 ${pcSelect('Velocidade','speed',[['LOW','Baixa'],['MEDIUM','Média'],['HIGH','Alta']],v.speed||'MEDIUM')}
 ${pcSelect('Direção','direction',[['BIDIRECTIONAL','Bidirecional'],['LEFT','Da direita para esquerda'],['RIGHT','Da esquerda para direita']],v.direction||'BIDIRECTIONAL')}
 ${pcField('Margem X (mm)','margin_x_mm',v.margin_x_mm??0,{type:'number',min:0,step:.1})}
 ${pcSelect('Barra de cores','color_bar',[['OFF','Desligada'],['LEFT','Esquerda'],['RIGHT','Direita'],['BOTH','Ambos os lados']],v.color_bar||'OFF')}
 ${pcField('Largura barra de cores (mm)','color_bar_width_mm',v.color_bar_width_mm??0,{type:'number',min:0,step:.1})}
 ${pcField('Distância barra de cores (mm)','color_bar_distance_mm',v.color_bar_distance_mm??0,{type:'number',min:0,step:.1})}
 ${pcSelect('Feather (registro local)','feather_mode',[['DESLIGADO','Desligado'],['SUAVE','Suave'],['MEDIO','Médio'],['FORTE','Forte']],v.feather_mode||'DESLIGADO')}
 </div><div class="pc-checks"><label><input type="checkbox" name="flash_before" ${v.flash_before?'checked':''}> Flash antes de imprimir (referência)</label><label><input type="checkbox" name="auto_clean" ${v.auto_clean?'checked':''}> Limpeza automática (referência)</label></div>
 <label class="pc-field"><span>Observações / preset do equipamento</span><textarea name="extra_notes" rows="3" maxlength="3000">${esc(v.extra_notes||'')}</textarea></label>
 <button class="action primary" type="submit">Salvar perfil no Fluxo RIP</button></form></div><div class="pc-side-explainer">${pcPanelTitle('COMO USAR ESTE PERFIL')}
 <p>Registre os parâmetros recomendados para esta impressora. Depois compare-os com a configuração real do PrintExp na estação responsável.</p>
 ${pcRow('Pressão de tinta / tensão','Valores críticos devem ser tratados pelo técnico','SEM COMANDO')}
 ${pcRow('Modo / passadas','Podem variar por RIP, firmware e cabeçote','VERIFICAR')}
 ${pcRow('Barras de cor / feather','Opções documentadas no PrintExp','REFERÊNCIA')}
 <div class="pc-tip">O Fluxo RIP não substitui o driver/RIP nem altera configuração de hardware nesta etapa.</div></div></div>`;
}
const pcCalibrationItems=[
 ['TESTE_BICOS','Teste de bicos','Verificar falhas nas linhas dos canais'],
 ['NIVEL_CABECOTE','Nivelamento do cabeçote','Avaliar plano horizontal dos cabeçotes'],
 ['VERTICAL_CABECOTE','Alinhamento vertical','Conferir perpendicularidade dos jatos'],
 ['STEPPING','Avanço / stepping','Conferir passo conforme modo e mídia'],
 ['ESPACAMENTO_HORIZONTAL','Espaçamento horizontal','Conferir registro entre cabeçotes em X'],
 ['ESPACAMENTO_VERTICAL','Espaçamento vertical','Conferir registro em Y'],
 ['BIDIRECIONAL','Alinhamento bidirecional','Validar registro em dois sentidos'],
 ['TRAPPING','Registro / trapping','Conferir coincidência das cores']
];
const pcMaintItems=[
 ['LIMPEZA','Limpeza de cabeçote','Fraca, média ou forte: escolha na máquina'],
 ['FLASH','Flash / aspersão','Verificar se a função está habilitada no PrintExp'],
 ['HIDRATACAO','Hidratação','Verificar manutenção de descanso'],
 ['ALIMENTACAO','Avanço de mídia','Conferir alimentação e tensão do filme'],
 ['MOVIMENTACAO','Movimentação / retorno','Confirmar ausência de obstáculos antes de comandar no PrintExp'],
 ['TINTA','Circuito de tinta','Conferir níveis e circulação conforme equipamento']
];
function pcActionCards(items,category){return `<div class="pc-card-grid">${items.map(([id,title,desc])=>`<div class="pc-procedure-card"><div class="pc-proc-icon">${category==='CALIBRACAO'?'⌖':'✳'}</div><strong>${esc(title)}</strong><p>${esc(desc)}</p><button class="action sm soft" data-pc-record="${id}" data-category="${category}">Registrar verificação</button></div>`).join('')}</div>`}
function pcCalibrationView(p){return `<div class="pc-section">${pcPanelTitle('CALIBRAÇÃO E ALINHAMENTO','Procedimentos documentados no PrintExp — somente registro')}
 <div class="pc-tip">Testes de bicos, stepping, alinhamento bidirecional e ajustes de cabeçote são realizados no PrintExp oficial por operador qualificado. Fluxo RIP registra o resultado, sem mover eixos ou alterar valores.</div>
 ${pcActionCards(pcCalibrationItems,'CALIBRACAO')}</div>`}
function pcMaintenanceView(p){return `<div class="pc-section">${pcPanelTitle('MANUTENÇÃO OPERACIONAL','Checklist para operador / nenhum comando à impressora')}
 <div class="pc-tip">Use os controles reais do PrintExp para acionar limpeza, flash e movimentação. No Fluxo RIP, cada botão abaixo abre somente um formulário de registro.</div>
 ${pcActionCards(pcMaintItems,'MANUTENCAO')}</div>`}
function pcAdvancedView(p){return `<div class="pc-split"><div class="pc-config-panel">${pcPanelTitle('CONTROLADORA HOSON','Identificação cadastrada, não lida da máquina')}
 ${pcRow('Impressora',p.name,'CADASTRO')}${pcRow('Tecnologia',processLabel(p.technology),'CADASTRO')}
 ${pcRow('Endereço IP',p.ip||'Não informado','NÃO CONSULTADO')}${pcRow('Estação',p.workstation||'Não informada','CADASTRO')}
 ${pcRow('Versão PrintExp',p.printexp_version||'Não identificada','PENDENTE')}${pcRow('Firmware',p.firmware||'Não identificado','PENDENTE')}
 ${pcRow('Controladora',p.controller||'Hoson','FAMÍLIA')}
 <button class="action soft" data-pc-edit-printer="${esc(p.id)}">Editar cadastro da máquina</button>
 </div><div class="pc-side-explainer">${pcPanelTitle('OPÇÕES TÉCNICAS AVANÇADAS','Somente consulta e documentação')}
 ${pcRow('Rede / comunicação','TCP configurado pelo PrintExp original','NÃO AUTOMATIZADO')}
 ${pcRow('Tensão de cabeçotes','Alterações podem danificar hardware','BLOQUEADO')}
 ${pcRow('Motores / origem','Movimentação de risco em produção','BLOQUEADO')}
 ${pcRow('Firmware .bsf / parâmetros .xtf','Faça backup pela ferramenta oficial','BLOQUEADO')}
 ${pcRow('Configurações de fábrica','Exigem identificação do modelo e validação','BLOQUEADO')}
 <div class="pc-tip">Não coloque senhas do PrintExp dentro do Fluxo RIP. O acesso ao menu de fábrica não implica que exista API para automação nem compatibilidade de parâmetros entre placas.</div>
 </div></div>`}
function pcLogsView(p){const records=printConsole.records||[];return `<div class="pc-section">${pcPanelTitle('REGISTROS DE INTERVENÇÕES','Atualizados manualmente pelo operador')}
 <div class="pc-log-list">${records.length?records.map(r=>`<div class="pc-log-line"><span class="pc-log-time">${dateTime(r.created_at)}</span><b>${esc(pcProcedure[r.procedure]||r.procedure)}</b><span>${esc(r.outcome)}</span><span>${esc(r.operator)}</span><small>${esc(r.notes||'—')}</small></div>`).join(''):empty('Nenhuma intervenção registrada','Registre um teste de calibração ou manutenção para iniciar o histórico.')}</div></div>`}
function pcRecordDialog(category,procedure){const p=pcPrinter();if(!p)return;
 openDialog(`${modalHead('Registrar procedimento técnico')}<p class="detail-intro">${esc(p.name)} • ${esc(pcProcedure[procedure]||procedure)}</p>
 <form id="pc-record-form" data-printer="${esc(p.id)}"><input type="hidden" name="category" value="${esc(category)}"><input type="hidden" name="procedure" value="${esc(procedure)}"><div class="form-body">
 <div class="note-block">Este formulário registra algo feito ou planejado pelo operador no PrintExp. Não acionará nenhum comando.</div>
 <div class="form-grid"><label><span>Resultado *</span><select name="outcome">${[['REALIZADO','Realizado pelo operador'],['PLANEJADO','Planejado'],['PENDENTE','Pendente'],['FALHA','Falha encontrada']].map(([k,v])=>option(k,v,'REALIZADO')).join('')}</select></label><label><span>Operador *</span><input name="operator" required minlength="2" maxlength="100" placeholder="Nome do responsável"></label></div>
 <label><span>Observações</span><textarea name="notes" maxlength="2000" rows="4" placeholder="Resultado obtido, próximos passos e materiais..."></textarea></label></div>
 ${formFooter('Salvar registro')}</form>`);
}
function pcNumber(value,emptyIsNull=false){return emptyIsNull&&value===''?null:Number(value)}
async function pcSaveProfile(form){const fd=new FormData(form),str=Object.fromEntries(fd.entries());
 const numeric=['passes','dpi_x','dpi_y','margin_x_mm','color_bar_width_mm','color_bar_distance_mm'];numeric.forEach(k=>str[k]=pcNumber(str[k],['passes','dpi_x','dpi_y'].includes(k)));
 str.flash_before=fd.has('flash_before');str.auto_clean=fd.has('auto_clean');
 await api('/api/print-console/profiles/'+encodeURIComponent(pcPrinter().id),{method:'PUT',body:JSON.stringify(str)});
 flash('Perfil administrativo salvo. Nada foi enviado ao PrintExp.');await printsLoad();
}
async function pcSaveLayout(form){const fd=new FormData(form),str=Object.fromEntries(fd.entries());
 ['columns','rows','spacing_x_mm','spacing_y_mm','origin_x_mm','origin_y_mm','region_width_mm','region_height_mm'].forEach(k=>str[k]=pcNumber(str[k],['region_width_mm','region_height_mm'].includes(k)));
 str.art_revision_id=str.art_revision_id||null;
 await api('/api/print-console/jobs/'+pcJob().id+'/layout',{method:'PUT',body:JSON.stringify(str)});
 flash('Composição salva (sem gerar arquivo RIP).');await printsLoad();
}
function pcFocus(name){
 const field=document.querySelector(`#view .pc-shell [name="${name}"]`);
 if(!field){flash('Campo não disponível nesta seção.',true);return}
 field.scrollIntoView({behavior:'auto',block:'center'});
 field.focus({preventScroll:true});
 field.closest('.pc-field')?.classList.add('pc-field-highlight');
}
function pcExportLogs(){
 const p=pcPrinter(),records=printConsole.records||[];
 if(!p)return;
 if(!records.length){flash('Não existem registros para exportar nesta impressora.',true);return}
 // CSV com BOM para Excel e proteção contra fórmulas em campos digitados pelo operador.
 const cell=(value)=>{let v=String(value??'');if(/^[\s]*[=+@\-]/.test(v))v="'"+v;return '"'+v.replace(/"/g,'""')+'"'};
 const rows=[['Data','Procedimento','Categoria','Resultado','Operador','Observações','Impressora'],
  ...records.map(r=>[dateTime(r.created_at),pcProcedure[r.procedure]||r.procedure,r.category,r.outcome,r.operator,r.notes||'',p.name])];
 const csv='\uFEFF'+rows.map(row=>row.map(cell).join(';')).join('\r\n');
 const url=URL.createObjectURL(new Blob([csv],{type:'text/csv;charset=utf-8;'}));
 const anchor=document.createElement('a');anchor.href=url;
 anchor.download='Fluxo RIP_registros_'+p.id.replace(/[^a-z0-9_-]/gi,'_')+'.csv';
 document.body.appendChild(anchor);anchor.click();anchor.remove();
 setTimeout(()=>URL.revokeObjectURL(url),1000);
 flash('Histórico exportado em CSV.');
}
async function pcContextAction(action){
 const p=pcPrinter();if(!p)return;
 const j=pcJob();
 switch(action){
  case 'new-job':
   if(!state.data.orders.length){flash('Cadastre um projeto antes de adicionar à fila.',true);return}
   jobModal();return;
  case 'preview':
   document.querySelector('.pc-previewpanel')?.scrollIntoView({behavior:'auto',block:'nearest'});return;
  case 'save-layout':
   document.querySelector('#pc-layout-form')?.requestSubmit();return;
  case 'move-up':
   if(!j)return;
   try{await api('/api/jobs/'+j.id+'/move',{method:'PATCH',body:JSON.stringify({direction:'up'})});await load();await printsLoad();flash('Trabalho movido na fila administrativa.')}catch(err){flash(err.message,true)}return;
  case 'focus-dpi':pcFocus('dpi_x');return;
  case 'focus-passes':pcFocus('passes');return;
  case 'focus-margin':pcFocus('margin_x_mm');return;
  case 'save-profile':document.querySelector('#pc-profile-form')?.requestSubmit();return;
  case 'nozzles':pcRecordDialog('CALIBRACAO','TESTE_BICOS');return;
  case 'bidirectional':pcRecordDialog('CALIBRACAO','BIDIRECIONAL');return;
  case 'stepping':pcRecordDialog('CALIBRACAO','STEPPING');return;
  case 'all-calibration':document.querySelector('.pc-card-grid')?.scrollIntoView({behavior:'auto',block:'start'});return;
  case 'cleaning':pcRecordDialog('MANUTENCAO','LIMPEZA');return;
  case 'flash':pcRecordDialog('MANUTENCAO','FLASH');return;
  case 'feeding':pcRecordDialog('MANUTENCAO','ALIMENTACAO');return;
  case 'all-maintenance':document.querySelector('.pc-card-grid')?.scrollIntoView({behavior:'auto',block:'start'});return;
  case 'edit-printer':printerModal(p);return;
  case 'network':document.querySelector('.pc-config-panel')?.scrollIntoView({behavior:'auto',block:'start'});return;
  case 'safety':document.querySelector('.pc-side-explainer')?.scrollIntoView({behavior:'auto',block:'start'});return;
  case 'refresh-logs':await printsLoad();flash('Histórico atualizado.');return;
  case 'export-logs':pcExportLogs();return;
  case 'new-note':pcRecordDialog('DIAGNOSTICO','OUTRO');return;
 }
}
function pcBind(){
 const rootEl=document.getElementById('view');const dialogEl=document.getElementById('dialog');
 rootEl.addEventListener('click',async e=>{
  if(state.page!=='prints')return;
  const b=e.target.closest('button');if(!b)return;
  if(b.dataset.pcAction){await pcContextAction(b.dataset.pcAction);return}
  if(b.dataset.pcStatus){const j=pcJob();if(j){await changeJobStatus(j.id,b.dataset.pcStatus);await printsLoad()}return}
  if(b.dataset.pcTab){printConsole.tab=b.dataset.pcTab;render();if(!printConsole.profile||!printConsole.capabilities)printsLoad();return}
  if(b.dataset.pcJob){printConsole.job=Number(b.dataset.pcJob);printConsole.layout=null;render();printsLoad();return}
  if(b.dataset.pcRecord){pcRecordDialog(b.dataset.category,b.dataset.pcRecord);return}
  if(b.dataset.pcEditPrinter){printerModal(state.data.printers.find(x=>x.id===b.dataset.pcEditPrinter));return}
  if(b.dataset.pcMove){const j=pcJob();if(!j)return;try{await api('/api/jobs/'+j.id+'/move',{method:'PATCH',body:JSON.stringify({direction:b.dataset.pcMove})});await load();await printsLoad();flash('Fila administrativa reordenada.')}catch(err){flash(err.message,true)}}
 });
 rootEl.addEventListener('change',e=>{if(state.page==='prints'&&e.target.id==='pc-printer'){printConsole.printer=e.target.value;printConsole.job=null;printConsole.layout=null;printConsole.profile=null;printConsole.records=[];render();printsLoad()}});
 rootEl.addEventListener('submit',async e=>{if(state.page!=='prints'||!['pc-layout-form','pc-profile-form'].includes(e.target.id))return;e.preventDefault();let btn=e.target.querySelector('[type=submit]');btn.disabled=true;try{if(e.target.id==='pc-layout-form')await pcSaveLayout(e.target);else await pcSaveProfile(e.target)}catch(err){flash(err.message,true)}finally{if(btn.isConnected)btn.disabled=false}});
 dialogEl.addEventListener('submit',async e=>{if(e.target.id!=='pc-record-form')return;e.preventDefault();e.stopImmediatePropagation();const fd=new FormData(e.target),payload={...Object.fromEntries(fd.entries()),printer_id:e.target.dataset.printer};try{await api('/api/print-console/records',{method:'POST',body:JSON.stringify(payload)});closeDialog();flash('Intervenção registrada no histórico.');await printsLoad()}catch(err){flash(err.message,true)}} ,true);
}
pcBind();
