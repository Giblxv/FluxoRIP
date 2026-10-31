"""Validação visual com respostas simuladas, sem rede nem impressoras."""
import json,re,base64
from pathlib import Path
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1]/'web'
html=(ROOT/'index.html').read_text(encoding='utf-8')
logo=base64.b64encode((ROOT/'assets/fluxo-rip-mark.svg').read_bytes()).decode('ascii')
html=html.replace('/static/assets/fluxo-rip-mark.svg',f'data:image/svg+xml;base64,{logo}')
css='\n'.join((ROOT/x).read_text(encoding='utf-8') for x in ['styles.css','motion.css','network_scanner.css','brand-fluxorip.css'])
html=re.sub(r'<link rel="stylesheet"[^>]*>', '',html)
html=re.sub(r'<link rel="preconnect"[^>]*>', '',html)
html=re.sub(r'<script src="[^"]+" defer></script>', '',html)
js='\n'.join((ROOT/x).read_text(encoding='utf-8') for x in ['motion.js','app.js','network_scanner.js','stations.js','art_editor.js','prints.js','brand-fluxorip.js'])
responses={
 '/api/orders':[], '/api/jobs':[], '/api/files?limit=300':[], '/api/events?limit=300':[],
 '/api/stats':{}, '/api/health':{'status':'ok'},
 '/api/printers':[
  {'id':'dtf-01','name':'DTF Funsun 60cm','technology':'DTF','ip':'192.168.127.10','workstation':'PC DTF 1'},
  {'id':'dtf-02','name':'DTF 2 Hoson','technology':'DTF','ip':'192.168.127.10','workstation':'PC DTF 2'},
  {'id':'dtfuv-01','name':'DTF UV 60cm','technology':'DTF_UV','ip':'192.168.127.20','workstation':'PC DTF UV'}],
 '/api/stations':{'stations':[
  {'id':'st-station0001','name':'PC DTF PRINCIPAL','hostname':'WIN11-DTF01','os_name':'Windows 11',
   'online':True,'last_seen':'2026-10-31T02:30:00','interfaces':[
     {'id':2,'name':'Ethernet Hoson','status':'Up','ips':['192.168.127.100'],'hoson_subnet':True},
     {'id':3,'name':'Ethernet Hoson 2','status':'Up','ips':['192.168.127.101'],'hoson_subnet':True}],
   'observations':[]},
  {'id':'st-station0002','name':'PC DTF UV','hostname':'WIN10-DTFUV','os_name':'Windows 10',
   'online':True,'last_seen':'2026-10-31T02:30:00','interfaces':[
     {'id':9,'name':'Ethernet 2','status':'Up','ips':['192.168.127.100'],'hoson_subnet':True}],
   'observations':[]}],'note':'Modo passivo; descoberta local somente com autorização.'},
 '/api/printer-links':{'links':[
  {'printer_id':'dtf-01','printer_name':'DTF Funsun 60cm','printer_ip':'192.168.127.10',
   'technology':'DTF','station_id':'st-station0001','station_name':'PC DTF PRINCIPAL',
   'station_online':True,'interface_id':2,'interface_name':'Ethernet Hoson','interface_status':'Up',
   'interface_ips':['192.168.127.100'],'observed_ip_on_interface':False,'observed_mac':None,
   'status':'VINCULO_CADASTRADO','linked_at':'2026-10-31T02:30:00','note':'Vínculo manual'}],
  'unassigned':[{'id':'dtf-02','name':'DTF 2 Hoson','ip':'192.168.127.10','technology':'DTF'},
                {'id':'dtfuv-01','name':'DTF UV 60cm','ip':'192.168.127.20','technology':'DTF_UV'}],
  'mode':'observe_only'}
}
mock='''
window.__mockData=MOCK;
window.fetch=async function(path, opts={}) {
 const url=String(path),method=(opts.method||'GET').toUpperCase();
 if(method==='PUT' && url.startsWith('/api/printer-links/')) {
   const payload=JSON.parse(opts.body),id=decodeURIComponent(url.split('/').pop());
   const printer=window.__mockData['/api/printers'].find(p=>p.id===id);
   const station=window.__mockData['/api/stations'].stations.find(s=>s.id===payload.station_id);
   const iface=station.interfaces.find(i=>i.id===payload.interface_id);
   const link={printer_id:id,printer_name:printer.name,printer_ip:printer.ip,technology:printer.technology,
     station_id:station.id,station_name:station.name,station_online:true,interface_id:iface.id,
     interface_name:iface.name,interface_ips:iface.ips,status:'VINCULO_CADASTRADO',
     observed_ip_on_interface:false};
   window.__mockData['/api/printer-links'].links.push(link);
   window.__mockData['/api/printer-links'].unassigned=window.__mockData['/api/printer-links'].unassigned.filter(p=>p.id!==id);
   return {ok:true,status:200,json:async()=>link};
 }
 const data=window.__mockData[url]??[];
 return {ok:true,status:200,json:async()=>data};
};
'''.replace('MOCK',json.dumps(responses,ensure_ascii=False))
html=html.replace('</head>',f'<style>{css}</style></head>')
html=html.replace('</body>',f'<script>{mock}</script><script>{js}</script></body>')
with sync_playwright() as p:
    browser=p.chromium.launch(headless=True,executable_path='/usr/bin/chromium',args=['--no-sandbox'])
    page=browser.new_page(viewport={'width':1650,'height':1000},device_scale_factor=1)
    errors=[];page.on('pageerror',lambda exc:errors.append(str(exc)))
    page.set_content(html,wait_until='load')
    page.evaluate("state.page='stations';stationsInit()")
    page.wait_for_timeout(1400)
    assert page.locator('text=MAPA IMPRESSORAS').count()>0
    assert page.get_by_text('DTF Funsun 60cm').count()>0
    page.get_by_role('button',name='＋ Associar impressora').last.click()
    assert page.locator('#station-link-form').count()==1
    page.locator('#station-link-form select[name=printer_id]').select_option('dtfuv-01')
    page.locator('#station-link-form button[type=submit]').click()
    page.wait_for_timeout(650)
    assert page.locator('#dialog').evaluate('(d) => d.open')==False
    assert page.locator('text=DTF UV 60cm').count()>0
    assert not errors,errors
    shot=Path('/mnt/data/Fluxo_RIP_v1.5_Preview_Mapa_Hoson.png')
    page.screenshot(path=str(shot),full_page=True)
    print('UI OFFLINE OK',str(shot),'browser errors',errors)
    browser.close()
