# AGENTS.md — Fluxo RIP (instruções para o Codex)

## Missão e contexto
Você está no repositório **Fluxo RIP**, antigo **FORGE**, sistema próprio de gestão de produção para uma gráfica com mais de cinco impressoras DTF e DTF UV genéricas (inclusive Funsun), todas com controladoras **Hoson** via Ethernet e uso de PrintExp no Windows. O projeto começou a partir de uma conversa longa com o usuário; consulte `CODEX_HANDOFF.md`, `HISTORICO_CONVERSA.md`, `docs/MAPA_ESTACOES_HOSON.md` e `docs/` antes de fazer mudanças importantes.

## Regras indispensáveis
- **Nunca confundir a fila administrativa do Fluxo RIP com a fila real do PrintExp.** Não afirmar impressão, RIP, limpeza, calibração ou status físico confirmado sem prova confiável. Os controles atuais são registros administrativos e observação de arquivos/rede.
- **Não enviar comandos para controladoras Hoson** (incluindo TCP/9100 ou portas similares), nem alterar IPs, parâmetros de cabeça, tensões, motores ou firmware com base em suposições. Protocolo/SDK não foram validados. Exigir documentação e testes supervisionados antes de qualquer integração ativa.
- Não armazenar nem expor senhas de manutenção, chaves, tokens ou dados de clientes nos commits, logs e prompts. Credenciais locais são geradas em tempo de execução.
- Manter compatibilidade com **Windows 10 22H2 x64 e Windows 11 x64**; build Python 3.12 com PyInstaller, WebView2 quando disponível e fallback para navegador. Um build feito no Windows 11 não comprova compatibilidade no Windows 10.
- Banco/arquivos persistentes estão em `%LOCALAPPDATA%\FORGE` por compatibilidade com versões antigas, apesar do nome visível ser Fluxo RIP. Criar migração com backup se algum dia renomear a pasta de dados.
- Preservar a identidade visual **Fluxo RIP** fornecida pelo usuário: gota CMY, ciano `#00A6D6`, magenta `#E5007D`, amarelo `#FFD500`, preto `#14171A`, fundo `#EEF1F2`, fontes Archivo/Public Sans e motion com respeito a `prefers-reduced-motion`.
- **ComfyUI foi removido a pedido do usuário; não reintroduzir.** Ferramentas opcionais VTracer, rembg e Real-ESRGAN só funcionam com requisitos externos compatíveis.
- Não copiar código proprietário do PrintExp; usar interface própria inspirada no fluxo operacional, sujeito à documentação real do dispositivo.
- No scanner, só varrer interfaces/redes explicitamente escolhidas pelo operador, máximo /24, com ICMP/ARP e sem alterar configurações; resposta de IP não confirma uma Hoson.
- Na Central multiestações, não expor HTTP Basic sem TLS na internet. Testar autorização e restringir modo LAN a rede isolada e confiável; planejar HTTPS/VPN.
- Editar com testes incrementais, preservar banco e artes, criar backup antes de migrações, e informar claramente o que foi testado localmente versus testes em máquinas reais.

## Stack e pontos de entrada
- Backend FastAPI/SQLAlchemy/SQLite: `app/` e `app/main.py`
- UI HTML/CSS/JS: `web/`; identidade em `web/brand-fluxorip.css`, `web/brand-fluxorip.js`
- Impressões: `app/print_console.py`, `web/prints.js`
- Scanner: `app/network_scanner.py`, `web/network_scanner.js`
- Multiestações: `app/station_agent.py`, `app/stations.py`, `app/central_auth.py`
- Vínculo impressora → estação/porta Ethernet: `app/printer_links.py` e `docs/MAPA_ESTACOES_HOSON.md`
- Editor: `app/art_editor.py`, `web/art_editor.js`
- Executável: `forge_launcher.py`, `FORGE.spec`, `INSTALAR_E_ABRIR.bat`, `GERAR_EXECUTAVEL.bat`, `.github/workflows/build-windows.yml`
- Testes: `tests/` via `python -m unittest discover -s tests -v`

## Primeiro passo recomendado
1. Faça `git status`/inspeção do projeto e teste num ambiente isolado (não modifique dados reais).
2. Leia `CODEX_HANDOFF.md` e `HISTORICO_CONVERSA.md`.
3. Valide requisitos no Windows, testes Python, inicialização da API e empacotamento `FluxoRIP.exe` com o workflow.
4. Faça relatório de bloqueios, problemas críticos de segurança e prioridades antes de integração com equipamentos reais.

## Regras adicionais v1.5
- O cadastro `printer_station_links` representa uma relação administrativa confirmada pelo operador, **não um enlace de controle real**.
- Permitir IPs iguais apenas em interfaces/estações isoladas; barrar IP duplicado na mesma NIC, sem alterar a configuração do Windows.
- Antes de editar fluxo de dados do mapa, revisar `tests/test_printer_links.py` e aplicar migração segura/backup.
