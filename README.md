# Fluxo RIP v1.4 — Identidade visual integrada

**Novo nome do aplicativo: Fluxo RIP.** O software anterior FORGE agora utiliza a identidade visual e motion fornecidos em `Fluxo RIP – Identidade visual.html` e `Fluxo RIP – Motion graphics.html`.

## Instalação rápida

1. No Windows 10/11 x64, extraia este ZIP.
2. Com Python 3.12 x64 instalado e acesso à internet na primeira compilação, dê dois cliques em `INSTALAR_E_ABRIR.bat`.
3. O processo gera `dist\FluxoRIP.exe` e o abre.
4. Na primeira execução, selecione **Uso local**, **Computador Central** ou **Estação da impressora**.
5. Nas próximas execuções, inicie com `dist\FluxoRIP.exe`.

**Dados antigos:** mantivemos `%LOCALAPPDATA%\FORGE` de propósito para preservar pedidos, artes, banco e credenciais; o nome visível e o arquivo `.exe` são Fluxo RIP. Faça backup da pasta antes de atualizar.

**Identidade:** gota CMY com base branca, cores #00A6D6 / #E5007D / #FFD500, títulos Archivo ExtraBold, interface Public Sans, motion de abertura e microanimações; fontes externas são carregadas quando houver internet, com alternativas locais em modo offline.

**Segurança:** scanner somente observação, sem comandos de impressão ou alterações físicas nas controladoras Hoson.

**Recursos preservados:** Projetos, Editor de Arte, Impressões, Fila de impressão, Histórico, Impressoras, Estações, Scanner de rede e Arquivos.

**Nota:** este pacote contém o projeto Python e o compilador, **não** um executável Windows já compilado.

---

## Histórico e detalhes do projeto anterior

# FORGE v1.3 — Instalação simplificada com assistente visual

**Agora é um processo guiado.** Na primeira execução o FORGE mostra uma janela com três opções: **Uso local**, **Computador Central** e **Estação da impressora**. Não é necessário editar JSON nem executar comandos PowerShell para configurar Central ou agente.

## Instalar pela primeira vez (Windows 10/11 x64)

1. Extraia o ZIP completo em uma pasta, por exemplo `C:\FORGE`.
2. Dê dois cliques em **`INSTALAR_E_ABRIR.bat`**. É necessário Python 3.12 x64 e internet **apenas no computador que compila**. O instalador cria `.venv-build`, baixa dependências, executa os testes e gera `dist\FluxoRIP.exe` automaticamente.
3. No assistente, escolha o uso:
   - **Uso local:** clique em *Abrir FORGE*; não exige outras informações.
   - **Central:** escolha o IP da rede administrativa na lista, clique em *Criar senha* e em *Iniciar Central*; o assistente informa o endereço compartilhado.
   - **Estação:** informe IP e porta da Central, nome da estação e cole a chave exibida na Central; o assistente verifica a ligação antes de iniciar o agente.
4. Nas próximas vezes abra apenas **`dist\FluxoRIP.exe`**. O papel configurado fica salvo. Para mudar, use `ALTERAR_CONFIGURACAO.bat` (ou `FluxoRIP.exe --assistente`).

**Distribuição:** depois de compilar uma vez, é possível copiar somente `dist\FluxoRIP.exe` para outras máquinas Windows 10/11 x64: elas não precisam de Python, mas podem necessitar do WebView2 Runtime (o navegador é alternativa). Cada máquina abre seu próprio assistente na primeira execução.

**Sem compilação no PC:** a pasta `.github/workflows` permite compilar em Windows pelo GitHub Actions e baixar o executável gerado. Isso exige configurar o projeto num repositório GitHub.

**Segurança:** o assistente não modifica IPs, firewall ou controladoras Hoson; a descoberta por ICMP/ARP só acontece quando autorizada. A Central usa HTTP Basic sem TLS: somente LAN privada e isolada, nunca internet ou rede compartilhada sem HTTPS/VPN. A senha e a chave são geradas pelo próprio FORGE; o arquivo de função salvo não guarda esses segredos.

**Dados:** banco, artes e configurações permanecem em `%LOCALAPPDATA%\FORGE` (copie para backup antes de atualizar). A versão 1.3 não envia comandos de impressão, limpeza ou calibração ao PrintExp/Hoson.

---

# FORGE v1.2.1 — Correção do ambiente de compilação Windows 10/11

Sistema de gestão de produção DTF/DTF UV com projetos, Kanban, fila de impressão, histórico, Editor de Arte, Console Impressões inspirado no PrintExp e scanner local de dispositivos Hoson.

**Atenção:** esta entrega é o **código-fonte completo pronto para compilar**, não um `.exe` já compilado. O controle Hoson permanece **passivo e administrativo**: sem comando de impressão, firmware, limpeza ou calibração enviado à máquina.

## Correção v1.2.1: dependência ausente nos testes

Se aparecer `RuntimeError: The starlette.testclient module requires the httpx2 package to be installed`, a biblioteca de testes está faltando no ambiente `.venv-build`. Esta revisão inclui `httpx2>=2.13,<3` em `requirements-build.txt`, então `GERAR_EXECUTAVEL.bat` a instala automaticamente.

Para consertar uma instalação v1.2 já extraída (sem baixar outra versão), execute no PowerShell na pasta antiga:

```powershell
.\.venv-build\Scripts\python.exe -m pip install "httpx2>=2.13,<3"
.\.venv-build\Scripts\python.exe -m unittest discover -s tests -v
```

A correção afeta apenas a etapa de testes/compilação e não modifica banco de dados, artes, configurações de impressoras ou comunicação com a controladora Hoson.

## Atualização v1.2

