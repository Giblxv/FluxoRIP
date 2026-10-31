"""Fluxo RIP standalone desktop launcher. One executable, persistent user data.

Start a FastAPI server on a random loopback port in a background thread and
show it in a native Edge WebView2 window. NO connection to Hoson is attempted.
"""
import argparse
import logging
from logging.handlers import RotatingFileHandler
import os
from pathlib import Path
import shutil
import socket
import sys
import threading
import time

from app.paths import DATA_ROOT, BUNDLE_ROOT
from app.windows_compat import windows_details, webview2_runtime, compatibility_report
from app.central_auth import create_credentials, get_credentials
from app.startup_profile import load_profile

LOG_PATH = DATA_ROOT / 'forge.log'


def setup_logging():
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    if not any(isinstance(handler, RotatingFileHandler) for handler in root_logger.handlers):
        handler = RotatingFileHandler(LOG_PATH, maxBytes=1_500_000, backupCount=3, encoding='utf-8')
        handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s %(name)s %(message)s'))
        root_logger.addHandler(handler)
    # --windowed Python executables can have sys.stdout/sys.stderr set to None.
    if sys.stdout is None:
        sys.stdout = open(os.devnull, 'w', encoding='utf-8')
    if sys.stderr is None:
        sys.stderr = open(os.devnull, 'w', encoding='utf-8')


def inform(title: str, message: str, *, error=False):
    if os.environ.get('FORGE_NO_DIALOG') == '1':
        logging.info('%s: %s', title, message)
        return
    if sys.platform == 'win32':
        import ctypes
        ctypes.windll.user32.MessageBoxW(None, message, title, 0x10 if error else 0x40)
    else:
        print(f'{title}: {message}', file=sys.stderr if error else sys.stdout)


def migrate_if_needed(candidate: Path) -> bool:
    """Copy, never remove, legacy database and art storage on first desktop run."""
    source = candidate.resolve()
    if source == DATA_ROOT.resolve():
        return False
    db = source / 'production.db'
    target = DATA_ROOT / 'production.db'
    if not db.is_file() or target.exists():
        return False
    art = source / 'art_storage'
    try:
        if art.is_dir():
            shutil.copytree(art, DATA_ROOT / 'art_storage', dirs_exist_ok=True)
        temp = DATA_ROOT / 'production.db.migrando'
        shutil.copy2(db, temp)
        temp.replace(target)
        logging.info('Base e artes copiadas de %s; originais preservados.', source)
        return True
    except Exception:
        logging.exception('Falha na migração; dados anteriores não foram alterados.')
        raise


def configure_external_editors():
    path_file = DATA_ROOT / 'realesrgan_path.txt'
    if path_file.is_file() and not os.environ.get('FORGE_REALESRGAN_EXE'):
        exe = path_file.read_text(encoding='utf-8-sig').strip().strip('"')
        if exe and Path(exe).is_file():
            os.environ['FORGE_REALESRGAN_EXE'] = exe


def serve(host='127.0.0.1', requested_port=0) -> tuple[object, threading.Thread, int]:
    import uvicorn
    from app.main import app
    listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    listener.bind((host, requested_port))
    listener.listen(128)
    port = listener.getsockname()[1]
    config = uvicorn.Config(app, host=host, port=port, log_config=None,
                            access_log=False, lifespan='on', timeout_keep_alive=10)
    server = uvicorn.Server(config)
    errors = []

    def background():
        try:
            server.run(sockets=[listener])
        except BaseException as exc:
            errors.append(exc)
            logging.exception('Falha ao iniciar o servidor local.')
        finally:
            listener.close()

    thread = threading.Thread(target=background, name='forge-api', daemon=True)
    thread.start()
    deadline = time.monotonic() + 25
    while time.monotonic() < deadline:
        if server.started:
            return server, thread, port
        if errors or not thread.is_alive():
            break
        time.sleep(0.12)
    server.should_exit = True
    thread.join(timeout=3)
    raise RuntimeError(f'Falha ao iniciar o servidor. Consulte {LOG_PATH}.')



def show_in_browser(url: str, reason: str = ''):
    """Works even without a WebView2 runtime. Keep API alive until dialog closes."""
    import webbrowser
    logging.warning('Iniciando interface no navegador: %s', reason or 'solicitado pelo usuário')
    opened = webbrowser.open(url)
    if not opened:
        inform('Fluxo RIP - Navegador', 'Abra manualmente no navegador: ' + url + '\n'
               'O servidor será encerrado ao fechar esta mensagem.')
    else:
        inform('Fluxo RIP - Navegador', 'Fluxo RIP foi aberto no navegador.\n'
               'Mantenha esta janela aberta durante o uso.\n'
               'Feche esta mensagem para encerrar o aplicativo.')


