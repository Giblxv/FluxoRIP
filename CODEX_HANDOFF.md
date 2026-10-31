# CODEX_HANDOFF.md — Contexto do ChatGPT para continuidade no Codex

**Data de preparação:** 31/10/2026. **Projeto:** Fluxo RIP, antigo FORGE. **Estado-base:** código v1.5, identidade visual integrada e mapa Hoson por estação/porta Ethernet. Este documento resume a conversa de desenvolvimento e seus requisitos. **Não é uma transcrição literal integral do histórico**: para a transcrição completa, use a função da interface de desktop que permite acrescentar um chat existente do ChatGPT a um chat do Codex, quando disponível.

## 1. Objetivo do usuário
Criar um software comercial próprio, Windows 10/11, para controlar a **gestão de produção gráfica DTF e DTF UV**, centralizar pedidos/arte/filas/histórico e **integrar gradualmente** com o PrintExp e controladoras Hoson em várias estações. Inspiração funcional e estética do PrintExp, mas não cópia de código proprietário. O usuário deseja automação máxima, interface dinâmica, instalação por poucos cliques, um `FluxoRIP.exe` e um quadro de gestão estilo Trello/Notion.

## 2. Ambiente e limitações confirmadas
- Mais de cinco impressoras genéricas chinesas como Funsun, DTF e DTF UV, **todas Hoson**, Ethernet, software PrintExp. Versão exata do PrintExp e firmware/modelo da placa **não informados**; RIP prévio desconhecido.
- Computadores Windows 10 ou 11 x64; contexto inicial do desenvolvimento era Windows 11, RAM >= 32GB, Radeon RX 7600/RX 7600 XT (não assumir que cada estação tem essa GPU).
- Rede Hoson frequentemente `192.168.127.0/24`; IP de exemplo de PC `192.168.127.100`, máscara `255.255.255.0`, gateway vazio para cabo dedicado. Esses valores não devem ser aplicados automaticamente; alguns dispositivos podem compartilhar o mesmo IP de fábrica em interfaces físicas diferentes. Detectar interface individual e sub-rede real antes de scan.
- Não há protocolo Hoson ou API de controle PrintExp autenticada/validada nesta conversa; tudo que pareça comando no FORGE deve ficar claramente em modo **administrativo/observe_only**, com ação real desabilitada.
- Usuário relatou erros de dependências (`uvicorn`, `PyYAML`, `httpx2`) durante instalações anteriores. Instalação confiável e diagnósticos claros são prioritários.

## 3. Features e navegação desejadas
- **Projetos**: clientes, pedidos, prazos, prioridade, Kanban com movimentação, artes anexadas e revisões.
- **Fila de impressão**: trabalhos por impressora, status *administrativos*, prioridades, composição, duplicação, registros manuais.
- **Histórico**: eventos, alterações, logs, ações do operador, exportação CSV quando aplicável.
- **Impressões**: console inspirado no PrintExp (Trabalhos, Configurações, Calibração, Manutenção, Avançado, Logs); submenu **contextual**, não repetir duas barras com os mesmos nomes (bug da v0.9 corrigido em v0.9.1). Perfis passadas/DPI/velocidade/direção/feather/margens, registros de calibração, log; nada disso escreve na Hoson.
- **Editor de Arte**: upload PNG/JPEG, crop, escala, tamanho/DPI, remoção de fundo simples, versões não destrutivas; ferramentas opcionais VTracer (vetorizar SVG), rembg (IA remoção de fundo), Real-ESRGAN (upscale) sem promessa de detalhes genuinamente recuperados. **Sem ComfyUI**, removido por solicitação expressa.
- **Impressoras**: cadastro ilimitado de máquinas Hoson e distinção DTF/DTF UV, IP confirmado, tecnologia, dados por estação.
- **Scanner de rede**: inventariar adaptadores Windows, examinar IPs até /24 com ICMP/ARP, várias interfaces separadamente e opção de varrer as interfaces na faixa Hoson já configuradas; nunca classificar resposta genérica como impressora confirmada, nem mexer no TCP das máquinas.
- **Estações**: Central de pedidos via LAN, agente por estação Windows, identificação de NICs e associação futura com cada impressora, credenciais locais de acesso (não commitar segredos). Banco único na Central, e usar SQLite local somente no modo local.
- **Visual/motion**: linguagem de controle industrial moderna, abas superiores, pequenas microanimações e botão MOTION ON/OFF, acessibilidade/movimento reduzido, nova marca Fluxo RIP.