- **Novo modo Central** para vários PCs da mesma rede administrativa acessarem o mesmo banco de pedidos e filas, com senha forte e login via navegador.
- **Nova aba Estações** com monitoramento passivo das interfaces de rede de cada PC.
- **Novo agente opcional**, sem controle de máquinas, com descoberta de IPs Hoson somente mediante autorização local.
- **Atenção à segurança:** acesso LAN via HTTP Basic é para redes isoladas; habilite HTTPS/VPN antes de uso em rede compartilhada.
- Guia detalhado em [`docs/CENTRAL_E_ESTACOES.md`](docs/CENTRAL_E_ESTACOES.md).
- Suporte direcionado a **Windows 10 22H2 x64** e **Windows 11 x64** com o mesmo código e a mesma interface.
- Nova detecção da versão do Windows para diagnóstico.
- Janela nativa via WebView2, com fallback automático para navegador quando indisponível.
- Scanner de rede adaptado para a nomenclatura e ferramentas do Windows 10/11.
- Ferramenta `--diagnostico` para verificar SO, componentes de rede do PowerShell e WebView2 sem executar scans.
- Compilador `.bat` verifica Python 3.12 x64, roda testes e gera um único `FluxoRIP.exe` com PyInstaller.
- Workflow GitHub Actions para compilar automaticamente em um ambiente Windows. **Não equivale a teste real em Windows 10.**

## Como gerar `FluxoRIP.exe`

1. Faça backup de `%LOCALAPPDATA%\FORGE` antes de atualizar.
2. Extraia o ZIP numa pasta nova (por exemplo, `C:\FORGE`).
3. Instale **Python 3.12 x64** em um PC de compilação com Windows 10 ou 11. Marque a instalação do `py launcher`.
4. Execute `GERAR_EXECUTAVEL.bat` (requer internet para instalar bibliotecas na etapa de build).
5. Após os testes e compilação, encontre `dist\FluxoRIP.exe`.
6. Copie apenas o `.exe` para os computadores Windows 10/11 de 64 bits. Não é necessário instalar Python nas estações de uso.

**Recomendação:** para maximizar compatibilidade com Windows 10, compile a distribuição em um Windows 10 22H2 x64, quando disponível, e valide em uma máquina Windows 11 x64. Um build feito somente no Windows 11/GitHub Actions **não garante** compatibilidade universal no Windows 10.

## Abrir e diagnosticar

- `FluxoRIP.exe`: abre janela própria se o WebView2 Runtime estiver disponível. Caso contrário, tenta abrir no navegador padrão e mantém o servidor local ativo enquanto o aviso estiver aberto.
- `FluxoRIP.exe --navegador`: força modo navegador no Windows 10/11.
- `FluxoRIP.exe --diagnostico`: escreve `%LOCALAPPDATA%\FORGE\diagnostico_windows.json` com diagnóstico sem varredura de IPs.
- `FluxoRIP.exe --autoteste`: sobe a API temporariamente, verifica interface e Editor de Arte, e encerra.
- `FluxoRIP.exe --verificar`: confere recursos e banco local.

Para a janela integrada, instale [Microsoft Edge WebView2 Runtime](https://developer.microsoft.com/en-us/microsoft-edge/webview2/) caso necessário. O pywebview também pode depender de componentes .NET do Windows. O navegador é uma alternativa quando o runtime não está disponível.

## Scanner Hoson

A aba **Scanner de rede** mostra adaptadores Ethernet, identifica a faixa `/24` local e faz verificações ICMP/ARP na rede selecionada, incluindo redes `192.168.127.0/24` em estações configuradas nessa faixa. O scan de todas as portas Hoson verifica somente interfaces conectadas com IPv4 `192.168.127.x`. Ele **não** altera IPs, gateways, firewall, rotas, firmware nem envia comandos à impressora. Uma resposta de IP/MAC não garante que o dispositivo seja uma placa Hoson.

Requisitos de descoberta: Windows PowerShell com `Get-NetAdapter`, `Get-NetIPAddress`, `Get-NetNeighbor`, além de `ping.exe`. Máquinas conectadas por outros computadores não são descobertas automaticamente; o scanner precisa rodar na estação com a placa de rede local conectada à impressora.

## Dados e recursos opcionais

O executável grava banco, artes, configurações e logs fora do EXE em `%LOCALAPPDATA%\FORGE`. Esses dados não devem ser apagados durante atualizações. O arquivo `production.db` e a pasta `art_storage` das versões anteriores podem ser migrados por cópia, com o aplicativo fechado, e backup prévio.

Recorte, tamanho, DPI e remoção simples de fundo integram o Editor de Arte. Ferramentas externas/opcionais, como rembg ou Real-ESRGAN, exigem instalação e validação próprias e não são incorporadas automaticamente ao EXE. O ComfyUI permanece removido.

## Testes e limites

- Testes unitários e integração de API podem ser executados por `python -m unittest discover -s tests -v`.
- Os testes automatizados incluem **simulações** dos builds Windows 10 e Windows 11. O teste físico no Windows e a compilação real `.exe` devem ser executados no Windows; não foram feitos neste ambiente.
- O FORGE escuta `127.0.0.1` por padrão. A nova opção `--central --host IP-PRIVADO` exige autenticação; HTTP Basic sem TLS é indicado apenas em rede LAN confiável e isolada. Nunca exponha diretamente à internet.
- O suporte padrão ao Windows 10 Home/Pro terminou em 14 de outubro de 2025. Use uma estratégia de atualizações estendidas quando aplicável, sobretudo nos computadores conectados à operação.

Detalhes técnicos em [`docs/COMPATIBILIDADE_WINDOWS_10_11.md`](docs/COMPATIBILIDADE_WINDOWS_10_11.md) e [`docs/SCANNER_DE_REDE_HOSON.md`](docs/SCANNER_DE_REDE_HOSON.md).
