"""Teste visual opcional em Chromium. Usa base temporária, sem equipamentos físicos."""
import json, os, socket, subprocess, sys, tempfile, time
from pathlib import Path
from urllib import request
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1]
SHOT=Path('/mnt/data/Fluxo_RIP_v1.5_Mapa_Hoson_Preview.png')

def api(base, path, data, method='POST'):
    req=request.Request(base+path, data=json.dumps(data).encode(),
        method=method,headers={'Content-Type':'application/json'})
    with request.urlopen(req, timeout=5) as r:return json.loads(r.read())

with tempfile.TemporaryDirectory(prefix='fluxorip-ui-') as t:
    s=socket.socket();s.bind(('127.0.0.1',0));port=s.getsockname()[1];s.close()
    env=os.environ.copy();env['FORGE_DATA_DIR']=t;env['FORGE_CENTRAL_MODE']='0'
    proc=subprocess.Popen([sys.executable,'-m','uvicorn','app.main:app','--host','127.0.0.1','--port',str(port)],
                           cwd=ROOT,env=env,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE)
    base=f'http://127.0.0.1:{port}'
    try:
        for i in range(80):
            try:
                request.urlopen(base+'/api/health', timeout=2);break
            except Exception:time.sleep(.1)
        else:raise RuntimeError('Server not started '+proc.stderr.read().decode())
        for key,name,ip,technology in [
            ('dtf-01','DTF Funsun 60cm','192.168.127.10','DTF'),
            ('dtf-02','DTF 2 Hoson','192.168.127.10','DTF'),
            ('dtfuv-01','DTF UV 60cm','192.168.127.20','DTF_UV')]:
            api(base,'/api/printers',{'id':key,'name':name,'technology':technology,'ip':ip,'controller':'Hoson'})
        for sid,name,os_,iface in [('st-station0001','PC DTF PRINCIPAL','Windows 11',2),('st-station0002','PC DTF UV','Windows 10',9)]:
            api(base,'/api/stations/heartbeat',{'station_id':sid,'station_name':name,'hostname':name,
                'os_name':os_,'interfaces':[{'id':iface,'name':'Ethernet Hoson','status':'Up',
                  'ips':['192.168.127.100'],'hoson_subnet':True}], 'observations':[]})
        api(base,'/api/printer-links/dtf-01',{'station_id':'st-station0001','interface_id':2},'PUT')
        with sync_playwright() as p:
            browser=p.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox'])
            page=browser.new_page(viewport={'width':1536,'height':960},device_scale_factor=1)
            errors=[]
            page.on('pageerror',lambda exc:errors.append(str(exc)))
            page.goto(base+'/#stations',wait_until='domcontentloaded')
            page.wait_for_timeout(3000)
            assert page.locator('text=MAPA IMPRESSORAS').count() > 0
            assert page.locator('text=DTF Funsun 60cm').count()>0
            page.get_by_role('button',name='＋ Associar impressora').last.click()
            assert page.locator('#station-link-form').count()==1
            page.locator('#station-link-form select[name=printer_id]').select_option('dtfuv-01')
            page.locator('#station-link-form button[type=submit]').click()
            page.wait_for_timeout(650)
            assert page.locator('#dialog').evaluate('(el) => el.open') == False
            assert not errors, errors
            page.screenshot(path=str(SHOT),full_page=True)
            browser.close()
        print('UI SMOKE OK, screenshot:',SHOT)
    finally:
        proc.terminate()
        try:proc.wait(timeout=5)
        except subprocess.TimeoutExpired:proc.kill();proc.wait()