## 4. Identidade visual fornecida pelo usuário (arquivos originais incluídos)
- Marca: **Fluxo RIP**, grafia de logo `fluxo rip`; slogan na proposta: "Do arquivo PNG à impressão, sem fila e sem retrabalho." Evitar prometer ausência literal de filas ou RIP automático real.
- Gota com três camadas CMY sobrepostas e duas linhas raster brancas; símbolo sempre com base branca. Regras e SVG originais estão em `referencias_identidade/` e `web/assets/fluxo-rip-mark.svg`.
- Ciano `#00A6D6`, magenta `#E5007D`, amarelo `#FFD500`, preto `#14171A`, papel `#EEF1F2` e suporte a dark mode.
- Archivo ExtraBold para títulos; Public Sans para corpo, com fallback offline.
- Motion: intro gotas entrando/registrando e linhas do raster desenhadas (~1,7s); varredura/ripagem conceitual, hot folder, loading, status; **qualquer porcentagem deve usar progresso real**, nunca uma animação que simule progresso técnico como se fosse dado físico.

## 5. Arquitetura e implementação atual (v1.5)
Backend Python 3.12 FastAPI + SQLAlchemy/SQLite (`app/`); frontend HTML/CSS/JS (`web/`); monitoramento opcional Watchdog; executável unificado com PyInstaller e pywebview/WebView2 (fallback navegador); builds via `INSTALAR_E_ABRIR.bat` ou GitHub Actions. Arquivos de dados persistem em `%LOCALAPPDATA%\FORGE` por retrocompatibilidade. Ver `README.md`, `docs/INSTALACAO_ATUALIZACAO.md`, `docs/CENTRAL_E_ESTACOES.md`, `docs/COMPATIBILIDADE_WINDOWS_10_11.md` e `docs/ESTUDO_PRINTEXP_HOSON.md`.

**Estado comprovado aqui:** arquivos de código e instruções do projeto v1.5, copiados do último pacote entregue na conversa. Versões anteriores relatavam resultados de testes automatizados (até 31) e screenshots com dados simulados; **não considerar teste em hardware real ou build `.exe` Windows comprovados** sem reproduzir. O ZIP entregue historicamente contém **código-fonte para gerar EXE**, não `FluxoRIP.exe` compilado.

## 6. Histórico de erros encontrados e remediações
- `No module named uvicorn`: instalação de dependências no Python errado; instalar na `.venv` correta.
- `ERROR: Failed building wheel for pyyaml`: dependência opcional de `uvicorn[standard]`; instalar `uvicorn` simples ou dependências por arquivo adequado.
- `GET /docs%2A%2A... 404`: link com asteriscos escapados; URL correta `/docs`.
- Menu Impressões duplicado: barras Trabalhos/Configurações/Calibração/... e ícones equivalentes; v0.9.1 substituiu segunda barra por ações contextuais.
- `RuntimeError: starlette.testclient ... httpx2`: build v1.2 falhava por dependência de teste; `requirements-build.txt` passou a declarar `httpx2` na v1.2.1.
- ComfyUI não instalou na máquina do usuário; **módulo removido** na v0.6.

## 7. Segurança e integrações futuras
- Credenciais da área avançada PrintExp nunca devem ser inseridas em código, documentação do pacote ou logs. O acesso foi mencionado pelo usuário apenas para contextualizar conhecimento das configurações, não como requisito para persistir senha.
- Não conectar diretamente à controladora via portas presumidas. Verificar o PrintExp instalado e documentação oficial, depois iniciar com telemetria leitura/observação em única impressora fora de produção.
- Scanner apenas em interfaces/redes explicitamente autorizadas; não aplicar IPs automaticamente nem varrer redes amplas indiscriminadamente.
- Central com HTTP Basic sem TLS exige LAN isolada; para produção empresarial planejar HTTPS/VPN, usuários, auditoria, lock/transações e sincronização robusta.
- Evitar sobrescrita de arte original; versionamento, backup e garantia de integridade de pedidos.
- Nenhuma função de alteração perigosa de máquina (tensão, eixos, firmware, temperatura) deve estar ativa sem suporte de protocolo do fabricante e guardas operacionais.

## 8. Sequência de versões solicitadas
v0.1 API FastAPI + banco; v0.2 base Hoson em observação; v0.3 UI PrintExp + Kanban/fila; v0.4 editor com Pillow e adaptadores VTracer/rembg/Real-ESRGAN; v0.5 gerador ComfyUI; v0.6 remoção ComfyUI; v0.7 projeto PyInstaller EXE; v0.8 aba Impressões e perfis; v0.9 microanimações; v0.9.1 correção menu duplicado; v1.0 scanner Hoson 192.168.127.x; v1.1 Windows 10/11; v1.2 Central multiestações; v1.2.1 correção httpx2; v1.3 assistente de instalação; v1.4 rebranding Fluxo RIP e identidade visual.

