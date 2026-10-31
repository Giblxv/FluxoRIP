'use strict';
const stationsState={items:[],links:[],unassigned:[],message:'Carregando...',updated:false};
async function stationsInit(){
  try {
    const [response, mapping]=await Promise.all([api('/api/stations'),api('/api/printer-links')]);
    stationsState.items=response.stations||[];
    stationsState.links=mapping.links||[];
    stationsState.unassigned=mapping.unassigned||[];
    stationsState.message=response.note||'';
    stationsState.updated=true;
    if(state.page==='stations')render();
  } catch(err){stationsState.message='Não foi possível carregar as estações: '+err.message;flash(stationsState.message,true)}
}
function stationStatus(link){
  if(!link.station_online)return '<span class="state waiting">Estação sem sinal</span>';
  if(link.status==='INTERFACE_NAO_ENCONTRADA')return '<span class="state waiting">Porta não encontrada</span>';
  return '<span class="state complete">Vínculo registrado</span>';
}
function stationsView(){
  if(!stationsState.updated)return `<div class="loading-card">${esc(stationsState.message)}</div>`;
  const items=stationsState.items, links=stationsState.links;
  return `<div class="metrics">
    ${metric('Estações cadastradas',items.length,'Computadores que relataram conexão',true)}
    ${metric('Agentes recentes',items.filter(x=>x.online).length,'Recebimento nos últimos 5 minutos')}
    ${metric('Portas Hoson',items.reduce((n,s)=>n+s.interfaces.filter(i=>i.hoson_subnet).length,0),'Interfaces em 192.168.127.x')}
    ${metric('Máquinas associadas',links.length,'Vínculos manuais, sem comandos físicos')}
   </div>
   <div class="panel" style="margin-bottom:18px"><div class="panel-header"><strong>MAPA IMPRESSORAS ↔ ESTAÇÕES / ETHERNET</strong><span class="dim">${links.length} associação(ões)</span></div>
   <div class="table-wrap"><table class="data-table"><thead><tr><th>Impressora</th><th>Estação</th><th>Porta Ethernet</th><th>IP da impressora</th><th>Situação</th><th>Ações</th></tr></thead><tbody>
   ${links.length?links.map(l=>`<tr><td><b>${esc(l.printer_name)}</b><div class="subline">${esc(l.technology)} · ${esc(l.printer_id)}</div></td>
   <td>${esc(l.station_name)}</td><td>${esc(l.interface_name||'Não encontrada')} <small class="dim">#${l.interface_id}</small></td>
   <td class="mono">${esc(l.printer_ip||'Não informado')}${l.observed_ip_on_interface?'<div class="subline">IP visto no scan (identidade não confirmada)</div>':''}</td>
   <td>${stationStatus(l)}</td><td><div class="row-actions"><button class="mini-btn" data-station-edit="${esc(l.printer_id)}">Alterar</button><button class="mini-btn" data-station-remove="${esc(l.printer_id)}">Desvincular</button></div></td></tr>`).join(''):
   `<tr><td colspan="6">${empty('Nenhuma máquina associada','Associe as impressoras manualmente às interfaces das estações.')}</td></tr>`}
   </tbody></table></div>
   ${stationsState.unassigned.length?`<div class="station-unassigned"><b>Sem associação:</b> ${stationsState.unassigned.map(p=>esc(p.name)).join(' · ')}</div>`:''}
   </div>
   <div class="panel"><div class="panel-header"><strong>COMPUTADORES DA PRODUÇÃO</strong><button class="action soft" data-refresh-stations="true">↻ Atualizar</button></div>
   <div class="table-wrap"><table class="data-table"><thead><tr><th>Estação</th><th>Sistema</th><th>Última comunicação</th><th>Interfaces de rede</th><th>Descobertas locais</th><th>Ações</th></tr></thead><tbody>
   ${items.length?items.map(s=>`<tr><td><b>${esc(s.name)}</b><div class="subline">${esc(s.hostname)}</div></td>
   <td>${esc(s.os_name)}</td><td><span class="state ${s.online?'complete':'waiting'}">${s.online?'Agente recente':'Sem atualização'}</span><div class="subline">${dateTime(s.last_seen)}</div></td>
   <td>${s.interfaces.length?s.interfaces.map(i=>`<div><b>${esc(i.name)}</b> · ${esc(i.status)} · ${esc(i.ips.join(', ')||'sem IPv4')} ${i.hoson_subnet?'• HOSON':''}</div>`).join(''):'Sem informações'}</td>
   <td>${s.observations.length?s.observations.map(o=>`<div>${esc(o.ip)} ${o.mac?`<span class="dim">(${esc(o.mac)})</span>`:''} · ${esc(o.interface_name)}</div>`).join(''):'Sem escaneamento autorizado'}</td>
   <td><button class="mini-btn" data-station-add="${esc(s.id)}" ${s.interfaces.length?'':'disabled'}>＋ Associar impressora</button></td></tr>`).join(''):`<tr><td colspan="6">${empty('Nenhuma estação conectada','Inicie o agente Fluxo RIP em um dos PCs Windows e configure a Central.')}</td></tr>`}
   </tbody></table></div><div class="panel-bottom"><span>${esc(stationsState.message)}</span><span>Sem controle remoto das impressoras</span></div></div>
   <div class="note-block" style="margin-top:14px">O mapeamento é manual. A mesma faixa IP em estações ou portas diferentes pode ser normal. Uma resposta de ping/ARP não comprova modelo, funcionamento ou conexão ao PrintExp. A Central não envia comandos à Hoson.</div>`;
}
function stationLinkModal(stationId, printerId=''){
  const station=stationsState.items.find(s=>s.id===stationId);
  if(!station)return flash('Estação não encontrada. Atualize a lista.',true);
  const candidates=state.data.printers.filter(p=>!stationsState.links.some(l=>l.printer_id===p.id)||p.id===printerId);
  if(!candidates.length)return flash('Todas as impressoras já estão associadas. Clique em Alterar para trocar uma associação.',true);
  if(!station.interfaces.length)return flash('Esta estação ainda não informou interfaces de rede.',true);
  const current=stationsState.links.find(l=>l.printer_id===printerId);
  openDialog(`${modalHead('Associar impressora à porta de rede')}
     <form id="station-link-form"><div class="form-body">
     <div class="note-block">Isto cria apenas um vínculo administrativo no Fluxo RIP. Não modifica o IP nem envia comandos de impressão.</div>
     <label><span>Impressora cadastrada</span><select name="printer_id" required>${candidates.map(p=>`<option value="${esc(p.id)}" ${p.id===printerId?'selected':''}>${esc(p.name)} (${esc(p.ip||'IP não informado')})</option>`).join('')}</select></label>
     <label><span>Computador de impressão</span><input readonly value="${esc(station.name)}" /><input type="hidden" name="station_id" value="${esc(station.id)}"></label>
     <label><span>Porta Ethernet identificada pelo agente</span><select name="interface_id" required>${station.interfaces.map(i=>`<option value="${i.id}" ${current?.interface_id===i.id?'selected':''}>${esc(i.name)} — ${esc(i.ips.join(', ')||'sem IPv4')} ${i.hoson_subnet?'(rede Hoson)':''}</option>`).join('')}</select></label>
     <p class="dim">Se duas máquinas usam o mesmo IP, escolha portas distintas. O sistema bloqueará o mesmo IP cadastrado duas vezes na mesma porta.</p>
     </div>${formFooter('Salvar associação')}</form>`);
}
function stationEditLink(printerId){
 const link=stationsState.links.find(l=>l.printer_id===printerId);
 if(link)stationLinkModal(link.station_id,printerId);
}
async function stationRemoveLink(printerId){
 const link=stationsState.links.find(l=>l.printer_id===printerId);
 if(!link||!confirm(`Desvincular ${link.printer_name} desta estação? Não afetará a impressora física.`))return;
 try{await api(`/api/printer-links/${encodeURIComponent(printerId)}`,{method:'DELETE'});flash('Vínculo removido.');await stationsInit()}
 catch(e){flash(e.message,true)}
}
async function stationSaveLink(values){
 await api(`/api/printer-links/${encodeURIComponent(values.printer_id)}`,{
   method:'PUT',body:JSON.stringify({station_id:values.station_id,interface_id:Number(values.interface_id)})});
 flash('Impressora associada à estação e porta Ethernet.');await stationsInit();
}