def open_desktop(url: str):
    """Prefer modern WebView2; safely fall back to browser on Win10/Win11."""
    current = webview2_runtime()
    if current['detected'] is False:
        show_in_browser(url, 'WebView2 não localizado no registro do Windows')
        return
    try:
        import webview
        webview.create_window('Fluxo RIP • Central de Produção', url,
                              width=1450, height=900,
                              min_size=(940, 600), resizable=True)
        webview.start(gui='edgechromium')
    except Exception:
        logging.exception('Falha no WebView2; ativando interface no navegador.')
        show_in_browser(url, 'Falha ao iniciar WebView2')


def open_first_run_wizard():
    """Launch Windows Forms setup UI bundled inside the single-file executable."""
    import subprocess
    if sys.platform != 'win32':
        raise RuntimeError('O assistente visual é destinado ao Windows 10/11.')
    if not getattr(sys, 'frozen', False):
        raise RuntimeError('Primeiro gere FluxoRIP.exe; o assistente é incluído no executável.')
    script = BUNDLE_ROOT / 'setup' / 'ASSISTENTE_FORGE.ps1'
    if not script.is_file():
        raise FileNotFoundError('O assistente não foi incluído no pacote executável.')
    logging.info('Abrindo assistente de configuração do Fluxo RIP')
    proc = subprocess.run(['powershell.exe', '-NoProfile', '-Sta',
                           '-ExecutionPolicy', 'Bypass', '-File', str(script),
                           '-ForgeExe', str(Path(sys.executable).resolve())],
                          timeout=None)
    if proc.returncode != 0:
        raise RuntimeError('O assistente foi encerrado com erro. Consulte forge.log.')