## 9. Próximas tarefas sugeridas para o Codex (com prioridade)
1. **Clonar/abrir o projeto e inspecionar** o código para identificar bugs, testes reais, dependências, arquitetura de segurança, inconsistências no README (há referências históricas FORGE). Não presumir que testes passados continuem passando.
2. Rodar tests e verificar fluxo completo de build em ambiente Windows 10/11; checar compatibilidade com WebView2 e dependências opcionais. Remover dependências de build frágeis ou piná-las com justificativa.
3. Verificar instalador e assistente em Windows, garantindo um processo de poucos cliques, mensagens de erro acionáveis, migração com backup e sem exigir várias etapas técnicas do usuário.
4. Implementar mapa Central ↔ Estações ↔ interfaces Ethernet ↔ impressoras e identificação de conflitos de IP por interface física, sem varredura invasiva.
5. Melhorar gestão de acesso/HTTPS/VPN para Central e estabilidade da sincronização; preservar dados no upgrade.
6. Reavaliar UX para que todos os botões tenham ação correta, nenhum status de impressão seja indevidamente apresentado como real, e interface respeite a nova identidade.
7. Antes de integrar controle PrintExp, solicitar **versão/firmware modelo da placa e SDK/API** ou demonstrar tecnicamente um caminho seguro. Não inventar comandos.

## 10. Critérios de aceite das próximas entregas
- Um `FluxoRIP.exe` (Windows 10/11 x64) efetivamente compilado e com smoke test; se não testado no Windows 10, declarar.
- Importação dos dados existentes `%LOCALAPPDATA%\FORGE` sem perda; backup/rollback documentados.
- UI em português, identidade CMY, motion leve; abas e funcionalidades sem duplicação.
- Scanner/Estações associados corretamente, sem confundir IP igual em duas NICs.
- Testes unitários/integrados e relatório separado de testes físicos nas Hoson (ainda pendentes).
- Sem ComfyUI e sem controle físico não validado.

## 11. Fontes no repositório
- Documentos de identidade originais em `referencias_identidade/`.
- Revisão das funções PrintExp em `docs/ESTUDO_PRINTEXP_HOSON.md` (inclui links dos manuais consultados anteriormente).
- Documentação da Central, scanner e compatibilidade em `docs/`.
- README de instalação na raiz.


## 8. Novidade v1.5 — mapa de impressoras e estações
- Nova implementação: `app/printer_links.py`, `web/stations.js`, `docs/MAPA_ESTACOES_HOSON.md` e `tests/test_printer_links.py`.
- Rotas administrativas: `GET /api/printer-links`, `PUT /api/printer-links/{printer_id}` e `DELETE /api/printer-links/{printer_id}`.
- Relaciona impressora → estação Windows → interface Ethernet (identificador da NIC). Aceita endereços IP iguais em interfaces isoladas e bloqueia duplicidade de IP na mesma NIC.
- Diferenciar **status do agente** de **status físico da placa e do PrintExp**. Vínculo cadastrado não confirma conectividade da impressora.
- Central ainda depende de LAN confiável (HTTP Basic). Antes de produção real, auditar autenticação, persistência e topologia de rede, com backup de `%LOCALAPPDATA%\FORGE`.
- Documentação: `docs/MAPA_ESTACOES_HOSON.md`.

## 9. Prioridades para o Codex
1. Auditar e executar toda a suíte de testes, incluindo instalação real do `httpx2` no ambiente correto.
2. Reproduzir `FluxoRIP.exe` no Windows 10/11 x64, verificar ícones/arquivos empacotados e abertura WebView2/fallback navegador.
3. Validar Central/Agente em LAN isolada, autenticação, revogação de tokens, backup e recuperação de dados.
4. Melhorar scanner e o mapa de estações sem confundir ARP/ICMP com identificação comprovada de Hoson.
5. Só investigar controle supervisionado do PrintExp após obter versão, modelo de placa, documentação/protocolo e autorização operacional. Nunca transmitir comandos por adivinhação.

**Nota de privacidade:** detalhes de credenciais de manutenção podem ter aparecido no chat original. Não transcrevê-los, inseri-los no repo nem publicá-los.
