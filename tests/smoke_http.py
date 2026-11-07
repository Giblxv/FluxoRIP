"""Teste real da API via HTTP loopback, sem TestClient e sem impressoras.
Executar no ambiente com as dependências de runtime:
    python tests/smoke_http.py
"""
import json, os, socket, subprocess, sys, tempfile, time
from urllib import request, error
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def send(base, path, payload=None, method='GET'):
    raw=json.dumps(payload).encode() if payload is not None else None
    headers={'Content-Type':'application/json'} if payload is not None else {}
    req=request.Request(base+path, data=raw, headers=headers, method=method)
    try:
        with request.urlopen(req,timeout=3) as response:
            return response.status,json.loads(response.read())
    except error.HTTPError as exc:
        return exc.code,json.loads(exc.read())

def main():
    with tempfile.TemporaryDirectory(prefix='fluxorip-api-') as data:
        with socket.socket() as s:
            s.bind(('127.0.0.1',0));port=s.getsockname()[1]
        env=os.environ.copy();env['FORGE_DATA_DIR']=data
        env['FORGE_CENTRAL_MODE']='0'
        proc=subprocess.Popen([sys.executable,'-m','uvicorn','app.main:app',
            '--host','127.0.0.1','--port',str(port)], cwd=ROOT, env=env,
            stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
        base=f'http://127.0.0.1:{port}'
        try:
            for _ in range(80):
                try:
                    status,response=send(base,'/api/health')
                    if status==200:break
                except Exception:pass
                if proc.poll() is not None:
                    raise RuntimeError(proc.stderr.read().decode(errors='replace'))
                time.sleep(.1)
            else:raise RuntimeError('Servidor não iniciou.')
            assert response['version']=='2.0.0',response
            for id,ip in [('dtf-a','192.168.127.10'),('dtf-b','192.168.127.10')]:
                st,_=send(base,'/api/printers',{'id':id,'name':id,'technology':'DTF','ip':ip,'controller':'Hoson'},'POST')
                assert st==201,st
            report={'station_id':'st-smoke0001','station_name':'PC Produção','hostname':'pc-01','os_name':'Windows 10',
                    'interfaces':[{'id':2,'name':'Ethernet 1','status':'Up','ips':['192.168.127.100'],'hoson_subnet':True},
                                  {'id':3,'name':'Ethernet 2','status':'Up','ips':['192.168.127.101'],'hoson_subnet':True}],
                    'observations':[]}
            assert send(base,'/api/stations/heartbeat',report,'POST')[0]==200
            assert send(base,'/api/printer-links/dtf-a',{'station_id':'st-smoke0001','interface_id':2},'PUT')[0]==200
            assert send(base,'/api/printer-links/dtf-b',{'station_id':'st-smoke0001','interface_id':2},'PUT')[0]==409
            assert send(base,'/api/printer-links/dtf-b',{'station_id':'st-smoke0001','interface_id':3},'PUT')[0]==200
            status,payload=send(base,'/api/printer-links')
            assert status==200 and len(payload['links'])==2, payload
            assert payload['mode']=='observe_only'
            assert send(base,'/api/printer-links/dtf-b',method='DELETE')[0]==200
            assert len(send(base,'/api/printer-links')[1]['links'])==1
            print('SMOKE HTTP OK: /api/health, heartbeat, vínculo, conflito de IP, exclusão')
        finally:
            proc.terminate()
            try:proc.wait(timeout=5)
            except subprocess.TimeoutExpired:proc.kill();proc.wait()

if __name__=='__main__':main()