def main():
    parser = argparse.ArgumentParser(description='Fluxo RIP - Central de Produção')
    parser.add_argument('--assistente', action='store_true', help='Abre configuração simplificada')
    parser.add_argument('--verificar', action='store_true', help='Valida os recursos e o banco local')
    parser.add_argument('--autoteste', action='store_true', help='Inicia API, valida HTTP e sai sem interface')
    parser.add_argument('--migrar', metavar='PASTA_ANTIGA', help='Importa cópia da base v0.6 se ainda não existir')
    parser.add_argument('--navegador', action='store_true', help='Abre em navegador ao invés de janela própria')
    parser.add_argument('--diagnostico', action='store_true', help='Salva diagnóstico Windows 10/11 sem alterar a rede')
    parser.add_argument('--configurar-central', action='store_true', help='Cria senha forte e chave unica de agente')
    parser.add_argument('--redefinir-central', action='store_true', help='Troca senha e revoga chaves de agentes')
    parser.add_argument('--chave-agente', action='store_true', help='Mostra chave de pareamento no computador central')
    parser.add_argument('--central', action='store_true', help='Habilita acesso protegido pela rede local')
    parser.add_argument('--host', default=None, help='IP privado da estacao central, nao usar IP da impressora')
    parser.add_argument('--port', type=int, default=8765, help='Porta TCP da central (padrao 8765)')
    parser.add_argument('--agente', action='store_true', help='Relata interfaces desta estacao a central')
    parser.add_argument('--testar-agente', action='store_true', help='Envia um heartbeat e encerra')
    args = parser.parse_args()
    setup_logging()
    logging.info('Fluxo RIP inicializando; raiz de dados: %s', DATA_ROOT)
    logging.info('SO identificado: %s', windows_details())
    try:
        if args.assistente:
            open_first_run_wizard()
            return
        # Executável por dois cliques: na primeira vez configura, depois
        # inicia o papel já escolhido (local, central ou agente da estação).
        user_chose_explicit_mode = any([
            args.verificar, args.autoteste, args.migrar, args.navegador,
            args.diagnostico, args.configurar_central, args.redefinir_central,
            args.chave_agente, args.central, args.agente, args.testar_agente,
        ])
        if not user_chose_explicit_mode and getattr(sys, 'frozen', False) and sys.platform == 'win32':
            stored = load_profile()
            if stored is None:
                open_first_run_wizard()
                return
            if stored['modo'] == 'central':
                args.central = True
                args.host = stored['ip']
                args.port = stored['porta']
            elif stored['modo'] == 'estacao':
                args.agente = True
        if args.configurar_central or args.redefinir_central:
            password=create_credentials(force=args.redefinir_central)
            inform('Fluxo RIP - Credenciais iniciais',
                   'Usuario: forge\nSenha criada (copie e guarde agora):\n'+password+'\n\n'
                   'Pressione Ctrl+C nesta caixa para copiar a mensagem inteira.\n'
                   'Essa senha nao sera exibida outra vez. Redefinir tambem invalida chaves de agentes.')
            return
        if args.chave_agente:
            inform('Fluxo RIP - Chave de agente',
                   'Use SOMENTE em estacoes confiaveis. Nao publique essa chave:\n\n'
                   + get_credentials()['agent_token'])
            return
        if args.agente or args.testar_agente:
            from app.station_agent import run_agent, run_agent_once
            if args.testar_agente:
                run_agent_once()
                inform('Fluxo RIP - Agente','A Central recebeu o teste de conectividade desta estacao.')
            else:
                run_agent()
            return
        if args.central:
            import ipaddress
            if not args.host:
                raise ValueError('Informe --host com o IPv4 PRIVADO desta estacao central. Ex.: 192.168.1.100')
            addr=ipaddress.ip_address(args.host)
            if addr.version != 4 or not (addr.is_private or addr.is_loopback):
                raise ValueError('O --host deve ser um endereco IPv4 privado da central.')
            if not 1024 <= args.port <= 65535:
                raise ValueError('Porta deve estar entre 1024 e 65535')
            if addr in ipaddress.ip_network('192.168.127.0/24'):
                raise ValueError('Escolha o IP da rede administrativa, nao a rede isolada 192.168.127.x das Hoson.')
            get_credentials()  # rejects unconfigured mode before any LAN listener
            os.environ['FORGE_CENTRAL_MODE']='1'
        if args.diagnostico:
            import json
            output = DATA_ROOT / 'diagnostico_windows.json'
            output.write_text(json.dumps(compatibility_report(), indent=2, ensure_ascii=False), encoding='utf-8')
            inform('Fluxo RIP - Diagnóstico', 'Diagnóstico salvo em:\n' + str(output))
            return
        # If FluxoRIP.exe is placed inside old FORGE folder, import from there.
        if args.migrar:
            migrated = migrate_if_needed(Path(args.migrar))
            inform('Fluxo RIP - Migração', 'Dados importados com sucesso.' if migrated else
                   'Nenhum banco importado. Confira a pasta; o destino pode já conter dados.')
            if not args.verificar:
                return
        elif getattr(sys, 'frozen', False):
            migrate_if_needed(Path(sys.executable).resolve().parent)
        configure_external_editors()
        if args.verificar:
            from app.db import init_db, DB_PATH
            init_db()
            if not (BUNDLE_ROOT / 'web' / 'index.html').is_file():
                raise RuntimeError('Arquivos da interface não encontrados no pacote.')
            if getattr(sys, 'frozen', False) and not (BUNDLE_ROOT / 'setup' / 'ASSISTENTE_FORGE.ps1').is_file():
                raise RuntimeError('Assistente de configuração não foi incluído no EXE.')
            inform('Fluxo RIP', f'Instalação verificada.\nBanco: {DB_PATH}')
            return
        server, thread, port = serve(args.host if args.central else '127.0.0.1', args.port if args.central else 0)
        try:
            if args.autoteste:
                import json
                import urllib.request
                with urllib.request.urlopen(f'http://127.0.0.1:{port}/api/health', timeout=10) as reply:
                    data = json.loads(reply.read())
                    assert data['status'] == 'ok', data
                with urllib.request.urlopen(f'http://127.0.0.1:{port}/', timeout=10) as reply:
                    assert 'Fluxo RIP' in reply.read(20000).decode('utf-8')
                with urllib.request.urlopen(f'http://127.0.0.1:{port}/api/art/capabilities', timeout=10) as reply:
                    assert json.loads(reply.read())['basic'] is True
                logging.info('Autoteste concluido: API, editor e interface OK')
                return
            display_host = args.host if args.central else '127.0.0.1'
            url = f'http://{display_host}:{port}/'
            if args.central:
                show_in_browser(url, 'Central LAN: acesso por usuario/senha; mantenha esta janela aberta')
            elif args.navegador:
                show_in_browser(url, 'modo navegador solicitado')
            else:
                open_desktop(url)
        finally:
            server.should_exit = True
            thread.join(timeout=12)
    except Exception as exc:
        logging.exception('Erro ao iniciar Fluxo RIP.')
        inform('Fluxo RIP - Erro', f'{exc}\n\nConsulte o log: {LOG_PATH}', error=True)
        sys.exit(1)


if __name__ == '__main__':
    main()
