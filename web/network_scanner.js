'use strict';
// Network discovery interface for Windows 10 and Windows 11: ICMP + Windows ARP cache only.
const scannerState = {
  adapters: [], chosen: '', network: '192.168.127.0/24',
  loading: false, scanning: false, error: '', report: null,
};
function scannerNetworkFor(adapter){
  if(!adapter) return '192.168.127.0/24';
  const ips = adapter.ips || [];
  const match = ips.find(p => /^192\.168\.127\./.test(p.ip));
  if(match) return '192.168.127.0/24';
  const first = ips.find(p => /^10\.|^192\.168\.|^172\./.test(p.ip));
  return first ? first.ip.split('.').slice(0,3).join('.') + '.0/24' : '192.168.127.0/24';
}
function scannerView(){
  const s=scannerState;
  const selected=s.adapters.find(p=>String(p.id)===String(s.chosen));
  const up=s.adapters.filter(p=>String(p.status).toLowerCase()==='up').length;
  const found=s.report?.devices?.length || 0;
  return `<div class="info-banner">◈ Scanner local de dispositivos em placas Ethernet. Faz verificações ICMP e consulta o cache ARP do Windows; não altera IPs nem envia comandos ao PrintExp.</div>
  <div class="metrics scanner-metrics">
    ${metric('Adaptadores detectados',s.adapters.length,'Placas de rede do Windows',true)}
    ${metric('Portas conectadas',up,'Status de link informado pelo Windows')}
    ${metric('Endereços examinados',s.report?.scanned||'—','Última busca na interface selecionada')}
    ${metric('Dispositivos encontrados',found,'Dispositivos de rede, não necessariamente impressoras')}
  </div>
  <section class="panel scanner-panel"><div class="panel-header"><strong>SCANNER DE REDE <small>/ HOSON • IPv4</small></strong><div class="controls"><button class="action sm soft" id="scanner-refresh-interfaces" ${s.loading||s.scanning?'disabled':''}>↻ Atualizar portas</button></div></div>
  <div class="scanner-settings">
    <div class="scanner-form-group"><label for="scanner-interface">Placa de rede / porta Ethernet</label><select class="select" id="scanner-interface" ${s.scanning?'disabled':''}>
      <option value="">Selecione uma placa de rede</option>${s.adapters.map(a=>`<option value="${a.id}" ${String(a.id)===String(s.chosen)?'selected':''}>${esc(a.name)} — ${esc(a.status)} — ${esc((a.ips||[]).map(p=>p.ip).join(', ')||'sem IPv4')}</option>`).join('')}
    </select></div>
    <div class="scanner-form-group"><label for="scanner-network">Faixa IPv4 a examinar (/24)</label><input id="scanner-network" class="input mono" value="${esc(s.network)}" placeholder="192.168.127.0/24" ${s.scanning?'disabled':''}/></div>
    <button id="scanner-scan" class="action primary" ${!selected||s.scanning||s.loading?'disabled':''}>${s.scanning?'⌛ Examinando IPs…':'⌕ Escanear porta selecionada'}</button>
    <button id="scanner-scan-all" class="action soft" ${!s.adapters.some(a=>a.is_hoson_subnet&&String(a.status).toLowerCase()==='up')||s.scanning||s.loading?'disabled':''}>▦ Escanear todas as portas Hoson</button>
  </div>
  ${s.scanning?'<div class="scanner-progress"><span class="scanner-progress-line"></span> Consultando os endereços da rede selecionada. Isso pode levar alguns segundos...</div>':''}
  ${s.loading?'<p class="scanner-note">Buscando adaptadores de rede do Windows...</p>':''}
  ${s.error?`<div class="info-banner warn">⚠ ${esc(s.error)}</div>`:''}
  ${selected?`<div class="scanner-interface-info">
    <strong>${esc(selected.name)}</strong>
    <span><b>Estado:</b> ${esc(selected.status)}</span>
    <span><b>Velocidade do link:</b> ${esc(selected.link_speed||'Desconhecida')}</span>
    <span><b>IPv4:</b> ${esc((selected.ips||[]).map(p=>p.ip+'/'+p.prefix).join(' • ')||'não configurado')}</span>
    <span><b>MAC local:</b> <code>${esc(selected.mac||'—')}</code></span>
    ${!selected.is_hoson_subnet?'<span class="scanner-caution">Esta porta não está configurada em 192.168.127.x. O scanner não altera seu IP.</span>':''}
  </div>`:''}
  </section>
  <section class="panel"><div class="panel-header"><strong>DISPOSITIVOS DETECTADOS <small>/ ${found}</small></strong><span class="dim">${s.report?`Busca em ${esc(s.report.network)} • ${esc(s.report.elapsed_s)} s`:'Aguardando escaneamento'}</span></div>
  ${!s.report?`<div class="scanner-empty">Escolha a placa Ethernet ligada à controladora Hoson e inicie a verificação.</div>`:
  `<div class="table-wrap"><table class="data-table"><thead><tr><th>Porta Ethernet</th><th>IP</th><th>Endereço MAC</th><th>Resposta</th><th>Tipo de dispositivo</th><th>Ações</th></tr></thead><tbody>${found?s.report.devices.map(d=>`<tr>
  <td>${esc(d.interface_name||s.report.interface?.name||"Porta selecionada")}</td>
  <td class="mono"><b>${esc(d.ip)}</b>${d.possible_hoson?'<div class="subline">IP frequente em algumas Hoson*</div>':''}</td>
  <td class="mono">${esc(d.mac||'—')}</td>
  <td><span class="state ${d.icmp?'complete':'waiting'}">${esc(d.icmp?'Respondeu ICMP':'Detectado via ARP')}</span></td>
  <td>${esc(d.device_type)}<div class="subline">Identificação Hoson não confirmada</div></td>
  <td><button class="mini-btn" data-scanner-register="${esc(d.ip)}">＋ Cadastrar manualmente</button></td>
  </tr>`).join(''):`<tr><td colspan="6">${empty('Nenhum dispositivo respondeu','Verifique o cabo, o IP da estação e o estado da placa. Algumas Hoson podem não responder ping.')}</td></tr>`}</tbody></table></div>
  <div class="panel-bottom"><span>${esc(s.report.warning)}</span><button class="mini-btn" id="scanner-export" ${found?'':'disabled'}>↓ Exportar CSV</button></div>`}
  </section>
  <div class="scanner-guide">
    <strong>Referência para redes Hoson</strong>
    <p>Um exemplo de configuração local é PC <code>192.168.127.100</code>, máscara <code>255.255.255.0</code>, gateway vazio em uma rede dedicada. Os endereços <code>192.168.127.10</code> e <code>192.168.127.1</code> são possibilidades, <b>não um padrão confirmado para todas as placas</b>. Primeiro confirme o IP utilizado pelo PrintExp na sua máquina.</p>
    <p>Para impressoras em outros computadores, execute o Fluxo RIP também na estação ligada a cada equipamento ou implemente posteriormente um agente local. Uma varredura de um PC não identifica, com garantia, todas as impressoras isoladas em outras portas.</p>
  </div>`;
}
async function scannerInit(force=false){
  if(scannerState.loading || scannerState.scanning || (scannerState.adapters.length&&!force))return;
  scannerState.loading=true;scannerState.error='';if(state.page==='scanner')render();
  try{
    const data=await api('/api/network/interfaces');
    scannerState.adapters=data.adapters||[];
    if(!scannerState.adapters.some(a=>String(a.id)===String(scannerState.chosen))){
      const preferred=scannerState.adapters.find(a=>a.is_hoson_subnet&&String(a.status).toLowerCase()==='up');
      scannerState.chosen=preferred?String(preferred.id):'';
      scannerState.network=scannerNetworkFor(preferred);
    }
  }catch(e){scannerState.error=e.message;}
  finally{scannerState.loading=false;if(state.page==='scanner')render();}
}
async function scannerScan(){
  if(scannerState.scanning||!scannerState.chosen)return;
  const net=document.querySelector('#scanner-network')?.value.trim()||scannerState.network;
  scannerState.network=net;scannerState.scanning=true;scannerState.error='';scannerState.report=null;render();
  try{
    scannerState.report=await api('/api/network/scan',{method:'POST',body:JSON.stringify({interface_index:Number(scannerState.chosen),network:net})});
    flash(`Busca concluída: ${scannerState.report.found} dispositivos encontrados.`);
  }catch(e){scannerState.error=e.message;flash(e.message,true);}
  finally{scannerState.scanning=false;if(state.page==='scanner')render();}
}
function scannerExport(){
  const devices=scannerState.report?.devices||[];
  if(!devices.length)return;
  const csv=['IP;MAC;ICMP;ARP;Identificacao',...devices.map(d=>[d.ip,d.mac||'',d.icmp?'Sim':'Não',d.arp_state||'','Não confirmada'].map(v=>'"'+String(v).replace(/"/g,'""')+'"').join(';'))].join('\r\n');
  const url=URL.createObjectURL(new Blob(['\ufeff'+csv],{type:'text/csv;charset=utf-8'}));
  const link=document.createElement('a');link.href=url;link.download='Fluxo RIP_scan_hoson_'+new Date().toISOString().slice(0,10)+'.csv';link.click();setTimeout(()=>URL.revokeObjectURL(url),2000);
}
function scannerRegister(ip){
  // Opens existing manual registration, no blind registration as confirmed Hoson.
  printerModal();const field=dialog.querySelector('input[name="ip"]');if(field)field.value=ip;
}

async function scannerScanAll(){
  if(scannerState.scanning)return;
  scannerState.scanning=true;scannerState.error='';scannerState.report=null;render();
  try{
    scannerState.report=await api('/api/network/scan-all',{method:'POST',body:'{}'});
    flash(`Busca em ${scannerState.report.interfaces_scanned} portas: ${scannerState.report.found} dispositivos observados.`);
  }catch(e){scannerState.error=e.message;flash(e.message,true)}
  finally{scannerState.scanning=false;if(state.page==='scanner')render()}
}
